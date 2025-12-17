from fastapi import APIRouter, HTTPException, status, Response
from beanie import PydanticObjectId
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import List, Optional

from app.models import Task

router = APIRouter()


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "active"
    column_id: Optional[PydanticObjectId] = None
    board_id: Optional[PydanticObjectId] = None
    assignee_id: Optional[PydanticObjectId] = None
    priority: str = "medium"
    due_date: Optional[datetime] = None
    labels: List[str] = Field(default_factory=list)
    position: int = 0
    subtasks: List[dict] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    column_id: Optional[PydanticObjectId] = None
    board_id: Optional[PydanticObjectId] = None
    assignee_id: Optional[PydanticObjectId] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    labels: Optional[List[str]] = None
    position: Optional[int] = None
    subtasks: Optional[List[dict]] = None


@router.get("/", response_model=List[Task], status_code=status.HTTP_200_OK)
async def get_all_tasks(status: Optional[str] = None):
    query = {}
    if status:
        if status not in ["active", "completed"]:
            return [] # Return empty list for invalid status as per contract
        query["status"] = status
    
    tasks = await Task.find(query).to_list()
    return tasks


@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(task_data: TaskCreate):
    now = datetime.now(timezone.utc)
    task = Task(
        **task_data.model_dump(),
        created_at=now,
        updated_at=now
    )
    await task.insert()
    return task


@router.get("/{id}", response_model=Task, status_code=status.HTTP_200_OK)
async def get_task_by_id(id: PydanticObjectId):
    task = await Task.get(id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.put("/{id}", response_model=Task, status_code=status.HTTP_200_OK)
async def update_task(id: PydanticObjectId, task_data: TaskUpdate):
    task = await Task.get(id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    update_data = task_data.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(task, key, value)
        task.updated_at = datetime.now(timezone.utc)
        await task.save()
    
    return task


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(id: PydanticObjectId):
    task = await Task.get(id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    await task.delete()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
