# app/arbormind/cognition/tree.py
"""
ArborMind Tree - The universe of possible execution paths.

The tree holds all branches and provides navigation/query capabilities.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from app.arbormind.cognition.branch import Branch


@dataclass
class ArborMindTree:
    """
    The ArborMind execution tree.
    
    Contains the root branch and all descendant branches.
    Provides methods to traverse, query, and manipulate the tree.
    """
    
    root: Branch
    branches: Dict[str, Branch] = field(default_factory=dict)
    
    def __post_init__(self):
        """Register root in branches dict."""
        self.branches[self.root.id] = self.root
    
    def add_branch(self, branch: Branch) -> None:
        """Add a branch to the tree."""
        self.branches[branch.id] = branch
    
    def get_branch(self, branch_id: str) -> Optional[Branch]:
        """Get a branch by ID."""
        return self.branches.get(branch_id)
    
    def get_children(self, branch_id: str) -> List[Branch]:
        """Get all children of a branch."""
        parent = self.branches.get(branch_id)
        if not parent:
            return []
        return [self.branches[cid] for cid in parent.children if cid in self.branches]
    
    def get_lineage(self, branch_id: str) -> List[Branch]:
        """Get the lineage (ancestors) of a branch, root first."""
        lineage = []
        current = self.branches.get(branch_id)
        while current:
            lineage.insert(0, current)
            if current.parent_id:
                current = self.branches.get(current.parent_id)
            else:
                break
        return lineage
    
    def get_leaves(self) -> List[Branch]:
        """Get all leaf branches (no children)."""
        return [b for b in self.branches.values() if not b.children]
    
    def get_active_branches(self) -> List[Branch]:
        """Get branches that are active (leaves with low entropy)."""
        leaves = self.get_leaves()
        # For now, return all leaves - entropy filtering can be added
        return leaves
    
    @property
    def depth(self) -> int:
        """Get the maximum depth of the tree."""
        if not self.branches:
            return 0
        return max(b.depth for b in self.branches.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize tree to dictionary."""
        return {
            "root_id": self.root.id,
            "branches": {bid: b.to_dict() for bid, b in self.branches.items()},
            "depth": self.depth,
        }
