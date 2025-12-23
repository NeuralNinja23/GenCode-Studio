# app/arbormind/observation/step_state_snapshot.py
"""
Step State Snapshot (SSS) - Phase 3 Primitive

PURPOSE: Capture workspace state at step entry and exit.
         Pure observation, no semantics.

═══════════════════════════════════════════════════════════════════════════════
NON-NEGOTIABLE CONSTRAINTS
═══════════════════════════════════════════════════════════════════════════════

1. OBSERVATIONAL ONLY - No interpretation, no semantics
2. NO DIFFS - Just "what exists", not "what changed"
3. NO BLAME - No "caused by", no "changed_by"
4. NO CAUSALITY - That's Phase 4
5. APPEND-ONLY - Every snapshot is immutable
6. FAIL-SAFE - Must never crash execution

This enables horizontal continuity between steps:
    "Step N entered with state X, exited with state Y"

Derivable later (Phase 4):
    - Overwrites (Y ≠ X)
    - Regressions
    - Missing dependencies
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODEL (Immutable)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class StepStateSnapshot:
    """
    Immutable workspace state at a moment in time.
    
    No semantics. Just facts.
    """
    run_id: str
    step_name: str
    position: Literal["entry", "exit"]
    timestamp: datetime
    
    # Artifact inventory
    artifact_count: int
    artifact_paths_hash: str  # SHA256 of sorted paths
    artifact_manifest: List[Dict[str, Any]]  # [{path, size_bytes}]
    
    # Workspace fingerprint
    workspace_hash: str  # Hash of (paths + sizes)


# ═══════════════════════════════════════════════════════════════════════════════
# CAPTURE FUNCTIONS (Pure, No Side Effects)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_paths_hash(paths: List[str]) -> str:
    """Hash of sorted artifact paths."""
    sorted_paths = sorted(paths)
    content = "\n".join(sorted_paths)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def compute_workspace_hash(manifest: List[Dict[str, Any]]) -> str:
    """Hash of workspace state (paths + sizes)."""
    # Sort by path for determinism
    sorted_manifest = sorted(manifest, key=lambda x: x.get("path", ""))
    content = json.dumps(sorted_manifest, sort_keys=True)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def capture_workspace_state(project_path: Path) -> tuple[List[Dict[str, Any]], int]:
    """
    Capture current workspace artifact inventory.
    
    Returns:
        (manifest, artifact_count)
    """
    manifest = []
    
    if not project_path.exists():
        return [], 0
    
    try:
        # Walk project, collecting files
        for root, dirs, files in os.walk(project_path):
            # Skip hidden directories and common noise
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                'node_modules', '__pycache__', '.git', '.venv', 'venv', 
                'dist', 'build', '.next', '.cache'
            }]
            
            for file in files:
                # Skip hidden files
                if file.startswith('.'):
                    continue
                
                file_path = Path(root) / file
                try:
                    rel_path = file_path.relative_to(project_path)
                    size = file_path.stat().st_size
                    manifest.append({
                        "path": str(rel_path),
                        "size_bytes": size
                    })
                except Exception:
                    pass  # Skip files we can't stat
        
        return manifest, len(manifest)
        
    except Exception:
        return [], 0


def create_snapshot(
    run_id: str,
    step_name: str,
    position: Literal["entry", "exit"],
    project_path: Path,
) -> StepStateSnapshot:
    """
    Create a step state snapshot.
    
    Pure function - no side effects, no database writes.
    """
    manifest, count = capture_workspace_state(project_path)
    paths = [m["path"] for m in manifest]
    
    return StepStateSnapshot(
        run_id=run_id,
        step_name=step_name,
        position=position,
        timestamp=datetime.now(timezone.utc),
        artifact_count=count,
        artifact_paths_hash=compute_paths_hash(paths),
        artifact_manifest=manifest,
        workspace_hash=compute_workspace_hash(manifest),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# RECORDING (Fire-and-Forget, Fail-Safe)
# ═══════════════════════════════════════════════════════════════════════════════

def record_step_state_snapshot(snapshot: StepStateSnapshot) -> bool:
    """
    Record a step state snapshot to database.
    
    MUST NEVER CRASH EXECUTION.
    Fire-and-forget.
    
    Returns True if recorded, False otherwise (but never raises).
    """
    try:
        from app.arbormind.observation.execution_ledger import get_store
        
        store = get_store()
        with store._cursor() as cursor:
            cursor.execute("""
                INSERT INTO step_state_snapshots (
                    run_id, step_name, position, timestamp,
                    artifact_count, artifact_paths_hash, artifact_manifest,
                    workspace_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot.run_id,
                snapshot.step_name,
                snapshot.position,
                snapshot.timestamp.isoformat(),
                snapshot.artifact_count,
                snapshot.artifact_paths_hash,
                json.dumps(snapshot.artifact_manifest),
                snapshot.workspace_hash,
            ))
        return True
        
    except Exception:
        # SSS must never crash execution
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE HOOKS (For Orchestrator Integration)
# ═══════════════════════════════════════════════════════════════════════════════

def record_step_entry(
    run_id: str,
    step_name: str,
    project_path: Path,
) -> Optional[StepStateSnapshot]:
    """
    Record workspace state at step entry.
    
    Call this BEFORE step execution begins.
    """
    try:
        snapshot = create_snapshot(run_id, step_name, "entry", project_path)
        record_step_state_snapshot(snapshot)
        return snapshot
    except Exception:
        return None


def record_step_exit(
    run_id: str,
    step_name: str,
    project_path: Path,
) -> Optional[StepStateSnapshot]:
    """
    Record workspace state at step exit.
    
    Call this AFTER step execution completes (success or failure).
    """
    try:
        snapshot = create_snapshot(run_id, step_name, "exit", project_path)
        record_step_state_snapshot(snapshot)
        return snapshot
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# QUERY FUNCTIONS (Read-Only, For Offline Analysis)
# ═══════════════════════════════════════════════════════════════════════════════

def get_step_snapshots(
    run_id: str,
    step_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get snapshots for a run (optionally filtered by step).
    
    For offline analysis only - NOT during execution.
    """
    try:
        from app.arbormind.observation.execution_ledger import get_store
        
        store = get_store()
        with store._cursor() as cursor:
            if step_name:
                cursor.execute("""
                    SELECT * FROM step_state_snapshots
                    WHERE run_id = ? AND step_name = ?
                    ORDER BY timestamp
                """, (run_id, step_name))
            else:
                cursor.execute("""
                    SELECT * FROM step_state_snapshots
                    WHERE run_id = ?
                    ORDER BY timestamp
                """, (run_id,))
            
            return [dict(row) for row in cursor.fetchall()]
            
    except Exception:
        return []


def get_step_state_diff(
    run_id: str,
    step_name: str,
) -> Optional[Dict[str, Any]]:
    """
    Get entry and exit state for a step.
    
    Returns {entry: ..., exit: ..., changed: bool}
    
    For offline analysis only.
    NOTE: This does NOT interpret WHY it changed - that's Phase 4.
    """
    try:
        snapshots = get_step_snapshots(run_id, step_name)
        
        entry = None
        exit_ = None
        
        for s in snapshots:
            if s.get("position") == "entry":
                entry = s
            elif s.get("position") == "exit":
                exit_ = s
        
        if entry and exit_:
            return {
                "entry": entry,
                "exit": exit_,
                "changed": entry.get("workspace_hash") != exit_.get("workspace_hash")
            }
        
        return None
        
    except Exception:
        return None
