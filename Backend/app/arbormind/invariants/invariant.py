# app/arbormind/invariants/invariant.py
"""
Invariant System - Structural Guardrails

PHASE 2 CHANGE: Invariants now RETURN violations instead of RAISING exceptions.
The orchestrator decides how to handle violations based on severity.

Old behavior (compiler-like): raise InvariantViolation → crash
New behavior (cognitive): return Violation → orchestrator decides
"""

from typing import Optional, List, Callable, Any
from app.arbormind.cognition.failures import (
    InvariantViolation as StructuredViolation,
    FailureSeverity,
    get_failure_severity,
)


# LEGACY: Keep exception for backward compatibility during transition
class InvariantViolation(Exception):
    """
    DEPRECATED: Use StructuredViolation instead.
    
    This exception is kept for backward compatibility but should be
    phased out. New code should use Invariant.check() which returns
    a StructuredViolation, not raises an exception.
    """
    pass


class Invariant:
    """
    A structural guardrail that returns violations instead of crashing.
    
    INVARIANTS:
    - check() returns Optional[StructuredViolation], never raises
    - Orchestrator decides action based on severity
    - All violation metadata is captured for learning
    """
    
    def __init__(
        self,
        name: str,
        detector: Callable[[Any], bool],
        failure_code: Optional[str] = None,
        message_template: str = "{name} invariant violated",
    ):
        self.name = name
        self.detector = detector
        self.failure_code = failure_code or name
        self.message_template = message_template
    
    def check(self, branch: Any) -> Optional[StructuredViolation]:
        """
        Check invariant and return violation if detected.
        
        Returns None if invariant holds.
        Returns StructuredViolation if invariant is violated.
        
        NEVER raises an exception.
        """
        try:
            if self.detector(branch):
                return StructuredViolation(
                    code=self.failure_code,
                    message=self.message_template.format(name=self.name),
                    severity=get_failure_severity(self.failure_code),
                    context={"branch_id": getattr(branch, "id", None)},
                )
            return None
        except Exception as e:
            # Detector itself failed - this is a non-fatal violation
            return StructuredViolation(
                code="InvariantDetectorError",
                message=f"Invariant '{self.name}' detector crashed: {e}",
                severity=FailureSeverity.NON_FATAL,
                context={"original_error": str(e)},
            )
    
    def enforce(self, branch: Any):
        """
        LEGACY: Raise exception if invariant violated.
        
        DEPRECATED: Use check() instead.
        This method is kept for backward compatibility only.
        """
        violation = self.check(branch)
        if violation:
            raise InvariantViolation(f"{violation.code}: {violation.message}")


def check_all_invariants(
    invariants: List[Invariant],
    branch: Any,
) -> List[StructuredViolation]:
    """
    Check all invariants and return list of violations.
    
    This is the cognitive way: collect all problems, then decide.
    """
    violations = []
    for inv in invariants:
        violation = inv.check(branch)
        if violation:
            violations.append(violation)
    return violations


def has_fatal_violation(violations: List[StructuredViolation]) -> bool:
    """Check if any violation is fatal."""
    return any(v.is_fatal() for v in violations)
