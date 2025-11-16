# Config 8 Test Results - Hierarchical Teams

**Date**: 2025-11-12 14:01:00
**Status**: ❌ FAILED
**Configuration**: Hierarchical agent teams with multiple supervisors

---

## Test Summary

- **Total Messages**: 0 (failed during graph construction)
- **Delegation Success**: Not reached
- **Planning Tools Used**: 0
- **Subagent Independence**: Not reached
- **Errors**: 1 critical error (schema validation)

**Error Type**: ValueError - Invalid managed channels in InputSchema

---

## Full Test Output

```
Exit code 1

🚀 Starting Config 8 Test: Hierarchical Agent Teams...


================================================================================
TEST CONFIG 8: HIERARCHICAL AGENT TEAMS
================================================================================


================================================================================
BUILDING CONFIG 8: HIERARCHICAL AGENT TEAMS
================================================================================

1. Building team subgraphs...

   Building Team A Subgraph (Research & Writing)...
      Team A supervisor tools: 10
      Researcher tools: 8
      Writer tools: 9
Traceback (most recent call last):
  File "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2/module-2-2-frontend-enhanced/backend/test_configs/test_config_8_hierarchical_teams.py", line 814, in <module>
    asyncio.run(test_config_8())
  File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/asyncio/runners.py", line 194, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/asyncio/base_events.py", line 687, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2/module-2-2-frontend-enhanced/backend/test_configs/test_config_8_hierarchical_teams.py", line 662, in test_config_8
    graph = build_config_8_graph()
            ^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2/module-2-2-frontend-enhanced/backend/test_configs/test_config_8_hierarchical_teams.py", line 565, in build_config_8_graph
    team_a_graph = build_team_a_subgraph()
                   ^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2/module-2-2-frontend-enhanced/backend/test_configs/test_config_8_hierarchical_teams.py", line 422, in build_team_a_subgraph
    team_a_supervisor = create_agent(
                        ^^^^^^^^^^^^^
  File "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/.venv/lib/python3.12/site-packages/langchain/agents/factory.py", line 777, in create_agent
    ] = StateGraph(
        ^^^^^^^^^^^
  File "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/.venv/lib/python3.12/site-packages/langgraph/graph/state.py", line 238, in __init__
    self._add_schema(self.input_schema, allow_managed=False)
  File "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/.venv/lib/python3.12/site-packages/langgraph/graph/state.py", line 254, in _add_schema
    raise ValueError(
ValueError: Invalid managed channels detected in InputSchema: remaining_steps. Managed channels are not permitted in Input/Output schema.
```

---

## Analysis

### Supervisor Behavior
- Created plan: Not reached (graph construction failed)
- Delegated task: Not reached
- Reflected after delegation: Not reached

### Subagent Behavior
- Received delegation: Not reached
- Created subplan: Not reached
- Executed independently: Not reached
- Tool calls made: None

### Distributed Planning Evidence

**Graph Construction Started**: ✅ Partial

```
Building Team A Subgraph (Research & Writing)...
   Team A supervisor tools: 10
   Researcher tools: 8
   Writer tools: 9
```

The hierarchical structure was being built:
- **Team A**: Research & Writing team with supervisor, researcher, writer
- Team A supervisor had 10 tools (including delegation)
- Researcher had 8 tools
- Writer had 9 tools

The construction failed when creating Team A's supervisor agent.

### Issues Found

**Critical Error**: Schema Validation Error

```
ValueError: Invalid managed channels detected in InputSchema: remaining_steps.
Managed channels are not permitted in Input/Output schema.
```

**Root Cause**: The state schema includes `remaining_steps` as a managed channel, but managed channels cannot be in the Input/Output schema of a subgraph.

**LangGraph Managed Channels**:

Managed channels are special state fields that LangGraph manages internally. They have specific rules:
- Can be used internally within a graph
- **Cannot** be exposed in the Input/Output schema of subgraphs
- Must be excluded when creating nested graphs

**Common Managed Channels**:
- `remaining_steps` - Tracks remaining plan steps
- `is_last_step` - Boolean flag for final step
- Other plan-tracking fields

**Where the Error Occurs**:

Line 422 in `test_config_8_hierarchical_teams.py`:
```python
team_a_supervisor = create_agent(
    # ... configuration ...
)
```

The `create_agent()` function is being called with a state schema that includes `remaining_steps`, which is a managed channel.

**StateGraph Nesting Rules** (LangGraph v0.2+):

When creating nested subgraphs:
1. Parent graph can have managed channels
2. Child subgraphs **cannot** have managed channels in their Input/Output schema
3. Managed channels must be internal to each subgraph level

---

## Recommendation

**Status**: ❌ **FAIL** - Schema validation error prevents graph construction

**Fix Required**:

### **Fix 1**: Separate State Schemas for Parent and Child Graphs (HIGH PRIORITY)

Create distinct state schemas for different graph levels:

```python
# Parent graph state (can have managed channels)
class ParentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    remaining_steps: List[str]  # Managed channel - OK at parent level
    # ... other fields

# Child graph state (NO managed channels)
class TeamState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    # NO remaining_steps here!
    team_context: dict  # Team-specific context
    # ... other fields

# Team A subgraph
team_a_graph = StateGraph(TeamState)  # Uses TeamState, not ParentState
```

### **Fix 2**: Use Input/Output Schemas for Subgraphs (HIGH PRIORITY)

Define explicit input/output schemas that exclude managed channels:

```python
from langgraph.graph import StateGraph

# Define team state WITHOUT managed channels
class TeamInputOutput(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    # Exclude remaining_steps and other managed channels

# Build team subgraph with explicit I/O schema
team_a_graph = StateGraph(
    state_schema=TeamState,
    input_schema=TeamInputOutput,  # Explicit input schema
    output_schema=TeamInputOutput  # Explicit output schema
)
```

### **Fix 3**: Remove Managed Channels from create_agent() (HIGH PRIORITY)

If using `create_agent()` from LangChain, ensure the state passed doesn't include managed channels:

```python
# WRONG:
team_a_supervisor = create_agent(
    llm=llm,
    tools=team_a_tools,
    state_schema=ParentState  # ❌ Contains remaining_steps
)

# CORRECT:
class TeamAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    # NO managed channels

team_a_supervisor = create_agent(
    llm=llm,
    tools=team_a_tools,
    state_schema=TeamAgentState  # ✅ No managed channels
)
```

### **Fix 4**: Alternative - Use Private State (MEDIUM PRIORITY)

If you need plan tracking at team level, use private state:

```python
from langgraph.managed import PrivateAttr

class TeamState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    _remaining_steps: PrivateAttr[List[str]]  # Private, not in I/O schema
```

---

## Expected Behavior After Fix

Once the schema issue is resolved, Config 8 should:

1. **Build Hierarchical Structure**:
   ```
   Top Supervisor
      ↓
   Team A (Research & Writing)
      ↓ Team A Supervisor
      ├─ Researcher
      └─ Writer
      ↓
   Team B (Data & Analysis)
      ↓ Team B Supervisor
      ├─ Data Analyst
      └─ Statistician
   ```

2. **Delegation Flow**:
   ```
   Top Supervisor → Delegates to Team A
      ↓
   Team A Supervisor → Delegates to Researcher
      ↓
   Researcher → Executes research
      ↓
   Results back to Team A Supervisor
      ↓
   Team A Supervisor → Delegates to Writer
      ↓
   Writer → Creates report
      ↓
   Results back to Top Supervisor
   ```

3. **Distributed Planning**:
   - Top supervisor creates high-level plan
   - Team supervisors create team-specific plans
   - Individual agents create execution plans
   - Three levels of planning independence

4. **State Management**:
   - Each level maintains its own state
   - Messages flow between levels
   - Context preserved across delegation boundaries

---

## Schema Design Recommendation

**Recommended State Architecture**:

```python
# Level 1: Top Supervisor State
class TopState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    high_level_plan: dict
    remaining_teams: List[str]  # OK at top level

# Level 2: Team State (NO managed channels from parent)
class TeamState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    team_plan: dict
    # NO remaining_teams here!

# Level 3: Agent State (NO managed channels)
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    agent_context: dict
    # Only agent-specific state
```

**Key Principle**: Each subgraph level should only contain state relevant to that level, not inherited managed channels from parent levels.

---

## Priority

**Priority**: 🔴 HIGH - Blocks testing of most complex configuration

**Estimated Fix Time**: 15-30 minutes (requires careful state schema refactoring)

**Complexity**: HIGH - Hierarchical teams are the most complex pattern, requiring careful state management across multiple graph levels.

**Test Viability**: Once schema issue is fixed, this configuration should demonstrate excellent distributed planning with three levels of independence. However, additional issues may emerge due to complexity.

**Recommendation**: Fix this configuration AFTER simpler configs (1-4) are working, as lessons learned from simpler patterns will help debug hierarchical issues.

---

## Additional Notes

**LangGraph Version Sensitivity**: This error is specific to LangGraph v0.2+ which has stricter schema validation. Earlier versions might have allowed managed channels in subgraphs.

**Documentation Reference**: See LangGraph docs on subgraphs and state management:
- https://langchain-ai.github.io/langgraph/how-tos/subgraph/
- https://langchain-ai.github.io/langgraph/concepts/low_level/#state-schema

**Testing Strategy**: Once fixed, test incrementally:
1. Test Team A subgraph in isolation
2. Test Team B subgraph in isolation
3. Test top supervisor → Team A delegation
4. Test top supervisor → Team B delegation
5. Test full hierarchical flow
