"""
Curator: Generate playbook deltas from reflection insights.

Uses two-pass workflow:
1. Claude reasons about de-duplication and updates (free-form)
2. Osmosis extracts structured PlaybookDelta

Includes semantic de-duplication using embeddings to prevent redundant entries.

The curator implements the "Curator" role from ACE framework:
- Decides which insights to add to playbook
- Updates existing entries based on new evidence
- Removes low-quality or outdated entries
- Prevents duplication through semantic similarity
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.embeddings import Embeddings
from langchain_community.embeddings import OllamaEmbeddings
import numpy as np

from ace.schemas import (
    ReflectionInsight,
    PlaybookState,
    PlaybookDelta,
    PlaybookEntry,
)
from ace.osmosis_extractor import OsmosisExtractor

logger = logging.getLogger(__name__)


class Curator:
    """
    Generate playbook deltas from reflection insights.

    Two-pass workflow:
    1. Pass 1: Claude reasons about de-duplication and updates
    2. Pass 2: Osmosis extracts structured PlaybookDelta

    Includes semantic de-duplication to prevent redundant entries.
    """

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        osmosis: Optional[OsmosisExtractor] = None,
        embeddings: Optional[Embeddings] = None,
        similarity_threshold: float = 0.85,
        temperature: float = 0.3,
    ):
        """
        Initialize Curator.

        Args:
            model: Claude model for curation reasoning
            osmosis: OsmosisExtractor instance (creates default if None)
            embeddings: Embeddings model for semantic de-duplication (default: nomic-embed-text via Ollama)
            similarity_threshold: Similarity threshold for de-duplication (0.0-1.0)
            temperature: LLM temperature (0.3 for consistent curation decisions)
        """
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
        )
        self.osmosis = osmosis or OsmosisExtractor(mode="ollama")
        # Use fast local embeddings via Ollama (nomic-embed-text: 274MB, very fast, 8K context)
        self.embeddings = embeddings or OllamaEmbeddings(model="nomic-embed-text")
        self.similarity_threshold = similarity_threshold

        logger.info(
            f"Initialized Curator with {model} and local Ollama embeddings "
            f"(similarity_threshold={similarity_threshold})"
        )

    async def curate(
        self,
        insights: List[ReflectionInsight],
        current_playbook: PlaybookState,
        execution_id: str,
    ) -> PlaybookDelta:
        """
        Generate playbook delta from reflection insights.

        Two-pass workflow:
        1. Claude analyzes insights vs current playbook, reasons about updates
        2. Osmosis extracts structured PlaybookDelta (add/update/remove)

        Args:
            insights: New reflection insights from execution
            current_playbook: Current playbook state
            execution_id: Execution that generated insights

        Returns:
            PlaybookDelta with add/update/remove operations
        """
        logger.info(
            f"Curating {len(insights)} insights against "
            f"{len(current_playbook['entries'])} playbook entries"
        )

        # Semantic de-duplication
        deduplicated_insights = await self._deduplicate_insights(
            insights,
            current_playbook,
        )

        logger.info(
            f"De-duplication: {len(insights)} → {len(deduplicated_insights)} insights "
            f"({len(insights) - len(deduplicated_insights)} duplicates removed)"
        )

        # PASS 1: Claude free-form curation reasoning
        curation_prompt = self._build_curation_prompt(
            deduplicated_insights,
            current_playbook,
        )

        messages = [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content=curation_prompt),
        ]

        logger.debug("Pass 1: Claude reasoning about curation...")
        response = await self.llm.ainvoke(messages)
        curation_text = response.content

        logger.debug(f"Pass 1 complete: {len(curation_text)} chars of reasoning")

        # PASS 2: Osmosis structured delta extraction
        logger.debug("Pass 2: Osmosis extracting delta...")
        delta = await self.osmosis.extract(
            text=curation_text,
            schema=PlaybookDelta,
        )

        logger.info(
            f"✓ Delta: +{len(delta.add)} entries, "
            f"~{len(delta.update)} updates, "
            f"-{len(delta.remove)} removals"
        )

        # Enrich delta metadata
        delta.execution_id = execution_id
        delta.created_at = datetime.now()

        return delta

    def _get_system_prompt(self) -> str:
        """Get system prompt for Claude's curation reasoning (Pass 1)."""
        return """You are an expert curator managing a playbook of learnings for an AI agent.

Your role is to decide how to update the playbook based on new insights from recent executions:
- ADD valuable new insights that aren't redundant
- UPDATE existing entries with new evidence or refinements
- REMOVE low-quality or outdated entries

Be strategic. Focus on long-term value. Avoid redundancy. Think step by step.

IMPORTANT: Write your curation reasoning in natural language. Do NOT format as JSON.
Focus on making smart decisions. Structure will be extracted later."""

    async def _deduplicate_insights(
        self,
        insights: List[ReflectionInsight],
        current_playbook: PlaybookState,
    ) -> List[ReflectionInsight]:
        """
        Remove insights that are too similar to existing playbook entries.

        Uses semantic similarity (embeddings) instead of exact matching.

        Args:
            insights: New insights to check
            current_playbook: Current playbook state

        Returns:
            Deduplicated list of insights
        """
        if not current_playbook["entries"]:
            logger.debug("Playbook empty - no deduplication needed")
            return insights

        # Generate embeddings for new insights
        insight_texts = [i.content for i in insights]
        logger.debug(f"Generating embeddings for {len(insight_texts)} insights...")
        insight_embeddings = await self.embeddings.aembed_documents(insight_texts)

        # Generate embeddings for existing entries
        entry_texts = [e.content for e in current_playbook["entries"]]
        logger.debug(f"Generating embeddings for {len(entry_texts)} playbook entries...")
        entry_embeddings = await self.embeddings.aembed_documents(entry_texts)

        # Filter out duplicates
        deduplicated = []
        duplicate_count = 0

        for i, insight in enumerate(insights):
            insight_vec = np.array(insight_embeddings[i])

            # Normalize vector
            insight_vec = insight_vec / np.linalg.norm(insight_vec)

            # Check similarity to all existing entries
            max_similarity = 0.0
            most_similar_entry = None

            for j, entry_vec in enumerate(entry_embeddings):
                # Normalize
                entry_vec_norm = np.array(entry_vec) / np.linalg.norm(entry_vec)

                # Cosine similarity
                similarity = np.dot(insight_vec, entry_vec_norm)
                if similarity > max_similarity:
                    max_similarity = similarity
                    most_similar_entry = current_playbook["entries"][j].content

            # Keep if sufficiently different
            if max_similarity < self.similarity_threshold:
                deduplicated.append(insight)
                logger.debug(
                    f"✓ Insight {i+1}: Novel (max_similarity={max_similarity:.3f})"
                )
            else:
                duplicate_count += 1
                logger.debug(
                    f"✗ Insight {i+1}: Duplicate (similarity={max_similarity:.3f} "
                    f"to '{most_similar_entry[:50]}...')"
                )

        logger.info(
            f"De-duplication removed {duplicate_count} similar insights "
            f"(threshold={self.similarity_threshold})"
        )

        return deduplicated

    def _build_curation_prompt(
        self,
        insights: List[ReflectionInsight],
        current_playbook: PlaybookState,
    ) -> str:
        """Build prompt for Claude's curation reasoning (Pass 1)."""

        playbook_summary = self._format_playbook_entries(current_playbook["entries"])
        insights_summary = self._format_insights(insights)

        prompt = f"""You are curating a playbook of learnings for the {current_playbook['agent_type']} agent.

You have NEW insights from a recent execution and need to decide how to update the CURRENT playbook.

═══════════════════════════════════════════════════════════════════════════
CURRENT PLAYBOOK ({len(current_playbook['entries'])} entries)
═══════════════════════════════════════════════════════════════════════════

{playbook_summary}

═══════════════════════════════════════════════════════════════════════════
NEW INSIGHTS ({len(insights)} insights - already de-duplicated)
═══════════════════════════════════════════════════════════════════════════

{insights_summary}

═══════════════════════════════════════════════════════════════════════════
CURATION TASK
═══════════════════════════════════════════════════════════════════════════

Analyze the new insights and decide how to update the playbook:

1. **ADD**: Which new insights are valuable and not redundant?
   Consider:
   - Novel helpful patterns worth preserving
   - New harmful patterns to avoid
   - Interesting neutral observations
   - Long-term value to the agent
   - Specificity and actionability

2. **UPDATE**: Which existing entries should be refined?
   Consider:
   - Insights that strengthen existing entries (increment helpful_count/harmful_count)
   - Insights that contradict existing entries (update content or category)
   - Entries that need better wording or clarity
   - Confidence score adjustments based on new evidence

3. **REMOVE**: Which existing entries are no longer useful?
   Consider:
   - Entries with very low confidence (<0.2)
   - Entries contradicted by recent insights
   - Outdated or superseded patterns
   - Entries that haven't been helpful in recent executions

For each operation:
- Explain WHY you're making this decision (reasoning)
- Be specific about WHAT to add/update/remove
- Think about long-term value to the agent
- Consider execution context and frequency

Think step by step. Be strategic. Prioritize quality over quantity.

IMPORTANT: Write your reasoning in natural language. Do NOT format as JSON.
Focus on making smart curation decisions. Structure will be extracted later.
"""
        return prompt

    def _format_playbook_entries(self, entries: List[PlaybookEntry]) -> str:
        """Format playbook entries for prompt."""
        if not entries:
            return "Empty playbook - no existing entries"

        # Sort by confidence (show top entries)
        sorted_entries = sorted(
            entries,
            key=lambda e: e.confidence_score,
            reverse=True,
        )

        formatted = []
        for i, entry in enumerate(sorted_entries[:20], 1):  # Top 20
            conf = entry.confidence_score
            cat = entry.category
            helpful = entry.helpful_count
            harmful = entry.harmful_count

            content = entry.content[:150]
            if len(entry.content) > 150:
                content += "..."

            formatted.append(
                f"{i}. [{cat}] (confidence: {conf:.2f}, +{helpful}/-{harmful}) "
                f"{content}"
            )

        if len(entries) > 20:
            formatted.append(f"\n... and {len(entries) - 20} more entries")

        return "\n".join(formatted)

    def _format_insights(self, insights: List[ReflectionInsight]) -> str:
        """Format new insights for prompt."""
        if not insights:
            return "No new insights"

        formatted = []
        for i, insight in enumerate(insights, 1):
            cat = insight.category
            conf = insight.confidence_score
            content = insight.content

            recommendation = ""
            if insight.recommendation:
                recommendation = f"\n   → {insight.recommendation}"

            formatted.append(
                f"{i}. [{cat}] (confidence: {conf:.2f})\n"
                f"   {content}{recommendation}"
            )

        return "\n".join(formatted)


# Example usage
async def example():
    """Example: Curate playbook with new insights."""
    from ace.schemas import create_initial_playbook
    import uuid

    curator = Curator()

    # Mock current playbook
    current_playbook = create_initial_playbook("researcher")

    # Add some existing entries
    existing_entry = PlaybookEntry(
        id=str(uuid.uuid4()),
        content="Always include exact quotes when citing sources",
        category="helpful",
        helpful_count=10,
        harmful_count=0,
        confidence_score=0.95,
        created_at=datetime.now(),
        last_updated=datetime.now(),
        source_executions=["exec_001", "exec_002"],
        tags=["citation", "accuracy"],
        metadata={},
    )
    current_playbook["entries"].append(existing_entry)

    # Mock new insights
    new_insights = [
        ReflectionInsight(
            id=str(uuid.uuid4()),
            content="Cross-referencing 3+ sources for important claims builds confidence",
            category="helpful",
            confidence_score=0.90,
            execution_id="exec_003",
            agent_type="researcher",
            tags=["verification", "cross-reference"],
            evidence="Quantum supremacy claim verified in Nature, Science, arXiv",
            recommendation="Use 3+ sources for critical facts",
            created_at=datetime.now(),
        ),
        ReflectionInsight(
            id=str(uuid.uuid4()),
            content="Redundant file reads add unnecessary latency",
            category="harmful",
            confidence_score=0.75,
            execution_id="exec_003",
            agent_type="researcher",
            tags=["performance", "file_io"],
            evidence="Same file read 3 times in one execution",
            recommendation="Cache file content after first read",
            created_at=datetime.now(),
        ),
    ]

    try:
        # Curate playbook (two-pass workflow)
        delta = await curator.curate(
            insights=new_insights,
            current_playbook=current_playbook,
            execution_id="exec_003",
        )

        print(f"\n✓ Playbook Delta Generated:\n")
        print(f"ADD {len(delta.add)} new entries:")
        for entry in delta.add:
            print(f"  - [{entry.category}] {entry.content[:80]}...")

        print(f"\nUPDATE {len(delta.update)} existing entries:")
        for update in delta.update:
            print(f"  - Entry {update.entry_id[:8]}...")
            for key, value in update.updates.items():
                print(f"    {key}: {value}")

        print(f"\nREMOVE {len(delta.remove)} entries:")
        for entry_id in delta.remove:
            print(f"  - {entry_id[:8]}...")

    except Exception as e:
        print(f"✗ Curation failed: {e}")

    finally:
        await curator.osmosis.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(example())
