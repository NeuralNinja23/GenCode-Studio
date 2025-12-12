# app/tracking/snapshots.py
"""
Workflow snapshots for rollback.
"""
import os
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from dataclasses import dataclass


@dataclass
class Snapshot:
    """A workflow snapshot."""
    step_name: str
    timestamp: str
    files: Dict[str, str]
    quality_score: int
    agent_name: str
    approved: bool


# In-memory snapshot storage
_project_snapshots: Dict[str, List[Snapshot]] = {}


def _collect_files_sync(project_path: Path) -> Dict[str, str]:
    """Synchronous file collection helper (to be run in thread pool)."""
    files = {}
    try:
        for root, _, filenames in os.walk(project_path):
            for filename in filenames:
                if filename.endswith(('.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.md', '.css')):
                    filepath = Path(root) / filename
                    rel_path = str(filepath.relative_to(project_path))
                    try:
                        files[rel_path] = filepath.read_text(encoding='utf-8')
                    except (UnicodeDecodeError, PermissionError) as e:
                        print(f"[SNAPSHOT] Warning: Skipping file {rel_path}: {e}")
    except Exception as e:
        print(f"[SNAPSHOT] Checkpoint creation failed: {e}")
    return files


async def save_snapshot(
    project_id: str,
    project_path: Path,
    step_name: str,
    agent_name: str,
    quality_score: int,
    approved: bool,
) -> None:
    """Save a snapshot of current project state (async-safe)."""
    if project_id not in _project_snapshots:
        _project_snapshots[project_id] = []
    
    # FIX ASYNC-001: Run blocking os.walk in thread pool to not block event loop
    files = await asyncio.to_thread(_collect_files_sync, project_path)
    
    snapshot = Snapshot(
        step_name=step_name,
        timestamp=datetime.now(timezone.utc).isoformat(),
        files=files,
        quality_score=quality_score,
        agent_name=agent_name,
        approved=approved,
    )
    
    _project_snapshots[project_id].append(snapshot)
    print(f"[SNAPSHOT] 📸 Saved snapshot for {step_name} ({len(files)} files)")


def get_snapshots(project_id: str) -> List[Dict[str, Any]]:
    """Get list of snapshots for rollback."""
    snapshots = _project_snapshots.get(project_id, [])
    return [
        {
            "index": i,
            "step_name": s.step_name,
            "timestamp": s.timestamp,
            "agent_name": s.agent_name,
            "quality_score": s.quality_score,
            "approved": s.approved,
            "file_count": len(s.files),
        }
        for i, s in enumerate(snapshots)
    ]


def rollback_to_snapshot(project_id: str, project_path: Path, snapshot_index: int) -> bool:
    """Rollback to a previous snapshot."""
    snapshots = _project_snapshots.get(project_id, [])
    
    if snapshot_index < 0 or snapshot_index >= len(snapshots):
        return False
    
    snapshot = snapshots[snapshot_index]
    
    try:
        for rel_path, content in snapshot.files.items():
            filepath = project_path / rel_path
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding='utf-8')
        
        # Remove snapshots after this one
        _project_snapshots[project_id] = snapshots[:snapshot_index + 1]
        
        print(f"[SNAPSHOT] ⏪ Rolled back to {snapshot.step_name}")
        return True
    except Exception as e:
        print(f"[SNAPSHOT] Rollback failed: {e}")
        return False
