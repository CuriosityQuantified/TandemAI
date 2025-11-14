# Module 2.2: DeepAgents with Tavily + Built-in Tools

## Overview

This module demonstrates a **single DeepAgent** with Tavily web search and built-in filesystem tools, showcasing how to build a production-ready agent within Claude Haiku 4.5's request size constraints.

**Architecture Decision**: Start simple with core tools, then add specialized capabilities via subagents (future modules).

###Critical Finding: Tool Count Limits

- **Haiku 4.5 Limit**: Supports ~7 tools max (1 production + 6 filesystem)
- **Previous Attempt**: 10+ tools (Tavily, Firecrawl, GitHub, e2b + filesystem) → 413 errors
- **Current Solution**: Tavily-only + built-in tools → **Works perfectly**
- **Future Growth**: Add Firecrawl, GitHub, e2b as subagents, not direct tools

## What Changed from Previous Version

### Before: Multi-Agent Supervisor Pattern
- **Architecture**: Supervisor + 3 sub-agents (researcher, analyst, writer)
- **Tools**: Simulated tools (mock web_search, analyze_data, format_document)
- **Complexity**: Higher - required coordination between multiple agents
- **Use Case**: Best for truly specialized, independent tasks

### After: Single Agent with Production Tools
- **Architecture**: One powerful DeepAgent with multiple tools
- **Tools**: Real production APIs (Tavily, Firecrawl, GitHub, e2b)
- **Complexity**: Lower - direct tool access, no delegation overhead
- **Use Case**: Most real-world scenarios requiring multiple capabilities

## Production Tools

### **Tavily Search** (Native LangChain Tool) ✅ Integrated
- **Purpose**: Real-time web search for current information
- **API**: Tavily API
- **LangChain Integration**: `TavilySearch` (langchain-tavily)
- **Example Use**: "Search for the latest LangChain v1.0 updates"
- **Status**: Active in main DeepAgent

### **Future Tools** (Coming as Subagents) 🔮

These tools will be added in future modules as specialized subagents:

#### **Firecrawl Subagent**
- **Purpose**: Advanced web scraping with markdown extraction
- **Why Subagent**: Reduces main agent tool overhead
- **When to Use**: When user needs specific page content extraction

#### **GitHub Subagent**
- **Purpose**: Repository search and code discovery
- **Why Subagent**: Specialized repository operations
- **When to Use**: When user needs to find or analyze code repositories

#### **e2b Subagent**
- **Purpose**: Secure Python code execution
- **Why Subagent**: Isolated execution environment
- **When to Use**: When user needs to run/test code safely

## Key Features

### DeepAgents v0.2 Capabilities
1. **Automatic Planning**: TodoListMiddleware creates task plans automatically
2. **Hybrid Storage**: CompositeBackend routes `/workspace/` to filesystem
3. **Built-in Filesystem Tools**: ls, read_file, write_file, edit_file, glob, grep
4. **Conversation Memory**: MemorySaver checkpointer for multi-turn conversations
5. **Large Result Eviction**: Automatically saves oversized tool outputs to filesystem

### Model Configuration

✅ **Successfully Using Haiku 4.5!**

- **Model**: Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)
- **Provider**: Anthropic (direct API)
- **Released**: October 1, 2025
- **Temperature**: 0.7 (balanced creativity and consistency)
- **Cost**: $1 per 1M input tokens, $5 per 1M output tokens

**Why Haiku Works Now**:
- Reduced from 10+ tools to 7 tools (1 Tavily + 6 filesystem)
- Optimized system prompt (~200 tokens, down from ~400)
- Streaming execution for real-time visibility
- Total overhead fits within Haiku's request limits

## Installation

### Required Dependencies

```bash
# Activate virtual environment
cd /Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons
source .venv/bin/activate

# Install core packages
pip install deepagents langchain-anthropic langchain-community

# Install tool dependencies
pip install e2b-code-interpreter tavily-python requests

# Install LangGraph dependencies
pip install langgraph
```

### Environment Variables (.env)

Required API keys in `.env` file:
```bash
ANTHROPIC_API_KEY=sk-ant-...          # Claude API key
TAVILY_API_KEY=tvly-...               # Tavily search API key
FIRECRAWL_API_KEY=fc-...              # Firecrawl scraping API key
GITHUB_API_KEY=github_pat_...         # GitHub personal access token
E2B_API_KEY=e2b_...                   # e2b code execution API key
```

## Usage

### Running the Examples

```bash
# Navigate to module directory
cd /Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2

# Activate virtual environment
source ../.venv/bin/activate

# Run the script
python module-2-2-simple.py
```

### Example Queries

#### Example 1: Web Search
```python
run_agent_task(
    "Search for the latest updates on LangChain v1.0 and summarize the key features",
    thread_id="tavily-demo"
)
```

#### Example 2: Research and Save
```python
run_agent_task(
    "Research DeepAgents v0.2 using web search and save a summary to /workspace/deepagents_summary.md",
    thread_id="research-demo"
)
```

#### Example 3: Multi-Step Planning
```python
run_agent_task(
    """Research the benefits of agentic AI systems, create a comparison with traditional AI,
    and save a detailed report to /workspace/agentic_ai_report.md""",
    thread_id="planning-demo"
)
```

## Architecture Details

### Hybrid Backend Configuration

```python
def create_hybrid_backend(rt):
    """Hybrid storage: ephemeral + filesystem."""
    return CompositeBackend(
        default=StateBackend(rt),  # Ephemeral for temporary data
        routes={
            "/workspace/": FilesystemBackend(root_dir=workspace_dir, virtual_mode=True),  # Persistent files
        }
    )
```

**Storage Strategy**:
- **Default (StateBackend)**: Ephemeral storage in LangGraph state
  - Lost when thread ends
  - Good for intermediate results
- **/workspace/ (FilesystemBackend)**: Persistent filesystem storage
  - **CRITICAL**: `virtual_mode=True` is required for proper path routing
  - Sandboxes and normalizes paths under `root_dir`
  - Agent writes to `/workspace/file.txt` → saves as `{root_dir}/file.txt`
  - Saved to `agent_workspace/` directory
  - Survives restarts
  - Good for reports, analysis results

### Tool Selection Logic

The agent automatically selects tools based on:
1. **Task Requirements**: What the user is asking for
2. **TodoListMiddleware**: Plans multi-step tasks
3. **Context**: Previous conversation and results

Example decision flow:
```
User: "Research LangChain and create a report"
  ↓
Agent Plans:
  1. Use tavily_search → Get web results
  2. Use write_file → Save to /workspace/report.md
  ↓
Agent Executes each step
```

## Production Considerations

### Rate Limits
- **Tavily**: 1,000 searches/month (free tier)
- **Firecrawl**: 500 pages/month (free tier)
- **GitHub**: 5,000 requests/hour (authenticated)
- **e2b**: 100 executions/month (free tier)

### Error Handling
Current implementation includes basic error handling:
- Network timeouts (30s for Firecrawl)
- API error responses
- Sandbox execution failures

**TODO**: Add retry logic with exponential backoff

### Cost Tracking
Estimated costs per query:
- **Tavily**: $0.001 per search (paid plan)
- **Firecrawl**: $0.002 per page
- **GitHub**: Free (up to rate limit)
- **e2b**: $0.005 per execution
- **Claude Haiku**: $0.000003 per 1K tokens

Average complex query: ~$0.02 - $0.05

### Security Best Practices
✅ API keys in environment variables (not hardcoded)
✅ Filesystem access sandboxed to `/workspace/`
✅ Code execution in isolated e2b sandbox
⚠️ GitHub token has read-only access
⚠️ Consider adding human-in-the-loop for write operations

## Comparison: Single Agent vs Multi-Agent

| Aspect | Single Agent (Current) | Multi-Agent (Previous) |
|--------|----------------------|----------------------|
| **Complexity** | Low - direct tool access | High - delegation overhead |
| **Latency** | Lower - fewer LLM calls | Higher - multiple agent calls |
| **Cost** | Lower - single agent token usage | Higher - multiple agents |
| **Flexibility** | High - agent chooses tools dynamically | Medium - rigid specialization |
| **Best For** | Most real-world tasks | Truly independent, specialized workflows |

## Next Steps

### Immediate Improvements
1. **Add StoreBackend**: Replace StateBackend with persistent cross-session memory
2. **Implement Retry Logic**: Handle rate limits and network failures gracefully
3. **Add Streaming**: Show real-time progress for long-running tasks
4. **Human-in-the-Loop**: Add approval workflow for sensitive operations

### Advanced Features
1. **Custom Middleware**: Add logging, metrics, and observability
2. **Multi-Modal Support**: Add image analysis, audio transcription
3. **Database Integration**: Add PostgreSQL tools for data analysis
4. **API Integrations**: Add Slack, email, calendar tools

### Production Deployment
1. **PostgreSQL Checkpointing**: Replace MemorySaver for scalability
2. **LangSmith Integration**: Add observability and debugging
3. **FastAPI Wrapper**: Create REST API endpoints
4. **Docker Containerization**: Package for deployment

## Resources

### Official Documentation
- **DeepAgents v0.2**: [Blog Post](https://blog.langchain.com/doubling-down-on-deepagents/)
- **LangChain Docs**: [python.langchain.com](https://python.langchain.com/docs)
- **LangGraph Docs**: [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph)

### Tool Documentation
- **Tavily**: [docs.tavily.com](https://docs.tavily.com)
- **Firecrawl**: [firecrawl.dev/docs](https://firecrawl.dev/docs)
- **GitHub API**: [docs.github.com/rest](https://docs.github.com/en/rest)
- **e2b**: [e2b.dev/docs](https://e2b.dev/docs)

### Internal Resources
- **Learning Guide**: `../langchain-langgraph-hands-on-guide.md`
- **DeepAgents Research**: `../deepagents_v0.2_research.md`
- **Module 1.1**: Model configuration examples

## Troubleshooting

### Common Issues

**1. Import Error: No module named 'langchain_community'**
```bash
pip install langchain-community
```

**2. Import Error: No module named 'e2b_code_interpreter'**
```bash
pip install e2b-code-interpreter
```

**3. API Rate Limit Exceeded**
- Wait for rate limit reset
- Upgrade to paid tier
- Implement caching to reduce API calls

**4. Sandbox Timeout (e2b)**
- Reduce code complexity
- Split into multiple executions
- Check e2b dashboard for quota

**5. Firecrawl Returns Empty Content**
- Check if website blocks scraping
- Try different URL format
- Verify API key is valid

**6. Request Too Large Error (413)**

This error occurs when the request to Claude exceeds the maximum size limit. Common causes and solutions:

**Causes:**
- Too many tools (each tool definition adds ~50-100 tokens)
- Verbose system prompts (400+ tokens)
- Large tool results in conversation history
- Deep conversation history accumulation

**Solutions:**
1. **Optimize Tool Descriptions** (Already Implemented)
   - Reduced from ~100 tokens to ~40 tokens per tool
   - Keep descriptions concise while maintaining functionality

2. **Optimize System Prompt** (Already Implemented)
   - Reduced from ~400 tokens to ~200 tokens
   - Added context management best practices
   - Teaches agent to save large results to files

3. **Use Streaming** (Already Implemented)
   - Real-time visibility of tool calls and results
   - Monitor execution progress
   - Catch issues early

4. **Leverage Auto-Eviction**
   - FilesystemMiddleware auto-evicts tool results >20,000 tokens
   - Large results saved to `/large_tool_results/`
   - Agent reads from files instead of keeping in context

5. **Manual File Writing**
   - For scraping/search: Save results to `/workspace/` immediately
   - Example:
     ```python
     # Instead of returning large content:
     result = tavily_search.invoke("query")
     # Agent should:
     write_file("/workspace/search_results.txt", result)
     # Then reference the file in response
     ```

6. **Clear Thread History**
   - Long conversations accumulate context
   - Use new `thread_id` for unrelated tasks
   - Example: `thread_id=f"task-{timestamp}"`

**Prevention Best Practices:**
- Start complex tasks with `write_todos` for planning
- Save intermediate results to `/workspace/`
- Use concise tool descriptions
- Teach agents context management in system prompt

## Key Features Added (v2.1)

### 1. **Streaming Execution**
- Real-time visibility of tool calls and results
- Shows planning decisions as they happen
- Displays execution progress with step counts

### 2. **Optimized Prompts**
- System prompt: 400 → 200 tokens (50% reduction)
- Tool descriptions: 100 → 40 tokens each (60% reduction)
- Total overhead reduction: ~500 tokens

### 3. **Context Management**
- Explicit guidance to save large results
- Auto-eviction threshold documented
- Best practices taught to the agent

### 4. **Transparency Features**
- `🔧 TOOL CALL:` displays tool invocations
- `📊 TOOL RESULT:` shows execution results (truncated)
- `✅ Completed in X events` tracks execution

## Support

For issues or questions:
1. Review the learning guide: `../langchain-langgraph-hands-on-guide.md`
2. Check DeepAgents research: `../deepagents_v0.2_research.md`
3. Consult official LangChain Discord: [discord.gg/langchain](https://discord.gg/langchain)

## v2.3 Updates: Citation System & Progress Logging

### Citation System
All generated documents now include:
- **Inline citations**: `[^1]`, `[^2]`, etc. after every factual claim
- **Footer references**: `[^1]: Source Title - URL` in a References section
- **Proper source attribution**: All claims traced back to source URLs from tavily_search

### Progress Logging
Real-time visibility into agent operations:
- **Search progress**: Log entries show what the agent is doing
- **Log helper functions**: `add_log()`, `complete_log()`, `clear_logs()` ready for custom tools
- **Streaming display**: Progress logs visible in `run_agent_task()` output

### Enhanced Tool Descriptions
Pydantic schemas for better tool usage:
- **ResearchSearchArgs**: Structured arguments for Tavily search
- **EnhancedTavilyTool**: Wrapper with enhanced descriptions for citation support
- **Tool usage patterns**: Documented best practices for research workflows

### Enhanced Frontend
New research canvas layout (see `module-2-2-frontend-enhanced/`):
- **Sources Panel**: Track all research sources with citation tracking
- **Document Viewer**: Display documents with clickable citations
- **Progress Logs**: Real-time execution progress sidebar
- **Professional Layout**: Three-column research workflow interface

### Migration from v2.2
No breaking changes - v2.3 is fully backward compatible:
- Existing code continues to work without modifications
- Citations are requested via query text (e.g., "with citations")
- Progress logging infrastructure ready for custom tools
- Enhanced frontend is optional upgrade

See `MIGRATION_v2.3.md` for detailed upgrade guide.

---

**Last Updated**: 2025-10-31
**Version**: 2.3 (Citation System & Progress Logging)
**Author**: Based on Module 2.2 from LangChain/LangGraph Hands-On Guide

## Changelog

### v2.3 (2025-10-31)
- ✅ **Citation System**: Enhanced system prompt with citation requirements
- ✅ **Progress Logging**: Added state schema and log helper functions
- ✅ **Enhanced Tools**: Pydantic schemas for better tool descriptions
- ✅ **Frontend v2.3**: Research canvas with sources panel, document viewer, progress logs
- ✅ **Validation Tests**: Citation and progress logging test scripts
- ✅ **Documentation**: Comprehensive guide to new features

### v2.2 (2025-10-30)
- ✅ **CRITICAL FIX**: Added `virtual_mode=True` to FilesystemBackend for proper path routing
- ✅ Simplified to Tavily-only architecture (7 tools total)
- ✅ Removed Firecrawl, GitHub, e2b from main agent (will be subagents in future)
- ✅ Successfully running on Claude Haiku 4.5 with no 413 errors
- ✅ Verified complete workflow: web search + file writing working perfectly
- ✅ Updated documentation with hybrid backend configuration details

### v2.1 (2025-10-30)
- ✅ Added streaming execution for real-time visibility
- ✅ Optimized system prompt (50% reduction)
- ✅ Optimized tool descriptions (60% reduction)
- ✅ Added comprehensive 413 error troubleshooting
- ✅ Documented context management best practices
- ✅ Added transparency features (tool call/result logging)

### v2.0 (2025-10-30)
- Initial release with production tools (Tavily, Firecrawl, GitHub, e2b)
- Single DeepAgent architecture
- Hybrid storage backend
