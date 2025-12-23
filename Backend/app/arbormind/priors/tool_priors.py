# app/arbormind/priors/tool_priors.py
"""
ArborMind Tool Priors (Phase 4 - Dormant)

Tool usage priors and preferences.
Currently a placeholder for future learning capabilities.
"""

from typing import Dict, List, Optional, Any


# Static tool priors (not learned, just defaults)
DEFAULT_TOOL_PRIORS: Dict[str, Dict[str, Any]] = {
    "file_write": {
        "priority": 1.0,
        "reliability": 0.95,
        "cost": 0.1,
    },
    "llm_call": {
        "priority": 0.8,
        "reliability": 0.85,
        "cost": 1.0,
    },
    "validation": {
        "priority": 0.9,
        "reliability": 0.99,
        "cost": 0.05,
    },
}


def get_tool_prior(tool_name: str) -> Dict[str, Any]:
    """
    Get prior information for a tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Prior dict with priority, reliability, cost
    """
    return DEFAULT_TOOL_PRIORS.get(tool_name, {
        "priority": 0.5,
        "reliability": 0.5,
        "cost": 0.5,
    })


def get_tool_priority(tool_name: str) -> float:
    """Get priority score for a tool (0-1)."""
    return get_tool_prior(tool_name).get("priority", 0.5)


def get_tool_reliability(tool_name: str) -> float:
    """Get reliability score for a tool (0-1)."""
    return get_tool_prior(tool_name).get("reliability", 0.5)


def rank_tools(tool_names: List[str]) -> List[str]:
    """
    Rank tools by priority.
    
    Args:
        tool_names: List of tool names to rank
        
    Returns:
        Tools sorted by priority (highest first)
    """
    return sorted(
        tool_names,
        key=lambda t: get_tool_priority(t),
        reverse=True,
    )
