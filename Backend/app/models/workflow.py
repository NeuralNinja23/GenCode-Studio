from datetime import datetime
from typing import List, Any, Dict, Optional
from beanie import Document
from pydantic import Field

class WorkflowStepRecord(Document):
    project_id: str
    step: str
    status: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        name = "workflow_steps"
