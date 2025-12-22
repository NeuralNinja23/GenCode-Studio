from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from beanie import Document, Indexed
from pydantic import Field

class WorkflowStepRecord(Document):
    project_id: str
    step: str
    status: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        name = "workflow_steps"


class WorkflowSession(Document):
    """
    Persisted state of a workflow session.
    Replaces in-memory _running_workflows, _paused_workflows, etc.
    """
    project_id: Indexed(str, unique=True)
    is_running: bool = False
    is_paused: bool = False
    current_step: Optional[str] = None
    
    # NEW: Track completed steps for resume functionality
    completed_steps: List[str] = Field(default_factory=list)
    
    # Stores the state dump when paused
    paused_state: Optional[Dict[str, Any]] = None
    
    # Context
    original_request: Optional[str] = None
    intent: Optional[Dict[str, Any]] = None
    
    # NEW: Store step context data for resume
    step_context: Dict[str, Any] = Field(default_factory=dict)
    
    # NEW: Cache architecture files from Victoria (avoids re-reading from disk)
    architecture_cache: Dict[str, str] = Field(default_factory=dict)
    
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "workflow_sessions"

