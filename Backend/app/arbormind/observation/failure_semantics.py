# app/arbormind/learning/failure_semantics.py
"""
Failure Semantics Decomposition v1

ONTOLOGICALLY SOUND SEMANTIC CLASSES:
- F7_RUNTIME_EXCEPTION: Tool executed but crashed internally (Execution plane)
- F8_TOOL_CONTRACT_VIOLATION: Tool invoked with missing/invalid inputs (Topology plane)
- F9_TOOL_ENVIRONMENT_MISSING: Tool unavailable in runtime environment (Environment plane)
- F10_POST_VALIDATION_FAILURE: Heuristic validator rejected output (Evaluation plane)
- F11_OPAQUE_TOOL_FAILURE: Tool failed without structured signal (Observability gap)

These classes are NOT siblings — they live in different causal planes.

INVARIANTS:
- These rules are PURE (no side effects)
- These rules are DETERMINISTIC (same input → same output)
- These rules are STRING-BASED (pattern matching only)
- These rules are ORDER-STABLE (first match wins)
- These rules are NON-OVERLAPPING (exactly one class per failure)
- These rules use NO PROBABILITIES
- These rules use NO LLM

These rules must NEVER:
- Call Arbormind
- Influence execution
- Change planner behavior

They are NAMING REALITY, not fixing it.
"""

import sqlite3
import re
from datetime import datetime, timezone
from typing import Optional, Literal
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════════
# SEMANTIC CLASSES (LOCKED - DO NOT MODIFY)
# ═══════════════════════════════════════════════════════════════════════════════

class SemanticClass(str, Enum):
    """
    Ontologically sound semantic failure classes.
    
    Each class lives in a different causal plane:
    - EXECUTION: Tool ran but crashed
    - TOPOLOGY: Tool was invoked incorrectly
    - ENVIRONMENT: Tool doesn't exist
    - EVALUATION: Validator rejected output
    - OBSERVABILITY: Unknown failure mode
    """
    F7_RUNTIME_EXCEPTION = "F7_RUNTIME_EXCEPTION"
    F8_TOOL_CONTRACT_VIOLATION = "F8_TOOL_CONTRACT_VIOLATION"
    F9_TOOL_ENVIRONMENT_MISSING = "F9_TOOL_ENVIRONMENT_MISSING"
    F10_POST_VALIDATION_FAILURE = "F10_POST_VALIDATION_FAILURE"
    F11_OPAQUE_TOOL_FAILURE = "F11_OPAQUE_TOOL_FAILURE"


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA (APPEND-ONLY, DETERMINISTIC, RE-RUNNABLE)
# ═══════════════════════════════════════════════════════════════════════════════

FAILURE_SEMANTICS_SCHEMA = """
CREATE TABLE IF NOT EXISTS failure_semantics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    failure_id TEXT NOT NULL,
    semantic_class TEXT NOT NULL,
    evidence TEXT NOT NULL,
    derived_by TEXT DEFAULT 'rules_v1',
    created_at DATETIME NOT NULL,
    
    FOREIGN KEY(failure_id) REFERENCES failures_v1(id)
);

CREATE INDEX IF NOT EXISTS idx_fs_failure_id ON failure_semantics(failure_id);
CREATE INDEX IF NOT EXISTS idx_fs_class ON failure_semantics(semantic_class);
CREATE INDEX IF NOT EXISTS idx_fs_derived_by ON failure_semantics(derived_by);
"""


# ═══════════════════════════════════════════════════════════════════════════════
# DETERMINISTIC MAPPING RULES v1 (LOCKED - ORDER MATTERS)
# ═══════════════════════════════════════════════════════════════════════════════

# Pattern → (SemanticClass, evidence_template)
# Order matters: first match wins
CLASSIFICATION_RULES = [
    # F9: Environment Missing (tool doesn't exist)
    (r"Unknown tool '(\w+)'", SemanticClass.F9_TOOL_ENVIRONMENT_MISSING, "Tool '{0}' not registered"),
    (r"No module named '(\w+)'", SemanticClass.F9_TOOL_ENVIRONMENT_MISSING, "Python module '{0}' not installed"),
    (r"command not found", SemanticClass.F9_TOOL_ENVIRONMENT_MISSING, "Shell command not found"),
    
    # F8: Contract Violation (missing/invalid args)
    (r"Missing (\w+)", SemanticClass.F8_TOOL_CONTRACT_VIOLATION, "Required argument '{0}' not provided"),
    (r"Missing file_path", SemanticClass.F8_TOOL_CONTRACT_VIOLATION, "file_path argument not provided by planner"),
    (r"Missing project_path", SemanticClass.F8_TOOL_CONTRACT_VIOLATION, "project_path argument not provided by planner"),
    (r"required argument", SemanticClass.F8_TOOL_CONTRACT_VIOLATION, "Required argument missing"),
    (r"invalid argument", SemanticClass.F8_TOOL_CONTRACT_VIOLATION, "Invalid argument provided"),
    
    # F10: Post-Validation Failure (heuristic rejection)
    (r"Heuristic.*check failed", SemanticClass.F10_POST_VALIDATION_FAILURE, "Heuristic validator rejected output"),
    (r"syntax check failed", SemanticClass.F10_POST_VALIDATION_FAILURE, "Syntax validation failed"),
    (r"lint.*failed", SemanticClass.F10_POST_VALIDATION_FAILURE, "Linter rejected output"),
    
    # F7: Runtime Exception (tool crashed during execution)
    (r"Tool '(\w+)' failed:", SemanticClass.F7_RUNTIME_EXCEPTION, "Tool '{0}' crashed during execution"),
    (r"Tool returned failure", SemanticClass.F7_RUNTIME_EXCEPTION, "Tool returned failure status"),
    (r"Exception|Error|Traceback", SemanticClass.F7_RUNTIME_EXCEPTION, "Runtime exception occurred"),
    
    # F11: Opaque Failure (fallback - no structured signal)
    (r".*", SemanticClass.F11_OPAQUE_TOOL_FAILURE, "Unclassified failure - needs investigation"),
]


@dataclass(frozen=True)
class SemanticClassification:
    """Result of classifying a failure."""
    failure_id: str
    semantic_class: SemanticClass
    evidence: str
    derived_by: str = "rules_v1"


def classify_failure(failure_id: str, error_message: str) -> SemanticClassification:
    """
    Classify a failure into a semantic class.
    
    PURE FUNCTION: No side effects, deterministic.
    
    Args:
        failure_id: The ID of the failure record
        error_message: The raw error message to classify
    
    Returns:
        SemanticClassification with class and evidence
    """
    if not error_message:
        return SemanticClassification(
            failure_id=failure_id,
            semantic_class=SemanticClass.F11_OPAQUE_TOOL_FAILURE,
            evidence="No error message provided",
        )
    
    for pattern, semantic_class, evidence_template in CLASSIFICATION_RULES:
        match = re.search(pattern, error_message, re.IGNORECASE)
        if match:
            # Format evidence with captured groups
            groups = match.groups()
            evidence = evidence_template.format(*groups) if groups else evidence_template
            
            return SemanticClassification(
                failure_id=failure_id,
                semantic_class=semantic_class,
                evidence=evidence,
            )
    
    # Should never reach here (last rule matches everything)
    return SemanticClassification(
        failure_id=failure_id,
        semantic_class=SemanticClass.F11_OPAQUE_TOOL_FAILURE,
        evidence=f"No rule matched: {error_message[:100]}",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PERSISTENCE (APPEND-ONLY)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_db_path() -> Path:
    """Get path to failure memory database."""
    # Same path as failure_memory.py
    return Path("arbormind_runs") / "failure_memory.db"


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Ensure failure_semantics table exists."""
    conn.executescript(FAILURE_SEMANTICS_SCHEMA)
    conn.commit()


def record_semantic_classification(classification: SemanticClassification) -> None:
    """
    Record a semantic classification (append-only).
    
    NEVER raises - observability should not crash execution.
    """
    try:
        db_path = _get_db_path()
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        _ensure_schema(conn)
        
        conn.execute(
            """
            INSERT INTO failure_semantics (failure_id, semantic_class, evidence, derived_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                classification.failure_id,
                classification.semantic_class.value,
                classification.evidence,
                classification.derived_by,
                datetime.now(timezone.utc).isoformat(),
            )
        )
        
        conn.commit()
        conn.close()
        
    except Exception:
        pass  # Never crash execution


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH RE-CLASSIFICATION (FOR HISTORICAL DATA)
# ═══════════════════════════════════════════════════════════════════════════════

def reclassify_all_failures(rules_version: str = "rules_v1") -> dict:
    """
    Re-run classification on all existing failures.
    
    This is safe because:
    - Append-only (new records, doesn't modify old)
    - Deterministic (same input → same output)
    - Re-runnable (can run multiple times)
    
    Returns stats about classification.
    """
    try:
        db_path = _get_db_path()
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        _ensure_schema(conn)
        
        # Get all failures
        cursor = conn.execute(
            "SELECT id, raw_error FROM failures_v1"
        )
        failures = cursor.fetchall()
        
        stats = {cls.value: 0 for cls in SemanticClass}
        
        for failure_id, raw_error in failures:
            classification = classify_failure(failure_id, raw_error or "")
            
            # Record with explicit rules version
            conn.execute(
                """
                INSERT INTO failure_semantics (failure_id, semantic_class, evidence, derived_by, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    classification.failure_id,
                    classification.semantic_class.value,
                    classification.evidence,
                    rules_version,
                    datetime.now(timezone.utc).isoformat(),
                )
            )
            
            stats[classification.semantic_class.value] += 1
        
        conn.commit()
        conn.close()
        
        return stats
        
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# QUERY HELPERS (READ-ONLY)
# ═══════════════════════════════════════════════════════════════════════════════

def get_semantic_stats() -> dict:
    """Get count of failures by semantic class."""
    try:
        db_path = _get_db_path()
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        
        cursor = conn.execute(
            """
            SELECT semantic_class, COUNT(*) as count
            FROM failure_semantics
            WHERE derived_by = 'rules_v1'
            GROUP BY semantic_class
            ORDER BY count DESC
            """
        )
        
        stats = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        
        return stats
        
    except Exception:
        return {}


def get_failures_by_class(semantic_class: SemanticClass, limit: int = 10) -> list:
    """Get recent failures of a specific semantic class."""
    try:
        db_path = _get_db_path()
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        
        cursor = conn.execute(
            """
            SELECT fs.failure_id, fs.evidence, fs.created_at, f.step, f.agent
            FROM failure_semantics fs
            JOIN failures_v1 f ON fs.failure_id = f.id
            WHERE fs.semantic_class = ? AND fs.derived_by = 'rules_v1'
            ORDER BY fs.created_at DESC
            LIMIT ?
            """,
            (semantic_class.value, limit)
        )
        
        results = [
            {
                "failure_id": row[0],
                "evidence": row[1],
                "created_at": row[2],
                "step": row[3],
                "agent": row[4],
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return results
        
    except Exception:
        return []
