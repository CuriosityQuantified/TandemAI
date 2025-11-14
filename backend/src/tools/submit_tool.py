"""
Submit tool for sub-agents to complete tasks with automatic review.

When a sub-agent calls submit(), it triggers the reviewer-agent to validate
the output with full context:
1. Supervisor's task delegation (provided by sub-agent)
2. Sub-agent's detailed plan (from write_todos)
3. Sub-agent's output file (provided by sub-agent)

The reviewer validates against universal standards:
- Accuracy: Is the information correct?
- Completeness: Is everything required included?
- Quality: Professional output, no placeholders?
- Citations: Sources provided (when applicable)?

All imports are ABSOLUTE.
"""

from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from typing import Annotated, Dict, Any
from langchain.tools.tool_node import InjectedState


# Store reviewer agent reference (set by supervisor during initialization)
_reviewer_agent = None


def set_reviewer_agent(agent):
    """Set the reviewer agent instance (called by supervisor during setup)"""
    global _reviewer_agent
    _reviewer_agent = agent


import logging

logger = logging.getLogger(__name__)


@tool
async def submit(
    supervisor_task: str,
    output_file: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Submit completed task for automatic review validation.

    When you have finished your task and saved output to a file, call this tool
    to submit your work. This triggers automatic review by the reviewer-agent.

    The reviewer receives full context:
    1. **Supervisor Task**: What the supervisor delegated to you (you provide this)
    2. **Your Plan**: Your detailed write_todos steps
    3. **Your Output**: The file you created (you provide this)

    The reviewer validates against universal standards:
    - **Accuracy**: Is the information correct and factual?
    - **Completeness**: Is everything required included?
    - **Quality**: Professional output, no placeholders like "[X]%" or "TBD"?
    - **Citations**: Sources provided (when applicable)?

    Review outcomes:
    - **ACCEPTED**: Supervisor is notified, task marked complete
    - **REJECTED**: You receive specific feedback to fix issues, then resubmit

    Args:
        supervisor_task: The task the supervisor delegated to you (copy from your task description)
        output_file: Path to your completed work (e.g., "/workspace/results.txt")

    Returns:
        Command updating state with review submission

    Example:
        submit(
            supervisor_task="Find AI-related news from today",
            output_file="/workspace/ai_news_today.txt"
        )

    WHEN TO USE:
    - After you've completed ALL steps in your plan
    - After you've saved output to the specified file
    - After you've verified your output meets requirements

    DO NOT call submit until your work is completely done!

    WHAT HAPPENS NEXT:
    1. Reviewer reads your output file
    2. Reviewer checks: Accuracy, Completeness, Quality, Citations
    3. Reviewer verifies alignment with supervisor task
    4. You receive either:
       - ✅ ACCEPTED: Task complete, supervisor notified
       - ❌ REJECTED: Specific feedback, fix issues and resubmit
    """

    logger.info(f"🔔 SUBMIT CALLED: task='{supervisor_task[:50]}...', file='{output_file}'")

    # CRITICAL PRE-SUBMISSION VALIDATION: Check if output file exists
    files = state.get("files", {})
    if output_file not in files:
        logger.error(f"❌ VALIDATION FAILED: Output file '{output_file}' does not exist")
        logger.error(f"   Available files: {list(files.keys())}")
        logger.error(f"   This error usually means write_file() was never called")

        # Return immediate rejection without invoking reviewer
        error_message = f"""❌ SUBMISSION REJECTED - File Does Not Exist

CRITICAL ERROR: You called submit() but the output file doesn't exist.

Output file specified: {output_file}
Files in filesystem: {list(files.keys()) if files else '(none)'}

Common Cause:
You marked the "save file" todo as [completed] WITHOUT actually calling write_file().

Required Fix:
1. Call write_file(path="{output_file}", content="...") with your research findings
2. Wait for confirmation: "File created successfully"
3. THEN mark the "save file" todo as [completed]
4. THEN call submit()

This is the exact error pattern we warned about in the EXECUTION PROTOCOL section.
Follow the tool-first, todo-second pattern from Example 1 in your prompt.
"""

        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=error_message,
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )

    logger.info(f"✅ File validation passed: {output_file} exists in filesystem")

    # Build 3-piece context bundle for reviewer
    context_bundle: Dict[str, Any] = {
        # 1. Supervisor's task delegation (from tool parameter)
        "supervisor_task": supervisor_task,

        # 2. Sub-agent's detailed plan (from write_todos)
        "subagent_plan": state.get("todos", []),

        # 3. Output file path (from tool parameter)
        "output_file": output_file,
    }

    logger.info(f"📦 Context bundle: {len(context_bundle['subagent_plan'])} plan steps, file: {output_file}")

    # Directly invoke reviewer-agent (similar to how task tool works)
    if not _reviewer_agent:
        logger.error("❌ Reviewer agent not configured!")
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="ERROR: Reviewer agent not configured. Cannot submit for review.",
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )

    logger.info("✅ Reviewer agent available, invoking...")

    try:
        # Create reviewer task with full context
        reviewer_task = f"""
Review this submission:

TASK ASSIGNED: {supervisor_task}

OUTPUT FILE: {output_file}

SUB-AGENT PLAN:
{chr(10).join(f"{i+1}. {todo.get('content', 'Unknown step')} [{todo.get('status', 'unknown')}]"
              for i, todo in enumerate(context_bundle['subagent_plan']))}

VALIDATE AGAINST STANDARDS:
1. Accuracy: Is information correct and factual?
2. Completeness: Are all required elements included?
3. Quality: No placeholders like "[X]%" or "TBD"?
4. Citations: Sources provided (when applicable)?

Use read_file("{output_file}") to review the output.
Then call accept_submission() if ALL standards pass, or reject_submission(feedback="...") if ANY fail.
"""

        # Invoke reviewer with context (INCLUDING todos so reviewer can update them)
        logger.info("🔍 Invoking reviewer agent...")
        reviewer_result = await _reviewer_agent.ainvoke({
            "messages": [{"role": "user", "content": reviewer_task}],
            "pending_review": context_bundle,
            "files": state.get("files", {}),  # Pass filesystem to reviewer
            "todos": state.get("todos", []),  # Pass todos so reviewer can mark complete/in-progress
        })

        logger.info(f"📊 Reviewer result keys: {list(reviewer_result.keys())}")
        logger.info(f"🔍 Full reviewer result: {reviewer_result}")

        # Extract reviewer decision from result
        review_status = reviewer_result.get("review_status")
        review_feedback = reviewer_result.get("review_feedback", "")

        # Debug: Check if reviewer tools actually set these values
        logger.info(f"   review_status value: {review_status}")
        logger.info(f"   review_feedback value: {review_feedback[:100] if review_feedback else 'None'}")

        logger.info(f"🎯 Review Status: {review_status}")
        logger.info(f"💬 Review Feedback: {review_feedback[:100] if review_feedback else 'None'}...")

        # Follow Deep Agents task tool pattern EXACTLY:
        # 1. Extract last message content from reviewer
        # 2. Propagate state (excluding messages)
        # 3. Return Command with ONE ToolMessage containing reviewer's response

        reviewer_messages = reviewer_result.get("messages", [])

        # Extract content from reviewer's last message (following task tool pattern)
        reviewer_response_content = ""
        if reviewer_messages:
            last_msg = reviewer_messages[-1]
            reviewer_response_content = getattr(last_msg, 'content', '')
            logger.info(f"📤 Extracted reviewer response: {reviewer_response_content[:100] if reviewer_response_content else '(empty)'}...")
        else:
            reviewer_response_content = "⚠️  REVIEW INCOMPLETE - Reviewer did not return any messages"
            logger.warning("⚠️  Reviewer returned no messages!")

        # CRITICAL: Validate content is non-empty to satisfy Groq API requirements
        # Groq requires ToolMessage content to be a non-empty string
        if not reviewer_response_content or reviewer_response_content.strip() == "":
            # Construct meaningful message from state fields as fallback
            logger.warning("⚠️  Reviewer response content was empty, using fallback message from state")

            if review_status == "ACCEPTED":
                reviewer_response_content = "✅ SUBMISSION ACCEPTED - Task complete, supervisor notified"
            elif review_status == "REJECTED":
                # Include feedback if available
                if review_feedback:
                    reviewer_response_content = f"❌ SUBMISSION REJECTED\n\n{review_feedback}"
                else:
                    reviewer_response_content = "❌ SUBMISSION REJECTED - See review_feedback in state for details"
            else:
                # Unknown status or missing state
                reviewer_response_content = "Review completed. Check state for review_status and review_feedback."

            logger.info(f"📤 Using fallback content: {reviewer_response_content[:100]}...")

        # Propagate ALL state from reviewer EXCEPT messages
        state_update = {}
        for k, v in reviewer_result.items():
            if k not in ["messages"]:
                state_update[k] = v

        logger.info(f"📦 Propagating state keys: {list(state_update.keys())}")

        # Return Command with state updates + single ToolMessage (Deep Agents pattern)
        return Command(
            update={
                **state_update,  # Propagate review_status, review_feedback, todos, etc.
                "messages": [
                    ToolMessage(
                        content=reviewer_response_content,  # Use reviewer's exact message
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )

    except Exception as e:
        logger.error(f"❌ Exception during review: {e}", exc_info=True)

        # Ensure error message is never empty (Groq API requirement)
        error_message = str(e) if str(e) else "Unknown error occurred"
        error_content = f"❌ ERROR during review: {error_message}\n\nPlease contact supervisor for assistance."

        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=error_content,
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )
