"""
Test script to debug todo visibility in streaming output.

This script will:
1. Create a simple DeepAgent with TodoListMiddleware
2. Stream a complex task that should trigger todo creation
3. Inspect all streaming events to see where todos appear
"""

import os
from dotenv import load_dotenv
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

# Create minimal agent with TodoListMiddleware
model = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.7,
)

agent = create_deep_agent(
    model=model,
    tools=[],
    checkpointer=MemorySaver(),
    system_prompt="You are a helpful AI assistant."
)

print("=" * 80)
print("TODO VISIBILITY TEST")
print("=" * 80)

# Complex query that should trigger todo creation
query = """Create a research report on quantum computing. The report should include:
1. Overview of quantum computing principles
2. Current state of the technology
3. Key players in the industry
4. Future applications
5. Save the report to /workspace/quantum_report.md"""

print(f"\nQuery: {query}\n")
print("=" * 80)

config = {"configurable": {"thread_id": "test-todo"}}

print("\nSTREAMING WITH MODE: 'updates'\n")
print("-" * 80)

for i, chunk in enumerate(agent.stream(
    {"messages": [{"role": "user", "content": query}]},
    config=config,
    stream_mode="updates"
)):
    print(f"\n[Chunk {i}]")
    for node_name, node_update in chunk.items():
        print(f"  Node: {node_name}")
        print(f"  Keys in update: {list(node_update.keys()) if node_update else 'None'}")

        if node_update and "todos" in node_update:
            print(f"  ✅ FOUND TODOS: {node_update['todos']}")

        if node_update and "messages" in node_update:
            for msg in node_update["messages"]:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        print(f"    Tool Call: {tc.get('name', 'unknown')}")
                        if tc.get('name') == 'write_todos':
                            print(f"      ⚠️ write_todos called with args: {tc.get('args', {})}")

print("\n" + "=" * 80)
print("\nNow testing with stream_mode='values'\n")
print("=" * 80)

for i, state in enumerate(agent.stream(
    {"messages": [{"role": "user", "content": query}]},
    config={"configurable": {"thread_id": "test-todo-2"}},
    stream_mode="values"
)):
    print(f"\n[State {i}]")
    print(f"  Keys: {list(state.keys())}")
    if "todos" in state:
        print(f"  ✅ TODOS in state: {state['todos']}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
