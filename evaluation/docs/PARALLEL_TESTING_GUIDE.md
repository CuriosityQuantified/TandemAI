# Parallel Prompt Testing Framework - Guide

**Status**: ✅ RUNNING (Started: November 12, 2025, 21:15 PST)

**Output Directory**: `/test_results/prompt_test_20251112_211520/`

---

## Overview

This framework tests the enhanced researcher system prompt across 10 diverse query patterns to identify areas for improvement. Each test saves detailed execution logs for longitudinal analysis.

## 10 Test Prompts

### Test 01: Simple Factual Query ✅ (COMPLETE)
**Prompt**: "What is quantum entanglement?"
**Purpose**: Baseline behavior for simple queries
**Expected**: Should skip planning tools, provide direct answer with citations
**Focus**: Citation quality, fact accuracy
**Status**: Complete (25KB log generated)

### Test 02: Complex Multi-Aspect Query
**Prompt**: Comprehensive research on quantum computing hardware (2024-2025)
**Purpose**: Test high-quality prompt engineering and comprehensive planning
**Expected**: 5-7 step plan, detailed research per area, extensive citations
**Focus**: Planning quality, sequential execution, progress tracking
**Key Features**:
- Explicit context (enterprise adoption decision)
- Clear goal (top 3 platforms by qubit count and error rates)
- Three focus areas (hardware specs, error correction, commercial availability)
- Success criteria (3+ peer-reviewed sources per area)
- Constraints (Nature/Science/IEEE + IBM/Google/IonQ)

### Test 03: Time-Constrained Query
**Prompt**: Quantum computing breakthroughs from last 3 months (August 2024+)
**Purpose**: Test temporal filtering and date verification
**Expected**: Careful date checking, flagging older sources
**Focus**: Date accuracy, source freshness

### Test 04: Source-Specific Query
**Prompt**: Quantum error correction from ONLY peer-reviewed journals (Nature/Science/Physical Review 2024)
**Purpose**: Test source discrimination and rigorous citation standards
**Expected**: Careful source selection, academic-only citations with DOIs
**Focus**: Citation precision, source quality verification

### Test 05: Comparison Query
**Prompt**: Compare superconducting qubits vs. trapped ion qubits
**Purpose**: Test structured comparison and balanced coverage
**Expected**: Equal depth for both approaches, quantitative comparison
**Focus**: Balanced research, structured synthesis

### Test 06: Trend Analysis Query
**Prompt**: Evolution of quantum computing error rates 2020-2025
**Purpose**: Test longitudinal analysis and temporal organization
**Expected**: Chronological structure, quantitative progression
**Focus**: Temporal organization, data synthesis

### Test 07: Technical Deep-Dive Query
**Prompt**: Technical details of surface code quantum error correction
**Purpose**: Test technical depth and complex topic handling
**Expected**: Detailed technical explanation with precise citations, equations/metrics
**Focus**: Accuracy for complex topics, expert-level citation quality

### Test 08: Contradictory Sources Query
**Prompt**: Quantum advantage/supremacy claims (Google vs. IBM critiques)
**Purpose**: Test handling contradictions and maintaining neutrality
**Expected**: Explicit conflict identification with balanced quotes from all sides
**Focus**: Objectivity, conflict resolution approach

### Test 09: Emerging Topic Query
**Prompt**: Quantum computing in drug discovery (2024)
**Purpose**: Test handling limited sources and uncertainty communication
**Expected**: Explicit knowledge gap identification, distinction between results vs. potential
**Focus**: Intellectual honesty, limitation acknowledgment

### Test 10: Comprehensive Survey Query
**Prompt**: Complete quantum computing landscape for $50M investment decision
**Purpose**: Maximum complexity stress test
**Expected**: 10-15 step plan, longest execution, most extensive citations
**Coverage**: Hardware, software, error correction, applications, key players, timelines, investment landscape
**Focus**: Complete workflow test, stress test all capabilities

---

## Execution Details

### Parallelism
- **Concurrency**: Up to 3 tests running simultaneously
- **Rate Limiting**: Respects Anthropic API rate limits
- **Duration**: Estimated 30-60 minutes for all 10 tests

### Output Files

For each test, the framework generates:

1. **Individual Log File**: `test_XX_[name].log`
   - Complete execution trace
   - All messages (HumanMessage, AIMessage, ToolMessage)
   - Tool calls with arguments
   - Timestamped events
   - Test summary with metrics

2. **Summary Report**: `summary_report.md`
   - Aggregate metrics across all tests
   - Individual test results
   - Analysis and recommendations
   - System prompt enhancement suggestions

3. **Raw Data**: `results.json`
   - Machine-readable JSON for programmatic analysis
   - All metrics for each test
   - Timestamp data for longitudinal tracking

---

## Metrics Tracked

For each test, the framework tracks:

### Planning Metrics
- `plan_created` (boolean): Did researcher create a plan?
- `num_steps` (int): Number of planned steps
- `steps_completed` (int): Number of steps marked complete
- `completion_percentage` (float): % of plan completed

### Execution Metrics
- `search_count` (int): Number of web searches performed
- `progress_updates` (int): Number of `update_plan_progress` calls
- `tool_calls` (int): Total tool invocations
- `total_messages` (int): Messages in final state
- `duration_seconds` (float): Total execution time

### Quality Indicators
- **Sequential Execution**: Are steps completed in order (0→1→2→...)?
- **Progress Tracking**: Does progress_updates match steps_completed?
- **Prompt Engineering**: For planning tests, did researcher craft good plan query?
- **Completion**: Did researcher finish ALL steps before final response?

---

## Analysis Goals

After all tests complete, analyze:

### 1. Planning Behavior
- Which queries triggered planning? (simple should skip, complex should use)
- Average steps per plan
- Completion rate for planned research

### 2. Sequential Execution
- Are steps executed in order?
- Are all steps completed before synthesis?
- Proper use of `update_plan_progress`

### 3. Prompt Engineering
- For complex queries, did researcher create well-structured plan queries?
- Inclusion of context, goal, constraints, success criteria

### 4. Citation Quality
- Consistent use of exact quotes
- Full attribution (source, URL, date)
- Cross-referencing for important claims

### 5. Edge Cases
- Time-constrained queries: proper date filtering
- Source-specific queries: rigorous source selection
- Contradictory sources: explicit conflict presentation
- Limited sources: knowledge gap acknowledgment

---

## How to Use Results

### Immediate Analysis

```bash
# Check progress
ls -lh test_results/prompt_test_20251112_211520/

# View completed test
cat test_results/prompt_test_20251112_211520/test_01_simple_factual_query.log

# Monitor execution
tail -f parallel_test_execution.log
```

### Post-Completion Analysis

1. **Read Summary Report**
   ```bash
   cat test_results/prompt_test_20251112_211520/summary_report.md
   ```

2. **Review Individual Logs**
   - Focus on tests that failed or had low completion percentages
   - Compare successful vs. incomplete tests
   - Identify patterns in errors or omissions

3. **Extract Insights**
   - What prompts triggered planning? What didn't?
   - Did researcher complete all planned steps?
   - Are progress updates consistent?
   - Citation quality across different query types

4. **Update System Prompt**
   - Add reminders for identified gaps
   - Strengthen requirements that were missed
   - Add examples for edge cases
   - Clarify ambiguous instructions

---

## Expected Patterns

### Good Behavior ✅
- Simple queries (Test 01): No planning, direct answer with citations
- Complex queries (Tests 02, 10): Multi-step plan, sequential execution, all steps complete
- Time-constrained (Test 03): Explicit date checking
- Source-specific (Test 04): Only requested source types
- Comparisons (Test 05): Balanced coverage of both sides
- Contradictions (Test 08): Explicit conflict presentation

### Red Flags ❌
- Complex queries without planning
- Partial execution (only completing 2/5 steps)
- Missing progress updates
- Skipping steps or out-of-order execution
- Final response before all steps complete
- Poor plan query quality (vague, no constraints)

---

## Longitudinal Tracking

This framework enables longitudinal analysis across prompt iterations:

1. **Run Baseline** (Today): Capture current behavior
2. **Update Prompt**: Add enhancements based on findings
3. **Run Comparison**: Test same prompts with updated prompt
4. **Measure Improvement**: Compare metrics across runs

### Tracking File

Create `test_results/longitudinal_tracking.json`:

```json
{
  "runs": [
    {
      "date": "2025-11-12",
      "prompt_version": "v1.0_initial",
      "avg_completion": 78.5,
      "avg_searches_per_step": 1.2,
      "planning_rate": 0.7
    },
    {
      "date": "2025-11-14",
      "prompt_version": "v1.1_enhanced_completion",
      "avg_completion": 95.2,
      "avg_searches_per_step": 1.5,
      "planning_rate": 0.9
    }
  ]
}
```

---

## Next Steps

After tests complete:

1. ✅ Review `summary_report.md` for high-level insights
2. ✅ Examine individual logs for detailed behavior
3. ✅ Identify system prompt gaps and ambiguities
4. ✅ Draft prompt enhancements
5. ✅ Re-run same tests to measure improvement
6. ✅ Iterate until target completion rate (>95%)

---

**Framework Location**: `/backend/test_configs/parallel_prompt_testing.py`

**Documentation**: This file (PARALLEL_TESTING_GUIDE.md)

**Status**: Running (check `parallel_test_execution.log` for real-time progress)

---

## Current Test Status

Check status with:

```bash
# Count completed tests
ls test_results/prompt_test_20251112_211520/*.log | wc -l

# Check file sizes (larger = more complete)
ls -lh test_results/prompt_test_20251112_211520/*.log

# Monitor execution
tail -f parallel_test_execution.log
```

Expected completion: ~30-60 minutes for all 10 tests.
