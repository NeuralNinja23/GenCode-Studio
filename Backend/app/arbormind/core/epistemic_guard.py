# app/arbormind/core/epistemic_guard.py
"""
ArborMind Epistemic Guard - Core Truth Protection
(Formerly boundary.py)

REQUIREMENT 1: Hard Epistemic Boundary (Non-Negotiable)

This module enforces the separation between:
- OBSERVATION (what happened) → CAN be read by anyone (Fact)
- COGNITION DATA (decisions, verdicts, confidence) → PRIVATE to execution context

Properties that make it impossible (not unlikely) for ArborMind to confuse truth with intent:
1. "Intent" tables are strictly forbidden from being treated as "Facts"
2. Observation logic must never depend on success/failure judgment

INVARIANT: If it can be joined, it will be abused.
INVARIANT: Observation MUST NOT depend on 'decisions' table.
"""

from typing import Set, FrozenSet


# ═══════════════════════════════════════════════════════════════════════════════
# BOUNDARY DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Tables that contain COGNITION DATA (decisions, intent, preference)
# Observation components should generally NOT query these to determine 'Truth'
FORBIDDEN_TABLES: FrozenSet[str] = frozenset({
    "decisions",           # Proto-V vectors - intent data
    "supervisor_verdicts", # Preference shaping - approval data
    "branches",            # Contains attention, entropy (reasoning state)
})

# Columns that contain COGNITION DATA
# If these appear in any query from a 'fact-finding' tool, it's a violation
FORBIDDEN_COLUMNS: FrozenSet[str] = frozenset({
    "confidence",          # Reasoning confidence
    "verdict",             # Approval state
    "quality_score",       # Quality judgment
    "rejection_reasons",   # Intent data
    "attention",           # Reasoning state
    "reason",              # Decision rationale
    "action",              # Action taken (intent)
    "outcome",             # Success/failure judgment (unless strictly binary fact)
})

# ═══════════════════════════════════════════════════════════════════════════════
# BOUNDARY ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class EpistemicBoundaryViolation(Exception):
    """
    Raised when code attempts to cross the epistemic boundary.
    This is a HARD failure - not recoverable.
    """
    pass


def assert_not_cognition_data(table_name: str):
    """
    Assert that a table is not cognition data.
    Call this before any 'truth extraction' operation.
    """
    if table_name in FORBIDDEN_TABLES:
        raise EpistemicBoundaryViolation(
            f"BOUNDARY VIOLATION: Table '{table_name}' contains cognition data (Intent). "
            f"Truth access MUST NOT read this table to establish fact."
        )


def assert_no_forbidden_columns(column_names: Set[str]):
    """
    Assert that no forbidden columns are being accessed.
    """
    violations = column_names & FORBIDDEN_COLUMNS
    if violations:
        raise EpistemicBoundaryViolation(
            f"BOUNDARY VIOLATION: Columns {violations} contain cognition data (Intent). "
            f"Truth access MUST NOT read these columns."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# BOUNDARY DOCUMENTATION
# ═══════════════════════════════════════════════════════════════════════════════

BOUNDARY_DOCUMENTATION = """
# ArborMind Epistemic Guard

## The Rule

ArborMind's fact-finding layer MUST NOT have access to:
- Decisions (what the system chose to do)
- Supervisor verdicts (approval/rejection states)
- Action reasons (why something was done)
- Confidence scores (how certain the system was)
- Approval states (whether something was approved)

## Why

If the observation layer determines 'What Happened' based on 'What We Wanted To Happen',
it will report success even when reality failed.

## The Test

"If I disappear for 6 months and come back, can ArborMind still tell me
what actually breaks — without knowing what we tried to do about it?"

If yes → boundary is maintained.
If no → boundary is violated.
"""

def print_boundary_info():
    """Print boundary documentation to stdout."""
    print(BOUNDARY_DOCUMENTATION)
    print("\n" + "="*70)
    print("FORBIDDEN TABLES:", ", ".join(sorted(FORBIDDEN_TABLES)))
    print("FORBIDDEN COLUMNS:", ", ".join(sorted(FORBIDDEN_COLUMNS)))
    print("="*70)
