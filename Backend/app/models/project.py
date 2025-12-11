from datetime import datetime, timezone
from typing import Optional, Literal
from beanie import Document, Indexed
from pydantic import Field


# FIX VALID-001: Define allowed status values as a type
ProjectStatus = Literal["created", "analyzing", "building", "completed", "failed"]


class Project(Document):
    name: Indexed(str)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    workspace_path: str
    provider: str = "gemini"
    model: str = "gemini-pro"
    status: ProjectStatus = "created"  # Now validated by Pydantic
    
    class Settings:
        name = "projects"
