from fastapi import APIRouter, Query, HTTPException, status
from beanie import PydanticObjectId
from app.models import Assignee # Assuming Assignee is a Beanie Document here

router = APIRouter()

@router.get(
    "/",
    response_model=dict,
    summary="List all assignees",
    response_description="A list of assignees with pagination details",
)
async def list_assignees(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
):
    """
    Retrieve a paginated list of all assignees.
    """
    skip = (page - 1) * limit
    assignees = await Assignee.find_all().skip(skip).limit(limit).to_list()
    total_assignees = await Assignee.count()

    return {
        "data": [assignee.model_dump(by_alias=True) for assignee in assignees],
        "total": total_assignees,
        "page": page,
        "limit": limit,
    }


@router.post(
    "/",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new assignee",
    response_description="The newly created assignee",
)
async def create_assignee(assignee: Assignee):
    """
    Create a new assignee with the provided details.
    """
    await assignee.insert()
    return {"data": assignee.model_dump(by_alias=True)}


@router.get(
    "/{id}",
    response_model=dict,
    summary="Get a single assignee by ID",
    response_description="Details of a specific assignee",
)
async def get_assignee(id: PydanticObjectId):
    """
    Retrieve a single assignee by its unique ID.
    """
    assignee = await Assignee.get(id)
    if not assignee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found")
    return {"data": assignee.model_dump(by_alias=True)}


@router.put(
    "/{id}",
    response_model=dict,
    summary="Update an existing assignee",
    response_description="The updated assignee details",
)
async def update_assignee(id: PydanticObjectId, updated_assignee: Assignee):
    """
    Update an existing assignee identified by its ID.
    """
    assignee = await Assignee.get(id)
    if not assignee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found")

    # Update fields manually or using set() with model_dump(exclude_unset=True) for partial updates
    # For PUT, typically a full replacement is expected, so we'll update all fields from the payload.
    assignee.name = updated_assignee.name
    assignee.avatar = updated_assignee.avatar

    await assignee.save()
    return {"data": assignee.model_dump(by_alias=True)}


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK, # 200 OK with data, or 204 No Content
    response_model=dict,
    summary="Delete an assignee",
    response_description="Confirmation of assignee deletion",
)
async def delete_assignee(id: PydanticObjectId):
    """
    Delete an assignee identified by its ID.
    """
    assignee = await Assignee.get(id)
    if not assignee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found")

    await assignee.delete()
    return {"data": {"message": f"Assignee with id {id} deleted successfully"}}
