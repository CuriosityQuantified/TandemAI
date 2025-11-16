"""
CopilotKit AG-UI Backend - TandemAI Research Assistant

Replaces 17 REST + 2 WebSocket endpoints with single ag-ui endpoint.
"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import logging

# Add parent directory to path (same pattern as backend_main.py)
parent_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, parent_dir)

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import with relative imports (same pattern as backend_main.py)
from langgraph_studio_graphs import create_unified_graph
from module_2_2_simple import setup_checkpointer

# Global graph instance
graph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize graph with PostgreSQL checkpointer on startup."""
    global graph

    logger.info("🚀 Initializing CopilotKit AG-UI Backend...")

    async with setup_checkpointer() as checkpointer:
        graph = create_unified_graph(custom_checkpointer=checkpointer)
        logger.info("✅ Unified graph initialized")

        # Register ag-ui endpoint after graph is ready
        add_langgraph_fastapi_endpoint(
            app=app,
            agent=LangGraphAGUIAgent(
                name="research_agent",
                description="AI research assistant with planning, execution, and multi-agent delegation",
                graph=graph,
            ),
            path="/copilotkit",
        )
        logger.info("✅ AG-UI endpoint registered at /copilotkit")

        yield

        logger.info("✅ Shutdown complete")

# FastAPI app
app = FastAPI(
    title="TandemAI Research Assistant - CopilotKit",
    version="2.0-copilotkit",
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
        "version": "2.0-copilotkit",
        "migration_phase": "Phase 1 - AG-UI Active",
        "ag_ui_enabled": graph is not None,
    }

if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*80)
    print("TandemAI CopilotKit AG-UI Backend")
    print("="*80)
    print("AG-UI Endpoint: http://localhost:8000/copilotkit")
    print("Health Check: http://localhost:8000/health")
    print("="*80 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
