from datetime import datetime
from typing import Optional
from beanie import Document, Indexed
from pydantic import Field

class Project(Document):
    name: Indexed(str)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    workspace_path: str
    provider: str = "gemini"
    model: str = "gemini-pro"
    status: str = "created"  # created, analyzing, building, completed, failed
    
    class Settings:
        name = "projects"
