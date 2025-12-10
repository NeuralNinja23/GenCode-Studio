# app/workflow/supervision/quality_gate.py
"""
Quality gate - blocks workflow if quality is too low.
"""
import asyncio
from typing import Any, Dict, Tuple

from app.core.config import settings


# Quality gate state
_quality_blocked: Dict[str, Dict[str, Any]] = {}
_quality_lock = asyncio.Lock()


async def check_quality_gate(
    project_id: str,
    step_name: str,
    quality_score: int,
    approved: bool,
    attempt: int,
    max_attempts: int,
) -> Tuple[bool, str]:
    """
    Check if workflow should be blocked due to quality issues.
    
    Returns: (should_block, reason)
    """
    threshold = settings.workflow.quality_gate_threshold
    
    async with _quality_lock:
        if approved:
            _quality_blocked.pop(project_id, None)
            return False, ""
        
        if attempt >= max_attempts and quality_score < threshold:
            reason = (
                f"Quality gate triggered: {step_name} scored {quality_score}/10 "
                f"after {attempt} attempts (minimum: {threshold})"
            )
            _quality_blocked[project_id] = {
                "step": step_name,
                "quality": quality_score,
                "reason": reason,
            }
            return True, reason
        
        return False, ""


async def override_quality_gate(project_id: str) -> None:
    """Allow user to override quality gate."""
    async with _quality_lock:
        _quality_blocked.pop(project_id, None)


def is_blocked(project_id: str) -> bool:
    """Check if project is blocked by quality gate."""
    return project_id in _quality_blocked


def get_block_reason(project_id: str) -> str:
    """Get the reason for quality gate block."""
    return _quality_blocked.get(project_id, {}).get("reason", "")

