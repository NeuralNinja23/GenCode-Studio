from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from beanie import PydanticObjectId

# CRITICAL: Docker imports: Use `app.X` NOT `backend.app.X`
from app.models import Note

router = APIRouter()

# Pydantic models for request bodies
class NoteCreate(BaseModel):
    lead_id: PydanticObjectId = Field(..., description="ID of the lead this note is associated with")
    content: str = Field(..., min_length=1, max_length=1000, description="Content of the note")

class NoteUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=1000, description="Updated content of the note")

@router.get("/", response_model=dict)
async def list_notes(
    page: int = Query(1, ge=1, description="Page number for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    lead_id: Optional[PydanticObjectId] = Query(None, description="Filter notes by lead ID")
):
    """
    Retrieve a list of notes, with optional pagination and filtering by lead_id.
    """
    query = {}
    if lead_id:
        query["lead_id"] = lead_id

    notes_query = Note.find(query)
    total_notes = await notes_query.count()
    
    notes = await notes_query.skip((page - 1) * limit).limit(limit).to_list()

    return {
        "data": [note.model_dump(by_alias=True) for note in notes],
        "total": total_notes,
        "page": page,
        "limit": limit
    }

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_note(note_data: NoteCreate):
    """
    Create a new note.
    """
    # Assuming Note model in app.models handles id and created_at defaults
    new_note = Note(**note_data.model_dump())
    await new_note.insert()
    return {"data": new_note.model_dump(by_alias=True)}

@router.get("/{id}", response_model=dict)
async def get_note(id: PydanticObjectId):
    """
    Retrieve a single note by its ID.
    """
    note = await Note.get(id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            "error": {"code": "NOTE_NOT_FOUND", "message": f"Note with ID {id} not found"}
        })
    return {"data": note.model_dump(by_alias=True)}

@router.put("/{id}", response_model=dict)
async def update_note(id: PydanticObjectId, note_update: NoteUpdate):
    """
    Update an existing note by its ID.
    """
    note = await Note.get(id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            "error": {"code": "NOTE_NOT_FOUND", "message": f"Note with ID {id} not found"}
        })
    
    update_data = note_update.model_dump(exclude_unset=True)
    if update_data: # Only update if there's data to update
        await note.set(update_data)
    
    return {"data": note.model_dump(by_alias=True)}

@router.delete("/{id}", response_model=dict)
async def delete_note(id: PydanticObjectId):
    """
    Delete a note by its ID.
    """
    note = await Note.get(id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            "error": {"code": "NOTE_NOT_FOUND", "message": f"Note with ID {id} not found"}
        })
    
    await note.delete()
    return {"data": note.model_dump(by_alias=True)} # Return the deleted item as per contract
