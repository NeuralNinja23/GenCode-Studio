# app/persistence/writer.py
"""
File persistence with safety checks.
Consolidated from app.lib.file_writer and app.persistence.writer.
"""
import re
from pathlib import Path
from typing import Any, Dict, List

from app.core.constants import PROTECTED_FILES
from app.core.logging import log
from app.persistence.filesystem import get_safe_workspace_path, sanitize_project_id
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
    
    Features:
    - Validates paths for security
    - Blocks protected sandbox files
    - Cleans invalid filename characters
    - Validates Python syntax (AST check)
    - Beautifies UI components (Tailwind sorting, etc.)
    - Broadcasts updates via WebSocket
    
    Args:
        manager: WebSocket connection manager
        project_id: Project identifier
        project_path: Path to project directory
        files: List of file dicts with 'path' and 'content' (or 'file', 'name', 'code', 'text')
        step_name: Workflow step name for logging
        log_prefix: Optional prefix for log messages
        
    Returns:
        Number of files successfully written
    """
    if not files:
        return 0

    # Apply UI beautifier to frontend files (provider-agnostic post-processing)
    try:
        from app.utils.ui_beautifier import beautify_frontend_files
        # Helper expects simple dicts, consistent with our input
        files = beautify_frontend_files(files)
    except ImportError:
        pass
    except Exception as e:
        log("PERSIST", f"⚠️ UI beautifier failed: {e}", project_id=project_id)

    safe_ws = get_safe_workspace_path(project_path.parent, sanitize_project_id(project_path.name))
    safe_ws.mkdir(parents=True, exist_ok=True)

    written: List[Dict[str, Any]] = []
    prefix = f"{log_prefix} " if log_prefix else ""
    count_written = 0

    for entry in files:
        if not isinstance(entry, dict):
            continue

        # Support multiple key names for path (unification from lib.file_writer)
        raw_path = entry.get("path") or entry.get("file") or entry.get("name") or entry.get("filename")
        # Support multiple key names for content
        content = entry.get("content") or entry.get("code") or entry.get("text") or ""

        if not raw_path:
            # log("PERSIST", f"{prefix}Skipping file with no path: {entry.keys()}")
            continue

        # Normalization
        rel_path = str(raw_path).replace("\\", "/").strip().lstrip("/")
        
        # Block protected infrastructure files
        if rel_path in PROTECTED_FILES:
            log("PERSIST", f"{prefix}❌ BLOCKED write to protected sandbox file: {rel_path}", project_id=project_id)
            continue

        # Clean filename - remove invalid characters
        clean_path = re.sub(r'[<>:"|?*]', "", rel_path)
        if not clean_path:
            log("PERSIST", f"{prefix}Invalid filename after cleaning: '{rel_path}', skipping", project_id=project_id)
            continue

        # Syntax Validation (from former persistence.writer)
        try:
             from app.validation.syntax_validator import validate_syntax
             validation_result = validate_syntax(clean_path, content)
             
             if not validation_result.valid:
                  log("PERSIST", f"{prefix}❌ Skipping invalid file (syntax error): {clean_path} - {validation_result.errors[0]}", project_id=project_id)
                  continue
             
             # ═══════════════════════════════════════════════════════════════
             # CRITICAL: Use normalized content if validation modified it
             # ═══════════════════════════════════════════════════════════════
             # validate_syntax returns Unicode-normalized content in fixed_content
             # We MUST use this instead of original content to ensure ASCII-only code
             if validation_result.fixed_content:
                 content = validation_result.fixed_content
                 log("PERSIST", f"{prefix}🔧 Using Unicode-normalized content for {clean_path}", project_id=project_id)
             
             # ═══════════════════════════════════════════════════════════════
             # ROUTER SEMANTIC VALIDATION (catches query param issues)
             # ═══════════════════════════════════════════════════════════════
             # Check routers for required list params BEFORE tests fail
             if clean_path.endswith('.py') and '/routers/' in clean_path:
                 try:
                     from app.orchestration.heal_helpers import has_optional_list_params
                     list_ok, list_issues = has_optional_list_params(content)
                     if not list_ok:
                         # Log warning but don't block - this is a semantic issue, not syntax
                         log("PERSIST", f"{prefix}⚠️ Router has required list params: {list_issues[0][:80]}", project_id=project_id)
                         # Note: We log but don't skip - tests will catch it and healing will fix
                 except Exception as router_err:
                     log("PERSIST", f"{prefix}⚠️ Router check failed: {router_err}", project_id=project_id)
                     
        except Exception as val_err:
             log("PERSIST", f"{prefix}⚠️ Validator crashed on {clean_path}: {val_err}. Skipping for safety.", project_id=project_id)
             continue

        # Write
        abs_path = safe_ws / Path(clean_path)
        
        # Security check: ensure escape from workspace is impossible (common traversal check)
        # safe_ws is absolute. abs_path must start with safe_ws.
        try:
            abs_path.resolve().relative_to(safe_ws.resolve())
        except ValueError:
            log("PERSIST", f"{prefix}❌ SECURITY: Path traversal detected - {clean_path}", project_id=project_id)
            continue

        try:
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content, encoding="utf-8")
        except Exception as e:
            log("PERSIST", f"{prefix}Failed to write {clean_path}: {e}", project_id=project_id)
            continue

        size_kb = round(len(content.encode("utf-8")) / 1024, 2)
        log("PERSIST", f"{prefix}📝 Wrote: {clean_path} ({size_kb} KB)", project_id=project_id)
        
        written.append({"path": clean_path, "size_kb": size_kb})
        count_written += 1

    if written:
        await broadcast_to_project(
            manager,
            project_id,
            {
                "type": "WORKSPACE_UPDATED",
                "projectId": project_id,
                "filesWritten": count_written, # Persistence API used list, but writer used count. Let's send count.
                "files": written, # Send detailed list too if needed
                "step": step_name,
            },
        )

    return count_written


async def persist_agent_output(
    manager: Any,
    project_id: str,
    project_path: Path,
    response: Dict[str, Any],
    step_name: str = "unknown",
) -> int:
    """
    Wrapper for safe_write_llm_files to handle standard agent response dict.
    Unpacks 'files' from the response and calls the core writer.
    """
    files = response.get("files", [])
    if not files:
        return 0
        
    return await safe_write_llm_files(
        manager=manager,
        project_id=project_id,
        project_path=project_path,
        files=files,
        step_name=step_name
    )
