# Anthropic Claude API Message Format Requirements Research

**Research Date:** November 9, 2025
**Purpose:** Understanding tool_use/tool_result message requirements and safe filtering strategies

---

## 1. Anthropic API Message Format Requirements

### Core Message Structure Rules

**Role Alternation Pattern:**
- Messages MUST alternate between `user` and `assistant` roles
- The first message MUST always have the `user` role
- Consecutive messages with the same role are automatically combined into a single turn
- The API is trained to operate on alternating conversational turns

**Message Content Types:**
Messages can contain different content block types:
- `text` - Standard conversational content
- `tool_use` - Model requests to invoke a tool
- `tool_result` - Results from tool execution
- `thinking`/`redacted_thinking` - Extended thinking feature
- MCP tool blocks - Model Context Protocol integration

---

## 2. Tool Use and Tool Result Requirements

### Valid Tool Use Sequence

The strict alternating pattern for tool use is:

```
1. User Message → Initial prompt + tool definitions
2. Assistant Message → Contains tool_use blocks (stop_reason: "tool_use")
3. User Message → Contains tool_result blocks with matching IDs
4. Assistant Message → Final response incorporating results
```

### Critical Requirements

**Each tool_use block MUST:**
- Have a unique `id` field (e.g., `toolu_123`)
- Specify the tool `name`
- Include the `input` parameters

**Each tool_result block MUST:**
- Include a `tool_use_id` that matches the original tool call ID
- Have a `content` field with the actual tool output
- Optionally include `is_error: true` for error scenarios

**Parallel Tool Calls:**
- All `tool_use` blocks are included in a single assistant message
- ALL corresponding `tool_result` blocks must be provided in the subsequent user message
- All results go in ONE user message, not multiple messages

### Example Structure

**Assistant Message with tool_use:**
```json
{
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Let me check the weather for you."
    },
    {
      "type": "tool_use",
      "id": "toolu_01A09q90qw90lq917835lq9",
      "name": "get_weather",
      "input": {"location": "San Francisco"}
    }
  ],
  "stop_reason": "tool_use"
}
```

**User Message with tool_result:**
```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
      "content": "Temperature: 72°F, Sunny"
    }
  ]
}
```

---

## 3. What Happens When tool_use Is Not Followed by tool_result?

### Two Valid Scenarios:

**Scenario 1: You Only Need the Intent**
Steps 3-4 (returning results and getting final response) are OPTIONAL. According to Anthropic docs:

> "Note: Steps 3 and 4 are optional. For some workflows, Claude's tool use request (step 2) might be all you need, without sending results back to Claude."

This is useful when you only need Claude's *intent* to call a tool, not its response.

**Scenario 2: You Send Another Message**
If you continue the conversation WITHOUT providing tool_result blocks, you will get an error:

**Error:** `tool_use ids were found without tool_result blocks immediately after: [tool_id]. Each tool_use block must have a corresponding tool_result block in the next message.`

### The Key Rule:

**IF you continue the conversation after a tool_use message, the VERY NEXT user message MUST contain all matching tool_result blocks.**

---

## 4. Common Error Patterns and Solutions

### Error 1: Missing tool_result After Continuing Conversation

**Error Message:**
```
"tool_use ids were found without tool_result blocks immediately after: [tool_id]"
```

**Cause:** You sent a new user message after an assistant message with `tool_use`, but didn't include `tool_result` blocks.

**Solution:** Either:
1. Include all matching `tool_result` blocks in the next user message, OR
2. Don't continue the conversation (treat the tool_use as the final output)

### Error 2: tool_result Without Corresponding tool_use

**Error Message:**
```
"tool_result without corresponding tool_use found"
```

**Cause:** You included a `tool_result` block but there's no matching `tool_use` in the previous assistant message.

**Solution:** Ensure the previous assistant message contains a `tool_use` block with the matching ID.

### Error 3: Mismatched tool_use_id

**Error Message:**
```
"Did not find 1 tool_result block(s) at the beginning of this message"
```

**Cause:** The `tool_use_id` in your `tool_result` doesn't match any `id` from the previous `tool_use` blocks.

**Solution:** Copy the exact ID from the `tool_use` block into the `tool_use_id` field.

### Error 4: Missing Tool Definitions

**Error Message:**
```
"Requests must define tools when including 'tool_use' or 'tool_result' blocks"
```

**Cause:** You're sending messages with tool blocks but didn't include the `tools` parameter in your API request.

**Solution:** Always include the full tool definitions in the `tools` array when replaying conversations with tool messages.

---

## 5. Message Filtering Strategies

### Why Filter Messages?

**Common Reasons:**
1. Reduce token usage by removing old tool interactions
2. Prevent conversation history from exceeding context limits
3. Clean up invalid message sequences after errors
4. Summarize tool interactions instead of keeping full details
5. Fix broken message sequences (e.g., orphaned tool_use blocks)

### Safe Filtering Approaches

#### Approach 1: Remove All Tool-Related Messages

**When to Use:** You want to keep only conversational turns, removing all tool interaction details.

**Implementation:**
```python
def filter_tool_messages(messages):
    """Remove all tool_use and tool_result content blocks."""
    filtered = []
    for msg in messages:
        if isinstance(msg.content, str):
            filtered.append(msg)
        else:
            # Filter out tool_use and tool_result blocks
            non_tool_content = [
                block for block in msg.content
                if block.get("type") not in ["tool_use", "tool_result"]
            ]
            if non_tool_content:
                filtered.append({
                    "role": msg.role,
                    "content": non_tool_content
                })
    return filtered
```

**Risk:** May lose important context from tool results.

#### Approach 2: Remove Orphaned tool_use Blocks

**When to Use:** You have assistant messages with `tool_use` blocks that won't be followed by `tool_result` blocks.

**Implementation:**
```python
def remove_orphaned_tool_use(messages):
    """Remove tool_use blocks from the last assistant message if not followed by tool_result."""
    if not messages:
        return messages

    # Check if last message is assistant with tool_use
    last_msg = messages[-1]
    if last_msg.role == "assistant" and isinstance(last_msg.content, list):
        # Remove tool_use blocks from last message
        filtered_content = [
            block for block in last_msg.content
            if block.get("type") != "tool_use"
        ]
        if filtered_content:
            messages[-1] = {
                "role": "assistant",
                "content": filtered_content
            }
        else:
            # If only tool_use blocks, remove entire message
            messages = messages[:-1]

    return messages
```

**Risk:** Lower - Only removes tool_use blocks that would cause errors.

#### Approach 3: Preserve Matched Pairs Only

**When to Use:** You want to keep tool interactions but ensure they're valid.

**Implementation:**
```python
def validate_tool_pairs(messages):
    """Ensure all tool_use blocks have matching tool_result blocks."""
    validated = []
    i = 0
    while i < len(messages):
        msg = messages[i]

        # Check if assistant message has tool_use
        if msg.role == "assistant" and has_tool_use(msg):
            tool_use_ids = extract_tool_use_ids(msg)

            # Check if next message has matching tool_results
            if i + 1 < len(messages) and messages[i + 1].role == "user":
                next_msg = messages[i + 1]
                result_ids = extract_tool_result_ids(next_msg)

                # If all tool_use have matching results, keep both
                if set(tool_use_ids) == set(result_ids):
                    validated.append(msg)
                    validated.append(next_msg)
                    i += 2
                    continue

            # No matching results - remove tool_use blocks
            cleaned_msg = remove_tool_use_blocks(msg)
            if cleaned_msg:
                validated.append(cleaned_msg)
        else:
            validated.append(msg)

        i += 1

    return validated
```

**Risk:** Lowest - Ensures message validity while preserving useful tool interactions.

#### Approach 4: Summarize Tool Interactions

**When to Use:** You want to preserve the semantic information but reduce tokens.

**Implementation:**
```python
def summarize_tool_interactions(messages):
    """Replace tool_use/tool_result pairs with text summaries."""
    summarized = []
    i = 0
    while i < len(messages):
        msg = messages[i]

        if msg.role == "assistant" and has_tool_use(msg):
            # Extract tool calls
            tool_calls = extract_tool_calls(msg)

            # Get results from next message
            results = {}
            if i + 1 < len(messages):
                results = extract_tool_results(messages[i + 1])

            # Create summary text
            summary = create_summary(tool_calls, results)

            summarized.append({
                "role": "assistant",
                "content": summary
            })

            i += 2  # Skip result message
        else:
            summarized.append(msg)
            i += 1

    return summarized
```

**Risk:** May lose important details, but preserves general context.

---

## 6. LangChain/LangGraph-Specific Considerations

### Message Type Conversions

**LangChain's Internal Representation:**
- `AIMessage` with `tool_calls` attribute → Anthropic `tool_use` blocks
- `ToolMessage` with `tool_call_id` → Anthropic `tool_result` blocks
- `HumanMessage` → User role
- `SystemMessage` → System parameter (not a message)

### Common LangChain Issues

#### Issue 1: trim_messages Breaking Tool Pairs

**Problem:** `trim_messages` can cut off tool_use without removing corresponding tool_result, or vice versa.

**Error:** "tool calls get trimmed and the number of tool calls and tool results don't match"

**Solution:** Use `start_on="human"` and validate tool pairs after trimming:

```python
from langchain_core.messages import trim_messages

trimmed = trim_messages(
    messages,
    token_counter=ChatAnthropic().get_num_tokens_from_messages,
    max_tokens=4000,
    strategy="last",
    start_on="human",  # Ensure we start with human message
    include_system=True
)

# Validate tool pairs
validated = validate_tool_pairs(trimmed)
```

#### Issue 2: ChatAnthropic Token Counter Failing

**Problem:** `ChatAnthropic.get_num_tokens_from_messages` uses Anthropic's API and errors on invalid sequences.

**Error:** API rejection due to invalid message sequence during token counting.

**Solution:** Pre-filter messages before token counting:

```python
# Filter first
cleaned = remove_orphaned_tool_use(messages)

# Then count
token_count = chat_anthropic.get_num_tokens_from_messages(cleaned)
```

#### Issue 3: Human-in-the-Loop Checkpoint Restoration

**Problem:** LangGraph checkpointer restores messages that violate tool_use/tool_result ordering after interrupt/resume.

**Error:** "tool_result without corresponding tool_use" after resuming from checkpoint.

**Solution:** Validate and clean messages after checkpoint restoration:

```python
# After resuming from checkpoint
state = graph.get_state(config)
messages = state.values["messages"]

# Clean before next invocation
cleaned_messages = validate_tool_pairs(messages)
```

### LangChain filter_messages Utility

**Built-in Filtering:**
```python
from langchain_core.messages import filter_messages

# Filter by type
filtered = filter_messages(
    messages,
    include_types=["human", "ai"],  # Exclude tool messages
)

# Filter by name
filtered = filter_messages(
    messages,
    exclude_names=["get_weather", "search_tool"]
)

# Filter by ID
filtered = filter_messages(
    messages,
    exclude_ids=["msg_123", "msg_456"]
)
```

**Limitation:** These filters don't automatically validate tool_use/tool_result pairing - you must do that manually.

---

## 7. Best Practices and Recommendations

### Development Best Practices

1. **Always Validate Before Sending:**
   - Check that tool_use blocks have matching tool_result blocks
   - Ensure role alternation (user → assistant → user → assistant)
   - Verify first message is always user role

2. **Handle Errors Gracefully:**
   - Catch Anthropic API errors and clean message history
   - Log the problematic message sequence for debugging
   - Have a fallback strategy (remove tool messages or reset conversation)

3. **Test Edge Cases:**
   - Empty messages after tool filtering
   - Orphaned tool_use blocks
   - Mismatched IDs
   - Parallel tool calls
   - Interrupted conversations

4. **Use Defensive Programming:**
   - Validate after every message history manipulation
   - Don't assume LangChain/LangGraph maintains validity
   - Add explicit checks before API calls

### Production Best Practices

1. **Logging and Monitoring:**
   - Log full message sequences when errors occur
   - Track tool_use/tool_result pairing metrics
   - Monitor for increasing error rates

2. **Graceful Degradation:**
   - If tool messages cause issues, fall back to tool-free conversation
   - Provide clear user feedback when tool calls fail
   - Don't expose raw API errors to users

3. **Message History Management:**
   - Implement sliding window with awareness of tool pairs
   - Summarize old tool interactions rather than removing
   - Keep recent context even if trimming history

4. **Testing Strategy:**
   - Unit tests for message filtering functions
   - Integration tests with mock Anthropic API
   - End-to-end tests with real API calls
   - Load tests for conversation history trimming

### Common Mistakes to Avoid

**Mistake 1: Removing Only One Half of a Pair**
```python
# BAD: Removes tool_result but leaves tool_use
filtered = [msg for msg in messages if not isinstance(msg, ToolMessage)]
```

**Solution:** Remove both or neither.

**Mistake 2: Not Checking Last Message**
```python
# BAD: Doesn't check if conversation ends with orphaned tool_use
return messages
```

**Solution:** Always validate the last message won't cause errors.

**Mistake 3: Assuming Alternating Roles**
```python
# BAD: Assumes messages already alternate
for i in range(0, len(messages), 2):
    assert messages[i].role == "user"
    assert messages[i+1].role == "assistant"
```

**Solution:** Explicitly validate and fix role order.

**Mistake 4: Filtering After Token Counting**
```python
# BAD: Count tokens on invalid sequence
tokens = chat.get_num_tokens_from_messages(messages)
filtered = remove_tool_use(messages)
```

**Solution:** Filter BEFORE any operations that call the API.

**Mistake 5: Not Handling Parallel Tool Calls**
```python
# BAD: Assumes one tool_use per message
tool_use_id = msg.content[0]["id"]
```

**Solution:** Handle arrays of tool_use blocks.

---

## 8. Summary and Key Takeaways

### Critical Rules

1. **Role Alternation:** Messages must alternate user → assistant → user → assistant
2. **First Message:** Must always be user role
3. **Tool Pairing:** Each tool_use must have matching tool_result OR be the final message
4. **Parallel Tools:** All results for parallel tool calls go in ONE user message
5. **ID Matching:** tool_result.tool_use_id must exactly match tool_use.id

### When to Filter Messages

- Conversation history too long (approaching context limit)
- Tool interactions no longer relevant
- Invalid sequence after checkpoint restoration
- Error recovery scenarios
- Orphaned tool_use blocks at end of conversation

### Safest Filtering Strategy

For most cases, use **Approach 3: Preserve Matched Pairs Only**:
1. Scan message history for tool_use blocks
2. Check if each has a matching tool_result in the next user message
3. Keep complete pairs, remove incomplete pairs
4. Validate final message doesn't end with orphaned tool_use

### LangChain-Specific Advice

- Don't trust `trim_messages` alone - always validate after
- Pre-filter before using `ChatAnthropic.get_num_tokens_from_messages`
- Validate after checkpoint restoration
- Use `start_on="human"` parameter
- Implement custom validation for tool pairs

### Error Recovery

When you encounter tool_use/tool_result errors:
1. Log the full message sequence
2. Identify the problematic pair (or missing pair)
3. Remove the problematic messages
4. Validate the cleaned sequence
5. Retry the API call
6. If still failing, fall back to removing all tool messages

---

## 9. Code Examples

### Complete Validation Function

```python
from typing import List, Dict, Any
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage, HumanMessage

def validate_anthropic_messages(messages: List[BaseMessage]) -> List[BaseMessage]:
    """
    Validate and clean message history for Anthropic API.

    Ensures:
    1. Alternating user/assistant roles
    2. First message is user
    3. All tool_use blocks have matching tool_result blocks
    4. No orphaned tool_use at end

    Returns cleaned, valid message list.
    """
    if not messages:
        return []

    # Step 1: Convert to dicts for easier manipulation
    msg_dicts = [msg.dict() if hasattr(msg, 'dict') else msg for msg in messages]

    # Step 2: Ensure first message is user
    if msg_dicts[0].get("role") != "user":
        # Add a minimal user message at start
        msg_dicts.insert(0, {
            "role": "user",
            "content": "Hello"
        })

    # Step 3: Validate tool_use/tool_result pairing
    cleaned = []
    i = 0
    while i < len(msg_dicts):
        msg = msg_dicts[i]

        # Check if assistant message has tool_use
        if msg.get("role") == "assistant":
            tool_use_blocks = extract_tool_use_blocks(msg)

            if tool_use_blocks:
                # Check next message for matching results
                if i + 1 < len(msg_dicts) and msg_dicts[i + 1].get("role") == "user":
                    next_msg = msg_dicts[i + 1]
                    result_blocks = extract_tool_result_blocks(next_msg)

                    tool_use_ids = {b["id"] for b in tool_use_blocks}
                    result_ids = {b["tool_use_id"] for b in result_blocks}

                    # If all IDs match, keep both messages
                    if tool_use_ids == result_ids:
                        cleaned.append(msg)
                        cleaned.append(next_msg)
                        i += 2
                        continue

                # No matching results - remove tool_use blocks
                cleaned_content = [
                    block for block in msg.get("content", [])
                    if block.get("type") != "tool_use"
                ]
                if cleaned_content:
                    cleaned.append({
                        "role": "assistant",
                        "content": cleaned_content
                    })
                i += 1
            else:
                # No tool_use - keep as is
                cleaned.append(msg)
                i += 1
        else:
            # User message - keep as is
            cleaned.append(msg)
            i += 1

    # Step 4: Ensure alternating roles
    cleaned = ensure_alternating_roles(cleaned)

    # Step 5: Convert back to BaseMessage objects
    result = []
    for msg in cleaned:
        if msg.get("role") == "user":
            result.append(HumanMessage(content=msg["content"]))
        elif msg.get("role") == "assistant":
            result.append(AIMessage(content=msg["content"]))

    return result


def extract_tool_use_blocks(msg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract tool_use blocks from message content."""
    content = msg.get("content", [])
    if isinstance(content, str):
        return []
    return [block for block in content if block.get("type") == "tool_use"]


def extract_tool_result_blocks(msg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract tool_result blocks from message content."""
    content = msg.get("content", [])
    if isinstance(content, str):
        return []
    return [block for block in content if block.get("type") == "tool_result"]


def ensure_alternating_roles(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure messages alternate between user and assistant roles."""
    if not messages:
        return []

    result = [messages[0]]
    for msg in messages[1:]:
        # Only add if role differs from previous
        if msg.get("role") != result[-1].get("role"):
            result.append(msg)
        else:
            # Merge with previous message
            prev_content = result[-1].get("content", [])
            curr_content = msg.get("content", [])

            if isinstance(prev_content, str) and isinstance(curr_content, str):
                result[-1]["content"] = prev_content + "\n\n" + curr_content
            elif isinstance(prev_content, list) and isinstance(curr_content, list):
                result[-1]["content"] = prev_content + curr_content

    return result
```

### Usage with LangChain

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import trim_messages

# Initialize
chat = ChatAnthropic(model="claude-3-5-sonnet-20241022")

# Get conversation history
state = graph.get_state(config)
messages = state.values["messages"]

# Clean and validate
validated_messages = validate_anthropic_messages(messages)

# Optionally trim for token limits
trimmed_messages = trim_messages(
    validated_messages,
    token_counter=chat.get_num_tokens_from_messages,
    max_tokens=4000,
    strategy="last",
    start_on="human",
    include_system=True
)

# Final validation before API call
final_messages = validate_anthropic_messages(trimmed_messages)

# Safe to invoke
response = chat.invoke(final_messages)
```

---

## 10. References

### Official Documentation
- [Anthropic Tool Use Documentation](https://docs.claude.com/en/docs/build-with-claude/tool-use)
- [Anthropic Messages API](https://docs.claude.com/en/api/messages)
- [LangChain filter_messages](https://python.langchain.com/api_reference/core/messages/langchain_core.messages.utils.filter_messages.html)
- [LangChain trim_messages](https://python.langchain.com/api_reference/core/messages/langchain_core.messages.utils.trim_messages.html)

### Known Issues
- [LangGraph Issue #1423 - Human-in-the-loop tool_result errors](https://github.com/langchain-ai/langgraphjs/issues/1423)
- [LangGraph Issue #3168 - Anthropic API error with empty content](https://github.com/langchain-ai/langgraph/issues/3168)
- [LangChain Issue #29637 - trim_messages and ChatAnthropic token counter with tools](https://github.com/langchain-ai/langchain/issues/29637)
- [LangChain Issue #31657 - Anthropic errors with system messages in tool flows](https://github.com/langchain-ai/langchain/issues/31657)

---

**End of Research Document**
