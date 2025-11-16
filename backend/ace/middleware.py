"""
ACEMiddleware: Non-invasive wrapper for agent nodes with ACE capabilities.

Implements the ACE (Agentic Context Engineering) framework:
- Generator: Agent executes with playbook-injected system prompts
- Reflector: Analyzes execution to generate insights (background, async)
- Curator: Generates playbook deltas from insights (background, async)

Key Features:
- Middleware pattern: Wraps existing nodes without modifying core logic
- Async reflection: Doesn't block user responses
- Per-agent configuration: Enable/disable ACE for specific agents
- Osmosis two-pass workflow: +284% accuracy improvement

Usage:
    from ace.middleware import ACEMiddleware

    middleware = ACEMiddleware(store, ACE_CONFIGS)

    # Wrap agent nodes
    wrapped_supervisor = middleware.wrap_node(supervisor_node, "supervisor")
    wrapped_researcher = middleware.wrap_node(researcher_node, "researcher")
"""

from typing import Callable, Dict, Any, Optional
from datetime import datetime
import logging
import asyncio
import traceback

from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from ace.config import ACEConfig
from ace.playbook_store import PlaybookStore
from ace.reflector import Reflector
from ace.curator import Curator
from ace.osmosis_extractor import OsmosisExtractor
from ace.schemas import (
    PlaybookState,
    PlaybookEntry,
    PlaybookDelta,
    format_playbook_for_prompt,
)

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


class ACEMiddleware:
    """
    Middleware for wrapping agent nodes with ACE capabilities.

    Implements non-invasive ACE pattern:
    1. Before execution: Inject playbook into system prompt
    2. During execution: Agent runs normally (no changes)
    3. After execution: Async reflection + curation (background)

    Per-agent configuration allows gradual rollout:
    - Phase 2: Observe mode (no updates)
    - Phase 3: Single agent A/B test
    - Phase 5: Staggered rollout across all 6 agents
    """

    def __init__(
        self,
        store: Optional[BaseStore] = None,
        configs: Optional[Dict[str, ACEConfig]] = None,
        osmosis_mode: str = "ollama",
    ):
        """
        Initialize ACEMiddleware.

        Args:
            store: LangGraph Store for playbook persistence
            configs: Per-agent ACE configurations
            osmosis_mode: "ollama" (local, free) or "api" (hosted)
        """
        # Initialize store
        self.store = store or InMemoryStore()

        # Initialize Osmosis (shared across all components)
        self.osmosis = OsmosisExtractor(mode=osmosis_mode)

        # Initialize PlaybookStore
        self.playbook_store = PlaybookStore(self.store)

        # Initialize Reflector and Curator
        self.reflector = Reflector(osmosis=self.osmosis)
        self.curator = Curator(osmosis=self.osmosis)

        # Per-agent configurations
        self.configs = configs or {}

        # Execution tracking
        self.execution_count = 0

        logger.info(
            f"Initialized ACEMiddleware with {len(self.configs)} agent configs "
            f"(osmosis_mode={osmosis_mode})"
        )

    def wrap_node(
        self,
        node_fn: Callable,
        agent_type: str,
    ) -> Callable:
        """
        Wrap agent node with ACE capabilities.

        Creates a wrapper function that:
        1. Injects playbook into system prompt (before execution)
        2. Executes the original node function (during execution)
        3. Triggers async reflection + curation (after execution)

        Args:
            node_fn: Original node function to wrap
            agent_type: Agent type (supervisor, researcher, etc.)

        Returns:
            Wrapped node function with ACE capabilities
        """
        # Get config for this agent (default: disabled)
        config = self.configs.get(agent_type, ACEConfig(enabled=False, playbook_id=f"{agent_type}_v1"))

        if not config.enabled:
            logger.info(f"ACE disabled for {agent_type} - returning unwrapped node")
            return node_fn

        logger.info(
            f"ACE enabled for {agent_type} "
            f"(mode={config.reflection_mode}, max_entries={config.max_playbook_entries})"
        )

        async def wrapped_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """
            Wrapped node with ACE capabilities.

            1. Pre-execution: Inject playbook into system prompt
            2. Execution: Call original node function
            3. Post-execution: Async reflection + curation
            """
            execution_id = f"exec_{agent_type}_{self.execution_count}"
            self.execution_count += 1

            logger.info(f"[{execution_id}] Starting execution for {agent_type}")

            # === PRE-EXECUTION: Inject Playbook ===
            try:
                playbook = await self.playbook_store.get_playbook(agent_type)
                enhanced_state = await self._inject_playbook(
                    state,
                    playbook,
                    agent_type,
                    config,
                )
                logger.debug(
                    f"[{execution_id}] Injected {len(playbook['entries'])} "
                    f"playbook entries into system prompt"
                )
            except Exception as e:
                logger.warning(f"[{execution_id}] Playbook injection failed: {e}")
                enhanced_state = state  # Fall back to original state

            # === EXECUTION: Call Original Node (sync or async) ===
            start_time = datetime.now()

            try:
                # Detect if node_fn is async or sync
                if asyncio.iscoroutinefunction(node_fn):
                    # Async node - await it
                    result_state = await node_fn(enhanced_state)
                    logger.debug(f"[{execution_id}] Executed async node")
                else:
                    # Sync node - call directly
                    result_state = node_fn(enhanced_state)
                    logger.debug(f"[{execution_id}] Executed sync node")

                execution_success = True
                execution_error = None
                logger.info(f"[{execution_id}] Node execution succeeded")

            except Exception as e:
                logger.error(f"[{execution_id}] Node execution failed: {e}")
                execution_success = False
                execution_error = str(e)
                result_state = state  # Return original state on error
                # Re-raise to preserve error handling
                raise

            finally:
                duration = (datetime.now() - start_time).total_seconds()

                # === POST-EXECUTION: Async Reflection + Curation ===
                if config.reflection_mode in ["automatic", "observe"]:
                    # Build execution trace
                    execution_trace = self._build_execution_trace(
                        enhanced_state,
                        result_state,
                        execution_success,
                        execution_error,
                        duration,
                    )

                    # Trigger async reflection (non-blocking)
                    asyncio.create_task(
                        self._reflect_and_update(
                            execution_trace,
                            execution_id,
                            agent_type,
                            config,
                        )
                    )

                    logger.debug(
                        f"[{execution_id}] Triggered async reflection "
                        f"(mode={config.reflection_mode})"
                    )

            return result_state

        return wrapped_node

    async def _inject_playbook(
        self,
        state: Dict[str, Any],
        playbook: PlaybookState,
        agent_type: str,
        config: ACEConfig,
    ) -> Dict[str, Any]:
        """
        Inject playbook into state's system prompt.

        Modifies the system message to include formatted playbook entries.
        Does NOT modify the state directly - returns enhanced copy.

        Args:
            state: Current agent state
            playbook: Playbook to inject
            agent_type: Agent type
            config: ACE configuration

        Returns:
            Enhanced state with playbook-injected system prompt
        """
        # Get top playbook entries (sorted by effectiveness)
        formatted_playbook = format_playbook_for_prompt(
            playbook["entries"],
            max_entries=config.max_playbook_entries,
        )

        # Inject into system prompt
        # NOTE: This assumes state has a "messages" key with system message
        # Adjust based on your actual state structure

        enhanced_state = state.copy()

        # Find system message
        messages = enhanced_state.get("messages", [])
        if not messages:
            logger.debug(f"No messages in state for {agent_type} - skipping injection")
            return state

        # Get first message - check if it's a SystemMessage
        first_message = messages[0]

        # Check if first message is a SystemMessage
        from langchain_core.messages import SystemMessage
        is_system_message = isinstance(first_message, SystemMessage)

        if not is_system_message:
            # First message is not a SystemMessage (e.g., it's a HumanMessage)
            # This happens on first execution before the node creates the SystemMessage
            # Skip injection - the node will create its own SystemMessage
            logger.debug(
                f"First message is not SystemMessage for {agent_type} "
                f"(type: {type(first_message).__name__}) - skipping injection. "
                f"ACE will activate on subsequent executions."
            )
            return state

        # Inject playbook section
        if formatted_playbook:
            playbook_section = f"""
═══════════════════════════════════════════════════════════════════════════
ACE PLAYBOOK (Learnings from Previous Executions)
═══════════════════════════════════════════════════════════════════════════

{formatted_playbook}

Use these learnings to inform your approach on this task.
═══════════════════════════════════════════════════════════════════════════
"""
            # Append to system message content
            if hasattr(first_message, 'content'):
                # LangChain Message object
                original_content = first_message.content
                enhanced_content = original_content + "\n" + playbook_section

                # Create new message with enhanced content
                enhanced_message = SystemMessage(content=enhanced_content)

                # Replace first message
                enhanced_state["messages"] = [enhanced_message] + messages[1:]
                logger.debug(
                    f"Injected {len(playbook['entries'])} playbook entries "
                    f"into SystemMessage for {agent_type}"
                )

            elif isinstance(first_message, dict):
                # Dict message
                first_message["content"] += "\n" + playbook_section

        return enhanced_state

    def _build_execution_trace(
        self,
        input_state: Dict[str, Any],
        output_state: Dict[str, Any],
        success: bool,
        error: Optional[str],
        duration_seconds: float,
    ) -> Dict[str, Any]:
        """
        Build execution trace for reflection.

        Extracts relevant information from input/output states.

        Args:
            input_state: State before execution
            output_state: State after execution
            success: Whether execution succeeded
            error: Error message if failed
            duration_seconds: Execution duration

        Returns:
            Execution trace dict
        """
        return {
            "input_state": input_state,
            "output_state": output_state,
            "messages": output_state.get("messages", []),
            "tool_calls": self._extract_tool_calls(input_state, output_state),
            "errors": [error] if error else [],
            "success": success,
            "duration_seconds": duration_seconds,
            "final_result": self._extract_final_result(output_state),
        }

    def _extract_tool_calls(
        self,
        input_state: Dict[str, Any],
        output_state: Dict[str, Any],
    ) -> list:
        """Extract tool calls from state."""
        # This depends on your state structure
        # Adjust based on how tool calls are tracked

        tool_calls = []

        # Example: Extract from messages
        messages = output_state.get("messages", [])
        for msg in messages:
            if hasattr(msg, 'tool_calls'):
                for tc in msg.tool_calls:
                    tool_calls.append({
                        "tool_name": tc.get("name", "unknown"),
                        "success": True,  # Assume success if in output
                    })

        return tool_calls

    def _extract_final_result(self, state: Dict[str, Any]) -> str:
        """Extract final result from state."""
        # Get last message content
        messages = state.get("messages", [])
        if not messages:
            return ""

        last_message = messages[-1]

        # Use helper function to extract content
        content = _get_message_content(last_message)

        # Truncate to reasonable length
        return content[:1000] if isinstance(content, str) else str(content)[:1000]

    async def _reflect_and_update(
        self,
        execution_trace: Dict[str, Any],
        execution_id: str,
        agent_type: str,
        config: ACEConfig,
    ):
        """
        Background reflection and playbook update.

        Runs asynchronously without blocking user responses.

        Args:
            execution_trace: Execution data
            execution_id: Unique execution ID
            agent_type: Agent type
            config: ACE configuration
        """
        try:
            logger.info(f"[{execution_id}] Starting async reflection...")

            # Get current playbook
            playbook = await self.playbook_store.get_playbook(agent_type)

            # STEP 1: Reflection (two-pass: Claude → Osmosis)
            insights = await self.reflector.analyze(
                execution_trace=execution_trace,
                execution_id=execution_id,
                agent_type=agent_type,
                current_playbook=playbook["entries"],
            )

            logger.info(
                f"[{execution_id}] Reflection generated {len(insights)} insights"
            )

            # STEP 2: Curation (two-pass: Claude → Osmosis)
            if config.reflection_mode == "automatic":
                # Automatic mode: Apply updates
                delta = await self.curator.curate(
                    insights=insights,
                    current_playbook=playbook,
                    execution_id=execution_id,
                )

                logger.info(
                    f"[{execution_id}] Curation delta: "
                    f"+{len(delta.add)} -{len(delta.remove)} ~{len(delta.update)}"
                )

                # STEP 3: Apply delta
                updated_playbook = self._apply_delta(playbook, delta)

                # STEP 4: Prune if needed
                if len(updated_playbook["entries"]) > config.max_playbook_entries:
                    logger.info(
                        f"[{execution_id}] Pruning playbook: "
                        f"{len(updated_playbook['entries'])} → {config.max_playbook_entries}"
                    )
                    await self.playbook_store.prune_playbook(
                        agent_type,
                        max_entries=config.max_playbook_entries,
                    )
                    # Reload pruned playbook
                    updated_playbook = await self.playbook_store.get_playbook(agent_type)

                # STEP 5: Save updated playbook
                updated_playbook["total_executions"] += 1
                await self.playbook_store.save_playbook(updated_playbook)

                logger.info(
                    f"[{execution_id}] ✓ Playbook updated "
                    f"(v{updated_playbook['version']}, "
                    f"{len(updated_playbook['entries'])} entries)"
                )

            elif config.reflection_mode == "observe":
                # Observe mode: Generate insights but don't update playbook
                logger.info(
                    f"[{execution_id}] Observe mode: "
                    f"{len(insights)} insights generated but not applied"
                )

        except Exception as e:
            logger.error(
                f"[{execution_id}] Async reflection failed: {e}\n"
                f"{traceback.format_exc()}"
            )

    def _apply_delta(
        self,
        playbook: PlaybookState,
        delta: PlaybookDelta,
    ) -> PlaybookState:
        """
        Apply playbook delta to current playbook.

        Args:
            playbook: Current playbook state
            delta: Delta operations (add/update/remove)

        Returns:
            Updated playbook state
        """
        # Copy playbook
        updated_playbook = playbook.copy()
        entries = list(updated_playbook["entries"])

        # REMOVE operations
        for entry_id in delta.remove:
            entries = [e for e in entries if e.id != entry_id]

        # UPDATE operations
        for update_op in delta.update:
            for entry in entries:
                if entry.id == update_op.entry_id:
                    # Apply updates
                    for key, value in update_op.updates.items():
                        if key == "helpful_count" and value.startswith("+"):
                            entry.helpful_count += int(value[1:])
                        elif key == "harmful_count" and value.startswith("+"):
                            entry.harmful_count += int(value[1:])
                        else:
                            setattr(entry, key, value)

                    # Recalculate confidence
                    entry.last_updated = datetime.now()
                    entry._recalculate_confidence()

        # ADD operations
        for new_entry in delta.add:
            entries.append(new_entry)

        # Update playbook
        updated_playbook["entries"] = entries

        return updated_playbook


# Example usage
async def example():
    """Example: Wrap agent nodes with ACE."""
    from ace.config import ACE_CONFIGS, enable_phase_2_observe_mode

    # Initialize middleware
    middleware = ACEMiddleware(
        configs=ACE_CONFIGS,
        osmosis_mode="ollama",
    )

    # Example node function
    async def researcher_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Mock researcher node."""
        from langchain_core.messages import AIMessage

        print("Researcher executing with playbook context...")

        # Simulate research
        result_message = AIMessage(
            content="Completed research on quantum computing with 15 citations"
        )

        # Return updated state
        state["messages"].append(result_message)
        return state

    # Wrap node with ACE
    wrapped_researcher = middleware.wrap_node(researcher_node, "researcher")

    # Enable observe mode for all agents
    enable_phase_2_observe_mode()

    # Execute wrapped node
    from langchain_core.messages import SystemMessage, HumanMessage

    state = {
        "messages": [
            SystemMessage(content="You are a researcher agent."),
            HumanMessage(content="Research quantum computing"),
        ]
    }

    print("\n=== Executing wrapped researcher node ===\n")
    result = await wrapped_researcher(state)

    print(f"\n✓ Execution complete")
    print(f"Messages: {len(result['messages'])}")

    # Wait for async reflection
    await asyncio.sleep(3)

    # Check playbook
    playbook = await middleware.playbook_store.get_playbook("researcher")
    print(f"\nPlaybook: v{playbook['version']}, {len(playbook['entries'])} entries")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example())
