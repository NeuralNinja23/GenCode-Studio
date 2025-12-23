# app/arbormind/cognition/__init__.py
"""
ArborMind Cognition Layer

Core cognitive components for branch-based execution.
"""

from app.arbormind.cognition.branch import Branch
from app.arbormind.cognition.tree import ArborMindTree
from app.arbormind.cognition.execution_report import ExecutionReport
from app.arbormind.cognition.failures import (
    FailureSeverity,
    InvariantViolation,
    get_failure_severity,
    is_fatal,
)
from app.arbormind.cognition.convergence import (
    is_converged,
    get_completion_confidence,
    should_preview,
)
from app.arbormind.cognition.partial_output import allows_partial_output

__all__ = [
    "Branch",
    "ArborMindTree",
    "ExecutionReport",
    "FailureSeverity",
    "InvariantViolation",
    "get_failure_severity",
    "is_fatal",
    "is_converged",
    "get_completion_confidence",
    "should_preview",
    "allows_partial_output",
]
