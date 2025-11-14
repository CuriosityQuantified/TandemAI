# Anthropic Claude Models Integration Guide for ATLAS

**Document Version**: 1.0
**Last Updated**: 2025-01-12
**Research Date**: 2025-01-12

## Executive Summary

This guide provides comprehensive information for integrating Anthropic Claude Sonnet models (3.5, 4, and 4.5) into the ATLAS multi-agent system using LangChain.

### Quick Reference

| Model | Model ID | Context | Max Output | Price (Input) | Price (Output) | SWE-bench Score |
|-------|----------|---------|------------|---------------|----------------|-----------------|
| Claude 3.5 Sonnet | `claude-3-5-sonnet-20241022` | 200K | 8,192 | $3/MTok | $15/MTok | 49% |
| Claude Sonnet 4 | `claude-sonnet-4-20250514` | 200K (1M beta) | 64,000 | $3/MTok | $15/MTok | 72.7% |
| Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` | 200K (1M beta) | 64,000 | $3/MTok | $15/MTok | **77.2%** |

**Key Decision**: All Sonnet models have identical pricing. Use **Sonnet 4.5** for most tasks (best performance), and **Sonnet 4** for deep analysis tasks requiring extended thinking mode.

---

## Model Specifications

### Claude 3.5 Sonnet (October 2024)

**Model ID**: `claude-3-5-sonnet-20241022`

**Capabilities**:
- Context Window: 200,000 tokens
- Max Output Tokens: 8,192
- Knowledge Cutoff: April 2024
- Performance: 49% on SWE-bench Verified (upgraded from 33.4%)
- Enhanced agentic coding and tool use capabilities

**Pricing**:
- Input: $3 per million tokens
- Output: $15 per million tokens

**Best For**:
- General-purpose tasks requiring solid performance
- Cost-conscious deployments with good quality needs
- Legacy compatibility (if upgrading from earlier 3.5 versions)

**Source**: [Anthropic Claude Models Overview](https://docs.claude.com/en/docs/about-claude/models/overview)

---

### Claude Sonnet 4 (May 2025)

**Model ID**: `claude-sonnet-4-20250514`

**Capabilities**:
- Context Window: 200,000 tokens (1M with beta header `context-1m-2025-08-07`)
- Max Output Tokens: 64,000
- Knowledge Cutoff: Mid-2024
- Performance: 72.7% on SWE-bench Verified
- **Hybrid Model**: Offers both near-instant responses and extended thinking mode
- Extended thinking: Can reason deeply for complex problems

**Pricing**:
- Input: $3 per million tokens (standard context)
- Output: $15 per million tokens (standard context)
- Input: $6 per million tokens (>200K context with 1M beta)
- Output: $22.50 per million tokens (>200K context with 1M beta)

**Best For**:
- Deep analysis requiring extended reasoning
- Complex problem-solving with thinking mode
- Tasks requiring very long output (up to 64K tokens)

**Extended Thinking Mode**:
- Not compatible with temperature modifications
- Use for: complex coding, mathematical reasoning, strategic planning
- Average 10-20 seconds for complex reasoning tasks

**Source**: [Anthropic Claude 4 Announcement](https://www.anthropic.com/news/claude-4)

---

### Claude Sonnet 4.5 (September 2025) ⭐ RECOMMENDED

**Model ID**: `claude-sonnet-4-5-20250929`

**Capabilities**:
- Context Window: 200,000 tokens (1M with beta header)
- Max Output Tokens: 64,000
- Knowledge Cutoff: Mid-2024
- Performance: **77.2%** on SWE-bench Verified (best coding model)
- Performance: **61.4%** on OSWorld (computer use benchmark)
- **Can maintain focus for 30+ hours on complex tasks**
- Best-in-class for coding, complex agents, and computer use

**Pricing**:
- Input: $3 per million tokens
- Output: $15 per million tokens
- Same pricing as Sonnet 4 and 3.5 at standard context

**Best For**:
- Coding and software development tasks
- Complex multi-agent orchestration
- Long-running autonomous tasks (30+ hours focus)
- Code review and evaluation
- Any task requiring best-in-class performance

**Why Choose 4.5 Over 4**:
- Same price as Sonnet 4
- Better performance (77.2% vs 72.7% on SWE-bench)
- Maintains focus longer (30+ hours)
- Better at computer use tasks

**Source**: [Anthropic Claude Sonnet 4.5 Announcement](https://www.anthropic.com/news/claude-sonnet-4-5)

---

## LangChain Integration

### Installation

```bash
# Install LangChain Anthropic integration
pip install langchain-anthropic

# Or using uv (recommended for ATLAS)
uv pip install langchain-anthropic
```

### Basic Configuration

```python
import os
from langchain_anthropic import ChatAnthropic

# Basic setup with Claude Sonnet 4.5
model = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0.7,
    max_tokens=30000,
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Invoke the model
response = await model.ainvoke("Explain multi-agent systems")
print(response.content)
```

### Required Parameters

- **model** (str): Model ID
  - Claude 3.5 Sonnet: `"claude-3-5-sonnet-20241022"`
  - Claude Sonnet 4: `"claude-sonnet-4-20250514"`
  - Claude Sonnet 4.5: `"claude-sonnet-4-5-20250929"`

### Optional Parameters

- **temperature** (float, 0.0-1.0): Randomness in responses
  - Default: Varies by use case
  - Analytical tasks: 0.0-0.3
  - Balanced: 0.5-0.7
  - Creative: 0.8-1.0

- **max_tokens** (int): Maximum output length
  - Default: 1024
  - Recommended for ATLAS: 30,000 (extended responses)
  - Maximum: 8,192 (Sonnet 3.5), 64,000 (Sonnet 4/4.5)

- **anthropic_api_key** (str): API key
  - Reads from `ANTHROPIC_API_KEY` environment variable if not provided

- **timeout** (int): Request timeout in seconds
  - Default: None (no timeout)

- **max_retries** (int): Number of retry attempts
  - Default: 2

- **streaming** (bool): Enable streaming responses
  - Default: False

**Source**: [LangChain ChatAnthropic API Reference](https://python.langchain.com/api_reference/anthropic/chat_models/langchain_anthropic.chat_models.ChatAnthropic.html)

---

## Configuration Best Practices

### Max Tokens Recommendations

```python
# Conservative (general use)
max_tokens=4000

# Extended responses (research reports, documentation)
max_tokens=30000  # RECOMMENDED FOR ATLAS

# Maximum output (long-form content)
max_tokens=64000  # Only for Sonnet 4/4.5
```

**AWS Best Practice**: Set max_tokens to 4,000 for optimal performance and cost control.

**ATLAS Recommendation**: Use 30,000 tokens for:
- Research reports with comprehensive findings
- Technical documentation
- Multi-section analysis
- Code generation with explanations

**Source**: [AWS Bedrock Model Parameters](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-text-completion.html)

### Temperature Guidelines

```python
# Analytical tasks (analysis-agent, reviewer-agent)
temperature=0.0  # Deterministic
temperature=0.3  # Precise with slight variation

# Balanced reasoning (supervisor-agent, research-agent)
temperature=0.5  # Factual with some flexibility
temperature=0.7  # Balanced creativity and accuracy

# Creative tasks (writing-agent)
temperature=0.8  # Engaging content
temperature=1.0  # Maximum creativity
```

**Important**: Don't modify both temperature and top_p simultaneously. Extended thinking mode is not compatible with temperature modifications.

**Source**: [PromptHub - Anthropic Best Practices](https://www.prompthub.us/blog/using-anthropic-best-practices-parameters-and-large-context-windows)

### API Key Configuration

**Environment Variable (Recommended)**:
```bash
# In .env file
ANTHROPIC_API_KEY=sk-ant-api03-...

# Or export in shell
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

**Direct Configuration**:
```python
model = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    anthropic_api_key="sk-ant-api03-..."  # Not recommended for production
)
```

**Source**: [LangChain Anthropic Integration](https://python.langchain.com/docs/integrations/chat/anthropic/)

### Error Handling

```python
from langchain_anthropic import ChatAnthropic

# Production-ready configuration
model = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0.7,
    max_tokens=30000,
    timeout=120,  # 2 minutes timeout
    max_retries=3,  # Retry up to 3 times
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Use with error handling
try:
    response = await model.ainvoke("Your prompt here")
except Exception as e:
    logger.error(f"Model invocation failed: {e}")
    # Fallback logic here
```

---

## ATLAS Agent Assignments (Sonnet Models Only)

### Recommended Model per Agent

| Agent | Model | Temperature | Max Tokens | Rationale |
|-------|-------|-------------|------------|-----------|
| **Supervisor** | Sonnet 4.5 | 0.7 | 30,000 | Best orchestration, 30+ hour focus |
| **Research** | Sonnet 4.5 | 0.5 | 30,000 | Best overall performance, factual accuracy |
| **Analysis** | Sonnet 4 | 0.3 | 30,000 | Extended thinking mode for deep analysis |
| **Writing** | Sonnet 4.5 | 0.8 | 30,000 | Best quality, engaging content |
| **Reviewer** | Sonnet 4.5 | 0.3 | 30,000 | 77.2% SWE-bench, best code evaluation |

### Configuration Examples

#### Supervisor Agent (Sonnet 4.5)
```python
supervisor_model = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0.7,  # Balanced reasoning
    max_tokens=30000,
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
)
```

#### Research Agent (Sonnet 4.5)
```python
research_model = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0.5,  # Factual, focused
    max_tokens=30000,
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
)
```

#### Analysis Agent (Sonnet 4 with Extended Thinking)
```python
analysis_model = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.3,  # Precise (Note: incompatible with extended thinking)
    max_tokens=30000,
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
)

# For extended thinking mode, don't set temperature
analysis_model_thinking = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    max_tokens=30000,
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
)
```

#### Writing Agent (Sonnet 4.5)
```python
writing_model = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0.8,  # Creative, engaging
    max_tokens=30000,
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
)
```

#### Reviewer Agent (Sonnet 4.5)
```python
reviewer_model = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0.3,  # Precise validation
    max_tokens=30000,
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
)
```

---

## Migration Guide: Groq to Anthropic

### Step 1: Update model_config.py

```python
"""
Centralized model configuration for all ATLAS agents.

PRIMARY MODEL: Claude Sonnet models (3.5, 4, 4.5)
FALLBACK MODEL: Groq qwen/qwen3-32b (faster but stricter validation)
"""

import os
from langchain_groq import ChatGroq
from langchain_anthropic import ChatAnthropic


def get_claude_sonnet_4_5(temperature: float = 0.7) -> ChatAnthropic:
    """Get Claude Sonnet 4.5 (RECOMMENDED - best performance)"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in .env file")

    return ChatAnthropic(
        model="claude-sonnet-4-5-20250929",
        temperature=temperature,
        max_tokens=30000,
        anthropic_api_key=api_key,
    )


def get_claude_sonnet_4(temperature: float = 0.7) -> ChatAnthropic:
    """Get Claude Sonnet 4 (for extended thinking mode)"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in .env file")

    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=temperature,
        max_tokens=30000,
        anthropic_api_key=api_key,
    )


def get_claude_sonnet_3_5(temperature: float = 0.7) -> ChatAnthropic:
    """Get Claude 3.5 Sonnet (legacy compatibility)"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in .env file")

    return ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        temperature=temperature,
        max_tokens=8192,  # Max for 3.5
        anthropic_api_key=api_key,
    )


def get_groq_model(temperature: float = 0.7) -> ChatGroq:
    """Get Groq model (FALLBACK - stricter validation)"""
    # Keep existing Groq implementation as fallback
    ...
```

### Step 2: Update supervisor_agent.py

```python
# OLD (Groq)
from backend.src.agents.model_config import get_groq_model

subagents = [
    {
        "name": "research-agent",
        "model": get_groq_model(temperature=0.5),
        ...
    }
]

# NEW (Claude)
from backend.src.agents.model_config import get_claude_sonnet_4_5, get_claude_sonnet_4

subagents = [
    {
        "name": "research-agent",
        "model": get_claude_sonnet_4_5(temperature=0.5),
        ...
    },
    {
        "name": "analysis-agent",
        "model": get_claude_sonnet_4(temperature=0.3),  # Extended thinking
        ...
    },
    {
        "name": "writing-agent",
        "model": get_claude_sonnet_4_5(temperature=0.8),
        ...
    },
    {
        "name": "reviewer-agent",
        "model": get_claude_sonnet_4_5(temperature=0.3),
        ...
    }
]
```

### Step 3: Update .env File

```bash
# Add Anthropic API key
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# Keep Groq as fallback
GROQ_API_KEY=your-groq-key-here
```

### Step 4: Test with Simple Workflow

```python
# test_claude_migration.py
import asyncio
from backend.src.agents.supervisor_agent import create_supervisor_agent

async def test_claude():
    supervisor = await create_supervisor_agent()

    result = await supervisor.ainvoke({
        "messages": [{"role": "user", "content": "Say hello"}]
    })

    print("✅ Claude integration working!")
    print(f"Response: {result['messages'][-1].content[:100]}")

if __name__ == "__main__":
    asyncio.run(test_claude())
```

### Step 5: Run Full Integration Tests

```bash
# Run Phase 2 integration tests
python backend/test_phase2_integration.py

# Expected: All tests pass with Claude (more lenient ToolMessage handling)
```

---

## Code Examples

### Streaming Responses

```python
from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0.7,
    max_tokens=30000,
    streaming=True,
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Stream responses
async for chunk in model.astream("Write a short story"):
    print(chunk.content, end="", flush=True)
```

**Source**: [LangChain Anthropic Integration](https://python.langchain.com/docs/integrations/chat/anthropic/)

### Tool/Function Calling

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

@tool
def calculate_sum(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

model = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0.7,
    max_tokens=30000
)

# Bind tools to model
model_with_tools = model.bind_tools([calculate_sum])

# Invoke with tool calling
response = await model_with_tools.ainvoke("What is 42 + 58?")
print(response.tool_calls)
```

**Source**: [LangChain Anthropic Integration](https://python.langchain.com/docs/integrations/chat/anthropic/)

### Parallel Tool Use

```python
from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0.7,
    max_tokens=30000
)

# Enable parallel tool use (default)
model_with_tools = model.bind_tools([tool1, tool2, tool3])

# Disable parallel tool use
model_sequential = model.bind_tools(
    [tool1, tool2, tool3],
    parallel_tool_calls=False
)

# Or use tool_choice parameter
model_controlled = model.bind_tools(
    [tool1, tool2, tool3],
    tool_choice={
        "type": "auto",
        "disable_parallel_tool_use": True
    }
)
```

**Source**: [LangChain Parallel Tool Calling](https://python.langchain.com/docs/how_to/tool_calling_parallel/)

### Async Methods

```python
import asyncio
from langchain_anthropic import ChatAnthropic

async def process_multiple_requests():
    model = ChatAnthropic(
        model="claude-sonnet-4-5-20250929",
        temperature=0.7,
        max_tokens=30000
    )

    # Process multiple requests in parallel
    tasks = [
        model.ainvoke("Question 1"),
        model.ainvoke("Question 2"),
        model.ainvoke("Question 3"),
    ]

    results = await asyncio.gather(*tasks)
    return results

# Run
results = asyncio.run(process_multiple_requests())
```

### Error Handling and Retries

```python
import logging
from langchain_anthropic import ChatAnthropic

logger = logging.getLogger(__name__)

model = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0.7,
    max_tokens=30000,
    timeout=120,  # 2 minute timeout
    max_retries=3,  # Retry up to 3 times
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
)

async def safe_invoke(prompt: str):
    try:
        response = await model.ainvoke(prompt)
        return response.content
    except TimeoutError:
        logger.error("Request timed out after 120 seconds")
        return "Error: Request timed out"
    except Exception as e:
        logger.error(f"Model invocation failed: {e}")
        return f"Error: {str(e)}"

# Use with error handling
result = await safe_invoke("Your prompt here")
```

---

## Performance Benchmarks

### SWE-bench Verified Scores

| Model | Score | Improvement |
|-------|-------|-------------|
| Claude 3.5 Sonnet (Oct 2024) | 49.0% | Baseline |
| Claude Sonnet 4 (May 2025) | 72.7% | +48% |
| **Claude Sonnet 4.5 (Sept 2025)** | **77.2%** | **+58%** |

SWE-bench Verified measures ability to solve real-world GitHub issues from open-source projects.

**Source**: [Anthropic Claude Sonnet 4.5 Announcement](https://www.anthropic.com/news/claude-sonnet-4-5)

### OSWorld Computer Use Score

- **Claude Sonnet 4.5**: 61.4% (best-in-class for computer use tasks)

OSWorld measures ability to interact with computer interfaces and complete complex multi-step tasks.

**Source**: [Anthropic Claude Sonnet 4.5 Announcement](https://www.anthropic.com/news/claude-sonnet-4-5)

### Task Focus Duration

- **Claude Sonnet 4.5**: Can maintain focus for **30+ hours** on complex tasks
- Critical for long-running autonomous agents in ATLAS

**Source**: [Anthropic Claude Sonnet 4.5 Announcement](https://www.anthropic.com/news/claude-sonnet-4-5)

### Cost Analysis (All Sonnet Models)

**Pricing (Standard Context ≤200K)**:
- Input: $3 per million tokens
- Output: $15 per million tokens
- **All three Sonnet models have identical pricing**

**Example Cost Calculation**:
```
Research Task:
- Input: 50K tokens (supervisor + research context) = $0.15
- Output: 30K tokens (research report) = $0.45
- Total: $0.60 per research task

Daily Usage (50 tasks):
- Total: $30/day = $900/month
```

**Extended Context Pricing (>200K tokens, beta feature)**:
- Input: $6 per million tokens (2x standard)
- Output: $22.50 per million tokens (1.5x standard)
- Only applicable to Sonnet 4 and 4.5 when using 1M context beta header

**Source**: [Anthropic Claude Models Pricing](https://docs.claude.com/en/docs/about-claude/models/overview)

---

## Beta Features

### 1M Context Window

**Availability**: Claude Sonnet 4 and 4.5 only

**How to Enable**:
```python
# Standard configuration (200K context)
model = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    max_tokens=30000
)

# Extended 1M context (beta)
# Note: Requires beta header configuration
# See Anthropic documentation for beta access
```

**Use Cases**:
- Processing entire codebases (up to 1M tokens)
- Analyzing large documents or datasets
- Long-context research synthesis

**Pricing Impact**:
- Standard (≤200K): $3 input / $15 output per MTok
- Extended (>200K): $6 input / $22.50 output per MTok

**Source**: [Anthropic Claude 4 Announcement](https://www.anthropic.com/news/claude-4)

### Extended Thinking Mode

**Availability**: Claude Sonnet 4 only

**Description**: Model can spend additional time reasoning before responding, useful for complex problems requiring deep analysis.

**How to Use**:
```python
# Don't set temperature for extended thinking
model = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    max_tokens=30000
    # No temperature parameter
)
```

**Performance**:
- Average thinking time: 10-20 seconds for complex tasks
- Significantly better on mathematical reasoning, complex coding, strategic planning

**Trade-offs**:
- Slower response times
- Higher latency
- Not compatible with temperature modifications

**When to Use**:
- Complex mathematical problems
- Multi-step reasoning tasks
- Strategic planning and decision-making
- Deep code analysis

**Source**: [Anthropic Claude 4 Announcement](https://www.anthropic.com/news/claude-4)

---

## References

1. **Anthropic Claude Models Overview**
   https://docs.claude.com/en/docs/about-claude/models/overview

2. **Anthropic Claude 4 Announcement**
   https://www.anthropic.com/news/claude-4

3. **Anthropic Claude Sonnet 4.5 Announcement**
   https://www.anthropic.com/news/claude-sonnet-4-5

4. **LangChain ChatAnthropic API Reference**
   https://python.langchain.com/api_reference/anthropic/chat_models/langchain_anthropic.chat_models.ChatAnthropic.html

5. **LangChain Anthropic Integration Guide**
   https://python.langchain.com/docs/integrations/chat/anthropic/

6. **LangChain Parallel Tool Calling**
   https://python.langchain.com/docs/how_to/tool_calling_parallel/

7. **AWS Bedrock Anthropic Model Parameters**
   https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-text-completion.html

8. **PromptHub - Anthropic Best Practices**
   https://www.prompthub.us/blog/using-anthropic-best-practices-parameters-and-large-context-windows

---

## Appendix: Quick Start Checklist

- [ ] Install `langchain-anthropic` package
- [ ] Add `ANTHROPIC_API_KEY` to `.env` file
- [ ] Update `model_config.py` with Claude model functions
- [ ] Update `supervisor_agent.py` to use Claude models
- [ ] Assign models to agents:
  - [ ] Supervisor → Sonnet 4.5
  - [ ] Research → Sonnet 4.5
  - [ ] Analysis → Sonnet 4 (extended thinking)
  - [ ] Writing → Sonnet 4.5
  - [ ] Reviewer → Sonnet 4.5
- [ ] Test with simple workflow
- [ ] Run full integration tests
- [ ] Monitor costs and performance
- [ ] Document any issues or optimizations

---

**End of Guide**
