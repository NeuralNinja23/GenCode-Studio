from fastapi import APIRouter, Query, HTTPException, status
from beanie import PydanticObjectId
from app.models import Tag # Assuming Tag is a Beanie Document

router = APIRouter()

# Helper for consistent single item response format
def _single_item_response(item):
    if item is None:
        return {"data": None} # Should typically be preceded by a 404 HTTPException
    return {"data": item.model_dump(by_alias=True, exclude_unset=True)}

# Helper for consistent list item response format
def _list_item_response(items, total, page, limit):
    return {
        "data": [item.model_dump(by_alias=True, exclude_unset=True) for item in items],
        "total": total,
        "page": page,
        "limit": limit,
    }

@router.get(
    "/",
    response_model=dict, # Use dict to allow custom {"data": ..., "total": ...} structure
    summary="List all tags",
    response_description="A list of tags with pagination details",
)
async def list_tags(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
):
    """
    Retrieve a paginated list of all tags.
    """
    skip = (page - 1) * limit
    
    # Fetch tags and total count
    tags = await Tag.find_all().skip(skip).limit(limit).to_list()
    total_tags = await Tag.count()
    
    return _list_item_response(tags, total_tags, page, limit)

@router.post(
    "/",
    response_model=dict, # Use dict to allow custom {"data": ...} structure
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tag",
    response_description="The newly created tag",
)
async def create_tag(tag: Tag):
    """
    Create a new tag with the provided details.
    """
    # Ensure ID is not set by client, let Beanie generate it
    tag.id = None 
    await tag.insert()
    return _single_item_response(tag)

@router.get(
    "/{id}",
    response_model=dict, # Use dict to allow custom {"data": ...} structure
    summary="Get a single tag by ID",
    response_description="The requested tag",
)
async def get_tag(id: PydanticObjectId):
    """
    Retrieve a single tag by its unique identifier.
    """
    tag = await Tag.get(id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return _single_item_response(tag)

@router.put(
    "/{id}",
    response_model=dict, # Use dict to allow custom {"data": ...} structure
    summary="Update an existing tag",
    response_description="The updated tag",
)
async def update_tag(id: PydanticObjectId, tag_update: Tag):
    """
    Update an existing tag with the provided details.
    """
    existing_tag = await Tag.get(id)
    if not existing_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    
    # Update fields from the request body. 
    # exclude_unset=True allows partial updates if client sends only some fields.
    # exclude={'id'} ensures the ID field is not updated.
    update_data = tag_update.model_dump(exclude_unset=True, exclude={"id"})
    
    await existing_tag.set(update_data)
    
    return _single_item_response(existing_tag)

@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK, # Contract implies {"data": {...}} for single item, so 200 OK
    response_model=dict, # Use dict to allow custom {"data": ...} structure
    summary="Delete a tag",
    response_description="Confirmation of tag deletion",
)
async def delete_tag(id: PydanticObjectId):
    """
    Delete a tag by its unique identifier.
    """
    tag = await Tag.get(id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    
    await tag.delete()
    return {"data": {"message": f"Tag with id {id} deleted successfully"}}
