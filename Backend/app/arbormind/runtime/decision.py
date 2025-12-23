# app/arbormind/runtime/decision.py
"""
ArborMind Decision - Execution actions and decisions.

Defines the possible actions the execution router can take.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any, Dict


class ExecutionAction(Enum):
    """Possible execution actions."""
    RUN_TOOL = "run_tool"      # Execute the tool/handler
    STOP = "stop"              # Stop execution
    HEAL = "heal"              # Attempt healing/recovery
    MUTATE = "mutate"          # Mutate the branch
    SKIP = "skip"              # Skip this step
    RETRY = "retry"            # Retry the step


@dataclass
class ExecutionDecision:
    """
    A decision made by the execution router.
    
    Contains:
    - action: What to do
    - reason: Why this action was chosen
    - metadata: Additional context
    """
    action: ExecutionAction
    reason: str = ""
    confidence: float = 1.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "reason": self.reason,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }
