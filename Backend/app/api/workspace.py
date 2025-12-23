# app/api/workspace.py
"""
Workspace file operations.
"""
import asyncio
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from app.core.config import settings
from app.core.logging import log
from app.utils.path_utils import get_project_path

# ============================================================================
# WORKSPACE API ROUTER
# ============================================================================
# This module provides file operations and workflow management for workspaces.
# 
# Note: Some routes have deprecated alternatives for backwards compatibility.
# These will be removed in a future major version.
# ============================================================================

router = APIRouter(prefix="/api/workspace", tags=["Workspace"])


# FIX #13: Validate project_id to prevent path traversal
def validate_project_id(project_id: str) -> bool:
    """
    Validate project_id format to prevent path traversal attacks.
    Only allows alphanumeric, hyphens, and underscores (1-100 chars).
    """
    if not project_id or not isinstance(project_id, str):
        return False
    return bool(re.match(r'^[a-zA-Z0-9_-]{1,100}$', project_id))


def get_safe_project_path(project_id: str) -> Path:
    """
    Get project path with security validation.
    Raises HTTPException if project_id is invalid.
    """
    if not validate_project_id(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    
    project_path = get_project_path(project_id)
    
    # FIX #12: Use resolve() to prevent symlink attacks
    try:
        resolved = project_path.resolve()
        workspaces_resolved = settings.paths.workspaces_dir.resolve()
        if not str(resolved).startswith(str(workspaces_resolved)):
            raise HTTPException(status_code=403, detail="Access denied")
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid project path")
    
    return project_path


class FileContent(BaseModel):
    path: str
    content: str


class GenerateRequest(BaseModel):
    description: str
    provider: Optional[str] = None
    model: Optional[str] = None
    resume_mode: Optional[str] = "auto"  # "auto", "resume", "fresh"


class ResumeRequest(BaseModel):
    project_id: str
    user_message: str

@router.get("/list")
async def list_workspaces():
    """List all workspaces (for connection test)."""
    workspaces = []
    workspaces_dir = settings.paths.workspaces_dir
    
    if workspaces_dir.exists():
        for p in workspaces_dir.iterdir():
            if p.is_dir() and not p.name.startswith('.'):
                workspaces.append({"id": p.name, "path": str(p)})
    
    return {"workspaces": workspaces}


@router.get("/{project_id}/files")
async def get_workspace_files(project_id: str):
    """Get workspace file tree."""
    project_path = get_safe_project_path(project_id)
    
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    
    def build_tree(path: Path) -> dict:
        if path.is_file():
            return {
                "name": path.name,
                "path": str(path.relative_to(project_path)),
                "type": "file",
            }
        
        children = []
        try:
            for child in sorted(path.iterdir()):
                if child.name.startswith('.') or child.name == 'node_modules':
                    continue
                children.append(build_tree(child))
        except PermissionError:
            pass
        
        return {
            "name": path.name,
            "path": str(path.relative_to(project_path)) if path != project_path else "",
            "type": "folder",
            "children": children,
        }
    
    root_tree = build_tree(project_path)
    return root_tree.get("children", [])


@router.get("/{project_id}/file")
async def get_file_content(project_id: str, path: str):
    """Get file content."""
    project_path = get_safe_project_path(project_id)
    file_path = project_path / path
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    
    # FIX #12: Use resolve() to prevent symlink-based path traversal
    try:
        resolved_file = file_path.resolve()
        resolved_project = project_path.resolve()
        if not str(resolved_file).startswith(str(resolved_project)):
            raise HTTPException(status_code=403, detail="Access denied")
    except (OSError, ValueError):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        content = file_path.read_text(encoding="utf-8")
        return {"path": path, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.put("/{project_id}/file")
async def save_file_content(project_id: str, data: FileContent):
    """Save file content."""
    project_path = get_safe_project_path(project_id)
    file_path = project_path / data.path
    
    # FIX #12: Use resolve() to prevent symlink-based path traversal
    try:
        # Need to check parent for new files, file itself may not exist yet
        resolved_parent = file_path.parent.resolve()
        resolved_project = project_path.resolve()
        if not str(resolved_parent).startswith(str(resolved_project)):
            raise HTTPException(status_code=403, detail="Access denied")
    except (OSError, ValueError):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(data.content, encoding="utf-8")
        return {"saved": True, "path": data.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/generate/backend")
async def generate_backend(request: Request, project_id: str, data: GenerateRequest):
    """
    Start backend generation workflow.
    
    Resume Modes:
    - "auto": Check for saved progress, resume if found, else start fresh
    - "resume": Force resume (fail if no progress)
    - "fresh": Clear progress and start fresh
    """
    from app.workflow import run_workflow
    from app.workflow.engine import resume_from_checkpoint_workflow
    from app.orchestration.state import WorkflowStateManager
    
    log("WORKSPACE", f"Starting generation for {project_id} (mode={data.resume_mode})")
    
    # FIX #13: Validate project_id
    if not validate_project_id(project_id):
        log("WORKSPACE", f"Invalid project_id: {project_id}")
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    
    # Guard: Check if workflow is already running
    is_running = await WorkflowStateManager.is_running(project_id)
    log("WORKSPACE", f"is_running check: {is_running}")
    
    if is_running:
        log("WORKSPACE", f"⚠️ Workflow already running for {project_id}, blocking new request")
        return {
            "success": True,
            "message": "Workflow already in progress",
            "project_id": project_id,
            "already_running": True,
        }
    
    # Get connection manager
    manager = request.app.state.manager
    
    # ════════════════════════════════════════════════════════════════
    # RESUME LOGIC: Auto-detect or force resume based on mode
    # ════════════════════════════════════════════════════════════════
    
    # Handle "fresh" mode - clear any saved progress
    if data.resume_mode == "fresh":
        log("WORKSPACE", f"🗑️ Clearing saved progress for {project_id} (fresh mode)")
        await WorkflowStateManager.clear_progress(project_id)
    
    # Check for saved progress (for "auto" and "resume" modes)
    has_progress = await WorkflowStateManager.has_progress(project_id)
    completed_steps = await WorkflowStateManager.get_completed_steps(project_id) if has_progress else []
    
    # Decide whether to resume
    should_resume = False
    if data.resume_mode == "resume":
        if not has_progress:
            raise HTTPException(status_code=400, detail="No saved progress to resume from")
        should_resume = True
    elif data.resume_mode == "auto" and has_progress:
        should_resume = True
        log("WORKSPACE", f"🔄 Auto-detected {len(completed_steps)} completed steps, will resume")
    
    project_path = get_project_path(project_id)
    
    if should_resume:
        # Resume from checkpoint
        async def _resume_workflow_with_logging():
            try:
                success = await resume_from_checkpoint_workflow(
                    project_id=project_id,
                    description=data.description,
                    workspaces_path=settings.paths.workspaces_dir,
                    manager=manager,
                    provider=data.provider,
                    model=data.model,
                )
                if not success:
                    log("WORKSPACE", f"Resume failed for {project_id}, no action taken")
            except Exception as e:
                log("WORKSPACE", f"ERROR resuming {project_id}: {e}")
        
        asyncio.create_task(_resume_workflow_with_logging())
        
        return {
            "success": True,
            "message": f"Resuming workflow from checkpoint (skipping {len(completed_steps)} steps)",
            "project_id": project_id,
            "mode": "resume",
            "completed_steps": completed_steps,
        }
    else:
        # Start fresh workflow
        project_path.mkdir(parents=True, exist_ok=True)
        
        async def _run_workflow_with_logging():
            try:
                await run_workflow(
                    project_id=project_id,
                    description=data.description,
                    workspaces_path=settings.paths.workspaces_dir,
                    manager=manager,
                    provider=data.provider,
                    model=data.model,
                )
            except Exception as e:
                log("WORKSPACE", f"ERROR {project_id}: {e}")
        
        asyncio.create_task(_run_workflow_with_logging())
        
        return {
            "success": True,
            "message": "Workflow started",
            "project_id": project_id,
            "mode": "fresh",
        }


@router.post("/resume")
async def resume_workflow_endpoint(request: Request, data: ResumeRequest):
    """
    Resume a paused workflow OR start a refine workflow for completed projects.
    
    Delegates to the consolidated engine.resume_workflow which handles:
    - Resuming paused workflows (ArborMind/FAST V2)
    - Starting refine workflows for existing projects (Refine Mode)
    """
    from app.workflow import resume_workflow as engine_resume_workflow
    from app.orchestration.state import WorkflowStateManager
    from app.orchestration.utils import broadcast_to_project
    from app.core.constants import WSMessageType
    
    project_path = get_project_path(data.project_id)
    
    if not project_path.exists():
         raise HTTPException(status_code=404, detail=f"Project {data.project_id} not found")

    try:
        manager = request.app.state.manager
        
        # NOTE: engine_resume_workflow handles checks for paused state, existing project, 
        # and atomic start constraints internally.
        
        # Broadcast intent to resume
        await broadcast_to_project(
            manager, 
            data.project_id, 
            {
                "type": WSMessageType.WORKFLOW_RESUMED,
                "projectId": data.project_id,
                "message": "Initiating workflow resume/refine..."
            }
        )

        asyncio.create_task(
            engine_resume_workflow(
                project_id=data.project_id,
                user_message=data.user_message,
                manager=manager,
                workspaces_dir=settings.paths.workspaces_dir,
            )
        )
        
        return {
            "success": True,
            "message": "Workflow resume/refine initiated",
            "project_id": data.project_id,
            "mode": "auto",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log("WORKSPACE", f"Resume endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ApplyInstructionRequest(BaseModel):
    instruction: str


@router.post("/apply/{project_id}")
async def apply_instruction(project_id: str, data: ApplyInstructionRequest):
    """Apply an instruction to modify project files."""
    # This would use AI to interpret the instruction and modify files
    # For now, return a mock response
    return {
        "success": True,
        "applied": 0,
        "changedFiles": [],
        "rationale": f"Instruction received: {data.instruction}",
    }


@router.post("/{project_id}/force-reset")
async def force_reset_workflow(project_id: str):
    """
    Force reset workflow state for a project.
    Use this if a workflow crashed and left stale state.
    """
    from app.orchestration.state import WorkflowStateManager
    
    log("WORKSPACE", f"Resetting workflow state for {project_id}")
    await WorkflowStateManager.cleanup(project_id)
    
    return {
        "success": True,
        "message": f"Workflow state reset for {project_id}",
        "project_id": project_id,
    }


@router.get("/{project_id}/progress")
async def get_project_progress(project_id: str):
    """
    Get workflow progress for a project.
    
    Returns:
    - completed_steps: List of steps that have been completed
    - current_step: The last completed step
    - is_running: Whether a workflow is currently running
    - is_paused: Whether the workflow is paused for user input
    - is_resumable: Whether the project can be resumed from checkpoint
    """
    from app.orchestration.state import WorkflowStateManager
    
    if not validate_project_id(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    
    project_path = get_project_path(project_id)
    project_exists = project_path.exists()
    
    completed_steps = await WorkflowStateManager.get_completed_steps(project_id)
    current_step = await WorkflowStateManager.get_current_step(project_id)
    is_running = await WorkflowStateManager.is_running(project_id)
    is_paused = await WorkflowStateManager.is_paused(project_id)
    has_progress = await WorkflowStateManager.has_progress(project_id)
    
    return {
        "project_id": project_id,
        "project_exists": project_exists,
        "completed_steps": completed_steps,
        "current_step": current_step,
        "is_running": is_running,
        "is_paused": is_paused,
        "is_resumable": has_progress and not is_running,
        "total_completed": len(completed_steps),
    }


@router.post("/{project_id}/clear-progress")
async def clear_project_progress(project_id: str):
    """
    Clear all saved progress for a project.
    Use this to force a fresh start on next generation.
    """
    from app.orchestration.state import WorkflowStateManager
    
    if not validate_project_id(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    
    log("WORKSPACE", f"Clearing progress for {project_id}")
    await WorkflowStateManager.clear_progress(project_id)
    
    return {
        "success": True,
        "message": f"Progress cleared for {project_id}",
        "project_id": project_id,
    }


@router.post("/{project_id}/force-stop")
async def force_stop_workflow(project_id: str):
    """
    Force stop a stuck workflow.
    
    Use this when a workflow is marked as running but is actually stuck/crashed.
    This manually clears the is_running flag.
    """
    from app.orchestration.state import WorkflowStateManager
    
    if not validate_project_id(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    
    # Check current state
    is_running = await WorkflowStateManager.is_running(project_id)
    
    if not is_running:
        return {
            "success": True,
            "message": f"Workflow for {project_id} is not stuck (already stopped)",
            "project_id": project_id,
            "was_running": False,
        }
    
    log("WORKSPACE", f"🔧 Force stopping stuck workflow for {project_id}")
    await WorkflowStateManager.stop_workflow(project_id)
    
    return {
        "success": True,
        "message": f"Force stopped workflow for {project_id}",
        "project_id": project_id,
        "was_running": True,
    }
