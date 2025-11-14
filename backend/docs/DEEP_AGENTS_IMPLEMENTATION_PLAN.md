# ATLAS Deep Agents Implementation Plan

**Version**: 1.0
**Date**: 2025-10-05
**Status**: Ready for Implementation

## Executive Summary

Complete migration from Letta to LangChain Deep Agents using Groq's `openai/gpt-oss-120b` model. All agents and tools are **async by default** for optimal parallel execution performance.

## Key Design Decisions

### 1. Async by Default
- **All tools are async** - No separate sync versions
- **All agents are async** - Use `async_create_deep_agent` exclusively
- **Tool naming** - Regular names (e.g., `internet_search`, not `async_internet_search`)
- **Parallel execution** - Multiple tools can execute concurrently

### 2. Absolute Imports Only
```python
# ✅ CORRECT
from backend.src.agents.model_config import get_groq_model

# ❌ WRONG
from ..agents.model_config import get_groq_model
```

### 3. Deep Agents Built-in Tools
The `deepagents` library provides these tools automatically:
- `write_todos` - Planning and task tracking
- `write_file` - Write to virtual filesystem
- `read_file` - Read from virtual filesystem
- `ls` - List virtual filesystem contents
- `edit_file` - Edit virtual filesystem files

**No custom implementation needed!**

### 4. Virtual Filesystem
- All file operations use LangGraph state (not actual disk)
- No conflicts between concurrent agents
- Files accessible via `result["files"]` after execution

### 5. System Prompts from YAML
All agent prompts loaded from `/Users/nicholaspate/Documents/01_Active/ATLAS/backend/src/prompts/`:
- `global_supervisor.yaml` ✅ (exists)
- `research_agent.yaml` (to be created)
- `analysis_agent.yaml` (to be created)
- `writing_agent.yaml` (to be created)

### 6. Model Configuration
- **Model**: Groq `openai/gpt-oss-120b`
- **Max Tokens**: 32,000 for all agents
- **Temperature**: Varies by agent type
  - Supervisor: 0.7 (balanced)
  - Research: 0.5 (factual)
  - Analysis: 0.3 (precise)
  - Writing: 0.8 (creative)

---

## Phase 1: Environment Setup (0.5 days)

### 1.1 Install Dependencies

```bash
source .venv/bin/activate

# Core dependencies
uv pip install deepagents
uv pip install langchain-groq
uv pip install tavily-python
uv pip install e2b-code-interpreter
uv pip install pyyaml
```

### 1.2 Environment Variables

Add to `.env`:
```bash
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
E2B_API_KEY=your_e2b_api_key
```

### 1.3 Create Agent Prompt Files

**File**: `backend/src/prompts/research_agent.yaml`
```yaml
agent_type: "Research Agent"
version: "1.0"
last_updated: "2025-10-05"

persona: |
  You are a research specialist for ATLAS. Your role is to conduct thorough web research,
  gather information from reliable sources, and return structured research findings with citations.

  CRITICAL RULES:
  - Always cite sources with URLs
  - Verify information from multiple sources when possible
  - Save research findings to files using write_file
  - Use internet_search tool for web queries
  - Organize findings clearly with headings and bullet points

  Your research should be:
  - Comprehensive and thorough
  - Well-cited and verifiable
  - Organized and easy to read
  - Focused on answering the specific question asked

capabilities:
  - "Web search and information gathering"
  - "Source verification and citation"
  - "Structured research documentation"
```

**File**: `backend/src/prompts/analysis_agent.yaml`
```yaml
agent_type: "Analysis Agent"
version: "1.0"
last_updated: "2025-10-05"

persona: |
  You are an analysis specialist for ATLAS. Your role is to analyze data using Python code execution,
  generate visualizations and statistical insights, and return structured analytical findings.

  CRITICAL RULES:
  - Use execute_python_code for all data analysis
  - Create visualizations when helpful (matplotlib, seaborn)
  - Save analysis results to files using write_file
  - Include code, results, and interpretations
  - Explain your analytical approach clearly

  Your analysis should be:
  - Data-driven and objective
  - Well-documented with code
  - Visually supported when appropriate
  - Clearly interpreted and explained

capabilities:
  - "Python code execution in sandbox"
  - "Statistical analysis and data processing"
  - "Visualization creation"
  - "Results interpretation"
```

**File**: `backend/src/prompts/writing_agent.yaml`
```yaml
agent_type: "Writing Agent"
version: "1.0"
last_updated: "2025-10-05"

persona: |
  You are a writing specialist for ATLAS. Your role is to create well-structured, professional documents
  that synthesize research and analysis into clear, engaging narratives.

  CRITICAL RULES:
  - Load research and analysis files using read_file
  - Create polished documents in markdown format
  - Use clear structure with headings and sections
  - Save final documents using write_file
  - Cite sources from research findings

  Your writing should be:
  - Clear and professional
  - Well-structured and organized
  - Engaging and readable
  - Properly cited and referenced

capabilities:
  - "Professional content creation"
  - "Research and analysis synthesis"
  - "Document structuring and formatting"
  - "Citation and referencing"
```

---

## Phase 2: Core Implementation (1 day)

### 2.1 Model Configuration

**File**: `backend/src/agents/model_config.py`

```python
"""
Centralized model configuration for all ATLAS agents.
Uses Groq's openai/gpt-oss-120b model with 32k max tokens.

All imports are ABSOLUTE.
"""

import os
from langchain_groq import ChatGroq


def get_groq_model(temperature: float = 0.7) -> ChatGroq:
    """
    Get configured Groq model instance.

    Args:
        temperature: Model temperature (0.0-2.0)

    Returns:
        ChatGroq instance configured with:
        - Model: openai/gpt-oss-120b
        - Max tokens: 32,000
        - Streaming: Enabled
    """
    return ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=temperature,
        max_tokens=32000,
        streaming=True,
        groq_api_key=os.getenv("GROQ_API_KEY")
    )
```

### 2.2 Prompt Loader Utility

**File**: `backend/src/utils/prompt_loader.py`

```python
"""
Utility to load agent prompts from YAML files.

All imports are ABSOLUTE.
"""

import yaml
from pathlib import Path
from typing import Dict, Any


PROMPTS_DIR = Path("/Users/nicholaspate/Documents/01_Active/ATLAS/backend/src/prompts")


def load_agent_prompt(agent_name: str) -> str:
    """
    Load agent system prompt from YAML file.

    Args:
        agent_name: Name of agent (e.g., "global_supervisor", "research_agent")

    Returns:
        System prompt string from persona field

    Raises:
        FileNotFoundError: If YAML file doesn't exist
    """
    yaml_file = PROMPTS_DIR / f"{agent_name}.yaml"

    if not yaml_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {yaml_file}")

    with open(yaml_file, 'r') as f:
        config = yaml.safe_load(f)

    return config.get('persona', '')


def load_agent_config(agent_name: str) -> Dict[str, Any]:
    """
    Load full agent configuration from YAML file.

    Returns complete configuration including:
    - agent_type
    - version
    - persona
    - capabilities
    - Any other fields defined in YAML
    """
    yaml_file = PROMPTS_DIR / f"{agent_name}.yaml"

    if not yaml_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {yaml_file}")

    with open(yaml_file, 'r') as f:
        return yaml.safe_load(f)
```

### 2.3 External Tools (Async by Default)

**File**: `backend/src/tools/external_tools.py`

```python
"""
External tools for ATLAS agents.
All tools are ASYNC by default for parallel execution.

All imports are ABSOLUTE.
"""

import os
import asyncio
from typing import Literal, Dict, Any
from tavily import AsyncTavilyClient
from e2b_code_interpreter import CodeInterpreter


# Initialize async Tavily client
tavily_client = AsyncTavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))


async def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
) -> Dict[str, Any]:
    """
    Search the web for information using Tavily.

    ASYNC by default - supports parallel searches.

    Args:
        query: Search query
        max_results: Number of results to return (default: 5)
        topic: Search topic category
        include_raw_content: Whether to include full page content

    Returns:
        Search results with URLs, titles, and snippets
    """
    try:
        results = await tavily_client.search(
            query,
            max_results=max_results,
            include_raw_content=include_raw_content,
            topic=topic,
        )
        return results
    except Exception as e:
        return {
            "error": f"Search failed: {str(e)}",
            "query": query
        }


async def execute_python_code(code: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute Python code safely in E2B sandbox.

    ASYNC by default - supports parallel code execution.

    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds

    Returns:
        Execution results including:
        - status: "success" or "error"
        - stdout: Standard output
        - stderr: Standard error
        - result: Return value
        - error: Error message if failed
    """
    if not os.environ.get("E2B_API_KEY"):
        return {
            "status": "error",
            "error": "E2B_API_KEY not configured"
        }

    try:
        # Run in thread pool to avoid blocking
        result = await asyncio.to_thread(_execute_code_sync, code, timeout)
        return result
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def _execute_code_sync(code: str, timeout: int) -> Dict[str, Any]:
    """
    Synchronous helper for code execution.
    Called from async context via asyncio.to_thread.
    """
    try:
        with CodeInterpreter(api_key=os.environ["E2B_API_KEY"]) as sandbox:
            execution = sandbox.notebook.exec_cell(code, timeout=timeout)

            return {
                "status": "success",
                "stdout": execution.logs.stdout if execution.logs else "",
                "stderr": execution.logs.stderr if execution.logs else "",
                "result": str(execution.results) if execution.results else None,
                "error": execution.error if execution.error else None
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
```

### 2.4 Supervisor Agent

**File**: `backend/src/agents/supervisor_agent.py`

```python
"""
ATLAS Supervisor Agent using Deep Agents library.

ASYNC by default for parallel execution.
All imports are ABSOLUTE.
"""

import logging
from typing import Dict, Any
from deepagents import async_create_deep_agent

from backend.src.agents.model_config import get_groq_model
from backend.src.utils.prompt_loader import load_agent_prompt
from backend.src.tools.external_tools import internet_search, execute_python_code

logger = logging.getLogger(__name__)


async def create_supervisor_agent():
    """
    Create ATLAS supervisor agent using Deep Agents.

    ASYNC by default - supports parallel tool execution.

    Features:
    - Built-in planning: write_todos
    - Built-in filesystem: write_file, read_file, ls, edit_file
    - External tools: internet_search, execute_python_code
    - Sub-agents: research, analysis, writing

    Returns:
        Async deep agent graph
    """
    # Load supervisor prompt from YAML
    supervisor_prompt = load_agent_prompt("global_supervisor")

    # Get Groq model (temp=0.7 for balanced reasoning)
    model = get_groq_model(temperature=0.7)

    # Define sub-agents for delegation
    subagents = [
        {
            "name": "research-agent",
            "description": "Specialized agent for web research and information gathering. Use for finding information, gathering data, and researching topics.",
            "prompt": load_agent_prompt("research_agent"),
            "tools": ["internet_search"],  # Only web search for research
            "model": get_groq_model(temperature=0.5),  # Lower temp for factual
        },
        {
            "name": "analysis-agent",
            "description": "Specialized agent for data analysis and code execution. Use for processing data, running calculations, and generating insights.",
            "prompt": load_agent_prompt("analysis_agent"),
            "tools": ["execute_python_code"],  # Only code execution for analysis
            "model": get_groq_model(temperature=0.3),  # Lowest temp for precision
        },
        {
            "name": "writing-agent",
            "description": "Specialized agent for content creation and document writing. Use for creating final reports, documents, and synthesizing findings.",
            "prompt": load_agent_prompt("writing_agent"),
            "tools": [],  # Only built-in file tools for writing
            "model": get_groq_model(temperature=0.8),  # Higher temp for creativity
        },
    ]

    # Create supervisor agent with async support
    agent = async_create_deep_agent(
        tools=[internet_search, execute_python_code],
        instructions=supervisor_prompt,
        model=model,
        subagents=subagents,
    )

    logger.info("✅ Supervisor agent created successfully")
    logger.info(f"📦 Built-in tools: write_todos, write_file, read_file, ls, edit_file")
    logger.info(f"🔧 External tools: internet_search, execute_python_code")
    logger.info(f"🤖 Sub-agents: research-agent, analysis-agent, writing-agent")
    logger.info(f"⚡ Async: Enabled for parallel execution")

    return agent
```

---

## Phase 3: API Integration (1 day)

### 3.1 API Endpoints

**File**: `backend/src/api/agent_endpoints.py`

```python
"""
API endpoints for ATLAS supervisor agent.

All agents and tools are ASYNC by default.
All imports are ABSOLUTE.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

from backend.src.agents.supervisor_agent import create_supervisor_agent
from langgraph.checkpoint.memory import InMemorySaver

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["agent"])


# Global checkpointer for session persistence
checkpointer = InMemorySaver()


class TaskRequest(BaseModel):
    """Task creation request."""
    message: str
    session_id: Optional[str] = None


class TaskResponse(BaseModel):
    """Task execution response."""
    task_id: str
    status: str
    messages: List[Dict[str, Any]]
    files: Dict[str, str]  # Virtual filesystem contents


@router.post("/tasks", response_model=TaskResponse)
async def create_task(request: TaskRequest):
    """
    Create and execute a task with ATLAS supervisor.

    Uses Deep Agents with:
    - Async execution for parallel tool calls
    - Built-in planning (write_todos)
    - Virtual filesystem (write_file, read_file, ls, edit_file)
    - Sub-agent delegation (research, analysis, writing)

    Args:
        request: Task request with message and optional session_id

    Returns:
        Task response with results and virtual files
    """
    try:
        # Create supervisor agent (async)
        agent = await create_supervisor_agent()

        # Attach checkpointer for session persistence
        agent.checkpointer = checkpointer

        # Create config with session ID
        session_id = request.session_id or "default"
        config = {
            "configurable": {
                "thread_id": session_id
            }
        }

        logger.info(f"🚀 Starting task for session: {session_id}")

        # Invoke agent (async)
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": request.message}]},
            config=config
        )

        # Extract results
        messages = result.get("messages", [])
        files = result.get("files", {})

        logger.info(f"✅ Task completed: {len(messages)} messages, {len(files)} files")

        return TaskResponse(
            task_id=session_id,
            status="completed",
            messages=[
                {
                    "role": msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "unknown"),
                    "content": msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
                }
                for msg in messages
            ],
            files=files
        )

    except Exception as e:
        logger.error(f"❌ Task execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/files")
async def get_task_files(task_id: str):
    """
    Get virtual filesystem contents for a task.

    Returns all files created by the agent during task execution.
    Files are stored in the virtual filesystem (not on disk).

    Args:
        task_id: Session/task identifier

    Returns:
        Dictionary of filename -> content
    """
    config = {"configurable": {"thread_id": task_id}}

    try:
        state = checkpointer.get(config)
        if state is None:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        files = state.get("files", {})

        return {
            "task_id": task_id,
            "files": files,
            "file_count": len(files)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/stream")
async def stream_task(task_id: str, message: str):
    """
    Stream task execution for real-time updates.

    Uses async streaming to return results as they're generated.
    Supports:
    - Token-by-token streaming
    - Tool call notifications
    - File creation events

    Args:
        task_id: Session identifier
        message: User message

    Yields:
        Stream of execution events
    """
    from fastapi.responses import StreamingResponse
    import json

    async def generate():
        try:
            agent = await create_supervisor_agent()
            agent.checkpointer = checkpointer

            config = {"configurable": {"thread_id": task_id}}

            async for chunk in agent.astream(
                {"messages": [{"role": "user", "content": message}]},
                config=config,
                stream_mode="values"
            ):
                # Send chunk as JSON
                yield json.dumps({
                    "type": "chunk",
                    "data": str(chunk)
                }) + "\n"

        except Exception as e:
            yield json.dumps({
                "type": "error",
                "error": str(e)
            }) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
```

---

## Phase 4: Testing (1 day)

### 4.1 Integration Tests

**File**: `backend/tests/test_deep_agents.py`

```python
"""
Integration tests for Deep Agents implementation.

All tests are ASYNC.
All imports are ABSOLUTE.
"""

import pytest
import asyncio
from backend.src.agents.supervisor_agent import create_supervisor_agent


@pytest.mark.asyncio
async def test_supervisor_creation():
    """Test supervisor agent creation."""
    agent = await create_supervisor_agent()
    assert agent is not None
    assert agent.checkpointer is None  # Not attached by default


@pytest.mark.asyncio
async def test_basic_task_execution():
    """Test basic task with virtual filesystem."""
    agent = await create_supervisor_agent()

    result = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Write 'Hello ATLAS' to a file named greeting.txt"
        }]
    })

    # Check virtual filesystem
    assert "files" in result
    assert "greeting.txt" in result["files"]
    assert "Hello ATLAS" in result["files"]["greeting.txt"]


@pytest.mark.asyncio
async def test_parallel_tool_execution():
    """Test parallel execution of multiple tools."""
    agent = await create_supervisor_agent()

    # Task requiring multiple web searches (should execute in parallel)
    result = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Research both Python and JavaScript, then compare them"
        }]
    })

    assert "messages" in result
    assert len(result["messages"]) > 1


@pytest.mark.asyncio
async def test_research_subagent():
    """Test research sub-agent delegation."""
    agent = await create_supervisor_agent()

    result = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Research the top 3 benefits of remote work"
        }]
    })

    # Verify completion and file creation
    assert "files" in result
    assert len(result["files"]) > 0
    assert result["messages"][-1].type == "ai"


@pytest.mark.asyncio
async def test_analysis_subagent():
    """Test analysis sub-agent with code execution."""
    agent = await create_supervisor_agent()

    result = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Calculate the fibonacci sequence up to 10 numbers using Python"
        }]
    })

    assert "messages" in result
    # Should have executed code
    assert any("fibonacci" in str(msg).lower() for msg in result["messages"])


@pytest.mark.asyncio
async def test_writing_subagent():
    """Test writing sub-agent document creation."""
    agent = await create_supervisor_agent()

    # First create some research, then write a report
    result = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Research AI trends and write a brief report"
        }]
    })

    # Should have created files
    assert "files" in result
    assert len(result["files"]) > 0


@pytest.mark.asyncio
async def test_session_persistence():
    """Test session state persistence with checkpointer."""
    from langgraph.checkpoint.memory import InMemorySaver

    agent = await create_supervisor_agent()
    checkpointer = InMemorySaver()
    agent.checkpointer = checkpointer

    config = {"configurable": {"thread_id": "test-session"}}

    # First message
    result1 = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "Write 'test' to file.txt"}]},
        config=config
    )

    # Second message in same session
    result2 = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "Read file.txt"}]},
        config=config
    )

    # Should maintain context
    assert "messages" in result2
    assert len(result2["messages"]) > len(result1["messages"])
```

---

## Success Criteria

✅ **Async by Default**
- All tools async with normal names (not `async_*`)
- Single agent implementation using `async_create_deep_agent`
- No separate sync/async versions

✅ **Absolute Imports**
- All imports use `backend.src.*` format
- No relative imports anywhere

✅ **Deep Agents Built-in Tools**
- Using `write_todos` for planning
- Using `write_file`, `read_file`, `ls`, `edit_file` for files
- No custom reimplementation

✅ **Configuration**
- All agents use 32k max tokens
- System prompts from YAML files
- Groq model throughout

✅ **Parallel Execution**
- Multiple tools can run concurrently
- Sub-agents support async delegation
- Proper async/await throughout

✅ **Testing**
- All tests are async
- Session persistence verified
- Sub-agent delegation confirmed

---

## Timeline

**Total: 3-3.5 days**

| Phase | Duration | Tasks |
|-------|----------|-------|
| Phase 1 | 0.5 days | Setup, dependencies, YAML prompts |
| Phase 2 | 1 day | Model config, tools, supervisor agent |
| Phase 3 | 1 day | API endpoints, streaming |
| Phase 4 | 1 day | Testing, validation |

---

## Architecture Benefits

### 1. Deep Agents Library
- ✅ No custom planning tools needed
- ✅ Virtual filesystem prevents conflicts
- ✅ Sub-agent context quarantine
- ✅ Proven Claude Code patterns

### 2. Async by Default
- ✅ Parallel tool execution
- ✅ Better performance
- ✅ Simpler codebase (no dual versions)
- ✅ Scalable architecture

### 3. Groq Model
- ✅ Ultra-fast inference (10x faster)
- ✅ 32k context window
- ✅ Cost-effective
- ✅ Consistent across agents

### 4. YAML Configuration
- ✅ Easy prompt updates
- ✅ Version controlled
- ✅ Clear separation of concerns
- ✅ Reusable across agents

---

## Next Steps

1. **Review Plan**: Confirm architecture and approach
2. **Phase 1**: Install dependencies and create YAML prompts
3. **Phase 2**: Implement core agents and tools
4. **Phase 3**: Build API endpoints
5. **Phase 4**: Test and validate
6. **Production**: Deploy and monitor

---

## Questions & Clarifications

### Q: Why async by default?
**A**: Enables parallel tool execution for better performance. Multiple web searches or code executions can run concurrently instead of sequentially.

### Q: Why no separate sync versions?
**A**: Simpler codebase, easier maintenance, and async is the modern Python standard for I/O operations.

### Q: Can we still use sync tools if needed?
**A**: Yes, wrap them with `asyncio.to_thread()` like we do for E2B code execution.

### Q: What about backwards compatibility?
**A**: This is a complete migration from Letta, not an incremental update. Old code will be archived.

---

**Document maintained by**: ATLAS Development Team
**Last updated**: 2025-10-05
**Next review**: After Phase 1 completion
