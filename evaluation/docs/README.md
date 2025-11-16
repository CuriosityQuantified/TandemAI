# LangGraph Delegation Pattern Test Configs

This directory contains standalone test configurations for evaluating different multi-agent delegation patterns with LangGraph.

## Purpose

Compare and evaluate different approaches to agent delegation:
1. **Command.goto routing** - Dynamic routing via Command objects
2. **Conditional edge routing** - Static graph structure with conditional edges
3. **DeepAgent patterns** - Full DeepAgent implementation
4. **Hybrid approaches** - Combinations of the above

## Test Configurations

### CONFIG 1: DeepAgent Supervisor + Command.goto ✅ PASSED
- **File**: `test_config_1_deepagent_supervisor_command.py`
- **Pattern**: DeepAgent-inspired supervisor with Command.goto delegation
- **Subagents**: ReAct researcher with Tavily search
- **Status**: ✅ All tests passing
- **Summary**: `CONFIG_1_SUMMARY.md`

### CONFIG 2: Coming Soon
- Conditional edge routing pattern
- Static graph structure with router node

### CONFIG 3: Coming Soon
- Full DeepAgent with subagent spawning
- Native deepagents library patterns

## Running Tests

All tests are standalone and can be run independently:

```bash
# From backend directory
cd /Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2/module-2-2-frontend-enhanced/backend

# Activate virtual environment
source /Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/.venv/bin/activate

# Run specific config
python test_configs/test_config_1_deepagent_supervisor_command.py
```

## Test Structure

Each test file includes:

1. **Configuration Overview** - Architecture and pattern description
2. **Research Sources** - Documentation links for the pattern
3. **Implementation** - Complete working code
4. **Graph Construction** - StateGraph setup with proper routing
5. **Test Function** - Validation with detailed logging
6. **Success Criteria** - Clear pass/fail indicators

## Success Criteria

All tests validate:
- ✅ Delegation tool execution
- ✅ Subagent routing correct
- ✅ Tool execution by subagent
- ✅ Final response generation
- ✅ Message flow integrity

## Common Dependencies

- `langgraph >= 0.3` (Command.goto support)
- `langchain-anthropic` (Claude models)
- `langchain-tavily` (web search)
- `langchain-core` (tools, messages)
- `python-dotenv` (environment variables)

## Environment Setup

Required environment variables (in `.env`):
```bash
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
```

## Model Configuration

All tests use:
- **Model**: Anthropic Claude Haiku 4.5 (`claude-3-5-haiku-20241022`)
- **Temperature**: 0.7 (supervisor), 0.0 (researcher)
- **Checkpointer**: MemorySaver for conversation state

## Comparison Metrics

Each config will be evaluated on:

1. **Routing Correctness** - Does delegation work as intended?
2. **Code Complexity** - Lines of code, maintainability
3. **Flexibility** - Easy to add new subagents?
4. **Debugging** - Clear error messages and traces?
5. **Performance** - Execution speed, token usage
6. **LangGraph Studio** - Visualization quality

## Directory Structure

```
test_configs/
├── README.md                                      # This file
├── test_config_1_deepagent_supervisor_command.py  # CONFIG 1
├── CONFIG_1_SUMMARY.md                            # CONFIG 1 results
├── test_config_2_conditional_edge.py              # Coming soon
└── test_config_3_full_deepagent.py                # Coming soon
```

## Contributing New Configs

When adding a new test config:

1. Create standalone file: `test_config_N_description.py`
2. Include full documentation header
3. Implement all components (tools, nodes, graph)
4. Add comprehensive test function with logging
5. Run and validate all success criteria
6. Create summary document: `CONFIG_N_SUMMARY.md`
7. Update this README

## Notes

- All tests are self-contained (no external imports from main project)
- Each test includes its own tool definitions
- Tests use production APIs (Tavily, Anthropic) - costs apply
- Test queries are designed to validate routing, not produce production outputs

---

**Last Updated**: November 12, 2025
**Configs**: 1 (3 planned)
**Status**: Active development
