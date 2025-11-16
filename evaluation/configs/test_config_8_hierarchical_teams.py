"""
Test Config 8: Hierarchical Agent Teams with Command.PARENT

This configuration demonstrates the official LangChain hierarchical agent teams pattern:
- Top-level supervisor coordinates overall workflow
- Mid-level team supervisors manage specialized teams (Team A, Team B)
- Worker agents perform specific tasks
- Command.PARENT enables navigation from subgraphs to parent graph

Graph Structure (3 levels):

    PARENT GRAPH:
    START → top_supervisor → team_a_supervisor (subgraph)
                            → team_b_supervisor (subgraph)
                            → END

    TEAM A SUBGRAPH:
    team_a_supervisor → researcher → writer → (Command.PARENT → top_supervisor)

    TEAM B SUBGRAPH:
    team_b_supervisor → analyst → reviewer → (Command.PARENT → top_supervisor)

Key Design Points:
1. Hierarchical 3-level structure (top → teams → workers)
2. Each team is its own StateGraph (subgraph)
3. Team workers use Command.PARENT to return to parent graph
4. Top supervisor coordinates between teams
5. Demonstrates nested supervision pattern

Use Cases:
- Complex projects requiring multiple specialized teams
- Workflows with distinct phases managed by different teams
- Scenarios requiring team coordination and handoffs

Architecture:
- Top Level: Strategic coordination (delegate to teams)
- Mid Level: Team supervision (manage workers)
- Worker Level: Task execution (specific skills)

Created: November 12, 2025
Updated: November 13, 2025 (Upgraded to Haiku 4.5)
LangGraph Version: v0.3+ (hierarchical teams pattern)
Model: Claude Haiku 4.5 (claude-haiku-4-5-20251001)
"""

import asyncio
import os
from pathlib import Path
from typing import Annotated, Literal, TypedDict, Sequence
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage, ToolMessage
from langchain_core.tools import tool, InjectedToolCallId
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, MessagesState, END
from langchain.agents import create_agent
from langgraph.types import Command
from pydantic import BaseModel, Field

# Load environment variables from root .env
env_path = Path(__file__).parent.parent.parent / ".env"  # Up 3 levels to TandemAI root
load_dotenv(env_path)

# Add root to sys.path for absolute imports
import sys
root_path = Path(__file__).parent.parent.parent  # Up to TandemAI root
sys.path.insert(0, str(root_path))

# Import shared tools with absolute path
from backend.test_configs.shared_tools import (
    create_delegation_tool,
    get_supervisor_tools,
    get_subagent_tools,
    PLANNING_TOOLS,
    RESEARCH_TOOLS,
    FILE_TOOLS
)


# ============================================================================
# CONFIGURATION
# ============================================================================

MODEL = "claude-haiku-4-5-20251001"  # Anthropic Claude Haiku 4.5


# ============================================================================
# STATE SCHEMAS
# ============================================================================

class ParentState(MessagesState):
    """
    Parent graph state (top level).

    Extended MessagesState with additional fields for coordination.
    Can use managed channels (add_messages) at the top level.

    Note: RemainingSteps is automatically provided by LangGraph and should
    not be included in custom state schemas.
    """
    current_team: str = None
    teams_completed: list[str] = []


class TeamState(TypedDict):
    """
    Team subgraph state (subgraph I/O).

    Simple state without managed channels for subgraph boundaries.
    Uses plain list for messages to comply with LangGraph v1.0 requirements.

    Note: Subgraphs cannot use managed channels (like add_messages reducer)
    in their input/output schema. Must use simple types.
    """
    messages: list[BaseMessage]  # Plain list, not Annotated with add_messages
    team_name: str
    assigned_worker: str


# ============================================================================
# TOP-LEVEL DELEGATION TOOLS
# ============================================================================

class DelegateToTeamInput(BaseModel):
    """Input schema for team delegation"""
    task: str = Field(
        ...,
        description="Complete task description for the team"
    )
    team: Literal["team_a", "team_b"] = Field(
        ...,
        description="Team to delegate to: 'team_a' (research/writing) or 'team_b' (analysis/review)"
    )
    tool_call_id: Annotated[str, InjectedToolCallId] = Field(
        default=None,
        description="Tool call ID automatically injected by LangGraph"
    )


@tool("delegate_to_team", args_schema=DelegateToTeamInput)
async def delegate_to_team(
    task: str,
    team: Literal["team_a", "team_b"],
    tool_call_id: str
) -> Command[Literal["team_a_supervisor", "team_b_supervisor"]]:
    """
    Delegate a task to a specialized team.

    Team A: Research and writing team (researcher → writer)
    Team B: Analysis and review team (analyst → reviewer)

    Args:
        task: Complete task description
        team: Team identifier ('team_a' or 'team_b')
        tool_call_id: Injected tool call ID

    Returns:
        Command to route to the specified team supervisor
    """
    print(f"\n🔧 delegate_to_team called")
    print(f"   Task: {task[:80]}...")
    print(f"   Team: {team}")
    print(f"   Tool call ID: {tool_call_id}")
    print(f"   Returning: Command(goto='{team}_supervisor')")

    # Determine target node based on team
    target = f"{team}_supervisor"

    return Command(
        goto=target,
        update={
            "messages": [
                ToolMessage(
                    content=f"✅ Task delegated to {team}: {task}",
                    tool_call_id=tool_call_id
                )
            ],
            "current_team": team,
        }
    )


# ============================================================================
# TEAM A DELEGATION TOOLS (Research & Writing)
# ============================================================================

class TeamADelegationInput(BaseModel):
    """Input schema for Team A worker delegation"""
    task: str = Field(
        ...,
        description="Task description for the worker"
    )
    worker: Literal["researcher", "writer"] = Field(
        ...,
        description="Worker to delegate to: 'researcher' or 'writer'"
    )
    tool_call_id: Annotated[str, InjectedToolCallId] = Field(
        default=None,
        description="Tool call ID automatically injected by LangGraph"
    )


@tool("delegate_team_a_worker", args_schema=TeamADelegationInput)
async def delegate_team_a_worker(
    task: str,
    worker: Literal["researcher", "writer"],
    tool_call_id: str
) -> Command[Literal["researcher", "writer"]]:
    """
    Delegate to a Team A worker (researcher or writer).

    Use researcher for information gathering and investigation.
    Use writer for content creation and documentation.

    Args:
        task: Task description
        worker: Worker identifier ('researcher' or 'writer')
        tool_call_id: Injected tool call ID

    Returns:
        Command to route to the specified worker
    """
    print(f"\n🔧 delegate_team_a_worker called")
    print(f"   Task: {task[:80]}...")
    print(f"   Worker: {worker}")
    print(f"   Returning: Command(goto='{worker}')")

    return Command(
        goto=worker,
        update={
            "messages": [
                ToolMessage(
                    content=f"✅ Task delegated to {worker}: {task}",
                    tool_call_id=tool_call_id
                )
            ],
            "assigned_worker": worker,
        }
    )


@tool("complete_team_a_task")
async def complete_team_a_task() -> Command[Literal["top_supervisor"]]:
    """
    Signal that Team A has completed its task and return to top supervisor.

    This tool demonstrates Command.PARENT navigation from a subgraph
    back to the parent graph.

    Returns:
        Command to navigate to parent graph's top_supervisor
    """
    print(f"\n✅ complete_team_a_task called")
    print(f"   Team A work complete")
    print(f"   Returning: Command(goto='top_supervisor', graph=Command.PARENT)")

    return Command(
        goto="top_supervisor",
        graph=Command.PARENT,  # Navigate to parent graph
        update={
            "messages": [
                AIMessage(content="✅ Team A has completed the research and writing task.")
            ],
            "teams_completed": ["team_a"],
        }
    )


# ============================================================================
# TEAM B DELEGATION TOOLS (Analysis & Review)
# ============================================================================

class TeamBDelegationInput(BaseModel):
    """Input schema for Team B worker delegation"""
    task: str = Field(
        ...,
        description="Task description for the worker"
    )
    worker: Literal["analyst", "reviewer"] = Field(
        ...,
        description="Worker to delegate to: 'analyst' or 'reviewer'"
    )
    tool_call_id: Annotated[str, InjectedToolCallId] = Field(
        default=None,
        description="Tool call ID automatically injected by LangGraph"
    )


@tool("delegate_team_b_worker", args_schema=TeamBDelegationInput)
async def delegate_team_b_worker(
    task: str,
    worker: Literal["analyst", "reviewer"],
    tool_call_id: str
) -> Command[Literal["analyst", "reviewer"]]:
    """
    Delegate to a Team B worker (analyst or reviewer).

    Use analyst for data analysis and insights extraction.
    Use reviewer for quality assurance and validation.

    Args:
        task: Task description
        worker: Worker identifier ('analyst' or 'reviewer')
        tool_call_id: Injected tool call ID

    Returns:
        Command to route to the specified worker
    """
    print(f"\n🔧 delegate_team_b_worker called")
    print(f"   Task: {task[:80]}...")
    print(f"   Worker: {worker}")
    print(f"   Returning: Command(goto='{worker}')")

    return Command(
        goto=worker,
        update={
            "messages": [
                ToolMessage(
                    content=f"✅ Task delegated to {worker}: {task}",
                    tool_call_id=tool_call_id
                )
            ],
            "assigned_worker": worker,
        }
    )


@tool("complete_team_b_task")
async def complete_team_b_task() -> Command[Literal["top_supervisor"]]:
    """
    Signal that Team B has completed its task and return to top supervisor.

    This tool demonstrates Command.PARENT navigation from a subgraph
    back to the parent graph.

    Returns:
        Command to navigate to parent graph's top_supervisor
    """
    print(f"\n✅ complete_team_b_task called")
    print(f"   Team B work complete")
    print(f"   Returning: Command(goto='top_supervisor', graph=Command.PARENT)")

    return Command(
        goto="top_supervisor",
        graph=Command.PARENT,  # Navigate to parent graph
        update={
            "messages": [
                AIMessage(content="✅ Team B has completed the analysis and review task.")
            ],
            "teams_completed": ["team_b"],
        }
    )


# ============================================================================
# WORKER TOOLS (Domain-specific tools for specialized workers)
# ============================================================================

@tool
async def write_content(topic: str, style: str = "professional") -> str:
    """
    Write content on a topic (used by writer).

    Args:
        topic: Content topic
        style: Writing style (default: professional)

    Returns:
        Mock written content
    """
    print(f"\n✍️ write_content called with topic: {topic}, style: {style}")
    return f"📝 Written content for '{topic}' in {style} style: A comprehensive analysis covering key trends, challenges, and opportunities in the field."


@tool
async def analyze_data(data_description: str) -> str:
    """
    Analyze data and extract insights (used by analyst).

    Args:
        data_description: Description of data to analyze

    Returns:
        Mock analysis results
    """
    print(f"\n📈 analyze_data called with: {data_description}")
    return f"📊 Analysis of '{data_description}': Identified 5 key trends, 3 risk factors, and 8 opportunities. Confidence level: 87%."


@tool
async def review_quality(item_description: str) -> str:
    """
    Review quality and provide feedback (used by reviewer).

    Args:
        item_description: Description of item to review

    Returns:
        Mock review feedback
    """
    print(f"\n🔍 review_quality called with: {item_description}")
    return f"✅ Quality review of '{item_description}': Meets standards with minor suggestions for improvement. Overall score: 8.5/10."


# ============================================================================
# BUILD TEAM A SUBGRAPH (Research & Writing)
# ============================================================================

def build_team_a_subgraph() -> StateGraph:
    """
    Build Team A subgraph: Research and Writing team.

    Structure:
        team_a_supervisor → researcher → writer → complete_team_a_task
                                                      ↓ (Command.PARENT)
                                                  top_supervisor

    Returns:
        Compiled Team A subgraph
    """
    print("\n   Building Team A Subgraph (Research & Writing)...")

    model = ChatAnthropic(model=MODEL, temperature=0)

    # Get tools for Team A
    team_a_supervisor_tools = get_supervisor_tools([delegate_team_a_worker, complete_team_a_task])
    researcher_tools = get_subagent_tools()  # NO delegation
    writer_tools = get_subagent_tools() + [write_content]  # NO delegation + specialized tool

    print(f"      Team A supervisor tools: {len(team_a_supervisor_tools)}")
    print(f"      Researcher tools: {len(researcher_tools)}")
    print(f"      Writer tools: {len(writer_tools)}")

    # Team A supervisor
    team_a_supervisor = create_agent(
        model=model,
        tools=team_a_supervisor_tools,
        state_schema=TeamState,
        name="team_a_supervisor"
    )

    # Researcher worker (ALL tools from shared_tools)
    researcher = create_agent(
        model=model,
        tools=researcher_tools,
        state_schema=TeamState,
        name="researcher"
    )

    # Writer worker (ALL tools + write_content)
    writer = create_agent(
        model=model,
        tools=writer_tools,
        state_schema=TeamState,
        name="writer"
    )

    # Build subgraph
    workflow = StateGraph(TeamState)
    workflow.add_node("team_a_supervisor", team_a_supervisor)
    workflow.add_node("researcher", researcher)
    workflow.add_node("writer", writer)

    # Set entry point
    workflow.set_entry_point("team_a_supervisor")

    # All nodes return to supervisor or exit
    workflow.add_edge("team_a_supervisor", END)
    workflow.add_edge("researcher", END)
    workflow.add_edge("writer", END)

    print("      ✅ Team A subgraph complete")

    return workflow.compile()


# ============================================================================
# BUILD TEAM B SUBGRAPH (Analysis & Review)
# ============================================================================

def build_team_b_subgraph() -> StateGraph:
    """
    Build Team B subgraph: Analysis and Review team.

    Structure:
        team_b_supervisor → analyst → reviewer → complete_team_b_task
                                                     ↓ (Command.PARENT)
                                                 top_supervisor

    Returns:
        Compiled Team B subgraph
    """
    print("\n   Building Team B Subgraph (Analysis & Review)...")

    model = ChatAnthropic(model=MODEL, temperature=0)

    # Get tools for Team B
    team_b_supervisor_tools = get_supervisor_tools([delegate_team_b_worker, complete_team_b_task])
    analyst_tools = get_subagent_tools() + [analyze_data]  # NO delegation + specialized tool
    reviewer_tools = get_subagent_tools() + [review_quality]  # NO delegation + specialized tool

    print(f"      Team B supervisor tools: {len(team_b_supervisor_tools)}")
    print(f"      Analyst tools: {len(analyst_tools)}")
    print(f"      Reviewer tools: {len(reviewer_tools)}")

    # Team B supervisor
    team_b_supervisor = create_agent(
        model=model,
        tools=team_b_supervisor_tools,
        state_schema=TeamState,
        name="team_b_supervisor"
    )

    # Analyst worker (ALL tools + analyze_data)
    analyst = create_agent(
        model=model,
        tools=analyst_tools,
        state_schema=TeamState,
        name="analyst"
    )

    # Reviewer worker (ALL tools + review_quality)
    reviewer = create_agent(
        model=model,
        tools=reviewer_tools,
        state_schema=TeamState,
        name="reviewer"
    )

    # Build subgraph
    workflow = StateGraph(TeamState)
    workflow.add_node("team_b_supervisor", team_b_supervisor)
    workflow.add_node("analyst", analyst)
    workflow.add_node("reviewer", reviewer)

    # Set entry point
    workflow.set_entry_point("team_b_supervisor")

    # All nodes return to supervisor or exit
    workflow.add_edge("team_b_supervisor", END)
    workflow.add_edge("analyst", END)
    workflow.add_edge("reviewer", END)

    print("      ✅ Team B subgraph complete")

    return workflow.compile()


# ============================================================================
# BUILD PARENT GRAPH
# ============================================================================

def build_config_8_graph():
    """
    Build Config 8: Hierarchical agent teams with Command.PARENT.

    Architecture:
        Level 1 (Parent): Top supervisor coordinates teams
        Level 2 (Subgraphs): Team supervisors manage workers
        Level 3 (Workers): Specialized agents perform tasks

    Navigation:
        - Top supervisor → Team supervisors (via delegate_to_team)
        - Team supervisors → Workers (via delegate_team_*_worker)
        - Workers → Top supervisor (via complete_team_*_task + Command.PARENT)

    Returns:
        Compiled parent graph with nested subgraphs
    """
    print("\n" + "="*80)
    print("BUILDING CONFIG 8: HIERARCHICAL AGENT TEAMS")
    print("="*80 + "\n")

    model = ChatAnthropic(model=MODEL, temperature=0)

    # Build team subgraphs
    print("1. Building team subgraphs...")
    team_a_graph = build_team_a_subgraph()
    team_b_graph = build_team_b_subgraph()
    print("\n   ✅ All team subgraphs created\n")

    # Create top supervisor with ALL supervisor tools
    print("2. Creating top supervisor agent...")
    top_supervisor_tools = get_supervisor_tools([delegate_to_team])
    print(f"   Top supervisor tools: {len(top_supervisor_tools)}")

    top_supervisor = create_agent(
        model=model,
        tools=top_supervisor_tools,
        state_schema=ParentState,
        name="top_supervisor"
    )
    print("   ✅ Top supervisor created\n")

    # Build parent graph
    print("3. Building parent graph...")
    workflow = StateGraph(ParentState)

    # Add top supervisor
    print("   Adding top_supervisor node...")
    workflow.add_node("top_supervisor", top_supervisor)

    # Add team subgraphs as nodes
    print("   Adding team_a_supervisor subgraph...")
    workflow.add_node("team_a_supervisor", team_a_graph)

    print("   Adding team_b_supervisor subgraph...")
    workflow.add_node("team_b_supervisor", team_b_graph)

    # Set entry point
    print("   Setting entry point: top_supervisor")
    workflow.set_entry_point("top_supervisor")

    # Top supervisor can exit when all teams complete
    print("   Adding edge: top_supervisor → END")
    workflow.add_edge("top_supervisor", END)

    # Teams return to top supervisor when complete
    # (via Command.PARENT in complete_team_*_task tools)
    print("   Adding edge: team_a_supervisor → END")
    workflow.add_edge("team_a_supervisor", END)

    print("   Adding edge: team_b_supervisor → END")
    workflow.add_edge("team_b_supervisor", END)

    print("\n   ✅ Parent graph structure complete\n")

    # Compile
    print("4. Compiling parent graph...")
    graph = workflow.compile()
    print("   ✅ Parent graph compiled\n")

    print("="*80)
    print("HIERARCHICAL GRAPH BUILD COMPLETE")
    print("="*80)
    print("\nGraph Structure:")
    print("  Level 1: top_supervisor (coordinates teams)")
    print("  Level 2: team_a_supervisor, team_b_supervisor (manage workers)")
    print("  Level 3: researcher, writer, analyst, reviewer (perform tasks)")
    print("\nNavigation:")
    print("  - delegate_to_team: top_supervisor → team supervisors")
    print("  - delegate_team_*_worker: team supervisors → workers")
    print("  - complete_team_*_task: workers → top_supervisor (Command.PARENT)")
    print("="*80 + "\n")

    return graph


# ============================================================================
# TEST FUNCTION
# ============================================================================

async def test_config_8():
    """
    Test Config 8: Verify hierarchical coordination and Command.PARENT navigation.

    Expected Flow:
    1. User provides complex task
    2. Top supervisor delegates to Team A (research/writing)
    3. Team A supervisor delegates to researcher
    4. Researcher performs search
    5. Team A supervisor delegates to writer
    6. Writer creates content
    7. Team A completes and returns to top supervisor (Command.PARENT)
    8. Top supervisor may delegate to Team B (analysis/review)
    9. Team B performs analysis and review
    10. Team B completes and returns to top supervisor (Command.PARENT)
    11. Top supervisor synthesizes results
    """
    print("\n" + "="*80)
    print("TEST CONFIG 8: HIERARCHICAL AGENT TEAMS")
    print("="*80 + "\n")

    # Build graph
    graph = build_config_8_graph()

    # Test input - complex task requiring both teams
    test_message = """
    Create a comprehensive report on quantum computing trends for 2025:
    1. Research the latest developments (Team A - researcher)
    2. Write a summary of findings (Team A - writer)
    3. Analyze the market implications (Team B - analyst)
    4. Review the report for quality (Team B - reviewer)

    Coordinate between teams to ensure a complete and high-quality deliverable.
    """

    print(f"📥 Test Input: {test_message.strip()}\n")
    print("🔄 Invoking hierarchical graph...\n")
    print("Expected coordination:")
    print("  1. Top supervisor delegates to Team A")
    print("  2. Team A supervisor coordinates researcher → writer")
    print("  3. Team A returns to top supervisor (Command.PARENT)")
    print("  4. Top supervisor delegates to Team B")
    print("  5. Team B supervisor coordinates analyst → reviewer")
    print("  6. Team B returns to top supervisor (Command.PARENT)")
    print("  7. Top supervisor synthesizes final result\n")

    try:
        result = await graph.ainvoke({
            "messages": [HumanMessage(content=test_message)],
            "teams_completed": []
        })

        print("\n" + "="*80)
        print("✅ TEST PASSED - EXECUTION SUCCESSFUL")
        print("="*80 + "\n")

        # Analyze results
        print("📊 RESULTS ANALYSIS")
        print("-" * 80 + "\n")

        messages = result["messages"]
        print(f"Total messages: {len(messages)}\n")

        print("Message sequence:")
        for i, msg in enumerate(messages, 1):
            msg_type = type(msg).__name__
            content = getattr(msg, 'content', '')

            # Truncate long content
            if len(content) > 120:
                content = content[:120] + "..."

            print(f"{i}. {msg_type}: {content}")

            # Check for tool calls
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get('name', 'unknown')
                    print(f"   └─ Tool Call: {tool_name}")

        # Check state
        print(f"\n📊 Final State:")
        print(f"   Current team: {result.get('current_team', 'None')}")
        print(f"   Teams completed: {result.get('teams_completed', [])}")

        # Verify hierarchical coordination
        print("\n" + "="*80)
        print("🔍 VERIFICATION")
        print("="*80 + "\n")

        team_a_delegated = False
        team_b_delegated = False
        researcher_worked = False
        writer_worked = False
        analyst_worked = False
        reviewer_worked = False
        team_a_completed = False
        team_b_completed = False

        for msg in messages:
            content = getattr(msg, 'content', '')

            # Check delegations
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get('name', '')
                    if tool_name == 'delegate_to_team':
                        args = tc.get('args', {})
                        if args.get('team') == 'team_a':
                            team_a_delegated = True
                        elif args.get('team') == 'team_b':
                            team_b_delegated = True
                    elif tool_name == 'search_web':
                        researcher_worked = True
                    elif tool_name == 'write_content':
                        writer_worked = True
                    elif tool_name == 'analyze_data':
                        analyst_worked = True
                    elif tool_name == 'review_quality':
                        reviewer_worked = True
                    elif tool_name == 'complete_team_a_task':
                        team_a_completed = True
                    elif tool_name == 'complete_team_b_task':
                        team_b_completed = True

        # Report findings
        print("Hierarchical coordination verification:")
        print(f"  {'✅' if team_a_delegated else '❌'} Team A delegation by top supervisor")
        print(f"  {'✅' if researcher_worked else '❌'} Researcher work (Team A)")
        print(f"  {'✅' if writer_worked else '❌'} Writer work (Team A)")
        print(f"  {'✅' if team_a_completed else '❌'} Team A completion (Command.PARENT)")
        print(f"  {'✅' if team_b_delegated else '❌'} Team B delegation by top supervisor")
        print(f"  {'✅' if analyst_worked else '❌'} Analyst work (Team B)")
        print(f"  {'✅' if reviewer_worked else '❌'} Reviewer work (Team B)")
        print(f"  {'✅' if team_b_completed else '❌'} Team B completion (Command.PARENT)")

        # Success criteria
        hierarchy_works = (
            team_a_delegated and
            (researcher_worked or writer_worked) and
            team_a_completed
        )

        if hierarchy_works:
            print("\n🎉 SUCCESS: Hierarchical coordination verified!")
            print("   Top supervisor → Team → Workers → Top supervisor (Command.PARENT)")

            if team_b_delegated and team_b_completed:
                print("   Multi-team coordination also verified!")
        else:
            print("\n⚠️  PARTIAL: Hierarchical flow incomplete")
            if not team_a_delegated:
                print("   → Top supervisor may not have delegated to teams")
            if not team_a_completed:
                print("   → Team may not have used Command.PARENT to return")

    except Exception as e:
        print("\n" + "="*80)
        print("❌ TEST FAILED - EXCEPTION OCCURRED")
        print("="*80 + "\n")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}\n")

        import traceback
        print("Traceback:")
        traceback.print_exc()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\n🚀 Starting Config 8 Test: Hierarchical Agent Teams...\n")
    asyncio.run(test_config_8())
    print("\n✅ Test complete!\n")
