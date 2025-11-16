# Deep Research Context Management for LangGraph

**Author:** AI Research Team
**Date:** November 4, 2025
**Version:** 1.0

## Executive Summary

This guide provides comprehensive patterns and strategies for managing context in deep research workflows using LangGraph and LangChain. When conducting research involving 50-500 searches, traditional context management approaches fail due to token limits, information overload, and state bloat. This document outlines production-ready architectures for knowledge graph auto-population, vector database integration, context summarization, and memory optimization.

## Table of Contents

1. [Context Management Challenges](#context-management-challenges)
2. [Architecture Overview](#architecture-overview)
3. [Knowledge Graph Integration](#knowledge-graph-integration)
4. [Vector Database Auto-Processing](#vector-database-auto-processing)
5. [Context Summarization Strategies](#context-summarization-strategies)
6. [State Management Patterns](#state-management-patterns)
7. [Document Processing Pipeline](#document-processing-pipeline)
8. [Memory Optimization Techniques](#memory-optimization-techniques)
9. [Implementation Examples](#implementation-examples)
10. [Production Considerations](#production-considerations)

---

## Context Management Challenges

### The Problem at Scale

Research agents conducting 50-500 searches face critical challenges:

- **Token Limit Exhaustion**: Even with 200K+ token windows, accumulated search results quickly exceed limits
- **Context Distraction**: Research shows model performance drops around 32,000 tokens, even with million-token windows
- **Information Overload**: LLMs struggle to extract relevant information from massive context
- **State Bloat**: Naive state accumulation leads to memory issues and slow performance
- **Deduplication**: Semantic overlap between search results wastes context space

### The Solution Framework

LangGraph provides four core strategies (2025):

1. **Write**: Strategic information persistence to external stores
2. **Select**: Intelligent filtering of relevant context
3. **Compress**: Summarization and context condensation
4. **Isolate**: Structured state schemas that separate LLM-visible context from background data

---

## Architecture Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Research Agent Workflow                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │  Search  │─────>│  Document    │─────>│  Entity      │  │
│  │  Node    │      │  Processing  │      │  Extraction  │  │
│  └──────────┘      └──────────────┘      └──────────────┘  │
│       │                    │                      │          │
│       v                    v                      v          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              External Memory Systems                  │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  Knowledge Graph  │  Vector Store  │  Checkpointer   │  │
│  │  (Neo4j/Memgraph) │  (ChromaDB)    │  (MongoDB/PG)   │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│                            v                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Context Summarization & Trimming              │  │
│  │  - SummarizationNode (recent 5 actions)              │  │
│  │  - Rolling window management                          │  │
│  │  - Semantic deduplication                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│                            v                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              LLM with Trimmed Context                 │  │
│  │  Essential info + Recent 5 actions + Retrieved KG     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Knowledge Graph** | Entity relationships, semantic connections | Neo4j, Memgraph + LangChain |
| **Vector Store** | Semantic search, similarity matching | ChromaDB, Pinecone + LangChain |
| **Checkpointer** | State persistence, conversation history | MongoDB, PostgreSQL |
| **Summarization** | Context compression, rolling windows | LangMem, custom nodes |

---

## Knowledge Graph Integration

### Auto-Population Architecture

Knowledge graphs transform unstructured search results into structured, queryable relationships. LangChain's `LLMGraphTransformer` (2025) enables automatic entity extraction and graph population.

### Core Components

#### 1. LLMGraphTransformer Setup

```python
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from langchain_neo4j import Neo4jGraph
from langchain_core.documents import Document
from typing import List

# Initialize LLM with function calling support
llm = ChatOpenAI(
    temperature=0,
    model_name="gpt-4o"  # GPT-4o provides best entity extraction
)

# Configure graph transformer with custom properties
llm_transformer = LLMGraphTransformer(
    llm=llm,
    node_properties=["description", "importance", "timestamp"],
    relationship_properties=["description", "confidence", "source"],
    # Optionally constrain entity types
    allowed_nodes=["Person", "Organization", "Concept", "Technology", "Location"],
    allowed_relationships=["RELATED_TO", "INVENTED", "WORKS_AT", "LOCATED_IN"]
)
```

#### 2. Neo4j/Memgraph Integration

```python
# Neo4j connection
neo4j_graph = Neo4jGraph(
    url="bolt://localhost:7687",
    username="neo4j",
    password="password",
    database="research"
)

# OR Memgraph connection (from langchain-memgraph)
from langchain_memgraph import MemgraphGraph

memgraph_graph = MemgraphGraph(
    url="bolt://localhost:7687",
    username="",
    password=""
)
```

#### 3. Document Processing Pipeline

```python
from typing import List
from langchain_core.documents import Document

def process_search_results_to_graph(
    search_results: List[str],
    graph: Neo4jGraph
) -> None:
    """
    Process search results and populate knowledge graph automatically.

    Args:
        search_results: List of text content from searches
        graph: Neo4j graph instance
    """
    # Convert to Document objects
    documents = [
        Document(
            page_content=text,
            metadata={"source": f"search_{i}", "timestamp": datetime.now()}
        )
        for i, text in enumerate(search_results)
    ]

    # Extract graph documents
    graph_documents = llm_transformer.convert_to_graph_documents(documents)

    # Add to graph database
    graph.add_graph_documents(
        graph_documents,
        baseEntityLabel=True,  # Add Document node
        include_source=True     # Link entities to source
    )

    print(f"Added {len(graph_documents)} graph documents to knowledge base")
```

#### 4. Incremental Graph Building

```python
from langgraph.graph import StateGraph
from typing import TypedDict, Annotated
import operator

class ResearchState(TypedDict):
    """State schema for research workflow"""
    messages: Annotated[list, operator.add]
    search_results: list[str]
    graph_entities_count: int
    current_question: str

def extract_entities_node(state: ResearchState) -> dict:
    """
    LangGraph node that automatically extracts entities from new searches
    and adds them to the knowledge graph.
    """
    new_results = state["search_results"][-5:]  # Process last 5 searches

    # Extract and add to graph
    docs = [Document(page_content=r) for r in new_results]
    graph_docs = llm_transformer.convert_to_graph_documents(docs)
    neo4j_graph.add_graph_documents(graph_docs)

    return {
        "graph_entities_count": state["graph_entities_count"] + len(graph_docs)
    }

# Add to LangGraph workflow
workflow = StateGraph(ResearchState)
workflow.add_node("extract_entities", extract_entities_node)
```

### Query Strategies

#### 1. Cypher Query Generation

```python
from langchain.chains import GraphCypherQAChain

# Create QA chain for knowledge-augmented research
cypher_chain = GraphCypherQAChain.from_llm(
    llm=ChatOpenAI(temperature=0, model="gpt-4o"),
    graph=neo4j_graph,
    verbose=True,
    return_intermediate_steps=True
)

def augment_with_graph_knowledge(question: str) -> str:
    """
    Query knowledge graph to augment LLM context with structured information.
    """
    result = cypher_chain.invoke({"query": question})
    return result["result"]
```

#### 2. Hybrid Search (Vector + Graph)

```python
from langchain_neo4j import Neo4jVector
from langchain_openai import OpenAIEmbeddings

# Create vector index in Neo4j
vector_index = Neo4jVector.from_existing_graph(
    embedding=OpenAIEmbeddings(),
    url="bolt://localhost:7687",
    username="neo4j",
    password="password",
    index_name="research_embeddings",
    node_label="Document",
    text_node_properties=["text"],
    embedding_node_property="embedding",
)

def hybrid_retrieval(query: str, k: int = 5) -> List[Document]:
    """
    Combine vector similarity with graph relationships for retrieval.
    """
    # Vector search
    similar_docs = vector_index.similarity_search(query, k=k)

    # Graph traversal to find related entities
    cypher_query = """
    MATCH (d:Document)-[r]->(e:Entity)
    WHERE d.text CONTAINS $query_text
    RETURN d, r, e
    LIMIT 10
    """
    graph_results = neo4j_graph.query(
        cypher_query,
        {"query_text": query}
    )

    return similar_docs, graph_results
```

### Benefits of Knowledge Graphs

1. **Semantic Relationships**: Capture connections between entities across searches
2. **Query Efficiency**: Structured queries faster than scanning all documents
3. **Deduplication**: Automatically merge duplicate entities
4. **Temporal Tracking**: Track entity evolution over research session
5. **Context Compression**: Represent complex relationships compactly

---

## Vector Database Auto-Processing

### Automatic Indexing Architecture

Vector databases enable semantic similarity search and automatic deduplication. LangChain provides unified interfaces for multiple vector stores.

### ChromaDB Integration

#### 1. Setup and Configuration

```python
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Initialize embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

# Create persistent ChromaDB instance
vectorstore = Chroma(
    collection_name="research_documents",
    embedding_function=embeddings,
    persist_directory="/path/to/chroma_db",
    collection_metadata={"hnsw:space": "cosine"}
)
```

#### 2. Automatic Document Processing

```python
from typing import List
import hashlib

class AutoVectorProcessor:
    """
    Automatically process, chunk, embed, and index search results.
    """

    def __init__(self, vectorstore: Chroma):
        self.vectorstore = vectorstore
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self.processed_hashes = set()

    def process_search_results(
        self,
        results: List[str],
        metadata: List[dict] = None
    ) -> int:
        """
        Process search results with automatic chunking and indexing.

        Returns:
            Number of new chunks added
        """
        documents = []

        for i, text in enumerate(results):
            # Semantic deduplication via hashing
            content_hash = hashlib.sha256(text.encode()).hexdigest()
            if content_hash in self.processed_hashes:
                continue

            self.processed_hashes.add(content_hash)

            # Create document with metadata
            doc = Document(
                page_content=text,
                metadata={
                    "source": metadata[i].get("source", f"search_{i}") if metadata else f"search_{i}",
                    "timestamp": datetime.now().isoformat(),
                    "content_hash": content_hash
                }
            )
            documents.append(doc)

        # Chunk documents
        chunks = self.text_splitter.split_documents(documents)

        # Add to vector store (automatic embedding)
        if chunks:
            self.vectorstore.add_documents(chunks)

        return len(chunks)
```

#### 3. LangGraph Integration

```python
def vector_indexing_node(state: ResearchState) -> dict:
    """
    LangGraph node for automatic vector indexing of new search results.
    """
    processor = AutoVectorProcessor(vectorstore)

    # Process only new results
    new_results = state["search_results"][-10:]  # Last 10 searches
    chunks_added = processor.process_search_results(new_results)

    return {
        "messages": [SystemMessage(content=f"Indexed {chunks_added} new chunks")]
    }

# Add to workflow
workflow.add_node("vector_index", vector_indexing_node)
```

### Semantic Deduplication

#### 1. Similarity-Based Filtering

```python
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class SemanticDeduplicator:
    """
    Remove semantically similar documents before indexing.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        self.threshold = similarity_threshold
        self.embeddings_cache = []

    def deduplicate(
        self,
        documents: List[Document],
        embeddings_func
    ) -> List[Document]:
        """
        Filter out semantically duplicate documents.
        """
        if not documents:
            return documents

        # Generate embeddings
        texts = [doc.page_content for doc in documents]
        new_embeddings = embeddings_func.embed_documents(texts)

        # Compare with cache
        unique_docs = []
        for i, doc in enumerate(documents):
            is_unique = True

            if self.embeddings_cache:
                similarities = cosine_similarity(
                    [new_embeddings[i]],
                    self.embeddings_cache
                )[0]

                if np.max(similarities) > self.threshold:
                    is_unique = False

            if is_unique:
                unique_docs.append(doc)
                self.embeddings_cache.append(new_embeddings[i])

        return unique_docs
```

#### 2. Integration in Processing Pipeline

```python
def process_with_deduplication(
    search_results: List[str],
    vectorstore: Chroma,
    embeddings: OpenAIEmbeddings
) -> int:
    """
    Process search results with semantic deduplication.
    """
    # Convert to documents
    docs = [Document(page_content=text) for text in search_results]

    # Deduplicate
    deduplicator = SemanticDeduplicator(similarity_threshold=0.85)
    unique_docs = deduplicator.deduplicate(docs, embeddings)

    # Chunk and index
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(unique_docs)

    vectorstore.add_documents(chunks)

    print(f"Processed {len(search_results)} results → {len(unique_docs)} unique → {len(chunks)} chunks")
    return len(chunks)
```

### Retrieval Strategies

#### 1. Context-Aware Search

```python
def retrieve_relevant_context(
    current_question: str,
    vectorstore: Chroma,
    k: int = 5
) -> List[Document]:
    """
    Retrieve most relevant documents for current research question.
    """
    # Similarity search with score
    results = vectorstore.similarity_search_with_score(
        current_question,
        k=k
    )

    # Filter by relevance threshold
    relevant_docs = [
        doc for doc, score in results
        if score < 0.7  # Lower is more similar in cosine distance
    ]

    return relevant_docs
```

#### 2. Multi-Query Retrieval

```python
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_openai import ChatOpenAI

# Create multi-query retriever
retriever = MultiQueryRetriever.from_llm(
    retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
    llm=ChatOpenAI(temperature=0, model="gpt-4o")
)

def enhanced_retrieval(question: str) -> List[Document]:
    """
    Generate multiple query variations for better retrieval.
    """
    # MultiQueryRetriever automatically generates variations
    # and deduplicates results
    results = retriever.get_relevant_documents(question)
    return results
```

---

## Context Summarization Strategies

### The Summarization Challenge

With 50-500 searches, maintaining full context is impossible. Summarization preserves essential information while reducing token count.

### LangGraph Summarization Patterns (2025)

#### 1. SummarizationNode with LangMem

```python
from langmem.short_term import SummarizationNode
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.prebuilt.chat_agent_executor import AgentState

# Initialize summarization model
summarization_llm = ChatOpenAI(
    model="gpt-4o-mini",  # Faster, cheaper for summarization
    max_tokens=256
)

# Create summarization node
summarization_node = SummarizationNode(
    token_counter=count_tokens_approximately,
    model=summarization_llm,
    max_tokens=8000,  # Trigger summarization above this
    max_summary_tokens=2000,  # Compress to this size
    output_messages_key="llm_input_messages",  # Field to write compressed context
)
```

#### 2. Rolling Window Implementation

```python
from typing import TypedDict, Annotated, List
import operator
from langchain_core.messages import BaseMessage, SystemMessage

class ResearchState(TypedDict):
    """State with rolling window context management"""
    messages: Annotated[List[BaseMessage], operator.add]
    search_results: List[str]

    # Context management fields
    recent_actions: List[dict]  # Rolling window of last 5 actions
    essential_context: str       # Compressed essential information
    knowledge_graph_context: str # Retrieved from KG when needed

def rolling_window_node(state: ResearchState) -> dict:
    """
    Maintain rolling window of recent N actions/results.
    """
    WINDOW_SIZE = 5

    # Extract recent actions (searches, analyses, etc.)
    all_actions = extract_actions_from_messages(state["messages"])

    # Keep only last N
    recent = all_actions[-WINDOW_SIZE:]

    # Summarize older actions if needed
    if len(all_actions) > WINDOW_SIZE:
        older_actions = all_actions[:-WINDOW_SIZE]
        essential_summary = summarize_actions(older_actions)
    else:
        essential_summary = state.get("essential_context", "")

    return {
        "recent_actions": recent,
        "essential_context": essential_summary
    }

def extract_actions_from_messages(messages: List[BaseMessage]) -> List[dict]:
    """Extract structured action log from message history"""
    actions = []
    for msg in messages:
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                actions.append({
                    "type": "tool_call",
                    "tool": tool_call["name"],
                    "timestamp": datetime.now().isoformat(),
                    "summary": tool_call["args"]
                })
    return actions

def summarize_actions(actions: List[dict]) -> str:
    """Compress action history into essential summary"""
    summary_prompt = f"""
    Summarize the following research actions into key findings and progress:

    {actions}

    Focus on:
    - Main topics researched
    - Key findings discovered
    - Important entities identified
    - Current research direction

    Keep summary under 500 tokens.
    """

    response = summarization_llm.invoke(summary_prompt)
    return response.content
```

#### 3. Pre-Model Hook Pattern

```python
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import trim_messages

def create_context_trimming_hook():
    """
    Create pre-model hook for automatic context trimming.
    """
    def pre_model_hook(state: AgentState) -> dict:
        """
        Trim messages before passing to LLM.
        """
        # Trim to keep essential context
        trimmed = trim_messages(
            state["messages"],
            strategy="last",  # Keep most recent
            max_tokens=16000,  # Safe buffer under model limit
            token_counter=count_tokens_approximately,
            # Always keep system message
            include_system=True,
        )

        return {"llm_input_messages": trimmed}

    return pre_model_hook

# Create agent with trimming
agent = create_react_agent(
    model=ChatOpenAI(model="gpt-4o"),
    tools=research_tools,
    state_modifier=create_context_trimming_hook()
)
```

#### 4. Hierarchical Summarization

```python
from typing import List

class HierarchicalSummarizer:
    """
    Multi-level summarization for large document sets.
    """

    def __init__(self, llm, chunk_size: int = 10):
        self.llm = llm
        self.chunk_size = chunk_size

    def summarize_hierarchical(self, documents: List[str]) -> str:
        """
        Summarize large document set through multiple levels.

        Level 1: Chunk into groups of N
        Level 2: Summarize each chunk
        Level 3: Summarize summaries
        """
        if len(documents) <= self.chunk_size:
            return self._summarize_batch(documents)

        # Level 1: Chunk
        chunks = [
            documents[i:i + self.chunk_size]
            for i in range(0, len(documents), self.chunk_size)
        ]

        # Level 2: Summarize each chunk
        chunk_summaries = [
            self._summarize_batch(chunk)
            for chunk in chunks
        ]

        # Level 3: Summarize summaries (recursive)
        if len(chunk_summaries) > self.chunk_size:
            return self.summarize_hierarchical(chunk_summaries)
        else:
            return self._summarize_batch(chunk_summaries)

    def _summarize_batch(self, texts: List[str]) -> str:
        """Summarize a batch of texts"""
        combined = "\n\n---\n\n".join(texts)
        prompt = f"""
        Provide a comprehensive summary of the following content.
        Focus on key findings, important entities, and main themes.

        Content:
        {combined}

        Summary:
        """
        return self.llm.invoke(prompt).content
```

### Context Compression Techniques

#### 1. Selective Field Exposure

```python
from typing import TypedDict

class IsolatedState(TypedDict):
    """State schema with isolated fields"""
    # LLM-visible fields
    messages: List[BaseMessage]
    current_task: str

    # Background fields (not in LLM context)
    full_search_history: List[str]
    vector_store_ids: List[str]
    graph_entity_ids: List[str]

    # Selectively exposed
    relevant_context: str  # Retrieved from background as needed

def selective_context_node(state: IsolatedState) -> dict:
    """
    Retrieve only relevant context from background stores.
    """
    # Query vector store based on current task
    relevant_docs = vectorstore.similarity_search(
        state["current_task"],
        k=3
    )

    # Query knowledge graph
    relevant_entities = cypher_chain.invoke({
        "query": state["current_task"]
    })

    # Combine into compact context
    context = f"""
    Relevant Research:
    {format_docs(relevant_docs)}

    Key Entities:
    {relevant_entities}
    """

    return {"relevant_context": context}
```

#### 2. Progressive Summarization

```python
class ProgressiveSummarizer:
    """
    Continuously update summary as research progresses.
    """

    def __init__(self, llm):
        self.llm = llm
        self.current_summary = ""

    def update_summary(self, new_findings: List[str]) -> str:
        """
        Update running summary with new findings.
        """
        prompt = f"""
        Current Research Summary:
        {self.current_summary}

        New Findings:
        {chr(10).join(new_findings)}

        Update the summary to incorporate new findings while:
        1. Removing redundant information
        2. Highlighting novel insights
        3. Maintaining key themes
        4. Keeping under 1000 tokens

        Updated Summary:
        """

        updated = self.llm.invoke(prompt).content
        self.current_summary = updated
        return updated
```

---

## State Management Patterns

### State Schema Design

LangGraph's state schema determines what gets stored, persisted, and passed to the LLM. For large research sessions, careful schema design is critical.

### Recommended Schema Architecture

```python
from typing import TypedDict, Annotated, List, Optional
from langgraph.graph import add_messages
import operator

class ResearchAgentState(TypedDict):
    """
    Optimized state schema for deep research workflows.
    """

    # === LLM-VISIBLE CONTEXT ===
    messages: Annotated[List[BaseMessage], add_messages]
    current_question: str
    recent_findings: str  # Summary of last 5 searches

    # === EXTERNAL MEMORY REFERENCES ===
    # Don't store full content, just IDs/references
    vector_store_collection: str
    knowledge_graph_session: str
    checkpoint_thread_id: str

    # === ROLLING WINDOW ===
    recent_actions: List[dict]  # Last 5 actions with metadata

    # === COMPRESSED CONTEXT ===
    essential_summary: str  # Hierarchically compressed older context
    research_themes: List[str]  # Extracted main themes
    key_entities: List[str]  # Important entities discovered

    # === METADATA ===
    total_searches: int
    session_start_time: str
    last_update_time: str

    # === CONTROL FLOW ===
    next_action: Optional[str]
    requires_human_input: bool
```

### State Reduction Strategies

#### 1. Automatic State Trimming

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

def create_research_workflow_with_trimming():
    """
    Create workflow with automatic state trimming.
    """

    workflow = StateGraph(ResearchAgentState)

    # State trimming node
    def trim_state_node(state: ResearchAgentState) -> dict:
        """
        Periodically trim state to prevent bloat.
        """
        # Trigger every 10 searches
        if state["total_searches"] % 10 == 0:
            # Summarize recent findings
            summary = summarize_findings(state["recent_findings"])

            # Update essential summary
            updated_summary = merge_summaries(
                state["essential_summary"],
                summary
            )

            # Clear recent findings buffer
            return {
                "essential_summary": updated_summary,
                "recent_findings": "",
                "recent_actions": state["recent_actions"][-5:]  # Keep last 5
            }

        return {}

    workflow.add_node("trim_state", trim_state_node)

    return workflow
```

#### 2. Checkpointing Strategy

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Configure PostgreSQL checkpointer
checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost:5432/research_db"
)

# Compile with checkpointing
research_graph = workflow.compile(
    checkpointer=checkpointer,
    # Auto-save every N steps
    interrupt_before=[],
    interrupt_after=[]
)

def save_research_checkpoint(
    thread_id: str,
    state: ResearchAgentState
) -> None:
    """
    Save research checkpoint with metadata.
    """
    # Checkpoint automatically saved by LangGraph
    # But we can add custom metadata
    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_metadata": {
                "total_searches": state["total_searches"],
                "themes": state["research_themes"],
                "timestamp": datetime.now().isoformat()
            }
        }
    }

    # Execute to trigger checkpoint save
    research_graph.invoke(state, config=config)
```

#### 3. Long-Term Memory Integration (MongoDB Store)

```python
from langgraph.store.mongodb import MongoDBStore

# Initialize MongoDB store (2025 feature)
store = MongoDBStore(
    connection_string="mongodb://localhost:27017",
    database_name="research_memory"
)

def save_to_long_term_memory(
    session_id: str,
    key_findings: List[str],
    entities: List[dict]
) -> None:
    """
    Save important research artifacts to long-term memory.
    """
    # Store findings
    store.put(
        namespace=("research", session_id, "findings"),
        key="key_findings",
        value={
            "findings": key_findings,
            "timestamp": datetime.now().isoformat()
        }
    )

    # Store entities
    store.put(
        namespace=("research", session_id, "entities"),
        key="entities",
        value=entities
    )

def retrieve_from_long_term_memory(
    session_id: str
) -> dict:
    """
    Retrieve past research context from long-term memory.
    """
    findings = store.get(
        namespace=("research", session_id, "findings"),
        key="key_findings"
    )

    entities = store.get(
        namespace=("research", session_id, "entities"),
        key="entities"
    )

    return {
        "findings": findings.value if findings else [],
        "entities": entities.value if entities else []
    }
```

---

## Document Processing Pipeline

### End-to-End Pipeline Architecture

```python
from typing import List, Dict
from langgraph.graph import StateGraph, END

class DocumentProcessor:
    """
    Complete document processing pipeline for research workflows.
    """

    def __init__(
        self,
        vectorstore: Chroma,
        knowledge_graph: Neo4jGraph,
        llm: ChatOpenAI
    ):
        self.vectorstore = vectorstore
        self.knowledge_graph = knowledge_graph
        self.llm = llm
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.graph_transformer = LLMGraphTransformer(
            llm=llm,
            node_properties=["description", "importance"],
            relationship_properties=["description", "confidence"]
        )
        self.deduplicator = SemanticDeduplicator(similarity_threshold=0.85)

    def process_batch(
        self,
        documents: List[str],
        metadata: List[Dict] = None
    ) -> Dict[str, int]:
        """
        Process batch of documents through complete pipeline.

        Returns:
            Stats about processing
        """
        stats = {
            "input_docs": len(documents),
            "unique_docs": 0,
            "chunks_created": 0,
            "entities_extracted": 0,
            "vectors_added": 0
        }

        # Step 1: Convert to Document objects
        docs = [
            Document(
                page_content=text,
                metadata=metadata[i] if metadata else {"source": f"doc_{i}"}
            )
            for i, text in enumerate(documents)
        ]

        # Step 2: Semantic deduplication
        unique_docs = self.deduplicator.deduplicate(
            docs,
            self.vectorstore.embeddings
        )
        stats["unique_docs"] = len(unique_docs)

        # Step 3: Chunking
        chunks = self.text_splitter.split_documents(unique_docs)
        stats["chunks_created"] = len(chunks)

        # Step 4: Vector indexing (parallel)
        if chunks:
            self.vectorstore.add_documents(chunks)
            stats["vectors_added"] = len(chunks)

        # Step 5: Entity extraction and KG population (parallel)
        if unique_docs:
            graph_docs = self.graph_transformer.convert_to_graph_documents(
                unique_docs
            )
            self.knowledge_graph.add_graph_documents(graph_docs)
            stats["entities_extracted"] = sum(
                len(gd.nodes) for gd in graph_docs
            )

        return stats
```

### LangGraph Integration

```python
def create_document_processing_workflow():
    """
    Create LangGraph workflow with document processing pipeline.
    """

    workflow = StateGraph(ResearchAgentState)

    # Search node
    def search_node(state: ResearchAgentState) -> dict:
        """Execute search and return raw results"""
        # ... search implementation ...
        return {"search_results": results}

    # Document processing node
    def process_documents_node(state: ResearchAgentState) -> dict:
        """Process new search results through pipeline"""
        processor = DocumentProcessor(vectorstore, neo4j_graph, llm)

        # Process new results
        stats = processor.process_batch(state["search_results"][-10:])

        # Update state
        return {
            "messages": [
                SystemMessage(
                    content=f"Processed documents: {stats}"
                )
            ],
            "total_searches": state["total_searches"] + stats["input_docs"]
        }

    # Context retrieval node
    def retrieve_context_node(state: ResearchAgentState) -> dict:
        """Retrieve relevant context for next action"""
        # Vector search
        vector_results = vectorstore.similarity_search(
            state["current_question"],
            k=5
        )

        # Graph query
        graph_results = cypher_chain.invoke({
            "query": state["current_question"]
        })

        # Combine
        context = f"""
        Vector Search Results:
        {format_docs(vector_results)}

        Knowledge Graph Context:
        {graph_results}
        """

        return {"recent_findings": context}

    # Build workflow
    workflow.add_node("search", search_node)
    workflow.add_node("process_docs", process_documents_node)
    workflow.add_node("retrieve_context", retrieve_context_node)

    # Define edges
    workflow.add_edge("search", "process_docs")
    workflow.add_edge("process_docs", "retrieve_context")

    return workflow
```

### Performance Optimization

#### 1. Batch Processing

```python
import asyncio
from typing import List, Coroutine

async def process_documents_parallel(
    documents: List[str],
    batch_size: int = 10
) -> List[Dict]:
    """
    Process documents in parallel batches for better performance.
    """
    batches = [
        documents[i:i + batch_size]
        for i in range(0, len(documents), batch_size)
    ]

    tasks = [
        process_batch_async(batch)
        for batch in batches
    ]

    results = await asyncio.gather(*tasks)
    return results

async def process_batch_async(batch: List[str]) -> Dict:
    """Async processing of document batch"""
    # Parallel operations
    vector_task = asyncio.create_task(
        vectorstore.aadd_documents(batch)
    )
    graph_task = asyncio.create_task(
        extract_and_add_to_graph(batch)
    )

    await asyncio.gather(vector_task, graph_task)

    return {"batch_size": len(batch), "status": "completed"}
```

#### 2. Memory Management

```python
import gc
from typing import List

class MemoryEfficientProcessor:
    """
    Process large document sets without memory leaks.
    """

    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size

    def process_large_dataset(
        self,
        documents: List[str],
        callback=None
    ) -> None:
        """
        Process documents in batches with memory cleanup.
        """
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]

            # Process batch
            stats = processor.process_batch(batch)

            if callback:
                callback(stats)

            # Clear batch and force garbage collection
            del batch
            gc.collect()

            # Optional: Clear loader cache if using document loaders
            # This addresses the memory leak issue mentioned in research
```

---

## Memory Optimization Techniques

### Token Budget Management

```python
class TokenBudgetManager:
    """
    Manage token allocation across context components.
    """

    def __init__(self, total_budget: int = 120000):
        self.total_budget = total_budget
        self.allocations = {
            "system_prompt": 1000,
            "essential_context": 5000,
            "recent_actions": 3000,
            "retrieved_context": 8000,
            "conversation_history": 10000,
            "buffer": 2000  # Safety margin
        }

    def get_allocation(self, component: str) -> int:
        """Get token allocation for component"""
        return self.allocations.get(component, 0)

    def trim_to_budget(
        self,
        components: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Trim each component to fit within budget.
        """
        trimmed = {}

        for component, content in components.items():
            budget = self.get_allocation(component)
            token_count = count_tokens_approximately(content)

            if token_count > budget:
                # Trim proportionally
                ratio = budget / token_count
                target_chars = int(len(content) * ratio)
                trimmed[component] = content[:target_chars] + "..."
            else:
                trimmed[component] = content

        return trimmed
```

### Context Pruning Strategies

```python
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage

class ContextPruner:
    """
    Intelligent context pruning based on relevance and recency.
    """

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def prune_messages(
        self,
        messages: List[BaseMessage],
        current_focus: str,
        max_messages: int = 20
    ) -> List[BaseMessage]:
        """
        Prune message history to most relevant messages.
        """
        if len(messages) <= max_messages:
            return messages

        # Always keep system message
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

        # Score messages by relevance
        scored = []
        for msg in other_msgs:
            score = self._score_relevance(msg.content, current_focus)
            scored.append((score, msg))

        # Sort by score (descending) and take top N
        scored.sort(reverse=True, key=lambda x: x[0])
        top_messages = [msg for _, msg in scored[:max_messages-len(system_msgs)]]

        return system_msgs + top_messages

    def _score_relevance(self, content: str, focus: str) -> float:
        """
        Score message relevance to current focus.
        Could use embeddings similarity or LLM-based scoring.
        """
        # Simple embedding-based approach
        from sklearn.metrics.pairwise import cosine_similarity

        emb1 = embeddings.embed_query(content)
        emb2 = embeddings.embed_query(focus)

        similarity = cosine_similarity([emb1], [emb2])[0][0]
        return similarity
```

### Cache Optimization

```python
from functools import lru_cache
from typing import Tuple

class CachedRetriever:
    """
    Cache retrieval results to avoid redundant operations.
    """

    def __init__(self, vectorstore: Chroma, cache_size: int = 128):
        self.vectorstore = vectorstore
        self.cache_size = cache_size

    @lru_cache(maxsize=128)
    def cached_similarity_search(
        self,
        query: str,
        k: int = 5
    ) -> Tuple[str]:
        """
        Cached vector similarity search.
        Returns tuple (immutable) for caching.
        """
        results = self.vectorstore.similarity_search(query, k=k)
        # Convert to tuple for caching
        return tuple(doc.page_content for doc in results)

    def get_relevant_docs(self, query: str, k: int = 5) -> List[str]:
        """Public interface returning list"""
        return list(self.cached_similarity_search(query, k))
```

---

## Implementation Examples

### Complete Research Agent

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_neo4j import Neo4jGraph

def create_deep_research_agent():
    """
    Create complete research agent with all optimizations.
    """

    # Initialize components
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    summarization_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    vectorstore = Chroma(
        collection_name="research",
        embedding_function=OpenAIEmbeddings(),
        persist_directory="./chroma_db"
    )

    neo4j_graph = Neo4jGraph(
        url="bolt://localhost:7687",
        username="neo4j",
        password="password"
    )

    checkpointer = PostgresSaver.from_conn_string(
        "postgresql://user:pass@localhost/research"
    )

    # Create workflow
    workflow = StateGraph(ResearchAgentState)

    # === NODES ===

    def search_node(state: ResearchAgentState) -> dict:
        """Execute research search"""
        # ... search implementation ...
        return {"search_results": results}

    def process_documents_node(state: ResearchAgentState) -> dict:
        """Process and index documents"""
        processor = DocumentProcessor(vectorstore, neo4j_graph, llm)
        stats = processor.process_batch(state["search_results"][-10:])
        return {
            "total_searches": state["total_searches"] + stats["input_docs"]
        }

    def retrieve_context_node(state: ResearchAgentState) -> dict:
        """Retrieve relevant context"""
        # Vector retrieval
        vector_docs = vectorstore.similarity_search(
            state["current_question"], k=5
        )

        # Graph retrieval
        graph_context = cypher_chain.invoke({
            "query": state["current_question"]
        })

        context = format_context(vector_docs, graph_context)
        return {"recent_findings": context}

    def summarize_node(state: ResearchAgentState) -> dict:
        """Summarize and compress context"""
        if state["total_searches"] % 10 == 0:
            summarizer = HierarchicalSummarizer(summarization_llm)
            summary = summarizer.summarize_hierarchical(
                state["recent_findings"].split("\n\n")
            )
            return {
                "essential_summary": summary,
                "recent_findings": ""
            }
        return {}

    def agent_node(state: ResearchAgentState) -> dict:
        """Main agent reasoning"""
        # Prepare context with token budget
        budget_mgr = TokenBudgetManager()
        components = {
            "essential_context": state["essential_summary"],
            "recent_actions": format_actions(state["recent_actions"]),
            "retrieved_context": state["recent_findings"],
            "conversation_history": format_messages(state["messages"][-10:])
        }
        trimmed = budget_mgr.trim_to_budget(components)

        # Build prompt
        context = "\n\n".join([
            f"=== {k.upper()} ===\n{v}"
            for k, v in trimmed.items()
        ])

        # Invoke LLM
        response = llm.invoke([
            SystemMessage(content=RESEARCH_SYSTEM_PROMPT),
            HumanMessage(content=f"{context}\n\nCurrent Task: {state['current_question']}")
        ])

        return {
            "messages": [response],
            "next_action": extract_next_action(response)
        }

    # === BUILD WORKFLOW ===

    workflow.add_node("search", search_node)
    workflow.add_node("process", process_documents_node)
    workflow.add_node("retrieve", retrieve_context_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("agent", agent_node)

    # Edges
    workflow.set_entry_point("search")
    workflow.add_edge("search", "process")
    workflow.add_edge("process", "retrieve")
    workflow.add_edge("retrieve", "summarize")
    workflow.add_edge("summarize", "agent")

    # Conditional edge for continuation
    def should_continue(state: ResearchAgentState) -> str:
        if state.get("next_action") == "complete":
            return END
        return "search"

    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "search": "search",
            END: END
        }
    )

    # Compile with checkpointing
    return workflow.compile(checkpointer=checkpointer)

# === USAGE ===

agent = create_deep_research_agent()

config = {
    "configurable": {
        "thread_id": "research_session_001"
    }
}

# Execute research
result = agent.invoke(
    {
        "current_question": "What are the latest developments in quantum computing?",
        "messages": [],
        "search_results": [],
        "recent_actions": [],
        "essential_summary": "",
        "total_searches": 0,
        "research_themes": [],
        "key_entities": []
    },
    config=config
)
```

---

## Production Considerations

### Scalability

#### 1. Distributed Processing

```python
from celery import Celery
from typing import List

app = Celery('research_tasks', broker='redis://localhost:6379')

@app.task
def process_document_batch(batch: List[str]) -> dict:
    """
    Celery task for distributed document processing.
    """
    processor = DocumentProcessor(vectorstore, neo4j_graph, llm)
    return processor.process_batch(batch)

def process_large_research_session(documents: List[str]) -> None:
    """
    Distribute processing across workers.
    """
    batch_size = 50
    batches = [
        documents[i:i+batch_size]
        for i in range(0, len(documents), batch_size)
    ]

    # Distribute to workers
    job = group(
        process_document_batch.s(batch)
        for batch in batches
    )

    result = job.apply_async()
    result.join()  # Wait for completion
```

#### 2. Resource Monitoring

```python
import psutil
from datetime import datetime

class ResourceMonitor:
    """
    Monitor resource usage during research sessions.
    """

    def __init__(self, alert_threshold: float = 0.8):
        self.alert_threshold = alert_threshold
        self.metrics = []

    def check_resources(self) -> dict:
        """Check current resource usage"""
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent

        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": cpu,
            "memory_percent": memory,
            "alert": cpu > self.alert_threshold * 100 or
                    memory > self.alert_threshold * 100
        }

        self.metrics.append(metrics)
        return metrics

    def get_recommendations(self) -> List[str]:
        """Get resource optimization recommendations"""
        recommendations = []

        avg_memory = sum(m["memory_percent"] for m in self.metrics) / len(self.metrics)

        if avg_memory > 70:
            recommendations.append(
                "High memory usage detected. Consider:\n"
                "- Reducing batch sizes\n"
                "- Increasing garbage collection frequency\n"
                "- Using streaming instead of batch processing"
            )

        return recommendations
```

### Error Handling

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class RobustResearchAgent:
    """
    Research agent with comprehensive error handling.
    """

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def execute_search_with_retry(self, query: str) -> List[str]:
        """Execute search with automatic retry on failure"""
        try:
            results = search_tool.invoke(query)
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def safe_process_documents(
        self,
        documents: List[str]
    ) -> Tuple[dict, List[str]]:
        """
        Process documents with error tracking.

        Returns:
            (stats, errors)
        """
        stats = {"processed": 0, "failed": 0}
        errors = []

        for i, doc in enumerate(documents):
            try:
                processor.process_batch([doc])
                stats["processed"] += 1
            except Exception as e:
                stats["failed"] += 1
                errors.append(f"Doc {i}: {str(e)}")
                logger.error(f"Failed to process document {i}: {e}")

        return stats, errors
```

### Observability

```python
from langsmith import Client
import logging

# Configure LangSmith tracing
client = Client()

def trace_research_session(
    session_id: str,
    agent_graph,
    input_state: dict
):
    """
    Execute research with full observability.
    """
    with client.trace_run(
        name="deep_research_session",
        run_type="chain",
        inputs=input_state,
        tags=["research", "production"]
    ) as run:

        # Execute agent
        result = agent_graph.invoke(
            input_state,
            config={
                "configurable": {"thread_id": session_id},
                "callbacks": [run]
            }
        )

        # Log metrics
        run.add_tags(["completed"])
        run.add_metadata({
            "total_searches": result["total_searches"],
            "themes": result["research_themes"],
            "duration_seconds": (
                datetime.now() -
                datetime.fromisoformat(result["session_start_time"])
            ).total_seconds()
        })

        return result
```

### Cost Optimization

```python
class CostOptimizer:
    """
    Track and optimize API costs during research.
    """

    def __init__(self):
        self.costs = {
            "gpt-4o": {"input": 0.005, "output": 0.015},  # per 1K tokens
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "text-embedding-3-large": {"input": 0.00013, "output": 0}
        }
        self.usage = []

    def track_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Track API call and calculate cost"""
        if model not in self.costs:
            return 0.0

        cost = (
            (input_tokens / 1000) * self.costs[model]["input"] +
            (output_tokens / 1000) * self.costs[model]["output"]
        )

        self.usage.append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "timestamp": datetime.now().isoformat()
        })

        return cost

    def get_total_cost(self) -> float:
        """Calculate total session cost"""
        return sum(u["cost"] for u in self.usage)

    def optimize_model_selection(
        self,
        task_type: str
    ) -> str:
        """Recommend most cost-effective model for task"""
        if task_type == "summarization":
            return "gpt-4o-mini"  # Cheaper for simple tasks
        elif task_type == "complex_reasoning":
            return "gpt-4o"
        elif task_type == "entity_extraction":
            return "gpt-4o"  # Better structured output
        return "gpt-4o-mini"
```

---

## Conclusion

Deep research workflows in LangGraph require sophisticated context management strategies to handle 50-500 searches effectively. The key patterns are:

1. **External Memory**: Offload content to knowledge graphs and vector databases
2. **Context Compression**: Use hierarchical summarization and rolling windows
3. **Selective Retrieval**: Pull relevant context just-in-time instead of maintaining everything
4. **State Optimization**: Careful schema design with isolated fields
5. **Automatic Processing**: Pipelines that chunk, deduplicate, embed, and extract entities

### Recommended Tech Stack (2025)

- **LangGraph**: 0.3.x for state management and orchestration
- **LangChain**: 0.3.x for tool integrations
- **Vector Store**: ChromaDB for local, Pinecone for cloud scale
- **Knowledge Graph**: Neo4j (mature) or Memgraph (performance)
- **Checkpointing**: PostgreSQL for production, MongoDB Store for advanced features
- **LLM**: GPT-4o for reasoning, GPT-4o-mini for summarization

### Performance Targets

| Metric | Target | Strategy |
|--------|--------|----------|
| Context Window Usage | < 50% of max | Compression + selective retrieval |
| Response Latency | < 5s per turn | Caching + parallel processing |
| Memory Usage | < 2GB per session | Batch processing + GC |
| Cost per 100 searches | < $2 | Model selection + caching |

### Next Steps

1. Implement knowledge graph auto-population for your domain
2. Set up vector database with semantic deduplication
3. Add LangMem SummarizationNode to your workflow
4. Configure PostgreSQL checkpointer for persistence
5. Instrument with LangSmith for observability
6. Optimize based on production metrics

---

## References

- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- LangChain Knowledge Graphs: https://python.langchain.com/docs/use_cases/graph/
- Neo4j LangChain Integration: https://neo4j.com/labs/genai-ecosystem/langchain/
- Memgraph LangChain: https://memgraph.com/blog/langchain-supports-memgraph
- Context Engineering Blog: https://blog.langchain.com/context-engineering-for-agents/
- MongoDB Store for LangGraph: https://www.mongodb.com/blog/langgraph
- LangMem Documentation: https://langchain-ai.github.io/langmem/

---

**Document Version:** 1.0
**Last Updated:** November 4, 2025
**Maintainer:** AI Research Team
