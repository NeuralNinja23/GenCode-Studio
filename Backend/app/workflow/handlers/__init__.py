# app/workflow/handlers/__init__.py
"""
Workflow step handlers - one function per workflow step.

GenCode Studio Frontend-First workflow:
1. Analysis → 2. Architecture → 3. Frontend (Mock) → 4. Screenshot Verify → 
5. Contracts → 6. Backend Models → 7. Backend Routers → 8. Backend Main → 
9. Testing Backend → 10. Frontend Integration → 11. Testing Frontend → 12. Preview
"""
from .analysis import step_analysis
from .architecture import step_architecture
from .frontend_mock import step_frontend_mock  # Frontend-first with mock data
from .screenshot_verify import step_screenshot_verify  # NEW: Visual QA after frontend
from .contracts import step_contracts
from .backend import step_backend_models, step_backend_routers, step_backend_main
from .testing_backend import step_testing_backend
from .frontend_integration import step_frontend_integration  # Replace mock with API
from .testing_frontend import step_testing_frontend
from .preview import step_preview_final
from .refine import step_refine

__all__ = [
    "step_analysis",
    "step_architecture",
    "step_frontend_mock",
    "step_screenshot_verify",
    "step_contracts",
    "step_backend_models",
    "step_backend_routers",
    "step_backend_main",
    "step_testing_backend",
    "step_frontend_integration",
    "step_testing_frontend",
    "step_preview_final",
    "step_refine",
]
