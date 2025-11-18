"""
Test Challenger Prompt V1 - Quick 8-Test Validation

Runs a subset of tests to validate Phase 1 improvements:
- Step completion tracking
- Consistent plan creation
- Overall workflow adherence

Compares against baseline metrics to measure improvements.
"""

import sys
from pathlib import Path

# Add project root to Python path
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

# Load environment variables
from dotenv import load_dotenv
env_path = root_path / ".env"
load_dotenv(env_path)

# Now import evaluation framework
from evaluation.test_runner import run_evaluation
from evaluation.configs import test_config_challenger_1

# Define 8-test subset (2 from each category for quick validation)
TEST_SUBSET = [
    "SIMPLE-001",      # Quantum error correction
    "SIMPLE-002",      # Python vs JavaScript
    "MULTI-001",       # LangChain vs LlamaIndex vs CrewAI
    "MULTI-002",       # LLM state analysis
    "TIME-001",        # Latest AI developments Nov 2025
    "TIME-002",        # Quantum computing 2025
    "COMP-001",        # Renewable energy analysis
    "COMP-002",        # Production AI applications
]

if __name__ == "__main__":
    print("=" * 80)
    print("CHALLENGER PROMPT V1 - VALIDATION TEST (8 queries)")
    print("=" * 80)
    print()
    print("Testing Phase 1 Improvements:")
    print("  - Mandatory step completion tracking")
    print("  - Consistent plan creation")
    print("  - Few-shot examples and checkpoints")
    print()
    print("Test IDs:", ", ".join(TEST_SUBSET))
    print()
    print("=" * 80)
    print()

    # Import the challenger config
    from evaluation.configs.test_config_challenger_1 import create_baseline_agent

    # Run evaluation on test subset
    results = run_evaluation(
        agent_factory=create_baseline_agent,
        output_file="evaluation/challenger_1_validation_results.json",
        test_ids=TEST_SUBSET,
        verbose=True
    )

    print()
    print("=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    print()
    print(f"Results saved to: evaluation/challenger_1_validation_results.json")
    print()
    print("Quick Comparison vs Baseline:")
    print(f"  Tests Run: {len(TEST_SUBSET)}")
    print(f"  Pass Rate: {results.get('pass_rate', 'N/A')}")
    print(f"  Avg Step Completion: {results.get('avg_step_completion', 'N/A')}")
    print()
    print("Next: Compare detailed results against baseline metrics")
    print("=" * 80)
