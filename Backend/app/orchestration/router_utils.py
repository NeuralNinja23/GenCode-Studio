# app/orchestration/router_utils.py
"""
Router Wiring Utilities - Single source of truth for router detection.

This module provides shared functions for detecting whether routers
are already imported or registered in main.py. Used by both:
- handlers/backend.py (step_system_integration)
- orchestration/self_healing_manager.py

Having a single implementation prevents inconsistent idempotency checks.
"""
import re
from typing import List, Tuple


def is_router_imported(content: str, router_name: str) -> bool:
    """
    Check if a router is already imported in main.py.
    
    Handles all import variants:
    - from app.routers import notes
    - from app.routers import notes, auth, users
    - from app.routers.notes import router
    - from app.routers.notes import router as notes_router
    
    Args:
        content: The main.py file content
        router_name: Name of the router (e.g., "notes", "auth")
        
    Returns:
        True if the router is already imported
    """
    patterns = [
        rf"from app\.routers import\s+.*\b{router_name}\b",
        rf"from app\.routers\.{router_name}\s+import",
    ]
    return any(re.search(p, content) for p in patterns)


def is_router_registered(content: str, router_name: str) -> bool:
    """
    Check if a router is already registered in main.py.
    
    Handles all registration variants:
    - app.include_router(notes.router, ...)
    - app.include_router(notes_router, ...)
    
    Args:
        content: The main.py file content
        router_name: Name of the router (e.g., "notes", "auth")
        
    Returns:
        True if the router is already registered
    """
    patterns = [
        rf"include_router\s*\(\s*{router_name}\.router",
        rf"include_router\s*\(\s*{router_name}_router",
    ]
    return any(re.search(p, content) for p in patterns)


def get_missing_routers(content: str, router_names: List[str]) -> Tuple[List[str], List[str]]:
    """
    Get routers that are missing import or registration.
    
    Args:
        content: The main.py file content
        router_names: List of router names to check
        
    Returns:
        Tuple of (missing_imports, missing_registrations)
    """
    missing_imports = [r for r in router_names if not is_router_imported(content, r)]
    missing_registrations = [r for r in router_names if not is_router_registered(content, r)]
    return missing_imports, missing_registrations


def get_routers_from_directory(routers_dir) -> List[str]:
    """
    Discover router names from a routers directory.
    
    Args:
        routers_dir: Path to the routers directory
        
    Returns:
        List of router names (without .py extension, excluding __init__)
    """
    from pathlib import Path
    routers_dir = Path(routers_dir)
    
    if not routers_dir.exists():
        return []
    
    return [
        f.stem.lower() 
        for f in routers_dir.glob("*.py") 
        if f.stem != "__init__"
    ]
