"""
Reviewer agent tools for validating sub-agent submissions.

The reviewer is a LangChain ReAct agent with 3 explicit tools:
1. read_file: Deep Agents built-in tool (passed explicitly to reviewer agent)
2. reject_submission: Custom tool for rejection with specific feedback
3. accept_submission: Custom tool for acceptance and supervisor notification

All imports are ABSOLUTE.
"""

from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from typing import Annotated
from langchain.tools.tool_node import InjectedState


@tool
def reject_submission(
    feedback: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Reject the submission and provide specific feedback to the sub-agent.

    Use this tool when the output FAILS one or more universal standards:
    - Accuracy: Incorrect information, wrong numbers, false claims
    - Completeness: Missing required elements, skipped steps from plan
    - Quality: Placeholders like "[X]%" or "TBD", poor formatting
    - Citations: Missing sources (when applicable)

    The feedback you provide will be sent back to the sub-agent so they can fix
    issues and resubmit.

    Args:
        feedback: Detailed explanation of what failed and how to fix it

    Returns:
        Command updating state with rejection and feedback

    Example:
        reject_submission(
            feedback="REJECTED - Quality Standard Failed\n\n"
                    "Issue: Output contains placeholder '[X]%' instead of actual percentage.\n\n"
                    "The task was to find the S&P 500 return, but the output shows '[X]%' "
                    "which is a template/placeholder, not the actual data.\n\n"
                    "Required Fix:\n"
                    "- Find the actual S&P 500 percentage return\n"
                    "- Replace '[X]%' with the real number (e.g., '4.2%')\n"
                    "- Ensure ALL data is actual values, not placeholders\n\n"
                    "Then resubmit."
        )

    IMPORTANT - Structure your feedback clearly:
    1. State which standard(s) failed
    2. Explain the specific issue
    3. Provide actionable steps to fix
    """
    # Keep todos in "in_progress" status (sub-agent continues working)
    # No modification needed - todos remain as-is
    todos = state.get("todos", [])

    return Command(
        update={
            "review_status": "REJECTED",
            "review_feedback": feedback,
            "todos": todos,  # Propagate todos (keeps in_progress status)
            "messages": [
                ToolMessage(
                    content=f"❌ SUBMISSION REJECTED\n\n{feedback}",
                    tool_call_id=tool_call_id
                )
            ]
        }
    )


@tool
def accept_submission(
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Accept the submission and notify the supervisor that the task is complete.

    Use this tool when the output PASSES all universal standards:
    - ✅ Accuracy: Information is correct and factual
    - ✅ Completeness: All required elements included, plan steps followed
    - ✅ Quality: Professional output, no placeholders, proper formatting
    - ✅ Citations: Sources provided (when applicable)

    Returns:
        Command updating state with acceptance

    Example:
        accept_submission()

    IMPORTANT:
    - Only call this if ALL standards pass
    - If even one standard fails, use reject_submission instead
    """
    # Mark the last todo as "completed" (following Option 2 architecture)
    todos = state.get("todos", [])
    if todos:
        todos[-1]["status"] = "completed"

    return Command(
        update={
            "review_status": "ACCEPTED",
            "todos": todos,  # Propagate updated todos
            "messages": [
                ToolMessage(
                    content="✅ SUBMISSION ACCEPTED - Task complete, supervisor notified",
                    tool_call_id=tool_call_id
                )
            ]
        }
    )
