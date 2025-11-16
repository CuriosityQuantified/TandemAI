# CLAUDE.md - TandemAI Project

This file provides guidance to Claude Code when working with the TandemAI codebase.

**Last Updated**: 2025-11-15 (After Major Reorganization)

---

## 📁 Project Overview

**TandemAI** is an AI-powered research assistant with evaluation framework featuring:
- **Backend**: FastAPI + LangGraph + Multi-Provider LLM Support (Anthropic, OpenAI, Google, Groq)
- **Frontend**: Next.js 14 + React + TypeScript (under development)
- **Evaluation**: Comprehensive judge-based evaluation system with 7 specialized judges
- **Features**: Multi-agent workflows, human-in-the-loop approval, research planning, experiment tracking

---

## 🚨 CRITICAL: Recent Reorganization (November 2025)

**The project underwent major reorganization**. Directory structure changed from nested `main/TandemAI/backend/` to flat `backend/`.

**Key Changes**:
1. **Flat Structure**: Eliminated nested `main/TandemAI/` directory
2. **Consolidated .env**: Single `.env` file at project root
3. **Unified Backend**: All backend code in `/backend/`
4. **Evaluation Framework**: Moved to `/evaluation/`
5. **Archive**: Old `main/` directory archived to `/archive/`
6. **Documentation**: Organized in `/docs/` with categorized subdirectories

**Important Documentation**:
- `docs/PHASE_5_PATH_UPDATES_COMPLETE.md` - Complete reorganization summary
- `docs/PHASE_5_PATH_UPDATES_SUMMARY.md` - Path fix requirements
- `docs/path_updates/` - Detailed scan reports (temporary, excluded from git)

---

## 📍 Directory Structure (Post-Reorganization)

```
TandemAI/
├── .env                        # Consolidated environment configuration
├── .venv/                      # Python virtual environment
├── backend/                    # FastAPI backend
│   ├── core_agent.py          # Main agent (was module_2_2_simple.py)
│   ├── prompts/               # Agent prompts
│   │   └── prompts/           # Double-nested structure
│   │       └── researcher/
│   ├── subagents/             # Specialized sub-agents
│   ├── test_configs/          # Agent configuration tests
│   └── utils/                 # Backend utilities
├── evaluation/                # Evaluation framework
│   ├── judge_agents.py        # 7 specialized judge agents
│   ├── rubrics.py             # Evaluation criteria
│   ├── test_runner.py         # Test execution
│   ├── baseline_agent_wrapper.py  # Agent wrapper
│   └── experiments/           # Experiment outputs (gitignored)
├── frontend/                  # Next.js frontend
├── tests/                     # Integration tests
├── docs/                      # Project documentation
│   ├── reorganization/        # Reorganization docs
│   ├── architecture/          # Architecture docs
│   └── setup/                 # Setup guides
├── logs/                      # Log files (gitignored)
├── archive/                   # Archived old code (gitignored)
├── deepagents/                # Third-party LangGraph repo (gitignored)
└── scripts/                   # Utility scripts
```

---

## ⚠️ CRITICAL: Python Import Patterns

**ALWAYS use absolute imports with `backend.` prefix:**

```python
# ✅ CORRECT - After reorganization
from backend.prompts.prompts.researcher.benchmark_researcher_prompt import get_researcher_prompt
from backend.utils.date_helper import get_current_date
from backend.subagents.researcher import create_researcher_agent

# ❌ WRONG - Old pattern (will fail)
from prompts.researcher.benchmark_researcher_prompt import get_researcher_prompt
from utils.date_helper import get_current_date
```

**Note**: The prompts directory has a double-nested structure: `backend/prompts/prompts/researcher/`

---

## 🔧 Environment Configuration

### Environment File Location

**Root .env file**: `/Users/nicholaspate/Documents/01_Active/TandemAI/.env`

**Loading .env in code**:

```python
from pathlib import Path
from dotenv import load_dotenv

# From backend/test_configs/ (3 levels up to root)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# From evaluation/ (2 levels up to root)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# From backend/ (2 levels up to root)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)
```

### sys.path Configuration

**Add root directory to Python path**:

```python
import sys
from pathlib import Path

# From backend/test_configs/ (3 levels up)
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

# From evaluation/ (2 levels up)
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))
```

---

## 🐍 Virtual Environment Usage

**Location**: `/Users/nicholaspate/Documents/01_Active/TandemAI/.venv`

**ALWAYS activate before running Python commands**:

```bash
# Activate virtual environment
source .venv/bin/activate

# Verify activation
which python
# Should show: /Users/nicholaspate/Documents/01_Active/TandemAI/.venv/bin/python

# Install packages (use uv, not pip)
uv pip install package-name

# Run Python scripts
python script.py
```

**Claude Code bash commands MUST include activation**:

```bash
# ✅ CORRECT
source .venv/bin/activate && python backend/core_agent.py

# ❌ WRONG (uses system Python)
python backend/core_agent.py
```

---

## 🔑 API Keys & Configuration

**All keys stored in root `.env` file**:

```bash
# Core LLM Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
GOOGLE_API_KEY=AIza...
GROQ_API_KEY=gsk_...

# Specialized Services
TAVILY_API_KEY=tvly-...        # Web search
FIRECRAWL_API_KEY=fc-...       # Web scraping
LETTA_API_KEY=sk-let-...       # Agent memory
LANGSMITH_API_KEY=lsv2_...     # LangChain tracing
E2B_API_KEY=e2b_...            # Code execution

# Local Services
JUDGE_MODEL=qwen3-vl:2b        # Ollama model for judges
OLLAMA_HOST=http://localhost:11434

# Backend Configuration
JWT_SECRET_KEY=...
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,...
POSTGRES_URI=postgresql://localhost:5432/langgraph_checkpoints
```

---

## 🧪 Testing & Evaluation

### Running Test Configurations

```bash
# Activate environment first
source .venv/bin/activate

# Run specific test config
python backend/test_configs/test_config_1_deepagent_supervisor_command.py

# Run evaluation framework
python evaluation/test_runner.py
```

### Judge Agents

**7 Specialized Judges** in `evaluation/judge_agents.py`:
1. Accuracy Judge
2. Completeness Judge
3. Relevance Judge
4. Clarity Judge
5. Depth Judge
6. Coherence Judge
7. Actionability Judge

**Judge Model**: Uses local Ollama (`qwen3-vl:2b`) for cost-effective evaluation

---

## 🚀 Running the Application

### Backend Development

```bash
# Activate environment
source .venv/bin/activate

# Run FastAPI backend (if applicable)
cd backend && uvicorn main:app --reload --port 8000
```

### Frontend Development

```bash
# Install dependencies
cd frontend && npm install

# Run development server
npm run dev
```

### Local Services

```bash
# Start Ollama (for judge agents)
ollama serve

# Verify Ollama model
ollama list | grep qwen3-vl
```

---

## 📦 Dependencies

### Python (backend/requirements.txt)

**Core Dependencies**:
- FastAPI, uvicorn (API server)
- LangChain, LangGraph (agent framework)
- anthropic, openai, google-generativeai, groq (LLM providers)
- langchain-ollama (local models)
- psycopg2-binary (PostgreSQL)
- python-dotenv (environment variables)

**Installation**:

```bash
source .venv/bin/activate
uv pip install -r backend/requirements.txt
```

### Node.js (frontend/package.json)

**Core Dependencies**:
- Next.js 14, React 18
- TypeScript
- Tailwind CSS

**Installation**:

```bash
cd frontend
npm install
```

---

## 🔍 Common File Locations

### Backend Files

| Purpose | Location |
|---------|----------|
| Main agent | `backend/core_agent.py` |
| Test configs | `backend/test_configs/test_config_*.py` |
| Researcher prompt | `backend/prompts/prompts/researcher/benchmark_researcher_prompt.py` |
| Sub-agents | `backend/subagents/*.py` |
| Date utilities | `backend/utils/date_helper.py` |

### Evaluation Files

| Purpose | Location |
|---------|----------|
| Judge agents | `evaluation/judge_agents.py` |
| Rubrics | `evaluation/rubrics.py` |
| Test runner | `evaluation/test_runner.py` |
| Agent wrapper | `evaluation/baseline_agent_wrapper.py` |
| Experiments | `evaluation/experiments/` (gitignored) |

---

## 🛠️ Development Workflow

### Adding New Features

1. **Check existing patterns** in codebase
2. **Use absolute imports** with `backend.` prefix
3. **Load .env correctly** based on file location
4. **Add to sys.path** if needed (root directory)
5. **Test imports** before committing
6. **Update documentation** as needed

### Debugging Import Errors

```bash
# Verify Python path
source .venv/bin/activate && python -c "import sys; print('\n'.join(sys.path))"

# Test specific import
source .venv/bin/activate && python -c "from backend.prompts.prompts.researcher.benchmark_researcher_prompt import get_researcher_prompt; print('SUCCESS')"

# Check .env loading
source .venv/bin/activate && python -c "from pathlib import Path; from dotenv import load_dotenv; import os; load_dotenv(Path.cwd() / '.env'); print(f'JUDGE_MODEL={os.getenv(\"JUDGE_MODEL\")}')"
```

---

## 📝 Git Workflow

### Ignored Patterns (see .gitignore)

**Development artifacts**:
- `.venv/`, `__pycache__/`, `*.pyc`
- `node_modules/`, `.next/`
- `*.log`, `logs/`

**Project-specific**:
- `archive/` - Old code from reorganization
- `deepagents/` - Third-party LangGraph repo
- `main/` - Legacy directory (archived)
- `.claude/` - Claude Code session data
- `docs/path_updates/` - Temporary scan reports
- `evaluation/experiments/*/results/` - Experiment outputs

### Committing Changes

```bash
# Check status
git status

# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: Add new evaluation judge for citation accuracy"

# Push to remote
git push origin main
```

---

## 🐛 Troubleshooting

### Import Errors

**Problem**: `No module named 'backend.prompts'`

**Solution**:
```python
# Add root to sys.path
import sys
from pathlib import Path
root_path = Path(__file__).parent.parent.parent  # Adjust levels as needed
sys.path.insert(0, str(root_path))
```

### .env Loading Errors

**Problem**: Environment variables not loading

**Solution**:
```python
# Verify .env path exists
from pathlib import Path
env_path = Path(__file__).parent.parent.parent / ".env"  # Adjust levels
print(f"Loading .env from: {env_path}")
print(f"Exists: {env_path.exists()}")
```

### Virtual Environment Issues

**Problem**: Wrong Python version or packages not found

**Solution**:
```bash
# Verify venv activation
which python
# Should show: /Users/nicholaspate/Documents/01_Active/TandemAI/.venv/bin/python

# If wrong, activate explicitly
source /Users/nicholaspate/Documents/01_Active/TandemAI/.venv/bin/activate

# Verify packages
uv pip list | grep langchain
```

---

## 📚 Documentation

### Key Documentation Files

| Document | Purpose |
|----------|---------|
| `docs/PHASE_5_PATH_UPDATES_COMPLETE.md` | Reorganization completion summary |
| `docs/PHASE_5_PATH_UPDATES_SUMMARY.md` | Path fix requirements |
| `docs/reorganization/` | Reorganization planning and execution |
| `docs/setup/` | Setup and installation guides |
| `docs/architecture/` | System architecture documentation |

### Documentation Standards

- Keep documentation in sync with code
- Document all major changes
- Include code examples
- Use clear, concise language
- Update this CLAUDE.md when structure changes

---

## 🎯 Quick Reference

### Essential Commands

```bash
# Activate environment
source .venv/bin/activate

# Run test config
python backend/test_configs/test_config_1_deepagent_supervisor_command.py

# Run evaluation
python evaluation/test_runner.py

# Install dependencies
uv pip install -r backend/requirements.txt

# Frontend dev server
cd frontend && npm run dev

# Check Ollama status
curl http://localhost:11434/api/tags
```

### Essential Imports

```python
# Agent framework
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END, START

# LLM providers
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

# TandemAI backend
from backend.prompts.prompts.researcher.benchmark_researcher_prompt import get_researcher_prompt
from backend.utils.date_helper import get_current_date
from evaluation.judge_agents import JudgeRegistry
from evaluation.rubrics import get_rubric_summary
```

---

## 🔗 External Resources

- **LangChain Docs**: https://python.langchain.com/docs/
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Next.js Docs**: https://nextjs.org/docs
- **Ollama Models**: https://ollama.com/library

---

## 👤 Project Maintainer

**GitHub**: CuriosityQuantified
**Email**: CuriosityQuantified@gmail.com

---

**Remember**: This project uses absolute imports (`from backend.*`), loads `.env` from root, and has a flat directory structure after November 2025 reorganization.
