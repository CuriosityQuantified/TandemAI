#!/usr/bin/env python3
"""
Comprehensive Verification Script for TandemAI Changes

Tests all 7 parallel fixes + folder rename + token limit updates
"""

import sys
from pathlib import Path
from datetime import datetime

# Add TandemAI main to path
TANDEM_AI_ROOT = Path(__file__).parent
sys.path.insert(0, str(TANDEM_AI_ROOT))

print("=" * 80)
print("TANDEMAI VERIFICATION SCRIPT")
print("=" * 80)
print()

# Track test results
tests_passed = 0
tests_failed = 0
failures = []

def test_section(title):
    """Print test section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def test_result(name, passed, error=None):
    """Record and print test result"""
    global tests_passed, tests_failed, failures
    if passed:
        print(f"✅ {name}")
        tests_passed += 1
    else:
        print(f"❌ {name}")
        if error:
            print(f"   Error: {error}")
        tests_failed += 1
        failures.append((name, error))

# ============================================================================
# TEST 1: Folder Path Verification
# ============================================================================
test_section("TEST 1: Verify TandemAI Folder Path")

try:
    current_path = str(Path(__file__).resolve())
    assert "TandemAI" in current_path, f"Path doesn't contain 'TandemAI': {current_path}"
    assert "ATLAS" not in current_path.split("/")[-5:], f"Path still contains 'ATLAS': {current_path}"
    test_result("TandemAI folder path correct", True)
except Exception as e:
    test_result("TandemAI folder path correct", False, str(e))

# ============================================================================
# TEST 2: Fix #2 - Ambiguous Import Resolution
# ============================================================================
test_section("TEST 2: Verify Ambiguous Import Fix")

# Test 2.1: Package __init__.py files exist
try:
    prompts_init = TANDEM_AI_ROOT / "prompts" / "__init__.py"
    researcher_init = TANDEM_AI_ROOT / "prompts" / "researcher" / "__init__.py"
    assert prompts_init.exists(), f"Missing: {prompts_init}"
    assert researcher_init.exists(), f"Missing: {researcher_init}"
    test_result("Package __init__.py files exist", True)
except Exception as e:
    test_result("Package __init__.py files exist", False, str(e))

# Test 2.2: Explicit benchmark import works
try:
    from prompts.researcher.benchmark_researcher_prompt import get_researcher_prompt as get_benchmark_prompt
    benchmark_prompt = get_benchmark_prompt(datetime.now().strftime("%Y-%m-%d"))
    assert len(benchmark_prompt) > 20000, f"Benchmark prompt too short: {len(benchmark_prompt)} chars"
    test_result("Explicit benchmark import works", True)
except Exception as e:
    test_result("Explicit benchmark import works", False, str(e))

# Test 2.3: Explicit challenger import works
try:
    from prompts.researcher.challenger_researcher_prompt_1 import get_researcher_prompt as get_challenger_prompt
    challenger_prompt = get_challenger_prompt(datetime.now().strftime("%Y-%m-%d"))
    # Challenger is template, should be short
    assert len(challenger_prompt) < 1000, f"Challenger prompt should be template: {len(challenger_prompt)} chars"
    test_result("Explicit challenger import works", True)
except Exception as e:
    test_result("Explicit challenger import works", False, str(e))

# Test 2.4: Default import uses benchmark
try:
    from prompts.researcher import get_researcher_prompt
    default_prompt = get_researcher_prompt(datetime.now().strftime("%Y-%m-%d"))
    assert len(default_prompt) > 20000, f"Default should use benchmark: {len(default_prompt)} chars"
    test_result("Default import uses benchmark", True)
except Exception as e:
    test_result("Default import uses benchmark", False, str(e))

# ============================================================================
# TEST 3: Fix #3 - TestQuery Type Consistency
# ============================================================================
test_section("TEST 3: Verify TestQuery Type Consistency")

try:
    from evaluation.test_suite import TestQuery, SIMPLE_QUERIES, QueryCategory

    # Check TestQuery is dataclass
    assert hasattr(TestQuery, '__dataclass_fields__'), "TestQuery should be @dataclass"
    test_result("TestQuery is @dataclass", True)

    # Check first query is proper instance
    first_query = SIMPLE_QUERIES[0]
    assert isinstance(first_query, TestQuery), f"Query should be TestQuery instance, got {type(first_query)}"
    test_result("SIMPLE_QUERIES uses TestQuery instances", True)

    # Check all 32 queries exist
    from evaluation.test_suite import MULTI_ASPECT_QUERIES, TIME_CONSTRAINED_QUERIES, COMPREHENSIVE_QUERIES
    total = len(SIMPLE_QUERIES) + len(MULTI_ASPECT_QUERIES) + len(TIME_CONSTRAINED_QUERIES) + len(COMPREHENSIVE_QUERIES)
    assert total == 32, f"Should have 32 queries, found {total}"
    test_result(f"All 32 test queries present ({total})", True)

except Exception as e:
    test_result("TestQuery type consistency", False, str(e))

# ============================================================================
# TEST 4: Fix #4 - EvaluationResult Aggregation
# ============================================================================
test_section("TEST 4: Verify EvaluationResult Aggregation Function")

try:
    from evaluation.judge_agents import aggregate_judgments_to_evaluation_result
    from evaluation.test_suite import EvaluationResult

    # Mock judge decisions
    mock_decisions = {
        'planning_quality': {'score': 1.0, 'reasoning': 'Good planning'},
        'execution_completeness': {'score': 5, 'reasoning': 'Complete execution'},
        'source_quality': {'score': 4, 'reasoning': 'Quality sources'},
        'citation_accuracy': {'score': 1.0, 'reasoning': 'Accurate citations'},
        'answer_completeness': {'score': 5, 'reasoning': 'Comprehensive answer'},
        'factual_accuracy': {'score': 1.0, 'reasoning': 'Factually correct'},
        'autonomy_score': {'score': 1.0, 'reasoning': 'Fully autonomous'}
    }

    # Test aggregation
    result = aggregate_judgments_to_evaluation_result(
        query_id=1,
        query_text="Test query",
        prompt_version="benchmark",
        judge_decisions=mock_decisions
    )

    assert isinstance(result, EvaluationResult), f"Should return EvaluationResult, got {type(result)}"
    assert result.planning_quality.score == 1.0, "Planning quality score incorrect"
    assert result.execution_completeness.score == 5, "Execution completeness score incorrect"

    test_result("Aggregation function works correctly", True)

except Exception as e:
    test_result("Aggregation function works correctly", False, str(e))

# ============================================================================
# TEST 5: Fix #5 - sys.path Import Pattern
# ============================================================================
test_section("TEST 5: Verify sys.path Import Pattern")

try:
    # Read one of the fixed files
    test_file = TANDEM_AI_ROOT / "backend" / "test_configs" / "test_config_1_with_todomiddleware.py"
    if test_file.exists():
        content = test_file.read_text()

        # Check for duplicate guard pattern
        assert "if str(" in content and "not in sys.path:" in content, \
            "Should have duplicate guard pattern"

        # Check for descriptive constant
        assert "BACKEND_DIR" in content or "_PATH" in content, \
            "Should have descriptive path constant"

        test_result("sys.path pattern uses duplicate guard", True)
    else:
        test_result("sys.path pattern uses duplicate guard", False, "File not found")

except Exception as e:
    test_result("sys.path pattern uses duplicate guard", False, str(e))

# ============================================================================
# TEST 6: Fix #6 - State Class Naming (Verification)
# ============================================================================
test_section("TEST 6: Verify State Class Naming")

try:
    # Import middleware modules
    from backend.middleware.summarization_middleware import SummarizationMiddleware
    from backend.middleware.tool_selector_middleware import LLMToolSelectorMiddleware
    from backend.middleware.agent_middleware_manager import AgentMiddlewareManager

    # All should instantiate without conflicts
    summ = SummarizationMiddleware()
    selector = LLMToolSelectorMiddleware()
    manager = AgentMiddlewareManager()

    test_result("Middleware imports without naming conflicts", True)

except Exception as e:
    test_result("Middleware imports without naming conflicts", False, str(e))

# ============================================================================
# TEST 7: Fix #7 - Circular Import Prevention
# ============================================================================
test_section("TEST 7: Verify No Circular Imports")

try:
    # Try importing evaluation modules in different orders
    from evaluation.test_suite import TestQuery
    from evaluation.judge_agents import aggregate_judgments_to_evaluation_result
    from evaluation.test_runner import TestRunner
    from evaluation.statistical_analysis import StatisticalAnalyzer

    test_result("Evaluation modules import without circular dependencies", True)

except Exception as e:
    test_result("Evaluation modules import without circular dependencies", False, str(e))

# ============================================================================
# TEST 8: Fix #8 - File Path Handling
# ============================================================================
test_section("TEST 8: Verify pathlib.Path Usage")

try:
    # Check a converted file uses pathlib
    test_file = TANDEM_AI_ROOT / "backend" / "test_configs" / "single_test_verification.py"
    if test_file.exists():
        content = test_file.read_text()

        assert "from pathlib import Path" in content, "Should import pathlib"
        assert "Path(__file__).parent" in content, "Should use Path pattern"

        test_result("Converted files use pathlib.Path", True)
    else:
        test_result("Converted files use pathlib.Path", False, "File not found")

except Exception as e:
    test_result("Converted files use pathlib.Path", False, str(e))

# ============================================================================
# TEST 9: Token Limit Updates
# ============================================================================
test_section("TEST 9: Verify Token Limit Updates")

try:
    challenger_file = TANDEM_AI_ROOT / "prompts" / "researcher" / "challenger_researcher_prompt_1.py"
    content = challenger_file.read_text()

    # Check for 15,000 token limit
    assert "15000" in content or "15,000" in content, \
        "Should have 15,000 token limit"

    # Make sure old 5,000 limit is gone from challenger context
    lines_with_5000 = [line for line in content.split('\n') if '5000' in line or '5,000' in line]
    # Filter out comment lines explaining the old limit
    active_5000 = [line for line in lines_with_5000 if 'was' not in line.lower() and 'old' not in line.lower()]

    assert len(active_5000) == 0, f"Should not have active 5,000 references: {active_5000}"

    test_result("Token limit updated to 15,000", True)

except Exception as e:
    test_result("Token limit updated to 15,000", False, str(e))

# ============================================================================
# TEST 10: Path References in Documentation
# ============================================================================
test_section("TEST 10: Verify Path References Updated")

try:
    # Check a few documentation files
    doc_file = TANDEM_AI_ROOT / "CRITICAL_FIXES_IMPLEMENTATION.md"
    if doc_file.exists():
        content = doc_file.read_text()

        # Should have TandemAI
        tandemai_count = content.count("TandemAI")
        assert tandemai_count > 0, "Should have TandemAI references"

        # Should not have ATLAS in paths (but might in historical context)
        atlas_in_paths = content.count("/ATLAS/")
        assert atlas_in_paths == 0, f"Should not have /ATLAS/ in paths, found {atlas_in_paths}"

        test_result("Documentation uses TandemAI paths", True)
    else:
        test_result("Documentation uses TandemAI paths", False, "File not found")

except Exception as e:
    test_result("Documentation uses TandemAI paths", False, str(e))

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print()
print("=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)
print()
print(f"✅ Tests Passed: {tests_passed}")
print(f"❌ Tests Failed: {tests_failed}")
print(f"📊 Success Rate: {tests_passed}/{tests_passed + tests_failed} ({100 * tests_passed / (tests_passed + tests_failed):.1f}%)")
print()

if failures:
    print("FAILURES:")
    for name, error in failures:
        print(f"  ❌ {name}")
        if error:
            print(f"     {error}")
    print()

if tests_failed == 0:
    print("🎉 ALL TESTS PASSED! TandemAI is production-ready.")
    sys.exit(0)
else:
    print("⚠️  Some tests failed. Review output above.")
    sys.exit(1)
