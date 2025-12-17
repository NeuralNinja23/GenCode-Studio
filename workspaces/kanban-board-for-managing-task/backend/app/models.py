from beanie import Document, PydanticObjectId
from pydantic import Field
from datetime import datetime, timezone
from typing import List, Optional


class Task(Document):
    title: str
    description: Optional[str] = None
    status: str = Field(default="active") # 'active' or 'completed'
    column_id: Optional[PydanticObjectId] = None
    board_id: Optional[PydanticObjectId] = None
    assignee_id: Optional[PydanticObjectId] = None
    priority: str = Field(default="medium") # low, medium, high, urgent
    due_date: Optional[datetime] = None
    labels: List[str] = Field(default_factory=list)
    position: int = 0  # For ordering within column
    subtasks: List[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "tasks"


__all__ = ["Task"]
