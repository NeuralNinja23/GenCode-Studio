# app/arbormind/cognition/divergence.py
"""
ArborMind Divergence - Branch splitting logic.

When a branch has high entropy, we can diverge it into multiple
alternative approaches.
"""

from typing import List, Optional
from app.arbormind.cognition.branch import Branch


def diverge(
    branch: Branch,
    strategies: Optional[List[dict]] = None,
) -> List[Branch]:
    """
    Diverge a branch into multiple child branches.
    
    Each child branch explores a different strategy/approach.
    
    Args:
        branch: Parent branch to diverge
        strategies: List of strategy dicts for each child
        
    Returns:
        List of child branches
    """
    if strategies is None:
        # Default: create one alternative with mutation
        strategies = [
            {"approach": "conservative"},
            {"approach": "aggressive"},
        ]
    
    children = []
    for i, strategy in enumerate(strategies):
        child = branch.fork(mutations={
            "strategy": {**branch.strategy, **strategy},
            "entropy": 0.0,  # Reset entropy for new branch
        })
        children.append(child)
    
    return children


def should_diverge(
    branch: Branch,
    entropy_threshold: float = 0.5,
    max_depth: int = 3,
) -> bool:
    """
    Determine if a branch should diverge.
    
    Args:
        branch: Branch to check
        entropy_threshold: Entropy level that triggers divergence
        max_depth: Maximum tree depth (prevent infinite divergence)
        
    Returns:
        True if branch should diverge
    """
    # Don't diverge too deep
    if branch.depth >= max_depth:
        return False
    
    # Diverge if entropy is high
    return branch.entropy >= entropy_threshold
