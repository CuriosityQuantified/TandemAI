"""Example usage of the Deep Research Agent

Demonstrates how to use the deep research system with different effort levels.
"""

import asyncio
import uuid
from datetime import datetime

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from .base_agent import create_deep_research_agent
from .state import create_initial_state
from .effort_config import EffortLevel


async def run_research_example(
    query: str,
    effort_level: str = "standard",
    hitl_enabled: bool = False,
):
    """Run a research query with the deep research agent

    Args:
        query: Research question
        effort_level: Effort level (quick/standard/thorough/deep/extended_deep/ultrathink_deep)
        hitl_enabled: Whether to enable human-in-the-loop approval

    Returns:
        Final state with research report
    """
    # Create PostgreSQL checkpointer
    connection_string = "postgresql://postgres:postgres@localhost:5432/postgres"
    pool = AsyncConnectionPool(connection_string)

    async with pool.connection() as conn:
        checkpointer = AsyncPostgresSaver(conn)
        await checkpointer.setup()

        # Create agent
        agent = create_deep_research_agent(checkpointer=checkpointer)

        # Create initial state
        session_id = str(uuid.uuid4())
        initial_state = create_initial_state(
            query=query,
            effort_level=effort_level,
            session_id=session_id,
            hitl_enabled=hitl_enabled,
        )

        # Run agent
        config = {
            "configurable": {
                "thread_id": session_id,
            }
        }

        print(f"\n🔍 Starting research with {effort_level} effort level...")
        print(f"Query: {query}")
        print(f"Session ID: {session_id}")
        print(f"HITL Enabled: {hitl_enabled}")
        print("-" * 80)

        final_state = None
        async for event in agent.astream(initial_state, config, stream_mode="values"):
            phase = event.get("phase", "unknown")
            iteration = event.get("iteration", 0)
            search_count = event.get("search_count", 0)
            min_required = event.get("min_searches_required", 0)

            print(f"Phase: {phase} | Iteration: {iteration} | Searches: {search_count}/{min_required}")

            # Check if approval required
            if event.get("approval_required"):
                print("\n⚠️  User approval required!")
                print("Plan:")
                if event.get("action_history"):
                    last_action = event["action_history"][-1]
                    print(last_action.output)

                # In real usage, would wait for user input here
                # For demo, auto-approve
                print("\n✓ Auto-approving for demo...")
                event["approval_required"] = False
                event["planning_approved"] = True

            final_state = event

        print("\n" + "=" * 80)
        print("✓ Research Complete!")
        print("=" * 80)

        if final_state and final_state.get("final_report"):
            print("\nFinal Report:")
            print("-" * 80)
            print(final_state["final_report"])
            print("-" * 80)

            print(f"\nTotal Searches: {final_state['search_count']}")
            print(f"Iterations: {final_state['iteration']}")
            print(f"Essential Findings: {len(final_state['essential_findings'])}")

            if final_state.get("quality_metrics"):
                metrics = final_state["quality_metrics"]
                print(f"\nQuality Metrics:")
                print(f"  Completeness: {metrics.completeness:.2f}")
                print(f"  Accuracy: {metrics.accuracy:.2f}")
                print(f"  Relevance: {metrics.relevance:.2f}")
                print(f"  Citation Quality: {metrics.citation_quality:.2f}")
                print(f"  Overall Score: {metrics.overall_score:.2f}")

        return final_state


async def main():
    """Run example research queries"""

    # Example 1: Quick research
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Quick Research (5 searches minimum)")
    print("=" * 80)
    await run_research_example(
        query="What are the latest developments in quantum computing?",
        effort_level=EffortLevel.QUICK,
        hitl_enabled=False,
    )

    # Example 2: Standard research with HITL
    print("\n\n" + "=" * 80)
    print("EXAMPLE 2: Standard Research with HITL (20 searches minimum)")
    print("=" * 80)
    await run_research_example(
        query="How does climate change affect global food security?",
        effort_level=EffortLevel.STANDARD,
        hitl_enabled=True,
    )

    # Example 3: Thorough research
    print("\n\n" + "=" * 80)
    print("EXAMPLE 3: Thorough Research (50 searches minimum)")
    print("=" * 80)
    await run_research_example(
        query="What are the ethical implications of artificial general intelligence?",
        effort_level=EffortLevel.THOROUGH,
        hitl_enabled=False,
    )


if __name__ == "__main__":
    asyncio.run(main())
