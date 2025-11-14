# LangChain Native Model Integrations

**Research Date**: November 14, 2025
**Purpose**: Document LangChain v1.0+ built-in integrations for Google Gemini and Groq to avoid separate SDKs

---

## ✅ Google Gemini Integration

### Package Information
- **Package Name**: `langchain-google-genai`
- **Latest Version**: 3.0.3 (Released: November 12, 2025)
- **Python Requirements**: >=3.10.0, <4.0.0
- **License**: MIT

### Installation
```bash
pip install langchain-google-genai
```

### Basic Usage
```python
from langchain_google_genai import ChatGoogleGenerativeAI

# Initialize model
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
    google_api_key="YOUR_GOOGLE_API_KEY"  # or set GOOGLE_API_KEY env var
)

# Use with LangGraph
from langgraph.graph import StateGraph
# model can be used directly in LangGraph nodes
```

### Supported Models (2025)
- `gemini-2.5-pro` - Latest flagship model
- `gemini-2.5-flash` - Fast, efficient model ($0.30/$2.50 per MTok)
- `gemini-2.0-flash` - Previous generation flash model
- `gemini-2.5-flash-preview-tts` - Audio generation model

### Key Features
- ✅ Chat completion
- ✅ Vision capabilities
- ✅ Embeddings
- ✅ Audio generation
- ✅ Structured output (JSON schema)
- ✅ Native streaming support
- ✅ Batch processing
- ✅ LangGraph compatible

### Documentation Links
- **API Reference**: https://reference.langchain.com/python/integrations/langchain_google_genai/
- **PyPI**: https://pypi.org/project/langchain-google-genai/
- **GitHub**: https://github.com/langchain-ai/langchain-google
- **Changelog**: https://github.com/langchain-ai/langchain-google/releases?q=%22genai%22

---

## ✅ Groq Integration

### Package Information
- **Package Name**: `langchain-groq`
- **Latest Version**: 1.0.1 (Released: November 13, 2025)
- **Python Requirements**: >=3.10.0, <4.0.0
- **License**: MIT

### Installation
```bash
pip install langchain-groq
```

### Basic Usage
```python
from langchain_groq import ChatGroq

# Initialize model
model = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.7,
    groq_api_key="YOUR_GROQ_API_KEY"  # or set GROQ_API_KEY env var
)

# Use with LangGraph
from langgraph.graph import StateGraph
# model can be used directly in LangGraph nodes
```

### Supported Models
- `llama-3.3-70b-versatile` - Latest Llama model
- `mixtral-8x7b-32768` - Mixture of Experts model
- `deepseek-r1-distill-llama-70b` - DeepSeek R1 distilled
- `kimi-k2-thinking` - Kimi K2-thinking model ($0.60/$2.50 per MTok)

### Key Features
- ✅ Chat completion
- ✅ Standard Runnable Interface
- ✅ Native streaming support
- ✅ Batch processing
- ✅ LangGraph compatible
- ✅ Fast inference via Groq LPU technology
- ✅ Methods: `with_types`, `with_retry`, `assign`, `bind`, `get_graph`

### Documentation Links
- **API Reference**: https://reference.langchain.com/python/integrations/langchain_groq/
- **PyPI**: https://pypi.org/project/langchain-groq/
- **GitHub**: https://github.com/langchain-ai/langchain/tree/master/libs/partners/groq
- **Official Docs**: https://console.groq.com/docs/langchain

---

## 🔧 Implementation for TandemAI

### Current Status
Both integrations are **production-ready** and **actively maintained** with regular updates throughout 2024-2025.

### Integration Approach
Instead of using separate SDKs:
- ❌ `google-generativeai` (separate SDK)
- ❌ `groq` (separate SDK)

Use LangChain native integrations:
- ✅ `langchain-google-genai` (unified LangChain interface)
- ✅ `langchain-groq` (unified LangChain interface)

### Benefits
1. **Unified Interface**: Same API across all models
2. **LangGraph Compatible**: Direct integration with LangGraph workflows
3. **No SDK Conflicts**: Avoid version conflicts between separate SDKs
4. **Better Maintenance**: Official LangChain support and updates
5. **Streaming Support**: Built-in streaming for all models
6. **Type Safety**: Full Python type annotations

---

## 📊 Cost Comparison (from ESTIMATE_PHASE_6_COST.py)

| Model | Provider | Input $/MTok | Output $/MTok | Total Cost* |
|-------|----------|--------------|---------------|-------------|
| Claude 3.5 Haiku | Anthropic | $0.25 | $1.25 | $0.57 |
| Gemini 2.5 Flash | Google | $0.30 | $2.50 | $0.99 |
| Kimi K2-thinking | Groq | $0.60 | $2.50 | $1.36 |
| Claude 4.5 Haiku | Anthropic | $1.00 | $5.00 | $2.27 |

*For 32 queries × 7 judges = 224 evaluations with prompt caching

---

## 🚀 Next Steps

1. ✅ Research completed - both integrations confirmed
2. 🔄 Update VERIFY_MODEL_COSTS.py to use native integrations
3. ⏳ Install dependencies: `langchain-google-genai`, `langchain-groq`
4. ⏳ Test single-query verification with all 4 models
5. ⏳ Run full Phase 6 benchmark evaluation (224 judgments)

---

## 📝 Code Examples

### Anthropic (Claude)
```python
from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(
    model="claude-3-5-haiku-20241022",
    temperature=0.7
)
```

### Google (Gemini)
```python
from langchain_google_genai import ChatGoogleGenerativeAI

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7
)
```

### Groq (Multi-Model)
```python
from langchain_groq import ChatGroq

model = ChatGroq(
    model="kimi-k2-thinking",  # or llama-3.3-70b-versatile, mixtral-8x7b-32768
    temperature=0.7
)
```

### LangGraph Integration (All Models)
```python
from langgraph.graph import StateGraph, MessagesState
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

# Any of these can be used in LangGraph nodes
def create_node(model):
    def node(state: MessagesState):
        response = model.invoke(state["messages"])
        return {"messages": [response]}
    return node

# Build graph with any model
workflow = StateGraph(MessagesState)
workflow.add_node("agent", create_node(model))
graph = workflow.compile()
```

---

**Status**: ✅ CONFIRMED - Both integrations are official, actively maintained, and production-ready
