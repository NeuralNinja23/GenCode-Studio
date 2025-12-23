# app/arbormind/learning/ontology_classifier.py
"""
ArborMind Ontology Classifier

Deterministically classifies failures across all 7 axes.

INVARIANTS:
    - PURE FUNCTION: No side effects
    - DETERMINISTIC: Same input → same output (always)
    - NO LLM: Pattern matching only
    - NO HEURISTICS WITH INTENT: Rules are explicit
    - ORDER-STABLE: First match wins

This classifier NEVER:
    - Calls ArborMind
    - Influences execution
    - Changes planner behavior
    - Enables retries
    
It is NAMING REALITY, not fixing it.
"""

import re
from typing import Optional, Dict
from dataclasses import dataclass

from .failure_ontology import (
    ONTOLOGY_VERSION,
    ExecutionLayer,
    AuthorityBoundary,
    GatingSemantics,
    TruthDomain,
    TemporalPosition,
    ArtifactImpact,
    RepeatabilitySignature,
    FailureOntologyClassification,
)
from .failure_canon import FailureClass


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL → GATING SEMANTICS MAPPING (CRITICAL)
# This resolves the syntaxvalidator paradox
# ═══════════════════════════════════════════════════════════════════════════════

TOOL_GATING_RULES: Dict[str, GatingSemantics] = {
    # ─────────────────────────────────────────────────────────────────────────
    # BLOCKING: Fatal to run success
    # If these tools fail, the run MUST fail
    # ─────────────────────────────────────────────────────────────────────────
    "subagentcaller": GatingSemantics.BLOCKING,
    "filewriter": GatingSemantics.BLOCKING,
    "tool_sub_agent_caller": GatingSemantics.BLOCKING,
    "artifact_handler": GatingSemantics.BLOCKING,
    "hdap_parser": GatingSemantics.BLOCKING,
    
    # ─────────────────────────────────────────────────────────────────────────
    # NON_BLOCKING: Execution continues, failure is recorded
    # These failures count but don't stop the pipeline
    # ─────────────────────────────────────────────────────────────────────────
    "pytestrunner": GatingSemantics.NON_BLOCKING,
    "playwrightrunner": GatingSemantics.NON_BLOCKING,
    "pytest_runner": GatingSemantics.NON_BLOCKING,
    "playwright_runner": GatingSemantics.NON_BLOCKING,
    "test_runner": GatingSemantics.NON_BLOCKING,
    
    # ─────────────────────────────────────────────────────────────────────────
    # NON_GATING: Telemetry only, run success ignores
    # These are observation tools — their failures are informational only
    # THIS IS THE KEY BUCKET FOR syntaxvalidator
    # ─────────────────────────────────────────────────────────────────────────
    "syntaxvalidator": GatingSemantics.NON_GATING,
    "syntax_validator": GatingSemantics.NON_GATING,
    "static_code_validator": GatingSemantics.NON_GATING,
    "codeviewer": GatingSemantics.NON_GATING,
    "code_viewer": GatingSemantics.NON_GATING,
    "filereader": GatingSemantics.NON_GATING,
    "file_reader": GatingSemantics.NON_GATING,
    "filelister": GatingSemantics.NON_GATING,
    "file_lister": GatingSemantics.NON_GATING,
    "dbschemareader": GatingSemantics.NON_GATING,
    "db_schema_reader": GatingSemantics.NON_GATING,
}

# Default for unknown tools
DEFAULT_GATING = GatingSemantics.NON_BLOCKING


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL → EXECUTION LAYER MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

TOOL_LAYER_RULES: Dict[str, ExecutionLayer] = {
    # Generation Layer: LLM-mediated artifact synthesis
    "subagentcaller": ExecutionLayer.GENERATION_LAYER,
    "tool_sub_agent_caller": ExecutionLayer.GENERATION_LAYER,
    
    # Tool Execution Layer: Deterministic tool invocations
    "filewriter": ExecutionLayer.TOOL_EXECUTION_LAYER,
    "file_writer": ExecutionLayer.TOOL_EXECUTION_LAYER,
    "artifact_handler": ExecutionLayer.TOOL_EXECUTION_LAYER,
    "hdap_parser": ExecutionLayer.TOOL_EXECUTION_LAYER,
    
    # Post-Execution Layer: After artifacts exist
    "pytestrunner": ExecutionLayer.POST_EXECUTION_LAYER,
    "playwrightrunner": ExecutionLayer.POST_EXECUTION_LAYER,
    "pytest_runner": ExecutionLayer.POST_EXECUTION_LAYER,
    "playwright_runner": ExecutionLayer.POST_EXECUTION_LAYER,
    "test_runner": ExecutionLayer.POST_EXECUTION_LAYER,
    
    # Runtime Layer: Environment-dependent
    "environment_guard": ExecutionLayer.RUNTIME_LAYER,
    "npm_runner": ExecutionLayer.RUNTIME_LAYER,
    "pip_runner": ExecutionLayer.RUNTIME_LAYER,
    
    # Observation Layer: Validators and observers
    "syntaxvalidator": ExecutionLayer.OBSERVATION_LAYER,
    "syntax_validator": ExecutionLayer.OBSERVATION_LAYER,
    "static_code_validator": ExecutionLayer.OBSERVATION_LAYER,
    "codeviewer": ExecutionLayer.OBSERVATION_LAYER,
    "code_viewer": ExecutionLayer.OBSERVATION_LAYER,
    "filereader": ExecutionLayer.OBSERVATION_LAYER,
    "file_reader": ExecutionLayer.OBSERVATION_LAYER,
    "filelister": ExecutionLayer.OBSERVATION_LAYER,
    "file_lister": ExecutionLayer.OBSERVATION_LAYER,
    "dbschemareader": ExecutionLayer.OBSERVATION_LAYER,
    "db_schema_reader": ExecutionLayer.OBSERVATION_LAYER,
}

# Default for unknown tools
DEFAULT_LAYER = ExecutionLayer.TOOL_EXECUTION_LAYER


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL → AUTHORITY BOUNDARY MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

TOOL_AUTHORITY_RULES: Dict[str, AuthorityBoundary] = {
    # Agent Authority: Specialized agents
    "subagentcaller": AuthorityBoundary.AGENT_AUTHORITY,
    "tool_sub_agent_caller": AuthorityBoundary.AGENT_AUTHORITY,
    
    # Supervisor Authority: Marcus and supervision rules
    "marcus_supervisor": AuthorityBoundary.SUPERVISOR_AUTHORITY,
    "supervisor": AuthorityBoundary.SUPERVISOR_AUTHORITY,
    "quality_gate": AuthorityBoundary.SUPERVISOR_AUTHORITY,
    
    # Environment Authority: External runtime
    "environment_guard": AuthorityBoundary.ENVIRONMENT_AUTHORITY,
    "npm_runner": AuthorityBoundary.ENVIRONMENT_AUTHORITY,
    "pip_runner": AuthorityBoundary.ENVIRONMENT_AUTHORITY,
}

# Default for unknown tools
DEFAULT_AUTHORITY = AuthorityBoundary.SYSTEM_AUTHORITY


# ═══════════════════════════════════════════════════════════════════════════════
# F-CLASS → TRUTH DOMAIN MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

FCLASS_TRUTH_RULES: Dict[str, TruthDomain] = {
    "F1": TruthDomain.INVARIANT_TRUTH,
    "F2": TruthDomain.STRUCTURAL_TRUTH,
    "F3": TruthDomain.STRUCTURAL_TRUTH,  # Truncation is structural
    "F4": TruthDomain.OBSERVATIONAL_TRUTH,  # Quality is observation
    "F5": TruthDomain.EXECUTION_TRUTH,
    "F6": TruthDomain.CAPABILITY_TRUTH,
    "F7": TruthDomain.EXECUTION_TRUTH,
    "F8": TruthDomain.INVARIANT_TRUTH,
    "F9": TruthDomain.CAPABILITY_TRUTH,
}

# Default for unknown classes
DEFAULT_TRUTH = TruthDomain.EXECUTION_TRUTH


# ═══════════════════════════════════════════════════════════════════════════════
# STEP → AGENT MAPPING (for authority inference)
# ═══════════════════════════════════════════════════════════════════════════════

STEP_AGENT_RULES: Dict[str, str] = {
    "backend_models": "Derek",
    "backend_routers": "Derek",
    "frontend_components": "Victoria",
    "frontend_pages": "Victoria",
    "frontend_integration": "Victoria",
    "testing_backend": "Derek",
    "testing_frontend": "Luna",
    "architecture": "Marcus",
    "analysis": "Marcus",
}


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSIFIER PATTERNS (for error message analysis)
# ═══════════════════════════════════════════════════════════════════════════════

# Patterns that indicate NON_DETERMINISTIC repeatability
NON_DETERMINISTIC_PATTERNS = [
    r"timeout",
    r"rate.?limit",
    r"connection.?(refused|reset|timeout)",
    r"network.?error",
    r"503|502|504",
    r"service.?unavailable",
]

# Patterns that indicate DETERMINISTIC repeatability
DETERMINISTIC_PATTERNS = [
    r"invalid.?syntax",
    r"parse.?error",
    r"missing.?required",
    r"undefined.?reference",
    r"type.?error",
    r"invariant.?violation",
]


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL NAME EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_tool_from_error(raw_error: str) -> Optional[str]:
    """
    Extract tool name from error message.
    
    Looks for patterns like:
    - Tool 'syntaxvalidator' failed
    - [syntaxvalidator] Error:
    - syntaxvalidator: failed
    """
    if not raw_error:
        return None
    
    patterns = [
        r"Tool '(\w+)' failed",
        r"Tool \"(\w+)\" failed",
        r"\[(\w+)\]",
        r"^(\w+):",
        r"tool_name[\"':\s]+(\w+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, raw_error, re.IGNORECASE)
        if match:
            return match.group(1).lower()
    
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPORAL POSITION DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_temporal_position(
    artifacts_before: int,
    artifacts_after: int,
) -> TemporalPosition:
    """
    Determine when failure occurred relative to artifact materialization.
    
    PURE FUNCTION: No side effects.
    """
    if artifacts_after == 0:
        return TemporalPosition.PRE_MATERIALIZATION
    elif artifacts_after > artifacts_before:
        return TemporalPosition.DURING_MATERIALIZATION
    else:
        return TemporalPosition.POST_MATERIALIZATION


# ═══════════════════════════════════════════════════════════════════════════════
# REPEATABILITY DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_repeatability(raw_error: str) -> RepeatabilitySignature:
    """
    Determine repeatability signature from error message.
    
    PURE FUNCTION: Pattern matching only.
    """
    if not raw_error:
        return RepeatabilitySignature.UNKNOWN
    
    error_lower = raw_error.lower()
    
    # Check for non-deterministic patterns first
    for pattern in NON_DETERMINISTIC_PATTERNS:
        if re.search(pattern, error_lower):
            return RepeatabilitySignature.NON_DETERMINISTIC
    
    # Check for deterministic patterns
    for pattern in DETERMINISTIC_PATTERNS:
        if re.search(pattern, error_lower):
            return RepeatabilitySignature.DETERMINISTIC
    
    return RepeatabilitySignature.UNKNOWN


# ═══════════════════════════════════════════════════════════════════════════════
# ARTIFACT IMPACT DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_artifact_impact(
    execution_layer: ExecutionLayer,
    gating_semantics: GatingSemantics,
    artifacts_created: int,
) -> ArtifactImpact:
    """
    Determine artifact impact from other axes and artifact count.
    
    PURE FUNCTION: No inference beyond explicit rules.
    """
    # Observation layer with non-gating = no artifact impact
    if (
        execution_layer == ExecutionLayer.OBSERVATION_LAYER
        and gating_semantics == GatingSemantics.NON_GATING
    ):
        return ArtifactImpact.NO_ARTIFACT_IMPACT
    
    # No artifacts created = ambiguous (we don't know if there should be any)
    if artifacts_created == 0:
        return ArtifactImpact.ARTIFACT_AMBIGUITY
    
    # Blocking failure with artifacts = full invalidation
    if gating_semantics == GatingSemantics.BLOCKING:
        return ArtifactImpact.FULL_ARTIFACT_INVALIDATION
    
    # Non-blocking with artifacts = partial impact
    if gating_semantics == GatingSemantics.NON_BLOCKING:
        return ArtifactImpact.PARTIAL_ARTIFACT_IMPACT
    
    return ArtifactImpact.NO_ARTIFACT_IMPACT


# ═══════════════════════════════════════════════════════════════════════════════
# F-CLASS RECOMMENDATION
# ═══════════════════════════════════════════════════════════════════════════════

def recommend_fclass(
    original_fclass: str,
    execution_layer: ExecutionLayer,
    gating_semantics: GatingSemantics,
) -> str:
    """
    Recommend F-class based on ontology classification.
    
    This may reclassify F7 → F10 for observation layer failures.
    The original class is preserved; this is a recommendation only.
    """
    # Key reclassification: F7 in observation layer → F10
    if (
        original_fclass == "F7"
        and execution_layer == ExecutionLayer.OBSERVATION_LAYER
    ):
        return "F10"  # Post-Execution Observation Failure
    
    return original_fclass


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CLASSIFIER
# ═══════════════════════════════════════════════════════════════════════════════

def classify_failure_ontology(
    tool_name: Optional[str],
    step_name: str,
    agent: Optional[str],
    primary_class: str,  # "F1" through "F9"
    raw_error: str,
    duration_ms: int = 0,
    artifacts_created: int = 0,
    artifacts_before: int = 0,
) -> FailureOntologyClassification:
    """
    Deterministically classify a failure across all 7 axes.
    
    PURE FUNCTION:
    - No side effects
    - Same input → same output (always)
    - No LLM
    - No heuristics with intent
    
    Args:
        tool_name: Name of the tool that failed (extracted from error if None)
        step_name: Name of the workflow step
        agent: Agent name (Derek, Victoria, Luna, Marcus)
        primary_class: Original F-class ("F1" through "F9")
        raw_error: Raw error message
        duration_ms: Execution duration (for future patterns)
        artifacts_created: Number of artifacts created by this step
        artifacts_before: Number of artifacts before this failure
    
    Returns:
        FailureOntologyClassification with all 7 axes populated
    """
    # Extract tool name from error if not provided
    if not tool_name:
        tool_name = extract_tool_from_error(raw_error)
    
    # Normalize tool name
    tool_key = tool_name.lower() if tool_name else ""
    
    # ─────────────────────────────────────────────────────────────────────────
    # AXIS A: Execution Layer
    # ─────────────────────────────────────────────────────────────────────────
    execution_layer = TOOL_LAYER_RULES.get(tool_key, DEFAULT_LAYER)
    
    # ─────────────────────────────────────────────────────────────────────────
    # AXIS B: Authority Boundary
    # ─────────────────────────────────────────────────────────────────────────
    authority_boundary = TOOL_AUTHORITY_RULES.get(tool_key, DEFAULT_AUTHORITY)
    
    # If we have an agent, it's agent authority
    if agent and agent.lower() in ["derek", "victoria", "luna", "marcus"]:
        authority_boundary = AuthorityBoundary.AGENT_AUTHORITY
    
    # ─────────────────────────────────────────────────────────────────────────
    # AXIS C: Gating Semantics (CRITICAL)
    # ─────────────────────────────────────────────────────────────────────────
    gating_semantics = TOOL_GATING_RULES.get(tool_key, DEFAULT_GATING)
    
    # ─────────────────────────────────────────────────────────────────────────
    # AXIS D: Truth Domain
    # ─────────────────────────────────────────────────────────────────────────
    truth_domain = FCLASS_TRUTH_RULES.get(primary_class, DEFAULT_TRUTH)
    
    # Override for observation layer → observational truth
    if execution_layer == ExecutionLayer.OBSERVATION_LAYER:
        truth_domain = TruthDomain.OBSERVATIONAL_TRUTH
    
    # ─────────────────────────────────────────────────────────────────────────
    # AXIS E: Temporal Position
    # ─────────────────────────────────────────────────────────────────────────
    temporal_position = detect_temporal_position(
        artifacts_before=artifacts_before,
        artifacts_after=artifacts_created,
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # AXIS F: Artifact Impact
    # ─────────────────────────────────────────────────────────────────────────
    artifact_impact = detect_artifact_impact(
        execution_layer=execution_layer,
        gating_semantics=gating_semantics,
        artifacts_created=artifacts_created,
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # AXIS G: Repeatability Signature
    # ─────────────────────────────────────────────────────────────────────────
    repeatability_sig = detect_repeatability(raw_error)
    
    # ─────────────────────────────────────────────────────────────────────────
    # F-Class Recommendation
    # ─────────────────────────────────────────────────────────────────────────
    recommended_fclass = recommend_fclass(
        original_fclass=primary_class,
        execution_layer=execution_layer,
        gating_semantics=gating_semantics,
    )
    
    return FailureOntologyClassification(
        execution_layer=execution_layer,
        authority_boundary=authority_boundary,
        gating_semantics=gating_semantics,
        truth_domain=truth_domain,
        temporal_position=temporal_position,
        artifact_impact=artifact_impact,
        repeatability_sig=repeatability_sig,
        recommended_fclass=recommended_fclass,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "classify_failure_ontology",
    "extract_tool_from_error",
    "detect_temporal_position",
    "detect_repeatability",
    "detect_artifact_impact",
    "recommend_fclass",
    # Rule dictionaries (for inspection/debugging)
    "TOOL_GATING_RULES",
    "TOOL_LAYER_RULES",
    "TOOL_AUTHORITY_RULES",
    "FCLASS_TRUTH_RULES",
]
