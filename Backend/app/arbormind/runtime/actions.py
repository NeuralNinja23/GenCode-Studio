# app/arbormind/runtime/actions.py
"""
ArborMind Actions - Executable actions for branches.

Defines the actions that can be taken during branch execution.
"""

from typing import Any, Dict, Callable, Optional
from dataclasses import dataclass


@dataclass
class Action:
    """
    An executable action.
    
    Actions are the primitive operations that branches can perform.
    """
    name: str
    description: str
    handler: Optional[Callable] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def execute(self, context: Dict[str, Any]) -> Any:
        """Execute the action with given context."""
        if self.handler:
            return self.handler(context)
        return None


class ActionRegistry:
    """
    Registry of available actions.
    """
    
    def __init__(self):
        self._actions: Dict[str, Action] = {}
    
    def register(self, action: Action) -> None:
        """Register an action."""
        self._actions[action.name] = action
    
    def get(self, name: str) -> Optional[Action]:
        """Get an action by name."""
        return self._actions.get(name)
    
    def list_actions(self) -> list:
        """List all registered action names."""
        return list(self._actions.keys())


# Global registry
_global_registry = ActionRegistry()


def register_action(action: Action) -> None:
    """Register an action globally."""
    _global_registry.register(action)


def get_action(name: str) -> Optional[Action]:
    """Get a globally registered action."""
    return _global_registry.get(name)


def list_actions() -> list:
    """List all globally registered actions."""
    return _global_registry.list_actions()
