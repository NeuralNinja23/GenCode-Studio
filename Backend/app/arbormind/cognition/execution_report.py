# app/arbormind/cognition/execution_report.py
"""
Execution Report - Result of branch execution.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ExecutionReport:
    """
    Report generated after executing a branch.
    
    Contains:
    - success: Whether execution succeeded
    - artifacts: Files/outputs generated
    - error: Error message if failed
    - metrics: Performance metrics
    """
    
    success: bool
    artifacts: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "artifacts": self.artifacts,
            "error": self.error,
            "metrics": self.metrics,
        }
