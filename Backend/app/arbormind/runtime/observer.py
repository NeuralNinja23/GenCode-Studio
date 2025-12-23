# app/arbormind/runtime/observer.py
"""
ArborMind Runtime Observer - Records execution events.

Passive observation of branch execution for learning.
"""

from typing import Any, Optional
from app.arbormind.cognition.branch import Branch
from app.arbormind.cognition.execution_report import ExecutionReport


def observe(branch: Branch, report: ExecutionReport) -> None:
    """
    Observe and record the result of branch execution.
    
    This is a passive observation - it does not affect execution.
    The observations are used for offline learning.
    
    Args:
        branch: The branch that was executed
        report: The execution report
    """
    try:
        # Record to observation layer (non-blocking)
        from app.arbormind.observation.observer import get_observer
        
        observer = get_observer()
        
        if report.success:
            observer.record_step_decision(
                run_id=branch.run_id,
                step=branch.step_name or "unknown",
                agent="arbormind",
                action="COMPLETE",
                outcome="success",
            )
        else:
            observer.record_step_failure(
                run_id=branch.run_id,
                step=branch.step_name or "unknown",
                failure_type="execution_failure",
                message=report.error or "Unknown error",
                agent="arbormind",
            )
    except Exception:
        pass  # Observation must never crash execution


def observe_decision(
    branch: Branch,
    action: str,
    reason: str,
) -> None:
    """
    Observe a decision made during execution.
    
    Args:
        branch: Current branch
        action: Action taken
        reason: Reason for action
    """
    try:
        from app.arbormind.observation.observer import get_observer
        
        observer = get_observer()
        observer.record_step_decision(
            run_id=branch.run_id,
            step=branch.step_name or "unknown",
            agent="arbormind",
            action=action,
            reason=reason,
        )
    except Exception:
        pass
