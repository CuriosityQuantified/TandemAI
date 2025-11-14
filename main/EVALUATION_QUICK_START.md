# Evaluation Framework - Quick Start Guide

**5-Minute Guide to Running Evaluations**

---

## Prerequisites

```bash
cd /Users/nicholaspate/Documents/01_Active/TandemAI/main
source /Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/.venv/bin/activate
pip install scipy numpy tqdm
```

---

## Basic Usage

### Step 1: Run Benchmark Evaluation

```bash
python run_evaluation.py --version benchmark
```

**What this does**:
- Runs 32 research queries through benchmark prompt
- Evaluates each with 7 judges (224 total evaluations)
- Saves results to `results/aggregated_benchmark.json`

**Time**: ~15-25 minutes

### Step 2: Run Challenger Evaluation

```bash
python run_evaluation.py --version challenger_1
```

### Step 3: Compare Statistically

```bash
python run_evaluation.py --compare benchmark challenger_1
```

**Output**: Statistical comparison with recommendation (ADOPT/REJECT/INCONCLUSIVE)

---

## Quick Testing (5 queries)

```bash
# Test benchmark on 5 queries
python run_evaluation.py --version benchmark --queries 1,2,3,4,5

# Test challenger on same 5 queries
python run_evaluation.py --version challenger_1 --queries 1,2,3,4,5

# Compare
python run_evaluation.py --compare benchmark challenger_1
```

**Time**: ~2-3 minutes

---

## Common Commands

### Run with more workers (faster)
```bash
python run_evaluation.py --version benchmark --workers 8
```

### Force re-evaluation (ignore cache)
```bash
python run_evaluation.py --version benchmark --no-cache
```

### Custom results directory
```bash
python run_evaluation.py --version benchmark --results-dir ./my_results/
```

---

## Understanding Results

### Aggregated Results (`results/aggregated_benchmark.json`)

Key metrics:
- `summary_statistics.<rubric>.mean`: Average score across all queries
- `query_results[N].scores.<rubric>`: Individual query scores

### Comparison Report (`results/statistical_comparison_*.json`)

Look for:
- `p_value < 0.05`: Statistically significant difference
- `mean_difference`: Positive = improvement, negative = regression
- `cohens_d`: Effect size (small/medium/large)
- `overall_recommendation`: ADOPT/REJECT/INCONCLUSIVE

---

## Interpreting p-values

- `p < 0.001`: *** (highly significant)
- `p < 0.01`: ** (very significant)
- `p < 0.05`: * (significant)
- `p ≥ 0.05`: ns (not significant)

---

## Interpreting Cohen's d

- `|d| < 0.2`: Negligible effect
- `0.2 ≤ |d| < 0.5`: Small effect
- `0.5 ≤ |d| < 0.8`: Medium effect
- `|d| ≥ 0.8`: Large effect

---

## Decision Matrix

| Improvements | Regressions | Recommendation |
|--------------|-------------|----------------|
| ≥3           | 0           | **ADOPT** (strong) |
| 1-2          | 0           | **ADOPT** (moderate) |
| Any          | ≥1          | **REJECT** |
| 0            | 0           | **INCONCLUSIVE** |

---

## File Structure

```
results/
├── response_benchmark_q1.json      # Cached researcher response
├── evaluation_benchmark_q1.json    # Cached judge evaluations
├── aggregated_benchmark.json       # Summary statistics
└── statistical_comparison_*.json   # Comparison report
```

---

## Troubleshooting

### Evaluation too slow?
```bash
python run_evaluation.py --version benchmark --workers 8
```

### Want to re-run specific query?
```bash
rm results/response_benchmark_q5.json
rm results/evaluation_benchmark_q5.json
python run_evaluation.py --version benchmark --queries 5
```

### Out of memory?
```bash
python run_evaluation.py --version benchmark --workers 2
```

---

## Next Steps

1. **Review judge decisions**: Check `results/evaluation_*.json` files
2. **Analyze failures**: Look at queries with low scores
3. **Iterate on prompt**: Update challenger based on findings
4. **Re-evaluate**: Run new challenger and compare

---

## Full Documentation

For detailed documentation, see:
- `evaluation/README.md` - Comprehensive guide
- `EVALUATION_FRAMEWORK_IMPLEMENTATION.md` - Implementation details
- `run_evaluation.py --help` - CLI help

---

**Need Help?**

Common issues:
1. **Judge inconsistency**: Review rubrics in `evaluation/rubrics.py`
2. **Statistical INCONCLUSIVE**: Use all 32 queries, not subset
3. **Performance**: Adjust `--workers` parameter

---

**Last Updated**: 2025-11-13
**Status**: Production Ready
