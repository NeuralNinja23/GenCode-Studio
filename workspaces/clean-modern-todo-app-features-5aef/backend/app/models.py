from beanie import Document, PydanticObjectId, Field
from datetime import datetime, date, timezone
from typing import Optional
from enum import Enum
from pydantic import BaseModel, ConfigDict

class TaskStatus(str, Enum):
    ACTIVE = "Active"
    COMPLETED = "Completed"

class TaskPriority(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class Task(Document):
    title: str
    content: str
    status: TaskStatus = Field(default=TaskStatus.ACTIVE)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    dueDate: Optional[date] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "tasks"

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

# Export all model classes for auto-discovery by database.py
__all__ = ["Task", "TaskStatus", "TaskPriority"]
