#!/usr/bin/env python3
"""
Single-Query Model Cost Verification Script (Updated with LangChain Native Integrations)

Tests 4 models with a single query to verify actual costs vs estimates:
- Claude 3.5 Haiku (baseline) - via langchain-anthropic
- Gemini 2.5 Flash (middle option) - via langchain-google-genai
- Kimi K2-thinking (reasoning specialist) - via langchain-groq
- Claude 4.5 Haiku (latest) - via langchain-anthropic

Uses LangChain native integrations instead of separate SDKs:
- langchain-anthropic (ChatAnthropic)
- langchain-google-genai (ChatGoogleGenerativeAI)
- langchain-groq (ChatGroq)

Usage:
    cd /Users/nicholaspate/Documents/01_Active/TandemAI/main
    python VERIFY_MODEL_COSTS.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import json

# Add TandemAI main to path
TANDEM_AI_ROOT = Path(__file__).parent
sys.path.insert(0, str(TANDEM_AI_ROOT))

# Add TandemAI/backend to path for imports
sys.path.insert(0, str(TANDEM_AI_ROOT / "TandemAI" / "backend"))

# Add test_configs to path for shared_tools
sys.path.insert(0, str(TANDEM_AI_ROOT / "TandemAI" / "backend" / "test_configs"))

print("=" * 80)
print("SINGLE-QUERY MODEL COST VERIFICATION")
print("=" * 80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============================================================================
# STEP 1: Load Environment and Import Dependencies
# ============================================================================

print("Step 1: Loading environment and dependencies...")
print("-" * 80)

from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent / "Corp_Strat" / "open-source-CC" / "docs" / "learning-plan" / "lessons" / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded environment from: {env_path}")
else:
    print(f"⚠️  Warning: .env file not found at {env_path}")
    print("   Assuming environment variables are already set")

# Verify required API keys
required_keys = {
    "ANTHROPIC_API_KEY": "For Claude models (Haiku 3.5, Haiku 4.5)",
    "GOOGLE_API_KEY": "For Gemini models (Gemini 2.5 Flash)",
    "GROQ_API_KEY": "For Groq models (Kimi K2-thinking)"
}

missing_keys = []
present_keys = []

for key, description in required_keys.items():
    if os.getenv(key):
        present_keys.append(f"{key} - {description}")
    else:
        missing_keys.append(f"{key} - {description}")

if present_keys:
    print("✓ Present API keys:")
    for key in present_keys:
        print(f"  - {key}")

if missing_keys:
    print("\n⚠️  WARNING: Missing optional API keys (some models will be skipped):")
    for key in missing_keys:
        print(f"  - {key}")
    print()
else:
    print("✓ All API keys present - all models can be tested")

# Import LangGraph components
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Import model providers (LangChain native integrations)
from langchain_anthropic import ChatAnthropic
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GOOGLE_AVAILABLE = True
    print("✓ langchain-google-genai available")
except ImportError:
    GOOGLE_AVAILABLE = False
    print("⚠️  langchain-google-genai not installed (pip install langchain-google-genai)")

try:
    from langchain_groq import ChatGroq
    GROQ_AVAILABLE = True
    print("✓ langchain-groq available")
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠️  langchain-groq not installed (pip install langchain-groq)")

# Import Anthropic for token counting
import anthropic

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
    sys.exit(1)

# Import benchmark researcher prompt (direct import to avoid package issues)
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "benchmark_researcher_prompt",
        TANDEM_AI_ROOT / "prompts" / "researcher" / "benchmark_researcher_prompt.py"
    )
    benchmark_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(benchmark_module)
    get_benchmark_prompt = benchmark_module.get_researcher_prompt
    print("✓ Imported benchmark researcher prompt")
except Exception as e:
    print(f"❌ ERROR: Could not import benchmark prompt: {e}")
    sys.exit(1)

# Import test queries
try:
    from evaluation.test_suite import SIMPLE_QUERIES, MULTI_ASPECT_QUERIES
    print("✓ Imported test queries")
except ImportError as e:
    print(f"❌ ERROR: Could not import test suite: {e}")
    sys.exit(1)

# ============================================================================
# STEP 2: Define Model Configurations
# ============================================================================

print("\nStep 2: Defining model configurations...")
print("-" * 80)

# Model configurations with pricing
MODELS = {
    "haiku-3.5": {
        "name": "Claude 3.5 Haiku",
        "model_id": "claude-3-5-haiku-20241022",
        "provider": "anthropic",
        "input_per_mtok": 0.25,
        "output_per_mtok": 1.25,
        "cache_write_per_mtok": 0.30,
        "cache_read_per_mtok": 0.025,
        "supports_caching": True
    },
    "gemini-2.5-flash": {
        "name": "Gemini 2.5 Flash",
        "model_id": "gemini-2.5-flash",
        "provider": "google",
        "input_per_mtok": 0.30,
        "output_per_mtok": 2.50,
        "supports_caching": False  # Gemini uses different caching mechanism
    },
    "llama-3.3-70b": {
        "name": "Llama 3.3 70B",
        "model_id": "llama-3.3-70b-versatile",
        "provider": "groq",
        "input_per_mtok": 0.59,
        "output_per_mtok": 0.79,
        "supports_caching": False
    },
    "sonnet-4.5": {
        "name": "Claude Sonnet 4.5",
        "model_id": "claude-sonnet-4-5-20250929",
        "provider": "anthropic",
        "input_per_mtok": 3.00,
        "output_per_mtok": 15.00,
        "cache_write_per_mtok": 3.75,
        "cache_read_per_mtok": 0.30,
        "supports_caching": True
    }
}

print("Model configurations:")
for key, model in MODELS.items():
    print(f"  - {model['name']}: ${model['input_per_mtok']:.2f}/${model['output_per_mtok']:.2f} per MTok")

# ============================================================================
# STEP 3: Select Test Query
# ============================================================================

print("\nStep 3: Selecting representative test query...")
print("-" * 80)

# Use a multi-aspect query as it's more representative of real usage
test_query = MULTI_ASPECT_QUERIES[0]  # First multi-aspect query
print(f"Selected Query ID: {test_query.id}")
print(f"Query: {test_query.query}")
print(f"Category: {test_query.category.value}")
print(f"Expected Steps: {test_query.expected_steps}")
print()

# ============================================================================
# STEP 4: Create LangGraph Agent Builder Function
# ============================================================================

print("Step 4: Creating agent builder function...")
print("-" * 80)

def create_researcher_agent(model_id: str, provider: str, temperature: float = 0.7):
    """
    Create a LangGraph researcher agent with specified model.

    Args:
        model_id: Model identifier (e.g., "claude-3-5-haiku-20241022")
        provider: Provider name ("anthropic", "google", "groq")
        temperature: Model temperature

    Returns:
        Compiled LangGraph graph
    """
    # Create delegation tool
    delegate_to_researcher = create_delegation_tool(
        agent_name="researcher",
        agent_description="Research agent for web search and information gathering",
        target_node="researcher"
    )

    # Get tools
    supervisor_tools = get_supervisor_tools([delegate_to_researcher])
    researcher_tools = get_subagent_tools()

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

        # Create model based on provider
        if provider == "anthropic":
            model = ChatAnthropic(
                model=model_id,
                temperature=temperature
            ).bind_tools(supervisor_tools)
        elif provider == "google":
            model = ChatGoogleGenerativeAI(
                model=model_id,
                temperature=temperature
            ).bind_tools(supervisor_tools)
        elif provider == "groq":
            model = ChatGroq(
                model=model_id,
                temperature=temperature
            ).bind_tools(supervisor_tools)
        else:
            raise ValueError(f"Unknown provider: {provider}")

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
        from langgraph.prebuilt import ToolNode
        tools_node = ToolNode(supervisor_tools)
        current_date_str = datetime.now().strftime("%Y-%m-%d")
        researcher_system_prompt = get_benchmark_prompt(current_date_str)

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
        # Create model based on provider
        if provider == "anthropic":
            chat_model = ChatAnthropic(model=model_id, temperature=temperature)
        elif provider == "google":
            chat_model = ChatGoogleGenerativeAI(model=model_id, temperature=temperature)
        elif provider == "groq":
            chat_model = ChatGroq(model=model_id, temperature=temperature)
        else:
            raise ValueError(f"Unknown provider: {provider}")

        researcher = create_react_agent(
            model=chat_model,
            tools=researcher_tools
        )
        return researcher

    # Build graph
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

print("✓ Agent builder function created")

# ============================================================================
# STEP 5: Token Counting Function
# ============================================================================

print("\nStep 5: Creating token counting function...")
print("-" * 80)

def count_tokens_anthropic(model_id: str, messages: list) -> Dict[str, int]:
    """
    Count tokens for Anthropic models using official API.

    Args:
        model_id: Anthropic model identifier
        messages: List of message dictionaries

    Returns:
        Dictionary with input_tokens count
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    # Extract system message if present
    system_content = None
    user_messages = []

    # Filter messages to exclude incomplete tool call sequences
    # Anthropic API requires that tool_use blocks must have corresponding tool_result blocks
    filtered_messages = []
    for i, msg in enumerate(messages):
        if isinstance(msg, AIMessage):
            # Check if this AIMessage has tool_calls
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                # Skip this message - it has incomplete tool calls
                # The Anthropic API will reject tool_use without tool_result
                continue
        filtered_messages.append(msg)

    for msg in filtered_messages:
        if isinstance(msg, SystemMessage):
            system_content = msg.content
        elif isinstance(msg, HumanMessage):
            user_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            user_messages.append({"role": "assistant", "content": msg.content})

    # Count tokens
    if system_content:
        response = client.beta.messages.count_tokens(
            model=model_id,
            system=system_content,
            messages=user_messages
        )
    else:
        response = client.beta.messages.count_tokens(
            model=model_id,
            messages=user_messages
        )

    return {
        "input_tokens": response.input_tokens
    }


def estimate_tokens(messages: list) -> Dict[str, int]:
    """
    Estimate tokens for non-Anthropic models using character count.

    Standard estimation: ~4 characters per token

    Args:
        messages: List of LangChain message objects

    Returns:
        Dictionary with estimated input_tokens
    """
    total_chars = 0
    for msg in messages:
        if hasattr(msg, 'content'):
            total_chars += len(str(msg.content))

    # Rough estimate: 4 chars per token
    estimated_tokens = total_chars // 4

    return {
        "input_tokens": estimated_tokens
    }


print("✓ Token counting functions created (Anthropic API + estimation)")

# ============================================================================
# STEP 6: Run Single Query with Each Model
# ============================================================================

print("\n" + "=" * 80)
print("STEP 6: RUNNING SINGLE QUERY WITH 4 MODELS")
print("=" * 80)
print()

results = []

for model_key in ["haiku-3.5", "gemini-2.5-flash", "llama-3.3-70b", "sonnet-4.5"]:
    model_config = MODELS[model_key]
    print(f"\n{'='*80}")
    print(f"Testing: {model_config['name']}")
    print(f"{'='*80}\n")

    # Check if provider integration is available
    skip_reasons = []

    if model_config["provider"] == "google" and not GOOGLE_AVAILABLE:
        skip_reasons.append("langchain-google-genai not installed")
    elif model_config["provider"] == "groq" and not GROQ_AVAILABLE:
        skip_reasons.append("langchain-groq not installed")

    # Check for API key
    provider_key_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "groq": "GROQ_API_KEY"
    }

    required_key = provider_key_map.get(model_config["provider"])
    if required_key and not os.getenv(required_key):
        skip_reasons.append(f"{required_key} not set")

    if skip_reasons:
        print(f"⚠️  SKIPPING: {model_config['name']}")
        for reason in skip_reasons:
            print(f"   - {reason}")
        print(f"\n   To enable this model:")
        if "not installed" in skip_reasons[0]:
            package = "langchain-google-genai" if "google" in skip_reasons[0] else "langchain-groq"
            print(f"   1. pip install {package}")
        if any("not set" in r for r in skip_reasons):
            print(f"   2. Set {required_key} environment variable")
        results.append({
            "model": model_config["name"],
            "model_key": model_key,
            "status": "skipped",
            "reasons": skip_reasons
        })
        continue

    try:
        # Create agent with this model
        print(f"⏳ Creating agent with {model_config['name']}...")
        graph = create_researcher_agent(
            model_config["model_id"],
            model_config["provider"]
        )
        print(f"✓ Agent created")

        # Run query
        print(f"⏳ Running query...")
        start_time = datetime.now()

        config = {
            "configurable": {"thread_id": f"verify-{model_key}"},
            "recursion_limit": 50
        }

        all_messages = []
        for event in graph.stream(
            {"messages": [HumanMessage(content=test_query.query)]},
            config=config,
            stream_mode="values"
        ):
            messages = event.get("messages", [])
            all_messages = messages

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        # Extract final response
        final_response = None
        for msg in reversed(all_messages):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                final_response = str(msg.content)
                break

        if not final_response:
            final_response = "[ERROR: No final response generated]"

        response_length = len(final_response)

        print(f"✓ Query completed in {execution_time:.1f}s")
        print(f"  Response length: {response_length} characters")

        # Count tokens
        print(f"⏳ Counting tokens...")
        if model_config["provider"] == "anthropic":
            # Use Anthropic's official token counting API
            token_data = count_tokens_anthropic(model_config["model_id"], all_messages)
            input_tokens = token_data["input_tokens"]
            token_method = "Anthropic API"
        else:
            # Estimate for other providers
            token_data = estimate_tokens(all_messages)
            input_tokens = token_data["input_tokens"]
            token_method = "Character-based estimation"

        # Estimate output tokens (rough estimate: chars / 4)
        output_tokens = response_length // 4

        print(f"✓ Token count (method: {token_method}):")
        print(f"  Input tokens: {input_tokens:,}")
        print(f"  Output tokens (estimated): {output_tokens:,}")

        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * model_config["input_per_mtok"]
        output_cost = (output_tokens / 1_000_000) * model_config["output_per_mtok"]
        total_cost = input_cost + output_cost

        print(f"✓ Cost calculation:")
        print(f"  Input cost: ${input_cost:.4f}")
        print(f"  Output cost: ${output_cost:.4f}")
        print(f"  Total cost: ${total_cost:.4f}")

        results.append({
            "model": model_config["name"],
            "model_key": model_key,
            "provider": model_config["provider"],
            "status": "success",
            "token_counting_method": token_method,
            "execution_time": execution_time,
            "response_length": response_length,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "input_price_per_mtok": model_config["input_per_mtok"],
            "output_price_per_mtok": model_config["output_per_mtok"]
        })

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        results.append({
            "model": model_config["name"],
            "model_key": model_key,
            "status": "error",
            "error": str(e)
        })

# ============================================================================
# STEP 7: Generate Comparison Report
# ============================================================================

print("\n" + "=" * 80)
print("STEP 7: COMPARISON REPORT")
print("=" * 80)
print()

# Find baseline (Haiku 3.5)
baseline = next((r for r in results if r["model_key"] == "haiku-3.5" and r["status"] == "success"), None)

if baseline:
    print("BASELINE: Claude 3.5 Haiku")
    print("-" * 80)
    print(f"Execution time: {baseline['execution_time']:.1f}s")
    print(f"Total cost: ${baseline['total_cost']:.4f}")
    print(f"Input tokens: {baseline['input_tokens']:,}")
    print(f"Output tokens: {baseline['output_tokens']:,}")
    print()

    print("COMPARISONS vs BASELINE:")
    print("-" * 80)

    for result in results:
        if result["status"] == "success" and result["model_key"] != "haiku-3.5":
            cost_diff = result["total_cost"] - baseline["total_cost"]
            cost_pct = ((result["total_cost"] / baseline["total_cost"]) - 1) * 100
            time_diff = result["execution_time"] - baseline["execution_time"]
            time_pct = ((result["execution_time"] / baseline["execution_time"]) - 1) * 100

            print(f"\n{result['model']}:")
            print(f"  Cost: ${result['total_cost']:.4f} ({cost_diff:+.4f}, {cost_pct:+.1f}%)")
            print(f"  Time: {result['execution_time']:.1f}s ({time_diff:+.1f}s, {time_pct:+.1f}%)")
            print(f"  Input tokens: {result['input_tokens']:,}")
            print(f"  Output tokens: {result['output_tokens']:,}")
        elif result["status"] == "skipped":
            print(f"\n{result['model']}: SKIPPED - {', '.join(result['reasons'])}")
        elif result["status"] == "error":
            print(f"\n{result['model']}: ERROR - {result['error']}")
else:
    print("⚠️  WARNING: Baseline (Haiku 3.5) test did not complete successfully")
    print("   Cannot generate comparison report")

# ============================================================================
# STEP 8: Save Results
# ============================================================================

print("\n" + "=" * 80)
print("STEP 8: SAVING RESULTS")
print("=" * 80)
print()

results_file = TANDEM_AI_ROOT / "results" / f"model_cost_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
results_file.parent.mkdir(parents=True, exist_ok=True)

with open(results_file, 'w') as f:
    json.dump({
        "timestamp": datetime.now().isoformat(),
        "test_query": {
            "id": test_query.id,
            "query": test_query.query,
            "category": str(test_query.category),
            "expected_steps": test_query.expected_steps
        },
        "results": results
    }, f, indent=2)

print(f"✓ Results saved: {results_file}")

# ============================================================================
# STEP 9: Summary
# ============================================================================

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
print()

successful_tests = [r for r in results if r["status"] == "success"]
skipped_tests = [r for r in results if r["status"] == "skipped"]
failed_tests = [r for r in results if r["status"] == "error"]

print(f"✅ Successful: {len(successful_tests)}/4 models")
print(f"⏭️  Skipped: {len(skipped_tests)}/4 models")
print(f"❌ Failed: {len(failed_tests)}/4 models")
print()

if successful_tests:
    print("COST SUMMARY (Single Query):")
    print("-" * 80)
    for result in sorted(successful_tests, key=lambda x: x["total_cost"]):
        print(f"{result['model']:30s} ${result['total_cost']:.4f}")
    print()

if skipped_tests:
    print("SKIPPED MODELS:")
    print("-" * 80)
    for result in skipped_tests:
        print(f"  - {result['model']}: {', '.join(result['reasons'])}")
    print()
    print("NOTE: Install missing packages and set API keys to test all models")
    print("      pip install langchain-google-genai langchain-groq")
    print("      Refer to LANGCHAIN_MODEL_INTEGRATIONS.md for setup instructions")
    print()

print(f"📁 Full results saved to: {results_file}")
print()
print("Next steps:")
print("  1. Review actual costs vs estimates in ESTIMATE_PHASE_6_COST.py")
print("  2. Decide which model(s) to use for full Phase 6 benchmark")
print("  3. Run RUN_PHASE_6_BENCHMARK.py with selected model")
print()

sys.exit(0 if len(failed_tests) == 0 else 1)
