# Delegation Fix Implementation Plan

**Date:** November 12, 2025
**Branch:** working-delegation
**Status:** IN PROGRESS

---

## Executive Summary

Two critical issues identified preventing delegation from working:

1. **🔴 CRITICAL:** Missing routing edges - delegation_tools node has no path to subagents
2. **⚠️ IMPORTANT:** Tool configuration inconsistency - subagents see tools they can't execute

---

## Root Cause Analysis

### Issue #1: Delegation Routing Failure

**The Problem:**
After supervisor calls `delegate_to_researcher`, execution stops. Researcher never executes.

**Root Cause:**
Missing edge in graph configuration (langgraph_studio_graphs.py:1659-1672)

**Current State:**
```
Supervisor → [conditional edge] → delegation_tools → [NO EDGE] → ???
                                                   ↓
                                              [GRAPH HANGS]
```

**Expected State:**
```
Supervisor → delegation_tools → [route based on tool] → researcher_agent
                              → data_scientist_agent
                              → expert_analyst_agent
                              → writer_agent
                              → reviewer_agent
```

**Evidence:**
- Log shows: "✅ Routing to researcher subagent"
- Tool returns: `Command(goto="researcher_agent")`
- Execution stops: researcher_agent never runs
- No edge exists from delegation_tools node

**Why Command.goto Doesn't Work:**
The ToolNode wrapper (line 164) may not properly pass through Command objects, or LangGraph requires explicit edges when using separate tools nodes.

---

### Issue #2: Tool Configuration Inconsistency

**The Problem:**
Subagents are bound to production_tools (11 tools) but their tools execution nodes only have 3-4 tools.

**Example - Researcher Agent:**

```python
# Agent node binding (line 1118)
model_with_tools = model.bind_tools(production_tools)  # 11 tools including planning

# Tools node list (lines 210-215)
researcher_tools_list = [
    tavily_search,
    write_file_tool,
    edit_file_with_approval,
    read_file_tool,
]  # Only 4 tools
```

**Impact:**
- LLM sees `create_research_plan_tool` in schema
- LLM calls the tool
- Tools node can't execute it (not in list)
- Tool execution fails

**All 5 subagents affected:**
- Researcher: sees 11, executes 4
- Data Scientist: sees 11, executes 4
- Expert Analyst: sees 11, executes 4
- Writer: sees 11, executes 3
- Reviewer: sees 11, executes 3

---

## Implementation Plan

### **Phase 1: Fix Delegation Routing** ⚡ IMMEDIATE (30 min)

**Goal:** Make delegation work NOW using conditional edges

**Architecture Decision:**
- Short-term: Add conditional edges (reliable, explicit)
- Long-term: Debug Command.goto and switch to that pattern

#### Task 1.1: Add Routing Function
**File:** `langgraph_studio_graphs.py`
**Location:** After line 1620 (after reviewer routing function)

```python
def should_continue_after_delegation(state: SupervisorAgentState) -> Literal[
    "researcher_agent",
    "data_scientist_agent",
    "expert_analyst_agent",
    "writer_agent",
    "reviewer_agent",
    "end"
]:
    """
    Route to appropriate subagent based on which delegation tool was called.

    Checks the second-to-last message for the delegation tool call name,
    then routes to the corresponding subagent node.
    """
    messages = state.get("messages", [])
    if len(messages) < 2:
        return "end"

    # Check second-to-last message (before ToolMessage) for tool call
    prev_msg = messages[-2]
    if hasattr(prev_msg, "tool_calls") and prev_msg.tool_calls:
        tool_name = prev_msg.tool_calls[0].get("name", "")

        # Route based on delegation tool called
        if tool_name == "delegate_to_researcher":
            return "researcher_agent"
        elif tool_name == "delegate_to_data_scientist":
            return "data_scientist_agent"
        elif tool_name == "delegate_to_expert_analyst":
            return "expert_analyst_agent"
        elif tool_name == "delegate_to_writer":
            return "writer_agent"
        elif tool_name == "delegate_to_reviewer":
            return "reviewer_agent"

    return "end"
```

#### Task 1.2: Add Conditional Edges
**File:** `langgraph_studio_graphs.py`
**Location:** Replace comment at line 1672

**Remove:**
```python
# Delegation tools have NO edge - Command.goto handles routing to subagent nodes
```

**Add:**
```python
# Delegation tools routing - conditional edges route to appropriate subagent
workflow.add_conditional_edges(
    "delegation_tools",
    should_continue_after_delegation,
    {
        "researcher_agent": "researcher_agent",
        "data_scientist_agent": "data_scientist_agent",
        "expert_analyst_agent": "expert_analyst_agent",
        "writer_agent": "writer_agent",
        "reviewer_agent": "reviewer_agent",
        "end": END,
    }
)
```

#### Task 1.3: Test Delegation
- Restart backend
- Test query: "have the researcher research the latest space news for 2025"
- Verify logs show researcher executing
- Verify task completes successfully

**Success Criteria:**
- ✅ Researcher agent executes after delegation
- ✅ No hanging/timeout
- ✅ Task completes with results

---

### **Phase 2: Enable Distributed Planning** 🌐 SHORT-TERM (1 hour)

**Goal:** Allow each subagent to create and manage their own research plans

**Architecture Decision:** Distributed planning with namespacing

#### Task 2.1: Add Planning Tools to Subagent Tools Lists
**File:** `langgraph_studio_graphs.py`
**Locations:** Lines 210, 224, 238, 252, 265

**Update all 5 tools lists:**

```python
# Researcher (line 210)
researcher_tools_list = [
    tavily_search,
    write_file_tool,
    edit_file_with_approval,
    read_file_tool,
    create_research_plan_tool,      # NEW
    update_plan_progress_tool,      # NEW
    read_current_plan_tool,         # NEW
    edit_plan_tool,                 # NEW
]

# Data Scientist (line 224)
data_scientist_tools_list = [
    tavily_search,
    write_file_tool,
    edit_file_with_approval,
    read_file_tool,
    create_research_plan_tool,      # NEW
    update_plan_progress_tool,      # NEW
    read_current_plan_tool,         # NEW
    edit_plan_tool,                 # NEW
]

# Expert Analyst (line 238)
expert_analyst_tools_list = [
    tavily_search,
    write_file_tool,
    edit_file_with_approval,
    read_file_tool,
    create_research_plan_tool,      # NEW
    update_plan_progress_tool,      # NEW
    read_current_plan_tool,         # NEW
    edit_plan_tool,                 # NEW
]

# Writer (line 252)
writer_tools_list = [
    write_file_tool,
    edit_file_with_approval,
    read_file_tool,
    create_research_plan_tool,      # NEW
    update_plan_progress_tool,      # NEW
    read_current_plan_tool,         # NEW
    edit_plan_tool,                 # NEW
]

# Reviewer (line 265)
reviewer_tools_list = [
    write_file_tool,
    edit_file_with_approval,
    read_file_tool,
    create_research_plan_tool,      # NEW
    update_plan_progress_tool,      # NEW
    read_current_plan_tool,         # NEW
    edit_plan_tool,                 # NEW
]
```

#### Task 2.2: Implement Plan Namespacing
**File:** `module_2_2_simple.py`
**Functions to modify:**
- `create_research_plan_tool` (line 699)
- `update_plan_progress_tool` (line 820)
- `read_current_plan_tool` (line 961)
- `edit_plan_tool` (line 1034)

**Changes:**

1. **Add agent context detection:**
```python
def _get_agent_context(state: dict) -> str:
    """Detect which agent is calling the tool"""
    subagent_type = state.get("subagent_type", "supervisor")
    return subagent_type
```

2. **Update plan_id format:**
```python
agent_name = _get_agent_context(state)
plan_id = f"{agent_name}/plan-{uuid.uuid4()}"
```

3. **Update file paths:**
```python
plan_dir = WORKSPACE_DIR / ".plans" / agent_name
plan_dir.mkdir(parents=True, exist_ok=True)
plan_file = plan_dir / f"{plan_id}.json"
current_plan_file = plan_dir / "current_plan.json"
```

4. **Update WebSocket events:**
```python
await websocket_manager.broadcast_to_thread(
    thread_id,
    {
        "type": "plan_created",
        "agent": agent_name,  # NEW
        "plan": plan_data,
        "timestamp": time.time(),
    }
)
```

#### Task 2.3: Update Frontend for Plan Hierarchy
**File:** `frontend/components/PlanProgressPanel.tsx`

- Add agent badge to plan display
- Show which agent created each plan
- Display plan hierarchy if needed

#### Task 2.4: Test Distributed Planning
Test scenarios:
1. Supervisor creates plan → saved to `supervisor/current_plan.json`
2. Delegate to researcher → researcher creates own plan → saved to `researcher/current_plan.json`
3. Both plans active simultaneously → no conflicts
4. Update progress in both plans → both update correctly
5. WebSocket events show agent names

**Success Criteria:**
- ✅ Each agent can create plans independently
- ✅ Plans stored in agent-specific directories
- ✅ No conflicts between agent plans
- ✅ WebSocket events include agent context
- ✅ Frontend displays which agent owns each plan

---

### **Phase 3: Debug Command.goto** 🔬 LONG-TERM (1-2 hours)

**Goal:** Understand why Command.goto doesn't work and fix for future

**Architecture Decision:** Once working, switch from conditional edges to Command.goto pattern

#### Task 3.1: Add Diagnostic Logging
**File:** `langgraph_studio_graphs.py`
**Location:** delegation_tools_node function (line 164)

```python
async def delegation_tools_node(state: SupervisorAgentState):
    """
    Delegation tool execution node using prebuilt ToolNode.

    Executes ONLY delegation tools which return Command.goto objects.
    ToolNode automatically handles Command.goto routing to subagent nodes.

    No edge back to agent - Command.goto handles routing dynamically.
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info("[DELEGATION] Executing delegation_tools_node")
    result = await delegation_tool_node.ainvoke(state)

    # Diagnostic logging
    logger.info(f"[DELEGATION] Result type: {type(result)}")
    logger.info(f"[DELEGATION] Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")

    if isinstance(result, Command):
        logger.info(f"[DELEGATION] ✅ Command object detected!")
        logger.info(f"[DELEGATION] Command.goto: {result.goto}")
        logger.info(f"[DELEGATION] Command.update: {result.update.keys()}")
    else:
        logger.warning(f"[DELEGATION] ⚠️ Not a Command object - type is {type(result)}")

    return result
```

#### Task 3.2: Test Command Pass-Through
1. Enable LangGraph debug logging
2. Run delegation test
3. Check logs for:
   - Is result a Command object?
   - Does LangGraph receive the Command?
   - Is Command.goto processed?

#### Task 3.3: Research LangGraph Command Handling
- Check LangGraph documentation for Command + ToolNode
- Review GitHub issues for similar problems
- Test with minimal reproduction case

#### Task 3.4: Implement Fix
Based on findings, choose one:

**Option A: Fix Wrapper**
```python
async def delegation_tools_node(state: SupervisorAgentState):
    result = await delegation_tool_node.ainvoke(state)
    # Preserve Command type explicitly
    if isinstance(result, Command):
        return result  # Return unchanged
    return {"messages": result.get("messages", [])}
```

**Option B: Configure ToolNode**
```python
delegation_tool_node = ToolNode(
    delegation_tools,
    handle_tool_errors=True,
    # Add Command-specific configuration if available
)
```

**Option C: Use Different Pattern**
If ToolNode doesn't support Command in this context, switch to custom node that manually executes tools.

#### Task 3.5: Switch to Command.goto
Once working:
1. Remove conditional edges from Phase 1
2. Let Command.goto handle routing
3. Update documentation
4. Test all subagents

**Success Criteria:**
- ✅ Command objects properly passed through ToolNode
- ✅ LangGraph processes Command.goto
- ✅ Routing works without conditional edges
- ✅ Cleaner graph structure

---

## Testing Plan

### Phase 1 Tests
- [ ] Test researcher delegation: "have the researcher research space news"
- [ ] Test data scientist delegation: "have the data scientist analyze these numbers: 10, 20, 30"
- [ ] Test writer delegation: "have the writer write about solar energy"
- [ ] Test concurrent delegation: delegate to multiple agents
- [ ] Verify no hangs/timeouts

### Phase 2 Tests
- [ ] Supervisor creates plan → verify namespace
- [ ] Researcher creates plan → verify separate namespace
- [ ] Both plans active → no conflicts
- [ ] Update supervisor plan progress → correct file updated
- [ ] Update researcher plan progress → correct file updated
- [ ] WebSocket events → agent names included
- [ ] Frontend → shows plan hierarchy

### Phase 3 Tests
- [ ] Command object detected in logs
- [ ] LangGraph receives Command
- [ ] Command.goto routing works
- [ ] Remove conditional edges → still works
- [ ] All 5 subagents work with Command routing

---

## Timeline

| Phase | Task | Duration | Status |
|-------|------|----------|--------|
| **Phase 1** | Add routing function | 10 min | ⏳ PENDING |
| **Phase 1** | Add conditional edges | 10 min | ⏳ PENDING |
| **Phase 1** | Test delegation | 10 min | ⏳ PENDING |
| **Phase 2** | Add tools to lists | 15 min | ⏳ PENDING |
| **Phase 2** | Implement namespacing | 30 min | ⏳ PENDING |
| **Phase 2** | Update frontend | 15 min | ⏳ PENDING |
| **Phase 2** | Test distributed planning | 15 min | ⏳ PENDING |
| **Phase 3** | Add diagnostic logging | 15 min | ⏳ PENDING |
| **Phase 3** | Test Command pass-through | 15 min | ⏳ PENDING |
| **Phase 3** | Research + implement fix | 45 min | ⏳ PENDING |
| **Phase 3** | Switch to Command.goto | 15 min | ⏳ PENDING |
| **TOTAL** | | **2.5-3.5 hours** | |

---

## Rollback Plan

### If Phase 1 Fails
- Remove conditional edges
- Add simple edge: `workflow.add_edge("delegation_tools", END)`
- Document failure in logs

### If Phase 2 Fails
- Revert tool list changes
- Remove namespacing code
- Keep centralized planning (supervisor only)

### If Phase 3 Fails
- Keep conditional edges (they work)
- Document Command.goto limitations
- Consider this working architecture

---

## Documentation Updates

After each phase, update:
- [ ] WORKING_DELEGATION_FORK.md - Add "delegation fixed" status
- [ ] CODE_MAP.md - Update routing section
- [ ] CALL_GRAPH.md - Add delegation flow diagrams
- [ ] This file - Update status and findings

---

## Success Metrics

### Phase 1 Success
- ✅ Delegation completes without hanging
- ✅ All 5 subagents reachable
- ✅ Tasks complete with results
- ✅ Backend logs show full flow

### Phase 2 Success
- ✅ Each agent creates plans independently
- ✅ Plans stored in agent directories
- ✅ No plan conflicts
- ✅ WebSocket events include agent context
- ✅ Frontend shows plan ownership

### Phase 3 Success
- ✅ Command.goto routing works
- ✅ Conditional edges removed
- ✅ Cleaner graph architecture
- ✅ Documentation updated

---

## Current Status

**Date:** November 12, 2025
**Phase:** Starting Phase 1
**Progress:** 0% complete

**Next Steps:**
1. Implement routing function
2. Add conditional edges
3. Test delegation

---

**End of Implementation Plan**
