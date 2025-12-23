# app/arbormind/runtime/execution_router.py
"""
ArborMind Execution Router - Central decision maker.

The router decides what action to take for each step based on
the current branch state and context.
"""

from typing import Any, Dict, Optional
from app.arbormind.runtime.decision import ExecutionAction, ExecutionDecision
from app.arbormind.cognition.branch import Branch


class ExecutionRouter:
    """
    Routes execution decisions based on branch state.
    
    The router examines:
    - Branch entropy
    - Step requirements
    - Previous failures
    - Context constraints
    
    And decides:
    - RUN_TOOL: Execute the step
    - STOP: Halt execution
    - HEAL: Attempt recovery
    - MUTATE: Try alternative approach
    """
    
    def __init__(self):
        self._decision_history: list = []
    
    def decide(
        self,
        branch: Branch,
        context: Dict[str, Any],
    ) -> ExecutionDecision:
        """
        Make an execution decision for a step.
        
        Args:
            branch: Current branch being executed
            context: Execution context with:
                - expected_outputs: Expected number of outputs
                - step: Current step name
                - failures: Previous failure count
                
        Returns:
            ExecutionDecision with action and reason
        """
        step = context.get("step", "unknown")
        failures = context.get("failures", 0)
        max_failures = context.get("max_failures", 3)
        
        # Check for too many failures
        if failures >= max_failures:
            decision = ExecutionDecision(
                action=ExecutionAction.STOP,
                reason=f"Too many failures ({failures}) for step {step}",
                confidence=1.0,
            )
            self._record_decision(decision)
            return decision
        
        # Check entropy threshold
        if branch.entropy > 1.0:
            decision = ExecutionDecision(
                action=ExecutionAction.HEAL,
                reason=f"High entropy ({branch.entropy:.2f}) suggests healing needed",
                confidence=0.7,
            )
            self._record_decision(decision)
            return decision
        
        # Default: run the tool
        decision = ExecutionDecision(
            action=ExecutionAction.RUN_TOOL,
            reason=f"Proceeding with step {step}",
            confidence=1.0,
        )
        self._record_decision(decision)
        return decision
    
    def _record_decision(self, decision: ExecutionDecision) -> None:
        """Record decision for history/debugging."""
        self._decision_history.append(decision)
    
    def get_decision_history(self) -> list:
        """Get history of decisions made."""
        return self._decision_history.copy()
