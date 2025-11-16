# TandemAI

> Multi-Agent AI Evaluation Framework with LangChain and LangGraph

## Overview

TandemAI is a comprehensive multi-agent AI system built for evaluating and benchmarking LLM-based research agents. The framework provides:

- **Multi-Agent Orchestration**: Hierarchical agent architecture with supervisor and specialized worker agents
- **Comprehensive Evaluation**: Built-in judge agents for quality assessment across multiple dimensions
- **Research Capabilities**: Deep integration with Tavily, Firecrawl, and GitHub for advanced research tasks
- **Flexible Configuration**: Multiple test configurations for different agent architectures and workflows
- **MLflow Integration**: Complete observability and tracking for all agent interactions

## Key Features

- 🤖 **Multiple Agent Architectures**: DeepAgent, ReAct, Multi-Agent Supervisor, Hierarchical Teams
- 📊 **Comprehensive Evaluation Framework**: 7 judge agents evaluating across 21 dimensions
- 🔍 **Research Tools**: Web search (Tavily), web scraping (Firecrawl), code analysis (GitHub)
- 📈 **MLflow Tracking**: Complete observability with experiment tracking and model comparison
- ⚙️ **Flexible Configuration**: 8+ test configurations for different use cases
- 🎯 **Quality Metrics**: Automated evaluation of factual accuracy, completeness, clarity, and more

## Repository Structure

```
TandemAI/
├── backend/                    # Backend agents and orchestration
│   ├── core_agent.py          # Main agent (Module 2.2 - Single DeepAgent)
│   ├── delegation_tools.py    # Tools for delegating to subagents
│   ├── websocket_manager.py   # WebSocket communication
│   ├── subagents/             # Specialized worker agents
│   │   ├── researcher.py
│   │   ├── data_scientist.py
│   │   ├── writer.py
│   │   ├── reviewer.py
│   │   └── expert_analyst.py
│   ├── prompts/               # Agent system prompts
│   │   └── prompts/           # Categorized prompts
│   └── test_configs/          # Test configurations for different architectures
│       ├── test_config_1_deepagent_supervisor_command.py
│       ├── test_config_2_deepagent_supervisor_conditional.py
│       ├── test_config_3_react_supervisor_command.py
│       ├── test_config_4_react_supervisor_conditional.py
│       ├── test_config_5_react_supervisor_handoffs.py
│       ├── test_config_7_multi_agent_supervisor.py
│       └── test_config_8_hierarchical_teams.py
│
├── evaluation/                 # Evaluation framework
│   ├── baseline_agent_wrapper.py  # Wraps agents for evaluation
│   ├── judge_agents.py        # 7 judge agents for quality assessment
│   ├── rubrics.py             # Evaluation rubrics and scoring
│   ├── test_runner.py         # Orchestrates evaluation runs
│   └── experiments/           # Evaluation experiments and results
│       └── baselines/         # Baseline experiment results
│
├── docs/                       # Documentation
│   ├── setup/                 # Setup and installation guides
│   ├── architecture/          # Architecture documentation
│   ├── guides/                # Development and usage guides
│   └── path_updates/          # Reorganization documentation
│
├── .env                        # Environment configuration (root)
├── .gitignore                 # Git ignore patterns
├── CLAUDE.md                  # AI assistant guidance
└── README.md                  # This file
```

## Prerequisites

### Required Software

- **Python**: 3.10 or higher
- **Node.js**: 16.x or higher (for frontend, if applicable)
- **PostgreSQL**: 15.x or higher (optional, for advanced features)
- **Ollama**: Latest version (for local judge models)

### API Keys

The following API keys are required (configured in `.env`):

- **Anthropic API Key**: For Claude models
- **OpenAI API Key**: For GPT models
- **Google API Key**: For Gemini models
- **Groq API Key**: For fast inference
- **Tavily API Key**: For web search
- **Firecrawl API Key**: For web scraping (optional)
- **GitHub API Key**: For code analysis (optional)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/CuriosityQuantified/TandemAI.git
cd TandemAI
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate  # On Windows
```

### 3. Install Dependencies

```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# For frontend (if applicable)
cd frontend && npm install
```

### 4. Configure Environment

Copy the example environment file and configure your API keys:

```bash
# The .env file should already exist at the root
# Edit it to add your API keys
nano .env  # or use your preferred editor
```

**Required environment variables:**

```env
# API Keys - Core Services
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here
GROQ_API_KEY=your_groq_key_here
TAVILY_API_KEY=your_tavily_key_here

# API Keys - Optional Services
FIRECRAWL_API_KEY=your_firecrawl_key_here
GITHUB_API_KEY=your_github_key_here

# Judge Model Configuration (Local Ollama)
JUDGE_MODEL=qwen3-vl:2b
OLLAMA_HOST=http://localhost:11434
```

### 5. Set Up Ollama (For Judge Models)

```bash
# Install Ollama (if not already installed)
# Visit: https://ollama.ai

# Pull the judge model
ollama pull qwen3-vl:2b

# Verify Ollama is running
curl http://localhost:11434/api/version
```

## Running the System

### Backend API Server

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the backend API server (FastAPI + Agent)
python backend/backend_main.py
```

**Note**: `backend_main.py` is the primary backend entry point. It runs a FastAPI server that exposes the TandemAI agent via HTTP/WebSocket endpoints.

### Test Configurations

Run specific test configurations:

```bash
# Example: DeepAgent with Supervisor Command
python backend/test_configs/test_config_1_deepagent_supervisor_command.py

# Example: ReAct with Supervisor Conditional
python backend/test_configs/test_config_4_react_supervisor_conditional.py

# Example: Hierarchical Teams
python backend/test_configs/test_config_8_hierarchical_teams.py
```

### Evaluation Framework

Run evaluation benchmarks:

```bash
# Run baseline evaluation
python evaluation/test_runner.py
```

## Development Workflow

### Import Pattern (Post-Reorganization)

All imports within the `backend/` directory must use the `backend.` prefix:

```python
# ✅ CORRECT
from backend.delegation_tools import delegate_to_researcher
from backend.subagents import create_researcher_subagent
from backend.websocket_manager import manager

# ❌ INCORRECT (will cause ModuleNotFoundError)
from delegation_tools import delegate_to_researcher
from subagents import create_researcher_subagent
from websocket_manager import manager
```

### Environment Loading

The `.env` file is located at the project root. Load it with:

```python
from pathlib import Path
from dotenv import load_dotenv

# From backend/test_configs/ directory (3 levels up to root)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)
```

### Adding New Agents

1. Create agent file in `backend/subagents/`
2. Define agent creation function
3. Add delegation tool in `backend/delegation_tools.py`
4. Update imports in `backend/core_agent.py`
5. Update documentation

## Architecture

### Agent Hierarchy

```
Global Supervisor Agent
├── Research Team
│   ├── Researcher Agent (Tavily search)
│   └── Data Scientist Agent (analysis)
├── Analysis Team
│   └── Expert Analyst Agent (domain expertise)
└── Writing Team
    ├── Writer Agent (content generation)
    └── Reviewer Agent (quality control)
```

### Technology Stack

- **Backend Framework**: LangChain + LangGraph
- **Primary Model**: Claude 3.5 Sonnet (Anthropic)
- **Research Tools**: Tavily (search), Firecrawl (scraping)
- **Evaluation**: 7 specialized judge agents
- **Observability**: MLflow for tracking and monitoring
- **Communication**: WebSocket for real-time updates

### Test Configurations

| Config | Architecture | Delegation | Use Case |
|--------|-------------|------------|----------|
| Config 1 | DeepAgent | Supervisor Command | Simple tasks with clear delegation |
| Config 2 | DeepAgent | Supervisor Conditional | Conditional delegation based on task |
| Config 3 | ReAct | Supervisor Command | Reasoning + Acting with explicit delegation |
| Config 4 | ReAct | Supervisor Conditional | ReAct with dynamic delegation |
| Config 5 | ReAct | Supervisor Handoffs | Sequential agent handoffs |
| Config 7 | Multi-Agent | Supervisor | Parallel multi-agent coordination |
| Config 8 | Hierarchical | Teams | Hierarchical team structures |

## Evaluation Framework

### Judge Agents

TandemAI includes 7 specialized judge agents:

1. **Factual Accuracy Judge**: Evaluates factual correctness
2. **Completeness Judge**: Assesses coverage and thoroughness
3. **Clarity Judge**: Evaluates communication clarity
4. **Source Quality Judge**: Assesses source reliability
5. **Relevance Judge**: Checks relevance to query
6. **Depth Judge**: Evaluates analysis depth
7. **Actionability Judge**: Assesses practical utility

### Evaluation Dimensions

Each judge evaluates responses across 3 dimensions:
- **Binary Score**: Pass/Fail assessment
- **Scaled Score**: 1-10 rating
- **Qualitative Feedback**: Detailed reasoning

## Recent Reorganization (November 2025)

TandemAI underwent a comprehensive reorganization to flatten the directory structure and improve maintainability.

### Key Changes

1. **Flattened Structure**: Moved from nested `main/TandemAI/backend/` to flat `backend/`
2. **Consolidated Environment**: Single `.env` file at project root
3. **Updated Imports**: All imports use `backend.` prefix for consistency
4. **Fixed Path References**: Updated 27 files with correct import paths
5. **Archived Legacy Code**: Moved `main/` directory for future archival

### Documentation

Comprehensive reorganization documentation available in:
- `docs/PHASE_5_PATH_UPDATES_COMPLETE.md` - Complete reorganization summary
- `docs/PHASE_5_PATH_UPDATES_SUMMARY.md` - Original analysis
- `docs/path_updates/` - Detailed scan reports

## Documentation

### Core Documentation

- **CLAUDE.md**: AI assistant guidance and project context
- **docs/setup/**: Installation and setup guides
- **docs/architecture/**: Architecture and design documentation
- **docs/guides/**: Development and usage guides

### API Documentation

- Backend agents and tools documented in-code
- Configuration patterns in test configs
- Evaluation framework in `evaluation/`

## Contributing

### Development Guidelines

1. **Follow Import Patterns**: Always use `backend.` prefix for backend imports
2. **Update Documentation**: Keep docs in sync with code changes
3. **Test Thoroughly**: Run relevant test configurations
4. **Environment Variables**: Never commit `.env` files

### Code Style

- Python: Follow PEP 8 guidelines
- Type hints: Use for all function signatures
- Docstrings: Required for all public functions and classes

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Error: ModuleNotFoundError: No module named 'delegation_tools'
# Fix: Update import to use backend. prefix
from backend.delegation_tools import ...
```

**Environment Loading:**
```bash
# Error: API keys not found
# Fix: Ensure .env is at project root and loaded correctly
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)
```

**Ollama Connection:**
```bash
# Error: Cannot connect to Ollama
# Fix: Verify Ollama is running
curl http://localhost:11434/api/version
```

## License

[Specify license here]

## Contact

- **Repository**: https://github.com/CuriosityQuantified/TandemAI
- **Email**: CuriosityQuantified@gmail.com

## Acknowledgments

- LangChain and LangGraph teams for the framework
- Anthropic for Claude models
- DeepAgents for inspiration on multi-agent architectures

---

**Last Updated**: November 2025
**Version**: Post-Reorganization (Phase 7 Complete)
**Status**: Active Development
