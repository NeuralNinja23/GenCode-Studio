# app/arbormind/learning/failure_ontology.py
"""
ArborMind 7-Axis Canonical Failure Ontology

Phase 3.5: Semantic Stratification

This module defines the 7 orthogonal axes for classifying failures.
Each axis is independent — no axis may be inferred from another.

CORE PRINCIPLE:
    "Name reality exactly as it is."
    
INVARIANTS:
    - All enums are frozen (str, Enum for serialization)
    - All axes are mandatory for new failures
    - All axes are nullable for historical failures
    - No axis influences execution behavior
    - No axis enables learning (Phase-4 only)

THE 7 AXES:
    A. Execution Layer     — WHERE the failure occurred
    B. Authority Boundary  — WHO had authority over the failing action
    C. Gating Semantics    — WHETHER the failure affects run success (CRITICAL)
    D. Truth Domain        — WHAT kind of truth was violated
    E. Temporal Position   — WHEN relative to artifact existence
    F. Artifact Impact     — WHAT the failure affected
    G. Repeatability       — WHETHER the failure is stable

This ontology resolves:
    - SUCCESS runs with HARD failures (Axis C)
    - F7 inflation from validators (Axis A + C)
    - syntaxvalidator paradox (Axis A: OBSERVATION_LAYER + Axis C: NON_GATING)
"""

from enum import Enum, unique
from dataclasses import dataclass
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════════
# ONTOLOGY VERSION - INCREMENT ON BREAKING CHANGES
# ═══════════════════════════════════════════════════════════════════════════════
ONTOLOGY_VERSION = 1  # v1: Initial 7-axis implementation


# ═══════════════════════════════════════════════════════════════════════════════
# AXIS A: EXECUTION LAYER
# Defines WHERE the failure occurred in the execution stack
# ═══════════════════════════════════════════════════════════════════════════════

@unique
class ExecutionLayer(str, Enum):
    """
    Where in the execution stack did the failure occur?
    
    This axis replaces the overloaded meaning currently collapsed into F7.
    """
    
    # Failure occurred during LLM-mediated artifact synthesis
    # Example: Derek generating a model file
    GENERATION_LAYER = "generation"
    
    # Failure occurred inside a deterministic tool invocation
    # Example: filewriter failing to write
    TOOL_EXECUTION_LAYER = "tool_execution"
    
    # Failure occurred after artifacts already existed
    # Example: pytest finding bugs in generated code
    POST_EXECUTION_LAYER = "post_execution"
    
    # Failure occurred during environment-dependent execution
    # Example: npm install failing due to missing Node.js
    RUNTIME_LAYER = "runtime"
    
    # Failure occurred while attempting to observe, validate, or measure
    # Example: syntaxvalidator checking code that may or may not be correct
    # THIS IS THE KEY LAYER FOR RESOLVING VALIDATOR NOISE
    OBSERVATION_LAYER = "observation"


# ═══════════════════════════════════════════════════════════════════════════════
# AXIS B: AUTHORITY BOUNDARY
# Defines WHO had authority over the failing action
# ═══════════════════════════════════════════════════════════════════════════════

@unique
class AuthorityBoundary(str, Enum):
    """
    Who had authority over the action that failed?
    
    Authority is NEVER inferred from failure content.
    It must be known at invocation time.
    """
    
    # Action executed by FAST-V2 infrastructure
    # Example: Pipeline orchestration, step sequencing
    SYSTEM_AUTHORITY = "system"
    
    # Action executed by a specialized agent
    # Example: Victoria generating frontend, Derek generating backend
    AGENT_AUTHORITY = "agent"
    
    # Action executed by Marcus or supervision rules
    # Example: Quality rejection, invariant enforcement
    SUPERVISOR_AUTHORITY = "supervisor"
    
    # Action governed by external runtime or OS state
    # Example: File system permissions, network availability
    ENVIRONMENT_AUTHORITY = "environment"


# ═══════════════════════════════════════════════════════════════════════════════
# AXIS C: GATING SEMANTICS (CRITICAL)
# Defines WHETHER the failure participates in run termination logic
# ═══════════════════════════════════════════════════════════════════════════════

@unique
class GatingSemantics(str, Enum):
    """
    Does this failure affect run success semantics?
    
    THIS IS THE CRITICAL AXIS that resolves the paradox:
        "SUCCESS run with HARD failures"
    
    The paradox exists because is_hard_failure conflates:
        - "Did the tool fail?" (execution truth)
        - "Does this block the run?" (gating semantics)
    
    These are orthogonal concerns.
    """
    
    # BLOCKING: Execution cannot continue past this point
    # The run MUST fail if this failure occurs
    # Example: subagentcaller timeout, filewriter permission denied
    BLOCKING = "blocking"
    
    # NON_BLOCKING: Execution continues regardless of outcome
    # The failure is recorded but doesn't stop the pipeline
    # Example: pytestrunner finding test failures (tests still run)
    NON_BLOCKING = "non_blocking"
    
    # NON_GATING: Run success semantics explicitly IGNORE this failure
    # The failure is telemetry-only — it cannot affect run status
    # Example: syntaxvalidator, static_code_validator, codeviewer
    # THIS IS THE KEY VALUE FOR RESOLVING syntaxvalidator PARADOX
    NON_GATING = "non_gating"


# ═══════════════════════════════════════════════════════════════════════════════
# AXIS D: TRUTH DOMAIN
# Defines WHAT kind of truth was violated
# ═══════════════════════════════════════════════════════════════════════════════

@unique
class TruthDomain(str, Enum):
    """
    What kind of truth was violated?
    
    This prevents validators from masquerading as execution failures.
    Observation truth ≠ Execution truth.
    """
    
    # Something that was supposed to execute did not execute correctly
    # Example: Tool crashed, process exited non-zero
    EXECUTION_TRUTH = "execution"
    
    # A structural constraint was violated
    # Example: Malformed JSON, invalid HDAP syntax
    STRUCTURAL_TRUTH = "structural"
    
    # A declared invariant failed
    # Example: Missing required field, schema mismatch
    # NOTE: Execution may succeed, artifacts may exist, supervisor may approve
    INVARIANT_TRUTH = "invariant"
    
    # The system failed to observe or validate something
    # WITHOUT asserting it was wrong
    # Example: syntaxvalidator timeout, linter unavailable
    OBSERVATIONAL_TRUTH = "observational"
    
    # The system lacks the ability to perform the requested action
    # Example: Python not installed, npm not found
    CAPABILITY_TRUTH = "capability"


# ═══════════════════════════════════════════════════════════════════════════════
# AXIS E: TEMPORAL POSITION
# Defines WHEN the failure occurred relative to artifact existence
# ═══════════════════════════════════════════════════════════════════════════════

@unique
class TemporalPosition(str, Enum):
    """
    When did the failure occur relative to artifact materialization?
    
    This is critical for distinguishing:
        - "Nothing was created"
        - "Something was created but flagged"
        - "Something exists and works despite flags"
    """
    
    # Failure occurred before any artifacts were created
    # Example: Prompt construction failed, dependency missing
    PRE_MATERIALIZATION = "pre"
    
    # Failure occurred while artifacts were being created
    # Example: File write interrupted, token limit during generation
    DURING_MATERIALIZATION = "during"
    
    # Failure occurred after artifacts already exist
    # Example: Validator rejected existing code, test failed on generated code
    POST_MATERIALIZATION = "post"


# ═══════════════════════════════════════════════════════════════════════════════
# AXIS F: ARTIFACT IMPACT
# Defines WHAT the failure affected
# ═══════════════════════════════════════════════════════════════════════════════

@unique
class ArtifactImpact(str, Enum):
    """
    What did the failure affect in terms of artifacts?
    
    Artifact validity is NOT inferred from this axis.
    This is observational only.
    """
    
    # No artifacts were affected by this failure
    # Example: Observation-only validator, telemetry tool
    NO_ARTIFACT_IMPACT = "none"
    
    # Some artifacts may be affected, but not all
    # Example: One of five models failed validation
    PARTIAL_ARTIFACT_IMPACT = "partial"
    
    # All artifacts from this step are invalidated
    # Example: Step-level hard failure, complete rollback
    FULL_ARTIFACT_INVALIDATION = "full"
    
    # It's unclear whether artifacts are valid
    # Example: Validator timed out, inconclusive check
    ARTIFACT_AMBIGUITY = "ambiguous"


# ═══════════════════════════════════════════════════════════════════════════════
# AXIS G: REPEATABILITY SIGNATURE
# Defines WHETHER the failure is stable
# ═══════════════════════════════════════════════════════════════════════════════

@unique
class RepeatabilitySignature(str, Enum):
    """
    Is this failure stable/repeatable?
    
    This is observational only — it does NOT enable retries.
    It exists for future learning (Phase-4) to avoid false patterns.
    """
    
    # Same input always produces this failure
    # Example: Invariant violation, parse error
    DETERMINISTIC = "deterministic"
    
    # Same input may or may not produce this failure
    # Example: Network timeout, rate limit
    NON_DETERMINISTIC = "non_deterministic"
    
    # Failure appears and disappears without pattern
    # Example: Race condition, timing-dependent
    FLAKY = "flaky"
    
    # Repeatability has not been determined
    # Default for new failures
    UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# COMPOSITE CLASSIFICATION RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class FailureOntologyClassification:
    """
    Complete 7-axis classification of a failure.
    
    Immutable once created.
    All axes are mandatory for new classifications.
    """
    
    # Axis A: Where did it fail?
    execution_layer: ExecutionLayer
    
    # Axis B: Who had authority?
    authority_boundary: AuthorityBoundary
    
    # Axis C: Does it affect run success? (CRITICAL)
    gating_semantics: GatingSemantics
    
    # Axis D: What kind of truth was violated?
    truth_domain: TruthDomain
    
    # Axis E: When relative to artifact existence?
    temporal_position: TemporalPosition
    
    # Axis F: What artifacts were affected?
    artifact_impact: ArtifactImpact
    
    # Axis G: Is it repeatable?
    repeatability_sig: RepeatabilitySignature
    
    # Optional: Recommended F-class based on ontology
    # May differ from originally assigned class
    recommended_fclass: Optional[str] = None
    
    def is_blocking(self) -> bool:
        """Should this failure stop the run?"""
        return self.gating_semantics == GatingSemantics.BLOCKING
    
    def is_observation_only(self) -> bool:
        """Is this purely observational (no execution impact)?"""
        return (
            self.execution_layer == ExecutionLayer.OBSERVATION_LAYER
            and self.gating_semantics == GatingSemantics.NON_GATING
            and self.artifact_impact == ArtifactImpact.NO_ARTIFACT_IMPACT
        )
    
    def explains_hard_success_paradox(self) -> bool:
        """
        Does this classification explain a HARD failure in a SUCCESS run?
        
        Returns True if:
        - Failure is NON_GATING (doesn't affect run success)
        - OR failure is observational-only
        """
        return (
            self.gating_semantics == GatingSemantics.NON_GATING
            or self.is_observation_only()
        )


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION & STATIC ASSERTIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Ensure all enums have expected sizes
assert len(ExecutionLayer) == 5, "ExecutionLayer must have exactly 5 values"
assert len(AuthorityBoundary) == 4, "AuthorityBoundary must have exactly 4 values"
assert len(GatingSemantics) == 3, "GatingSemantics must have exactly 3 values"
assert len(TruthDomain) == 5, "TruthDomain must have exactly 5 values"
assert len(TemporalPosition) == 3, "TemporalPosition must have exactly 3 values"
assert len(ArtifactImpact) == 4, "ArtifactImpact must have exactly 4 values"
assert len(RepeatabilitySignature) == 4, "RepeatabilitySignature must have exactly 4 values"

# Total: 5 + 4 + 3 + 5 + 3 + 4 + 4 = 28 enum values across 7 axes


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Version
    "ONTOLOGY_VERSION",
    
    # Axis A
    "ExecutionLayer",
    
    # Axis B
    "AuthorityBoundary",
    
    # Axis C (CRITICAL)
    "GatingSemantics",
    
    # Axis D
    "TruthDomain",
    
    # Axis E
    "TemporalPosition",
    
    # Axis F
    "ArtifactImpact",
    
    # Axis G
    "RepeatabilitySignature",
    
    # Composite
    "FailureOntologyClassification",
]
