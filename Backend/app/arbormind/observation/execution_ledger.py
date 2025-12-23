# app/arbormind/observation/execution_ledger.py
"""
ArborMind "Execution Ledger"
PHASE 3: Pure Event Stream (Append-Only)

ONE RESPONSIBILITY:
    Persist execution events exactly as they happened.

INVARIANTS:
1. NO Interpretation (no "decisions", only "events")
2. NO Updates (append-only history)
3. NO Reads (reconstruction only via external builder)
4. NO Semantics (raw signals, not classifications)

This module is the "Disk Writer" for the RunSlice.
"""

import sqlite3
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA DEFINITION (Pure Event Stream)
# ═══════════════════════════════════════════════════════════════════════════════

SCHEMA_SQL = """
-- 1. RUN EVENTS (Lifecycle)
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    project_id TEXT,
    timestamp TEXT,
    status_event TEXT -- "CREATED", "STARTED", "COMPLETED"
);

-- 2. STEP EVENTS (Lifecycle - Replaces 'steps' table)
-- Stores ENTRY and EXIT events separately.
-- Reconstruction calculates duration.
CREATE TABLE IF NOT EXISTS step_events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT,
    step_name TEXT,
    event_type TEXT, -- "ENTRY", "EXIT"
    payload TEXT,    -- JSON Context (e.g. status code at exit)
    timestamp TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);

-- 3. DECISION EVENTS (Replaces 'decisions' table)
-- Records the issuance of a judgment, not the judgment itself.
CREATE TABLE IF NOT EXISTS decision_events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT,
    step TEXT,
    source_agent TEXT,
    event_type TEXT,   -- "VERDICT_EMITTED", "BRANCH_PROPOSED"
    raw_payload TEXT,  -- Opaque JSON (the actual decision content)
    timestamp TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);

-- 4. ARTIFACT EVENTS
CREATE TABLE IF NOT EXISTS artifact_events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT,
    step TEXT,
    file_path TEXT,
    event_type TEXT,   -- "CREATED", "MODIFIED"
    size_bytes INTEGER,
    timestamp TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);

-- 5. FAILURE EVENTS (Replaces 'failures' table)
-- Records raw signals. No classification logic here.
CREATE TABLE IF NOT EXISTS failure_events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT,
    step TEXT,
    origin TEXT,       -- "TOOL", "SYSTEM", "ORCHESTRATOR"
    raw_signal TEXT,   -- Exception class or error code
    message TEXT,      -- Raw error text
    timestamp TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);

-- 6. SUPERVISOR EVENTS
CREATE TABLE IF NOT EXISTS supervisor_events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT,
    step TEXT,
    agent TEXT,
    event_type TEXT,   -- "REVIEW_COMPLETED"
    raw_payload TEXT,  -- JSON with score, issues, etc.
    timestamp TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);

-- 7. TOOL INVOCATION TRACE (TIT)
CREATE TABLE IF NOT EXISTS tool_invocations (
    trace_id TEXT PRIMARY KEY,
    run_id TEXT,
    step TEXT,
    tool_name TEXT,
    input_hash TEXT,
    exit_code INTEGER,
    duration_ms INTEGER,
    timestamp TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);

-- 8. STEP STATE SNAPSHOTS (SSS)
CREATE TABLE IF NOT EXISTS step_state_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    run_id TEXT,
    step TEXT,
    stage TEXT, -- "ENTRY", "EXIT"
    workspace_hash TEXT,
    artifacts_hash TEXT,
    timestamp TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);
"""


# ═══════════════════════════════════════════════════════════════════════════════
# STORE IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════════

class EpistemicViolation(RuntimeError):
    pass

class ExecutionLedger:
    """
    Append-only event recorder.
    Ignorant of semantics.
    """
    _instance = None
    _lock = threading.Lock()
    DB_PATH = Path("arbormind_runs/arbormind.db")

    def __init__(self):
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = cls()
        return cls._instance

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(
                str(self.DB_PATH), 
                check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    @contextmanager
    def _cursor(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def _init_db(self):
        with self._cursor() as cursor:
            cursor.executescript(SCHEMA_SQL)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # WRITE API (Record Events)
    # ═══════════════════════════════════════════════════════════════════════════

    def record_run_start(self, run_id: str, project_id: str):
        with self._cursor() as cursor:
            cursor.execute(
                "INSERT INTO runs (run_id, project_id, timestamp, status_event) VALUES (?, ?, ?, ?)",
                (run_id, project_id, datetime.now().isoformat(), "STARTED")
            )

    def record_step_entry(self, run_id: str, step: str):
        with self._cursor() as cursor:
            cursor.execute(
                "INSERT INTO step_events (event_id, run_id, step_name, event_type, timestamp) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), run_id, step, "ENTRY", datetime.now().isoformat())
            )

    def record_step_exit(self, run_id: str, step: str, status: str):
        payload = json.dumps({"status": status})
        with self._cursor() as cursor:
            cursor.execute(
                "INSERT INTO step_events (event_id, run_id, step_name, event_type, payload, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), run_id, step, "EXIT", payload, datetime.now().isoformat())
            )

    def record_decision_event(self, run_id: str, step: str, agent: str, event_type: str, payload_json: str):
        with self._cursor() as cursor:
            cursor.execute(
                "INSERT INTO decision_events (event_id, run_id, step, source_agent, event_type, raw_payload, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), run_id, step, agent, event_type, payload_json, datetime.now().isoformat())
            )

    def record_failure_event(self, run_id: str, step: str, origin: str, signal: str, message: str):
        with self._cursor() as cursor:
            cursor.execute(
                "INSERT INTO failure_events (event_id, run_id, step, origin, raw_signal, message, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), run_id, step, origin, signal, message, datetime.now().isoformat())
            )

    def record_supervisor_event(self, run_id: str, step: str, agent: str, payload_json: str):
         with self._cursor() as cursor:
            cursor.execute(
                "INSERT INTO supervisor_events (event_id, run_id, step, agent, event_type, raw_payload, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), run_id, step, agent, "REVIEW_COMPLETED", payload_json, datetime.now().isoformat())
            )

    def record_tool_trace(self, run_id: str, step: str, tool_name: str, input_hash: str, exit_code: int, duration_ms: int):
        with self._cursor() as cursor:
            cursor.execute(
                "INSERT INTO tool_invocations (trace_id, run_id, step, tool_name, input_hash, exit_code, duration_ms, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), run_id, step, tool_name, input_hash, exit_code, duration_ms, datetime.now().isoformat())
            )

    def record_artifact_event(self, run_id: str, step: str, file_path: str, event_type: str, size_bytes: int):
        """Record artifact birth/modification event at the file materialization boundary."""
        with self._cursor() as cursor:
            cursor.execute(
                "INSERT INTO artifact_events (event_id, run_id, step, file_path, event_type, size_bytes, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), run_id, step, file_path, event_type, size_bytes, datetime.now().isoformat())
            )

    def record_snapshot(self, run_id: str, step: str, stage: str, workspace_hash: str, artifacts_hash: str):
        with self._cursor() as cursor:
            cursor.execute(
                "INSERT INTO step_state_snapshots (snapshot_id, run_id, step, stage, workspace_hash, artifacts_hash, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), run_id, step, stage, workspace_hash, artifacts_hash, datetime.now().isoformat())
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # READ API (Reconstruction Builder Access ONLY)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _dump_table(self, table_name: str, run_id: str):
        """Raw table dump for builder. No logic."""
        with self._cursor() as cursor:
            # Safe parameterized query for known table names
            cursor.execute(f"SELECT * FROM {table_name} WHERE run_id = ? ORDER BY timestamp", (run_id,))
            return [dict(row) for row in cursor.fetchall()]


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL WRAPPERS (Strictly Typed Events)
# ═══════════════════════════════════════════════════════════════════════════════

_CURRENT_RUN_ID = None

def set_current_run_id(run_id: str):
    global _CURRENT_RUN_ID
    _CURRENT_RUN_ID = run_id

def get_current_run_id() -> str:
    return _CURRENT_RUN_ID

def get_store() -> ExecutionLedger:
    return ExecutionLedger.get_instance()

# WRITE WRAPPERS
def record_run_start(run_id: str, project_id: str):
    get_store().record_run_start(run_id, project_id)

def record_step_entry(run_id: str, step: str):
    get_store().record_step_entry(run_id, step)

def record_step_exit(run_id: str, step: str, status: str):
    get_store().record_step_exit(run_id, step, status)

def record_decision_event(run_id: str, step: str, agent: str, decision: str, reason: str):
    # Semantic mapping moved OUT of store. We simply JSONify the intent.
    payload = json.dumps({"decision": decision, "reason": reason})
    # We call it "INTENT_EMITTED" to signify we recorded what they wanted, not truth
    get_store().record_decision_event(run_id, step, agent, "INTENT_EMITTED", payload)

def record_failure_event(run_id: str, step: str, origin: str, message: str, signal: str = "UNKNOWN"):
    get_store().record_failure_event(run_id, step, origin, signal, message)

def record_supervisor_event(run_id: str, step: str, agent: str, verdict: str, quality: int, issues: list):
    payload = json.dumps({"verdict": verdict, "quality": quality, "issues": issues})
    get_store().record_supervisor_event(run_id, step, agent, payload)

def record_snapshot(run_id: str, step: str, stage: str, workspace_hash: str, artifacts_hash: str):
    get_store().record_snapshot(run_id, step, stage, workspace_hash, artifacts_hash)

def record_artifact_event(run_id: str, step: str, file_path: str, event_type: str, size_bytes: int):
    """Record artifact birth/modification at materialization boundary."""
    get_store().record_artifact_event(run_id, step, file_path, event_type, size_bytes)

def record_tool_trace(run_id: str, step: str, tool_name: str, input_hash: str, exit_code: int, duration_ms: int):
    """Record tool invocation trace for cost/duration attribution."""
    get_store().record_tool_trace(run_id, step, tool_name, input_hash, exit_code, duration_ms)

# LEGACY COMPATIBILITY HELPERS (To bridge existing calls to new event model)

def update_decision_outcome(run_id: str, step: str, outcome: str, duration_ms: int, artifacts_count: int):
    # Maps old "outcome" logic to a clean STEP EXIT event
    record_step_exit(run_id, step, outcome)

def record_failure(run_id: str, step: str, failure_type: str, message: str, stack_trace: str = ""):
    # Map old "failure record" to new event
    record_failure_event(run_id, step, origin="SYSTEM", signal=failure_type, message=message)


def record_run_end(run_id: str, status: str, total_steps: int, completed_steps: int, failed_steps: int):
    """Record run completion event."""
    try:
        store = get_store()
        with store._cursor() as cursor:
            cursor.execute(
                "UPDATE runs SET status_event = ? WHERE run_id = ?",
                (f"COMPLETED_{status.upper()}", run_id)
            )
    except Exception:
        pass  # Non-fatal


# ═══════════════════════════════════════════════════════════════════════════════
# LEARNING INGESTION STUBS (Phase 4 - Currently No-Ops)
# ═══════════════════════════════════════════════════════════════════════════════

def ingest_failure(
    run_id: str,
    step: str,
    primary_class,
    scope,
    raw_error: str,
    agent: str,
    retry_index: int = 0,
    is_hard_failure: bool = False,
):
    """
    Ingest a canonical failure for learning.
    Currently a no-op placeholder for Phase 4.
    """
    # Phase 3: Just record as failure event
    record_failure_event(run_id, step, origin=agent, signal=str(primary_class), message=raw_error)


def ingest_runtime_exception(
    run_id: str,
    step: str,
    exception_info: str,
    agent: str,
):
    """
    Ingest a runtime exception for learning.
    Currently a no-op placeholder for Phase 4.
    """
    # Phase 3: Just record as failure event
    record_failure_event(run_id, step, origin=agent, signal="RUNTIME_EXCEPTION", message=exception_info[:500])
