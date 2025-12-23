# app/arbormind/observation/__init__.py
"""
ArborMind Observation Layer

Passive, append-only event recording with SQLite persistence.
INVARIANT: Observations MUST NOT influence execution.
"""

from app.arbormind.observation.observer import (
    ArborMindObserver,
    get_observer,
    observe_step_start,
    observe_step_success,
    observe_step_failure,
)
from app.arbormind.observation.execution_ledger import (
    ExecutionLedger,
    get_store,
    record_run_start,
    record_step_entry,
    record_step_exit,
    record_decision_event,
    record_failure_event,
    record_supervisor_event,
    record_snapshot,
    record_artifact_event,
    record_tool_trace,
)

__all__ = [
    # Observer
    "ArborMindObserver",
    "get_observer",
    "observe_step_start",
    "observe_step_success",
    "observe_step_failure",
    
    # Execution Ledger (Event Stream)
    "ExecutionLedger",
    "get_store",
    "record_run_start",
    "record_step_entry",
    "record_step_exit",
    "record_decision_event",
    "record_failure_event",
    "record_supervisor_event",
    "record_snapshot",
    "record_artifact_event",
    "record_tool_trace",
]
