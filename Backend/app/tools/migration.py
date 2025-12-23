# app/tools/migration.py
"""
Tool Planning Migration Adapter

This module provides a gradual migration path from the old handler architecture
to the new tool planning architecture.

OLD ARCHITECTURE:
- Each handler calls supervised_agent_call directly
- Handler knows about Derek/Victoria/Luna
- No tool observation

NEW ARCHITECTURE:
- Handlers describe intent via build_tool_plan
- Execute via execute_tool_plan
- Full tool observation

MIGRATION STRATEGY:
1. Keep existing handlers working (backward compatible)
2. Add adapter that wraps existing handlers with tool observation
3. Gradually migrate handlers to use tool planning directly

This file provides the adapter layer (step 2).
"""

from typing import Any, Dict, Callable, Optional
from datetime import datetime, timezone
import functools

from app.tools.planning import (
    ToolPlan,
    ToolInvocationPlan,
    ToolInvocationResult,
    ToolPlanExecutionResult,
)
from app.core.logging import log


def observe_handler(step_name: str, agent_name: str = "System"):
    """
    Decorator that adds tool observation to an existing handler.
    
    Usage:
        @observe_handler("backend_models", "Derek")
        async def step_backend_models(branch):
            ... existing handler code ...
    
    This wraps the handler with:
    - Plan creation (synthetic)
    - Tool invocation start/end recording
    - Full observation without changing handler code
    """
    def decorator(handler_func: Callable):
        @functools.wraps(handler_func)
        async def wrapper(branch: Any) -> Any:
            # Create synthetic plan for observation
            plan = ToolPlan(
                step=step_name,
                agent=agent_name,
                goal=f"Execute {step_name} step",
                sequence=[
                    ToolInvocationPlan(
                        tool_name="supervised_agent_call",
                        args={"step": step_name, "agent": agent_name},
                        reason="Legacy handler execution",
                        required=True,
                    )
                ],
            )
            
            # Record start
            _record_handler_start(plan, step_name, agent_name)
            
            started_at = datetime.now(timezone.utc)
            
            try:
                # Execute original handler
                result = await handler_func(branch)
                
                ended_at = datetime.now(timezone.utc)
                duration_ms = int((ended_at - started_at).total_seconds() * 1000)
                
                # Record success
                _record_handler_end(plan, step_name, agent_name, True, duration_ms, result)
                
                return result
                
            except Exception as e:
                ended_at = datetime.now(timezone.utc)
                duration_ms = int((ended_at - started_at).total_seconds() * 1000)
                
                # Record failure
                _record_handler_end(plan, step_name, agent_name, False, duration_ms, None, str(e))
                
                raise
        
        return wrapper
    return decorator


def _record_handler_start(plan: ToolPlan, step: str, agent: str):
    """Record handler execution start to ArborMind."""
    log("TOOL-OBS", f"▶️ [{step}] Starting (agent={agent}, plan={plan.plan_id})")
    
    try:
        from app.arbormind.observation.execution_ledger import record_decision, get_current_run_id
        
        run_id = get_current_run_id()
        if run_id:
            record_decision(
                run_id=run_id,
                step=step,
                agent=agent,
                action="HANDLER_INVOKE",
                tool="supervised_agent_call",
                outcome="pending",
                reason=f"Executing {step} via legacy handler",
            )
    except Exception:
        pass


def _record_handler_end(
    plan: ToolPlan,
    step: str,
    agent: str,
    success: bool,
    duration_ms: int,
    result: Any = None,
    error: Optional[str] = None,
):
    """Record handler execution end to ArborMind."""
    status = "✅" if success else "❌"
    log("TOOL-OBS", f"{status} [{step}] Completed in {duration_ms}ms")
    
    try:
        from app.arbormind.observation.execution_ledger import update_decision_outcome, get_current_run_id
        
        run_id = get_current_run_id()
        if run_id:
            update_decision_outcome(
                run_id=run_id,
                step=step,
                outcome="success" if success else "failure",
                duration_ms=duration_ms,
                artifacts_count=1 if success else 0,
            )
    except Exception:
        pass
    
    # Record failure to learning layer
    if not success and error:
        try:
            from app.arbormind.learning import ingest_runtime_exception
            from app.arbormind.observation.execution_ledger import get_current_run_id
            
            run_id = get_current_run_id()
            if run_id:
                ingest_runtime_exception(
                    run_id=run_id,
                    step=step,
                    exception_info=f"Handler failed: {error}",
                    agent=agent,
                )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# HANDLER WRAPPER (for gradual migration)
# ═══════════════════════════════════════════════════════════════════════════════

class ObservedHandler:
    """
    Wraps an existing handler to add tool observation.
    
    Usage:
        HANDLERS = {
            "backend_models": ObservedHandler(step_backend_models, "backend_models", "Derek"),
            ...
        }
    
    This allows gradual migration without modifying handler code.
    """
    
    def __init__(self, handler: Callable, step_name: str, agent_name: str = "System"):
        self.handler = handler
        self.step_name = step_name
        self.agent_name = agent_name
    
    async def __call__(self, branch: Any) -> Any:
        """Execute handler with observation."""
        # Create synthetic plan
        plan = ToolPlan(
            step=self.step_name,
            agent=self.agent_name,
            goal=f"Execute {self.step_name} step",
            sequence=[
                ToolInvocationPlan(
                    tool_name="supervised_agent_call",
                    args={"step": self.step_name},
                    reason="Legacy handler execution",
                    required=True,
                )
            ],
        )
        
        _record_handler_start(plan, self.step_name, self.agent_name)
        started_at = datetime.now(timezone.utc)
        
        try:
            result = await self.handler(branch)
            
            ended_at = datetime.now(timezone.utc)
            duration_ms = int((ended_at - started_at).total_seconds() * 1000)
            
            _record_handler_end(plan, self.step_name, self.agent_name, True, duration_ms, result)
            return result
            
        except Exception as e:
            ended_at = datetime.now(timezone.utc)
            duration_ms = int((ended_at - started_at).total_seconds() * 1000)
            
            _record_handler_end(plan, self.step_name, self.agent_name, False, duration_ms, None, str(e))
            raise


def wrap_handlers_with_observation(handlers: Dict[str, Callable]) -> Dict[str, Callable]:
    """
    Wrap all handlers with observation.
    
    Usage:
        from app.handlers import HANDLERS
        from app.tools.migration import wrap_handlers_with_observation
        
        OBSERVED_HANDLERS = wrap_handlers_with_observation(HANDLERS)
    """
    # Agent mapping
    agent_map = {
        "architecture": "Victoria",
        "frontend_mock": "Derek",
        "backend_models": "Derek",
        "backend_routers": "Derek",
        "system_integration": "Derek",
        "testing_backend": "Derek",
        "testing_frontend": "Luna",
        "preview_final": "System",
        "refine": "Derek",
    }
    
    observed = {}
    for step_name, handler in handlers.items():
        agent = agent_map.get(step_name, "System")
        observed[step_name] = ObservedHandler(handler, step_name, agent)
    
    return observed
