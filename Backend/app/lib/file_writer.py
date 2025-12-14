# app/lib/file_writer.py
"""
Centralized File Writing Utilities - Single source of truth for LLM file persistence.

This module provides safe file writing for LLM-generated content.
Import from here instead of duplicating in handlers.
"""
import re
from pathlib import Path
from typing import Any, Dict, List

from app.core.logging import log
from app.core.constants import PROTECTED_SANDBOX_FILES
from app.lib.file_system import get_safe_workspace_path, sanitize_project_id
from app.orchestration.utils import broadcast_to_project


async def safe_write_llm_files(
    manager: Any,
    project_id: str,
    project_path: Path,
    files: List[Dict[str, Any]],
    step_name: str,
    log_prefix: str = "",
) -> int:
    """
    Safely write LLM-generated files to the workspace.
    
    This is the SINGLE SOURCE OF TRUTH for writing LLM output files.
    Replaces the duplicate safe_write_llm_files_for_testing in multiple handlers.
    
    Features:
    - Validates paths for security
    - Blocks protected sandbox files
    - Cleans invalid filename characters
    - Broadcasts updates via WebSocket
    
    Args:
        manager: WebSocket connection manager
        project_id: Project identifier
        project_path: Path to project directory
        files: List of file dicts with 'path' and 'content'
        step_name: Workflow step name for logging
        log_prefix: Optional prefix for log messages (e.g., "[TEST]", "[REFINE]")
        
    Returns:
        Number of files successfully written
    """
    if not files:
        return 0

    safe_ws = get_safe_workspace_path(project_path.parent, sanitize_project_id(project_path.name))
    safe_ws.mkdir(parents=True, exist_ok=True)

    written: List[Dict[str, Any]] = []
    prefix = f"{log_prefix} " if log_prefix else ""

    for entry in files:
        if not isinstance(entry, dict):
            continue

        # Support multiple key names for path
        raw_path = entry.get("path") or entry.get("file") or entry.get("name") or entry.get("filename")
        # Support multiple key names for content
        content = entry.get("content") or entry.get("code") or entry.get("text") or ""

        if not raw_path:
            log("PERSIST", f"{prefix}Skipping file with no path: {entry.keys()}")
            continue

        rel_path = str(raw_path).replace("\\", "/").strip()

        # Block protected infrastructure files
        if rel_path in PROTECTED_SANDBOX_FILES:
            log("PERSIST", f"{prefix}❌ BLOCKED write to protected sandbox file: {rel_path}")
            continue

        # Clean filename - remove invalid characters
        clean_path = re.sub(r'[<>:"|?*]', "", rel_path)
        if not clean_path:
            log("PERSIST", f"{prefix}Invalid filename after cleaning: '{rel_path}', skipping")
            continue

        abs_path = safe_ws / Path(clean_path)
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            abs_path.write_text(content, encoding="utf-8")
        except Exception as e:
            log("PERSIST", f"{prefix}Failed to write {abs_path}: {e}")
            continue

        size_kb = round(len(content.encode("utf-8")) / 1024, 2)
        log("WRITE", f"{prefix}{abs_path} ({size_kb} KB)")
        written.append({"path": clean_path, "size_kb": size_kb})

    if written:
        await broadcast_to_project(
            manager,
            project_id,
            {
                "type": "WORKSPACE_UPDATED",
                "projectId": project_id,
                "filesWritten": written,
                "step": step_name,
            },
        )

    return len(written)
