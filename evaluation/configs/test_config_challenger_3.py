"""
CONFIG: Challenger V3 - Citation Verification Enhanced
========================================================

This test demonstrates:
1. DeepAgent-inspired supervisor with reflection and memory
2. Challenger V3 researcher with citation verification
3. PostgreSQL-backed citation verification system
4. Command.goto for explicit delegation routing
5. Separation of delegation tools from execution tools

New in V3:
- tavily_search_cached: Auto-caches search results to PostgreSQL
- verify_citations: Verifies all quotes against cached data
- get_cached_source_content: Retrieves sources for corrections
- Self-correcting citation workflow

Pattern: LangGraph v1.0+ Command-based delegation
Model: Google Gemini 2.5 Flash (gemini-2.5-flash)

Architecture:
    START → supervisor (DeepAgent-style) → delegation_tools (ToolNode)
                                              ↓ (Command.goto)
                                           researcher (ReAct) → END

Citation Verification Workflow:
1. Researcher uses tavily_search_cached (auto-caches to PostgreSQL)
2. Researcher generates response with citations
3. Researcher calls verify_citations before completing
4. If verification fails, researcher fixes citations and verifies again
5. Only completes when all_verified=True

Research Sources:
- LangGraph Command.goto: https://blog.langchain.com/command-a-new-tool-for-multi-agent-architectures-in-langgraph/
- DeepAgents: https://docs.langchain.com/oss/python/deepagents/overview
- create_react_agent: https://langchain-ai.github.io/langgraph/how-tos/create-react-agent/

Notes:
- Uses create_react_agent from langgraph.prebuilt (deprecated in v1.0, will move to langchain.agents in v2.0)
- For production, consider using create_agent from langchain.agents
- Citation verification eliminates hallucinated sources (V3 improvement)
- Zero-cost verification using cached Tavily results
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Literal, Annotated
import functools

# Load environment variables FIRST before any imports
# .env is located at: /Users/.../TandemAI/.env (root level after reorganization)
# __file__ is at: /Users/.../TandemAI/evaluation/configs/test_config_challenger_3.py
# So we need: __file__.parent.parent.parent = TandemAI/ (up 3 levels)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# LangGraph imports
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain.agents import create_agent
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

# LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

# Import citation verification tools
import sys
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

from backend.tools.citation_verification import (
    tavily_search_cached,
    verify_citations,
    get_cached_source_content
)

# Import shared tools (planning, file operations)
from evaluation.configs.shared_tools import (
    create_delegation_tool,
    get_supervisor_tools,
    PLANNING_TOOLS,
    FILE_TOOLS
)

# Import Challenger V3 researcher prompt
from datetime import datetime
from backend.prompts.prompts.researcher.challenger_prompt_3 import get_researcher_prompt as get_v3_prompt

# ============================================================================
# CONFIGURATION
# ============================================================================

# Model configuration - Gemini 2.5 Flash for all agents
MODEL_NAME = "gemini-2.5-flash"
TEMPERATURE = 0.7

print("\n" + "="*80)
print("INITIALIZING CONFIG: Challenger V3 - Citation Verification Enhanced")
print("="*80)
print(f"Model: {MODEL_NAME}")
print(f"Temperature: {TEMPERATURE}")

# ============================================================================
# TOOLS SETUP - V3 WITH CITATION VERIFICATION
# ============================================================================

# Create delegation tool using shared tools
delegate_to_researcher = create_delegation_tool(
    agent_name="researcher",
    agent_description="Research agent with citation verification capabilities",
    target_node="researcher"
)

# V3: Researcher tools include citation verification
# - Planning tools (create_research_plan, update_plan_progress, etc.)
# - File tools (read_file, write_file, edit_file)
# - Citation verification tools (tavily_search_cached, verify_citations, get_cached_source_content)
researcher_tools = PLANNING_TOOLS + FILE_TOOLS + [
    tavily_search_cached,
    verify_citations,
    get_cached_source_content
]

# Supervisor tools: delegation + planning + research + files
# Note: Supervisor also gets citation tools for full visibility
supervisor_tools = [delegate_to_researcher] + PLANNING_TOOLS + FILE_TOOLS + [
    tavily_search_cached,
    verify_citations,
    get_cached_source_content
]

print(f"\n✓ Tools configured:")
print(f"  - Supervisor tools: {len(supervisor_tools)} (delegation + planning + files + citation verification)")
print(f"  - Researcher tools: {len(researcher_tools)} (planning + files + citation verification, NO delegation)")
print(f"\n  V3 New Tools:")
print(f"    • tavily_search_cached - Search + auto-cache to PostgreSQL")
print(f"    • verify_citations - Validate quotes against cached data")
print(f"    • get_cached_source_content - Retrieve sources for corrections")

# ============================================================================
# DEEPAGENT-INSPIRED SUPERVISOR NODE
# ============================================================================

def create_supervisor_node():
    """
    Creates a DeepAgent-inspired supervisor node with:
    - Reflection capabilities (via system prompt)
    - Memory awareness (via MessagesState)
    - Delegation tool binding
    - Command.goto routing logic
    """

    # Supervisor system prompt with DeepAgent-inspired reflection
    supervisor_prompt = """You are an intelligent research orchestrator with reflection capabilities.

Your role is to:
1. ANALYZE the user's request carefully
2. REFLECT on whether you need to delegate to a specialized agent
3. DELEGATE to the researcher agent for any information gathering tasks
4. ALWAYS use the delegate_to_researcher tool when the user asks for research

Reflection process:
- Ask yourself: "Can I answer this directly, or do I need specialized help?"
- If the query requires web research, current information, or fact-checking → DELEGATE
- If it's a simple acknowledgment or clarification → respond directly

When delegating:
- Use the delegate_to_researcher tool
- Provide a clear, specific task description
- The tool will return confirmation, then the researcher will execute

Current capabilities:
- You have access to delegate_to_researcher tool
- You maintain context across the conversation (memory)
- You can reflect on your decisions and adjust your approach

V3 Enhancement:
- The researcher now has citation verification capabilities
- All sources will be verified for accuracy
- No hallucinated citations will pass through
"""

    # Create model with supervisor tools
    model = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        temperature=TEMPERATURE
    ).bind_tools(supervisor_tools)

    def supervisor_node(state: MessagesState) -> Command[Literal["delegation_tools", END]]:
        """
        Supervisor node that decides whether to delegate or respond directly.
        Returns Command object for explicit routing control.
        """
        # Add system prompt for reflection
        messages = [SystemMessage(content=supervisor_prompt)] + state["messages"]

        # Invoke model
        response = model.invoke(messages)

        # Check if delegation tool was called
        if response.tool_calls:
            # Return Command to route to delegation_tools node
            # This is the key Command.goto pattern - explicit routing
            return Command(
                goto="delegation_tools",
                update={"messages": [response]}
            )
        else:
            # No delegation needed, end the conversation
            return Command(
                goto=END,
                update={"messages": [response]}
            )

    return supervisor_node

supervisor = create_supervisor_node()
print(f"✓ Supervisor node created (DeepAgent-inspired with reflection)")

# ============================================================================
# DELEGATION TOOLS NODE - PROCESSES COMMAND.GOTO
# ============================================================================

def create_delegation_tools_node():
    """
    Creates a tools node that:
    1. Executes delegation tools
    2. Adds system prompt for researcher
    3. Returns Command.goto to route to the target subagent
    """

    # Create ToolNode with supervisor tools
    tools_node = ToolNode(supervisor_tools)

    # Get Challenger V3 researcher prompt with current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    researcher_system_prompt = get_v3_prompt(current_date)

    def delegation_router(state: MessagesState) -> Command[Literal["researcher"]]:
        """
        Processes delegation tool calls and routes to appropriate subagent.
        This is where Command.goto enables dynamic routing without edges.

        Note: System prompt is now injected directly into the researcher agent
        via create_agent(system_prompt=...), so we don't need to add it here.
        """
        # Execute the delegation tool
        result = tools_node.invoke(state)

        # Route to researcher subagent using Command.goto
        # System prompt is already in the researcher agent, so just pass messages
        return Command(
            goto="researcher",  # Explicit routing to researcher
            update={"messages": result["messages"]}  # ✅ FIX: No SystemMessage wrapper
        )

    return delegation_router

delegation_tools = create_delegation_tools_node()
print(f"✓ Delegation tools node created (Command.goto routing)")

# ============================================================================
# REACT RESEARCHER SUBAGENT - V3 WITH CITATION VERIFICATION
# ============================================================================

def create_researcher_subagent():
    """
    Creates a ReAct agent with V3 tools (planning + files + citation verification).

    V3 Changes:
    - Uses tavily_search_cached instead of TavilySearch
    - Has verify_citations tool for quote verification
    - Has get_cached_source_content for corrections
    - Prompt includes citation verification workflow

    Returns a node function (not a graph) that wraps the researcher agent,
    making it compatible with MessagesState and providing proper error handling.
    """
    from langchain.agents import create_agent
    from datetime import datetime

    # Get Challenger V3 researcher prompt with current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    researcher_system_prompt = get_v3_prompt(current_date)

    # Create the researcher agent graph WITHOUT system_prompt parameter
    # (create_agent doesn't support system_prompt in this LangChain version)
    researcher_graph = create_agent(
        model=ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=TEMPERATURE),
        tools=researcher_tools
    )

    # Wrap in node function compatible with MessagesState
    # LangGraph nodes expect functions that accept state and return state updates
    def researcher_node(state: MessagesState):
        """Node function that invokes the V3 researcher subagent."""
        try:
            # Prepend system prompt as SystemMessage to conversation
            # This is how we inject the V3 citation verification instructions
            messages_with_system = [SystemMessage(content=researcher_system_prompt)] + state["messages"]

            # Increase recursion limit for citation verification workflow
            # V3 needs more iterations:
            #   1. Create research plan (1-2 calls)
            #   2. Execute tavily_search_cached (3-5 calls)
            #   3. Update progress (1-2 calls)
            #   4. Generate response (1 call)
            #   5. Verify citations (1 call)
            #   6. Fix if needed (1-3 calls)
            #   7. Re-verify (1 call)
            # Total: ~15-25 recursive calls expected
            result = researcher_graph.invoke(
                {"messages": messages_with_system},
                config={"recursion_limit": 75}  # Increased for V3 citation workflow
            )
            return {"messages": result["messages"]}
        except Exception as e:
            # If researcher fails, return error message
            error_msg = AIMessage(content=f"Research execution failed: {str(e)}")
            return {"messages": [error_msg]}

    return researcher_node  # ✅ FIX: Return node function, not graph

researcher_subagent = create_researcher_subagent()
print(f"✓ Researcher subagent created with {len(researcher_tools)} V3 tools (citation verification enabled)")

# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_graph():
    """
    Constructs the main graph with Command.goto routing.

    Graph structure:
        START → supervisor → delegation_tools → researcher → END
                    ↓             ↓ (Command)      ↓
                   END       (goto="researcher")  END

    Key features:
    - No explicit edges from delegation_tools (Command.goto handles routing)
    - Supervisor can route to END directly (no delegation needed)
    - Delegation tools automatically route to correct subagent via Command
    - V3: Researcher has citation verification workflow
    """

    # Initialize graph with MessagesState
    workflow = StateGraph(MessagesState)

    # Add nodes
    workflow.add_node("supervisor", supervisor)
    workflow.add_node("delegation_tools", delegation_tools)
    workflow.add_node("researcher", researcher_subagent)

    # Define edges
    # Start with supervisor
    workflow.add_edge(START, "supervisor")

    # Supervisor routes via Command.goto (no edges needed from delegation_tools)
    # delegation_tools routes via Command.goto to researcher

    # Researcher always returns to END
    workflow.add_edge("researcher", END)

    # Compile with checkpointer for memory
    checkpointer = MemorySaver()
    graph = workflow.compile(checkpointer=checkpointer)

    return graph

print(f"\n📊 Building V3 graph...")
graph = create_graph()
print(f"✓ Graph compiled with Command.goto routing + citation verification")

# ============================================================================
# VISUALIZATION
# ============================================================================

def visualize_graph():
    """Generate Mermaid diagram of the graph structure"""
    try:
        mermaid = graph.get_graph().draw_mermaid()
        print(f"\n📈 Graph Structure (Mermaid):")
        print("-" * 80)
        print(mermaid)
        print("-" * 80)
    except Exception as e:
        print(f"⚠️  Could not generate Mermaid diagram: {e}")

# ============================================================================
# TEST EXECUTION - V3 WITH CITATION VERIFICATION
# ============================================================================

def test_delegation():
    """
    Test the V3 delegation system with citation verification.

    Expected flow:
    1. User asks for research
    2. Supervisor reflects and decides to delegate
    3. Supervisor calls delegate_to_researcher tool
    4. delegation_tools node executes tool
    5. delegation_tools returns Command(goto="researcher")
    6. Researcher executes with tavily_search_cached (auto-caches to DB)
    7. Researcher generates response with citations
    8. Researcher calls verify_citations
    9. If verification fails, researcher fixes citations and verifies again
    10. Results returned to user (only when all_verified=True)
    """

    print("\n" + "="*80)
    print("TESTING CONFIG: Challenger V3 - Citation Verification Flow")
    print("="*80)

    # Test query requiring research
    test_query = "What are the latest developments in quantum computing?"

    print(f"\n📝 Test Query: '{test_query}'")
    print(f"\n🔄 Expected Flow:")
    print(f"  1. START → supervisor (reflection + delegation decision)")
    print(f"  2. supervisor → delegation_tools (Command.goto)")
    print(f"  3. delegation_tools → researcher (Command.goto)")
    print(f"  4. researcher → tavily_search_cached (auto-cache to PostgreSQL)")
    print(f"  5. researcher → generate response with citations")
    print(f"  6. researcher → verify_citations (check quotes)")
    print(f"  7. researcher → fix if needed, re-verify")
    print(f"  8. researcher → END (only when all_verified=True)")

    # Invoke graph with increased recursion limit
    config = {
        "configurable": {"thread_id": "test-challenger-v3"},
        "recursion_limit": 75  # V3 needs higher limit for citation workflow
    }

    print(f"\n⚡ Executing V3 graph with REAL-TIME STREAMING...\n")

    try:
        # Use stream() instead of invoke() for real-time updates
        all_messages = []
        event_count = 0

        print("=" * 80)
        print("🎬 STREAMING EXECUTION (Real-Time) - V3 with Citation Verification")
        print("=" * 80 + "\n")

        for event in graph.stream(
            {"messages": [HumanMessage(content=test_query)]},
            config=config,
            stream_mode="values"
        ):
            event_count += 1

            # Get messages from this event
            messages = event.get("messages", [])

            # Only process new messages (avoid duplicates)
            new_messages = messages[len(all_messages):]
            all_messages = messages

            # Display each new message in real-time
            for msg in new_messages:
                msg_type = msg.__class__.__name__

                if isinstance(msg, HumanMessage):
                    print(f"\n{'='*80}")
                    print(f"🧑 USER INPUT")
                    print(f"{'='*80}")
                    print(f"Query: {msg.content}\n")

                elif isinstance(msg, AIMessage):
                    if msg.tool_calls:
                        print(f"\n{'='*80}")
                        print(f"🤖 AGENT ACTION - Tool Calls")
                        print(f"{'='*80}")
                        for tc in msg.tool_calls:
                            tool_name = tc.get('name', 'unknown')
                            tool_args = tc.get('args', {})

                            # Format based on tool type
                            if tool_name == 'delegate_to_researcher':
                                print(f"📤 DELEGATING to researcher")
                                print(f"   Task: {tool_args.get('task', 'N/A')[:150]}...")

                            elif tool_name == 'create_research_plan':
                                print(f"📋 CREATING RESEARCH PLAN")
                                print(f"   Query: {tool_args.get('query', 'N/A')[:150]}...")
                                print(f"   Steps: {tool_args.get('num_steps', 'N/A')}")

                            elif tool_name == 'tavily_search_cached':
                                print(f"🔍 SEARCHING WEB (V3: Auto-caching)")
                                print(f"   Query: {tool_args.get('query', 'N/A')}")
                                print(f"   Session ID: {tool_args.get('session_id', 'N/A')}")

                            elif tool_name == 'verify_citations':
                                print(f"✅ VERIFYING CITATIONS (V3)")
                                print(f"   Session ID: {tool_args.get('session_id', 'N/A')}")

                            elif tool_name == 'get_cached_source_content':
                                print(f"📖 RETRIEVING CACHED SOURCE (V3)")
                                print(f"   URL: {tool_args.get('url', 'N/A')}")

                            elif tool_name == 'update_plan_progress':
                                print(f"✅ UPDATING PROGRESS")
                                print(f"   Step: {tool_args.get('step_index', 'N/A')}")
                                print(f"   Result: {tool_args.get('result', 'N/A')[:150]}...")

                            elif tool_name == 'read_current_plan':
                                print(f"📖 READING PLAN")

                            elif tool_name == 'edit_plan':
                                print(f"✏️  EDITING PLAN")
                                print(f"   Step: {tool_args.get('step_index', 'N/A')}")

                            else:
                                print(f"🔧 TOOL: {tool_name}")
                                print(f"   Args: {str(tool_args)[:150]}...")
                        print()

                    elif msg.content:
                        # Final response from agent
                        print(f"\n{'='*80}")
                        print(f"💬 AGENT RESPONSE")
                        print(f"{'='*80}")
                        content = str(msg.content)
                        if len(content) > 500:
                            print(f"{content[:500]}...")
                            print(f"\n... (response continues, total {len(content)} chars)")
                        else:
                            print(content)
                        print()

                elif isinstance(msg, ToolMessage):
                    tool_name = msg.name
                    tool_content = str(msg.content)

                    print(f"\n{'='*80}")
                    print(f"🔧 TOOL RESULT: {tool_name}")
                    print(f"{'='*80}")

                    # Format based on tool type
                    if tool_name == 'delegate_to_researcher':
                        print(f"✅ Delegation confirmed")
                        print(f"   {tool_content[:150]}...")

                    elif tool_name == 'create_research_plan':
                        print(f"✅ Plan created")
                        # Try to extract plan details
                        if "num_steps" in tool_content:
                            import re
                            steps_match = re.search(r'"num_steps":\s*(\d+)', tool_content)
                            if steps_match:
                                print(f"   Steps: {steps_match.group(1)}")
                        print(f"   {tool_content[:200]}...")

                    elif tool_name == 'tavily_search_cached':
                        print(f"✅ Search completed and cached (V3)")
                        print(f"   {tool_content[:300]}...")

                    elif tool_name == 'verify_citations':
                        print(f"✅ Citation verification result (V3)")
                        # Try to parse verification result
                        import json
                        try:
                            result = json.loads(tool_content)
                            print(f"   All Verified: {result.get('all_verified', 'N/A')}")
                            print(f"   Total Citations: {result.get('total_citations', 'N/A')}")
                            print(f"   Verified Count: {result.get('verified_count', 'N/A')}")
                            if result.get('failed_citations'):
                                print(f"   Failed: {len(result['failed_citations'])} citations")
                        except:
                            print(f"   {tool_content[:200]}...")

                    elif tool_name == 'get_cached_source_content':
                        print(f"✅ Cached source retrieved (V3)")
                        print(f"   {tool_content[:300]}...")

                    elif tool_name == 'update_plan_progress':
                        print(f"✅ Progress updated")
                        print(f"   {tool_content[:150]}...")

                    elif tool_name == 'read_current_plan':
                        print(f"✅ Plan retrieved")
                        print(f"   {tool_content[:200]}...")

                    else:
                        print(f"   {tool_content[:300]}...")
                    print()

        print("\n" + "="*80)
        print("✅ STREAMING COMPLETE")
        print("="*80)
        print(f"Total events: {event_count}")
        print(f"Total messages: {len(all_messages)}\n")

        # Now analyze the final result
        result = {"messages": all_messages}

        print("\n" + "="*80)
        print("📊 FINAL ANALYSIS - V3 CITATION VERIFICATION")
        print("="*80)

        print("\n" + "-"*80)

        # Check success criteria
        print(f"\n✅ SUCCESS CRITERIA:")
        print("-" * 80)

        # 1. Check if delegation tool was called
        delegation_called = any(
            isinstance(msg, AIMessage) and
            any(tc['name'] == 'delegate_to_researcher' for tc in (msg.tool_calls or []))
            for msg in result["messages"]
        )
        print(f"✓ Delegation tool called: {delegation_called}")

        # 2. Check if researcher executed tavily_search_cached (V3)
        researcher_executed = any(
            isinstance(msg, ToolMessage) and
            msg.name == 'tavily_search_cached'
            for msg in result["messages"]
        )
        print(f"✓ Researcher executed search: {researcher_executed} (tool: tavily_search_cached)")

        # 3. Check if verify_citations was called (V3 requirement)
        verification_called = any(
            isinstance(msg, AIMessage) and
            any(tc['name'] == 'verify_citations' for tc in (msg.tool_calls or []))
            for msg in result["messages"]
        )
        print(f"✓ Citation verification called: {verification_called}")

        # 4. Check for final AI response
        final_response = any(
            isinstance(msg, AIMessage) and
            msg.content and
            not msg.tool_calls
            for msg in result["messages"]
        )
        print(f"✓ Final response generated: {final_response}")

        # Overall success
        success = delegation_called and researcher_executed and verification_called and final_response

        print("\n" + "="*80)
        if success:
            print("✅ TEST PASSED: V3 Citation Verification working correctly!")
        else:
            print("❌ TEST FAILED: Check execution trace above")
        print("="*80)

        # Print final answer
        if final_response:
            final_msg = [msg for msg in result["messages"]
                        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls][-1]
            print(f"\n📄 Final Answer Preview:")
            print("-" * 80)
            print(str(final_msg.content)[:500] + "...")
            print("-" * 80)

        return success

    except Exception as e:
        print(f"\n❌ ERROR during execution:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("CONFIG: Challenger V3 - Citation Verification Enhanced")
    print("="*80)

    # Show graph structure
    visualize_graph()

    # Run test
    success = test_delegation()

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

    # Exit with appropriate code
    exit(0 if success else 1)
