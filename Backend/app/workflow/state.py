# app/workflow/state.py
"""
Workflow state management.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, field

from app.core.types import ChatMessage, WorkflowStatus
from app.core.constants import WorkflowStep


# Global state storage
_paused_workflows: Dict[str, Dict[str, Any]] = {}
_project_intents: Dict[str, Dict[str, Any]] = {}
_original_requests: Dict[str, str] = {}
_running_workflows: Dict[str, bool] = {}
_active_managers: Dict[str, Any] = {}  # project_id -> ConnectionManager

# Lock for thread safety
_workflow_lock = asyncio.Lock()


class WorkflowStateManager:
    """Manages workflow state across the application."""
    
    @staticmethod
    def is_running(project_id: str) -> bool:
        """Check if a workflow is running for a project (non-atomic, use with caution)."""
        return _running_workflows.get(project_id, False)
    
    @staticmethod
    def set_running(project_id: str, running: bool) -> None:
        """Set the running state for a project (non-atomic, use with caution)."""
        _running_workflows[project_id] = running
    
    @staticmethod
    async def try_start_workflow(project_id: str) -> bool:
        """
        Atomically check if workflow can start and mark it as running.
        
        This is the SAFE way to start a workflow - prevents race conditions
        where two requests both pass the is_running check before either sets running=True.
        
        Returns:
            True if workflow was started (caller should proceed)
            False if workflow was already running (caller should abort)
        """
        async with _workflow_lock:
            if _running_workflows.get(project_id, False):
                return False  # Already running
            _running_workflows[project_id] = True
            return True  # Successfully marked as running
    
    @staticmethod
    async def stop_workflow(project_id: str) -> None:
        """Atomically mark workflow as stopped."""
        async with _workflow_lock:
            _running_workflows[project_id] = False
    
    @staticmethod
    def is_paused(project_id: str) -> bool:
        """Check if a workflow is paused for a project."""
        return project_id in _paused_workflows
    
    @staticmethod
    def get_paused_state(project_id: str) -> Optional[Dict[str, Any]]:
        """Get the paused workflow state (checks file if not in memory)."""
        # First check in-memory
        if project_id in _paused_workflows:
            return _paused_workflows[project_id]
        
        # FIX #5: Check filesystem for persisted state (recovery after restart)
        try:
            from app.core.config import settings
            paused_file = settings.paths.workspaces_dir / project_id / ".gencode_paused.json"
            if paused_file.exists():
                import json
                state = json.loads(paused_file.read_text(encoding="utf-8"))
                # Restore to memory
                _paused_workflows[project_id] = state
                return state
        except Exception as e:
            print(f"[STATE] Could not load paused state from file: {e}")
        
        return None
    
    @staticmethod
    def pause_workflow(
        project_id: str,
        step: str,
        turn: int,
        chat_history: List[ChatMessage],
        user_request: str,
        project_path: Path,
        provider: str,
        model: str,
    ) -> None:
        """Pause a workflow for user input. State is persisted to disk."""
        state = {
            "step": step,
            "turn": turn,
            "chat_history": chat_history,
            "user_request": user_request,
            "project_path": str(project_path),
            "provider": provider,
            "model": model,
            "paused_at": datetime.now(timezone.utc).isoformat(),
        }
        _paused_workflows[project_id] = state
        
        # FIX #5: Persist to filesystem for recovery after restart
        try:
            import json
            paused_file = project_path / ".gencode_paused.json"
            paused_file.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
        except Exception as e:
            print(f"[STATE] Could not persist paused state: {e}")
    
    @staticmethod
    def resume_workflow(project_id: str) -> Optional[Dict[str, Any]]:
        """Resume a paused workflow, returning the saved state and cleaning up."""
        state = _paused_workflows.pop(project_id, None)
        
        # FIX #5: Clean up persisted file
        if state:
            try:
                from pathlib import Path
                paused_file = Path(state.get("project_path", "")) / ".gencode_paused.json"
                if paused_file.exists():
                    paused_file.unlink()
            except Exception as e:
                print(f"[STATE] Could not remove paused state file: {e}")
        
        return state
    
    @staticmethod
    def set_intent(project_id: str, intent: Dict[str, Any]) -> None:
        """Store analyzed intent for a project."""
        _project_intents[project_id] = intent
    
    @staticmethod
    def get_intent(project_id: str) -> Dict[str, Any]:
        """Get stored intent for a project."""
        return _project_intents.get(project_id, {})
    
    @staticmethod
    def set_original_request(project_id: str, request: str) -> None:
        """Store original user request."""
        _original_requests[project_id] = request
    
    @staticmethod
    def get_original_request(project_id: str) -> str:
        """Get original user request."""
        return _original_requests.get(project_id, "")
    
    @staticmethod
    def set_manager(project_id: str, manager: Any) -> None:
        """Store connection manager for a project."""
        _active_managers[project_id] = manager
    
    @staticmethod
    def get_manager(project_id: str) -> Optional[Any]:
        """Get connection manager for a project."""
        return _active_managers.get(project_id)
    
    @staticmethod
    def cleanup(project_id: str) -> None:
        """Clean up all state for a project."""
        _paused_workflows.pop(project_id, None)
        _project_intents.pop(project_id, None)
        _original_requests.pop(project_id, None)
        _running_workflows.pop(project_id, None)
        _active_managers.pop(project_id, None)
    
    @staticmethod
    async def acquire_lock():
        """Acquire the workflow lock."""
        return await _workflow_lock.acquire()
    
    @staticmethod
    def release_lock():
        """Release the workflow lock."""
        _workflow_lock.release()


# Backwards compatibility exports
paused_workflows = _paused_workflows
project_intents = _project_intents
original_requests = _original_requests
CURRENT_MANAGERS = _active_managers
running_workflows = _running_workflows
WORKFLOW_LOCK = _workflow_lock
