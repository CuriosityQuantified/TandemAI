"""
Phase 3: Comprehensive Test Suite for Benchmark Researcher Agent

This test suite provides 32+ diverse test queries across 4 categories to evaluate
the researcher agent's performance on planning quality, execution completeness,
source quality, citation accuracy, answer completeness, factual accuracy, and autonomy.

VERSION: 1.0
DATE: 2025-11-13
FRAMEWORK: Based on LangChain chat model testing patterns
TARGET: Benchmark Researcher Prompt V3.0

USAGE:
    from evaluation.test_suite import TEST_QUERIES, run_evaluation

    # Run all tests
    results = run_evaluation(agent_function)

    # Run specific category
    results = run_evaluation(agent_function, category="simple")

    # Run single test
    result = run_single_test(agent_function, TEST_QUERIES[0])
"""

from typing import Dict, List, Any, Callable, Optional, Literal
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json


# ==============================================================================
# TEST QUERY CATEGORIES
# ==============================================================================

class QueryCategory(str, Enum):
    """Test query complexity categories"""
    SIMPLE = "simple"  # Single-fact lookups, 3-4 steps
    MULTI_ASPECT = "multi_aspect"  # Multiple topics, 5-6 steps
    TIME_CONSTRAINED = "time_constrained"  # Latest/recent information
    COMPREHENSIVE = "comprehensive"  # Exhaustive coverage, 7-10 steps


class ExpectedBehavior(str, Enum):
    """Expected agent behaviors during execution"""
    MUST_CREATE_PLAN = "must_create_plan"
    MUST_EXECUTE_ALL_STEPS = "must_execute_all_steps"
    MUST_FIND_MULTIPLE_SOURCES = "must_find_multiple_sources"
    MUST_CITE_WITH_QUOTES = "must_cite_with_quotes"
    MUST_BE_AUTONOMOUS = "must_be_autonomous"
    MUST_VERIFY_COMPLETION = "must_verify_completion"
    MUST_USE_RECENT_SOURCES = "must_use_recent_sources"
    MUST_CROSS_REFERENCE = "must_cross_reference"


# ==============================================================================
# TEST QUERY DATA STRUCTURE
# ==============================================================================

@dataclass
class TestQuery:
    """
    Represents a single test query with metadata and success criteria.

    Attributes:
        id: Unique identifier (e.g., "SIMPLE-001")
        query: The research question/prompt
        category: Complexity category
        expected_steps: Expected number of planning steps
        expected_behaviors: List of behaviors that must be demonstrated
        min_sources: Minimum number of sources required
        success_criteria: Dict of specific success criteria with thresholds
        description: Human-readable description of what's being tested
        tags: Additional categorization tags
    """
    id: str
    query: str
    category: QueryCategory
    expected_steps: int
    expected_behaviors: List[ExpectedBehavior]
    min_sources: int
    success_criteria: Dict[str, Any]
    description: str
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "query": self.query,
            "category": self.category.value,
            "expected_steps": self.expected_steps,
            "expected_behaviors": [b.value for b in self.expected_behaviors],
            "min_sources": self.min_sources,
            "success_criteria": self.success_criteria,
            "description": self.description,
            "tags": self.tags
        }


# ==============================================================================
# TEST QUERIES - CATEGORY 1: SIMPLE QUERIES (8 queries)
# ==============================================================================

SIMPLE_QUERIES = [
    TestQuery(
        id="SIMPLE-001",
        query="What is quantum error correction and why is it important?",
        category=QueryCategory.SIMPLE,
        expected_steps=4,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=3,
        success_criteria={
            "has_definition": True,
            "has_importance_explanation": True,
            "has_exact_quotes": True,
            "has_source_urls": True,
            "plan_created": True,
            "all_steps_completed": True
        },
        description="Tests basic definition + explanation pattern with planning",
        tags=["definition", "explanation", "quantum"]
    ),

    TestQuery(
        id="SIMPLE-002",
        query="Compare Python vs JavaScript for backend development",
        category=QueryCategory.SIMPLE,
        expected_steps=4,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=4,
        success_criteria={
            "covers_python": True,
            "covers_javascript": True,
            "has_comparison": True,
            "has_pros_cons": True,
            "plan_created": True,
            "all_steps_completed": True
        },
        description="Tests comparison pattern with two subjects",
        tags=["comparison", "programming", "backend"]
    ),

    TestQuery(
        id="SIMPLE-003",
        query="Explain how transformers work in natural language processing",
        category=QueryCategory.SIMPLE,
        expected_steps=4,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=3,
        success_criteria={
            "has_architecture_explanation": True,
            "has_attention_mechanism": True,
            "has_technical_details": True,
            "has_exact_quotes": True,
            "plan_created": True
        },
        description="Tests technical concept explanation with depth",
        tags=["machine-learning", "nlp", "technical"]
    ),

    TestQuery(
        id="SIMPLE-004",
        query="What are the main benefits and challenges of renewable energy?",
        category=QueryCategory.SIMPLE,
        expected_steps=4,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=4,
        success_criteria={
            "has_benefits": True,
            "has_challenges": True,
            "has_multiple_energy_types": True,
            "plan_created": True,
            "all_steps_completed": True
        },
        description="Tests pros/cons pattern across domain",
        tags=["renewable-energy", "pros-cons", "environment"]
    ),

    TestQuery(
        id="SIMPLE-005",
        query="How does blockchain consensus work in Bitcoin?",
        category=QueryCategory.SIMPLE,
        expected_steps=4,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=3,
        success_criteria={
            "has_consensus_explanation": True,
            "has_technical_details": True,
            "has_proof_of_work": True,
            "has_exact_quotes": True,
            "plan_created": True
        },
        description="Tests technical process explanation",
        tags=["blockchain", "bitcoin", "consensus", "technical"]
    ),

    TestQuery(
        id="SIMPLE-006",
        query="What is the difference between REST and GraphQL APIs?",
        category=QueryCategory.SIMPLE,
        expected_steps=4,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=3,
        success_criteria={
            "covers_rest": True,
            "covers_graphql": True,
            "has_comparison": True,
            "has_use_cases": True,
            "plan_created": True
        },
        description="Tests API architecture comparison",
        tags=["api", "rest", "graphql", "comparison"]
    ),

    TestQuery(
        id="SIMPLE-007",
        query="Explain the concept of vector databases and their applications",
        category=QueryCategory.SIMPLE,
        expected_steps=4,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=3,
        success_criteria={
            "has_definition": True,
            "has_applications": True,
            "has_examples": True,
            "has_technical_details": True,
            "plan_created": True
        },
        description="Tests emerging technology explanation",
        tags=["vector-database", "ai", "technical"]
    ),

    TestQuery(
        id="SIMPLE-008",
        query="What are the key principles of microservices architecture?",
        category=QueryCategory.SIMPLE,
        expected_steps=4,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=3,
        success_criteria={
            "has_principles_list": True,
            "has_explanations": True,
            "has_examples": True,
            "plan_created": True,
            "all_steps_completed": True
        },
        description="Tests architectural principles enumeration",
        tags=["architecture", "microservices", "principles"]
    )
]


# ==============================================================================
# TEST QUERIES - CATEGORY 2: MULTI-ASPECT QUERIES (8 queries)
# ==============================================================================

MULTI_ASPECT_QUERIES = [
    TestQuery(
        id="MULTI-001",
        query="Compare LangChain vs LlamaIndex vs CrewAI for building AI agent applications",
        category=QueryCategory.MULTI_ASPECT,
        expected_steps=5,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS,
            ExpectedBehavior.MUST_CROSS_REFERENCE
        ],
        min_sources=6,
        success_criteria={
            "covers_langchain": True,
            "covers_llamaindex": True,
            "covers_crewai": True,
            "has_comparison_table": True,
            "has_use_case_recommendations": True,
            "plan_created": True,
            "all_steps_completed": True,
            "plan_has_5_steps": True
        },
        description="Tests 3-way framework comparison with synthesis",
        tags=["framework-comparison", "ai-agents", "multi-framework"]
    ),

    TestQuery(
        id="MULTI-002",
        query="Analyze the current state of large language models: capabilities, limitations, costs, and future trends",
        category=QueryCategory.MULTI_ASPECT,
        expected_steps=6,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS,
            ExpectedBehavior.MUST_CROSS_REFERENCE
        ],
        min_sources=8,
        success_criteria={
            "covers_capabilities": True,
            "covers_limitations": True,
            "covers_costs": True,
            "covers_future_trends": True,
            "has_multiple_models": True,
            "plan_created": True,
            "all_steps_completed": True
        },
        description="Tests multi-dimensional analysis of complex topic",
        tags=["llm", "analysis", "multi-aspect"]
    ),

    TestQuery(
        id="MULTI-003",
        query="Technical deep-dive into quantum error correction: surface codes, topological codes, and vendor implementations (IBM, Google, IonQ)",
        category=QueryCategory.MULTI_ASPECT,
        expected_steps=6,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS,
            ExpectedBehavior.MUST_CROSS_REFERENCE
        ],
        min_sources=8,
        success_criteria={
            "covers_surface_codes": True,
            "covers_topological_codes": True,
            "covers_ibm": True,
            "covers_google": True,
            "covers_ionq": True,
            "has_technical_depth": True,
            "plan_created": True,
            "all_steps_completed": True
        },
        description="Tests technical deep-dive with multiple subtopics",
        tags=["quantum", "error-correction", "technical", "deep-dive"]
    ),

    TestQuery(
        id="MULTI-004",
        query="Compare database options for AI applications: PostgreSQL with pgvector, Pinecone, Weaviate, and ChromaDB",
        category=QueryCategory.MULTI_ASPECT,
        expected_steps=6,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=6,
        success_criteria={
            "covers_postgresql_pgvector": True,
            "covers_pinecone": True,
            "covers_weaviate": True,
            "covers_chromadb": True,
            "has_performance_comparison": True,
            "has_use_case_recommendations": True,
            "plan_created": True
        },
        description="Tests 4-way database comparison for specific use case",
        tags=["database", "vector-db", "ai", "comparison"]
    ),

    TestQuery(
        id="MULTI-005",
        query="Evaluate cloud providers for machine learning: AWS SageMaker, Google Vertex AI, Azure ML, and Databricks",
        category=QueryCategory.MULTI_ASPECT,
        expected_steps=6,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=6,
        success_criteria={
            "covers_aws": True,
            "covers_google": True,
            "covers_azure": True,
            "covers_databricks": True,
            "has_pricing": True,
            "has_comparison": True,
            "plan_created": True
        },
        description="Tests cloud platform comparison for ML",
        tags=["cloud", "machine-learning", "platform-comparison"]
    ),

    TestQuery(
        id="MULTI-006",
        query="Analyze retrieval-augmented generation (RAG) approaches: naive RAG, advanced RAG, and modular RAG with examples",
        category=QueryCategory.MULTI_ASPECT,
        expected_steps=5,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=5,
        success_criteria={
            "covers_naive_rag": True,
            "covers_advanced_rag": True,
            "covers_modular_rag": True,
            "has_examples": True,
            "has_comparison": True,
            "plan_created": True
        },
        description="Tests RAG architecture comparison",
        tags=["rag", "ai", "architecture"]
    ),

    TestQuery(
        id="MULTI-007",
        query="Compare programming languages for data science: Python, R, Julia, and SQL - strengths, weaknesses, and use cases",
        category=QueryCategory.MULTI_ASPECT,
        expected_steps=6,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=6,
        success_criteria={
            "covers_python": True,
            "covers_r": True,
            "covers_julia": True,
            "covers_sql": True,
            "has_strengths_weaknesses": True,
            "has_use_cases": True,
            "plan_created": True
        },
        description="Tests 4-language comparison for data science",
        tags=["programming", "data-science", "comparison"]
    ),

    TestQuery(
        id="MULTI-008",
        query="Examine AI agent architectures: ReAct, Plan-and-Execute, Reflection, and Multi-Agent systems",
        category=QueryCategory.MULTI_ASPECT,
        expected_steps=6,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=6,
        success_criteria={
            "covers_react": True,
            "covers_plan_execute": True,
            "covers_reflection": True,
            "covers_multi_agent": True,
            "has_technical_details": True,
            "has_comparison": True,
            "plan_created": True
        },
        description="Tests agent architecture pattern comparison",
        tags=["ai-agents", "architecture", "patterns"]
    )
]


# ==============================================================================
# TEST QUERIES - CATEGORY 3: TIME-CONSTRAINED QUERIES (8 queries)
# ==============================================================================

TIME_CONSTRAINED_QUERIES = [
    TestQuery(
        id="TIME-001",
        query="Summarize the latest AI developments and breakthroughs from November 2025",
        category=QueryCategory.TIME_CONSTRAINED,
        expected_steps=6,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_USE_RECENT_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES
        ],
        min_sources=8,
        success_criteria={
            "has_recent_sources": True,
            "sources_from_2025": True,
            "covers_multiple_developments": True,
            "has_dates": True,
            "plan_created": True,
            "all_steps_completed": True
        },
        description="Tests time-constrained comprehensive research",
        tags=["time-constrained", "recent", "ai", "comprehensive"]
    ),

    TestQuery(
        id="TIME-002",
        query="What are the latest quantum computing achievements in 2025?",
        category=QueryCategory.TIME_CONSTRAINED,
        expected_steps=5,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_USE_RECENT_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS,
            ExpectedBehavior.MUST_CROSS_REFERENCE
        ],
        min_sources=5,
        success_criteria={
            "sources_from_2025": True,
            "has_achievements": True,
            "has_dates": True,
            "has_verification": True,
            "plan_created": True
        },
        description="Tests recent achievement tracking",
        tags=["time-constrained", "quantum", "2025"]
    ),

    TestQuery(
        id="TIME-003",
        query="Review the most significant open-source AI releases in the past 3 months",
        category=QueryCategory.TIME_CONSTRAINED,
        expected_steps=5,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_USE_RECENT_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=6,
        success_criteria={
            "has_recent_releases": True,
            "has_significance_assessment": True,
            "sources_recent": True,
            "plan_created": True,
            "all_steps_completed": True
        },
        description="Tests rolling time window research",
        tags=["time-constrained", "open-source", "ai"]
    ),

    TestQuery(
        id="TIME-004",
        query="What are the latest developments in LangChain and LangGraph (2025)?",
        category=QueryCategory.TIME_CONSTRAINED,
        expected_steps=5,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_USE_RECENT_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=5,
        success_criteria={
            "covers_langchain": True,
            "covers_langgraph": True,
            "sources_from_2025": True,
            "has_version_info": True,
            "plan_created": True
        },
        description="Tests framework-specific recent updates",
        tags=["time-constrained", "langchain", "langgraph"]
    ),

    TestQuery(
        id="TIME-005",
        query="Summarize recent breakthroughs in protein folding and AlphaFold developments (2024-2025)",
        category=QueryCategory.TIME_CONSTRAINED,
        expected_steps=5,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_USE_RECENT_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS,
            ExpectedBehavior.MUST_CROSS_REFERENCE
        ],
        min_sources=5,
        success_criteria={
            "covers_protein_folding": True,
            "covers_alphafold": True,
            "sources_recent": True,
            "has_breakthroughs": True,
            "plan_created": True
        },
        description="Tests biotech recent research",
        tags=["time-constrained", "biotech", "alphafold"]
    ),

    TestQuery(
        id="TIME-006",
        query="What are the latest cybersecurity threats and vulnerabilities disclosed in the past month?",
        category=QueryCategory.TIME_CONSTRAINED,
        expected_steps=5,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_USE_RECENT_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=6,
        success_criteria={
            "has_recent_threats": True,
            "has_cve_numbers": True,
            "sources_very_recent": True,
            "has_severity_info": True,
            "plan_created": True
        },
        description="Tests very recent security research",
        tags=["time-constrained", "security", "threats"]
    ),

    TestQuery(
        id="TIME-007",
        query="Review the latest Claude and GPT model releases and capabilities (2025)",
        category=QueryCategory.TIME_CONSTRAINED,
        expected_steps=5,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_USE_RECENT_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=5,
        success_criteria={
            "covers_claude": True,
            "covers_gpt": True,
            "has_capabilities": True,
            "sources_from_2025": True,
            "plan_created": True
        },
        description="Tests LLM release tracking",
        tags=["time-constrained", "llm", "claude", "gpt"]
    ),

    TestQuery(
        id="TIME-008",
        query="What are the newest trends in vector databases and embedding models this year?",
        category=QueryCategory.TIME_CONSTRAINED,
        expected_steps=5,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_USE_RECENT_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=6,
        success_criteria={
            "covers_vector_dbs": True,
            "covers_embedding_models": True,
            "has_trends": True,
            "sources_from_2025": True,
            "plan_created": True
        },
        description="Tests emerging technology trend tracking",
        tags=["time-constrained", "vector-db", "embeddings"]
    )
]


# ==============================================================================
# TEST QUERIES - CATEGORY 4: COMPREHENSIVE QUERIES (8 queries)
# ==============================================================================

COMPREHENSIVE_QUERIES = [
    TestQuery(
        id="COMP-001",
        query="Comprehensive analysis of renewable energy technologies: solar, wind, hydro, geothermal, and nuclear - covering technology, economics, environmental impact, and future outlook",
        category=QueryCategory.COMPREHENSIVE,
        expected_steps=8,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS,
            ExpectedBehavior.MUST_CROSS_REFERENCE,
            ExpectedBehavior.MUST_VERIFY_COMPLETION
        ],
        min_sources=12,
        success_criteria={
            "covers_all_5_technologies": True,
            "has_technology_section": True,
            "has_economics_section": True,
            "has_environmental_section": True,
            "has_future_outlook": True,
            "plan_created": True,
            "plan_has_8_steps": True,
            "all_steps_completed": True
        },
        description="Tests comprehensive multi-dimensional analysis",
        tags=["comprehensive", "renewable-energy", "multi-dimensional"]
    ),

    TestQuery(
        id="COMP-002",
        query="Exhaustive guide to building production-ready AI applications: architecture patterns, frameworks, databases, deployment, monitoring, security, and costs",
        category=QueryCategory.COMPREHENSIVE,
        expected_steps=8,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS,
            ExpectedBehavior.MUST_VERIFY_COMPLETION
        ],
        min_sources=15,
        success_criteria={
            "covers_architecture": True,
            "covers_frameworks": True,
            "covers_databases": True,
            "covers_deployment": True,
            "covers_monitoring": True,
            "covers_security": True,
            "covers_costs": True,
            "plan_created": True,
            "all_steps_completed": True
        },
        description="Tests comprehensive production guide",
        tags=["comprehensive", "ai", "production", "guide"]
    ),

    TestQuery(
        id="COMP-003",
        query="Complete overview of modern web development: frontend frameworks (React, Vue, Svelte, Angular), backend (Node.js, Python, Go), databases (SQL vs NoSQL), deployment (cloud platforms), and best practices",
        category=QueryCategory.COMPREHENSIVE,
        expected_steps=9,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=15,
        success_criteria={
            "covers_frontend": True,
            "covers_backend": True,
            "covers_databases": True,
            "covers_deployment": True,
            "covers_best_practices": True,
            "has_framework_comparisons": True,
            "plan_created": True,
            "all_steps_completed": True
        },
        description="Tests comprehensive web dev stack overview",
        tags=["comprehensive", "web-development", "full-stack"]
    ),

    TestQuery(
        id="COMP-004",
        query="Comprehensive machine learning lifecycle guide: problem formulation, data collection, preprocessing, model selection, training, evaluation, deployment, monitoring, and retraining",
        category=QueryCategory.COMPREHENSIVE,
        expected_steps=10,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS,
            ExpectedBehavior.MUST_VERIFY_COMPLETION
        ],
        min_sources=12,
        success_criteria={
            "covers_all_9_stages": True,
            "has_best_practices": True,
            "has_tools_recommendations": True,
            "plan_created": True,
            "plan_has_10_steps": True,
            "all_steps_completed": True
        },
        description="Tests comprehensive ML lifecycle coverage",
        tags=["comprehensive", "machine-learning", "lifecycle"]
    ),

    TestQuery(
        id="COMP-005",
        query="In-depth analysis of AI agent frameworks ecosystem: LangChain, LangGraph, LlamaIndex, CrewAI, AutoGen, DSPy - covering architecture, use cases, strengths, limitations, integration patterns, and selection guide",
        category=QueryCategory.COMPREHENSIVE,
        expected_steps=8,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS,
            ExpectedBehavior.MUST_CROSS_REFERENCE
        ],
        min_sources=12,
        success_criteria={
            "covers_all_6_frameworks": True,
            "has_architecture_details": True,
            "has_use_cases": True,
            "has_strengths_limitations": True,
            "has_selection_guide": True,
            "plan_created": True,
            "all_steps_completed": True
        },
        description="Tests comprehensive framework ecosystem analysis",
        tags=["comprehensive", "ai-agents", "frameworks", "comparison"]
    ),

    TestQuery(
        id="COMP-006",
        query="Complete guide to distributed systems: CAP theorem, consensus algorithms (Paxos, Raft), data replication, partitioning strategies, consistency models, failure handling, and monitoring",
        category=QueryCategory.COMPREHENSIVE,
        expected_steps=8,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=10,
        success_criteria={
            "covers_cap_theorem": True,
            "covers_consensus": True,
            "covers_replication": True,
            "covers_partitioning": True,
            "covers_consistency": True,
            "has_technical_depth": True,
            "plan_created": True
        },
        description="Tests comprehensive distributed systems guide",
        tags=["comprehensive", "distributed-systems", "technical"]
    ),

    TestQuery(
        id="COMP-007",
        query="Exhaustive analysis of AI safety and alignment: current challenges, proposed solutions (RLHF, constitutional AI, red teaming), research directions, policy considerations, and future outlook",
        category=QueryCategory.COMPREHENSIVE,
        expected_steps=7,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS,
            ExpectedBehavior.MUST_CROSS_REFERENCE
        ],
        min_sources=10,
        success_criteria={
            "covers_challenges": True,
            "covers_rlhf": True,
            "covers_constitutional_ai": True,
            "covers_red_teaming": True,
            "covers_policy": True,
            "has_future_outlook": True,
            "plan_created": True
        },
        description="Tests comprehensive AI safety analysis",
        tags=["comprehensive", "ai-safety", "alignment"]
    ),

    TestQuery(
        id="COMP-008",
        query="Complete blockchain ecosystem overview: consensus mechanisms, smart contract platforms (Ethereum, Solana, Cardano), DeFi protocols, NFT standards, scaling solutions (L2s), and security considerations",
        category=QueryCategory.COMPREHENSIVE,
        expected_steps=8,
        expected_behaviors=[
            ExpectedBehavior.MUST_CREATE_PLAN,
            ExpectedBehavior.MUST_EXECUTE_ALL_STEPS,
            ExpectedBehavior.MUST_CITE_WITH_QUOTES,
            ExpectedBehavior.MUST_FIND_MULTIPLE_SOURCES,
            ExpectedBehavior.MUST_BE_AUTONOMOUS
        ],
        min_sources=12,
        success_criteria={
            "covers_consensus": True,
            "covers_platforms": True,
            "covers_defi": True,
            "covers_nfts": True,
            "covers_scaling": True,
            "covers_security": True,
            "plan_created": True,
            "all_steps_completed": True
        },
        description="Tests comprehensive blockchain ecosystem coverage",
        tags=["comprehensive", "blockchain", "ecosystem"]
    )
]


# ==============================================================================
# COMBINED TEST SUITE
# ==============================================================================

TEST_QUERIES: List[TestQuery] = (
    SIMPLE_QUERIES +
    MULTI_ASPECT_QUERIES +
    TIME_CONSTRAINED_QUERIES +
    COMPREHENSIVE_QUERIES
)


# ==============================================================================
# EVALUATION RESULT DATA STRUCTURE
# ==============================================================================

@dataclass
class EvaluationResult:
    """
    Results from evaluating a single test query.

    Attributes:
        test_query: The original test query
        agent_response: The agent's response
        execution_time: Time taken in seconds
        plan_created: Whether a plan was created
        num_steps: Number of steps in plan
        steps_completed: Number of steps completed
        num_sources: Number of unique sources cited
        has_exact_quotes: Whether response includes exact quotes
        has_source_urls: Whether sources include full URLs
        autonomy_score: 0-1 score for autonomous execution
        success_criteria_met: Dict of criteria met (True/False)
        overall_pass: Whether test passed
        notes: Additional notes or observations
    """
    test_query: TestQuery
    agent_response: str
    execution_time: float
    plan_created: bool
    num_steps: int
    steps_completed: int
    num_sources: int
    has_exact_quotes: bool
    has_source_urls: bool
    autonomy_score: float
    success_criteria_met: Dict[str, bool]
    overall_pass: bool
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "test_query": self.test_query.to_dict(),
            "execution_time": self.execution_time,
            "plan_created": self.plan_created,
            "num_steps": self.num_steps,
            "steps_completed": self.steps_completed,
            "num_sources": self.num_sources,
            "has_exact_quotes": self.has_exact_quotes,
            "has_source_urls": self.has_source_urls,
            "autonomy_score": self.autonomy_score,
            "success_criteria_met": self.success_criteria_met,
            "overall_pass": self.overall_pass,
            "notes": self.notes
        }

    def pass_rate(self) -> float:
        """Calculate percentage of success criteria met"""
        if not self.success_criteria_met:
            return 0.0
        total = len(self.success_criteria_met)
        passed = sum(1 for v in self.success_criteria_met.values() if v)
        return (passed / total) * 100


# ==============================================================================
# EVALUATION FUNCTIONS
# ==============================================================================

def run_single_test(
    agent_function: Callable[[str], Dict[str, Any]],
    test_query: TestQuery,
    verbose: bool = True
) -> EvaluationResult:
    """
    Run a single test query and evaluate the results.

    Args:
        agent_function: Function that takes query string and returns agent result
        test_query: The test query to run
        verbose: Whether to print progress

    Returns:
        EvaluationResult with evaluation metrics

    Example:
        >>> def my_agent(query: str) -> Dict[str, Any]:
        ...     # Your agent implementation
        ...     return result
        >>> result = run_single_test(my_agent, TEST_QUERIES[0])
    """
    if verbose:
        print(f"\n{'='*80}")
        print(f"TEST: {test_query.id}")
        print(f"QUERY: {test_query.query}")
        print(f"CATEGORY: {test_query.category.value}")
        print(f"{'='*80}\n")

    import time
    start_time = time.time()

    try:
        # Run the agent
        result = agent_function(test_query.query)
        execution_time = time.time() - start_time

        # Extract response
        agent_response = result.get("messages", [])[-1].content if result.get("messages") else ""

        # Evaluate planning
        plan_created = bool(result.get("plan"))
        num_steps = len(result.get("plan", {}).get("steps", [])) if plan_created else 0

        # Count completed steps
        steps_completed = 0
        if plan_created and result.get("plan"):
            steps = result.get("plan", {}).get("steps", [])
            steps_completed = sum(1 for step in steps if step.get("status") == "completed")

        # Count sources (simple heuristic: count unique URLs)
        import re
        urls = re.findall(r'https?://[^\s\]]+', agent_response)
        num_sources = len(set(urls))

        # Check for exact quotes (simple heuristic: look for quoted text)
        has_exact_quotes = '"' in agent_response and len(re.findall(r'"[^"]+"', agent_response)) >= 3

        # Check for source URLs
        has_source_urls = num_sources >= test_query.min_sources

        # Calculate autonomy score (did it complete without intervention?)
        autonomy_score = 1.0 if steps_completed == num_steps and num_steps > 0 else 0.5

        # Evaluate success criteria
        success_criteria_met = {}
        for criterion, expected_value in test_query.success_criteria.items():
            if criterion == "plan_created":
                success_criteria_met[criterion] = plan_created == expected_value
            elif criterion == "all_steps_completed":
                success_criteria_met[criterion] = steps_completed == num_steps if num_steps > 0 else False
            elif criterion.startswith("plan_has_"):
                expected_steps = int(criterion.split("_")[-2])
                success_criteria_met[criterion] = num_steps == expected_steps
            elif criterion == "has_exact_quotes":
                success_criteria_met[criterion] = has_exact_quotes == expected_value
            elif criterion == "has_source_urls":
                success_criteria_met[criterion] = has_source_urls == expected_value
            else:
                # For content-based criteria, do simple keyword matching
                # This is a simplified heuristic - real evaluation would be more sophisticated
                keywords = criterion.replace("_", " ")
                success_criteria_met[criterion] = keywords.lower() in agent_response.lower()

        # Determine overall pass
        pass_rate = sum(1 for v in success_criteria_met.values() if v) / len(success_criteria_met)
        overall_pass = pass_rate >= 0.7  # 70% threshold

        # Notes
        notes = []
        if num_steps != test_query.expected_steps:
            notes.append(f"Expected {test_query.expected_steps} steps, got {num_steps}")
        if num_sources < test_query.min_sources:
            notes.append(f"Expected {test_query.min_sources} sources, got {num_sources}")
        if not has_exact_quotes:
            notes.append("Missing exact quotes from sources")

        return EvaluationResult(
            test_query=test_query,
            agent_response=agent_response,
            execution_time=execution_time,
            plan_created=plan_created,
            num_steps=num_steps,
            steps_completed=steps_completed,
            num_sources=num_sources,
            has_exact_quotes=has_exact_quotes,
            has_source_urls=has_source_urls,
            autonomy_score=autonomy_score,
            success_criteria_met=success_criteria_met,
            overall_pass=overall_pass,
            notes=notes
        )

    except Exception as e:
        if verbose:
            print(f"ERROR: {str(e)}")

        return EvaluationResult(
            test_query=test_query,
            agent_response="",
            execution_time=time.time() - start_time,
            plan_created=False,
            num_steps=0,
            steps_completed=0,
            num_sources=0,
            has_exact_quotes=False,
            has_source_urls=False,
            autonomy_score=0.0,
            success_criteria_met={k: False for k in test_query.success_criteria.keys()},
            overall_pass=False,
            notes=[f"Error: {str(e)}"]
        )


def run_evaluation(
    agent_function: Callable[[str], Dict[str, Any]],
    category: Optional[Literal["simple", "multi_aspect", "time_constrained", "comprehensive"]] = None,
    max_tests: Optional[int] = None,
    verbose: bool = True
) -> List[EvaluationResult]:
    """
    Run evaluation on multiple test queries.

    Args:
        agent_function: Function that takes query string and returns agent result
        category: Optional category filter
        max_tests: Optional limit on number of tests to run
        verbose: Whether to print progress

    Returns:
        List of EvaluationResult objects

    Example:
        >>> results = run_evaluation(my_agent, category="simple", max_tests=5)
        >>> passed = sum(1 for r in results if r.overall_pass)
        >>> print(f"Passed: {passed}/{len(results)}")
    """
    # Filter queries by category if specified
    queries = TEST_QUERIES
    if category:
        cat_enum = QueryCategory(category)
        queries = [q for q in TEST_QUERIES if q.category == cat_enum]

    # Limit number of tests if specified
    if max_tests:
        queries = queries[:max_tests]

    if verbose:
        print(f"\n{'='*80}")
        print(f"RUNNING EVALUATION")
        print(f"Total tests: {len(queries)}")
        if category:
            print(f"Category: {category}")
        print(f"{'='*80}\n")

    results = []
    for i, query in enumerate(queries, 1):
        if verbose:
            print(f"\n[{i}/{len(queries)}] Running test: {query.id}")

        result = run_single_test(agent_function, query, verbose=verbose)
        results.append(result)

        if verbose:
            status = "✅ PASS" if result.overall_pass else "❌ FAIL"
            print(f"Result: {status} ({result.pass_rate():.1f}% criteria met)")
            print(f"Time: {result.execution_time:.1f}s")
            if result.notes:
                print(f"Notes: {', '.join(result.notes)}")

    return results


def print_evaluation_summary(results: List[EvaluationResult]) -> None:
    """
    Print a summary of evaluation results.

    Args:
        results: List of EvaluationResult objects
    """
    print(f"\n{'='*80}")
    print("EVALUATION SUMMARY")
    print(f"{'='*80}\n")

    total = len(results)
    passed = sum(1 for r in results if r.overall_pass)

    print(f"Overall Pass Rate: {passed}/{total} ({(passed/total)*100:.1f}%)\n")

    # Group by category
    from collections import defaultdict
    by_category = defaultdict(list)
    for r in results:
        by_category[r.test_query.category].append(r)

    print("Results by Category:")
    for category, cat_results in sorted(by_category.items()):
        cat_passed = sum(1 for r in cat_results if r.overall_pass)
        cat_total = len(cat_results)
        print(f"  {category.value}: {cat_passed}/{cat_total} ({(cat_passed/cat_total)*100:.1f}%)")

    print("\nAverage Metrics:")
    avg_time = sum(r.execution_time for r in results) / total
    avg_steps = sum(r.num_steps for r in results) / total
    avg_sources = sum(r.num_sources for r in results) / total
    avg_autonomy = sum(r.autonomy_score for r in results) / total

    print(f"  Execution Time: {avg_time:.1f}s")
    print(f"  Plan Steps: {avg_steps:.1f}")
    print(f"  Sources: {avg_sources:.1f}")
    print(f"  Autonomy Score: {avg_autonomy:.2f}")

    # Common issues
    print("\nCommon Issues:")
    all_notes = [note for r in results for note in r.notes]
    from collections import Counter
    note_counts = Counter(all_notes)
    for note, count in note_counts.most_common(5):
        print(f"  {note}: {count} occurrences")

    print(f"\n{'='*80}\n")


def save_results(
    results: List[EvaluationResult],
    output_path: str = "/Users/nicholaspate/Documents/01_Active/TandemAI/main/results/evaluation_results.json"
) -> None:
    """
    Save evaluation results to JSON file.

    Args:
        results: List of EvaluationResult objects
        output_path: Path to output file
    """
    import json
    from pathlib import Path

    # Create results directory if it doesn't exist
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Convert results to dict
    results_dict = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": len(results),
        "passed": sum(1 for r in results if r.overall_pass),
        "results": [r.to_dict() for r in results]
    }

    # Save to file
    with open(output_path, 'w') as f:
        json.dump(results_dict, f, indent=2)

    print(f"Results saved to: {output_path}")


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    print(f"""
{'='*80}
PHASE 3: COMPREHENSIVE TEST SUITE FOR BENCHMARK RESEARCHER AGENT
{'='*80}

Total Test Queries: {len(TEST_QUERIES)}

Breakdown by Category:
  - Simple Queries: {len(SIMPLE_QUERIES)} (3-4 steps)
  - Multi-Aspect Queries: {len(MULTI_ASPECT_QUERIES)} (5-6 steps)
  - Time-Constrained Queries: {len(TIME_CONSTRAINED_QUERIES)} (recent info)
  - Comprehensive Queries: {len(COMPREHENSIVE_QUERIES)} (7-10 steps)

Evaluation Criteria:
  1. Planning Quality: Does agent create appropriate plans?
  2. Execution Completeness: Does agent finish all steps?
  3. Source Quality: Does agent find authoritative sources?
  4. Citation Accuracy: Are citations properly formatted?
  5. Answer Completeness: Does response cover all aspects?
  6. Factual Accuracy: Are facts correct?
  7. Autonomy: Does agent execute without asking permission?

Usage Example:
  from evaluation.test_suite import TEST_QUERIES, run_evaluation

  # Define your agent function
  def my_agent(query: str) -> Dict[str, Any]:
      # Your agent implementation here
      return result

  # Run evaluation
  results = run_evaluation(my_agent, category="simple", max_tests=5)
  print_evaluation_summary(results)
  save_results(results)

{'='*80}
""")

    # Print sample queries
    print("\nSample Test Queries:\n")
    for category in [QueryCategory.SIMPLE, QueryCategory.MULTI_ASPECT,
                     QueryCategory.TIME_CONSTRAINED, QueryCategory.COMPREHENSIVE]:
        sample = next(q for q in TEST_QUERIES if q.category == category)
        print(f"{category.value.upper()}:")
        print(f"  ID: {sample.id}")
        print(f"  Query: {sample.query[:80]}...")
        print(f"  Expected Steps: {sample.expected_steps}")
        print(f"  Min Sources: {sample.min_sources}")
        print()
