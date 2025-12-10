# app/api/sandbox.py
"""
Docker sandbox control routes.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/sandbox", tags=["Sandbox"])


class ExecRequest(BaseModel):
    project_id: str
    service: str
    command: str
    timeout: Optional[int] = 300


@router.post("/exec")
async def sandbox_exec(data: ExecRequest):
    """Execute command in sandbox."""
    try:
        from app.sandbox import sandbox as manager
        
        result = await manager.exec_in_container(
            project_id=data.project_id,
            service=data.service,
            command=data.command,
            timeout=data.timeout,
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/status")
async def get_sandbox_status(project_id: str):
    """Get sandbox status for a project."""
    try:
        from app.sandbox import sandbox as manager
        
        status = await manager.get_status(project_id)
        
        return status
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


@router.post("/{project_id}/create")
async def create_sandbox(project_id: str):
    """Create/initialize sandbox for a project (idempotent)."""
    try:
        from app.sandbox import sandbox as manager
        from app.core.config import settings
        
        # Get workspace path using proper settings
        project_path = settings.paths.workspaces_dir / project_id
        
        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found at {project_path}")
        
        # Create/reinitialize sandbox
        result = await manager.create_sandbox(project_id, project_path)
        
        return {"success": True, "project_id": project_id, "detail": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/start")
async def start_sandbox(project_id: str, wait_healthy: bool = True):
    """Start sandbox for a project."""
    try:
        from app.sandbox import sandbox as manager
        
        result = await manager.start_sandbox(project_id, wait_healthy=wait_healthy)
        
        return {"success": result.get("success", False), "detail": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/stop")
async def stop_sandbox(project_id: str):
    """Stop sandbox for a project."""
    try:
        from app.sandbox import sandbox as manager
        
        await manager.stop_sandbox(project_id)
        
        return {"stopped": True, "project_id": project_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/preview")
async def get_preview_url(project_id: str):
    """Get preview URL for a project sandbox."""
    try:
        from app.sandbox import sandbox as manager
        
        # Try to start sandbox if not running
        status = await manager.get_status(project_id)
        
        if status.get("status") != "running":
            # Start the sandbox
            await manager.start_sandbox(project_id)
        
        # Get the preview URL (frontend port)
        preview_url = await manager.get_preview_url(project_id)
        
        if preview_url:
            return {
                "preview_url": preview_url,
                "previewUrl": preview_url,  # Alternative key for compatibility
                "url": preview_url,
                "status": "ready",
            }
        else:
            return {
                "preview_url": None,
                "status": "starting",
                "message": "Sandbox is starting, please wait...",
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
