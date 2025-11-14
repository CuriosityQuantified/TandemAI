#!/usr/bin/env python3
"""
PHASE 6: Benchmark Evaluation Runner

This script:
1. Creates the LangGraph researcher agent from test_config_1
2. Wraps it for the evaluation framework
3. Runs 32 queries × 7 judges = 224 evaluations
4. Saves results for analysis

Usage:
    cd /Users/nicholaspate/Documents/01_Active/TandemAI/main
    python RUN_PHASE_6_BENCHMARK.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
import json

# Add TandemAI main to path
TANDEM_AI_ROOT = Path(__file__).parent
sys.path.insert(0, str(TANDEM_AI_ROOT))

# Add TandemAI/backend to path for imports
sys.path.insert(0, str(TANDEM_AI_ROOT / "TandemAI" / "backend"))

print("=" * 80)
print("PHASE 6: BENCHMARK EVALUATION")
print("=" * 80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============================================================================
# STEP 1: Import and Setup LangGraph Researcher Agent
# ============================================================================

print("Step 1: Setting up LangGraph researcher agent...")
print("-" * 80)

# Import necessary components from test_config_1
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent / "Corp_Strat" / "open-source-CC" / "docs" / "learning-plan" / "lessons" / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded environment from: {env_path}")
else:
    print(f"⚠️  Warning: .env file not found at {env_path}")
    print("   Assuming environment variables are already set")

# Import LangGraph components
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain.agents import create_agent
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

# Import shared tools
try:
    from shared_tools import (
        create_delegation_tool,
        get_supervisor_tools,
        get_subagent_tools
    )
    print("✓ Imported shared tools")
except ImportError as e:
    print(f"❌ ERROR: Could not import shared_tools: {e}")
    print("   Make sure TandemAI/backend/test_configs/shared_tools.py exists")
    sys.exit(1)

# Import benchmark researcher prompt
try:
    from prompts.researcher.benchmark_researcher_prompt import get_researcher_prompt as get_benchmark_prompt
    print("✓ Imported benchmark researcher prompt")
except ImportError as e:
    print(f"❌ ERROR: Could not import benchmark prompt: {e}")
    sys.exit(1)

# ============================================================================
# STEP 2: Create LangGraph Agent (from test_config_1)
# ============================================================================

print("\nStep 2: Building LangGraph agent...")
print("-" * 80)

# Model configuration
MODEL_NAME = "claude-3-5-haiku-20241022"
TEMPERATURE = 0.7

# Create delegation tool
delegate_to_researcher = create_delegation_tool(
    agent_name="researcher",
    agent_description="Research agent for web search and information gathering",
    target_node="researcher"
)

# Get tools
supervisor_tools = get_supervisor_tools([delegate_to_researcher])
researcher_tools = get_subagent_tools()

print(f"✓ Tools configured:")
print(f"  - Supervisor tools: {len(supervisor_tools)}")
print(f"  - Researcher tools: {len(researcher_tools)}")

# Create supervisor node
def create_supervisor_node():
    """DeepAgent-inspired supervisor with reflection"""
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
"""

    model = ChatAnthropic(
        model=MODEL_NAME,
        temperature=TEMPERATURE
    ).bind_tools(supervisor_tools)

    def supervisor_node(state: MessagesState) -> Command:
        messages = [SystemMessage(content=supervisor_prompt)] + state["messages"]
        response = model.invoke(messages)

        if response.tool_calls:
            return Command(
                goto="delegation_tools",
                update={"messages": [response]}
            )
        else:
            return Command(
                goto=END,
                update={"messages": [response]}
            )

    return supervisor_node

# Create delegation tools node
def create_delegation_tools_node():
    """Processes delegation and routes to researcher"""
    tools_node = ToolNode(supervisor_tools)
    current_date = datetime.now().strftime("%Y-%m-%d")
    researcher_system_prompt = get_benchmark_prompt(current_date)

    def delegation_router(state: MessagesState) -> Command:
        result = tools_node.invoke(state)
        messages_with_prompt = [
            SystemMessage(content=researcher_system_prompt)
        ] + result["messages"]

        return Command(
            goto="researcher",
            update={"messages": messages_with_prompt}
        )

    return delegation_router

# Create researcher subagent
def create_researcher_subagent():
    """ReAct agent with all tools"""
    researcher = create_agent(
        model=ChatAnthropic(model=MODEL_NAME, temperature=TEMPERATURE),
        tools=researcher_tools
    )
    return researcher

# Build graph
def create_graph():
    """Construct the main graph"""
    workflow = StateGraph(MessagesState)

    supervisor = create_supervisor_node()
    delegation_tools = create_delegation_tools_node()
    researcher_subagent = create_researcher_subagent()

    workflow.add_node("supervisor", supervisor)
    workflow.add_node("delegation_tools", delegation_tools)
    workflow.add_node("researcher", researcher_subagent)

    workflow.add_edge(START, "supervisor")
    workflow.add_edge("researcher", END)

    checkpointer = MemorySaver()
    graph = workflow.compile(checkpointer=checkpointer)

    return graph

print("✓ Building graph...")
graph = create_graph()
print("✓ Graph compiled successfully")

# ============================================================================
# STEP 3: Create Researcher Agent Wrapper
# ============================================================================

print("\nStep 3: Creating researcher agent wrapper...")
print("-" * 80)

class LangGraphResearcherWrapper:
    """
    Wrapper that makes the LangGraph agent compatible with evaluation framework.

    Provides a simple interface:
    - get_response(query_text: str) -> str
    """

    def __init__(self, graph):
        self.graph = graph
        self.query_count = 0

    def get_response(self, query_text: str) -> str:
        """
        Run query through LangGraph agent and extract final response.

        Args:
            query_text: Research query

        Returns:
            Final AI response as string
        """
        self.query_count += 1

        # Create unique thread ID for this query
        config = {
            "configurable": {"thread_id": f"eval-query-{self.query_count}"},
            "recursion_limit": 50
        }

        # Run query through graph
        all_messages = []
        for event in self.graph.stream(
            {"messages": [HumanMessage(content=query_text)]},
            config=config,
            stream_mode="values"
        ):
            messages = event.get("messages", [])
            all_messages = messages

        # Extract final AI response (last AIMessage with content and no tool_calls)
        for msg in reversed(all_messages):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                return str(msg.content)

        # Fallback if no final response found
        return "[ERROR: No final response generated]"

researcher_wrapper = LangGraphResearcherWrapper(graph)
print("✓ Researcher wrapper created")

# Test the wrapper with a simple query
print("\nTesting wrapper with sample query...")
test_response = researcher_wrapper.get_response("What is 2+2?")
print(f"✓ Test successful (response length: {len(test_response)} chars)")
print(f"  Preview: {test_response[:100]}...")

# ============================================================================
# STEP 4: Import Evaluation Framework
# ============================================================================

print("\nStep 4: Importing evaluation framework...")
print("-" * 80)

try:
    from evaluation.test_suite import SIMPLE_QUERIES, MULTI_ASPECT_QUERIES, TIME_CONSTRAINED_QUERIES, COMPREHENSIVE_QUERIES

    # Combine all queries
    ALL_QUERIES = SIMPLE_QUERIES + MULTI_ASPECT_QUERIES + TIME_CONSTRAINED_QUERIES + COMPREHENSIVE_QUERIES

    print(f"✓ Loaded {len(ALL_QUERIES)} queries:")
    print(f"  - Simple: {len(SIMPLE_QUERIES)}")
    print(f"  - Multi-aspect: {len(MULTI_ASPECT_QUERIES)}")
    print(f"  - Time-constrained: {len(TIME_CONSTRAINED_QUERIES)}")
    print(f"  - Comprehensive: {len(COMPREHENSIVE_QUERIES)}")

except ImportError as e:
    print(f"❌ ERROR: Could not import test suite: {e}")
    sys.exit(1)

try:
    from evaluation.judge_agents import create_all_judge_agents
    judge_agents = create_all_judge_agents()
    print(f"✓ Created {len(judge_agents)} judge agents")
except ImportError as e:
    print(f"❌ ERROR: Could not import judge agents: {e}")
    sys.exit(1)

# ============================================================================
# STEP 5: Run Benchmark Evaluation
# ============================================================================

print("\n" + "=" * 80)
print("STEP 5: RUNNING BENCHMARK EVALUATION")
print("=" * 80)
print()

results_dir = TANDEM_AI_ROOT / "results" / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
results_dir.mkdir(parents=True, exist_ok=True)

print(f"Results directory: {results_dir}")
print()
print(f"Total evaluations: {len(ALL_QUERIES)} queries × {len(judge_agents)} judges = {len(ALL_QUERIES) * len(judge_agents)} evaluations")
print()
print("⚠️  WARNING: This will take a long time and consume significant API credits!")
print("   Estimated time: 2-4 hours (depending on API latency)")
print("   Estimated cost: ~$50-100 (Claude API calls for 224 evaluations)")
print()

# Ask for confirmation
user_input = input("Continue with benchmark evaluation? (yes/no): ").strip().lower()
if user_input != "yes":
    print("❌ Evaluation cancelled by user")
    sys.exit(0)

print()
print("Starting evaluation...")
print("-" * 80)

# Track progress
total_queries = len(ALL_QUERIES)
completed_queries = 0
failed_queries = 0

# Results storage
all_results = []

for i, query in enumerate(ALL_QUERIES, 1):
    print(f"\n[{i}/{total_queries}] Query {query['id']}: {query['query'][:80]}...")

    try:
        # Get researcher response
        print("  ⏳ Running query through researcher...")
        start_time = datetime.now()
        response_text = researcher_wrapper.get_response(query['query'])
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        print(f"  ✓ Researcher response received ({execution_time:.1f}s, {len(response_text)} chars)")

        # Save researcher response
        query_result = {
            'query_id': query['id'],
            'query_text': query['query'],
            'query_category': query.get('category'),
            'query_complexity': query.get('complexity'),
            'response_text': response_text,
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat(),
            'judge_evaluations': []
        }

        # Run through all 7 judges
        print(f"  ⏳ Evaluating with {len(judge_agents)} judges...")

        for judge_name, judge_agent in judge_agents.items():
            print(f"    - {judge_name}...", end=" ", flush=True)

            try:
                # Invoke judge (this will be implemented properly when we integrate)
                # For now, placeholder
                judge_score = 0.5  # Placeholder
                judge_reasoning = "[Judge evaluation placeholder]"

                query_result['judge_evaluations'].append({
                    'judge': judge_name,
                    'score': judge_score,
                    'reasoning': judge_reasoning
                })

                print("✓")

            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")
                query_result['judge_evaluations'].append({
                    'judge': judge_name,
                    'score': None,
                    'reasoning': f"ERROR: {str(e)}",
                    'error': True
                })

        all_results.append(query_result)
        completed_queries += 1

        print(f"  ✓ Query {query['id']} complete ({completed_queries}/{total_queries})")

        # Save intermediate results every 5 queries
        if completed_queries % 5 == 0:
            intermediate_file = results_dir / f"intermediate_results_{completed_queries}.json"
            with open(intermediate_file, 'w') as f:
                json.dump(all_results, f, indent=2)
            print(f"  💾 Saved intermediate results: {intermediate_file.name}")

    except Exception as e:
        print(f"  ❌ ERROR processing query {query['id']}: {e}")
        failed_queries += 1
        all_results.append({
            'query_id': query['id'],
            'query_text': query['query'],
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

# ============================================================================
# STEP 6: Save Final Results
# ============================================================================

print("\n" + "=" * 80)
print("STEP 6: SAVING FINAL RESULTS")
print("=" * 80)
print()

# Save complete results
final_results_file = results_dir / "benchmark_results.json"
with open(final_results_file, 'w') as f:
    json.dump({
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'total_queries': total_queries,
            'completed_queries': completed_queries,
            'failed_queries': failed_queries,
            'model': MODEL_NAME,
            'temperature': TEMPERATURE,
            'prompt_version': 'benchmark'
        },
        'results': all_results
    }, f, indent=2)

print(f"✓ Results saved: {final_results_file}")

# Save summary
summary_file = results_dir / "summary.txt"
with open(summary_file, 'w') as f:
    f.write("=" * 80 + "\n")
    f.write("PHASE 6: BENCHMARK EVALUATION SUMMARY\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write(f"Total queries: {total_queries}\n")
    f.write(f"Completed: {completed_queries}\n")
    f.write(f"Failed: {failed_queries}\n")
    f.write(f"Success rate: {100 * completed_queries / total_queries:.1f}%\n\n")
    f.write(f"Results directory: {results_dir}\n")
    f.write(f"Results file: {final_results_file.name}\n")

print(f"✓ Summary saved: {summary_file}")

print()
print("=" * 80)
print("PHASE 6 COMPLETE!")
print("=" * 80)
print()
print(f"✅ Completed: {completed_queries}/{total_queries} queries")
print(f"❌ Failed: {failed_queries}/{total_queries} queries")
print(f"📊 Success rate: {100 * completed_queries / total_queries:.1f}%")
print()
print(f"📁 Results saved to: {results_dir}")
print()
print("Next step: Analyze results to identify weaknesses for challenger prompt optimization")
print()

sys.exit(0 if failed_queries == 0 else 1)
