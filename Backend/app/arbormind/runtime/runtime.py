# app/arbormind/runtime/runtime.py
"""
ArborMind Runtime - Main cognitive loop.

The runtime manages the cognitive cycle: observe, decide, act.
"""

from typing import Any, Optional
from app.arbormind.cognition.tree import ArborMindTree
from app.arbormind.cognition.branch import Branch


class ArborMindRuntime:
    """
    The ArborMind cognitive runtime.
    
    Manages the cognitive loop:
    1. Observe: Gather state from branches
    2. Decide: Choose next action (via router)
    3. Act: Execute the decision
    4. Record: Log observations
    """
    
    def __init__(self):
        self._cycles = 0
        self._max_cycles = 100
    
    def cycle(self, tree: ArborMindTree) -> ArborMindTree:
        """
        Run one cognitive cycle on the tree.
        
        The cycle:
        1. Examines all active branches
        2. Prunes high-entropy branches
        3. Selects best branches for execution
        
        Args:
            tree: The execution tree
            
        Returns:
            Updated tree after cycle
        """
        self._cycles += 1
        
        # Phase 3: Inhibition-only cognition
        # Just pass through - no cognitive decisions made
        # All decisions happen in the orchestrator
        
        return tree
    
    def reset(self) -> None:
        """Reset the runtime state."""
        self._cycles = 0
    
    @property
    def cycle_count(self) -> int:
        """Get number of cycles executed."""
        return self._cycles
