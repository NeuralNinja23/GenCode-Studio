"""
Tool policy - Filtering and selection logic for tools.

Phase 2: Added environment-aware filtering to prevent platform-incompatible tools.
"""
import platform
from typing import List

from app.tools.registry import get_tools_for_step
from app.tools.specs import ToolSpec


def filter_by_environment(tools: List[ToolSpec]) -> List[ToolSpec]:
    """
    CHANGE I: Pre-filter tools by environment constraints.
    
    Prevents tools from being selected if they can't work on current platform.
    This is Phase 2's main contribution - proactive incompatibility prevention.
    
    Args:
        tools: List of ToolSpec objects to filter
        
    Returns:
        Filtered list containing only platform-compatible tools
        
    Example:
        Playwright tool with constraints {"os": ["linux", "darwin"]}
        will be filtered out on Windows automatically.
    """
    # Get current platform
    current_os = platform.system().lower()
    os_map = {
        "windows": "windows",
        "linux": "linux",
        "darwin": "darwin",  # macOS
        "darwin": "macos",   # Alternative name
    }
    normalized_os = os_map.get(current_os, current_os)
    
    filtered = []
    for tool in tools:
        # Check OS constraints
        if "os" in tool.environment_constraints:
            allowed_os = tool.environment_constraints["os"]
            if isinstance(allowed_os, list):
                # Check if current OS is in allowed list
                if normalized_os not in allowed_os and "any" not in allowed_os:
                    continue  # Skip this tool
        
        # TODO: Add version checks for node, python, etc.
        # For now, OS filtering is sufficient
        
        filtered.append(tool)
    
    return filtered


def allowed_tools_for_step(step_name: str, filter_environment: bool = True) -> List[str]:
    """
    Get allowed tools for a step, optionally filtered by environment.
    
    Args:
        step_name: Name of the workflow step
        filter_environment: If True, filter out incompatible tools
        
    Returns:
        List of tool IDs that are allowed for this step
    """
    tools = get_tools_for_step(step_name)
    
    # Phase 2: Apply environment filtering by default
    if filter_environment:
        tools = filter_by_environment(tools)
    
    return [tool.id for tool in tools]

