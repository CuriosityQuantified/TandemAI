"""
CopilotKit AG-UI Backend - Minimal Test Version

Demonstrates CopilotKit AG-UI endpoint with a simple graph.
This is a test to verify CopilotKit integration before full migration.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import logging

# LangGraph imports for minimal graph
from langgraph.graph import StateGraph, END, START, MessagesState
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from typing import Literal

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global graph instance
graph = None

def create_minimal_graph():
    """Create a minimal test graph for CopilotKit integration."""

    # Initialize Claude model
    model = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.7,
    )

    def agent_node(state: MessagesState):
        """Simple agent that responds to messages."""
        messages = state["messages"]
        system_prompt = SystemMessage(content="You are a helpful research assistant. Provide concise, accurate responses.")
        response = model.invoke([system_prompt] + list(messages))
        return {"messages": [response]}

    # Create simple graph
    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", agent_node)
    workflow.add_edge(START, "agent")
    workflow.add_edge("agent", END)

    return workflow.compile()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize minimal graph on startup."""
    global graph

    logger.info("🚀 Initializing CopilotKit AG-UI Backend (Minimal Test)...")

    graph = create_minimal_graph()
    logger.info("✅ Minimal test graph initialized")

    # Register ag-ui endpoint
    add_langgraph_fastapi_endpoint(
        app=app,
        agent=LangGraphAGUIAgent(
            name="research_agent",
            description="AI research assistant (minimal test version)",
            graph=graph,
        ),
        path="/copilotkit",
    )
    logger.info("✅ AG-UI endpoint registered at /copilotkit")

    yield

    logger.info("✅ Shutdown complete")

# FastAPI app
app = FastAPI(
    title="TandemAI Research Assistant - CopilotKit (Minimal Test)",
    version="2.0-copilotkit-test",
    lifespan=lifespan
)

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    """Health check with migration status."""
    return {
        "status": "healthy",
        "version": "2.0-copilotkit-test",
        "migration_phase": "Phase 1 - AG-UI Test",
        "ag_ui_enabled": graph is not None,
    }

if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*80)
    print("TandemAI CopilotKit AG-UI Backend (Minimal Test)")
    print("="*80)
    print("AG-UI Endpoint: http://localhost:8000/copilotkit")
    print("Health Check: http://localhost:8000/health")
    print("="*80 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
