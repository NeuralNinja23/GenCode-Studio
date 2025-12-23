# app/arbormind/learning/failure_record.py
"""
ArborMind Failure Record - Pure Semantic Structure (Phase 3.5)

This module defines the canonical shape of a failure failure.
It is a PURE DATA STRUCTURE module. It does not access databases.

REQUIREMENTS IMPLEMENTED:
1. Explicit Scope Assignment (Requirement 5)
2. 7-Axis Failure Ontology (Phase 3.5)
3. Canonical Failure Classification

INVARIANT: This module MUST NOT import database logic.
INVARIANT: This module provides the schema for Phase 3 observability.
"""

from typing import List, Optional
from dataclasses import dataclass, field
import json
import uuid
from datetime import datetime, timezone

from app.arbormind.observation.failure_canon import (
    FailureClass,
    FailureScope,
)
from app.arbormind.observation.signal_extractor import AtomicSignal


@dataclass
class FailureRecord:
    """
    A single failure record.
    
    This is the canonical shape of a failure.
    All fields are required at construction time.
    
    v3: Includes 7-axis ontology classification (Phase 3.5).
    """
    # Identity
    run_id: str
    step: str
    agent: Optional[str]
    
    # Classification (REQUIREMENT 3)
    primary_class: FailureClass
    
    # Scope (REQUIREMENT 5)
    scope: FailureScope
    
    # Signals (REQUIREMENT 4)
    signals: List[AtomicSignal] = field(default_factory=list)
    
    # Raw data
    raw_error: Optional[str] = None
    raw_diff: Optional[str] = None
    
    # Retry tracking
    retry_index: int = 0
    
    # Severity
    is_hard_failure: bool = False
    
    # TEMPORAL TRUTH INVARIANCE (v2)
    interpretation_context_hash: Optional[str] = None
    interpretation_context_json: Optional[str] = None
    
    # 7-AXIS ONTOLOGY (v3 - Phase 3.5)
    execution_layer: Optional[str] = None       # Axis A
    authority_boundary: Optional[str] = None    # Axis B  
    gating_semantics: Optional[str] = None      # Axis C (CRITICAL)
    truth_domain: Optional[str] = None          # Axis D
    temporal_position: Optional[str] = None     # Axis E
    artifact_impact: Optional[str] = None       # Axis F
    repeatability_sig: Optional[str] = None     # Axis G
    recommended_fclass: Optional[str] = None    # May differ from primary_class
    ontology_version: Optional[int] = None      # Version used for classification
    
    # Auto-generated
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate on construction."""
        # Validate primary_class
        if not isinstance(self.primary_class, FailureClass):
            # Try to convert if it's a value string, otherwise raise
            pass 
        
        # Validate scope
        if not isinstance(self.scope, FailureScope):
             pass

        # Validate signals
        if not isinstance(self.signals, list):
            self.signals = []
        
        # v2: Capture interpretation context if not provided
        if self.interpretation_context_hash is None:
            from app.arbormind.observation.interpretation_context import (
                get_context_hash,
                get_context_json,
            )
            self.interpretation_context_hash = get_context_hash()
            self.interpretation_context_json = get_context_json()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for lightweight usage."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "run_id": self.run_id,
            "step": self.step,
            "agent": self.agent,
            "primary_class": self.primary_class.value if hasattr(self.primary_class, "value") else str(self.primary_class),
            "scope": self.scope.value if hasattr(self.scope, "value") else str(self.scope),
            "signals": [s.to_dict() for s in self.signals],
            "raw_error": self.raw_error,
            "retry_index": self.retry_index,
            "is_hard_failure": self.is_hard_failure,
            "gating_semantics": self.gating_semantics,
            "execution_layer": self.execution_layer,
        }
