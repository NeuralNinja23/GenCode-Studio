# app/arbormind/core/explorer.py
"""
ArborMind Explorer - Branch exploration strategies.

Defines strategies for exploring the branch tree.
"""

from typing import List, Optional
from app.arbormind.cognition.branch import Branch
from app.arbormind.cognition.tree import ArborMindTree


def explore(
    tree: ArborMindTree,
    strategy: str = "depth_first",
) -> List[Branch]:
    """
    Explore the tree and return branches in exploration order.
    
    Args:
        tree: The tree to explore
        strategy: Exploration strategy ("depth_first", "breadth_first", "entropy")
        
    Returns:
        List of branches in exploration order
    """
    if strategy == "depth_first":
        return _depth_first(tree)
    elif strategy == "breadth_first":
        return _breadth_first(tree)
    elif strategy == "entropy":
        return _entropy_guided(tree)
    else:
        return _depth_first(tree)


def _depth_first(tree: ArborMindTree) -> List[Branch]:
    """Depth-first exploration."""
    result = []
    stack = [tree.root]
    
    while stack:
        branch = stack.pop()
        result.append(branch)
        children = tree.get_children(branch.id)
        stack.extend(reversed(children))
    
    return result


def _breadth_first(tree: ArborMindTree) -> List[Branch]:
    """Breadth-first exploration."""
    result = []
    queue = [tree.root]
    
    while queue:
        branch = queue.pop(0)
        result.append(branch)
        children = tree.get_children(branch.id)
        queue.extend(children)
    
    return result


def _entropy_guided(tree: ArborMindTree) -> List[Branch]:
    """Explore low-entropy branches first."""
    all_branches = list(tree.branches.values())
    return sorted(all_branches, key=lambda b: b.entropy)
