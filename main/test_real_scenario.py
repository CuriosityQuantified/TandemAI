"""Test real scenario with Tavily to see if todos are created."""

import os
from dotenv import load_dotenv
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend
from langchain_anthropic import ChatAnthropic
from langchain_tavily import TavilySearch
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

model = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.7,
)

workspace_dir = "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/agent_workspace"
os.makedirs(workspace_dir, exist_ok=True)

def create_hybrid_backend(rt):
    return CompositeBackend(
        default=StateBackend(rt),
        routes={
            "/workspace/": FilesystemBackend(root_dir=workspace_dir, virtual_mode=True),
        }
    )

tavily_search = TavilySearch(
    max_results=5,
    api_key=os.getenv("TAVILY_API_KEY"),
)

agent = create_deep_agent(
    model=model,
    tools=[tavily_search],
    backend=create_hybrid_backend,
    checkpointer=MemorySaver(),
    system_prompt="""AI research assistant with web search and filesystem capabilities.

Tools:
- tavily_search: Web search for current information
- write_todos: Plan and track tasks
- Filesystem: ls, read_file, write_file, edit_file, glob, grep

Best practices:
1. For complex research tasks: Use write_todos for planning first
2. Use tavily_search for research
3. File writing: Prepare full content, then write_file in single call

IMPORTANT: For multi-step tasks, ALWAYS use write_todos tool first to create a plan.
"""
)

query = """Research the benefits of agentic AI systems, create a comparison with traditional AI,
and save a detailed report to /workspace/agentic_ai_report.md"""

print("=" * 80)
print("REAL SCENARIO TEST")
print("=" * 80)
print(f"Query: {query}\n")
print("=" * 80)

config = {"configurable": {"thread_id": "real-test"}}

print("\nStreaming with 'updates' mode:\n")
print("-" * 80)

for i, chunk in enumerate(agent.stream(
    {"messages": [{"role": "user", "content": query}]},
    config=config,
    stream_mode="updates"
)):
    for node_name, node_update in chunk.items():
        if node_name in ("__start__", "__end__"):
            continue

        if not node_update:
            continue

        print(f"\n[Chunk {i}] Node: {node_name}")

        # Check for messages
        if "messages" in node_update:
            messages = node_update["messages"]
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        print(f"  🔧 TOOL CALL: {tool_call['name']}")
                        if tool_call['name'] == 'write_todos':
                            args = tool_call.get('args', {})
                            if 'todos' in args:
                                print(f"  📝 Creating {len(args['todos'])} todos:")
                                for todo in args['todos'][:3]:
                                    print(f"     [{todo.get('status')}] {todo.get('content', '')[:60]}")

        # Check for todos in state update
        if "todos" in node_update:
            todos = node_update["todos"]
            if todos:
                print(f"  📝 TODOS IN STATE: {len(todos)} tasks")
                for todo in todos[:3]:
                    status = todo.get("status", "unknown")
                    content = todo.get("content", "")
                    print(f"     [{status}] {content[:60]}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
