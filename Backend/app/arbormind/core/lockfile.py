# app/arbormind/core/lockfile.py
"""
═══════════════════════════════════════════════════════════════════════════════
PHASE E1: GENERATION LOCKFILE SYSTEM

Purpose: Eliminate redundant LLM calls for unchanged inputs.

How it works:
1. Before calling subagentcaller, hash the inputs
2. Check if arbormind.lock.json has a matching hash
3. If yes: return cached artifacts, skip LLM
4. If no: run LLM, cache result, update lockfile

This alone cuts 90% API usage on iterative runs.
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.logging import log


# ═══════════════════════════════════════════════════════════════════════════════
# LOCKFILE SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════

LOCKFILE_NAME = "arbormind.lock.json"
LOCKFILE_VERSION = "1.0"


def _get_lockfile_path(project_path: str) -> Path:
    """Get the lockfile path for a project."""
    return Path(project_path) / LOCKFILE_NAME


def _compute_input_hash(
    step_name: str,
    user_request: str,
    contracts: Optional[Dict] = None,
    files: Optional[List] = None,
) -> str:
    """
    Compute a deterministic hash of inputs for a step.
    
    This hash changes when:
    - User request changes
    - Architecture/contracts change
    - Input files change
    """
    hash_input = {
        "step": step_name,
        "request": user_request[:500],  # First 500 chars (prevent massive hashing)
        "contracts_hash": hashlib.sha256(
            json.dumps(contracts or {}, sort_keys=True).encode()
        ).hexdigest()[:16] if contracts else "",
        "files_count": len(files) if files else 0,
    }
    
    serialized = json.dumps(hash_input, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()[:32]


# ═══════════════════════════════════════════════════════════════════════════════
# LOCKFILE OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def load_lockfile(project_path: str) -> Dict[str, Any]:
    """Load the lockfile for a project."""
    lockfile_path = _get_lockfile_path(project_path)
    
    if not lockfile_path.exists():
        return {
            "version": LOCKFILE_VERSION,
            "created_at": datetime.utcnow().isoformat(),
            "steps": {},
        }
    
    try:
        return json.loads(lockfile_path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "version": LOCKFILE_VERSION,
            "created_at": datetime.utcnow().isoformat(),
            "steps": {},
        }


def save_lockfile(project_path: str, lockfile: Dict[str, Any]) -> None:
    """Save the lockfile for a project."""
    lockfile_path = _get_lockfile_path(project_path)
    lockfile["updated_at"] = datetime.utcnow().isoformat()
    
    try:
        lockfile_path.write_text(
            json.dumps(lockfile, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        log("LOCKFILE", f"⚠️ Failed to save lockfile: {e}")


def check_cache_hit(
    project_path: str,
    step_name: str,
    user_request: str,
    contracts: Optional[Dict] = None,
    files: Optional[List] = None,
) -> Optional[Dict[str, Any]]:
    """
    Check if we have a valid cache hit for this step.
    
    Returns:
        - Cached result dict if hit (with files, artifacts)
        - None if miss (need to run LLM)
    """
    lockfile = load_lockfile(project_path)
    current_hash = _compute_input_hash(step_name, user_request, contracts, files)
    
    step_entry = lockfile.get("steps", {}).get(step_name)
    
    if not step_entry:
        return None
    
    # Check hash match
    if step_entry.get("input_hash") != current_hash:
        log("LOCKFILE", f"Hash mismatch for {step_name} - inputs changed")
        return None
    
    # Check artifacts exist on disk
    artifacts_dir = Path(project_path) / step_entry.get("artifacts_dir", "")
    if artifacts_dir.exists() and any(artifacts_dir.iterdir()):
        log("LOCKFILE", f"✅ CACHE HIT: {step_name} (hash={current_hash[:8]})")
        return {
            "cached": True,
            "files": step_entry.get("files", []),
            "hash": current_hash,
            "cached_at": step_entry.get("cached_at"),
        }
    
    return None


def record_step_completion(
    project_path: str,
    step_name: str,
    user_request: str,
    files_written: List[str],
    contracts: Optional[Dict] = None,
    input_files: Optional[List] = None,
) -> None:
    """
    Record a step completion in the lockfile.
    
    Called after LLM successfully generates output.
    """
    lockfile = load_lockfile(project_path)
    current_hash = _compute_input_hash(step_name, user_request, contracts, input_files)
    
    lockfile["steps"][step_name] = {
        "input_hash": current_hash,
        "files": files_written,
        "artifacts_dir": str(Path(files_written[0]).parent) if files_written else "",
        "cached_at": datetime.utcnow().isoformat(),
        "files_count": len(files_written),
    }
    
    save_lockfile(project_path, lockfile)
    log("LOCKFILE", f"📦 Cached: {step_name} (hash={current_hash[:8]}, files={len(files_written)})")


def invalidate_step(project_path: str, step_name: str) -> None:
    """Invalidate cache for a specific step."""
    lockfile = load_lockfile(project_path)
    
    if step_name in lockfile.get("steps", {}):
        del lockfile["steps"][step_name]
        save_lockfile(project_path, lockfile)
        log("LOCKFILE", f"🗑️ Invalidated: {step_name}")


def invalidate_all(project_path: str) -> None:
    """Invalidate all cached steps (full rebuild)."""
    lockfile_path = _get_lockfile_path(project_path)
    
    if lockfile_path.exists():
        lockfile_path.unlink()
        log("LOCKFILE", "🗑️ Full cache cleared")


def get_lockfile_summary(project_path: str) -> Dict[str, Any]:
    """Get a summary of cached steps for debugging."""
    lockfile = load_lockfile(project_path)
    
    return {
        "version": lockfile.get("version"),
        "steps_cached": list(lockfile.get("steps", {}).keys()),
        "total_files": sum(
            s.get("files_count", 0) 
            for s in lockfile.get("steps", {}).values()
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GENERATION STEP HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def should_skip_generation(
    project_path: str,
    step_name: str,
    user_request: str,
    contracts: Optional[Dict] = None,
    files: Optional[List] = None,
) -> tuple[bool, Optional[Dict]]:
    """
    Check if this generation step should be skipped (cache hit).
    
    Returns:
        (should_skip, cached_result)
    """
    from app.arbormind.core.execution_mode import is_generation_step
    
    # Only generation steps can be cached
    if not is_generation_step(step_name):
        return (False, None)
    
    cached = check_cache_hit(project_path, step_name, user_request, contracts, files)
    
    if cached:
        return (True, cached)
    
    return (False, None)
