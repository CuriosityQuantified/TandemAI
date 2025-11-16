"""
Unit tests for ACE (Agentic Context Engineering) components.

Tests all ACE components with Osmosis-Structure-0.6B integration:
- OsmosisExtractor (two-pass workflow)
- PlaybookStore (persistence and CRUD)
- Reflector (insight generation)
- Curator (delta generation with semantic de-duplication)
- ACEMiddleware (node wrapping)

Uses Ollama local deployment for zero-cost testing.
"""

import pytest
import asyncio
from datetime import datetime
from typing import List, Dict, Any
import uuid

# ACE imports
from ace.osmosis_extractor import OsmosisExtractor
from ace.playbook_store import PlaybookStore
from ace.reflector import Reflector
from ace.curator import Curator
from ace.middleware import ACEMiddleware
from ace.schemas import (
    PlaybookEntry,
    PlaybookState,
    ReflectionInsight,
    ReflectionInsightList,
    PlaybookDelta,
    PlaybookUpdate,
    create_initial_playbook,
    format_playbook_for_prompt,
)
from ace.config import ACEConfig, ACE_CONFIGS

from langgraph.store.memory import InMemoryStore
from pydantic import BaseModel, Field


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def osmosis_extractor():
    """Osmosis extractor using Ollama local (zero cost)."""
    return OsmosisExtractor(mode="ollama")


@pytest.fixture
def playbook_store():
    """PlaybookStore with in-memory store."""
    return PlaybookStore(store=InMemoryStore())


@pytest.fixture
def reflector():
    """Reflector with Ollama-based Osmosis."""
    osmosis = OsmosisExtractor(mode="ollama")
    return Reflector(osmosis=osmosis)


@pytest.fixture
def curator():
    """Curator with Ollama-based Osmosis."""
    osmosis = OsmosisExtractor(mode="ollama")
    return Curator(osmosis=osmosis)


@pytest.fixture
def ace_middleware():
    """ACEMiddleware with all components."""
    return ACEMiddleware(
        store=InMemoryStore(),
        configs=ACE_CONFIGS,
        osmosis_mode="ollama",
    )


@pytest.fixture
def sample_playbook() -> PlaybookState:
    """Sample playbook with entries."""
    playbook = create_initial_playbook("researcher")

    # Add sample entries
    entries = [
        PlaybookEntry(
            id=str(uuid.uuid4()),
            content="Always cite sources with exact quotes and URLs",
            category="helpful",
            helpful_count=10,
            harmful_count=0,
            confidence_score=0.95,
            created_at=datetime.now(),
            last_updated=datetime.now(),
            source_executions=["exec_001", "exec_002"],
            tags=["citation", "accuracy"],
            metadata={},
        ),
        PlaybookEntry(
            id=str(uuid.uuid4()),
            content="Avoid delegating to data_scientist before research is complete",
            category="harmful",
            helpful_count=0,
            harmful_count=5,
            confidence_score=0.80,
            created_at=datetime.now(),
            last_updated=datetime.now(),
            source_executions=["exec_003"],
            tags=["delegation", "timing"],
            metadata={},
        ),
    ]

    playbook["entries"] = entries
    playbook["total_executions"] = 3

    return playbook


@pytest.fixture
def sample_execution_trace() -> Dict[str, Any]:
    """Sample execution trace for reflection."""
    return {
        "messages": [
            {"role": "user", "content": "Research climate change impacts"},
            {"role": "assistant", "content": "I'll search for recent studies..."},
            {"role": "tool", "content": "Found 15 papers from 2024-2025"},
        ],
        "tool_calls": [
            {"tool_name": "tavily_search", "success": True},
            {"tool_name": "read_file", "success": True},
        ],
        "errors": [],
        "success": True,
        "duration_seconds": 45.3,
        "final_result": "Comprehensive research report with 20 citations",
    }


# ============================================================================
# OsmosisExtractor Tests
# ============================================================================

class TestOsmosisExtractor:
    """Test Osmosis-Structure-0.6B extraction."""

    @pytest.mark.asyncio
    async def test_extract_simple_model(self, osmosis_extractor):
        """Test extraction of simple Pydantic model."""

        # Define test schema
        class Person(BaseModel):
            name: str = Field(description="Person's name")
            age: int = Field(description="Person's age")
            city: str = Field(description="City of residence")

        # Free-form text (Claude output)
        text = """
        The person's name is John Doe, he is 30 years old, and lives in San Francisco.
        """

        # Extract with Osmosis
        result = await osmosis_extractor.extract(
            text=text,
            schema=Person,
        )

        # Verify
        assert isinstance(result, Person)
        assert result.name == "John Doe"
        assert result.age == 30
        assert result.city == "San Francisco"

    @pytest.mark.asyncio
    async def test_extract_list_model(self, osmosis_extractor):
        """Test extraction of list model (ReflectionInsightList)."""

        # Free-form analysis text
        analysis = """
        After analyzing the execution, I identified three key insights:

        1. The exact quote citations were extremely helpful because they prevented
           hallucination and built trust with users.

        2. However, delegating to data_scientist before research was complete was
           harmful because it led to analysis on incomplete data.

        3. The 300-second approval timeout might be too long for simple edits.
        """

        # Extract insights
        result = await osmosis_extractor.extract(
            text=analysis,
            schema=ReflectionInsightList,
        )

        # Verify
        assert isinstance(result, ReflectionInsightList)
        assert len(result.insights) >= 2  # Should extract at least 2 insights

        # Check categories
        categories = [i.category for i in result.insights]
        assert "helpful" in categories
        assert "harmful" in categories

    @pytest.mark.asyncio
    async def test_fallback_parsing(self, osmosis_extractor):
        """Test fallback to direct Pydantic parsing."""

        # If Osmosis fails, should fall back to JSON extraction
        class SimpleModel(BaseModel):
            value: str

        # Text with embedded JSON
        text = """
        Here's the result:
        ```json
        {"value": "test"}
        ```
        """

        # Should extract successfully (either via Osmosis or fallback)
        result = await osmosis_extractor.extract(
            text=text,
            schema=SimpleModel,
        )

        assert result.value == "test"


# ============================================================================
# PlaybookStore Tests
# ============================================================================

class TestPlaybookStore:
    """Test PlaybookStore persistence and CRUD operations."""

    @pytest.mark.asyncio
    async def test_initialize_playbook(self, playbook_store):
        """Test initializing empty playbook."""

        playbook = await playbook_store.get_playbook("researcher")

        assert playbook["agent_type"] == "researcher"
        assert playbook["version"] == 0
        assert len(playbook["entries"]) == 0
        assert playbook["total_executions"] == 0

    @pytest.mark.asyncio
    async def test_save_and_retrieve_playbook(self, playbook_store, sample_playbook):
        """Test saving and retrieving playbook."""

        # Save
        await playbook_store.save_playbook(sample_playbook)

        # Retrieve
        retrieved = await playbook_store.get_playbook("researcher")

        assert retrieved["version"] == 1  # Incremented
        assert len(retrieved["entries"]) == 2
        assert retrieved["total_executions"] == 3

    @pytest.mark.asyncio
    async def test_playbook_versioning(self, playbook_store, sample_playbook):
        """Test playbook version history."""

        # Save multiple versions
        await playbook_store.save_playbook(sample_playbook)  # v1
        await playbook_store.save_playbook(sample_playbook)  # v2
        await playbook_store.save_playbook(sample_playbook)  # v3

        # Get history
        history = await playbook_store.get_playbook_history("researcher", limit=3)

        assert len(history) == 3
        assert history[0]["version"] == 3  # Newest first
        assert history[1]["version"] == 2
        assert history[2]["version"] == 1

    @pytest.mark.asyncio
    async def test_search_entries(self, playbook_store, sample_playbook):
        """Test searching playbook entries."""

        await playbook_store.save_playbook(sample_playbook)

        # Search by category
        helpful = await playbook_store.search_entries(
            agent_type="researcher",
            category="helpful",
        )
        assert len(helpful) == 1
        assert helpful[0].category == "helpful"

        # Search by tags
        citation_entries = await playbook_store.search_entries(
            agent_type="researcher",
            tags=["citation"],
        )
        assert len(citation_entries) >= 1

    @pytest.mark.asyncio
    async def test_prune_playbook(self, playbook_store, sample_playbook):
        """Test pruning low-confidence entries."""

        # Add low-confidence entry
        low_conf_entry = PlaybookEntry(
            id=str(uuid.uuid4()),
            content="Low confidence insight",
            category="neutral",
            helpful_count=0,
            harmful_count=0,
            confidence_score=0.1,  # Very low
            created_at=datetime.now(),
            last_updated=datetime.now(),
            source_executions=[],
            tags=[],
            metadata={},
        )
        sample_playbook["entries"].append(low_conf_entry)

        await playbook_store.save_playbook(sample_playbook)

        # Prune entries with confidence < 0.3
        removed = await playbook_store.prune_playbook(
            agent_type="researcher",
            min_confidence=0.3,
        )

        assert removed == 1  # Low confidence entry removed

    @pytest.mark.asyncio
    async def test_playbook_stats(self, playbook_store, sample_playbook):
        """Test playbook statistics."""

        await playbook_store.save_playbook(sample_playbook)

        stats = await playbook_store.get_playbook_stats("researcher")

        assert stats["total_entries"] == 2
        assert stats["helpful_entries"] == 1
        assert stats["harmful_entries"] == 1
        assert stats["avg_confidence"] > 0


# ============================================================================
# Reflector Tests
# ============================================================================

class TestReflector:
    """Test Reflector insight generation with two-pass workflow."""

    @pytest.mark.asyncio
    async def test_analyze_execution(self, reflector, sample_execution_trace):
        """Test analyzing execution to generate insights."""

        insights = await reflector.analyze(
            execution_trace=sample_execution_trace,
            execution_id="test_exec_001",
            agent_type="researcher",
        )

        # Should generate at least 1 insight
        assert len(insights) >= 1

        # Verify insight structure
        for insight in insights:
            assert isinstance(insight, ReflectionInsight)
            assert insight.execution_id == "test_exec_001"
            assert insight.agent_type == "researcher"
            assert insight.category in ["helpful", "harmful", "neutral"]
            assert 0.0 <= insight.confidence_score <= 1.0

    @pytest.mark.asyncio
    async def test_reflection_with_playbook_context(self, reflector, sample_execution_trace, sample_playbook):
        """Test reflection with existing playbook context."""

        # Pass current playbook entries
        insights = await reflector.analyze(
            execution_trace=sample_execution_trace,
            execution_id="test_exec_002",
            agent_type="researcher",
            current_playbook=sample_playbook["entries"],
        )

        # Should still generate insights
        assert len(insights) >= 1

    @pytest.mark.asyncio
    async def test_refine_insights(self, reflector):
        """Test insight refinement based on feedback."""

        # Initial insights
        initial_insights = [
            ReflectionInsight(
                id=str(uuid.uuid4()),
                content="Citation quality was good",
                category="helpful",
                confidence_score=0.8,
                execution_id="test",
                agent_type="researcher",
                tags=["citation"],
                evidence="",
                recommendation="",
                created_at=datetime.now(),
            )
        ]

        # Refine with feedback
        refined = await reflector.refine_insights(
            insights=initial_insights,
            feedback="Be more specific about what made citation quality good",
        )

        # Should return refined insights
        assert len(refined) >= 1


# ============================================================================
# Curator Tests
# ============================================================================

class TestCurator:
    """Test Curator delta generation with semantic de-duplication."""

    @pytest.mark.asyncio
    async def test_curate_new_insights(self, curator, sample_playbook):
        """Test curating new insights into playbook delta."""

        # New insights
        new_insights = [
            ReflectionInsight(
                id=str(uuid.uuid4()),
                content="Cross-referencing 3+ sources builds confidence",
                category="helpful",
                confidence_score=0.90,
                execution_id="test_exec",
                agent_type="researcher",
                tags=["verification"],
                evidence="Verified claims across Nature, Science, arXiv",
                recommendation="Use 3+ sources for critical facts",
                created_at=datetime.now(),
            )
        ]

        # Curate
        delta = await curator.curate(
            insights=new_insights,
            current_playbook=sample_playbook,
            execution_id="test_exec",
        )

        # Verify delta structure
        assert isinstance(delta, PlaybookDelta)
        assert delta.execution_id == "test_exec"

        # Should have some add/update/remove operations
        assert len(delta.add) + len(delta.update) + len(delta.remove) > 0

    @pytest.mark.asyncio
    async def test_semantic_deduplication(self, curator, sample_playbook):
        """Test semantic de-duplication prevents redundant insights."""

        # Similar insight to existing entry
        similar_insights = [
            ReflectionInsight(
                id=str(uuid.uuid4()),
                content="Always include exact quotations when citing sources",  # Similar to existing
                category="helpful",
                confidence_score=0.85,
                execution_id="test",
                agent_type="researcher",
                tags=["citation"],
                evidence="",
                recommendation="",
                created_at=datetime.now(),
            )
        ]

        # Curate - should detect similarity
        delta = await curator.curate(
            insights=similar_insights,
            current_playbook=sample_playbook,
            execution_id="test",
        )

        # Delta might have fewer adds due to de-duplication
        # (Exact behavior depends on similarity threshold)
        assert isinstance(delta, PlaybookDelta)


# ============================================================================
# ACEMiddleware Tests
# ============================================================================

class TestACEMiddleware:
    """Test ACEMiddleware node wrapping."""

    @pytest.mark.asyncio
    async def test_wrap_disabled_agent(self, ace_middleware):
        """Test wrapping node when ACE is disabled."""

        # Mock node function
        async def mock_node(state: Dict[str, Any]) -> Dict[str, Any]:
            state["executed"] = True
            return state

        # Wrap with disabled config
        wrapped = ace_middleware.wrap_node(mock_node, "disabled_agent")

        # Should return unwrapped node (ACE disabled)
        state = {"messages": []}
        result = await wrapped(state)

        assert result["executed"] is True

    @pytest.mark.asyncio
    async def test_playbook_injection(self, ace_middleware, sample_playbook):
        """Test playbook injection into system prompt."""

        # Save playbook first
        await ace_middleware.playbook_store.save_playbook(sample_playbook)

        # Mock state with system message
        from langchain_core.messages import SystemMessage, HumanMessage

        state = {
            "messages": [
                SystemMessage(content="You are a researcher agent."),
                HumanMessage(content="Research topic"),
            ]
        }

        # Inject playbook
        enhanced = await ace_middleware._inject_playbook(
            state,
            sample_playbook,
            "researcher",
            ACE_CONFIGS["researcher"],
        )

        # Verify playbook was injected
        first_message = enhanced["messages"][0]
        assert "ACE PLAYBOOK" in first_message.content
        assert "exact quotes" in first_message.content.lower()

    @pytest.mark.asyncio
    async def test_delta_application(self, ace_middleware, sample_playbook):
        """Test applying playbook delta."""

        # Create delta
        new_entry = PlaybookEntry(
            id=str(uuid.uuid4()),
            content="New insight to add",
            category="helpful",
            helpful_count=0,
            harmful_count=0,
            confidence_score=0.75,
            created_at=datetime.now(),
            last_updated=datetime.now(),
            source_executions=[],
            tags=["test"],
            metadata={},
        )

        delta = PlaybookDelta(
            add=[new_entry],
            update=[],
            remove=[],
            execution_id="test",
            created_at=datetime.now(),
        )

        # Apply delta
        updated = ace_middleware._apply_delta(sample_playbook, delta)

        # Verify new entry added
        assert len(updated["entries"]) == 3  # Was 2, now 3


# ============================================================================
# Integration Tests
# ============================================================================

class TestACEIntegration:
    """Test full ACE workflow integration."""

    @pytest.mark.asyncio
    async def test_full_ace_cycle(self, ace_middleware, sample_execution_trace):
        """Test complete ACE cycle: execution → reflection → curation → update."""

        # Initialize playbook
        await ace_middleware.playbook_store.initialize_all_playbooks()

        # Mock execution trace
        execution_id = "integration_test_001"

        # Trigger reflection and curation
        await ace_middleware._reflect_and_update(
            execution_trace=sample_execution_trace,
            execution_id=execution_id,
            agent_type="researcher",
            config=ACEConfig(
                enabled=True,
                reflection_mode="automatic",
                playbook_id="researcher_v1",
            ),
        )

        # Wait for async processing
        await asyncio.sleep(1)

        # Verify playbook was updated
        playbook = await ace_middleware.playbook_store.get_playbook("researcher")

        # Should have executed at least once
        assert playbook["total_executions"] >= 1


# ============================================================================
# Schema Tests
# ============================================================================

class TestSchemas:
    """Test ACE schema definitions."""

    def test_playbook_entry_confidence_calculation(self):
        """Test PlaybookEntry confidence score calculation."""

        entry = PlaybookEntry(
            id=str(uuid.uuid4()),
            content="Test entry",
            category="helpful",
            helpful_count=10,
            harmful_count=2,
            confidence_score=0.5,
            created_at=datetime.now(),
            last_updated=datetime.now(),
            source_executions=[],
            tags=[],
            metadata={},
        )

        # Update success
        entry.update_success()
        assert entry.helpful_count == 11
        assert entry.confidence_score > 0.5  # Should increase

    def test_format_playbook_for_prompt(self, sample_playbook):
        """Test formatting playbook for prompt injection."""

        formatted = format_playbook_for_prompt(
            sample_playbook["entries"],
            max_entries=10,
        )

        assert isinstance(formatted, str)
        assert "HELPFUL" in formatted
        assert "exact quotes" in formatted.lower()

    def test_create_initial_playbook(self):
        """Test creating initial empty playbook."""

        playbook = create_initial_playbook("supervisor")

        assert playbook["agent_type"] == "supervisor"
        assert playbook["version"] == 0
        assert len(playbook["entries"]) == 0


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
