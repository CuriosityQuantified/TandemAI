"""Test different streaming modes to see where todos appear."""

import os
from dotenv import load_dotenv
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

model = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
)

agent = create_deep_agent(model=model, tools=[], checkpointer=MemorySaver())

query = "Create a 3-step plan to build a mobile app: design, develop, test"

print("=" * 80)
print("TESTING STREAM_MODE='updates'")
print("=" * 80)

for i, chunk in enumerate(agent.stream(
    {"messages": [{"role": "user", "content": query}]},
    config={"configurable": {"thread_id": "test-updates"}},
    stream_mode="updates"
)):
    print(f"\n[Chunk {i}]")
    for node_name, node_update in chunk.items():
        if node_name in ("__start__", "__end__"):
            continue
        print(f"  Node: {node_name}")
        if node_update:
            keys = list(node_update.keys())
            print(f"  Keys: {keys}")
            if "todos" in node_update:
                print(f"  ✅ TODOS IN UPDATE: {node_update['todos']}")

print("\n" + "=" * 80)
print("TESTING STREAM_MODE='values'")
print("=" * 80)

for i, state in enumerate(agent.stream(
    {"messages": [{"role": "user", "content": query}]},
    config={"configurable": {"thread_id": "test-values"}},
    stream_mode="values"
)):
    print(f"\n[State {i}]")
    if "todos" in state and state["todos"]:
        print(f"  ✅ TODOS IN STATE: {state['todos']}")

print("\n" + "=" * 80)
print("TESTING STREAM_MODE='debug'")
print("=" * 80)

for i, event in enumerate(agent.stream(
    {"messages": [{"role": "user", "content": query}]},
    config={"configurable": {"thread_id": "test-debug"}},
    stream_mode="debug"
)):
    if i > 20:  # Limit debug output
        break
    print(f"\n[Event {i}] Type: {event.get('type', 'unknown')}")
    if event.get('type') == 'task_result':
        state = event.get('payload', {}).get('result', {})
        if state and isinstance(state, dict) and "todos" in state:
            print(f"  ✅ TODOS: {state['todos']}")
