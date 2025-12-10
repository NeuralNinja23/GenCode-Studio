# app/handlers/base.py
"""
Shared utilities for workflow handlers.
"""
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import importlib

from app.core.logging import log


def _get_broadcast_to_project():
    """Lazy import to avoid circular dependency with app.workflow package."""
    # Import the module directly without triggering app.workflow.__init__
    orchestration_utils = importlib.import_module('app.orchestration.utils')
    return orchestration_utils.broadcast_to_project


# Utility functions for step handlers

async def broadcast_status(
    manager: Any,
    project_id: str,
    step: str,
    status: str,
    current_turn: int,
    max_turns: int,
) -> None:
    """Broadcast workflow status update."""
    broadcast_to_project = _get_broadcast_to_project()
    await broadcast_to_project(
        manager,
        project_id,
        {
            "type": "WORKFLOW_UPDATE",
            "projectId": project_id,
            "step": step,
            "status": status,
            "currentTurn": current_turn,
            "maxTurns": max_turns,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )



async def broadcast_agent_log(
    manager: Any,
    project_id: str,
    scope: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """Broadcast an agent log/thinking message."""
    broadcast_to_project = _get_broadcast_to_project()
    
    # Also log to backend stdout
    log(scope, message, project_id=project_id)
    
    payload = {
        "type": "AGENT_LOG",
        "projectId": project_id,
        "scope": scope,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if data:
        payload["data"] = data

    await broadcast_to_project(
        manager,
        project_id,
        payload,
    )

