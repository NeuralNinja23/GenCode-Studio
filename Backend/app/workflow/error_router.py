# app/workflow/error_router.py
"""
FAST v2 Error Router

Maps FAST v2 step failures to the correct repair action.
Used by the healing pipeline to determine what to repair.
"""


class ErrorRouter:
    """
    Maps FAST v2 step failures to the correct repair action.
    
    When step X fails, this tells us what artifact needs repair.
    """
    
    # Map steps to artifact names for repair
    STEP_TO_ARTIFACT = {
        "backend_routers": "backend_router",
        "BACKEND_ROUTERS": "backend_router",
        "frontend_integration": "frontend_api",
        "FRONTEND_INTEGRATION": "frontend_api",
        "backend_main": "backend_main",
        "BACKEND_MAIN": "backend_main",
        "backend_models": "backend_models",
        "BACKEND_MODELS": "backend_models",
    }
    
    # Priority order for repair (lower = higher priority)
    REPAIR_PRIORITY = {
        "backend_models": 1,
        "backend_router": 2,
        "backend_main": 3,
        "frontend_api": 4,
    }

    def route(self, step: str) -> str:
        """Get the artifact name to repair for a failed step."""
        return self.STEP_TO_ARTIFACT.get(step, "noop")

    def is_repairable(self, step: str) -> bool:
        """Check if a step can be repaired."""
        return step in self.STEP_TO_ARTIFACT or step.upper() in self.STEP_TO_ARTIFACT

    def get_repair_priority(self, step: str) -> int:
        """Get repair priority (lower = higher priority)."""
        artifact = self.route(step)
        return self.REPAIR_PRIORITY.get(artifact, 99)

    def get_repair_order(self, failed_steps: list) -> list:
        """Sort failed steps by repair priority."""
        return sorted(failed_steps, key=lambda s: self.get_repair_priority(s))
