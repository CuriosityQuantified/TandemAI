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
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Literal, List, Any, TypedDict

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global graph instance
graph = None

# Human-in-the-loop tool for agent to query user
@tool
def query_user(question: str, options: list[str]) -> str:
    """
    Ask the user a question and wait for their response.
    Use this when you need user input, approval, or clarification during your work.

    Args:
        question: The question to ask the user (be clear and concise)
        options: List of possible response options (e.g., ["Yes", "No"], ["Option A", "Option B", "Both"])

    Returns:
        The user's selected response as a string

    Examples:
        - query_user("Should I search for recent or historical data?", ["Recent (last 6 months)", "Historical (last 5 years)", "Both"])
        - query_user("This operation will cost $5. Proceed?", ["Yes, proceed", "No, cancel"])
    """
    # This tool's execution is handled by the frontend's useHumanInTheLoop hook
    # The AG-UI protocol intercepts this call and waits for user response
    pass

def create_minimal_graph():
    """Create a minimal test graph for CopilotKit integration."""

    # CRITICAL: AgentState must extend MessagesState and include tools field
    class AgentState(MessagesState):
        tools: List[Any]  # Required for AG-UI protocol
        plan: List[dict]  # Research plan steps for inline editing

    # Initialize Google Gemini 2.5 Flash model
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",  # Latest Gemini model with 1M token context
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.7,
        max_retries=2,
    )

    def agent_node(state: AgentState):
        """Agent node with human-in-the-loop capabilities and plan execution."""
        messages = state["messages"]
        frontend_tools = state.get("tools", [])  # Get tools from frontend
        plan = state.get("plan", [])  # Get research plan from state

        # Build plan-aware system prompt
        plan_context = ""
        if plan:
            plan_steps = "\n".join([f"{i+1}. {step.get('step', 'Unknown step')} - Status: {step.get('status', 'pending')}"
                                   for i, step in enumerate(plan)])
            plan_context = f"""

CURRENT RESEARCH PLAN:
{plan_steps}

Follow this plan when executing research. If the user has modified the plan, acknowledge the changes and adjust your approach accordingly. Execute steps in order based on their status."""

        system_prompt = SystemMessage(content=f"""You are a helpful research assistant with human-in-the-loop capabilities.{plan_context}

When you need user input or approval, use the query_user tool:
- Ask clear, concise questions
- Provide specific options for the user to choose from
- Use it when multiple approaches are possible
- Use it before potentially expensive or time-consuming operations
- Use it to clarify ambiguous requests

Examples:
- "Should I focus on recent data (last 6 months) or historical data (last 5 years)?"
- "I can search academic papers or news articles. Which would you prefer?"
- "This will search 100+ sources. Proceed?" (options: ["Yes", "No"])

Provide concise, accurate responses and engage the user when needed.""")

        # Bind only frontend tools (query_user is provided by frontend's useCopilotAction)
        # Note: The backend @tool query_user definition above serves as documentation only
        model_with_tools = model.bind_tools(frontend_tools)

        response = model_with_tools.invoke([system_prompt] + list(messages))
        return {"messages": [response]}

    # Create graph with AgentState (includes tools field)
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_edge(START, "agent")
    workflow.add_edge("agent", END)

    # CRITICAL: Compile with checkpointer for state persistence
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)

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
        "version": "2.2-gemini-flash",
        "migration_phase": "Phase 2 - Gemini Migration Complete",
        "model": "gemini-2.5-flash",
        "provider": "Google AI",
        "ag_ui_enabled": graph is not None,
        "hitl_enabled": True,
        "tools": ["query_user"],
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
