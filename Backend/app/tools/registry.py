# app/tools/registry.py
"""
Tool registry and dispatcher.

Uses the consolidated tools.py as the single source of truth.
"""

from typing import Dict, Any, Optional, List


async def run_tool(name: str = None, args: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    Run a tool by name.
    
    Uses the consolidated tools.py registry.
    
    Supports both:
    - run_tool("toolname", args)
    - run_tool(name="toolname", args=args)
    """
    # Handle both positional and keyword
    tool_name = name or kwargs.get("name", "")
    tool_args = args or kwargs.get("args", {})
    
    from app.tools.tools import run_tool as tools_run_tool
    return await tools_run_tool(tool_name, tool_args)


def get_available_tools() -> List[str]:
    """Get list of all available tool names."""
    from app.tools.tools import TOOLS
    return list(TOOLS.keys())


def get_tools_for_step(step: str) -> List[str]:
    """Get tools available for a specific step."""
    from app.tools.tools import get_tools_for_phase
    return [t.id for t in get_tools_for_phase(step)]


async def get_relevant_tools_for_query(
    query: str,
    top_k: int = 3,
    context_type: str = "agent_tool_selection",
    archetype: str = "unknown",
    step_name: str = ""
) -> List[Any]:
    """
    Find the most relevant tools for a given query and context.
    
    Legacy compatibility function - returns tool definitions.
    """
    from app.tools.tools import get_tools_for_phase, TOOLS
    
    # Get tools for this specific step
    if step_name:
        tools = get_tools_for_phase(step_name)
    else:
        tools = list(TOOLS.values())
    
    # Return top_k tools
    return tools[:top_k]


def log(module: str, message: str):
    """Simple internal logger."""
    try:
        from app.core.logging import log as core_log
        core_log(module, message)
    except ImportError:
        print(f"[{module}] {message}")
