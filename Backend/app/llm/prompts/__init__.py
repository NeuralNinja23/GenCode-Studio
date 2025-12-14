# app/llm/prompts/__init__.py
"""
Agent prompts - organized by agent.
"""
from .marcus import MARCUS_PROMPT, MARCUS_SUPERVISION_PROMPT
from .derek import DEREK_PROMPT, DEREK_TESTING_PROMPT
from .luna import LUNA_PROMPT, LUNA_TESTING_PROMPT
from .victoria import VICTORIA_PROMPT

__all__ = [
    "MARCUS_PROMPT", "MARCUS_SUPERVISION_PROMPT",
    "DEREK_PROMPT", "DEREK_TESTING_PROMPT",
    "LUNA_PROMPT", "LUNA_TESTING_PROMPT",
    "VICTORIA_PROMPT",
]


