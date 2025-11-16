#!/usr/bin/env python3
"""
Parallel Prompt Testing for Config 1 Researcher Enhancement

Tests 10 different prompt patterns to analyze researcher behavior and identify
areas for system prompt improvement.

Each test saves output for analysis of:
- Planning quality (how well researcher structures research)
- Sequential execution (proper step-by-step execution)
- Progress tracking (update_plan_progress usage)
- Citation quality (exact quotes, full attribution)
- Completeness (all steps executed before final response)
- Prompt engineering (how well researcher creates plan queries)

Usage:
    python parallel_prompt_testing.py

Output:
    test_results/prompt_test_YYYYMMDD_HHMMSS/
        ├── test_01_simple_factual.log
        ├── test_02_complex_multi_aspect.log
        ├── ...
        ├── test_10_comprehensive_survey.log
        └── summary_report.md
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import json

# Add test_configs to path
sys.path.insert(0, str(Path(__file__).parent))

from langchain_core.messages import HumanMessage
from test_config_1_deepagent_supervisor_command import create_graph


# ============================================================================
# TEST PROMPTS - 10 Diverse Patterns
# ============================================================================

TEST_PROMPTS: List[Tuple[str, str, str]] = [
    # (test_id, test_name, prompt, description)

    (
        "test_01",
        "Simple Factual Query",
        "What is quantum entanglement?",
        """
        Tests: Baseline behavior for simple queries
        Expected: Should skip planning tools, provide direct answer with citations
        Focus: Citation quality, fact accuracy
        """
    ),

    (
        "test_02",
        "Complex Multi-Aspect Query",
        """Research the state of quantum computing hardware in 2024-2025.

        Context: Preparing technical assessment for enterprise adoption decision.
        Goal: Identify top 3 quantum computing platforms by qubit count and error rates.

        Focus areas:
        1. Hardware specifications (qubit count, coherence time, gate fidelity)
        2. Error correction capabilities and recent improvements
        3. Commercial availability and pricing models

        Success criteria: 3+ peer-reviewed sources per area, quantitative benchmarks required.
        Constraints: Prioritize Nature, Science, IEEE journals + industry leaders (IBM, Google, IonQ).
        """,
        """
        Tests: High-quality prompt engineering, comprehensive planning
        Expected: 5-7 step plan, detailed research per area, extensive citations
        Focus: Planning quality, sequential execution, progress tracking
        """
    ),

    (
        "test_03",
        "Time-Constrained Query",
        """What are the quantum computing breakthroughs announced in the last 3 months (since August 2024)?

        CRITICAL: Only include developments from August 2024 or later. Explicitly note the date of each finding.
        """,
        """
        Tests: Temporal filtering, date verification
        Expected: Check dates carefully, flag older sources
        Focus: Date accuracy, source freshness
        """
    ),

    (
        "test_04",
        "Source-Specific Query",
        """Analyze quantum error correction advances based ONLY on peer-reviewed academic papers from
        Nature, Science, or Physical Review journals published in 2024.

        Requirements:
        - Each citation must include journal name, publication date, DOI
        - Exclude blog posts, news articles, preprints, corporate announcements
        - Minimum 5 academic sources
        """,
        """
        Tests: Source discrimination, rigorous citation standards
        Expected: Careful source selection, academic-only citations
        Focus: Citation precision, source quality verification
        """
    ),

    (
        "test_05",
        "Comparison Query",
        """Compare superconducting qubits vs. trapped ion qubits for quantum computing.

        Comparison framework:
        1. Technical advantages and disadvantages of each approach
        2. Current performance metrics (gate fidelity, coherence time, qubit count)
        3. Scalability challenges for each technology
        4. Leading companies/institutions for each approach

        Provide side-by-side comparison with exact metrics from recent sources (2024-2025).
        """,
        """
        Tests: Structured comparison, balanced coverage, metric extraction
        Expected: Equal depth for both approaches, quantitative comparison
        Focus: Balanced research, structured synthesis
        """
    ),

    (
        "test_06",
        "Trend Analysis Query",
        """Analyze the evolution of quantum computing error rates from 2020 to 2025.

        Requirements:
        - Identify key milestones in error rate reduction
        - Track improvements year-by-year with specific metrics
        - Highlight breakthrough moments and their causes
        - Project future trends based on current trajectory

        Success: Show clear progression with exact error rate figures and dates.
        """,
        """
        Tests: Longitudinal analysis, trend identification, temporal organization
        Expected: Chronological structure, quantitative progression
        Focus: Temporal organization, data synthesis
        """
    ),

    (
        "test_07",
        "Technical Deep-Dive Query",
        """Explain the technical details of surface code quantum error correction.

        Required depth:
        1. Physical implementation on superconducting qubits
        2. Logical vs. physical qubit relationship and overhead
        3. Threshold theorem requirements and current achievements
        4. Recent improvements in code distance and logical error rates

        Target audience: Quantum computing engineers (highly technical acceptable).
        Minimum 5 academic sources with exact equations/metrics where applicable.
        """,
        """
        Tests: Technical depth, complex topic handling, expert-level accuracy
        Expected: Detailed technical explanation with precise citations
        Focus: Accuracy for complex topics, technical citation quality
        """
    ),

    (
        "test_08",
        "Contradictory Sources Query",
        """Research the current state of quantum advantage/supremacy claims.

        Note: This topic has CONFLICTING claims and debates. Your task:
        1. Present multiple perspectives (Google's claims, IBM's critiques, other views)
        2. Explicitly identify where sources disagree
        3. Provide exact quotes for contradictory claims
        4. Maintain neutrality while presenting all viewpoints

        Success: Clear presentation of conflicts with exact quotes from each side.
        """,
        """
        Tests: Handling contradictions, neutrality, conflict presentation
        Expected: Explicit conflict identification, balanced quotes
        Focus: Objectivity, conflict resolution approach
        """
    ),

    (
        "test_09",
        "Emerging Topic Query",
        """Research quantum computing applications in drug discovery announced in 2024.

        Note: This is an EMERGING area with potentially limited sources.
        - If sources are scarce, explicitly note this limitation
        - Distinguish between actual results vs. theoretical potential
        - Flag speculative claims vs. proven results
        - Identify knowledge gaps

        Success: Honest assessment of available evidence, clear uncertainty communication.
        """,
        """
        Tests: Handling limited sources, uncertainty communication, speculation vs. fact
        Expected: Explicit knowledge gap identification
        Focus: Intellectual honesty, limitation acknowledgment
        """
    ),

    (
        "test_10",
        "Comprehensive Survey Query",
        """Conduct a comprehensive survey of the quantum computing landscape in 2024-2025.

        Context: Board-level presentation for $50M quantum computing investment decision.
        Goal: Provide complete picture of technology readiness, key players, and timeline to practical utility.

        Coverage areas:
        1. Current hardware state (all major platforms: superconducting, trapped ion, photonic, etc.)
        2. Software ecosystem and algorithm development
        3. Error correction progress and projections
        4. Commercial applications and use cases
        5. Key players (companies, research institutions, governments)
        6. Timeline projections for fault-tolerant quantum computing
        7. Investment landscape and funding trends

        Success criteria per area: 3+ authoritative sources, quantitative data, expert consensus.
        Constraints: Balance technical accuracy with board-level accessibility.
        Time frame: Focus on 2024-2025 data.

        Expected output: 10-15 page equivalent with extensive citations, structured sections.
        """,
        """
        Tests: Maximum complexity, comprehensive planning, extensive research
        Expected: 10-15 step plan, longest execution time, most extensive citations
        Focus: Complete workflow test, stress test all capabilities
        """
    ),
]


# ============================================================================
# TEST EXECUTION FUNCTIONS
# ============================================================================

async def run_single_test(
    test_id: str,
    test_name: str,
    prompt: str,
    description: str,
    output_dir: Path,
    graph
) -> Dict:
    """
    Run a single test prompt and save results.

    Args:
        test_id: Test identifier (e.g., "test_01")
        test_name: Human-readable test name
        prompt: The test prompt to execute
        description: Test description and expected behavior
        output_dir: Directory to save output
        graph: Compiled LangGraph

    Returns:
        Dictionary with test results and metrics
    """

    print(f"\n{'='*80}")
    print(f"🧪 RUNNING: {test_id} - {test_name}")
    print(f"{'='*80}\n")

    # Prepare output file
    output_file = output_dir / f"{test_id}_{test_name.lower().replace(' ', '_')}.log"

    start_time = datetime.now()

    # Open file for writing
    with open(output_file, 'w') as f:
        # Write header
        f.write("="*80 + "\n")
        f.write(f"TEST: {test_id} - {test_name}\n")
        f.write("="*80 + "\n")
        f.write(f"Start Time: {start_time.isoformat()}\n")
        f.write(f"\nDescription:\n{description}\n")
        f.write(f"\nPrompt:\n{'-'*80}\n{prompt}\n{'-'*80}\n\n")
        f.write("="*80 + "\n")
        f.write("EXECUTION LOG\n")
        f.write("="*80 + "\n\n")

        # Track metrics
        metrics = {
            "test_id": test_id,
            "test_name": test_name,
            "start_time": start_time.isoformat(),
            "prompt_length": len(prompt),
            "plan_created": False,
            "num_steps": 0,
            "steps_completed": 0,
            "search_count": 0,
            "progress_updates": 0,
            "total_messages": 0,
            "tool_calls": 0,
            "error": None,
        }

        try:
            # Execute graph with streaming
            all_messages = []
            event_count = 0

            config = {
                "configurable": {"thread_id": f"{test_id}-{int(start_time.timestamp())}"},
                "recursion_limit": 100  # Higher limit for comprehensive tests
            }

            for event in graph.stream(
                {"messages": [HumanMessage(content=prompt)]},
                config=config,
                stream_mode="values"
            ):
                event_count += 1
                messages = event.get("messages", [])
                new_messages = messages[len(all_messages):]
                all_messages = messages

                # Log each new message
                for msg in new_messages:
                    msg_type = msg.__class__.__name__

                    # Count tool calls
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        metrics["tool_calls"] += len(msg.tool_calls)

                        for tc in msg.tool_calls:
                            tool_name = tc.get('name', 'unknown')

                            # Track specific metrics
                            if tool_name == 'create_research_plan':
                                metrics["plan_created"] = True
                                num_steps = tc.get('args', {}).get('num_steps', 0)
                                metrics["num_steps"] = num_steps

                            elif tool_name in ['tavily_search', 'search_web']:
                                metrics["search_count"] += 1

                            elif tool_name == 'update_plan_progress':
                                metrics["progress_updates"] += 1
                                step_idx = tc.get('args', {}).get('step_index', -1)
                                if step_idx >= 0:
                                    metrics["steps_completed"] = max(metrics["steps_completed"], step_idx + 1)

                    # Write message to log
                    f.write(f"\n{'-'*80}\n")
                    f.write(f"Message {len(all_messages)}: {msg_type}\n")
                    f.write(f"{'-'*80}\n")

                    if hasattr(msg, 'content') and msg.content:
                        content = str(msg.content)
                        f.write(f"Content ({len(content)} chars):\n{content}\n")

                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        f.write(f"Tool Calls: {len(msg.tool_calls)}\n")
                        for tc in msg.tool_calls:
                            f.write(f"  - {tc.get('name')}: {tc.get('args')}\n")

                    f.flush()  # Ensure real-time writing

            # Calculate final metrics
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            metrics["end_time"] = end_time.isoformat()
            metrics["duration_seconds"] = duration
            metrics["total_messages"] = len(all_messages)
            metrics["events"] = event_count

            # Calculate completion percentage
            if metrics["num_steps"] > 0:
                metrics["completion_percentage"] = (metrics["steps_completed"] / metrics["num_steps"]) * 100
            else:
                metrics["completion_percentage"] = 0 if not metrics["plan_created"] else 100

            # Write summary
            f.write(f"\n\n{'='*80}\n")
            f.write("TEST SUMMARY\n")
            f.write(f"{'='*80}\n")
            f.write(f"End Time: {end_time.isoformat()}\n")
            f.write(f"Duration: {duration:.2f} seconds\n")
            f.write(f"Total Messages: {metrics['total_messages']}\n")
            f.write(f"Total Events: {event_count}\n")
            f.write(f"Tool Calls: {metrics['tool_calls']}\n")
            f.write(f"\nPlanning Metrics:\n")
            f.write(f"  Plan Created: {metrics['plan_created']}\n")
            f.write(f"  Planned Steps: {metrics['num_steps']}\n")
            f.write(f"  Completed Steps: {metrics['steps_completed']}\n")
            f.write(f"  Completion: {metrics['completion_percentage']:.1f}%\n")
            f.write(f"\nExecution Metrics:\n")
            f.write(f"  Search Calls: {metrics['search_count']}\n")
            f.write(f"  Progress Updates: {metrics['progress_updates']}\n")

            print(f"✅ {test_id} COMPLETED in {duration:.1f}s")
            print(f"   Messages: {metrics['total_messages']} | Steps: {metrics['steps_completed']}/{metrics['num_steps']} | Searches: {metrics['search_count']}")

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            metrics["error"] = error_msg

            f.write(f"\n\n{'='*80}\n")
            f.write("❌ ERROR OCCURRED\n")
            f.write(f"{'='*80}\n")
            f.write(f"{error_msg}\n")

            import traceback
            f.write(f"\nTraceback:\n{traceback.format_exc()}\n")

            print(f"❌ {test_id} FAILED: {error_msg}")

    return metrics


async def run_all_tests_parallel(output_dir: Path):
    """
    Run all test prompts in parallel (up to 3 concurrent to avoid API rate limits).

    Args:
        output_dir: Directory to save all test outputs
    """

    print("\n" + "="*80)
    print("🚀 PARALLEL PROMPT TESTING - Config 1 Researcher Enhancement")
    print("="*80)
    print(f"\nOutput Directory: {output_dir}")
    print(f"Total Tests: {len(TEST_PROMPTS)}")
    print(f"Concurrency: 3 (to respect API rate limits)")
    print("\n" + "="*80 + "\n")

    # Create graph once (reuse for all tests)
    print("📊 Building graph...")
    from test_config_1_deepagent_supervisor_command import create_graph
    graph = create_graph()
    print("✅ Graph built\n")

    # Run tests with concurrency limit
    semaphore = asyncio.Semaphore(3)  # Max 3 concurrent tests

    async def run_with_semaphore(test_data):
        async with semaphore:
            test_id, test_name, prompt, description = test_data
            return await run_single_test(
                test_id, test_name, prompt, description, output_dir, graph
            )

    # Execute all tests
    tasks = [run_with_semaphore(test_data) for test_data in TEST_PROMPTS]
    results = await asyncio.gather(*tasks)

    return results


def generate_summary_report(results: List[Dict], output_dir: Path):
    """
    Generate comprehensive summary report analyzing all test results.

    Args:
        results: List of test result dictionaries
        output_dir: Directory to save summary
    """

    summary_file = output_dir / "summary_report.md"

    with open(summary_file, 'w') as f:
        f.write("# Parallel Prompt Testing - Summary Report\n\n")
        f.write(f"**Generated**: {datetime.now().isoformat()}\n")
        f.write(f"**Test Count**: {len(results)}\n\n")

        f.write("---\n\n")
        f.write("## Overall Metrics\n\n")

        # Calculate aggregate metrics
        total_duration = sum(r.get('duration_seconds', 0) for r in results)
        total_messages = sum(r.get('total_messages', 0) for r in results)
        total_searches = sum(r.get('search_count', 0) for r in results)
        tests_with_plans = sum(1 for r in results if r.get('plan_created'))
        tests_with_errors = sum(1 for r in results if r.get('error'))

        avg_completion = sum(r.get('completion_percentage', 0) for r in results) / len(results)

        f.write(f"- **Total Execution Time**: {total_duration:.1f} seconds\n")
        f.write(f"- **Total Messages**: {total_messages}\n")
        f.write(f"- **Total Searches**: {total_searches}\n")
        f.write(f"- **Tests with Plans**: {tests_with_plans}/{len(results)}\n")
        f.write(f"- **Tests with Errors**: {tests_with_errors}/{len(results)}\n")
        f.write(f"- **Average Completion**: {avg_completion:.1f}%\n\n")

        f.write("---\n\n")
        f.write("## Individual Test Results\n\n")

        # Sort by test_id
        sorted_results = sorted(results, key=lambda r: r.get('test_id', ''))

        for result in sorted_results:
            f.write(f"### {result['test_id']}: {result['test_name']}\n\n")

            # Status
            if result.get('error'):
                f.write(f"**Status**: ❌ FAILED\n")
                f.write(f"**Error**: {result['error']}\n\n")
            elif result.get('completion_percentage', 0) >= 95:
                f.write(f"**Status**: ✅ PASSED\n\n")
            else:
                f.write(f"**Status**: ⚠️ PARTIAL ({result.get('completion_percentage', 0):.1f}% complete)\n\n")

            # Metrics
            f.write("**Metrics**:\n")
            f.write(f"- Duration: {result.get('duration_seconds', 0):.1f}s\n")
            f.write(f"- Messages: {result.get('total_messages', 0)}\n")
            f.write(f"- Tool Calls: {result.get('tool_calls', 0)}\n")
            f.write(f"- Plan Created: {result.get('plan_created', False)}\n")
            f.write(f"- Planned Steps: {result.get('num_steps', 0)}\n")
            f.write(f"- Completed Steps: {result.get('steps_completed', 0)}\n")
            f.write(f"- Searches: {result.get('search_count', 0)}\n")
            f.write(f"- Progress Updates: {result.get('progress_updates', 0)}\n")
            f.write(f"- Completion: {result.get('completion_percentage', 0):.1f}%\n\n")

        f.write("---\n\n")
        f.write("## Analysis & Recommendations\n\n")

        f.write("### Planning Behavior\n\n")
        f.write(f"- {tests_with_plans}/{len(results)} tests created research plans\n")
        f.write(f"- Average steps per plan: {sum(r.get('num_steps', 0) for r in results if r.get('plan_created')) / max(tests_with_plans, 1):.1f}\n")
        f.write(f"- Average completion rate: {avg_completion:.1f}%\n\n")

        f.write("### Sequential Execution\n\n")
        complete_tests = [r for r in results if r.get('steps_completed', 0) == r.get('num_steps', 0) and r.get('num_steps', 0) > 0]
        f.write(f"- {len(complete_tests)}/{tests_with_plans} tests completed all planned steps\n")
        f.write(f"- Average progress updates per test: {sum(r.get('progress_updates', 0) for r in results) / len(results):.1f}\n\n")

        f.write("### Search Behavior\n\n")
        f.write(f"- Average searches per test: {sum(r.get('search_count', 0) for r in results) / len(results):.1f}\n")
        f.write(f"- Searches per planned step: {total_searches / max(sum(r.get('num_steps', 0) for r in results), 1):.1f}\n\n")

        f.write("### Recommendations for System Prompt Enhancement\n\n")
        f.write("Based on test results, consider:\n\n")

        # Analyze patterns
        if avg_completion < 90:
            f.write("1. **⚠️ Incomplete Execution**: Some tests didn't complete all steps\n")
            f.write("   - Strengthen requirement to complete ALL steps before final response\n")
            f.write("   - Add explicit verification step: read_current_plan() before synthesis\n\n")

        if tests_with_plans < len(results) * 0.8:
            f.write("2. **⚠️ Planning Underutilization**: Some complex queries didn't trigger planning\n")
            f.write("   - Clarify when to use planning tools vs. direct research\n")
            f.write("   - Add complexity heuristics to planning decision\n\n")

        progress_ratio = sum(r.get('progress_updates', 0) for r in results) / max(sum(r.get('steps_completed', 0) for r in results), 1)
        if progress_ratio < 0.9:
            f.write("3. **⚠️ Progress Tracking Gaps**: Not all steps recorded progress updates\n")
            f.write("   - Emphasize MANDATORY progress updates after each step\n")
            f.write("   - Add reminder before step execution\n\n")

        f.write("\n---\n\n")
        f.write("## Next Steps\n\n")
        f.write("1. Review individual test logs for detailed execution traces\n")
        f.write("2. Identify patterns in successful vs. incomplete tests\n")
        f.write("3. Update system prompt based on findings\n")
        f.write("4. Re-run tests to verify improvements\n\n")

        f.write(f"**Report saved**: {summary_file}\n")

    print(f"\n📊 Summary report saved: {summary_file}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main execution function."""

    # Create output directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).parent / "test_results" / f"prompt_test_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📁 Created output directory: {output_dir}\n")

    # Run all tests in parallel
    results = await run_all_tests_parallel(output_dir)

    # Generate summary report
    print("\n" + "="*80)
    print("📊 Generating Summary Report")
    print("="*80 + "\n")

    generate_summary_report(results, output_dir)

    # Save raw results as JSON
    results_json = output_dir / "results.json"
    with open(results_json, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"💾 Raw results saved: {results_json}")

    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETE")
    print("="*80)
    print(f"\nResults directory: {output_dir}")
    print(f"  - {len(TEST_PROMPTS)} individual test logs")
    print(f"  - summary_report.md")
    print(f"  - results.json")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
