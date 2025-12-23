# app/arbormind/cognition/branch.py
"""
ArborMind Branch - Core execution unit.

A Branch represents a single execution path through the decision tree.
It carries context, assumptions, and intent for a particular approach.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from datetime import datetime
import uuid


@dataclass
class Branch:
    """
    A Branch represents an execution path in the ArborMind tree.
    
    Branches carry:
    - Intent: What we're trying to accomplish
    - Assumptions: Beliefs about the problem space
    - Strategy: How we plan to approach execution
    - Agent roles: Which agents handle which tasks
    
    Branches can be:
    - Created (from a parent or as root)
    - Executed (run through the workflow)
    - Observed (results recorded)
    - Diverged (split into multiple paths)
    - Converged (combined from multiple paths)
    """
    
    parent_id: Optional[str] = None
    depth: int = 0
    assumptions: Dict[str, Any] = field(default_factory=dict)
    intent: Dict[str, Any] = field(default_factory=dict)
    strategy: Dict[str, Any] = field(default_factory=dict)
    agent_roles: Dict[str, str] = field(default_factory=dict)
    
    # Auto-generated fields
    id: str = field(default_factory=lambda: f"branch_{uuid.uuid4().hex[:12]}")
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Execution state (mutable)
    step_name: str = ""
    run_id: str = ""
    entropy: float = 0.0
    children: List[str] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize computed fields."""
        if not self.run_id:
            self.run_id = self.intent.get("run_id", f"run_{uuid.uuid4().hex[:8]}")
    
    @property
    def project_id(self) -> str:
        """Get project ID from intent."""
        return self.intent.get("project_id", "")
    
    @property
    def project_path(self):
        """Get project path from intent."""
        return self.intent.get("project_path")
    
    @property
    def manager(self):
        """Get WebSocket manager from intent."""
        return self.intent.get("manager")
    
    @property
    def user_request(self) -> str:
        """Get user request from intent."""
        return self.intent.get("user_request", "")
    
    @property
    def provider(self) -> Optional[str]:
        """Get LLM provider from intent."""
        return self.intent.get("provider")
    
    @property
    def model(self) -> Optional[str]:
        """Get LLM model from intent."""
        return self.intent.get("model")
    
    def fork(self, mutations: Optional[Dict[str, Any]] = None) -> Branch:
        """
        Create a child branch with optional mutations.
        
        Args:
            mutations: Dict of fields to override in the child
            
        Returns:
            New Branch with this branch as parent
        """
        child = Branch(
            parent_id=self.id,
            depth=self.depth + 1,
            assumptions=dict(self.assumptions),
            intent=dict(self.intent),
            strategy=dict(self.strategy),
            agent_roles=dict(self.agent_roles),
            run_id=self.run_id,
        )
        
        if mutations:
            for key, value in mutations.items():
                if hasattr(child, key):
                    setattr(child, key, value)
                else:
                    child.metadata[key] = value
        
        self.children.append(child.id)
        return child
    
    def with_step(self, step_name: str) -> Branch:
        """Return a copy of this branch set to a specific step."""
        new_branch = Branch(
            parent_id=self.parent_id,
            depth=self.depth,
            assumptions=dict(self.assumptions),
            intent=dict(self.intent),
            strategy=dict(self.strategy),
            agent_roles=dict(self.agent_roles),
            id=self.id,
            run_id=self.run_id,
            step_name=step_name,
            entropy=self.entropy,
            metadata=dict(self.metadata),
        )
        return new_branch
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize branch to dictionary."""
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "depth": self.depth,
            "assumptions": self.assumptions,
            "intent": {k: str(v) if not isinstance(v, (str, int, float, bool, dict, list, type(None))) else v 
                      for k, v in self.intent.items()},
            "strategy": self.strategy,
            "agent_roles": self.agent_roles,
            "step_name": self.step_name,
            "run_id": self.run_id,
            "entropy": self.entropy,
            "created_at": self.created_at.isoformat(),
            "children": self.children,
        }
