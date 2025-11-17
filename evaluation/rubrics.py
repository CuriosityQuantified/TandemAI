"""
Evaluation Rubrics for Researcher Agent Performance
====================================================

Defines 7 evaluation categories with detailed scoring criteria.
Each rubric is designed for objective judge agent evaluation.

Version: 1.0
Created: 2025-11-13
"""

from typing import Dict, Any, Literal
from pydantic import BaseModel, Field


# ==============================================================================
# RUBRIC 1: PLANNING QUALITY (BINARY)
# ==============================================================================

class PlanningQualityRubric(BaseModel):
    """Binary evaluation of research planning quality."""

    name: str = "Planning Quality"
    description: str = "Evaluates whether the agent created an appropriate research plan"
    scale: str = "Binary (Good/Poor)"

    criteria: Dict[str, str] = {
        "good": """
        GOOD PLANNING (Score: 1.0):
        ✅ Agent called create_research_plan() for multi-step queries
        ✅ Plan has appropriate number of steps (matches query complexity)
        ✅ Steps are logically ordered and comprehensive
        ✅ Each step has clear action and expected outcome
        ✅ Plan covers all aspects mentioned in the query

        Examples of GOOD:
        - Query: "Compare A vs B" → 5-6 steps (research A, research B, compare)
        - Query: "Latest developments in X" → 4-5 steps (multiple search angles)
        - Query: "Analyze X, Y, and Z" → 6-8 steps (1-2 per topic + synthesis)
        """,

        "poor": """
        POOR PLANNING (Score: 0.0):
        ❌ No plan created for multi-step query requiring planning
        ❌ Plan has too few steps (underestimates complexity)
        ❌ Plan has too many steps (overcomplicates simple query)
        ❌ Steps are illogical, redundant, or poorly ordered
        ❌ Plan misses key aspects of the query

        Examples of POOR:
        - Query: "Compare A vs B" → No plan created, just 1 search
        - Query: "Latest X developments" → Only 1-2 steps (insufficient coverage)
        - Simple query "What is X?" → Created 10-step plan (overkill)
        """
    }

    decision_tree: str = """
    EVALUATION DECISION TREE:

    1. Does the query require planning? (multi-step, comparison, comprehensive, time-constrained)
       YES → Go to step 2
       NO → Skip to step 4

    2. Did agent create a plan?
       YES → Go to step 3
       NO → Score: POOR (0.0)

    3. Is the plan appropriate? (right # steps, logical, comprehensive)
       YES → Score: GOOD (1.0)
       NO → Score: POOR (0.0)

    4. Did agent skip planning correctly? (simple single-fact query)
       YES → Score: GOOD (1.0)
       NO → Score: POOR (0.0)
    """


# ==============================================================================
# RUBRIC 2: EXECUTION COMPLETENESS (1-5 SCALE)
# ==============================================================================

class ExecutionCompletenessRubric(BaseModel):
    """Scaled evaluation of research execution completeness."""

    name: str = "Execution Completeness"
    description: str = "Evaluates how thoroughly the agent executed the research plan"
    scale: str = "1-5 Scale (1=Incomplete, 5=Fully Complete)"

    scoring_guide: Dict[int, str] = {
        5: """
        SCORE 5 - FULLY COMPLETE:
        ✅ ALL planned steps executed
        ✅ All plan steps marked as 'completed'
        ✅ Agent called update_plan_progress() for each step
        ✅ No premature stopping or partial execution
        ✅ Final response synthesizes ALL research

        Evidence required:
        - Plan completion: 100% (e.g., "6/6 steps completed")
        - All steps show status: "completed"
        - Final response references all research areas
        """,

        4: """
        SCORE 4 - MOSTLY COMPLETE:
        ✅ 80-95% of planned steps executed
        ⚠️ Minor aspects skipped (not critical to query)
        ✅ Most steps marked as completed
        ✅ Final response covers main research areas

        Evidence:
        - Plan completion: 80-95% (e.g., "5/6 steps completed")
        - Non-critical step skipped
        - Final response still comprehensive
        """,

        3: """
        SCORE 3 - MODERATELY COMPLETE:
        ⚠️ 60-79% of planned steps executed
        ⚠️ Some important aspects missing
        ⚠️ Several steps not completed
        ⚠️ Final response has noticeable gaps

        Evidence:
        - Plan completion: 60-79% (e.g., "4/6 steps completed")
        - Moderate gaps in coverage
        - Response incomplete but useful
        """,

        2: """
        SCORE 2 - MINIMALLY COMPLETE:
        ❌ 30-59% of planned steps executed
        ❌ Major aspects missing
        ❌ Most steps not completed
        ❌ Final response is partial/incomplete

        Evidence:
        - Plan completion: 30-59% (e.g., "2/6 steps completed")
        - Significant gaps in research
        - Premature stopping
        """,

        1: """
        SCORE 1 - INCOMPLETE:
        ❌ <30% of planned steps executed
        ❌ Critical failures in execution
        ❌ Almost no steps completed
        ❌ Final response severely incomplete

        Evidence:
        - Plan completion: <30% (e.g., "1/6 steps completed")
        - Research barely started
        - Response useless or missing
        """
    }


# ==============================================================================
# RUBRIC 3: SOURCE QUALITY (1-5 SCALE)
# ==============================================================================

class SourceQualityRubric(BaseModel):
    """Scaled evaluation of research source quality."""

    name: str = "Source Quality"
    description: str = "Evaluates the credibility and relevance of sources used"
    scale: str = "1-5 Scale (1=Poor Sources, 5=Excellent Sources)"

    scoring_guide: Dict[int, str] = {
        5: """
        SCORE 5 - EXCELLENT SOURCES:
        ✅ All sources are authoritative and credible
        ✅ Primary sources or peer-reviewed research
        ✅ Recent publications (within relevant timeframe)
        ✅ Multiple independent sources corroborate claims
        ✅ Sources directly relevant to query

        Examples of excellent sources:
        - Scientific journals (Nature, Science, NEJM)
        - Official documentation (language framework docs)
        - Reputable news outlets (NYT, WSJ, Reuters)
        - Government/academic institutions
        - Industry leaders' official publications
        """,

        4: """
        SCORE 4 - GOOD SOURCES:
        ✅ Most sources are credible
        ✅ Mix of primary and secondary sources
        ⚠️ Minor reliance on less authoritative sources
        ✅ Sources are recent and relevant

        Examples:
        - Tech blogs from reputable companies
        - Industry analysis from known firms
        - Well-regarded trade publications
        - Established tech news sites
        """,

        3: """
        SCORE 3 - ACCEPTABLE SOURCES:
        ⚠️ Mix of credible and less credible sources
        ⚠️ Some sources lack authority
        ⚠️ Some outdated information
        ⚠️ Limited source diversity

        Examples:
        - General news aggregators
        - Personal blogs (with expertise)
        - Wikipedia (as starting point)
        - Forum discussions (with caveats)
        """,

        2: """
        SCORE 2 - POOR SOURCES:
        ❌ Many sources lack credibility
        ❌ Heavy reliance on secondary/tertiary sources
        ❌ Outdated information
        ❌ Limited source diversity

        Examples:
        - Random blogs without credentials
        - Outdated articles (>5 years for tech)
        - Single-source research
        - Promotional/marketing content
        """,

        1: """
        SCORE 1 - UNACCEPTABLE SOURCES:
        ❌ Sources are unreliable or non-existent
        ❌ No credible sources cited
        ❌ Misinformation or propaganda
        ❌ Completely irrelevant sources

        Examples:
        - No sources provided
        - Conspiracy sites
        - Unverified social media
        - Completely off-topic sources
        """
    }


# ==============================================================================
# RUBRIC 4: CITATION ACCURACY (BINARY)
# ==============================================================================

class CitationAccuracyRubric(BaseModel):
    """Binary evaluation of citation accuracy and attribution."""

    name: str = "Citation Accuracy"
    description: str = "Evaluates whether citations are accurate and properly attributed"
    scale: str = "Binary (Correct/Incorrect)"

    criteria: Dict[str, str] = {
        "correct": """
        CORRECT CITATIONS (Score: 1.0):
        ✅ All factual claims have source attribution
        ✅ Direct quotes use quotation marks
        ✅ Source URLs are valid and accessible
        ✅ Citations match the actual source content
        ✅ No hallucinated sources or fake citations

        Required format:
        - Inline citations: "According to [Source Name], 'exact quote' (URL)"
        - Reference format: Clear source identification
        - Verification: Random spot-checks confirm accuracy

        Examples of CORRECT:
        - "LangChain v0.3 introduced LCEL" [langchain.com/docs]
        - "According to Nature (2025), 'CRISPR efficiency improved by 40%' (nature.com/articles/xyz)"
        """,

        "incorrect": """
        INCORRECT CITATIONS (Score: 0.0):
        ❌ Factual claims without attribution
        ❌ Quotes without quotation marks or sources
        ❌ Invalid or broken URLs
        ❌ Citations don't match source content
        ❌ Hallucinated/fabricated sources

        Examples of INCORRECT:
        - "Studies show X" (no source specified)
        - Claims without any citations
        - URL returns 404 or wrong content
        - "According to Nature..." but no such article exists
        """
    }


# ==============================================================================
# RUBRIC 5: ANSWER COMPLETENESS (1-5 SCALE)
# ==============================================================================

class AnswerCompletenessRubric(BaseModel):
    """Scaled evaluation of final answer completeness."""

    name: str = "Answer Completeness"
    description: str = "Evaluates how completely the final answer addresses the query"
    scale: str = "1-5 Scale (1=Minimal, 5=Comprehensive)"

    scoring_guide: Dict[int, str] = {
        5: """
        SCORE 5 - COMPREHENSIVE:
        ✅ Addresses ALL aspects of the query
        ✅ Provides sufficient depth on each aspect
        ✅ Includes context and nuance
        ✅ Answers follow-up questions preemptively
        ✅ Well-structured and easy to understand

        Example for "Compare A vs B":
        - Detailed analysis of A (multiple dimensions)
        - Detailed analysis of B (same dimensions)
        - Direct comparison on each dimension
        - Trade-offs and use case recommendations
        - Summary of key differences
        """,

        4: """
        SCORE 4 - MOSTLY COMPLETE:
        ✅ Addresses most aspects of the query
        ✅ Good depth on main topics
        ⚠️ Minor aspects could be expanded
        ✅ Well-structured

        Example:
        - Covers A and B thoroughly
        - Comparison present but could be deeper
        - Most questions answered
        """,

        3: """
        SCORE 3 - MODERATELY COMPLETE:
        ⚠️ Addresses main aspects but misses some
        ⚠️ Adequate depth but not comprehensive
        ⚠️ Some questions left unanswered
        ⚠️ Structure is acceptable

        Example:
        - Covers A and B at surface level
        - Limited comparison
        - Leaves obvious questions unanswered
        """,

        2: """
        SCORE 2 - MINIMALLY COMPLETE:
        ❌ Addresses only some aspects
        ❌ Shallow treatment of topics
        ❌ Many questions unanswered
        ❌ Poor structure

        Example:
        - Covers only A or only B
        - Minimal comparison
        - Superficial analysis
        """,

        1: """
        SCORE 1 - INCOMPLETE:
        ❌ Fails to address query properly
        ❌ Extremely shallow or off-topic
        ❌ Critical questions unanswered
        ❌ Incoherent or missing

        Example:
        - Doesn't address A or B meaningfully
        - No comparison provided
        - Response is useless
        """
    }


# ==============================================================================
# RUBRIC 6: FACTUAL ACCURACY (BINARY)
# ==============================================================================

class FactualAccuracyRubric(BaseModel):
    """Binary evaluation of factual accuracy."""

    name: str = "Factual Accuracy"
    description: str = "Evaluates whether the information provided is factually accurate"
    scale: str = "Binary (Accurate/Inaccurate)"

    criteria: Dict[str, str] = {
        "accurate": """
        FACTUALLY ACCURATE (Score: 1.0):
        ✅ All verifiable facts are correct
        ✅ No significant factual errors detected
        ✅ Claims are supported by sources
        ✅ Dates, numbers, and names are accurate
        ✅ No misleading statements

        Verification method:
        - Cross-check key facts against sources
        - Verify dates and version numbers
        - Confirm technical specifications
        - Check for internal consistency

        Tolerance:
        - Minor typos acceptable (e.g., "Oct 28" vs "Oct 27" for recent events)
        - Rounding acceptable (e.g., "approximately 1000" vs "1023")
        - No tolerance for: wrong years, wrong companies, wrong products
        """,

        "inaccurate": """
        FACTUALLY INACCURATE (Score: 0.0):
        ❌ Contains significant factual errors
        ❌ Dates, numbers, or names are wrong
        ❌ Misrepresents source information
        ❌ Makes unsupported claims
        ❌ Contains hallucinations

        Examples of inaccurate:
        - "LangChain v2.0 released in 2023" (version/date wrong)
        - "Python is a compiled language" (fundamental error)
        - "NASA landed on Mars in 1969" (wrong mission/date)
        - Claims contradicting provided sources
        """
    }


# ==============================================================================
# RUBRIC 7: AUTONOMY SCORE (BINARY)
# ==============================================================================

class AutonomyScoreRubric(BaseModel):
    """Binary evaluation of agent autonomy."""

    name: str = "Autonomy Score"
    description: str = "Evaluates whether the agent executed autonomously without seeking user input"
    scale: str = "Binary (Autonomous/Non-autonomous)"

    criteria: Dict[str, str] = {
        "autonomous": """
        AUTONOMOUS (Score: 1.0):
        ✅ Agent executed task without asking for permission
        ✅ No mid-execution questions to user
        ✅ Completed full research plan independently
        ✅ Made reasonable decisions autonomously
        ✅ Provided complete result without prompting

        Acceptable agent behavior:
        - Create plan → Execute all steps → Provide complete answer
        - Use tools as needed without asking
        - Update progress autonomously
        - Make research decisions independently

        Examples of autonomous:
        - "I will research X, Y, and Z..." → [executes] → [complete answer]
        - Plan created → All 6 steps executed → Synthesis provided
        - No questions like "Should I continue?" or "Would you like more detail?"
        """,

        "non_autonomous": """
        NON-AUTONOMOUS (Score: 0.0):
        ❌ Agent asked for user input mid-execution
        ❌ Sought permission to continue
        ❌ Provided partial results and asked if more needed
        ❌ Required prompting to complete task
        ❌ Asked clarifying questions unnecessarily

        Examples of non-autonomous:
        - "I've completed steps 1-3. Would you like me to continue?"
        - "Should I search for more information on X?"
        - "I found some results. Do you want more details?"
        - Stops at step 3/6 without completing
        - Asks "How should I proceed?" for straightforward queries
        """
    }


# ==============================================================================
# EVALUATION RESULT MODELS
# ==============================================================================

class BinaryScore(BaseModel):
    """Binary evaluation score (0 or 1)."""
    score: Literal[0, 1] = Field(
        description="Binary score: 1 for positive criteria met, 0 otherwise"
    )
    reasoning: str = Field(
        description="Detailed explanation for the score with evidence from the response"
    )


class ScaledScore(BaseModel):
    """Scaled evaluation score (1-5)."""
    score: Literal[1, 2, 3, 4, 5] = Field(
        description="Integer score from 1 (worst) to 5 (best)"
    )
    reasoning: str = Field(
        description="Detailed explanation for the score with evidence from the response"
    )


class EvaluationResult(BaseModel):
    """Complete evaluation result for a single query."""
    query_id: str  # Changed from int to str to support string IDs like "SIMPLE-001"
    query_text: str
    prompt_version: str  # "benchmark" or "challenger_1", etc.

    # 7 evaluation dimensions
    planning_quality: BinaryScore
    execution_completeness: ScaledScore
    source_quality: ScaledScore
    citation_accuracy: BinaryScore
    answer_completeness: ScaledScore
    factual_accuracy: BinaryScore
    autonomy_score: BinaryScore

    # Metadata
    evaluation_timestamp: str
    judge_version: str = "1.0"

    @property
    def overall_score(self) -> float:
        """
        Calculate overall score as sum of all 7 judge scores.

        Binary scores contribute 0-1 each, scaled scores contribute 1-5 each.
        Maximum possible score: 4 (binary) + 15 (scaled) = 19
        Minimum possible score: 0 (binary) + 3 (scaled) = 3

        Returns:
            Sum of all 7 scores (raw, not normalized)
        """
        return (
            self.planning_quality.score +
            self.execution_completeness.score +
            self.source_quality.score +
            self.citation_accuracy.score +
            self.answer_completeness.score +
            self.factual_accuracy.score +
            self.autonomy_score.score
        )


# ==============================================================================
# RUBRIC REGISTRY
# ==============================================================================

RUBRICS = {
    "planning_quality": PlanningQualityRubric(),
    "execution_completeness": ExecutionCompletenessRubric(),
    "source_quality": SourceQualityRubric(),
    "citation_accuracy": CitationAccuracyRubric(),
    "answer_completeness": AnswerCompletenessRubric(),
    "factual_accuracy": FactualAccuracyRubric(),
    "autonomy_score": AutonomyScoreRubric(),
}


def get_rubric(rubric_name: str) -> BaseModel:
    """Get a rubric by name."""
    if rubric_name not in RUBRICS:
        raise ValueError(f"Unknown rubric: {rubric_name}. Available: {list(RUBRICS.keys())}")
    return RUBRICS[rubric_name]


def get_all_rubrics() -> Dict[str, BaseModel]:
    """Get all rubrics."""
    return RUBRICS


# ==============================================================================
# RUBRIC SUMMARY FOR JUDGE AGENTS
# ==============================================================================

def get_rubric_summary(rubric_name: str) -> str:
    """Get a concise summary of a rubric for judge agent prompts."""
    rubric = get_rubric(rubric_name)

    summary = f"""
{rubric.name}
{'=' * len(rubric.name)}

Description: {rubric.description}
Scale: {rubric.scale}

"""

    if hasattr(rubric, 'criteria'):
        summary += "Criteria:\n"
        for key, value in rubric.criteria.items():
            summary += f"\n{key.upper()}:\n{value}\n"

    if hasattr(rubric, 'scoring_guide'):
        summary += "\nScoring Guide:\n"
        for score, description in rubric.scoring_guide.items():
            summary += f"\nSCORE {score}:\n{description}\n"

    if hasattr(rubric, 'decision_tree'):
        summary += f"\n{rubric.decision_tree}\n"

    return summary


if __name__ == "__main__":
    # Test: Print all rubrics
    print("=" * 80)
    print("EVALUATION RUBRICS FOR RESEARCHER AGENT")
    print("=" * 80)

    for name, rubric in RUBRICS.items():
        print(f"\n{rubric.name}")
        print(f"Scale: {rubric.scale}")
        print(f"Description: {rubric.description}")
        print("-" * 80)

    print("\n✅ All rubrics loaded successfully!")
    print(f"Total rubrics: {len(RUBRICS)}")
