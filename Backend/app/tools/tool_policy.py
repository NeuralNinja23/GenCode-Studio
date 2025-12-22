# app/tools/tool_policy.py
"""
Tool policy - Filtering and selection logic for tools.

Uses the consolidated tools.py as the single source of truth.
"""
import platform
from typing import List

from app.tools.tools import get_tools_for_phase, ToolDefinition


def filter_by_environment(tools: List[ToolDefinition]) -> List[ToolDefinition]:
    """
    Pre-filter tools by environment constraints.
    
    Prevents tools from being selected if they can't work on current platform.
    """
    current_os = platform.system().lower()
    
    # For now, all tools pass - specific constraints can be added to ToolDefinition
    # if needed in the future
    return tools


def allowed_tools_for_step(step_name: str, filter_environment: bool = True) -> List[str]:
    """
    Get allowed tools for a step, optionally filtered by environment.
    
    Args:
        step_name: Name of the workflow step
        filter_environment: If True, filter out incompatible tools
        
    Returns:
        List of tool IDs that are allowed for this step
    """
    tools = get_tools_for_phase(step_name)
    
    if filter_environment:
        tools = filter_by_environment(tools)
    
    return [tool.id for tool in tools]
