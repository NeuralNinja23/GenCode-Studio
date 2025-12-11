# app/handlers/refine.py
"""
Refine Mode - Conversational Iteration (post-workflow).

Triggered when user sends follow-up messages to a completed project.
This matches the legacy workflows.py step_refine logic exactly.
"""
from pathlib import Path
from typing import Any, Dict, List

from app.core.types import ChatMessage, StepResult
from app.core.constants import WorkflowStep
from app.core.exceptions import RateLimitError
from app.handlers.base import broadcast_status
from app.core.logging import log
from app.tools import run_tool
from app.utils.parser import normalize_llm_output
from app.orchestration.state import WorkflowStateManager
from app.attention import compute_ui_vibe_routing


# Constants from legacy
MAX_FILES_PER_STEP = 20


from app.persistence.validator import validate_file_output



async def safe_write_llm_files_for_testing(
    manager: Any,
    project_id: str,
    project_path: Path,
    files: List[Dict[str, Any]],
    step_name: str,
) -> int:
    """Safely write files for refine step."""
    import re
    from app.lib.file_system import get_safe_workspace_path, sanitize_project_id
    from app.orchestration.utils import broadcast_to_project

    if not files:
        return 0

    safe_ws = get_safe_workspace_path(project_path.parent, sanitize_project_id(project_path.name))
    safe_ws.mkdir(parents=True, exist_ok=True)

    written: List[Dict[str, Any]] = []

    for entry in files:
        if not isinstance(entry, dict):
            continue

        raw_path = entry.get("path") or entry.get("file") or entry.get("name") or entry.get("filename")
        content = entry.get("content") or entry.get("code") or entry.get("text") or ""

        if not raw_path:
            log("PERSIST", f"[REFINE] Skipping file with no path: {entry.keys()}")
            continue

        rel_path = str(raw_path).replace("\\", "/").strip()

        # Clean filename
        clean_path = re.sub(r'[<>:"|?*]', "", rel_path)
        if not clean_path:
            log("PERSIST", f"[REFINE] Invalid filename after cleaning: '{rel_path}', skipping")
            continue

        abs_path = safe_ws / Path(clean_path)
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            abs_path.write_text(content, encoding="utf-8")
        except Exception as e:
            log("PERSIST", f"[REFINE] Failed to write {abs_path}: {e}")
            continue

        size_kb = round(len(content.encode("utf-8")) / 1024, 2)
        log("WRITE", f"[REFINE] {abs_path} ({size_kb} KB)")
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


async def step_refine(
    project_id: str,
    user_request: str,
    manager: Any,
    project_path: Path,
    chat_history: List[ChatMessage],
    provider: str,
    model: str,
    current_turn: int,
    max_turns: int,
) -> StepResult:
    """
    Refine Mode - Conversational Iteration (post-workflow).
    
    Allows the user to modify the existing codebase using natural language.
    Example: "Change the button color to blue" or "Add a phone number field".
    """
    await broadcast_status(
        manager,
        project_id,
        WorkflowStep.REFINE,
        f"Refining codebase: {user_request[:50]}...",
        current_turn,
        max_turns,
    )

    # 🔥 NEW: detect if user is changing vibe/style
    intent = await WorkflowStateManager.get_intent(project_id) or {}
    prev_vibe = ((intent.get("uiVibeRouting") or {}).get("top")) or None
    archetype = (intent.get("archetypeRouting") or {}).get("top") or "general"

    new_vibe = None
    try:
        routing = await compute_ui_vibe_routing(user_request)
        new_vibe = (routing or {}).get("top")
        if new_vibe:
            intent["uiVibeRouting"] = routing
            await WorkflowStateManager.set_intent(project_id, intent)
    except Exception as e:
        log("REFINE", f"UI vibe routing failed during refine: {e}", project_id=project_id)

    vibe_changed = bool(prev_vibe and new_vibe and prev_vibe != new_vibe)
    
    # 🔥 NEW: Classify if this is a backend change
    lower_req = user_request.lower()
    backend_keywords = ["api", "endpoint", "status code", "model", "database", "validation", "soft delete", "field", "schema", "backend", "priority", "order", "tenant", "organization"]
    ui_keywords = ["color", "button", "layout", "spacing", "gradient", "font", "theme", "vibe", "animation", "style"]

    backend_score = sum(1 for k in backend_keywords if k in lower_req)
    ui_score = sum(1 for k in ui_keywords if k in lower_req)

    is_backend_change = backend_score >= ui_score and backend_score > 0

    # 1. List all files to give Derek context of the project structure
    # We use a simple recursive list, excluding node_modules/venv
    all_files = []
    for f in project_path.rglob("*"):
        if f.is_file() and "node_modules" not in f.parts and "__pycache__" not in f.parts and ".git" not in f.parts:
            try:
                # Only include text files
                all_files.append(str(f.relative_to(project_path)))
            except Exception:
                pass
    
    file_list_str = "\n".join(all_files[:200])  # Limit to avoid token overflow

    # 2. Ask Derek to identify which files need to be modified
    analysis_prompt = f"""
    USER REQUEST: "{user_request}"
    
    PROJECT FILES:
    {file_list_str}
    
    Identify which files need to be modified to satisfy the user request.
    Return ONLY a JSON object with a "files_to_read" list.
    Example: {{ "files_to_read": ["frontend/src/App.jsx", "backend/app/models.py"] }}
    """

    try:
        log("REFINE", f"Analyzing project to find files related to: {user_request[:80]}...", project_id=project_id)
        
        # We use a quick tool call to get the file list
        tool_result = await run_tool(
            name="subagentcaller",
            args={
                "sub_agent": "Derek",
                "instructions": analysis_prompt,
                "project_path": str(project_path),
                "project_id": project_id,  # For thinking broadcast
            },
        )
        
        raw_output = tool_result.get("output", {})
        parsed = raw_output if isinstance(raw_output, dict) else normalize_llm_output(str(raw_output))
        files_to_read = parsed.get("files_to_read", [])
        
        log("REFINE", f"Derek identified {len(files_to_read)} files to modify: {files_to_read}", project_id=project_id)
        
        # 3. Read the content of the identified files
        file_contents = {}
        for rel_path in files_to_read:
            try:
                full_path = project_path / rel_path
                if full_path.exists():
                    file_contents[rel_path] = full_path.read_text(encoding="utf-8")
            except Exception as e:
                log("REFINE", f"Failed to read {rel_path}: {e}", project_id=project_id)

        context_str = "\n".join([f"--- {k} ---\n{v}" for k, v in file_contents.items()])

        # 4. Ask Derek to generate the fix (Patches or Full Files)
        backend_hint = ""
        if is_backend_change:
            backend_hint = f"""
This refine request appears to be BACKEND/BUSINESS-LOGIC related.

You MUST:
1. Update `contracts.md` and the `## Backend Design Patterns` section in `architecture.md`
   to reflect the new behaviour (fields, status values, flows).
2. Then update backend models/routers (`backend/app/models.py`, `backend/app/routers/**`)
   so they strictly follow the updated contracts and patterns.
3. Add or fix backend tests in `backend/tests/**` to cover the new behaviour.
"""

        vibe_note = ""
        if new_vibe:
            vibe_note = f"Detected NEW requested UI vibe: {new_vibe} (previous: {prev_vibe or 'unknown'}).\n"
            if vibe_changed:
                vibe_note += (
                    "You MUST first update the UI Design System in architecture.md and the design tokens in "
                    "`frontend/src/design/tokens.json` / `frontend/src/design/theme.ts` to match this new vibe, "
                    "then update components to use the updated tokens.\n"
                )

        refine_prompt = f"""
        USER REQUEST: "{user_request}"
        
        ARCHETYPE: {archetype}
        
        {backend_hint}
        
        {vibe_note}
        
        CONTEXT FILES:
        {context_str}
        
        TASK:
        Apply the requested changes.

        If the requested change is primarily visual or vibe-related:
        - Prefer editing `architecture.md` (UI Design System section) and `frontend/src/design/tokens.json` / `theme.ts`
          to update global styling.
        - Then adjust only the minimal set of components needed to align with the new design system.
        
        OUTPUT FORMAT:
        Return a JSON object with EITHER:
        1. "files": [ {{ "path": "...", "content": "FULL NEW CONTENT" }} ]
        OR
        2. "patch": "Unified Diff String"
        """

        log("REFINE", f"Derek is generating code changes...", project_id=project_id)
        
        tool_result = await run_tool(
            name="subagentcaller",
            args={
                "sub_agent": "Derek",
                "instructions": refine_prompt,
                "project_path": str(project_path),
                "project_id": project_id,  # For thinking broadcast
            },
        )

        # 5. Apply the changes
        raw_output = tool_result.get("output", {})
        parsed = raw_output if isinstance(raw_output, dict) else normalize_llm_output(str(raw_output))

        changes_made = 0
        
        # Handle full file rewrites
        if "files" in parsed and parsed["files"]:
            valid = validate_file_output(parsed, WorkflowStep.REFINE)
            changes_made = await safe_write_llm_files_for_testing(
                manager, project_id, project_path, valid["files"], WorkflowStep.REFINE
            )
        
        # Handle patches
        elif "patch" in parsed and parsed["patch"]:
            patch_res = await run_tool(
                name="unifiedpatchapplier",
                args={
                    "project_path": str(project_path),
                    "patch": parsed["patch"]
                }
            )
            if patch_res.get("success"):
                changes_made = patch_res.get("files_patched", 1)
                log("REFINE", f"Applied patch successfully", project_id=project_id)
            else:
                log("REFINE", f"Patch failed: {patch_res.get('error')}", project_id=project_id)

        log("REFINE", f"✅ Applied {changes_made} file changes", project_id=project_id)
        chat_history.append({"role": "assistant", "content": str(parsed)})
        
    except RateLimitError:
        log("REFINE", "Rate limit exhausted - stopping workflow", project_id=project_id)
        raise
        
    except Exception as e:
        log("REFINE", f"Refinement failed: {e}", project_id=project_id)

    # FIX #5: Return to REFINE step (not PREVIEW_FINAL) to allow multiple refinements
    # The workflow will pause at REFINE waiting for more user input
    # Only go to PREVIEW_FINAL if user explicitly asks to "preview" or "finish"
    lower_request = user_request.lower()
    wants_preview = any(word in lower_request for word in ["preview", "finish", "done", "complete", "show me", "run it"])
    
    if wants_preview:
        return StepResult(
            nextstep=WorkflowStep.PREVIEW_FINAL,
            turn=current_turn + 1,
        )
    else:
        # Stay in refine mode for further iterations
        return StepResult(
            nextstep=WorkflowStep.COMPLETE,  # Mark as complete but allow resume_workflow to start REFINE again
            turn=current_turn + 1,
            data={"refine_complete": True, "awaiting_more_input": True}
        )
