# app/arbormind/observation/tool_trace.py
"""
Tool Invocation Trace (TIT)

PURPOSE: Expose execution topology without influencing it.
TIT answers "what actually happened?" 
NOT "why?", NOT "what should we do?"

═══════════════════════════════════════════════════════════════════════════════
NON-NEGOTIABLE CONSTRAINTS
═══════════════════════════════════════════════════════════════════════════════

1. Append-only
2. Write-through only (no buffering, no aggregation)
3. No interpretation
4. No dependency on Arbormind decisions
5. Failure-safe (TIT must never crash execution)
6. Opt-out capable (env flag)

If any are violated → false learning later.

This module is NOT:
- a tool
- a planner
- a router
- a learner

It is a SINK.
"""

import os
import json
import sqlite3
import threading
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Optional, Literal
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE FLAG
# ═══════════════════════════════════════════════════════════════════════════════

ARBORMIND_TIT_ENABLED = os.getenv("ARBORMIND_TIT", "1") == "1"


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA (v1 - Final, Correct, Minimal)
# ═══════════════════════════════════════════════════════════════════════════════

TIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS tool_invocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Lineage
    run_id TEXT NOT NULL,
    branch_id TEXT,
    decision_id INTEGER,
    step TEXT NOT NULL,
    agent TEXT NOT NULL,

    -- Tool identity
    tool_name TEXT NOT NULL,
    tool_type TEXT NOT NULL,

    -- Invocation context
    invocation_index INTEGER,
    called_at DATETIME NOT NULL,
    duration_ms INTEGER,

    -- Raw I/O (truncated, forensic only)
    input_summary TEXT,
    output_summary TEXT,

    -- Result
    status TEXT NOT NULL,
    error_type TEXT,
    error_message TEXT,

    -- Resource signals
    tokens_used INTEGER,
    model_name TEXT,
    retries INTEGER DEFAULT 0,

    -- Integrity
    schema_version INTEGER DEFAULT 1,

    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(decision_id) REFERENCES decisions(id)
);

CREATE INDEX IF NOT EXISTS idx_tit_run_id ON tool_invocations(run_id);
CREATE INDEX IF NOT EXISTS idx_tit_step ON tool_invocations(step);
CREATE INDEX IF NOT EXISTS idx_tit_tool_name ON tool_invocations(tool_name);
CREATE INDEX IF NOT EXISTS idx_tit_status ON tool_invocations(status);
"""


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODEL (Strict, Typed, Immutable)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ToolInvocationEvent:
    """
    Single tool invocation record.
    
    Immutable. No defaults. If data is missing → pass None.
    """
    # Lineage
    run_id: str
    branch_id: Optional[str]
    decision_id: Optional[int]
    step: str
    agent: str
    
    # Tool identity
    tool_name: str
    tool_type: str
    
    # Invocation context
    invocation_index: int
    called_at: datetime
    duration_ms: Optional[int]
    
    # Raw I/O (truncated)
    input_summary: Optional[str]
    output_summary: Optional[str]
    
    # Result
    status: Literal["success", "failure", "timeout", "aborted"]
    error_type: Optional[str]
    error_message: Optional[str]
    
    # Resource signals
    tokens_used: Optional[int]
    model_name: Optional[str]
    retries: int


# ═══════════════════════════════════════════════════════════════════════════════
# TRUNCATION (Hard Rules)
# ═══════════════════════════════════════════════════════════════════════════════

MAX_PAYLOAD_BYTES = 2048
MAX_VALUE_CHARS = 512

# Secrets to never store
SECRET_KEYS = frozenset({
    "api_key", "apikey", "api-key",
    "token", "access_token", "secret",
    "password", "passwd", "credentials",
    "authorization", "auth",
})


def truncate_payload(obj: Any) -> Optional[str]:
    """
    Truncate payload for forensic storage.
    
    Rules:
    1. JSON only
    2. UTF-8 only  
    3. Max 2048 bytes total
    4. Max 512 chars per value
    5. No binary
    6. No secrets
    """
    if obj is None:
        return None
    
    try:
        # Handle non-dict types
        if not isinstance(obj, dict):
            if isinstance(obj, str):
                return obj[:MAX_PAYLOAD_BYTES]
            return json.dumps(obj)[:MAX_PAYLOAD_BYTES]
        
        # Truncate dict values
        truncated = {}
        for key, value in obj.items():
            # Skip secrets
            if key.lower() in SECRET_KEYS:
                truncated[key] = "[REDACTED]"
                continue
            
            # Truncate value
            if isinstance(value, str):
                truncated[key] = value[:MAX_VALUE_CHARS] if len(value) > MAX_VALUE_CHARS else value
            elif isinstance(value, (dict, list)):
                # First-level keys only - summarize nested
                truncated[key] = f"[{type(value).__name__}: {len(value)} items]"
            elif isinstance(value, bytes):
                truncated[key] = f"[bytes: {len(value)}]"
            else:
                truncated[key] = value
        
        result = json.dumps(truncated, default=str, ensure_ascii=False)
        
        # Final truncation to max bytes
        if len(result.encode('utf-8')) > MAX_PAYLOAD_BYTES:
            result = result[:MAX_PAYLOAD_BYTES]
        
        return result
        
    except Exception:
        return None


def truncate_error(error: Optional[str]) -> Optional[str]:
    """Truncate error message to reasonable length."""
    if error is None:
        return None
    return error[:1024] if len(error) > 1024 else error


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE CONNECTION (Thread-Safe Singleton)
# ═══════════════════════════════════════════════════════════════════════════════

_db_lock = threading.Lock()
_db_initialized = False


def _get_db_path() -> Path:
    """Get path to TIT database (same as arbormind.db)."""
    from app.arbormind.observation.execution_ledger import _get_db_path as get_arbormind_db
    return get_arbormind_db()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Ensure TIT table exists."""
    global _db_initialized
    
    if _db_initialized:
        return
    
    with _db_lock:
        if _db_initialized:
            return
        
        try:
            conn.executescript(TIT_SCHEMA)
            conn.commit()
            _db_initialized = True
        except Exception:
            pass  # Best effort


def _get_connection() -> sqlite3.Connection:
    """Get database connection."""
    db_path = _get_db_path()
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    _ensure_schema(conn)
    return conn


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLE ENTRY POINT (Critical Design Choice)
# ═══════════════════════════════════════════════════════════════════════════════

def record_tool_invocation(event: ToolInvocationEvent) -> None:
    """
    Fire-and-forget tool invocation recording.
    
    MUST NEVER RAISE.
    
    This is the ONLY function that writes to tool_invocations.
    All other paths are forbidden.
    """
    # Feature flag check - short circuit if disabled
    if not ARBORMIND_TIT_ENABLED:
        return
    
    try:
        conn = _get_connection()
        
        conn.execute(
            """
            INSERT INTO tool_invocations (
                run_id, branch_id, decision_id, step, agent,
                tool_name, tool_type,
                invocation_index, called_at, duration_ms,
                input_summary, output_summary,
                status, error_type, error_message,
                tokens_used, model_name, retries,
                schema_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                event.run_id,
                event.branch_id,
                event.decision_id,
                event.step,
                event.agent,
                event.tool_name,
                event.tool_type,
                event.invocation_index,
                event.called_at.isoformat(),
                event.duration_ms,
                event.input_summary,
                event.output_summary,
                event.status,
                event.error_type,
                truncate_error(event.error_message),
                event.tokens_used,
                event.model_name,
                event.retries,
            )
        )
        
        conn.commit()
        conn.close()
        
    except Exception:
        # TIT must never crash execution
        # Silently fail - execution continues
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE BUILDERS (For Hook Points)
# ═══════════════════════════════════════════════════════════════════════════════

def build_tool_event(
    run_id: str,
    step: str,
    agent: str,
    tool_name: str,
    tool_type: str,
    invocation_index: int,
    called_at: datetime,
    duration_ms: Optional[int],
    status: Literal["success", "failure", "timeout", "aborted"],
    input_args: Optional[dict] = None,
    output_result: Optional[Any] = None,
    error: Optional[Exception] = None,
    tokens_used: Optional[int] = None,
    model_name: Optional[str] = None,
    retries: int = 0,
    branch_id: Optional[str] = None,
    decision_id: Optional[int] = None,
) -> ToolInvocationEvent:
    """
    Build a ToolInvocationEvent with proper truncation.
    
    Convenience function for hook points.
    """
    error_type = None
    error_message = None
    
    if error is not None:
        error_type = type(error).__name__
        error_message = str(error)
    
    return ToolInvocationEvent(
        run_id=run_id,
        branch_id=branch_id,
        decision_id=decision_id,
        step=step,
        agent=agent,
        tool_name=tool_name,
        tool_type=tool_type,
        invocation_index=invocation_index,
        called_at=called_at,
        duration_ms=duration_ms,
        input_summary=truncate_payload(input_args),
        output_summary=truncate_payload(output_result) if status == "success" else None,
        status=status,
        error_type=error_type,
        error_message=error_message,
        tokens_used=tokens_used,
        model_name=model_name,
        retries=retries,
    )
