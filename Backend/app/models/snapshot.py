from datetime import datetime, timezone
from typing import Any, Dict
from beanie import Document
from pydantic import Field

class Snapshot(Document):
    project_id: str
    step: str
    agent: str
    quality_score: int
    approved: bool
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    files_snapshot: Dict[str, str] = Field(default_factory=dict)
    
    class Settings:
        name = "snapshots"
