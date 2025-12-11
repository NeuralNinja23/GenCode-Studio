# app/learning/__init__.py
"""
Learning module - Pattern memory, failure tracking, and quality improvement over time.

Includes:
- PatternStore: Successful patterns for positive learning
- FailureStore: Anti-patterns for avoiding repeated mistakes
- VVectorStore: Routing decision learning for self-evolution
"""
from .pattern_store import (
    PatternStore,
    CodePattern,
    get_pattern_store,
    learn_from_success,
    get_learned_enhancement,
)
from .failure_store import (
    FailureStore,
    FailurePattern,
    get_failure_store,
)
from .v_vector_store import (
    VVectorStore,
    VVectorDecision,
    EvolvedVVector,
    get_v_vector_store,
    record_routing_decision,
    record_decision_outcome,
    get_evolved_options,
)

__all__ = [
    # Pattern Store (Success Learning)
    "PatternStore",
    "CodePattern",
    "get_pattern_store",
    "learn_from_success",
    "get_learned_enhancement",
    # Failure Store (Anti-Pattern Learning)
    "FailureStore",
    "FailurePattern",
    "get_failure_store",
    # V-Vector Store (Routing Evolution)
    "VVectorStore",
    "VVectorDecision",
    "EvolvedVVector",
    "get_v_vector_store",
    "record_routing_decision",
    "record_decision_outcome",
    "get_evolved_options",
]

