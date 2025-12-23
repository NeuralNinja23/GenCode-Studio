# app/arbormind/observation/observer.py
"""
ArborMind Observer - Passive event recorder.

SIMPLIFIED: This is a thin passthrough to the ExecutionLedger.
No logic, no branching, no interpretation.

INVARIANT: Observer MUST NOT affect execution decisions.
INVARIANT: Observer MUST NOT block on I/O.
INVARIANT: All writes are best-effort (failures swallowed).
"""

from __future__ import annotations
from typing import Optional, List
from app.arbormind.observation.execution_ledger import (
    get_store,
    record_decision_event,
    record_failure_event,
    record_supervisor_event,
)


class ArborMindObserver:
    """
    Passive observer that records execution events to the ledger.
    
    This class has ZERO cognitive authority. It only watches and records.
    It is a THIN PASSTHROUGH - no logic, no branching, no interpretation.
    """
    
    def __init__(self):
        """Initialize observer with ledger store."""
        self._store = get_store()
    
    def record_step_decision(
        self,
        run_id: str,
        step: str,
        agent: str,
        action: str,
        outcome: str = "pending",
        reason: Optional[str] = None,
        tool: Optional[str] = None,
        confidence: Optional[float] = None,
        entropy: Optional[float] = None,
    ):
        """
        Record a step-level decision to the ledger.
        Passthrough only - no interpretation.
        """
        try:
            record_decision_event(
                run_id=run_id,
                step=step,
                agent=agent or "unknown",
                decision=action,
                reason=reason or "",
            )
        except Exception:
            pass  # Non-fatal
    
    def record_step_failure(
        self,
        run_id: str,
        step: str,
        failure_type: str,
        message: str,
        agent: Optional[str] = None,
        stack_trace: Optional[str] = None,
    ):
        """
        Record a step failure to the ledger.
        Passthrough only - no interpretation.
        """
        try:
            record_failure_event(
                run_id=run_id,
                step=step,
                origin=agent or "SYSTEM",
                signal=failure_type,
                message=message,
            )
        except Exception:
            pass  # Non-fatal
    
    def record_verdict(
        self,
        run_id: str,
        step: str,
        agent: str,
        verdict: str,
        quality_score: Optional[float] = None,
        rejection_reasons: Optional[List[str]] = None,
        files_count: int = 0,
    ):
        """
        Record a supervisor verdict to the ledger.
        Passthrough only - no interpretation.
        """
        try:
            record_supervisor_event(
                run_id=run_id,
                step=step,
                agent=agent,
                verdict=verdict,
                quality=int(quality_score or 0),
                issues=rejection_reasons or [],
            )
        except Exception:
            pass  # Non-fatal


# ─────────────────────────────────────────────────────────────
# SINGLETON OBSERVER INSTANCE
# ─────────────────────────────────────────────────────────────

_observer: Optional[ArborMindObserver] = None

def get_observer() -> ArborMindObserver:
    """Get singleton observer instance."""
    global _observer
    if _observer is None:
        _observer = ArborMindObserver()
    return _observer


# ─────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTIONS (THIN PASSTHROUGHS)
# ─────────────────────────────────────────────────────────────

def observe_step_start(run_id: str, step: str, agent: str):
    """Record start of a step execution."""
    get_observer().record_step_decision(
        run_id=run_id,
        step=step,
        agent=agent,
        action="START",
        outcome="pending",
    )


def observe_step_success(run_id: str, step: str, agent: str, files_count: int = 0):
    """Record successful step completion."""
    get_observer().record_verdict(
        run_id=run_id,
        step=step,
        agent=agent,
        verdict="approved",
        files_count=files_count,
    )


def observe_step_failure(
    run_id: str,
    step: str,
    agent: str,
    failure_type: str,
    message: str,
    rejection_reasons: Optional[List[str]] = None,
):
    """Record step failure with categorization."""
    observer = get_observer()
    
    # Record failure
    observer.record_step_failure(
        run_id=run_id,
        step=step,
        failure_type=failure_type,
        message=message,
        agent=agent,
    )
    
    # Record rejection verdict
    observer.record_verdict(
        run_id=run_id,
        step=step,
        agent=agent,
        verdict="rejected",
        rejection_reasons=rejection_reasons or [message],
    )


def record_event(branch, decision):
    """
    Legacy event recording function.
    
    Records a decision event for a branch execution.
    Used for backward compatibility with older orchestration code.
    
    Args:
        branch: The branch being executed
        decision: The decision made (should have .action and .reason)
    """
    try:
        from app.arbormind.observation.execution_ledger import record_decision_event
        
        # Extract action string
        action = decision.action if hasattr(decision, "action") else "UNKNOWN"
        if hasattr(action, "value"):
            action_str = action.value
        elif hasattr(action, "name"):
            action_str = action.name
        else:
            action_str = str(action)
        
        # Extract reason
        reason = getattr(decision, "reason", "") or ""
        
        # Record to ledger
        record_decision_event(
            run_id=getattr(branch, "run_id", "unknown"),
            step=getattr(branch, "step_name", "unknown"),
            agent="arbormind",
            decision=action_str,
            reason=reason,
        )
    except Exception:
        pass  # Non-fatal - observation must never crash execution
