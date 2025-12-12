# app/persistence/writer.py
"""
File persistence with safety checks.
"""
from pathlib import Path
from typing import Any, Dict

from app.core.constants import PROTECTED_FILES
from app.core.logging import log


async def persist_agent_output(
    manager: Any,
    project_id: str,
    project_path: Path,
    response: Dict[str, Any],
    step_name: str = "unknown",
) -> int:
    """
    Write agent output files to disk.
    
    Respects:
    - Protected files (Dockerfiles, etc.)
    - Creates parent directories as needed
    - Applies UI beautification to frontend files (provider-agnostic)
    
    Returns:
        Number of files written
    """
    files = response.get("files", [])
    
    # Apply UI beautifier to frontend files (provider-agnostic post-processing)
    try:
        from app.utils.ui_beautifier import beautify_frontend_files
        files = beautify_frontend_files(files)
    except ImportError:
        pass  # Beautifier not available, continue without it
    except Exception as e:
        log("PERSIST", f"⚠️ UI beautifier failed: {e}", project_id=project_id)
    
    written = 0
    
    for f in files:
        path = f.get("path", "")
        content = f.get("content", "")
        
        if not path or not content:
            continue
        
        # Check protected files
        normalized = path.replace("\\", "/").lstrip("/")
        if normalized in PROTECTED_FILES:
            log("PERSIST", f"⚠️ Skipping protected file: {path}", project_id=project_id)
            continue
        
        # Persistence-Level Hard Stop
        # Enforce AST validation before any file hits disk
        try:
             from app.validation.syntax_validator import validate_file
             validation_result = validate_file(normalized, content)
             
             if not validation_result.valid:
                  # CRITICAL: Do not write broken files. 
                  # This ensures Orchestrator sees empty output if all files are bad.
                  log("PERSIST", f"❌ Skipping invalid file (blocked by validator): {normalized} - {validation_result.errors[0]}", project_id=project_id)
                  continue
             
        except Exception as val_err:
             # If validator itself crashes (rare), play it safe and warn but maybe allow?
             # Better to be strict: log and skip
             log("PERSIST", f"⚠️ Validator crashed on {normalized}: {val_err}. Skipping for safety.", project_id=project_id)
             continue

        try:
            target = project_path / normalized
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            written += 1
            log("PERSIST", f"📝 Wrote: {normalized}", project_id=project_id)
        except Exception as e:
            log("PERSIST", f"❌ Failed to write {path}: {e}", project_id=project_id)
    
    if written > 0:
        # Notify frontend of workspace update
        from app.orchestration.utils import broadcast_to_project
        await broadcast_to_project(
            manager,
            project_id,
            {
                "type": "WORKSPACE_UPDATED",
                "projectId": project_id,
                "step": step_name,
                "filesWritten": written,
            },
        )
    
    return written
