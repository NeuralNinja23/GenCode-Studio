# app/arbormind/cognition/partial_output.py
"""
ArborMind Partial Output - Handles incomplete/partial step outputs.

Some steps can produce partial output and still be considered successful.
"""

from typing import Set


# Steps that allow partial output (non-fatal if incomplete)
PARTIAL_OUTPUT_STEPS: Set[str] = {
    "testing_backend",
    "testing_frontend", 
    "preview_final",
    "system_integration",
}

# Steps that MUST produce complete output
COMPLETE_OUTPUT_STEPS: Set[str] = {
    "architecture",
    "backend_models",
    "backend_routers",
    "frontend_mock",
}


def allows_partial_output(step_name: str) -> bool:
    """
    Check if a step allows partial output.
    
    Partial output steps can produce incomplete results and still
    be considered successful. This is useful for:
    - Testing steps (some tests may fail but others pass)
    - Preview steps (can show partial preview)
    - Integration steps (best-effort integration)
    
    Args:
        step_name: Name of the step to check
        
    Returns:
        True if step allows partial output
    """
    return step_name in PARTIAL_OUTPUT_STEPS


def requires_complete_output(step_name: str) -> bool:
    """
    Check if a step requires complete output.
    
    These steps are critical and must produce complete, valid output.
    Failure to produce complete output is a hard failure.
    
    Args:
        step_name: Name of the step to check
        
    Returns:
        True if step requires complete output
    """
    return step_name in COMPLETE_OUTPUT_STEPS


def get_minimum_files_required(step_name: str) -> int:
    """
    Get the minimum number of files required for a step.
    
    Args:
        step_name: Name of the step
        
    Returns:
        Minimum file count (0 if partial output allowed)
    """
    if allows_partial_output(step_name):
        return 0
    
    minimums = {
        "architecture": 5,  # 5 architecture files
        "backend_models": 1,  # At least models.py
        "backend_routers": 1,  # At least one router
        "frontend_mock": 1,  # At least one component
    }
    
    return minimums.get(step_name, 1)
