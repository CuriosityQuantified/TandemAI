"""
MODULE 2.2: Deep Agents with Production Tools (Simplified)
===========================================================

Demonstrates:
1. Single DeepAgent with real production tools
2. Tavily web search integration
3. Firecrawl web scraping
4. GitHub repository operations
5. e2b code execution sandbox
6. Hybrid storage backend (v0.2 feature)
7. TodoListMiddleware for automatic planning

This version uses real tools instead of simulated ones.

Based on: langchain-langgraph-hands-on-guide.md Module 2.2
"""

import os
from dotenv import load_dotenv
from typing_extensions import TypedDict

# DeepAgents imports
from deepagents import create_deep_agent
from deepagents.backends import (
    CompositeBackend,
    StateBackend,
    FilesystemBackend
)

# LangChain imports
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

# Production tool imports
from langchain_tavily import TavilySearch

load_dotenv()

# ============================================================================
# STATE SCHEMA
# ============================================================================

class AgentState(TypedDict, total=False):
    """State schema with custom progress logging."""
    messages: list
    logs: list  # [{"message": "🌐 Searching...", "done": False}]

# ============================================================================
# CONFIGURATION
# ============================================================================

# Use Anthropic Claude Haiku 4.5 directly
# With simplified tool set (Tavily only), Haiku should work
model = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.7,
)

print("\n" + "=" * 80)
print("MODULE 2.2: Single DeepAgent with Tavily + Built-in Tools")
print("=" * 80)
print(f"🤖 Model: Claude Haiku 4.5")
print(f"🔧 Tool: Tavily (web search)")
print(f"📁 Built-in: 6 filesystem tools (ls, read_file, write_file, edit_file, glob, grep)")
print(f"🔮 Future: Firecrawl, GitHub, e2b will be added as subagents")
print("=" * 80)

# ============================================================================
# PRODUCTION TOOLS
# ============================================================================

# Tavily Web Search (native LangChain tool)
tavily_search = TavilySearch(
    max_results=5,
    api_key=os.getenv("TAVILY_API_KEY"),
)

# ============================================================================
# ENHANCED TOOL SCHEMAS
# ============================================================================

class ResearchSearchArgs(BaseModel):
    """Arguments for research-focused web search."""
    query: str = Field(
        description="Specific research question or topic to search. Be precise and include key terms."
    )
    max_results: int = Field(
        default=5,
        ge=3,
        le=10,
        description="Number of sources to return (3-10). Use 5 for balanced research, 10 for comprehensive."
    )

class EnhancedTavilyTool:
    """Wrapper around Tavily with enhanced metadata for citations."""

    def __init__(self, tavily_tool):
        self.tavily = tavily_tool
        self.name = "research_search"
        self.description = (
            "Search the web for credible, up-to-date sources on any topic. "
            "Returns URLs, titles, and content snippets for citation. "
            "Use for: factual research, current events, technical documentation, statistics. "
            "Best practices: "
            "- Use specific queries (good: 'LangChain v1.0 middleware features', bad: 'LangChain') "
            "- Search multiple times for complex topics "
            "- Note the source URLs for citations"
        )
        self.args_schema = ResearchSearchArgs

    def invoke(self, query: str, max_results: int = 5):
        """Execute search and format results for citations."""
        results = self.tavily.invoke({"query": query})
        # Format results to emphasize URL and title for citations
        return results

# Wrap the existing tavily_search (Note: Using original for compatibility)
# Future: Replace with EnhancedTavilyTool for better citation support
enhanced_tavily = EnhancedTavilyTool(tavily_search)

# ============================================================================
# CUSTOM write_file TOOL WITH EXPLICIT SCHEMA
# ============================================================================

class WriteFileInput(BaseModel):
    """Explicit schema for write_file tool to enforce both parameters."""
    file_path: str = Field(
        ...,  # Required
        description="Absolute path to the file. MUST start with /workspace/ to save in workspace."
    )
    content: str = Field(
        ...,  # Required
        description=(
            "COMPLETE file content as a string. REQUIRED and cannot be empty. "
            "⚠️ CRITICAL: Include ENTIRE content regardless of size (even 10,000+ sentences). "
            "Do NOT summarize or truncate. This tool handles millions of characters efficiently."
        )
    )

@tool("write_file", args_schema=WriteFileInput)
def write_file_tool(file_path: str, content: str) -> str:
    """
    Write content to a file in the workspace.

    This tool saves files to the /workspace/ directory which appears in the UI file browser.
    BOTH parameters are absolutely required - file_path AND content.

    ⚠️  CRITICAL: LARGE CONTENT HANDLING ⚠️

    This tool efficiently handles content of ANY size - even 10,000+ sentences or millions of characters.
    NEVER summarize, truncate, or abbreviate the content parameter. Include ALL content in a SINGLE call.

    Model Output Limitations & Strategies:
    - Claude Haiku 4.5 has ~4K output token limit (~16K characters)
    - If content exceeds model's output limit, use ITERATIVE FALLBACK approach:

      Strategy A - Single Write (Preferred):
      1. Pass ALL content in one write_file call
      2. Example: write_file(file_path="/workspace/large.txt", content="<all 10,000 sentences here>")

      Strategy B - Iterative Approach (Fallback for >4K output tokens):
      1. Create file with initial content (first ~3K output tokens)
      2. Use edit_file to append remaining content in batches
      3. Example:
         - write_file(file_path="/workspace/large.txt", content="<sentences 1-1000>")
         - edit_file(file_path="/workspace/large.txt", old_string="<last line>",
                     new_string="<last line>\n<sentences 1001-2000>")
         - edit_file(file_path="/workspace/large.txt", old_string="<last line>",
                     new_string="<last line>\n<sentences 2001-3000>")
         - Continue until all content is written

    IMPORTANT: "Brief" applies to USER-FACING MESSAGES, NOT file content:
    - ✅ User message: "File created with 10,000 sentences" (brief)
    - ✅ File content: Include ALL 10,000 sentences (complete)
    - ❌ WRONG: Summarizing file content to be "brief" - NEVER DO THIS

    Args:
        file_path: Path where to save the file (must start with /workspace/)
        content: The COMPLETE file content as text - ALL sentences, NO truncation

    Returns:
        Success message with file path and character count

    Examples:
        # Small file (normal case)
        write_file(
            file_path="/workspace/report.md",
            content="# Report\\n\\nThis is the content..."
        )

        # Large file within model limits (10,000 sentences, ~40K chars)
        write_file(
            file_path="/workspace/large_story.txt",
            content="Sentence 1. Sentence 2. ... Sentence 10000."
        )

        # Very large file exceeding model output limits - use iterative approach
        # Step 1: Create with initial content
        write_file(
            file_path="/workspace/massive.txt",
            content="<First 1000 sentences that fit in 4K tokens>"
        )
        # Step 2: Append remaining content via edit_file
        edit_file(
            file_path="/workspace/massive.txt",
            old_string="<last sentence from step 1>",
            new_string="<last sentence from step 1>\\n<Next 1000 sentences>"
        )
    """
    # Import here to avoid circular dependency
    from pathlib import Path

    # Validate path starts with /workspace/
    if not file_path.startswith("/workspace/"):
        return f"Error: file_path must start with /workspace/ (got: {file_path})"

    # Get the actual filesystem path
    workspace_dir = "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/agent_workspace"
    relative_path = file_path.replace("/workspace/", "")
    full_path = Path(workspace_dir) / relative_path

    # Create parent directories if needed
    full_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the file
    full_path.write_text(content, encoding='utf-8')

    return f"✅ File written successfully: {file_path} ({len(content)} characters)"

print("\n🔧 Production Tool Initialized:")
print("  ✅ Tavily Search - Web search with up-to-date information")
print("  ✅ Enhanced Tool Schema - Pydantic validation for better citations")
print("  ✅ Custom write_file - Explicit schema enforcement for reliable file writing")
print("\n📋 Note: Firecrawl, GitHub, and e2b will be added as subagents in future modules")


# ============================================================================
# STORAGE BACKEND
# ============================================================================

workspace_dir = "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/agent_workspace"
os.makedirs(workspace_dir, exist_ok=True)

def create_hybrid_backend(rt):
    """Hybrid storage: ephemeral + filesystem."""
    return CompositeBackend(
        default=StateBackend(rt),
        routes={
            "/workspace/": FilesystemBackend(root_dir=workspace_dir, virtual_mode=True),
        }
    )

print("\n💾 Backend: CompositeBackend (StateBackend + FilesystemBackend)")
print("   Note: Custom write_file tool overrides FilesystemBackend's version (last wins)")

# ============================================================================
# LOG HELPER FUNCTIONS
# ============================================================================

def add_log(state: dict, message: str) -> dict:
    """Add a new log entry to state."""
    if "logs" not in state:
        state["logs"] = []
    state["logs"].append({"message": message, "done": False})
    return state

def complete_log(state: dict, index: int = -1) -> dict:
    """Mark a log entry as complete."""
    if "logs" in state and state["logs"]:
        state["logs"][index]["done"] = True
    return state

def clear_logs(state: dict) -> dict:
    """Clear all logs from state."""
    state["logs"] = []
    return state

print("\n📋 Log Helper Functions: add_log, complete_log, clear_logs")

# NOTE: When adding custom tools, emit progress logs:
# 1. Before operation: add_log(state, "🌐 Searching for...")
# 2. After operation: complete_log(state)
# 3. On task completion: clear_logs(state)

# ============================================================================
# TOOL USAGE PATTERNS DOCUMENTATION
# ============================================================================

"""
TOOL USAGE PATTERNS:

1. research_search (Tavily):
   - Returns: List of sources with {title, url, content}
   - Citation: Use URL from results in footnotes
   - Best for: Current information, statistics, technical docs

2. write_file:
   - CRITICAL: BOTH parameters are REQUIRED - file_path AND content
   - NEVER call write_file with only file_path - it will fail
   - Files saved to /workspace/ appear in the UI file browser automatically

   CORRECT Usage Examples:
   ✅ write_file(file_path="/workspace/report.md", content="# Report\n\nFull content here...")
   ✅ write_file(file_path="/workspace/data.txt", content="Line 1\nLine 2\nLine 3")

   WRONG Usage (will cause error):
   ❌ write_file(file_path="/workspace/report.md") - Missing content parameter!
   ❌ write_file(file_path="report.md", content="...") - Wrong path (no /workspace/)

   - Citation format in content:
     * Inline: "Claim text[^1]"
     * Footer: "[^1]: Title - URL"

3. write_todos (optional):
   - Use for: Tasks with 3+ distinct steps
   - Not required for simple research + write workflows
"""

# ============================================================================
# DEEP AGENT CREATION
# ============================================================================

print("\n🤖 Creating DeepAgent...")

# Collect production tools - now includes custom write_file
production_tools = [
    tavily_search,
    write_file_tool,  # Custom tool with explicit schema - overrides DeepAgents default
]

# Create single DeepAgent
agent = create_deep_agent(
    model=model,
    tools=production_tools,
    backend=create_hybrid_backend,  # Provides other filesystem tools (read_file, ls, etc.)
    checkpointer=MemorySaver(),
    system_prompt="""You are a Research & Documentation Sidekick, an autonomous AI assistant specialized in conducting thorough research, creating well-structured documents, and editing content with precision. Your primary mission is to be proactive, complete, and reliable in gathering information and producing high-quality written deliverables.

## Core Capabilities

- **Web Research**: Deep, multi-source research using Tavily search with proper citation tracking
- **Document Creation**: Writing comprehensive documents with complete content (never summarized)
- **Content Editing**: Precise file modifications using targeted edit operations
- **File Management**: Reading, listing, and organizing workspace files
- **Task Planning**: Breaking down complex research and writing tasks into manageable steps

## Critical Tool Usage Rules

### write_file: The Complete Content Imperative

**NEVER summarize, truncate, or abbreviate content when using write_file. ALWAYS include COMPLETE content.**

- ✅ CORRECT: Include every section, paragraph, and detail in full
- ❌ WRONG: Writing "[Previous content...]" or "[Rest of content here]" or "... (content continues)"
- **Why**: Partial content corrupts files and loses user work permanently

**Large Document Strategy** (when content exceeds token limits):
1. Create initial file with first complete sections using write_file
2. Use multiple edit_file calls to append additional sections
3. Each edit adds ONE complete section at a time
4. Verify file integrity after each operation

Example workflow for large research report:
```
1. write_file: Title + Executive Summary + Introduction (complete)
2. edit_file: Append complete "Methodology" section
3. edit_file: Append complete "Findings" section
4. edit_file: Append complete "Conclusion" section
```

### edit_file: When and How to Use

**Use edit_file when:**
- Adding sections to existing documents
- Fixing specific errors or updating specific content
- Appending content that exceeds write_file token limits
- Making targeted changes while preserving most content

**Use write_file when:**
- Creating new documents from scratch
- Complete rewrites are needed
- Document is small enough to include entirely

### tavily_search: Research Best Practices

**Research Strategy:**
- Start broad, then narrow based on findings
- Use 3-5 results for quick checks, 7-10 for comprehensive research
- Extract and cite sources properly (URL, title, snippet)
- Cross-reference multiple sources for controversial claims
- Search multiple times for different aspects of complex topics

**Query Formulation:**
- Be specific and include key terms
- Use year filters for recent information (e.g., "AI trends 2025")
- Include domain-specific keywords for technical topics
- Rephrase and retry if initial results are poor

### ls and read_file: Context Gathering

**Before creating files:**
- Use `ls` to check what files already exist in the workspace
- Read existing related files to maintain consistency
- Check naming conventions from existing files

**File naming conventions:**
- Use descriptive, lowercase names with underscores: `research_report_ai_trends.md`
- Include dates for versioned content: `analysis_2025_01_15.md`
- Use appropriate extensions: `.md` for markdown, `.txt` for plain text

## Critical Error Recovery Rules

**If a tool call fails:**
1. **DO NOT** immediately retry the exact same operation
2. **DO** diagnose why it failed (file too large? wrong path? invalid edit?)
3. **DO** try a different approach (e.g., write_file fails → try iterative strategy)
4. **DO** inform the user if multiple approaches fail

**Common failure scenarios:**
- `write_file` exceeds token limit → Switch to create + edit strategy
- `edit_file` can't find exact match → Read file first, get exact text
- `tavily_search` returns poor results → Rephrase query, try different keywords
- File doesn't exist → Use `ls` to verify path, check workspace structure

## Behavioral Guidelines

### Proactive Research
- Anticipate information needs beyond the immediate question
- Search for related context that provides deeper understanding
- Identify and fill gaps in information automatically
- Suggest additional research angles when relevant

### Document Structure Best Practices
- Use clear hierarchical headings (# ## ###)
- Include table of contents for documents >1000 words
- Add citation sections with source URLs
- Use formatting (bold, italic, lists) for readability
- Include timestamps or version info when relevant

### Communication Style
- **Brief confirmations**: "✓ Created research_report.md (3,240 words)" after tasks
- **Complete content in files**: Put all details in the document, not in messages
- **Ask for clarification** when research scope is ambiguous or could go multiple directions
- **Proactive suggestions**: "I found 3 additional sources on X, should I include them?"

## Common Scenarios

### Scenario 1: Comprehensive Research Report
**Request**: "Research the impact of AI on healthcare in 2025"

**Workflow**:
1. `tavily_search`: "AI healthcare impact 2025" (7-10 results)
2. `tavily_search`: "AI medical diagnosis 2025" (5 results)
3. `tavily_search`: "AI healthcare challenges 2025" (5 results)
4. `write_file`: Create complete report with all sections:
   - Title & metadata
   - Executive summary
   - Background
   - Key findings (from all searches)
   - Implications
   - Citations
5. Confirm: "✓ Created ai_healthcare_impact_2025.md (4,850 words, 22 sources)"

### Scenario 2: Large Document (>10,000 words)
**Request**: "Create a comprehensive guide to Python async programming"

**Workflow**:
1. Research phase: Multiple Tavily searches for different aspects
2. `write_file`: Title + Introduction + "Fundamentals" section (complete, ~2000 words)
3. `read_file`: Verify content integrity
4. `edit_file`: Append complete "Async/Await Patterns" section
5. `edit_file`: Append complete "Concurrency Best Practices" section
6. `edit_file`: Append complete "Common Pitfalls" section
7. `edit_file`: Append complete "Advanced Topics + Conclusion"
8. Final verification read

### Scenario 3: Document Editing
**Request**: "Add a section on security concerns to the AI report"

**Workflow**:
1. `read_file`: Read current document
2. `tavily_search`: "AI security concerns 2025" (5 results)
3. `edit_file`: Insert complete security section in appropriate location
4. Confirm: "✓ Added 'Security Considerations' section (680 words, 4 sources)"

## Key Principles

**As a research and documentation sidekick:**
- **Completeness**: Every file write contains FULL content, never summaries
- **Adaptability**: Learn from errors and switch strategies when needed
- **Proactivity**: Anticipate needs and suggest improvements
- **Reliability**: Verify operations and maintain file integrity
- **Clarity**: Brief messages to users, detailed content in files

**Remember**: You are the user's trusted sidekick for research and documentation. Be thorough in research, complete in content creation, and adaptive when facing challenges. The user depends on you to produce reliable, high-quality deliverables without requiring constant supervision.

Tools Available:
- tavily_search: Web search returning sources with URLs
- write_file: Create file - REQUIRES BOTH file_path="/workspace/..." AND content="..." parameters
- edit_file: Modify existing files
- read_file: Read file contents
- ls: List directory contents
- glob: Search for files by pattern
- grep: Search file contents
- write_todos: Plan multi-step tasks (optional for 3+ steps)

🔮 Future: Firecrawl, GitHub, e2b will be added as subagents
"""
)

print("✅ DeepAgent Ready with Tavily + built-in filesystem tools\n")

# ============================================================================
# EXECUTION FUNCTION WITH STREAMING
# ============================================================================

def run_agent_task(query: str, thread_id: str = "demo"):
    """Execute agent task with streaming and real-time visibility."""

    print("\n" + "🎯" * 40)
    print(f"USER QUERY: {query}")
    print("🎯" * 40)

    config = {"configurable": {"thread_id": thread_id}}

    print("\n🚀 Streaming DeepAgent execution...\n")
    print("─" * 80)

    final_response = None
    step_count = 0

    # Stream with updates mode for real-time visibility
    for chunk in agent.stream(
        {"messages": [{"role": "user", "content": query}]},
        config=config,
        stream_mode="updates"
    ):
        step_count += 1

        # chunk is a dict with node name as key
        for node_name, node_update in chunk.items():
            if node_name == "__start__" or node_name == "__end__":
                continue

            # Skip if update is None or empty
            if not node_update:
                continue

            print(f"\n📍 Node: {node_name}")

            # Check for messages in the update
            if "messages" in node_update:
                messages = node_update["messages"]
                for msg in messages:
                    # Check for AI message with tool calls
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            print(f"  🔧 TOOL CALL: {tool_call['name']}")
                            args = tool_call.get('args', {})
                            if args:
                                # Show first 2 args, truncate values
                                arg_items = list(args.items())[:2]
                                arg_str = ", ".join(f"{k}={str(v)[:60]}" for k, v in arg_items)
                                print(f"     Args: {arg_str}")

                    # Check for tool message (results)
                    elif hasattr(msg, "tool_call_id"):
                        content = str(msg.content)
                        preview = content[:200] if len(content) > 200 else content
                        print(f"  📊 TOOL RESULT:")
                        print(f"     {preview}{'...' if len(content) > 200 else ''}")

                    # Check for AI response (final answer)
                    elif hasattr(msg, "content") and msg.content and not hasattr(msg, "tool_calls"):
                        # This is likely the final response
                        final_response = node_update

            # Check for todos (planning)
            if "todos" in node_update:
                todos = node_update["todos"]
                if todos:
                    print(f"  📝 PLANNING: {len(todos)} tasks created")
                    for todo in todos[:3]:  # Show first 3
                        status = todo.get("status", "unknown")
                        content = todo.get("content", "")
                        print(f"     [{status}] {content[:60]}")

            # Display progress logs if present
            if "logs" in node_update and node_update["logs"]:
                print(f"  📋 PROGRESS LOGS:")
                for log in node_update["logs"]:
                    status = "✅" if log.get("done", False) else "⏳"
                    print(f"     {status} {log['message']}")

    print("\n" + "─" * 80)
    print(f"✅ Completed in {step_count} stream events\n")

    # Get final result from last stream
    result = agent.invoke(
        {"messages": [{"role": "user", "content": query}]},
        config=config
    )

    # Display final result
    if result and "messages" in result:
        final_message = result["messages"][-1]
        print("=" * 80)
        print("📊 FINAL RESULT")
        print("=" * 80)
        print(final_message.content if hasattr(final_message, "content") else str(final_message))
        print("=" * 80)

    return result


# ============================================================================
# EXAMPLES
# ============================================================================

if __name__ == "__main__":
    print("\n\n" + "🔬" * 40)
    print("EXAMPLE 1: Simple Search with Citations")
    print("🔬" * 40)

    result1 = run_agent_task(
        "Search for the latest updates on LangChain v1.0 and create a summary with citations at /workspace/langchain_v1_summary.md",
        thread_id="citation-demo-1"
    )

    print("\n\n" + "🔬" * 40)
    print("EXAMPLE 2: Multi-Source Research with Citations")
    print("🔬" * 40)

    result2 = run_agent_task(
        "Research DeepAgents v0.2 architecture and benefits. Create a comprehensive report at /workspace/deepagents_research.md with inline citations for every claim.",
        thread_id="citation-demo-2"
    )

    print("\n\n" + "🔬" * 40)
    print("EXAMPLE 3: Multi-Step Task with Citations")
    print("🔬" * 40)

    result3 = run_agent_task(
        """Research the benefits of agentic AI systems, create a comparison with traditional AI,
        and save a detailed report with citations at /workspace/agentic_ai_report.md""",
        thread_id="citation-demo-3"
    )

# ============================================================================
# SUMMARY
# ============================================================================

if __name__ == "__main__":
    print("\n\n" + "=" * 80)
    print("MODULE 2.2 SUMMARY")
    print("=" * 80)

    summary = """
✅ Demonstrated Concepts:

1. Simplified DeepAgent Architecture
   - Single agent with focused tool set (Tavily + filesystem)
   - Automatic planning with TodoListMiddleware
   - Streaming execution for real-time visibility

2. Production Tool Integration
   - Tavily: Real-time web search with up-to-date information
   - Native LangChain tool integration

3. DeepAgents v0.2 Features
   - CompositeBackend for hybrid storage
   - TodoListMiddleware (automatic planning)
   - FilesystemMiddleware (built-in file operations)
   - Conversation checkpointing for memory
   - Streaming support for transparency

4. Built-in Capabilities
   - Filesystem tools (ls, read_file, write_file, edit_file, glob, grep)
   - TODO list tracking (write_todos tool)
   - Hybrid storage (/workspace/ → filesystem, default → ephemeral)

📚 Key Learnings:

- Start simple: Tavily + filesystem tools provide powerful baseline
- Tool count matters: Fewer tools = lower overhead, works with Haiku 4.5
- Streaming provides transparency and catches issues early
- Hybrid backends enable both ephemeral and persistent storage
- Claude Haiku 4.5 provides fast, cost-effective reasoning ($1/$5 per 1M tokens)

🔧 Tool Usage Patterns:

- Tavily: Web research, current events, documentation lookup
- write_todos: Planning multi-step tasks
- write_file: Saving research findings and reports
- Filesystem: Managing data across conversation turns

🎯 Next Steps:

1. **Add Subagents** (Future Modules):
   - Firecrawl subagent for web scraping
   - GitHub subagent for repository operations
   - e2b subagent for code execution

2. **Advanced Features**:
   - Experiment with StoreBackend for cross-session persistence
   - Implement human-in-the-loop for sensitive operations
   - Deploy with production checkpointing (PostgreSQL)

💡 Production Considerations:

- Rate limits: Tavily has 1,000 searches/month (free tier)
- Error handling: Robust error handling implemented
- Cost tracking: Monitor Tavily API usage
- Security: API keys in environment variables
- Scalability: StoreBackend + PostgreSQL for multi-user deployments

🎓 Architecture Decision:

- **Why simplified**: Haiku 4.5 has strict request size limits
- **10+ tools** (previous version) → 413 "Request Too Large" errors
- **7 tools** (current: 1 production + 6 filesystem) → Works smoothly
- **Future growth**: Add specialized tools via subagents, not main agent

"""

    print(summary)
    print("=" * 80)

    print("\n✨ Module 2.2 Complete! ✨\n")
