# LangChain v1.0 Advanced Features for ATLAS

**Document Focus**: Practical implementation patterns for ATLAS multi-agent system
**Last Updated**: 2025-01-03
**Status**: Research and recommendations

---

## 1. Multi-Agent Orchestration

### Two Core Patterns

**Tool Calling Pattern** (ATLAS Current Approach)
- Centralized supervisor calls sub-agents as tools
- Best for structured workflows with supervisor control
- Sub-agents don't interact directly with users

**Handoffs Pattern** (Future Enhancement)
- Decentralized agent-to-agent communication
- Allows direct user interaction with specialist agents
- More flexible conversation routing

### ATLAS Implementation: Supervisor + Tool-Based Sub-Agents

```python
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# Define sub-agent as callable tool
@tool(
    name="research_agent",
    description="Performs web research using Firecrawl. Use for gathering information, facts, and data from web sources."
)
def call_research_agent(query: str, max_results: int = 5) -> str:
    """
    Delegates research tasks to specialized research agent.

    Args:
        query: Research question or topic
        max_results: Maximum number of sources to retrieve

    Returns:
        Research findings with source citations
    """
    # Initialize research agent with Firecrawl tool
    research_agent = create_react_agent(
        model=call_model(model="anthropic/claude-3-5-sonnet"),
        tools=[firecrawl_search_tool],
        state_modifier="You are a research specialist. Focus on finding accurate, well-sourced information."
    )

    result = research_agent.invoke({
        "messages": [{"role": "user", "content": query}],
        "max_results": max_results
    })

    return result["messages"][-1].content


@tool(
    name="analysis_agent",
    description="Executes Python code in E2B sandbox. Use for data analysis, calculations, and code execution."
)
def call_analysis_agent(code: str, context: str = "") -> str:
    """
    Delegates code execution and analysis tasks.

    Args:
        code: Python code to execute
        context: Additional context about the analysis task

    Returns:
        Analysis results and execution output
    """
    analysis_agent = create_react_agent(
        model=call_model(model="openai/gpt-4o"),
        tools=[e2b_code_execution_tool],
        state_modifier="You are a data analyst. Execute code safely and interpret results clearly."
    )

    prompt = f"Context: {context}\n\nExecute this code:\n```python\n{code}\n```"
    result = analysis_agent.invoke({
        "messages": [{"role": "user", "content": prompt}]
    })

    return result["messages"][-1].content


# Supervisor agent with sub-agent tools
supervisor_tools = [
    call_research_agent,
    call_analysis_agent,
    call_writing_agent,
    plan_task_tool,
    create_todo_tool,
    save_output_tool
]

supervisor_agent = create_react_agent(
    model=call_model(model="openai/gpt-4o"),
    tools=supervisor_tools,
    state_modifier="""You are the ATLAS supervisor. You coordinate research, analysis, and writing tasks.

Your capabilities:
1. Research: Use call_research_agent for web searches and fact gathering
2. Analysis: Use call_analysis_agent for data processing and calculations
3. Writing: Use call_writing_agent for document generation
4. Planning: Use plan_task to decompose complex tasks
5. Tracking: Use create_todo to manage task progress
6. Storage: Use save_output to persist results

Always explain your reasoning and cite sources."""
)
```

### Key Design Patterns for ATLAS

**Context Engineering**
```python
# Each agent needs specialized context
RESEARCH_AGENT_CONTEXT = """You are a research specialist focusing on:
- Web searches using Firecrawl
- Source validation and citation
- Fact extraction and summarization
- Multi-source synthesis

Output format: Findings with [source_url] citations."""

ANALYSIS_AGENT_CONTEXT = """You are a data analyst focusing on:
- Python code execution in E2B sandbox
- Statistical analysis and visualization
- Data transformation and processing
- Result interpretation

Output format: Analysis summary + code + visualizations."""

WRITING_AGENT_CONTEXT = """You are a content writer focusing on:
- Document structure and formatting
- Clear, professional writing
- Integration of research and analysis
- Session-scoped file management

Output format: Polished documents with citations."""
```

**Parallel Execution Pattern**
```python
from langchain_core.runnables import RunnableParallel

# Execute multiple sub-agents concurrently
parallel_tasks = RunnableParallel(
    research=call_research_agent.bind(query="Market trends 2025"),
    analysis=call_analysis_agent.bind(code="analyze_data(df)", context="Financial analysis"),
    background=call_research_agent.bind(query="Industry background")
)

results = await parallel_tasks.ainvoke({})
# Returns: {"research": "...", "analysis": "...", "background": "..."}
```

---

## 2. Structured Output

### Pydantic Models for Tool Parameters

**ATLAS Tool Schema Example**
```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class TaskPlan(BaseModel):
    """Structured task decomposition output."""
    task_id: str = Field(description="Unique task identifier")
    task_type: Literal["research", "analysis", "writing"] = Field(
        description="Type of task to delegate"
    )
    description: str = Field(description="Clear task description")
    dependencies: list[str] = Field(
        default_factory=list,
        description="Task IDs that must complete first"
    )
    priority: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="Task priority level"
    )

class PlanningOutput(BaseModel):
    """Complete task planning output."""
    tasks: list[TaskPlan] = Field(description="Ordered list of tasks")
    execution_strategy: Literal["sequential", "parallel", "hybrid"] = Field(
        description="How tasks should be executed"
    )
    estimated_duration: Optional[int] = Field(
        None,
        description="Estimated completion time in minutes"
    )


# Use structured output in planning tool
@tool(response_format=PlanningOutput)
def plan_task(objective: str, constraints: Optional[str] = None) -> PlanningOutput:
    """
    Decomposes objective into structured task plan.
    Returns validated PlanningOutput with task graph.
    """
    planner_agent = create_react_agent(
        model=call_model(model="openai/gpt-4o"),
        tools=[],
        state_modifier="You are a task planning specialist. Create comprehensive, executable task plans."
    )

    prompt = f"Create task plan for: {objective}"
    if constraints:
        prompt += f"\n\nConstraints: {constraints}"

    result = planner_agent.invoke({
        "messages": [{"role": "user", "content": prompt}]
    })

    # LangChain automatically validates against PlanningOutput schema
    return result["structured_output"]
```

### Tool Call Validation

```python
from langchain_core.tools import StructuredTool

class ResearchParams(BaseModel):
    """Validated parameters for research tool."""
    query: str = Field(min_length=3, description="Search query")
    max_results: int = Field(default=5, ge=1, le=20, description="Number of results")
    search_depth: Literal["basic", "deep"] = Field(default="basic")
    include_sources: bool = Field(default=True)

research_tool = StructuredTool.from_function(
    func=perform_research,
    name="research",
    description="Execute web research with validated parameters",
    args_schema=ResearchParams  # Automatic validation
)
```

### Type-Safe Responses

```python
from typing import TypedDict

class AgentResponse(TypedDict):
    """Type-safe agent response structure."""
    content: str
    sources: list[str]
    confidence: float
    metadata: dict

# Agent with structured response
def create_typed_agent(model: str, tools: list) -> Runnable:
    """Creates agent with type-safe responses."""
    return create_react_agent(
        model=call_model(model=model),
        tools=tools,
        response_format=AgentResponse  # Enforces response structure
    )
```

---

## 3. Human-in-the-Loop

### Interrupt Pattern for ATLAS

**HITL Middleware Configuration**
```python
from langgraph.prebuilt import HumanInTheLoopMiddleware

# Configure interrupts for sensitive operations
hitl_config = HumanInTheLoopMiddleware(
    interrupt_on={
        # File operations - require approval
        "save_output": {"allow_accept": True, "allow_edit": True, "allow_respond": True},
        "append_content": {"allow_accept": True, "allow_edit": True, "allow_respond": True},

        # Code execution - require approval
        "call_analysis_agent": {"allow_accept": True, "allow_edit": True, "allow_respond": True},

        # Research - no interruption needed
        "call_research_agent": False,

        # Planning - no interruption needed
        "plan_task": False,
        "create_todo": False
    }
)
```

### ATLAS HITL Integration

```python
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres import PostgresSaver

# Create supervisor with HITL support
def create_supervisor_with_hitl():
    """Creates supervisor agent with human approval gates."""

    # PostgreSQL checkpointer for state persistence
    checkpointer = PostgresSaver.from_conn_string(
        conn_string="postgresql://atlas_user:password@localhost/atlas_agents"
    )

    # Build state graph
    graph = StateGraph(state_schema=SupervisorState)

    # Add nodes
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("research", call_research_agent)
    graph.add_node("analysis", call_analysis_agent)
    graph.add_node("writing", call_writing_agent)

    # Add edges with HITL middleware
    graph.add_edge("supervisor", "research")
    graph.add_edge("supervisor", "analysis")
    graph.add_edge("supervisor", "writing")

    # Compile with checkpointer and HITL
    return graph.compile(
        checkpointer=checkpointer,
        middleware=[hitl_config],
        interrupt_before=["analysis", "writing"]  # Additional interrupt points
    )


# Execute with HITL support
async def execute_with_approval(task: str, thread_id: str):
    """Execute task with human approval gates."""

    graph = create_supervisor_with_hitl()
    config = {"configurable": {"thread_id": thread_id}}

    # Initial invocation
    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": task}]},
        config=config
    )

    # Check for interrupts
    if result.get("interrupt"):
        interrupt = result["interrupt"]
        print(f"Approval required for: {interrupt['tool_name']}")
        print(f"Tool arguments: {interrupt['tool_args']}")

        # Wait for user response via AG-UI
        user_response = await wait_for_user_approval(thread_id)

        if user_response["action"] == "accept":
            # Continue execution
            result = await graph.ainvoke(None, config=config)

        elif user_response["action"] == "edit":
            # Modify tool arguments
            result = await graph.ainvoke(
                {"tool_args": user_response["modified_args"]},
                config=config
            )

        elif user_response["action"] == "reject":
            # Cancel execution
            return {"status": "cancelled", "reason": user_response["feedback"]}

    return result
```

### AG-UI Integration for Approvals

```python
from backend.src.agui.server import agui_server

async def wait_for_user_approval(thread_id: str) -> dict:
    """Waits for user approval via AG-UI."""

    # Broadcast approval request
    await agui_server.broadcast_event({
        "type": "user_approval_required",
        "thread_id": thread_id,
        "tool_name": "save_output",
        "tool_args": {"file_path": "/outputs/session_123/report.md"},
        "timestamp": datetime.now().isoformat()
    })

    # Wait for user response (WebSocket or API)
    response = await agui_server.wait_for_response(
        thread_id=thread_id,
        timeout=300  # 5 minutes
    )

    return {
        "action": response["action"],  # "accept", "edit", "reject"
        "modified_args": response.get("modified_args"),
        "feedback": response.get("feedback")
    }
```

---

## 4. Long-Term Memory

### ChromaDB Integration for ATLAS

**Vector Store Setup**
```python
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.stores import InMemoryStore

# Initialize ChromaDB for ATLAS
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vector_store = Chroma(
    collection_name="atlas_agent_memory",
    embedding_function=embeddings,
    persist_directory="/Users/nicholaspate/Documents/01_Active/ATLAS/data/chromadb"
)

# In-memory store for rapid access (development)
memory_store = InMemoryStore()
```

### Cross-Session Memory Patterns

**Namespace Organization**
```python
# Memory namespace structure for ATLAS
MEMORY_NAMESPACES = {
    "users": ("users",),  # User preferences and history
    "projects": ("projects",),  # Project-specific knowledge
    "agents": ("agents",),  # Agent learnings and patterns
    "domain": ("domain",)  # Domain-specific knowledge
}

# Store user preferences
memory_store.put(
    MEMORY_NAMESPACES["users"],
    "user_123",
    {
        "preferred_model": "anthropic/claude-3-5-sonnet",
        "writing_style": "professional",
        "citation_format": "APA",
        "research_depth": "deep"
    }
)

# Store project context
memory_store.put(
    MEMORY_NAMESPACES["projects"],
    "project_market_analysis",
    {
        "domain": "finance",
        "key_entities": ["Tesla", "EV market", "battery technology"],
        "research_sources": ["Bloomberg", "Reuters"],
        "analysis_methods": ["time_series", "regression"]
    }
)

# Store agent learnings
memory_store.put(
    MEMORY_NAMESPACES["agents"],
    "research_agent_patterns",
    {
        "successful_queries": ["market analysis 2025", "industry trends"],
        "failed_queries": ["too vague questions"],
        "optimization_notes": "Use specific date ranges for better results"
    }
)
```

### Semantic Memory Search

```python
from langchain_core.stores import VectorStoreRetriever

class ATLASMemoryManager:
    """Manages long-term memory with vector search."""

    def __init__(self, vector_store: Chroma, memory_store: InMemoryStore):
        self.vector_store = vector_store
        self.memory_store = memory_store
        self.retriever = VectorStoreRetriever(vectorstore=vector_store)

    async def store_conversation(
        self,
        session_id: str,
        messages: list[dict],
        metadata: dict
    ):
        """Stores conversation in vector store for semantic search."""
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}" for msg in messages
        ])

        await self.vector_store.aadd_texts(
            texts=[conversation_text],
            metadatas=[{
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                **metadata
            }]
        )

    async def recall_similar_conversations(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[dict] = None
    ) -> list[dict]:
        """Retrieves similar past conversations."""
        results = await self.retriever.aget_relevant_documents(
            query=query,
            k=k,
            filter=filter_metadata
        )

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity": doc.metadata.get("score", 0)
            }
            for doc in results
        ]

    def get_user_context(self, user_id: str) -> dict:
        """Retrieves user preferences from memory store."""
        return self.memory_store.get(
            MEMORY_NAMESPACES["users"],
            user_id
        )

    def get_project_context(self, project_id: str) -> dict:
        """Retrieves project context from memory store."""
        return self.memory_store.get(
            MEMORY_NAMESPACES["projects"],
            project_id
        )
```

### Memory-Augmented Agent Execution

```python
async def execute_with_memory(
    task: str,
    session_id: str,
    user_id: str,
    memory_manager: ATLASMemoryManager
):
    """Executes task with long-term memory augmentation."""

    # Retrieve user preferences
    user_context = memory_manager.get_user_context(user_id)

    # Retrieve similar past conversations
    similar_tasks = await memory_manager.recall_similar_conversations(
        query=task,
        k=3,
        filter_metadata={"user_id": user_id}
    )

    # Build enriched context
    enriched_context = f"""
Task: {task}

User Preferences:
- Preferred model: {user_context.get('preferred_model', 'openai/gpt-4o')}
- Writing style: {user_context.get('writing_style', 'professional')}
- Citation format: {user_context.get('citation_format', 'APA')}

Similar Past Tasks:
{chr(10).join([f"- {task['content'][:100]}..." for task in similar_tasks])}

Execute this task using the user's preferences and learning from similar past tasks.
"""

    # Execute with enriched context
    result = await supervisor_agent.ainvoke({
        "messages": [{"role": "user", "content": enriched_context}]
    })

    # Store conversation for future reference
    await memory_manager.store_conversation(
        session_id=session_id,
        messages=result["messages"],
        metadata={
            "user_id": user_id,
            "task_type": "research",
            "success": True
        }
    )

    return result
```

---

## 5. Retrieval (RAG)

### RAG Architecture Selection for ATLAS

**Agentic RAG** (Recommended for ATLAS)
- Dynamic retrieval during reasoning
- Agent decides when to search for information
- Flexible but variable latency
- Perfect for research assistant use cases

**Implementation Pattern**
```python
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate

# Create Tavily search tool for agentic RAG
tavily_tool = TavilySearchResults(
    max_results=5,
    search_depth="advanced",
    include_answer=True,
    include_raw_content=True
)

# Research agent with agentic RAG
research_agent_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a research specialist with access to web search.

When you need information:
1. Decide if you need to search or if you already have enough context
2. Use the tavily_search tool to find current information
3. Synthesize findings from multiple sources
4. Always cite sources with [source_url] format

You have access to:
- tavily_search: Search the web for current information
- Your knowledge cutoff: January 2025"""),
    ("human", "{query}")
])

research_agent = create_react_agent(
    model=call_model(model="anthropic/claude-3-5-sonnet"),
    tools=[tavily_tool],
    prompt=research_agent_prompt
)
```

### ATLAS Document Processing RAG

**2-Step RAG for Document Analysis**
```python
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

class ATLASDocumentRAG:
    """Document-based RAG for ATLAS analysis tasks."""

    def __init__(self, session_dir: str):
        self.session_dir = session_dir
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vector_store = None
        self.retriever = None

    async def index_documents(self, file_patterns: list[str] = ["*.md", "*.txt"]):
        """Indexes documents from session directory."""

        # Load documents
        loaders = [
            DirectoryLoader(
                self.session_dir,
                glob=pattern,
                loader_cls=TextLoader
            )
            for pattern in file_patterns
        ]

        documents = []
        for loader in loaders:
            documents.extend(await loader.aload())

        # Split into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        splits = text_splitter.split_documents(documents)

        # Create vector store
        self.vector_store = await Chroma.afrom_documents(
            documents=splits,
            embedding=self.embeddings,
            collection_name=f"session_{self.session_dir}",
            persist_directory=f"{self.session_dir}/vectorstore"
        )

        # Create retriever
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )

        return len(splits)

    async def query_documents(self, query: str, k: int = 5) -> list[dict]:
        """Retrieves relevant document chunks."""
        if not self.retriever:
            raise ValueError("Documents not indexed. Call index_documents() first.")

        results = await self.retriever.aget_relevant_documents(query)

        return [
            {
                "content": doc.page_content,
                "source": doc.metadata.get("source"),
                "chunk_id": i
            }
            for i, doc in enumerate(results[:k])
        ]


# Analysis agent with document RAG
async def analyze_with_rag(
    query: str,
    session_dir: str,
    code_execution: bool = False
):
    """Performs analysis with document context."""

    # Initialize RAG system
    rag = ATLASDocumentRAG(session_dir=session_dir)
    await rag.index_documents()

    # Retrieve relevant context
    context_docs = await rag.query_documents(query=query, k=5)
    context = "\n\n".join([
        f"Source: {doc['source']}\n{doc['content']}"
        for doc in context_docs
    ])

    # Build analysis prompt with RAG context
    analysis_prompt = f"""
Query: {query}

Relevant Document Context:
{context}

Analyze the query using the provided document context. If code execution is needed, use the E2B sandbox.
"""

    # Execute analysis
    analysis_agent = create_react_agent(
        model=call_model(model="openai/gpt-4o"),
        tools=[e2b_code_execution_tool] if code_execution else [],
        state_modifier="You are a data analyst. Use provided context and execute code when needed."
    )

    result = await analysis_agent.ainvoke({
        "messages": [{"role": "user", "content": analysis_prompt}]
    })

    return {
        "analysis": result["messages"][-1].content,
        "sources": [doc["source"] for doc in context_docs],
        "context_chunks": len(context_docs)
    }
```

### Hybrid RAG for Complex Queries

```python
async def hybrid_rag_research(
    query: str,
    session_dir: str,
    max_iterations: int = 3
):
    """Combines web search with document RAG for comprehensive research."""

    # Initialize both RAG systems
    doc_rag = ATLASDocumentRAG(session_dir=session_dir)
    await doc_rag.index_documents()

    # Initial web search
    web_results = await tavily_tool.ainvoke({"query": query})

    # Query local documents
    doc_results = await doc_rag.query_documents(query=query)

    # Combine context
    combined_context = f"""
Web Search Results:
{web_results}

Local Document Context:
{chr(10).join([doc['content'] for doc in doc_results])}

Synthesize findings from both web and local sources.
"""

    # Research agent with combined context
    research_agent = create_react_agent(
        model=call_model(model="anthropic/claude-3-5-sonnet"),
        tools=[tavily_tool],
        state_modifier="You are a research specialist. Combine web and document sources."
    )

    result = await research_agent.ainvoke({
        "messages": [{"role": "user", "content": combined_context}]
    })

    return {
        "synthesis": result["messages"][-1].content,
        "web_sources": len(web_results.get("results", [])),
        "doc_sources": len(doc_results)
    }
```

---

## ATLAS Integration Strategy

### 1. Multi-Agent Architecture

**Current Implementation**:
- ✅ Supervisor with tool-based delegation
- ✅ Research, Analysis, Writing sub-agents
- 🔄 Parallel execution for independent tasks

**Recommended Enhancements**:
```python
# Enhanced supervisor with memory and structured output
class EnhancedATLASSupervisor:
    def __init__(
        self,
        memory_manager: ATLASMemoryManager,
        doc_rag: ATLASDocumentRAG,
        session_dir: str
    ):
        self.memory_manager = memory_manager
        self.doc_rag = doc_rag
        self.session_dir = session_dir

        # Create supervisor with all enhancements
        self.supervisor = create_react_agent(
            model=call_model(model="openai/gpt-4o"),
            tools=[
                call_research_agent,
                call_analysis_agent,
                call_writing_agent,
                self._create_plan_with_memory(),
                self._create_save_with_hitl()
            ],
            state_modifier=self._build_context_aware_prompt()
        )

    def _create_plan_with_memory(self) -> StructuredTool:
        """Creates planning tool with memory augmentation."""
        @tool(response_format=PlanningOutput)
        async def plan_with_memory(objective: str) -> PlanningOutput:
            # Recall similar past plans
            similar_plans = await self.memory_manager.recall_similar_conversations(
                query=f"planning for {objective}",
                k=3
            )

            # Use LLM to create optimized plan
            # ... (planning logic with past learnings)

            return plan

        return plan_with_memory

    def _create_save_with_hitl(self) -> StructuredTool:
        """Creates save tool with human approval gate."""
        @tool
        async def save_with_approval(
            file_path: str,
            content: str
        ) -> str:
            # Trigger HITL approval
            approval = await self._request_approval(
                tool_name="save_output",
                tool_args={"file_path": file_path, "content": content[:200]}
            )

            if approval["action"] == "accept":
                # Save file
                with open(file_path, 'w') as f:
                    f.write(content)
                return f"Saved to {file_path}"
            else:
                return f"Save cancelled: {approval['feedback']}"

        return save_with_approval

    def _build_context_aware_prompt(self) -> str:
        """Builds supervisor prompt with user preferences."""
        user_context = self.memory_manager.get_user_context(self.user_id)

        return f"""You are the ATLAS supervisor coordinating research, analysis, and writing.

User Preferences:
- Model: {user_context.get('preferred_model')}
- Style: {user_context.get('writing_style')}
- Citations: {user_context.get('citation_format')}

Your capabilities:
1. Research: call_research_agent (web search)
2. Analysis: call_analysis_agent (code execution)
3. Writing: call_writing_agent (document generation)
4. Planning: plan_with_memory (task decomposition with learnings)
5. Storage: save_with_approval (HITL-protected file operations)

Session directory: {self.session_dir}
"""
```

### 2. Session Management Integration

```python
from backend.src.api.agent_endpoints import create_chat_session

async def create_enhanced_session(
    user_id: str,
    session_name: str
) -> dict:
    """Creates session with all LangChain v1.0 features."""

    # Create base session
    session = await create_chat_session(user_id, session_name)
    session_dir = session["session_directory"]

    # Initialize LangChain components
    memory_manager = ATLASMemoryManager(
        vector_store=Chroma(...),
        memory_store=InMemoryStore()
    )

    doc_rag = ATLASDocumentRAG(session_dir=session_dir)

    # Create enhanced supervisor
    supervisor = EnhancedATLASSupervisor(
        memory_manager=memory_manager,
        doc_rag=doc_rag,
        session_dir=session_dir
    )

    # Store in session context
    session["supervisor"] = supervisor
    session["memory_manager"] = memory_manager
    session["doc_rag"] = doc_rag

    return session
```

### 3. MLflow Integration

```python
from backend.src.mlflow.enhanced_tracking import EnhancedATLASTracker

class TrackedSupervisor:
    """Supervisor with comprehensive MLflow tracking."""

    def __init__(self, supervisor: EnhancedATLASSupervisor, tracker: EnhancedATLASTracker):
        self.supervisor = supervisor
        self.tracker = tracker

    async def execute_tracked(self, task: str, thread_id: str):
        """Executes task with full observability."""

        # Log task start
        self.tracker.log_agent_status(
            agent_id="supervisor",
            agent_name="ATLAS_Supervisor",
            status="executing",
            metadata={"task": task, "thread_id": thread_id}
        )

        # Execute with tracking
        try:
            result = await self.supervisor.supervisor.ainvoke({
                "messages": [{"role": "user", "content": task}]
            })

            # Log tool calls
            for tool_call in result.get("tool_calls", []):
                self.tracker.log_tool_call(
                    tool_name=tool_call["name"],
                    tool_args=tool_call["args"],
                    tool_output=tool_call["output"],
                    agent_id="supervisor"
                )

            # Log success
            self.tracker.log_agent_status(
                agent_id="supervisor",
                status="completed",
                metadata={"thread_id": thread_id, "success": True}
            )

            return result

        except Exception as e:
            # Log failure
            self.tracker.log_agent_error(
                agent_id="supervisor",
                error_type=type(e).__name__,
                error_message=str(e),
                metadata={"thread_id": thread_id}
            )
            raise
```

### 4. AG-UI Event Broadcasting

```python
from backend.src.agui.server import agui_server

async def execute_with_realtime_updates(
    task: str,
    thread_id: str,
    supervisor: EnhancedATLASSupervisor
):
    """Executes task with real-time AG-UI updates."""

    # Stream execution events
    async for event in supervisor.supervisor.astream_events({
        "messages": [{"role": "user", "content": task}]
    }):
        # Broadcast to frontend via AG-UI
        if event["event"] == "on_chat_model_start":
            await agui_server.broadcast_event({
                "type": "agent_status_changed",
                "agent_id": event["metadata"]["agent_id"],
                "status": "thinking",
                "thread_id": thread_id
            })

        elif event["event"] == "on_tool_start":
            await agui_server.broadcast_event({
                "type": "agent_dialogue_update",
                "agent_id": "supervisor",
                "message": f"Using tool: {event['name']}",
                "thread_id": thread_id
            })

        elif event["event"] == "on_tool_end":
            await agui_server.broadcast_event({
                "type": "agent_dialogue_update",
                "agent_id": "supervisor",
                "message": f"Tool result: {event['data']['output'][:100]}...",
                "thread_id": thread_id
            })
```

---

## Implementation Priorities

### Phase 1: Core Multi-Agent (Week 1)
1. ✅ Tool-based sub-agent delegation
2. 🔄 Structured output for planning tool
3. ⏳ Parallel execution for independent tasks

### Phase 2: Memory & RAG (Week 2)
1. ChromaDB integration for long-term memory
2. Document RAG for analysis tasks
3. Memory-augmented planning

### Phase 3: HITL & Observability (Week 3)
1. HITL middleware for file operations
2. AG-UI approval flow
3. Enhanced MLflow tracking

### Phase 4: Optimization (Week 4)
1. Hybrid RAG for comprehensive research
2. Cross-session learning patterns
3. Performance tuning

---

## References

- [LangChain Multi-Agent Documentation](https://docs.langchain.com/oss/python/langchain/multi-agent)
- [LangChain Structured Output](https://docs.langchain.com/oss/python/langchain/structured-output)
- [LangChain Human-in-the-Loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)
- [LangChain Long-Term Memory](https://docs.langchain.com/oss/python/langchain/long-term-memory)
- [LangChain Retrieval (RAG)](https://docs.langchain.com/oss/python/langchain/retrieval)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [ATLAS Repository](https://github.com/CuriosityQuantified/ATLAS)

---

**Document Status**: Ready for implementation
**Next Steps**: Begin Phase 1 implementation with tool-based multi-agent patterns
