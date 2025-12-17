# app/orchestration/retry_policy.py
"""
CHANGE C: Brief retry for environment failures.

Rules:
- 1 immediate retry
- 1 delayed retry (5s)
- Then isolate

Phase 6: Never try to "fix" environment with reasoning.
Environment constraints are platform-level, not code-level.
"""
import asyncio
from typing import Callable, Any
from app.core.step_outcome import StepOutcome, StepExecutionResult
from app.core.logging import log


class RetryPolicy:
    """
    Retry policy for environment failures.
    
    Philosophy:
    - Environment failures MIGHT be transient (network glitch, temp resource lock)
    - OR they might be persistent (Playwright not installed on Windows)
    - We retry briefly to distinguish transient from persistent
    - If still failing after retries → it's persistent → isolate
    """
    
    @staticmethod
    async def retry_environment_failures(
        step_fn: Callable,
        step_name: str,
        max_retries: int = 0  # CHANGED: Default to 0 (One Shot Policy)
    ) -> StepExecutionResult:
        """
        Retry with backoff for environment failures only.
        
        Args:
            step_fn: Async function to execute
            step_name: Name of step (for logging)
            max_retries: Maximum number of retries (default: 2)
            
        Returns:
            StepExecutionResult from the step execution
        """
        result = None
        
        for attempt in range(max_retries + 1):  # +1 for initial attempt
            if attempt > 0:
                log("RETRY", f"🔄 Retry {attempt}/{max_retries} for {step_name}")
            
            result = await step_fn()
            
            # Only retry ENVIRONMENT_FAILURE
            if not isinstance(result, StepExecutionResult):
                # Not a StepExecutionResult, return as-is
                return result
            
            if result.outcome != StepOutcome.ENVIRONMENT_FAILURE:
                # Success or other failure type, don't retry
                if attempt > 0:
                    log("RETRY", f"✅ Retry succeeded for {step_name} on attempt {attempt + 1}")
                return result
            
            # It's an ENVIRONMENT_FAILURE
            if attempt < max_retries:
                # Wait before retry (exponential backoff)
                delay = 5 * (attempt + 1)  # 5s, 10s
                log("RETRY", f"⏳ ENVIRONMENT_FAILURE detected, waiting {delay}s before retry...")
                await asyncio.sleep(delay)
            else:
                # Max retries reached, it's persistent
                log("RETRY", f"🔒 Max retries reached for {step_name} - environment constraint is persistent")
        
        # Still failing after all retries → mark for isolation
        return result
    
    @staticmethod
    async def should_retry(result: Any) -> bool:
        """
        Check if a result should be retried.
        
        Args:
            result: Step execution result
            
        Returns:
            True if should retry
        """
        if not isinstance(result, StepExecutionResult):
            return False
        
        # Only retry ENVIRONMENT_FAILURE
        return result.outcome == StepOutcome.ENVIRONMENT_FAILURE
    
    @staticmethod
    def get_retry_delay(attempt: int) -> int:
        """
        Get retry delay for attempt number.
        
        Args:
            attempt: Attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: 5s, 10s, 15s...
        return 5 * (attempt + 1)
