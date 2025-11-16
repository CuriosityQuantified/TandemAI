# Deep Research Agent System

A sophisticated multi-agent research system built on LangChain DeepAgents with configurable effort levels, knowledge graph integration, and human-in-the-loop workflows.

## Overview

This system implements a **6-tier effort level** research framework with automatic search tracking, context management, and quality assessment. It's designed to handle everything from quick 5-search queries to comprehensive 500-search deep dives.

## Architecture

### Core Components

1. **State Management** (`state.py`)
   - `ResearchState`: TypedDict with accumulators for search results, citations, actions
   - `SearchResult`, `Citation`, `ActionRecord`: Pydantic models for structured data
   - `QualityMetrics`: Quality assessment tracking
   - Automatic action history trimming (keeps last 5 + essential context)

2. **Effort Level Configuration** (`effort_config.py`)
   - 6 effort levels: quick, standard, thorough, deep, extended_deep, ultrathink_deep
   - Configurable parameters per level: min_searches, max_iterations, depth, features
   - Dynamic quality threshold checks
   - Feature flags (knowledge graph, vector RAG, advanced summarization)

3. **Base Agent** (`base_agent.py`)
   - LangGraph StateGraph orchestrating the workflow
   - 4 main nodes: planning, research, analysis, writing
   - Conditional routing based on search count and quality
   - PostgreSQL checkpoint integration for state persistence

### Workflow

```
┌─────────────┐
│  Planning   │  - Clarify query, create research plan
└──────┬──────┘  - Request HITL approval if enabled
       │
       ▼
┌─────────────┐
│  Research   │  - Perform searches using Tavily
└──────┬──────┘  - Track search count and queries
       │
       ▼
┌─────────────┐
│  Analysis   │  - Extract key findings
└──────┬──────┘  - Assess quality
       │
       ▼
┌─────────────┐
│  Continue?  │  - Check min searches met
└──────┬──────┘  - Check quality threshold
       │
       ├─► Continue ──► Research (loop back)
       │
       └─► Write ──┐
                   │
                   ▼
            ┌─────────────┐
            │   Writing   │  - Generate final report
            └─────────────┘  - Include citations
                   │
                   ▼
                  END
```

## Effort Levels

| Level | Min Searches | Max Iterations | Features |
|-------|--------------|----------------|----------|
| **quick** | 5 | 3 | Basic search, 2 parallel |
| **standard** | 20 | 5 | Vector RAG, 3 parallel, loop detection |
| **thorough** | 50 | 8 | + Knowledge graph, summarization, 4 parallel |
| **deep** | 100 | 12 | + Enhanced KG/RAG, 5 parallel |
| **extended_deep** | 250 | 20 | + Advanced summarization, 6 parallel |
| **ultrathink_deep** | 500 | 30 | + Definitive coverage, 8 parallel |

## Installation

```bash
# Already installed in project
pip install deepagents langchain-anthropic langchain-tavily langgraph langgraph-checkpoint-postgres
```

## Usage

### Basic Usage

```python
import asyncio
from agents.deep_research import create_deep_research_agent, create_initial_state, EffortLevel

async def run_research():
    # Create agent with checkpointing
    agent = create_deep_research_agent(checkpointer=your_checkpointer)

    # Create initial state
    state = create_initial_state(
        query="What are the latest developments in quantum computing?",
        effort_level=EffortLevel.STANDARD,
        session_id="unique-session-id",
        hitl_enabled=False,
    )

    # Run research
    config = {"configurable": {"thread_id": "unique-session-id"}}
    async for event in agent.astream(state, config, stream_mode="values"):
        print(f"Phase: {event['phase']} | Searches: {event['search_count']}")

    # Get final report
    final_state = event
    print(final_state["final_report"])

asyncio.run(run_research())
```

### With Human-in-the-Loop

```python
state = create_initial_state(
    query="How does climate change affect food security?",
    effort_level=EffortLevel.THOROUGH,
    session_id="session-123",
    hitl_enabled=True,  # Enable HITL approval
)

# Agent will pause at planning phase for approval
# Check event["approval_required"] and event["planning_approved"]
```

### Running Examples

```bash
cd backend
python -m agents.deep_research.example_usage
```

## State Schema

### Key State Fields

```python
ResearchState = {
    # Core
    "query": str,                           # Original question
    "clarified_query": str | None,          # Refined question
    "final_report": str | None,             # Final output

    # Search tracking
    "search_results": list[SearchResult],   # All search results
    "search_count": int,                    # Total searches
    "search_requirement": int,              # Minimum required

    # Quality
    "quality_metrics": QualityMetrics,      # Quality assessment
    "quality_threshold_met": bool,          # Threshold reached?

    # Context management
    "action_history": list[ActionRecord],   # Last 5 actions + essential
    "essential_findings": list[str],        # Key discoveries

    # Progress
    "iteration": int,                       # Current iteration
    "phase": str,                           # Current phase
    "should_continue": bool,                # Continue research?

    # HITL
    "hitl_enabled": bool,                   # HITL mode on?
    "approval_required": bool,              # Waiting for approval?
    "planning_approved": bool,              # Plan approved?

    # Effort config
    "effort_level": str,                    # Current effort level
    "min_searches_required": int,           # Min searches for level
    "max_iterations": int,                  # Max iterations allowed
}
```

## Implementation Status

### ✅ Phase 1 Complete (Week 1-2)

- [x] State schema with accumulators and quality tracking
- [x] 6-tier effort level configuration system
- [x] Base agent with planning, research, analysis, writing nodes
- [x] Conditional routing based on search count and quality
- [x] PostgreSQL checkpoint integration
- [x] Action history trimming (keep last 5)
- [x] HITL approval workflow foundation
- [x] Example usage scripts

### 🚧 Next: Phase 2 (Week 2-3)

- [ ] Search count tracking middleware with hooks
- [ ] PostgreSQL schema for search analytics
- [ ] Real-time progress updates via WebSocket
- [ ] Enforce minimum search requirements in routing logic
- [ ] Quality threshold calculations

### 📋 Future Phases

**Phase 3 (Week 3-4)**: Context Management
- Knowledge graph integration with LLMGraphTransformer
- ChromaDB vector database with auto-indexing
- LangMem context summarization
- Document processing pipeline

**Phase 4 (Week 4-5)**: Loop Detection
- Semantic similarity checking for duplicate queries
- Next-best-action recommendation tool
- Automatic query diversification
- Recovery mechanisms

**Phase 5 (Week 5-6)**: Enhanced HITL
- User question/approval tools
- Planning mode visualization
- Feedback collection
- Supervisor communication

**Phase 6 (Week 6-8)**: Frontend Integration
- CopilotKit setup
- Custom visualization components
- Real-time state sync
- Citation network display

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your_anthropic_key
TAVILY_API_KEY=your_tavily_key

# Optional
LANGSMITH_API_KEY=your_langsmith_key  # For observability
POSTGRES_CONNECTION_STRING=postgresql://...  # For checkpointing
```

### Effort Level Customization

Edit `effort_config.py` to customize effort levels:

```python
EFFORT_CONFIGS[EffortLevel.CUSTOM] = EffortConfig(
    name="custom",
    min_searches=75,
    max_iterations=10,
    depth="custom_depth",
    use_knowledge_graph=True,
    use_vector_rag=True,
    enable_advanced_summarization=True,
    max_tokens_per_search=7000,
    parallel_searches=5,
    quality_threshold=0.78,
    enable_loop_detection=True,
)
```

## Integration Points

### FastAPI Endpoint Example

```python
from fastapi import FastAPI
from agents.deep_research import create_deep_research_agent, create_initial_state

app = FastAPI()

@app.post("/research")
async def start_research(query: str, effort_level: str = "standard"):
    agent = create_deep_research_agent(checkpointer=checkpointer)
    state = create_initial_state(query, effort_level, session_id=uuid.uuid4())

    results = []
    async for event in agent.astream(state, config):
        results.append(event)

    return {"report": results[-1]["final_report"]}
```

### WebSocket Streaming

```python
@app.websocket("/ws/research/{session_id}")
async def research_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    agent = create_deep_research_agent(checkpointer)
    # Stream events to websocket
    async for event in agent.astream(state, config, stream_mode="values"):
        await websocket.send_json({
            "phase": event["phase"],
            "search_count": event["search_count"],
            "progress": event["search_count"] / event["min_searches_required"],
        })
```

## Performance Considerations

### Token Usage

- **Quick**: ~10-20K tokens
- **Standard**: ~50-100K tokens
- **Thorough**: ~200-300K tokens
- **Deep**: ~500-800K tokens
- **Extended**: ~1.5-2M tokens
- **Ultrathink**: ~4-6M tokens

### Latency

- Search latency: ~1-2s per search
- Analysis: ~3-5s per iteration
- Writing: ~10-15s for final report

### Memory

- State size: ~1-5MB depending on search count
- Action history: Trimmed to last 5 + essential findings
- Checkpointing: Full state persisted to PostgreSQL

## Observability

Integration with LangSmith provides:
- Full trace of agent execution
- Tool call tracking
- Token usage monitoring
- Performance metrics
- Error tracking

Access traces at: https://smith.langchain.com

## Next Steps

1. **Test the basic agent**: Run `example_usage.py` to verify setup
2. **Implement middleware**: Add search tracking hooks (Phase 2)
3. **Add knowledge graph**: Integrate Neo4j/Memgraph (Phase 3)
4. **Build frontend**: CopilotKit UI components (Phase 6)

## Documentation

- [Deep Research Effort Levels & Tracking](../../workspace/deep_research_effort_levels_tracking.md)
- [Context Management Strategy](../../workspace/deep_research_context_management.md)
- [Loop Prevention Mechanisms](../../workspace/deep_research_loop_prevention.md)
- [HITL Interaction Patterns](../../workspace/deep_research_hitl_interactions.md)
- [DeepAgents Framework Analysis](../../workspace/deepagents_framework_analysis.md)
- [CopilotKit & AG-UI Research](../../../frontend/workspace/copilotkit_ag_ui_research.md)

## Contributing

When adding new features:
1. Update state schema in `state.py` if needed
2. Add configuration to `effort_config.py` for feature flags
3. Create new nodes or tools as separate modules
4. Update this README with usage examples
5. Add tests in `tests/` directory

## License

Part of the DeepAgent Research Canvas project.
