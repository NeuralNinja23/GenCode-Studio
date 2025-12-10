# app/learning/__init__.py
"""
Learning module - Pattern memory and quality improvement over time.
"""
from .pattern_store import (
    PatternStore,
    CodePattern,
    get_pattern_store,
    learn_from_success,
    get_learned_enhancement,
)

__all__ = [
    "PatternStore",
    "CodePattern",
    "get_pattern_store",
    "learn_from_success",
    "get_learned_enhancement",
]
