# LangChain DeepAgents Framework: Comprehensive Analysis

**Research Date**: November 4, 2025
**Framework Version**: deepagents 0.2+ (2025)
**Purpose**: Deep research to determine what's pre-built vs custom development needed for deep research system

---

## Executive Summary

**DeepAgents is a production-ready framework that provides 70-80% of required functionality for a deep research system.** LangChain's DeepAgents framework and the companion `open_deep_research` project deliver sophisticated multi-agent orchestration, planning, context management, and research workflows out-of-the-box. The framework is built on LangGraph and inspired by Claude Code, Deep Research (OpenAI), and Manus.

### Key Findings

1. **Pre-Built Capabilities**:
   - Multi-agent orchestration with supervisor-researcher patterns
   - Built-in planning system with TODO tracking
   - Virtual filesystem for artifact management
   - Context management and summarization
   - Human-in-the-loop approval workflows
   - Web search integration (Tavily, native providers)
   - Subagent spawning and delegation
   - Production-grade state management
   - LangSmith observability integration

2. **What Needs Custom Development**:
   - Effort level configuration (6 levels: quick/balanced/thorough/deep/exhaustive/definitive)
   - Search count tracking and enforcement
   - Loop detection mechanisms
   - Knowledge graph integration
   - Vector database RAG integration
   - Custom approval workflow UI
   - Real-time progress tracking
   - Advanced citation management

3. **Migration Path**: HIGH compatibility with existing architecture - can adopt incrementally

4. **Production Readiness**: EXCELLENT - actively maintained, well-documented, battle-tested

---

## 1. DeepAgents Framework Architecture

### 1.1 Core Concept

DeepAgents addresses the "shallow agent" problem by implementing four foundational capabilities:

1. **Planning Tool**: Built-in `write_todos` enables task decomposition and progress tracking
2. **Virtual Filesystem**: State-persisted files (`ls`, `read_file`, `write_file`, `edit_file`) for artifact management
3. **Subagent Delegation**: Hierarchical task distribution via `task` tool with context isolation
4. **Detailed System Prompts**: Comprehensive behavioral instructions via `BASE_AGENT_PROMPT`

### 1.2 Architecture Principles

**From Harrison Chase's Blog Post:**

> "Using an LLM to call tools in a loop is the simplest form of an agent. However, deep agents incorporate four critical enhancements that distinguish them from naive implementations."

The framework moves beyond basic ReAct agents to handle:
- Complex, multi-step tasks requiring sustained execution
- Long-horizon planning and execution
- Context management across extended operations
- Specialized task delegation

### 1.3 Design Philosophy

**Shallow Agents** (what DeepAgents replaces):
- Simple tool-calling loops
- Limited planning capability
- Context overflow on complex tasks
- No task decomposition
- Monolithic execution

**Deep Agents** (what DeepAgents provides):
- Strategic planning with checkpoints
- Hierarchical task delegation
- Persistent memory management
- Context isolation via subagents
- Composable middleware architecture

---

## 2. Installation and Setup

### 2.1 Installation

```bash
# Primary package
pip install deepagents

# For async support and MCP integration
pip install deepagents[async]

# Alternative package managers
uv add deepagents
poetry add deepagents
```

### 2.2 Dependencies

**Core Requirements:**
- `langchain` >= 1.0.0a10 - Agent framework
- `langgraph` >= 1.0.0a3 - State graphs and orchestration
- `langchain-anthropic` >= 0.1.23 - Claude integration (default model)
- `langgraph-prebuilt` >= 0.7.0a2 - Pre-built agent patterns

**Optional Dependencies:**
- `tavily-python` - Web search integration
- Provider-specific packages (OpenAI, Google, Groq, etc.)

### 2.3 Basic Usage

```python
from deepagents import create_deep_agent

# Simplest configuration
agent = create_deep_agent(
    system_prompt="You are a research assistant."
)

# With custom tools
agent = create_deep_agent(
    tools=[internet_search, calculator],
    system_prompt="You are a thorough researcher."
)

# Invoke the agent
result = agent.invoke({
    "messages": [{"role": "user", "content": "Research quantum computing trends"}]
})
```

---

## 3. Research Agent Implementation Analysis

### 3.1 Complete Research Agent Code

**From `examples/research/research_agent.py`:**

```python
import os
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent

# Initialize search client
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# Search tool definition
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    search_docs = tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )
    return search_docs

# Research subagent configuration
sub_research_prompt = """You are a dedicated researcher. Your job is to conduct research based on the users questions.

Conduct thorough research and then reply to the user with a detailed answer to their question

only your FINAL answer will be passed on to the user. They will have NO knowledge of anything except your final message, so your final report should be your final message!"""

research_sub_agent = {
    "name": "research-agent",
    "description": "Used to research more in depth questions. Only give this researcher one topic at a time. Do not pass multiple sub questions to this researcher. Instead, you should break down a large topic into the necessary components, and then call multiple research agents in parallel, one for each sub question.",
    "system_prompt": sub_research_prompt,
    "tools": [internet_search],
}

# Critique subagent configuration
sub_critique_prompt = """You are a dedicated editor. You are being tasked to critique a report.

You can find the report at `final_report.md`.
You can find the question/topic for this report at `question.txt`.

The user may ask for specific areas to critique the report in. Respond to the user with a detailed critique of the report. Things that could be improved.

You can use the search tool to search for information, if that will help you critique the report

Do not write to the `final_report.md` yourself.

Things to check:
- Check that each section is appropriately named
- Check that the report is written as you would find in an essay or a textbook - it should be text heavy, do not let it just be a list of bullet points!
- Check that the report is comprehensive. If any paragraphs or sections are short, or missing important details, point it out.
- Check that the article covers key areas of the industry, ensures overall understanding, and does not omit important parts.
- Check that the article deeply analyzes causes, impacts, and trends, providing valuable insights
- Check that the article closely follows the research topic and directly answers questions
- Check that the article has a clear structure, fluent language, and is easy to understand."""

critique_sub_agent = {
    "name": "critique-agent",
    "description": "Used to critique the final report. Give this agent some information about how you want it to critique the report.",
    "system_prompt": sub_critique_prompt,
}

# Main agent instructions
research_instructions = """You are an expert researcher. Your job is to conduct thorough research, and then write a polished report.

The first thing you should do is to write the original user question to `question.txt` so you have a record of it.

Use the research-agent to conduct deep research. It will respond to your questions/topics with a detailed answer.

When you think you enough information to write a final report, write it to `final_report.md`

You can call the critique-agent to get a critique of the final report. After that (if needed) you can do more research and edit the `final_report.md`
You can do this however many times you want until are you satisfied with the result.

Only edit the file once at a time (if you call this tool in parallel, there may be conflicts).

Here are instructions for writing the final report:

<report_instructions>

CRITICAL: Make sure the answer is written in the same language as the human messages! If you make a todo plan - you should note in the plan what language the report should be in so you dont forget!
Note: the language the report should be in is the language the QUESTION is in, not the language/country that the question is ABOUT.

Please create a detailed answer to the overall research brief that:
1. Is well-organized with proper headings (# for title, ## for sections, ### for subsections)
2. Includes specific facts and insights from the research
3. References relevant sources using [Title](URL) format
4. Provides a balanced, thorough analysis. Be as comprehensive as possible, and include all information that is relevant to the overall research question. People are using you for deep research and will expect detailed, comprehensive answers.
5. Includes a "Sources" section at the end with all referenced links

You can structure your report in a number of different ways. Here are some examples:

To answer a question that asks you to compare two things, you might structure your report like this:
1/ intro
2/ overview of topic A
3/ overview of topic B
4/ comparison between A and B
5/ conclusion

To answer a question that asks you to return a list of things, you might only need a single section which is the entire list.
1/ list of things or table of things
Or, you could choose to make each item in the list a separate section in the report. When asked for lists, you don't need an introduction or conclusion.
1/ item 1
2/ item 2
3/ item 3

To answer a question that asks you to summarize a topic, give a report, or give an overview, you might structure your report like this:
1/ overview of topic
2/ concept 1
3/ concept 2
4/ concept 3
5/ conclusion

If you think you can answer the question with a single section, you can do that too!
1/ answer

REMEMBER: Section is a VERY fluid and loose concept. You can structure your report however you think is best, including in ways that are not listed above!
Make sure that your sections are cohesive, and make sense for the reader.

For each section of the report, do the following:
- Use simple, clear language
- Use ## for section title (Markdown format) for each section of the report
- Do NOT ever refer to yourself as the writer of the report. This should be a professional report without any self-referential language.
- Do not say what you are doing in the report. Just write the report without any commentary from yourself.
- Each section should be as long as necessary to deeply answer the question with the information you have gathered. It is expected that sections will be fairly long and verbose. You are writing a deep research report, and users will expect a thorough answer.
- Use bullet points to list out information when appropriate, but by default, write in paragraph form.

REMEMBER:
The brief and research may be in English, but you need to translate this information to the right language when writing the final answer.
Make sure the final answer report is in the SAME language as the human messages in the message history.

Format the report in clear markdown with proper structure and include source references where appropriate.

<Citation Rules>
- Assign each unique URL a single citation number in your text
- End with ### Sources that lists each source with corresponding numbers
- IMPORTANT: Number sources sequentially without gaps (1,2,3,4...) in the final list regardless of which sources you choose
- Each source should be a separate line item in a list, so that in markdown it is rendered as a list.
- Example format:
 [1] Source Title: URL
 [2] Source Title: URL
- Citations are extremely important. Make sure to include these, and pay a lot of attention to getting these right. Users will often use these citations to look into more information.
</Citation Rules>
</report_instructions>

You have access to a few tools.

## `internet_search`

Use this to run an internet search for a given query. You can specify the number of results, the topic, and whether raw content should be included."""

# Create the agent
agent = create_deep_agent(
    tools=[internet_search],
    system_prompt=research_instructions,
    subagents=[critique_sub_agent, research_sub_agent],
)
```

### 3.2 Key Pattern Analysis

**Multi-Agent Orchestration:**
- Main coordinator agent
- Specialized research subagent for deep investigations
- Critique subagent for quality assurance
- Parallel execution support (implicit in instructions)

**Workflow Pattern:**
1. Record question to virtual filesystem (`question.txt`)
2. Delegate research to specialized subagent
3. Write draft report (`final_report.md`)
4. Iterate with critique feedback
5. Refine until satisfied

**Context Management:**
- Virtual filesystem isolates artifacts
- Subagents prevent context bloat
- Only final results returned to main agent

**Quality Assurance:**
- Dedicated critique agent reviews output
- Iterative refinement loop
- Comprehensive quality checklist

---

## 4. Analysis Subagent Capabilities

### 4.1 Built-in Analysis Patterns

DeepAgents doesn't include pre-built "analysis" agents, but provides the **framework to build them easily**:

```python
analysis_subagent = {
    "name": "data-analyzer",
    "description": "Analyzes research findings for patterns, insights, and trends",
    "system_prompt": """You are a data analyst specializing in synthesizing research findings.

Your tasks:
1. Identify key patterns and themes across research sources
2. Extract actionable insights
3. Highlight contradictions or gaps in information
4. Provide quantitative analysis where applicable
5. Return structured analysis in clear sections

Format your analysis as:
## Key Findings
- Finding 1
- Finding 2

## Patterns and Trends
[Detailed analysis]

## Gaps and Contradictions
[What's missing or contradictory]

## Recommendations
[Actionable insights]
""",
    "tools": [],  # Analysis typically doesn't need external tools
}
```

### 4.2 Analysis Workflow Example

```python
# Multi-stage research + analysis workflow
agent = create_deep_agent(
    tools=[internet_search],
    system_prompt="""You are a research coordinator.

Workflow:
1. Use research-agent to gather information on the topic
2. Use data-analyzer to extract insights from research
3. Use synthesis-agent to combine multiple analyses
4. Write comprehensive report with analysis

Store intermediate artifacts:
- `research_findings.md` - Raw research
- `analysis_report.md` - Analytical insights
- `final_synthesis.md` - Combined report
""",
    subagents=[
        research_subagent,
        analysis_subagent,
        synthesis_subagent
    ]
)
```

### 4.3 Integration with Our Requirements

**For Our System's Analysis Needs:**

```python
# Custom analysis subagent for deep research canvas
deep_analysis_agent = {
    "name": "deep-analyzer",
    "description": "Performs comprehensive analysis on research findings with citation tracking",
    "system_prompt": """You are a senior research analyst.

Tasks:
1. Review research findings in `research_notes.md`
2. Identify key themes and patterns
3. Cross-reference sources for validation
4. Track citation frequency and credibility
5. Generate analysis with evidence backing

Output Format:
## Executive Summary
[2-3 paragraph overview]

## Detailed Analysis
### Theme 1: [Name]
Evidence: [Citations]
Analysis: [Detailed explanation]

### Theme 2: [Name]
Evidence: [Citations]
Analysis: [Detailed explanation]

## Source Quality Assessment
- High confidence: [Sources]
- Medium confidence: [Sources]
- Requires validation: [Sources]

## Gaps and Next Steps
[What's missing, what to research next]
""",
    "tools": [],
    "middleware": []  # Can add custom middleware for citation tracking
}
```

**Key Takeaway**: Analysis agents are **not pre-built** but the framework makes them **trivial to implement** with proper prompting and subagent configuration.

---

## 5. Writing Subagent Capabilities

### 5.1 Built-in Writing Patterns

Similar to analysis, writing agents are **framework-supported but not pre-built**:

```python
writing_subagent = {
    "name": "report-writer",
    "description": "Generates polished, publication-quality research reports",
    "system_prompt": """You are a professional technical writer specializing in research reports.

Your responsibilities:
1. Read research findings from virtual filesystem
2. Structure content logically with clear sections
3. Use markdown formatting appropriately
4. Maintain consistent tone and style
5. Ensure proper citations throughout
6. Write concisely but comprehensively

Report Structure Template:
# [Title]

## Executive Summary
[High-level overview, 200-300 words]

## Introduction
[Context and research objectives]

## Methodology
[How research was conducted]

## Findings
### Finding 1
[Detailed explanation with citations]

### Finding 2
[Detailed explanation with citations]

## Analysis
[Interpretation of findings]

## Conclusions
[Key takeaways and implications]

## Recommendations
[Actionable next steps]

## Sources
[Numbered citation list]

Formatting Guidelines:
- Use ## for main sections
- Use ### for subsections
- Use bullet points for lists
- Use **bold** for emphasis
- Cite sources as [1], [2], etc.
- Number sources sequentially in Sources section
""",
    "tools": ["read_file", "write_file"],  # Built-in filesystem tools
}
```

### 5.2 Multi-Stage Writing Workflow

The research agent example demonstrates a sophisticated writing workflow:

**Stage 1: Research** → Gather information
**Stage 2: Draft** → Write initial report
**Stage 3: Critique** → Quality review
**Stage 4: Refine** → Incorporate feedback
**Stage 5: Finalize** → Polish and publish

This can be extended:

```python
# Advanced writing workflow with multiple specialists
agent = create_deep_agent(
    tools=[internet_search],
    system_prompt="""You are a research report coordinator.

Workflow:
1. research-agent: Gather information
2. outliner-agent: Create report structure
3. section-writer: Write each section in detail
4. citation-manager: Verify and format citations
5. editor-agent: Copyedit and polish
6. formatter-agent: Final formatting and styling

Use the virtual filesystem to track:
- `outline.md` - Report structure
- `sections/` - Individual sections (Note: filesystem is flat, use naming like `section_1_intro.md`)
- `draft_report.md` - Combined draft
- `final_report.md` - Polished version
""",
    subagents=[
        research_subagent,
        outliner_subagent,
        section_writer_subagent,
        citation_manager_subagent,
        editor_subagent,
        formatter_subagent
    ]
)
```

### 5.3 Writing Quality Control

The critique agent pattern from the research example is excellent for writing QA:

```python
writing_critique_agent = {
    "name": "writing-critic",
    "description": "Reviews written content for quality, clarity, and completeness",
    "system_prompt": """You are an expert editor reviewing research reports.

Review Criteria:
1. **Clarity**: Is the writing clear and easy to understand?
2. **Structure**: Does the report flow logically?
3. **Completeness**: Are all topics covered thoroughly?
4. **Citations**: Are sources properly cited and relevant?
5. **Style**: Is the tone consistent and professional?
6. **Grammar**: Are there any grammatical errors?
7. **Accuracy**: Do claims align with cited sources?

Review Process:
1. Read the report from virtual filesystem
2. Check against each criterion
3. Provide specific, actionable feedback
4. Rate each criterion (Excellent/Good/Needs Work/Poor)
5. Suggest concrete improvements

Output Format:
## Overall Assessment
[Summary rating and key issues]

## Detailed Feedback

### Clarity: [Rating]
[Specific feedback and examples]

### Structure: [Rating]
[Specific feedback and examples]

[... continue for each criterion ...]

## Priority Improvements
1. [Highest priority fix]
2. [Second priority fix]
3. [Third priority fix]

## Minor Suggestions
- [Suggestion 1]
- [Suggestion 2]
""",
    "tools": ["read_file"],  # Read-only for critique
}
```

**Key Takeaway**: Writing agents follow the same pattern as analysis - **framework provides the structure, you provide the specialization**.

---

## 6. Multi-Agent Orchestration

### 6.1 Built-in Orchestration Mechanisms

DeepAgents provides **sophisticated orchestration out-of-the-box**:

#### Supervisor Pattern

The main agent acts as a supervisor, delegating to specialized subagents:

```python
# Main agent coordinates subagents
agent = create_deep_agent(
    tools=[shared_tools],
    system_prompt="Coordinate research, analysis, and writing subagents",
    subagents=[researcher, analyzer, writer]
)
```

#### Parallel Execution

Implicit in the instructions (from research example):

> "Instead, you should break down a large topic into the necessary components, and then call multiple research agents in parallel, one for each sub question."

The agent can spawn multiple subagents concurrently.

#### Sequential Workflows

Explicitly controlled via instructions:

```python
system_prompt = """Execute tasks in sequence:
1. research-agent: Gather data
2. analysis-agent: Analyze findings
3. writing-agent: Generate report
4. critique-agent: Review quality
5. If issues found, loop back to step 2 or 3
"""
```

### 6.2 Handoff Patterns

**Artifact-Based Handoff** (Recommended):

```python
# Agent A writes to filesystem
research_agent_prompt = """
Conduct research and write findings to:
- `research_notes.md` - Detailed notes
- `key_sources.md` - Important sources
- `research_summary.md` - Brief overview
"""

# Agent B reads from filesystem
analysis_agent_prompt = """
Read research findings from:
- `research_notes.md`
- `key_sources.md`

Generate analysis and write to:
- `analysis_report.md`
"""
```

**Message-Based Handoff**:

The subagent's final response becomes the "result" for the main agent:

```python
# Research subagent returns summary
research_result = "Based on 15 sources, quantum computing market will grow 35% CAGR..."

# Main agent receives this as a message
# Can then pass to next subagent
```

### 6.3 State Sharing

DeepAgents manages state through **multiple channels**:

#### 1. Messages State

```python
class DeepAgentState:
    messages: Annotated[list, add_messages]  # Conversation history
    # Subagents inherit message context
```

#### 2. Virtual Filesystem State

```python
class DeepAgentState:
    files: Annotated[dict[str, str], file_reducer]  # Filename → content
    # All agents share the same filesystem
```

#### 3. Todo State

```python
class DeepAgentState:
    todos: list[Todo]  # {content, status}
    # Shared planning state
```

#### 4. Custom State via Middleware

```python
from deepagents.middleware import AgentMiddleware

class CustomStateMiddleware(AgentMiddleware):
    @property
    def state_schema(self):
        return {
            "research_metadata": {
                "search_count": int,
                "sources_found": list,
                "confidence_score": float
            }
        }

    def modify_model_request(self, state, request):
        # Inject custom state into prompts
        request["prompt"] += f"\n\nCurrent search count: {state['research_metadata']['search_count']}"
        return request

# Apply to agent
agent = create_deep_agent(
    system_prompt="...",
    middleware=[CustomStateMiddleware()]
)
```

### 6.4 Agent Communication Protocols

**Direct Delegation** (Primary Method):

```python
# Main agent explicitly calls subagent
# Instruction: "Use research-agent to investigate quantum computing trends"
# Framework handles routing via `task` tool
```

**Implicit Coordination** (Via Filesystem):

```python
# Agent A:
write_file("next_steps.md", "Analyze these 10 sources for contradictions")

# Agent B (in next iteration):
# Reads next_steps.md and acts on it
```

**Conditional Routing**:

```python
system_prompt = """
If research requires technical analysis:
  - Use technical-analyzer agent

If research requires business analysis:
  - Use business-analyzer agent

If both needed:
  - Use technical-analyzer first
  - Then use business-analyzer
  - Finally use synthesis-agent to combine
"""
```

### 6.5 Advanced: Cyclic Workflows

DeepAgents (built on LangGraph) supports **cyclic graphs**:

```python
# Iterative refinement loop
system_prompt = """
Loop until quality threshold met:

1. writing-agent: Generate draft
2. critique-agent: Review quality
3. If score < 8/10:
   - analysis-agent: Identify gaps
   - research-agent: Fill gaps
   - Go back to step 1
4. If score >= 8/10:
   - finalize-agent: Polish and publish
"""
```

This is **implicit** in the framework - the agent decides when to loop based on instructions.

---

## 7. Open Deep Research Architecture

### 7.1 Project Overview

`open_deep_research` is LangChain's **reference implementation** of a production-grade deep research system using DeepAgents patterns (though implemented directly with LangGraph rather than using the deepagents package).

**Key Stats:**
- Ranks #6 on Deep Research Bench Leaderboard
- Score: 0.4344 (GPT-4o), 0.4943 (GPT-5)
- Fully open-source (MIT License)
- Multi-provider support (OpenAI, Anthropic, Google)

### 7.2 Architecture Components

**Source Code Structure:**

```
src/open_deep_research/
├── configuration.py      # Configuration management
├── deep_researcher.py    # Main agent implementation
├── prompts.py           # Prompt templates
├── state.py             # State definitions
└── utils.py             # Utility functions
```

### 7.3 State Management

**From `state.py`:**

```python
###################
# Structured Outputs
###################
class ConductResearch(BaseModel):
    """Call this tool to conduct research on a specific topic."""
    research_topic: str = Field(
        description="The topic to research. Should be a single topic, and should be described in high detail (at least a paragraph).",
    )

class ResearchComplete(BaseModel):
    """Call this tool to indicate that the research is complete."""

class Summary(BaseModel):
    """Research summary with key findings."""
    summary: str
    key_excerpts: str

class ClarifyWithUser(BaseModel):
    """Model for user clarification requests."""
    need_clarification: bool
    question: str
    verification: str

class ResearchQuestion(BaseModel):
    """Research question and brief for guiding research."""
    research_brief: str

###################
# State Definitions
###################
def override_reducer(current_value, new_value):
    """Reducer function that allows overriding values in state."""
    if isinstance(new_value, dict) and new_value.get("type") == "override":
        return new_value.get("value", new_value)
    else:
        return operator.add(current_value, new_value)

class AgentInputState(MessagesState):
    """InputState is only 'messages'."""

class AgentState(MessagesState):
    """Main agent state containing messages and research data."""
    supervisor_messages: Annotated[list[MessageLikeRepresentation], override_reducer]
    research_brief: Optional[str]
    raw_notes: Annotated[list[str], override_reducer] = []
    notes: Annotated[list[str], override_reducer] = []
    final_report: str

class SupervisorState(TypedDict):
    """State for the supervisor that manages research tasks."""
    supervisor_messages: Annotated[list[MessageLikeRepresentation], override_reducer]
    research_brief: str
    notes: Annotated[list[str], override_reducer] = []
    research_iterations: int = 0
    raw_notes: Annotated[list[str], override_reducer] = []

class ResearcherState(TypedDict):
    """State for individual researchers conducting research."""
    researcher_messages: Annotated[list[MessageLikeRepresentation], operator.add]
    tool_call_iterations: int = 0
    research_topic: str
    compressed_research: str
    raw_notes: Annotated[list[str], override_reducer] = []
```

**Key Patterns:**

1. **Structured Outputs**: Pydantic models enforce tool schemas
2. **State Layering**: Separate states for supervisor, researcher, and main agent
3. **Custom Reducers**: `override_reducer` allows value replacement (not just addition)
4. **Iteration Tracking**: Built-in counters for loop control

### 7.4 Multi-Stage Workflow

**From Documentation Analysis:**

```
User Input
→ Clarification (optional)
→ Research Brief Generation
→ Supervisor Coordination
  ├→ Parallel Researcher 1
  ├→ Parallel Researcher 2
  └→ Parallel Researcher N
→ Compression & Synthesis
→ Final Report Generation
```

**Clarification Phase:**

```python
def clarify_with_user():
    """Determines whether the research request needs clarification before proceeding.

    Analyzes user messages and asks clarifying questions if the research scope is unclear.
    """
```

**Research Brief Generation:**

```python
def write_research_brief():
    """Transforms user input into structured research objectives.

    Formats the user's messages and initializes the supervisor with appropriate context.
    """
```

**Supervisor Coordination:**

```python
def supervisor():
    """Manages research strategy and task delegation.

    Uses three available tools:
    - think_tool: For strategic planning
    - ConductResearch: For delegating tasks to researchers
    - ResearchComplete: For signaling completion
    """
```

**Individual Research Execution:**

```python
def researcher():
    """Conducts focused investigation on specific topics.

    Uses available tools (search, think_tool, MCP tools) to gather comprehensive information.
    """
```

**Research Compression:**

```python
def compress_research():
    """Synthesizes findings into concise summaries while preserving important information.

    Handles token limit issues through progressive message truncation.
    """
```

**Report Generation:**

```python
def final_report_generation():
    """Creates comprehensive final reports with retry logic for handling token constraints."""
```

### 7.5 Model Specialization

**Cost Optimization Through Task-Specific Models:**

| Stage | Model | Purpose |
|-------|-------|---------|
| Summarization | gpt-4o-mini | Search result compression (cost-effective) |
| Research | gpt-4o | Core analysis and planning (capability) |
| Compression | gpt-4o-mini | Finding synthesis (cost-effective) |
| Final Report | gpt-4o | Comprehensive output (quality) |

This is **highly adaptable** - can use Claude, Gemini, etc.

### 7.6 Configuration System

**From Documentation:**

```python
class Configuration:
    """Centralized configuration management."""

    # Research parameters
    max_concurrent_research_units: int = Field(ge=1, le=20, default=5)
    max_researcher_iterations: int = Field(default=3)
    max_react_tool_calls: int = Field(default=5)
    allow_clarification: bool = Field(default=True)

    # Search configuration
    search_api: Literal["tavily", "openai", "anthropic", None] = "tavily"

    # Model configuration
    summarization_model: str = "gpt-4o-mini"
    research_model: str = "gpt-4o"
    compression_model: str = "gpt-4o-mini"
    final_report_model: str = "gpt-4o"
```

**Loading Priority:**
1. Environment variables (uppercase)
2. Runtime configuration (dict)
3. Default field values
4. Pydantic validation

### 7.7 Search Tool Integration

**Tavily Implementation:**

```python
def tavily_search(queries: list[str]) -> str:
    """Professional search API with parallel query execution.

    Features:
    - Parallel query execution for multiple search formulations
    - URL-based deduplication across results
    - Automatic summarization of search content
    - 50,000 character limit to prevent token overflow
    - 60-second timeout with structured retry logic
    """
```

**Provider Native Search:**

```python
def get_search_tool(provider: str):
    """Returns provider-appropriate search implementation.

    - Anthropic: native web_search_20250305
    - OpenAI: web_search_preview
    - Tavily: custom implementation
    - None: empty tool list
    """
```

### 7.8 Think Tool Pattern

**Strategic Reflection:**

```python
def think_tool():
    """Enables agents to pause and reflect.

    Agents use this to:
    - Analyze findings
    - Assess information gaps
    - Evaluate evidence sufficiency
    - Plan subsequent research actions

    Creates deliberate checkpoints in the research process.
    """
```

This is a **critical pattern** - prevents agents from rushing through tasks without strategic thinking.

### 7.9 Performance Metrics

**Deep Research Bench Results:**

- **GPT-4o**: 0.4344 score, 58M tokens, ~$46 cost
- **GPT-5**: 0.4943 score, 204M tokens, ~$46 cost
- Ranks #6 overall on leaderboard

**Key Insight**: Production-quality results at reasonable cost.

---

## 8. Integration with Our Requirements

### 8.1 Requirements Mapping

| Our Requirement | DeepAgents Support | Implementation Effort |
|----------------|-------------------|---------------------|
| **Research Subagent** | ✅ Excellent (pre-built patterns) | LOW - Use research_agent.py example |
| **Analysis Subagent** | ⚠️ Framework only | LOW - Simple subagent configuration |
| **Writing Subagent** | ⚠️ Framework only | LOW - Simple subagent configuration |
| **Multi-Agent Orchestration** | ✅ Excellent (supervisor pattern) | LOW - Built-in coordination |
| **6 Effort Levels** | ❌ Not built-in | MEDIUM - Custom configuration layer |
| **Search Count Tracking** | ⚠️ Partial (iteration tracking exists) | MEDIUM - Extend state management |
| **Loop Detection** | ⚠️ Partial (max iterations exists) | LOW - Already implemented in open_deep_research |
| **HITL Approval** | ✅ Excellent (interrupt_on) | LOW - Built-in middleware |
| **Knowledge Graph** | ❌ Not built-in | HIGH - Custom integration needed |
| **Vector DB RAG** | ❌ Not built-in | MEDIUM - Add as custom tools |
| **Context Summarization** | ✅ Excellent (SummarizationMiddleware) | LOW - Pre-built |
| **Virtual Filesystem** | ✅ Excellent (FilesystemMiddleware) | LOW - Pre-built |
| **Planning/TODO** | ✅ Excellent (PlanningMiddleware) | LOW - Pre-built |
| **LangSmith Observability** | ✅ Excellent (native integration) | LOW - Automatic |
| **State Persistence** | ✅ Excellent (LangGraph checkpointer) | LOW - Built-in |
| **Streaming Support** | ✅ Excellent (LangGraph streaming) | LOW - Built-in |

### 8.2 Effort Level Configuration

**Custom Implementation Needed:**

```python
# Define effort configurations
EFFORT_CONFIGS = {
    "quick": {
        "max_searches": 3,
        "max_iterations": 1,
        "max_concurrent_researchers": 1,
        "compression_enabled": True,
        "critique_enabled": False,
        "research_depth": "surface"
    },
    "balanced": {
        "max_searches": 8,
        "max_iterations": 2,
        "max_concurrent_researchers": 2,
        "compression_enabled": True,
        "critique_enabled": False,
        "research_depth": "moderate"
    },
    "thorough": {
        "max_searches": 15,
        "max_iterations": 3,
        "max_concurrent_researchers": 3,
        "compression_enabled": True,
        "critique_enabled": True,
        "research_depth": "comprehensive"
    },
    "deep": {
        "max_searches": 30,
        "max_iterations": 4,
        "max_concurrent_researchers": 4,
        "compression_enabled": False,  # Keep all detail
        "critique_enabled": True,
        "research_depth": "exhaustive"
    },
    "exhaustive": {
        "max_searches": 50,
        "max_iterations": 5,
        "max_concurrent_researchers": 5,
        "compression_enabled": False,
        "critique_enabled": True,
        "research_depth": "comprehensive"
    },
    "definitive": {
        "max_searches": 100,
        "max_iterations": 8,
        "max_concurrent_researchers": 8,
        "compression_enabled": False,
        "critique_enabled": True,
        "research_depth": "authoritative"
    }
}

# Custom middleware for effort level enforcement
class EffortLevelMiddleware(AgentMiddleware):
    def __init__(self, effort_level: str):
        self.config = EFFORT_CONFIGS[effort_level]

    @property
    def state_schema(self):
        return {
            "effort_config": dict,
            "search_count": int,
            "iteration_count": int
        }

    def modify_model_request(self, state, request):
        # Inject effort constraints into prompt
        search_count = state.get("search_count", 0)
        remaining = self.config["max_searches"] - search_count

        request["prompt"] += f"""

EFFORT LEVEL CONSTRAINTS:
- Research depth: {self.config['research_depth']}
- Searches remaining: {remaining}/{self.config['max_searches']}
- Max iterations: {self.config['max_iterations']}
- Concurrent researchers: {self.config['max_concurrent_researchers']}
- Critique enabled: {self.config['critique_enabled']}

Adjust your research strategy accordingly.
"""
        return request

    def should_continue(self, state):
        """Check if agent should continue or stop based on effort limits."""
        if state.get("search_count", 0) >= self.config["max_searches"]:
            return False
        if state.get("iteration_count", 0) >= self.config["max_iterations"]:
            return False
        return True

# Usage
agent = create_deep_agent(
    tools=[internet_search],
    system_prompt=research_instructions,
    subagents=[research_sub_agent, critique_sub_agent],
    middleware=[EffortLevelMiddleware("thorough")]
)
```

**Implementation Effort**: MEDIUM (2-3 days)

### 8.3 Search Count Tracking

**Extension of Existing Pattern:**

```python
class SearchTrackingMiddleware(AgentMiddleware):
    @property
    def state_schema(self):
        return {
            "search_count": int,
            "search_history": list,
            "search_results_summary": list
        }

    def before_tool_execution(self, state, tool_name, tool_input):
        """Track search tool invocations."""
        if tool_name == "internet_search":
            state["search_count"] = state.get("search_count", 0) + 1
            state["search_history"].append({
                "query": tool_input.get("query"),
                "timestamp": datetime.now().isoformat()
            })
        return state

    def after_tool_execution(self, state, tool_name, tool_output):
        """Summarize search results."""
        if tool_name == "internet_search":
            state["search_results_summary"].append({
                "query": tool_input.get("query"),
                "result_count": len(tool_output.get("results", [])),
                "top_source": tool_output.get("results", [{}])[0].get("url")
            })
        return state
```

**Integration**: Add to `open_deep_research` configuration

**Implementation Effort**: LOW (1 day)

### 8.4 Loop Detection

**Already Partially Implemented in open_deep_research:**

```python
class SupervisorState(TypedDict):
    research_iterations: int = 0
    # ...

def supervisor():
    # Check iteration limit
    if state["research_iterations"] >= config.max_researcher_iterations:
        return Command(goto="compress_research")
```

**Enhancement for Pattern Detection:**

```python
class LoopDetectionMiddleware(AgentMiddleware):
    @property
    def state_schema(self):
        return {
            "action_history": list,
            "loop_detected": bool
        }

    def detect_loop(self, action_history):
        """Detect repeated action patterns."""
        if len(action_history) < 6:
            return False

        # Check for repeated 3-action pattern
        recent_6 = action_history[-6:]
        pattern_a = tuple(recent_6[:3])
        pattern_b = tuple(recent_6[3:])

        if pattern_a == pattern_b:
            return True

        return False

    def after_model_call(self, state, response):
        """Track actions and detect loops."""
        action = response.get("tool_calls", [{}])[0].get("name")
        state["action_history"].append(action)

        if self.detect_loop(state["action_history"]):
            state["loop_detected"] = True
            # Inject loop warning into next prompt

        return state
```

**Implementation Effort**: LOW (1-2 days)

### 8.5 HITL Approval Workflow

**Already Built-in:**

```python
agent = create_deep_agent(
    tools=[internet_search, write_file, edit_file],
    system_prompt=research_instructions,
    subagents=[research_sub_agent],
    interrupt_on={
        "internet_search": {
            "allowed_decisions": ["approve", "edit", "reject"]
        },
        "write_file": {
            "allowed_decisions": ["approve", "reject"]
        }
    }
)

# In our application (async endpoint)
@app.post("/research/invoke")
async def research_invoke(request: ResearchRequest):
    thread = await client.threads.create()

    # Start research
    run = await client.runs.create(
        thread_id=thread.thread_id,
        assistant_id=agent.id,
        input={"messages": [{"role": "user", "content": request.question}]}
    )

    # Check for interrupts
    if run.status == "interrupted":
        # Wait for user approval via WebSocket or HTTP endpoint
        return {"status": "awaiting_approval", "tool": run.interrupted_on}

    # Stream results
    async for event in client.runs.stream(run_id=run.run_id):
        yield event
```

**Implementation Effort**: LOW (Already working in our current system)

### 8.6 Knowledge Graph Integration

**Custom Tool Implementation:**

```python
from neo4j import GraphDatabase

def knowledge_graph_query(cypher_query: str) -> str:
    """Query the knowledge graph for entity relationships.

    Args:
        cypher_query: Cypher query to execute

    Returns:
        Query results as formatted string
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        result = session.run(cypher_query)
        records = list(result)

    # Format results
    return json.dumps([dict(record) for record in records], indent=2)

def knowledge_graph_add_entity(entity_type: str, entity_name: str, properties: dict) -> str:
    """Add an entity to the knowledge graph.

    Args:
        entity_type: Type of entity (Person, Organization, Concept, etc.)
        entity_name: Name of the entity
        properties: Additional properties

    Returns:
        Success message
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        query = f"""
        MERGE (e:{entity_type} {{name: $name}})
        SET e += $properties
        RETURN e
        """
        session.run(query, name=entity_name, properties=properties)

    return f"Added {entity_type} entity: {entity_name}"

def knowledge_graph_add_relationship(
    entity1: str,
    relationship: str,
    entity2: str,
    properties: dict = None
) -> str:
    """Add a relationship between two entities.

    Args:
        entity1: First entity name
        relationship: Relationship type
        entity2: Second entity name
        properties: Optional relationship properties

    Returns:
        Success message
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        query = f"""
        MATCH (a {{name: $entity1}})
        MATCH (b {{name: $entity2}})
        MERGE (a)-[r:{relationship}]->(b)
        SET r += $properties
        RETURN r
        """
        session.run(query, entity1=entity1, entity2=entity2, properties=properties or {})

    return f"Created relationship: {entity1} -{relationship}-> {entity2}"

# Add to agent
agent = create_deep_agent(
    tools=[
        internet_search,
        knowledge_graph_query,
        knowledge_graph_add_entity,
        knowledge_graph_add_relationship
    ],
    system_prompt="""You are a research agent with access to a knowledge graph.

As you conduct research:
1. Extract key entities (people, organizations, concepts)
2. Add them to the knowledge graph
3. Identify relationships between entities
4. Query the graph to find connections
5. Use graph insights to guide further research

Example workflow:
- Research "quantum computing companies"
- Add entities: Google, IBM, Rigetti (Organizations)
- Add relationships: Google -DEVELOPS-> Quantum Processors
- Query graph: What other technologies does Google develop?
- Use results to expand research
""",
    subagents=[research_sub_agent]
)
```

**Implementation Effort**: MEDIUM (3-4 days for full integration)

### 8.7 Vector Database RAG

**Custom Retrieval Tool:**

```python
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# Initialize vector store
vectorstore = Chroma(
    collection_name="research_documents",
    embedding_function=OpenAIEmbeddings()
)

def vector_search(query: str, top_k: int = 5) -> str:
    """Search vector database for relevant documents.

    Args:
        query: Search query
        top_k: Number of results to return

    Returns:
        Formatted search results with sources
    """
    results = vectorstore.similarity_search_with_score(query, k=top_k)

    formatted = []
    for doc, score in results:
        formatted.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "Unknown"),
            "score": float(score)
        })

    return json.dumps(formatted, indent=2)

def add_to_vector_store(content: str, metadata: dict) -> str:
    """Add document to vector database.

    Args:
        content: Document content
        metadata: Document metadata (source, title, etc.)

    Returns:
        Success message
    """
    vectorstore.add_texts([content], metadatas=[metadata])
    return f"Added document to vector store: {metadata.get('title', 'Untitled')}"

# Add to agent
agent = create_deep_agent(
    tools=[
        internet_search,
        vector_search,
        add_to_vector_store
    ],
    system_prompt="""You are a research agent with RAG capabilities.

Research workflow:
1. Search the web for new information
2. Add valuable findings to vector store
3. Use vector search to find related existing knowledge
4. Synthesize web + vector results
5. Avoid duplicate research on topics already covered

Example:
- Query: "quantum computing applications"
- First check vector store for existing research
- If found, use as context and focus on new angles
- If not found, conduct fresh research
- Add findings to vector store for future use
""",
    subagents=[research_sub_agent]
)
```

**Implementation Effort**: MEDIUM (2-3 days)

### 8.8 Real-Time Progress Tracking

**WebSocket Streaming Integration:**

```python
# In our FastAPI backend
from fastapi import WebSocket
import json

@app.websocket("/research/stream/{thread_id}")
async def research_stream(websocket: WebSocket, thread_id: str):
    await websocket.accept()

    try:
        # Stream agent execution
        async for event in agent.astream(
            {"messages": [{"role": "user", "content": "..."}]},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="values"
        ):
            # Extract progress information
            progress_update = {
                "type": "progress",
                "current_step": extract_current_step(event),
                "todos": event.get("todos", []),
                "search_count": event.get("search_count", 0),
                "files_created": list(event.get("files", {}).keys()),
                "status": event.get("status", "running")
            }

            await websocket.send_json(progress_update)

            # Send message updates
            if "messages" in event:
                await websocket.send_json({
                    "type": "message",
                    "message": event["messages"][-1]
                })

    except Exception as e:
        await websocket.send_json({"type": "error", "error": str(e)})
    finally:
        await websocket.close()

def extract_current_step(event):
    """Extract human-readable current step from agent state."""
    if event.get("todos"):
        in_progress = [t for t in event["todos"] if t["status"] == "in_progress"]
        if in_progress:
            return in_progress[0]["content"]
    return "Thinking..."
```

**Implementation Effort**: LOW (Already have WebSocket infrastructure)

---

## 9. Gap Analysis: Built vs Needed

### 9.1 What's Built-In and Production-Ready

✅ **Excellent Support (Use As-Is):**

1. **Multi-Agent Orchestration**
   - Supervisor-researcher patterns
   - Subagent spawning and delegation
   - Parallel execution support
   - Sequential workflows
   - Cyclic refinement loops

2. **Context Management**
   - Virtual filesystem (state-persisted)
   - Summarization middleware (120k token limits)
   - Artifact-based handoffs
   - Context isolation per subagent

3. **Planning and Tracking**
   - Built-in TODO system
   - Task decomposition
   - Progress tracking
   - Adaptive planning

4. **State Management**
   - LangGraph state graphs
   - Custom reducers
   - Checkpointing and persistence
   - State sharing across agents

5. **Human-in-the-Loop**
   - Interrupt on specific tools
   - Approve/edit/reject decisions
   - Batch approval handling
   - Configurable approval rules

6. **Observability**
   - LangSmith native integration
   - Tracing and debugging
   - Performance metrics
   - Error tracking

7. **Streaming and Async**
   - Real-time event streaming
   - Async tool execution
   - WebSocket integration patterns

8. **Search Integration**
   - Tavily search (production-grade)
   - Native provider search (OpenAI, Anthropic)
   - MCP server integration
   - Custom search tools

### 9.2 What's Framework-Supported (Easy to Build)

⚠️ **Good Framework Support (1-3 Days Implementation):**

1. **Analysis Subagents**
   - Framework: ✅ Subagent configuration
   - Need to build: Specialized prompts and workflow
   - Complexity: LOW

2. **Writing Subagents**
   - Framework: ✅ Virtual filesystem + subagents
   - Need to build: Writing-specific prompts and quality checks
   - Complexity: LOW

3. **Search Count Tracking**
   - Framework: ✅ Iteration tracking exists
   - Need to build: Search-specific counter middleware
   - Complexity: LOW

4. **Loop Detection**
   - Framework: ✅ Max iteration limits exist
   - Need to build: Pattern detection logic
   - Complexity: LOW

5. **Vector Database RAG**
   - Framework: ✅ Custom tool support
   - Need to build: Retrieval tool implementations
   - Complexity: MEDIUM

### 9.3 What Needs Custom Development

❌ **Requires Custom Implementation (3-7 Days Each):**

1. **Effort Level Configuration**
   - No built-in concept of difficulty levels
   - Need: Custom middleware for effort constraints
   - Need: Configuration system for 6 levels
   - Need: Dynamic search/iteration limits
   - Complexity: MEDIUM
   - Effort: 3-4 days

2. **Knowledge Graph Integration**
   - No built-in graph database support
   - Need: Custom tools for Neo4j/Memgraph
   - Need: Entity extraction logic
   - Need: Relationship mapping
   - Complexity: MEDIUM-HIGH
   - Effort: 4-5 days

3. **Advanced Citation Management**
   - Basic citation in prompts exists
   - Need: Structured citation tracking
   - Need: Source deduplication
   - Need: Citation validation
   - Complexity: MEDIUM
   - Effort: 2-3 days

4. **Custom Approval UI**
   - Framework provides approval hooks
   - Need: UI for approval decisions
   - Need: WebSocket real-time updates
   - Need: Approval queue management
   - Complexity: MEDIUM
   - Effort: 3-4 days (already have UI, just integration)

5. **Research Quality Metrics**
   - No built-in quality scoring
   - Need: Custom evaluation logic
   - Need: Confidence scoring
   - Need: Source credibility assessment
   - Complexity: HIGH
   - Effort: 5-7 days

### 9.4 Gap Summary Matrix

| Feature Category | Built-In | Framework Support | Custom Needed | Est. Effort |
|-----------------|----------|-------------------|---------------|-------------|
| Multi-Agent Orchestration | 90% | ✅ Excellent | 10% refinement | 1-2 days |
| Research Workflow | 85% | ✅ Excellent | 15% customization | 2-3 days |
| Analysis Capabilities | 20% | ✅ Good | 80% implementation | 2-3 days |
| Writing Capabilities | 20% | ✅ Good | 80% implementation | 2-3 days |
| Context Management | 95% | ✅ Excellent | 5% tuning | 1 day |
| HITL Approval | 85% | ✅ Excellent | 15% UI integration | 2-3 days |
| Search Tools | 90% | ✅ Excellent | 10% customization | 1 day |
| Effort Level System | 0% | ⚠️ Partial | 100% implementation | 3-4 days |
| Search Tracking | 40% | ✅ Good | 60% implementation | 1-2 days |
| Loop Detection | 50% | ✅ Good | 50% enhancement | 1-2 days |
| Knowledge Graph | 0% | ⚠️ Partial | 100% implementation | 4-5 days |
| Vector RAG | 0% | ✅ Good | 100% implementation | 2-3 days |
| Citation Management | 30% | ⚠️ Partial | 70% implementation | 2-3 days |
| Quality Metrics | 0% | ⚠️ Partial | 100% implementation | 5-7 days |
| Observability | 95% | ✅ Excellent | 5% configuration | 1 day |
| State Persistence | 100% | ✅ Excellent | 0% | 0 days |
| Streaming | 100% | ✅ Excellent | 0% | 0 days |

**Overall Coverage: 70-75% pre-built or easy to implement**

---

## 10. Migration Recommendations

### 10.1 Migration Strategy: Incremental Adoption

**Phase 1: Foundation (Week 1)**
- Install deepagents and dependencies
- Create basic research agent using research_agent.py pattern
- Integrate with existing WebSocket streaming
- Test with simplified workflow (no effort levels yet)
- Validate state persistence and HITL approval

**Phase 2: Subagent Specialization (Week 2)**
- Implement analysis subagent with custom prompt
- Implement writing subagent with quality checks
- Configure multi-agent orchestration
- Add critique agent for quality assurance
- Test end-to-end research → analysis → writing workflow

**Phase 3: Custom Features (Week 3)**
- Implement effort level configuration system
- Add search count tracking middleware
- Enhance loop detection logic
- Build custom approval UI integration
- Add real-time progress tracking

**Phase 4: Advanced Integration (Week 4)**
- Integrate knowledge graph tools
- Add vector database RAG tools
- Implement citation management system
- Build quality metrics evaluation
- Optimize performance and costs

**Phase 5: Polish and Production (Week 5)**
- Add comprehensive error handling
- Optimize prompts based on testing
- Fine-tune effort level configurations
- Load testing and scaling
- Documentation and monitoring

### 10.2 Code Migration Pattern

**Current System → DeepAgents:**

```python
# BEFORE (Our current custom implementation)
class ResearchOrchestrator:
    def __init__(self):
        self.research_agent = ResearchAgent()
        self.analysis_agent = AnalysisAgent()
        self.writing_agent = WritingAgent()

    async def execute_research(self, question, effort_level):
        # Custom orchestration logic
        research_results = await self.research_agent.research(question)
        analysis = await self.analysis_agent.analyze(research_results)
        report = await self.writing_agent.write(analysis)
        return report

# AFTER (Using DeepAgents)
from deepagents import create_deep_agent

research_subagent = {
    "name": "research-agent",
    "description": "Conducts thorough research on topics",
    "system_prompt": research_prompt,
    "tools": [internet_search, vector_search, knowledge_graph_query]
}

analysis_subagent = {
    "name": "analysis-agent",
    "description": "Analyzes research findings for insights",
    "system_prompt": analysis_prompt,
    "tools": []  # Read-only, uses filesystem
}

writing_subagent = {
    "name": "writing-agent",
    "description": "Generates polished research reports",
    "system_prompt": writing_prompt,
    "tools": ["read_file", "write_file"]
}

agent = create_deep_agent(
    tools=[internet_search, vector_search, knowledge_graph_query],
    system_prompt=coordinator_prompt,
    subagents=[research_subagent, analysis_subagent, writing_subagent],
    middleware=[
        EffortLevelMiddleware(effort_level),
        SearchTrackingMiddleware(),
        LoopDetectionMiddleware()
    ],
    interrupt_on={
        "internet_search": {"allowed_decisions": ["approve", "edit", "reject"]}
    }
)

# Execute (same interface)
result = await agent.ainvoke({
    "messages": [{"role": "user", "content": question}]
})
```

### 10.3 Compatibility Assessment

**High Compatibility Areas:**
- ✅ WebSocket streaming (LangGraph native)
- ✅ State persistence (PostgreSQL checkpointer)
- ✅ HITL approval (direct mapping)
- ✅ Tool integration (same interface)
- ✅ LangSmith observability (automatic)

**Medium Compatibility Areas:**
- ⚠️ Effort level configuration (needs new middleware)
- ⚠️ Progress tracking (needs event extraction)
- ⚠️ Custom UI (needs adapter layer)

**Low Compatibility Areas:**
- ❌ Knowledge graph (completely new integration)
- ❌ Quality metrics (new evaluation system)

### 10.4 Risk Assessment

**Low Risk:**
- Core research workflow (well-proven pattern)
- Multi-agent orchestration (battle-tested)
- State management (LangGraph stable)
- Streaming (production-ready)

**Medium Risk:**
- Effort level enforcement (new concept, needs testing)
- Search limit tracking (edge cases in parallel execution)
- Loop detection (false positives possible)

**High Risk:**
- Knowledge graph at scale (performance unknown)
- Quality metrics accuracy (subjective evaluations)
- Cost optimization (token usage can grow quickly)

### 10.5 Recommended Approach

**✅ ADOPT DeepAgents Framework:**

**Reasons:**
1. **70-75% pre-built** - Significant time savings
2. **Production-tested** - Ranks #6 on Deep Research Bench
3. **Well-maintained** - Active LangChain development
4. **Extensible** - Middleware system for customization
5. **Compatible** - Fits existing architecture
6. **Observable** - LangSmith integration built-in
7. **Documented** - Good examples and patterns

**Implementation Plan:**
1. Start with research_agent.py example
2. Add analysis and writing subagents
3. Implement effort level middleware
4. Integrate knowledge graph tools
5. Add vector RAG tools
6. Build custom UI integration
7. Optimize and scale

**Timeline Estimate:**
- **Minimal Viable Product**: 2-3 weeks
- **Full Feature Parity**: 4-5 weeks
- **Production-Ready**: 6-8 weeks (including testing and optimization)

---

## 11. Code Examples and Patterns

### 11.1 Complete Research System Example

```python
"""
Complete Deep Research System using DeepAgents
Includes: Research, Analysis, Writing, Critique, Knowledge Graph, Vector RAG
"""

import os
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent
from neo4j import GraphDatabase
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# =====================
# TOOL DEFINITIONS
# =====================

# Search tool
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search using Tavily."""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

# Knowledge graph tools
neo4j_driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"])
)

def kg_add_entity(entity_type: str, entity_name: str, properties: dict = None):
    """Add an entity to the knowledge graph."""
    with neo4j_driver.session() as session:
        query = f"""
        MERGE (e:{entity_type} {{name: $name}})
        SET e += $properties
        RETURN e
        """
        session.run(query, name=entity_name, properties=properties or {})
    return f"Added {entity_type}: {entity_name}"

def kg_add_relationship(entity1: str, relationship: str, entity2: str):
    """Create a relationship between two entities."""
    with neo4j_driver.session() as session:
        query = f"""
        MATCH (a {{name: $entity1}})
        MATCH (b {{name: $entity2}})
        MERGE (a)-[r:{relationship}]->(b)
        RETURN r
        """
        session.run(query, entity1=entity1, entity2=entity2)
    return f"Created: {entity1} -{relationship}-> {entity2}"

def kg_query(cypher_query: str):
    """Query the knowledge graph."""
    with neo4j_driver.session() as session:
        result = session.run(cypher_query)
        records = [dict(record) for record in result]
    return json.dumps(records, indent=2)

# Vector search tools
vectorstore = Chroma(
    collection_name="research_docs",
    embedding_function=OpenAIEmbeddings()
)

def vector_search(query: str, top_k: int = 5):
    """Search vector database for relevant documents."""
    results = vectorstore.similarity_search_with_score(query, k=top_k)
    formatted = [
        {
            "content": doc.page_content,
            "source": doc.metadata.get("source"),
            "score": float(score)
        }
        for doc, score in results
    ]
    return json.dumps(formatted, indent=2)

def vector_add(content: str, metadata: dict):
    """Add document to vector database."""
    vectorstore.add_texts([content], metadatas=[metadata])
    return f"Added to vector store: {metadata.get('title')}"

# =====================
# SUBAGENT DEFINITIONS
# =====================

research_subagent = {
    "name": "research-agent",
    "description": """Conducts in-depth research on specific topics.

    Capabilities:
    - Web search using Tavily
    - Vector similarity search for existing knowledge
    - Knowledge graph queries for entity relationships

    Use for: Gathering information, finding sources, exploring topics

    IMPORTANT: Give this agent ONE focused topic at a time.
    For complex queries, break into subtopics and call in parallel.
    """,
    "system_prompt": """You are a thorough research specialist.

Your process:
1. Check vector store for existing research on this topic
2. Query knowledge graph for related entities and relationships
3. Conduct web searches to fill gaps
4. Extract key entities and add to knowledge graph
5. Add valuable findings to vector store for future use
6. Return comprehensive research summary

Research Guidelines:
- Prioritize authoritative sources
- Note confidence level of findings
- Track all sources with URLs
- Identify contradictions or uncertainties
- Extract structured data (entities, relationships, facts)

Output Format:
# Research Summary: [Topic]

## Key Findings
- Finding 1 [Source 1]
- Finding 2 [Source 2]

## Entities Identified
- Entity 1 (Type: Organization)
- Entity 2 (Type: Person)

## Relationships Discovered
- Entity A -> Relationship -> Entity B

## Sources
1. [Title](URL)
2. [Title](URL)

## Confidence Assessment
- High confidence: [Claims]
- Medium confidence: [Claims]
- Low confidence / Needs validation: [Claims]

Your final message should be a detailed, well-sourced answer.
Only your FINAL message will be passed to the coordinator.
""",
    "tools": [
        internet_search,
        vector_search,
        vector_add,
        kg_query,
        kg_add_entity,
        kg_add_relationship
    ]
}

analysis_subagent = {
    "name": "analysis-agent",
    "description": """Analyzes research findings to extract insights, patterns, and trends.

    Use for: Synthesizing information, identifying themes, extracting actionable insights
    """,
    "system_prompt": """You are a senior research analyst.

Your tasks:
1. Read research findings from virtual filesystem
2. Identify common themes and patterns
3. Cross-reference sources for validation
4. Assess evidence strength
5. Extract actionable insights
6. Identify gaps and contradictions

Analysis Framework:
- What are the key themes?
- What patterns emerge across sources?
- Where do sources agree/disagree?
- What's well-supported vs. speculative?
- What questions remain unanswered?

Output Format:
# Analysis: [Topic]

## Executive Summary
[3-4 paragraph overview of key insights]

## Thematic Analysis

### Theme 1: [Name]
**Pattern**: [Description]
**Evidence**: [Citations]
**Confidence**: High/Medium/Low
**Insights**: [Actionable takeaways]

### Theme 2: [Name]
[Same structure]

## Cross-Source Validation
- **Consistent findings**: [What multiple sources agree on]
- **Contradictions**: [Where sources disagree]
- **Gaps**: [What's missing or unclear]

## Evidence Quality Assessment
- **Strong evidence**: [Well-supported claims]
- **Moderate evidence**: [Partially supported]
- **Weak evidence**: [Requires validation]

## Actionable Insights
1. [Insight 1]
2. [Insight 2]

## Recommendations for Further Research
- [Gap 1 to investigate]
- [Gap 2 to investigate]

Write analysis to `analysis_report.md` when complete.
""",
    "tools": []  # Analysis primarily reads from filesystem
}

writing_subagent = {
    "name": "writing-agent",
    "description": """Generates polished, publication-quality research reports.

    Use for: Creating final reports, structuring content, professional writing
    """,
    "system_prompt": """You are a professional technical writer and research communicator.

Your responsibilities:
1. Read research findings and analysis from virtual filesystem
2. Structure content logically and coherently
3. Write in clear, accessible language
4. Maintain professional tone
5. Ensure proper citations throughout
6. Create executive summaries

Report Structure Template:
# [Report Title]

## Executive Summary
[2-3 paragraphs: key findings, main insights, conclusions]

## Introduction
- Context and background
- Research objectives
- Methodology overview

## Findings

### [Major Topic 1]
[Comprehensive exploration with evidence and citations]
[Use paragraphs, not bullet points as default]
[Bullet points only for lists or short items]

### [Major Topic 2]
[Same structure]

## Analysis and Insights
[Synthesis of findings]
[Patterns and trends]
[Implications]

## Conclusions
[Key takeaways]
[Answered questions]
[Remaining uncertainties]

## Recommendations
[Actionable next steps]
[Strategic implications]

## Sources
[Numbered list of all citations]
1. [Source Title](URL)
2. [Source Title](URL)

Writing Guidelines:
- Use ## for main sections, ### for subsections
- Write comprehensive paragraphs (aim for 150-300 words per section)
- Use **bold** for key terms, *italics* for emphasis
- Cite sources as [1], [2] inline
- Number sources sequentially without gaps
- Maintain consistent voice (third person, professional)
- Never refer to yourself as the writer
- No meta-commentary ("In this section, I will...")

Quality Standards:
- Clarity: Avoid jargon, explain complex terms
- Comprehensiveness: Cover topics thoroughly
- Coherence: Logical flow between sections
- Accuracy: Claims must align with cited sources
- Professionalism: Publication-ready quality

Write final report to `final_report.md`
""",
    "tools": []  # Writing reads from filesystem
}

critique_subagent = {
    "name": "critique-agent",
    "description": """Reviews reports for quality, completeness, and accuracy.

    Use for: Quality assurance, identifying improvements, validation
    """,
    "system_prompt": """You are an expert editor and quality assurance specialist.

Review Process:
1. Read the report from `final_report.md`
2. Read the research question from `question.txt`
3. Read research findings from `research_notes.md` (if available)
4. Evaluate against quality criteria
5. Provide specific, actionable feedback

Quality Criteria:

1. **Completeness** (0-10 score)
   - Does it fully answer the research question?
   - Are all major topics covered?
   - Are sections sufficiently detailed?

2. **Structure** (0-10 score)
   - Is the organization logical?
   - Do sections flow coherently?
   - Are headings clear and appropriate?

3. **Writing Quality** (0-10 score)
   - Is it clear and readable?
   - Is the tone professional?
   - Are there grammatical errors?

4. **Citation Quality** (0-10 score)
   - Are claims properly cited?
   - Are sources authoritative?
   - Are citations formatted correctly?

5. **Accuracy** (0-10 score)
   - Do claims align with sources?
   - Are there unsupported assertions?
   - Are there factual errors?

6. **Depth** (0-10 score)
   - Is the analysis thorough?
   - Are insights meaningful?
   - Is it just surface-level or truly deep?

Feedback Format:
# Critique: [Report Title]

## Overall Assessment
**Overall Score**: [Average of all criteria]/10
**Recommendation**: [Publish as-is / Minor revisions / Major revisions / Rewrite]

## Detailed Evaluation

### Completeness: [Score]/10
**Strengths**: [What's done well]
**Issues**: [What's missing or incomplete]
**Suggestions**: [Specific improvements]

### Structure: [Score]/10
[Same format]

### Writing Quality: [Score]/10
[Same format]

### Citation Quality: [Score]/10
[Same format]

### Accuracy: [Score]/10
[Same format]

### Depth: [Score]/10
[Same format]

## Priority Improvements
1. [Highest priority fix with specific location]
2. [Second priority fix]
3. [Third priority fix]

## Minor Suggestions
- [Quick improvement 1]
- [Quick improvement 2]

## Exemplary Elements
[What the report does particularly well]

If major revisions needed, you may suggest:
- Additional research topics
- Sections to expand
- Specific sources to find

Write critique to `critique_report.md`
""",
    "tools": [internet_search]  # Can verify claims
}

# =====================
# MAIN COORDINATOR
# =====================

coordinator_instructions = """You are a research project coordinator managing a team of specialized agents.

Your team:
- **research-agent**: Gathers information, builds knowledge graph, searches web and vector store
- **analysis-agent**: Synthesizes findings, identifies patterns and insights
- **writing-agent**: Generates polished reports
- **critique-agent**: Reviews quality and suggests improvements

Workflow:

1. **Initial Planning**
   - Write the research question to `question.txt`
   - Create a research plan using write_todos
   - Break complex topics into focused subtopics

2. **Research Phase**
   - For each subtopic, call research-agent (can call multiple in parallel)
   - Consolidate findings into `research_notes.md`
   - Track key entities in knowledge graph

3. **Analysis Phase**
   - Call analysis-agent to synthesize research
   - Review `analysis_report.md` for insights

4. **Writing Phase**
   - Call writing-agent to create report
   - Review `final_report.md`

5. **Quality Assurance**
   - Call critique-agent for evaluation
   - Review `critique_report.md`
   - If score < 8/10, iterate:
     a. Identify gaps from critique
     b. Call research-agent for additional info
     c. Call writing-agent to revise
     d. Re-evaluate
   - If score >= 8/10, finalize

6. **Finalization**
   - Ensure all sources cited
   - Verify formatting
   - Mark as complete

File Organization:
- `question.txt` - Original research question
- `research_notes.md` - Consolidated research findings
- `analysis_report.md` - Analytical insights
- `final_report.md` - Final polished report
- `critique_report.md` - Quality assessment

Best Practices:
- Parallel research: Call multiple research-agents for different subtopics simultaneously
- Iterative refinement: Don't settle for mediocre quality, iterate until excellent
- Knowledge building: Use vector store and knowledge graph to accumulate expertise
- Source tracking: Maintain rigorous citation discipline
- Progress tracking: Update todos as work progresses

You have access to all tools directly, but delegate specialized work to subagents.
Use internet_search only for quick lookups.
For thorough research, delegate to research-agent.
"""

# =====================
# CUSTOM MIDDLEWARE
# =====================

from deepagents.middleware import AgentMiddleware

class EffortLevelMiddleware(AgentMiddleware):
    """Enforces effort level constraints on research depth."""

    EFFORT_CONFIGS = {
        "quick": {
            "max_searches": 3,
            "max_iterations": 1,
            "max_concurrent_researchers": 1,
            "critique_enabled": False,
            "description": "Quick overview"
        },
        "balanced": {
            "max_searches": 8,
            "max_iterations": 2,
            "max_concurrent_researchers": 2,
            "critique_enabled": False,
            "description": "Standard research"
        },
        "thorough": {
            "max_searches": 15,
            "max_iterations": 3,
            "max_concurrent_researchers": 3,
            "critique_enabled": True,
            "description": "Comprehensive analysis"
        },
        "deep": {
            "max_searches": 30,
            "max_iterations": 4,
            "max_concurrent_researchers": 4,
            "critique_enabled": True,
            "description": "Exhaustive investigation"
        }
    }

    def __init__(self, effort_level: str):
        self.config = self.EFFORT_CONFIGS[effort_level]

    @property
    def state_schema(self):
        return {
            "effort_config": dict,
            "search_count": int,
            "iteration_count": int
        }

    def modify_model_request(self, state, request):
        search_count = state.get("search_count", 0)
        remaining = self.config["max_searches"] - search_count

        request["prompt"] += f"""

EFFORT LEVEL: {self.config['description']}
- Searches remaining: {remaining}/{self.config['max_searches']}
- Max research iterations: {self.config['max_iterations']}
- Parallel researchers allowed: {self.config['max_concurrent_researchers']}
- Quality critique: {'Enabled' if self.config['critique_enabled'] else 'Disabled'}

Adjust your research strategy to fit these constraints.
"""
        return request

class SearchTrackingMiddleware(AgentMiddleware):
    """Tracks search tool usage."""

    @property
    def state_schema(self):
        return {
            "search_count": int,
            "search_history": list
        }

    def before_tool_execution(self, state, tool_name, tool_input):
        if tool_name == "internet_search":
            state["search_count"] = state.get("search_count", 0) + 1
            state["search_history"] = state.get("search_history", [])
            state["search_history"].append({
                "query": tool_input.get("query"),
                "timestamp": datetime.now().isoformat()
            })
        return state

# =====================
# AGENT CREATION
# =====================

def create_research_system(effort_level: str = "thorough"):
    """Create a complete deep research system."""

    agent = create_deep_agent(
        tools=[
            internet_search,
            vector_search,
            vector_add,
            kg_query,
            kg_add_entity,
            kg_add_relationship
        ],
        system_prompt=coordinator_instructions,
        subagents=[
            research_subagent,
            analysis_subagent,
            writing_subagent,
            critique_subagent
        ],
        middleware=[
            EffortLevelMiddleware(effort_level),
            SearchTrackingMiddleware()
        ],
        interrupt_on={
            "internet_search": {
                "allowed_decisions": ["approve", "edit", "reject"]
            }
        }
    )

    return agent

# =====================
# USAGE
# =====================

async def run_research(question: str, effort_level: str = "thorough"):
    """Execute a research task."""

    agent = create_research_system(effort_level)

    # Stream execution
    async for event in agent.astream(
        {"messages": [{"role": "user", "content": question}]},
        stream_mode="values"
    ):
        # Extract progress
        if "todos" in event:
            current = [t for t in event["todos"] if t["status"] == "in_progress"]
            if current:
                print(f"Current step: {current[0]['content']}")

        # Extract messages
        if "messages" in event:
            last_msg = event["messages"][-1]
            if hasattr(last_msg, "content"):
                print(f"Message: {last_msg.content[:100]}...")

        # Check for completion
        if event.get("final_report"):
            print("Research complete!")
            return event["final_report"]

# Example usage
if __name__ == "__main__":
    import asyncio

    question = "What are the major trends in quantum computing as of 2025?"

    result = asyncio.run(run_research(question, effort_level="thorough"))
    print(result)
```

### 11.2 Effort Level Configuration Examples

```python
"""
Effort Level System for Deep Research
Maps user intent to concrete research constraints
"""

EFFORT_LEVELS = {
    "quick": {
        "name": "Quick Overview",
        "description": "Fast, high-level summary",
        "use_case": "Getting started, initial exploration",
        "constraints": {
            "max_searches": 3,
            "max_iterations": 1,
            "max_concurrent_researchers": 1,
            "max_tool_calls_per_agent": 5,
            "compression_enabled": True,
            "critique_enabled": False,
            "max_report_length": 1000,  # words
            "research_depth": "surface"
        },
        "estimated_time": "2-5 minutes",
        "estimated_cost": "$0.10-0.30"
    },

    "balanced": {
        "name": "Balanced Research",
        "description": "Standard depth, good coverage",
        "use_case": "Most research tasks, general questions",
        "constraints": {
            "max_searches": 8,
            "max_iterations": 2,
            "max_concurrent_researchers": 2,
            "max_tool_calls_per_agent": 10,
            "compression_enabled": True,
            "critique_enabled": False,
            "max_report_length": 3000,
            "research_depth": "moderate"
        },
        "estimated_time": "5-10 minutes",
        "estimated_cost": "$0.50-1.00"
    },

    "thorough": {
        "name": "Thorough Analysis",
        "description": "Comprehensive research with quality checks",
        "use_case": "Important decisions, detailed investigations",
        "constraints": {
            "max_searches": 15,
            "max_iterations": 3,
            "max_concurrent_researchers": 3,
            "max_tool_calls_per_agent": 15,
            "compression_enabled": True,
            "critique_enabled": True,
            "max_report_length": 5000,
            "research_depth": "comprehensive"
        },
        "estimated_time": "10-20 minutes",
        "estimated_cost": "$1.50-3.00"
    },

    "deep": {
        "name": "Deep Investigation",
        "description": "Exhaustive research, maximum detail",
        "use_case": "Complex topics, academic research",
        "constraints": {
            "max_searches": 30,
            "max_iterations": 4,
            "max_concurrent_researchers": 4,
            "max_tool_calls_per_agent": 20,
            "compression_enabled": False,  # Keep all detail
            "critique_enabled": True,
            "max_report_length": 10000,
            "research_depth": "exhaustive"
        },
        "estimated_time": "20-40 minutes",
        "estimated_cost": "$4.00-8.00"
    },

    "exhaustive": {
        "name": "Exhaustive Research",
        "description": "Maximum thoroughness, multiple perspectives",
        "use_case": "High-stakes research, publication-quality",
        "constraints": {
            "max_searches": 50,
            "max_iterations": 5,
            "max_concurrent_researchers": 5,
            "max_tool_calls_per_agent": 30,
            "compression_enabled": False,
            "critique_enabled": True,
            "max_report_length": 15000,
            "research_depth": "comprehensive_multi_perspective"
        },
        "estimated_time": "40-60 minutes",
        "estimated_cost": "$10.00-15.00"
    },

    "definitive": {
        "name": "Definitive Study",
        "description": "Authoritative, publication-ready research",
        "use_case": "Authoritative references, comprehensive reports",
        "constraints": {
            "max_searches": 100,
            "max_iterations": 8,
            "max_concurrent_researchers": 8,
            "max_tool_calls_per_agent": 50,
            "compression_enabled": False,
            "critique_enabled": True,
            "max_report_length": 25000,
            "research_depth": "authoritative"
        },
        "estimated_time": "60-120 minutes",
        "estimated_cost": "$20.00-40.00"
    }
}

def get_effort_prompt_addition(effort_level: str) -> str:
    """Generate prompt addition for effort level."""
    config = EFFORT_LEVELS[effort_level]

    return f"""

RESEARCH EFFORT LEVEL: {config['name']}
{config['description']}

Constraints:
- Maximum searches: {config['constraints']['max_searches']}
- Research iterations: {config['constraints']['max_iterations']}
- Parallel researchers: {config['constraints']['max_concurrent_researchers']}
- Research depth: {config['constraints']['research_depth']}
- Critique phase: {'Required' if config['constraints']['critique_enabled'] else 'Skip'}
- Target report length: ~{config['constraints']['max_report_length']} words

Expected completion: {config['estimated_time']}

Adjust your research strategy to match this effort level:
- **Quick**: Surface-level overview, key points only
- **Balanced**: Good coverage of main topics
- **Thorough**: Comprehensive with quality checks
- **Deep**: Exhaustive investigation, all angles
- **Exhaustive**: Maximum thoroughness, multiple perspectives
- **Definitive**: Authoritative, publication-ready

"""
```

### 11.3 WebSocket Integration Example

```python
"""
WebSocket integration for real-time research progress
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import AsyncIterator
import json

app = FastAPI()

async def stream_research_progress(
    agent,
    question: str,
    thread_id: str
) -> AsyncIterator[dict]:
    """Stream research progress events."""

    async for event in agent.astream(
        {"messages": [{"role": "user", "content": question}]},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="values"
    ):
        # Progress update from todos
        if "todos" in event:
            in_progress = [t for t in event["todos"] if t["status"] == "in_progress"]
            completed = [t for t in event["todos"] if t["status"] == "completed"]
            pending = [t for t in event["todos"] if t["status"] == "pending"]

            yield {
                "type": "progress",
                "current_step": in_progress[0]["content"] if in_progress else None,
                "completed_count": len(completed),
                "pending_count": len(pending),
                "total_count": len(event["todos"])
            }

        # Search count update
        if "search_count" in event:
            yield {
                "type": "search_update",
                "search_count": event["search_count"],
                "max_searches": event.get("effort_config", {}).get("max_searches", 0)
            }

        # File creation/update
        if "files" in event:
            yield {
                "type": "file_update",
                "files": list(event["files"].keys())
            }

        # Agent messages
        if "messages" in event:
            last_msg = event["messages"][-1]
            if hasattr(last_msg, "content"):
                yield {
                    "type": "message",
                    "role": last_msg.type if hasattr(last_msg, "type") else "agent",
                    "content": last_msg.content
                }

        # Completion
        if event.get("final_report"):
            yield {
                "type": "complete",
                "report": event["final_report"]
            }

@app.websocket("/research/stream/{thread_id}")
async def research_websocket(websocket: WebSocket, thread_id: str):
    """WebSocket endpoint for streaming research."""
    await websocket.accept()

    try:
        # Receive question
        data = await websocket.receive_json()
        question = data["question"]
        effort_level = data.get("effort_level", "balanced")

        # Create agent
        agent = create_research_system(effort_level)

        # Stream progress
        async for event in stream_research_progress(agent, question, thread_id):
            await websocket.send_json(event)

    except WebSocketDisconnect:
        print(f"Client disconnected: {thread_id}")
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "error": str(e)
        })
    finally:
        await websocket.close()
```

---

## 12. Best Practices and Patterns

### 12.1 Prompt Engineering Best Practices

**1. Structured Instructions:**

```python
system_prompt = """
# Role
You are [role description]

# Responsibilities
1. [Responsibility 1]
2. [Responsibility 2]

# Process
1. [Step 1]
2. [Step 2]

# Output Format
[Format description]

# Quality Standards
- [Standard 1]
- [Standard 2]
"""
```

**2. Few-Shot Examples:**

```python
system_prompt = """
When analyzing research findings:

Example Input:
Research on quantum computing market...

Expected Output:
## Key Findings
- Market growing 35% CAGR [Source 1]
- Major players: IBM, Google, Rigetti [Source 2]
...

Now analyze: {research_findings}
"""
```

**3. Explicit Constraints:**

```python
system_prompt = """
CONSTRAINTS:
- Only call research-agent for topics requiring >5 sources
- Use parallel calls for independent subtopics
- Always cite sources inline [1]
- Maximum section length: 500 words
"""
```

### 12.2 Subagent Design Patterns

**Pattern 1: Specialist Agents**

```python
# Each agent is an expert in one domain
data_collector = {...}  # Gathers raw data
data_analyzer = {...}   # Analyzes data
report_writer = {...}   # Writes reports
```

**Pattern 2: Pipeline Agents**

```python
# Sequential processing pipeline
stage_1_agent → stage_2_agent → stage_3_agent
```

**Pattern 3: Hub-and-Spoke**

```python
# Central coordinator delegates to specialists
coordinator → [specialist_1, specialist_2, specialist_3]
```

**Pattern 4: Iterative Refinement**

```python
# Loop for quality improvement
generator → critic → [if score < threshold: generator] → finalizer
```

### 12.3 State Management Patterns

**Pattern 1: Artifact-Based Communication**

```python
# Agents communicate via virtual filesystem
agent_a: write_file("data.json", results)
agent_b: read_file("data.json")
```

**Pattern 2: Structured State**

```python
# Use typed state for clarity
class ResearchState(TypedDict):
    research_phase: Literal["planning", "gathering", "analysis", "writing"]
    search_count: int
    confidence_score: float
```

**Pattern 3: Custom Reducers**

```python
# Control state updates precisely
def confidence_reducer(old, new):
    """Take minimum confidence across updates."""
    return min(old, new)
```

### 12.4 Error Handling Patterns

**Pattern 1: Graceful Degradation**

```python
system_prompt = """
If a tool fails:
1. Log the error
2. Try alternative approach
3. Continue with available data
4. Note limitation in final report
"""
```

**Pattern 2: Retry Logic**

```python
# Built into open_deep_research
def with_retry(fn, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return fn()
        except TokenLimitError:
            # Truncate input
            continue
    raise
```

**Pattern 3: Validation Checkpoints**

```python
system_prompt = """
After each major phase:
1. Validate output quality
2. Check completeness
3. If issues found, retry with corrections
"""
```

### 12.5 Cost Optimization Patterns

**Pattern 1: Model Tiering**

```python
# Use cheaper models for simple tasks
summarization_model = "gpt-4o-mini"  # Cheap
research_model = "gpt-4o"             # Capable
final_report_model = "gpt-4o"         # Quality
```

**Pattern 2: Compression**

```python
# Compress intermediate results
SummarizationMiddleware(max_tokens=120000)
```

**Pattern 3: Caching**

```python
# Cache prompt prefixes (Anthropic)
AnthropicPromptCachingMiddleware()
```

---

## 13. Production Deployment Guidance

### 13.1 LangSmith Integration

```python
"""
LangSmith observability configuration
"""

import os
from langsmith import Client

# Enable tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your-api-key"
os.environ["LANGCHAIN_PROJECT"] = "deep-research-production"

# Client for custom tracking
langsmith_client = Client()

# Custom run tracking
from langsmith import traceable

@traceable(run_type="chain", name="Research Workflow")
async def execute_research(question: str, effort_level: str):
    """Traced research execution."""
    agent = create_research_system(effort_level)
    result = await agent.ainvoke({"messages": [{"role": "user", "content": question}]})
    return result
```

### 13.2 Deployment Options

**Option 1: LangGraph Platform (Recommended)**

```bash
# Deploy to LangGraph Cloud
langgraph deploy \
  --name deep-research-agent \
  --server https://api.langchain.com \
  --config ./langgraph.json
```

**Option 2: Self-Hosted with Docker**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Option 3: Kubernetes**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deep-research-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: deep-research
  template:
    metadata:
      labels:
        app: deep-research
    spec:
      containers:
      - name: agent
        image: your-registry/deep-research:latest
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: openai
```

### 13.3 Monitoring and Alerting

```python
"""
Monitoring configuration
"""

from prometheus_client import Counter, Histogram, Gauge

# Metrics
research_requests = Counter("research_requests_total", "Total research requests")
research_duration = Histogram("research_duration_seconds", "Research duration")
search_count = Histogram("search_count", "Searches per request")
error_count = Counter("research_errors_total", "Total errors")
concurrent_researches = Gauge("concurrent_researches", "Ongoing research tasks")

# Middleware for tracking
class MetricsMiddleware(AgentMiddleware):
    def before_model_call(self, state):
        research_requests.inc()
        concurrent_researches.inc()

    def after_model_call(self, state):
        concurrent_researches.dec()
        if state.get("search_count"):
            search_count.observe(state["search_count"])

    def on_error(self, error):
        error_count.inc()
```

### 13.4 Security Best Practices

```python
"""
Security configuration
"""

# 1. API key management
from google.cloud import secretmanager

def get_secret(secret_id: str) -> str:
    """Fetch secrets from cloud provider."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/PROJECT_ID/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# 2. Input validation
from pydantic import BaseModel, Field

class ResearchRequest(BaseModel):
    question: str = Field(..., max_length=1000, min_length=10)
    effort_level: Literal["quick", "balanced", "thorough", "deep", "exhaustive", "definitive"]

# 3. Rate limiting
from slowapi import Limiter

limiter = Limiter(key_func=lambda: get_user_id())

@app.post("/research")
@limiter.limit("10/minute")
async def research(request: ResearchRequest):
    ...

# 4. Output sanitization
def sanitize_output(text: str) -> str:
    """Remove sensitive patterns from output."""
    # Remove API keys
    text = re.sub(r"sk-[a-zA-Z0-9]{48}", "[REDACTED]", text)
    # Remove email addresses
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]", text)
    return text
```

---

## 14. Conclusion and Next Steps

### 14.1 Summary of Findings

**DeepAgents provides 70-75% of required functionality pre-built:**

✅ **Excellent Pre-Built Support:**
- Multi-agent orchestration
- Research workflows
- Context management
- HITL approval
- State persistence
- Streaming
- Observability

⚠️ **Good Framework Support (Easy to Build):**
- Analysis agents
- Writing agents
- Search tracking
- Loop detection
- Vector RAG

❌ **Requires Custom Development:**
- Effort level system
- Knowledge graph integration
- Quality metrics
- Advanced citation management

### 14.2 Recommended Implementation Path

**Phase 1: Foundation (Week 1)**
- ✅ Adopt DeepAgents framework
- ✅ Implement basic research workflow
- ✅ Integrate with existing infrastructure

**Phase 2: Specialization (Week 2)**
- ✅ Add analysis subagent
- ✅ Add writing subagent
- ✅ Configure multi-agent orchestration

**Phase 3: Custom Features (Week 3)**
- ✅ Implement effort level system
- ✅ Add search tracking
- ✅ Enhance loop detection

**Phase 4: Advanced Integration (Week 4)**
- ✅ Integrate knowledge graph
- ✅ Add vector RAG
- ✅ Implement quality metrics

**Phase 5: Production (Week 5)**
- ✅ Optimize performance
- ✅ Load testing
- ✅ Documentation
- ✅ Deployment

### 14.3 Key Takeaways

1. **DeepAgents is production-ready** - Use it as the foundation
2. **70-75% pre-built** - Significant time savings
3. **Highly extensible** - Middleware system enables customization
4. **Compatible with our architecture** - Fits existing infrastructure
5. **Well-maintained** - Active LangChain development
6. **Observable** - LangSmith integration included
7. **Cost-effective** - Model tiering and caching built-in

### 14.4 Success Criteria

**Week 1 Goal:**
- Basic research workflow operational
- Single research task end-to-end
- WebSocket streaming working

**Week 3 Goal:**
- All 6 effort levels implemented
- Multi-agent orchestration working
- HITL approval integrated

**Week 5 Goal:**
- Full feature parity with requirements
- Production deployment
- Monitoring and observability
- Documentation complete

### 14.5 Risk Mitigation

**Technical Risks:**
- Effort level edge cases → Extensive testing
- Search limit enforcement → Middleware validation
- Cost control → Budget alerts and monitoring

**Integration Risks:**
- Knowledge graph performance → Caching and indexing
- Vector store scaling → Choose Chroma vs Pinecone based on load
- HITL UI complexity → Reuse existing approval components

**Operational Risks:**
- Cost overruns → Implement per-user budgets
- Quality variance → Critique agent enforcement
- Latency issues → Async execution and caching

### 14.6 Final Recommendation

**✅ ADOPT DeepAgents Framework Immediately**

The framework provides excellent pre-built functionality, is production-tested (ranks #6 on Deep Research Bench), and significantly reduces development time. The 25-30% custom development needed is straightforward and well-supported by the middleware system.

**Expected Timeline:**
- MVP: 2-3 weeks
- Full feature parity: 4-5 weeks
- Production-ready: 6-8 weeks

**Expected Outcome:**
A sophisticated, scalable deep research system with minimal custom development effort, leveraging battle-tested patterns and production-grade infrastructure.

---

## Appendix A: Complete API Reference

### A.1 Core Functions

```python
from deepagents import create_deep_agent, async_create_deep_agent

agent = create_deep_agent(
    tools: list[Callable] = [],
    system_prompt: str = BASE_AGENT_PROMPT,
    subagents: list[SubAgent | CompiledSubAgent] = [],
    model: BaseChatModel | str = "claude-sonnet-4-5-20250929",
    middleware: list[AgentMiddleware] = DEFAULT_MIDDLEWARE,
    interrupt_on: dict[str, dict] = {},
    checkpointer: BaseCheckpointSaver = None
) -> CompiledStateGraph
```

### A.2 State Schema

```python
class DeepAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    todos: list[Todo]  # {content: str, status: str}
    files: Annotated[dict[str, str], file_reducer]
```

### A.3 Built-in Tools

```python
# Planning
write_todos(todos: list[Todo]) -> Command

# Filesystem
ls() -> list[str]
read_file(path: str) -> str
write_file(path: str, content: str) -> Command
edit_file(path: str, old_string: str, new_string: str) -> Command

# Delegation
task(description: str, subagent_type: str) -> str
```

### A.4 Middleware API

```python
class AgentMiddleware:
    @property
    def state_schema(self) -> dict:
        """Additional state fields."""

    def modify_model_request(self, state: dict, request: dict) -> dict:
        """Modify prompt/config before LLM call."""

    def before_tool_execution(self, state: dict, tool_name: str, tool_input: dict) -> dict:
        """Hook before tool runs."""

    def after_tool_execution(self, state: dict, tool_name: str, tool_output: any) -> dict:
        """Hook after tool completes."""
```

---

## Appendix B: Resources and Links

### B.1 Official Documentation

- **DeepAgents GitHub**: https://github.com/langchain-ai/deepagents
- **DeepAgents Docs**: https://docs.langchain.com/oss/python/deepagents/overview
- **Open Deep Research**: https://github.com/langchain-ai/open_deep_research
- **LangChain Blog**: https://blog.langchain.com/deep-agents/
- **LangSmith**: https://www.langchain.com/langsmith

### B.2 Key Examples

- **Research Agent**: https://github.com/langchain-ai/deepagents/blob/master/examples/research/research_agent.py
- **Deep Researcher**: https://github.com/langchain-ai/open_deep_research/blob/main/src/open_deep_research/deep_researcher.py

### B.3 Community Resources

- **DeepWiki Documentation**: https://deepwiki.com/langchain-ai/deepagents
- **DataCamp Tutorial**: https://www.datacamp.com/tutorial/deep-agents
- **Medium Articles**: Search "LangChain DeepAgents 2025"

---

**End of Analysis**

This comprehensive research provides everything needed to make an informed decision about adopting the DeepAgents framework. The recommendation is clear: **adopt immediately** for 70-75% pre-built functionality with straightforward paths to implement the remaining custom features.
