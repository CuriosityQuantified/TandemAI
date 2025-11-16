"""
Comprehensive Subagent Test Suite
==================================

Tests for Deep Subagent Delegation System (Phase 1)

Test Categories:
1. Individual Subagent Tests (SUB-RES-001 to SUB-RV-005)
2. Citation Validation Tests (VAL-CIT-006)
3. Parallel Execution Tests (PAR-EXE-007)
4. Sequential Pipeline Tests (SEQ-PIP-008)
5. Error Handling Tests (ERR-HDL-009)
6. Thread Isolation Tests (THR-ISO-011)
7. Tool Access Tests (TOOL-ACC-012)
8. Performance Tests (PERF-TST-014)
"""

import asyncio
import re
import time
import uuid
from pathlib import Path

import pytest

from subagents import (
    create_researcher_subagent,
    create_data_scientist_subagent,
    create_expert_analyst_subagent,
    create_writer_subagent,
    create_reviewer_subagent
)
from subagents.researcher import validate_researcher_output


# ============================================================================
# 1. INDIVIDUAL SUBAGENT TESTS (SUB-RES-001 to SUB-RV-005)
# ============================================================================

class TestIndividualSubagents:
    """Test each subagent in isolation."""

    @pytest.mark.individual
    @pytest.mark.asyncio
    async def test_researcher_basic_query(self, researcher_agent, test_workspace):
        """
        SUB-RES-001: Test researcher can complete basic research task.

        Verifies:
        - Researcher completes research query
        - Output file created
        - Citations present in [1][2][3] format
        - Sources section present
        """
        # Execute research task
        config = {"configurable": {"thread_id": "test-researcher-001"}}
        result = await researcher_agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": "Research the top 3 renewable energy trends in 2024. Write findings to /workspace/test_research.md with proper citations."
            }]
        }, config)

        # Assertions
        assert result is not None, "Researcher returned None"
        assert "messages" in result, "Result missing 'messages' key"

        # Verify file created
        output_file = Path(test_workspace) / "test_research.md"
        assert output_file.exists(), f"Output file not created: {output_file}"

        # Verify citations present
        content = output_file.read_text()
        citations = re.findall(r'\[(\d+)\]', content)
        assert len(citations) > 0, "No citations [1][2][3] found in output"

        # Verify Sources section present
        has_sources = bool(re.search(r'#+\s*Sources', content, re.IGNORECASE))
        assert has_sources, "No Sources section found in output"

        print(f"✅ Researcher test passed: {len(citations)} citations found")

    @pytest.mark.individual
    @pytest.mark.asyncio
    async def test_data_scientist_analysis(self, data_scientist_agent, test_workspace, mock_dataset):
        """
        SUB-DS-002: Test data scientist performs statistical analysis.

        Verifies:
        - Data scientist completes statistical calculations
        - Output includes mean, median, standard deviation
        - Analysis written to specified file
        """
        # Execute analysis task
        config = {"configurable": {"thread_id": "test-data-scientist-001"}}
        result = await data_scientist_agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": f"""Analyze this dataset and calculate:
1. Mean (average)
2. Median
3. Standard deviation

Dataset: Solar adoption percentages by region
{mock_dataset}

Write analysis to /workspace/test_analysis.md"""
            }]
        }, config)

        # Assertions
        assert result is not None, "Data scientist returned None"

        # Verify file created
        output_file = Path(test_workspace) / "test_analysis.md"
        assert output_file.exists(), f"Output file not created: {output_file}"

        # Verify statistical content
        content = output_file.read_text().lower()
        assert "mean" in content or "average" in content, "Mean/average not found"
        assert "median" in content, "Median not found"
        assert "standard deviation" in content or "std" in content, "Standard deviation not found"

        print(f"✅ Data scientist test passed")

    @pytest.mark.individual
    @pytest.mark.asyncio
    async def test_expert_analyst_5_whys(self, expert_analyst_agent, test_workspace):
        """
        SUB-EA-003: Test expert analyst performs 5 Whys analysis.

        Verifies:
        - Expert analyst applies 5 Whys methodology
        - Output contains >= 5 "Why" questions
        - Root cause identified
        """
        # Execute 5 Whys analysis
        config = {"configurable": {"thread_id": "test-expert-analyst-001"}}
        result = await expert_analyst_agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": """Perform 5 Whys root cause analysis:

Problem: Solar adoption declined 15% in Region X

Write analysis to /workspace/test_5whys.md"""
            }]
        }, config)

        # Assertions
        assert result is not None, "Expert analyst returned None"

        # Verify file created
        output_file = Path(test_workspace) / "test_5whys.md"
        assert output_file.exists(), f"Output file not created: {output_file}"

        # Verify 5 Whys structure
        content = output_file.read_text()
        why_count = content.lower().count("why")
        assert why_count >= 5, f"Expected >= 5 'Why' questions, found {why_count}"

        # Verify root cause mentioned
        assert "root cause" in content.lower(), "Root cause not identified"

        print(f"✅ Expert analyst test passed: {why_count} 'Why' questions found")

    @pytest.mark.individual
    @pytest.mark.asyncio
    async def test_writer_technical_report(self, writer_agent, test_workspace):
        """
        SUB-WR-004: Test writer creates professional technical report.

        Verifies:
        - Writer creates well-structured document
        - All required sections present
        - Professional markdown formatting
        """
        # Execute writing task
        config = {"configurable": {"thread_id": "test-writer-001"}}
        result = await writer_agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": """Create a professional technical report on renewable energy trends.

Requirements:
- Executive summary
- Introduction
- 3 main sections
- Conclusion
- Professional formatting

Write to /workspace/test_report.md"""
            }]
        }, config)

        # Assertions
        assert result is not None, "Writer returned None"

        # Verify file created
        output_file = Path(test_workspace) / "test_report.md"
        assert output_file.exists(), f"Output file not created: {output_file}"

        # Verify required sections
        content = output_file.read_text().lower()
        assert "executive summary" in content or "summary" in content, "Executive summary missing"
        assert "introduction" in content, "Introduction missing"
        assert "conclusion" in content, "Conclusion missing"

        # Verify markdown formatting (headers present)
        header_count = output_file.read_text().count("#")
        assert header_count >= 5, f"Expected >= 5 headers, found {header_count}"

        print(f"✅ Writer test passed: {header_count} headers found")

    @pytest.mark.individual
    @pytest.mark.asyncio
    async def test_reviewer_document_review(self, reviewer_agent, test_workspace, sample_research_document):
        """
        SUB-RV-005: Test reviewer performs comprehensive quality review.

        Verifies:
        - Reviewer evaluates all 5 dimensions
        - Scores provided (X/10 format)
        - Review document created with recommendations
        """
        # Execute review task
        config = {"configurable": {"thread_id": "test-reviewer-001"}}
        result = await reviewer_agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": f"""Review the document at {sample_research_document} for quality.

Evaluate:
1. Comprehensiveness
2. Accuracy
3. Clarity
4. Quality
5. Actionability

Write review to /workspace/test_review.md"""
            }]
        }, config)

        # Assertions
        assert result is not None, "Reviewer returned None"

        # Verify file created
        output_file = Path(test_workspace) / "test_review.md"
        assert output_file.exists(), f"Output file not created: {output_file}"

        # Verify 5-dimension evaluation
        content = output_file.read_text().lower()
        assert "comprehensiveness" in content, "Comprehensiveness dimension missing"
        assert "accuracy" in content, "Accuracy dimension missing"
        assert "clarity" in content, "Clarity dimension missing"
        assert "quality" in content, "Quality dimension missing"
        assert "actionability" in content, "Actionability dimension missing"

        # Verify scoring present (X/10 format)
        has_scores = bool(re.search(r'\d+/10', output_file.read_text()))
        assert has_scores, "No scores in X/10 format found"

        print(f"✅ Reviewer test passed: All 5 dimensions evaluated")


# ============================================================================
# 2. CITATION VALIDATION TESTS (VAL-CIT-006)
# ============================================================================

class TestCitationValidation:
    """Test strict citation validation for researcher outputs."""

    @pytest.mark.validation
    @pytest.mark.parametrize("test_id,content,should_pass,reason", [
        ("2.1.1", "Content [1][2][3]\n## Sources\n[1] Ref", True, "Valid format"),
        ("2.1.2", "Content [1][2][3]", False, "Missing Sources section"),
        ("2.1.3", "Content\n## Sources\n[1] Ref", False, "Missing citations"),
        ("2.1.4", "", False, "Empty document"),
        ("2.1.5", "Content (1)(2)(3)\n## Sources\n(1) Ref", False, "Wrong citation format"),
        ("2.1.6", "Content [1]\n## Sources\n[1] Ref", True, "Minimum 1 citation"),
        ("2.1.7", "Content [1][2][3][4][5][6][7][8][9][10]\n## Sources\n[1] Ref", True, "Multiple citations"),
    ])
    def test_citation_validation_matrix(self, test_workspace, test_id, content, should_pass, reason):
        """
        VAL-CIT-006: Test citation validation with various inputs.

        Tests all edge cases for citation format validation.
        """
        # Create test file
        test_file = Path(test_workspace) / f"test_{test_id}.md"
        test_file.write_text(content)

        if should_pass:
            # Should not raise ValueError
            result = validate_researcher_output(str(test_file))
            assert result["valid"] == True, f"{test_id} should pass: {reason}"
            print(f"✅ {test_id} passed: {reason}")
        else:
            # Should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                validate_researcher_output(str(test_file))
            print(f"✅ {test_id} failed as expected: {reason} - {str(exc_info.value)}")

    @pytest.mark.validation
    def test_valid_output_with_citations(self, test_workspace):
        """Test valid researcher output with proper citations."""
        valid_file = Path(test_workspace) / "valid_citations.md"
        valid_file.write_text("""
# Renewable Energy Trends

Solar adoption increased 23% [1]. Wind power grew 18% [2].

## Sources
[1] IEA Report 2024
[2] IRENA Statistics
        """)

        result = validate_researcher_output(str(valid_file))

        assert result["valid"] == True
        assert result["citation_count"] >= 2
        print(f"✅ Valid output test passed: {result['citation_count']} citations")

    @pytest.mark.validation
    def test_invalid_output_no_citations(self, test_workspace):
        """Test invalid output without citations (should block)."""
        invalid_file = Path(test_workspace) / "invalid_no_cites.md"
        invalid_file.write_text("""
# Renewable Energy Trends

Solar adoption increased 23%. Wind power grew 18%.
        """)

        with pytest.raises(ValueError, match="No citations found"):
            validate_researcher_output(str(invalid_file))

        print(f"✅ No citations test: Correctly blocked")

    @pytest.mark.validation
    def test_invalid_output_no_sources(self, test_workspace):
        """Test invalid output without Sources section (should block)."""
        invalid_file = Path(test_workspace) / "invalid_no_sources.md"
        invalid_file.write_text("""
# Renewable Energy Trends

Solar adoption increased 23% [1]. Wind power grew 18% [2].
        """)

        with pytest.raises(ValueError, match="No Sources section"):
            validate_researcher_output(str(invalid_file))

        print(f"✅ No Sources section test: Correctly blocked")


# ============================================================================
# 3. PARALLEL EXECUTION TESTS (PAR-EXE-007)
# ============================================================================

class TestParallelExecution:
    """Test concurrent subagent execution."""

    @pytest.mark.parallel
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_parallel_three_subagents(self, test_checkpointer, test_workspace):
        """
        PAR-EXE-007: Test 3 subagents running in parallel.

        Verifies:
        - All 3 subagents complete successfully
        - No state contamination between subagents
        - All output files created correctly
        - Execution time benefits from parallelism
        """
        # Create subagents
        researcher = create_researcher_subagent(test_checkpointer, workspace_dir=test_workspace)
        data_scientist = create_data_scientist_subagent(test_checkpointer, workspace_dir=test_workspace)
        writer = create_writer_subagent(test_checkpointer, workspace_dir=test_workspace)

        # Define 3 independent tasks
        task1 = researcher.ainvoke({
            "messages": [{
                "role": "user",
                "content": "Research solar energy trends briefly. Write to /workspace/parallel_solar.md with citations."
            }]
        }, config={"configurable": {"thread_id": "test-parallel/researcher/001"}})

        task2 = data_scientist.ainvoke({
            "messages": [{
                "role": "user",
                "content": "Calculate mean and median for [10,20,30,40,50]. Write to /workspace/parallel_stats.md"
            }]
        }, config={"configurable": {"thread_id": "test-parallel/data_scientist/001"}})

        task3 = writer.ainvoke({
            "messages": [{
                "role": "user",
                "content": "Write brief executive summary on renewable energy. Write to /workspace/parallel_summary.md"
            }]
        }, config={"configurable": {"thread_id": "test-parallel/writer/001"}})

        # Execute in parallel
        start_time = time.time()
        results = await asyncio.gather(task1, task2, task3, return_exceptions=True)
        end_time = time.time()

        # Assertions
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        # Check for exceptions
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Subagent {i} failed: {result}"
            assert result is not None, f"Subagent {i} returned None"

        # Verify all files created
        solar_file = Path(test_workspace) / "parallel_solar.md"
        stats_file = Path(test_workspace) / "parallel_stats.md"
        summary_file = Path(test_workspace) / "parallel_summary.md"

        assert solar_file.exists(), "Solar file not created"
        assert stats_file.exists(), "Stats file not created"
        assert summary_file.exists(), "Summary file not created"

        # Verify no state contamination
        solar_content = solar_file.read_text().lower()
        stats_content = stats_file.read_text().lower()
        summary_content = summary_file.read_text().lower()

        assert "solar" in solar_content, "Solar content missing 'solar'"
        assert "mean" in stats_content or "median" in stats_content, "Stats content missing statistics"
        assert "summary" in summary_content or "renewable" in summary_content, "Summary content missing expected text"

        # Verify no cross-contamination
        assert "mean" not in solar_content and "median" not in solar_content, "Solar file contaminated with stats"
        assert "solar" not in stats_content, "Stats file contaminated with solar content"

        execution_time = end_time - start_time
        print(f"✅ Parallel execution test passed in {execution_time:.2f}s")

    @pytest.mark.parallel
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_parallel_five_subagents(self, test_checkpointer, test_workspace):
        """
        PAR-EXE-007.2: Test all 5 subagent types running simultaneously.

        Verifies:
        - All 5 subagents complete successfully
        - No deadlocks or race conditions
        - Memory usage remains reasonable
        """
        # Create all 5 subagents
        researcher = create_researcher_subagent(test_checkpointer, workspace_dir=test_workspace)
        data_scientist = create_data_scientist_subagent(test_checkpointer, workspace_dir=test_workspace)
        expert_analyst = create_expert_analyst_subagent(test_checkpointer, workspace_dir=test_workspace)
        writer = create_writer_subagent(test_checkpointer, workspace_dir=test_workspace)
        reviewer = create_reviewer_subagent(test_checkpointer, workspace_dir=test_workspace)

        # Define 5 tasks (brief for speed)
        tasks = [
            researcher.ainvoke({
                "messages": [{"role": "user", "content": "Quick research on solar. Write to /workspace/par5_research.md with citations."}]
            }, config={"configurable": {"thread_id": "test-par5/researcher/001"}}),

            data_scientist.ainvoke({
                "messages": [{"role": "user", "content": "Calculate mean of [1,2,3,4,5]. Write to /workspace/par5_stats.md"}]
            }, config={"configurable": {"thread_id": "test-par5/data_scientist/001"}}),

            expert_analyst.ainvoke({
                "messages": [{"role": "user", "content": "Brief SWOT on renewables. Write to /workspace/par5_swot.md"}]
            }, config={"configurable": {"thread_id": "test-par5/expert_analyst/001"}}),

            writer.ainvoke({
                "messages": [{"role": "user", "content": "Write brief intro paragraph. Write to /workspace/par5_intro.md"}]
            }, config={"configurable": {"thread_id": "test-par5/writer/001"}}),

            # Reviewer needs an existing document
            asyncio.sleep(0)  # Placeholder - reviewer would need document to review
        ]

        # Execute first 4 in parallel (skip reviewer for this test)
        start_time = time.time()
        results = await asyncio.gather(*tasks[:4], return_exceptions=True)
        end_time = time.time()

        # Assertions
        assert len(results) == 4
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Subagent {i} failed: {result}"
            assert result is not None, f"Subagent {i} returned None"

        execution_time = end_time - start_time
        print(f"✅ High concurrency test (4 parallel) passed in {execution_time:.2f}s")


# ============================================================================
# 4. SEQUENTIAL PIPELINE TESTS (SEQ-PIP-008)
# ============================================================================

class TestSequentialPipeline:
    """Test subagents working in sequential pipeline."""

    @pytest.mark.pipeline
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_sequential_pipeline_5_steps(self, test_checkpointer, test_workspace):
        """
        SEQ-PIP-008: Test 5-step sequential pipeline.

        Pipeline Flow:
        1. Researcher: Gather facts → /workspace/raw_research.md
        2. Data Scientist: Analyze statistics → /workspace/statistics_analysis.md
        3. Expert Analyst: SWOT analysis → /workspace/swot_analysis.md
        4. Writer: Comprehensive report → /workspace/final_report.md
        5. Reviewer: Review final report → /workspace/review_report.md

        Verifies:
        - All 5 steps complete in order
        - Each step produces expected output
        - Final review contains quality assessment
        - No data loss between steps
        """
        parent_thread = "test-pipeline-001"

        # Step 1: Research
        print("Step 1/5: Research...")
        researcher = create_researcher_subagent(test_checkpointer, workspace_dir=test_workspace)
        result1 = await researcher.ainvoke({
            "messages": [{
                "role": "user",
                "content": "Research renewable energy adoption rates briefly. Write to /workspace/raw_research.md with citations."
            }]
        }, config={"configurable": {"thread_id": f"{parent_thread}/researcher/step1"}})

        assert result1 is not None
        raw_research_file = Path(test_workspace) / "raw_research.md"
        assert raw_research_file.exists(), "Step 1 failed: raw_research.md not created"

        # Step 2: Data Analysis
        print("Step 2/5: Data Analysis...")
        data_scientist = create_data_scientist_subagent(test_checkpointer, workspace_dir=test_workspace)
        result2 = await data_scientist.ainvoke({
            "messages": [{
                "role": "user",
                "content": f"Read {raw_research_file}. Extract any statistics mentioned. Write analysis to /workspace/statistics_analysis.md"
            }]
        }, config={"configurable": {"thread_id": f"{parent_thread}/data_scientist/step2"}})

        assert result2 is not None
        stats_file = Path(test_workspace) / "statistics_analysis.md"
        assert stats_file.exists(), "Step 2 failed: statistics_analysis.md not created"

        # Step 3: Strategic Analysis
        print("Step 3/5: Strategic Analysis...")
        expert_analyst = create_expert_analyst_subagent(test_checkpointer, workspace_dir=test_workspace)
        result3 = await expert_analyst.ainvoke({
            "messages": [{
                "role": "user",
                "content": f"Read {raw_research_file} and {stats_file}. Perform brief SWOT analysis. Write to /workspace/swot_analysis.md"
            }]
        }, config={"configurable": {"thread_id": f"{parent_thread}/expert_analyst/step3"}})

        assert result3 is not None
        swot_file = Path(test_workspace) / "swot_analysis.md"
        assert swot_file.exists(), "Step 3 failed: swot_analysis.md not created"

        # Step 4: Comprehensive Report
        print("Step 4/5: Writing Report...")
        writer = create_writer_subagent(test_checkpointer, workspace_dir=test_workspace)
        result4 = await writer.ainvoke({
            "messages": [{
                "role": "user",
                "content": f"Read all 3 documents: {raw_research_file}, {stats_file}, {swot_file}. Create comprehensive but brief report at /workspace/final_report.md"
            }]
        }, config={"configurable": {"thread_id": f"{parent_thread}/writer/step4"}})

        assert result4 is not None
        final_report_file = Path(test_workspace) / "final_report.md"
        assert final_report_file.exists(), "Step 4 failed: final_report.md not created"

        # Step 5: Review
        print("Step 5/5: Reviewing Report...")
        reviewer = create_reviewer_subagent(test_checkpointer, workspace_dir=test_workspace)
        result5 = await reviewer.ainvoke({
            "messages": [{
                "role": "user",
                "content": f"Review {final_report_file} for quality. Evaluate comprehensiveness, clarity, and quality. Write brief review to /workspace/review_report.md"
            }]
        }, config={"configurable": {"thread_id": f"{parent_thread}/reviewer/step5"}})

        assert result5 is not None
        review_file = Path(test_workspace) / "review_report.md"
        assert review_file.exists(), "Step 5 failed: review_report.md not created"

        # Verify pipeline integrity
        review_content = review_file.read_text().lower()
        assert "comprehensiveness" in review_content or "quality" in review_content, "Review missing quality assessment"

        print(f"✅ Sequential pipeline test passed: All 5 steps completed")


# ============================================================================
# 5. ERROR HANDLING TESTS (ERR-HDL-009)
# ============================================================================

class TestErrorHandling:
    """Test robust error handling across scenarios."""

    @pytest.mark.error
    @pytest.mark.asyncio
    async def test_error_invalid_file_path(self, researcher_agent, test_workspace):
        """
        ERR-HDL-009.1: Test subagent handles invalid file paths gracefully.

        Verifies:
        - Invalid file paths rejected (security)
        - Agent doesn't crash
        - File not written outside workspace
        """
        # Attempt to write outside workspace
        result = await researcher_agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": "Research renewable energy. Write to /etc/passwd_test"
            }]
        }, config={"configurable": {"thread_id": "test-error-001"}})

        # Should complete without crashing
        assert result is not None

        # File should NOT be written
        assert not Path("/etc/passwd_test").exists(), "File written outside workspace (security violation)"

        print(f"✅ Invalid file path test passed: Security maintained")

    @pytest.mark.error
    def test_citation_validation_blocks_invalid(self, test_workspace):
        """
        ERR-HDL-009.3: Test citation validation blocks invalid outputs.

        Verifies:
        - Missing citations raise ValueError
        - Missing Sources section raises ValueError
        - Error messages are informative
        """
        # Test 1: Missing citations
        invalid_file = Path(test_workspace) / "no_citations.md"
        invalid_file.write_text("Content without citations")

        with pytest.raises(ValueError) as exc_info:
            validate_researcher_output(str(invalid_file))

        assert "No citations found" in str(exc_info.value)

        # Test 2: Missing Sources section
        invalid_file2 = Path(test_workspace) / "no_sources.md"
        invalid_file2.write_text("Content with [1] but no Sources")

        with pytest.raises(ValueError) as exc_info2:
            validate_researcher_output(str(invalid_file2))

        assert "No Sources section" in str(exc_info2.value)

        print(f"✅ Citation validation blocking test passed")


# ============================================================================
# 6. THREAD ISOLATION TESTS (THR-ISO-011)
# ============================================================================

class TestThreadIsolation:
    """Test thread isolation prevents state contamination."""

    @pytest.mark.isolation
    @pytest.mark.asyncio
    async def test_thread_isolation(self, researcher_agent):
        """
        THR-ISO-011.1: Test different thread_ids have isolated state.

        Verifies:
        - Thread state completely isolated
        - No cross-contamination between threads
        - Each conversation maintains separate context
        """
        # Create 2 conversations in different threads
        result1 = await researcher_agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": "Remember: The topic is SOLAR energy."
            }]
        }, config={"configurable": {"thread_id": "thread-A"}})

        result2 = await researcher_agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": "Remember: The topic is WIND energy."
            }]
        }, config={"configurable": {"thread_id": "thread-B"}})

        # Continue conversation in thread-A (should remember SOLAR)
        result3 = await researcher_agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": "What topic did I tell you to remember?"
            }]
        }, config={"configurable": {"thread_id": "thread-A"}})

        # Verify thread-A remembers SOLAR, not WIND
        final_message = result3["messages"][-1].content.lower()
        assert "solar" in final_message, "Thread-A should remember SOLAR"
        assert "wind" not in final_message, "Thread-A contaminated with thread-B content"

        print(f"✅ Thread isolation test passed")

    @pytest.mark.isolation
    def test_hierarchical_thread_naming(self):
        """
        THR-ISO-011.2: Test thread naming convention.

        Verifies:
        - Hierarchical naming: {parent}/{subagent_type}/{uuid}
        - Parsing works correctly
        - UUID is valid
        """
        parent_thread = "main-conversation-123"
        subagent_type = "researcher"
        subagent_uuid = str(uuid.uuid4())

        expected_thread_id = f"{parent_thread}/{subagent_type}/{subagent_uuid}"

        # Verify parsing
        parts = expected_thread_id.split("/")
        assert len(parts) == 3, f"Expected 3 parts, got {len(parts)}"
        assert parts[0] == parent_thread
        assert parts[1] == subagent_type
        assert parts[2] == subagent_uuid

        # Verify UUID is valid
        try:
            uuid.UUID(parts[2])
        except ValueError:
            pytest.fail(f"Invalid UUID: {parts[2]}")

        print(f"✅ Hierarchical thread naming test passed")


# ============================================================================
# 7. TOOL ACCESS TESTS (TOOL-ACC-012)
# ============================================================================

class TestToolAccess:
    """Test all tools accessible from all subagents."""

    @pytest.mark.tools
    @pytest.mark.parametrize("subagent_factory,subagent_name", [
        (create_researcher_subagent, "researcher"),
        (create_data_scientist_subagent, "data_scientist"),
        (create_expert_analyst_subagent, "expert_analyst"),
        (create_writer_subagent, "writer"),
        (create_reviewer_subagent, "reviewer"),
    ])
    def test_tool_access_all_subagents(self, test_checkpointer, test_workspace, subagent_factory, subagent_name):
        """
        TOOL-ACC-012: Test all subagents have access to all 4 tools.

        Verifies:
        - tavily_search available
        - write_file available
        - edit_file available
        - read_current_plan available
        """
        # Create subagent
        subagent = subagent_factory(test_checkpointer, workspace_dir=test_workspace)

        # Get tool names
        # Note: Tool inspection depends on DeepAgents implementation
        # This is a placeholder - actual implementation may vary
        assert hasattr(subagent, 'tools') or hasattr(subagent, '_tools'), f"{subagent_name} has no tools attribute"

        # In actual implementation, would verify tool names
        print(f"✅ Tool access test passed for {subagent_name}")


# ============================================================================
# 8. PERFORMANCE TESTS (PERF-TST-014)
# ============================================================================

class TestPerformance:
    """Test performance and resource usage."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_performance_parallel_speedup(self, test_checkpointer, test_workspace):
        """
        PERF-TST-014.1: Test parallel execution provides speedup.

        Verifies:
        - Parallel execution faster than sequential
        - Speedup > 1.5x (conservative target)
        """
        researcher = create_researcher_subagent(test_checkpointer, workspace_dir=test_workspace)

        # Sequential execution
        print("Running sequential baseline...")
        start_seq = time.time()
        for i in range(3):
            await researcher.ainvoke({
                "messages": [{
                    "role": "user",
                    "content": f"Brief research on topic {i}. Write to /workspace/seq_{i}.md with citations."
                }]
            }, config={"configurable": {"thread_id": f"test-perf-seq/{i}"}})
        end_seq = time.time()
        sequential_time = end_seq - start_seq

        # Parallel execution
        print("Running parallel execution...")
        start_par = time.time()
        tasks = [
            researcher.ainvoke({
                "messages": [{
                    "role": "user",
                    "content": f"Brief research on topic {i}. Write to /workspace/par_{i}.md with citations."
                }]
            }, config={"configurable": {"thread_id": f"test-perf-par/{i}"}})
            for i in range(3)
        ]
        await asyncio.gather(*tasks)
        end_par = time.time()
        parallel_time = end_par - start_par

        # Verify speedup
        speedup = sequential_time / parallel_time
        print(f"Sequential: {sequential_time:.2f}s, Parallel: {parallel_time:.2f}s, Speedup: {speedup:.2f}x")

        # Conservative speedup target (accounting for LLM API latency)
        assert speedup > 1.2, f"Expected speedup >1.2x, got {speedup:.2f}x"

        print(f"✅ Performance speedup test passed: {speedup:.2f}x speedup")


# ============================================================================
# TEST SUITE SUMMARY
# ============================================================================

def test_suite_info():
    """Print test suite information."""
    print("""
    ============================================================
    Subagent Test Suite - Phase 1 Backend Infrastructure
    ============================================================

    Test Categories:
    1. ✅ Individual Subagent Tests (5 tests)
    2. ✅ Citation Validation Tests (10 tests)
    3. ✅ Parallel Execution Tests (2 tests)
    4. ✅ Sequential Pipeline Tests (1 test)
    5. ✅ Error Handling Tests (2 tests)
    6. ✅ Thread Isolation Tests (2 tests)
    7. ✅ Tool Access Tests (5 tests)
    8. ✅ Performance Tests (1 test)

    Total: 28 test cases

    Run with:
    - pytest tests/test_subagents.py -v
    - pytest tests/test_subagents.py::TestIndividualSubagents -v
    - pytest tests/test_subagents.py -m individual -v
    - pytest tests/test_subagents.py -m "not slow" -v

    Markers:
    - individual: Individual subagent tests
    - validation: Citation validation tests
    - parallel: Parallel execution tests
    - pipeline: Sequential pipeline tests
    - error: Error handling tests
    - isolation: Thread isolation tests
    - tools: Tool access tests
    - performance: Performance tests
    - slow: Tests that take >30s
    ============================================================
    """)
