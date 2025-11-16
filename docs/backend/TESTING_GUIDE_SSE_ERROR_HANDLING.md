# Testing Guide: SSE Error Handling

**Purpose:** Verify defensive SSE error handling prevents `ERR_INCOMPLETE_CHUNKED_ENCODING` crashes

---

## Quick Start Testing

### 1. Restart Backend Server

```bash
cd /Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2/module-2-2-frontend-enhanced/backend
python main.py
```

Expected output:
```
================================================================================
DeepAgent Research API v2.4 - Enhanced Backend with WebSocket
================================================================================
Features:
  ✅ Progress logging support
  ✅ Citation-aware streaming
  ✅ Enhanced event types
  ✅ WebSocket real-time collaboration
  ✅ JWT authentication
================================================================================

Starting server at http://localhost:8000
Frontend: http://localhost:3000
```

### 2. Test Basic Streaming (Control Test)

**Endpoint:** `POST http://localhost:8000/api/chat`

**Payload:**
```json
{
  "message": "What is 2 + 2?",
  "auto_approve": true,
  "plan_mode": false
}
```

**Expected:**
- ✅ Stream starts immediately
- ✅ Receives `llm_thinking` events
- ✅ Receives `llm_final_response` event
- ✅ Receives `stream_complete` event
- ✅ No errors in backend logs
- ✅ No `ERR_INCOMPLETE_CHUNKED_ENCODING` in frontend

### 3. Test Delegation (Previously Crashed)

**Endpoint:** `POST http://localhost:8000/api/chat`

**Payload:**
```json
{
  "message": "Delegate to researcher: Find latest news about quantum computing",
  "auto_approve": true,
  "plan_mode": false
}
```

**Expected Before Fix:**
- ❌ Stream crashes with `ERR_INCOMPLETE_CHUNKED_ENCODING`
- ❌ Backend logs show exception
- ❌ Frontend freezes
- ❌ No completion signal

**Expected After Fix:**
- ✅ Stream continues even if delegation has issues
- ✅ Receives error event if delegation fails: `{"type": "error", ...}`
- ✅ Always receives `stream_complete` event
- ✅ Backend logs full error trace
- ✅ Frontend shows error message (not frozen)

---

## Detailed Test Cases

### Test Case 1: Normal Operation
**Scenario:** Verify error handling doesn't break normal flow

**Steps:**
1. Send simple query: "What is the capital of France?"
2. Verify SSE events received in order:
   - `llm_thinking` (optional)
   - `llm_final_response`
   - `stream_complete`
3. Check backend logs for no errors

**Pass Criteria:**
- All events received correctly
- No error events
- Clean completion
- Response time < 5 seconds

---

### Test Case 2: Delegation Error Handling
**Scenario:** Test error handling during delegation

**Steps:**
1. Send delegation query: "Delegate to researcher: [complex task]"
2. Monitor SSE stream for:
   - Tool call events (`delegate` tool)
   - Possible error events
   - Completion signal
3. Check backend logs for error traces

**Pass Criteria:**
- Stream doesn't crash
- Error events have helpful messages
- `stream_complete` always received
- Errors logged with full stack trace

---

### Test Case 3: Timeout Handling
**Scenario:** Verify timeout errors handled gracefully

**Steps:**
1. Send very complex query with many steps
2. If timeout occurs, verify:
   - Timeout error event received: `{"type": "error", "error_type": "timeout", ...}`
   - Backend logs timeout error
   - Stream completes properly

**Pass Criteria:**
- Timeout error visible to user
- No `ERR_INCOMPLETE_CHUNKED_ENCODING`
- Completion signal sent
- Detailed logs available

---

### Test Case 4: Chunk Processing Errors
**Scenario:** Test error handling for malformed chunks

**Steps:**
1. Monitor backend logs during normal operation
2. If `AttributeError` or processing errors occur:
   - Verify error event sent to frontend
   - Verify stream continues to next chunk
   - Verify completion signal sent

**Pass Criteria:**
- Processing errors don't crash stream
- Error events formatted correctly
- Stream recovers and continues
- Full error trace in logs

---

### Test Case 5: Plan Mode Execution
**Scenario:** Test error handling in plan mode

**Steps:**
1. Send plan mode query: `{"message": "Create plan for research", "plan_mode": true}`
2. Verify plan creation and execution
3. Monitor for any errors during:
   - Plan creation
   - Step execution
   - Plan updates
4. Verify completion signal

**Pass Criteria:**
- Plan mode works with error handling
- All plan events received
- Errors (if any) handled gracefully
- Clean completion

---

## Error Event Formats

### Error Event
```json
{
  "type": "error",
  "error_type": "error",  // "error" | "warning" | "timeout" | "fatal"
  "message": "Human-readable error message",
  "timestamp": 1699999999.999
}
```

### Warning Event
```json
{
  "type": "error",
  "error_type": "warning",
  "message": "Warning message",
  "timestamp": 1699999999.999
}
```

### Completion Event
```json
{
  "type": "stream_complete",
  "thread_id": "uuid-string",
  "success": true,
  "timestamp": 1699999999.999
}
```

---

## Debugging

### Check Backend Logs

**Look for:**
1. `[SSE Stream] FATAL: Agent stream failed` - Outer loop error
2. `[SSE Stream] AttributeError processing chunk` - Chunk processing error
3. `[SSE Stream] Error flushing approval queue` - Cleanup error
4. `[SSE Stream] Error sending completion signal` - Completion error

**All errors should:**
- Include full stack trace (`exc_info=True`)
- Be followed by error event emission
- Be followed by completion signal

### Check Frontend Console

**Look for:**
1. SSE events logged in console
2. Error events with type `"error"`
3. No `ERR_INCOMPLETE_CHUNKED_ENCODING` errors
4. Completion events always received

**Example good output:**
```javascript
data: {"type": "llm_thinking", "content": "...", "agent": "Supervisor"}
data: {"type": "tool_call", "tool": "delegate", "args": {...}}
data: {"type": "tool_result", "content": "..."}
data: {"type": "stream_complete", "thread_id": "...", "success": true}
```

**Example error output (acceptable):**
```javascript
data: {"type": "llm_thinking", "content": "..."}
data: {"type": "error", "error_type": "error", "message": "Chunk processing error: ..."}
data: {"type": "stream_complete", "thread_id": "...", "success": true}
```

---

## Common Issues

### Issue: Backend still crashes
**Diagnosis:** Check if error is OUTSIDE `stream_agent_response()` function
**Solution:** Errors must be inside the async generator to be caught

### Issue: Completion signal not received
**Diagnosis:** Check if `finally` block executed
**Solution:** Verify no `return` statements inside try block (use `yield` only)

### Issue: Error events not visible in frontend
**Diagnosis:** Frontend may not be displaying error events
**Solution:** Update frontend to handle `{"type": "error"}` events

### Issue: Too many error events
**Diagnosis:** Errors on every chunk indicate systematic issue
**Solution:** Fix root cause instead of relying on error handling

---

## Success Metrics

### Must Have:
- ✅ Zero `ERR_INCOMPLETE_CHUNKED_ENCODING` errors
- ✅ Completion signal received in 100% of requests
- ✅ Error messages visible to users (not silent failures)
- ✅ Full error traces in backend logs

### Nice to Have:
- ✅ < 5% error rate during normal operation
- ✅ Error messages suggest recovery actions
- ✅ Frontend displays errors in UI (not just console)
- ✅ Automatic retry for transient errors

---

## Test Automation Ideas

### Python Test Script
```python
import requests
import json

def test_sse_error_handling():
    url = "http://localhost:8000/api/chat"
    payload = {
        "message": "Delegate to researcher: Test query",
        "auto_approve": True
    }

    response = requests.post(url, json=payload, stream=True)

    events = []
    for line in response.iter_lines():
        if line.startswith(b"data: "):
            data = json.loads(line[6:])
            events.append(data)

    # Verify completion signal
    assert events[-1]["type"] == "stream_complete"

    # Verify no ERR_INCOMPLETE_CHUNKED_ENCODING
    assert response.status_code == 200

    print("✅ SSE error handling test passed!")

if __name__ == "__main__":
    test_sse_error_handling()
```

---

## Rollback Plan

If implementation causes issues:

1. **Revert to previous version:**
   ```bash
   git checkout HEAD~1 backend/main.py
   ```

2. **Keep helper functions, remove error handling:**
   - Keep `format_sse_error()` functions
   - Remove try/except/finally around main loop
   - Keep inner chunk processing try/except

3. **Emergency fix:**
   - Comment out outer try/except
   - Keep finally block for cleanup
   - Monitor for crashes

---

## Next Steps After Testing

1. **If tests pass:**
   - Commit changes to git
   - Update frontend to display error events
   - Monitor production for error patterns
   - Add retry logic if needed

2. **If tests fail:**
   - Review error logs
   - Identify specific failure case
   - Add targeted fix
   - Re-test

3. **Documentation:**
   - Update API documentation with error event formats
   - Update frontend integration guide
   - Add troubleshooting section

---

**Happy Testing!**

Remember: The goal is **zero crashes**, not zero errors. Errors are handled gracefully and visible to users.
