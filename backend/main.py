"""
Enhanced Backend for Module 2.2 Frontend
Adds support for progress logs and better streaming
"""

from fastapi import FastAPI, Request, HTTPException, Query, WebSocket, WebSocketDisconnect, Header
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
from pathlib import Path
from contextlib import asynccontextmanager
import sys
import os
import json
import asyncio
import uuid
import logging
import time
import psycopg
from datetime import datetime
from auth import verify_token, create_access_token
from websocket_manager import manager
from file_watcher import FileWatcher
from observability.tracing import get_user_metadata, get_user_tags
from planning_agent import initialize_planning_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path
parent_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, parent_dir)

# Import the approval functions and checkpointer setup
# Note: agent is now None at module level and will be initialized in lifespan
from module_2_2_simple import submit_approval_decision, get_approval_for_tool, setup_checkpointer
import module_2_2_simple

# Import unified graph with all subagent nodes for Command.goto routing
from langgraph_studio_graphs import create_unified_graph

# Import planning agent and middleware
from planning_agent import start_research_with_plan, get_plan_state, create_plan_only
from middleware.plan_websocket_bridge import stream_agent_with_websocket_updates, send_plan_error

# Global variables for file watcher and workspace
file_watcher = None
WORKSPACE_ROOT = Path(__file__).parent / "workspace"
WORKSPACE_ROOT.mkdir(exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup/shutdown.

    Replaces deprecated @app.on_event() decorators with modern async context manager.
    Handles:
    - PostgreSQL checkpointer initialization
    - Agent creation with persistence
    - File watcher startup/shutdown
    """
    global file_watcher

    logger.info("🚀 [Startup] Initializing PostgreSQL checkpointer...")

    # Initialize PostgreSQL checkpointer and create agent
    async with setup_checkpointer() as checkpointer:
        # Create unified graph with all subagent nodes (for Command.goto routing)
        module_2_2_simple.agent = create_unified_graph(custom_checkpointer=checkpointer)
        logger.info("✅ [Startup] Unified graph initialized with PostgreSQL persistence")

        # Initialize planning agent with SAME checkpointer
        initialize_planning_agent(checkpointer)
        logger.info("✅ [Startup] Planning agent initialized with shared checkpointer")

        # Start file watcher
        logger.info("🚀 [Startup] Initializing file watcher...")
        file_watcher = FileWatcher(WORKSPACE_ROOT, manager)
        file_watcher.start()
        logger.info("✅ [Startup] File watcher started successfully")

        yield  # Application runs here

        # Shutdown
        logger.info("🛑 [Shutdown] Stopping file watcher...")
        if file_watcher:
            file_watcher.stop()
        logger.info("✅ [Shutdown] File watcher stopped")
        logger.info("✅ [Shutdown] PostgreSQL checkpointer connection closed")

app = FastAPI(
    title="DeepAgent Research API v2.5",
    lifespan=lifespan  # Modern lifespan pattern replacing @app.on_event()
)

# CORS Configuration from environment
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003").split(",")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# File System API Models
# ============================================================================

class FileMetadata(BaseModel):
    """File metadata information."""
    size: int = Field(..., description="File size in bytes")
    lastModified: float = Field(..., description="Unix timestamp")
    extension: Optional[str] = Field(None, description="File extension")


class FileNode(BaseModel):
    """File tree node structure."""
    id: str = Field(..., description="Unique node identifier")
    name: str = Field(..., description="File/folder name")
    path: str = Field(..., description="Relative path from workspace root")
    type: Literal["file", "directory"] = Field(..., description="Node type")
    children: Optional[List["FileNode"]] = Field(None, description="Child nodes for directories")
    size: Optional[int] = Field(None, description="File size in bytes")
    extension: Optional[str] = Field(None, description="File extension")
    lastModified: float = Field(..., description="Unix timestamp")


FileNode.model_rebuild()


class FileContent(BaseModel):
    """File content with metadata."""
    content: str = Field(..., description="File content as string")
    metadata: FileMetadata


class SaveFileRequest(BaseModel):
    """Request to save file content."""
    path: str = Field(..., description="Relative file path")
    content: str = Field(..., description="File content to save")

    @field_validator('path')
    def validate_path(cls, v):
        # Prevent path traversal attacks
        if '..' in v or v.startswith('/'):
            raise ValueError('Invalid path: path traversal detected')
        return v


class SaveFileResponse(BaseModel):
    """Response from file save operation."""
    success: bool
    message: str
    metadata: Optional[FileMetadata] = None


# ============================================================================
# Security Utilities
# ============================================================================

# Point to the same workspace the agent uses
# This ensures files created by the agent appear in the UI file browser
# WORKSPACE_ROOT and file_watcher now defined at top of file (near lifespan)


def validate_workspace_path(relative_path: str) -> Path:
    """
    Validate and resolve path within workspace.
    Prevents path traversal attacks.

    Args:
        relative_path: Relative path from workspace root

    Returns:
        Resolved absolute path within workspace

    Raises:
        HTTPException: 403 if path is outside workspace
    """
    # Remove leading slashes and normalize
    clean_path = relative_path.lstrip('/')

    # Resolve absolute path
    full_path = (WORKSPACE_ROOT / clean_path).resolve()

    # Ensure path is within workspace
    if not str(full_path).startswith(str(WORKSPACE_ROOT.resolve())):
        raise HTTPException(
            status_code=403,
            detail="Access denied: path outside workspace"
        )

    return full_path


# ============================================================================
# Existing Helper Functions
# ============================================================================

def extract_text_from_content(content):
    """
    Extract text from Claude API content format.

    Claude API sends content as an array of message parts:
    [{'text': 'actual text here', 'type': 'text'}, {'id': '...', 'type': 'tool_use'}]

    This function extracts just the text content from the array.
    If content is already a string, returns it as-is for backwards compatibility.
    """
    if not content:
        return ""

    # If it's already a string, return it
    if isinstance(content, str):
        return content

    # If it's a list/array, find the text part
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict):
                # Look for parts with type='text' or that have a 'text' field
                if part.get('type') == 'text' and 'text' in part:
                    return part['text']
                elif 'text' in part:
                    return part['text']

        # Fallback: if no text part found, stringify the whole thing
        return str(content)

    # Fallback for other types
    return str(content)


def get_agent_display_name(state: dict, node_name: str) -> str:
    """
    Determine agent display name from state and node name.

    Args:
        state: Node state dict (may contain subagent_type)
        node_name: LangGraph node name

    Returns:
        Human-readable agent name (e.g., "Supervisor", "Researcher")
    """
    # Check for subagent_type in state
    if isinstance(state, dict) and state.get('subagent_type'):
        subagent_type = state['subagent_type']
        # Map subagent types to display names
        display_names = {
            'researcher': 'Researcher',
            'data_scientist': 'Data Scientist',
            'expert_analyst': 'Expert Analyst',
            'writer': 'Writer',
            'reviewer': 'Reviewer',
        }
        return display_names.get(subagent_type, subagent_type.title())

    # Default: Supervisor
    return 'Supervisor'


async def stream_agent_response(
    query: str,
    auto_approve: bool = True,
    plan_mode: bool = False,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
):
    """
    Stream agent execution with plan tracking, approval flow, and LangSmith tracing.

    Args:
        query: User query to process
        auto_approve: If True, auto-approve all tool calls. If False, request approval.
        plan_mode: If True, use planning agent workflow. If False, use normal agent (default).
        user_id: Unique user identifier from JWT token (optional)
        session_id: Unique session identifier for this conversation (optional)
    """
    # Import the module-level auto_approve functions and sse_event_queue from module_2_2_simple
    import module_2_2_simple
    from middleware.plan_websocket_bridge import stream_agent_with_websocket_updates
    from planning_agent import start_research_with_plan

    module_2_2_simple.set_auto_approve(auto_approve)

    # Prepare LangSmith metadata and tags
    metadata = get_user_metadata(user_id, session_id)
    tags = get_user_tags(user_id)

    # Generate thread_id from session or user, fallback to "web-session"
    thread_id = session_id or user_id or "web-session"

    # Choose agent based on plan_mode toggle
    if plan_mode:
        # Plan Mode: Create plan ONLY, then pass to main agent for execution
        # Main agent will execute using its full toolset with SSE events for Progress Logs
        # Main agent can update plan via edit_plan tool (broadcasts to Plan Panel)

        logger.info(f"[Plan Mode] Creating research plan for query: {query}")

        # Step 1: Create plan (no execution)
        plan_data = await create_plan_only(query, thread_id, num_steps=5)

        # Step 2: Format plan context for main agent
        plan_context = f"""
PLAN MODE IS ACTIVE - YOU MUST FOLLOW THE RESEARCH PLAN BELOW

RESEARCH PLAN (ID: {plan_data['plan_id']}):
"""
        for idx, step in enumerate(plan_data['steps']):
            plan_context += f"\n{idx + 1}. {step}"

        plan_context += f"""

CRITICAL REQUIREMENTS (YOU MUST FOLLOW THESE):
1. YOU MUST execute each step in order using your available tools (tavily_search, write_file, etc.)
2. YOU MUST call edit_plan(action="mark_completed", step_index=<index>, result="<brief summary>") after completing EACH step
3. YOU MUST complete ALL steps in the plan - skipping steps is NOT allowed
4. YOU MAY modify the plan if absolutely necessary:
   - Add steps: edit_plan(action="add_step", step_text="new step")
   - Remove steps: edit_plan(action="remove_step", step_index=<index>)
   - Update steps: edit_plan(action="update_step", step_index=<index>, step_text="updated text")
5. DO NOT finish until ALL plan steps are completed and marked complete

ORIGINAL USER QUERY: {query}

Begin executing the plan now. Remember: YOU MUST follow the plan step-by-step and mark each step complete."""

        logger.info(f"[Plan Mode] Plan created ({len(plan_data['steps'])} steps). Passing to main agent...")

        # Step 3: Execute main agent with plan context
        # Main agent stream uses "updates" mode → SSE events → Progress Logs populated
        agent_stream = module_2_2_simple.agent.astream(
            {"messages": [{"role": "user", "content": plan_context}]},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="updates"
        )
    else:
        # Normal agent flow: DeepAgent with full toolset (default)
        # Emits standard SSE events for ProgressLogs sidebar
        agent_stream = module_2_2_simple.agent.astream(
            {"messages": [{"role": "user", "content": query}]},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="updates"
        )

    # Use astream for async iteration (PostgreSQL checkpointer requires async)
    async for chunk in agent_stream:
        # Check for pending approval requests in the queue (non-blocking)
        try:
            while True:
                approval_event = module_2_2_simple.sse_event_queue.get_nowait()
                yield f"data: {json.dumps(approval_event)}\n\n"
                await asyncio.sleep(0)  # Force flush
        except asyncio.QueueEmpty:
            pass  # No approval events pending

        # Debug logging for chunk type
        logger.debug(f"[SSE Stream] Chunk type: {type(chunk).__name__}")

        # Handle custom events (tuples) - skip them, WebSocket already broadcasts
        if isinstance(chunk, tuple):
            logger.debug(f"[SSE Stream] Skipping custom event tuple: {chunk[0] if chunk else 'empty'}")
            continue

        # Only process dict chunks (node updates)
        if not isinstance(chunk, dict):
            logger.warning(f"[SSE Stream] Unexpected chunk type: {type(chunk)}, value: {chunk}")
            continue

        # Add error handling for chunk processing
        try:
            for node_name, node_update in chunk.items():
                if node_name in ["__start__", "__end__"]:
                    continue

                # Skip if update is None or empty
                if not node_update:
                    continue

                # Extract agent type from state for identification
                agent_name = get_agent_display_name(node_update, node_name)

                # Emit enhanced event types
                event_data = {"type": "node_update", "node": node_name, "data": {}}

                # Handle messages
                if "messages" in node_update:
                    messages = node_update["messages"]

                    # Ensure messages is iterable
                    # LangGraph can return Overwrite objects in stream_mode="updates"
                    if not isinstance(messages, (list, tuple)):
                        # If it's a single message or Overwrite object, wrap in list
                        messages = [messages]

                    for msg in messages:
                        # LLM thinking/reasoning (AIMessage with content)
                        if hasattr(msg, "content") and msg.content and hasattr(msg, "tool_calls"):
                            # If there's content AND tool_calls, emit thinking before tools
                            if msg.content and msg.tool_calls:
                                yield f"data: {
                                    json.dumps(
                                        {
                                            'type': 'llm_thinking',
                                            'content': extract_text_from_content(msg.content),
                                            'agent': agent_name,
                                        }
                                    )
                                }\n\n"
                                await asyncio.sleep(0)  # Force flush
                            # If there's content but NO tool_calls, it's the final response
                            elif msg.content and not msg.tool_calls:
                                yield f"data: {
                                    json.dumps(
                                        {
                                            'type': 'llm_final_response',
                                            'content': extract_text_from_content(msg.content),
                                            'agent': agent_name,
                                        }
                                    )
                                }\n\n"
                                await asyncio.sleep(0)  # Force flush

                        # Tool calls with full arguments
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tool_call in msg.tool_calls:
                                tool_name = tool_call['name']
                                tool_args = tool_call.get('args', {})

                                # Yield the tool_call event
                                yield f"data: {
                                    json.dumps(
                                        {
                                            'type': 'tool_call',
                                            'tool': tool_name,
                                            'args': tool_args,
                                            'agent': agent_name,
                                        }
                                    )
                                }\n\n"
                                await asyncio.sleep(0)  # Force flush

                        # Tool results (full content, no truncation)
                        elif hasattr(msg, "tool_call_id"):
                            yield f"data: {
                                json.dumps(
                                    {
                                        'type': 'tool_result',
                                        'content': extract_text_from_content(msg.content),
                                        'agent': agent_name,
                                    }
                                )
                            }\n\n"
                            await asyncio.sleep(0)  # Force flush

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
                        await asyncio.sleep(0)  # Force flush
        except AttributeError as e:
            logger.error(f"[SSE Stream] AttributeError processing chunk: {type(chunk)} - {e}")
            logger.error(f"[SSE Stream] Chunk value: {chunk}")
            continue
        except Exception as e:
            logger.error(f"[SSE Stream] Error processing chunk: {e}")
            continue

    # Final queue flush - send any remaining approval events after stream completes
    try:
        while True:
            approval_event = module_2_2_simple.sse_event_queue.get_nowait()
            yield f"data: {json.dumps(approval_event)}\n\n"
            await asyncio.sleep(0)  # Force flush
    except asyncio.QueueEmpty:
        pass  # No more approval events

    # Signal stream completion to frontend
    logger.info(f"[SSE Stream] Completed for thread {thread_id}")
    yield f"data: {json.dumps({'type': 'stream_complete', 'thread_id': thread_id})}\n\n"


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="User message")
    auto_approve: bool = Field(True, description="Whether to auto-approve tool calls")
    plan_mode: bool = Field(False, description="Enable planning workflow (default: direct execution)")
    session_id: Optional[str] = Field(None, description="Session ID for conversation persistence")


@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Chat endpoint with streaming support, approval control, and user-scoped tracing.

    Args:
        request: ChatRequest with message and auto_approve flag
        authorization: Optional JWT token in Authorization header

    Returns:
        StreamingResponse with SSE events
    """
    # Extract user_id from JWT token if present
    user_id = None
    if authorization:
        # Remove "Bearer " prefix if present
        token = authorization.replace("Bearer ", "")
        user_id = verify_token(token)

    # Use session_id from request if provided, otherwise generate new one
    # This enables conversation persistence across multiple messages
    session_id = request.session_id or str(uuid.uuid4())
    logger.info(f"💬 Chat request with session_id: {session_id}")

    return StreamingResponse(
        stream_agent_response(
            request.message,
            auto_approve=request.auto_approve,
            plan_mode=request.plan_mode,
            user_id=user_id,
            session_id=session_id
        ),
        media_type="text/event-stream"
    )


# ============================================================================
# File System API Endpoints
# ============================================================================

@app.get("/api/workspace/tree", response_model=List[FileNode])
async def get_workspace_tree() -> List[FileNode]:
    """
    Return hierarchical file/folder tree structure for workspace.

    Returns:
        List of root FileNode objects with nested children

    Raises:
        HTTPException: 500 if workspace directory doesn't exist
    """
    try:
        if not WORKSPACE_ROOT.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Workspace directory not found: {WORKSPACE_ROOT}"
            )

        def build_tree(directory: Path, base_path: Path) -> List[FileNode]:
            """Recursively build file tree structure."""
            nodes = []

            try:
                items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            except PermissionError:
                return nodes

            for item in items:
                # Skip hidden files
                if item.name.startswith('.'):
                    continue

                relative_path = str(item.relative_to(base_path))
                node_id = relative_path.replace('/', '_').replace('\\', '_')

                if item.is_dir():
                    node = FileNode(
                        id=node_id,
                        name=item.name,
                        path=relative_path,
                        type="directory",
                        children=build_tree(item, base_path),
                        lastModified=item.stat().st_mtime
                    )
                else:
                    stat = item.stat()
                    node = FileNode(
                        id=node_id,
                        name=item.name,
                        path=relative_path,
                        type="file",
                        size=stat.st_size,
                        extension=item.suffix,
                        lastModified=stat.st_mtime
                    )

                nodes.append(node)

            return nodes

        return build_tree(WORKSPACE_ROOT, WORKSPACE_ROOT)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/file", response_model=FileContent)
async def get_file_content(
    path: str = Query(..., description="Relative path from workspace root")
) -> FileContent:
    """
    Return content of specific file.

    Args:
        path: Relative file path from workspace root

    Returns:
        FileContent with content string and metadata

    Raises:
        HTTPException: 400 for invalid path, 404 if file not found, 403 for access denied
    """
    try:
        full_path = validate_workspace_path(path)

        if not full_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {path}")

        if not full_path.is_file():
            raise HTTPException(status_code=400, detail=f"Path is not a file: {path}")

        # Read file content
        try:
            content = full_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Handle binary files
            raise HTTPException(
                status_code=400,
                detail="File is binary and cannot be displayed as text"
            )

        # Get file metadata
        stat = full_path.stat()
        metadata = FileMetadata(
            size=stat.st_size,
            lastModified=stat.st_mtime,
            extension=full_path.suffix
        )

        return FileContent(content=content, metadata=metadata)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/workspace/file", response_model=SaveFileResponse)
async def save_file_content(request: SaveFileRequest) -> SaveFileResponse:
    """
    Save file content and emit SSE event.

    Args:
        request: SaveFileRequest with path and content

    Returns:
        SaveFileResponse with success status and metadata

    Raises:
        HTTPException: 403 for invalid path, 500 for write errors
    """
    try:
        full_path = validate_workspace_path(request.path)

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file content
        full_path.write_text(request.content, encoding='utf-8')

        # Get updated metadata
        stat = full_path.stat()
        metadata = FileMetadata(
            size=stat.st_size,
            lastModified=stat.st_mtime,
            extension=full_path.suffix
        )

        # Note: SSE event emission would be integrated here
        # For Phase 1, we're just returning the response

        return SaveFileResponse(
            success=True,
            message=f"File saved: {request.path}",
            metadata=metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )


class CreateFileRequest(BaseModel):
    """Request model for creating a new file."""
    path: str = Field(..., description="Relative path for new file")
    content: str = Field(default="", description="Initial file content")


class CreateFolderRequest(BaseModel):
    """Request model for creating a new folder."""
    path: str = Field(..., description="Relative path for new folder")


@app.post("/api/workspace/file/new", response_model=SaveFileResponse)
async def create_new_file(request: CreateFileRequest) -> SaveFileResponse:
    """
    Create a new file in the workspace.

    Args:
        request: CreateFileRequest with path and optional content

    Returns:
        SaveFileResponse with success status and metadata

    Raises:
        HTTPException: 403 for invalid path, 409 if file exists, 500 for write errors
    """
    try:
        full_path = validate_workspace_path(request.path)

        # Check if file already exists
        if full_path.exists():
            raise HTTPException(
                status_code=409,
                detail=f"File already exists: {request.path}"
            )

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write initial content
        full_path.write_text(request.content, encoding='utf-8')

        # Get metadata
        stat = full_path.stat()
        metadata = FileMetadata(
            size=stat.st_size,
            lastModified=stat.st_mtime,
            extension=full_path.suffix
        )

        return SaveFileResponse(
            success=True,
            message=f"File created: {request.path}",
            metadata=metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create file: {str(e)}"
        )


@app.post("/api/workspace/folder/new")
async def create_new_folder(request: CreateFolderRequest):
    """
    Create a new folder in the workspace.

    Args:
        request: CreateFolderRequest with path

    Returns:
        Success status and message

    Raises:
        HTTPException: 403 for invalid path, 409 if folder exists, 500 for creation errors
    """
    try:
        full_path = validate_workspace_path(request.path)

        # Check if folder already exists
        if full_path.exists():
            raise HTTPException(
                status_code=409,
                detail=f"Folder already exists: {request.path}"
            )

        # Create folder
        full_path.mkdir(parents=True, exist_ok=False)

        return {
            "success": True,
            "message": f"Folder created: {request.path}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create folder: {str(e)}"
        )


@app.post("/api/auth/token")
async def get_auth_token():
    """Generate authentication token for new user."""
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    return {"access_token": token, "user_id": user_id}


# ============================================================================
# Human-in-the-Loop Approval Endpoints
# ============================================================================

class ApprovalDecisionRequest(BaseModel):
    """Request model for approval decision."""
    request_id: str = Field(..., description="Unique request identifier")
    approved: bool = Field(..., description="Whether to approve the tool call")
    feedback: Optional[str] = Field(None, description="Optional feedback message")


@app.post("/api/approval/decision")
async def approval_decision(request: ApprovalDecisionRequest):
    """
    Receive approval decision from frontend.

    Args:
        request: ApprovalDecisionRequest with request_id, approved, and optional feedback

    Returns:
        {"status": "ok"} if successful, or error details
    """
    try:
        result = await submit_approval_decision(
            request_id=request.request_id,
            approved=request.approved,
            feedback=request.feedback
        )
        return result
    except Exception as e:
        logger.error(f"Error processing approval decision: {e}")
        return {"status": "error", "message": str(e)}


@app.websocket("/ws/plan")
async def plan_websocket_endpoint(websocket: WebSocket, token: str = Query("dummy")):
    """
    WebSocket endpoint for real-time plan event broadcasting.

    This endpoint broadcasts plan events (plan_created, step_started, step_completed)
    to all connected clients for real-time UI updates.

    Args:
        websocket: WebSocket connection
        token: JWT authentication token (optional, defaults to "dummy" for development)
    """
    logger.info("🔌 [Plan WebSocket] New connection request")

    # Accept connection (token validation is optional for plan events)
    await websocket.accept()
    logger.info("🤝 [Plan WebSocket] Connection accepted")

    # Register with connection manager using special "_plan_events" room
    user_id = "plan_subscriber"
    await manager.connect(websocket, "_plan_events", user_id)

    try:
        # Keep connection alive and listen for client messages (if any)
        while True:
            # Wait for messages (mostly just to keep connection alive)
            data = await websocket.receive_text()
            # Plan events are broadcast from the agent, not received from clients
            logger.debug(f"[Plan WebSocket] Received message: {data}")
    except WebSocketDisconnect:
        logger.info("🔌 [Plan WebSocket] Client disconnected")
    except Exception as e:
        logger.error(f"❌ [Plan WebSocket] Error: {e}")
    finally:
        # Cleanup connection
        await manager.disconnect(websocket, "_plan_events", user_id)
        logger.info("✅ [Plan WebSocket] Cleanup complete")


@app.websocket("/ws/workspace/{file_path:path}")
async def websocket_endpoint(websocket: WebSocket, file_path: str, token: str = Query(...)):
    """
    WebSocket endpoint for real-time file synchronization.

    Args:
        websocket: WebSocket connection
        file_path: Relative path from workspace root
        token: JWT authentication token
    """
    logger.info(f"🔌 [WebSocket] New connection request for file: {file_path}")

    # Verify token
    user_id = verify_token(token)
    if not user_id:
        logger.warning(f"🚫 [WebSocket] Invalid token for file: {file_path}")
        await websocket.close(code=1008, reason="Invalid authentication token")
        return

    logger.info(f"✅ [WebSocket] Token verified, user_id: {user_id}")

    # Accept the WebSocket connection (required by ASGI protocol)
    await websocket.accept()
    logger.info(f"🤝 [WebSocket] Connection accepted for {file_path}, user: {user_id}")

    try:
        # Send initial content BEFORE registering with manager
        # This ensures we only track connections that are fully functional
        full_path = validate_workspace_path(file_path)
        if full_path.exists() and full_path.is_file():
            initial_content = full_path.read_text(encoding='utf-8')
            await websocket.send_json({"type": "initial_content", "new_content": initial_content})
            logger.info(f"📤 [WebSocket] Sent initial_content for {file_path} ({len(initial_content)} chars)")
        else:
            logger.warning(f"⚠️  [WebSocket] File not found: {file_path}")

        # Register connection with manager ONLY after initial send succeeds
        # This prevents zombie connections where manager tracks broken sockets
        await manager.connect(websocket, file_path, user_id)
        logger.info(f"📝 [WebSocket] Registered with manager: {file_path}, user: {user_id}")

        # Keep alive with ping/pong
        logger.info(f"💓 [WebSocket] Entering ping/pong keep-alive loop for {file_path}")
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"📨 [WebSocket] Received message from {user_id}: {data[:50]}")
                if data == "ping":
                    await websocket.send_text("pong")
                    logger.debug(f"🏓 [WebSocket] Sent pong to {user_id}")
            except WebSocketDisconnect as e:
                logger.info(f"🔌 [WebSocket] Client disconnected: {file_path}, user: {user_id}, code: {e.code}")
                break
    except Exception as e:
        logger.error(f"❌ [WebSocket] Unexpected error for {file_path}: {type(e).__name__}: {e}")
        return  # Exit immediately - finally block will still run for cleanup
    finally:
        logger.info(f"🧹 [WebSocket] Cleaning up connection: {file_path}, user: {user_id}")
        await manager.disconnect(websocket, file_path, user_id)
        logger.info(f"✅ [WebSocket] Disconnected from manager: {file_path}, user: {user_id}")


# @app.on_event decorators removed - replaced with lifespan context manager above
# The lifespan context manager handles both startup and shutdown events


# ============================================================================
# Planning API Models and Endpoints
# ============================================================================

class ResearchPlanRequest(BaseModel):
    """Request to start research with plan tracking."""
    query: str = Field(..., description="Research query")
    thread_id: Optional[str] = Field(None, description="Optional thread ID for session persistence")


class ResearchPlanResponse(BaseModel):
    """Response from starting a research plan."""
    thread_id: str = Field(..., description="Thread ID for this research session")
    message: str = Field(..., description="Status message")


class PlanStateResponse(BaseModel):
    """Current state of a research plan."""
    plan_id: Optional[str] = Field(None, description="Unique plan identifier")
    plan: List[str] = Field(default_factory=list, description="List of plan steps")
    current_step: int = Field(0, description="Index of current step")
    past_steps: List[tuple] = Field(default_factory=list, description="Completed steps with results")
    progress: float = Field(0.0, description="Completion progress (0.0 to 1.0)")
    response: Optional[str] = Field(None, description="Final response if completed")


@app.post("/api/research/plan/start", response_model=ResearchPlanResponse)
async def start_research_plan(request: ResearchPlanRequest):
    """
    Start a research task with plan tracking and real-time WebSocket updates.

    This endpoint initializes a new research session with:
    - Automatic plan generation
    - SQLite persistence of plan state
    - Real-time WebSocket broadcasts of plan updates

    Args:
        request: ResearchPlanRequest with query and optional thread_id

    Returns:
        ResearchPlanResponse with thread_id and status

    Example:
        POST /api/research/plan/start
        {
            "query": "Analyze the impact of AI on healthcare",
            "thread_id": "optional-custom-id"
        }
    """
    try:
        thread_id = request.thread_id or str(uuid.uuid4())

        # Start research with plan tracking
        # This will stream events via WebSocket automatically through middleware
        async for event in stream_agent_with_websocket_updates(
            start_research_with_plan(request.query, thread_id),
            thread_id=thread_id
        ):
            # Events are automatically broadcast via middleware
            # We just consume the stream here
            pass

        return ResearchPlanResponse(
            thread_id=thread_id,
            message="Research plan started successfully"
        )

    except Exception as e:
        logger.error(f"Error starting research plan: {e}")
        await send_plan_error(str(e), thread_id if 'thread_id' in locals() else "unknown")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/research/plan/{thread_id}", response_model=PlanStateResponse)
async def get_research_plan_state(thread_id: str):
    """
    Retrieve current plan state from database.

    This endpoint fetches the persisted plan state for a given thread,
    including plan steps, progress, and completion status.

    Args:
        thread_id: Thread ID for the research session

    Returns:
        PlanStateResponse with current plan state

    Example:
        GET /api/research/plan/abc-123-def
    """
    try:
        plan_state = await get_plan_state(thread_id)

        if not plan_state:
            raise HTTPException(status_code=404, detail="Plan not found")

        return PlanStateResponse(
            plan_id=plan_state.get("plan_id"),
            plan=plan_state.get("plan", []),
            current_step=plan_state.get("current_step", 0),
            past_steps=plan_state.get("past_steps", []),
            progress=plan_state.get("progress", 0.0),
            response=plan_state.get("response")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving plan state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Conversation History API Endpoints (Phase 2: State Persistence)
# ============================================================================

class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history."""
    thread_id: str = Field(..., description="Thread/session identifier")
    messages: List[dict] = Field(default_factory=list, description="Conversation messages")
    checkpoint_count: int = Field(0, description="Number of checkpoints in conversation")
    latest_checkpoint_timestamp: Optional[float] = Field(None, description="Unix timestamp of latest checkpoint")


@app.get("/api/conversation/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    thread_id: str = Query(..., description="Thread/session identifier (UUID)")
):
    """
    Retrieve conversation history for a given thread_id.

    This endpoint retrieves all messages, tool calls, and state from the PostgreSQL
    checkpointer for a specific conversation thread. It converts LangGraph's internal
    message format to the frontend Log format used by ProgressLogs component.

    Args:
        thread_id: Session/thread identifier (UUID string)

    Returns:
        ConversationHistoryResponse with messages, checkpoint count, and metadata

    Raises:
        HTTPException: 400 if thread_id invalid, 404 if not found, 500 on errors

    Example:
        GET /api/conversation/history?thread_id=550e8400-e29b-41d4-a716-446655440000
    """
    try:
        # Validate thread_id format (basic UUID check)
        if not thread_id or len(thread_id) < 10:
            raise HTTPException(
                status_code=400,
                detail="Invalid thread_id: must be a valid UUID string"
            )

        # Access agent from module_2_2_simple (initialized in lifespan)
        agent = module_2_2_simple.agent
        if agent is None:
            raise HTTPException(
                status_code=500,
                detail="Agent not initialized - server startup may have failed"
            )

        # Retrieve current state for this thread
        logger.info(f"📖 [History] Retrieving state for thread_id: {thread_id}")
        config = {"configurable": {"thread_id": thread_id}}

        try:
            state = await agent.aget_state(config)
        except Exception as e:
            logger.error(f"❌ [History] Failed to retrieve state: {e}")
            # If state retrieval fails, thread likely doesn't exist
            raise HTTPException(
                status_code=404,
                detail=f"Conversation not found for thread_id: {thread_id}"
            )

        # Extract messages from state
        messages = []
        checkpoint_count = 0
        latest_timestamp = None

        if state and state.values and "messages" in state.values:
            raw_messages = state.values["messages"]
            logger.info(f"📊 [History] Found {len(raw_messages)} messages in state")

            # Convert LangGraph messages to frontend Log format
            for msg in raw_messages:
                timestamp = getattr(msg, "additional_kwargs", {}).get("timestamp", time.time())

                # User message (HumanMessage)
                if hasattr(msg, "type") and msg.type == "human":
                    messages.append({
                        "type": "user_message",
                        "message": msg.content if hasattr(msg, "content") else str(msg),
                        "timestamp": timestamp,
                        "done": True
                    })

                # AI message with thinking/reasoning (AIMessage with content)
                elif hasattr(msg, "type") and msg.type == "ai":
                    # Check if this is thinking (has content AND tool_calls) or final response (content only)
                    has_tool_calls = hasattr(msg, "tool_calls") and msg.tool_calls

                    if msg.content:
                        if has_tool_calls:
                            # Thinking/reasoning before tool calls
                            messages.append({
                                "type": "llm_thinking",
                                "message": "🤔 LLM Thinking",
                                "detail": extract_text_from_content(msg.content),
                                "timestamp": timestamp,
                                "done": False
                            })
                        else:
                            # Final response (no tool calls)
                            messages.append({
                                "type": "llm_response",
                                "message": "✨ LLM Response",
                                "detail": extract_text_from_content(msg.content),
                                "timestamp": timestamp,
                                "done": True
                            })

                    # Tool calls
                    if has_tool_calls:
                        for tool_call in msg.tool_calls:
                            messages.append({
                                "type": "tool_call",
                                "message": f"🔧 Tool: {tool_call.get('name', 'Unknown')}",
                                "detail": tool_call.get('args', {}),
                                "timestamp": timestamp,
                                "done": False
                            })

                # Tool result (ToolMessage)
                elif hasattr(msg, "tool_call_id"):
                    messages.append({
                        "type": "tool_result",
                        "message": "📊 Tool Result",
                        "detail": extract_text_from_content(msg.content),
                        "timestamp": timestamp,
                        "done": True
                    })

        # Get checkpoint metadata
        if state and hasattr(state, "metadata"):
            checkpoint_count = 1  # Current state counts as 1 checkpoint
            latest_timestamp = state.metadata.get("timestamp") if state.metadata else None

        # Retrieve state history for checkpoint count (optional - can be expensive)
        try:
            history_count = 0
            async for historical_state in agent.aget_state_history(config):
                history_count += 1
                if history_count >= 10:  # Limit to 10 for performance
                    break

            if history_count > 0:
                checkpoint_count = history_count
                logger.info(f"📊 [History] Found {checkpoint_count} checkpoints in history")
        except Exception as e:
            logger.warning(f"⚠️ [History] Could not retrieve state history count: {e}")

        logger.info(f"✅ [History] Retrieved {len(messages)} messages for thread_id: {thread_id}")

        return ConversationHistoryResponse(
            thread_id=thread_id,
            messages=messages,
            checkpoint_count=checkpoint_count,
            latest_checkpoint_timestamp=latest_timestamp
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [History] Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve conversation history: {str(e)}"
        )


# ============================================================================
# Thread Management API Endpoints (Multi-Conversation Support)
# ============================================================================

class Thread(BaseModel):
    """Thread/conversation metadata model."""
    thread_id: str = Field(..., description="Unique thread identifier (UUID)")
    thread_title: str = Field(default="New Conversation", description="Auto-generated or custom title")
    user_id: str = Field(default="anonymous", description="User identifier")
    created_at: str = Field(..., description="ISO timestamp of creation")
    updated_at: str = Field(..., description="ISO timestamp of last update")
    message_count: int = Field(default=0, description="Number of messages in thread")
    is_archived: bool = Field(default=False, description="Archived status")


class ThreadListResponse(BaseModel):
    """Response model for thread listing."""
    threads: List[Thread] = Field(default_factory=list, description="List of conversation threads")
    total_count: int = Field(0, description="Total number of threads")


class CreateThreadRequest(BaseModel):
    """Request model for creating a new thread."""
    user_id: str = Field(default="anonymous", description="User identifier")
    thread_title: Optional[str] = Field(None, description="Optional custom title")


class CreateThreadResponse(BaseModel):
    """Response model for thread creation."""
    thread_id: str = Field(..., description="Newly created thread ID")
    thread_title: str = Field(..., description="Thread title")
    created_at: str = Field(..., description="ISO timestamp")


class UpdateThreadTitleRequest(BaseModel):
    """Request model for updating thread title."""
    thread_title: str = Field(..., min_length=1, max_length=200, description="New thread title")


async def generate_thread_title(first_message: str, first_response: str) -> str:
    """
    Generate conversation title using Claude Haiku 4.5.

    Uses Anthropic's fast, cost-effective Haiku model to create a 5-word
    title capturing the essence of the conversation starter.

    Args:
        first_message: User's first message
        first_response: Agent's first response

    Returns:
        Generated title (max 5 words)
    """
    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        system_prompt = """Generate an extremely short title (maximum 5 words) that captures
the essence of this conversation starter. Be specific and descriptive.
Return ONLY the title, no quotes, no explanation."""

        message = await client.messages.create(
            model="gemini-2.5-flash",  # Haiku 4.5
            max_tokens=20,
            temperature=0.7,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": f"User: {first_message[:200]}\nAssistant: {first_response[:200]}"
            }]
        )

        # Extract text from response
        title = message.content[0].text.strip()
        # Remove quotes if LLM added them
        title = title.strip('"').strip("'")
        return title[:100]  # Safety limit

    except Exception as e:
        logger.warning(f"⚠️ Auto-title generation failed: {e}")
        # Fallback to truncated first message
        return first_message[:50] + ("..." if len(first_message) > 50 else "")


@app.post("/api/threads/create", response_model=CreateThreadResponse)
async def create_thread(request: CreateThreadRequest):
    """
    Create a new conversation thread.

    Generates a unique thread_id and inserts it into user_threads table.
    Frontend should use this thread_id for all subsequent chat messages.

    Args:
        request: CreateThreadRequest with optional user_id and title

    Returns:
        CreateThreadResponse with new thread_id and metadata

    Example:
        POST /api/threads/create
        {"user_id": "user123", "thread_title": "My Research"}
    """
    try:
        # Generate new thread UUID
        thread_id = str(uuid.uuid4())
        thread_title = request.thread_title or "New Conversation"
        created_at = datetime.now().isoformat()

        # Get database URI from environment
        db_uri = os.getenv("POSTGRES_URI", "postgresql://localhost:5432/langgraph_checkpoints")

        # Insert into user_threads table
        async with await psycopg.AsyncConnection.connect(db_uri) as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO user_threads (user_id, thread_id, thread_title, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    RETURNING thread_id, thread_title, created_at
                """, (request.user_id, thread_id, thread_title))

                result = await cur.fetchone()
                await conn.commit()

        logger.info(f"✅ [Threads] Created new thread: {thread_id} for user: {request.user_id}")

        return CreateThreadResponse(
            thread_id=thread_id,
            thread_title=thread_title,
            created_at=created_at
        )

    except Exception as e:
        logger.error(f"❌ [Threads] Failed to create thread: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create thread: {str(e)}"
        )


@app.get("/api/threads/list", response_model=ThreadListResponse)
async def list_threads(
    user_id: str = Query(default="anonymous", description="User identifier"),
    include_archived: bool = Query(default=False, description="Include archived threads")
):
    """
    List all conversation threads for a user.

    Returns threads sorted by most recently updated first.
    Includes message count from checkpoints table.

    Args:
        user_id: User identifier (default: "anonymous")
        include_archived: Include archived threads (default: False)

    Returns:
        ThreadListResponse with list of threads and total count

    Example:
        GET /api/threads/list?user_id=user123&include_archived=false
    """
    try:
        db_uri = os.getenv("POSTGRES_URI", "postgresql://localhost:5432/langgraph_checkpoints")

        # Build query based on include_archived flag
        archive_filter = "" if include_archived else "AND t.is_archived = false"

        query = f"""
            SELECT
                t.thread_id,
                t.thread_title,
                t.user_id,
                t.created_at,
                t.updated_at,
                t.is_archived,
                COUNT(DISTINCT c.checkpoint_id) as message_count
            FROM user_threads t
            LEFT JOIN checkpoints c ON c.thread_id = t.thread_id::text
            WHERE t.user_id = %s {archive_filter}
            GROUP BY t.thread_id, t.thread_title, t.user_id, t.created_at, t.updated_at, t.is_archived
            ORDER BY t.updated_at DESC
        """

        async with await psycopg.AsyncConnection.connect(db_uri) as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (user_id,))
                rows = await cur.fetchall()

        # Convert to Thread models
        threads = []
        for row in rows:
            threads.append(Thread(
                thread_id=row[0],
                thread_title=row[1],
                user_id=row[2],
                created_at=row[3].isoformat() if row[3] else datetime.now().isoformat(),
                updated_at=row[4].isoformat() if row[4] else datetime.now().isoformat(),
                message_count=row[6] or 0,
                is_archived=row[5] or False
            ))

        logger.info(f"📊 [Threads] Retrieved {len(threads)} threads for user: {user_id}")

        return ThreadListResponse(
            threads=threads,
            total_count=len(threads)
        )

    except Exception as e:
        logger.error(f"❌ [Threads] Failed to list threads: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list threads: {str(e)}"
        )


@app.put("/api/threads/{thread_id}/title")
async def update_thread_title(
    thread_id: str,
    request: UpdateThreadTitleRequest
):
    """
    Update the title of an existing thread.

    Args:
        thread_id: Thread identifier (UUID)
        request: UpdateThreadTitleRequest with new title

    Returns:
        Success message with updated title

    Example:
        PUT /api/threads/550e8400-e29b-41d4-a716-446655440000/title
        {"thread_title": "Updated Title"}
    """
    try:
        db_uri = os.getenv("POSTGRES_URI", "postgresql://localhost:5432/langgraph_checkpoints")

        async with await psycopg.AsyncConnection.connect(db_uri) as conn:
            async with conn.cursor() as cur:
                # Update title and updated_at timestamp
                await cur.execute("""
                    UPDATE user_threads
                    SET thread_title = %s, updated_at = NOW()
                    WHERE thread_id = %s
                    RETURNING thread_id
                """, (request.thread_title, thread_id))

                result = await cur.fetchone()
                await conn.commit()

                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Thread not found: {thread_id}"
                    )

        logger.info(f"✅ [Threads] Updated title for thread: {thread_id}")

        return {
            "success": True,
            "thread_id": thread_id,
            "thread_title": request.thread_title
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [Threads] Failed to update thread title: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update thread title: {str(e)}"
        )


@app.delete("/api/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    permanent: bool = Query(default=False, description="Permanently delete (default: archive)")
):
    """
    Delete or archive a conversation thread.

    By default, threads are archived (soft delete). Use permanent=true for hard delete.

    Args:
        thread_id: Thread identifier (UUID)
        permanent: If True, permanently delete. If False, archive (default)

    Returns:
        Success message

    Example:
        DELETE /api/threads/550e8400-e29b-41d4-a716-446655440000?permanent=false
    """
    try:
        db_uri = os.getenv("POSTGRES_URI", "postgresql://localhost:5432/langgraph_checkpoints")

        async with await psycopg.AsyncConnection.connect(db_uri) as conn:
            async with conn.cursor() as cur:
                if permanent:
                    # Permanent delete from database
                    await cur.execute("""
                        DELETE FROM user_threads WHERE thread_id = %s
                        RETURNING thread_id
                    """, (thread_id,))
                else:
                    # Soft delete (archive)
                    await cur.execute("""
                        UPDATE user_threads
                        SET is_archived = true, updated_at = NOW()
                        WHERE thread_id = %s
                        RETURNING thread_id
                    """, (thread_id,))

                result = await cur.fetchone()
                await conn.commit()

                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Thread not found: {thread_id}"
                    )

        action = "deleted" if permanent else "archived"
        logger.info(f"✅ [Threads] {action.capitalize()} thread: {thread_id}")

        return {
            "success": True,
            "thread_id": thread_id,
            "action": action
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [Threads] Failed to delete thread: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete thread: {str(e)}"
        )


@app.get("/health")
async def health():
    """Health check endpoint with WebSocket status."""
    return {
        "status": "healthy",
        "version": "2.5",
        "websocket_enabled": True,
        "file_watcher_enabled": file_watcher is not None,
        "active_connections": sum(len(conns) for conns in manager.active_connections.values()),
        "features": {
            "plan_tracking": True,
            "sqlite_persistence": True,
            "conversation_history": True,
            "thread_management": True
        }
    }


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 80)
    print("DeepAgent Research API v2.4 - Enhanced Backend with WebSocket")
    print("=" * 80)
    print("Features:")
    print("  ✅ Progress logging support")
    print("  ✅ Citation-aware streaming")
    print("  ✅ Enhanced event types")
    print("  ✅ WebSocket real-time collaboration")
    print("  ✅ JWT authentication")
    print("=" * 80)
    print("\nStarting server at http://localhost:8000")
    print("Frontend: http://localhost:3000")
    print("\n" + "=" * 80 + "\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        timeout_keep_alive=120,  # Increased from default 5s to 120s for large file operations
        timeout_graceful_shutdown=30  # Allow time for ongoing requests to complete
    )
