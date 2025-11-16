"""
PlaybookStore: LangGraph Store wrapper for ACE playbook persistence.

Handles CRUD operations for agent playbooks with namespace management.
Integrates with Osmosis for schema validation and integrity.

Each agent (supervisor, researcher, data_scientist, expert_analyst, writer, reviewer)
has its own playbook namespace with versioned entries.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from ace.schemas import (
    PlaybookState,
    PlaybookEntry,
    create_initial_playbook,
)


class PlaybookStore:
    """
    LangGraph Store wrapper for ACE playbook persistence.

    Manages playbooks for all 6 agents with versioning and namespace isolation.

    Namespace structure:
        ("ace", "playbooks", "{agent_type}")

    Example:
        ("ace", "playbooks", "researcher")  # Researcher's playbook
        ("ace", "playbooks", "supervisor")  # Supervisor's playbook
    """

    def __init__(self, store: Optional[BaseStore] = None):
        """
        Initialize PlaybookStore.

        Args:
            store: LangGraph Store instance (defaults to InMemoryStore for testing)
        """
        self.store = store or InMemoryStore()

        # Agent types (6 agents)
        self.agent_types = [
            "supervisor",
            "researcher",
            "data_scientist",
            "expert_analyst",
            "writer",
            "reviewer",
        ]

    def _get_namespace(self, agent_type: str) -> tuple:
        """
        Get namespace tuple for agent's playbook.

        Args:
            agent_type: Agent type (supervisor, researcher, etc.)

        Returns:
            Namespace tuple for LangGraph Store

        Raises:
            ValueError: If agent_type is invalid
        """
        if agent_type not in self.agent_types:
            raise ValueError(
                f"Invalid agent_type: {agent_type}. "
                f"Must be one of: {', '.join(self.agent_types)}"
            )

        return ("ace", "playbooks", agent_type)

    async def get_playbook(self, agent_type: str) -> PlaybookState:
        """
        Retrieve playbook for agent.

        If no playbook exists, creates and returns initial empty playbook.

        Args:
            agent_type: Agent type (supervisor, researcher, etc.)

        Returns:
            PlaybookState for the agent
        """
        namespace = self._get_namespace(agent_type)

        # Search for playbook versions
        items = await self.store.asearch(namespace)

        if not items:
            # No playbook exists - create initial
            return create_initial_playbook(agent_type)

        # Get latest version
        latest_item = max(items, key=lambda x: x.value.get("version", 0))
        playbook_data = latest_item.value

        # Validate and return as PlaybookState
        return PlaybookState(**playbook_data)

    async def save_playbook(self, playbook: PlaybookState) -> None:
        """
        Save playbook to store.

        Automatically increments version number and updates timestamp.

        Args:
            playbook: PlaybookState to save
        """
        agent_type = playbook["agent_type"]
        namespace = self._get_namespace(agent_type)

        # Increment version
        playbook["version"] += 1
        playbook["last_updated"] = datetime.now()

        # Generate version key
        version_key = f"v{playbook['version']}"

        # Save to store
        await self.store.aput(
            namespace=namespace,
            key=version_key,
            value=dict(playbook),
        )

    async def get_playbook_history(
        self,
        agent_type: str,
        limit: int = 10,
    ) -> List[PlaybookState]:
        """
        Get playbook version history.

        Args:
            agent_type: Agent type
            limit: Maximum number of versions to return (most recent first)

        Returns:
            List of PlaybookState versions (newest first)
        """
        namespace = self._get_namespace(agent_type)

        # Get all versions
        items = await self.store.asearch(namespace)

        if not items:
            return []

        # Sort by version (newest first)
        sorted_items = sorted(
            items,
            key=lambda x: x.value.get("version", 0),
            reverse=True,
        )

        # Limit results
        limited_items = sorted_items[:limit]

        # Convert to PlaybookState
        return [PlaybookState(**item.value) for item in limited_items]

    async def delete_playbook(self, agent_type: str) -> None:
        """
        Delete all playbook versions for agent.

        WARNING: This is destructive and cannot be undone.

        Args:
            agent_type: Agent type
        """
        namespace = self._get_namespace(agent_type)

        # Get all versions
        items = await self.store.asearch(namespace)

        # Delete each version
        for item in items:
            await self.store.adelete(namespace, item.key)

    async def initialize_all_playbooks(self) -> Dict[str, PlaybookState]:
        """
        Initialize empty playbooks for all 6 agents.

        Useful for first-time setup or reset.

        Returns:
            Dict mapping agent_type → initial PlaybookState
        """
        playbooks = {}

        for agent_type in self.agent_types:
            # Check if playbook exists
            existing = await self.get_playbook(agent_type)

            if existing["version"] == 0:
                # Doesn't exist - save initial
                await self.save_playbook(existing)

            playbooks[agent_type] = existing

        return playbooks

    async def get_all_playbooks(self) -> Dict[str, PlaybookState]:
        """
        Get current playbooks for all agents.

        Returns:
            Dict mapping agent_type → PlaybookState
        """
        playbooks = {}

        for agent_type in self.agent_types:
            playbooks[agent_type] = await self.get_playbook(agent_type)

        return playbooks

    async def get_playbook_stats(self, agent_type: str) -> Dict[str, Any]:
        """
        Get statistics about agent's playbook.

        Args:
            agent_type: Agent type

        Returns:
            Dict with playbook statistics
        """
        playbook = await self.get_playbook(agent_type)

        # Calculate stats
        total_entries = len(playbook["entries"])
        helpful_entries = len([e for e in playbook["entries"] if e.category == "helpful"])
        harmful_entries = len([e for e in playbook["entries"] if e.category == "harmful"])
        neutral_entries = len([e for e in playbook["entries"] if e.category == "neutral"])

        # Average confidence
        if total_entries > 0:
            avg_confidence = sum(
                e.confidence_score for e in playbook["entries"]
            ) / total_entries
        else:
            avg_confidence = 0.0

        # Top tags
        tag_counts: Dict[str, int] = {}
        for entry in playbook["entries"]:
            for tag in entry.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        top_tags = sorted(
            tag_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return {
            "agent_type": agent_type,
            "version": playbook["version"],
            "total_entries": total_entries,
            "helpful_entries": helpful_entries,
            "harmful_entries": harmful_entries,
            "neutral_entries": neutral_entries,
            "avg_confidence": round(avg_confidence, 3),
            "total_executions": playbook["total_executions"],
            "last_updated": playbook["last_updated"],
            "top_tags": top_tags,
        }

    async def prune_playbook(
        self,
        agent_type: str,
        min_confidence: float = 0.3,
        max_entries: Optional[int] = None,
    ) -> int:
        """
        Prune low-quality entries from playbook.

        Removes entries below confidence threshold or exceeds max_entries limit.

        Args:
            agent_type: Agent type
            min_confidence: Minimum confidence score to keep (default 0.3)
            max_entries: Maximum entries to keep (keeps highest confidence)

        Returns:
            Number of entries removed
        """
        playbook = await self.get_playbook(agent_type)

        original_count = len(playbook["entries"])

        # Filter by confidence
        filtered_entries = [
            e for e in playbook["entries"]
            if e.confidence_score >= min_confidence
        ]

        # Limit by max_entries (keep highest confidence)
        if max_entries and len(filtered_entries) > max_entries:
            sorted_entries = sorted(
                filtered_entries,
                key=lambda e: e.confidence_score,
                reverse=True,
            )
            filtered_entries = sorted_entries[:max_entries]

        # Update playbook
        playbook["entries"] = filtered_entries

        # Save
        await self.save_playbook(playbook)

        # Return number removed
        return original_count - len(filtered_entries)

    async def search_entries(
        self,
        agent_type: str,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_confidence: float = 0.0,
    ) -> List[PlaybookEntry]:
        """
        Search playbook entries with filters.

        Args:
            agent_type: Agent type
            query: Text search in content (case-insensitive substring)
            category: Filter by category (helpful/harmful/neutral)
            tags: Filter by tags (must include ALL specified tags)
            min_confidence: Minimum confidence score

        Returns:
            List of matching PlaybookEntry objects
        """
        playbook = await self.get_playbook(agent_type)

        results = playbook["entries"]

        # Filter by query (case-insensitive substring)
        if query:
            query_lower = query.lower()
            results = [
                e for e in results
                if query_lower in e.content.lower()
            ]

        # Filter by category
        if category:
            results = [e for e in results if e.category == category]

        # Filter by tags (must have ALL specified tags)
        if tags:
            results = [
                e for e in results
                if all(tag in e.tags for tag in tags)
            ]

        # Filter by min confidence
        results = [e for e in results if e.confidence_score >= min_confidence]

        return results


# Example usage
async def example():
    """Example usage of PlaybookStore."""

    # Initialize store
    store = PlaybookStore()

    # Initialize all playbooks
    print("Initializing playbooks for all 6 agents...")
    playbooks = await store.initialize_all_playbooks()
    print(f"✓ Initialized {len(playbooks)} playbooks")

    # Get researcher playbook
    researcher_playbook = await store.get_playbook("researcher")
    print(f"\nResearcher playbook v{researcher_playbook['version']}")
    print(f"Entries: {len(researcher_playbook['entries'])}")

    # Add a test entry
    from ace.schemas import PlaybookEntry
    import uuid

    test_entry = PlaybookEntry(
        id=str(uuid.uuid4()),
        content="Always cite sources with exact quotes and URLs",
        category="helpful",
        helpful_count=5,
        harmful_count=0,
        confidence_score=0.9,
        created_at=datetime.now(),
        last_updated=datetime.now(),
        source_executions=["exec_001", "exec_002"],
        tags=["citation", "accuracy", "researcher"],
        metadata={"priority": "high"},
    )

    researcher_playbook["entries"].append(test_entry)
    researcher_playbook["total_executions"] += 1

    # Save updated playbook
    await store.save_playbook(researcher_playbook)
    print(f"\n✓ Saved playbook v{researcher_playbook['version']}")

    # Get stats
    stats = await store.get_playbook_stats("researcher")
    print(f"\nPlaybook Stats:")
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Helpful: {stats['helpful_entries']}")
    print(f"  Avg confidence: {stats['avg_confidence']}")

    # Search entries
    citation_entries = await store.search_entries(
        agent_type="researcher",
        tags=["citation"],
        min_confidence=0.8,
    )
    print(f"\n✓ Found {len(citation_entries)} high-confidence citation entries")

    # Get history
    history = await store.get_playbook_history("researcher", limit=5)
    print(f"\nPlaybook History (last 5 versions):")
    for playbook in history:
        print(f"  v{playbook['version']}: {len(playbook['entries'])} entries")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example())
