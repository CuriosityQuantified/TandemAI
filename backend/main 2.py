"""
Enhanced Backend for Module 2.2 Frontend
Adds support for progress logs and better streaming
"""

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
import json

# Add parent directory to path
parent_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, parent_dir)

# Import the existing agent
from module_2_2_simple import agent

app = FastAPI(title="DeepAgent Research API v2.3")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003", "http://localhost:3004"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def stream_agent_response(query: str):
    """Stream agent execution with enhanced log support."""

    for chunk in agent.stream(
        {"messages": [{"role": "user", "content": query}]},
        config={"configurable": {"thread_id": "web-session"}},
        stream_mode="updates",
    ):
        for node_name, node_update in chunk.items():
            if node_name in ["__start__", "__end__"]:
                continue

            # Skip if update is None or empty
            if not node_update:
                continue

            # Emit enhanced event types
            event_data = {"type": "node_update", "node": node_name, "data": {}}

            # Handle messages
            if "messages" in node_update:
                messages = node_update["messages"]
                for msg in messages:
                    # LLM thinking/reasoning (AIMessage with content)
                    if hasattr(msg, "content") and msg.content and hasattr(msg, "tool_calls"):
                        # If there's content AND tool_calls, emit thinking before tools
                        if msg.content and msg.tool_calls:
                            yield f"data: {
                                json.dumps(
                                    {
                                        'type': 'llm_thinking',
                                        'content': str(msg.content),
                                    }
                                )
                            }\n\n"
                        # If there's content but NO tool_calls, it's the final response
                        elif msg.content and not msg.tool_calls:
                            yield f"data: {
                                json.dumps(
                                    {
                                        'type': 'llm_final_response',
                                        'content': str(msg.content),
                                    }
                                )
                            }\n\n"

                    # Tool calls with full arguments
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            yield f"data: {
                                json.dumps(
                                    {
                                        'type': 'tool_call',
                                        'tool': tool_call['name'],
                                        'args': tool_call.get('args', {}),
                                    }
                                )
                            }\n\n"

                    # Tool results (full content, no truncation)
                    elif hasattr(msg, "tool_call_id"):
                        yield f"data: {
                            json.dumps(
                                {
                                    'type': 'tool_result',
                                    'content': str(msg.content),
                                }
                            )
                        }\n\n"

            # Handle progress logs (NEW!)
            if "logs" in node_update:
                for log in node_update["logs"]:
                    yield f"data: {
                        json.dumps(
                            {
                                'type': 'progress_log',
                                'message': log['message'],
                                'done': log['done'],
                            }
                        )
                    }\n\n"


@app.post("/api/chat")
async def chat(request: Request):
    """Chat endpoint with streaming support."""
    body = await request.json()
    query = body.get("message", "")

    return StreamingResponse(
        stream_agent_response(query), media_type="text/event-stream"
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.3"}


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 80)
    print("DeepAgent Research API v2.3 - Enhanced Backend")
    print("=" * 80)
    print("Features:")
    print("  ✅ Progress logging support")
    print("  ✅ Citation-aware streaming")
    print("  ✅ Enhanced event types")
    print("=" * 80)
    print("\nStarting server at http://localhost:8000")
    print("Frontend: http://localhost:3000")
    print("\n" + "=" * 80 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
