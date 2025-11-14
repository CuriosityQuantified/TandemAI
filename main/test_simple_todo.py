"""Simple test to check todo state structure."""

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

agent = create_deep_agent(
    model=model,
    tools=[],
    checkpointer=MemorySaver(),
)

print("Testing agent with simple query...")

# Simple query
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Create a todo list with 3 tasks: research, write, review"}]},
    config={"configurable": {"thread_id": "test"}}
)

print("\nResult keys:", list(result.keys()))
if "todos" in result:
    print("\nTODOS FOUND in final state:")
    for todo in result["todos"]:
        print(f"  - {todo}")
else:
    print("\nNo todos in final state")

print("\n\nNow testing streaming with 'values' mode:")
for i, state in enumerate(agent.stream(
    {"messages": [{"role": "user", "content": "Create a todo list for building a website: design, develop, deploy"}]},
    config={"configurable": {"thread_id": "test2"}},
    stream_mode="values"
)):
    if "todos" in state:
        print(f"[State {i}] Todos: {state['todos']}")
