# Phase 3: Evaluation Framework for Benchmark Researcher Agent

Comprehensive test suite for evaluating the benchmark researcher agent's performance on planning quality, execution completeness, source quality, citation accuracy, answer completeness, factual accuracy, and autonomy.

## Overview

This evaluation framework provides **32+ diverse test queries** across **4 categories** to systematically test and measure agent performance.

### Test Categories

1. **Simple Queries** (8 tests) - Single-fact lookups, 3-4 steps
   - Definition + explanation patterns
   - Basic comparisons
   - Technical concept explanations

2. **Multi-Aspect Queries** (8 tests) - Multiple topics, 5-6 steps
   - Framework comparisons (3-4 frameworks)
   - Multi-dimensional analysis
   - Technical deep-dives

3. **Time-Constrained Queries** (8 tests) - Latest/recent information
   - Recent developments (2025)
   - Trend tracking
   - Rolling time windows

4. **Comprehensive Queries** (8 tests) - Exhaustive coverage, 7-10 steps
   - Multi-domain analysis
   - Complete ecosystem overviews
   - Production guides

## Quick Start

### Installation

```bash
# Ensure you're in the ATLAS main directory
cd /Users/nicholaspate/Documents/01_Active/ATLAS/main/

# Activate virtual environment
source /Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/.venv/bin/activate

# Install dependencies (if needed)
pip install langchain langchain-anthropic tavily-python
```

### Run All Tests

```bash
python evaluation/run_tests.py
```

### Run Specific Category

```bash
# Simple queries only
python evaluation/run_tests.py --category simple

# Multi-aspect queries only
python evaluation/run_tests.py --category multi_aspect

# Time-constrained queries only
python evaluation/run_tests.py --category time_constrained

# Comprehensive queries only
python evaluation/run_tests.py --category comprehensive
```

### Run Limited Tests

```bash
# Run only 5 tests
python evaluation/run_tests.py --max-tests 5

# Run 3 simple queries
python evaluation/run_tests.py --category simple --max-tests 3
```

### Run Single Test

```bash
# Run specific test by ID
python evaluation/run_tests.py --test-id SIMPLE-001
python evaluation/run_tests.py --test-id MULTI-001
python evaluation/run_tests.py --test-id TIME-001
python evaluation/run_tests.py --test-id COMP-001
```

## Test Suite Structure

### Test Query Format

Each test query includes:

```python
TestQuery(
    id="SIMPLE-001",  # Unique identifier
    query="What is quantum error correction...",  # Research question
    category=QueryCategory.SIMPLE,  # Complexity category
    expected_steps=4,  # Expected planning steps
    expected_behaviors=[...],  # List of required behaviors
    min_sources=3,  # Minimum source count
    success_criteria={...},  # Pass/fail criteria
    description="Tests...",  # What this tests
    tags=["quantum", "definition"]  # Categorization tags
)
```

### Evaluation Criteria

Each test is evaluated on:

1. **Planning Quality**
   - Was a plan created?
   - Correct number of steps?
   - Appropriate step breakdown?

2. **Execution Completeness**
   - All steps completed?
   - Sequential execution?
   - Progress tracking?

3. **Source Quality**
   - Sufficient number of sources?
   - Authoritative sources?
   - Recent sources (for time-constrained queries)?

4. **Citation Accuracy**
   - Exact quotes included?
   - Full URLs provided?
   - Proper citation format?

5. **Answer Completeness**
   - Covers all query aspects?
   - Addresses all success criteria?
   - Comprehensive synthesis?

6. **Factual Accuracy**
   - Facts match sources?
   - Cross-referenced claims?
   - Conflicts noted?

7. **Autonomy**
   - Completed without prompting?
   - No "should I continue?" questions?
   - Full execution without intervention?

## Results and Reporting

### Output Format

Results are saved to JSON with structure:

```json
{
  "timestamp": "2025-11-13T20:30:00",
  "total_tests": 32,
  "passed": 28,
  "results": [
    {
      "test_query": {...},
      "execution_time": 45.2,
      "plan_created": true,
      "num_steps": 4,
      "steps_completed": 4,
      "num_sources": 5,
      "has_exact_quotes": true,
      "has_source_urls": true,
      "autonomy_score": 1.0,
      "success_criteria_met": {...},
      "overall_pass": true,
      "notes": []
    },
    ...
  ]
}
```

### Viewing Results

```bash
# List all available tests
python evaluation/run_tests.py list

# Analyze saved results
python evaluation/run_tests.py analyze results/evaluation_results.json
```

### Custom Output Path

```bash
python evaluation/run_tests.py --output results/my_evaluation.json
```

## Example Test Queries

### Simple Query Example

```
ID: SIMPLE-001
Query: What is quantum error correction and why is it important?
Expected Steps: 4
Min Sources: 3
Success Criteria:
  - has_definition: True
  - has_importance_explanation: True
  - has_exact_quotes: True
  - plan_created: True
```

### Multi-Aspect Query Example

```
ID: MULTI-001
Query: Compare LangChain vs LlamaIndex vs CrewAI for building AI agent applications
Expected Steps: 5
Min Sources: 6
Success Criteria:
  - covers_langchain: True
  - covers_llamaindex: True
  - covers_crewai: True
  - has_comparison_table: True
  - plan_has_5_steps: True
```

### Time-Constrained Query Example

```
ID: TIME-001
Query: Summarize the latest AI developments and breakthroughs from November 2025
Expected Steps: 6
Min Sources: 8
Success Criteria:
  - has_recent_sources: True
  - sources_from_2025: True
  - covers_multiple_developments: True
```

### Comprehensive Query Example

```
ID: COMP-001
Query: Comprehensive analysis of renewable energy technologies: solar, wind, hydro,
       geothermal, and nuclear - covering technology, economics, environmental
       impact, and future outlook
Expected Steps: 8
Min Sources: 12
Success Criteria:
  - covers_all_5_technologies: True
  - has_technology_section: True
  - has_economics_section: True
  - plan_has_8_steps: True
```

## Integration with Agent

### Agent Function Requirements

The test suite expects an agent function with signature:

```python
def agent_function(query: str) -> Dict[str, Any]:
    """
    Args:
        query: The research question

    Returns:
        Dict containing:
          - messages: List of messages (final message = response)
          - plan: Optional plan dict with steps
          - files: Optional list of created files
    """
    # Your agent implementation
    return result
```

### Example Integration

```python
from evaluation.test_suite import run_evaluation, print_evaluation_summary
from your_module import your_agent_function

# Run evaluation
results = run_evaluation(
    agent_function=your_agent_function,
    category="simple",
    max_tests=5,
    verbose=True
)

# Print summary
print_evaluation_summary(results)

# Save results
from evaluation.test_suite import save_results
save_results(results, output_path="results/my_eval.json")
```

## Expected Behaviors

The test suite checks for these behaviors:

- `MUST_CREATE_PLAN` - Agent creates research plan
- `MUST_EXECUTE_ALL_STEPS` - All planned steps completed
- `MUST_FIND_MULTIPLE_SOURCES` - Multiple authoritative sources
- `MUST_CITE_WITH_QUOTES` - Exact quotes with citations
- `MUST_BE_AUTONOMOUS` - No user prompting required
- `MUST_VERIFY_COMPLETION` - Verifies 100% completion
- `MUST_USE_RECENT_SOURCES` - Recent sources for time-constrained
- `MUST_CROSS_REFERENCE` - Cross-references multiple sources

## Success Thresholds

- **Overall Pass**: ≥70% of success criteria met
- **Autonomy Score**: 1.0 = full autonomous execution
- **Source Count**: Must meet minimum per query
- **Citation Quality**: Must include exact quotes + URLs

## Statistical Significance

For benchmark comparison:
- **Minimum N**: 32 test queries (met by this suite)
- **Confidence Level**: Use 95% confidence intervals
- **Comparison**: Paired t-test for challenger vs benchmark

## Troubleshooting

### Common Issues

**Issue**: Agent not creating plans
**Solution**: Check system prompt includes planning directives

**Issue**: Missing citations
**Solution**: Verify citation protocol in prompt

**Issue**: Incomplete execution
**Solution**: Check for "should I continue?" patterns in responses

**Issue**: Import errors
**Solution**: Ensure virtual environment activated and dependencies installed

### Debug Mode

```python
# Run with verbose output
python evaluation/run_tests.py --verbose

# Run single test for debugging
python evaluation/run_tests.py --test-id SIMPLE-001 --verbose
```

## File Structure

```
evaluation/
├── README.md              # This file
├── test_suite.py          # Test queries and evaluation logic
├── run_tests.py           # CLI runner
└── utils/                 # Utility functions (future)
```

## Extending the Framework

### Adding New Test Queries

```python
# In test_suite.py, add to appropriate category list:

NEW_QUERY = TestQuery(
    id="SIMPLE-009",
    query="Your research question here",
    category=QueryCategory.SIMPLE,
    expected_steps=4,
    expected_behaviors=[
        ExpectedBehavior.MUST_CREATE_PLAN,
        ExpectedBehavior.MUST_CITE_WITH_QUOTES
    ],
    min_sources=3,
    success_criteria={
        "has_definition": True,
        "plan_created": True
    },
    description="Tests new pattern",
    tags=["new-category"]
)

# Add to SIMPLE_QUERIES list
SIMPLE_QUERIES.append(NEW_QUERY)
```

### Custom Evaluation Metrics

```python
# Extend EvaluationResult class for custom metrics
@dataclass
class CustomEvaluationResult(EvaluationResult):
    custom_metric: float

    def calculate_custom_score(self) -> float:
        # Your custom scoring logic
        return score
```

## Best Practices

1. **Baseline First**: Run full suite against baseline prompt
2. **Document Changes**: Track prompt versions and results
3. **Statistical Analysis**: Use 32+ tests for significance
4. **Iterative Improvement**: Analyze failures → Update prompt → Re-test
5. **Version Control**: Track evaluation results in git
6. **Reproducibility**: Use same test suite for comparisons

## Future Enhancements

- [ ] Automated fact-checking integration
- [ ] LLM-as-judge evaluation
- [ ] Citation format validation
- [ ] Source quality scoring
- [ ] Parallel test execution
- [ ] Web dashboard for results
- [ ] A/B testing framework
- [ ] Prompt optimization suggestions

## Resources

- **LangChain Docs**: https://python.langchain.com/docs/
- **Benchmark Prompt**: `/prompts/researcher/benchmark_researcher_prompt.py`
- **Results Directory**: `/results/`
- **Main Agent**: `/module-2-2-simple.py`

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review test query definitions in `test_suite.py`
3. Examine `run_tests.py` for usage examples
4. Analyze saved results JSON for detailed metrics

---

**Version**: 1.0
**Date**: 2025-11-13
**Status**: Production Ready
**Tests**: 32 queries across 4 categories
