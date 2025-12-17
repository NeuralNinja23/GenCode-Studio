from fastapi import APIRouter, Query, HTTPException, status
from beanie import PydanticObjectId
from app.models import Task, EmbeddedAssignee, EmbeddedTag # Import Task (Beanie Document) and its embedded types
from typing import List, Optional
from datetime import datetime

router = APIRouter()

# Helper for consistent single item response format
def _single_item_response(item: Optional[Task]):
    if item is None:
        # This case should typically be handled by an HTTPException(404) before calling this
        return {"data": None}
    return {"data": item.model_dump(by_alias=True, exclude_unset=True)}

# Helper for consistent list item response format
def _list_response(items: List[Task], total: int, page: int, limit: int):
    return {
        "data": [item.model_dump(by_alias=True, exclude_unset=True) for item in items],
        "total": total,
        "page": page,
        "limit": limit,
    }

@router.get(
    "/",
    response_model=dict, # Use dict for custom response format
    summary="List all tasks",
    response_description="A list of tasks with pagination and filtering details",
)
async def list_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter tasks by status (e.g., 'Backlog', 'In Progress', 'Review', 'Done')"),
    priority: Optional[str] = Query(None, description="Filter tasks by priority (e.g., 'Low', 'Medium', 'High')"),
    assignee_id: Optional[str] = Query(None, description="Filter tasks by embedded assignee's ID"),
    tag_id: Optional[str] = Query(None, description="Filter tasks by embedded tag's ID"),
    search: Optional[str] = Query(None, description="Search tasks by title or description (case-insensitive)"),
):
    query = Task.find_all()

    if status:
        query = query.find(Task.status == status)
    if priority:
        query = query.find(Task.priority == priority)
    if assignee_id:
        # Filter by embedded assignee's ID
        query = query.find(Task.assignee.id == assignee_id)
    if tag_id:
        # Filter by embedded tags' IDs (any tag in the list matches)
        query = query.find(Task.tags.id == tag_id)
    if search:
        # Case-insensitive search on title or description
        query = query.find(
            {
                "$or": [
                    {"title": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}},
                ]
            }
        )

    total_count = await query.count()
    tasks = await query.skip((page - 1) * limit).limit(limit).to_list()

    return _list_response(tasks, total_count, page, limit)

@router.post(
    "/",
    response_model=dict, # Use dict for custom response format
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    response_description="The newly created task",
)
async def create_task(task: Task):
    # Ensure the ID is not set by the client for new creations
    if task.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {"code": "INVALID_INPUT", "message": "ID should not be provided for new tasks."}
            }
        )
    
    # Beanie automatically handles `createdAt` and `updatedAt` defaults
    # For embedded documents, their IDs are part of the Task document. If provided, they are used.
    await task.insert()
    return _single_item_response(task)

@router.get(
    "/{id}",
    response_model=dict, # Use dict for custom response format
    summary="Get a single task by ID",
    response_description="The requested task",
)
async def get_task(id: PydanticObjectId):
    task = await Task.get(id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {"code": "NOT_FOUND", "message": f"Task with ID {id} not found"}
            }
        )
    return _single_item_response(task)

@router.put(
    "/{id}",
    response_model=dict, # Use dict for custom response format
    summary="Update an existing task",
    response_description="The updated task",
)
async def update_task(id: PydanticObjectId, task_update: Task):
    task = await Task.get(id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {"code": "NOT_FOUND", "message": f"Task with ID {id} not found"}
            }
        )
    
    # Prevent updating the ID itself if provided in the body and different from path ID
    if task_update.id and task_update.id != str(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {"code": "INVALID_INPUT", "message": "Task ID in path and body do not match or cannot be changed."}
            }
        )
    
    # Update the task fields. model_dump(exclude_unset=True) ensures only provided fields are updated.
    # Exclude 'id' from the update payload to prevent Beanie from trying to update '_id'.
    update_data = task_update.model_dump(by_alias=True, exclude_unset=True, exclude={"id"})
    
    # Beanie's set() method handles nested updates for embedded documents.
    task.set(update_data)
    
    # Manually update `updatedAt` timestamp
    task.updatedAt = datetime.utcnow()

    await task.save()
    return _single_item_response(task)

@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    response_description="No content",
)
async def delete_task(id: PydanticObjectId):
    task = await Task.get(id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {"code": "NOT_FOUND", "message": f"Task with ID {id} not found"}
            }
        )
    await task.delete()
    # For 204 No Content, no response body is typically returned.
    return