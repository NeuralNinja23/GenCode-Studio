# app/workflow/engine_v2/task_graph.py
"""
FAST v2 Task Graph - Fixed Pipeline with Dependencies

Defines the fixed FAST v2 pipeline, but allows adaptive
behavior INSIDE each step (hybrid adaptive mode).
Steps cannot be removed, added, or reordered globally.
Only intra-step adaptation is allowed.
"""
from typing import Dict, List


class TaskGraph:
    """
    Defines the fixed FAST v2 pipeline, but allows adaptive
    behavior INSIDE each step (hybrid adaptive mode).
    Steps cannot be removed, added, or reordered globally.
    Only intra-step adaptation is allowed.
    """

    def __init__(self):
        # Ordered execution graph (fixed)
        self.steps: List[str] = [
            "analysis",
            "architecture",
            "frontend_mock",
            "screenshot_verify",
            "contracts",
            "backend_implementation",
            "system_integration",
            "testing_backend",
            "frontend_integration",
            "testing_frontend",
            "preview_final"
        ]

        # Dependencies prevent premature execution.
        # A step can only run when ALL its dependencies have completed successfully.
        self.dependencies: Dict[str, List[str]] = {
            "analysis": [],
            "architecture": ["analysis"],
            "frontend_mock": ["architecture"],
            "screenshot_verify": ["frontend_mock"],
            "contracts": ["frontend_mock"],
            "backend_implementation": ["architecture", "contracts"],
            "system_integration": ["backend_implementation"],
            "testing_backend": ["system_integration"],
            "frontend_integration": ["contracts", "backend_implementation"],
            "testing_frontend": ["frontend_integration"],
            "preview_final": [
                "testing_backend",
                "testing_frontend"
            ]
        }

    def get_steps(self) -> List[str]:
        """Get the ordered list of all workflow steps."""
        return self.steps.copy()

    def required_for(self, step: str) -> List[str]:
        """Get the dependencies required for a step."""
        return self.dependencies.get(step, [])

    def is_ready(self, step: str, completed: List[str]) -> bool:
        """Check if all dependencies for a step are satisfied."""
        needed = self.required_for(step)
        return all(dep in completed for dep in needed)

    def get_blocking(self, step: str, completed: List[str]) -> List[str]:
        """Get the dependencies that are NOT yet completed."""
        needed = self.required_for(step)
        return [dep for dep in needed if dep not in completed]

    def get_dependents(self, step: str) -> List[str]:
        """Get all steps that depend on this step."""
        dependents = []
        for s, deps in self.dependencies.items():
            if step in deps:
                dependents.append(s)
        return dependents

    def get_parallel_batch(self, completed: List[str]) -> List[str]:
        """Get all steps that can run in parallel right now."""
        ready = []
        for step in self.steps:
            if step not in completed and self.is_ready(step, completed):
                ready.append(step)
        return ready
