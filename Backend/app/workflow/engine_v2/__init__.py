# app/workflow/engine_v2/__init__.py
"""
FAST V2 Engine - Complete Workflow Overhaul

Key improvements over V1:
1. Dependency barriers prevent cascade failures
2. Pre-step validation for critical files
3. Self-healing with fallback agents
4. Uses existing handlers (Derek, Luna, Victoria, Marcus)
5. Post-step validation for critical outputs
6. Checkpointing after each successful step
7. BudgetManager for cost control (30 INR per run target)

Usage:
    from app.workflow.engine_v2 import FASTOrchestratorV2, BudgetManager
    
    budget = BudgetManager()
    engine = FASTOrchestratorV2(
        project_id=project_id,
        manager=manager,
        project_path=project_path,
        user_request=description,
        budget_manager=budget,
    )
    await engine.run()
"""

from .fast_orchestrator import FASTOrchestratorV2, run_fast_v2_workflow
from .task_graph import TaskGraph
from .step_contracts import StepContracts
from .llm_output_integrity import LLMOutputIntegrity
from .structural_compiler import StructuralCompiler
from .fallback_router_agent import FallbackRouterAgent
from .fallback_api_agent import FallbackAPIAgent
from .budget_manager import (
    BudgetManager,
    BudgetConfig,
    StepPolicy,
    get_budget_manager,
    reset_budget_manager,
)

__all__ = [
    "FASTOrchestratorV2",
    "run_fast_v2_workflow",
    "TaskGraph", 
    "StepContracts",
    "LLMOutputIntegrity",
    "StructuralCompiler",
    "FallbackRouterAgent",
    "FallbackAPIAgent",
    # Budget management
    "BudgetManager",
    "BudgetConfig",
    "StepPolicy",
    "get_budget_manager",
    "reset_budget_manager",
]

