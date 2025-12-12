# app/orchestration/state.py
"""
Workflow state management.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

from app.core.types import ChatMessage

from app.models.workflow import WorkflowSession

# Connection managers (kept in-memory as they are objects)
_active_managers: Dict[str, Any] = {}
_workflow_lock = asyncio.Lock()


class WorkflowStateManager:
    """Manages workflow state using persistent storage (MongoDB)."""
    
    @staticmethod
    async def get_session(project_id: str) -> WorkflowSession:
        """Get or create session."""
        session = await WorkflowSession.find_one(WorkflowSession.project_id == project_id)
        if not session:
            session = WorkflowSession(project_id=project_id)
            await session.insert()
        return session

    @staticmethod
    async def is_running(project_id: str) -> bool:
        """Check if a workflow is running for a project."""
        session = await WorkflowSession.find_one(WorkflowSession.project_id == project_id)
        return session.is_running if session else False
    
    @staticmethod
    async def set_running(project_id: str, running: bool) -> None:
        """Set the running state for a project."""
        session = await WorkflowStateManager.get_session(project_id)
        session.is_running = running
        session.last_updated = datetime.now(timezone.utc)
        await session.save()
    
    @staticmethod
    async def try_start_workflow(project_id: str) -> bool:
        """
        Atomically check if workflow can start and mark it as running.
        FIX STATE-001: Uses DB atomicity (mostly) and lock for safety.
        """
        async with _workflow_lock:
            session = await WorkflowStateManager.get_session(project_id)
            if session.is_running:
                return False
            
            session.is_running = True
            session.last_updated = datetime.now(timezone.utc)
            await session.save()
            return True
    
    @staticmethod
    async def stop_workflow(project_id: str) -> None:
        """Atomically mark workflow as stopped."""
        async with _workflow_lock:
            session = await WorkflowStateManager.get_session(project_id)
            session.is_running = False
            session.last_updated = datetime.now(timezone.utc)
            await session.save()
    
    @staticmethod
    async def is_paused(project_id: str) -> bool:
        """Check if a workflow is paused for a project."""
        session = await WorkflowSession.find_one(WorkflowSession.project_id == project_id)
        return session.is_paused if session else False
    
    @staticmethod
    async def get_paused_state(project_id: str) -> Optional[Dict[str, Any]]:
        """Get the paused workflow state."""
        session = await WorkflowSession.find_one(WorkflowSession.project_id == project_id)
        return session.paused_state if (session and session.is_paused) else None
    
    @staticmethod
    async def pause_workflow(
        project_id: str,
        step: str,
        turn: int,
        chat_history: List[ChatMessage],
        user_request: str,
        project_path: Path,
        provider: str,
        model: str,
    ) -> None:
        """Pause a workflow for user input. State is persisted to DB."""
        state = {
            "step": step,
            "turn": turn,
            "chat_history": [c.model_dump() if hasattr(c, 'model_dump') else c for c in chat_history],
            "user_request": user_request,
            "project_path": str(project_path),
            "provider": provider,
            "model": model,
            "paused_at": datetime.now(timezone.utc).isoformat(),
        }
        
        session = await WorkflowStateManager.get_session(project_id)
        session.is_paused = True
        session.paused_state = state
        session.last_updated = datetime.now(timezone.utc)
        await session.save()
    
    @staticmethod
    async def resume_workflow(project_id: str) -> Optional[Dict[str, Any]]:
        """Resume a paused workflow, returning the saved state and cleaning up."""
        session = await WorkflowSession.find_one(WorkflowSession.project_id == project_id)
        if not session or not session.is_paused:
            return None
            
        state = session.paused_state
        session.is_paused = False
        session.paused_state = None
        session.last_updated = datetime.now(timezone.utc)
        await session.save()
        
        return state
    
    @staticmethod
    async def set_intent(project_id: str, intent: Dict[str, Any]) -> None:
        """Store analyzed intent for a project."""
        session = await WorkflowStateManager.get_session(project_id)
        session.intent = intent
        await session.save()
    
    @staticmethod
    async def get_intent(project_id: str) -> Dict[str, Any]:
        """Get stored intent for a project."""
        session = await WorkflowSession.find_one(WorkflowSession.project_id == project_id)
        return session.intent if (session and session.intent) else {}
    
    @staticmethod
    async def set_original_request(project_id: str, request: str) -> None:
        """Store original user request."""
        session = await WorkflowStateManager.get_session(project_id)
        session.original_request = request
        await session.save()
    
    @staticmethod
    async def get_original_request(project_id: str) -> str:
        """Get original user request."""
        session = await WorkflowSession.find_one(WorkflowSession.project_id == project_id)
        return session.original_request if (session and session.original_request) else ""
    
    @staticmethod
    def set_manager(project_id: str, manager: Any) -> None:
        """Store connection manager (Memory only)."""
        _active_managers[project_id] = manager
    
    @staticmethod
    def get_manager(project_id: str) -> Optional[Any]:
        """Get connection manager."""
        return _active_managers.get(project_id)
    
    @staticmethod
    async def cleanup(project_id: str) -> None:
        """Clean up state (stop running, unpause)."""
        session = await WorkflowSession.find_one(WorkflowSession.project_id == project_id)
        if session:
            session.is_running = False
            session.is_paused = False
            session.paused_state = None
            await session.save()
            
        _active_managers.pop(project_id, None)

    @staticmethod
    async def acquire_lock():
        return await _workflow_lock.acquire()

    @staticmethod
    def release_lock():
        _workflow_lock.release()

# Backwards compatibility globals are REMOVED to force usage of async methods.
# Any usage of these globals will now fail, prompting fixes.
WORKFLOW_LOCK = _workflow_lock
CURRENT_MANAGERS = _active_managers
