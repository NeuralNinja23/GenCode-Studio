from fastapi import APIRouter, HTTPException, Query, status
from app.models import Task, TaskStatus, TaskPriority
from beanie import PydanticObjectId
from typing import List, Optional
from datetime import datetime, date, timezone
from pydantic import BaseModel, Field, ConfigDict

router = APIRouter()

# Pydantic models for API input/output
class TaskCreate(BaseModel):
    title: str
    content: str
    status: TaskStatus = TaskStatus.ACTIVE
    priority: TaskPriority = TaskPriority.MEDIUM
    dueDate: Optional[date] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    dueDate: Optional[date] = None

class TaskOut(BaseModel):
    id: PydanticObjectId = Field(..., alias="_id") # Alias _id to id for frontend contract
    title: str
    content: str
    status: TaskStatus
    priority: TaskPriority
    dueDate: Optional[date] = None
    created_at: datetime

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

# Helper for error responses
def error_response(code: str, message: str, status_code: int):
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message}}
    )

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_task(task_data: TaskCreate):
    """Creates a new task."""
    new_task = Task(**task_data.model_dump())
    await new_task.insert()
    return {"data": TaskOut.model_validate(new_task)}

@router.get("/", response_model=dict)
async def get_all_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    """Retrieves a list of all tasks, with optional filtering and pagination."""
    query = {}
    if status_filter:
        query["status"] = status_filter

    total_count = await Task.find(query).count()
    
    tasks = await Task.find(query).skip((page - 1) * limit).limit(limit).to_list()
    
    return {
        "data": [TaskOut.model_validate(task) for task in tasks],
        "total": total_count,
        "page": page,
        "limit": limit
    }

@router.get("/{task_id}", response_model=dict)
async def get_task_by_id(task_id: PydanticObjectId):
    """Retrieves a single task by its unique ID."""
    task = await Task.get(task_id)
    if not task:
        raise error_response("TASK_NOT_FOUND", "Task not found", status.HTTP_404_NOT_FOUND)
    return {"data": TaskOut.model_validate(task)}

@router.put("/{task_id}", response_model=dict)
async def update_task(task_id: PydanticObjectId, task_update: TaskUpdate):
    """Updates an existing task identified by its ID."""
    task = await Task.get(task_id)
    if not task:
        raise error_response("TASK_NOT_FOUND", "Task not found", status.HTTP_404_NOT_FOUND)
    
    update_data = task_update.model_dump(exclude_unset=True)
    if not update_data:
        raise error_response("NO_UPDATE_DATA", "No fields provided for update", status.HTTP_422_UNPROCESSABLE_ENTITY)

    for key, value in update_data.items():
        setattr(task, key, value)
    
    await task.save()
    return {"data": TaskOut.model_validate(task)}

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: PydanticObjectId):
    """Deletes a task identified by its ID."""
    task = await Task.get(task_id)
    if not task:
        raise error_response("TASK_NOT_FOUND", "Task not found", status.HTTP_404_NOT_FOUND)
    
    await task.delete()
    return # 204 No Content response
