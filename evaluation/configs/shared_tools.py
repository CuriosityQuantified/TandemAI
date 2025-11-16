"""
Shared Tools for Test Configurations

Contains ALL tools from the main system that should be available to
all test configurations, including:
- Planning tools (create_research_plan, edit_plan, etc.)
- Research tools (tavily_search)
- File operation tools (read_file, write_file, edit_file)
- Delegation tools (specific to each config, but created from templates here)
"""

import os
import json
from typing import Literal
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from pydantic import BaseModel, Field


# ============================================================================
# FILE OPERATION TOOLS
# ============================================================================

class ReadFileInput(BaseModel):
    """Input for read_file tool."""
    file_path: str = Field(description="Path to the file to read")


class WriteFileInput(BaseModel):
    """Input for write_file tool."""
    file_path: str = Field(description="Path to the file to write")
    content: str = Field(description="Content to write to the file")


class EditFileInput(BaseModel):
    """Input for edit_file tool."""
    file_path: str = Field(description="Path to the file to edit")
    old_content: str = Field(description="Content to replace")
    new_content: str = Field(description="New content")


@tool("read_file", args_schema=ReadFileInput)
def read_file_tool(file_path: str) -> str:
    """Read contents of a file."""
    try:
        workspace_path = Path("/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2/module-2-2-frontend-enhanced/backend/workspace")
        full_path = workspace_path / file_path

        with open(full_path, 'r') as f:
            content = f.read()

        return f"✅ File read successfully:\n{content}"
    except Exception as e:
        return f"❌ Error reading file: {str(e)}"


@tool("write_file", args_schema=WriteFileInput)
def write_file_tool(file_path: str, content: str) -> str:
    """Write content to a file."""
    try:
        workspace_path = Path("/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2/module-2-2-frontend-enhanced/backend/workspace")
        full_path = workspace_path / file_path

        # Create directory if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, 'w') as f:
            f.write(content)

        return f"✅ File written successfully: {file_path}"
    except Exception as e:
        return f"❌ Error writing file: {str(e)}"


@tool("edit_file", args_schema=EditFileInput)
def edit_file_tool(file_path: str, old_content: str, new_content: str) -> str:
    """Edit a file by replacing old_content with new_content."""
    try:
        workspace_path = Path("/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2/module-2-2-frontend-enhanced/backend/workspace")
        full_path = workspace_path / file_path

        with open(full_path, 'r') as f:
            content = f.read()

        if old_content not in content:
            return f"❌ Old content not found in file"

        new_file_content = content.replace(old_content, new_content)

        with open(full_path, 'w') as f:
            f.write(new_file_content)

        return f"✅ File edited successfully: {file_path}"
    except Exception as e:
        return f"❌ Error editing file: {str(e)}"


# ============================================================================
# PLANNING TOOLS
# ============================================================================

class CreatePlanInput(BaseModel):
    """Input for create_research_plan tool."""
    query: str = Field(description="Research question or topic to plan for")
    num_steps: int = Field(default=5, description="Number of steps (3-10)")


class UpdatePlanInput(BaseModel):
    """Input for update_plan_progress tool."""
    step_index: int = Field(description="Index of the step to update (0-based)")
    result: str = Field(description="Result or findings from this step")


class EditPlanInput(BaseModel):
    """Input for edit_plan tool."""
    step_index: int = Field(description="Index of step to edit (0-based)")
    new_description: str = Field(description="New step description")
    new_action: str = Field(description="New action for this step")


@tool("create_research_plan", args_schema=CreatePlanInput)
def create_research_plan_tool(query: str, num_steps: int = 5) -> str:
    """
    Create a structured research plan for a query.

    This tool generates a step-by-step research plan with 3-10 actionable steps.
    The plan is stored and can be referenced by other tools.

    PROMPT ENGINEERING BEST PRACTICES for 'query' parameter:

    To ensure high-quality, focused research, structure your query with:

    1. **Context**: Background information about why this research is needed
       Example: "For enterprise adoption report on quantum computing..."

    2. **Goal**: Clear statement of what successful completion looks like
       Example: "...identify top 3 error correction techniques by fidelity rate"

    3. **Focus Areas**: Specific aspects to research (if multi-faceted)
       Example: "Focus on: 1) fidelity benchmarks, 2) scalability, 3) vendor adoption"

    4. **Constraints**: Time periods, geographic focus, source preferences
       Example: "2024-2025 data, prioritize Nature/Science/IEEE journals"

    5. **Success Criteria**: What makes each step sufficient
       Example: "3+ peer-reviewed sources per topic, quantitative data required"

    GOOD query example:
    "Research quantum error correction for superconducting qubits (2024-2025).
    Context: Enterprise adoption readiness report. Goal: Identify top 3 techniques
    by fidelity. Focus: 1) benchmarks, 2) scalability challenges, 3) commercial use.
    Success: 3+ academic sources per area, quantitative fidelity data.
    Prioritize Nature/Science/IEEE and industry leaders (IBM/Google)."

    BAD query example (too vague):
    "quantum computing"

    Higher quality queries → More focused steps → Better research results
    """
    try:
        if num_steps < 3 or num_steps > 10:
            return "❌ Number of steps must be between 3 and 10"

        # Create workspace/.plans directory
        plans_dir = Path("/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2/module-2-2-frontend-enhanced/backend/workspace/.plans")
        plans_dir.mkdir(parents=True, exist_ok=True)

        # Generate plan
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        plan = {
            "plan_id": plan_id,
            "query": query,
            "created_at": datetime.now().isoformat(),
            "num_steps": num_steps,
            "steps": [
                {
                    "step_index": i,
                    "description": f"Step {i+1}: Research aspect {i+1} of {query}",
                    "action": f"tavily_search for topic {i+1}",
                    "status": "pending",
                    "result": None
                }
                for i in range(num_steps)
            ]
        }

        # Save plan
        plan_file = plans_dir / f"{plan_id}.json"
        with open(plan_file, 'w') as f:
            json.dump(plan, f, indent=2)

        # Save as current plan
        current_plan_file = plans_dir / "current_plan.json"
        with open(current_plan_file, 'w') as f:
            json.dump(plan, f, indent=2)

        return f"✅ Research plan created with {num_steps} steps:\n{json.dumps(plan, indent=2)}"

    except Exception as e:
        return f"❌ Error creating plan: {str(e)}"


@tool("update_plan_progress")
def update_plan_progress_tool(step_index: int, result: str) -> str:
    """Update the progress of a specific step in the current plan."""
    try:
        plans_dir = Path("/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2/module-2-2-frontend-enhanced/backend/workspace/.plans")
        current_plan_file = plans_dir / "current_plan.json"

        if not current_plan_file.exists():
            return "❌ No current plan found. Create a plan first."

        with open(current_plan_file, 'r') as f:
            plan = json.load(f)

        if step_index < 0 or step_index >= len(plan["steps"]):
            return f"❌ Invalid step index. Must be 0-{len(plan['steps'])-1}"

        plan["steps"][step_index]["status"] = "completed"
        plan["steps"][step_index]["result"] = result
        plan["steps"][step_index]["completed_at"] = datetime.now().isoformat()

        with open(current_plan_file, 'w') as f:
            json.dump(plan, f, indent=2)

        return f"✅ Step {step_index} updated: {result[:100]}..."

    except Exception as e:
        return f"❌ Error updating plan: {str(e)}"


@tool("read_current_plan")
def read_current_plan_tool() -> str:
    """Read the current active research plan."""
    try:
        plans_dir = Path("/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2/module-2-2-frontend-enhanced/backend/workspace/.plans")
        current_plan_file = plans_dir / "current_plan.json"

        if not current_plan_file.exists():
            return "❌ No current plan found."

        with open(current_plan_file, 'r') as f:
            plan = json.load(f)

        return f"✅ Current plan:\n{json.dumps(plan, indent=2)}"

    except Exception as e:
        return f"❌ Error reading plan: {str(e)}"


@tool("edit_plan", args_schema=EditPlanInput)
def edit_plan_tool(step_index: int, new_description: str, new_action: str) -> str:
    """Edit a step in the current research plan."""
    try:
        plans_dir = Path("/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2/module-2-2-frontend-enhanced/backend/workspace/.plans")
        current_plan_file = plans_dir / "current_plan.json"

        if not current_plan_file.exists():
            return "❌ No current plan found."

        with open(current_plan_file, 'r') as f:
            plan = json.load(f)

        if step_index < 0 or step_index >= len(plan["steps"]):
            return f"❌ Invalid step index."

        plan["steps"][step_index]["description"] = new_description
        plan["steps"][step_index]["action"] = new_action
        plan["steps"][step_index]["edited_at"] = datetime.now().isoformat()

        with open(current_plan_file, 'w') as f:
            json.dump(plan, f, indent=2)

        return f"✅ Step {step_index} edited successfully"

    except Exception as e:
        return f"❌ Error editing plan: {str(e)}"


# ============================================================================
# RESEARCH TOOLS
# ============================================================================

@tool
def search_web(query: str) -> str:
    """
    Search the web for information.

    Mock implementation for testing - returns simulated search results.
    In production, this would use Tavily or similar search API.
    """
    return f"Search results for '{query}': [Mock Result 1], [Mock Result 2], [Mock Result 3]"


def get_tavily_search_tool():
    """
    Get the Tavily search tool if available.

    Returns:
        TavilySearch tool or None if not available
    """
    try:
        from langchain_tavily import TavilySearch
        return TavilySearch(max_results=5)
    except Exception as e:
        print(f"⚠️  Tavily not available: {e}")
        return None


# ============================================================================
# DELEGATION TOOL TEMPLATES
# ============================================================================

def create_delegation_tool(
    agent_name: str,
    agent_description: str,
    target_node: str
):
    """
    Factory function to create delegation tools with Command.goto routing.

    Args:
        agent_name: Name of the agent (e.g., "researcher")
        agent_description: Description of agent's capabilities
        target_node: Target node name in the graph

    Returns:
        A tool function that returns Command(goto=target_node)

    IMPORTANT: The delegation tool does NOT return a Command directly.
    Instead, it returns a success message as a string, and the Command
    routing logic is handled in the delegation_router node that wraps
    the ToolNode. This is the correct LangGraph v1.0+ pattern.
    """

    # Create a function with proper docstring
    def delegation_tool(task: str) -> str:
        """Delegate task to the specialized agent."""
        print(f"\n🔧 delegate_to_{agent_name} called")
        print(f"   Task: {task[:100]}...")
        print(f"   Will route to: {target_node}\n")

        # Return simple string - ToolNode will create proper ToolMessage
        return f"✅ Task delegated to {agent_name}: {task[:100]}..."

    # Decorate it as a tool with proper description
    tool_name = f"delegate_to_{agent_name}"
    tool_description = f"Delegate a task to the {agent_name} agent. {agent_description}"

    return tool(tool_name, description=tool_description)(delegation_tool)


# ============================================================================
# TOOL COLLECTIONS
# ============================================================================

# File operation tools
FILE_TOOLS = [
    read_file_tool,
    write_file_tool,
    edit_file_tool
]

# Planning tools
PLANNING_TOOLS = [
    create_research_plan_tool,
    update_plan_progress_tool,
    read_current_plan_tool,
    edit_plan_tool
]

# Research tools - includes Tavily if available
_tavily_tool = get_tavily_search_tool()
RESEARCH_TOOLS = [_tavily_tool] if _tavily_tool else [search_web]

# All tools for supervisor (delegation + planning + research + files)
def get_supervisor_tools(delegation_tools: list) -> list:
    """Get all tools for supervisor agent."""
    return delegation_tools + PLANNING_TOOLS + RESEARCH_TOOLS + FILE_TOOLS


# All tools for subagents (planning + research + files, NO delegation)
def get_subagent_tools() -> list:
    """Get all tools for subagent (no delegation tools)."""
    return PLANNING_TOOLS + RESEARCH_TOOLS + FILE_TOOLS


if __name__ == "__main__":
    print("✅ Shared tools module loaded")
    print(f"   File tools: {len(FILE_TOOLS)}")
    print(f"   Planning tools: {len(PLANNING_TOOLS)}")
    print(f"   Research tools: {len(RESEARCH_TOOLS)}")
    print(f"   Total tools available: {len(FILE_TOOLS + PLANNING_TOOLS + RESEARCH_TOOLS)}")
