# app/arbormind/cognition/lineage.py
"""
ArborMind Lineage - Track branch ancestry and history.

Provides functions to trace branch lineage and compare branches.
"""

from typing import Any, Dict, List, Optional, Tuple
from app.arbormind.cognition.branch import Branch


class LineageTracker:
    """
    Tracks and queries branch lineage within a tree.
    """
    
    def __init__(self):
        self._branches: Dict[str, Branch] = {}
        self._parent_map: Dict[str, str] = {}  # child_id -> parent_id
        self._children_map: Dict[str, List[str]] = {}  # parent_id -> [child_ids]
    
    def register(self, branch: Branch) -> None:
        """Register a branch in the lineage tracker."""
        self._branches[branch.id] = branch
        
        if branch.parent_id:
            self._parent_map[branch.id] = branch.parent_id
            if branch.parent_id not in self._children_map:
                self._children_map[branch.parent_id] = []
            self._children_map[branch.parent_id].append(branch.id)
    
    def get_ancestors(self, branch_id: str) -> List[Branch]:
        """Get all ancestors of a branch, root first."""
        ancestors = []
        current_id = branch_id
        
        while current_id in self._parent_map:
            parent_id = self._parent_map[current_id]
            if parent_id in self._branches:
                ancestors.insert(0, self._branches[parent_id])
            current_id = parent_id
        
        return ancestors
    
    def get_descendants(self, branch_id: str) -> List[Branch]:
        """Get all descendants of a branch."""
        descendants = []
        to_visit = self._children_map.get(branch_id, []).copy()
        
        while to_visit:
            child_id = to_visit.pop(0)
            if child_id in self._branches:
                descendants.append(self._branches[child_id])
                to_visit.extend(self._children_map.get(child_id, []))
        
        return descendants
    
    def get_siblings(self, branch_id: str) -> List[Branch]:
        """Get siblings of a branch (same parent)."""
        if branch_id not in self._parent_map:
            return []  # Root has no siblings
        
        parent_id = self._parent_map[branch_id]
        sibling_ids = self._children_map.get(parent_id, [])
        
        return [self._branches[sid] for sid in sibling_ids 
                if sid != branch_id and sid in self._branches]
    
    def common_ancestor(self, branch_id_1: str, branch_id_2: str) -> Optional[Branch]:
        """Find the common ancestor of two branches."""
        ancestors_1 = set(b.id for b in self.get_ancestors(branch_id_1))
        ancestors_1.add(branch_id_1)
        
        # Walk up from branch_2, find first common
        current_id = branch_id_2
        while current_id:
            if current_id in ancestors_1:
                return self._branches.get(current_id)
            current_id = self._parent_map.get(current_id)
        
        return None
    
    def distance(self, branch_id_1: str, branch_id_2: str) -> int:
        """Calculate distance between two branches in the tree."""
        common = self.common_ancestor(branch_id_1, branch_id_2)
        if not common:
            return -1  # No common ancestor
        
        # Distance = depth_1 - common_depth + depth_2 - common_depth
        b1 = self._branches.get(branch_id_1)
        b2 = self._branches.get(branch_id_2)
        
        if not b1 or not b2:
            return -1
        
        return (b1.depth - common.depth) + (b2.depth - common.depth)


def get_lineage_summary(branch: Branch, tracker: LineageTracker) -> Dict[str, Any]:
    """
    Get a summary of a branch's lineage.
    
    Returns dict with:
    - depth: Branch depth
    - ancestor_count: Number of ancestors
    - sibling_count: Number of siblings
    - descendant_count: Number of descendants
    """
    ancestors = tracker.get_ancestors(branch.id)
    siblings = tracker.get_siblings(branch.id)
    descendants = tracker.get_descendants(branch.id)
    
    return {
        "branch_id": branch.id,
        "depth": branch.depth,
        "ancestor_count": len(ancestors),
        "sibling_count": len(siblings),
        "descendant_count": len(descendants),
    }


def trace_execution_path(
    branch: Branch,
    tracker: LineageTracker,
) -> List[Tuple[str, str]]:
    """
    Trace the execution path from root to this branch.
    
    Returns list of (branch_id, step_name) tuples.
    """
    ancestors = tracker.get_ancestors(branch.id)
    path = [(a.id, a.step_name) for a in ancestors]
    path.append((branch.id, branch.step_name))
    return path
