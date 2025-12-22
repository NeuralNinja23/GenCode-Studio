# app/handlers/__init__.py
"""
Workflow step handlers - one function per workflow step.

GenCode Studio Frontend-First workflow:
1. Architecture → 2. Frontend (Mock) → 3. Backend Implementation (Atomic) → 
4. System Integration (Backend + Frontend) → 5. Testing Backend → 
6. Testing Frontend → 7. Preview

NEW ARCHITECTURE (Tool Planning Migration):
- All handlers are now wrapped with ObservedHandler
- Every handler execution is recorded to ArborMind
- Enables gradual migration to full tool planning
"""
from .architecture import step_architecture
from .frontend_mock import step_frontend_mock 
from .backend_models import step_backend_models
from .backend_routers import step_backend_routers
from .system_integration import step_system_integration
from .testing_backend import step_testing_backend

from .testing_frontend import step_testing_frontend
from .preview import step_preview_final
from .refine import step_refine

# Tool Planning Migration: Wrap handlers with observation
from app.tools.migration import wrap_handlers_with_observation

__all__ = [
    "step_architecture",
    "step_frontend_mock",
    "step_backend_models",
    "step_backend_routers",
    "step_system_integration",
    "step_testing_backend",

    "step_testing_frontend",
    "step_preview_final",
    "step_refine",
    "HANDLERS",
]

# Raw handlers (without observation)
_RAW_HANDLERS = {
    "architecture": step_architecture,
    "frontend_mock": step_frontend_mock,
    "backend_models": step_backend_models,
    "backend_routers": step_backend_routers,
    "system_integration": step_system_integration,
    "testing_backend": step_testing_backend,

    "testing_frontend": step_testing_frontend,
    "preview_final": step_preview_final,
    "refine": step_refine,
}

# Handler registry for FASTOrchestratorV2
# All handlers are now wrapped with observation for tool planning
HANDLERS = wrap_handlers_with_observation(_RAW_HANDLERS)


