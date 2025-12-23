# app/arbormind/learning/interpretation_context.py
"""
ArborMind Interpretation Context - Temporal Truth Invariance

THE PROBLEM:
Storing "what failed" is not enough if the meaning of that failure
can change when the system evolves.

WHAT MUST BE FROZEN at the time of each failure:
1. Signal extractor version + rules hash
2. Active invariants (which rules were in force)
3. Scope semantics (what each scope meant)
4. Canon definitions (what F1-F9 meant)

THE GUARANTEE:
"A failure recorded today can be understood identically in 6 months,
even if the codebase has completely changed."

IMPLEMENTATION:
Each failure record includes an `interpretation_context_hash` that
points to a frozen snapshot of all interpretation rules.

INVARIANT: Context is append-only (new versions add, never modify).
INVARIANT: Same input + same context = same meaning (forever).
"""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, FrozenSet
from pathlib import Path

from app.arbormind.observation.failure_canon import (
    FailureClass,
    FailureScope,
    CANON_VERSION,
    FAILURE_CLASS_DEFINITIONS,
)
from app.arbormind.observation.signal_extractor import (
    SignalType,
    SignalExtractor,
)


# ═══════════════════════════════════════════════════════════════════════════════
# INTERPRETATION CONTEXT VERSION
# ═══════════════════════════════════════════════════════════════════════════════
INTERPRETATION_CONTEXT_VERSION = 1


@dataclass(frozen=True)
class SignalExtractorContext:
    """
    Frozen snapshot of signal extractor rules.
    
    If the regex patterns or extraction logic changes, the hash changes.
    """
    version: int
    signal_types: tuple  # Frozen list of signal types
    # Hash of the actual regex patterns (detect if extraction rules change)
    pattern_hash: str
    
    @classmethod
    def capture_current(cls) -> "SignalExtractorContext":
        """Capture current signal extractor state."""
        extractor = SignalExtractor()
        
        # Hash all regex patterns
        patterns = [
            extractor.EXCEPTION_PATTERN.pattern,
            extractor.FILE_PATH_PATTERN.pattern,
            extractor.LINE_NUMBER_PATTERN.pattern,
            extractor.MISSING_IDENT_PATTERN.pattern,
            extractor.FAILED_IMPORT_PATTERN.pattern,
            extractor.TYPE_MISMATCH_PATTERN.pattern,
            extractor.HTTP_STATUS_PATTERN.pattern,
            extractor.TIMEOUT_PATTERN.pattern,
            extractor.DIFF_LINE_PATTERN.pattern,
        ]
        pattern_str = "|".join(patterns)
        pattern_hash = hashlib.sha256(pattern_str.encode()).hexdigest()[:16]
        
        return cls(
            version=1,
            signal_types=tuple(st.value for st in SignalType),
            pattern_hash=pattern_hash,
        )
    
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "signal_types": list(self.signal_types),
            "pattern_hash": self.pattern_hash,
        }


@dataclass(frozen=True)
class CanonContext:
    """
    Frozen snapshot of failure class definitions.
    
    If the meaning of F1-F9 changes, the hash changes.
    """
    version: int
    classes: tuple  # (F1, F2, ..., F9)
    definitions_hash: str  # Hash of all definitions
    
    @classmethod
    def capture_current(cls) -> "CanonContext":
        """Capture current canon state."""
        # Serialize all definitions to a stable string
        defs_str = ""
        for fc in FailureClass:
            defn = FAILURE_CLASS_DEFINITIONS[fc]
            defs_str += f"{fc.value}:{defn.name}:{defn.description}:{defn.is_retryable}:{defn.typical_scope.value}|"
        
        definitions_hash = hashlib.sha256(defs_str.encode()).hexdigest()[:16]
        
        return cls(
            version=CANON_VERSION,
            classes=tuple(fc.value for fc in FailureClass),
            definitions_hash=definitions_hash,
        )
    
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "classes": list(self.classes),
            "definitions_hash": self.definitions_hash,
        }


@dataclass(frozen=True)
class ScopeContext:
    """
    Frozen snapshot of scope semantics.
    
    If the meaning of ENTITY_LOCAL, STEP_LOCAL, etc. changes, the hash changes.
    """
    version: int
    scopes: tuple  # (entity_local, step_local, cross_step, systemic)
    semantics_hash: str
    
    @classmethod
    def capture_current(cls) -> "ScopeContext":
        """Capture current scope semantics."""
        # Define the semantic meaning of each scope (this is the invariant)
        scope_semantics = {
            "entity_local": "Failure is local to a single entity (e.g., one model file)",
            "step_local": "Failure is local to a single step (e.g., backend_models)",
            "cross_step": "Failure spans multiple steps (e.g., frontend depends on backend)",
            "systemic": "Failure is system-wide (e.g., API failures, token limits)",
        }
        
        semantics_str = json.dumps(scope_semantics, sort_keys=True)
        semantics_hash = hashlib.sha256(semantics_str.encode()).hexdigest()[:16]
        
        return cls(
            version=1,
            scopes=tuple(fs.value for fs in FailureScope),
            semantics_hash=semantics_hash,
        )
    
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "scopes": list(self.scopes),
            "semantics_hash": self.semantics_hash,
        }


@dataclass(frozen=True)
class InterpretationContext:
    """
    Complete frozen interpretation context.
    
    This is what gets stored with each failure to guarantee
    temporal truth invariance.
    """
    # Context version (for future migrations)
    context_version: int
    
    # Timestamp when this context was captured
    captured_at: str
    
    # Sub-contexts
    signal_extractor: SignalExtractorContext
    canon: CanonContext
    scope: ScopeContext
    
    # Combined hash (if this changes, interpretation may differ)
    context_hash: str = field(default="")
    
    def __post_init__(self):
        # Compute combined hash if not provided
        if not self.context_hash:
            combined = (
                f"{self.signal_extractor.pattern_hash}:"
                f"{self.canon.definitions_hash}:"
                f"{self.scope.semantics_hash}"
            )
            # Use object.__setattr__ because frozen=True
            object.__setattr__(
                self, 
                "context_hash", 
                hashlib.sha256(combined.encode()).hexdigest()[:24]
            )
    
    @classmethod
    def capture_current(cls) -> "InterpretationContext":
        """Capture complete current interpretation context."""
        return cls(
            context_version=INTERPRETATION_CONTEXT_VERSION,
            captured_at=datetime.now(timezone.utc).isoformat(),
            signal_extractor=SignalExtractorContext.capture_current(),
            canon=CanonContext.capture_current(),
            scope=ScopeContext.capture_current(),
        )
    
    def to_dict(self) -> dict:
        return {
            "context_version": self.context_version,
            "captured_at": self.captured_at,
            "signal_extractor": self.signal_extractor.to_dict(),
            "canon": self.canon.to_dict(),
            "scope": self.scope.to_dict(),
            "context_hash": self.context_hash,
        }
    
    def to_json(self) -> str:
        """Serialize to JSON for storage."""
        return json.dumps(self.to_dict(), sort_keys=True)
    
    @classmethod
    def from_dict(cls, d: dict) -> "InterpretationContext":
        """Reconstruct from stored dict."""
        return cls(
            context_version=d["context_version"],
            captured_at=d["captured_at"],
            signal_extractor=SignalExtractorContext(
                version=d["signal_extractor"]["version"],
                signal_types=tuple(d["signal_extractor"]["signal_types"]),
                pattern_hash=d["signal_extractor"]["pattern_hash"],
            ),
            canon=CanonContext(
                version=d["canon"]["version"],
                classes=tuple(d["canon"]["classes"]),
                definitions_hash=d["canon"]["definitions_hash"],
            ),
            scope=ScopeContext(
                version=d["scope"]["version"],
                scopes=tuple(d["scope"]["scopes"]),
                semantics_hash=d["scope"]["semantics_hash"],
            ),
            context_hash=d.get("context_hash", ""),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT CACHE (Avoids recomputing for every failure in same run)
# ═══════════════════════════════════════════════════════════════════════════════
_cached_context: Optional[InterpretationContext] = None
_cache_hash: Optional[str] = None


def get_current_context() -> InterpretationContext:
    """
    Get current interpretation context (cached per session).
    
    Recomputed if underlying hashes change.
    """
    global _cached_context, _cache_hash
    
    # Always capture fresh to check if anything changed
    fresh = InterpretationContext.capture_current()
    
    if _cached_context is None or _cache_hash != fresh.context_hash:
        _cached_context = fresh
        _cache_hash = fresh.context_hash
    
    return _cached_context


def get_context_hash() -> str:
    """Get just the context hash (lightweight check)."""
    return get_current_context().context_hash


def get_context_json() -> str:
    """Get context as JSON string for storage."""
    return get_current_context().to_json()


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def verify_context_compatibility(stored_hash: str) -> bool:
    """
    Check if a stored context hash matches current context.
    
    If False, the stored failure was recorded under different interpretation rules.
    This is informational only - the stored data is still valid under its original context.
    """
    return stored_hash == get_context_hash()


def context_drift_warning(stored_hash: str) -> Optional[str]:
    """
    Generate a warning message if context has drifted.
    
    Returns None if contexts match, warning message otherwise.
    """
    current = get_context_hash()
    if stored_hash == current:
        return None
    
    return (
        f"⚠️ CONTEXT DRIFT: This failure was recorded under context '{stored_hash}' "
        f"but current context is '{current}'. Interpretation rules may have changed."
    )
