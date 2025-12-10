# app/workflow/checkpoint.py
"""
Checkpoint & Recovery System

Saves workflow progress at each step so crashes don't lose 15+ minutes of work.
Enables resuming from the last successful step.

Usage:
    # Save checkpoint after each step
    await checkpoint.save(project_id, step_name, context, output)
    
    # On crash/restart, resume from last checkpoint
    state = await checkpoint.load(project_id)
    if state:
        workflow.resume_from(state["step"], state["context"])
"""
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from app.core.logging import log


@dataclass
class CheckpointData:
    """Data stored in a checkpoint."""
    project_id: str
    step_name: str
    turn: int
    timestamp: str
    status: str  # "completed", "failed", "in_progress"
    output: Dict[str, Any]
    context: Dict[str, Any]
    duration_seconds: float = 0.0
    error: Optional[str] = None


class CheckpointManager:
    """
    Manages workflow checkpoints for crash recovery.
    
    Checkpoints are stored as JSON files in the workspace directory.
    Each step creates a checkpoint on completion.
    """
    
    CHECKPOINT_DIR = ".workflow_checkpoints"
    CURRENT_CHECKPOINT_FILE = "current_state.json"
    HISTORY_FILE = "checkpoint_history.json"
    
    def __init__(self, workspaces_dir: Path):
        self.workspaces_dir = workspaces_dir
    
    def _get_checkpoint_dir(self, project_id: str) -> Path:
        """Get the checkpoint directory for a project."""
        return self.workspaces_dir / project_id / self.CHECKPOINT_DIR
    
    def _ensure_dir(self, project_id: str) -> Path:
        """Ensure checkpoint directory exists."""
        checkpoint_dir = self._get_checkpoint_dir(project_id)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        return checkpoint_dir
    
    async def save(
        self,
        project_id: str,
        step_name: str,
        turn: int,
        output: Dict[str, Any],
        context: Dict[str, Any],
        status: str = "completed",
        duration_seconds: float = 0.0,
        error: Optional[str] = None,
    ) -> bool:
        """
        Save a checkpoint after a step completes.
        
        Args:
            project_id: Project identifier
            step_name: Name of the completed step
            turn: Current workflow turn
            output: Step output data
            context: Workflow context (for resuming)
            status: Step status (completed, failed, in_progress)
            duration_seconds: How long the step took
            error: Error message if failed
            
        Returns:
            True if saved successfully
        """
        try:
            checkpoint_dir = self._ensure_dir(project_id)
            
            # Create checkpoint data
            checkpoint = CheckpointData(
                project_id=project_id,
                step_name=step_name,
                turn=turn,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status=status,
                output=self._sanitize_output(output),
                context=self._sanitize_context(context),
                duration_seconds=duration_seconds,
                error=error,
            )
            
            # Save current state
            current_file = checkpoint_dir / self.CURRENT_CHECKPOINT_FILE
            current_file.write_text(
                json.dumps(asdict(checkpoint), indent=2, default=str),
                encoding="utf-8"
            )
            
            # Append to history
            await self._append_to_history(checkpoint_dir, checkpoint)
            
            log("CHECKPOINT", f"📸 Saved checkpoint: {step_name} (turn {turn})")
            return True
            
        except Exception as e:
            log("CHECKPOINT", f"⚠️ Failed to save checkpoint: {e}")
            return False
    
    async def load(self, project_id: str) -> Optional[CheckpointData]:
        """
        Load the most recent checkpoint for a project.
        
        Returns:
            CheckpointData if found, None otherwise
        """
        try:
            checkpoint_dir = self._get_checkpoint_dir(project_id)
            current_file = checkpoint_dir / self.CURRENT_CHECKPOINT_FILE
            
            if not current_file.exists():
                return None
            
            data = json.loads(current_file.read_text(encoding="utf-8"))
            checkpoint = CheckpointData(**data)
            
            log("CHECKPOINT", f"📂 Loaded checkpoint: {checkpoint.step_name} (turn {checkpoint.turn})")
            return checkpoint
            
        except Exception as e:
            log("CHECKPOINT", f"⚠️ Failed to load checkpoint: {e}")
            return None
    
    async def get_history(self, project_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get checkpoint history for a project."""
        try:
            checkpoint_dir = self._get_checkpoint_dir(project_id)
            history_file = checkpoint_dir / self.HISTORY_FILE
            
            if not history_file.exists():
                return []
            
            history = json.loads(history_file.read_text(encoding="utf-8"))
            return history[-limit:] if limit else history
            
        except Exception as e:
            log("CHECKPOINT", f"⚠️ Failed to load history: {e}")
            return []
    
    async def clear(self, project_id: str) -> bool:
        """Clear all checkpoints for a project (on successful completion)."""
        try:
            checkpoint_dir = self._get_checkpoint_dir(project_id)
            
            if checkpoint_dir.exists():
                # Archive instead of delete
                archive_dir = checkpoint_dir.parent / ".workflow_checkpoints_archive"
                archive_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_file = archive_dir / f"checkpoint_{timestamp}.json"
                
                # Save final state to archive
                current_file = checkpoint_dir / self.CURRENT_CHECKPOINT_FILE
                if current_file.exists():
                    archive_file.write_text(current_file.read_text(encoding="utf-8"))
                
                # Clear current checkpoints
                for f in checkpoint_dir.glob("*.json"):
                    f.unlink()
            
            log("CHECKPOINT", f"🧹 Cleared checkpoints for {project_id}")
            return True
            
        except Exception as e:
            log("CHECKPOINT", f"⚠️ Failed to clear checkpoints: {e}")
            return False
    
    def can_resume(self, project_id: str) -> bool:
        """Check if a project has a checkpoint to resume from."""
        checkpoint_dir = self._get_checkpoint_dir(project_id)
        current_file = checkpoint_dir / self.CURRENT_CHECKPOINT_FILE
        return current_file.exists()
    
    def _sanitize_output(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize output for JSON serialization."""
        sanitized = {}
        for key, value in output.items():
            if key == "files":
                # Only save file metadata, not full content (too large)
                sanitized["files"] = [
                    {"path": f.get("path", ""), "size": len(f.get("content", ""))}
                    for f in value if isinstance(f, dict)
                ]
            elif isinstance(value, (str, int, float, bool, list, dict, type(None))):
                sanitized[key] = value
        return sanitized
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize context for JSON serialization."""
        # Only keep essential context fields
        essential_keys = [
            "user_request", "archetype", "primary_entity", 
            "provider", "model", "current_turn", "max_turns"
        ]
        return {k: context.get(k) for k in essential_keys if k in context}
    
    async def _append_to_history(self, checkpoint_dir: Path, checkpoint: CheckpointData):
        """Append checkpoint to history file."""
        history_file = checkpoint_dir / self.HISTORY_FILE
        
        # Load existing history
        history = []
        if history_file.exists():
            try:
                history = json.loads(history_file.read_text(encoding="utf-8"))
            except Exception:
                history = []
        
        # Append new entry (limited info for history)
        history.append({
            "step": checkpoint.step_name,
            "turn": checkpoint.turn,
            "status": checkpoint.status,
            "timestamp": checkpoint.timestamp,
            "duration": checkpoint.duration_seconds,
        })
        
        # Keep last 100 entries
        history = history[-100:]
        
        history_file.write_text(
            json.dumps(history, indent=2),
            encoding="utf-8"
        )


# Singleton instance
_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """Get the global checkpoint manager instance."""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        from app.core.config import settings
        _checkpoint_manager = CheckpointManager(settings.workspaces_dir)
    return _checkpoint_manager


async def save_checkpoint(
    project_id: str,
    step_name: str,
    turn: int,
    output: Dict[str, Any],
    context: Dict[str, Any],
    **kwargs
) -> bool:
    """Convenience function for saving checkpoints."""
    manager = get_checkpoint_manager()
    return await manager.save(project_id, step_name, turn, output, context, **kwargs)


async def load_checkpoint(project_id: str) -> Optional[CheckpointData]:
    """Convenience function for loading checkpoints."""
    manager = get_checkpoint_manager()
    return await manager.load(project_id)


def can_resume(project_id: str) -> bool:
    """Check if workflow can resume from checkpoint."""
    manager = get_checkpoint_manager()
    return manager.can_resume(project_id)
