"""
Delegation Tools for Deep Subagent System

This module provides tools for the main research agent to delegate specialized
tasks to subagents. Each delegation function creates a hierarchical thread ID,
executes the subagent, and broadcasts WebSocket events for real-time UI updates.

Created: November 7, 2025
Part of: Phase 1b - Deep Subagent Delegation System
"""

from typing import Optional, Annotated, Literal
from pydantic import BaseModel, Field
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from datetime import datetime
import uuid

# Import subagent creators (updated for reorganization - uses backend. prefix)
from backend.subagents import (
    create_researcher_subagent,
    create_data_scientist_subagent,
    create_expert_analyst_subagent,
    create_writer_subagent,
    create_reviewer_subagent,
)

# Workspace configuration imported lazily to avoid circular import
# from module_2_2_simple import get_workspace_dir  # Moved to function-level imports

# Import WebSocket manager for broadcasting (updated for reorganization - uses backend. prefix)
from backend.websocket_manager import manager


# ============================================================================
# PYDANTIC INPUT SCHEMA (UNIFIED)
# ============================================================================

class DelegationInput(BaseModel):
    """
    Unified input schema for all delegation tools.

    The task field should contain a complete, well-crafted prompt for the subagent
    following prompt engineering best practices. Include all context, requirements,
    constraints, output specifications, and success criteria in this single field.
    """

    task: str = Field(
        ...,
        description=(
            "Complete task description for the subagent. This should be a well-crafted prompt that includes:\n"
            "- Clear objective and context\n"
            "- All necessary requirements and constraints\n"
            "- Output file location (e.g., '/workspace/report.md')\n"
            "- Expected format and structure\n"
            "- Any relevant examples or references\n"
            "\n"
            "Example: 'Research the latest trends in quantum computing for 2025. Focus on practical business "
            "applications, not theoretical physics. Search for sources from Q4 2024 onwards. Create a structured "
            "report with: (1) Executive Summary, (2) Key Trends (3-5 bullet points each), (3) Business Impact "
            "Analysis, (4) Sources (numbered citations). Save to /workspace/quantum_trends_2025.md'"
        )
    )

    # Injected parameter - must be declared in schema with default=None for injection to work
    tool_call_id: Annotated[str, InjectedToolCallId] = Field(
        default=None,
        description="Tool call ID automatically injected by LangGraph for ToolMessage matching"
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_subagent_thread_id(parent_thread_id: str, subagent_type: str) -> str:
    """
    Generate hierarchical thread ID for subagent execution.

    Format: {parent_thread_id}/subagent-{type}-{uuid}
    Example: thread-abc123/subagent-researcher-xyz789

    Args:
        parent_thread_id: Thread ID of the main agent
        subagent_type: Type of subagent (e.g., 'researcher', 'data_scientist')

    Returns:
        Hierarchical thread ID for the subagent
    """
    subagent_uuid = str(uuid.uuid4())[:8]
    return f"{parent_thread_id}/subagent-{subagent_type}-{subagent_uuid}"


async def broadcast_subagent_event(
    thread_id: str,
    event_type: str,
    subagent_type: str,
    data: dict
):
    """
    Broadcast subagent lifecycle event via WebSocket.

    Event Types:
        - subagent_started: Subagent execution began
        - subagent_completed: Subagent finished successfully
        - subagent_error: Subagent encountered an error

    Args:
        thread_id: Main agent thread ID
        event_type: Type of event (started/completed/error)
        subagent_type: Type of subagent
        data: Event-specific data (task, output_file, error, etc.)
    """
    event = {
        "type": event_type,
        "thread_id": thread_id,
        "subagent_type": subagent_type,
        "timestamp": datetime.now().isoformat(),
        **data
    }
    await manager.broadcast(event)


# ============================================================================
# DELEGATION TOOL IMPLEMENTATIONS
# ============================================================================

@tool("delegate_to_researcher", args_schema=DelegationInput)
async def delegate_to_researcher(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command[Literal["researcher_agent"]]:
    """
    Delegate a research task to the Researcher subagent.

    The Researcher specializes in:
    - Web research using Tavily search
    - Synthesizing information from multiple sources
    - Creating well-cited documents with [1] [2] [3] format
    - Producing comprehensive research reports

    Args:
        task: Complete task description including research question, output file,
              and all requirements. Should follow prompt engineering best practices.
        tool_call_id: Tool call ID injected by LangGraph for matching tool_use/tool_result

    Returns:
        Command object with ToolMessage for proper tool_use/tool_result pairing

    Example:
        >>> delegate_to_researcher(
        ...     task="Research the latest trends in AI agents focusing on 2025 developments. "
        ...          "Search for sources from Q4 2024 onwards. Create a structured report with: "
        ...          "(1) Executive Summary, (2) Key Trends (3-5 bullet points each), "
        ...          "(3) Business Impact Analysis, (4) Sources (numbered citations). "
        ...          "Save to /workspace/ai_trends_2025.md"
        ... )
        Command(update={"messages": [ToolMessage(...)]})
    """
    try:
        # Generate simple thread ID (not hierarchical for now)
        # TODO: Pass parent thread_id via RunnableConfig once deepagents supports it
        thread_id = None  # Will be None for now

        # Generate hierarchical thread ID
        subagent_thread_id = generate_subagent_thread_id(thread_id, "researcher")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Generated researcher thread ID: {subagent_thread_id}")

        # Broadcast start event
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Broadcasting researcher start event...")
        await broadcast_subagent_event(
            thread_id=thread_id,
            event_type="subagent_started",
            subagent_type="researcher",
            data={
                "task": task[:200] + "..." if len(task) > 200 else task,  # Truncate for broadcast
                "subagent_thread_id": subagent_thread_id
            }
        )
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Researcher start event broadcast complete")

        # Use Command.goto to route directly to researcher_agent node
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Routing to researcher_agent node via Command.goto")

        # Broadcast completion event (immediate since we're just routing)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Broadcasting researcher routing event...")
        await broadcast_subagent_event(
            thread_id=thread_id,
            event_type="subagent_completed",
            subagent_type="researcher",
            data={
                "task": task[:200] + "..." if len(task) > 200 else task,
                "subagent_thread_id": subagent_thread_id,
                "success": True,
                "routing": "Command.goto to researcher_agent"
            }
        )

        # Return Command with goto routing to researcher_agent node
        import logging
        logger = logging.getLogger(__name__)

        command = Command(
            goto="researcher_agent",  # Direct routing to subagent node
            update={
                "messages": [
                    ToolMessage(
                        content=f"✅ Routing to researcher subagent: {task[:100]}...",
                        tool_call_id=tool_call_id,
                        name="delegate_to_researcher"
                    )
                ],
                "parent_thread_id": thread_id,  # Pass parent thread for event emission
                "subagent_thread_id": subagent_thread_id,  # Pass subagent thread for event emission
                "subagent_type": "researcher",  # Pass subagent type for event emission
            }
        )

        logger.debug(f"🎯 delegate_to_researcher returning Command(goto={command.goto})")
        logger.debug(f"   Update keys: {list(command.update.keys())}")
        logger.debug(f"   Parent thread: {thread_id}")
        logger.debug(f"   Subagent thread: {subagent_thread_id}")

        return command

    except Exception as e:
        # Broadcast error event
        await broadcast_subagent_event(
            thread_id=thread_id,
            event_type="subagent_error",
            subagent_type="researcher",
            data={
                "task": task[:200] + "..." if len(task) > 200 else task,
                "error": str(e),
                "subagent_thread_id": subagent_thread_id if 'subagent_thread_id' in locals() else None
            }
        )

        # Return Command with error ToolMessage
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"❌ Researcher failed: {str(e)}",
                        tool_call_id=tool_call_id,
                        name="delegate_to_researcher",
                        status="error"
                    )
                ]
            }
        )



@tool("delegate_to_data_scientist", args_schema=DelegationInput)
async def delegate_to_data_scientist(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    thread_id: Optional[str] = None,
    checkpointer=None
) -> Command[Literal["data_scientist_agent"]]:
    """
    Delegate a data analysis task to the Data Scientist subagent.

    The Data Scientist specializes in:
    - Statistical analysis and data interpretation
    - Creating visualizations and charts
    - Identifying patterns and trends in data
    - Producing analysis reports with findings and insights

    Args:
        task: Complete task description including analysis objective, data location,
              output file, and all requirements. Should follow prompt engineering best practices.
        tool_call_id: Injected by LangGraph to match tool_use with tool_result
        thread_id: Parent thread ID for hierarchical execution
        checkpointer: Memory checkpointer for conversation history

    Returns:
        Command object with ToolMessage for proper tool_use/tool_result pairing

    Example:
        >>> delegate_to_data_scientist(
        ...     task="Analyze Q4 2025 sales trends focusing on regional performance. "
        ...          "Data is in /workspace/sales_q4_2025.csv. Perform descriptive analysis "
        ...          "with focus on top 5 regions and YoY comparison. Create visualizations "
        ...          "for trends and patterns. Structure report with: (1) Executive Summary, "
        ...          "(2) Regional Analysis (3-5 regions), (3) Year-over-Year Trends, "
        ...          "(4) Key Insights and Recommendations. Save to /workspace/q4_sales_analysis.md"
        ... )
        "✅ Data Scientist completed: Task executed successfully"
    """
    try:
        # Generate hierarchical thread ID
        subagent_thread_id = generate_subagent_thread_id(thread_id, "data_scientist")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Generated data_scientist thread ID: {subagent_thread_id}")

        # Broadcast start event
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Broadcasting data_scientist start event...")
        await broadcast_subagent_event(
            thread_id=thread_id,
            event_type="subagent_started",
            subagent_type="data_scientist",
            data={
                "task": task[:200] + "..." if len(task) > 200 else task,  # Truncate for broadcast
                "subagent_thread_id": subagent_thread_id
            }
        )
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Data_scientist start event broadcast complete")

        # Use Command.goto to route directly to data_scientist_agent node
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Routing to data_scientist_agent node via Command.goto")

        # Broadcast completion event (immediate since we're just routing)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Broadcasting data_scientist routing event...")
        await broadcast_subagent_event(
            thread_id=thread_id,
            event_type="subagent_completed",
            subagent_type="data_scientist",
            data={
                "task": task[:200] + "..." if len(task) > 200 else task,
                "subagent_thread_id": subagent_thread_id,
                "success": True,
                "routing": "Command.goto to data_scientist_agent"
            }
        )

        # Return Command with goto routing to data_scientist_agent node
        return Command(
            goto="data_scientist_agent",  # Direct routing to subagent node
            update={
                "messages": [
                    ToolMessage(
                        content=f"✅ Routing to data scientist subagent: {task[:100]}...",
                        tool_call_id=tool_call_id,
                        name="delegate_to_data_scientist"
                    )
                ]
            }
        )

    except Exception as e:
        # Broadcast error event
        await broadcast_subagent_event(
            thread_id=thread_id,
            event_type="subagent_error",
            subagent_type="data_scientist",
            data={
                "task": task[:200] + "..." if len(task) > 200 else task,
                "error": str(e),
                "subagent_thread_id": subagent_thread_id if 'subagent_thread_id' in locals() else None
            }
        )

        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"❌ Data Scientist failed: {str(e)}",
                        tool_call_id=tool_call_id,
                        name="delegate_to_data_scientist",
                        status="error"
                    )
                ]
            }
        )


@tool("delegate_to_expert_analyst", args_schema=DelegationInput)
async def delegate_to_expert_analyst(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    thread_id: Optional[str] = None,
    checkpointer=None
) -> Command[Literal["expert_analyst_agent"]]:
    """
    Delegate a problem analysis task to the Expert Analyst subagent.

    The Expert Analyst specializes in:
    - Root cause analysis (5 Whys, Fishbone diagrams)
    - SWOT analysis and strategic thinking
    - Problem decomposition and structured analysis
    - Producing analytical reports with recommendations

    Args:
        task: Complete task description including problem statement, analysis framework,
              output file, and all requirements. Should follow prompt engineering best practices.
        tool_call_id: Injected by LangGraph to match tool_use with tool_result
        thread_id: Parent thread ID for hierarchical execution
        checkpointer: Memory checkpointer for conversation history

    Returns:
        Command object with ToolMessage for proper tool_use/tool_result pairing

    Example:
        >>> delegate_to_expert_analyst(
        ...     task="Analyze customer churn increased 20% in Q4 using 5 Whys framework. "
        ...          "Identify root causes and contributing factors. Provide structured analysis "
        ...          "with clear sections and actionable recommendations. Save results to "
        ...          "/workspace/churn_analysis.md"
        ... )
        "✅ Expert Analyst completed: Task executed successfully"
    """
    try:
        # Generate hierarchical thread ID
        subagent_thread_id = generate_subagent_thread_id(thread_id, "expert_analyst")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Generated expert_analyst thread ID: {subagent_thread_id}")

        # Broadcast start event
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Broadcasting expert_analyst start event...")
        await broadcast_subagent_event(
            thread_id=thread_id,
            event_type="subagent_started",
            subagent_type="expert_analyst",
            data={
                "task": task[:200] + "..." if len(task) > 200 else task,  # Truncate for broadcast
                "subagent_thread_id": subagent_thread_id
            }
        )
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Expert_analyst start event broadcast complete")

        # Use Command.goto to route directly to expert_analyst_agent node
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Routing to expert_analyst_agent node via Command.goto")

        # Broadcast completion event (immediate since we're just routing)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Broadcasting expert_analyst routing event...")
        await broadcast_subagent_event(
            thread_id=thread_id,
            event_type="subagent_completed",
            subagent_type="expert_analyst",
            data={
                "task": task[:200] + "..." if len(task) > 200 else task,
                "subagent_thread_id": subagent_thread_id,
                "success": True,
                "routing": "Command.goto to expert_analyst_agent"
            }
        )

        # Return Command with goto routing to expert_analyst_agent node
        return Command(
            goto="expert_analyst_agent",  # Direct routing to subagent node
            update={
                "messages": [
                    ToolMessage(
                        content=f"✅ Routing to expert analyst subagent: {task[:100]}...",
                        tool_call_id=tool_call_id,
                        name="delegate_to_expert_analyst"
                    )
                ]
            }
        )

    except Exception as e:
        # Broadcast error event
        await broadcast_subagent_event(
            thread_id=thread_id,
            event_type="subagent_error",
            subagent_type="expert_analyst",
            data={
                "task": task[:200] + "..." if len(task) > 200 else task,
                "error": str(e),
                "subagent_thread_id": subagent_thread_id if 'subagent_thread_id' in locals() else None
            }
        )

        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"❌ Expert Analyst failed: {str(e)}",
                        tool_call_id=tool_call_id,
                        name="delegate_to_expert_analyst",
                        status="error"
                    )
                ]
            }
        )


@tool("delegate_to_writer", args_schema=DelegationInput)
async def delegate_to_writer(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    thread_id: Optional[str] = None,
    checkpointer=None
) -> Command[Literal["writer_agent"]]:
    """
    Delegate a writing task to the Writer subagent.

    The Writer specializes in:
    - Creating professional documents and reports
    - Adapting tone and style for different audiences
    - Structuring content for clarity and impact
    - Producing polished, publication-ready content

    Args:
        task: Complete task description including writing requirements, output file,
              and all specifications. Should follow prompt engineering best practices.
        tool_call_id: Injected by LangGraph to match tool_use with tool_result
        thread_id: Parent thread ID for hierarchical execution
        checkpointer: Memory checkpointer for conversation history

    Returns:
        Command object with ToolMessage for proper tool_use/tool_result pairing

    Example:
        >>> delegate_to_writer(
        ...     task="Write a professional executive summary of Q4 2025 financial results. "
        ...          "Include: (1) Business Performance Summary, (2) Key Financial Metrics "
        ...          "(revenue, profit, margins), (3) Strategic Highlights, (4) Risk Factors. "
        ...          "Target audience: C-suite executives. Style: professional, concise. "
        ...          "Save to /workspace/q4_2025_executive_summary.md"
        ... )
        "✅ Writer completed: Task executed successfully"
    """
    try:
        # Generate hierarchical thread ID
        subagent_thread_id = generate_subagent_thread_id(thread_id, "writer")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Generated writer thread ID: {subagent_thread_id}")

        # Broadcast start event
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Broadcasting writer start event...")
        await broadcast_subagent_event(
            thread_id=thread_id,
            event_type="subagent_started",
            subagent_type="writer",
            data={
                "task": task[:200] + "..." if len(task) > 200 else task,  # Truncate for broadcast
                "subagent_thread_id": subagent_thread_id
            }
        )
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Writer start event broadcast complete")

        # Use Command.goto to route directly to writer_agent node
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Routing to writer_agent node via Command.goto")

        # Broadcast completion event (immediate since we're just routing)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Broadcasting writer routing event...")
        await broadcast_subagent_event(
            thread_id=thread_id,
            event_type="subagent_completed",
            subagent_type="writer",
            data={
                "task": task[:200] + "..." if len(task) > 200 else task,
                "subagent_thread_id": subagent_thread_id,
                "success": True,
                "routing": "Command.goto to writer_agent"
            }
        )

        # Return Command with goto routing to writer_agent node
        return Command(
            goto="writer_agent",  # Direct routing to subagent node
            update={
                "messages": [
                    ToolMessage(
                        content=f"✅ Routing to writer subagent: {task[:100]}...",
                        tool_call_id=tool_call_id,
                        name="delegate_to_writer"
                    )
                ]
            }
        )

    except Exception as e:
        # Broadcast error event
        await broadcast_subagent_event(
            thread_id=thread_id,
            event_type="subagent_error",
            subagent_type="writer",
            data={
                "task": task[:200] + "..." if len(task) > 200 else task,
                "error": str(e),
                "subagent_thread_id": subagent_thread_id if 'subagent_thread_id' in locals() else None
            }
        )

        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"❌ Writer failed: {str(e)}",
                        tool_call_id=tool_call_id,
                        name="delegate_to_writer",
                        status="error"
                    )
                ]
            }
        )


@tool("delegate_to_reviewer", args_schema=DelegationInput)
async def delegate_to_reviewer(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    thread_id: Optional[str] = None,
    checkpointer=None
) -> Command[Literal["reviewer_agent"]]:
    """
    Delegate a document review task to the Reviewer subagent.

    The Reviewer specializes in:
    - Quality assessment of documents
    - Identifying improvements in clarity, accuracy, and completeness
    - Providing constructive feedback and suggestions
    - Producing detailed review reports

    Args:
        task: Complete task description including document path, review criteria,
              output file, and all requirements. Should follow prompt engineering best practices.
        tool_call_id: Injected by LangGraph to match tool_use with tool_result
        thread_id: Parent thread ID for hierarchical execution
        checkpointer: Memory checkpointer for conversation history

    Returns:
        Command object with ToolMessage for proper tool_use/tool_result pairing

    Example:
        >>> delegate_to_reviewer(
        ...     task="Review the document at /workspace/ai_trends_2025.md. "
        ...          "Assess clarity, accuracy, and completeness. Focus on: (1) Is the executive summary clear "
        ...          "and comprehensive? (2) Are all claims supported by citations? (3) Is the structure logical? "
        ...          "(4) Are there any gaps or inconsistencies? Create a detailed review document with "
        ...          "specific, actionable feedback. Save to /workspace/ai_trends_review.md"
        ... )
        "✅ Reviewer completed: Task executed successfully"
    """
    try:
        # Generate hierarchical thread ID
        subagent_thread_id = generate_subagent_thread_id(thread_id, "reviewer")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Generated reviewer thread ID: {subagent_thread_id}")

        # Broadcast start event
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Broadcasting reviewer start event...")
        await broadcast_subagent_event(
            thread_id=thread_id,
            event_type="subagent_started",
            subagent_type="reviewer",
            data={
                "task": task[:200] + "..." if len(task) > 200 else task,  # Truncate for broadcast
                "subagent_thread_id": subagent_thread_id
            }
        )
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Reviewer start event broadcast complete")

        # Use Command.goto to route directly to reviewer_agent node
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Routing to reviewer_agent node via Command.goto")

        # Broadcast completion event (immediate since we're just routing)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [DELEGATION] Broadcasting reviewer routing event...")
        await broadcast_subagent_event(
            thread_id=thread_id,
            event_type="subagent_completed",
            subagent_type="reviewer",
            data={
                "task": task[:200] + "..." if len(task) > 200 else task,
                "subagent_thread_id": subagent_thread_id,
                "success": True,
                "routing": "Command.goto to reviewer_agent"
            }
        )

        # Return Command with goto routing to reviewer_agent node
        return Command(
            goto="reviewer_agent",  # Direct routing to subagent node
            update={
                "messages": [
                    ToolMessage(
                        content=f"✅ Routing to reviewer subagent: {task[:100]}...",
                        tool_call_id=tool_call_id,
                        name="delegate_to_reviewer"
                    )
                ]
            }
        )

    except Exception as e:
        # Broadcast error event
        await broadcast_subagent_event(
            thread_id=thread_id,
            event_type="subagent_error",
            subagent_type="reviewer",
            data={
                "task": task[:200] + "..." if len(task) > 200 else task,
                "error": str(e),
                "subagent_thread_id": subagent_thread_id if 'subagent_thread_id' in locals() else None
            }
        )

        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"❌ Reviewer failed: {str(e)}",
                        tool_call_id=tool_call_id,
                        name="delegate_to_reviewer",
                        status="error"
                    )
                ]
            }
        )
