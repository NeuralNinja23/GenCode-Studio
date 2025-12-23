# app/arbormind/core/synthesis.py
"""
ArborMind Synthesis - Branch selection and synthesis.

Selects the best branch from the tree for execution.
"""

from typing import Optional
from app.arbormind.cognition.tree import ArborMindTree
from app.arbormind.cognition.branch import Branch


def synthesize(tree: ArborMindTree) -> Branch:
    """
    Synthesize/select the best branch for execution.
    
    Currently returns the root branch (single-branch execution).
    Future: Will select from multiple branches based on:
    - Entropy levels
    - Success probability
    - Resource constraints
    
    Args:
        tree: The execution tree
        
    Returns:
        The branch to execute
    """
    # Phase 3: Simple - just return root
    # Phase 4+: Will implement multi-branch selection
    return tree.root


def select_best_branch(branches: list) -> Optional[Branch]:
    """
    Select the best branch from a list.
    
    Selection criteria:
    - Lowest entropy
    - Highest confidence
    - Fewest failures
    
    Args:
        branches: List of candidate branches
        
    Returns:
        Best branch, or None if list is empty
    """
    if not branches:
        return None
    
    # Sort by entropy (ascending) - lower is better
    sorted_branches = sorted(branches, key=lambda b: b.entropy)
    return sorted_branches[0]
