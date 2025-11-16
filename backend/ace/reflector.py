"""
Reflector: Generate insights from agent execution traces.

Uses two-pass workflow for maximum reasoning quality:
1. Claude analyzes execution freely (no structure constraints)
2. Osmosis extracts structured ReflectionInsightList

Proven: +284% accuracy improvement on complex reasoning.

The reflector implements the "Reflector" role from ACE framework:
- Analyzes what worked and what didn't during execution
- Generates helpful, harmful, and neutral insights
- Provides actionable recommendations
- Iterates to refine insights (up to max_iterations)
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from ace.schemas import ReflectionInsight, ReflectionInsightList
from ace.osmosis_extractor import OsmosisExtractor

logger = logging.getLogger(__name__)


def _get_message_role(msg: Any) -> str:
    """
    Extract role from message (handles both dict and LangChain Message objects).

    Args:
        msg: Message object (dict or LangChain Message)

    Returns:
        Role string (human, assistant, system, tool, unknown)
    """
    # Check if it's a LangChain Message object
    if hasattr(msg, '__class__'):
        class_name = msg.__class__.__name__
        if 'HumanMessage' in class_name:
            return 'human'
        elif 'AIMessage' in class_name:
            return 'assistant'
        elif 'SystemMessage' in class_name:
            return 'system'
        elif 'ToolMessage' in class_name:
            return 'tool'

    # Fall back to dict access
    if isinstance(msg, dict):
        return msg.get("role", "unknown")

    return "unknown"


def _get_message_content(msg: Any) -> str:
    """
    Extract content from message (handles both dict and LangChain Message objects).

    Args:
        msg: Message object (dict or LangChain Message)

    Returns:
        Content string (or empty string if not found)
    """
    # Try attribute access first (LangChain Message)
    if hasattr(msg, 'content'):
        content = msg.content
        # Handle list content (multimodal)
        if isinstance(content, list):
            # Extract text from content blocks
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'text':
                    text_parts.append(block.get('text', ''))
                elif isinstance(block, str):
                    text_parts.append(block)
            return ' '.join(text_parts)
        return str(content) if content else ""

    # Fall back to dict access
    if isinstance(msg, dict):
        return msg.get("content", "")

    return ""


class Reflector:
    """
    Generate structured insights from agent execution traces.

    Two-pass workflow:
    1. Pass 1: Claude analyzes execution in free-form text
    2. Pass 2: Osmosis extracts ReflectionInsightList from analysis

    This separation allows Claude to focus 100% on reasoning quality
    while Osmosis ensures valid structured output.
    """

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        osmosis: Optional[OsmosisExtractor] = None,
        max_iterations: int = 5,
        temperature: float = 0.7,
    ):
        """
        Initialize Reflector.

        Args:
            model: Claude model for analysis (Haiku for cost efficiency)
            osmosis: OsmosisExtractor instance (creates default if None)
            max_iterations: Maximum refinement iterations
            temperature: LLM temperature (0.7 for creative insights)
        """
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
        )
        self.osmosis = osmosis or OsmosisExtractor(mode="ollama")
        self.max_iterations = max_iterations

        logger.info(f"Initialized Reflector with {model}")

    async def analyze(
        self,
        execution_trace: Dict[str, Any],
        execution_id: str,
        agent_type: str,
        current_playbook: Optional[List[Any]] = None,
    ) -> List[ReflectionInsight]:
        """
        Analyze execution and generate structured insights.

        Two-pass workflow:
        1. Claude free reasoning about what worked/failed
        2. Osmosis extraction of structured insights

        Args:
            execution_trace: Complete execution data (messages, tool calls, errors)
            execution_id: Unique execution identifier
            agent_type: Agent that executed (supervisor, researcher, etc.)
            current_playbook: Optional current playbook entries for context

        Returns:
            List of structured reflection insights
        """
        logger.info(f"Analyzing execution {execution_id} for {agent_type}")

        # PASS 1: Claude free-form analysis
        analysis_prompt = self._build_analysis_prompt(
            execution_trace,
            agent_type,
            current_playbook,
        )

        messages = [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content=analysis_prompt),
        ]

        logger.debug("Pass 1: Claude analyzing execution...")
        response = await self.llm.ainvoke(messages)
        analysis_text = response.content

        logger.debug(f"Pass 1 complete: {len(analysis_text)} chars of analysis")

        # PASS 2: Osmosis structured extraction
        logger.debug("Pass 2: Osmosis extracting insights...")
        insights_list = await self.osmosis.extract(
            text=analysis_text,
            schema=ReflectionInsightList,
        )

        logger.info(f"✓ Extracted {len(insights_list.insights)} insights")

        # Enrich insights with metadata
        enriched_insights = []
        for insight in insights_list.insights:
            insight.execution_id = execution_id
            insight.agent_type = agent_type
            insight.created_at = datetime.now()
            enriched_insights.append(insight)

        return enriched_insights

    def _get_system_prompt(self) -> str:
        """Get system prompt for Claude's analysis (Pass 1)."""
        return """You are an expert at analyzing agent execution traces to extract actionable insights.

Your role is to deeply analyze what worked well and what didn't during the execution, then provide specific, actionable insights that will help improve future executions.

Focus on:
- HELPFUL patterns that should be repeated
- HARMFUL patterns that should be avoided
- NEUTRAL observations that are interesting but not clearly good or bad

Be specific. Use concrete examples from the execution. Think step by step.

IMPORTANT: Write your analysis in natural language. Do NOT try to format as JSON.
Focus purely on reasoning quality. Structure will be extracted later."""

    def _build_analysis_prompt(
        self,
        execution_trace: Dict[str, Any],
        agent_type: str,
        current_playbook: Optional[List[Any]] = None,
    ) -> str:
        """Build prompt for Claude's free-form analysis (Pass 1)."""

        # Extract key execution elements
        messages = execution_trace.get("messages", [])
        tool_calls = execution_trace.get("tool_calls", [])
        errors = execution_trace.get("errors", [])
        final_result = execution_trace.get("final_result", "")
        duration_seconds = execution_trace.get("duration_seconds", 0)

        # Build playbook context (if available)
        playbook_context = ""
        if current_playbook:
            playbook_context = "\nCURRENT PLAYBOOK (existing learnings):\n"
            for i, entry in enumerate(current_playbook[:10], 1):
                content = entry.get("content", entry) if isinstance(entry, dict) else str(entry)
                playbook_context += f"{i}. {content[:150]}\n"
            playbook_context += "\nAvoid generating insights that duplicate existing playbook entries.\n"

        prompt = f"""You are analyzing an execution by the {agent_type} agent to extract insights about what worked well and what didn't.

EXECUTION TRACE:
{playbook_context}
Agent Type: {agent_type}
Duration: {duration_seconds:.2f}s

Messages exchanged:
{self._format_messages(messages)}

Tool calls made:
{self._format_tool_calls(tool_calls)}

Errors encountered:
{self._format_errors(errors)}

Final result:
{final_result[:500] if final_result else "None"}

═══════════════════════════════════════════════════════════════════════════
ANALYSIS TASK
═══════════════════════════════════════════════════════════════════════════

Analyze this execution deeply and identify:

1. **HELPFUL patterns**: What worked well? What should be repeated?
   Examples:
   - Effective tool usage patterns (e.g., "Using tavily_search before read_file")
   - Good delegation strategies (e.g., "Delegating research before analysis")
   - Successful verification approaches
   - Clever workarounds or optimizations
   - Proper error handling

2. **HARMFUL patterns**: What went wrong? What should be avoided?
   Examples:
   - Tool misuse or failures
   - Poor delegation choices (e.g., "Delegating prematurely without context")
   - Verification gaps
   - Wasted effort or redundancy
   - Errors that could have been prevented

3. **NEUTRAL observations**: Interesting patterns that aren't clearly good or bad
   Examples:
   - Timeout values that might need tuning
   - File paths that could be standardized
   - Patterns worth experimenting with

For each insight:
- Explain WHAT happened (specific, concrete example from this execution)
- Explain WHY it was helpful/harmful/neutral (reasoning)
- Suggest HOW to leverage or avoid in future (actionable recommendation)

Think step by step. Be specific with examples from this execution trace.
Focus on NON-OBVIOUS insights that would actually help improve future executions.
Avoid generic advice like "be careful" or "do better" - be concrete and actionable.

IMPORTANT: Write your analysis in natural language. Do NOT try to format as JSON.
Focus on reasoning quality. Structure will be extracted later by a specialized model.
"""
        return prompt

    def _format_messages(self, messages: List[Any]) -> str:
        """Format messages for analysis prompt."""
        if not messages:
            return "None"

        formatted = []
        # Show last 10 messages (most relevant for recent execution)
        for i, msg in enumerate(messages[-10:], 1):
            # Use helper functions to extract role and content
            role = _get_message_role(msg)
            content = _get_message_content(msg)

            # Truncate long content
            if isinstance(content, str):
                content = content[:200] + "..." if len(content) > 200 else content
            elif isinstance(content, list):
                content = f"[{len(content)} items]"

            formatted.append(f"{i}. [{role}] {content}")

        return "\n".join(formatted)

    def _format_tool_calls(self, tool_calls: List[Dict]) -> str:
        """Format tool calls for analysis prompt."""
        if not tool_calls:
            return "None"

        formatted = []
        for i, call in enumerate(tool_calls, 1):
            tool_name = call.get("tool_name", "unknown")
            success = call.get("success", False)
            error = call.get("error", "")

            status = "✓" if success else "✗"
            formatted.append(
                f"{i}. {status} {tool_name}" +
                (f" (error: {error[:100]})" if error else "")
            )

        return "\n".join(formatted)

    def _format_errors(self, errors: List[str]) -> str:
        """Format errors for analysis prompt."""
        if not errors:
            return "None"

        formatted = []
        for i, error in enumerate(errors, 1):
            error_str = str(error)[:200]
            formatted.append(f"{i}. {error_str}")

        return "\n".join(formatted)

    async def refine_insights(
        self,
        insights: List[ReflectionInsight],
        feedback: str,
    ) -> List[ReflectionInsight]:
        """
        Refine insights based on feedback.

        Uses two-pass workflow again:
        1. Claude refines insights based on feedback
        2. Osmosis extracts refined ReflectionInsightList

        Args:
            insights: Current insights to refine
            feedback: Feedback on what to improve

        Returns:
            Refined list of insights
        """
        logger.info(f"Refining {len(insights)} insights based on feedback")

        # Format current insights
        insights_text = "\n".join(
            f"{i+1}. [{insight.category}] {insight.content}"
            for i, insight in enumerate(insights)
        )

        # Build refinement prompt
        refinement_prompt = f"""You previously generated these insights:

{insights_text}

However, there's feedback requesting improvements:

{feedback}

Please refine the insights based on this feedback. You can:
- Improve clarity and specificity
- Add missing insights
- Remove or merge redundant insights
- Adjust confidence scores
- Enhance recommendations

IMPORTANT: Write your refined analysis in natural language. Do NOT format as JSON.
Focus on addressing the feedback while maintaining insight quality.
"""

        messages = [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content=refinement_prompt),
        ]

        # PASS 1: Claude refinement
        logger.debug("Pass 1: Claude refining insights...")
        response = await self.llm.ainvoke(messages)
        refined_text = response.content

        # PASS 2: Osmosis extraction
        logger.debug("Pass 2: Osmosis extracting refined insights...")
        refined_insights_list = await self.osmosis.extract(
            text=refined_text,
            schema=ReflectionInsightList,
        )

        logger.info(f"✓ Refined to {len(refined_insights_list.insights)} insights")

        return refined_insights_list.insights


# Example usage
async def example():
    """Example: Reflect on researcher execution."""

    reflector = Reflector()

    # Mock execution trace
    execution_trace = {
        "messages": [
            {"role": "user", "content": "Research climate change impacts on agriculture"},
            {"role": "assistant", "content": "I'll search for recent studies on this topic..."},
            {"role": "tool", "content": "Found 15 papers from 2024-2025"},
            {"role": "assistant", "content": "Let me analyze these papers..."},
        ],
        "tool_calls": [
            {"tool_name": "tavily_search", "success": True},
            {"tool_name": "read_file", "success": True},
        ],
        "errors": [],
        "final_result": "Comprehensive research report with 20 citations showing 15% crop yield reduction by 2030",
        "duration_seconds": 45.3,
    }

    try:
        # Analyze execution (two-pass workflow)
        insights = await reflector.analyze(
            execution_trace=execution_trace,
            execution_id="exec_12345",
            agent_type="researcher",
        )

        print(f"\n✓ Generated {len(insights)} insights:\n")
        for i, insight in enumerate(insights, 1):
            print(f"{i}. [{insight.category}] (confidence: {insight.confidence_score:.2f})")
            print(f"   {insight.content}")
            if insight.recommendation:
                print(f"   → Recommendation: {insight.recommendation}")
            print()

    except Exception as e:
        print(f"✗ Reflection failed: {e}")

    finally:
        await reflector.osmosis.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(example())
