from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from beanie import Document
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class Task(Document):
    """
    Example Beanie document used as a reference by GenCode Studio agents.
    """

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2_000)

    status: TaskStatus = Field(default=TaskStatus.OPEN)
    tags: List[str] = Field(default_factory=list)

    owner_id: Optional[str] = None
    assignee_id: Optional[str] = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "tasks"


class TaskIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2_000)
    tags: List[str] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2_000)
    status: Optional[TaskStatus] = None
    tags: Optional[List[str]] = None
    assignee_id: Optional[str] = None
