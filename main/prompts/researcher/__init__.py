"""
Researcher Prompt Package

This package contains multiple versions of the researcher prompt:
- benchmark_researcher_prompt: Production baseline (Enhanced V3)
- challenger_researcher_prompt_1: Experimental optimization template

By default, this package exports the benchmark version.
To use challenger versions, import them explicitly:

    from prompts.researcher.challenger_researcher_prompt_1 import get_researcher_prompt as get_challenger_prompt
"""

# Export benchmark version by default
from prompts.researcher.benchmark_researcher_prompt import get_researcher_prompt

__all__ = ['get_researcher_prompt']
