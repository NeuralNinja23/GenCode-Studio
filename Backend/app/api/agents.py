# app/api/agents.py
"""
Agent status routes.
"""
from fastapi import APIRouter

from app.core.constants import AgentName

router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.get("/status")
async def get_agents_status():
    """Get status of all agents."""
    return {
        "agents": [
            {
                "name": AgentName.MARCUS,
                "role": "Lead Architect & Supervisor",
                "status": "available",
            },
            {
                "name": AgentName.VICTORIA,
                "role": "Software Architect", 
                "status": "available",
            },
            {
                "name": AgentName.DEREK,
                "role": "Full-Stack Developer",
                "status": "available",
            },
            {
                "name": AgentName.LUNA,
                "role": "QA Engineer",
                "status": "available",
            },
        ]
    }


@router.get("/active")
async def get_active_workflows():
    """Get list of active workflows."""
    from app.orchestration.state import _running_workflows
    
    return {
        "active": [
            {"project_id": pid, "running": running}
            for pid, running in _running_workflows.items()
            if running
        ]
    }
