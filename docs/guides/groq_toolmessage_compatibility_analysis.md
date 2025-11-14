# Groq API ToolMessage Compatibility Analysis

**Research Date:** 2025-01-10
**Focus:** ToolMessage content format requirements for Groq API compatibility
**Error:** `'messages.X.content' : one of the following must be satisfied[('messages.X.content' : value must be a string) OR ('messages.X.content' : minimum number of items is 1)]`

---

## Executive Summary

**Root Cause Identified:** Groq API requires ToolMessage `content` field to be a **non-empty string**. Empty strings, None values, or missing content will trigger validation errors.

**Key Findings:**
1. Groq follows OpenAI message format standards
2. Tool messages MUST have `role: "tool"`, `tool_call_id`, and non-empty `content` as string
3. The error indicates ToolMessage content is either empty, None, or improperly formatted
4. LangChain Command pattern requires careful handling of ToolMessage content extraction

---

## Part 1: Groq API Requirements

### 1.1 Official Tool Message Format

Source: https://console.groq.com/docs/tool-use

**Required Fields:**
```json
{
  "role": "tool",
  "tool_call_id": "call_d5wg",
  "name": "get_weather",
  "content": "22°C, Sunny"
}
```

**Field Requirements:**
- `role`: MUST be `"tool"`
- `tool_call_id`: String matching the ID from assistant's tool call
- `name`: Tool/function name (optional in some implementations)
- `content`: **MUST be a non-empty string**

### 1.2 Content Validation Rules

Based on Groq API error messages and community discussions:

**Valid Content:**
```python
# ✅ Valid - String with content
ToolMessage(content="Results found", tool_call_id="call_123")

# ✅ Valid - JSON string
ToolMessage(content='{"status": "success"}', tool_call_id="call_123")

# ✅ Valid - Error message string
ToolMessage(content="Error: File not found", tool_call_id="call_123")
```

**Invalid Content:**
```python
# ❌ Invalid - Empty string
ToolMessage(content="", tool_call_id="call_123")

# ❌ Invalid - None
ToolMessage(content=None, tool_call_id="call_123")

# ❌ Invalid - Missing content
ToolMessage(tool_call_id="call_123")

# ❌ Invalid - Object/Dict (not serialized)
ToolMessage(content={"status": "success"}, tool_call_id="call_123")

# ❌ Invalid - List
ToolMessage(content=["result1", "result2"], tool_call_id="call_123")
```

### 1.3 Error Message Breakdown

**Error Pattern:**
```
'messages.X' : for 'role:tool' the following must be satisfied[
  ('messages.X.content' : one of the following must be satisfied[
    ('messages.X.content' : value must be a string) OR
    ('messages.X.content' : minimum number of items is 1)
  ])
]
```

**Translation:**
- Groq expects `content` to be either:
  1. A non-empty string, OR
  2. An array with at least 1 item (multi-modal content blocks)

**Why This Error Occurs:**
- Content field is empty string: `content=""`
- Content field is None: `content=None`
- Content field is missing entirely
- Content is not properly converted to string

---

## Part 2: Current Implementation Analysis

### 2.1 File: `/backend/src/tools/submit_tool.py`

**Lines 184-192: Content Extraction**
```python
reviewer_messages = reviewer_result.get("messages", [])

# Extract content from reviewer's last message (following task tool pattern)
reviewer_response_content = ""
if reviewer_messages:
    last_msg = reviewer_messages[-1]
    reviewer_response_content = getattr(last_msg, 'content', '')
    logger.info(f"📤 Extracted reviewer response: {reviewer_response_content[:100]}...")
else:
    reviewer_response_content = "⚠️  REVIEW INCOMPLETE - Reviewer did not return any messages"
    logger.warning("⚠️  Reviewer returned no messages!")
```

**Issue:** If `last_msg.content` is an empty string, the ToolMessage will be created with empty content.

**Lines 202-212: ToolMessage Creation**
```python
return Command(
    update={
        **state_update,  # Propagate review_status, review_feedback, todos, etc.
        "messages": [
            ToolMessage(
                content=reviewer_response_content,  # ❌ Could be empty string!
                tool_call_id=tool_call_id
            )
        ]
    }
)
```

**Problem:** `reviewer_response_content` may be empty string if:
1. Reviewer's last message has no content
2. Reviewer's last message is malformed
3. Content extraction fails

### 2.2 File: `/backend/src/tools/reviewer_tools.py`

**Lines 99-110: reject_submission Tool**
```python
return Command(
    update={
        "review_status": "REJECTED",
        "review_feedback": feedback,
        "todos": todos,
        "messages": [
            ToolMessage(
                content=f"❌ SUBMISSION REJECTED\n\n{feedback}",
                tool_call_id=tool_call_id
            )
        ]
    }
)
```

**Status:** ✅ This is correct - content always has a non-empty string.

**Lines 142-153: accept_submission Tool**
```python
return Command(
    update={
        "review_status": "ACCEPTED",
        "todos": todos,  # Propagate updated todos
        "messages": [
            ToolMessage(
                content="✅ SUBMISSION ACCEPTED - Task complete, supervisor notified",
                tool_call_id=tool_call_id
            )
        ]
    }
)
```

**Status:** ✅ This is correct - content always has a non-empty string.

### 2.3 File: `/backend/src/agents/supervisor_agent.py`

**Lines 138-144: Reviewer Agent Creation**
```python
reviewer_agent = async_create_deep_agent(
    tools=reviewer_config["tools"],
    instructions=reviewer_config["prompt"],
    model=reviewer_config["model"],
    subagents=[],  # Reviewer has no sub-agents
)
set_reviewer_agent(reviewer_agent)
```

**Status:** ✅ Configuration looks correct.

---

## Part 3: Deep Agents Command Pattern Analysis

### 3.1 Deep Agents Task Tool Pattern

Source: `/docs/langchain-deep-agents-research/01_deep_agents_implementation.md` (lines 456-553)

**Standard Pattern for Tool Returning Command:**

From middleware deep dive documentation (lines 798-823):

```python
# Pattern 1: Structured Output
sub_agent = create_deep_agent(
    tools=tools,
    instructions=instructions,
    middleware=[
        StructuredOutputMiddleware(output_schema=ResultSchema)
    ]
)

# Main agent extracts structured data
result = sub_agent.invoke({"messages": [{"role": "user", "content": task}]})
structured_data = result["structured_output"]

# Pattern 2: File-Based Exchange
result = sub_agent.invoke({
    "messages": [{"role": "user", "content": "Research topic and save to findings.md"}]
})

findings = result["files"]["findings.md"]
main_agent_state["research_data"].append(findings)
```

**Key Insight:** Deep Agents expects message content to be extracted from sub-agent's last message.

### 3.2 Message Content Extraction Best Practices

From middleware research (lines 968-970):

```python
# Validate message structure
if hasattr(last_message, "content"):
    extracted_content = last_message.content
elif isinstance(last_message, dict):
    extracted_content = last_message.get("content", "")
else:
    raise ValueError(f"Unexpected message type: {type(last_message)}")
```

**Issue in Current Code:** The fallback `""` for missing content violates Groq's requirement.

### 3.3 Command Return Type Pattern

From LangChain v1 documentation (lines 356-367 in `02_langchain_v1_core_components.md`):

**Context Engineering - Update Session Context in Tools:**
```python
from langgraph.types import Command

def update_tool(value: str):
    """Tool that updates state."""
    return Command(update={"custom_field": value})

agent = create_agent(
    model="openai:gpt-4o",
    tools=[update_tool]
)
```

**Important:** Command tools can return state updates, but ToolMessage creation is handled by the framework UNLESS explicitly provided.

---

## Part 4: Root Cause Analysis

### 4.1 The Problem Chain

**Scenario Leading to Empty Content:**

1. **Sub-agent (reviewer) executes** and completes task
2. **Last message from reviewer** is extracted:
   ```python
   last_msg = reviewer_messages[-1]
   reviewer_response_content = getattr(last_msg, 'content', '')
   ```
3. **Issue:** If reviewer's tools (`accept_submission`, `reject_submission`) were the last action, the last message might be:
   - An AIMessage with empty content (only tool calls)
   - A ToolMessage from the reviewer's own tool execution
   - A message object without content attribute

4. **Result:** `reviewer_response_content = ""`

5. **ToolMessage created with empty content:**
   ```python
   ToolMessage(
       content="",  # ❌ EMPTY STRING
       tool_call_id=tool_call_id
   )
   ```

6. **Groq API rejects the message chain** with validation error

### 4.2 Why This Wasn't Caught Earlier

**Testing Gap:**
- Unit tests may have used mock responses with non-empty content
- Integration tests may not have tested the full reviewer → supervisor flow
- Groq API validation is stricter than other providers (OpenAI may accept empty content)

### 4.3 Comparison with Deep Agents Examples

From research files, the standard Deep Agents pattern for sub-agent invocation:

```python
# From research example (approximate pattern)
result = sub_agent.invoke({"messages": [{"role": "user", "content": task}]})

# Extract last message content
last_message_content = result["messages"][-1].content

# Use in parent context
return f"Sub-agent completed: {last_message_content}"
```

**Key Difference:** In ATLAS implementation, we're creating a ToolMessage ourselves, which requires more careful content validation.

---

## Part 5: Recommended Fixes

### 5.1 Fix 1: Add Content Validation (Recommended)

**Location:** `/backend/src/tools/submit_tool.py` lines 184-212

**Current Code:**
```python
reviewer_response_content = ""
if reviewer_messages:
    last_msg = reviewer_messages[-1]
    reviewer_response_content = getattr(last_msg, 'content', '')
    logger.info(f"📤 Extracted reviewer response: {reviewer_response_content[:100]}...")
else:
    reviewer_response_content = "⚠️  REVIEW INCOMPLETE - Reviewer did not return any messages"
    logger.warning("⚠️  Reviewer returned no messages!")
```

**Fixed Code:**
```python
reviewer_response_content = ""
if reviewer_messages:
    last_msg = reviewer_messages[-1]

    # Extract content with validation
    if hasattr(last_msg, 'content') and last_msg.content:
        reviewer_response_content = last_msg.content
    elif isinstance(last_msg, dict) and last_msg.get("content"):
        reviewer_response_content = last_msg["content"]
    else:
        # Fallback: Construct meaningful message from available data
        reviewer_response_content = "Review completed. Check review_status in state for details."

    logger.info(f"📤 Extracted reviewer response: {reviewer_response_content[:100]}...")
else:
    reviewer_response_content = "⚠️  REVIEW INCOMPLETE - Reviewer did not return any messages"
    logger.warning("⚠️  Reviewer returned no messages!")

# Additional validation before ToolMessage creation
if not reviewer_response_content or reviewer_response_content.strip() == "":
    reviewer_response_content = "Review completed. Status and feedback available in state."
    logger.warning("⚠️  Reviewer response content was empty, using fallback message")
```

**Why This Works:**
- Validates content is non-empty before using
- Provides meaningful fallback message
- Ensures Groq API validation passes
- Maintains state propagation through `state_update`

### 5.2 Fix 2: Enhanced Error Handling

**Location:** `/backend/src/tools/submit_tool.py` lines 214-225

**Current Code:**
```python
except Exception as e:
    logger.error(f"❌ Exception during review: {e}", exc_info=True)
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"ERROR during review: {str(e)}\n\nPlease contact supervisor for assistance.",
                    tool_call_id=tool_call_id
                )
            ]
        }
    )
```

**Enhanced Code:**
```python
except Exception as e:
    logger.error(f"❌ Exception during review: {e}", exc_info=True)

    # Ensure error message is non-empty string
    error_content = f"ERROR during review: {str(e)}\n\nPlease contact supervisor for assistance."
    if not error_content or error_content.strip() == "":
        error_content = "An unknown error occurred during review. Please contact supervisor."

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=error_content,
                    tool_call_id=tool_call_id
                )
            ]
        }
    )
```

### 5.3 Fix 3: Smarter Message Extraction

**Create helper function for robust message content extraction:**

```python
def extract_message_content(message, fallback: str = "No content available") -> str:
    """
    Safely extract content from a message object.

    Ensures returned content is always a non-empty string for Groq API compatibility.

    Args:
        message: Message object (AIMessage, ToolMessage, HumanMessage, dict, etc.)
        fallback: Fallback string if content is empty (must be non-empty)

    Returns:
        Non-empty string content
    """
    content = ""

    # Try attribute access
    if hasattr(message, 'content'):
        content = message.content
    # Try dict access
    elif isinstance(message, dict):
        content = message.get("content", "")
    # Try text property (some message types)
    elif hasattr(message, 'text'):
        content = message.text

    # Validate content is string
    if not isinstance(content, str):
        content = str(content) if content else ""

    # Ensure non-empty
    if not content or content.strip() == "":
        content = fallback
        logger.warning(f"Message content was empty, using fallback: {fallback[:50]}...")

    return content
```

**Usage:**
```python
reviewer_response_content = extract_message_content(
    last_msg,
    fallback="Review completed. Check state for review_status and review_feedback."
)
```

### 5.4 Fix 4: Alternative - Use State Fields

**Concept:** Instead of relying on message content, construct a message from state fields.

```python
# After reviewer invocation
review_status = reviewer_result.get("review_status", "UNKNOWN")
review_feedback = reviewer_result.get("review_feedback", "")

# Construct message from state
if review_status == "ACCEPTED":
    reviewer_response_content = "✅ SUBMISSION ACCEPTED - Task complete, supervisor notified"
elif review_status == "REJECTED":
    reviewer_response_content = f"❌ SUBMISSION REJECTED\n\n{review_feedback}"
else:
    # Fallback to last message content
    reviewer_response_content = extract_message_content(
        reviewer_messages[-1] if reviewer_messages else None,
        fallback="Review completed with unknown status"
    )
```

**Advantages:**
- More reliable - doesn't depend on message extraction
- State is the source of truth
- Clearer for debugging

**Disadvantages:**
- Slightly more code
- Duplicates logic from reviewer tools

---

## Part 6: Testing Recommendations

### 6.1 Unit Tests

**Test Case 1: Empty Content Handling**
```python
def test_submit_tool_empty_reviewer_content():
    """Test submit tool handles empty reviewer content"""

    # Mock reviewer returning empty content
    mock_reviewer_result = {
        "messages": [AIMessage(content="")],
        "review_status": "ACCEPTED",
        "review_feedback": ""
    }

    # Call submit tool
    result = await submit(
        supervisor_task="Test task",
        output_file="/workspace/test.txt",
        state=mock_state,
        tool_call_id="call_123"
    )

    # Verify ToolMessage has non-empty content
    tool_message = result.update["messages"][0]
    assert isinstance(tool_message, ToolMessage)
    assert tool_message.content != ""
    assert len(tool_message.content) > 0
```

**Test Case 2: None Content Handling**
```python
def test_submit_tool_none_reviewer_content():
    """Test submit tool handles None reviewer content"""

    # Mock reviewer returning None content
    mock_reviewer_result = {
        "messages": [AIMessage(content=None)],
        "review_status": "REJECTED",
        "review_feedback": "Issues found"
    }

    result = await submit(
        supervisor_task="Test task",
        output_file="/workspace/test.txt",
        state=mock_state,
        tool_call_id="call_123"
    )

    tool_message = result.update["messages"][0]
    assert tool_message.content is not None
    assert isinstance(tool_message.content, str)
    assert len(tool_message.content) > 0
```

**Test Case 3: Missing Messages**
```python
def test_submit_tool_no_reviewer_messages():
    """Test submit tool handles missing reviewer messages"""

    mock_reviewer_result = {
        "messages": [],
        "review_status": "UNKNOWN",
        "review_feedback": ""
    }

    result = await submit(
        supervisor_task="Test task",
        output_file="/workspace/test.txt",
        state=mock_state,
        tool_call_id="call_123"
    )

    tool_message = result.update["messages"][0]
    assert tool_message.content != ""
    assert "REVIEW INCOMPLETE" in tool_message.content or "Review completed" in tool_message.content
```

### 6.2 Integration Tests

**Test Case 4: Full Reviewer Flow**
```python
async def test_full_reviewer_flow_with_groq():
    """Test complete submit → reviewer → supervisor flow with Groq API"""

    # Create real supervisor agent with Groq
    supervisor = await create_supervisor_agent()

    # Run a task that triggers submission
    result = await supervisor.ainvoke({
        "messages": [{"role": "user", "content": "Complete a simple research task"}]
    })

    # Verify all ToolMessages have non-empty content
    for msg in result["messages"]:
        if isinstance(msg, ToolMessage):
            assert msg.content != ""
            assert len(msg.content) > 0
```

### 6.3 Groq API Validation Test

**Test Case 5: Direct Groq API Validation**
```python
from langchain_groq import ChatGroq

async def test_groq_toolmessage_validation():
    """Test ToolMessage content requirements with real Groq API"""

    model = ChatGroq(model="qwen/qwen3-32b")

    # Test 1: Valid non-empty content
    messages = [
        AIMessage(content="", tool_calls=[{
            "name": "test_tool",
            "args": {},
            "id": "call_123"
        }]),
        ToolMessage(content="Valid content", tool_call_id="call_123")
    ]

    try:
        response = await model.ainvoke(messages)
        assert response is not None  # Should succeed
    except Exception as e:
        pytest.fail(f"Valid ToolMessage failed: {e}")

    # Test 2: Invalid empty content (expected to fail)
    messages_empty = [
        AIMessage(content="", tool_calls=[{
            "name": "test_tool",
            "args": {},
            "id": "call_456"
        }]),
        ToolMessage(content="", tool_call_id="call_456")  # Empty content
    ]

    with pytest.raises(Exception) as exc_info:
        await model.ainvoke(messages_empty)

    assert "content" in str(exc_info.value).lower()
```

---

## Part 7: Prevention Strategies

### 7.1 Linting Rules

**Create custom linting rule for ToolMessage creation:**

```python
# pyproject.toml or .pylintrc
[tool.pylint.custom-rules]
# Enforce ToolMessage content validation
```

**Example Rule:**
```python
def check_toolmessage_content(node):
    """Ensure ToolMessage always has non-empty content"""
    if isinstance(node, ast.Call):
        if hasattr(node.func, 'id') and node.func.id == 'ToolMessage':
            # Check if content keyword arg exists and is non-empty
            for keyword in node.keywords:
                if keyword.arg == 'content':
                    if isinstance(keyword.value, ast.Constant) and keyword.value.value == "":
                        return "ToolMessage content cannot be empty string"
```

### 7.2 Type Hints

**Strengthen type hints for message content:**

```python
from typing import Literal

def create_tool_message(
    content: str,  # Not Optional[str]
    tool_call_id: str
) -> ToolMessage:
    """
    Create a ToolMessage with validated content.

    Args:
        content: Non-empty string content (required by Groq API)
        tool_call_id: Tool call identifier

    Raises:
        ValueError: If content is empty
    """
    if not content or content.strip() == "":
        raise ValueError("ToolMessage content cannot be empty for Groq API compatibility")

    return ToolMessage(content=content, tool_call_id=tool_call_id)
```

### 7.3 Message Content Validator

**Middleware to validate all ToolMessages before sending:**

```python
from langchain.agents.middleware import AgentMiddleware

class ToolMessageValidatorMiddleware(AgentMiddleware):
    """Validate ToolMessage content before sending to Groq API"""

    def after_model(self, state: AgentState) -> dict[str, Any] | None:
        """Check all ToolMessages have non-empty content"""
        messages = state.get("messages", [])

        for i, msg in enumerate(messages):
            if isinstance(msg, ToolMessage):
                if not msg.content or msg.content.strip() == "":
                    logger.error(f"⚠️  Empty ToolMessage at index {i}")
                    # Fix it
                    messages[i] = ToolMessage(
                        content="[No content provided]",
                        tool_call_id=msg.tool_call_id
                    )

        return {"messages": messages} if any(
            isinstance(m, ToolMessage) and not m.content
            for m in messages
        ) else None
```

---

## Part 8: References and Sources

### 8.1 Primary Sources

**Groq API Documentation:**
- URL: https://console.groq.com/docs/tool-use
- Title: "Introduction to Tool Use"
- Date: 2025 (current)
- Key Content: Tool message format requirements, role specifications

**Groq API Reference:**
- URL: https://console.groq.com/docs/api-reference
- Title: "API Reference"
- Date: 2025 (current)
- Key Content: Message validation rules, error codes

**Groq Community Discussion:**
- URL: https://community.groq.com/t/how-to-include-tool-call-arguments-in-messages-for-tool-call-responses/186
- Title: "How to include tool call arguments in messages for tool call responses?"
- Date: 2024-2025
- Key Content: Discussion of ToolMessage format, comparison with OpenAI/Anthropic

### 8.2 LangChain Documentation

**LangChain ToolMessage API:**
- URL: https://python.langchain.com/api_reference/core/messages/langchain_core.messages.tool.ToolMessage.html
- Title: "ToolMessage — LangChain documentation"
- Date: 2025
- Key Content: ToolMessage class definition, parameters

**LangChain Tool Error Handling:**
- URL: https://python.langchain.com/docs/how_to/tools_error/
- Title: "How to handle tool errors"
- Date: 2025
- Key Content: Best practices for tool error handling

**ChatGroq Integration:**
- URL: https://python.langchain.com/docs/integrations/chat/groq/
- Title: "ChatGroq | LangChain"
- Date: 2025
- Key Content: Groq-specific integration details

### 8.3 Deep Agents Research

**Files Analyzed:**
- `/docs/langchain-deep-agents-research/01_deep_agents.md`
- `/docs/langchain-deep-agents-research/01_deep_agents_implementation.md`
- `/docs/langchain-deep-agents-research/02_langchain_v1_core.md`
- `/docs/langchain-deep-agents-research/03_langchain_v1_advanced.md`
- `/docs/langchain-deep-agents-research/middleware-deep-dive.md`

**Key Patterns Extracted:**
- Command return type usage
- Message content extraction best practices
- Sub-agent invocation patterns
- State propagation through tools

### 8.4 Code Files Analyzed

**ATLAS Implementation:**
- `/backend/src/tools/submit_tool.py` (lines 1-226)
- `/backend/src/tools/reviewer_tools.py` (lines 1-154)
- `/backend/src/agents/supervisor_agent.py` (lines 1-236)

**Key Issues Found:**
- Line 188 in submit_tool.py: `reviewer_response_content = getattr(last_msg, 'content', '')`
- Line 207 in submit_tool.py: ToolMessage creation without content validation

---

## Part 9: Action Items

### 9.1 Immediate Fixes (Priority: Critical)

- [ ] **Fix 1:** Add content validation in `submit_tool.py` (lines 184-212)
  - Validate `reviewer_response_content` is non-empty before ToolMessage creation
  - Add fallback message for empty content
  - Log warnings when fallback is used

- [ ] **Fix 2:** Create `extract_message_content()` helper function
  - Place in `/backend/src/utils/message_utils.py`
  - Use throughout codebase for message content extraction
  - Include comprehensive docstring with examples

- [ ] **Fix 3:** Add unit tests for empty content handling
  - Test empty string content
  - Test None content
  - Test missing messages array
  - Test various message types

### 9.2 Short-Term Improvements (Priority: High)

- [ ] **Improvement 1:** Add `ToolMessageValidatorMiddleware`
  - Validate all ToolMessages before sending to Groq
  - Auto-fix empty content with meaningful defaults
  - Log validation issues for debugging

- [ ] **Improvement 2:** Enhance error messages in reviewer tools
  - Ensure all return paths have non-empty content
  - Add structured error information
  - Include context in error messages

- [ ] **Improvement 3:** Integration test with real Groq API
  - Test full submission → review → supervisor flow
  - Verify all ToolMessages pass Groq validation
  - Test error scenarios

### 9.3 Long-Term Enhancements (Priority: Medium)

- [ ] **Enhancement 1:** Type system improvements
  - Create `NonEmptyStr` type alias
  - Use in ToolMessage content parameters
  - Add mypy validation

- [ ] **Enhancement 2:** Documentation updates
  - Document Groq ToolMessage requirements in ATLAS docs
  - Add troubleshooting guide for message content errors
  - Create examples of correct ToolMessage usage

- [ ] **Enhancement 3:** Monitoring and alerting
  - Add metrics for ToolMessage validation failures
  - Set up alerts for repeated validation errors
  - Track error patterns for proactive fixes

---

## Part 10: Conclusion

### 10.1 Root Cause Summary

**The error occurs because:**
1. Reviewer agent's last message may have empty content
2. Content extraction uses fallback empty string: `getattr(last_msg, 'content', '')`
3. ToolMessage is created with this empty content
4. Groq API validates and rejects the empty content

### 10.2 Solution Summary

**Recommended Fix:**
Add validation before ToolMessage creation to ensure content is always a non-empty string. Use state fields (`review_status`, `review_feedback`) as fallback source of truth.

**Implementation Priority:**
1. **Immediate:** Add content validation in submit_tool.py
2. **Short-term:** Create helper function and add tests
3. **Long-term:** Add middleware validator and enhance type system

### 10.3 Key Learnings

**Groq API Requirements:**
- Stricter validation than some other providers
- Follows OpenAI message format standards
- ToolMessage content MUST be non-empty string

**LangChain Command Pattern:**
- Commands can return state updates with messages
- Message content must be explicitly managed
- Fallback values must be non-empty

**Deep Agents Best Practices:**
- Always validate message content extraction
- Use state fields as source of truth when available
- Provide meaningful fallback messages

### 10.4 Prevention

**Going Forward:**
1. Add linting rules for ToolMessage creation
2. Use type hints to enforce non-empty content
3. Implement validation middleware
4. Add comprehensive test coverage
5. Document provider-specific requirements

---

**Document Status:** Complete
**Next Steps:** Implement immediate fixes and validate with integration tests
**Owner:** ATLAS Development Team
**Review Date:** 2025-01-10

---

## Appendix A: Example Groq API Error Response

```json
{
  "error": {
    "message": "'messages.5' : for 'role:tool' the following must be satisfied[('messages.5.content' : one of the following must be satisfied[('messages.5.content' : value must be a string) OR ('messages.5.content' : minimum number of items is 1)])]",
    "type": "invalid_request_error",
    "code": 400
  }
}
```

**Interpretation:**
- Error at message index 5
- Message has `role: "tool"`
- Content validation failed
- Expected: non-empty string OR array with 1+ items
- Actual: empty string or None

## Appendix B: Correct ToolMessage Patterns

**Pattern 1: Simple String Content**
```python
ToolMessage(
    content="Operation completed successfully",
    tool_call_id="call_abc123"
)
```

**Pattern 2: JSON String Content**
```python
import json

result_data = {"status": "success", "count": 42}
ToolMessage(
    content=json.dumps(result_data),
    tool_call_id="call_def456"
)
```

**Pattern 3: Error Message Content**
```python
ToolMessage(
    content="Error: File not found at specified path",
    tool_call_id="call_ghi789"
)
```

**Pattern 4: Fallback Content**
```python
content = extracted_content if extracted_content else "No content available"
ToolMessage(
    content=content,
    tool_call_id="call_jkl012"
)
```

## Appendix C: Message Content Extraction Patterns

**From Deep Agents Documentation:**

```python
# Pattern 1: Attribute access with validation
if hasattr(message, 'content') and message.content:
    content = message.content
else:
    content = "Default content"

# Pattern 2: Dict access with validation
if isinstance(message, dict):
    content = message.get("content", "Default content")
else:
    content = "Default content"

# Pattern 3: Multiple fallbacks
content = (
    getattr(message, 'content', None) or
    message.get('content') if isinstance(message, dict) else None or
    "Default content"
)

# Pattern 4: Type checking
if isinstance(message, (AIMessage, HumanMessage, ToolMessage)):
    content = message.content if message.content else "Default content"
else:
    content = str(message) if message else "Default content"
```

---

**End of Document**
