"""Inspect actual tool descriptions being sent to Claude."""
import os
import sys
from dotenv import load_dotenv

os.chdir('/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2')
sys.path.insert(0, os.getcwd())
load_dotenv('../.env')

# Import everything needed
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langchain_tavily import TavilySearch
from e2b_code_interpreter import Sandbox

# Create model
model = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.7,
)

# Create minimal tools
tavily_search = TavilySearch(
    max_results=5,
    api_key=os.getenv("TAVILY_API_KEY"),
)

@tool
def test_tool(query: str) -> str:
    """Test tool."""
    return "test"

# Create agent
workspace_dir = "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/agent_workspace"
os.makedirs(workspace_dir, exist_ok=True)

def create_hybrid_backend(rt):
    return CompositeBackend(
        default=StateBackend(rt),
        routes={
            "/workspace/": FilesystemBackend(root_dir=workspace_dir),
        }
    )

agent = create_deep_agent(
    model=model,
    tools=[tavily_search, test_tool],
    backend=create_hybrid_backend,
    checkpointer=MemorySaver(),
    system_prompt="Test agent."
)

# Inspect tool count and descriptions
print("\n" + "=" * 80)
print("TOOL INSPECTION")
print("=" * 80)

# Access the graph to see tools
graph = agent.get_graph()
print(f"\nGraph nodes: {list(graph.nodes.keys())}")

# Get the actual tools being used
from deepagents.graph import create_deep_agent
import inspect

# Try to access the internal tools
print("\n📊 Attempting to access tool definitions...\n")

# The agent should have middleware that adds tools
print("Agent attributes:")
for attr in dir(agent):
    if 'tool' in attr.lower() or 'middleware' in attr.lower():
        print(f"  - {attr}")

# Try to get the compiled graph's tools
try:
    # Look at the graph structure
    print("\nGraph structure:")
    for node_name, node_value in graph.nodes.items():
        print(f"  Node: {node_name}")
        if hasattr(node_value, 'metadata'):
            print(f"    Metadata: {node_value.metadata}")
except Exception as e:
    print(f"  Error: {e}")

print("\n" + "=" * 80)
print("TOKEN ESTIMATE")
print("=" * 80)

# Estimate token count
system_prompt_tokens = len("Test agent.".split()) * 1.3  # rough estimate
print(f"System prompt: ~{int(system_prompt_tokens)} tokens")

# Estimate tool definition tokens (very rough)
tool_count = 2 + 6  # 2 production + 6 filesystem (ls, read, write, edit, glob, grep)
avg_tool_tokens = 80  # conservative estimate per tool
total_tool_tokens = tool_count * avg_tool_tokens

print(f"Estimated tools: {tool_count} × ~{avg_tool_tokens} tokens = ~{total_tool_tokens} tokens")
print(f"\nTotal overhead estimate: ~{int(system_prompt_tokens + total_tool_tokens)} tokens")
print("=" * 80)
