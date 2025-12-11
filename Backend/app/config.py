# app/config.py
"""
DEPRECATED - Use app.core.config instead.
This file exists for backward compatibility and will be removed in v3.0.
"""
import warnings

warnings.warn(
    "app.config is deprecated, use app.core.config instead",
    DeprecationWarning,
    stacklevel=2
)

from app.core.config import settings

# Re-export for backward compatibility
WORKSPACES_DIR = settings.paths.workspaces_dir
FRONTEND_DIST_PATH = settings.paths.frontend_dist
PORT = settings.port

__all__ = ["WORKSPACES_DIR", "FRONTEND_DIST_PATH", "PORT", "settings"]
