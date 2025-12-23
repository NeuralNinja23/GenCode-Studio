# app/arbormind/cognition/failures.py
"""
ArborMind Failure System - Severity classification and handling.

Failures are classified by severity to determine recovery actions.
"""

from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


class FailureSeverity(Enum):
    """Severity levels for failures."""
    FATAL = "fatal"           # Must stop execution
    NON_FATAL = "non_fatal"   # Can continue with degraded output
    WARNING = "warning"       # Log and continue
    RECOVERABLE = "recoverable"  # Can retry or heal


# Failure code to severity mapping
FAILURE_SEVERITY_MAP = {
    # Fatal failures
    "RepeatedInvariant": FailureSeverity.FATAL,
    "CriticalStepFailure": FailureSeverity.FATAL,
    "BudgetExhausted": FailureSeverity.FATAL,
    
    # Non-fatal failures
    "SupervisorRejection": FailureSeverity.NON_FATAL,
    "QualityWarning": FailureSeverity.NON_FATAL,
    "PartialOutput": FailureSeverity.NON_FATAL,
    
    # Recoverable failures
    "InfraTransient": FailureSeverity.RECOVERABLE,
    "RateLimitHit": FailureSeverity.RECOVERABLE,
    "TimeoutRetryable": FailureSeverity.RECOVERABLE,
    
    # Warnings
    "MinorValidationIssue": FailureSeverity.WARNING,
    "DeprecationWarning": FailureSeverity.WARNING,
}


def get_failure_severity(failure_code: str) -> FailureSeverity:
    """
    Get the severity level for a failure code.
    
    Args:
        failure_code: The failure type identifier
        
    Returns:
        FailureSeverity enum value
    """
    return FAILURE_SEVERITY_MAP.get(failure_code, FailureSeverity.NON_FATAL)


def is_fatal(failure_code: str) -> bool:
    """Check if a failure code indicates a fatal error."""
    return get_failure_severity(failure_code) == FailureSeverity.FATAL


@dataclass
class InvariantViolation:
    """
    Structured representation of an invariant violation.
    
    Used instead of raising exceptions to allow orchestrator
    to decide how to handle violations.
    """
    code: str
    message: str
    severity: FailureSeverity = FailureSeverity.NON_FATAL
    context: Dict[str, Any] = field(default_factory=dict)
    
    def is_fatal(self) -> bool:
        """Check if this violation is fatal."""
        return self.severity == FailureSeverity.FATAL
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "context": self.context,
        }


# Legacy exception for backward compatibility
class InvariantViolationException(Exception):
    """
    DEPRECATED: Use InvariantViolation dataclass instead.
    Kept for backward compatibility.
    """
    pass
