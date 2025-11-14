# Evaluation Framework - Quick Reference Guide

## One-Liner Commands

```bash
# Run all 32 tests
python evaluation/run_tests.py

# Run simple category (8 tests)
python evaluation/run_tests.py --category simple

# Run 5 tests (quick validation)
python evaluation/run_tests.py --max-tests 5

# Run single test
python evaluation/run_tests.py --test-id SIMPLE-001

# List all tests
python evaluation/run_tests.py list

# Analyze results
python evaluation/run_tests.py analyze results/evaluation_results.json
```

## Test IDs Quick Reference

### Simple Queries (3-4 steps, single topic)
- **SIMPLE-001**: Quantum error correction definition
- **SIMPLE-002**: Python vs JavaScript comparison
- **SIMPLE-003**: How transformers work (NLP)
- **SIMPLE-004**: Renewable energy pros/cons
- **SIMPLE-005**: Bitcoin consensus mechanism
- **SIMPLE-006**: REST vs GraphQL APIs
- **SIMPLE-007**: Vector databases explanation
- **SIMPLE-008**: Microservices principles

### Multi-Aspect Queries (5-6 steps, multiple topics)
- **MULTI-001**: LangChain vs LlamaIndex vs CrewAI
- **MULTI-002**: LLM state: capabilities, limits, costs, trends
- **MULTI-003**: Quantum error correction deep-dive
- **MULTI-004**: AI database comparison (4 options)
- **MULTI-005**: ML cloud platforms (AWS, GCP, Azure, Databricks)
- **MULTI-006**: RAG approaches comparison
- **MULTI-007**: Data science languages (Python, R, Julia, SQL)
- **MULTI-008**: AI agent architectures

### Time-Constrained Queries (recent information)
- **TIME-001**: Latest AI developments (Nov 2025)
- **TIME-002**: Quantum computing achievements (2025)
- **TIME-003**: Open-source AI releases (past 3 months)
- **TIME-004**: LangChain/LangGraph updates (2025)
- **TIME-005**: Protein folding breakthroughs (2024-2025)
- **TIME-006**: Cybersecurity threats (past month)
- **TIME-007**: Claude and GPT releases (2025)
- **TIME-008**: Vector DB and embedding trends (2025)

### Comprehensive Queries (7-10 steps, exhaustive)
- **COMP-001**: Renewable energy complete analysis
- **COMP-002**: Production AI applications guide
- **COMP-003**: Modern web development overview
- **COMP-004**: ML lifecycle complete guide
- **COMP-005**: AI agent frameworks ecosystem
- **COMP-006**: Distributed systems complete guide
- **COMP-007**: AI safety and alignment analysis
- **COMP-008**: Blockchain ecosystem overview

## Expected Results by Category

### Simple Queries
- **Expected Steps**: 4
- **Min Sources**: 3
- **Expected Time**: 30-60 seconds
- **Pass Criteria**: 70% of success criteria

### Multi-Aspect Queries
- **Expected Steps**: 5-6
- **Min Sources**: 5-8
- **Expected Time**: 60-120 seconds
- **Pass Criteria**: 70% of success criteria

### Time-Constrained Queries
- **Expected Steps**: 5-6
- **Min Sources**: 5-8
- **Expected Time**: 60-120 seconds
- **Pass Criteria**: 70% + recent sources

### Comprehensive Queries
- **Expected Steps**: 7-10
- **Min Sources**: 10-15
- **Expected Time**: 120-180 seconds
- **Pass Criteria**: 70% + all aspects covered

## Success Criteria Examples

### Planning Quality
```python
success_criteria = {
    "plan_created": True,           # Was plan created?
    "plan_has_5_steps": True,       # Correct step count?
    "all_steps_completed": True     # All finished?
}
```

### Citation Quality
```python
success_criteria = {
    "has_exact_quotes": True,       # Exact quotes included?
    "has_source_urls": True,        # Full URLs provided?
    "has_multiple_sources": True    # 3+ sources?
}
```

### Content Coverage
```python
success_criteria = {
    "covers_topic_a": True,         # First aspect covered?
    "covers_topic_b": True,         # Second aspect covered?
    "has_comparison": True,         # Comparison section?
    "has_synthesis": True           # Final synthesis?
}
```

## Evaluation Metrics

### Autonomy Score
- **1.0** = Fully autonomous (all steps completed without prompting)
- **0.5** = Partial autonomy (some steps completed)
- **0.0** = Failed to execute

### Pass Rate
- **≥90%** = Excellent
- **70-89%** = Good (passing)
- **50-69%** = Fair (needs improvement)
- **<50%** = Poor (failing)

### Citation Score (heuristic)
- Count unique URLs in response
- Check for quotation marks
- Verify source list at end
- Minimum 3 sources for pass

## Common Patterns

### Pattern 1: Definition + Explanation
```
Query: "What is X and why is it important?"
Expected:
  - Step 0: Search for X definition
  - Step 1: Search for X importance/applications
  - Step 2: Find examples/use cases
  - Step 3: Synthesize findings
```

### Pattern 2: Comparison (2-way)
```
Query: "Compare A vs B"
Expected:
  - Step 0: Research A overview + strengths
  - Step 1: Research B overview + strengths
  - Step 2: Head-to-head comparison
  - Step 3: Use case recommendations
```

### Pattern 3: Comparison (3-way)
```
Query: "Compare A vs B vs C"
Expected:
  - Step 0: Research A
  - Step 1: Research B
  - Step 2: Research C
  - Step 3: Comparison matrix
  - Step 4: Recommendations
```

### Pattern 4: Time-Constrained
```
Query: "Latest developments in X (2025)"
Expected:
  - Step 0: Search recent X developments
  - Step 1: Search X breakthroughs
  - Step 2: Search X releases/announcements
  - Step 3: Cross-reference sources
  - Step 4: Verify dates
  - Step 5: Synthesize timeline
```

### Pattern 5: Comprehensive Survey
```
Query: "Complete analysis of X: aspects A, B, C, D"
Expected:
  - Step 0: Research aspect A
  - Step 1: Research aspect B
  - Step 2: Research aspect C
  - Step 3: Research aspect D
  - Step 4: Economic comparison
  - Step 5: Future trends
  - Step 6: Synthesis
```

## Python API Quick Reference

### Run Tests Programmatically

```python
from evaluation.test_suite import (
    TEST_QUERIES,
    run_evaluation,
    run_single_test,
    print_evaluation_summary,
    save_results
)

# Your agent function
def my_agent(query: str) -> Dict[str, Any]:
    # Implementation
    return result

# Run all tests
results = run_evaluation(my_agent)

# Run category
results = run_evaluation(my_agent, category="simple")

# Run single test
test_query = TEST_QUERIES[0]
result = run_single_test(my_agent, test_query)

# Print summary
print_evaluation_summary(results)

# Save results
save_results(results, "results/my_eval.json")
```

### Access Test Queries

```python
from evaluation.test_suite import TEST_QUERIES, QueryCategory

# Get all simple queries
simple = [q for q in TEST_QUERIES if q.category == QueryCategory.SIMPLE]

# Get specific test by ID
test = next(q for q in TEST_QUERIES if q.id == "SIMPLE-001")

# Print test details
print(test.query)
print(test.expected_steps)
print(test.min_sources)
print(test.success_criteria)
```

### Custom Evaluation

```python
from evaluation.test_suite import run_single_test, TestQuery

# Create custom test
custom_test = TestQuery(
    id="CUSTOM-001",
    query="Your research question",
    category=QueryCategory.SIMPLE,
    expected_steps=4,
    expected_behaviors=[...],
    min_sources=3,
    success_criteria={...},
    description="Tests custom pattern"
)

# Run it
result = run_single_test(my_agent, custom_test)
print(f"Pass: {result.overall_pass}")
print(f"Score: {result.pass_rate():.1f}%")
```

## Interpreting Results

### Result JSON Structure
```json
{
  "test_query": {...},           // Original test query
  "execution_time": 45.2,        // Seconds
  "plan_created": true,          // Planning
  "num_steps": 4,                // Steps in plan
  "steps_completed": 4,          // Completed steps
  "num_sources": 5,              // Unique sources
  "has_exact_quotes": true,      // Citation quality
  "has_source_urls": true,       // URL inclusion
  "autonomy_score": 1.0,         // Autonomy (0-1)
  "success_criteria_met": {...}, // Detailed criteria
  "overall_pass": true,          // Pass/fail
  "notes": []                    // Issues/observations
}
```

### Success Criteria Breakdown
```json
"success_criteria_met": {
  "plan_created": true,
  "all_steps_completed": true,
  "has_definition": true,
  "has_importance_explanation": true,
  "has_exact_quotes": true,
  "has_source_urls": true
}
```

### Common Notes/Issues
- "Expected X steps, got Y" - Step count mismatch
- "Expected X sources, got Y" - Insufficient sources
- "Missing exact quotes" - Citation format issue
- "Error: <message>" - Execution failure

## Troubleshooting Checklist

- [ ] Virtual environment activated?
- [ ] Dependencies installed? (`langchain`, `langchain-anthropic`, `tavily-python`)
- [ ] API keys set? (`ANTHROPIC_API_KEY`, `TAVILY_API_KEY`)
- [ ] Agent function returns correct format?
- [ ] Using correct Python interpreter?
- [ ] Results directory exists?

## Key Files

```
/Users/nicholaspate/Documents/01_Active/ATLAS/main/
├── evaluation/
│   ├── test_suite.py              # 32 test queries + evaluation logic
│   ├── run_tests.py               # CLI runner
│   ├── README.md                  # Full documentation
│   └── QUICK_REFERENCE.md         # This file
├── prompts/
│   └── researcher/
│       └── benchmark_researcher_prompt.py  # Baseline prompt
├── results/
│   └── evaluation_results.json    # Saved results
└── module-2-2-simple.py           # Main agent (example)
```

## Statistical Significance

For benchmark comparisons:
- **N ≥ 32**: This test suite meets minimum for statistical significance
- **Confidence**: Use 95% confidence intervals
- **Test**: Paired t-test (challenger vs benchmark)
- **Effect Size**: Cohen's d for practical significance

---

**Quick Help**: `python evaluation/run_tests.py --help`
**List Tests**: `python evaluation/run_tests.py list`
**Version**: 1.0 | **Date**: 2025-11-13
