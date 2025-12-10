# app/workflow/__init__.py
"""
Workflow module - Orchestrates the GenCode Studio workflow engine.

Note: Imports are done lazily to avoid circular dependencies with app.handlers.
"""

def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name == "WorkflowEngine":
        from .engine import WorkflowEngine
        return WorkflowEngine
    elif name == "run_workflow":
        from .engine import run_workflow
        return run_workflow
    elif name == "resume_workflow":
        from .engine import resume_workflow
        return resume_workflow
    elif name == "autonomous_agent_workflow":
        from .engine import autonomous_agent_workflow
        return autonomous_agent_workflow
    elif name == "WorkflowStateManager":
        from app.orchestration.state import WorkflowStateManager
        return WorkflowStateManager
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "WorkflowEngine", 
    "run_workflow", 
    "resume_workflow",
    "autonomous_agent_workflow",
    "WorkflowStateManager",
]
