"""
Utility to load agent prompts from YAML files.

All imports are ABSOLUTE.
"""

import yaml
from pathlib import Path
from typing import Dict, Any


PROMPTS_DIR = Path("/Users/nicholaspate/Documents/01_Active/ATLAS/backend/src/prompts")


def load_agent_prompt(agent_name: str) -> str:
    """
    Load agent system prompt from YAML file.

    Args:
        agent_name: Name of agent YAML file (without .yaml extension)
            Examples: "global_supervisor", "research_agent", "analysis_agent"

    Returns:
        System prompt string from persona field

    Raises:
        FileNotFoundError: If YAML file doesn't exist
        KeyError: If 'persona' field is missing from YAML

    Example:
        >>> prompt = load_agent_prompt("research_agent")
        >>> print(prompt)
        You are a research specialist for ATLAS...
    """
    yaml_file = PROMPTS_DIR / f"{agent_name}.yaml"

    if not yaml_file.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {yaml_file}\n"
            f"Expected location: {PROMPTS_DIR}/{agent_name}.yaml"
        )

    with open(yaml_file, 'r') as f:
        config = yaml.safe_load(f)

    if 'persona' not in config:
        raise KeyError(
            f"'persona' field missing in {yaml_file}\n"
            f"YAML files must include a 'persona' field with the system prompt"
        )

    return config['persona']


def load_agent_config(agent_name: str) -> Dict[str, Any]:
    """
    Load full agent configuration from YAML file.

    Returns complete configuration including:
    - agent_type: Agent type identifier
    - version: Configuration version
    - persona: System prompt text
    - capabilities: List of agent capabilities
    - Any other custom fields defined in YAML

    Args:
        agent_name: Name of agent YAML file (without .yaml extension)

    Returns:
        Dictionary with all YAML configuration fields

    Raises:
        FileNotFoundError: If YAML file doesn't exist

    Example:
        >>> config = load_agent_config("research_agent")
        >>> print(config['agent_type'])
        Research Agent
        >>> print(config['capabilities'])
        ['Web search and information gathering', ...]
    """
    yaml_file = PROMPTS_DIR / f"{agent_name}.yaml"

    if not yaml_file.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {yaml_file}\n"
            f"Expected location: {PROMPTS_DIR}/{agent_name}.yaml"
        )

    with open(yaml_file, 'r') as f:
        return yaml.safe_load(f)


def validate_prompt_file(agent_name: str) -> bool:
    """
    Validate that a prompt file exists and has required fields.

    Args:
        agent_name: Name of agent YAML file (without .yaml extension)

    Returns:
        True if file exists and has 'persona' field, False otherwise

    Example:
        >>> if validate_prompt_file("research_agent"):
        ...     prompt = load_agent_prompt("research_agent")
    """
    try:
        yaml_file = PROMPTS_DIR / f"{agent_name}.yaml"
        if not yaml_file.exists():
            return False

        with open(yaml_file, 'r') as f:
            config = yaml.safe_load(f)

        return 'persona' in config
    except Exception:
        return False
