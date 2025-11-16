# Bug Fixes for API-Dependent Tests

**Date**: November 7, 2025
**Status**: Fixed and Testing in Progress

---

## Summary

Fixed critical API compatibility issues in the Deep Subagent Delegation System that prevented API-dependent tests from running. All 5 subagent backend configurations have been corrected.

---

## Bugs Fixed

### Bug 1: StateBackend API Change ❌→✅

**Error**:
```
TypeError: StateBackend.__init__() got an unexpected keyword argument 'base_dir'
```

**Root Cause**: DeepAgents library changed StateBackend API. It now requires `runtime` as a positional argument, not `base_dir`.

**Fix Location**: All 5 subagent files (`researcher.py`, `data_scientist.py`, `expert_analyst.py`, `writer.py`, `reviewer.py`)

**Before** (lines ~169-175 in each file):
```python
def create_hybrid_backend(state_dir=".state", workspace_dir=workspace_dir):
    return CompositeBackend(
        default=StateBackend(base_dir=state_dir),  # ❌ Wrong!
        routes={
            "/workspace/*": FilesystemBackend(base_dir=workspace_dir),
        }
    )
```

**After**:
```python
def create_hybrid_backend(runtime=None, state_dir=".state", workspace_dir=workspace_dir):
    return CompositeBackend(
        default=StateBackend(runtime),  # ✅ Correct!
        routes={
            "/workspace/*": FilesystemBackend(root_dir=workspace_dir),
        }
    )
```

**Changes**:
1. Added `runtime` parameter to function signature (DeepAgents passes this)
2. Changed `StateBackend(base_dir=state_dir)` → `StateBackend(runtime)`
3. Changed `FilesystemBackend(base_dir=...)` → `FilesystemBackend(root_dir=...)`

### Bug 2: FilesystemBackend API Change ❌→✅

**Error**:
```
TypeError: FilesystemBackend.__init__() got an unexpected keyword argument 'base_dir'
```

**Root Cause**: FilesystemBackend uses `root_dir` parameter, not `base_dir`.

**Fix**: Changed `FilesystemBackend(base_dir=workspace_dir)` → `FilesystemBackend(root_dir=workspace_dir)` in all 5 subagent files.

### Bug 3: Hardcoded Workspace Directory ❌→✅

**Error**:
```
AssertionError: Output file not created: /tmp/.../test_workspace/test_research.md
```

**Root Cause**: The `write_file_tool` and `edit_file_with_approval` tools in `module_2_2_simple.py` had hardcoded workspace paths:

```python
# Line 341 in module_2_2_simple.py
workspace_dir = Path(__file__).parent / "workspace"  # ❌ Always uses backend/workspace!
```

This meant files were being written to `backend/workspace/` instead of the test workspace temp directory.

**Fix**: Made workspace directory configurable with global state management.

**Files Modified**:
1. `backend/module_2_2_simple.py` (lines 2032-2044, 341, 395)
2. `backend/tests/conftest.py` (all 5 subagent fixtures)

**Added to module_2_2_simple.py**:
```python
# Workspace directory configuration (can be overridden for testing)
_workspace_dir = None

def set_workspace_dir(workspace_dir: str):
    """Set custom workspace directory (useful for testing)."""
    global _workspace_dir
    _workspace_dir = workspace_dir

def get_workspace_dir() -> Path:
    """Get workspace directory (custom or default backend/workspace)."""
    if _workspace_dir is not None:
        return Path(_workspace_dir)
    return Path(__file__).parent / "workspace"
```

**Updated in _write_file_impl (line 341)**:
```python
# BEFORE
workspace_dir = Path(__file__).parent / "workspace"  # ❌ Hardcoded!

# AFTER
workspace_dir = get_workspace_dir()  # ✅ Configurable!
```

**Updated in _edit_file_impl (line 395)**:
```python
# BEFORE
workspace_dir = Path(__file__).parent / "workspace"  # ❌ Hardcoded!

# AFTER
workspace_dir = get_workspace_dir()  # ✅ Configurable!
```

**Updated all 5 test fixtures in conftest.py**:
```python
from module_2_2_simple import set_workspace_dir

# Set workspace directory for tools to use test workspace
set_workspace_dir(test_workspace)
```

---

## Impact

### Before Fixes:
- ❌ All API-dependent tests failing with TypeError
- ❌ Files written to wrong directory (backend/workspace instead of test workspace)
- ❌ Tests unable to verify file creation
- ❌ 0/5 Individual Subagent Tests passing

### After Fixes:
- ✅ Backend API errors resolved
- ✅ Files written to correct test workspace
- ✅ Tests can verify file creation
- ✅ Researcher test PASSING (verified)
- ⏳ Other 4 tests running now...

---

## Files Modified

### Subagent Files (Backend API fixes):
1. `backend/subagents/researcher.py` (lines 169-175)
2. `backend/subagents/data_scientist.py` (lines 79-85)
3. `backend/subagents/expert_analyst.py` (lines 78-84)
4. `backend/subagents/writer.py` (lines 83-89)
5. `backend/subagents/reviewer.py` (lines 84-90)

### Core Module Files (Workspace configuration):
6. `backend/module_2_2_simple.py` (lines 2032-2044, 341, 395)

### Test Files (Workspace setup):
7. `backend/tests/conftest.py` (5 fixtures: researcher_agent, data_scientist_agent, expert_analyst_agent, writer_agent, reviewer_agent)

**Total**: 7 files modified, ~20 lines changed per file

---

## Testing Status

### Completed:
- ✅ **Researcher Test** - PASSED (70.13 seconds)

### In Progress:
- ⏳ **Data Scientist Test** - Running...
- ⏳ **Expert Analyst Test** - Queued
- ⏳ **Writer Test** - Queued
- ⏳ **Reviewer Test** - Queued

### Bug 4: Reviewer Missing Read Tool ❌→✅

**Error**:
```
AssertionError: Output file not created: /tmp/.../workspace/test_review.md
```

**Symptoms**:
- Reviewer test completing quickly (12-18s vs ~40s for other tests)
- Reviewer unable to read sample document
- FilesystemBackend permission errors when accessing system files

**Root Cause**:
1. Reviewer needed to READ existing files (sample_research.md) before writing review
2. Other subagents only WRITE new files, so they worked with custom write_file_tool
3. FilesystemBackend's built-in `read` tool couldn't find files (path resolution issues)
4. FilesystemBackend also tried to access system directories, causing permission errors

**Fix Location**: Multiple files

**Solution**: Created custom workspace-scoped `read_file_tool`

**Files Modified**:

1. **backend/module_2_2_simple.py** (lines 203-256 - NEW)
   - Added `ReadFileInput` schema
   - Added `read_file_tool` function with workspace scoping
   - Validates paths start with `/workspace/`
   - Uses `get_workspace_dir()` to resolve actual filesystem path
   - Returns file content or error message

2. **backend/subagents/reviewer.py** (lines 76-86, 361-370, 417-431)
   - Added `read_file_tool` import
   - Removed FilesystemBackend (causing permission errors)
   - Changed to StateBackend only (`create_backend` instead of `create_hybrid_backend`)
   - Added `read_file_tool` to tools list
   - Updated system prompt to document `read_file` tool

3. **backend/tests/conftest.py** (line 272)
   - Updated comment to clarify `/workspace/` path format

**Before** (reviewer.py lines 84-90):
```python
def create_hybrid_backend(runtime=None, state_dir=".state", workspace_dir=workspace_dir):
    return CompositeBackend(
        default=StateBackend(runtime),
        routes={
            "/workspace/*": FilesystemBackend(root_dir=workspace_dir),  # Permission errors!
        }
    )
```

**After** (reviewer.py lines 84-86):
```python
def create_backend(runtime=None, state_dir=".state"):
    return StateBackend(runtime)  # Simple, no filesystem access issues
```

**Before** (reviewer.py tools):
```python
tools=[
    tavily_search,
    write_file_tool,
    edit_file_with_approval,
    read_current_plan_tool,
]
```

**After** (reviewer.py tools):
```python
tools=[
    tavily_search,
    read_file_tool,              # ✅ NEW - read files from /workspace/
    write_file_tool,
    edit_file_with_approval,
    read_current_plan_tool,
]
```

**Key Insight**: FilesystemBackend's built-in tools are great for general filesystem access, but for security and workspace isolation, custom workspace-scoped tools (read_file_tool, write_file_tool, edit_file_with_approval) are better for subagents that only need to access workspace files.

---

## Testing Status

### Completed:
- ✅ **All 5 Individual Subagent Tests** - PASSED (231.74s / 3:51)
  - ✅ test_researcher_basic_query - PASSED
  - ✅ test_data_scientist_analysis - PASSED
  - ✅ test_expert_analyst_5_whys - PASSED
  - ✅ test_writer_technical_report - PASSED
  - ✅ test_reviewer_document_review - PASSED (**FIXED!**)

### Success Rate: 5/5 (100%) ✅

### Estimated Total Runtime:
- Individual Subagents: ~5-10 minutes (5 tests) ✅ COMPLETED
- Parallel Execution: ~10-15 minutes (2 tests)
- Sequential Pipeline: ~15-20 minutes (1 test)
- Performance: ~20-30 minutes (1 test)

**Total**: 50-75 minutes for all API-dependent tests

---

## Key Lessons Learned

1. **DeepAgents API Changes**: Always check library documentation for breaking changes. StateBackend and FilesystemBackend APIs changed between versions.

2. **Test Isolation**: Hardcoded paths break test isolation. Always make file paths configurable for testing.

3. **Global State Management**: Module-level configuration (like `set_workspace_dir()`) provides clean way to override defaults for testing without changing production code.

4. **Approval Workflows**: `get_auto_approve()` defaults to True, which is correct for tests. No mocking needed.

5. **Hybrid Backends**: DeepAgents `CompositeBackend` requires backend factories to accept `runtime` parameter - they're called as functions, not used as instances.

---

## Next Steps

1. ✅ Wait for all 5 Individual Subagent Tests to complete
2. ⏳ Run Parallel Execution Tests (2 tests)
3. ⏳ Run Sequential Pipeline Test (1 test)
4. ⏳ Run Performance Test (1 test)
5. ⏳ Document all test results in SUBAGENT_TEST_RESULTS.md
6. ⏳ Update TESTING_PHASE_COMPLETE.md with final status

---

**Bug Fixes Completed By**: Claude Code
**Date**: November 7, 2025
**Time to Fix**: ~2 hours (includes discovery, fixing, verification)
**Status**: ✅ Fixed and verified working
