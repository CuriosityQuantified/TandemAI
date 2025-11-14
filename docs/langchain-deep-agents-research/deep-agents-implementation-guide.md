# Deep Agents: Practical Implementation Guide for ATLAS

**Date:** January 12, 2025
**Author:** ATLAS Research Team
**Purpose:** Correct implementation patterns based on Deep Agents design principles

---

## Overview

This guide provides concrete, actionable steps for refactoring ATLAS to properly implement Deep Agents patterns. It's based on the understanding that our previous approach was fighting against Deep Agents' design rather than working with it.

---

## Core Principle: Separation of Concerns

**The Golden Rule:** Each agent should have ONE clear responsibility, not multiple.

### Current (Wrong) Architecture

```
Research Agent:
├── internet_search tool
├── submit tool
└── Complex prompt managing: planning, execution, submission, validation
```

**Problem:** Agent is confused about whether it's:
- A researcher
- A project manager
- A quality controller

### Correct Architecture

```
Supervisor Agent (Coordinator)
├── write_todos (planning - no-op)
├── task (delegation to sub-agents)
└── Reads files to synthesize results

Research Agent (Specialist)
└── internet_search ONLY

Reviewer Agent (Validator)
├── read_file
├── accept_submission
└── reject_submission
```

**Solution:** Each agent has ONE job and does it well.

---

## Implementation Pattern 1: The No-Op Planning Tool

### Understanding `write_todos`

**What It Is:**
```python
@tool
def write_todos(todos: list[dict]):
    """
    Organize your approach to a complex task.

    This tool doesn't execute anything - it helps you think.
    Call it to articulate your plan, then execute with actual tools.
    """
    return f"Plan recorded: {len(todos)} steps"
```

**What It's NOT:**
- ❌ A task execution tracker
- ❌ Something that enforces tool execution order
- ❌ A validation mechanism

**What It IS:**
- ✅ Context engineering for better reasoning
- ✅ A way to structure the agent's thinking
- ✅ A planning phase separate from execution

### How to Use It Correctly

**In Supervisor Agent:**
```python
supervisor_prompt = """You coordinate research workflows.

When you receive a complex task:
1. Call write_todos to plan your approach
2. Delegate specific parts to specialized agents
3. Read results from files
4. Synthesize and deliver

Example:
User: "Research AI regulation in US, EU, and China"

Your approach:
write_todos([
  {"content": "Delegate US regulation research", "status": "pending"},
  {"content": "Delegate EU regulation research", "status": "pending"},
  {"content": "Delegate China regulation research", "status": "pending"},
  {"content": "Synthesize findings into comparison", "status": "pending"}
])

Then delegate each research task to research-agent.
"""
```

**In Sub-Agents (If Needed):**
```python
research_prompt = """You research topics and save findings to files.

For complex research:
1. Optionally use write_todos to organize your approach
2. Execute internet_search to gather information
3. Save comprehensive findings to files
4. Inform supervisor you're done

Remember: write_todos is for YOUR thinking, not task tracking.
"""
```

---

## Implementation Pattern 2: Specialized Sub-Agents

### Research Agent (Simplified)

```python
research_agent = {
    "name": "research-agent",
    "description": "Web research specialist. Searches internet and saves findings to files.",
    "prompt": """You are a web research specialist.

YOUR ONLY JOB: Find information and save it to files.

Tools available:
- internet_search: Search the web
- write_file: Save findings
- (Optional) write_todos: Plan complex research

Workflow:
1. Understand the research question
2. (Optional) Plan your search strategy with write_todos
3. Execute internet_search with well-crafted queries
4. Save comprehensive findings to files
5. Return to supervisor

Output format:
Save findings to descriptive filenames like:
- /workspace/ai_regulation_us.md
- /workspace/competitor_analysis_asana.md

Include:
- Executive summary
- Key findings with sources
- Detailed information
- All URLs/citations

DO NOT:
- Try to submit for review (supervisor handles this)
- Validate your own work (reviewer does this)
- Wait for approval (just complete and return)
""",
    "tools": [internet_search],  # ✅ Single responsibility
    "model": get_claude_sonnet_4_5(temperature=0.5)  # Factual
}
```

### Analysis Agent (Example)

```python
analysis_agent = {
    "name": "analysis-agent",
    "description": "Data analysis and code execution specialist.",
    "prompt": """You analyze data and execute Python code.

YOUR ONLY JOB: Run analysis and save results to files.

Tools available:
- execute_python_code: Run Python in sandbox
- write_file: Save analysis results
- read_file: Load data files
- (Optional) write_todos: Plan complex analysis

Workflow:
1. Understand the analysis request
2. (Optional) Plan your approach with write_todos
3. Write Python code for analysis
4. Execute code in sandbox
5. Save results (data + visualizations) to files
6. Return to supervisor

DO NOT:
- Submit for review
- Make final conclusions (supervisor synthesizes)
- Try to do web research (delegate to research-agent)
""",
    "tools": [execute_python_code],
    "model": get_claude_sonnet_4(temperature=0.3)  # Extended thinking
}
```

### Writing Agent (Example)

```python
writing_agent = {
    "name": "writing-agent",
    "description": "Professional document creation specialist.",
    "prompt": """You create polished documents.

YOUR ONLY JOB: Read research/analysis files and write final documents.

Tools available:
- read_file: Load research findings
- write_file: Create final documents
- edit_file: Refine documents
- (Optional) write_todos: Plan document structure

Workflow:
1. Read research and analysis files
2. (Optional) Plan document structure with write_todos
3. Create well-structured, professional document
4. Save to file
5. Return to supervisor

Output format:
Professional documents with:
- Executive summary
- Clear sections and headings
- Citations where needed
- Proper formatting

DO NOT:
- Conduct new research (read existing files)
- Submit for review
- Make recommendations beyond the data
""",
    "tools": [],  # Uses built-in file tools only
    "model": get_claude_sonnet_4_5(temperature=0.8)  # Creative
}
```

### Reviewer Agent (Independent)

```python
def create_reviewer_agent():
    """
    Standalone LangChain ReAct agent for quality validation.

    IMPORTANT: Reviewer is NOT a sub-agent of the main graph.
    It's invoked independently by the supervisor.
    """
    reviewer_prompt = """You validate research and analysis outputs.

YOUR ONLY JOB: Read files and assess quality.

Tools available:
- read_file: Read the output to review
- accept_submission: Output meets standards
- reject_submission: Output needs improvement

Validation Standards:
1. Accuracy: Information is correct
2. Completeness: All requirements met
3. Quality: Professional, no placeholders
4. Citations: Sources provided

Workflow:
1. Read the specified file
2. Check against standards
3. Accept or reject with specific feedback

DO NOT:
- Fix issues yourself (agent will fix based on feedback)
- Conduct research
- Rewrite content
"""

    return create_agent(
        model=get_claude_sonnet_4_5(temperature=0.2),  # Strict
        tools=[read_file, accept_submission, reject_submission],
        prompt=reviewer_prompt
    )
```

---

## Implementation Pattern 3: Supervisor Coordination

### Supervisor Agent Design

```python
supervisor_prompt = """You are ATLAS Supervisor - a research workflow coordinator.

YOUR JOB: Orchestrate specialized agents to complete user tasks.

Available Sub-Agents:
- research-agent: Web search specialist
- analysis-agent: Data analysis specialist
- writing-agent: Document creation specialist

Available Tools:
- write_todos: Plan your coordination approach (no-op, just for thinking)
- task: Delegate to sub-agents

Workflow Pattern:
1. Understand user's request
2. Call write_todos to plan which agents to use and in what order
3. Delegate specific tasks using task tool
4. Read results from files (agents save their work there)
5. Decide if more work needed or if ready to deliver
6. Synthesize and present final answer

Example:
User: "Research top 3 competitors and create comparison report"

Step 1 - Plan:
write_todos([
  {"content": "Delegate competitor research to research-agent (3 separate tasks)", "status": "pending"},
  {"content": "Read research files and synthesize", "status": "pending"},
  {"content": "Delegate report creation to writing-agent", "status": "pending"},
  {"content": "Present final report to user", "status": "pending"}
])

Step 2 - Delegate Research:
task(
  subagent_type="research-agent",
  description="Research Competitor A (Asana). Save findings to /workspace/competitor_asana.md"
)

Step 3 - Read Results:
read_file(path="/workspace/competitor_asana.md")

Step 4 - Continue with next competitor...

Step 5 - Delegate Writing:
task(
  subagent_type="writing-agent",
  description="Read competitor research files and create professional comparison report. Save to /workspace/final_report.md"
)

Step 6 - Deliver:
Read /workspace/final_report.md and present to user.

Key Principles:
- You coordinate, you don't execute specialized work
- Sub-agents save results to files
- You read files to know what happened
- You synthesize, they specialize
- write_todos is for YOUR thinking, not enforcement
"""

agent = async_create_deep_agent(
    tools=[],  # ✅ No external tools - delegates everything
    instructions=supervisor_prompt,
    model=get_claude_sonnet_4_5(temperature=0.7),
    subagents=[research_agent, analysis_agent, writing_agent]
)
```

---

## Implementation Pattern 4: File-Based Coordination

### How Agents Communicate

**Via Files, Not Direct Messages:**

```python
# Research Agent writes findings
write_file(
    path="/workspace/ai_regulation_us.md",
    content="""# AI Regulation in United States

## Summary
The US takes a sector-specific approach...

## Key Findings
- No comprehensive federal law as of 2025
- Executive Order 14110 establishes framework
- [detailed findings...]

## Sources
- https://whitehouse.gov/ai-policy
- [more sources...]
"""
)

# Supervisor reads to check progress
us_research = read_file(path="/workspace/ai_regulation_us.md")

# Supervisor can now delegate synthesis
task(
    subagent_type="writing-agent",
    description="""Read these research files:
    - /workspace/ai_regulation_us.md
    - /workspace/ai_regulation_eu.md
    - /workspace/ai_regulation_china.md

    Create comprehensive comparison report at /workspace/comparison_report.md
    """
)
```

### File Naming Conventions

**Good Naming:**
```
✅ /workspace/competitor_asana_research.md
✅ /workspace/market_analysis_results.json
✅ /workspace/final_report_draft_v1.md
```

**Bad Naming:**
```
❌ /workspace/output.txt (too generic)
❌ /workspace/file.md (meaningless)
❌ /workspace/temp.json (unclear purpose)
```

---

## Implementation Pattern 5: Context Isolation

### Clean Sub-Agent Invocation

**Current (Wrong) - Context Pollution:**
```python
# Sub-agent sees EVERYTHING
result = research_agent.invoke({
    "messages": full_conversation_history,  # ❌ Includes supervisor routing
    "todos": supervisor_todos,              # ❌ Supervisor's plan
    "files": all_files,                     # ❌ Irrelevant files
    "review_status": "...",                 # ❌ Supervisor's state
    # ... everything
})
```

**Correct - Clean Context:**
```python
# Sub-agent gets only what it needs
result = research_agent.invoke({
    "messages": [
        # System prompt added automatically by Deep Agents
        {
            "role": "user",
            "content": """Research AI regulation in the United States.

Save comprehensive findings to /workspace/ai_regulation_us.md

Include:
- Current legislation status
- Enforcement mechanisms
- Industry impact

Focus on 2025 information."""
        }
    ],
    "files": {}  # Empty at start, agent will create files
})
```

### Task Delegation Pattern

```python
# In supervisor's custom tool or Deep Agents' built-in task tool
result = await sub_agent.ainvoke({
    "messages": [
        {
            "role": "user",
            "content": create_clean_task_description(
                topic="AI regulation in US",
                requirements=["legislation status", "enforcement", "impact"],
                output_file="/workspace/ai_regulation_us.md"
            )
        }
    ],
    "files": {}  # Start fresh
})

# Extract result from files, not messages
research_output = result["files"].get("/workspace/ai_regulation_us.md")
```

---

## Common Mistakes to Avoid

### Mistake 1: Multi-Tool Agents

**Wrong:**
```python
research_agent = {
    "tools": [internet_search, write_file, edit_file, submit]  # ❌ Too many concerns
}
```

**Right:**
```python
research_agent = {
    "tools": [internet_search]  # ✅ Single concern
    # write_file, edit_file, read_file, ls are built-in
}
```

### Mistake 2: Complex Prompt Rules

**Wrong:**
```yaml
persona: |
  ⛔ MANDATORY RULE: Before marking todo complete, check previous message...
  ⛔ CRITICAL: Execute tool first, update second...
  ❌ WRONG PATTERN: [20 lines of what not to do]
  ✅ RIGHT PATTERN: [20 lines of correct execution]
  [... 29KB of rules ...]
```

**Right:**
```yaml
persona: |
  You are a research specialist. Your job: search web, save findings to files.

  Workflow:
  1. Search with internet_search
  2. Save with write_file
  3. Done

  That's it. Keep it simple.
```

### Mistake 3: Validation in Wrong Place

**Wrong:**
```python
@tool
def submit(...):
    # Pre-validate file exists
    if output_file not in state["files"]:  # ❌ Fighting natural workflow
        return "ERROR: File doesn't exist..."
```

**Right:**
```python
# Let reviewer handle validation naturally
@tool
def accept_submission(...):
    """Accept if ALL standards pass"""
    return Command(update={"review_status": "ACCEPTED"})

@tool
def reject_submission(feedback: str, ...):
    """Reject with specific feedback"""
    return Command(update={"review_status": "REJECTED", "review_feedback": feedback})
```

### Mistake 4: Forcing Linear Workflows

**Wrong:**
```
Research Agent MUST follow this exact sequence:
  write_todos → internet_search → mark search complete →
  write_file → mark file complete → submit
```

**Right:**
```
Research Agent workflow:
  1. (Optional) write_todos to think
  2. Do research and save files (in whatever order makes sense)
  3. Return when done

Supervisor handles coordination and review.
```

---

## Refactoring Checklist for ATLAS

### Phase 1: Simplify Agents

- [ ] Remove `submit` tool from research agent
- [ ] Remove `submit` tool from analysis agent
- [ ] Remove `submit` tool from writing agent
- [ ] Keep only specialized tools per agent

### Phase 2: Simplify Prompts

- [ ] Remove complex execution protocols from prompts
- [ ] Remove "wrong vs right" pattern sections
- [ ] Remove mechanical validation rules
- [ ] Focus on: "Here's your ONE job, do it well"

### Phase 3: Supervisor Coordination

- [ ] Add file-reading logic to supervisor
- [ ] Supervisor triggers review (not sub-agents)
- [ ] Supervisor synthesizes results
- [ ] Supervisor decides when to delegate vs when to deliver

### Phase 4: Independent Review

- [ ] Make reviewer standalone (not part of main graph)
- [ ] Supervisor calls reviewer with file path
- [ ] Reviewer returns accept/reject
- [ ] Supervisor handles rejection feedback

### Phase 5: Testing

- [ ] Test research agent in isolation (no submit)
- [ ] Test supervisor coordination
- [ ] Test file-based result extraction
- [ ] Test review process
- [ ] Test full workflow

---

## Expected Behavior After Refactoring

### Successful Research Flow

```
1. User: "Research top 3 Python frameworks"

2. Supervisor:
   - Calls write_todos (planning phase)
   - Returns: "Plan recorded: 3 steps"

3. Supervisor:
   - Delegates: task(subagent_type="research-agent", description="Research Django...")

4. Research Agent (in isolation):
   - Calls internet_search(query="Django Python framework 2025")
   - Calls write_file(path="/workspace/django.md", content="...")
   - Returns to supervisor

5. Supervisor:
   - Reads /workspace/django.md
   - Sees research complete
   - Repeats for Flask and FastAPI

6. Supervisor:
   - Has 3 research files
   - Delegates to writing-agent: "Create comparison report"

7. Writing Agent:
   - Reads all 3 files
   - Creates /workspace/comparison_report.md
   - Returns to supervisor

8. Supervisor:
   - Optionally triggers review
   - Presents final report to user

Total: ~8-12 steps (not 25)
```

---

## Summary: The Deep Agents Way

**Core Philosophy:**
- **Specialization over generalization**
- **Coordination over control**
- **Files over messages**
- **Delegation over execution**

**What Changed:**
- We stopped fighting agent behavior
- We started working with Deep Agents design
- We removed complexity, added clarity
- We separated concerns properly

**Expected Outcome:**
- Fewer recursion errors
- Cleaner execution traces
- More reliable results
- Easier to debug and extend

---

## References

1. Deep Agents Design Philosophy
   `/docs/langchain-deep-agents-research/deep-agents-design-philosophy.md`

2. LangChain Deep Agents Blog
   https://blog.langchain.com/deep-agents/

3. Deep Agents GitHub
   https://github.com/langchain-ai/deepagents

---

**End of Implementation Guide**
