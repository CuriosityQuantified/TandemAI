# LangChain v1.0 Core Components - Comprehensive Research

**Document Purpose**: Detailed research and implementation guide for LangChain v1.0 core components for ATLAS rebuild.

**Research Date**: 2025-10-01

**Documentation Status**: Alpha Release - Subject to Change

---

## Table of Contents

1. [Overview](#overview)
2. [Installation & Setup](#installation--setup)
3. [Philosophy & Design Principles](#philosophy--design-principles)
4. [Models](#models)
5. [Messages](#messages)
6. [Tools](#tools)
7. [Agents](#agents)
8. [Short-Term Memory](#short-term-memory)
9. [Streaming](#streaming)
10. [Migration Considerations](#migration-considerations)
11. [Best Practices for ATLAS](#best-practices-for-atlas)

---

## Overview

### LangChain v1.0 Major Changes

LangChain v1.0 represents a significant evolution from v0.x with focus on modularity, performance, and production readiness.

#### Key Highlights

**1. Python Version Requirements**
- **Dropped**: Python 3.9 support
- **Required**: Python 3.10+
- **Impact**: Enables modern Python features and type hints

**2. Package Restructuring**
- **Core Split**: Reduced `langchain` package surface area
- **New Packages**:
  - `langchain-core`: Core abstractions and interfaces
  - `langchain-anthropic`: Anthropic Claude integration
  - `langchain-aws`: AWS Bedrock integration
  - `langchain-openai`: OpenAI GPT integration
  - `langchain-legacy`: Backward compatibility layer
- **Benefit**: Avoid dependency bloat, install only what you need

**3. New Features**
- `.content_blocks` property on message objects
- Standardized message content across LLM providers
- Prebuilt `langgraph` chains and agents
- Enhanced structured output capabilities

**4. Agent Improvements**
- Enhanced `create_react_agent` with structured outputs
- Improved tool calling and error handling
- Support for sophisticated output generation
- Better streaming and intermediate results

#### Breaking Changes

**Return Type Updates**
```python
# Before (v0.x)
response = model.invoke("Hello")
response.text()  # Method call

# After (v1.0)
response = model.invoke("Hello")
response.text  # Property access
```

**Import Changes**
```python
# Before (v0.x)
from langchain import LLMChain
from langchain.agents import initialize_agent

# After (v1.0)
from langchain_legacy import LLMChain
from langchain.agents import create_agent
```

**Message Format Changes**
- Updated default message formats
- Standardized content representation
- Enhanced multimodal support

---

## Installation & Setup

### Core Installation

**Using pip (standard)**
```bash
# Create virtual environment
python3.10 -m venv .venv
source .venv/bin/activate

# Install LangChain v1.0 (alpha)
pip install --pre -U langchain
```

**Using uv (recommended for ATLAS)**
```bash
# Create virtual environment with uv
uv venv

# Activate environment
source .venv/bin/activate

# Install LangChain v1.0 (alpha)
uv pip install --prerelease=allow langchain
```

### Provider Integrations

Install provider-specific packages based on your LLM needs:

**OpenAI**
```bash
pip install -U langchain-openai
# or
uv pip install langchain-openai
```

**Anthropic (Claude)**
```bash
pip install -U langchain-anthropic
# or
uv pip install langchain-anthropic
```

**Google (Gemini)**
```bash
pip install -U langchain-google-genai
# or
uv pip install langchain-google-genai
```

**AWS Bedrock**
```bash
pip install -U langchain-aws
# or
uv pip install langchain-aws
```

**Groq**
```bash
pip install -U langchain-groq
# or
uv pip install langchain-groq
```

### Environment Configuration

Create a `.env` file with your API keys:

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google
GOOGLE_API_KEY=...

# Groq
GROQ_API_KEY=gsk_...

# AWS (if using Bedrock)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
```

### Minimal Requirements for ATLAS

```txt
# requirements.txt for ATLAS backend
langchain>=1.0.0a0
langchain-core>=1.0.0
langchain-openai>=0.2.0
langchain-anthropic>=0.3.0
langchain-groq>=0.2.0
langgraph>=0.3.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

### Installation Verification

```python
import langchain
from langchain.chat_models import init_chat_model

print(f"LangChain version: {langchain.__version__}")

# Test basic model initialization
model = init_chat_model("openai:gpt-4o-mini")
response = model.invoke("Say hello!")
print(response.content)
```

---

## Philosophy & Design Principles

### Core Design Philosophy

LangChain v1.0 is built on these foundational principles:

#### 1. Flexibility and Accessibility

**Goal**: "Easiest place to start building with LLMs, while also being production-ready"

**Implementation**:
- Low barrier to entry with simple APIs
- Progressive complexity for advanced use cases
- Production-grade reliability and performance

**Example**:
```python
# Simple: Single line agent creation
agent = create_agent("openai:gpt-4o", tools=[search_tool])

# Advanced: Full configuration
agent = create_agent(
    model=model,
    tools=tools,
    prompt=dynamic_prompt_fn,
    checkpointer=postgres_saver,
    response_format=StructuredOutput,
    pre_model_hook=auth_middleware,
    post_model_hook=logging_middleware
)
```

#### 2. Avoid Vendor Lock-in

**Strategy**: Standardize model inputs/outputs across providers

**Benefits**:
- Switch between OpenAI, Anthropic, Google, etc. with minimal code changes
- Compare model performance easily
- Optimize costs by routing to different providers

**Example**:
```python
# Same code works with any provider
models = [
    init_chat_model("openai:gpt-4o"),
    init_chat_model("anthropic:claude-3-7-sonnet-latest"),
    init_chat_model("google:gemini-2.0-flash-exp")
]

for model in models:
    response = model.invoke("Explain quantum computing")
    print(f"{model.model}: {response.content[:100]}...")
```

#### 3. Technology Transformation Vision

**Core Belief**: LLMs are most impactful when:
1. Combined with external data sources (RAG)
2. Used to create "agentic" applications (ReAct)
3. Orchestrating complex computational flows (LangGraph)

**Architectural Principles**:

**Model Abstraction**
- Standardize different provider APIs
- Enable easy switching between models
- Support evolving capabilities (multimodal, function calling)

**Computational Orchestration**
- Models should do more than simple generation
- Enable dynamic tool usage
- Support complex interaction flows
- Provide low-level control mechanisms (via LangGraph)

**Modular Component Design**
- Composable building blocks
- Extensible integration framework
- Clear separation of concerns
- Progressive complexity support

### Design Evolution Strategy

1. **Iterative Development**: Continuous improvement based on feedback
2. **Community-Driven**: Incorporate user patterns and needs
3. **Developer Experience**: Focus on usability and documentation
4. **Proactive Adaptation**: Respond to emerging AI technologies

### Application to ATLAS

**For ATLAS Multi-Agent System**:

1. **Flexibility**: Start with simple agents, evolve to complex orchestration
2. **Vendor Agnostic**: Route tasks to optimal models (GPT-4o for reasoning, Claude for analysis)
3. **Modular Design**: Research, Analysis, Writing agents as composable units
4. **Orchestration**: LangGraph for supervisor coordination and state management

---

## Models

### Overview

LLMs (Large Language Models) are the core intelligence layer in LangChain applications. v1.0 provides a unified interface for working with models from multiple providers.

### Model Capabilities

**Core Capabilities**:
- Text generation and completion
- Translation and summarization
- Question answering
- Conversational interfaces

**Advanced Features**:
- Tool calling (function invocation)
- Structured outputs (Pydantic, JSON Schema)
- Multimodal processing (text, images, audio, video)
- Reasoning and chain-of-thought
- Streaming responses

### Model Initialization

**Unified Initialization**:
```python
from langchain.chat_models import init_chat_model

# Simple initialization with model identifier
model = init_chat_model("openai:gpt-4o-mini")

# Provider-specific initialization
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

openai_model = ChatOpenAI(model="gpt-4o", temperature=0.7)
anthropic_model = ChatAnthropic(model="claude-3-7-sonnet-latest")
```

**Model Identifier Format**:
```
provider:model-name

Examples:
- openai:gpt-4o
- openai:gpt-4o-mini
- openai:gpt-5-nano
- anthropic:claude-3-7-sonnet-latest
- anthropic:claude-3-opus-latest
- google:gemini-2.0-flash-exp
- groq:llama-3.3-70b-versatile
```

### Core Invocation Methods

#### 1. Standard Invocation

```python
model = init_chat_model("openai:gpt-4o-mini")

# Simple string input
response = model.invoke("Why do parrots talk?")
print(response.content)

# Message-based input
from langchain_core.messages import HumanMessage, SystemMessage

messages = [
    SystemMessage(content="You are a helpful biology expert."),
    HumanMessage(content="Why do parrots talk?")
]
response = model.invoke(messages)
print(response.content)
```

#### 2. Streaming

```python
# Stream tokens as they're generated
for chunk in model.stream("Write a short poem about AI"):
    print(chunk.content, end="", flush=True)
```

#### 3. Batch Processing

```python
# Process multiple requests in parallel
inputs = [
    "What is Python?",
    "What is JavaScript?",
    "What is Rust?"
]
responses = model.batch(inputs)
for response in responses:
    print(response.content)
```

#### 4. Async Invocation

```python
import asyncio

async def async_example():
    # Non-blocking async invocation
    response = await model.ainvoke("Explain quantum computing")
    print(response.content)

    # Async streaming
    async for chunk in model.astream("Write a story"):
        print(chunk.content, end="", flush=True)

    # Async batch
    responses = await model.abatch(["Question 1", "Question 2"])
    return responses

asyncio.run(async_example())
```

### Configuration Options

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="gpt-4o",
    temperature=0.7,           # Creativity control (0.0-2.0)
    max_tokens=1000,           # Maximum response length
    top_p=0.9,                 # Nucleus sampling
    frequency_penalty=0.0,     # Reduce repetition
    presence_penalty=0.0,      # Encourage topic diversity
    timeout=30,                # Request timeout
    max_retries=3,             # Retry failed requests
    api_key="sk-...",          # API key (or use env var)
)
```

### Tool Calling

Enable models to request tool execution:

```python
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    return f"The weather in {city} is sunny and 72°F"

# Bind tools to model
model_with_tools = model.bind_tools([get_weather])

# Model can now request tool calls
response = model_with_tools.invoke("What's the weather in San Francisco?")

# Response includes tool call request
if response.tool_calls:
    tool_call = response.tool_calls[0]
    print(f"Tool: {tool_call['name']}")
    print(f"Args: {tool_call['args']}")
```

### Structured Outputs

Force model responses to follow a specific schema:

```python
from pydantic import BaseModel, Field

class WeatherResponse(BaseModel):
    city: str = Field(description="The city name")
    temperature: float = Field(description="Temperature in Fahrenheit")
    conditions: str = Field(description="Weather conditions")

# Bind structured output schema
structured_model = model.with_structured_output(WeatherResponse)

# Response automatically parsed to Pydantic model
response = structured_model.invoke("What's the weather in Boston?")
print(f"City: {response.city}")
print(f"Temp: {response.temperature}°F")
print(f"Conditions: {response.conditions}")
```

### Multimodal Support

Process images, audio, and other media:

```python
from langchain_core.messages import HumanMessage

# Image input
message = HumanMessage(
    content=[
        {"type": "text", "text": "Describe this image"},
        {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
    ]
)
response = model.invoke([message])
print(response.content)

# Base64 image
import base64
with open("image.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

message = HumanMessage(
    content=[
        {"type": "text", "text": "What's in this image?"},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
    ]
)
```

### Token Usage Tracking

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4o-mini")

# Enable token tracking
response = model.invoke("Hello!", return_usage=True)

# Access usage data
print(f"Prompt tokens: {response.usage_metadata['input_tokens']}")
print(f"Completion tokens: {response.usage_metadata['output_tokens']}")
print(f"Total tokens: {response.usage_metadata['total_tokens']}")
```

### Local Models (Ollama)

```python
from langchain_community.chat_models import ChatOllama

# Use local models via Ollama
local_model = ChatOllama(model="llama3")
response = local_model.invoke("Explain LangChain")
print(response.content)
```

### Model Selection for ATLAS

**Recommended Model Strategy**:

```python
# models.py - ATLAS model configuration

from langchain.chat_models import init_chat_model
from typing import Literal

ModelType = Literal["fast", "smart", "balanced", "reasoning"]

def get_atlas_model(model_type: ModelType):
    """Get appropriate model for task type."""

    models = {
        # Fast: Quick responses, simple tasks
        "fast": "groq:llama-3.3-70b-versatile",

        # Smart: Complex reasoning, research
        "smart": "openai:gpt-4o",

        # Balanced: General purpose
        "balanced": "anthropic:claude-3-7-sonnet-latest",

        # Reasoning: Deep analysis
        "reasoning": "openai:gpt-5-nano"
    }

    return init_chat_model(models[model_type])

# Usage in ATLAS agents
research_model = get_atlas_model("smart")
writing_model = get_atlas_model("balanced")
quick_check_model = get_atlas_model("fast")
```

---

## Messages

### Overview

Messages are the fundamental unit of context for language models in LangChain. They represent communication between users, AI, system instructions, and tool results.

### Message Structure

Every message contains:
1. **Role**: Who the message is from (system, user, AI, tool)
2. **Content**: The message payload (text, images, audio, etc.)
3. **Metadata**: Optional additional information

### Message Types

#### 1. SystemMessage

Provides initial instructions and context to the model:

```python
from langchain_core.messages import SystemMessage

system_msg = SystemMessage(
    content="You are a helpful research assistant specializing in scientific literature."
)

# With metadata
system_msg = SystemMessage(
    content="You are an expert data analyst.",
    metadata={
        "persona": "analyst",
        "expertise": ["statistics", "visualization"],
        "created_at": "2025-10-01"
    }
)
```

#### 2. HumanMessage

Represents user input:

```python
from langchain_core.messages import HumanMessage

# Simple text
user_msg = HumanMessage(content="What is quantum computing?")

# With metadata
user_msg = HumanMessage(
    content="Explain machine learning",
    metadata={
        "user_id": "user_123",
        "timestamp": "2025-10-01T10:30:00Z",
        "session_id": "session_456"
    }
)
```

#### 3. AIMessage

Model's response:

```python
from langchain_core.messages import AIMessage

# Simple response
ai_msg = AIMessage(content="Quantum computing uses quantum mechanics...")

# With tool calls
ai_msg = AIMessage(
    content="I'll search for that information.",
    tool_calls=[
        {
            "id": "call_abc123",
            "name": "search_database",
            "args": {"query": "quantum computing", "limit": 5}
        }
    ]
)
```

#### 4. ToolMessage

Represents tool execution results:

```python
from langchain_core.messages import ToolMessage

tool_msg = ToolMessage(
    content='{"results": ["Result 1", "Result 2"]}',
    tool_call_id="call_abc123",
    name="search_database"
)
```

### Message Content Formats

#### Text Content

```python
# Simple string
msg = HumanMessage(content="Hello, world!")

# Text content block
msg = HumanMessage(
    content=[
        {"type": "text", "text": "Analyze this data"}
    ]
)
```

#### Multimodal Content

**Images**:
```python
# Image URL
msg = HumanMessage(
    content=[
        {"type": "text", "text": "Describe this image"},
        {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
    ]
)

# Base64 image
msg = HumanMessage(
    content=[
        {"type": "text", "text": "What's in this image?"},
        {
            "type": "image_url",
            "image_url": {
                "url": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
            }
        }
    ]
)

# File ID (provider-specific)
msg = HumanMessage(
    content=[
        {"type": "text", "text": "Analyze this"},
        {"type": "image_url", "image_url": {"url": "file://file-abc123"}}
    ]
)
```

**Audio**:
```python
msg = HumanMessage(
    content=[
        {"type": "text", "text": "Transcribe this audio"},
        {"type": "audio_url", "audio_url": {"url": "https://example.com/audio.mp3"}}
    ]
)
```

**Video**:
```python
msg = HumanMessage(
    content=[
        {"type": "text", "text": "Summarize this video"},
        {"type": "video_url", "video_url": {"url": "https://example.com/video.mp4"}}
    ]
)
```

**Documents**:
```python
msg = HumanMessage(
    content=[
        {"type": "text", "text": "Analyze this document"},
        {"type": "document_url", "document_url": {"url": "https://example.com/doc.pdf"}}
    ]
)
```

### Content Blocks Property

New in v1.0: `.content_blocks` provides structured access to message content:

```python
response = model.invoke([
    HumanMessage(content=[
        {"type": "text", "text": "Describe this image"},
        {"type": "image_url", "image_url": {"url": "https://example.com/img.jpg"}}
    ])
])

# Access content blocks
for block in response.content_blocks:
    if block.type == "text":
        print(f"Text: {block.text}")
    elif block.type == "image":
        print(f"Image: {block.image_url}")
```

### Conversation History

```python
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# Build conversation history
messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="What is Python?"),
    AIMessage(content="Python is a high-level programming language..."),
    HumanMessage(content="What are its main features?"),
]

# Continue conversation
response = model.invoke(messages)
messages.append(response)
```

### Message Metadata

```python
msg = HumanMessage(
    content="Analyze this data",
    metadata={
        "user_id": "user_123",
        "session_id": "session_456",
        "timestamp": "2025-10-01T10:30:00Z",
        "language": "en",
        "priority": "high",
        "context": {
            "project": "ATLAS",
            "task": "research",
            "agent": "supervisor"
        }
    }
)

# Access metadata
print(msg.metadata["user_id"])
print(msg.metadata["context"]["project"])
```

### Provider-Specific Metadata

```python
# OpenAI-specific
msg = AIMessage(
    content="Response text",
    metadata={
        "model": "gpt-4o",
        "finish_reason": "stop",
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 50,
            "total_tokens": 60
        }
    }
)

# Anthropic-specific
msg = AIMessage(
    content="Response text",
    metadata={
        "model": "claude-3-7-sonnet-latest",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 10,
            "output_tokens": 50
        }
    }
)
```

### Streaming Messages

```python
# Stream message chunks
for chunk in model.stream("Write a story"):
    # Each chunk is an AIMessage
    print(chunk.content, end="", flush=True)

    # Access metadata
    if hasattr(chunk, "usage_metadata"):
        print(f"\nTokens: {chunk.usage_metadata}")
```

### Message Utilities

**Convert to Dict**:
```python
msg = HumanMessage(content="Hello")
msg_dict = msg.dict()
# {'type': 'human', 'content': 'Hello', 'metadata': {}}
```

**From Dict**:
```python
from langchain_core.messages import message_from_dict

msg_dict = {'type': 'human', 'content': 'Hello'}
msg = message_from_dict(msg_dict)
```

### ATLAS Message Patterns

```python
# atlas_messages.py

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from datetime import datetime
from typing import Dict, Any

def create_atlas_system_message(agent_role: str, context: Dict[str, Any]) -> SystemMessage:
    """Create ATLAS system message with agent context."""
    return SystemMessage(
        content=f"You are the ATLAS {agent_role} agent.",
        metadata={
            "agent": agent_role,
            "project": context.get("project_name"),
            "session_id": context.get("session_id"),
            "created_at": datetime.utcnow().isoformat()
        }
    )

def create_atlas_user_message(content: str, user_id: str, task_id: str) -> HumanMessage:
    """Create ATLAS user message with task context."""
    return HumanMessage(
        content=content,
        metadata={
            "user_id": user_id,
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

def create_atlas_tool_result(
    tool_name: str,
    result: Any,
    tool_call_id: str,
    success: bool = True
) -> ToolMessage:
    """Create ATLAS tool result message."""
    return ToolMessage(
        content=str(result),
        tool_call_id=tool_call_id,
        name=tool_name,
        metadata={
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

---

## Tools

### Overview

Tools extend model capabilities by allowing them to interact with external systems through well-defined inputs and outputs. In LangChain v1.0, tools are the primary mechanism for giving agents actionable capabilities.

### Creating Tools

#### Basic Tool with Decorator

The simplest way to create a tool:

```python
from langchain_core.tools import tool

@tool
def search_database(query: str, limit: int = 10) -> str:
    """Search the customer database for records matching the query.

    Args:
        query: The search query string
        limit: Maximum number of results to return

    Returns:
        JSON string containing search results
    """
    # Implementation
    results = perform_search(query, limit)
    return json.dumps(results)
```

**Requirements**:
- Type hints are mandatory for all parameters
- Docstring describes the tool's purpose
- Function defines clear input/output schema

#### Custom Tool Name

```python
@tool("customer_search")
def search_database(query: str) -> str:
    """Search customer records."""
    return perform_search(query)
```

#### Complex Input Schema

Using Pydantic for structured inputs:

```python
from pydantic import BaseModel, Field
from typing import Literal

class WeatherInput(BaseModel):
    location: str = Field(description="City name or ZIP code")
    units: Literal["celsius", "fahrenheit"] = Field(default="fahrenheit")
    include_forecast: bool = Field(default=False, description="Include 5-day forecast")

@tool(args_schema=WeatherInput)
def get_weather(location: str, units: str = "fahrenheit", include_forecast: bool = False) -> str:
    """Retrieve weather information for a location.

    Returns current weather and optionally a 5-day forecast.
    """
    # Implementation
    return fetch_weather_data(location, units, include_forecast)
```

#### Tool with Return Schema

```python
from pydantic import BaseModel

class WeatherOutput(BaseModel):
    temperature: float
    conditions: str
    humidity: int
    wind_speed: float

@tool(return_schema=WeatherOutput)
def get_weather(location: str) -> WeatherOutput:
    """Get structured weather data."""
    data = fetch_weather(location)
    return WeatherOutput(**data)
```

### Tool Configuration

#### Tool Properties

```python
# Access tool metadata
print(search_database.name)           # "search_database"
print(search_database.description)    # Docstring content
print(search_database.args_schema)    # Pydantic model for args
```

#### Custom Tool Class

For advanced use cases:

```python
from langchain_core.tools import BaseTool
from pydantic import Field

class CustomSearchTool(BaseTool):
    name: str = "custom_search"
    description: str = "Search with custom logic"
    api_key: str = Field(..., description="API key for search service")

    def _run(self, query: str) -> str:
        """Synchronous implementation."""
        return self._perform_search(query)

    async def _arun(self, query: str) -> str:
        """Async implementation."""
        return await self._perform_search_async(query)

    def _perform_search(self, query: str) -> str:
        # Use self.api_key
        return results

# Instantiate with configuration
search_tool = CustomSearchTool(api_key="sk-...")
```

### Binding Tools to Models

```python
from langchain_core.tools import tool

@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    return str(eval(expression))

@tool
def search_web(query: str) -> str:
    """Search the web for information."""
    return perform_web_search(query)

# Bind tools to model
model_with_tools = model.bind_tools([calculator, search_web])

# Model can now request tool calls
response = model_with_tools.invoke("What is 15 * 23?")

if response.tool_calls:
    tool_call = response.tool_calls[0]
    print(f"Tool: {tool_call['name']}")      # "calculator"
    print(f"Args: {tool_call['args']}")      # {"expression": "15 * 23"}
```

### Tool Execution

#### Manual Execution

```python
# Execute tool manually
tool_result = calculator.invoke({"expression": "15 * 23"})
print(tool_result)  # "345"
```

#### ToolNode (Automated Execution)

```python
from langgraph.prebuilt import ToolNode

# Create tool node that automatically executes tool calls
tools = [calculator, search_web]
tool_node = ToolNode(tools)

# Execute tool calls from AI message
ai_message = model_with_tools.invoke("What is 10 + 5?")
tool_results = tool_node.invoke(ai_message)
```

### Error Handling

#### Basic Error Handling

```python
@tool
def divide(a: float, b: float) -> str:
    """Divide two numbers."""
    try:
        result = a / b
        return str(result)
    except ZeroDivisionError:
        return "Error: Cannot divide by zero"
    except Exception as e:
        return f"Error: {str(e)}"
```

#### ToolNode Error Handling

```python
from langgraph.prebuilt import ToolNode

# Catch all errors and return as tool messages
tool_node = ToolNode(
    tools=[divide],
    handle_tool_errors=True
)

# Catch specific error types
tool_node = ToolNode(
    tools=[divide],
    handle_tool_errors={
        ZeroDivisionError: "Cannot divide by zero. Please use a non-zero divisor.",
        ValueError: "Invalid input. Please provide valid numbers."
    }
)

# Custom error handler
def custom_error_handler(error: Exception) -> str:
    logger.error(f"Tool error: {error}")
    return f"An error occurred: {str(error)}"

tool_node = ToolNode(
    tools=[divide],
    handle_tool_errors=custom_error_handler
)
```

### Advanced Tool Capabilities

#### Tools with State Access

Tools can access and modify agent state:

```python
from typing import TypedDict

class AgentState(TypedDict):
    messages: list
    user_context: dict
    iteration_count: int

@tool
def update_context(key: str, value: str, state: AgentState) -> str:
    """Update user context in agent state."""
    state["user_context"][key] = value
    return f"Updated {key} to {value}"
```

#### Async Tools

```python
@tool
async def async_search(query: str) -> str:
    """Perform async web search."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.search.com?q={query}") as resp:
            data = await resp.json()
            return data["results"]
```

#### Tool with Dependencies

```python
from typing import Annotated

@tool
def query_database(
    query: str,
    db_connection: Annotated[DatabaseConnection, "Database connection"]
) -> str:
    """Query database with injected connection."""
    results = db_connection.execute(query)
    return json.dumps(results)

# Provide dependencies when creating tool node
tool_node = ToolNode(
    tools=[query_database],
    dependencies={
        "db_connection": database_connection
    }
)
```

### Parallel Tool Execution

```python
from langgraph.prebuilt import ToolNode

# Enable parallel execution
tool_node = ToolNode(
    tools=[search_web, query_database, fetch_weather],
    parallel=True  # Execute multiple tool calls concurrently
)

# Model can request multiple tools
response = model_with_tools.invoke(
    "What's the weather in SF and search for news about AI?"
)

# Both tools execute in parallel
results = tool_node.invoke(response)
```

### Tool Metadata

```python
@tool
def analytics_query(query: str) -> str:
    """Query analytics database."""
    return perform_query(query)

# Add metadata
analytics_query.metadata = {
    "requires_auth": True,
    "rate_limit": "100/hour",
    "cost": 0.01,
    "category": "analytics"
}

# Access metadata
if analytics_query.metadata.get("requires_auth"):
    # Check authentication
    pass
```

### ATLAS Tool Patterns

```python
# atlas_tools.py

from langchain_core.tools import tool
from typing import Literal
import json

@tool
def atlas_research_search(
    query: str,
    sources: list[str] = ["web", "academic", "news"],
    max_results: int = 10
) -> str:
    """Search multiple sources for research information.

    Used by ATLAS Research Agent to gather information from
    web, academic papers, and news sources.
    """
    results = perform_multi_source_search(query, sources, max_results)
    return json.dumps(results)

@tool
def atlas_analyze_data(
    data: str,
    analysis_type: Literal["statistical", "comparative", "trend"],
    output_format: Literal["text", "json", "chart"] = "json"
) -> str:
    """Analyze data using specified analysis type.

    Used by ATLAS Analysis Agent to perform various data
    analysis operations.
    """
    analysis_result = perform_analysis(data, analysis_type)

    if output_format == "json":
        return json.dumps(analysis_result)
    elif output_format == "chart":
        return generate_chart(analysis_result)
    else:
        return format_as_text(analysis_result)

@tool
def atlas_write_content(
    content_type: Literal["summary", "report", "article"],
    data: str,
    style: Literal["formal", "casual", "technical"] = "formal",
    length: Literal["short", "medium", "long"] = "medium"
) -> str:
    """Generate written content from data.

    Used by ATLAS Writing Agent to create various document types.
    """
    written_content = generate_content(content_type, data, style, length)
    return written_content

@tool
def atlas_file_operation(
    operation: Literal["save", "load", "append", "list"],
    file_path: str,
    content: str = None
) -> str:
    """Perform file operations in ATLAS workspace.

    Used by all agents to interact with project files.
    """
    if operation == "save":
        save_file(file_path, content)
        return f"Saved content to {file_path}"
    elif operation == "load":
        content = load_file(file_path)
        return content
    elif operation == "append":
        append_to_file(file_path, content)
        return f"Appended content to {file_path}"
    elif operation == "list":
        files = list_files(file_path)
        return json.dumps(files)

# Tool collections for different agents
RESEARCH_TOOLS = [atlas_research_search, atlas_file_operation]
ANALYSIS_TOOLS = [atlas_analyze_data, atlas_file_operation]
WRITING_TOOLS = [atlas_write_content, atlas_file_operation]
```

---

## Agents

### Overview

Agents combine language models with tools to reason about and solve tasks iteratively. LangChain v1.0 uses a ReAct (Reasoning + Acting) implementation that follows a thought → action → observation loop.

### Core Agent Components

**1. Model**: The LLM that drives reasoning and decision-making
**2. Tools**: Available actions the agent can take
**3. Prompt**: System instructions and persona
**4. State**: Memory and conversation history
**5. Checkpointer**: Persistence layer for state

### Creating Agents

#### Basic Agent

```python
from langchain.agents import create_agent
from langchain_core.tools import tool

@tool
def search_web(query: str) -> str:
    """Search the web for information."""
    return perform_search(query)

@tool
def calculate(expression: str) -> str:
    """Evaluate mathematical expressions."""
    return str(eval(expression))

# Create basic agent
agent = create_agent(
    model="anthropic:claude-3-7-sonnet-latest",
    tools=[search_web, calculate],
    prompt="You are a helpful assistant. Be concise and accurate."
)

# Use agent
response = agent.invoke({
    "messages": [{"role": "user", "content": "What is 15 * 23?"}]
})
print(response["messages"][-1]["content"])
```

#### Agent with Dynamic Model Selection

```python
def select_model(state: dict) -> str:
    """Select model based on task complexity."""
    message = state["messages"][-1]["content"]

    if "complex" in message or "analyze" in message:
        return "openai:gpt-4o"
    else:
        return "groq:llama-3.3-70b-versatile"

agent = create_agent(
    model=select_model,  # Callable for dynamic selection
    tools=tools,
    prompt="You are a helpful assistant."
)
```

#### Agent with Structured Output

```python
from pydantic import BaseModel, Field

class ResearchOutput(BaseModel):
    summary: str = Field(description="Brief summary of findings")
    sources: list[str] = Field(description="List of sources used")
    confidence: float = Field(description="Confidence score 0-1")

agent = create_agent(
    model="openai:gpt-4o",
    tools=[search_web],
    prompt="You are a research assistant.",
    response_format=ResearchOutput  # Force structured output
)

response = agent.invoke({
    "messages": [{"role": "user", "content": "Research quantum computing"}]
})

# Response automatically parsed to Pydantic model
output = response["output"]
print(f"Summary: {output.summary}")
print(f"Sources: {output.sources}")
print(f"Confidence: {output.confidence}")
```

### Agent Configuration

#### Full Configuration Example

```python
from langgraph.checkpoint.memory import MemorySaver

agent = create_agent(
    # Model configuration
    model="openai:gpt-4o",

    # Tools
    tools=[search_web, calculate, fetch_data],

    # System prompt
    prompt="You are an expert research assistant with access to web search and data analysis tools.",

    # Memory/persistence
    checkpointer=MemorySaver(),

    # Structured output
    response_format=ResearchOutput,

    # State customization
    state_schema=CustomAgentState,

    # Interrupt before/after tools
    interrupt_before=["tools"],
    interrupt_after=["tools"],
)
```

#### Dynamic Prompts

```python
def create_dynamic_prompt(state: dict) -> str:
    """Generate prompt based on state."""
    user_role = state.get("user_role", "guest")

    if user_role == "admin":
        return "You are an admin assistant with full access."
    else:
        return "You are a helpful assistant with limited access."

agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    prompt=create_dynamic_prompt  # Callable for dynamic prompts
)
```

### Tool Node Configuration

```python
from langgraph.prebuilt import ToolNode

# Basic tool node
tool_node = ToolNode(tools=[search_web, calculate])

# With error handling
tool_node = ToolNode(
    tools=tools,
    handle_tool_errors=True,
    parallel=True  # Enable parallel tool execution
)

# Custom tool node with middleware
def log_tool_calls(tool_call):
    """Log all tool invocations."""
    logger.info(f"Tool called: {tool_call['name']}")
    return tool_call

tool_node = ToolNode(
    tools=tools,
    pre_tool_hook=log_tool_calls
)
```

### State Management

#### Default Agent State

```python
# Default state schema
{
    "messages": list[BaseMessage],  # Conversation history
}
```

#### Custom State Schema

```python
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage

class CustomAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], "Conversation history"]
    user_id: str
    user_context: dict
    iteration_count: int
    research_data: list[dict]

agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    state_schema=CustomAgentState
)

# Access custom state
response = agent.invoke({
    "messages": [{"role": "user", "content": "Hello"}],
    "user_id": "user_123",
    "user_context": {"role": "admin"},
    "iteration_count": 0,
    "research_data": []
})
```

### Memory and Persistence

#### In-Memory Checkpointer

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    checkpointer=checkpointer
)

# Use with thread ID for conversation continuity
config = {"configurable": {"thread_id": "conversation_1"}}

response1 = agent.invoke(
    {"messages": [{"role": "user", "content": "My name is Alice"}]},
    config=config
)

response2 = agent.invoke(
    {"messages": [{"role": "user", "content": "What's my name?"}]},
    config=config
)
# Agent remembers: "Your name is Alice"
```

#### PostgreSQL Checkpointer

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost:5432/langchain"
)

agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    checkpointer=checkpointer
)
```

### Agent Execution Patterns

#### Standard Invocation

```python
response = agent.invoke({
    "messages": [{"role": "user", "content": "Research AI trends"}]
})

# Access final response
final_message = response["messages"][-1]
print(final_message["content"])
```

#### Streaming

```python
# Stream agent progress
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Search for news"}]},
    stream_mode="updates"
):
    print(chunk)
```

#### Async Invocation

```python
import asyncio

async def run_agent():
    response = await agent.ainvoke({
        "messages": [{"role": "user", "content": "Analyze data"}]
    })
    return response

asyncio.run(run_agent())
```

### Hooks and Middleware

#### Pre-Model Hook

Execute logic before LLM invocation:

```python
def pre_model_hook(state: dict) -> dict:
    """Log and modify state before model call."""
    logger.info(f"Model input: {state['messages']}")

    # Add system context
    state["messages"].insert(0, {
        "role": "system",
        "content": "Current time: " + datetime.now().isoformat()
    })

    return state

agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    pre_model_hook=pre_model_hook
)
```

#### Post-Model Hook

Execute logic after LLM response:

```python
def post_model_hook(state: dict, response: dict) -> dict:
    """Log and modify response."""
    logger.info(f"Model response: {response}")

    # Track token usage
    track_tokens(response.get("usage"))

    return response

agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    post_model_hook=post_model_hook
)
```

### Human-in-the-Loop

```python
agent = create_agent(
    model="openai:gpt-4o",
    tools=[search_web, send_email],
    interrupt_before=["tools"]  # Pause before tool execution
)

# Run until interruption
response = agent.invoke({
    "messages": [{"role": "user", "content": "Send email to boss"}]
})

# Check if interrupted
if response.get("interrupted"):
    tool_call = response["next"][0]

    # Approve or modify
    if tool_call["name"] == "send_email":
        if approve_email(tool_call["args"]):
            # Continue execution
            response = agent.invoke(None, config=response["config"])
```

### Multi-Agent Patterns

#### Supervisor Pattern

```python
# Create specialized agents
research_agent = create_agent(
    model="openai:gpt-4o",
    tools=[search_web, fetch_data],
    prompt="You are a research specialist."
)

writing_agent = create_agent(
    model="anthropic:claude-3-7-sonnet-latest",
    tools=[write_content, save_file],
    prompt="You are a writing specialist."
)

# Supervisor delegates to agents
@tool
def delegate_research(task: str) -> str:
    """Delegate research tasks to research agent."""
    response = research_agent.invoke({
        "messages": [{"role": "user", "content": task}]
    })
    return response["messages"][-1]["content"]

@tool
def delegate_writing(task: str) -> str:
    """Delegate writing tasks to writing agent."""
    response = writing_agent.invoke({
        "messages": [{"role": "user", "content": task}]
    })
    return response["messages"][-1]["content"]

supervisor = create_agent(
    model="openai:gpt-4o",
    tools=[delegate_research, delegate_writing],
    prompt="You are a supervisor. Delegate tasks to appropriate specialists."
)
```

### ATLAS Agent Configuration

```python
# atlas_agents.py

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.postgres import PostgresSaver
from typing import Literal

# Initialize checkpointer
checkpointer = PostgresSaver.from_conn_string(
    "postgresql://atlas:atlas@localhost:5432/atlas_main"
)

def create_atlas_agent(
    agent_type: Literal["research", "analysis", "writing", "supervisor"],
    session_id: str,
    tools: list
):
    """Create ATLAS agent with appropriate configuration."""

    # Model selection based on agent type
    models = {
        "research": "openai:gpt-4o",
        "analysis": "anthropic:claude-3-7-sonnet-latest",
        "writing": "anthropic:claude-3-7-sonnet-latest",
        "supervisor": "openai:gpt-4o"
    }

    # Prompts for each agent type
    prompts = {
        "research": """You are the ATLAS Research Agent.
Your role is to gather, verify, and synthesize information from multiple sources.
Use your tools to search web, academic papers, and databases.
Always cite sources and assess information quality.""",

        "analysis": """You are the ATLAS Analysis Agent.
Your role is to analyze data, identify patterns, and generate insights.
Use your tools to perform statistical analysis and data visualization.
Present findings clearly with supporting evidence.""",

        "writing": """You are the ATLAS Writing Agent.
Your role is to create clear, well-structured written content.
Use your tools to organize information and generate documents.
Adapt your writing style to the requested format and audience.""",

        "supervisor": """You are the ATLAS Supervisor Agent.
Your role is to coordinate multiple specialist agents to accomplish complex tasks.
Break down tasks, delegate to appropriate agents, and synthesize results.
Ensure high-quality output by reviewing and refining agent work."""
    }

    # Create agent
    agent = create_agent(
        model=models[agent_type],
        tools=tools,
        prompt=prompts[agent_type],
        checkpointer=checkpointer
    )

    return agent

# Usage
research_agent = create_atlas_agent(
    agent_type="research",
    session_id="session_123",
    tools=[atlas_research_search, atlas_file_operation]
)
```

---

## Short-Term Memory

### Overview

Short-term memory allows AI agents to maintain context and remember interactions within a single conversation thread. Proper memory management is crucial as conversation history can quickly exceed LLM context windows.

### Core Concepts

**Memory Persistence**:
- Store conversation state between interactions
- Maintain context for coherent multi-turn conversations
- Manage token limits through strategic history management

**Checkpointers**:
- In-memory: Fast, ephemeral (development)
- Database-backed: Persistent, scalable (production)
- Support for PostgreSQL, Redis, etc.

### Checkpointer Implementation

#### In-Memory Saver

```python
from langgraph.checkpoint.memory import MemorySaver

# Create in-memory checkpointer
checkpointer = MemorySaver()

agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    checkpointer=checkpointer
)

# Use with thread ID
config = {"configurable": {"thread_id": "conversation_1"}}

# First message
response1 = agent.invoke(
    {"messages": [{"role": "user", "content": "My favorite color is blue"}]},
    config=config
)

# Second message - agent remembers context
response2 = agent.invoke(
    {"messages": [{"role": "user", "content": "What's my favorite color?"}]},
    config=config
)
# Response: "Your favorite color is blue"
```

#### PostgreSQL Checkpointer

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Create PostgreSQL checkpointer
checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:password@localhost:5432/database"
)

# Initialize schema (first time only)
checkpointer.setup()

agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    checkpointer=checkpointer
)

# Use with thread ID - persists across sessions
config = {"configurable": {"thread_id": "user_123_conversation"}}

response = agent.invoke(
    {"messages": [{"role": "user", "content": "Hello"}]},
    config=config
)
```

#### Redis Checkpointer

```python
from langgraph.checkpoint.redis import RedisSaver

checkpointer = RedisSaver.from_conn_info(
    host="localhost",
    port=6379,
    db=0
)

agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    checkpointer=checkpointer
)
```

### Custom Agent State

Define custom state schema to store additional context:

```python
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # Required: conversation history
    messages: Annotated[list[BaseMessage], "Conversation messages"]

    # Custom fields
    user_id: str
    user_preferences: dict
    research_data: list[dict]
    iteration_count: int

agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    state_schema=AgentState,
    checkpointer=checkpointer
)

# Provide custom state
response = agent.invoke({
    "messages": [{"role": "user", "content": "Hello"}],
    "user_id": "user_123",
    "user_preferences": {"theme": "dark"},
    "research_data": [],
    "iteration_count": 0
}, config=config)
```

### Memory Management Strategies

#### 1. Trim Messages

Remove oldest messages to stay within token limits:

```python
from langchain_core.messages import trim_messages

def manage_memory_trim(state: dict) -> dict:
    """Trim oldest messages to fit context window."""
    messages = state["messages"]

    # Keep system message and last N messages
    trimmed = trim_messages(
        messages,
        max_tokens=4000,  # Target token count
        strategy="last",   # Keep most recent
        include_system=True  # Always keep system message
    )

    state["messages"] = trimmed
    return state

agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    pre_model_hook=manage_memory_trim
)
```

#### 2. Delete Messages

Permanently remove specific messages:

```python
def manage_memory_delete(state: dict) -> dict:
    """Delete tool messages after processing."""
    messages = state["messages"]

    # Remove all tool messages (keep only user/AI)
    filtered = [
        msg for msg in messages
        if msg["role"] not in ["tool"]
    ]

    state["messages"] = filtered
    return state
```

#### 3. Summarize Messages

Create condensed summaries of conversation history:

```python
from langchain.chat_models import init_chat_model

summarizer = init_chat_model("openai:gpt-4o-mini")

def manage_memory_summarize(state: dict) -> dict:
    """Summarize old messages when context grows too large."""
    messages = state["messages"]

    if len(messages) > 20:  # Threshold
        # Extract messages to summarize (skip recent ones)
        old_messages = messages[1:-10]  # Skip system and recent
        recent_messages = messages[-10:]

        # Create summary
        summary_prompt = f"Summarize this conversation:\n{old_messages}"
        summary = summarizer.invoke(summary_prompt)

        # Replace old messages with summary
        state["messages"] = [
            messages[0],  # Keep system message
            {"role": "system", "content": f"Previous conversation summary: {summary.content}"},
            *recent_messages
        ]

    return state

agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    pre_model_hook=manage_memory_summarize
)
```

### Accessing Memory

#### Via Tools

Tools can access and modify agent state:

```python
from typing import Annotated

@tool
def get_user_info(
    key: str,
    state: Annotated[dict, "Agent state"]
) -> str:
    """Retrieve user information from memory."""
    return state.get("user_preferences", {}).get(key, "Not found")

@tool
def update_user_info(
    key: str,
    value: str,
    state: Annotated[dict, "Agent state"]
) -> str:
    """Update user information in memory."""
    if "user_preferences" not in state:
        state["user_preferences"] = {}
    state["user_preferences"][key] = value
    return f"Updated {key} to {value}"
```

#### Via Prompt Functions

```python
def create_prompt_with_context(state: dict) -> str:
    """Generate prompt with user context."""
    user_prefs = state.get("user_preferences", {})

    prompt = f"""You are a helpful assistant.

User context:
- Theme: {user_prefs.get('theme', 'default')}
- Language: {user_prefs.get('language', 'en')}

Be helpful and personalized."""

    return prompt

agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    prompt=create_prompt_with_context  # Dynamic prompt with memory
)
```

#### Via Hooks

```python
def pre_model_hook_with_memory(state: dict) -> dict:
    """Access memory before model call."""
    iteration = state.get("iteration_count", 0)
    state["iteration_count"] = iteration + 1

    # Add iteration context to messages
    if iteration > 5:
        state["messages"].insert(1, {
            "role": "system",
            "content": "Note: This conversation has been ongoing. Focus on concluding."
        })

    return state

def post_model_hook_with_memory(state: dict, response: dict) -> dict:
    """Update memory after model response."""
    # Store research findings
    if "research_data" not in state:
        state["research_data"] = []

    # Extract and store data from response
    if response.get("tool_calls"):
        for tool_call in response["tool_calls"]:
            if tool_call["name"] == "search_web":
                state["research_data"].append({
                    "query": tool_call["args"]["query"],
                    "timestamp": datetime.now().isoformat()
                })

    return response

agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    pre_model_hook=pre_model_hook_with_memory,
    post_model_hook=post_model_hook_with_memory
)
```

### Memory Lifecycle

```python
# Session start
config = {"configurable": {"thread_id": "user_123"}}

# First interaction - empty memory
response1 = agent.invoke({
    "messages": [{"role": "user", "content": "My name is Alice"}],
    "user_id": "user_123",
    "user_preferences": {}
}, config=config)

# Second interaction - has memory
response2 = agent.invoke({
    "messages": [{"role": "user", "content": "What's my name?"}]
}, config=config)
# Response: "Your name is Alice"

# Access checkpoint history
history = checkpointer.list(config)
for checkpoint in history:
    print(checkpoint["state"])

# Clear memory for thread
checkpointer.delete(config)
```

### ATLAS Memory Architecture

```python
# atlas_memory.py

from langgraph.checkpoint.postgres import PostgresSaver
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from datetime import datetime

# ATLAS State Schema
class ATLASState(TypedDict):
    # Core conversation
    messages: Annotated[list[BaseMessage], "Conversation history"]

    # Session context
    session_id: str
    user_id: str
    project_name: str

    # Agent state
    current_agent: str
    iteration_count: int

    # Research data
    research_findings: list[dict]
    sources: list[str]

    # Analysis data
    analysis_results: list[dict]
    data_files: list[str]

    # Writing progress
    drafts: list[dict]
    final_outputs: list[str]

    # User preferences
    output_format: str
    detail_level: str
    style_preferences: dict

# Initialize checkpointer
atlas_checkpointer = PostgresSaver.from_conn_string(
    "postgresql://atlas:atlas@localhost:5432/atlas_main"
)
atlas_checkpointer.setup()

def create_atlas_memory_config(session_id: str, user_id: str):
    """Create memory configuration for ATLAS session."""
    return {
        "configurable": {
            "thread_id": f"{user_id}_{session_id}",
            "checkpoint_ns": "atlas"
        }
    }

def initialize_atlas_state(session_id: str, user_id: str, project_name: str) -> ATLASState:
    """Initialize ATLAS state for new session."""
    return {
        "messages": [],
        "session_id": session_id,
        "user_id": user_id,
        "project_name": project_name,
        "current_agent": "supervisor",
        "iteration_count": 0,
        "research_findings": [],
        "sources": [],
        "analysis_results": [],
        "data_files": [],
        "drafts": [],
        "final_outputs": [],
        "output_format": "markdown",
        "detail_level": "comprehensive",
        "style_preferences": {}
    }

# Memory management for ATLAS
def atlas_memory_manager(state: ATLASState) -> ATLASState:
    """Manage ATLAS memory - trim, summarize, or maintain full history."""
    messages = state["messages"]

    # Trim if too large
    if len(messages) > 50:
        # Keep system message, summary, and recent messages
        system_msg = messages[0]
        recent = messages[-20:]

        # Summarize middle messages
        middle = messages[1:-20]
        summary = create_conversation_summary(middle)

        state["messages"] = [
            system_msg,
            {"role": "system", "content": f"Previous conversation: {summary}"},
            *recent
        ]

    return state
```

---

## Streaming

### Overview

Streaming enables real-time updates during LLM and agent interactions, improving user experience by showing progressive output. LangChain v1.0 supports multiple streaming modes for different use cases.

### Streaming Modes

#### 1. Agent Progress (`stream_mode="updates"`)

Emits events after each agent step:

```python
agent = create_agent(
    model="openai:gpt-4o",
    tools=[search_web, calculate]
)

# Stream agent progress
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Search for AI news and calculate 15 * 23"}]},
    stream_mode="updates"
):
    print(chunk)

# Output:
# {'llm': {'messages': [AIMessage(content='I will search and calculate')]}}
# {'tools': {'messages': [ToolMessage(content='News: ...', tool_call_id='1')]}}
# {'tools': {'messages': [ToolMessage(content='345', tool_call_id='2')]}}
# {'llm': {'messages': [AIMessage(content='Here are the results...')]}}
```

#### 2. LLM Tokens (`stream_mode="messages"`)

Streams individual tokens as generated:

```python
# Stream tokens
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Write a short poem"}]},
    stream_mode="messages"
):
    # Each chunk is a message or token
    if hasattr(chunk, "content"):
        print(chunk.content, end="", flush=True)
```

#### 3. Custom Updates (`stream_mode="custom"`)

Emit arbitrary data from tools:

```python
from langgraph.prebuilt import get_stream_writer

@tool
def long_running_task(query: str) -> str:
    """Task that sends progress updates."""
    writer = get_stream_writer()

    # Send custom progress updates
    writer({"status": "starting", "progress": 0})

    for i in range(5):
        time.sleep(1)
        writer({"status": "processing", "progress": (i + 1) * 20})

    writer({"status": "complete", "progress": 100})
    return "Task complete"

# Stream custom updates
for mode, chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Run long task"}]},
    stream_mode="custom"
):
    print(f"Progress: {chunk['progress']}%")
```

#### 4. Multiple Modes

Stream multiple modes simultaneously:

```python
# Stream both progress and custom updates
for mode, chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Complex task"}]},
    stream_mode=["updates", "custom", "messages"]
):
    if mode == "updates":
        print(f"Agent step: {chunk}")
    elif mode == "custom":
        print(f"Custom: {chunk}")
    elif mode == "messages":
        print(chunk.content, end="", flush=True)
```

### Streaming Model Responses

#### Basic Token Streaming

```python
from langchain.chat_models import init_chat_model

model = init_chat_model("openai:gpt-4o")

# Stream tokens
for chunk in model.stream("Write a story about AI"):
    print(chunk.content, end="", flush=True)
```

#### Async Streaming

```python
import asyncio

async def stream_async():
    async for chunk in model.astream("Write a poem"):
        print(chunk.content, end="", flush=True)

asyncio.run(stream_async())
```

#### Stream with Tool Calls

```python
model_with_tools = model.bind_tools([search_web])

for chunk in model_with_tools.stream("Search for news"):
    # Stream may include tool calls
    if chunk.content:
        print(chunk.content, end="", flush=True)
    if chunk.tool_calls:
        print(f"\nTool call: {chunk.tool_calls}")
```

### Streaming Agent Execution

#### Stream Complete Agent Run

```python
agent = create_agent(
    model="openai:gpt-4o",
    tools=[search_web, calculate]
)

# Stream all agent activity
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Research and calculate"}]},
    stream_mode="updates"
):
    node = list(chunk.keys())[0]
    data = chunk[node]

    if node == "llm":
        print(f"LLM: {data['messages'][-1].content}")
    elif node == "tools":
        print(f"Tool result: {data['messages'][-1].content}")
```

#### Stream with Interrupts

```python
agent = create_agent(
    model="openai:gpt-4o",
    tools=[search_web],
    interrupt_before=["tools"]
)

# Stream until interrupt
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Search the web"}]},
    stream_mode="updates"
):
    print(chunk)

    # Check for interrupt
    if "interrupt" in chunk:
        print("Paused for approval")
        break
```

### Event Handling

#### Custom Event Handlers

```python
from langchain.callbacks import StreamingStdOutCallbackHandler

class CustomStreamHandler(StreamingStdOutCallbackHandler):
    def on_llm_start(self, *args, **kwargs):
        print("LLM started")

    def on_llm_new_token(self, token: str, **kwargs):
        print(token, end="", flush=True)

    def on_llm_end(self, *args, **kwargs):
        print("\nLLM finished")

    def on_tool_start(self, tool, *args, **kwargs):
        print(f"\nTool started: {tool['name']}")

    def on_tool_end(self, output, **kwargs):
        print(f"Tool finished: {output}")

# Use handler
agent = create_agent(
    model="openai:gpt-4o",
    tools=[search_web],
    callbacks=[CustomStreamHandler()]
)
```

#### Async Event Handlers

```python
from langchain.callbacks import AsyncCallbackHandler

class AsyncStreamHandler(AsyncCallbackHandler):
    async def on_llm_new_token(self, token: str, **kwargs):
        await websocket.send(token)

    async def on_tool_start(self, tool, *args, **kwargs):
        await websocket.send(json.dumps({
            "type": "tool_start",
            "tool": tool["name"]
        }))

# Use async handler
agent = create_agent(
    model="openai:gpt-4o",
    tools=[search_web],
    callbacks=[AsyncStreamHandler()]
)
```

### Streaming Configuration

#### Disable Streaming

```python
# Disable streaming for specific models
agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    stream=False  # Disable streaming
)
```

#### Stream Timeout

```python
# Set timeout for streaming
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Task"}]},
    stream_mode="updates",
    timeout=30  # 30 second timeout
):
    print(chunk)
```

### ATLAS Streaming Patterns

```python
# atlas_streaming.py

from typing import AsyncGenerator, Generator
import json
from datetime import datetime

def stream_atlas_agent(
    agent,
    user_input: str,
    session_id: str,
    config: dict
) -> Generator:
    """Stream ATLAS agent execution with structured events."""

    # Emit start event
    yield {
        "type": "task_started",
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Stream agent execution
    for mode, chunk in agent.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        config=config,
        stream_mode=["updates", "custom"]
    ):
        if mode == "updates":
            node = list(chunk.keys())[0]
            data = chunk[node]

            if node == "llm":
                yield {
                    "type": "agent_thinking",
                    "content": data["messages"][-1].content,
                    "timestamp": datetime.utcnow().isoformat()
                }
            elif node == "tools":
                yield {
                    "type": "tool_execution",
                    "tool": data["messages"][-1].name,
                    "result": data["messages"][-1].content,
                    "timestamp": datetime.utcnow().isoformat()
                }

        elif mode == "custom":
            yield {
                "type": "custom_update",
                "data": chunk,
                "timestamp": datetime.utcnow().isoformat()
            }

    # Emit completion
    yield {
        "type": "task_completed",
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat()
    }

async def stream_atlas_agent_async(
    agent,
    user_input: str,
    session_id: str,
    config: dict
) -> AsyncGenerator:
    """Async stream ATLAS agent execution."""

    yield {
        "type": "task_started",
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    async for mode, chunk in agent.astream(
        {"messages": [{"role": "user", "content": user_input}]},
        config=config,
        stream_mode=["updates", "custom"]
    ):
        if mode == "updates":
            node = list(chunk.keys())[0]
            data = chunk[node]

            yield {
                "type": f"agent_{node}",
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }

        elif mode == "custom":
            yield {
                "type": "custom_update",
                "data": chunk,
                "timestamp": datetime.utcnow().isoformat()
            }

    yield {
        "type": "task_completed",
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat()
    }

# FastAPI endpoint example
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.post("/agent/stream")
async def stream_agent(user_input: str, session_id: str):
    """Stream agent execution to client."""

    async def event_generator():
        async for event in stream_atlas_agent_async(
            agent=atlas_agent,
            user_input=user_input,
            session_id=session_id,
            config={"configurable": {"thread_id": session_id}}
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

# Frontend integration (JavaScript)
"""
const eventSource = new EventSource('/agent/stream?user_input=task&session_id=123');

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'agent_thinking') {
        updateThinkingDisplay(data.content);
    } else if (data.type === 'tool_execution') {
        updateToolDisplay(data.tool, data.result);
    } else if (data.type === 'task_completed') {
        eventSource.close();
        showCompletion();
    }
};
"""
```

---

## Migration Considerations

### v0.x to v1.0 Migration

#### Import Changes

```python
# OLD (v0.x)
from langchain import LLMChain
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory

# NEW (v1.0)
from langchain_legacy import LLMChain  # Legacy compatibility
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
```

#### Agent Creation

```python
# OLD (v0.x)
from langchain.agents import initialize_agent, AgentType

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    memory=memory,
    verbose=True
)

# NEW (v1.0)
from langchain.agents import create_agent

agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    checkpointer=MemorySaver()
)
```

#### Message Access

```python
# OLD (v0.x)
response = model.invoke("Hello")
text = response.text()  # Method call

# NEW (v1.0)
response = model.invoke("Hello")
text = response.text  # Property access
text = response.content  # Preferred
```

#### Memory Management

```python
# OLD (v0.x)
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory()
agent = initialize_agent(tools, llm, memory=memory)

# NEW (v1.0)
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
agent = create_agent(model="openai:gpt-4o", tools=tools, checkpointer=checkpointer)
```

### Breaking Changes Checklist

- [ ] Update Python version to 3.10+
- [ ] Replace `langchain` imports with `langchain-legacy` where needed
- [ ] Update agent initialization to use `create_agent`
- [ ] Replace memory classes with checkpointers
- [ ] Update `.text()` method calls to `.content` property
- [ ] Install provider-specific packages separately
- [ ] Update structured output to use `response_format`
- [ ] Replace callback handlers with streaming modes

### Testing Migration

```python
# Create compatibility layer for gradual migration
def create_agent_v0_compatible(tools, llm, **kwargs):
    """Wrapper to support v0.x agent creation pattern."""
    # Map v0.x parameters to v1.0
    model = llm  # Assuming llm is already a chat model
    checkpointer = None

    if "memory" in kwargs:
        checkpointer = MemorySaver()

    return create_agent(
        model=model,
        tools=tools,
        checkpointer=checkpointer
    )

# Use wrapper during migration
agent = create_agent_v0_compatible(tools, llm, memory=memory)
```

---

## Best Practices for ATLAS

### 1. Model Selection Strategy

```python
# Use fast models for simple tasks
supervisor_quick_check = init_chat_model("groq:llama-3.3-70b-versatile")

# Use smart models for complex reasoning
research_deep_analysis = init_chat_model("openai:gpt-4o")

# Use balanced models for general work
writing_balanced = init_chat_model("anthropic:claude-3-7-sonnet-latest")
```

### 2. Tool Organization

```python
# Organize tools by agent type
RESEARCH_TOOLS = [
    atlas_web_search,
    atlas_academic_search,
    atlas_file_operations
]

ANALYSIS_TOOLS = [
    atlas_statistical_analysis,
    atlas_data_visualization,
    atlas_file_operations
]

WRITING_TOOLS = [
    atlas_content_generation,
    atlas_formatting,
    atlas_file_operations
]

# Shared tools across all agents
COMMON_TOOLS = [atlas_file_operations, atlas_memory_access]
```

### 3. Memory Architecture

```python
# PostgreSQL for production
production_checkpointer = PostgresSaver.from_conn_string(
    "postgresql://atlas:atlas@localhost:5432/atlas_main"
)

# In-memory for development/testing
dev_checkpointer = MemorySaver()

# Use appropriate checkpointer based on environment
checkpointer = production_checkpointer if ENV == "production" else dev_checkpointer
```

### 4. Error Handling

```python
# Comprehensive error handling in tools
@tool
def atlas_operation(param: str) -> str:
    """Perform ATLAS operation with error handling."""
    try:
        result = perform_operation(param)
        return json.dumps({"success": True, "result": result})
    except SpecificError as e:
        logger.error(f"Specific error: {e}")
        return json.dumps({"success": False, "error": str(e)})
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return json.dumps({"success": False, "error": "Internal error"})
```

### 5. Streaming for UX

```python
# Always stream for user-facing interactions
async def handle_user_request(user_input: str, session_id: str):
    """Stream ATLAS response to user."""
    async for event in stream_atlas_agent_async(
        agent=supervisor,
        user_input=user_input,
        session_id=session_id,
        config=create_atlas_memory_config(session_id, user_id)
    ):
        await websocket.send_json(event)
```

### 6. State Management

```python
# Define clear state schema
class ATLASState(TypedDict):
    messages: list[BaseMessage]
    session_id: str
    user_id: str
    project_name: str
    current_phase: Literal["research", "analysis", "writing", "review"]
    research_data: list[dict]
    analysis_results: list[dict]
    draft_content: list[str]
```

### 7. Agent Coordination

```python
# Supervisor delegates to specialized agents
@tool
def delegate_to_research(task: str) -> str:
    """Delegate to research agent."""
    config = create_atlas_memory_config(session_id, user_id)
    response = research_agent.invoke(
        {"messages": [{"role": "user", "content": task}]},
        config=config
    )
    return response["messages"][-1].content
```

### 8. Observability

```python
# Track all agent operations
def post_model_hook_tracking(state: dict, response: dict) -> dict:
    """Track agent operations in MLflow."""
    mlflow.log_metric("iteration_count", state.get("iteration_count", 0))
    mlflow.log_param("current_agent", state.get("current_agent"))

    if response.get("tool_calls"):
        for tool_call in response["tool_calls"]:
            mlflow.log_param(f"tool_{tool_call['name']}", tool_call["args"])

    return response
```

### 9. Testing

```python
# Test agents with mock tools
@tool
def mock_search(query: str) -> str:
    """Mock search for testing."""
    return json.dumps({"results": ["result1", "result2"]})

test_agent = create_agent(
    model="openai:gpt-4o-mini",  # Use cheaper model for testing
    tools=[mock_search],
    checkpointer=MemorySaver()  # Use in-memory for tests
)

def test_research_flow():
    response = test_agent.invoke({
        "messages": [{"role": "user", "content": "Search for AI trends"}]
    })
    assert len(response["messages"]) > 0
```

### 10. Cost Optimization

```python
# Route to appropriate model based on task complexity
def select_cost_optimal_model(task: str) -> str:
    """Select model based on cost and task complexity."""

    # Simple tasks -> fast/cheap model
    if len(task) < 100 and not any(word in task.lower() for word in ["complex", "analyze", "detailed"]):
        return "groq:llama-3.3-70b-versatile"  # $0.04/$0.08 per 1M tokens

    # Complex tasks -> powerful model
    elif any(word in task.lower() for word in ["analyze", "research", "detailed"]):
        return "openai:gpt-4o"  # $2.50/$10 per 1M tokens

    # Balanced tasks -> mid-tier model
    else:
        return "anthropic:claude-3-7-sonnet-latest"  # $3/$15 per 1M tokens
```

---

## Summary

LangChain v1.0 represents a significant evolution focused on:
- **Modularity**: Separate provider packages
- **Production Readiness**: Better error handling, streaming, memory management
- **Developer Experience**: Simplified APIs, better documentation
- **Performance**: Async support, parallel execution, optimized checkpointing

**Key Takeaways for ATLAS**:
1. Use `create_agent` for all agent creation
2. Implement proper checkpointing with PostgreSQL
3. Leverage streaming for real-time UX
4. Organize tools by agent specialization
5. Use appropriate models for different tasks
6. Implement comprehensive error handling
7. Track all operations with MLflow
8. Test with cheaper models and mock tools
9. Optimize costs with smart model routing
10. Maintain clean state management

**Next Steps**:
1. Update ATLAS dependencies to LangChain v1.0
2. Migrate existing agents to new API
3. Implement PostgreSQL checkpointing
4. Add streaming support to all endpoints
5. Create comprehensive test suite
6. Document migration process

---

**Document Version**: 1.0
**Last Updated**: 2025-10-01
**Status**: Complete - Ready for implementation
**Reviewed By**: Claude Code (LangChain/LangGraph Engineer)
