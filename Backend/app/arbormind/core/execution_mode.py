# app/arbormind/core/execution_mode.py
"""
ArborMind Execution Mode - Step execution policies.

Defines execution modes and policies for different step types.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ExecutionMode(Enum):
    """Execution mode for a step."""
    ARTIFACT = "artifact"       # Must produce files
    VALIDATION = "validation"   # Validates previous output
    INTEGRATION = "integration" # Combines outputs
    TESTING = "testing"         # Runs tests
    PREVIEW = "preview"         # Shows preview


@dataclass
class ExecutionPolicy:
    """
    Policy for executing a step.
    
    Defines requirements and behavior for step execution.
    """
    mode: ExecutionMode
    requires_output: bool = True
    is_fatal: bool = True
    max_retries: int = 1
    timeout_seconds: int = 300
    
    def allows_empty_output(self) -> bool:
        """Check if empty output is allowed."""
        return not self.requires_output


# Step to policy mapping
STEP_POLICIES = {
    # ARTIFACT steps - must produce files
    "architecture": ExecutionPolicy(
        mode=ExecutionMode.ARTIFACT,
        requires_output=True,
        is_fatal=True,
        max_retries=2,
    ),
    "backend_models": ExecutionPolicy(
        mode=ExecutionMode.ARTIFACT,
        requires_output=True,
        is_fatal=True,
        max_retries=2,
    ),
    "backend_routers": ExecutionPolicy(
        mode=ExecutionMode.ARTIFACT,
        requires_output=True,
        is_fatal=True,
        max_retries=2,
    ),
    "frontend_mock": ExecutionPolicy(
        mode=ExecutionMode.ARTIFACT,
        requires_output=True,
        is_fatal=True,
        max_retries=2,
    ),
    
    # INTEGRATION steps
    "system_integration": ExecutionPolicy(
        mode=ExecutionMode.INTEGRATION,
        requires_output=False,
        is_fatal=False,
        max_retries=1,
    ),
    
    # TESTING steps - non-fatal
    "testing_backend": ExecutionPolicy(
        mode=ExecutionMode.TESTING,
        requires_output=False,
        is_fatal=False,
        max_retries=1,
    ),
    "testing_frontend": ExecutionPolicy(
        mode=ExecutionMode.TESTING,
        requires_output=False,
        is_fatal=False,
        max_retries=1,
    ),
    
    # PREVIEW steps
    "preview_final": ExecutionPolicy(
        mode=ExecutionMode.PREVIEW,
        requires_output=False,
        is_fatal=False,
        max_retries=0,
    ),
    
    # Refinement
    "refine": ExecutionPolicy(
        mode=ExecutionMode.ARTIFACT,
        requires_output=True,
        is_fatal=False,
        max_retries=1,
    ),
}


def get_execution_policy(step_name: str) -> ExecutionPolicy:
    """
    Get the execution policy for a step.
    
    Args:
        step_name: Name of the step
        
    Returns:
        ExecutionPolicy for the step
    """
    return STEP_POLICIES.get(step_name, ExecutionPolicy(
        mode=ExecutionMode.ARTIFACT,
        requires_output=True,
        is_fatal=False,
        max_retries=1,
    ))


def is_critical_step(step_name: str) -> bool:
    """Check if a step is critical (fatal if fails)."""
    policy = get_execution_policy(step_name)
    return policy.is_fatal


def get_max_retries(step_name: str) -> int:
    """Get maximum retry count for a step."""
    policy = get_execution_policy(step_name)
    return policy.max_retries


# Generation steps that produce code files
GENERATION_STEPS = {
    "architecture",
    "backend_models",
    "backend_routers",
    "frontend_mock",
    "refine",
}


def is_generation_step(step_name: str) -> bool:
    """
    Check if a step is a generation step (produces code files).
    
    Generation steps:
    - Produce code/file artifacts
    - Require LLM calls
    - Should be filtered for relevant context
    
    Args:
        step_name: Name of the step
        
    Returns:
        True if step generates code files
    """
    return step_name in GENERATION_STEPS
