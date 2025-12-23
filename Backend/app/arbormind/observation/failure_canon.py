# app/arbormind/learning/failure_canon.py
"""
ArborMind Failure Class Canon (F1–F9)

REQUIREMENT 3: Failure Class Canon as Law

Properties:
- Finite alphabet (exactly 9 classes)
- One and only one primary class per failure
- Immutable definitions
- Code-defined, versioned, referenced by ID

INVARIANT: This file defines the ONLY legal failure classes.
INVARIANT: No free-form failure types allowed.
INVARIANT: Schema version frozen once deployed.
"""

from enum import Enum, unique
from dataclasses import dataclass
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════════
# CANON VERSION - FROZEN ONCE DEPLOYED
# ═══════════════════════════════════════════════════════════════════════════════
CANON_VERSION = 1  # NEVER INCREMENT WITHOUT MIGRATION


@unique
class FailureClass(Enum):
    """
    The 9 canonical failure classes.
    
    Referenced by ID (e.g., F1, F2), not by text.
    Each has exactly one semantic meaning.
    """
    
    # ───────────────────────────────────────────────────────────────────────────
    # F1: INVARIANT_VIOLATION
    # The output violates a declared invariant (e.g., missing required field)
    # ───────────────────────────────────────────────────────────────────────────
    F1_INVARIANT_VIOLATION = "F1"
    
    # ───────────────────────────────────────────────────────────────────────────
    # F2: PARSE_FAILURE
    # The output could not be parsed (e.g., malformed JSON, invalid HDAP)
    # ───────────────────────────────────────────────────────────────────────────
    F2_PARSE_FAILURE = "F2"
    
    # ───────────────────────────────────────────────────────────────────────────
    # F3: TRUNCATION
    # The output was cut off before completion (token limit, timeout)
    # ───────────────────────────────────────────────────────────────────────────
    F3_TRUNCATION = "F3"
    
    # ───────────────────────────────────────────────────────────────────────────
    # F4: QUALITY_REJECTION
    # Supervisor rejected output for quality reasons (not structural)
    # ───────────────────────────────────────────────────────────────────────────
    F4_QUALITY_REJECTION = "F4"
    
    # ───────────────────────────────────────────────────────────────────────────
    # F5: TIMEOUT
    # Operation exceeded time budget
    # ───────────────────────────────────────────────────────────────────────────
    F5_TIMEOUT = "F5"
    
    # ───────────────────────────────────────────────────────────────────────────
    # F6: DEPENDENCY_MISSING
    # Required upstream artifact/context was not available
    # ───────────────────────────────────────────────────────────────────────────
    F6_DEPENDENCY_MISSING = "F6"
    
    # ───────────────────────────────────────────────────────────────────────────
    # F7: RUNTIME_EXCEPTION
    # Unhandled exception during execution (not LLM output, but code crash)
    # ───────────────────────────────────────────────────────────────────────────
    F7_RUNTIME_EXCEPTION = "F7"
    
    # ───────────────────────────────────────────────────────────────────────────
    # F8: SEMANTIC_CONFLICT
    # Output conflicts with existing artifacts (e.g., duplicate entity names)
    # ───────────────────────────────────────────────────────────────────────────
    F8_SEMANTIC_CONFLICT = "F8"
    
    # ───────────────────────────────────────────────────────────────────────────
    # F9: EXTERNAL_FAILURE
    # External system failed (API, database, file system)
    # ───────────────────────────────────────────────────────────────────────────
    F9_EXTERNAL_FAILURE = "F9"


@unique
class FailureScope(Enum):
    """
    REQUIREMENT 5: Explicit Scope Assignment
    
    Every failure MUST declare where truth lives.
    No inference later. No retroactive correction.
    """
    
    # Failure is local to a single entity (e.g., one model file)
    ENTITY_LOCAL = "entity_local"
    
    # Failure is local to a single step (e.g., backend_models)
    STEP_LOCAL = "step_local"
    
    # Failure spans multiple steps (e.g., frontend depends on backend)
    CROSS_STEP = "cross_step"
    
    # Failure is systemic (e.g., token limits, API failures)
    SYSTEMIC = "systemic"


@dataclass(frozen=True)
class FailureClassDefinition:
    """
    Immutable definition of a failure class.
    
    These are the canonical definitions. They cannot be changed at runtime.
    """
    id: str
    name: str
    description: str
    is_retryable: bool  # Can this failure type be retried without mutation?
    typical_scope: FailureScope  # Most common scope for this class


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL DEFINITIONS - DO NOT MODIFY
# ═══════════════════════════════════════════════════════════════════════════════
FAILURE_CLASS_DEFINITIONS: dict[FailureClass, FailureClassDefinition] = {
    FailureClass.F1_INVARIANT_VIOLATION: FailureClassDefinition(
        id="F1",
        name="Invariant Violation",
        description="Output violates a declared invariant",
        is_retryable=True,
        typical_scope=FailureScope.ENTITY_LOCAL,
    ),
    FailureClass.F2_PARSE_FAILURE: FailureClassDefinition(
        id="F2",
        name="Parse Failure",
        description="Output could not be parsed",
        is_retryable=True,
        typical_scope=FailureScope.STEP_LOCAL,
    ),
    FailureClass.F3_TRUNCATION: FailureClassDefinition(
        id="F3",
        name="Truncation",
        description="Output was cut off before completion",
        is_retryable=True,
        typical_scope=FailureScope.STEP_LOCAL,
    ),
    FailureClass.F4_QUALITY_REJECTION: FailureClassDefinition(
        id="F4",
        name="Quality Rejection",
        description="Supervisor rejected output for quality reasons",
        is_retryable=True,
        typical_scope=FailureScope.ENTITY_LOCAL,
    ),
    FailureClass.F5_TIMEOUT: FailureClassDefinition(
        id="F5",
        name="Timeout",
        description="Operation exceeded time budget",
        is_retryable=True,
        typical_scope=FailureScope.SYSTEMIC,
    ),
    FailureClass.F6_DEPENDENCY_MISSING: FailureClassDefinition(
        id="F6",
        name="Dependency Missing",
        description="Required upstream artifact was not available",
        is_retryable=False,
        typical_scope=FailureScope.CROSS_STEP,
    ),
    FailureClass.F7_RUNTIME_EXCEPTION: FailureClassDefinition(
        id="F7",
        name="Runtime Exception",
        description="Unhandled exception during execution",
        is_retryable=False,
        typical_scope=FailureScope.SYSTEMIC,
    ),
    FailureClass.F8_SEMANTIC_CONFLICT: FailureClassDefinition(
        id="F8",
        name="Semantic Conflict",
        description="Output conflicts with existing artifacts",
        is_retryable=True,
        typical_scope=FailureScope.CROSS_STEP,
    ),
    FailureClass.F9_EXTERNAL_FAILURE: FailureClassDefinition(
        id="F9",
        name="External Failure",
        description="External system failed",
        is_retryable=True,
        typical_scope=FailureScope.SYSTEMIC,
    ),
}


def get_failure_class(class_id: str) -> Optional[FailureClass]:
    """
    Get FailureClass by ID string (e.g., "F1").
    
    Returns None if not found (illegal ID).
    """
    for fc in FailureClass:
        if fc.value == class_id:
            return fc
    return None


def get_definition(fc: FailureClass) -> FailureClassDefinition:
    """Get the canonical definition for a failure class."""
    return FAILURE_CLASS_DEFINITIONS[fc]


def validate_class_id(class_id: str) -> bool:
    """Check if a class ID is legal."""
    return get_failure_class(class_id) is not None


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC ASSERTIONS - Enforced at import time
# ═══════════════════════════════════════════════════════════════════════════════
assert len(FailureClass) == 9, "Canon must have exactly 9 failure classes"
assert len(FAILURE_CLASS_DEFINITIONS) == 9, "All classes must have definitions"
assert all(
    fc in FAILURE_CLASS_DEFINITIONS for fc in FailureClass
), "Every FailureClass must have a definition"
