"""
Example FastAPI router for the Task model.

This file is intentionally small and focused so that GenCode Studio agents
can copy patterns for list/create/update/delete endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from ..models import Task, TaskIn, TaskUpdate, TaskStatus

router = APIRouter(prefix="/tasks", tags=["tasks"])


class PaginatedTasks(BaseModel):
    items: List[Task]
    total: int
    skip: int
    limit: int


@router.get("/", response_model=PaginatedTasks)
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    search: Optional[str] = Query(None, min_length=1, max_length=200),
) -> PaginatedTasks:
    query = {}
    if status_filter is not None:
        query["status"] = status_filter
    if search:
        query["title"] = {"$regex": search, "$options": "i"}

    cursor = Task.find(query).skip(skip).limit(limit)
    items = await cursor.to_list()
    total = await Task.find(query).count()

    return PaginatedTasks(items=items, total=total, skip=skip, limit=limit)


@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskIn) -> Task:
    task = Task(**payload.dict())
    await task.insert()
    return task


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str) -> Task:
    task = await Task.get(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=Task)
async def update_task(task_id: str, payload: TaskUpdate) -> Task:
    task = await Task.get(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    await task.save()
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str) -> None:
    task = await Task.get(task_id)
    if not task:
        # Deleting a non-existent resource is treated as success in many APIs
        return
    await task.delete()
