# app/api/projects.py
"""
Project management routes.

NOTE: The workflow is NOT started here. It is started via the 
/api/workspace/{id}/generate/backend endpoint to prevent duplicates.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.config import settings


router = APIRouter(prefix="/api/projects", tags=["Projects"])


class CreateProjectRequest(BaseModel):
    prompt: str
    provider: Optional[str] = None
    model: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    status: str
    createdAt: str
    description: str
    imageUrl: str
    lastModified: str
    provider: Optional[str] = None
    model: Optional[str] = None


@router.post("", response_model=ProjectResponse)
async def create_project(request: Request, data: CreateProjectRequest):
    """Create a new project. 
    
    NOTE: This endpoint only creates the project directory.
    The workflow is started separately via /api/workspace/{id}/generate/backend
    to prevent duplicate workflow execution.
    """
    import re
    import uuid
    import json
    
    def generate_slug(prompt: str) -> str:
        """Generate a URL-safe slug from the user prompt."""
        # Take first 50 chars and clean up
        text = prompt[:50].lower()
        
        # Remove common filler words for shorter slugs
        filler_words = ['a', 'an', 'the', 'create', 'build', 'make', 'develop', 'i want', 'i need', 'please', 'for me']
        for word in filler_words:
            text = re.sub(rf'\b{word}\b', '', text, flags=re.IGNORECASE)
        
        # Replace non-alphanumeric with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', text)
        
        # Clean up multiple hyphens and leading/trailing hyphens
        slug = re.sub(r'-+', '-', slug).strip('-')
        
        # Ensure minimum length
        if len(slug) < 3:
            slug = "project"
        
        # Truncate to reasonable length
        slug = slug[:30]
        
        return slug
    
    # Generate human-readable slug from prompt
    base_slug = generate_slug(data.prompt)
    project_id = base_slug
    
    # Handle duplicates by appending a short unique suffix
    project_path = settings.paths.workspaces_dir / project_id
    if project_path.exists():
        # Add a 4-char suffix to make it unique
        suffix = str(uuid.uuid4())[:4]
        project_id = f"{base_slug}-{suffix}"
        project_path = settings.paths.workspaces_dir / project_id
    
    project_path.mkdir(parents=True, exist_ok=True)
    
    # Generate name from prompt (first 30 chars)
    project_name = data.prompt[:30] + "..." if len(data.prompt) > 30 else data.prompt
    creation_time = datetime.now(timezone.utc).isoformat()
    
    # Create formatted time for display
    formatted_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    # Save project metadata to project.json
    metadata = {
        "id": project_id,
        "name": project_name,
        "description": data.prompt,
        "provider": data.provider,
        "model": data.model,
        "createdAt": creation_time,
        "status": "created",
        "lastModified": formatted_time
    }
    
    metadata_path = project_path / "project.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    # Don't start workflow here - frontend will call /generate/backend endpoint
    
    return ProjectResponse(
        id=project_id,
        name=project_name,
        status="created",
        createdAt=creation_time,
        description=data.prompt,
        imageUrl=f"https://placehold.co/600x400/1a1a2e/9333ea?text={project_name}",
        lastModified=formatted_time,
        provider=data.provider,
        model=data.model
    )


@router.get("")
async def list_projects():
    """List all projects."""
    projects = []
    workspaces_dir = settings.paths.workspaces_dir
    
    if workspaces_dir.exists():
        import json
        
        # Sort by mtime desc
        sorted_paths = sorted(
            [p for p in workspaces_dir.iterdir() if p.is_dir() and not p.name.startswith('.')],
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for p in sorted_paths:
            # Try to read metadata from project.json
            metadata_path = p / "project.json"
            description = f"Project {p.name}"
            name = p.name
            
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        description = data.get("description", description)
                        name = data.get("name", name)
                except Exception as e:
                    print(f"Error reading metadata for {p.name}: {e}")
            
            # Get modification time
            try:
                mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                last_modified = mtime.strftime("%Y-%m-%d %H:%M")
            except OSError:
                last_modified = "Unknown"
            
            projects.append({
                "id": p.name,
                "name": name,
                "description": description,
                "path": str(p),
                "imageUrl": f"https://placehold.co/600x400/1a1a2e/9333ea?text={name}",
                "lastModified": last_modified,
            })
    
    return projects


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get project details."""
    project_path = settings.paths.workspaces_dir / project_id
    
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    
    import json
    
    # Default values
    name = project_id
    description = f"Project {project_id}"
    metadata = {}
    
    # Try to read metadata from project.json
    metadata_path = project_path / "project.json"
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                name = metadata.get("name", name)
                description = metadata.get("description", description)
        except Exception as e:
            print(f"Error reading metadata for {project_id}: {e}")
    
    # Get last modification time
    try:
        mtime = datetime.fromtimestamp(project_path.stat().st_mtime, tz=timezone.utc)
        last_modified = mtime.strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError) as e:
        # FIX #10: Log the error instead of silently swallowing it
        print(f"[PROJECTS] Could not get mtime for {project_id}: {e}")
        last_modified = "Unknown"
        
    return {
        "id": project_id,
        "name": name,
        "description": description,
        "path": str(project_path),
        "imageUrl": metadata.get("imageUrl", f"https://placehold.co/600x400/1a1a2e/9333ea?text={name}"),
        "lastModified": metadata.get("lastModified", last_modified),
        "exists": True,
        **metadata # Include all other metadata fields
    }


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete a project."""
    import shutil
    
    project_path = settings.paths.workspaces_dir / project_id
    
    if project_path.exists():
        shutil.rmtree(project_path)
        return {"deleted": True, "id": project_id}
    
    raise HTTPException(status_code=404, detail="Project not found")
