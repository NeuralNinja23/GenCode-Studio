#backend/app/sandbox/_init_.py

"""
GenCode Studio - Docker Sandbox Manager
Isolated testing environment with live previews
"""

from .sandbox_manager import SandboxManager
from .sandbox_config import SandboxConfig
from .health_monitor import HealthMonitor
from .log_streamer import LogStreamer
from .preview_manager import PreviewManager

# Lazy initialization - only create when first accessed
_sandbox_instance = None

def get_sandbox() -> SandboxManager:
    """Get the sandbox singleton (lazy initialization)."""
    global _sandbox_instance
    if _sandbox_instance is None:
        _sandbox_instance = SandboxManager()
    return _sandbox_instance

# For backward compatibility, create a property-like access
# NOTE: Direct access to `sandbox` still works but is now a function call
sandbox = None  # Will be None until get_sandbox() is called


__all__ = [
    "SandboxManager",
    "SandboxConfig",
    "HealthMonitor",
    "LogStreamer",
    "PreviewManager",
    "sandbox",
    "get_sandbox",
]

