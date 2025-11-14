# Groq Function Calling Issues - Research Report

Based on comprehensive research into Groq's function calling implementation and common issues in 2025, here's a detailed analysis relevant to the ATLAS project:

## Key Findings

### 1. **Official Groq Support for Function/Tool Calling**

Groq officially supports tool use (function calling) with the following capabilities:

**Supported Models (as of 2025):**
- ✅ `moonshotai/kimi-k2-instruct-0905` - Supports parallel tool use
- ✅ `llama-3.3-70b-versatile` - Supports parallel tool use (RECOMMENDED)
- ✅ `llama-3.1-8b-instant` - Supports parallel tool use
- ✅ `qwen/qwen3-32b` - Supports parallel tool use
- ⚠️ `openai/gpt-oss-20b` and `openai/gpt-oss-120b` - Tool use supported, but NO parallel tool use

**Tool Call Structure:**
```python
tools = [{
    "type": "function",
    "function": {
        "name": "tool_name",
        "description": "Clear description of what tool does",
        "parameters": {
            "type": "object",
            "properties": {
                "param_name": {
                    "type": "string",
                    "description": "Parameter description"
                }
            },
            "required": ["param_name"]
        }
    }
}]
```

### 2. **Common Groq Function Calling Issues**

#### **Issue #1: JSON Parsing Failures (Most Common)**
**Symptom:** "Failed to parse tool call arguments as JSON"

**Root Causes:**
- Model outputs explanatory text before JSON (e.g., "sure here's your json object")
- Model-specific behavior - Mixtral 8x7b and Gemma2-9b-It particularly problematic
- Token length > 2000 increases failure rates

**Solutions:**
```python
# ✅ Use recommended models
model = "llama-3.3-70b-versatile"  # Most reliable

# ✅ Keep token counts under 2000 for consistency
max_tokens = 1500

# ✅ Add explicit JSON formatting instructions
system_prompt = """You are a helpful assistant.
When calling tools, respond ONLY with the JSON tool call, no explanatory text."""
```

#### **Issue #2: Tool Choice Limitations**
**Symptom:** "Groq does not currently support tool_choice='any'"

**Root Cause:** Groq only supports: `"auto"`, `"none"`, or specific tool name

**Solution:**
```python
# ❌ Don't use
tool_choice = "any"  # Not supported

# ✅ Use instead
tool_choice = "auto"  # Let model decide
tool_choice = "get_weather"  # Force specific tool
tool_choice = "none"  # No tools
```

#### **Issue #3: Structured Output Failures**
**Symptom:** RuntimeError with "Failed to call a function. Please adjust your prompt"

**Root Causes:**
- Context length exceeds optimal range (>2000 tokens)
- Tool descriptions too vague or ambiguous
- Schema validation mismatches

**Solutions:**
```python
# ✅ Use Instructor library for validation
import instructor
from pydantic import BaseModel

client = instructor.from_groq(Groq(), mode=instructor.Mode.JSON)

class ToolCall(BaseModel):
    tool_name: str
    parameters: dict

# This provides automatic validation
```

#### **Issue #4: tool_use_failed Errors**
**Symptom:** 400 error with "tool_use_failed" in response

**Root Cause:** Model generates invalid tool call object

**Groq's Behavior:** Returns detailed error in "failed_generation" field

**Solution:**
```python
try:
    response = client.chat.completions.create(...)
except Exception as e:
    if "tool_use_failed" in str(e):
        # Check e.response.json()["failed_generation"] for details
        logger.error(f"Tool use validation failed: {e}")
```

### 3. **ATLAS-Specific Considerations**

#### **Current ATLAS Implementation Analysis:**

Looking at `/Users/nicholaspate/Documents/01_Active/ATLAS/backend/src/utils/call_model.py`:

**Current Groq Implementation (Lines 751-829):**
```python
async def call_groq_direct(self, request: ModelRequest) -> ModelResponse:
    # ✅ Good: Basic message structure
    # ⚠️ Missing: No tool/function calling support
    # ⚠️ Missing: No structured output handling
    # ⚠️ Missing: No error handling for tool_use_failed
```

**Recommendations for ATLAS:**

1. **Add Tool Calling Support to CallModel:**
```python
async def call_groq_direct(self, request: ModelRequest, tools: Optional[List[Dict]] = None) -> ModelResponse:
    """Enhanced Groq call with tool support."""

    # Build API parameters
    call_params = {
        "model": request.model_name,
        "messages": messages,
        "max_tokens": min(request.max_tokens or 1000, 1500),  # Keep under 2000 for reliability
        "temperature": request.temperature or 0.7,
    }

    # Add tools if provided
    if tools:
        call_params["tools"] = tools
        call_params["tool_choice"] = "auto"  # Only use auto/none/tool_name

    try:
        response = client.chat.completions.create(**call_params)

        # Check for tool calls in response
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            # Handle tool calls
            return ModelResponse(
                success=True,
                content=None,  # No text content when tool called
                tool_calls=response.choices[0].message.tool_calls,
                # ... rest of response
            )
    except Exception as e:
        # Enhanced error handling for Groq-specific errors
        if "tool_use_failed" in str(e):
            logger.error(f"Groq tool validation failed: {e}")
            # Parse failed_generation field if available
```

2. **Use Recommended Models:**
```python
# In openrouter_config.py or model_config.py
GROQ_RECOMMENDED_MODELS = [
    "llama-3.3-70b-versatile",  # Best for tool calling
    "llama-3.1-8b-instant",     # Fast alternative
    "qwen/qwen3-32b"           # Alternative option
]
```

3. **Best Practices for ATLAS Agents:**

```python
# When creating supervisor agents with tool calling:
class SupervisorAgent:
    def __init__(self):
        # Use recommended model
        self.model = "llama-3.3-70b-versatile"

        # Optimize token usage
        self.max_tokens = 1500  # Stay under 2000

        # Clear tool descriptions
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "delegate_research",
                    "description": "Delegates a research task to the research agent. Use when you need to gather information from the web.",  # Be specific
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The specific research question or topic to investigate"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
```

4. **Error Handling Strategy:**
```python
async def call_with_fallback(self, request: ModelRequest, tools: Optional[List[Dict]] = None):
    """Groq call with automatic fallback if tool calling fails."""

    try:
        # Try with tools
        return await self.call_groq_direct(request, tools=tools)
    except Exception as e:
        if "tool_use_failed" in str(e) or "Failed to parse" in str(e):
            logger.warning(f"Groq tool calling failed, retrying without tools: {e}")
            # Retry without tools - let agent respond naturally
            return await self.call_groq_direct(request, tools=None)
        raise
```

### 4. **Performance Characteristics**

**Groq's Strengths:**
- ⚡ **Fastest inference** (0.2s avg vs 0.8s Anthropic, 4.0s OpenAI)
- 💰 **Cost-effective** for high-volume tool calling
- ✅ **Parallel tool use** supported on recommended models

**Groq's Limitations:**
- ⚠️ **Token length sensitivity** (>2000 tokens = higher failure rate)
- ⚠️ **Model-specific quirks** (some models add explanatory text)
- ⚠️ **Less forgiving** than OpenAI/Anthropic for ambiguous tool descriptions

### 5. **Recommended Implementation Path for ATLAS**

1. **Update `call_model.py`** to add tool calling support to `call_groq_direct()`
2. **Use `llama-3.3-70b-versatile`** as primary Groq model for agents
3. **Add Instructor library** for structured output validation
4. **Implement fallback strategy** when tool calling fails
5. **Keep prompts concise** - optimize for <2000 tokens when using tools
6. **Add comprehensive error handling** for Groq-specific errors

## Summary

Groq's function calling is **production-ready** for ATLAS, but requires:
- ✅ Using recommended models (`llama-3.3-70b-versatile`)
- ✅ Proper error handling for JSON parsing failures
- ✅ Token optimization (<2000 for reliability)
- ✅ Clear, specific tool descriptions
- ✅ Fallback strategies for when tool calling fails

The combination of Groq's speed with proper implementation patterns makes it an excellent choice for ATLAS's multi-agent architecture, especially for the supervisor agent's tool delegation workflow.
