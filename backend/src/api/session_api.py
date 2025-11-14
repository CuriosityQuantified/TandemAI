"""
Session Management API for ATLAS
Provides CRUD operations for chat sessions with agent configurations
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import json
import os
import uuid
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Create sessions directory if it doesn't exist
SESSIONS_DIR = Path("./data/sessions")
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# Pydantic models for request/response
class AgentConfiguration(BaseModel):
    """Configuration for agents in a session."""
    enable_supervisor: bool = True
    enable_research: bool = True
    enable_analysis: bool = True
    enable_writing: bool = True
    preferred_model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    enabled_tools: List[str] = Field(
        default_factory=lambda: [
            "firecrawl_web_search",
            "firecrawl_scrape",
            "e2b_execute_python",
            "plan_task",
            "create_todo",
            "save_output"
        ]
    )


class SessionConfig(BaseModel):
    """Configuration for creating a new session."""
    title: str
    description: Optional[str] = None
    task_type: str = "general"  # general, research, analysis, writing
    agents: AgentConfiguration = Field(default_factory=AgentConfiguration)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Session(BaseModel):
    """Complete session object."""
    id: str
    title: str
    description: Optional[str] = None
    task_type: str
    agents: AgentConfiguration
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_message: Optional[str] = None
    message_count: int = 0
    status: str = "active"  # active, archived, deleted
    output_dir: str


class SessionUpdate(BaseModel):
    """Update session fields."""
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    last_message: Optional[str] = None


class Message(BaseModel):
    """Chat message in a session."""
    id: str
    session_id: str
    role: str  # user, assistant, system, tool
    content: str
    agent_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


# In-memory session storage (replace with database in production)
_sessions: Dict[str, Session] = {}
_messages: Dict[str, List[Message]] = {}


def _save_session(session: Session):
    """Save session to disk and memory."""
    _sessions[session.id] = session

    # Save to disk
    session_file = SESSIONS_DIR / f"{session.id}.json"
    with open(session_file, 'w') as f:
        json.dump(session.model_dump(mode='json'), f, indent=2, default=str)


def _load_session(session_id: str) -> Optional[Session]:
    """Load session from disk or memory."""
    if session_id in _sessions:
        return _sessions[session_id]

    session_file = SESSIONS_DIR / f"{session_id}.json"
    if session_file.exists():
        with open(session_file, 'r') as f:
            data = json.load(f)
            # Convert string dates back to datetime
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            session = Session(**data)
            _sessions[session_id] = session
            return session

    return None


def _load_all_sessions() -> List[Session]:
    """Load all sessions from disk."""
    sessions = []

    for session_file in SESSIONS_DIR.glob("*.json"):
        try:
            with open(session_file, 'r') as f:
                data = json.load(f)
                data['created_at'] = datetime.fromisoformat(data['created_at'])
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                session = Session(**data)
                sessions.append(session)
                _sessions[session.id] = session
        except Exception as e:
            logger.error(f"Failed to load session {session_file}: {e}")

    return sessions


def _save_messages(session_id: str, messages: List[Message]):
    """Save messages to disk."""
    messages_file = SESSIONS_DIR / f"{session_id}_messages.json"
    with open(messages_file, 'w') as f:
        json.dump(
            [msg.model_dump(mode='json') for msg in messages],
            f,
            indent=2,
            default=str
        )


def _load_messages(session_id: str) -> List[Message]:
    """Load messages from disk or memory."""
    if session_id in _messages:
        return _messages[session_id]

    messages_file = SESSIONS_DIR / f"{session_id}_messages.json"
    if messages_file.exists():
        with open(messages_file, 'r') as f:
            data = json.load(f)
            messages = []
            for msg_data in data:
                msg_data['timestamp'] = datetime.fromisoformat(msg_data['timestamp'])
                messages.append(Message(**msg_data))
            _messages[session_id] = messages
            return messages

    return []


# API Endpoints

@router.post("/", response_model=Session)
async def create_session(config: SessionConfig) -> Session:
    """Create a new chat session."""
    session_id = str(uuid.uuid4())

    # Create output directory for this session
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"./outputs/session_{timestamp}_{session_id[:8]}"
    os.makedirs(output_dir, exist_ok=True)

    session = Session(
        id=session_id,
        title=config.title,
        description=config.description,
        task_type=config.task_type,
        agents=config.agents,
        tags=config.tags,
        metadata=config.metadata,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        output_dir=output_dir
    )

    _save_session(session)
    _messages[session_id] = []

    logger.info(f"Created session {session_id}: {config.title}")

    return session


@router.get("/{session_id}", response_model=Session)
async def get_session(session_id: str) -> Session:
    """Get a specific session by ID."""
    session = _load_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return session


@router.get("/", response_model=List[Session])
async def list_sessions(
    status: Optional[str] = Query(None, description="Filter by status"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> List[Session]:
    """List all sessions with optional filters."""
    sessions = _load_all_sessions()

    # Apply filters
    if status:
        sessions = [s for s in sessions if s.status == status]

    if tag:
        sessions = [s for s in sessions if tag in s.tags]

    if task_type:
        sessions = [s for s in sessions if s.task_type == task_type]

    # Sort by updated_at (most recent first)
    sessions.sort(key=lambda s: s.updated_at, reverse=True)

    # Apply pagination
    return sessions[offset:offset + limit]


@router.patch("/{session_id}", response_model=Session)
async def update_session(session_id: str, update: SessionUpdate) -> Session:
    """Update session properties."""
    session = _load_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Apply updates
    if update.title is not None:
        session.title = update.title

    if update.description is not None:
        session.description = update.description

    if update.tags is not None:
        session.tags = update.tags

    if update.metadata is not None:
        session.metadata.update(update.metadata)

    if update.status is not None:
        session.status = update.status

    if update.last_message is not None:
        session.last_message = update.last_message

    session.updated_at = datetime.now()

    _save_session(session)

    logger.info(f"Updated session {session_id}")

    return session


@router.delete("/{session_id}")
async def delete_session(session_id: str, permanent: bool = False):
    """Delete or archive a session."""
    session = _load_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    if permanent:
        # Permanent deletion
        if session_id in _sessions:
            del _sessions[session_id]

        if session_id in _messages:
            del _messages[session_id]

        # Delete files
        session_file = SESSIONS_DIR / f"{session_id}.json"
        messages_file = SESSIONS_DIR / f"{session_id}_messages.json"

        if session_file.exists():
            session_file.unlink()

        if messages_file.exists():
            messages_file.unlink()

        logger.info(f"Permanently deleted session {session_id}")

        return {"message": f"Session {session_id} permanently deleted"}

    else:
        # Soft delete (archive)
        session.status = "deleted"
        session.updated_at = datetime.now()
        _save_session(session)

        logger.info(f"Archived session {session_id}")

        return {"message": f"Session {session_id} archived"}


@router.post("/{session_id}/messages", response_model=Message)
async def add_message(session_id: str,
                      role: str,
                      content: str,
                      agent_id: Optional[str] = None,
                      tool_calls: Optional[List[Dict[str, Any]]] = None) -> Message:
    """Add a message to a session."""
    session = _load_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    message = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role=role,
        content=content,
        agent_id=agent_id,
        tool_calls=tool_calls,
        timestamp=datetime.now()
    )

    # Load existing messages
    messages = _load_messages(session_id)
    messages.append(message)

    # Update session
    session.last_message = content[:100] if len(content) > 100 else content
    session.message_count = len(messages)
    session.updated_at = datetime.now()

    # Save everything
    _messages[session_id] = messages
    _save_messages(session_id, messages)
    _save_session(session)

    return message


@router.get("/{session_id}/messages", response_model=List[Message])
async def get_messages(session_id: str,
                      limit: int = Query(100, ge=1, le=500),
                      offset: int = Query(0, ge=0)) -> List[Message]:
    """Get messages for a session."""
    session = _load_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    messages = _load_messages(session_id)

    # Apply pagination
    return messages[offset:offset + limit]


@router.post("/{session_id}/export")
async def export_session(session_id: str, format: str = "json"):
    """Export a session and its messages."""
    session = _load_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    messages = _load_messages(session_id)

    export_data = {
        "session": session.model_dump(mode='json'),
        "messages": [msg.model_dump(mode='json') for msg in messages]
    }

    if format == "json":
        return export_data

    elif format == "markdown":
        # Create markdown export
        md_content = f"# {session.title}\n\n"
        md_content += f"**Created:** {session.created_at}\n"
        md_content += f"**Type:** {session.task_type}\n\n"

        if session.description:
            md_content += f"## Description\n{session.description}\n\n"

        md_content += "## Conversation\n\n"

        for msg in messages:
            role_label = msg.role.upper()
            if msg.agent_id:
                role_label += f" ({msg.agent_id})"

            md_content += f"### {role_label}\n"
            md_content += f"{msg.content}\n\n"

        return {"format": "markdown", "content": md_content}

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


@router.post("/templates")
async def get_session_templates():
    """Get predefined session templates."""
    templates = [
        {
            "name": "Research Task",
            "config": {
                "title": "Research: [Topic]",
                "task_type": "research",
                "agents": {
                    "enable_supervisor": True,
                    "enable_research": True,
                    "enable_analysis": False,
                    "enable_writing": False,
                    "enabled_tools": [
                        "firecrawl_web_search",
                        "firecrawl_scrape",
                        "save_output"
                    ]
                }
            }
        },
        {
            "name": "Data Analysis",
            "config": {
                "title": "Analysis: [Dataset]",
                "task_type": "analysis",
                "agents": {
                    "enable_supervisor": True,
                    "enable_research": False,
                    "enable_analysis": True,
                    "enable_writing": False,
                    "enabled_tools": [
                        "e2b_execute_python",
                        "save_output",
                        "create_todo"
                    ]
                }
            }
        },
        {
            "name": "Report Writing",
            "config": {
                "title": "Report: [Subject]",
                "task_type": "writing",
                "agents": {
                    "enable_supervisor": True,
                    "enable_research": True,
                    "enable_analysis": True,
                    "enable_writing": True,
                    "enabled_tools": [
                        "firecrawl_web_search",
                        "e2b_execute_python",
                        "save_output",
                        "plan_task",
                        "create_todo"
                    ]
                }
            }
        },
        {
            "name": "Full Analysis",
            "config": {
                "title": "Complete Analysis: [Topic]",
                "task_type": "general",
                "agents": {
                    "enable_supervisor": True,
                    "enable_research": True,
                    "enable_analysis": True,
                    "enable_writing": True,
                    "enabled_tools": "all"
                }
            }
        }
    ]

    return templates


# Export router for use in main app
__all__ = ['router']