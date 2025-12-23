# app/arbormind/cognition/convergence.py
"""
ArborMind Convergence - Determines when execution is complete.

Provides functions to check if a workflow has converged to a solution.
"""

from typing import Any, Dict, Optional, List


def is_converged(
    completed_steps: List[str],
    failed_steps: List[str],
    total_steps: List[str],
    artifacts: Dict[str, Any],
) -> bool:
    """
    Check if the workflow has converged to completion.
    
    Convergence means:
    - All required steps are complete, OR
    - Remaining steps are non-critical and we have sufficient output
    
    Args:
        completed_steps: List of completed step names
        failed_steps: List of failed step names  
        total_steps: List of all step names
        artifacts: Generated artifacts/files
        
    Returns:
        True if workflow has converged
    """
    # Simple implementation: converged if all steps done or only non-critical remain
    critical_steps = {"architecture", "backend_models", "backend_routers"}
    
    remaining = set(total_steps) - set(completed_steps) - set(failed_steps)
    critical_remaining = remaining & critical_steps
    
    # Converged if no critical steps remain
    return len(critical_remaining) == 0


def get_completion_confidence(
    completed_steps: List[str],
    failed_steps: List[str],
    total_steps: List[str],
) -> float:
    """
    Calculate confidence that the workflow will complete successfully.
    
    Returns:
        Float between 0.0 and 1.0
    """
    if not total_steps:
        return 1.0
    
    completed_count = len(completed_steps)
    failed_count = len(failed_steps)
    total_count = len(total_steps)
    
    # Base confidence from completion ratio
    base_confidence = completed_count / total_count
    
    # Penalty for failures
    failure_penalty = (failed_count / total_count) * 0.5
    
    return max(0.0, min(1.0, base_confidence - failure_penalty))


def should_preview(
    completed_steps: List[str],
    artifacts: Dict[str, Any],
) -> bool:
    """
    Determine if the workflow should show a preview.
    
    Preview is appropriate when:
    - Core steps are complete
    - We have generated files to show
    
    Args:
        completed_steps: List of completed step names
        artifacts: Generated artifacts
        
    Returns:
        True if preview should be shown
    """
    required_for_preview = {"architecture", "backend_models", "frontend_mock"}
    completed_set = set(completed_steps)
    
    # Need at least the required steps
    if not required_for_preview.issubset(completed_set):
        return False
    
    # Need some artifacts
    if not artifacts:
        return False
    
    return True
