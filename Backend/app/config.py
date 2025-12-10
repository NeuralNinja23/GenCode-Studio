# app/config.py
"""
DEPRECATED - Use app.core.config instead.
This file exists for backward compatibility.
"""
from app.core.config import settings

# Re-export for backward compatibility
WORKSPACES_DIR = settings.paths.workspaces_dir
FRONTEND_DIST_PATH = settings.paths.frontend_dist
PORT = settings.port

__all__ = ["WORKSPACES_DIR", "FRONTEND_DIST_PATH", "PORT", "settings"]
