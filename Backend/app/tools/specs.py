from dataclasses import dataclass, field
from typing import List, Optional, Literal, Dict, Any


ToolOutputType = Literal["markdown", "code", "patch", "json", "none"]
ToolExecution = Literal["none", "static", "runtime"]


@dataclass(frozen=True)
class ToolSpec:
    id: str
    description: str

    # Output guarantees
    output_type: ToolOutputType
    writes_files: List[str]

    # Safety constraints
    allows_execution: ToolExecution = "none"
    allows_network: bool = False
    allows_shell: bool = False
    allows_partial: bool = False

    # Scope
    allowed_steps: List[str] = field(default_factory=list)
    
    # Phase 2: Environment constraints for platform-aware filtering
    # Example: {"os": ["linux", "darwin"], "node": ">=18", "python": ">=3.9"}
    environment_constraints: Dict[str, Any] = field(default_factory=dict)
