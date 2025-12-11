# app/api/workspace.py
"""
Workspace file operations.
"""
import asyncio
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional

from app.core.config import settings

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
    
    project_path = settings.paths.workspaces_dir / project_id
    
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
    """Start backend generation workflow."""
    from app.workflow import run_workflow
    from app.orchestration.state import WorkflowStateManager
    
    print(f"[GENERATE] Starting generation for {project_id}")
    
    # FIX #13: Validate project_id
    if not validate_project_id(project_id):
        print(f"[GENERATE] Invalid project_id: {project_id}")
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    
    # Guard: Check if workflow is already running
    is_running = await WorkflowStateManager.is_running(project_id)
    print(f"[GENERATE] is_running check: {is_running}")
    
    if is_running:
        print(f"[GENERATE] ⚠️ Workflow already running for {project_id}, blocking new request")
        return {
            "success": True,
            "message": "Workflow already in progress",
            "project_id": project_id,
            "already_running": True,
        }
    
    project_path = settings.paths.workspaces_dir / project_id
    project_path.mkdir(parents=True, exist_ok=True)
    
    # Get connection manager
    manager = request.app.state.manager
    
    # Start workflow in background with exception logging
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
            import traceback
            print(f"[WORKFLOW ERROR] {project_id}: {e}")
            print(traceback.format_exc())
    
    asyncio.create_task(_run_workflow_with_logging())
    
    return {
        "success": True,
        "message": "Workflow started",
        "project_id": project_id,
    }


@router.post("/resume")
async def resume_workflow_endpoint(request: Request, data: ResumeRequest):
    """
    Resume a paused workflow OR start a refine workflow for completed projects.
    
    - If workflow is paused: Resume from saved state
    - If project exists but not paused: Start refine workflow
    """
    from app.orchestration.state import WorkflowStateManager
    from app.workflow import resume_workflow as engine_resume_workflow
    from app.core.constants import WorkflowStep, WSMessageType
    from app.orchestration.utils import broadcast_to_project
    
    project_path = settings.paths.workspaces_dir / data.project_id
    
    # Check if workflow is paused
    if await WorkflowStateManager.is_paused(data.project_id):
        # Resume paused workflow using the engine's resume_workflow
        try:
            manager = request.app.state.manager
            
            # Broadcast resume event
            await broadcast_to_project(
                manager, 
                data.project_id, 
                {
                    "type": WSMessageType.WORKFLOW_RESUMED,
                    "projectId": data.project_id,
                    "message": "Resuming workflow..."
                }
            )
            
            # Use engine's resume_workflow which properly handles paused state
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
                "message": "Workflow resumed",
                "project_id": data.project_id,
                "mode": "resume",
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # Check if project exists - start refine workflow
    elif project_path.exists():
        # Guard: Atomically check and set running state (FIX #5: prevent race condition)
        can_start = await WorkflowStateManager.try_start_workflow(data.project_id)
        if not can_start:
            return {
                "success": True,
                "message": "Workflow already in progress",
                "project_id": data.project_id,
                "already_running": True,
            }
        
        manager = request.app.state.manager
        
        # Import refine handler to start directly at refine step
        from app.workflow.engine import WorkflowEngine
        
        async def run_refine():
            try:
                engine = WorkflowEngine(
                    project_id=data.project_id,
                    manager=manager,
                    project_path=project_path,
                    user_request=data.user_message,
                )
                engine.current_step = WorkflowStep.REFINE
                await engine.run()
            except Exception as e:
                # Engine.run() handles cleanup in finally block
                print(f"[RESUME] Refine workflow error: {e}")
        
        asyncio.create_task(run_refine())
        
        return {
            "success": True,
            "message": "Refine workflow started",
            "project_id": data.project_id,
            "mode": "refine",
        }
    
    else:
        raise HTTPException(status_code=404, detail=f"Project {data.project_id} not found")


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
    
    print(f"[FORCE-RESET] Resetting workflow state for {project_id}")
    await WorkflowStateManager.cleanup(project_id)
    
    return {
        "success": True,
        "message": f"Workflow state reset for {project_id}",
        "project_id": project_id,
    }
