"""
Simple debug test to understand reviewer result structure.
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parents[1]
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_simple():
    """Simple test with maximum logging"""
    from backend.src.agents.supervisor_agent import create_supervisor_agent

    logger.info("Creating supervisor...")
    supervisor = await create_supervisor_agent()

    task = "Search for news about Claude AI. Save to /workspace/test.txt"

    logger.info(f"Running task: {task}")
    result = await supervisor.ainvoke({
        "messages": [{"role": "user", "content": task}]
    })

    logger.info("=" * 80)
    logger.info("FINAL RESULT ANALYSIS")
    logger.info("=" * 80)
    logger.info(f"Result keys: {list(result.keys())}")
    logger.info(f"Review status: {result.get('review_status')}")
    logger.info(f"Review feedback: {result.get('review_feedback', 'N/A')[:200]}")
    logger.info(f"Todos: {result.get('todos', 'N/A')}")
    logger.info(f"Number of messages: {len(result.get('messages', []))}")

    # Print last few messages
    messages = result.get("messages", [])
    logger.info(f"\nLast 3 messages:")
    for msg in messages[-3:]:
        logger.info(f"  - {type(msg).__name__}: {str(msg)[:200]}")


if __name__ == "__main__":
    asyncio.run(test_simple())
