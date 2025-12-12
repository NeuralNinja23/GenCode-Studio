# app/workflow/supervision/quality_gate.py
"""
Quality gate - blocks workflow if quality is too low.
"""
import asyncio
from typing import Any, Dict, Tuple



# Quality gate state
_quality_blocked: Dict[str, Dict[str, Any]] = {}
_quality_lock = asyncio.Lock()


# PHASE 4: Critical steps definition
CRITICAL_STEPS = {
    "backend_routers", 
    "backend_main", 
    "frontend_integration",
    "architecture",
    "contracts"
}

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
    
    PHASE 4 CHANGE: Only blocks CRITICAL steps with quality < 5.
    
    Returns: (should_block, reason)
    """
    # Strict threshold for critical steps
    CRITICAL_THRESHOLD = 5
    
    # Normalize step name to check against critical set
    normalized_step = step_name.lower().replace(" ", "_")
    is_critical = any(c in normalized_step for c in CRITICAL_STEPS)
    
    async with _quality_lock:
        if approved:
            _quality_blocked.pop(project_id, None)
            return False, ""
        
        # Only block on max attempts
        if attempt >= max_attempts:
            # Block ONLY if critical step fails with low quality
            if is_critical and quality_score < CRITICAL_THRESHOLD:
                reason = (
                    f"⛔ CRITICAL GATE: {step_name} scored {quality_score}/10 "
                    f"(below threshold {CRITICAL_THRESHOLD}). Workflow halted to prevent broken core."
                )
                _quality_blocked[project_id] = {
                    "step": step_name,
                    "quality": quality_score,
                    "reason": reason,
                }
                return True, reason
            
            # Non-critical steps or acceptable quality on critical steps -> Pass with warning
            if quality_score < CRITICAL_THRESHOLD:
                 # It's low quality but not critical (or not in set), so we allow it
                 # In a real system we might flag this, but here we just don't block
                 pass

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

