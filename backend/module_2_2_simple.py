"""
MODULE 2.2: Deep Agents with Production Tools (Simplified)
===========================================================

Demonstrates:
1. Single DeepAgent with real production tools
2. Tavily web search integration
3. Firecrawl web scraping
4. GitHub repository operations
5. e2b code execution sandbox
6. Hybrid storage backend (v0.2 feature)
7. TodoListMiddleware for automatic planning

This version uses real tools instead of simulated ones.

Based on: langchain-langgraph-hands-on-guide.md Module 2.2
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
from typing_extensions import TypedDict
import asyncio
import time
import threading
import functools
import uuid

# DeepAgents imports
from deepagents import create_deep_agent
from deepagents.backends import (
    CompositeBackend,
    StateBackend,
    FilesystemBackend
)

# LangChain imports
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # PostgreSQL checkpointer for persistence
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

# Production tool imports
from langchain_tavily import TavilySearch

# Delegation tools import (updated for reorganization - uses backend. prefix)
from backend.delegation_tools import (
    delegate_to_researcher,
    delegate_to_data_scientist,
    delegate_to_expert_analyst,
    delegate_to_writer,
    delegate_to_reviewer,
)

# WebSocket manager import (updated for reorganization - uses backend. prefix)
try:
    from backend.websocket_manager import manager
except ImportError:
    # Graceful fallback if websocket_manager not yet created
    manager = None
    print("⚠️  Warning: websocket_manager.py not found - WebSocket broadcasting disabled")

load_dotenv()

# ============================================================================
# DATABASE CONFIGURATION FOR POSTGRESQL CHECKPOINTING
# ============================================================================

# PostgreSQL connection string from environment
DB_URI = os.getenv("POSTGRES_URI", "postgresql://localhost:5432/langgraph_checkpoints")

# Global checkpointer instance (initialized in FastAPI lifespan)
checkpointer = None

# Global agent instance (initialized in FastAPI lifespan with checkpointer)
agent = None

@asynccontextmanager
async def setup_checkpointer():
    """
    Initialize PostgreSQL checkpointer with proper connection management.

    This context manager:
    1. Creates database connection
    2. Sets up required tables for checkpointing
    3. Yields the checkpointer for agent creation
    4. Ensures proper cleanup on shutdown

    Raises:
        Exception: If PostgreSQL connection fails, preventing silent failures

    Usage in FastAPI lifespan:
        async with setup_checkpointer() as saver:
            global agent
            agent = create_deep_agent(..., checkpointer=saver)
    """
    global checkpointer

    try:
        async with AsyncPostgresSaver.from_conn_string(DB_URI) as saver:
            # Create database tables if they don't exist
            print(f"📊 Connecting to PostgreSQL: {DB_URI}")
            await saver.setup()
            checkpointer = saver
            print(f"✅ PostgreSQL checkpointer initialized successfully")
            print(f"   Database: {DB_URI}")
            print(f"   Tables created/verified")
            yield saver

        print("🛑 PostgreSQL checkpointer connection closed")

    except Exception as e:
        error_msg = f"❌ CRITICAL: PostgreSQL checkpointer initialization failed!"
        print(error_msg)
        print(f"   Error: {str(e)}")
        print(f"   Connection string: {DB_URI}")
        print(f"   Possible causes:")
        print(f"   - Database 'langgraph_checkpoints' does not exist")
        print(f"   - PostgreSQL service not running")
        print(f"   - Connection string incorrect")
        print(f"   - Insufficient permissions")
        print(f"\n⚠️  PERSISTENCE WILL NOT WORK WITHOUT DATABASE CONNECTION\n")
        # Re-raise to prevent app startup with broken persistence
        raise

# ============================================================================
# STATE SCHEMA
# ============================================================================

class AgentState(TypedDict, total=False):
    """State schema with custom progress logging."""
    messages: list
    logs: list  # [{"message": "🌐 Searching...", "done": False}]

# ============================================================================
# CONFIGURATION
# ============================================================================

# Use Anthropic Claude Haiku 4.5 directly
# With simplified tool set (Tavily only), Haiku should work
model = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.7,
)

print("\n" + "=" * 80)
print("MODULE 2.2: Single DeepAgent with Tavily + Built-in Tools")
print("=" * 80)
print(f"🤖 Model: Claude Haiku 4.5")
print(f"🔧 Tool: Tavily (web search)")
print(f"📁 Built-in: 6 filesystem tools (ls, read_file, write_file, edit_file, glob, grep)")
print(f"🔮 Future: Firecrawl, GitHub, e2b will be added as subagents")
print("=" * 80)

# ============================================================================
# PRODUCTION TOOLS
# ============================================================================

# Tavily Web Search (native LangChain tool)
tavily_search = TavilySearch(
    max_results=5,
    api_key=os.getenv("TAVILY_API_KEY"),
)

# ============================================================================
# ENHANCED TOOL SCHEMAS
# ============================================================================

class ResearchSearchArgs(BaseModel):
    """Arguments for research-focused web search."""
    query: str = Field(
        description="Specific research question or topic to search. Be precise and include key terms."
    )
    max_results: int = Field(
        default=5,
        ge=3,
        le=10,
        description="Number of sources to return (3-10). Use 5 for balanced research, 10 for comprehensive."
    )

class EnhancedTavilyTool:
    """Wrapper around Tavily with enhanced metadata for citations."""

    def __init__(self, tavily_tool):
        self.tavily = tavily_tool
        self.name = "research_search"
        self.description = (
            "Search the web for credible, up-to-date sources on any topic. "
            "Returns URLs, titles, and content snippets for citation. "
            "Use for: factual research, current events, technical documentation, statistics. "
            "Best practices: "
            "- Use specific queries (good: 'LangChain v1.0 middleware features', bad: 'LangChain') "
            "- Search multiple times for complex topics "
            "- Note the source URLs for citations"
        )
        self.args_schema = ResearchSearchArgs

    def invoke(self, query: str, max_results: int = 5):
        """Execute search and format results for citations."""
        results = self.tavily.invoke({"query": query})
        # Format results to emphasize URL and title for citations
        return results

# Wrap the existing tavily_search (Note: Using original for compatibility)
# Future: Replace with EnhancedTavilyTool for better citation support
enhanced_tavily = EnhancedTavilyTool(tavily_search)

# ============================================================================
# CUSTOM read_file TOOL WITH WORKSPACE SCOPING
# ============================================================================

class ReadFileInput(BaseModel):
    """Schema for read_file tool."""
    file_path: str = Field(
        ...,  # Required
        description="Absolute path to the file to read. MUST start with /workspace/"
    )


@tool("read_file", args_schema=ReadFileInput)
def read_file_tool(file_path: str) -> str:
    """
    Read content from a file in the workspace.

    This tool reads files from the /workspace/ directory.
    All paths must be absolute and start with /workspace/

    Args:
        file_path: Absolute path to file (must start with /workspace/)

    Returns:
        File content as string

    Examples:
        read_file(file_path="/workspace/report.md")
        read_file(file_path="/workspace/reviews/analysis.txt")
    """
    from pathlib import Path

    # Validate path starts with /workspace/
    if not file_path.startswith("/workspace/"):
        return f"Error: file_path must start with /workspace/ (got: {file_path})"

    # Get the actual filesystem path
    workspace_dir = get_workspace_dir()
    relative_path = file_path.replace("/workspace/", "")
    full_path = Path(workspace_dir) / relative_path

    # Check if file exists
    if not full_path.exists():
        return f"Error: File '{file_path}' not found"

    if not full_path.is_file():
        return f"Error: '{file_path}' is not a file"

    # Read and return content
    try:
        content = full_path.read_text(encoding="utf-8")
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"


# ============================================================================
# CUSTOM write_file TOOL WITH EXPLICIT SCHEMA
# ============================================================================

class WriteFileInput(BaseModel):
    """Explicit schema for write_file tool to enforce both parameters."""
    file_path: str = Field(
        ...,  # Required
        description="Absolute path to the file. MUST start with /workspace/ to save in workspace."
    )
    content: str = Field(
        ...,  # Required
        description=(
            "COMPLETE file content as a string. REQUIRED and cannot be empty. "
            "⚠️ CRITICAL: Include ENTIRE content regardless of size (even 10,000+ sentences). "
            "Do NOT summarize or truncate. This tool handles millions of characters efficiently."
        )
    )


class EditFileInput(BaseModel):
    """Input schema for edit_file tool with validation."""
    file_path: str = Field(
        ...,
        description="Path to file to edit (must start with /workspace/)"
    )
    old_string: str = Field(
        ...,
        description="Exact string to find and replace in the file"
    )
    new_string: str = Field(
        ...,
        description="New string to replace old_string with"
    )


# ============================================================================
# Research Planning Tool Schemas
# ============================================================================

class CreatePlanInput(BaseModel):
    """Input schema for create_research_plan tool."""
    query: str = Field(
        ...,
        description="Research query or question to create a plan for"
    )
    num_steps: int = Field(
        default=5,
        ge=3,
        le=10,
        description="Number of research steps to generate (3-10, default 5)"
    )


class UpdatePlanInput(BaseModel):
    """Input schema for update_plan_progress tool."""
    step_index: int = Field(
        ...,
        ge=0,
        description="Index of the completed step (0-based, e.g., 0 for first step)"
    )
    result: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Brief summary of step result (1-2 sentences, max 500 chars)"
    )


class EditPlanInput(BaseModel):
    """Input schema for edit_plan tool."""
    action: str = Field(
        ...,
        description="Action to perform: 'mark_completed', 'add_step', 'remove_step', or 'update_step'"
    )
    step_index: Optional[int] = Field(
        None,
        ge=0,
        description="Index of step to modify (required for mark_completed, remove_step, update_step)"
    )
    step_text: Optional[str] = Field(
        None,
        min_length=1,
        max_length=500,
        description="New step text (required for add_step and update_step)"
    )
    result: Optional[str] = Field(
        None,
        min_length=1,
        max_length=500,
        description="Result/completion summary (required for mark_completed)"
    )
    insert_position: Optional[int] = Field(
        None,
        ge=0,
        description="Position to insert new step (for add_step, defaults to end)"
    )


# ============================================================================
# WebSocket Broadcasting Helper
# ============================================================================

def _run_broadcast_in_thread(coro):
    """
    Run async broadcast in separate thread with own event loop.

    This helper allows synchronous tools like write_file to trigger async
    WebSocket broadcasts without blocking or requiring an async context.

    Args:
        coro: Async coroutine to run (e.g., manager.broadcast_file_change(...))
    """
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()


def _write_file_impl(file_path: str, content: str) -> str:
    """
    Internal implementation of write_file without approval check.
    This is the actual file writing logic.
    """
    # Import here to avoid circular dependency
    from pathlib import Path

    # Validate path starts with /workspace/
    if not file_path.startswith("/workspace/"):
        return f"Error: file_path must start with /workspace/ (got: {file_path})"

    # Get the actual filesystem path (uses custom workspace if set, otherwise default)
    workspace_dir = get_workspace_dir()
    relative_path = file_path.replace("/workspace/", "")
    full_path = Path(workspace_dir) / relative_path

    # Create parent directories if needed
    full_path.parent.mkdir(parents=True, exist_ok=True)

    # Read old content before writing (if file exists)
    old_content = ""
    if full_path.exists():
        try:
            old_content = full_path.read_text(encoding='utf-8')
        except Exception as e:
            # If we can't read old content, proceed with empty string
            print(f"⚠️  Warning: Could not read old content from {file_path}: {e}")

    # Write the file
    full_path.write_text(content, encoding='utf-8')

    # Broadcast file change via WebSocket (if manager is available)
    if manager is not None:
        try:
            # Run broadcast in background thread (non-blocking)
            _run_broadcast_in_thread(
                manager.broadcast_file_change(
                    file_path=relative_path,
                    old_content=old_content,
                    new_content=content,
                    editor_user_id="ai_agent",
                    change_metadata={
                        "timestamp": time.time(),
                        "change_type": "ai_edit",
                        "file_size": len(content),
                        "editor": "ai_agent"
                    }
                )
            )
            print(f"📡 [WebSocket] Broadcast initiated for {file_path} ({len(content)} characters)")
        except Exception as e:
            # Don't fail the file write if broadcasting fails
            print(f"⚠️  Warning: WebSocket broadcast failed for {file_path}: {e}")

    return f"✅ File written successfully: {file_path} ({len(content)} characters)"


def _edit_file_impl(file_path: str, old_string: str, new_string: str) -> str:
    """Internal implementation of edit_file without approval check."""
    from pathlib import Path

    # Validate path starts with /workspace/
    if not file_path.startswith("/workspace/"):
        return f"❌ Error: file_path must start with /workspace/ (got: {file_path})"

    # Get the actual filesystem path (uses custom workspace if set, otherwise default)
    workspace_dir = get_workspace_dir()
    relative_path = file_path.replace("/workspace/", "")
    full_path = Path(workspace_dir) / relative_path

    # Validation - file must exist
    if not full_path.exists():
        return f"❌ Error: File not found: {file_path}"

    # Security check - must be within workspace
    try:
        full_path.resolve().relative_to(workspace_dir.resolve())
    except ValueError:
        return f"❌ Error: Access denied - file must be in /workspace/"

    # Read, replace, write
    try:
        old_content = full_path.read_text(encoding='utf-8')
    except Exception as e:
        return f"❌ Error reading file: {str(e)}"

    if old_string not in old_content:
        return f"❌ Error: old_string not found in {file_path}"

    occurrence_count = old_content.count(old_string)
    new_content = old_content.replace(old_string, new_string, 1)  # Replace first occurrence only

    try:
        full_path.write_text(new_content, encoding='utf-8')
    except Exception as e:
        return f"❌ Error writing file: {str(e)}"

    # WebSocket broadcasting
    if manager is not None:
        try:
            _run_broadcast_in_thread(
                manager.broadcast_file_change(
                    file_path=relative_path,
                    old_content=old_content,
                    new_content=new_content,
                    editor_user_id="ai_agent",
                    change_metadata={
                        "timestamp": time.time(),
                        "change_type": "ai_edit",
                        "file_size": len(new_content),
                        "editor": "ai_agent",
                        "edit_type": "replace"
                    }
                )
            )
        except Exception as e:
            print(f"⚠️  Warning: WebSocket broadcast failed: {e}")

    warning = f" (Note: {occurrence_count} occurrence(s) found, replaced first only)" if occurrence_count > 1 else ""
    return f"✅ File edited successfully: {file_path} ({len(new_content)} characters){warning}"


@tool("write_file", args_schema=WriteFileInput)
def write_file_tool(file_path: str, content: str) -> str:
    """
    Write content to a file in the workspace.

    This tool saves files to the /workspace/ directory which appears in the UI file browser.
    BOTH parameters are absolutely required - file_path AND content.

    ⚠️  CRITICAL: LARGE CONTENT HANDLING ⚠️

    This tool efficiently handles content of ANY size - even 10,000+ sentences or millions of characters.
    NEVER summarize, truncate, or abbreviate the content parameter. Include ALL content in a SINGLE call.

    Model Output Limitations & Strategies:
    - Claude Haiku 4.5 has ~4K output token limit (~16K characters)
    - If content exceeds model's output limit, use ITERATIVE FALLBACK approach:

      Strategy A - Single Write (Preferred):
      1. Pass ALL content in one write_file call
      2. Example: write_file(file_path="/workspace/large.txt", content="<all 10,000 sentences here>")

      Strategy B - Iterative Approach (Fallback for >4K output tokens):
      1. Create file with initial content (first ~3K output tokens)
      2. Use edit_file to append remaining content in batches
      3. Example:
         - write_file(file_path="/workspace/large.txt", content="<sentences 1-1000>")
         - edit_file(file_path="/workspace/large.txt", old_string="<last line>",
                     new_string="<last line>\n<sentences 1001-2000>")
         - edit_file(file_path="/workspace/large.txt", old_string="<last line>",
                     new_string="<last line>\n<sentences 2001-3000>")
         - Continue until all content is written

    IMPORTANT: "Brief" applies to USER-FACING MESSAGES, NOT file content:
    - ✅ User message: "File created with 10,000 sentences" (brief)
    - ✅ File content: Include ALL 10,000 sentences (complete)
    - ❌ WRONG: Summarizing file content to be "brief" - NEVER DO THIS

    Args:
        file_path: Path where to save the file (must start with /workspace/)
        content: The COMPLETE file content as text - ALL sentences, NO truncation

    Returns:
        Success message with file path and character count

    Examples:
        # Small file (normal case)
        write_file(
            file_path="/workspace/report.md",
            content="# Report\\n\\nThis is the content..."
        )

        # Large file within model limits (10,000 sentences, ~40K chars)
        write_file(
            file_path="/workspace/large_story.txt",
            content="Sentence 1. Sentence 2. ... Sentence 10000."
        )

        # Very large file exceeding model output limits - use iterative approach
        # Step 1: Create with initial content
        write_file(
            file_path="/workspace/massive.txt",
            content="<First 1000 sentences that fit in 4K tokens>"
        )
        # Step 2: Append remaining content via edit_file
        edit_file(
            file_path="/workspace/massive.txt",
            old_string="<last sentence from step 1>",
            new_string="<last sentence from step 1>\\n<Next 1000 sentences>"
        )
    """
    # Check if approval is required
    if not get_auto_approve():
        # Generate request ID
        request_id = str(uuid.uuid4())

        # Create approval request synchronously
        try:
            # We need to run async code from sync context
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                approval_result = loop.run_until_complete(
                    get_approval_for_tool(
                        tool_name="write_file",
                        tool_args={"file_path": file_path, "content": content[:100] + "..."},
                        request_id=request_id
                    )
                )
                loop.close()
            else:
                # Running in async context, schedule coroutine in the event loop
                future = asyncio.run_coroutine_threadsafe(
                    get_approval_for_tool(
                        tool_name="write_file",
                        tool_args={"file_path": file_path, "content": content[:100] + "..."},
                        request_id=request_id
                    ),
                    loop
                )
                approval_result = future.result()  # This blocks until complete

            # Check approval
            if not approval_result.get("approved", False):
                feedback = approval_result.get("feedback", "Operation rejected by user")
                return f"❌ Operation rejected: {feedback}"

        except Exception as e:
            print(f"⚠️ [Approval] Error during approval check: {e}")
            return f"❌ Approval system error: {str(e)}"

    # Execute the actual file write
    return _write_file_impl(file_path, content)


@tool("edit_file", args_schema=EditFileInput)
def edit_file_with_approval(file_path: str, old_string: str, new_string: str) -> str:
    """
    Edit a file by replacing old_string with new_string.
    Requires user approval when auto_approve is disabled.
    Replaces the built-in edit_file tool from FilesystemBackend.
    """
    # Check if approval is required
    if not get_auto_approve():
        request_id = str(uuid.uuid4())

        # Truncate strings for display
        old_display = old_string[:100] + "..." if len(old_string) > 100 else old_string
        new_display = new_string[:100] + "..." if len(new_string) > 100 else new_string

        try:
            # Run async code from sync context (EXACT pattern from write_file_tool)
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                approval_result = loop.run_until_complete(
                    get_approval_for_tool(
                        tool_name="edit_file",
                        tool_args={
                            "file_path": file_path,
                            "old_string": old_display,
                            "new_string": new_display
                        },
                        request_id=request_id
                    )
                )
                loop.close()
            else:
                future = asyncio.run_coroutine_threadsafe(
                    get_approval_for_tool(
                        tool_name="edit_file",
                        tool_args={
                            "file_path": file_path,
                            "old_string": old_display,
                            "new_string": new_display
                        },
                        request_id=request_id
                    ),
                    loop
                )
                approval_result = future.result()  # Blocks until approval

            if not approval_result.get("approved", False):
                feedback = approval_result.get("feedback", "Operation rejected by user")
                return f"❌ Operation rejected: {feedback}"

        except Exception as e:
            return f"❌ Approval system error: {str(e)}"

    # Execute the actual file edit
    return _edit_file_impl(file_path, old_string, new_string)


# ============================================================================
# RESEARCH PLANNING TOOLS
# ============================================================================

@tool("create_research_plan", args_schema=CreatePlanInput)
def create_research_plan_tool(query: str, num_steps: int = 5) -> str:
    """
    Create a structured research plan for a query.

    This tool generates a step-by-step research plan with 3-10 actionable steps.
    The plan is stored in /workspace/.plans/ and can be referenced by other tools.

    Use this at the START of complex multi-step research tasks to organize your approach.

    Args:
        query: Research question or topic to plan for
        num_steps: Number of steps to generate (3-10, default 5)

    Returns:
        JSON string containing the plan structure with plan_id, steps, and metadata

    Example workflow:
        1. create_research_plan(query="AI trends in healthcare", num_steps=5)
        2. Execute each step using tavily_search, write_file, etc.
        3. update_plan_progress(step_index=0, result="Found 15 sources...")
        4. Continue with next steps
        5. Write final report

    The plan is automatically tracked in the UI with progress indicators.
    """
    import json
    import time
    import logging
    from planning_agent import create_plan_logic

    logger = logging.getLogger(__name__)

    try:
        # Generate plan using extracted logic from planning_agent.py
        plan_response = create_plan_logic(query, num_steps)

        # Generate unique plan ID
        plan_id = str(uuid.uuid4())
        created_at = time.time()

        # Create plan structure
        plan_dict = {
            "plan_id": plan_id,
            "query": query,
            "steps": plan_response.steps,
            "current_step": 0,
            "progress": 0.0,
            "past_steps": [],
            "created_at": created_at,
            "status": "active"
        }

        # Store plan in filesystem (/workspace/.plans/)
        plan_dir = workspace_dir / ".plans"
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Save plan with unique ID
        plan_file = plan_dir / f"{plan_id}.json"
        plan_file.write_text(json.dumps(plan_dict, indent=2), encoding='utf-8')

        # Also save as "current" for easy access
        current_plan_file = plan_dir / "current_plan.json"
        current_plan_file.write_text(json.dumps(plan_dict, indent=2), encoding='utf-8')

        logger.info(f"✅ Created research plan: {plan_id} ({len(plan_response.steps)} steps)")

        # Broadcast plan creation via WebSocket
        if manager is not None:
            try:
                _run_broadcast_in_thread(
                    manager.broadcast({
                        "type": "agent_event",
                        "event_type": "plan_created",
                        "thread_id": "unknown",  # Will be filled by middleware
                        "data": {
                            "type": "plan_created",
                            "plan_id": plan_id,
                            "steps": plan_response.steps,
                            "progress": 0.0,
                        },
                        "timestamp": created_at
                    })
                )
                logger.info(f"📡 Broadcast plan_created event for {plan_id}")
            except Exception as e:
                logger.warning(f"⚠️ WebSocket broadcast failed: {e}")

        # Return plan as JSON
        return json.dumps({
            "status": "success",
            "plan_id": plan_id,
            "steps": plan_response.steps,
            "num_steps": len(plan_response.steps),
            "message": f"Created {len(plan_response.steps)}-step research plan. Track progress with update_plan_progress()."
        }, indent=2)

    except Exception as e:
        error_msg = f"❌ Failed to create research plan: {str(e)}"
        logger.error(error_msg, exc_info=True)

        # Broadcast error
        if manager is not None:
            try:
                _run_broadcast_in_thread(
                    manager.broadcast({
                        "type": "agent_event",
                        "event_type": "plan_error",
                        "data": {
                            "type": "plan_error",
                            "error": str(e)
                        },
                        "timestamp": time.time()
                    })
                )
            except:
                pass

        return json.dumps({"status": "error", "message": error_msg})


@tool("update_plan_progress", args_schema=UpdatePlanInput)
def update_plan_progress_tool(step_index: int, result: str) -> str:
    """
    Mark a research plan step as completed and update progress.

    Call this AFTER completing each step in an active research plan.
    Updates the plan file and broadcasts progress to the UI.

    Args:
        step_index: Index of the completed step (0-based, e.g., 0 for first step)
        result: Brief summary of what was accomplished (1-2 sentences)

    Returns:
        Success message with updated progress and next step

    Example:
        After completing step 0 (searching for sources):
        update_plan_progress(
            step_index=0,
            result="Found 15 relevant sources on AI healthcare trends from 2024-2025"
        )

        Returns: "✅ Step 1/5 completed (20%). Next: Analyze key themes..."
    """
    import json
    import time
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Load current plan from filesystem
        plan_file = workspace_dir / ".plans" / "current_plan.json"

        if not plan_file.exists():
            return json.dumps({
                "status": "error",
                "message": "❌ No active plan found. Create one with create_research_plan() first."
            })

        # Read plan
        plan_data = json.loads(plan_file.read_text(encoding='utf-8'))

        # Validate step_index
        num_steps = len(plan_data["steps"])
        if step_index < 0 or step_index >= num_steps:
            return json.dumps({
                "status": "error",
                "message": f"❌ Invalid step_index {step_index}. Plan has {num_steps} steps (0-{num_steps-1})."
            })

        # Update plan
        step_text = plan_data["steps"][step_index]
        plan_data["past_steps"].append([step_text, result])
        plan_data["current_step"] = step_index + 1
        plan_data["progress"] = plan_data["current_step"] / num_steps
        plan_data["last_updated"] = time.time()

        # Save updated plan
        plan_file.write_text(json.dumps(plan_data, indent=2), encoding='utf-8')

        # Also update plan_id-specific file
        plan_id_file = workspace_dir / ".plans" / f"{plan_data['plan_id']}.json"
        if plan_id_file.exists():
            plan_id_file.write_text(json.dumps(plan_data, indent=2), encoding='utf-8')

        logger.info(
            f"✅ Updated plan {plan_data['plan_id']}: "
            f"Step {step_index + 1}/{num_steps} completed ({plan_data['progress']:.0%})"
        )

        # Broadcast update via WebSocket
        if manager is not None:
            try:
                _run_broadcast_in_thread(
                    manager.broadcast({
                        "type": "agent_event",
                        "event_type": "step_completed",
                        "thread_id": "unknown",
                        "data": {
                            "type": "step_completed",
                            "plan_id": plan_data["plan_id"],
                            "step_index": step_index,
                            "step_text": step_text,
                            "result": result[:200],  # Truncate for WebSocket
                            "progress": plan_data["progress"]
                        },
                        "timestamp": time.time()
                    })
                )
                logger.info(f"📡 Broadcast step_completed event")
            except Exception as e:
                logger.warning(f"⚠️ WebSocket broadcast failed: {e}")

        # Check if plan is complete
        if plan_data["current_step"] >= num_steps:
            plan_data["status"] = "completed"
            plan_file.write_text(json.dumps(plan_data, indent=2), encoding='utf-8')

            # Broadcast completion
            if manager is not None:
                try:
                    _run_broadcast_in_thread(
                        manager.broadcast({
                            "type": "agent_event",
                            "event_type": "plan_complete",
                            "thread_id": "unknown",
                            "data": {
                                "type": "plan_complete",
                                "plan_id": plan_data["plan_id"],
                                "progress": 1.0
                            },
                            "timestamp": time.time()
                        })
                    )
                except:
                    pass

            return json.dumps({
                "status": "complete",
                "message": f"✅ ALL STEPS COMPLETE ({num_steps}/{num_steps})",
                "progress": 1.0,
                "completed_steps": num_steps
            })

        # Return progress message
        next_step_index = plan_data["current_step"]
        next_step = plan_data["steps"][next_step_index]

        return json.dumps({
            "status": "success",
            "message": f"✓ Step {step_index} complete. Progress: {plan_data['current_step']}/{num_steps} steps.",
            "next_step": next_step,
            "progress": plan_data["progress"],
            "completed_steps": plan_data["current_step"]
        })

    except Exception as e:
        error_msg = f"❌ Failed to update plan progress: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({"status": "error", "message": error_msg})


@tool("read_current_plan")
def read_current_plan_tool() -> str:
    """
    Read the current active research plan.

    Returns the plan with progress, completed steps, and next step to execute.
    Use this to check plan status or decide what to do next.

    Returns:
        JSON string with plan details including:
        - plan_id: Unique plan identifier
        - steps: List of all plan steps
        - current_step: Index of next step to execute
        - progress: Completion percentage (0.0-1.0)
        - past_steps: Array of [step, result] tuples for completed steps
        - next_step: Text of the next step to execute (or null if complete)
        - status: "active", "completed", or "no_plan"

    Example:
        read_current_plan()

        Returns:
        {
            "status": "active",
            "plan_id": "550e8400-...",
            "steps": ["Search for sources", "Analyze themes", "Write report"],
            "current_step": 1,
            "progress": 0.33,
            "past_steps": [["Search for sources", "Found 15 sources"]],
            "next_step": "Analyze themes",
            "completed": 1,
            "remaining": 2
        }
    """
    import json
    from pathlib import Path
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Load current plan
        plan_file = workspace_dir / ".plans" / "current_plan.json"

        if not plan_file.exists():
            return json.dumps({
                "status": "no_plan",
                "message": "No active plan found. Create one with create_research_plan()."
            })

        # Read and return plan
        plan_data = json.loads(plan_file.read_text(encoding='utf-8'))

        # Add next_step field for convenience
        if plan_data["current_step"] < len(plan_data["steps"]):
            plan_data["next_step"] = plan_data["steps"][plan_data["current_step"]]
        else:
            plan_data["next_step"] = None

        # Add computed fields
        plan_data["completed"] = plan_data["current_step"]
        plan_data["remaining"] = len(plan_data["steps"]) - plan_data["current_step"]

        logger.info(f"📖 Read current plan: {plan_data['plan_id']} ({plan_data['progress']:.0%})")

        return json.dumps(plan_data, indent=2)

    except Exception as e:
        error_msg = f"❌ Failed to read plan: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({"status": "error", "message": error_msg})


@tool("edit_plan", args_schema=EditPlanInput)
def edit_plan_tool(
    action: str,
    step_index: Optional[int] = None,
    step_text: Optional[str] = None,
    result: Optional[str] = None,
    insert_position: Optional[int] = None
) -> str:
    """
    Modify the current research plan during execution.

    Allows dynamic plan adjustments: mark steps complete, add/remove/update steps.
    All modifications broadcast via WebSocket to update the Plan Panel in real-time.

    Args:
        action: One of 'mark_completed', 'add_step', 'remove_step', 'update_step'
        step_index: Index of step to modify (required for mark_completed, remove_step, update_step)
        step_text: New/updated step text (required for add_step, update_step)
        result: Completion summary (required for mark_completed)
        insert_position: Where to insert new step (for add_step, defaults to end)

    Returns:
        JSON string with operation status and updated plan info

    Examples:
        # Mark step 0 as completed
        edit_plan(
            action="mark_completed",
            step_index=0,
            result="Found 15 sources on AI healthcare trends"
        )

        # Add new step at end
        edit_plan(
            action="add_step",
            step_text="Validate findings with domain experts"
        )

        # Insert step at position 2
        edit_plan(
            action="add_step",
            step_text="Cross-reference with recent studies",
            insert_position=2
        )

        # Update step 1 text
        edit_plan(
            action="update_step",
            step_index=1,
            step_text="Analyze key themes AND emerging patterns"
        )

        # Remove step 3
        edit_plan(
            action="remove_step",
            step_index=3
        )
    """
    import json
    import time
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Load current plan
        plan_file = workspace_dir / ".plans" / "current_plan.json"

        if not plan_file.exists():
            return json.dumps({
                "status": "error",
                "message": "❌ No active plan found. Create one with create_research_plan() first."
            })

        # Read plan
        plan_data = json.loads(plan_file.read_text(encoding='utf-8'))
        num_steps = len(plan_data["steps"])

        # Validate and execute action
        if action == "mark_completed":
            # Mark step as completed
            if step_index is None or result is None:
                return json.dumps({
                    "status": "error",
                    "message": "❌ mark_completed requires step_index and result"
                })

            if step_index < 0 or step_index >= num_steps:
                return json.dumps({
                    "status": "error",
                    "message": f"❌ Invalid step_index {step_index}. Plan has {num_steps} steps (0-{num_steps-1})."
                })

            # Update plan
            step_text_completed = plan_data["steps"][step_index]
            plan_data["past_steps"].append([step_text_completed, result])
            plan_data["current_step"] = max(plan_data["current_step"], step_index + 1)
            plan_data["progress"] = plan_data["current_step"] / len(plan_data["steps"])
            plan_data["last_updated"] = time.time()

            # Broadcast step_completed event
            if manager is not None:
                try:
                    _run_broadcast_in_thread(
                        manager.broadcast({
                            "type": "agent_event",
                            "event_type": "step_completed",
                            "thread_id": "unknown",
                            "data": {
                                "type": "step_completed",
                                "plan_id": plan_data["plan_id"],
                                "step_index": step_index,
                                "step_text": step_text_completed,
                                "result": result[:200],
                                "progress": plan_data["progress"]
                            },
                            "timestamp": time.time()
                        })
                    )
                    logger.info(f"📡 Broadcast step_completed event for step {step_index}")
                except Exception as e:
                    logger.warning(f"⚠️ WebSocket broadcast failed: {e}")

            message = f"✅ Step {step_index + 1}/{len(plan_data['steps'])} marked complete ({plan_data['progress']:.0%})"

        elif action == "add_step":
            # Add new step
            if step_text is None:
                return json.dumps({
                    "status": "error",
                    "message": "❌ add_step requires step_text"
                })

            # Insert at position or append
            if insert_position is not None:
                insert_position = max(0, min(insert_position, len(plan_data["steps"])))
                plan_data["steps"].insert(insert_position, step_text)
                message = f"➕ Added step at position {insert_position}: \"{step_text}\""
            else:
                plan_data["steps"].append(step_text)
                message = f"➕ Added new step at end: \"{step_text}\""

            plan_data["last_updated"] = time.time()
            plan_data["progress"] = plan_data["current_step"] / len(plan_data["steps"])

            # Broadcast plan_updated event
            if manager is not None:
                try:
                    _run_broadcast_in_thread(
                        manager.broadcast({
                            "type": "agent_event",
                            "event_type": "plan_updated",
                            "thread_id": "unknown",
                            "data": {
                                "type": "plan_updated",
                                "plan_id": plan_data["plan_id"],
                                "steps": plan_data["steps"],
                                "current_step": plan_data["current_step"],
                                "progress": plan_data["progress"]
                            },
                            "timestamp": time.time()
                        })
                    )
                    logger.info(f"📡 Broadcast plan_updated event (added step)")
                except Exception as e:
                    logger.warning(f"⚠️ WebSocket broadcast failed: {e}")

        elif action == "remove_step":
            # Remove step
            if step_index is None:
                return json.dumps({
                    "status": "error",
                    "message": "❌ remove_step requires step_index"
                })

            if step_index < 0 or step_index >= num_steps:
                return json.dumps({
                    "status": "error",
                    "message": f"❌ Invalid step_index {step_index}. Plan has {num_steps} steps (0-{num_steps-1})."
                })

            removed_step = plan_data["steps"].pop(step_index)
            plan_data["last_updated"] = time.time()
            plan_data["progress"] = plan_data["current_step"] / max(len(plan_data["steps"]), 1)

            message = f"➖ Removed step {step_index}: \"{removed_step}\""

            # Broadcast plan_updated event
            if manager is not None:
                try:
                    _run_broadcast_in_thread(
                        manager.broadcast({
                            "type": "agent_event",
                            "event_type": "plan_updated",
                            "thread_id": "unknown",
                            "data": {
                                "type": "plan_updated",
                                "plan_id": plan_data["plan_id"],
                                "steps": plan_data["steps"],
                                "current_step": plan_data["current_step"],
                                "progress": plan_data["progress"]
                            },
                            "timestamp": time.time()
                        })
                    )
                    logger.info(f"📡 Broadcast plan_updated event (removed step)")
                except Exception as e:
                    logger.warning(f"⚠️ WebSocket broadcast failed: {e}")

        elif action == "update_step":
            # Update step text
            if step_index is None or step_text is None:
                return json.dumps({
                    "status": "error",
                    "message": "❌ update_step requires step_index and step_text"
                })

            if step_index < 0 or step_index >= num_steps:
                return json.dumps({
                    "status": "error",
                    "message": f"❌ Invalid step_index {step_index}. Plan has {num_steps} steps (0-{num_steps-1})."
                })

            old_text = plan_data["steps"][step_index]
            plan_data["steps"][step_index] = step_text
            plan_data["last_updated"] = time.time()

            message = f"✏️  Updated step {step_index}: \"{old_text}\" → \"{step_text}\""

            # Broadcast plan_updated event
            if manager is not None:
                try:
                    _run_broadcast_in_thread(
                        manager.broadcast({
                            "type": "agent_event",
                            "event_type": "plan_updated",
                            "thread_id": "unknown",
                            "data": {
                                "type": "plan_updated",
                                "plan_id": plan_data["plan_id"],
                                "steps": plan_data["steps"],
                                "current_step": plan_data["current_step"],
                                "progress": plan_data["progress"]
                            },
                            "timestamp": time.time()
                        })
                    )
                    logger.info(f"📡 Broadcast plan_updated event (updated step)")
                except Exception as e:
                    logger.warning(f"⚠️ WebSocket broadcast failed: {e}")

        else:
            return json.dumps({
                "status": "error",
                "message": f"❌ Invalid action '{action}'. Must be: mark_completed, add_step, remove_step, or update_step"
            })

        # Save updated plan
        plan_file.write_text(json.dumps(plan_data, indent=2), encoding='utf-8')

        # Also update plan_id-specific file
        plan_id_file = workspace_dir / ".plans" / f"{plan_data['plan_id']}.json"
        if plan_id_file.exists():
            plan_id_file.write_text(json.dumps(plan_data, indent=2), encoding='utf-8')

        logger.info(f"✅ Plan edited: {message}")

        # Return success
        return json.dumps({
            "status": "success",
            "message": message,
            "plan_id": plan_data["plan_id"],
            "total_steps": len(plan_data["steps"]),
            "current_step": plan_data["current_step"],
            "progress": plan_data["progress"]
        })

    except Exception as e:
        error_msg = f"❌ Failed to edit plan: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({"status": "error", "message": error_msg})


print("\n🔧 Production Tools Initialized:")
print("  ✅ Tavily Search - Web search with up-to-date information")
print("  ✅ Enhanced Tool Schema - Pydantic validation for better citations")
print("  ✅ Custom write_file - Explicit schema with human-in-the-loop approval")
print("  ✅ Custom edit_file - Replaces built-in tool with approval workflow")
print("\n📋 Note: Firecrawl, GitHub, and e2b will be added as subagents in future modules")


# ============================================================================
# STORAGE BACKEND
# ============================================================================

workspace_dir = Path(__file__).parent / "workspace"
os.makedirs(workspace_dir, exist_ok=True)

def create_hybrid_backend(rt):
    """Hybrid storage: ephemeral + filesystem."""
    return CompositeBackend(
        default=StateBackend(rt),
        routes={
            "/workspace/": FilesystemBackend(root_dir=workspace_dir, virtual_mode=True),
        }
    )

print("\n💾 Backend: CompositeBackend (StateBackend + FilesystemBackend)")
print("   Note: Custom write_file tool overrides FilesystemBackend's version (last wins)")

# ============================================================================
# LOG HELPER FUNCTIONS
# ============================================================================

def add_log(state: dict, message: str) -> dict:
    """Add a new log entry to state."""
    if "logs" not in state:
        state["logs"] = []
    state["logs"].append({"message": message, "done": False})
    return state

def complete_log(state: dict, index: int = -1) -> dict:
    """Mark a log entry as complete."""
    if "logs" in state and state["logs"]:
        state["logs"][index]["done"] = True
    return state

def clear_logs(state: dict) -> dict:
    """Clear all logs from state."""
    state["logs"] = []
    return state

print("\n📋 Log Helper Functions: add_log, complete_log, clear_logs")

# NOTE: When adding custom tools, emit progress logs:
# 1. Before operation: add_log(state, "🌐 Searching for...")
# 2. After operation: complete_log(state)
# 3. On task completion: clear_logs(state)

# ============================================================================
# TOOL USAGE PATTERNS DOCUMENTATION
# ============================================================================

"""
TOOL USAGE PATTERNS:

1. research_search (Tavily):
   - Returns: List of sources with {title, url, content}
   - Citation: Use URL from results in footnotes
   - Best for: Current information, statistics, technical docs

2. write_file:
   - CRITICAL: BOTH parameters are REQUIRED - file_path AND content
   - NEVER call write_file with only file_path - it will fail
   - Files saved to /workspace/ appear in the UI file browser automatically

   CORRECT Usage Examples:
   ✅ write_file(file_path="/workspace/report.md", content="# Report\n\nFull content here...")
   ✅ write_file(file_path="/workspace/data.txt", content="Line 1\nLine 2\nLine 3")

   WRONG Usage (will cause error):
   ❌ write_file(file_path="/workspace/report.md") - Missing content parameter!
   ❌ write_file(file_path="report.md", content="...") - Wrong path (no /workspace/)

   - Citation format in content:
     * Inline: "Claim text[^1]"
     * Footer: "[^1]: Title - URL"

3. write_todos (optional):
   - Use for: Tasks with 3+ distinct steps
   - Not required for simple research + write workflows
"""

# ============================================================================
# DEEP AGENT CREATION
# ============================================================================

# Collect production tools - supervisor coordinates but delegates specialized tasks
# NOTE: tavily_search is intentionally EXCLUDED - research MUST be delegated to researcher
# This enforces proper architectural boundaries and enables V3 citation verification
production_tools = [
    write_file_tool,            # Custom tool with explicit schema and approval
    edit_file_with_approval,    # Custom tool that overrides built-in edit_file
    create_research_plan_tool,  # Create structured research plan (NEW)
    update_plan_progress_tool,  # Track plan progress (NEW)
    read_current_plan_tool,     # Check plan status (NEW)
    edit_plan_tool,             # Modify plan during execution (NEW - Plan Mode)
    # Delegation tools (Phase 1b - Deep Subagent System)
    delegate_to_researcher,     # Delegate research tasks to Researcher subagent
    delegate_to_data_scientist, # Delegate data analysis to Data Scientist subagent
    delegate_to_expert_analyst, # Delegate problem analysis to Expert Analyst subagent
    delegate_to_writer,         # Delegate writing tasks to Writer subagent
    delegate_to_reviewer,       # Delegate document review to Reviewer subagent
]

# Agent creation moved to create_agent_with_checkpointer() function below
# This allows async initialization in main.py's lifespan with PostgreSQL checkpointer
# agent = None  # Now defined at module level (line 69)

def create_agent_with_checkpointer(saver):
    """
    Create DeepAgent with the provided checkpointer.

    This function is called from main.py's lifespan context manager
    after the PostgreSQL checkpointer has been initialized.

    Args:
        saver: AsyncPostgresSaver instance from setup_checkpointer()

    Returns:
        Configured DeepAgent with persistence enabled
    """
    from datetime import datetime

    print("\n🤖 Creating DeepAgent with PostgreSQL checkpointer...")

    # Generate current date for system prompt
    current_date = datetime.now().strftime('%Y-%m-%d (%A, %B %d)')

    return create_deep_agent(
        model=model,
        tools=production_tools,
        backend=create_hybrid_backend,  # Provides other filesystem tools (read_file, ls, etc.)
        checkpointer=saver,  # PostgreSQL checkpointer for persistence
        system_prompt=f"""Today's date is {current_date}.

You are a Research & Documentation Sidekick, an autonomous AI assistant specialized in conducting thorough research, creating well-structured documents, and editing content with precision. Your primary mission is to be proactive, complete, and reliable in gathering information and producing high-quality written deliverables.

## Core Capabilities

- **Web Research**: Deep, multi-source research using Tavily search with proper citation tracking
- **Document Creation**: Writing comprehensive documents with complete content (never summarized)
- **Content Editing**: Precise file modifications using targeted edit operations
- **File Management**: Reading, listing, and organizing workspace files
- **Task Planning**: Breaking down complex research and writing tasks into manageable steps

## Critical Tool Usage Rules

### EXECUTION DISCIPLINE: Always Execute, Never Just Announce

**CRITICAL: When you identify that a tool needs to be called, IMMEDIATELY make the tool call. Do NOT announce your intentions without executing them.**

- ✅ CORRECT: Make the tool call directly (e.g., call edit_file immediately)
- ❌ WRONG: Saying "I will now call edit_file..." then stopping without making the call
- ❌ WRONG: Explaining what you're about to do without actually doing it
- ❌ WRONG: Writing "Let me...", "I'm about to...", "I'll use..." then not following through

**If you find yourself writing phrases like:**
- "I will now use [tool]..."
- "Let me call [tool]..."
- "I'm about to execute [tool]..."

**STOP immediately and make the actual tool call instead of announcing it.**

**Example - WRONG approach:**
"I will now use edit_file to update the document with the research findings..."
[stops without calling the tool]

**Example - CORRECT approach:**
[Directly calls edit_file with proper parameters, no announcement]

**Why this matters:**
- Tool execution is required to complete tasks
- Announcements without execution waste user time
- The user expects actions, not descriptions of future actions

### write_file: The Complete Content Imperative

**NEVER summarize, truncate, or abbreviate content when using write_file. ALWAYS include COMPLETE content.**

- ✅ CORRECT: Include every section, paragraph, and detail in full
- ❌ WRONG: Writing "[Previous content...]" or "[Rest of content here]" or "... (content continues)"
- **Why**: Partial content corrupts files and loses user work permanently

**Large Document Strategy** (when content exceeds token limits):
1. Create initial file with first complete sections using write_file
2. Use multiple edit_file calls to append additional sections
3. Each edit adds ONE complete section at a time
4. Verify file integrity after each operation

Example workflow for large research report:
```
1. write_file: Title + Executive Summary + Introduction (complete)
2. edit_file: Append complete "Methodology" section
3. edit_file: Append complete "Findings" section
4. edit_file: Append complete "Conclusion" section
```

### edit_file: When and How to Use

**Use edit_file when:**
- Adding sections to existing documents
- Fixing specific errors or updating specific content
- Appending content that exceeds write_file token limits
- Making targeted changes while preserving most content

**Use write_file when:**
- Creating new documents from scratch
- Complete rewrites are needed
- Document is small enough to include entirely

### tavily_search: Research Best Practices

**Research Strategy:**
- Start broad, then narrow based on findings
- Use 3-5 results for quick checks, 7-10 for comprehensive research
- Extract and cite sources properly (URL, title, snippet)
- Cross-reference multiple sources for controversial claims
- Search multiple times for different aspects of complex topics

**Query Formulation:**
- Be specific and include key terms
- Use year filters for recent information (e.g., "AI trends 2025")
- Include domain-specific keywords for technical topics
- Rephrase and retry if initial results are poor

### ls and read_file: Context Gathering

**Before creating files:**
- Use `ls` to check what files already exist in the workspace
- Read existing related files to maintain consistency
- Check naming conventions from existing files

**File naming conventions:**
- Use descriptive, lowercase names with underscores: `research_report_ai_trends.md`
- Include dates for versioned content: `analysis_2025_01_15.md`
- Use appropriate extensions: `.md` for markdown, `.txt` for plain text

### Delegation Tools: Leveraging Specialized Subagents

**When to delegate:**
- Complex specialized tasks that benefit from focused expertise
- Tasks requiring different skill sets (research, analysis, writing, review)
- Parallel execution opportunities (multiple independent tasks)
- Quality assurance (review existing work)

**Available delegation tools:**

1. **delegate_to_researcher**: Web research and information synthesis
   - Use for: Market research, competitive analysis, technology trends
   - Produces: Well-cited documents with [1] [2] [3] format
   - Example: `delegate_to_researcher(research_question="AI agents market size 2025", output_file="market_research.md")`

2. **delegate_to_data_scientist**: Statistical analysis and data interpretation
   - Use for: Data analysis, pattern identification, trend analysis
   - Produces: Analysis reports with findings and visualizations
   - Example: `delegate_to_data_scientist(analysis_task="Analyze sales trends", data_description="Q4 data in /workspace/sales.csv", output_file="analysis.md")`

3. **delegate_to_expert_analyst**: Problem analysis and root cause investigation
   - Use for: 5 Whys analysis, SWOT analysis, strategic thinking
   - Produces: Structured problem analysis with recommendations
   - Example: `delegate_to_expert_analyst(problem_statement="Customer churn increased 20%", output_file="churn_analysis.md", analysis_framework="5_whys")`

4. **delegate_to_writer**: Professional document creation
   - Use for: Reports, executive summaries, blog posts, documentation
   - Produces: Polished, publication-ready content
   - Example: `delegate_to_writer(writing_task="Executive summary of Q4 results", output_file="summary.md", document_type="executive_summary", audience="executives")`

5. **delegate_to_reviewer**: Quality assessment and feedback
   - Use for: Document review, quality checks, improvement suggestions
   - Produces: Detailed review reports with constructive feedback
   - Example: `delegate_to_reviewer(document_to_review="/workspace/report.md", output_file="review.md", review_criteria="clarity and completeness")`

**Delegation best practices:**
- Provide clear, specific task descriptions
- Use descriptive output file names (e.g., "ai_market_research.md" not "output.md")
- Include additional instructions/criteria when needed for better results
- Review subagent output and iterate if needed
- Consider parallel delegation for independent tasks (e.g., research + analysis in parallel)

**Delegation workflow example:**
```
User: "Analyze the competitive landscape for AI coding assistants"

Workflow:
1. delegate_to_researcher(
     research_question="Current AI coding assistants and market leaders 2025",
     output_file="coding_assistant_landscape.md"
   )
2. delegate_to_expert_analyst(
     problem_statement="Key competitive differentiators in AI coding market",
     output_file="competitive_analysis.md",
     analysis_framework="swot"
   )
3. delegate_to_writer(
     writing_task="Executive brief on AI coding assistant landscape",
     output_file="executive_brief.md",
     document_type="executive_summary",
     audience="technical leadership"
   )
4. delegate_to_reviewer(
     document_to_review="/workspace/executive_brief.md",
     output_file="brief_review.md",
     review_criteria="accuracy and clarity for technical audience"
   )
```

## Critical Error Recovery Rules

**If a tool call fails:**
1. **DO NOT** immediately retry the exact same operation
2. **DO** diagnose why it failed (file too large? wrong path? invalid edit?)
3. **DO** try a different approach (e.g., write_file fails → try iterative strategy)
4. **DO** inform the user if multiple approaches fail

**Common failure scenarios:**
- `write_file` exceeds token limit → Switch to create + edit strategy
- `edit_file` can't find exact match → Read file first, get exact text
- `tavily_search` returns poor results → Rephrase query, try different keywords
- File doesn't exist → Use `ls` to verify path, check workspace structure

## Behavioral Guidelines

### Proactive Research
- Anticipate information needs beyond the immediate question
- Search for related context that provides deeper understanding
- Identify and fill gaps in information automatically
- Suggest additional research angles when relevant

### Document Structure Best Practices
- Use clear hierarchical headings (# ## ###)
- Include table of contents for documents >1000 words
- Add citation sections with source URLs
- Use formatting (bold, italic, lists) for readability
- Include timestamps or version info when relevant

### Communication Style
- **Brief confirmations**: "✓ Created research_report.md (3,240 words)" after tasks
- **Complete content in files**: Put all details in the document, not in messages
- **Ask for clarification** when research scope is ambiguous or could go multiple directions
- **Proactive suggestions**: "I found 3 additional sources on X, should I include them?"

## Common Scenarios

### Scenario 1: Comprehensive Research Report
**Request**: "Research the impact of AI on healthcare in 2025"

**Workflow**:
1. `tavily_search`: "AI healthcare impact 2025" (7-10 results)
2. `tavily_search`: "AI medical diagnosis 2025" (5 results)
3. `tavily_search`: "AI healthcare challenges 2025" (5 results)
4. `write_file`: Create complete report with all sections:
   - Title & metadata
   - Executive summary
   - Background
   - Key findings (from all searches)
   - Implications
   - Citations
5. Confirm: "✓ Created ai_healthcare_impact_2025.md (4,850 words, 22 sources)"

### Scenario 2: Large Document (>10,000 words)
**Request**: "Create a comprehensive guide to Python async programming"

**Workflow**:
1. Research phase: Multiple Tavily searches for different aspects
2. `write_file`: Title + Introduction + "Fundamentals" section (complete, ~2000 words)
3. `read_file`: Verify content integrity
4. `edit_file`: Append complete "Async/Await Patterns" section
5. `edit_file`: Append complete "Concurrency Best Practices" section
6. `edit_file`: Append complete "Common Pitfalls" section
7. `edit_file`: Append complete "Advanced Topics + Conclusion"
8. Final verification read

### Scenario 3: Document Editing
**Request**: "Add a section on security concerns to the AI report"

**Workflow**:
1. `read_file`: Read current document
2. `tavily_search`: "AI security concerns 2025" (5 results)
3. `edit_file`: Insert complete security section in appropriate location
4. Confirm: "✓ Added 'Security Considerations' section (680 words, 4 sources)"

## Key Principles

**As a research and documentation sidekick:**
- **Completeness**: Every file write contains FULL content, never summaries
- **Adaptability**: Learn from errors and switch strategies when needed
- **Proactivity**: Anticipate needs and suggest improvements
- **Reliability**: Verify operations and maintain file integrity
- **Clarity**: Brief messages to users, detailed content in files

**Remember**: You are the user's trusted sidekick for research and documentation. Be thorough in research, complete in content creation, and adaptive when facing challenges. The user depends on you to produce reliable, high-quality deliverables without requiring constant supervision.

## Research Planning Tools (NEW!)

For complex multi-step research tasks, you can create structured plans that track your progress:

### create_research_plan
**When to use**: Complex research with 3+ distinct steps requiring organized execution
**Example**: "Research AI trends in healthcare" → create 5-step plan → execute systematically

**Workflow**:
1. Call `create_research_plan(query="topic", num_steps=5)` at the START
2. Execute each step using your tools (tavily_search, write_file, etc.)
3. Call `update_plan_progress(step_index=0, result="...")` after EACH step
4. Continue until all steps complete
5. Plan progress appears in UI automatically

**Example**:
User asks: "Research AI in education and create a comprehensive report"

Step 1: create_research_plan(query="AI in education comprehensive research", num_steps=5)
→ Returns: {{{{"plan_id": "...", "steps": ["Search trends", "Find case studies", "Analyze impact", "Gather expert opinions", "Write report"]}}}}

Step 2: Execute step 0 - tavily_search(query="AI education trends 2025")
→ Got 10 sources...

Step 3: update_plan_progress(step_index=0, result="Found 10 sources on AI education trends")
→ Returns: "✅ Step 1/5 completed (20%). Next: Find case studies"

Step 4: Execute step 1 - tavily_search(query="AI education case studies")
...continue...

Step 5: After all steps, write final report with write_file

### When NOT to use planning:
- Simple 1-2 step tasks ("search for X")
- Quick edits or reads
- User asks for immediate answer

### Key benefits:
- Visual progress tracking in UI
- Organized approach to complex research
- Easy to resume if interrupted
- User sees your systematic methodology

# ============================================================================
# COMPREHENSIVE TOOL DOCUMENTATION
# ============================================================================

## Available Tools - Detailed Reference

You have access to the following tools. Understanding when and how to use each tool is critical to your success.

### 1. tavily_search - Real-Time Web Research

**What it does**:
Searches the web in real-time to gather current information, facts, statistics, and sources. Returns a list of results with titles, URLs, and content snippets.

**When to use**:
- Need latest news, trends, or current events
- Researching topics not in your training data or after your knowledge cutoff
- Gathering statistics, data, or factual information
- Finding expert opinions, technical documentation, or how-to guides
- Verifying claims across multiple sources
- Any time you need information more recent than your training data

**When NOT to use**:
- User asks for analysis or opinion (use your reasoning instead)
- Information is basic and within your training data (e.g., "What is Python?")
- No internet connectivity required

**Best practices**:
- Use specific, focused queries for better results (e.g., "AI healthcare trends 2025" not "AI healthcare")
- Search multiple times with different angles for comprehensive research
- Request 7-10 results for thorough research, 3-5 for quick checks
- Always cite sources in your reports using [^1] format with URLs
- Cross-reference multiple sources for controversial or critical claims
- Include year in queries for time-sensitive topics (e.g., "Python best practices 2025")
- Rephrase and retry if initial results are poor quality
- Extract key information and URLs from results for citations

**Example usage patterns**:
```
# Quick fact check (3-5 results)
tavily_search(query="current GDP of France", max_results=3)

# Comprehensive research (7-10 results)
tavily_search(query="AI impact on healthcare 2025", max_results=10)

# Multi-angle research
tavily_search(query="renewable energy adoption rates 2025", max_results=7)
tavily_search(query="renewable energy challenges 2025", max_results=5)
tavily_search(query="renewable energy policy changes 2025", max_results=5)
```

### 2. write_file_tool - Document Creation

**What it does**:
Creates a new file or completely overwrites an existing file in the /workspace/ directory. Files automatically appear in the UI file browser.

**When to use**:
- Creating new research reports, documents, or summaries from scratch
- Generating content that doesn't exceed token limits (~8000 words)
- Complete rewrites of existing documents
- Creating structured data files (JSON, CSV, etc.)

**When NOT to use**:
- Content exceeds ~8000 words (use write + multiple edits instead)
- Making small changes to existing files (use edit_file instead)
- Appending to existing documents (use edit_file instead)

**Best practices**:
- CRITICAL: BOTH parameters are REQUIRED - file_path AND content
- NEVER call with only file_path - it will fail immediately
- Always use absolute paths: /workspace/filename.md
- Use descriptive filenames: research_report_ai_healthcare_2025.md
- Include complete content - NEVER truncate or summarize
- Format with markdown for readability
- Include proper citations with [^1]: Title - URL format
- Add table of contents for documents >1000 words
- Use clear hierarchical headings (# ## ###)
- Include metadata (date, topic, sources count) at the top

**WRONG usage examples**:
❌ write_file(file_path="/workspace/report.md")  # Missing content!
❌ write_file(file_path="report.md", content="...") # Wrong path (no /workspace/)
❌ write_file(file_path="/workspace/report.md", content="# Report\n\n[Rest of content here]...") # Incomplete content!

**CORRECT usage examples**:
✅ write_file(file_path="/workspace/report.md", content="# Complete Report\n\n## Introduction\n\nFull text here...\n\n## Findings\n\nComplete findings...\n\n## Sources\n[^1]: Title - URL")
✅ write_file(file_path="/workspace/data.txt", content="Line 1\nLine 2\nLine 3\n...")

**Citation format in content**:
```markdown
The study found significant improvements[^1] in patient outcomes[^2].

## Sources
[^1]: AI in Healthcare 2025 - https://example.com/article1
[^2]: Medical AI Study - https://example.com/article2
```

### 3. edit_file_with_approval - Targeted Document Editing

**What it does**:
Modifies existing files with precision using exact string matching. Requires user approval before making changes (except when auto-approve is enabled).

**When to use**:
- Adding sections to existing documents
- Fixing specific errors or updating specific content
- Appending content to large documents built incrementally
- Making targeted changes while preserving most content
- Correcting mistakes or typos in existing files

**When NOT to use**:
- Creating new files from scratch (use write_file instead)
- Complete rewrites (easier to use write_file)
- File doesn't exist yet (use write_file first)

**Best practices**:
- Read the file first with read_file to get exact current content
- Use exact string matching - must match precisely including whitespace
- Show user what's changing and why (for approval context)
- For large additions, append one complete section at a time
- Verify edits succeeded by reading file after editing
- Use for incremental builds when document exceeds token limits

**Approval workflow**:
1. You propose the edit with old_string and new_string
2. System asks user for approval (unless auto-approve enabled)
3. User approves or rejects with optional feedback
4. Edit executes if approved

**Example usage patterns**:
```
# Append new section
edit_file(
    file_path="/workspace/report.md",
    old_string="## Conclusion\n\nFinal thoughts here.",
    new_string="## Security Considerations\n\nNew section content...\n\n## Conclusion\n\nFinal thoughts here."
)

# Fix typo
edit_file(
    file_path="/workspace/data.txt",
    old_string="teh quick brown fox",
    new_string="the quick brown fox"
)

# Append to end of document
edit_file(
    file_path="/workspace/report.md",
    old_string="[^5]: Last source - https://example.com",
    new_string="[^5]: Last source - https://example.com\n[^6]: New source - https://newsite.com"
)
```

### 4. create_research_plan_tool - Structured Research Planning

**What it does**:
Creates a structured research plan with 3-10 distinct steps. The plan is displayed in the UI with a progress tracker.

**When to use**:
- Complex research requiring 3+ distinct steps
- Multi-faceted topics needing systematic exploration
- User requests comprehensive or detailed research
- Tasks benefit from visible progress tracking
- Research that will take multiple searches and synthesis

**When NOT to use**:
- Simple 1-2 step tasks (e.g., "search for X")
- Quick fact checks or single-topic queries
- User asks for immediate answer without research process
- Editing or reading existing files

**Best practices**:
- Call at the START of complex research, before any searches
- Create 3-10 specific, actionable steps
- Each step should be independently executable
- Steps should build logically toward final deliverable
- Typical pattern: Search → Analyze → Synthesize → Document
- Plan is created once per research task, not multiple times

**Example usage**:
```python
# User asks: "Research AI in education and create a comprehensive report"

# Step 1: Create the plan
create_research_plan(
    query="AI in education comprehensive research",
    num_steps=5
)

# Returns:
{{
    "plan_id": "uuid-here",
    "steps": [
        "Search current AI education trends and adoption rates",
        "Find real-world case studies and implementations",
        "Analyze impact on learning outcomes",
        "Gather expert opinions and criticisms",
        "Write comprehensive report with findings"
    ]
}}

# Now execute each step and update progress...
```

**Typical research plan structures**:

For technology research:
1. Search current trends and state of technology
2. Find technical specifications and capabilities
3. Research real-world applications and case studies
4. Investigate challenges and limitations
5. Write comprehensive analysis report

For market research:
1. Search market size and growth data
2. Find key players and competitive landscape
3. Research customer needs and pain points
4. Analyze trends and future projections
5. Create market analysis document

### 5. update_plan_progress_tool - Plan Step Completion

**What it does**:
Marks a plan step as completed and updates the UI progress tracker. Automatically advances to next step.

**When to use**:
- Immediately after completing EACH step of your research plan
- After gathering information for a step
- After finishing any plan-defined task
- Before moving to the next step

**When NOT to use**:
- Before starting a step (only after completion)
- Multiple times for the same step
- When no plan has been created

**Best practices**:
- Call immediately after finishing each step - don't batch updates
- Provide brief 1-2 sentence summary of what was accomplished
- Include key metrics when relevant (e.g., "Found 12 sources on topic X")
- Updates UI progress bar automatically (20%, 40%, 60%, etc.)
- Required for accurate progress tracking
- Step index is 0-based (first step is 0, second is 1, etc.)

**Example workflow**:
```python
# After creating plan with 5 steps...

# Complete step 0
tavily_search(query="AI education trends 2025", max_results=10)
# ... gather and analyze results ...
update_plan_progress(
    step_index=0,
    result="Found 10 authoritative sources on AI education trends including statistics and expert analysis"
)
# Returns: "✅ Step 1/5 completed (20%). Next: Find real-world case studies"

# Complete step 1
tavily_search(query="AI education case studies 2025", max_results=7)
# ... gather case studies ...
update_plan_progress(
    step_index=1,
    result="Gathered 7 detailed case studies from universities and schools implementing AI"
)
# Returns: "✅ Step 2/5 completed (40%). Next: Analyze impact on learning outcomes"

# Continue for remaining steps...
```

### 6. read_current_plan_tool - Plan Status Check

**What it does**:
Returns the current research plan including all steps, completion status, and progress percentage.

**When to use**:
- Need to verify what step comes next
- Check overall progress status
- Resuming work after interruption
- Confirming plan structure before proceeding

**When NOT to use**:
- No plan has been created yet
- You already know the next step
- Just completed a step (update_plan_progress returns next step)

**Best practices**:
- Use when resuming work or uncertain about progress
- Helpful for staying organized in long research tasks
- Review before executing next step to ensure alignment
- Returns complete plan structure for reference

**Example usage**:
```python
read_current_plan()

# Returns:
{{
    "plan_id": "uuid-here",
    "query": "AI in education comprehensive research",
    "total_steps": 5,
    "completed_steps": 2,
    "progress_percentage": 40,
    "steps": [
        {{"step": "Search trends", "completed": true, "result": "Found 10 sources..."}},
        {{"step": "Find case studies", "completed": true, "result": "Gathered 7 cases..."}},
        {{"step": "Analyze impact", "completed": false, "result": null}},
        {{"step": "Gather opinions", "completed": false, "result": null}},
        {{"step": "Write report", "completed": false, "result": null}}
    ],
    "current_step": "Analyze impact on learning outcomes"
}}
```

# ============================================================================
# TOOL SELECTION DECISION GUIDE
# ============================================================================

## Choosing the Right Tool

### For Research Tasks:
1. **Simple query**: Just search once with tavily_search
2. **Complex research (3+ steps)**:
   - create_research_plan first
   - Execute searches for each step
   - update_plan_progress after each step
   - write_file for final report
3. **Verification**: tavily_search with multiple queries from different angles

### For Document Creation:
1. **New document (<8000 words)**: write_file with complete content
2. **New document (>8000 words)**:
   - write_file for first sections
   - edit_file to append additional sections
   - read_file to verify after each edit
3. **Modifying existing**: edit_file with precise changes

### For File Operations:
1. **Check what exists**: ls or glob
2. **Read content**: read_file
3. **Create new**: write_file
4. **Modify existing**: edit_file
5. **Search content**: grep

## Common Workflow Patterns

### Pattern 1: Simple Research & Document
```
1. tavily_search (gather info)
2. tavily_search (additional searches as needed)
3. write_file (create report with findings)
```

### Pattern 2: Complex Research with Planning
```
1. create_research_plan (5 steps)
2. tavily_search (step 1)
3. update_plan_progress (mark step 1 complete)
4. tavily_search (step 2)
5. update_plan_progress (mark step 2 complete)
... continue for all steps ...
N. write_file (final deliverable)
```

### Pattern 3: Large Document Creation
```
1. Multiple tavily_search calls (research phase)
2. write_file (create first 2-3 sections)
3. read_file (verify content)
4. edit_file (append next complete section)
5. edit_file (append another complete section)
6. edit_file (append final sections)
7. read_file (final verification)
```

### Pattern 4: Document Enhancement
```
1. read_file (understand current content)
2. tavily_search (gather new information)
3. edit_file (add new section or update existing)
```

## Tool Combination Best Practices

1. **Always read before editing**: Use read_file to get exact content before edit_file
2. **Search before writing**: Use tavily_search to gather information before write_file
3. **Verify after creating**: Use read_file after write_file for large documents
4. **Plan complex tasks**: Use create_research_plan for 3+ step research
5. **Update incrementally**: Call update_plan_progress after EACH step, not in batches

🔮 Future: Firecrawl, GitHub, e2b will be added as subagents
"""
)

print("✅ DeepAgent Ready with Tavily + built-in filesystem tools\n")

# ============================================================================
# HUMAN-IN-THE-LOOP APPROVAL SYSTEM
# ============================================================================

# Global state for approval tracking
pending_approvals = {}  # {request_id: {tool_name, tool_args, event, future}}
approval_decisions = {}  # {request_id: {approved, feedback}}
approval_lock = asyncio.Lock()

# Thread-local storage for auto-approve mode (controlled by frontend via chat request)
_auto_approve_state = threading.local()

def set_auto_approve(enabled: bool):
    """Set auto-approve mode for current thread/coroutine."""
    _auto_approve_state.enabled = enabled

def get_auto_approve() -> bool:
    """Get auto-approve mode for current thread/coroutine."""
    return getattr(_auto_approve_state, 'enabled', True)  # Default True

# Workspace directory configuration (can be overridden for testing)
_workspace_dir = None

def set_workspace_dir(workspace_dir: str):
    """Set custom workspace directory (useful for testing)."""
    global _workspace_dir
    _workspace_dir = workspace_dir

def get_workspace_dir() -> Path:
    """Get workspace directory (custom or default backend/workspace)."""
    if _workspace_dir is not None:
        return Path(_workspace_dir)
    return Path(__file__).parent / "workspace"

# SSE event queue for approval requests
# Tools push approval events here, SSE stream yields them
sse_event_queue = asyncio.Queue()

async def get_approval_for_tool(tool_name: str, tool_args: dict, request_id: str) -> dict:
    """
    Request approval for a tool call.

    Args:
        tool_name: Name of the tool being called
        tool_args: Arguments for the tool call
        request_id: Unique identifier for this approval request

    Returns:
        {"approved": True} to proceed
        {"approved": False, "feedback": "..."} to reject with feedback
    """
    # Create an event to wait for decision
    approval_event = asyncio.Event()
    future = asyncio.Future()

    async with approval_lock:
        pending_approvals[request_id] = {
            "tool_name": tool_name,
            "tool_args": tool_args,
            "event": approval_event,
            "future": future
        }

    # Push approval request to SSE event queue
    try:
        await sse_event_queue.put({
            "type": "tool_approval_request",
            "request_id": request_id,
            "tool_name": tool_name,
            "tool_args": tool_args
        })
        print(f"📡 [Approval] Queued SSE event for {tool_name} (request_id: {request_id})")
    except Exception as e:
        print(f"⚠️ [Approval] Failed to queue SSE event: {e}")

    # Wait for decision (with timeout)
    try:
        decision = await asyncio.wait_for(future, timeout=300.0)  # 5 minute timeout
        return decision
    except asyncio.TimeoutError:
        print(f"⏱️ [Approval] Timeout waiting for decision on {tool_name}")
        # Cleanup
        async with approval_lock:
            pending_approvals.pop(request_id, None)
            approval_decisions.pop(request_id, None)
        return {"approved": False, "feedback": "Approval timeout - operation cancelled"}
    finally:
        # Cleanup
        async with approval_lock:
            pending_approvals.pop(request_id, None)


async def submit_approval_decision(request_id: str, approved: bool, feedback: str = None):
    """
    Submit an approval decision for a pending request.

    Args:
        request_id: Unique identifier for the approval request
        approved: Whether to approve the tool call
        feedback: Optional feedback message (used when rejecting)

    Returns:
        {"status": "ok"} if successful, {"status": "error", "message": "..."} otherwise
    """
    async with approval_lock:
        if request_id not in pending_approvals:
            return {"status": "error", "message": "Request ID not found"}

        # Store decision
        decision = {
            "approved": approved,
            "feedback": feedback
        }
        approval_decisions[request_id] = decision

        # Resolve the future
        pending_approval = pending_approvals[request_id]
        if not pending_approval["future"].done():
            pending_approval["future"].set_result(decision)

        # Signal the event
        pending_approval["event"].set()

        print(f"✅ [Approval] Decision recorded for {request_id}: approved={approved}")

        return {"status": "ok"}


# ============================================================================
# EXECUTION FUNCTION WITH STREAMING
# ============================================================================

def run_agent_task(query: str, thread_id: str = "demo"):
    """Execute agent task with streaming and real-time visibility."""

    print("\n" + "🎯" * 40)
    print(f"USER QUERY: {query}")
    print("🎯" * 40)

    config = {"configurable": {"thread_id": thread_id}}

    print("\n🚀 Streaming DeepAgent execution...\n")
    print("─" * 80)

    final_response = None
    step_count = 0

    # Stream with updates mode for real-time visibility
    for chunk in agent.stream(
        {"messages": [{"role": "user", "content": query}]},
        config=config,
        stream_mode="updates"
    ):
        step_count += 1

        # chunk is a dict with node name as key
        for node_name, node_update in chunk.items():
            if node_name == "__start__" or node_name == "__end__":
                continue

            # Skip if update is None or empty
            if not node_update:
                continue

            print(f"\n📍 Node: {node_name}")

            # Check for messages in the update
            if "messages" in node_update:
                messages = node_update["messages"]
                for msg in messages:
                    # Check for AI message with tool calls
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            print(f"  🔧 TOOL CALL: {tool_call['name']}")
                            args = tool_call.get('args', {})
                            if args:
                                # Show first 2 args, truncate values
                                arg_items = list(args.items())[:2]
                                arg_str = ", ".join(f"{k}={str(v)[:60]}" for k, v in arg_items)
                                print(f"     Args: {arg_str}")

                    # Check for tool message (results)
                    elif hasattr(msg, "tool_call_id"):
                        content = str(msg.content)
                        preview = content[:200] if len(content) > 200 else content
                        print(f"  📊 TOOL RESULT:")
                        print(f"     {preview}{'...' if len(content) > 200 else ''}")

                    # Check for AI response (final answer)
                    elif hasattr(msg, "content") and msg.content and not hasattr(msg, "tool_calls"):
                        # This is likely the final response
                        final_response = node_update

            # Check for todos (planning)
            if "todos" in node_update:
                todos = node_update["todos"]
                if todos:
                    print(f"  📝 PLANNING: {len(todos)} tasks created")
                    for todo in todos[:3]:  # Show first 3
                        status = todo.get("status", "unknown")
                        content = todo.get("content", "")
                        print(f"     [{status}] {content[:60]}")

            # Display progress logs if present
            if "logs" in node_update and node_update["logs"]:
                print(f"  📋 PROGRESS LOGS:")
                for log in node_update["logs"]:
                    status = "✅" if log.get("done", False) else "⏳"
                    print(f"     {status} {log['message']}")

    print("\n" + "─" * 80)
    print(f"✅ Completed in {step_count} stream events\n")

    # Get final result from last stream
    result = agent.invoke(
        {"messages": [{"role": "user", "content": query}]},
        config=config
    )

    # Display final result
    if result and "messages" in result:
        final_message = result["messages"][-1]
        print("=" * 80)
        print("📊 FINAL RESULT")
        print("=" * 80)
        print(final_message.content if hasattr(final_message, "content") else str(final_message))
        print("=" * 80)

    return result


# ============================================================================
# EXAMPLES
# ============================================================================

if __name__ == "__main__":
    print("\n\n" + "🔬" * 40)
    print("EXAMPLE 1: Simple Search with Citations")
    print("🔬" * 40)

    result1 = run_agent_task(
        "Search for the latest updates on LangChain v1.0 and create a summary with citations at /workspace/langchain_v1_summary.md",
        thread_id="citation-demo-1"
    )

    print("\n\n" + "🔬" * 40)
    print("EXAMPLE 2: Multi-Source Research with Citations")
    print("🔬" * 40)

    result2 = run_agent_task(
        "Research DeepAgents v0.2 architecture and benefits. Create a comprehensive report at /workspace/deepagents_research.md with inline citations for every claim.",
        thread_id="citation-demo-2"
    )

    print("\n\n" + "🔬" * 40)
    print("EXAMPLE 3: Multi-Step Task with Citations")
    print("🔬" * 40)

    result3 = run_agent_task(
        """Research the benefits of agentic AI systems, create a comparison with traditional AI,
        and save a detailed report with citations at /workspace/agentic_ai_report.md""",
        thread_id="citation-demo-3"
    )

# ============================================================================
# SUMMARY
# ============================================================================

if __name__ == "__main__":
    print("\n\n" + "=" * 80)
    print("MODULE 2.2 SUMMARY")
    print("=" * 80)

    summary = """
✅ Demonstrated Concepts:

1. Simplified DeepAgent Architecture
   - Single agent with focused tool set (Tavily + filesystem)
   - Automatic planning with TodoListMiddleware
   - Streaming execution for real-time visibility

2. Production Tool Integration
   - Tavily: Real-time web search with up-to-date information
   - Native LangChain tool integration

3. DeepAgents v0.2 Features
   - CompositeBackend for hybrid storage
   - TodoListMiddleware (automatic planning)
   - FilesystemMiddleware (built-in file operations)
   - Conversation checkpointing for memory
   - Streaming support for transparency

4. Built-in Capabilities
   - Filesystem tools (ls, read_file, write_file, edit_file, glob, grep)
   - TODO list tracking (write_todos tool)
   - Hybrid storage (/workspace/ → filesystem, default → ephemeral)

📚 Key Learnings:

- Start simple: Tavily + filesystem tools provide powerful baseline
- Tool count matters: Fewer tools = lower overhead, works with Haiku 4.5
- Streaming provides transparency and catches issues early
- Hybrid backends enable both ephemeral and persistent storage
- Claude Haiku 4.5 provides fast, cost-effective reasoning ($1/$5 per 1M tokens)

🔧 Tool Usage Patterns:

- Tavily: Web research, current events, documentation lookup
- write_todos: Planning multi-step tasks
- write_file: Saving research findings and reports
- Filesystem: Managing data across conversation turns

🎯 Next Steps:

1. **Add Subagents** (Future Modules):
   - Firecrawl subagent for web scraping
   - GitHub subagent for repository operations
   - e2b subagent for code execution

2. **Advanced Features**:
   - Experiment with StoreBackend for cross-session persistence
   - Implement human-in-the-loop for sensitive operations
   - Deploy with production checkpointing (PostgreSQL)

💡 Production Considerations:

- Rate limits: Tavily has 1,000 searches/month (free tier)
- Error handling: Robust error handling implemented
- Cost tracking: Monitor Tavily API usage
- Security: API keys in environment variables
- Scalability: StoreBackend + PostgreSQL for multi-user deployments

🎓 Architecture Decision:

- **Why simplified**: Haiku 4.5 has strict request size limits
- **10+ tools** (previous version) → 413 "Request Too Large" errors
- **7 tools** (current: 1 production + 6 filesystem) → Works smoothly
- **Future growth**: Add specialized tools via subagents, not main agent

"""

    print(summary)
    print("=" * 80)

    print("\n✨ Module 2.2 Complete! ✨\n")
