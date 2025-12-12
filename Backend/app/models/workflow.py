from datetime import datetime, timezone
from typing import Any, Dict, Optional
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
    
    # Stores the state dump when paused
    paused_state: Optional[Dict[str, Any]] = None
    
    # Context
    original_request: Optional[str] = None
    intent: Optional[Dict[str, Any]] = None
    
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "workflow_sessions"
