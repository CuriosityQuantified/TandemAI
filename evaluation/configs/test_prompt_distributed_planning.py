"""
TEST PROMPT FOR DISTRIBUTED PLANNING & PARALLEL DELEGATION

This test prompt is designed to evaluate each configuration's ability to handle:
1. Supervisor creates a plan
2. Supervisor delegates step 1 to researcher
3. Researcher creates subplan and executes independently
4. Supervisor reflects after delegation
5. Supervisor decides: wait or delegate parallel task to another subagent

The prompt explicitly requests planning and parallel delegation behavior.
"""

# Test Prompt Version 1: Explicit Planning Instructions
TEST_PROMPT_V1_EXPLICIT = """You are the supervisor coordinating a multi-step research project. Here is your task:

MAIN OBJECTIVE: Create a comprehensive analysis of quantum computing trends for 2025.

YOUR PROCESS:
1. First, CREATE A PLAN with these steps:
   - Step 1: Research latest quantum computing breakthroughs (delegate to researcher)
   - Step 2: Analyze quantum computing market data (delegate to data_scientist)
   - Step 3: Synthesize findings into final report (you will do this)

2. START EXECUTION by delegating Step 1 to the researcher:
   - Tell the researcher to create their own detailed subplan
   - The researcher should plan to gather info from multiple sources
   - The researcher should execute their subplan independently

3. AFTER DELEGATING to researcher, REFLECT and DECIDE:
   - Should you WAIT for researcher to finish before moving on?
   - OR should you IMMEDIATELY delegate Step 2 to data_scientist IN PARALLEL?
   - Make this decision explicitly and explain your reasoning

4. Execute your decision (wait OR delegate in parallel)

IMPORTANT:
- Use planning tools if available
- Use delegation tools for each subagent
- Each subagent should create their own plan
- Demonstrate parallel delegation if possible
- Explain your reasoning at each step

Begin now."""

# Test Prompt Version 2: Natural Language (Less Explicit)
TEST_PROMPT_V2_NATURAL = """I need you to coordinate a comprehensive research project on quantum computing trends for 2025.

This project has multiple components:
- We need to research the latest scientific breakthroughs and industry news
- We need to analyze market trends and investment data
- We need to synthesize everything into a final report

I'd like you to plan out how to tackle this, delegate the research and analysis tasks to the appropriate specialists (researcher for literature review, data scientist for market analysis), and coordinate their work efficiently.

Please think about whether the tasks can be done in parallel or if they need to be sequential. Each specialist should also plan their own approach to their assigned task.

How would you orchestrate this project?"""

# Test Prompt Version 3: Implicit Parallel Requirement
TEST_PROMPT_V3_IMPLICIT = """Create a research report on quantum computing trends by:

1. Gathering latest research papers and news (this will take the researcher some time)
2. Analyzing market data and investment trends (this will take the data scientist some time)
3. Writing the final synthesis report

Both step 1 and 2 could potentially be done at the same time to save time. Coordinate the team to complete this efficiently.

Have each team member plan their approach before starting work."""

# Expected Behaviors for Each Configuration

EXPECTED_BEHAVIORS = {
    "config_1_deepagent_command": {
        "planning": "DeepAgent has reflection capability, may create implicit plan",
        "delegation": "Command.goto routing, delegation tools in parent graph",
        "parallel": "Possible - supervisor can call multiple delegation tools",
        "reflection": "DeepAgent has built-in reflection, should reflect after delegation",
        "subagent_planning": "Researcher is ReAct agent, no built-in planning unless prompted"
    },
    "config_3_react_command": {
        "planning": "ReAct supervisor, no explicit planning capability",
        "delegation": "Command.goto routing, delegation tools in parent graph",
        "parallel": "Possible - supervisor can call multiple delegation tools",
        "reflection": "No built-in reflection, depends on prompt",
        "subagent_planning": "Researcher is ReAct agent, no built-in planning unless prompted"
    },
    "config_4_react_conditional": {
        "planning": "ReAct supervisor, no explicit planning capability",
        "delegation": "Conditional edge routing",
        "parallel": "Difficult - conditional routing typically sequential",
        "reflection": "No built-in reflection, depends on prompt",
        "subagent_planning": "Researcher is ReAct agent, no built-in planning unless prompted"
    },
    "config_7_multi_agent": {
        "planning": "Supervisor uses handoff tools, no explicit planning",
        "delegation": "Handoff tools with Command.PARENT",
        "parallel": "Possible - supervisor can transfer to multiple agents",
        "reflection": "Workers return to supervisor, supervisor can reflect",
        "subagent_planning": "Agents are ReAct agents, no built-in planning unless prompted"
    },
    "config_8_hierarchical": {
        "planning": "Hierarchical structure, team supervisors can plan",
        "delegation": "Command.PARENT for navigation",
        "parallel": "Very possible - nested subgraphs allow parallel execution",
        "reflection": "Team supervisors can reflect before delegating to workers",
        "subagent_planning": "Workers in teams can plan before execution"
    }
}

# Evaluation Criteria

EVALUATION_CRITERIA = {
    "supervisor_creates_plan": {
        "description": "Does supervisor create an explicit plan before executing?",
        "scoring": {
            "2": "Explicit plan with steps outlined",
            "1": "Implicit planning evident in execution",
            "0": "No planning, jumps straight to execution"
        }
    },
    "delegates_with_context": {
        "description": "Does supervisor provide plan context when delegating?",
        "scoring": {
            "2": "Full context and subplan instructions provided",
            "1": "Partial context provided",
            "0": "No context, just delegates task"
        }
    },
    "supervisor_reflects": {
        "description": "Does supervisor reflect after delegation to decide next action?",
        "scoring": {
            "2": "Explicit reflection and decision reasoning",
            "1": "Implicit reflection (pauses, considers)",
            "0": "No reflection, continues immediately or ends"
        }
    },
    "parallel_delegation": {
        "description": "Does supervisor delegate parallel tasks?",
        "scoring": {
            "2": "Successfully delegates 2+ tasks in parallel",
            "1": "Attempts parallel delegation but sequential execution",
            "0": "Only sequential delegation, waits between tasks"
        }
    },
    "subagent_independence": {
        "description": "Does subagent create subplan and execute independently?",
        "scoring": {
            "2": "Subagent creates explicit subplan and executes multiple steps",
            "1": "Subagent executes multiple steps without explicit subplan",
            "0": "Subagent does single action and returns"
        }
    },
    "coordination_quality": {
        "description": "Overall coordination and workflow orchestration quality",
        "scoring": {
            "2": "Excellent orchestration, efficient parallel execution",
            "1": "Good coordination, mostly sequential",
            "0": "Poor coordination, disjointed execution"
        }
    }
}

def print_test_info():
    """Print test information and expected behaviors."""
    print("\n" + "="*80)
    print("DISTRIBUTED PLANNING & PARALLEL DELEGATION TEST")
    print("="*80)

    print("\n📋 TEST OBJECTIVES:")
    print("1. Supervisor creates a plan with multiple steps")
    print("2. Supervisor delegates step 1 to researcher with planning instructions")
    print("3. Researcher creates subplan and executes independently")
    print("4. Supervisor reflects after delegation")
    print("5. Supervisor decides: wait or delegate parallel task")
    print("6. Supervisor demonstrates parallel delegation if possible")

    print("\n📝 TEST PROMPTS AVAILABLE:")
    print("- V1 (Explicit): Detailed instructions for planning and parallel delegation")
    print("- V2 (Natural): Natural language, less prescriptive")
    print("- V3 (Implicit): Hints at parallel execution without explicit instructions")

    print("\n📊 EVALUATION CRITERIA:")
    for criterion, details in EVALUATION_CRITERIA.items():
        print(f"\n{criterion}:")
        print(f"  {details['description']}")
        for score, desc in details['scoring'].items():
            print(f"    {score}: {desc}")

    print("\n" + "="*80)
    print("EXPECTED BEHAVIORS BY CONFIGURATION")
    print("="*80)

    for config, behaviors in EXPECTED_BEHAVIORS.items():
        print(f"\n{config}:")
        for behavior_type, description in behaviors.items():
            print(f"  {behavior_type}: {description}")

    print("\n" + "="*80)

if __name__ == "__main__":
    print_test_info()

    print("\n\n" + "="*80)
    print("TEST PROMPT V1 (EXPLICIT)")
    print("="*80)
    print(TEST_PROMPT_V1_EXPLICIT)

    print("\n\n" + "="*80)
    print("TEST PROMPT V2 (NATURAL)")
    print("="*80)
    print(TEST_PROMPT_V2_NATURAL)

    print("\n\n" + "="*80)
    print("TEST PROMPT V3 (IMPLICIT)")
    print("="*80)
    print(TEST_PROMPT_V3_IMPLICIT)
