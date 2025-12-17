# app/core/failure_boundary.py
"""
Failure boundary enforcer.

CRITICAL: NO step can return raw failures.
All exceptions/errors pass through classification.

This is Phase 0 - the choke point that ensures ALL errors are classified.
"""
from typing import Any, Dict, Callable
from functools import wraps
import logging

from app.core.step_outcome import StepOutcome, StepExecutionResult
from app.orchestration.failure_classifier import FailureClassifier

logger = logging.getLogger(__name__)


class FailureBoundary:
    """
    Enforces classification boundary.
    
    This decorator ensures that:
    1. No handler can return raw "failed" status
    2. All exceptions are caught and classified
    3. Legacy StepResult objects are converted to new format
    
    This prevents the taxonomy from being bypassed.
    """
    
    @staticmethod
    def enforce(fn: Callable) -> Callable:
        """
        Decorator that catches all failures and classifies them.
        
        Prevents legacy paths from bypassing taxonomy.
        
        Usage:
            @FailureBoundary.enforce
            async def handle_my_step(...) -> StepResult:
                # Your code here
        """
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            try:
                result = await fn(*args, **kwargs)
                
                # If function returns old-style StepResult with status="failed"
                if hasattr(result, 'status') and result.status == 'failed':
                    logger.warning(
                        f"Handler {fn.__name__} returned legacy failed status - classifying",
                        extra={"handler": fn.__name__}
                    )
                    
                    # Force classification
                    outcome = FailureClassifier.classify(
                        error=result.error or "Unknown failure",
                        context=result.data or {}
                    )
                    
                    # Convert to new format
                    return StepExecutionResult(
                        outcome=outcome,
                        step_name=kwargs.get('step_name', ''),
                        data=result.data if hasattr(result, 'data') else {},
                        error_details=result.error if hasattr(result, 'error') else None
                    )
                
                # If it's already a StepExecutionResult, pass through
                if isinstance(result, StepExecutionResult):
                    return result
                
                # Otherwise, assume success and pass through
                return result
                
            except Exception as e:
                logger.error(
                    f"Exception in handler {fn.__name__}: {e}",
                    exc_info=True,
                    extra={"handler": fn.__name__}
                )
                
                # Classify exception
                context = {
                    "handler": fn.__name__,
                    "args": str(args)[:200],  # Limit context size
                    "kwargs_keys": list(kwargs.keys()),
                }
                
                # Add any context from kwargs
                if 'context' in kwargs:
                    context.update(kwargs['context'])
                
                outcome = FailureClassifier.classify(
                    error=e,
                    context=context
                )
                
                logger.info(
                    f"Classified error as {outcome.value}",
                    extra={
                        "handler": fn.__name__,
                        "outcome": outcome.value,
                        "error": str(e)[:200]
                    }
                )
                
                return StepExecutionResult(
                    outcome=outcome,
                    step_name=kwargs.get('step_name', ''),
                    error_details=str(e),
                    data={}
                )
        
        return wrapper


class LegacyStepResultConverter:
    """
    Helper to convert legacy StepResult objects to new StepExecutionResult.
    
    Use this during migration phase when you need to manually convert results.
    """
    
    @staticmethod
    def convert(legacy_result: Any) -> StepExecutionResult:
        """
        Convert legacy StepResult to new StepExecutionResult.
        
        Args:
            legacy_result: Old-style StepResult object
            
        Returns:
            New StepExecutionResult with classified outcome
        """
        # Extract status
        status = getattr(legacy_result, 'status', 'ok')
        error = getattr(legacy_result, 'error', None)
        data = getattr(legacy_result, 'data', {})
        
        # Determine outcome
        if status == 'ok':
            outcome = StepOutcome.SUCCESS
        elif status == 'failed' and error:
            # Classify the error
            outcome = FailureClassifier.classify(error, data)
        else:
            # Unknown status, classify as cognitive
            outcome = StepOutcome.COGNITIVE_FAILURE
        
        return StepExecutionResult(
            outcome=outcome,
            data=data,
            error_details=error
        )
