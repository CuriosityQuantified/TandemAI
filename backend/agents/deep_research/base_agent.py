"""Deep Research Agent - Main Supervisor

Orchestrates multi-agent research workflow with configurable effort levels,
search tracking, and HITL capabilities. Adapted from LangChain DeepAgents patterns.
"""

from datetime import datetime
from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_anthropic import ChatAnthropic
from langchain_community.tools.tavily_search import TavilySearchResults

from .state import ResearchState, create_initial_state, trim_action_history, ActionRecord
from .effort_config import get_effort_config, should_continue_searching


# Initialize LLM (using Claude Haiku 4.5 for research tasks)
llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.7)


def planning_node(state: ResearchState) -> ResearchState:
    """Planning phase - create research plan and clarify query

    Args:
        state: Current research state

    Returns:
        Updated state with plan and clarified query
    """
    query = state["query"]
    effort_level = state["effort_level"]
    config = get_effort_config(effort_level)

    # Create planning prompt
    planning_prompt = f"""You are a research planning assistant. Create a comprehensive research plan for the following query:

Query: {query}

Research Configuration:
- Effort Level: {effort_level}
- Minimum Searches: {config.min_searches}
- Depth: {config.depth}
- Use Knowledge Graph: {config.use_knowledge_graph}
- Use Vector RAG: {config.use_vector_rag}

Tasks:
1. Clarify and refine the research question if needed
2. Break down the research into key sub-questions
3. Identify the types of sources needed
4. Suggest search strategies

Provide:
- Clarified Query (one sentence)
- Research Plan (structured breakdown)
"""

    # Get plan from LLM
    response = llm.invoke(planning_prompt)
    plan_content = response.content

    # Extract clarified query (simplified - in production would use structured output)
    clarified_query = query  # Default to original
    if "Clarified Query:" in plan_content:
        lines = plan_content.split("\n")
        for i, line in enumerate(lines):
            if "Clarified Query:" in line:
                clarified_query = line.split(":", 1)[1].strip()
                break

    # Update state
    state["clarified_query"] = clarified_query
    state["phase"] = "researching"
    state["iteration"] = 1

    # Record action
    action = ActionRecord(
        action_type="analyze",
        agent_name="planner",
        input=query,
        output=plan_content,
        timestamp=datetime.now(),
        metadata={"effort_level": effort_level}
    )
    state["action_history"].append(action)
    state["updated_at"] = datetime.now()

    # If HITL enabled and not yet approved, require approval
    if state["hitl_enabled"] and not state["planning_approved"]:
        state["approval_required"] = True
        state["next_action"] = "Wait for user approval of research plan"

    return state


def research_node(state: ResearchState) -> ResearchState:
    """Research phase - perform searches

    Args:
        state: Current research state

    Returns:
        Updated state with search results
    """
    query = state["clarified_query"] or state["query"]
    config = get_effort_config(state["effort_level"])

    # Initialize Tavily search tool
    search = TavilySearchResults(
        max_results=5,
        search_depth="advanced" if config.depth in ["deep", "extended", "definitive"] else "basic",
        include_answer=True,
        include_raw_content=False,
    )

    # Perform search
    try:
        results = search.invoke({"query": query})

        # Process results
        for result in results:
            from .state import SearchResult
            search_result = SearchResult(
                query=query,
                content=result.get("content", ""),
                url=result.get("url", ""),
                title=result.get("title", ""),
                score=result.get("score"),
                timestamp=datetime.now()
            )
            state["search_results"].append(search_result)

        # Update search count
        state["search_count"] = len(state["search_results"])

        # Track query for loop detection
        state["query_history"].append(query)

        # Record action
        action = ActionRecord(
            action_type="search",
            agent_name="researcher",
            input=query,
            output=f"Found {len(results)} results",
            timestamp=datetime.now(),
            metadata={
                "search_count": state["search_count"],
                "min_required": config.min_searches
            }
        )
        state["action_history"].append(action)

    except Exception as e:
        # Handle search errors gracefully
        action = ActionRecord(
            action_type="search",
            agent_name="researcher",
            input=query,
            output=f"Search failed: {str(e)}",
            timestamp=datetime.now(),
            metadata={"error": True}
        )
        state["action_history"].append(action)

    state["updated_at"] = datetime.now()
    state["iteration"] += 1

    # Trim action history to keep context manageable
    state = trim_action_history(state, keep_recent=5)

    return state


def analysis_node(state: ResearchState) -> ResearchState:
    """Analysis phase - synthesize findings

    Args:
        state: Current research state

    Returns:
        Updated state with analysis
    """
    # Get recent search results
    recent_results = state["search_results"][-10:]  # Last 10 results

    # Create analysis prompt
    results_text = "\n\n".join([
        f"Source: {r.title}\nURL: {r.url}\nContent: {r.content}"
        for r in recent_results
    ])

    analysis_prompt = f"""Analyze the following search results and extract key findings:

Query: {state['clarified_query'] or state['query']}

Search Results:
{results_text}

Provide:
1. Key findings (bullet points)
2. Information gaps
3. Suggested next searches
4. Quality assessment (0-1 score)
"""

    # Get analysis
    response = llm.invoke(analysis_prompt)
    analysis = response.content

    # Extract essential findings (simplified)
    if "Key findings:" in analysis or "Key Findings:" in analysis:
        findings_section = analysis.split("Key findings:")[-1].split("\n\n")[0]
        findings = [line.strip("- ").strip() for line in findings_section.split("\n") if line.strip().startswith("-")]
        state["essential_findings"].extend(findings[:5])  # Keep top 5

    # Record action
    action = ActionRecord(
        action_type="analyze",
        agent_name="analyst",
        input=f"Analyzed {len(recent_results)} results",
        output=analysis,
        timestamp=datetime.now()
    )
    state["action_history"].append(action)

    state["phase"] = "analyzing"
    state["updated_at"] = datetime.now()

    return state


def should_continue_node(state: ResearchState) -> Literal["continue", "write", "end"]:
    """Routing function - decide whether to continue research or move to writing

    Args:
        state: Current research state

    Returns:
        Next node name
    """
    # Check if we need approval
    if state["approval_required"]:
        return "end"  # Wait for user input

    # Check if quality threshold met
    if state["quality_threshold_met"] and state["search_count"] >= state["min_searches_required"]:
        return "write"

    # Check if minimum searches met
    quality_score = state["quality_metrics"].overall_score if state["quality_metrics"] else None

    if should_continue_searching(
        state["search_count"],
        state["effort_level"],
        quality_score
    ):
        # Check if under max iterations
        config = get_effort_config(state["effort_level"])
        if state["iteration"] < config.max_iterations:
            return "continue"

    # Default to writing phase
    return "write"


def writing_node(state: ResearchState) -> ResearchState:
    """Writing phase - generate final report

    Args:
        state: Current research state

    Returns:
        Updated state with final report
    """
    # Gather all findings
    all_results = state["search_results"]
    findings = state["essential_findings"]

    # Create writing prompt
    sources_text = "\n\n".join([
        f"[{i+1}] {r.title} ({r.url})\n{r.content}"
        for i, r in enumerate(all_results[-20:])  # Last 20 results
    ])

    writing_prompt = f"""Write a comprehensive research report based on the following findings:

Query: {state['clarified_query'] or state['query']}

Key Findings:
{chr(10).join([f'- {f}' for f in findings])}

Sources:
{sources_text}

Report Requirements:
1. Clear structure with sections
2. Evidence-based claims with citations [1], [2], etc.
3. Comprehensive coverage of the topic
4. Professional academic tone
5. Bibliography at the end

Write the final research report:
"""

    # Generate report
    response = llm.invoke(writing_prompt)
    report = response.content

    state["final_report"] = report
    state["phase"] = "done"
    state["should_continue"] = False

    # Record action
    action = ActionRecord(
        action_type="write",
        agent_name="writer",
        input=f"Synthesized {len(all_results)} sources",
        output=f"Generated report ({len(report)} chars)",
        timestamp=datetime.now()
    )
    state["action_history"].append(action)

    state["updated_at"] = datetime.now()

    return state


def create_deep_research_agent(checkpointer: AsyncPostgresSaver | None = None):
    """Create the deep research agent graph

    Args:
        checkpointer: Optional PostgreSQL checkpointer for state persistence

    Returns:
        Compiled StateGraph
    """
    # Build graph
    workflow = StateGraph(ResearchState)

    # Add nodes
    workflow.add_node("planning", planning_node)
    workflow.add_node("research", research_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("writing", writing_node)

    # Add edges
    workflow.set_entry_point("planning")
    workflow.add_edge("planning", "research")
    workflow.add_edge("research", "analysis")

    # Conditional routing from analysis
    workflow.add_conditional_edges(
        "analysis",
        should_continue_node,
        {
            "continue": "research",
            "write": "writing",
            "end": END,
        }
    )

    # Writing leads to end
    workflow.add_edge("writing", END)

    # Compile
    app = workflow.compile(checkpointer=checkpointer)

    return app
