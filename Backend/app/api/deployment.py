# app/api/deployment.py
"""
Deployment routes.
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime, timezone
import io

from app.models.deployment import Deployment

router = APIRouter(prefix="/api/deployment", tags=["Deployment"])


class DeploymentInitRequest(BaseModel):
    projectId: str
    projectName: str
    customDomain: Optional[str] = None
    environmentVars: Optional[Dict[str, str]] = None


class DeploymentRequest(BaseModel):
    projectId: str
    customDomain: Optional[str] = None
    environmentVars: Optional[Dict[str, str]] = None


class EnvVarsRequest(BaseModel):
    environmentVars: Dict[str, str]


class DomainRequest(BaseModel):
    customDomain: str


@router.post("/initialize")
async def initialize_deployment(data: DeploymentInitRequest):
    """Initialize a new deployment."""
    # FIX STATE-002: Persist to DB instead of memory
    existing = await Deployment.find_one(Deployment.project_id == data.projectId)
    if existing:
        existing.status = "initialized"
        existing.environment_vars = data.environmentVars or {}
        existing.custom_domain = data.customDomain
        existing.last_updated_at = datetime.now(timezone.utc)
        await existing.save()
    else:
        deployment = Deployment(
            project_id=data.projectId,
            project_name=data.projectName,
            status="initialized",
            environment_vars=data.environmentVars or {},
            custom_domain=data.customDomain
        )
        await deployment.insert()
        
    return {
        "success": True,
        "project_id": data.projectId,
        "status": "initialized",
    }


@router.post("/{project_id}")
async def start_deployment(project_id: str, data: DeploymentRequest):
    """Start one-click deployment."""
    deployment = await Deployment.find_one(Deployment.project_id == project_id)
    if not deployment:
        # Auto-create if not exists (lazy init)
        deployment = Deployment(
            project_id=project_id,
            project_name=project_id,  # Default name
            status="deploying"
        )
        await deployment.insert()
    else:
        deployment.status = "deploying"
        if data.environmentVars:
            deployment.environment_vars = data.environmentVars
        await deployment.save()
    
    # In production, trigger actual deployment here
    
    return {
        "success": True,
        "status": "deploying",
        "project_id": project_id,
        "message": "Deployment started",
    }


@router.get("/status/{project_id}")
async def get_deployment_status(project_id: str):
    """Get deployment status."""
    deployment = await Deployment.find_one(Deployment.project_id == project_id)
    if not deployment:
        return {
            "project_id": project_id,
            "status": "not_deployed",
            "version": "1.0.0",
        }
        
    return {
        "project_id": project_id,
        "status": deployment.status,
        "version": deployment.version,
        "url": deployment.url,
        "customDomain": deployment.custom_domain,
        "containerHealth": deployment.container_health,
        "deployedAt": deployment.deployed_at.isoformat() if deployment.deployed_at else None,
        "port": deployment.port,
    }


@router.get("/history/{project_id}")
async def get_deployment_history(project_id: str, limit: int = 10):
    """Get deployment history."""
    # In V2: implement actual history table. for now return mock based on current state.
    deployment = await Deployment.find_one(Deployment.project_id == project_id)
    history = []
    if deployment and deployment.deployed_at:
        history.append({
            "version": deployment.version,
            "status": "success",
            "deployed_at": deployment.deployed_at.isoformat(),
        })
        
    return {
        "project_id": project_id,
        "history": history,
    }


@router.post("/rollback/{project_id}")
async def rollback_deployment(project_id: str):
    """Rollback to previous version."""
    deployment = await Deployment.find_one(Deployment.project_id == project_id)
    if deployment:
        deployment.status = "rolling_back"
        await deployment.save()
        
    return {
        "success": True,
        "project_id": project_id,
        "message": "Rollback initiated",
    }


@router.post("/config/env/{project_id}")
async def update_env_vars(project_id: str, data: EnvVarsRequest):
    """Update environment variables."""
    deployment = await Deployment.find_one(Deployment.project_id == project_id)
    if not deployment:
         deployment = Deployment(project_id=project_id, project_name=project_id)
         await deployment.insert()
         
    deployment.environment_vars = data.environmentVars
    await deployment.save()
    
    return {
        "success": True,
        "project_id": project_id,
    }


@router.get("/config/env/{project_id}")
async def get_env_vars(project_id: str):
    """Get environment variables."""
    deployment = await Deployment.find_one(Deployment.project_id == project_id)
    return {
        "project_id": project_id,
        "environmentVars": deployment.environment_vars if deployment else {},
    }


@router.post("/config/domain/{project_id}")
async def setup_custom_domain(project_id: str, data: DomainRequest):
    """Setup custom domain."""
    deployment = await Deployment.find_one(Deployment.project_id == project_id)
    if not deployment:
         deployment = Deployment(project_id=project_id, project_name=project_id)
         await deployment.insert()
         
    deployment.custom_domain = data.customDomain
    await deployment.save()
    
    return {
        "success": True,
        "project_id": project_id,
        "customDomain": data.customDomain,
    }


@router.get("/logs/{project_id}")
async def get_deployment_logs(project_id: str):
    """Get deployment logs."""
    # In future: fetch from DB or container logs
    return {
        "project_id": project_id,
        "logs": [
            {"timestamp": datetime.now(timezone.utc).isoformat(), "message": "Deployment logs not yet integrated with DB persistence."},
        ],
    }


@router.get("/logs/{project_id}/download")
async def download_logs(project_id: str):
    """Download deployment logs as file."""
    log_content = f"Deployment logs for {project_id}\n\nNo logs available yet."
    buffer = io.BytesIO(log_content.encode("utf-8"))
    return StreamingResponse(
        buffer,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={project_id}_logs.txt"},
    )


@router.post("/restart/{project_id}")
async def restart_deployment(project_id: str):
    """Restart deployment."""
    # Logic to restart container would go here
    return {
        "success": True,
        "project_id": project_id,
        "message": "Deployment restart initiated",
    }


@router.get("/metrics/{project_id}")
async def get_deployment_metrics(project_id: str):
    """Get deployment metrics."""
    return {
        "project_id": project_id,
        "cpu": "0%",
        "memory": "0 MB",
        "restartCount": 0,
    }


@router.get("/health/{project_id}")
async def get_container_health(project_id: str):
    """Get container health status."""
    deployment = await Deployment.find_one(Deployment.project_id == project_id)
    return {
        "project_id": project_id,
        "status": deployment.container_health if deployment else "unknown",
        "healthy": deployment.container_health == "healthy" if deployment else False,
    }
