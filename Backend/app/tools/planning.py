# app/tools/planning.py
"""
Tool Planning Primitives

THE SHIFT:
- Handlers describe INTENT, not tools
- Router builds BINDING plans, not suggestions
- Agents ORCHESTRATE tools, they don't BE tools
- Execution is LINEAR and OBSERVABLE

INVARIANT: ToolPlan is immutable
INVARIANT: ToolPlan is observable (before, during, after)
INVARIANT: ToolPlan is non-executing (just a plan)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid


@dataclass(frozen=True)
class ToolInvocationPlan:
    """
    A single tool invocation in a plan.
    
    Immutable. Observable. Non-executing.
    """
    tool_name: str
    args: Dict[str, Any]
    reason: str
    required: bool = True
    
    # For tracing
    invocation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def to_dict(self) -> dict:
        return {
            "invocation_id": self.invocation_id,
            "tool_name": self.tool_name,
            "args": self.args,
            "reason": self.reason,
            "required": self.required,
        }


@dataclass(frozen=True)
class ToolPlan:
    """
    A complete execution plan for a step.
    
    This is the ONLY new concept you need.
    
    Properties:
    - Immutable: Cannot be modified after creation
    - Observable: Can be logged, recorded, inspected
    - Non-executing: Just a plan, no side effects
    
    The plan is built by the Router.
    The plan is executed by execute_tool_plan().
    """
    step: str
    agent: str
    goal: str
    sequence: tuple  # Tuple of ToolInvocationPlan (frozen)
    
    # Metadata
    plan_id: str = field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:12]}")
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def __post_init__(self):
        # Ensure sequence is a tuple (immutable)
        if isinstance(self.sequence, list):
            object.__setattr__(self, 'sequence', tuple(self.sequence))
    
    @property
    def tool_count(self) -> int:
        return len(self.sequence)
    
    @property
    def tool_names(self) -> List[str]:
        return [inv.tool_name for inv in self.sequence]
    
    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "step": self.step,
            "agent": self.agent,
            "goal": self.goal,
            "sequence": [inv.to_dict() for inv in self.sequence],
            "created_at": self.created_at,
        }


@dataclass
class ToolInvocationResult:
    """
    Result of executing a single tool invocation.
    """
    invocation_id: str
    tool_name: str
    success: bool
    output: Any
    error: Optional[str] = None
    duration_ms: int = 0
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "invocation_id": self.invocation_id,
            "tool_name": self.tool_name,
            "success": self.success,
            "output": self.output if not isinstance(self.output, Exception) else str(self.output),
            "error": self.error,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }


@dataclass
class ToolPlanExecutionResult:
    """
    Result of executing a complete tool plan.
    """
    plan_id: str
    step: str
    success: bool
    results: List[ToolInvocationResult]
    final_output: Any
    error: Optional[str] = None
    total_duration_ms: int = 0
    
    @property
    def completed_count(self) -> int:
        return sum(1 for r in self.results if r.success)
    
    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.success)
    
    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "step": self.step,
            "success": self.success,
            "completed": self.completed_count,
            "failed": self.failed_count,
            "total_duration_ms": self.total_duration_ms,
            "error": self.error,
            "results": [r.to_dict() for r in self.results],
        }


class StepFailure(Exception):
    """
    Raised when a required tool in a plan fails.
    """
    def __init__(self, step: str, tool_name: str, error: str, invocation_id: str):
        self.step = step
        self.tool_name = tool_name
        self.error = error
        self.invocation_id = invocation_id
        super().__init__(f"Step '{step}' failed at tool '{tool_name}': {error}")
