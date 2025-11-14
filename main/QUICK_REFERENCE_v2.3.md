# Module 2.2 v2.3 Quick Reference

## Installation & Setup

### Basic Usage (CLI)
```bash
cd module-2-2
source ../.venv/bin/activate  # Activate virtual environment
python module-2-2-simple.py    # Run examples
```

### Enhanced Frontend
```bash
# Terminal 1: Backend
cd module-2-2-frontend-enhanced/backend
python main.py

# Terminal 2: Frontend
cd module-2-2-frontend-enhanced/frontend
npm install  # First time only
npm run dev

# Open: http://localhost:3000
```

## Citation System

### Request Citations
```python
# In your queries, explicitly request citations
run_agent_task(
    "Research topic X with citations",
    thread_id="demo"
)
```

### Citation Format
```markdown
LangChain v1.0 introduces middleware system[^1] and simplified APIs[^2].

---
## References
[^1]: Source Title - https://full-url.com
[^2]: Another Source - https://another-url.com
```

### Validation
```bash
python test_citations.py  # Validate citation format
```

## Progress Logging

### Helper Functions
```python
from module_2_2_simple import add_log, complete_log, clear_logs

# Add a log entry
state = add_log(state, "🌐 Searching for data...")

# Mark last log as complete
state = complete_log(state)

# Clear all logs
state = clear_logs(state)
```

### Custom Tool with Logging
```python
from langchain_core.tools import tool

@tool
def my_research_tool(query: str, state: dict):
    """Custom research tool with progress logging."""
    # Log start
    add_log(state, f"🔬 Analyzing {query}...")

    # Do work
    result = analyze(query)

    # Log completion
    complete_log(state)

    return result
```

### View Logs
```python
# Logs appear automatically in streaming output
run_agent_task("Research topic", thread_id="demo")
# Output includes:
#   📋 PROGRESS LOGS:
#      ⏳ 🌐 Searching...
#      ✅ 🌐 Searching... (done)
```

### Validation
```bash
python test_progress_logs.py  # Check log infrastructure
```

## Enhanced Tools

### Pydantic Schema Example
```python
from pydantic import BaseModel, Field

class MyToolArgs(BaseModel):
    """Arguments for my custom tool."""
    query: str = Field(
        description="Specific question to answer"
    )
    depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Analysis depth (1-10)"
    )
```

### Tool Wrapper
```python
class EnhancedMyTool:
    """Enhanced tool with better descriptions."""

    def __init__(self, base_tool):
        self.tool = base_tool
        self.name = "enhanced_tool"
        self.description = "Detailed description for citations"
        self.args_schema = MyToolArgs

    def invoke(self, query: str, depth: int = 3):
        return self.tool.invoke({"query": query, "depth": depth})
```

## Frontend Components

### Event Types
```typescript
// Tool call
{
  type: 'tool_call',
  tool: 'tavily_search',
  args: { query: '...' }
}

// Progress log
{
  type: 'progress_log',
  message: '🌐 Searching...',
  done: false
}

// Tool result
{
  type: 'tool_result',
  content: '...'
}
```

### Custom Event Handler
```typescript
const handleMessage = async (message: string) => {
  const response = await fetch('http://localhost:8000/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));

        if (data.type === 'progress_log') {
          // Handle progress log
          console.log(`${data.done ? '✅' : '⏳'} ${data.message}`);
        }
      }
    }
  }
};
```

## Common Queries

### Research with Citations
```python
"Search for latest React 19 features and create summary with citations"
```

### Multi-Source Research
```python
"Research DeepAgents v0.2 architecture and benefits. Create report with inline citations for every claim."
```

### Comparison Study
```python
"Compare agentic AI vs traditional AI and save detailed report with citations"
```

## File Paths

### Workspace Files
```python
# Always use /workspace/ prefix
write_file(
    file_path="/workspace/report.md",
    content="Full document content..."
)

# Maps to: agent_workspace/report.md
```

### Reading Workspace Files
```bash
cat agent_workspace/report.md
ls agent_workspace/
```

## Troubleshooting

### Citations Not Appearing
```bash
# Check system prompt loaded
grep "Citation" module-2-2-simple.py

# Request citations explicitly
"Research X with citations"

# Validate output
python test_citations.py
```

### Logs Not Showing
```bash
# Check state schema defined
grep "AgentState" module-2-2-simple.py

# Verify helper functions
grep "add_log" module-2-2-simple.py

# Run validation
python test_progress_logs.py
```

### Frontend Not Connecting
```bash
# Check backend running
curl http://localhost:8000/health

# Check frontend running
curl http://localhost:3000

# Verify CORS settings in backend/main.py
```

## Testing

### Run All Tests
```bash
# Citation validation
python test_citations.py

# Progress logging check
python test_progress_logs.py

# Run examples
python module-2-2-simple.py
```

### Manual Testing
```bash
# Test CLI
python -c "from module_2_2_simple import run_agent_task; run_agent_task('Search for Python 3.12', 'test')"

# Check generated files
ls agent_workspace/
cat agent_workspace/*.md
```

## Configuration

### Environment Variables (.env)
```bash
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
```

### Model Settings
```python
# In module-2-2-simple.py
model = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    temperature=0.7,  # Adjust for creativity
)
```

### Workspace Directory
```python
# In module-2-2-simple.py
workspace_dir = "/path/to/agent_workspace"
```

## Version Information

- **Version**: 2.3
- **Python**: 3.10+
- **Node.js**: 18+ (for frontend)
- **Claude Model**: Haiku 4.5
- **Dependencies**: See `requirements.txt`

## Quick Links

- Full README: `README.md`
- Migration Guide: `MIGRATION_v2.3.md`
- Implementation Details: `IMPLEMENTATION_SUMMARY_v2.3.md`
- Frontend Docs: `module-2-2-frontend-enhanced/README.md`

---

**Last Updated**: 2025-10-31
**Version**: 2.3
