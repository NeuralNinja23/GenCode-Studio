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

sandbox = SandboxManager()   # <--- The entire missing piece


__all__ = [
    "SandboxManager",
    "SandboxConfig",
    "HealthMonitor",
    "LogStreamer",
    "PreviewManager",
    "sandbox"     
]
