# app/arbormind/core/tool_selector.py
"""
ArborMind Tool Selector - Tool selection for steps.

Selects appropriate tools for each step based on capabilities.
"""

from typing import List, Optional, Dict, Any


# Step to tools mapping
STEP_TOOLS: Dict[str, List[str]] = {
    "architecture": ["llm_generate", "file_write"],
    "backend_models": ["llm_generate", "file_write", "validate_python"],
    "backend_routers": ["llm_generate", "file_write", "validate_python"],
    "frontend_mock": ["llm_generate", "file_write", "validate_jsx"],
    "system_integration": ["file_modify", "validate_imports"],
    "testing_backend": ["llm_generate", "file_write", "run_tests"],
    "testing_frontend": ["llm_generate", "file_write", "run_playwright"],
    "preview_final": ["start_preview", "capture_screenshot"],
    "refine": ["llm_generate", "file_modify"],
}


def select_tools(step_name: str) -> List[str]:
    """
    Select tools for a step.
    
    Args:
        step_name: Name of the step
        
    Returns:
        List of tool names to use
    """
    return STEP_TOOLS.get(step_name, ["llm_generate", "file_write"])


def get_primary_tool(step_name: str) -> str:
    """Get the primary tool for a step."""
    tools = select_tools(step_name)
    return tools[0] if tools else "llm_generate"


def requires_llm(step_name: str) -> bool:
    """Check if a step requires LLM generation."""
    tools = select_tools(step_name)
    return "llm_generate" in tools


def requires_validation(step_name: str) -> bool:
    """Check if a step requires validation."""
    tools = select_tools(step_name)
    return any(t.startswith("validate_") for t in tools)
