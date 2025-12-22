# app/core/execution_record.py
"""
Phase-0 Execution Record

Tracks files created by each step for deterministic rollback.
Orchestrator owns truth - handlers never write these records.
"""
from dataclasses import dataclass, field
from typing import List
from datetime import datetime


@dataclass
class StepExecutionRecord:
    """
    Record of what a step produced during execution.
    
    Used for:
    - Rollback (delete files created by failed step)
    - Resume (know what each step created)
    - Debugging (audit trail)
    """
    step_name: str
    files_created: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    attempt_number: int = 1  # 1 = first attempt, 2 = retry
    
    def to_dict(self) -> dict:
        """Serialize for checkpoint persistence."""
        return {
            "step_name": self.step_name,
            "files_created": self.files_created,
            "timestamp": self.timestamp,
            "attempt_number": self.attempt_number
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "StepExecutionRecord":
        """Deserialize from checkpoint."""
        return cls(
            step_name=data.get("step_name", ""),
            files_created=data.get("files_created", []),
            timestamp=data.get("timestamp", ""),
            attempt_number=data.get("attempt_number", 1)
        )
