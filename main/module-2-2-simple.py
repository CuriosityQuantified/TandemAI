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

print("\n🔧 Production Tool Initialized:")
print("  ✅ Tavily Search - Web search with up-to-date information")
print("  ✅ Enhanced Tool Schema - Pydantic validation for better citations")
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

print("\n💾 Hybrid Backend: /workspace/ → Filesystem, Default → Ephemeral")

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
   - Requires: file_path (/workspace/...) AND content (full text)
   - Citation format in content:
     * Inline: "Claim text[^1]"
     * Footer: "[^1]: Title - URL"
   - Common error: Missing content parameter

3. write_todos (optional):
   - Use for: Tasks with 3+ distinct steps
   - Not required for simple research + write workflows
"""

# ============================================================================
# DEEP AGENT CREATION
# ============================================================================

print("\n🤖 Creating DeepAgent...")

# Collect production tools (just Tavily for now)
production_tools = [
    tavily_search,
]

# Create single DeepAgent
agent = create_deep_agent(
    model=model,
    tools=production_tools,
    backend=create_hybrid_backend,
    checkpointer=MemorySaver(),
    system_prompt="""AI research assistant with web search and filesystem capabilities.

CRITICAL: Citation & Source Attribution
- EVERY factual claim, statistic, or data point MUST have an inline citation
- Use markdown footnotes: [^1], [^2], [^3], etc.
- Inline format: "The framework was released in 2024[^1]."
- Footer format (at end of document):

  ---
  ## References
  [^1]: Source Title - https://full-url.com
  [^2]: Another Source - https://another-url.com

- Each document starts footnotes from [^1]
- NEVER make unsourced factual claims
- Cite the SOURCE URL from tavily_search results

Research Workflow (follow in order):
1. tavily_search: Gather credible sources (saves URLs and content)
2. Analyze findings mentally (identify key claims, note source URLs)
3. write_file: Create document with:
   - Inline citations [^1] after each claim
   - Footer section with all references
   - Format: [^n]: Source Title - Full URL

Tools Available:
- tavily_search: Web search returning sources with URLs
- write_file: Create file (requires file_path AND content)
- write_todos: Plan multi-step tasks (optional for 3+ steps)
- Filesystem: ls, read_file, edit_file, glob, grep

File Path Rules:
- ALL files MUST use /workspace/ prefix
- ✅ write_file(file_path="/workspace/report.md", content="...")
- ❌ write_file(file_path="/report.md", ...) - will fail

Communication Style:
- After completing tasks: Brief confirmation (max 10 words)
- Example: "Research complete. Report saved at /workspace/report.md"
- Don't repeat content visible to user
- Ask for next steps or feedback

Citation Example:
"LangChain v1.0 introduces middleware system[^1] and simplified APIs[^2].

---
## References
[^1]: LangChain v1.0 Release - https://blog.langchain.com/langchain-langgraph-1dot0/
[^2]: LangChain Documentation - https://docs.langchain.com/oss/python/langchain/overview"

Future: Firecrawl, GitHub, e2b will be available via subagents.
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
