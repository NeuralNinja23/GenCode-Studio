# app/arbormind/core/t_am_operators.py
"""
ArborMind T-AM Operators - Tree manipulation operators.

Operators for transforming the ArborMind tree structure.
"""

from typing import List, Optional, Callable, Any
from app.arbormind.cognition.tree import ArborMindTree
from app.arbormind.cognition.branch import Branch


class TreeOperator:
    """Base class for tree operators."""
    
    def __init__(self, name: str):
        self.name = name
    
    def apply(self, tree: ArborMindTree) -> ArborMindTree:
        """Apply the operator to the tree."""
        raise NotImplementedError


class PruneOperator(TreeOperator):
    """Prune high-entropy branches."""
    
    def __init__(self, threshold: float = 1.0):
        super().__init__("prune")
        self.threshold = threshold
    
    def apply(self, tree: ArborMindTree) -> ArborMindTree:
        """Remove branches with entropy above threshold."""
        to_remove = [
            bid for bid, branch in tree.branches.items()
            if branch.entropy > self.threshold and bid != tree.root.id
        ]
        
        for bid in to_remove:
            del tree.branches[bid]
        
        return tree


class DivergeOperator(TreeOperator):
    """Create divergent branches."""
    
    def __init__(self, strategies: List[dict] = None):
        super().__init__("diverge")
        self.strategies = strategies or [{"approach": "default"}]
    
    def apply(self, tree: ArborMindTree) -> ArborMindTree:
        """Create child branches with different strategies."""
        leaves = tree.get_leaves()
        
        for leaf in leaves:
            for strategy in self.strategies:
                child = leaf.fork(mutations={"strategy": strategy})
                tree.add_branch(child)
        
        return tree


class ConvergeOperator(TreeOperator):
    """Converge branches back together."""
    
    def __init__(self):
        super().__init__("converge")
    
    def apply(self, tree: ArborMindTree) -> ArborMindTree:
        """Select best leaf and prune others."""
        leaves = tree.get_leaves()
        if len(leaves) <= 1:
            return tree
        
        # Select best (lowest entropy)
        best = min(leaves, key=lambda b: b.entropy)
        
        # Remove other leaves
        for leaf in leaves:
            if leaf.id != best.id:
                del tree.branches[leaf.id]
        
        return tree


def apply_operators(
    tree: ArborMindTree,
    operators: List[TreeOperator],
) -> ArborMindTree:
    """Apply a sequence of operators to a tree."""
    result = tree
    for op in operators:
        result = op.apply(result)
    return result
