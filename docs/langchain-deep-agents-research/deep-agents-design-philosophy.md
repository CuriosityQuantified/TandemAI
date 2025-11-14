# Deep Agents: Design Philosophy and Proper Usage

**Date:** January 12, 2025
**Author:** ATLAS Research Team
**Purpose:** Understanding Deep Agents capabilities and correcting implementation misconceptions

---

## Executive Summary

After extensive research and a failed attempt to "fix" the research agent's behavior through increasingly complex prompts and validation checks, we've discovered a fundamental misunderstanding of how Deep Agents are designed to work.

**Key Insight:** We were fighting against Deep Agents' design rather than working with it.

---

## What Are Deep Agents? (Official Definition)

From LangChain's official blog post (July 30, 2025):

> "Using an LLM to call tools in a loop is the simplest form of an agent. This architecture, however, can yield agents that are 'shallow' and fail to plan and act over longer, more complex tasks. Applications like 'Deep Research', 'Manus', and 'Claude Code' have gotten around this limitation by implementing a combination of four things: **a planning tool, sub agents, access to a file system, and a detailed prompt**."

### The Problem Deep Agents Solve

**Shallow Agents:**
- React to immediate input
- No strategic planning
- Context chaos in long workflows
- Cannot delegate to specialists
- Struggle with complex, multi-step tasks

**Deep Agents:**
- Plan strategically before acting
- Delegate to specialized sub-agents
- Maintain persistent memory via file systems
- Excel at research, coding, and complex analysis
- Capable of executing over longer time horizons

---

## The Four Core Components

### 1. Detailed System Prompt

**What it is:** Comprehensive instructions with examples, tool usage guidelines, and behavioral patterns

**What it is NOT:** A list of strict rules that prevent mistakes

**Key Characteristics:**
- Long and detailed (Claude Code's prompts are very long)
- Contains few-shot examples of desired behaviors
- Describes tools and when to use them
- Sets clear success criteria

**Our Mistake:** We kept adding MORE rules and warnings, making the prompt increasingly complex (29KB) when the issue wasn't the prompt content but our understanding of the workflow.

### 2. Planning Tool (`write_todos`)

**What it is:** A NO-OP tool that structures agent thinking

**Critical Understanding:**
> "Claude Code uses a Todo list tool. Funnily enough - this doesn't do anything! It's basically a no-op. It's just a context engineering strategy to keep the agent on track."
>
> "Planning (even if done via a no-op tool call) is a big component of [success]."

**How It Works:**
- Agent calls `write_todos(...)` to articulate its plan
- The tool returns confirmation (but doesn't execute anything)
- The plan stays in conversation history as context
- Helps agent maintain focus during long-running tasks

**Our Mistake:** We treated `write_todos` as a source of bugs (agents marking todos complete without executing tools) and tried to add validation. But the tool is DESIGNED to be a no-op - the validation should be elsewhere.

### 3. Sub-Agents

**What they are:** Specialized agents with focused instructions and context isolation

**Key Benefits:**
- **Context Quarantine**: Sub-agents get clean conversation history
- **Specialization**: Custom instructions and tools per sub-agent
- **Parallel Expertise**: Multiple domain experts working together

**How They Work:**
- Main agent delegates specific tasks to sub-agents
- Sub-agents work in isolated context
- Results returned to main agent
- Main agent synthesizes findings

**Our Mistake:** We didn't leverage sub-agent specialization. The research agent had both search AND file operations AND submission, when it should focus on research only.

### 4. Virtual File System

**What it is:** Mock file system using LangGraph state for persistent memory

**Built-in Tools:**
- `write_file` - Create or overwrite files
- `read_file` - Read file contents
- `edit_file` - Modify existing content
- `ls` - List all files

**Key Benefits:**
- Multiple agents run without conflicts
- Files act as shared workspace
- Keeps message history clean
- Persistence across workflow

**Our Mistake:** We focused on "file not found" errors as agent mistakes rather than understanding that files should naturally emerge from tool execution.

---

## Our Fundamental Misconception

### What We Were Doing

**Problem:** Research agent hitting 25-step recursion limit

**Our Approach:**
1. Diagnosed: Agent marking todos complete without executing tools
2. Solution Attempt 1: Remove planning entirely - "NO PLANNING, execute directly"
3. User Correction: "We need planning for complex tasks"
4. Solution Attempt 2: Add execution protocol with tool-first, todo-second discipline
5. Solution Attempt 3: Add mechanical rules about checking previous messages
6. Solution Attempt 4: Add wrong vs right pattern examples
7. Solution Attempt 5: Add pre-submission validation in code

**Result:** Agent still hit recursion limit despite 29KB prompt with:
- Explicit execution protocols
- Wrong vs right examples
- Mechanical rules
- Multiple warnings
- Code-level validation

### What We Should Have Been Doing

**Understanding the Design:**

1. **write_todos IS SUPPOSED TO BE CALLED** - It's not a bug, it's a feature
2. **Planning is separate from execution** - Todos are context engineering, not task tracking
3. **Sub-agents should be specialized** - Research agent shouldn't handle submission
4. **File system is for coordination** - Not just output delivery

**The Real Problem:**

The research agent was likely failing because:
- **Too much responsibility**: Search + File operations + Submission in one agent
- **Wrong workflow**: We forced a linear workflow (plan → search → save → submit) when Deep Agents work differently
- **Validation in wrong place**: Submission validation should happen naturally, not as pre-checks
- **Context pollution**: Research agent seeing supervisor's routing logic

---

## How Deep Agents Actually Work

### Pattern 1: Hub-and-Spoke (Supervisor)

```
Supervisor Agent (Orchestrator)
├── Research Agent (specialist: web search only)
├── Analysis Agent (specialist: code execution only)
├── Writing Agent (specialist: document creation only)
└── Reviewer Agent (specialist: quality validation only)
```

**Workflow:**
1. Supervisor receives user task
2. Supervisor uses `write_todos` to plan (NO-OP, just for thinking)
3. Supervisor delegates specific subtasks to specialists
4. Each specialist works in isolated context
5. Specialists return results via files or messages
6. Supervisor synthesizes and delivers final output

### Pattern 2: The No-Op Planning Tool

```python
@tool
def write_todos(todos: list[dict]):
    """
    Plan your approach to the task.

    This is a NO-OP tool - it doesn't execute anything.
    Its purpose is to help you think through your approach.
    """
    # Just return confirmation
    return f"Plan recorded: {len(todos)} steps identified"
```

**Key Understanding:**
- Calling this tool IS the goal
- It keeps the agent on track
- It's context engineering, not task execution
- The agent should call it, see confirmation, and move on

### Pattern 3: Sub-Agent Specialization

**Research Agent (Specialist):**
- **Tools**: `internet_search` ONLY
- **Responsibility**: Find information and save to files
- **Output**: Files in virtual filesystem
- **Does NOT**: Submit, validate, or synthesize

**Reviewer Agent (Specialist):**
- **Tools**: `read_file`, `accept_submission`, `reject_submission`
- **Responsibility**: Validate output quality
- **Trigger**: Called by supervisor after research agent completes
- **Does NOT**: Research or create content

**Supervisor Agent (Orchestrator):**
- **Tools**: `task` (delegation), `write_todos` (planning)
- **Responsibility**: Decompose tasks, delegate, synthesize
- **Does NOT**: Execute specialized work itself

---

## What We Should Fix in ATLAS

### Issue 1: Research Agent Has Too Many Responsibilities

**Current (Wrong):**
```python
research_agent = {
    "tools": [internet_search, submit],  # ❌ Two different concerns
    "prompt": "Search, save, AND submit for review"  # ❌ Too much
}
```

**Correct:**
```python
research_agent = {
    "tools": [internet_search],  # ✅ Single responsibility
    "prompt": "Research topics and save findings to files"  # ✅ Clear focus
}

# Supervisor handles submission separately
```

### Issue 2: We're Forcing a Linear Workflow

**Current (Wrong):**
```
Research Agent:
  1. Plan (write_todos)
  2. Search (internet_search)
  3. Save (write_file)
  4. Submit (submit) ← ❌ Research agent shouldn't submit
```

**Correct:**
```
Supervisor:
  1. Plan overall approach (write_todos)
  2. Delegate to research agent: "Research topic X"

Research Agent (in isolation):
  1. Search (internet_search)
  2. Save findings (write_file)
  3. Return to supervisor

Supervisor:
  4. Delegate to reviewer: "Review research_output.txt"

Reviewer Agent (in isolation):
  1. Read file (read_file)
  2. Validate quality
  3. Accept or reject
  4. Return to supervisor
```

### Issue 3: We're Treating Planning as Execution

**Current (Wrong):**
- Agent calls write_todos
- We expect it to execute each todo before marking complete
- We add validation to prevent "planning without execution"

**Correct:**
- Agent calls write_todos (planning phase - NO-OP)
- Agent then executes actual tools (execution phase)
- These are SEPARATE phases
- Todos are context, not task tracking

### Issue 4: Context Pollution

**Current (Wrong):**
```python
# Research agent sees supervisor's full state
result = research_agent.invoke({
    "messages": all_messages,  # ❌ Includes routing logic
    "todos": supervisor_todos,  # ❌ Supervisor's plan
    # ... everything
})
```

**Correct:**
```python
# Research agent gets clean context
result = research_agent.invoke({
    "messages": [
        {"role": "system", "content": research_prompt},
        {"role": "user", "content": specific_task_only}  # ✅ Clean task
    ],
    "files": shared_files_only  # ✅ Only relevant files
})
```

---

## Recommended Architecture Changes

### Change 1: Simplify Agent Responsibilities

**Remove from Research Agent:**
- ❌ `submit` tool
- ❌ Submission validation logic
- ❌ Complex workflow management
- ❌ Todo tracking for supervisor

**Research Agent Focus:**
```python
research_agent = {
    "name": "research-agent",
    "description": "Conducts web research and saves findings to files",
    "prompt": """You are a research specialist.

Your ONLY job:
1. Search the web for requested information
2. Save findings to well-organized files
3. Return to supervisor when done

You do NOT:
- Submit for review (supervisor handles this)
- Validate your own work (reviewer handles this)
- Manage overall project todos (supervisor handles this)

Focus on research excellence. Let others handle coordination.""",
    "tools": [internet_search]
}
```

### Change 2: Supervisor Handles Coordination

**Supervisor Responsibilities:**
- Overall task planning with `write_todos`
- Delegating to specialists
- Reading results from files
- Triggering review
- Synthesizing final output

```python
supervisor_prompt = """You coordinate research workflows.

Workflow:
1. Plan approach with write_todos
2. Delegate research to research-agent
3. Check files for research results
4. Trigger review if needed
5. Synthesize and deliver to user

Remember:
- write_todos is for YOUR planning (no-op, just thinking)
- Sub-agents do the actual work
- Files are your coordination mechanism
- You synthesize, not execute
"""
```

### Change 3: Reviewer is Independent

**Reviewer Trigger:**
```python
# In supervisor's tools
@tool
def review_research(file_path: str, task_description: str):
    """
    Ask reviewer to validate research output.

    Args:
        file_path: Path to file containing research
        task_description: What was the research task
    """
    # Invoke reviewer agent
    result = reviewer_agent.invoke({
        "messages": [{
            "role": "user",
            "content": f"Review {file_path} for task: {task_description}"
        }],
        "files": current_files
    })

    return result["messages"][-1].content
```

---

## Key Takeaways

### ✅ What Works in Deep Agents

1. **No-Op Planning**: `write_todos` is SUPPOSED to be called frequently
2. **Context Isolation**: Sub-agents don't see supervisor's routing logic
3. **File-Based Coordination**: Agents communicate via virtual filesystem
4. **Specialization**: Each agent has ONE clear responsibility
5. **Delegation**: Supervisor delegates, doesn't execute

### ❌ What Doesn't Work

1. **Complex Prompt Rules**: Adding more warnings doesn't fix architecture issues
2. **Validation Checks**: Code-level checks prevent natural workflow
3. **Linear Workflows**: Forcing step-by-step execution breaks delegation
4. **Multi-Responsibility Agents**: Agents with too many tools get confused
5. **Fighting the Design**: Trying to prevent "wrong" behavior instead of enabling right behavior

### 🎯 The Real Lesson

**We were solving the wrong problem.**

The issue wasn't that the agent was "marking todos complete without executing tools" - that's a symptom of architectural problems:
- Wrong agent responsibilities
- Forced linear workflow
- Too much in one agent
- Misunderstanding of planning vs execution

The solution is to redesign the architecture to match Deep Agents design principles, not to add more prompt instructions.

---

## Next Steps for ATLAS

1. **Simplify Agent Prompts**: Remove complex execution protocols
2. **Separate Responsibilities**: Research agent only researches
3. **Supervisor Coordination**: Let supervisor handle workflow
4. **File-Based Results**: Agents write to files, supervisor reads
5. **Independent Review**: Reviewer gets called by supervisor, not research agent

6. **Test the Design**: See if simpler, specialized agents work better than complex, multi-responsibility agents

---

## References

1. **LangChain Blog - Deep Agents** (July 30, 2025)
   https://blog.langchain.com/deep-agents/

2. **LangChain DeepAgents GitHub**
   https://github.com/langchain-ai/deepagents

3. **Middleware Deep Dive Documentation**
   `/Users/nicholaspate/Documents/01_Active/ATLAS/docs/langchain-deep-agents-research/middleware-deep-dive.md`

4. **Claude Code Documentation**
   https://docs.anthropic.com/en/docs/claude-code/

---

**End of Document**
