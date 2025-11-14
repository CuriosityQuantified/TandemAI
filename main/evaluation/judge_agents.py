"""
Judge Agents for Researcher Evaluation Framework
=================================================

Implements 7 specialized ReAct judge agents using LangGraph.
Each judge evaluates one dimension of researcher performance.

Architecture:
- Each judge is a simple ReAct agent
- Each has a submit_answer tool to provide final rating
- After submit_answer is invoked, route to END
- Judges are objective, unbiased experts

Version: 1.0
Created: 2025-11-13
"""

import os
import json
from typing import Dict, Any, Literal, Annotated
from datetime import datetime

from dotenv import load_dotenv

# LangChain/LangGraph imports
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

# Local imports
from evaluation.rubrics import (
    get_rubric_summary,
    BinaryScore,
    ScaledScore,
)

load_dotenv('/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/.env')


# ==============================================================================
# STATE DEFINITIONS
# ==============================================================================

class JudgeState(TypedDict):
    """State for judge agent."""
    messages: Annotated[list, add_messages]
    evaluation_complete: bool
    final_score: Dict[str, Any] | None


# ==============================================================================
# SUBMIT TOOLS (ONE PER JUDGE)
# ==============================================================================

# Global storage for judge decisions (used during evaluation)
_JUDGE_DECISIONS: Dict[str, Any] = {}


@tool
def submit_planning_quality_score(
    score: Literal[0.0, 1.0],
    reasoning: str
) -> str:
    """Submit final Planning Quality evaluation.

    Args:
        score: Binary score (0.0 = Poor, 1.0 = Good)
        reasoning: Detailed explanation with evidence from the response

    Returns:
        Confirmation message
    """
    global _JUDGE_DECISIONS
    _JUDGE_DECISIONS['planning_quality'] = {
        'score': score,
        'reasoning': reasoning,
        'timestamp': datetime.now().isoformat()
    }
    return f"✅ Planning Quality score submitted: {score}"


@tool
def submit_execution_completeness_score(
    score: Literal[1, 2, 3, 4, 5],
    reasoning: str
) -> str:
    """Submit final Execution Completeness evaluation.

    Args:
        score: Integer score (1=Incomplete, 5=Fully Complete)
        reasoning: Detailed explanation with evidence from the response

    Returns:
        Confirmation message
    """
    global _JUDGE_DECISIONS
    _JUDGE_DECISIONS['execution_completeness'] = {
        'score': score,
        'reasoning': reasoning,
        'timestamp': datetime.now().isoformat()
    }
    return f"✅ Execution Completeness score submitted: {score}/5"


@tool
def submit_source_quality_score(
    score: Literal[1, 2, 3, 4, 5],
    reasoning: str
) -> str:
    """Submit final Source Quality evaluation.

    Args:
        score: Integer score (1=Poor Sources, 5=Excellent Sources)
        reasoning: Detailed explanation with evidence from the response

    Returns:
        Confirmation message
    """
    global _JUDGE_DECISIONS
    _JUDGE_DECISIONS['source_quality'] = {
        'score': score,
        'reasoning': reasoning,
        'timestamp': datetime.now().isoformat()
    }
    return f"✅ Source Quality score submitted: {score}/5"


@tool
def submit_citation_accuracy_score(
    score: Literal[0.0, 1.0],
    reasoning: str
) -> str:
    """Submit final Citation Accuracy evaluation.

    Args:
        score: Binary score (0.0 = Incorrect, 1.0 = Correct)
        reasoning: Detailed explanation with evidence from the response

    Returns:
        Confirmation message
    """
    global _JUDGE_DECISIONS
    _JUDGE_DECISIONS['citation_accuracy'] = {
        'score': score,
        'reasoning': reasoning,
        'timestamp': datetime.now().isoformat()
    }
    return f"✅ Citation Accuracy score submitted: {score}"


@tool
def submit_answer_completeness_score(
    score: Literal[1, 2, 3, 4, 5],
    reasoning: str
) -> str:
    """Submit final Answer Completeness evaluation.

    Args:
        score: Integer score (1=Minimal, 5=Comprehensive)
        reasoning: Detailed explanation with evidence from the response

    Returns:
        Confirmation message
    """
    global _JUDGE_DECISIONS
    _JUDGE_DECISIONS['answer_completeness'] = {
        'score': score,
        'reasoning': reasoning,
        'timestamp': datetime.now().isoformat()
    }
    return f"✅ Answer Completeness score submitted: {score}/5"


@tool
def submit_factual_accuracy_score(
    score: Literal[0.0, 1.0],
    reasoning: str
) -> str:
    """Submit final Factual Accuracy evaluation.

    Args:
        score: Binary score (0.0 = Inaccurate, 1.0 = Accurate)
        reasoning: Detailed explanation with evidence from the response

    Returns:
        Confirmation message
    """
    global _JUDGE_DECISIONS
    _JUDGE_DECISIONS['factual_accuracy'] = {
        'score': score,
        'reasoning': reasoning,
        'timestamp': datetime.now().isoformat()
    }
    return f"✅ Factual Accuracy score submitted: {score}"


@tool
def submit_autonomy_score(
    score: Literal[0.0, 1.0],
    reasoning: str
) -> str:
    """Submit final Autonomy evaluation.

    Args:
        score: Binary score (0.0 = Non-autonomous, 1.0 = Autonomous)
        reasoning: Detailed explanation with evidence from the response

    Returns:
        Confirmation message
    """
    global _JUDGE_DECISIONS
    _JUDGE_DECISIONS['autonomy_score'] = {
        'score': score,
        'reasoning': reasoning,
        'timestamp': datetime.now().isoformat()
    }
    return f"✅ Autonomy Score submitted: {score}"


# ==============================================================================
# JUDGE SYSTEM PROMPTS
# ==============================================================================

def create_judge_prompt(rubric_name: str, rubric_summary: str) -> str:
    """Create system prompt for a judge agent."""
    return f"""You are an expert, objective, and unbiased judge evaluating researcher agent performance.

YOUR ROLE:
You evaluate ONE specific dimension: {rubric_name.replace('_', ' ').title()}

EVALUATION RUBRIC:
{rubric_summary}

EVALUATION PROCESS:

1. **Read the query and agent response carefully**
   - Understand what was asked
   - Analyze what the agent delivered

2. **Apply the rubric criteria objectively**
   - Compare response against rubric standards
   - Look for specific evidence
   - Be fair and unbiased

3. **Determine the appropriate score**
   - Follow the scoring guide exactly
   - Use the decision tree if provided
   - Justify your decision with evidence

4. **Submit your final evaluation**
   - Call the submit tool with your score and reasoning
   - Provide detailed reasoning with specific examples
   - Quote evidence from the response

CRITICAL REQUIREMENTS:

✅ **Be objective**: Judge based on rubric, not personal opinion
✅ **Be evidence-based**: Cite specific examples from the response
✅ **Be consistent**: Same standards for all evaluations
✅ **Be thorough**: Read entire response before judging
✅ **Be decisive**: Submit a clear score with reasoning

❌ **Don't be lenient**: Apply rubric strictly
❌ **Don't assume**: Judge only what's in the response
❌ **Don't skip**: Evaluate thoroughly, don't rush

REMEMBER:
- You are evaluating the AGENT'S PERFORMANCE, not the topic quality
- Your evaluation helps improve AI systems
- Accuracy and objectivity are paramount
- Submit your score when ready (no need to ask permission)
"""


# ==============================================================================
# JUDGE AGENT BUILDERS
# ==============================================================================

def create_judge_agent(
    rubric_name: str,
    submit_tool: Any,
    model: ChatAnthropic | None = None
) -> StateGraph:
    """Create a ReAct judge agent for a specific rubric.

    Args:
        rubric_name: Name of the rubric (e.g., "planning_quality")
        submit_tool: The submit_answer tool for this judge
        model: Optional ChatAnthropic model (will create default if None)

    Returns:
        Compiled StateGraph for the judge agent
    """
    # Create model if not provided
    if model is None:
        model = ChatAnthropic(
            model="claude-haiku-4-5-20251001",
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.0,  # Deterministic for consistent judging
        )

    # Get rubric summary
    rubric_summary = get_rubric_summary(rubric_name)

    # Create system prompt
    system_prompt = create_judge_prompt(rubric_name, rubric_summary)

    # Bind tools to model
    model_with_tools = model.bind_tools([submit_tool])

    # Define agent node
    def agent_node(state: JudgeState) -> Dict[str, Any]:
        """Agent reasoning node."""
        messages = state['messages']

        # Add system prompt if first call
        if len(messages) == 1:  # Only user message
            messages = [SystemMessage(content=system_prompt)] + messages

        response = model_with_tools.invoke(messages)
        return {'messages': [response]}

    # Define routing function
    def should_continue(state: JudgeState) -> Literal["tools", "end"]:
        """Determine if we should continue or end."""
        messages = state['messages']
        last_message = messages[-1]

        # If tool calls present, go to tools
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        else:
            # No tool calls means agent is done
            return "end"

    # Create graph
    workflow = StateGraph(JudgeState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode([submit_tool]))

    # Add edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        }
    )
    workflow.add_edge("tools", "agent")  # After tool, go back to agent

    # Compile
    return workflow.compile()


# ==============================================================================
# JUDGE REGISTRY
# ==============================================================================

class JudgeRegistry:
    """Registry of all judge agents."""

    def __init__(self, model: ChatAnthropic | None = None):
        """Initialize judge registry.

        Args:
            model: Optional shared model for all judges (creates default if None)
        """
        self.model = model or ChatAnthropic(
            model="claude-haiku-4-5-20251001",
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.0,
        )

        # Create all judges
        self.judges = {
            'planning_quality': create_judge_agent(
                'planning_quality',
                submit_planning_quality_score,
                self.model
            ),
            'execution_completeness': create_judge_agent(
                'execution_completeness',
                submit_execution_completeness_score,
                self.model
            ),
            'source_quality': create_judge_agent(
                'source_quality',
                submit_source_quality_score,
                self.model
            ),
            'citation_accuracy': create_judge_agent(
                'citation_accuracy',
                submit_citation_accuracy_score,
                self.model
            ),
            'answer_completeness': create_judge_agent(
                'answer_completeness',
                submit_answer_completeness_score,
                self.model
            ),
            'factual_accuracy': create_judge_agent(
                'factual_accuracy',
                submit_factual_accuracy_score,
                self.model
            ),
            'autonomy_score': create_judge_agent(
                'autonomy_score',
                submit_autonomy_score,
                self.model
            ),
        }

    def get_judge(self, rubric_name: str) -> StateGraph:
        """Get a judge by rubric name."""
        if rubric_name not in self.judges:
            raise ValueError(
                f"Unknown judge: {rubric_name}. "
                f"Available: {list(self.judges.keys())}"
            )
        return self.judges[rubric_name]

    def evaluate(
        self,
        query: str,
        response: str,
        rubric_name: str | None = None
    ) -> Dict[str, Any]:
        """Run evaluation with one or all judges.

        Args:
            query: The research query
            response: The agent's response to evaluate
            rubric_name: Specific rubric to evaluate (None = all judges)

        Returns:
            Dictionary of evaluation results
        """
        global _JUDGE_DECISIONS
        _JUDGE_DECISIONS = {}  # Reset decisions

        # Prepare evaluation input
        evaluation_input = f"""QUERY:
{query}

AGENT RESPONSE:
{response}

Please evaluate this response according to your rubric and submit your score.
"""

        if rubric_name:
            # Single judge
            judge = self.get_judge(rubric_name)
            initial_state = {
                'messages': [HumanMessage(content=evaluation_input)],
                'evaluation_complete': False,
                'final_score': None
            }
            result = judge.invoke(initial_state)
            return _JUDGE_DECISIONS

        else:
            # All judges
            results = {}
            for name, judge in self.judges.items():
                _JUDGE_DECISIONS = {}  # Reset for each judge
                initial_state = {
                    'messages': [HumanMessage(content=evaluation_input)],
                    'evaluation_complete': False,
                    'final_score': None
                }
                judge.invoke(initial_state)
                results[name] = _JUDGE_DECISIONS.get(name, {})

            return results


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================

def create_all_judges(model: ChatAnthropic | None = None) -> JudgeRegistry:
    """Create all 7 judge agents.

    Args:
        model: Optional shared model

    Returns:
        JudgeRegistry with all judges
    """
    return JudgeRegistry(model=model)


def evaluate_response(
    query: str,
    response: str,
    rubric_name: str | None = None,
    model: ChatAnthropic | None = None
) -> Dict[str, Any]:
    """Convenience function to evaluate a response.

    Args:
        query: Research query
        response: Agent response
        rubric_name: Specific rubric (None = all)
        model: Optional model

    Returns:
        Evaluation results
    """
    registry = create_all_judges(model=model)
    return registry.evaluate(query, response, rubric_name)


# ==============================================================================
# TESTING
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("JUDGE AGENTS - Testing")
    print("=" * 80)

    # Test: Create all judges
    print("\n📊 Creating judge registry...")
    registry = create_all_judges()
    print(f"✅ Created {len(registry.judges)} judges:")
    for name in registry.judges.keys():
        print(f"   - {name.replace('_', ' ').title()}")

    # Test: Sample evaluation
    print("\n" + "=" * 80)
    print("SAMPLE EVALUATION")
    print("=" * 80)

    sample_query = "Summarize latest developments in quantum computing"
    sample_response = """
I will research quantum computing developments.

According to Nature (2025), "Quantum computing achieved 99.9% gate fidelity in superconducting qubits" (nature.com/articles/quantum2025).

Recent developments include:
1. Hardware: IBM released 127-qubit processor
2. Software: Google demonstrated quantum error correction
3. Applications: Drug discovery simulations

Sources:
- IBM Quantum Blog (ibm.com/quantum)
- Nature Quantum (nature.com/quantum)
- Google AI Blog (ai.googleblog.com)
"""

    print(f"\nQuery: {sample_query}")
    print(f"\nResponse preview: {sample_response[:200]}...")

    print("\n🔍 Running Planning Quality judge...")
    result = registry.evaluate(sample_query, sample_response, 'planning_quality')
    print(f"\nResult: {json.dumps(result, indent=2)}")

    print("\n✅ Judge agents test complete!")
