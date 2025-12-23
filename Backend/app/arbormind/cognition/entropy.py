# app/arbormind/cognition/entropy.py
"""
ArborMind Entropy - Uncertainty measurement for branches.

Entropy measures how uncertain we are about a branch's execution path.
High entropy = more uncertainty = might need to diverge.
"""

from typing import Any, Dict, List, Optional
import math


def calculate_branch_entropy(
    failures: int = 0,
    retries: int = 0,
    depth: int = 0,
    confidence: float = 1.0,
) -> float:
    """
    Calculate entropy for a branch based on execution history.
    
    Entropy increases with:
    - More failures
    - More retries
    - Lower confidence
    - Greater depth (more decisions made)
    
    Args:
        failures: Number of failures encountered
        retries: Number of retries attempted
        depth: Depth of branch in tree
        confidence: Current confidence level (0-1)
        
    Returns:
        Entropy value (0 = certain, higher = more uncertain)
    """
    # Base entropy from failures and retries
    failure_entropy = failures * 0.3
    retry_entropy = retries * 0.1
    
    # Depth adds minor entropy (more decisions = more uncertainty)
    depth_entropy = math.log1p(depth) * 0.05
    
    # Low confidence increases entropy
    confidence_entropy = (1.0 - confidence) * 0.5
    
    total_entropy = failure_entropy + retry_entropy + depth_entropy + confidence_entropy
    
    # Clamp to reasonable range
    return min(2.0, max(0.0, total_entropy))


def should_diverge(entropy: float, threshold: float = 0.5) -> bool:
    """
    Determine if a branch should diverge based on entropy.
    
    When entropy is high, we should consider creating alternative
    branches to explore different approaches.
    
    Args:
        entropy: Current entropy value
        threshold: Divergence threshold
        
    Returns:
        True if branch should diverge
    """
    return entropy >= threshold


def entropy_from_results(
    step_results: Dict[str, Dict[str, Any]],
) -> float:
    """
    Calculate entropy from step execution results.
    
    Args:
        step_results: Dict of step name -> result dict
        
    Returns:
        Aggregate entropy value
    """
    if not step_results:
        return 0.0
    
    failures = sum(1 for r in step_results.values() if r.get("status") == "failed")
    total = len(step_results)
    
    if total == 0:
        return 0.0
    
    failure_rate = failures / total
    
    # Shannon entropy approximation
    if failure_rate == 0 or failure_rate == 1:
        return 0.0
    
    entropy = -(failure_rate * math.log2(failure_rate) + 
                (1 - failure_rate) * math.log2(1 - failure_rate))
    
    return entropy


def get_entropy_label(entropy: float) -> str:
    """Get human-readable label for entropy value."""
    if entropy < 0.2:
        return "LOW"
    elif entropy < 0.5:
        return "MEDIUM"
    elif entropy < 1.0:
        return "HIGH"
    else:
        return "CRITICAL"
