# app/orchestration/artifact_types.py
"""
Centralized Artifact Type Definitions

This module defines canonical artifact names used throughout the healing system.
By centralizing these constants, we prevent naming mismatches between:
- error_router.py (step → artifact mapping)
- self_healing_manager.py (artifact → repair handler)
- healing_pipeline.py (fallback routing)

USAGE:
    from app.orchestration.artifact_types import Artifact
    
    # In error_router.py:
    STEP_TO_ARTIFACT = {
        "backend_implementation": Artifact.BACKEND_VERTICAL,
        ...
    }
    
    # In self_healing_manager.py:
    if artifact_name == Artifact.BACKEND_VERTICAL:
        return self._repair_backend_vertical()
"""
from enum import Enum


class Artifact(str, Enum):
    """
    Canonical artifact names for the healing system.
    
    Each artifact represents a reparable component of the generated workspace.
    """
    # Backend artifacts
    BACKEND_VERTICAL = "backend_vertical"      # Complete backend: models + router + wiring
    BACKEND_ROUTER = "backend_router"          # Just the router file
    BACKEND_MAIN = "backend_main"              # main.py integrator
    BACKEND_DB = "backend_db"                  # Database connection wrapper
    BACKEND_MODELS = "backend_models"          # Just models.py
    
    # Frontend artifacts  
    FRONTEND_API = "frontend_api"              # Frontend API client (lib/api.js)
    FRONTEND_PAGES = "frontend_pages"          # Page components
    FRONTEND_COMPONENTS = "frontend_components"  # Reusable UI components
    
    # Integration artifacts
    SYSTEM_INTEGRATION = "system_integration"  # Router wiring in main.py
    
    # Special
    NOOP = "noop"                              # No repair available


# Reverse mapping for display/logging
ARTIFACT_DISPLAY_NAMES = {
    Artifact.BACKEND_VERTICAL: "Backend Vertical (Models + Router)",
    Artifact.BACKEND_ROUTER: "Backend Router",
    Artifact.BACKEND_MAIN: "Backend Main",
    Artifact.BACKEND_DB: "Database Connection",
    Artifact.BACKEND_MODELS: "Backend Models",
    Artifact.FRONTEND_API: "Frontend API Client",
    Artifact.FRONTEND_PAGES: "Frontend Pages",
    Artifact.FRONTEND_COMPONENTS: "Frontend Components",
    Artifact.SYSTEM_INTEGRATION: "System Integration",
    Artifact.NOOP: "No Repair Available",
}


def get_artifact_display_name(artifact: Artifact) -> str:
    """Get human-readable display name for an artifact."""
    return ARTIFACT_DISPLAY_NAMES.get(artifact, artifact.value)
