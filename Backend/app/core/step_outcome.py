# app/core/step_outcome.py
"""
Canonical step-level outcome types.

CRITICAL: These are STEP outcomes, not WORKFLOW outcomes.

Part of Phase 1 - Core Taxonomy & Types
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path


class StepOutcome(Enum):
    """Step-level outcomes (4 types only)."""
    SUCCESS = "success"
    HARD_FAILURE = "hard_failure"           # Logical impossibility (GLOBAL)
    COGNITIVE_FAILURE = "cognitive_failure" # Agent mistake (healable)
    ENVIRONMENT_FAILURE = "environment_failure" # Platform constraint


@dataclass
class StepExecutionResult:
    """Result of a single step execution."""
    outcome: StepOutcome
    step_name: str = ""
    isolated: bool = False  # True if quarantined (dead branch)
    artifacts: List[Path] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    error_details: Optional[str] = None
    tool_used: Optional[str] = None
    
    def is_successful(self) -> bool:
        """Only SUCCESS counts as success."""
        return self.outcome == StepOutcome.SUCCESS
    
    def requires_healing(self) -> bool:
        """Only COGNITIVE_FAILURE triggers healing."""
        return self.outcome == StepOutcome.COGNITIVE_FAILURE
    
    def is_dead_branch(self) -> bool:
        """Isolated steps are dead branches."""
        return self.isolated
    
    def is_hard_failure(self) -> bool:
        """HARD_FAILURE is a global truth (ignores isolation)."""
        return self.outcome == StepOutcome.HARD_FAILURE
