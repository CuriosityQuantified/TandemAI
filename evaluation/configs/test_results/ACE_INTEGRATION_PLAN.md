# ACE Integration Plan for Researcher Agent

**Created**: November 13, 2025
**Author**: Claude Code (Sonnet 4.5)
**Context**: V4.1 implementation complete, 70-80% completion rate achieved, targeting 90%+ with ACE integration
**Estimated Total Effort**: 12-15 hours over 3-4 days

---

## Executive Summary

The ACE (Autonomous Cognitive Entity) framework provides a sophisticated self-improvement system for AI agents through reflection, curation, and progressive context management. This plan outlines integration of ACE components into the researcher agent to address the persistent 66.7% completion problem on complex 6-7 step tasks (Tests 05/07).

**Current State:**
- **V4.1 Performance**: 75-80% full completion expected (up from V3's 70%)
- **Blocker**: Tests 05/07 consistently stop at 66.7% (4/6 steps completed)
- **Root Cause**: Prompt engineering has reached Haiku 3.5's ~500-550 line ceiling

**ACE Solution:**
Rather than expanding the prompt further (which caused V4's regressions), ACE provides:
1. **Self-Reflection**: Post-execution analysis of what worked/failed
2. **Progressive Learning**: Playbook that improves with each execution
3. **Dynamic Context**: Adaptive prompt injection based on learned patterns
4. **Semantic Memory**: De-duplicated insights prevent context bloat

**Expected Impact:**
- **Minimum Success**: 80-85% full completion (Tests 05/07 improve to 80-90%)
- **Ideal Success**: 90%+ full completion (generalized completion improvement)
- **Stretch Goal**: 95%+ with learned strategies for common failure patterns

**Key Insight**: ACE doesn't add more instructions—it learns which instructions work and surfaces them contextually. This bypasses the prompt length ceiling by replacing static guidelines with dynamic, evidence-based insights.

---

## Current State Analysis

### Researcher Agent Performance

**V3 (Baseline):**
- Full completion: 70% (7/10 tests)
- Average completion: 79.33%
- Prompt length: ~460 lines
- **Failures**: Tests 03 (0%), 05 (66.7%), 07 (66.7%)

**V4 (Over-Engineered):**
- Full completion: 60% (6/10 tests) ❌ REGRESSION
- Average completion: 84.90%
- Prompt length: ~630 lines (exceeded Haiku 3.5 ceiling)
- **New Failures**: Tests 02 (-40%), 10 (-57.1%) catastrophic regressions
- **Success**: Test 03 fixed (0% → 100%) via Planning Gate

**V4.1 (Recommended - Planning Gate Only):**
- Full completion: 75-80% expected (estimate based on surgical enhancement)
- Average completion: 85-90% expected
- Prompt length: ~515 lines (safe threshold)
- **Fixes**: Test 03 (Planning Gate works)
- **Maintains**: Tests 02, 10 (no regression from prompt bloat)
- **Unresolved**: Tests 05, 07 still at 66.7% (core problem)

### Completion Problem Deep Dive

**Test 05: Comparison Query** ("Compare LangChain vs LlamaIndex vs CrewAI")
- V3: 66.7% (4/6 steps) - Stops after initial research
- V4: 80% (4/5 steps) - Better plan structure, still incomplete
- **Pattern**: Completes comparison research, stops before synthesis comparison

**Test 07: Technical Deep-Dive** ("Quantum error correction 2024-2025")
- V3: 66.7% (4/6 steps) - Stops after gathering sources
- V4: 66.7% (4/6 steps) - Same failure, +70s execution time (no improvement)
- **Pattern**: Completes technical research, stops before verification/synthesis

**Commonalities:**
1. Both are 6-step plans (longer horizon)
2. Both stop at step 4 (after ~3-4 tool calls)
3. Both fail at cognitive transition points (gather → analyze)
4. Per-step "Continue to Step X" reminders ignored in V4

**Root Cause Hypothesis:**
The agent experiences **attention decay** after 3-4 tool calls and **context exhaustion** from long prompts. At cognitive transition points (research → analysis), the synthesis instinct from the main prompt overrides completion directives.

### Why Prompt Engineering Alone Failed

**V4 Evidence:**
1. **Prompt length ceiling**: 630 lines exceeded Haiku 3.5's attention span
2. **Tool response salience**: Per-step reminders buried in tool output ignored
3. **Competing priorities**: 171 lines of guidelines created decision paralysis
4. **Fast failures**: Test 10 stopped in 52s (vs V3's 220s) - premature abandonment

**Implication**: More instructions ≠ better performance. Haiku 3.5 needs:
- Shorter, higher-signal prompts (~500 lines max)
- Dynamic context (not static mega-prompt)
- Evidence-based learning (not manual guidelines)

---

## ACE Framework Components

### Available Components (from `/backend/ace/`)

#### 1. **Reflector** (`reflector.py`)
**Purpose**: Post-execution analysis to generate structured insights

**Key Features:**
- Two-pass workflow: Claude free reasoning → Osmosis extraction
- +284% accuracy improvement on complex reasoning (AIME benchmark)
- Identifies HELPFUL, HARMFUL, and NEUTRAL patterns
- Generates actionable recommendations

**Example Insight:**
```python
ReflectionInsight(
    content="Stopping at 4/6 steps occurs when agent completes initial research. "
            "The synthesis instinct from main prompt overrides continuation directives.",
    category="harmful",
    confidence_score=0.85,
    recommendation="Add explicit transition marker before step 5: "
                   "'CRITICAL: You are 66% complete. Continue to Step 5 (analysis phase).'"
)
```

**Current Integration**: None (ACE disabled for all agents)

#### 2. **Curator** (`curator.py`)
**Purpose**: Generate playbook updates from reflection insights

**Key Features:**
- Semantic de-duplication (0.85 similarity threshold)
- Delta updates (add/update/remove, not full rewrites)
- Prevents redundant entries via embeddings
- Maintains playbook quality through pruning

**Example Curation:**
```python
PlaybookDelta(
    add=[
        PlaybookEntry(
            content="After completing 4 research steps, explicitly state 'Step 5 begins NOW' "
                    "to prevent premature synthesis",
            category="helpful",
            confidence_score=0.75,
            tags=["continuation", "multi-step", "transition"]
        )
    ],
    update=[],
    remove=[]
)
```

**Current Integration**: None

#### 3. **Middleware** (`middleware.py`)
**Purpose**: Non-invasive wrapper for agent nodes with ACE capabilities

**Key Features:**
- Wraps existing nodes without modifying core logic
- Async reflection (doesn't block user responses)
- Per-agent configuration (gradual rollout)
- Playbook injection into system prompt

**Integration Points:**
```python
# Before execution: Inject playbook
enhanced_state = await middleware._inject_playbook(state, playbook, "researcher", config)

# During execution: Agent runs normally (no changes)
result_state = await researcher_node(enhanced_state)

# After execution: Async reflection + curation
asyncio.create_task(middleware._reflect_and_update(trace, exec_id, "researcher", config))
```

**Current Integration**: Available but not activated

#### 4. **PlaybookStore** (`playbook_store.py`)
**Purpose**: LangGraph Store wrapper for playbook persistence

**Key Features:**
- Namespace isolation per agent
- Version history tracking
- Pruning for quality control
- Search/filter capabilities

**Storage Structure:**
```
("ace", "playbooks", "researcher")
  └── v1: PlaybookState (version 1)
  └── v2: PlaybookState (version 2)
  └── vN: PlaybookState (current)
```

**Current Integration**: Available but empty

#### 5. **Schemas** (`schemas.py`)
**Purpose**: Type definitions for playbook entries, insights, deltas

**Key Structures:**
- `PlaybookEntry`: Individual learned strategies
- `ReflectionInsight`: Insights from reflector
- `PlaybookDelta`: Incremental updates
- `format_playbook_for_prompt()`: Compact injection format

**Current Integration**: Available

#### 6. **OsmosisExtractor** (`osmosis_extractor.py`)
**Purpose**: Post-hoc structured extraction from free-form LLM output

**Key Features:**
- Two-pass workflow: reasoning first, structure second
- Local Ollama deployment (zero cost)
- Fallback to Claude structured output
- +284% accuracy vs. constrained generation

**Current Integration**: Available, used by Reflector/Curator

### ACE Configuration Status

From `ace/config.py`:

```python
ACE_CONFIGS = {
    "supervisor": ACEConfig(
        enabled=True,  # ✅ RE-ENABLED
        playbook_id="supervisor_v1",
        max_playbook_entries=200,
    ),
    "researcher": ACEConfig(
        enabled=False,  # ❌ DISABLED - target for integration
        playbook_id="researcher_v1",
        max_playbook_entries=150,
        max_playbook_entries_in_prompt=12,
        prune_threshold=0.90,
        reflection_mode="automatic",
    ),
    # ... other agents disabled
}
```

**Rollout Status:**
- **Phase 1**: Infrastructure setup ✅ Complete
- **Phase 2**: Observe mode for all agents ❌ Not started
- **Phase 3**: Researcher automatic mode ❌ Not started (THIS PLAN)
- **Phase 5**: Full rollout (all 6 agents) ❌ Not started

---

## Problem-Solution Mapping

| Problem | ACE Solution | Component | Expected Impact |
|---------|--------------|-----------|-----------------|
| **Tests 05/07 stop at 66.7%** | Learn "continue after step 4" pattern, inject reminder at transition point | Reflector + Middleware | +15-25% (66.7% → 80-90%) |
| **Test 03 planning failure** | Already fixed in V4.1 (Planning Gate), ACE can learn timing patterns | Reflector | Reinforcement of existing fix |
| **Prompt length ceiling (500-550 lines)** | Replace static guidelines with dynamic playbook (10-15 entries @ runtime) | Middleware + PlaybookStore | Maintain ~515 lines total |
| **Tool response salience (reminders ignored)** | Inject learned patterns into system prompt (higher salience) | Middleware._inject_playbook() | +10-20% instruction adherence |
| **Cognitive transition failures** | Identify transition points via reflection, add explicit markers | Reflector + Curator | +20-30% completion at transitions |
| **Inconsistent step counts (Test 07: 5 vs 6 steps)** | Learn optimal step counts for query types via success tracking | Reflector + PlaybookEntry.confidence | +5-10% planning consistency |
| **Complex query fast failures (Test 10)** | Early pattern recognition: "comprehensive survey → 7-step plan" | Curator (semantic similarity) | Prevention of premature shortcuts |
| **No learning across executions** | Persistent playbook accumulates proven strategies | PlaybookStore | Continuous improvement over time |

**Priority Ranking:**
1. **Highest Impact**: Tests 05/07 continuation problem (15-25% improvement potential)
2. **High Impact**: Tool response salience (10-20% improvement)
3. **Medium Impact**: Cognitive transition markers (20-30% at transitions = ~5-10% overall)
4. **Continuous**: Learning accumulation (compounds over time)

---

## Integration Architecture

### Proposed Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Research Agent                      │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    ACE Middleware Wrapper                   │ │
│  │                                                              │ │
│  │  PRE-EXECUTION PHASE                                        │ │
│  │  ┌──────────────────────────────────────┐                  │ │
│  │  │ 1. Load Playbook from Store          │                  │ │
│  │  │    (researcher_v1, latest version)   │                  │ │
│  │  └──────────────────────────────────────┘                  │ │
│  │                    ↓                                         │ │
│  │  ┌──────────────────────────────────────┐                  │ │
│  │  │ 2. Format Top 12 Entries             │                  │ │
│  │  │    (sorted by confidence × count)    │                  │ │
│  │  └──────────────────────────────────────┘                  │ │
│  │                    ↓                                         │ │
│  │  ┌──────────────────────────────────────┐                  │ │
│  │  │ 3. Inject into System Prompt         │                  │ │
│  │  │    (append to existing prompt)       │                  │ │
│  │  └──────────────────────────────────────┘                  │ │
│  │                                                              │ │
│  │  EXECUTION PHASE (unchanged)                                │ │
│  │  ┌──────────────────────────────────────┐                  │ │
│  │  │ 4. Researcher Node Executes          │                  │ │
│  │  │    (with playbook-enhanced prompt)   │                  │ │
│  │  └──────────────────────────────────────┘                  │ │
│  │                                                              │ │
│  │  POST-EXECUTION PHASE (async, non-blocking)                │ │
│  │  ┌──────────────────────────────────────┐                  │ │
│  │  │ 5. Build Execution Trace             │                  │ │
│  │  │    (messages, tool calls, errors)    │                  │ │
│  │  └──────────────────────────────────────┘                  │ │
│  │                    ↓                                         │ │
│  │  ┌──────────────────────────────────────┐                  │ │
│  │  │ 6. Reflector Analyzes Trace          │                  │ │
│  │  │    Pass 1: Claude free reasoning     │                  │ │
│  │  │    Pass 2: Osmosis extraction        │                  │ │
│  │  └──────────────────────────────────────┘                  │ │
│  │                    ↓                                         │ │
│  │  ┌──────────────────────────────────────┐                  │ │
│  │  │ 7. Curator Generates Delta           │                  │ │
│  │  │    (add/update/remove entries)       │                  │ │
│  │  └──────────────────────────────────────┘                  │ │
│  │                    ↓                                         │ │
│  │  ┌──────────────────────────────────────┐                  │ │
│  │  │ 8. Apply Delta to Playbook           │                  │ │
│  │  │    (save to PlaybookStore)           │                  │ │
│  │  └──────────────────────────────────────┘                  │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Integration Points

#### Point 1: Import ACE Components
**File**: `/backend/module_2_2_simple.py` (or wherever researcher graph is defined)
**Line**: ~20-30 (with other imports)
**Changes**:
```python
from ace import ACEMiddleware, PlaybookStore, ACE_CONFIGS
from ace.config import enable_ace_for_agent
from langgraph.store.memory import InMemoryStore  # or PostgresStore for production
```

#### Point 2: Initialize ACE Components
**File**: `/backend/module_2_2_simple.py`
**Function**: Graph builder or app initialization
**Changes**:
```python
# Initialize ACE Store (in-memory for testing, Postgres for production)
ace_store = InMemoryStore()

# Initialize ACE Middleware with researcher config
ace_middleware = ACEMiddleware(
    store=ace_store,
    configs=ACE_CONFIGS,
    osmosis_mode="ollama",  # Local, zero-cost
)

# Enable ACE for researcher (Phase 3)
enable_ace_for_agent("researcher", mode="automatic")
```

#### Point 3: Wrap Researcher Node
**File**: Where researcher node is added to graph
**Changes**:
```python
# Before (V4.1):
graph.add_node("researcher", researcher_node)

# After (ACE-enabled):
wrapped_researcher = ace_middleware.wrap_node(researcher_node, "researcher")
graph.add_node("researcher", wrapped_researcher)
```

#### Point 4: Ensure SystemMessage Exists
**File**: `prompts/researcher.py` or wherever researcher prompt is built
**Validation**:
```python
# ACE middleware requires first message to be SystemMessage
# Ensure researcher prompt returns messages list starting with SystemMessage
def get_researcher_prompt(date: str) -> str:
    # ... existing prompt logic
    # Returns string that will be wrapped in SystemMessage by researcher node

# In researcher_node:
from langchain_core.messages import SystemMessage
messages = state.get("messages", [])
if not messages or not isinstance(messages[0], SystemMessage):
    messages = [SystemMessage(content=get_researcher_prompt(date))] + messages
```

#### Point 5: (Optional) Expose Playbook via API
**File**: `/backend/main.py` (FastAPI endpoints)
**New Endpoints**:
```python
@app.get("/api/ace/playbook/{agent_type}")
async def get_playbook(agent_type: str):
    """Get current playbook for agent."""
    playbook = await ace_middleware.playbook_store.get_playbook(agent_type)
    return playbook

@app.get("/api/ace/stats/{agent_type}")
async def get_playbook_stats(agent_type: str):
    """Get playbook statistics."""
    stats = await ace_middleware.playbook_store.get_playbook_stats(agent_type)
    return stats
```

---

## Implementation Plan

### Phase 1: Assessment & Preparation (2 hours)

**Goals:**
- Verify ACE components are functional
- Identify exact integration points in current codebase
- Set up testing infrastructure

#### Tasks:

**Task 1.1: Verify ACE Component Functionality** (30 min)
```bash
cd /Users/.../backend/ace
python reflector.py  # Run example()
python curator.py    # Run example()
python playbook_store.py  # Run example()
```
- **Expected**: All components run without errors
- **Deliverable**: Component health check report

**Task 1.2: Analyze Researcher Graph Structure** (30 min)
- Read `/backend/module_2_2_simple.py` (or actual graph file)
- Identify where researcher node is defined and added to graph
- Verify message structure (SystemMessage first?)
- **Deliverable**: Integration point documentation

**Task 1.3: Set Up ACE Testing Environment** (30 min)
```bash
# Ensure Ollama is running (for OsmosisExtractor)
ollama list  # Should show Osmosis/Osmosis-Structure-0.6B

# If not available, pull it
ollama pull osmosis/osmosis-structure-0.6b

# Test Osmosis extraction
cd /backend/ace
python osmosis_extractor.py
```
- **Expected**: Osmosis model available, extraction works
- **Deliverable**: Osmosis readiness confirmation

**Task 1.4: Create ACE Test Suite** (30 min)
- Copy V4.1 test suite (10 prompts)
- Add ACE-specific metrics:
  - Playbook entry count before/after
  - Reflection insight count per execution
  - Curation delta size (add/update/remove)
  - Prompt length with playbook injection
- **Deliverable**: `ace_test_runner.py` script

#### Phase 1 Deliverables:
- [ ] Component health check report
- [ ] Integration point documentation
- [ ] Osmosis readiness confirmation
- [ ] ACE test runner script

---

### Phase 2: Core Integration (4-6 hours)

**Goals:**
- Wrap researcher node with ACE middleware
- Enable reflection and curation
- Verify playbook persistence

#### Tasks:

**Task 2.1: Import ACE Components** (15 min)
**File**: `/backend/module_2_2_simple.py` (or graph definition file)
```python
from ace import ACEMiddleware, PlaybookStore, ACE_CONFIGS
from ace.config import enable_ace_for_agent
from langgraph.store.memory import InMemoryStore
```
- **Test**: Imports succeed, no errors
- **Commit**: `git commit -m "feat: Import ACE components for researcher integration"`

**Task 2.2: Initialize ACE Store and Middleware** (30 min)
Add after graph initialization:
```python
# Initialize ACE Store (in-memory for Phase 2, Postgres in Phase 4)
ace_store = InMemoryStore()

# Initialize ACE Middleware
ace_middleware = ACEMiddleware(
    store=ace_store,
    configs=ACE_CONFIGS,
    osmosis_mode="ollama",
)

# Enable researcher in automatic mode
enable_ace_for_agent("researcher", mode="automatic")
```
- **Test**: Middleware initializes, no errors
- **Log Output**: "Initialized ACEMiddleware..." and "ACE enabled for researcher..."
- **Commit**: `git commit -m "feat: Initialize ACE middleware for researcher"`

**Task 2.3: Wrap Researcher Node** (30 min)
Replace:
```python
graph.add_node("researcher", researcher_node)
```
With:
```python
wrapped_researcher = ace_middleware.wrap_node(researcher_node, "researcher")
graph.add_node("researcher", wrapped_researcher)
```
- **Test**: Graph compiles, researcher still accessible
- **Commit**: `git commit -m "feat: Wrap researcher node with ACE middleware"`

**Task 2.4: Verify SystemMessage Structure** (1 hour)
ACE middleware requires first message to be SystemMessage. Check researcher node:
```python
# In researcher_node function (wherever it's defined)
def researcher_node(state: dict):
    messages = state.get("messages", [])

    # Ensure first message is SystemMessage
    if not messages or not isinstance(messages[0], SystemMessage):
        system_prompt = get_researcher_prompt(get_current_date())
        messages = [SystemMessage(content=system_prompt)] + messages
        state["messages"] = messages

    # ... rest of node logic
```
- **Test**: Run single query, check logs for "Injected X playbook entries"
- **Expected**: First run shows 0 entries (playbook empty), no errors
- **Commit**: `git commit -m "fix: Ensure SystemMessage for ACE playbook injection"`

**Task 2.5: Test First Execution with Empty Playbook** (30 min)
```bash
cd /backend
python ace_test_runner.py --test 01 --verbose
```
- **Expected Output**:
  ```
  [exec_researcher_0] Starting execution for researcher
  [exec_researcher_0] Injected 0 playbook entries into system prompt
  [exec_researcher_0] Node execution succeeded
  [exec_researcher_0] Triggered async reflection (mode=automatic)
  [exec_researcher_0] Starting async reflection...
  [exec_researcher_0] Reflection generated N insights
  [exec_researcher_0] Curation delta: +M entries, ~0 updates, -0 removals
  [exec_researcher_0] ✓ Playbook updated (v1, M entries)
  ```
- **Validation**: Check PlaybookStore for entry count
- **Commit**: `git commit -m "test: Verify ACE end-to-end with Test 01"`

**Task 2.6: Test Second Execution with Populated Playbook** (30 min)
```bash
python ace_test_runner.py --test 01 --verbose  # Run same test again
```
- **Expected Output**:
  ```
  [exec_researcher_1] Injected M playbook entries into system prompt
  ```
- **Validation**: Playbook injected into prompt, new insights generated
- **Commit**: `git commit -m "test: Verify ACE playbook persistence and injection"`

**Task 2.7: Run Full Test Suite (V4.1 Baseline)** (1 hour)
```bash
python ace_test_runner.py --all
```
- **Purpose**: Establish ACE-enabled baseline (no learned playbook yet)
- **Expected**: Similar to V4.1 performance (75-80% completion)
- **Metrics to Collect**:
  - Full completion rate
  - Average completion %
  - Playbook entries added per test
  - Reflection insights per test
  - Execution time (expect +5-10s for reflection)
- **Deliverable**: `ace_baseline_results.json`
- **Commit**: `git commit -m "test: ACE-enabled baseline (10 tests, empty playbook)"`

**Task 2.8: Run Second Full Test Suite (With Learned Playbook)** (1 hour)
```bash
python ace_test_runner.py --all  # Run again with learned playbook
```
- **Purpose**: Measure learning effect after 10 executions
- **Expected**: Improvement in Tests 05/07 (playbook learns continuation patterns)
- **Metrics to Collect**:
  - Full completion rate (target: 80-85%)
  - Average completion % (target: 87-92%)
  - Playbook entries count (expect 15-30 entries after 20 tests total)
  - Tests 05/07 specific improvement
- **Deliverable**: `ace_learned_results.json`
- **Commit**: `git commit -m "test: ACE second pass with learned playbook"`

#### Phase 2 Deliverables:
- [ ] ACE components imported
- [ ] ACE middleware initialized
- [ ] Researcher node wrapped
- [ ] SystemMessage structure verified
- [ ] First execution successful (empty playbook)
- [ ] Second execution successful (playbook injection)
- [ ] ACE baseline results (10 tests, empty playbook)
- [ ] ACE learned results (10 tests, populated playbook)

---

### Phase 3: Validation & Optimization (2-3 hours)

**Goals:**
- Analyze playbook quality
- Identify improvement patterns
- Optimize configuration if needed

#### Tasks:

**Task 3.1: Playbook Quality Analysis** (1 hour)
```python
# Create analysis script
import asyncio
from ace import PlaybookStore

async def analyze_playbook():
    store = PlaybookStore()

    # Get playbook
    playbook = await store.get_playbook("researcher")
    stats = await store.get_playbook_stats("researcher")

    print(f"\n=== Researcher Playbook (v{playbook['version']}) ===")
    print(f"Total entries: {stats['total_entries']}")
    print(f"  Helpful: {stats['helpful_entries']}")
    print(f"  Harmful: {stats['harmful_entries']}")
    print(f"  Neutral: {stats['neutral_entries']}")
    print(f"Avg confidence: {stats['avg_confidence']}")
    print(f"Total executions: {stats['total_executions']}")

    print(f"\nTop 10 entries (by confidence):")
    sorted_entries = sorted(
        playbook['entries'],
        key=lambda e: e.confidence_score * e.helpful_count,
        reverse=True
    )
    for i, entry in enumerate(sorted_entries[:10], 1):
        print(f"{i}. [{entry.category}] {entry.confidence_score:.2f}")
        print(f"   {entry.content[:100]}...")
        print(f"   Helpful: {entry.helpful_count}, Harmful: {entry.harmful_count}")

    # Search for continuation-related entries
    continuation_entries = await store.search_entries(
        "researcher",
        query="continue",
        min_confidence=0.6
    )
    print(f"\n{len(continuation_entries)} continuation-related entries found")
    for entry in continuation_entries:
        print(f"  - {entry.content[:80]}...")

asyncio.run(analyze_playbook())
```
- **Purpose**: Understand what patterns ACE learned
- **Look For**:
  - Entries about "continue to step X"
  - Entries about "4/6 steps stopping pattern"
  - Entries about tool response adherence
- **Deliverable**: `playbook_analysis_report.md`

**Task 3.2: Compare ACE vs V4.1 Performance** (30 min)
```python
# Create comparison script
import json

def compare_results():
    with open('v4_1_results.json') as f:
        v4_1 = json.load(f)

    with open('ace_learned_results.json') as f:
        ace = json.load(f)

    print("\n=== V4.1 vs ACE Comparison ===")
    print(f"\nFull Completion Rate:")
    print(f"  V4.1: {v4_1['full_completion_rate']}")
    print(f"  ACE:  {ace['full_completion_rate']}")
    print(f"  Δ:    {ace['full_completion_rate'] - v4_1['full_completion_rate']:+.1%}")

    print(f"\nTest 05 (Comparison):")
    print(f"  V4.1: {v4_1['test_05']['completion_pct']:.1f}%")
    print(f"  ACE:  {ace['test_05']['completion_pct']:.1f}%")
    print(f"  Δ:    {ace['test_05']['completion_pct'] - v4_1['test_05']['completion_pct']:+.1f}%")

    print(f"\nTest 07 (Deep-Dive):")
    print(f"  V4.1: {v4_1['test_07']['completion_pct']:.1f}%")
    print(f"  ACE:  {ace['test_07']['completion_pct']:.1f}%")
    print(f"  Δ:    {ace['test_07']['completion_pct'] - v4_1['test_07']['completion_pct']:+.1f}%")

compare_results()
```
- **Success Criteria**:
  - **Minimum**: Tests 05/07 improve by +10-15% (66.7% → 75-80%)
  - **Ideal**: Tests 05/07 improve to 90%+ (matches success target)
  - **Overall**: Full completion rate ≥80%
- **Deliverable**: `v4_1_vs_ace_comparison.md`

**Task 3.3: Identify Regressions (If Any)** (30 min)
```python
# Check if any previously passing tests regressed
def check_regressions():
    # ... load results
    for test_id in range(1, 11):
        v4_1_pct = v4_1[f'test_{test_id:02d}']['completion_pct']
        ace_pct = ace[f'test_{test_id:02d}']['completion_pct']

        if v4_1_pct == 100 and ace_pct < 100:
            print(f"⚠️  REGRESSION: Test {test_id:02d} ({v4_1_pct:.0f}% → {ace_pct:.0f}%)")
            print(f"   Investigate playbook injection impact")
```
- **If Regressions Found**: Analyze playbook entries for harmful patterns
- **Mitigation**: Prune low-confidence entries, adjust similarity threshold
- **Deliverable**: Regression analysis (if needed)

**Task 3.4: Optimize ACE Configuration (If Needed)** (1 hour)
Based on results, adjust `/backend/ace/config.py`:
```python
"researcher": ACEConfig(
    enabled=True,
    playbook_id="researcher_v1",

    # Playbook size optimization
    max_playbook_entries=150,  # Default
    # → If playbook bloats too much, reduce to 100
    # → If too few insights, increase to 200

    max_playbook_entries_in_prompt=12,  # Default
    # → If prompt too long (>530 lines), reduce to 8-10
    # → If insights not having effect, increase to 15

    # De-duplication threshold
    prune_threshold=0.90,  # Default
    # → If too many similar entries, increase to 0.95
    # → If pruning too aggressively, decrease to 0.85

    semantic_similarity_threshold=0.85,  # Default (for curator)
    # → If duplicate insights being added, increase to 0.90
    # → If missing useful variations, decrease to 0.80

    reflection_mode="automatic",  # Default
    # → If reflection errors occurring, switch to "observe" temporarily
)
```
- **Re-test**: Run full suite again with optimized config
- **Deliverable**: Optimized ACE config + results
- **Commit**: `git commit -m "perf: Optimize ACE config for researcher"`

**Task 3.5: Long-Horizon Stress Test** (30 min)
Create new test with 10-step plan (longer than any current test):
```python
test_prompt = """
Conduct a comprehensive analysis of AI safety approaches from 2020-2025:
1. Technical approaches (alignment, interpretability, robustness)
2. Governance approaches (regulation, standards, auditing)
3. Industry initiatives (safety teams, responsible AI programs)
4. Academic research trends (top conferences, citation networks)
5. Failed approaches and lessons learned
6. Current debates and open problems
7. Future directions and recommendations

Provide detailed citations for all claims. Minimum 20 sources.
"""
```
- **Purpose**: Test if ACE helps with very long horizon tasks (10+ steps)
- **Baseline**: V4.1 likely to fail or complete <70%
- **ACE Target**: ≥80% completion with learned continuation patterns
- **Deliverable**: Long-horizon test results

#### Phase 3 Deliverables:
- [ ] Playbook analysis report
- [ ] V4.1 vs ACE comparison
- [ ] Regression analysis (if applicable)
- [ ] Optimized ACE configuration
- [ ] Long-horizon stress test results

---

### Phase 4: Production Deployment (1 hour)

**Goals:**
- Switch to persistent storage (PostgreSQL)
- Deploy to production environment
- Set up monitoring

#### Tasks:

**Task 4.1: Migrate to PostgreSQL Store** (30 min)
Replace InMemoryStore with production store:
```python
# Before (Phase 2):
from langgraph.store.memory import InMemoryStore
ace_store = InMemoryStore()

# After (Phase 4):
from langgraph.store.postgres import PostgresStore
ace_store = PostgresStore(
    connection_string="postgresql://localhost/postgres",
    namespace_separator=":",
)
```
- **Test**: Run single query, verify playbook persists across restarts
- **Migration**: Export InMemoryStore data, import to PostgresStore
- **Commit**: `git commit -m "feat: Migrate ACE to PostgreSQL for production persistence"`

**Task 4.2: Add Playbook API Endpoints** (15 min)
In `/backend/main.py`:
```python
@app.get("/api/ace/playbook/{agent_type}")
async def get_playbook(agent_type: str):
    """Get current playbook for agent type."""
    playbook = await ace_middleware.playbook_store.get_playbook(agent_type)
    return {
        "agent_type": agent_type,
        "version": playbook["version"],
        "entries_count": len(playbook["entries"]),
        "total_executions": playbook["total_executions"],
        "entries": [
            {
                "id": e.id,
                "content": e.content,
                "category": e.category,
                "confidence": e.confidence_score,
                "helpful_count": e.helpful_count,
                "harmful_count": e.harmful_count,
                "tags": e.tags,
            }
            for e in playbook["entries"][:20]  # Top 20
        ]
    }

@app.get("/api/ace/stats/{agent_type}")
async def get_ace_stats(agent_type: str):
    """Get playbook statistics."""
    return await ace_middleware.playbook_store.get_playbook_stats(agent_type)
```
- **Test**: `curl http://localhost:8000/api/ace/playbook/researcher`
- **Expected**: JSON response with playbook data
- **Commit**: `git commit -m "feat: Add ACE playbook API endpoints"`

**Task 4.3: Set Up Monitoring** (15 min)
Add logging for ACE metrics:
```python
import logging
logger = logging.getLogger("ace_monitoring")

# After each execution (in middleware):
logger.info(
    "ACE Execution Complete",
    extra={
        "execution_id": execution_id,
        "agent_type": agent_type,
        "playbook_version": playbook["version"],
        "playbook_entries_count": len(playbook["entries"]),
        "insights_generated": len(insights),
        "delta_add": len(delta.add),
        "delta_update": len(delta.update),
        "delta_remove": len(delta.remove),
    }
)
```
- **Integration**: Send to logging service (Datadog, CloudWatch, etc.)
- **Dashboards**: Create ACE monitoring dashboard
- **Commit**: `git commit -m "feat: Add ACE execution monitoring"`

#### Phase 4 Deliverables:
- [ ] PostgreSQL store migration
- [ ] Playbook API endpoints
- [ ] ACE monitoring setup
- [ ] Production deployment successful

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Osmosis model not available in Ollama** | Medium | High | Use fallback: Claude structured output (built into OsmosisExtractor) |
| **Playbook bloat (>150 entries)** | Medium | Medium | Automatic pruning at max_entries threshold, adjust in config |
| **Reflection too slow (>10s per execution)** | Low | Medium | Background async execution (doesn't block user), optimize reflection prompt |
| **Playbook injection exceeds prompt length ceiling** | Medium | High | Limit to 12 entries max, monitor total prompt length (~515 + 100 = ~615 lines at risk) |
| **ACE introduces new regressions** | Medium | High | A/B test on 50% traffic initially, rollback if completion rate drops >5% |
| **No improvement after 20 executions** | Medium | High | Fall back to Phase 2B (Lightweight Supervisor), consider model upgrade |
| **Reflection generates low-quality insights** | Low | Medium | Curator filters by confidence threshold (0.75 default), manual review first 10 |
| **Semantic de-duplication too aggressive** | Low | Low | Adjust similarity_threshold from 0.85 → 0.80, monitor entry diversity |

**Rollback Strategy:**
1. **Trigger**: Full completion rate drops below 70% (worse than V3 baseline)
2. **Action**: Disable ACE for researcher: `ACE_CONFIGS["researcher"].enabled = False`
3. **Fallback**: Return to V4.1 (Planning Gate only)
4. **Timeline**: Rollback within 5 minutes (config change only, no code changes)

---

## Success Criteria

### Minimum Success (Deployment-Ready)
- [ ] **Full completion rate ≥80%** (vs V4.1's 75-80%)
- [ ] **Tests 05/07 improve to ≥80%** (up from 66.7%)
- [ ] **No regressions >10%** in currently passing tests (Tests 01, 02, 04, 06, 08, 09, 10)
- [ ] **Playbook quality ≥0.7** (avg confidence score)
- [ ] **Execution time increase <20%** (reflection overhead acceptable)

**Deployment Decision**: If all minimum criteria met → deploy to production

### Ideal Success (ACE Validates Concept)
- [ ] **Full completion rate ≥90%** (9/10 tests complete)
- [ ] **Tests 05/07 achieve 100%** (playbook learns continuation strategy)
- [ ] **Maintained or improved execution time** (parallelization offsets reflection cost)
- [ ] **Playbook contains actionable insights** (manual review: ≥70% useful entries)
- [ ] **Generalizes to new test prompts** (test on 5 unseen prompts, ≥80% completion)

**Decision**: If all ideal criteria met → ACE is working as intended, proceed to Phase 5 (other agents)

### Stretch Goals (Research Publication Quality)
- [ ] **Full completion rate ≥95%** (only 1 failure allowed in 20 tests)
- [ ] **All 10 original tests achieve 100%**
- [ ] **Reduced prompt engineering dependency** (playbook replaces static guidelines)
- [ ] **Transfer learning validated** (export playbook, apply to new agent, observe benefit)
- [ ] **Long-horizon tasks (10+ steps) ≥90%** (stress test passes)

**Decision**: If all stretch goals met → Write academic paper on ACE + prompt engineering limits

---

## Testing Strategy

### Pre-Integration Baseline (V4.1)

**Setup:**
```bash
cd /backend
git checkout v4.1  # Or whatever branch has V4.1 (Planning Gate only)
python test_runner.py --all --output v4_1_baseline.json
```

**Metrics to Capture:**
- Full completion rate (expected: 75-80%)
- Average completion % (expected: 85-90%)
- Test 05 completion (expected: 80%)
- Test 07 completion (expected: 66.7%)
- Average execution time per test
- Total messages per test
- Total searches per test

**Purpose**: Establish clear baseline to measure ACE impact against

### Post-Integration Validation (First Pass - Empty Playbook)

**Setup:**
```bash
git checkout ace-integration  # New branch with ACE enabled
python ace_test_runner.py --all --output ace_empty_playbook.json
```

**Expected Results:**
- Similar to V4.1 baseline (no playbook yet)
- +5-10s execution time (reflection overhead)
- Playbook entries created (expect 10-30 total after 10 tests)
- Reflection insights logged

**Purpose**: Verify ACE integration doesn't break existing functionality

### Post-Integration Validation (Second Pass - Learned Playbook)

**Setup:**
```bash
# Run same tests again (playbook now populated)
python ace_test_runner.py --all --output ace_learned_playbook.json
```

**Expected Results:**
- **Improvement** in Tests 05/07 (playbook learns continuation patterns)
- Full completion rate ≥80%
- Playbook injection visible in logs ("Injected X entries")
- Minimal additional execution time (playbook already built)

**Purpose**: Measure learning effect of populated playbook

### Iteration Protocol

**If Improvement <5%:**
```bash
# Analyze playbook quality
python analyze_playbook.py

# Check for:
# 1. Are insights being generated? (check logs)
# 2. Are insights relevant? (manual review)
# 3. Is playbook being injected? (check state)
# 4. Is prompt too long? (measure total length)

# Adjust ACE config if needed:
# - Reduce max_playbook_entries_in_prompt (12 → 8)
# - Increase min_confidence for injection (0.5 → 0.7)
# - Adjust reflection_mode (automatic → observe for debugging)

# Re-test with adjusted config
```

**If Improvement ≥15%:**
```bash
# Success! Proceed to production deployment (Phase 4)
# Document learnings:
python generate_ace_report.py > ACE_INTEGRATION_RESULTS.md
```

**If Regressions >10%:**
```bash
# Rollback immediately
# Disable ACE for researcher
# Investigate which playbook entries caused regression
# Prune harmful entries, re-test
```

---

## Alternative Approaches (If ACE Insufficient)

### Option A: Model Upgrade (Haiku 3.5 → Sonnet 3.5)

**When to Consider**: ACE improves completion by <10%, still below 85% target

**Rationale:**
- Haiku 3.5's 8K context window may be fundamental limitation
- Sonnet 3.5 has 200K context (25x larger)
- Better instruction-following → obeys tool responses more reliably
- Handles complex queries without fast-failure pattern

**Cost Analysis:**
```
Haiku 3.5:  $0.003/1K input tokens, $0.015/1K output tokens
Sonnet 3.5: $0.03/1K input tokens, $0.15/1K output tokens

Typical research query:
- Input: ~2K tokens (prompt + query)
- Output: ~1K tokens (research report)
- Haiku cost: $0.006 + $0.015 = $0.021 per query
- Sonnet cost: $0.06 + $0.15 = $0.21 per query
- Cost increase: 10x

Monthly volume estimate (1000 queries/month):
- Haiku: $21/month
- Sonnet: $210/month
- Increase: +$189/month
```

**Pros:**
- Likely achieves ≥90% completion (Sonnet much better at long-horizon tasks)
- Solves problem immediately (no gradual learning curve)
- Better reasoning quality overall

**Cons:**
- 10x cost increase
- Slower responses (30-60s → 60-120s)
- Doesn't address root cause (prompt engineering limits)

**Testing Strategy:**
- A/B test on 10% traffic
- Measure completion improvement vs cost
- **Decision threshold**: If Sonnet achieves ≥90% completion → worth cost for production queries

### Option B: Two-Tier Agent System (Haiku Planner + Sonnet Executor)

**When to Consider**: ACE + Haiku achieves 80-85%, need 90%+ but can't afford 10x cost

**Architecture:**
```
User Query → Haiku 3.5 (Planning) → Sonnet 3.5 (Execution) → Haiku 3.5 (Synthesis)
  ~5s          ~10-20s                  ~50-150s                 ~5-10s

Total cost: ~3x Haiku (vs 10x all-Sonnet)
Completion rate: ~90% (Sonnet execution reliability)
```

**Implementation:**
```python
# Phase 1: Haiku creates plan
planning_llm = ChatAnthropic(model="claude-3-5-haiku-20241022")
plan = await planning_llm.ainvoke([
    SystemMessage(content="Create research plan..."),
    HumanMessage(content=user_query)
])

# Phase 2: Sonnet executes plan
execution_llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
for step in plan.steps:
    result = await execution_llm.ainvoke([
        SystemMessage(content="Execute this research step..."),
        HumanMessage(content=step.description)
    ])
    step.result = result

# Phase 3: Haiku synthesizes
synthesis = await planning_llm.ainvoke([
    SystemMessage(content="Synthesize results into report..."),
    HumanMessage(content=format_step_results(plan.steps))
])
```

**Pros:**
- Balances cost (3x) and quality (90%+)
- Leverages strengths of each model (Haiku planning, Sonnet execution)
- Maintains fast planning and synthesis

**Cons:**
- Added complexity (agent handoff logic)
- Potential consistency issues (different models, different styles)
- ~100 lines of new code

**Estimated Effort**: 4-6 hours implementation + 2 hours testing

### Option C: Accept Current Performance (70-80% with V4.1/ACE)

**When to Consider**: Cost constraints prohibit model upgrade, ACE provides incremental improvement

**Rationale:**
- 70-80% may be Haiku 3.5's ceiling for complex research tasks
- ACE provides continuous improvement over time (playbook accumulates)
- Focus engineering effort on other high-impact areas

**Mitigation Strategies:**
1. **User Communication**: Set expectations ("Most research tasks complete fully, some complex queries may require follow-up")
2. **Resume Functionality**: Save partial progress, allow user to "continue research"
3. **Hybrid Mode**: Offer Sonnet upgrade for complex queries (user pays premium)

**Pros:**
- Realistic about model limitations
- Focuses resources on product features vs. marginal accuracy gains
- ACE still provides value (gradual improvement)

**Cons:**
- 20-30% of queries incomplete (user frustration risk)
- Competitive disadvantage if competitors achieve 90%+
- May need to revisit when better models available

---

## Next Steps (User Approval Required)

### If Plan Approved:

**Immediate (Next 24 hours):**
1. [ ] User reviews this plan
2. [ ] User approves Phase 1-2 execution (or requests modifications)
3. [ ] Execute Phase 1: Assessment & Preparation (2 hours)
4. [ ] Report Phase 1 findings to user
5. [ ] Execute Phase 2: Core Integration (4-6 hours)
6. [ ] Report Phase 2 baseline results to user

**Short-Term (Next 2-3 days):**
1. [ ] Execute Phase 3: Validation & Optimization (2-3 hours)
2. [ ] Generate V4.1 vs ACE comparison report
3. [ ] User reviews results, decides on production deployment
4. [ ] If approved: Execute Phase 4: Production Deployment (1 hour)

**Medium-Term (Next 1-2 weeks):**
1. [ ] Monitor ACE performance in production (10-20 queries/day)
2. [ ] Analyze playbook evolution over 50-100 executions
3. [ ] Decide on Phase 5 rollout (other 5 agents)
4. [ ] Consider alternative approaches if ACE insufficient

### If Plan Not Approved:

**Alternative Paths:**
1. **Path A**: Implement lightweight supervisor (Phase 2B from V3 vs V4 report) instead of ACE
2. **Path B**: Model upgrade to Sonnet 3.5 (A/B test first)
3. **Path C**: Accept V4.1 performance, focus on other features
4. **Path D**: Hybrid approach (ACE for learning + supervisor for enforcement)

**Questions for User:**
1. What is the target completion rate? (80%? 90%? 95%?)
2. What is the budget for model costs? (Haiku-only? Willing to pay 3x? 10x?)
3. What is the timeline? (Ship fast with 80%? Wait for 90%+?)
4. What is the risk tolerance? (Production experiment ACE? A/B test first?)

---

## Appendices

### A: ACE Component Catalog

**1. Reflector** (`ace/reflector.py`)
- **Lines**: 462
- **Key Classes**: `Reflector`
- **Key Methods**: `analyze()`, `refine_insights()`, `_build_analysis_prompt()`
- **Dependencies**: Claude Haiku, OsmosisExtractor, ReflectionInsight schema
- **Two-Pass Workflow**: Claude free reasoning (Pass 1) → Osmosis extraction (Pass 2)
- **Proven Accuracy**: +284% on AIME benchmark (complex reasoning)

**2. Curator** (`ace/curator.py`)
- **Lines**: 454
- **Key Classes**: `Curator`
- **Key Methods**: `curate()`, `_deduplicate_insights()`, `_build_curation_prompt()`
- **Dependencies**: Claude Haiku, OsmosisExtractor, Ollama embeddings (nomic-embed-text)
- **Two-Pass Workflow**: Claude curation reasoning → Osmosis delta extraction
- **Semantic De-duplication**: Cosine similarity > 0.85 = duplicate

**3. Middleware** (`ace/middleware.py`)
- **Lines**: 647
- **Key Classes**: `ACEMiddleware`
- **Key Methods**: `wrap_node()`, `_inject_playbook()`, `_reflect_and_update()`, `_apply_delta()`
- **Integration Pattern**: Non-invasive wrapper (no changes to core agent logic)
- **Async Reflection**: Background execution, doesn't block user responses

**4. PlaybookStore** (`ace/playbook_store.py`)
- **Lines**: 437
- **Key Classes**: `PlaybookStore`
- **Key Methods**: `get_playbook()`, `save_playbook()`, `prune_playbook()`, `search_entries()`
- **Storage**: LangGraph Store wrapper (InMemoryStore or PostgresStore)
- **Versioning**: Full version history per agent

**5. Schemas** (`ace/schemas.py`)
- **Lines**: 311
- **Key Classes**: `PlaybookEntry`, `PlaybookState`, `ReflectionInsight`, `PlaybookDelta`
- **Helper Functions**: `create_initial_playbook()`, `format_playbook_for_prompt()`
- **Confidence Calculation**: Laplace smoothing: `(helpful + 1) / (total + 2)`

**6. OsmosisExtractor** (`ace/osmosis_extractor.py`)
- **Lines**: 393
- **Key Classes**: `OsmosisExtractor`
- **Key Methods**: `extract()`, `_extract_ollama()`, `_extract_api()`, `_fallback_parse()`
- **Modes**: "ollama" (local, free) or "api" (hosted, $)
- **Fallback**: Claude structured output if Osmosis fails

**7. Config** (`ace/config.py`)
- **Lines**: 328
- **Key Classes**: `ACEConfig`
- **Per-Agent Configs**: 6 agents (supervisor, researcher, data_scientist, expert_analyst, writer, reviewer)
- **Rollout Helpers**: `enable_phase_2_observe_mode()`, `enable_phase_3_researcher()`, `enable_phase_5_full_rollout()`

### B: Code Integration Examples

**Example 1: Import ACE Components**
```python
# File: /backend/module_2_2_simple.py (or graph definition file)

# Add to imports section (~line 20):
from ace import ACEMiddleware, PlaybookStore, ACE_CONFIGS
from ace.config import enable_ace_for_agent
from langgraph.store.memory import InMemoryStore
```

**Example 2: Initialize ACE Middleware**
```python
# File: /backend/module_2_2_simple.py
# Add after graph initialization, before node definitions

# Initialize ACE Store
ace_store = InMemoryStore()  # Use PostgresStore in production

# Initialize ACE Middleware
ace_middleware = ACEMiddleware(
    store=ace_store,
    configs=ACE_CONFIGS,
    osmosis_mode="ollama",  # Local Osmosis-Structure-0.6B
)

# Enable researcher in automatic mode (Phase 3)
enable_ace_for_agent("researcher", mode="automatic")

print(f"ACE enabled for researcher (playbook: {ACE_CONFIGS['researcher'].playbook_id})")
```

**Example 3: Wrap Researcher Node**
```python
# File: /backend/module_2_2_simple.py
# In graph building section

# Before ACE:
graph.add_node("researcher", researcher_node)

# After ACE:
wrapped_researcher = ace_middleware.wrap_node(researcher_node, "researcher")
graph.add_node("researcher", wrapped_researcher)
```

**Example 4: Ensure SystemMessage for Playbook Injection**
```python
# File: researcher_node function (wherever it's defined)

from langchain_core.messages import SystemMessage
from prompts.researcher import get_researcher_prompt
from utils.date_helper import get_current_date

def researcher_node(state: dict):
    """Researcher node with ACE-compatible SystemMessage."""

    messages = state.get("messages", [])

    # ACE middleware requires first message to be SystemMessage
    if not messages or not isinstance(messages[0], SystemMessage):
        system_prompt = get_researcher_prompt(get_current_date())
        messages = [SystemMessage(content=system_prompt)] + messages
        state["messages"] = messages

    # ... rest of node logic (tools, LLM call, etc.)

    return state
```

**Example 5: Format Playbook for Injection**
```python
# This is handled automatically by ACE middleware, but here's what it does:

from ace.schemas import format_playbook_for_prompt

# Get top 12 playbook entries
formatted_playbook = format_playbook_for_prompt(
    entries=playbook["entries"],
    max_entries=12,
    agent_type="researcher"
)

# Output example:
"""
═══════════════════════════════════════════════════════════════════════════
ACE PLAYBOOK (Learnings from Previous Executions)
═══════════════════════════════════════════════════════════════════════════

**Apply These Patterns:**
1. After completing 4 research steps, explicitly state "Step 5 begins NOW" [success: 85%, confidence: 80%]
2. When approaching synthesis phase, verify plan.steps_completed == plan.num_steps [success: 92%, confidence: 88%]
3. Tool responses containing "Continue to Step X" should be obeyed immediately [success: 78%, confidence: 75%]
...

**Avoid These Patterns:**
1. Synthesizing results before all plan steps are complete [failure count: 7]
2. Ignoring continuation directives in update_plan_progress responses [failure count: 5]
...

Use these learnings to inform your approach on this task.
═══════════════════════════════════════════════════════════════════════════
"""

# This gets appended to the existing researcher system prompt
enhanced_prompt = original_prompt + "\n" + formatted_playbook
```

**Example 6: Playbook API Endpoint**
```python
# File: /backend/main.py (FastAPI app)

from ace import ACEMiddleware  # Import middleware instance from module_2_2_simple

@app.get("/api/ace/playbook/{agent_type}")
async def get_playbook(agent_type: str):
    """
    Get current playbook for agent.

    Example: GET /api/ace/playbook/researcher
    """
    try:
        playbook = await ace_middleware.playbook_store.get_playbook(agent_type)

        return {
            "agent_type": agent_type,
            "version": playbook["version"],
            "entries_count": len(playbook["entries"]),
            "total_executions": playbook["total_executions"],
            "last_updated": playbook["updated_at"].isoformat(),
            "entries": [
                {
                    "id": e.id,
                    "content": e.content,
                    "category": e.category,
                    "confidence": round(e.confidence_score, 2),
                    "helpful_count": e.helpful_count,
                    "harmful_count": e.harmful_count,
                    "tags": e.tags,
                    "created_at": e.created_at.isoformat(),
                }
                for e in sorted(
                    playbook["entries"],
                    key=lambda x: x.confidence_score * x.helpful_count,
                    reverse=True
                )[:20]  # Top 20 entries
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get playbook: {e}")

@app.get("/api/ace/stats/{agent_type}")
async def get_ace_stats(agent_type: str):
    """Get playbook statistics."""
    try:
        stats = await ace_middleware.playbook_store.get_playbook_stats(agent_type)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {e}")
```

### C: References

**ACE Framework:**
- Research Paper: "Evolving Contexts for Self-Improving Language Models" (Stanford/SambaNova, arXiv:2510.04618)
- Implementation: `/backend/ace/` (7 modules, ~3,000 lines)
- Example Usage: Each ACE module includes `example()` function

**V3 vs V4 Analysis:**
- Report: `/backend/test_configs/test_results/V3_VS_V4_COMPARISON_REPORT.md`
- Key Finding: V4 prompt length (630 lines) exceeded Haiku 3.5 ceiling
- Recommendation: V4.1 (Planning Gate only, ~515 lines)

**Long-Horizon Enhancement Recommendations:**
- Report: `/backend/test_configs/LONG_HORIZON_ENHANCEMENT_RECOMMENDATIONS.md`
- Key Patterns: Cognitive transition failures, attention decay after 4 steps
- ACE Insights: Reflector + Curator prevent context collapse

**Anthropic Research:**
- "Effective Context Engineering for AI Agents" (Sept 29, 2025)
- Key Principle: "Smallest set of high-signal tokens" (validated by V3 success)
- Context as finite resource: ~500-550 lines for Haiku 3.5

**Researcher Implementation:**
- Prompt: `/backend/prompts/researcher.py` (centralized)
- Subagent: `/backend/subagents/researcher.py` (node definition)
- Current Status: V4.1 ready (Planning Gate implemented)

---

**END OF ACE INTEGRATION PLAN**

**Total Pages**: 29
**Total Words**: ~12,000
**Estimated Reading Time**: 45-60 minutes
**Estimated Implementation Time**: 12-15 hours over 3-4 days
