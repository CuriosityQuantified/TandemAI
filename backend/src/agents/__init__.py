# ATLAS Agent System
# Hierarchical multi-agent system for task decomposition and execution

# Base classes still needed for compatibility
from .base import BaseAgent, BaseSupervisor, AgentStatus, TaskResult, Task

# NEW: Deep Agents supervisor (primary implementation)
from .supervisor_agent import create_supervisor_agent, invoke_supervisor

# OLD: Letta-based supervisor (archived, commented out during migration)
# from .supervisor import Supervisor

# Note: ResearchAgent, AnalysisAgent, WritingAgent deprecated - now handled via LangChain tools
# from .research import ResearchAgent
# from .analysis import AnalysisAgent
# from .writing import WritingAgent
# from .agent_factory import LettaAgentFactory  # Archived in backend/archive/letta/

__all__ = [
    # Base classes
    'BaseAgent',
    'BaseSupervisor',

    # Data models
    'AgentStatus',
    'TaskResult',
    'Task',

    # NEW Deep Agents implementation
    'create_supervisor_agent',
    'invoke_supervisor',

    # OLD: Letta-based supervisor (archived)
    # 'Supervisor',

    # Deprecated: Letta-based agents (archived)
    # 'ResearchAgent',
    # 'AnalysisAgent',
    # 'WritingAgent',
    # 'LettaAgentFactory'
]