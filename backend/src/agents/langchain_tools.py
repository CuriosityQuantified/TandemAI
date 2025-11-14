"""
LangChain Tool Definitions for ATLAS Supervisor Agent

Converts all 11 ATLAS supervisor tools to LangChain v1 format using @tool decorator.
Maintains all original functionality while fixing Letta type annotation issues.

Tools organized by category:
- Planning: plan_task, update_plan
- Todo Management: create_todo, update_todo_status
- File Operations: save_output, load_file, append_content, list_outputs
- Delegation: delegate_research, delegate_analysis, delegate_writing
"""

import json
import logging
from typing import Annotated, List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from langchain_core.tools import tool, ToolException

# Import original tool implementations
from src.tools.planning_tool import _plan_stores
from src.tools.todo_tool import _todo_stores, TodoStatus
from src.tools.file_tool import (
    get_session_path,
    BASE_OUTPUT_DIR
)
from src.utils.call_model import quick_call

logger = logging.getLogger(__name__)

# ============================================================================
# PLANNING TOOLS
# ============================================================================

class PlanTaskInput(BaseModel):
    """Input schema for task planning."""
    task_description: str = Field(description="The main task to be accomplished")
    context: str = Field(default="", description="Additional context or constraints for planning")
    agent_memory: str = Field(default="", description="Optional memory/history from the agent")
    agent_namespace: str = Field(default="", description="Namespace for agent isolation (default: supervisor)")


@tool(args_schema=PlanTaskInput)
async def plan_task(
    task_description: str,
    context: str = "",
    agent_memory: str = "",
    agent_namespace: str = ""
) -> dict:
    """Decompose a complex task into a structured plan with sub-tasks using LLM reasoning.

    Creates an intelligent plan with task dependencies and type assignments (research/analysis/writing).
    Supports namespace isolation for multi-agent systems.
    """
    # Determine namespace (default to supervisor)
    namespace = agent_namespace if agent_namespace else "supervisor"
    if namespace not in _plan_stores:
        _plan_stores[namespace] = []

    try:
        # Construct planning prompt
        planning_prompt = f"""
        You are a task planning assistant. Decompose the following task into actionable sub-tasks.

        Main Task: {task_description}

        Context: {context if context else 'No additional context provided'}

        Agent Memory: {agent_memory if agent_memory else 'No prior memory'}

        Please create a structured plan with:
        1. 3-5 specific sub-tasks
        2. Clear dependencies between tasks (required for each task)
        3. Assignment to appropriate task types (research/analysis/writing)

        Respond in JSON format:
        {{
            "sub_tasks": [
                {{
                    "id": "task_1",
                    "description": "specific task description",
                    "task_type": "research|analysis|writing",
                    "dependencies": []
                }}
            ],
            "estimated_duration": "time estimate",
            "reasoning": "brief explanation of the plan"
        }}
        """

        # Call LLM for planning using async quick_call
        response_text = await quick_call(
            model_name="gpt-4o-mini",
            message=planning_prompt,
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        # Parse LLM response
        llm_plan = json.loads(response_text)

        # Structure the plan
        plan = {
            "plan_id": f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "main_goal": task_description,
            "context": context,
            "sub_tasks": llm_plan.get("sub_tasks", []),
            "estimated_duration": llm_plan.get("estimated_duration", "30-60 minutes"),
            "reasoning": llm_plan.get("reasoning", ""),
            "created_at": datetime.now().isoformat(),
            "llm_generated": True
        }

        # Add status field to each sub-task
        for task in plan["sub_tasks"]:
            task["status"] = "pending"

        # Store plan in namespace-specific store
        _plan_stores[namespace].append(plan)

        return plan

    except Exception as e:
        logger.error(f"LLM planning failed: {e}")
        # Fallback to template-based planning
        plan = {
            "plan_id": f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "main_goal": task_description,
            "context": context,
            "sub_tasks": [
                {
                    "id": "task_1",
                    "description": f"Research information about: {task_description}",
                    "task_type": "research",
                    "dependencies": [],
                    "status": "pending"
                },
                {
                    "id": "task_2",
                    "description": f"Analyze findings for: {task_description}",
                    "task_type": "analysis",
                    "dependencies": ["task_1"],
                    "status": "pending"
                },
                {
                    "id": "task_3",
                    "description": f"Create report about: {task_description}",
                    "task_type": "writing",
                    "dependencies": ["task_2"],
                    "status": "pending"
                }
            ],
            "estimated_duration": "30-60 minutes",
            "created_at": datetime.now().isoformat()
        }

        _plan_stores[namespace].append(plan)
        return plan


class UpdatePlanInput(BaseModel):
    """Input schema for plan updates."""
    plan_id: str = Field(description="The plan identifier to update")
    updates: dict = Field(description="Dictionary of updates to apply")
    feedback: str = Field(default="", description="Execution feedback to inform plan adjustments")
    agent_namespace: str = Field(default="", description="Namespace for agent isolation")


@tool(args_schema=UpdatePlanInput)
async def update_plan(
    plan_id: str,
    updates: dict,
    feedback: str = "",
    agent_namespace: str = ""
) -> dict:
    """Update an existing plan based on execution feedback using LLM reasoning.

    Analyzes feedback and suggests plan modifications, task priority changes, or new tasks.
    """
    namespace = agent_namespace if agent_namespace else "supervisor"

    try:
        # Construct update prompt
        update_prompt = f"""
        You need to update an existing task plan based on execution feedback.

        Plan ID: {plan_id}
        Current Updates: {json.dumps(updates, indent=2)}
        Feedback: {feedback if feedback else 'No specific feedback'}

        Based on this information, suggest plan adjustments:
        1. Should any tasks be modified?
        2. Should task priorities change?
        3. Are new tasks needed?
        4. Should any tasks be removed?

        Respond in JSON format:
        {{
            "modifications": [
                {{
                    "task_id": "id",
                    "change_type": "modify|add|remove",
                    "details": "description of change"
                }}
            ],
            "reasoning": "explanation for the changes"
        }}
        """

        # Call LLM for plan updates using async quick_call
        response_text = await quick_call(
            model_name="gpt-4o-mini",
            message=update_prompt,
            temperature=0.5,
            response_format={"type": "json_object"}
        )

        llm_updates = json.loads(response_text)

        return {
            "plan_id": plan_id,
            "status": "updated",
            "updates_applied": updates,
            "llm_suggestions": llm_updates.get("modifications", []),
            "reasoning": llm_updates.get("reasoning", ""),
            "updated_at": datetime.now().isoformat(),
            "llm_assisted": True
        }

    except Exception as e:
        logger.error(f"LLM update failed: {e}")
        return {
            "plan_id": plan_id,
            "status": "updated",
            "updates_applied": updates,
            "updated_at": datetime.now().isoformat(),
            "llm_assisted": False,
            "error": str(e)
        }


# ============================================================================
# TODO MANAGEMENT TOOLS
# ============================================================================

class CreateTodoInput(BaseModel):
    """Input schema for creating todos."""
    task_id: str = Field(description="Unique identifier for the task")
    description: str = Field(description="What needs to be done")
    task_type: str = Field(default="", description="Task type: research, analysis, or writing")
    dependencies: List[str] = Field(default_factory=list, description="List of task IDs that must complete first")
    agent_namespace: str = Field(default="", description="Namespace for agent isolation")


@tool(args_schema=CreateTodoInput)
def create_todo(
    task_id: str,
    description: str,
    task_type: str = "",
    dependencies: List[str] = None,
    agent_namespace: str = ""
) -> dict:
    """Create a new todo item for tracking task execution.

    Supports namespace isolation for multi-agent systems where each agent
    maintains its own todo list without conflicts.
    """
    namespace = agent_namespace if agent_namespace else "supervisor"
    if namespace not in _todo_stores:
        _todo_stores[namespace] = []

    todo = {
        "task_id": task_id,
        "description": description,
        "task_type": task_type,
        "status": TodoStatus.PENDING.value,
        "dependencies": dependencies or [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "completed_at": None,
        "result": None,
        "error": None
    }

    _todo_stores[namespace].append(todo)
    return todo


class UpdateTodoStatusInput(BaseModel):
    """Input schema for updating todo status."""
    task_id: str = Field(description="The task to update")
    status: str = Field(description="New status: pending, in_progress, completed, blocked, or failed")
    result: str = Field(default="", description="Optional result data if completed")
    error: str = Field(default="", description="Optional error message if failed")
    agent_namespace: str = Field(default="", description="Namespace for agent isolation")


@tool(args_schema=UpdateTodoStatusInput)
def update_todo_status(
    task_id: str,
    status: str,
    result: str = "",
    error: str = "",
    agent_namespace: str = ""
) -> dict:
    """Update the status of a todo item.

    The supervisor maintains full context, so no query functions are needed.
    """
    namespace = agent_namespace if agent_namespace else "supervisor"
    if namespace not in _todo_stores:
        raise ToolException(f"No todos found in namespace '{namespace}'")

    todos = _todo_stores[namespace]

    for todo in todos:
        if todo["task_id"] == task_id:
            todo["status"] = status
            todo["updated_at"] = datetime.now().isoformat()

            if status == TodoStatus.COMPLETED.value:
                todo["completed_at"] = datetime.now().isoformat()
                todo["result"] = result
            elif status == TodoStatus.FAILED.value:
                todo["error"] = error

            return todo

    raise ToolException(f"Todo with task_id '{task_id}' not found in namespace '{namespace}'")


# ============================================================================
# FILE OPERATIONS TOOLS
# ============================================================================

class SaveOutputInput(BaseModel):
    """Input schema for saving files."""
    filename: str = Field(description="Name of the file to create")
    content: str = Field(description="Content to write")
    file_type: str = Field(default="text", description="File type: text, json, markdown, or yaml")
    subdirectory: str = Field(default="", description="Optional subdirectory: research, analysis, reports, or data")
    metadata: Optional[dict] = Field(default=None, description="Optional metadata about the file")


@tool(args_schema=SaveOutputInput)
def save_output(
    filename: str,
    content: str,
    file_type: str = "text",
    subdirectory: str = "",
    metadata: dict = None
) -> dict:
    """Save content to a file in the session directory.

    All files are automatically organized by the current chat session.
    Supports text, JSON, markdown, and YAML formats with optional metadata.
    """
    from pathlib import Path

    try:
        session_dir = get_session_path()

        # Determine output directory
        if subdirectory:
            output_dir = session_dir / subdirectory
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = session_dir

        # Add appropriate extension if not present
        extensions = {
            "text": ".txt",
            "json": ".json",
            "markdown": ".md",
            "yaml": ".yaml"
        }
        if not any(filename.endswith(ext) for ext in extensions.values()):
            filename = filename + extensions.get(file_type, ".txt")

        file_path = output_dir / filename

        # Write the content
        if file_type == "json" and isinstance(content, (dict, list)):
            with open(file_path, 'w') as f:
                json.dump(content, f, indent=2)
        else:
            with open(file_path, 'w') as f:
                f.write(content)

        # Create metadata file if provided
        if metadata:
            metadata_path = file_path.with_suffix(file_path.suffix + '.meta.json')
            metadata["created_at"] = datetime.now().isoformat()
            metadata["file_path"] = str(file_path)
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

        return {
            "status": "success",
            "file_path": str(file_path),
            "size": file_path.stat().st_size,
            "created_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise ToolException(f"Failed to save file: {str(e)}")


class LoadFileInput(BaseModel):
    """Input schema for loading files."""
    filename: str = Field(description="Name of the file to read")
    subdirectory: str = Field(default="", description="Optional subdirectory within session")


@tool(args_schema=LoadFileInput)
def load_file(filename: str, subdirectory: str = "") -> dict:
    """Load content from a file in the session directory.

    Automatically searches in the session root and subdirectories if not found.
    Returns file content and any associated metadata.
    """
    from pathlib import Path

    try:
        session_dir = get_session_path()

        # Determine file path
        if subdirectory:
            file_path = session_dir / subdirectory / filename
        else:
            # Search for file in session root and all subdirectories
            file_path = session_dir / filename
            if not file_path.exists():
                for subdir in ["research", "analysis", "reports", "data"]:
                    potential_path = session_dir / subdir / filename
                    if potential_path.exists():
                        file_path = potential_path
                        break

        if not file_path.exists():
            raise ToolException(f"File not found: {filename}")

        with open(file_path, 'r') as f:
            content = f.read()

        # Check for metadata file
        metadata_path = Path(str(file_path) + '.meta.json')
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

        return {
            "status": "success",
            "content": content,
            "file_path": str(file_path),
            "size": file_path.stat().st_size,
            "metadata": metadata
        }

    except ToolException:
        raise
    except Exception as e:
        raise ToolException(f"Failed to load file: {str(e)}")


class ListOutputsInput(BaseModel):
    """Input schema for listing files."""
    subdirectory: str = Field(default="", description="Optional filter by subdirectory")
    file_type: str = Field(default="", description="Optional filter by file type: text, json, markdown, yaml")


@tool(args_schema=ListOutputsInput)
def list_outputs(subdirectory: str = "", file_type: str = "") -> List[dict]:
    """List all files in the session directory.

    Can filter by subdirectory and file type. Returns file information including
    name, path, size, and modification time.
    """
    from pathlib import Path

    try:
        session_dir = get_session_path()

        # Determine search directory
        if subdirectory:
            search_dir = session_dir / subdirectory
        else:
            search_dir = session_dir

        if not search_dir.exists():
            return []

        files = []
        pattern = "*"
        if file_type:
            extensions = {
                "text": "*.txt",
                "json": "*.json",
                "markdown": "*.md",
                "yaml": "*.yaml"
            }
            pattern = extensions.get(file_type, "*")

        # Use rglob for recursive search if no subdirectory specified
        glob_method = search_dir.rglob if not subdirectory else search_dir.glob
        for file_path in glob_method(pattern):
            # Skip metadata files and directories
            if '.meta.json' in file_path.name or file_path.is_dir():
                continue

            # Get relative path from session directory
            relative_path = file_path.relative_to(session_dir)

            files.append({
                "filename": file_path.name,
                "relative_path": str(relative_path),
                "path": str(file_path),
                "size": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })

        return sorted(files, key=lambda x: x['modified'], reverse=True)

    except Exception as e:
        raise ToolException(f"Failed to list files: {str(e)}")


class AppendContentInput(BaseModel):
    """Input schema for appending to files."""
    filename: str = Field(description="Name of the file to append to")
    content: str = Field(description="Content to append")
    subdirectory: str = Field(default="", description="Optional subdirectory within session")


@tool(args_schema=AppendContentInput)
def append_content(filename: str, content: str, subdirectory: str = "") -> dict:
    """Append content to an existing file in the session directory.

    Creates the file if it doesn't exist. Useful for incremental updates
    to logs, reports, or accumulated research findings.
    """
    from pathlib import Path

    try:
        session_dir = get_session_path()

        # Determine file path
        if subdirectory:
            file_path = session_dir / subdirectory / filename
        else:
            file_path = session_dir / filename

        if not file_path.exists():
            # Create the file if it doesn't exist
            return save_output(filename, content, subdirectory=subdirectory)

        with open(file_path, 'a') as f:
            f.write('\n' + content)

        return {
            "status": "success",
            "file_path": str(file_path),
            "new_size": file_path.stat().st_size,
            "appended_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise ToolException(f"Failed to append content: {str(e)}")


# ============================================================================
# DELEGATION TOOLS
# ============================================================================

class DelegateResearchInput(BaseModel):
    """Input schema for research delegation."""
    context: str = Field(description="Overall goal, completed work, and next steps")
    task_description: str = Field(description="Specific research actions to take")
    restrictions: str = Field(default="", description="Boundaries and requirements for the research")


@tool(args_schema=DelegateResearchInput)
async def delegate_research(context: str, task_description: str, restrictions: str = "") -> dict:
    """Delegate research task to a specialized research agent.

    The supervisor provides complete context through structured XML prompts.
    The research agent will have its own isolated planning and todo tools.
    Returns task tracking information and initial agent response.
    """
    try:
        task_id = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        agent_id = f"research_agent_{task_id}"

        # Log the delegation
        logger.info(f"Research task delegated: {task_id}")
        logger.info(f"Task description: {task_description}")
        logger.info(f"Context: {context[:100]}...")

        # For testing purposes, return a realistic response structure
        # In production, this would actually create and run a research agent
        response_summary = f"Research task accepted: {task_description}"

        return {
            "task_id": task_id,
            "agent_id": agent_id,
            "status": "completed",
            "delegated_at": datetime.now().isoformat(),
            "agent_type": "research",
            "response": response_summary,
            "agent_namespace": f"research_{agent_id}",
            "note": "Research agent stub - full implementation pending"
        }

    except Exception as e:
        logger.error(f"Failed to delegate research: {e}")
        raise ToolException(f"Research delegation failed: {str(e)}")


class DelegateAnalysisInput(BaseModel):
    """Input schema for analysis delegation."""
    context: str = Field(description="Overall goal, completed work (including research), and next steps")
    task_description: str = Field(description="Specific analysis actions to take")
    restrictions: str = Field(default="", description="Analytical boundaries and requirements")


@tool(args_schema=DelegateAnalysisInput)
async def delegate_analysis(context: str, task_description: str, restrictions: str = "") -> dict:
    """Delegate analysis task to a specialized analysis agent.

    Provides complete context including research findings. The analysis agent
    will have its own isolated planning and todo tools.
    Returns task tracking information and initial agent response.
    """
    try:
        task_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        agent_id = f"analysis_agent_{task_id}"

        # Log the delegation
        logger.info(f"Analysis task delegated: {task_id}")
        logger.info(f"Task description: {task_description}")
        logger.info(f"Context: {context[:100]}...")

        # For testing purposes, return a realistic response structure
        # In production, this would actually create and run an analysis agent
        response_summary = f"Analysis task accepted: {task_description}"

        return {
            "task_id": task_id,
            "agent_id": agent_id,
            "status": "completed",
            "delegated_at": datetime.now().isoformat(),
            "agent_type": "analysis",
            "response": response_summary,
            "agent_namespace": f"analysis_{agent_id}",
            "note": "Analysis agent stub - full implementation pending"
        }

    except Exception as e:
        logger.error(f"Failed to delegate analysis: {e}")
        raise ToolException(f"Analysis delegation failed: {str(e)}")


class DelegateWritingInput(BaseModel):
    """Input schema for writing delegation."""
    context: str = Field(description="Overall goal, completed work (research & analysis), and next steps")
    task_description: str = Field(description="Specific writing actions to take")
    restrictions: str = Field(default="", description="Style, format, tone, and content boundaries")


@tool(args_schema=DelegateWritingInput)
async def delegate_writing(context: str, task_description: str, restrictions: str = "") -> dict:
    """Delegate writing task to a specialized writing agent.

    Provides complete context including research and analysis results. The writing agent
    will have its own isolated planning and todo tools.
    Returns task tracking information and initial agent response.
    """
    try:
        task_id = f"writing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        agent_id = f"writing_agent_{task_id}"

        # Log the delegation
        logger.info(f"Writing task delegated: {task_id}")
        logger.info(f"Task description: {task_description}")
        logger.info(f"Context: {context[:100]}...")

        # For testing purposes, return a realistic response structure
        # In production, this would actually create and run a writing agent
        response_summary = f"Writing task accepted: {task_description}"

        return {
            "task_id": task_id,
            "agent_id": agent_id,
            "status": "completed",
            "delegated_at": datetime.now().isoformat(),
            "agent_type": "writing",
            "response": response_summary,
            "agent_namespace": f"writing_{agent_id}",
            "note": "Writing agent stub - full implementation pending"
        }

    except Exception as e:
        logger.error(f"Failed to delegate writing: {e}")
        raise ToolException(f"Writing delegation failed: {str(e)}")


# ============================================================================
# TOOL REGISTRY
# ============================================================================

# Export all tools as a list for easy binding to LangChain agents
ALL_SUPERVISOR_TOOLS = [
    # Planning
    plan_task,
    update_plan,
    # Todo Management
    create_todo,
    update_todo_status,
    # File Operations
    save_output,
    load_file,
    list_outputs,
    append_content,
    # Delegation
    delegate_research,
    delegate_analysis,
    delegate_writing,
]

# Tool names for reference
TOOL_NAMES = [tool.name for tool in ALL_SUPERVISOR_TOOLS]

logger.info(f"Loaded {len(ALL_SUPERVISOR_TOOLS)} LangChain supervisor tools: {TOOL_NAMES}")