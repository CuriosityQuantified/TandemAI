# Critical Fixes Implementation Plan

**Date**: 2025-11-13
**Status**: IN PROGRESS
**Priority**: Fix blocking issues before benchmark evaluation

---

## Summary of Critical Issues

Based on cross-file dependency review, we have **3 remaining critical issues** blocking execution:

1. ✅ **RESOLVED**: `shared_tools.py` exists with correct exports (not a blocker)
2. 🔴 **CRITICAL**: TodoListMiddleware import fails (non-existent LangChain module)
3. 🔴 **CRITICAL**: `get_researcher_prompt` ambiguous import (could use wrong version)
4. 🔴 **CRITICAL**: TestQuery type inconsistency (TypedDict vs dict literals)

---

## Fix #1: TodoListMiddleware Import ✅ IN PROGRESS

### Problem
`test_config_1_with_todomiddleware.py:64` imports from non-existent module:
```python
from langchain.agents.middleware import TodoListMiddleware, AgentState
```

**Impact**: File cannot execute, blocks TodoMiddleware investigation comparison

### Solution
Create local stub implementation to allow investigation file to run.

**Files to modify**:
1. Create `/backend/test_configs/todo_list_middleware_stub.py` (new)
2. Update `/backend/test_configs/test_config_1_with_todomiddleware.py` import (line 64)

### Implementation

#### Step 1: Create TodoListMiddleware Stub

```python
# File: /backend/test_configs/todo_list_middleware_stub.py
"""
Stub Implementation of TodoListMiddleware

NOTE: This is a local implementation created because LangChain doesn't have
TodoListMiddleware yet. This was created as part of an investigation into
what TodoListMiddleware would look like if it existed.

Reference: https://docs.langchain.com/oss/python/langchain/middleware/built-in#to-do-list
Status: Planned feature, not yet released
"""

from typing import TypedDict, NotRequired
from typing_extensions import Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    Base state type that TodoListMiddleware expects.

    Includes standard message history and optional todos tracking.
    """
    messages: Annotated[list, add_messages]


class TodoListMiddlewareStub:
    """
    STUB: Simulates what LangChain's TodoListMiddleware would do.

    This is a placeholder implementation for investigation purposes.
    In production, use custom planning tools instead.

    Real TodoListMiddleware (when released) will:
    - Automatically inject todo management into system prompts
    - Provide write_todos tool
    - Track task completion
    - Persist todos in state
    """

    def __init__(self):
        """Initialize stub middleware"""
        pass

    def __call__(self, state: dict) -> dict:
        """
        Pass-through for now. Real implementation would:
        1. Inject todo guidance into system prompts
        2. Track todo updates
        3. Provide progress monitoring
        """
        return state


# Backward compatibility alias
TodoListMiddleware = TodoListMiddlewareStub
```

#### Step 2: Update test_config_1_with_todomiddleware.py

Replace line 64:
```python
# OLD (broken):
from langchain.agents.middleware import TodoListMiddleware, AgentState

# NEW (working):
from todo_list_middleware_stub import TodoListMiddleware, AgentState
```

Add comment explaining this is investigative code:
```python
# TodoListMiddleware import (STUB - LangChain doesn't have this yet)
# This file investigates what the API would look like when released
from todo_list_middleware_stub import TodoListMiddleware, AgentState
```

---

## Fix #2: Ambiguous get_researcher_prompt Import 🔴 TODO

### Problem
`test_config_1_with_todomiddleware.py:77` imports:
```python
from prompts.researcher import get_researcher_prompt
```

But BOTH `benchmark_researcher_prompt.py` AND `challenger_researcher_prompt_1.py` define this function!

**Impact**:
- Non-deterministic - could import from either file
- Test results invalidated (unknown which prompt was tested)
- Evaluation framework unreliable

### Solution
Make imports explicit with version-specific imports.

**Files to modify**:
1. `/backend/test_configs/test_config_1_with_todomiddleware.py:77`
2. `/backend/test_configs/compare_planning_approaches.py` (if it has same issue)

### Implementation

#### Update to Explicit Imports

```python
# OLD (ambiguous):
from prompts.researcher import get_researcher_prompt

# NEW (explicit - choose one):
from prompts.researcher.benchmark_researcher_prompt import get_researcher_prompt as get_benchmark_prompt
# OR for testing challenger:
from prompts.researcher.challenger_researcher_prompt_1 import get_researcher_prompt as get_challenger_prompt

# Then use explicitly:
researcher_system_prompt = get_benchmark_prompt(current_date)
```

#### Best Practice: Add Version Parameter

For files that need to test both versions, add version parameter:
```python
def get_prompt_by_version(version: Literal["benchmark", "challenger"], current_date: str) -> str:
    """Get researcher prompt by version."""
    if version == "benchmark":
        from prompts.researcher.benchmark_researcher_prompt import get_researcher_prompt
    else:
        from prompts.researcher.challenger_researcher_prompt_1 import get_researcher_prompt

    return get_researcher_prompt(current_date)
```

---

## Fix #3: TestQuery Type Consistency 🔴 TODO

### Problem
`test_suite.py:45` defines `TestQuery` as TypedDict, but uses plain dict literals.

**Type definition**:
```python
class TestQuery(TypedDict):
    query_id: str
    query_text: str
    category: str
    complexity: str
    expected_aspects: List[str]
    expected_sources_min: int
    context: Optional[str]
    success_criteria: List[str]
    metadata: Dict[str, Any]
```

**Actual usage** (line ~348):
```python
{
    "query_id": "quantum_latest",
    "query_text": "What are the latest developments...",
    # ... plain dict, not TestQuery instance
}
```

**Impact**:
- Type checkers (mypy/pyright) will fail
- Runtime works but no type safety
- Could cause subtle bugs if fields mismatched

### Solution
Create explicit constructor function or use TypedDict correctly.

**Files to modify**:
1. `/Users/nicholaspate/Documents/01_Active/ATLAS/main/evaluation/test_suite.py` (lines 45-400+)

### Implementation

#### Option A: Constructor Function (Recommended)

```python
def create_test_query(
    query_id: str,
    query_text: str,
    category: str,
    complexity: str,
    expected_aspects: List[str],
    expected_sources_min: int,
    success_criteria: List[str],
    context: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> TestQuery:
    """Create a properly typed TestQuery instance."""
    return TestQuery(
        query_id=query_id,
        query_text=query_text,
        category=category,
        complexity=complexity,
        expected_aspects=expected_aspects,
        expected_sources_min=expected_sources_min,
        context=context,
        success_criteria=success_criteria,
        metadata=metadata or {}
    )

# Then update all query definitions:
SIMPLE_QUERIES = [
    create_test_query(
        query_id="quantum_latest",
        query_text="What are the latest developments in quantum computing?",
        category="simple_research",
        complexity="medium",
        expected_aspects=["hardware", "software", "applications"],
        expected_sources_min=3,
        success_criteria=["Multiple sources", "Recent data"],
    ),
    # ... rest
]
```

#### Option B: TypedDict Direct Construction

```python
# Works at runtime but type checkers happier with explicit typing
quantum_query: TestQuery = {
    "query_id": "quantum_latest",
    "query_text": "What are the latest developments...",
    "category": "simple_research",
    "complexity": "medium",
    "expected_aspects": ["hardware", "software", "applications"],
    "expected_sources_min": 3,
    "context": None,
    "success_criteria": ["Multiple sources", "Recent data"],
    "metadata": {}
}
```

---

## Fix #4: EvaluationResult Aggregation Function 🟠 HIGH PRIORITY

### Problem
Individual judgment TypedDicts don't map clearly to EvaluationResult structure.

**Impact**: `test_runner.py` may fail when aggregating results from judges.

### Solution
Create aggregation function that maps 7 judgment types → EvaluationResult.

**Files to modify**:
1. `/Users/nicholaspate/Documents/01_Active/ATLAS/main/evaluation/judge_agents.py` (add aggregation function)
2. `/Users/nicholaspate/Documents/01_Active/ATLAS/main/evaluation/test_runner.py` (use aggregation function)

### Implementation

```python
# Add to judge_agents.py:

from evaluation.test_suite import TestQuery, EvaluationResult
from datetime import datetime

def aggregate_judgments_to_evaluation_result(
    test_query: TestQuery,
    prompt_version: str,
    planning_judgment: PlanningQualityJudgment,
    execution_judgment: ExecutionCompletenessJudgment,
    source_judgment: SourceQualityJudgment,
    citation_judgment: CitationAccuracyJudgment,
    answer_judgment: AnswerCompletenessJudgment,
    factual_judgment: FactualAccuracyJudgment,
    autonomy_judgment: AutonomyScoreJudgment,
    researcher_response: str,
    researcher_plan: Optional[Dict] = None
) -> EvaluationResult:
    """
    Aggregate individual judge results into single EvaluationResult.

    Args:
        test_query: The original test query
        prompt_version: "benchmark" or "challenger"
        *_judgment: Results from each of the 7 judges
        researcher_response: Full response from researcher agent
        researcher_plan: Optional plan generated by researcher

    Returns:
        Complete EvaluationResult ready for statistical analysis
    """
    return EvaluationResult(
        query_id=test_query["query_id"],
        prompt_version=prompt_version,
        timestamp=datetime.now().isoformat(),

        # Map judgments to result fields
        planning_quality=1.0 if planning_judgment["rating"] == "Good" else 0.0,
        execution_completeness=float(execution_judgment["rating"]),
        source_quality=float(source_judgment["rating"]),
        citation_accuracy=1.0 if citation_judgment["rating"] == "Accurate" else 0.0,
        answer_completeness=float(answer_judgment["rating"]),
        factual_accuracy=1.0 if factual_judgment["rating"] == "Accurate" else 0.0,
        autonomy_score=1.0 if autonomy_judgment["rating"] == "Autonomous" else 0.0,

        # Include full data for analysis
        researcher_response=researcher_response,
        researcher_plan=researcher_plan,

        # Include reasoning from judges for review
        judge_reasoning={
            "planning": planning_judgment["reasoning"],
            "execution": execution_judgment["reasoning"],
            "source": source_judgment["reasoning"],
            "citation": citation_judgment["reasoning"],
            "answer": answer_judgment["reasoning"],
            "factual": factual_judgment["reasoning"],
            "autonomy": autonomy_judgment["reasoning"],
        }
    )
```

---

## Testing Plan

### After Each Fix
1. Run syntax check: `python -m py_compile <file>`
2. Import test: `python -c "import test_configs.test_config_1_with_todomiddleware"`
3. Type check: `mypy --strict test_suite.py`

### Integration Test
Once all critical fixes complete:
```bash
cd /Users/nicholaspate/Documents/01_Active/ATLAS/main
python -m pytest evaluation/test_suite.py -v
```

### Full Evaluation Test
```bash
python run_evaluation.py --version benchmark --max-tests 1
```

---

## Completion Criteria

- [ ] Fix #1: TodoListMiddleware stub created and imported ✅ IN PROGRESS
- [ ] Fix #2: All ambiguous imports made explicit
- [ ] Fix #3: TestQuery uses constructor function
- [ ] Fix #4: Aggregation function created and tested
- [ ] All syntax checks pass
- [ ] All import tests pass
- [ ] Type checking passes
- [ ] Single evaluation test completes successfully

---

## Estimated Time

- **Fix #1 (TodoMiddleware)**: 30 minutes ✅ CURRENT
- **Fix #2 (Imports)**: 15 minutes
- **Fix #3 (TestQuery)**: 45 minutes
- **Fix #4 (Aggregation)**: 30 minutes
- **Testing**: 30 minutes

**Total**: ~2.5 hours to production-ready state

---

**Next Action**: Implement Fix #1 (TodoListMiddleware stub)
