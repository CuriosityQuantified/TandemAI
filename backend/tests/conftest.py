"""
Pytest Configuration and Fixtures for Subagent Testing
=======================================================

Provides shared fixtures and test utilities for comprehensive subagent testing.
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest

# Add backend to path for imports
backend_dir = str(Path(__file__).parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)


@pytest.fixture(scope="session")
def event_loop():
    """
    Create event loop for async tests.

    Scope: session (reused across all tests)
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_workspace(tmp_path):
    """
    Create isolated test workspace for each test.

    Provides:
    - Temporary workspace directory
    - Automatic cleanup after test
    - Isolated from other tests

    Scope: function (new workspace per test)
    """
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (workspace_dir / "reports").mkdir(exist_ok=True)
    (workspace_dir / "analysis").mkdir(exist_ok=True)
    (workspace_dir / "reviews").mkdir(exist_ok=True)
    (workspace_dir / "research").mkdir(exist_ok=True)

    yield str(workspace_dir)

    # Cleanup happens automatically with tmp_path


@pytest.fixture(scope="function")
def test_checkpointer():
    """
    Create in-memory checkpointer for testing.

    Uses MemorySaver instead of PostgreSQL for faster tests.
    State is isolated per test.

    Scope: function (new checkpointer per test)
    """
    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()
    return checkpointer


@pytest.fixture(scope="function")
async def researcher_agent(test_checkpointer, test_workspace):
    """
    Create researcher subagent for testing.

    Returns configured researcher agent with:
    - In-memory checkpointer
    - Isolated test workspace
    - All 4 tools available

    Scope: function (new agent per test)
    """
    from subagents import create_researcher_subagent
    from module_2_2_simple import set_workspace_dir

    # Set workspace directory for tools to use test workspace
    set_workspace_dir(test_workspace)

    researcher = create_researcher_subagent(
        checkpointer=test_checkpointer,
        workspace_dir=test_workspace
    )
    return researcher


@pytest.fixture(scope="function")
async def data_scientist_agent(test_checkpointer, test_workspace):
    """
    Create data scientist subagent for testing.

    Returns configured data scientist agent with:
    - In-memory checkpointer
    - Isolated test workspace
    - All 4 tools available

    Scope: function (new agent per test)
    """
    from subagents import create_data_scientist_subagent
    from module_2_2_simple import set_workspace_dir

    set_workspace_dir(test_workspace)

    data_scientist = create_data_scientist_subagent(
        checkpointer=test_checkpointer,
        workspace_dir=test_workspace
    )
    return data_scientist


@pytest.fixture(scope="function")
async def expert_analyst_agent(test_checkpointer, test_workspace):
    """
    Create expert analyst subagent for testing.

    Returns configured expert analyst agent with:
    - In-memory checkpointer
    - Isolated test workspace
    - All 4 tools available

    Scope: function (new agent per test)
    """
    from subagents import create_expert_analyst_subagent
    from module_2_2_simple import set_workspace_dir

    set_workspace_dir(test_workspace)

    expert_analyst = create_expert_analyst_subagent(
        checkpointer=test_checkpointer,
        workspace_dir=test_workspace
    )
    return expert_analyst


@pytest.fixture(scope="function")
async def writer_agent(test_checkpointer, test_workspace):
    """
    Create writer subagent for testing.

    Returns configured writer agent with:
    - In-memory checkpointer
    - Isolated test workspace
    - All 4 tools available

    Scope: function (new agent per test)
    """
    from subagents import create_writer_subagent
    from module_2_2_simple import set_workspace_dir

    set_workspace_dir(test_workspace)

    writer = create_writer_subagent(
        checkpointer=test_checkpointer,
        workspace_dir=test_workspace
    )
    return writer


@pytest.fixture(scope="function")
async def reviewer_agent(test_checkpointer, test_workspace):
    """
    Create reviewer subagent for testing.

    Returns configured reviewer agent with:
    - In-memory checkpointer
    - Isolated test workspace
    - All 4 tools available

    Scope: function (new agent per test)
    """
    from subagents import create_reviewer_subagent
    from module_2_2_simple import set_workspace_dir

    set_workspace_dir(test_workspace)

    reviewer = create_reviewer_subagent(
        checkpointer=test_checkpointer,
        workspace_dir=test_workspace
    )
    return reviewer


@pytest.fixture(scope="function")
async def all_subagents(
    researcher_agent,
    data_scientist_agent,
    expert_analyst_agent,
    writer_agent,
    reviewer_agent
):
    """
    Provide all 5 subagents for multi-agent tests.

    Returns dict with all configured subagents:
    {
        "researcher": researcher_agent,
        "data_scientist": data_scientist_agent,
        "expert_analyst": expert_analyst_agent,
        "writer": writer_agent,
        "reviewer": reviewer_agent
    }

    Scope: function (new agents per test)
    """
    return {
        "researcher": researcher_agent,
        "data_scientist": data_scientist_agent,
        "expert_analyst": expert_analyst_agent,
        "writer": writer_agent,
        "reviewer": reviewer_agent
    }


@pytest.fixture(scope="function")
def sample_research_document(test_workspace):
    """
    Create sample research document with citations for testing.

    Returns path to document with:
    - Valid citation format [1][2][3]
    - Sources section
    - Markdown formatting

    Used for: reviewer testing, validation testing
    """
    doc_path = Path(test_workspace) / "sample_research.md"
    content = """# Renewable Energy Trends 2024

## Executive Summary

Solar energy adoption increased 23% globally in 2024 [1]. This represents
significant growth compared to the 18% increase in 2023 [2].

## Key Findings

Wind power installations grew by 18% across major markets [3]. The combined
renewable energy capacity now exceeds 3,000 GW worldwide [1].

### Regional Analysis

Europe led adoption with 35% growth in solar installations [2]. Asia-Pacific
followed with 28% growth, primarily driven by China and India [3].

## Sources

[1] International Energy Agency (IEA). "Renewable Energy Market Update 2024."
    Published May 2024. https://www.iea.org/reports/renewable-energy-market-update-2024

[2] International Renewable Energy Agency (IRENA). "Renewable Capacity Statistics 2024."
    Published March 2024. https://www.irena.org/publications/2024/Mar/Renewable-Capacity-Statistics-2024

[3] Global Wind Energy Council (GWEC). "Global Wind Report 2024."
    Published April 2024. https://gwec.net/global-wind-report-2024
"""
    doc_path.write_text(content)
    # Return /workspace/ path for custom read_file_tool
    return "/workspace/sample_research.md"


@pytest.fixture(scope="function")
def sample_invalid_document_no_citations(test_workspace):
    """
    Create sample document WITHOUT citations for validation testing.

    Returns path to invalid document (missing citations).

    Used for: citation validation failure tests
    """
    doc_path = Path(test_workspace) / "invalid_no_citations.md"
    content = """# Renewable Energy Trends 2024

Solar energy adoption increased 23% globally in 2024. This represents
significant growth.

Wind power installations also grew substantially across major markets.
"""
    doc_path.write_text(content)
    return str(doc_path)


@pytest.fixture(scope="function")
def sample_invalid_document_no_sources(test_workspace):
    """
    Create sample document with citations but NO Sources section.

    Returns path to invalid document (missing Sources section).

    Used for: citation validation failure tests
    """
    doc_path = Path(test_workspace) / "invalid_no_sources.md"
    content = """# Renewable Energy Trends 2024

Solar energy adoption increased 23% globally in 2024 [1]. This represents
significant growth [2].

Wind power installations grew by 18% across major markets [3].
"""
    doc_path.write_text(content)
    return str(doc_path)


@pytest.fixture(scope="function")
def mock_dataset():
    """
    Provide sample dataset for data scientist testing.

    Returns list of values for statistical analysis.
    """
    return [23, 18, 31, 27, 22, 29, 25, 20, 28, 24]


# Test markers for categorizing tests
def pytest_configure(config):
    """
    Register custom markers for test categorization.
    """
    config.addinivalue_line("markers", "individual: Individual subagent tests")
    config.addinivalue_line("markers", "validation: Citation validation tests")
    config.addinivalue_line("markers", "parallel: Parallel execution tests")
    config.addinivalue_line("markers", "pipeline: Sequential pipeline tests")
    config.addinivalue_line("markers", "error: Error handling tests")
    config.addinivalue_line("markers", "websocket: WebSocket event tests")
    config.addinivalue_line("markers", "isolation: Thread isolation tests")
    config.addinivalue_line("markers", "tools: Tool access tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow-running tests (>30s)")


# Helper functions for tests

def assert_file_exists(file_path: str, message: str = None):
    """Helper to assert file exists with custom message."""
    path = Path(file_path)
    assert path.exists(), message or f"Expected file {file_path} to exist"


def assert_file_contains(file_path: str, text: str, case_sensitive: bool = False):
    """Helper to assert file contains specific text."""
    path = Path(file_path)
    content = path.read_text()

    if not case_sensitive:
        content = content.lower()
        text = text.lower()

    assert text in content, f"Expected '{text}' in {file_path}"


def assert_citations_present(file_path: str):
    """Helper to assert citations [1][2][3] format present."""
    import re
    path = Path(file_path)
    content = path.read_text()

    citations = re.findall(r'\[(\d+)\]', content)
    assert len(citations) > 0, f"No citations found in {file_path}"


def assert_sources_section(file_path: str):
    """Helper to assert Sources section present."""
    import re
    path = Path(file_path)
    content = path.read_text()

    has_sources = bool(re.search(r'#+\s*Sources', content, re.IGNORECASE))
    assert has_sources, f"No Sources section found in {file_path}"
