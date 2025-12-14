# app/utils/path_utils.py
"""
Centralized Path Utilities - Single source of truth for project path resolution.

This module provides utilities for:
- Resolving project paths from project_id
- Validating paths are within workspace boundaries
- Constructing common paths (backend, frontend, etc.)

All modules should import these utilities instead of constructing paths inline.
"""
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import log


def get_project_path(project_id: str) -> Path:
    """
    Get the absolute path to a project workspace.
    
    This is the SINGLE SOURCE OF TRUTH for project path resolution.
    Import this function instead of constructing paths inline.
    
    Args:
        project_id: The project identifier (directory name)
        
    Returns:
        Path object pointing to the project workspace directory
        
    Example:
        from app.utils.path_utils import get_project_path
        project_path = get_project_path("my-notes-app-1234")
    """
    return settings.paths.workspaces_dir / project_id


def get_backend_path(project_id: str) -> Path:
    """Get the backend directory path for a project."""
    return get_project_path(project_id) / "backend"


def get_frontend_path(project_id: str) -> Path:
    """Get the frontend directory path for a project."""
    return get_project_path(project_id) / "frontend"


def get_backend_app_path(project_id: str) -> Path:
    """Get the backend app directory path for a project."""
    return get_project_path(project_id) / "backend" / "app"


def get_routers_path(project_id: str) -> Path:
    """Get the routers directory path for a project."""
    return get_project_path(project_id) / "backend" / "app" / "routers"


def get_models_path(project_id: str) -> Path:
    """Get the models.py file path for a project."""
    return get_project_path(project_id) / "backend" / "app" / "models.py"


def get_main_py_path(project_id: str) -> Path:
    """Get the main.py file path for a project."""
    return get_project_path(project_id) / "backend" / "app" / "main.py"


def get_contracts_path(project_id: str) -> Path:
    """Get the contracts.md file path for a project."""
    return get_project_path(project_id) / "contracts.md"


def get_tests_path(project_id: str) -> Path:
    """Get the backend tests directory path for a project."""
    return get_project_path(project_id) / "backend" / "tests"


def is_valid_project_path(path: Path) -> bool:
    """
    Check if a path is within the workspaces directory.
    
    Security check to prevent path traversal attacks.
    """
    try:
        workspaces_resolved = settings.paths.workspaces_dir.resolve()
        path_resolved = path.resolve()
        return str(path_resolved).startswith(str(workspaces_resolved))
    except Exception:
        return False


def ensure_project_directories(project_id: str) -> None:
    """
    Ensure all required project directories exist.
    
    Creates:
    - backend/app/routers
    - backend/tests
    - frontend/src/pages
    - frontend/src/components
    - frontend/src/lib
    - frontend/src/data
    """
    project_path = get_project_path(project_id)
    
    directories = [
        project_path / "backend" / "app" / "routers",
        project_path / "backend" / "tests",
        project_path / "frontend" / "src" / "pages",
        project_path / "frontend" / "src" / "components",
        project_path / "frontend" / "src" / "lib",
        project_path / "frontend" / "src" / "data",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
