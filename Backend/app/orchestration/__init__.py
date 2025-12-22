# app/orchestration/__init__.py
"""
FAST V2 Engine - ArborMind Execution Body

Key improvements:
1. Dependency barriers prevent cascade failures
2. Pre-step validation for critical files
3. ArborMind handles all cognitive decisions (retry, heal, escalate)
4. Uses existing handlers (Derek, Luna, Victoria, Marcus)
5. Post-step validation for critical outputs
6. Checkpointing after each successful step
7. BudgetManager for cost control (30 INR per run target)

Usage:
    from app.orchestration import FASTOrchestratorV2, BudgetManager
    
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
from app.core.llm_output_integrity import validate_llm_files, LLMOutputIntegrityError
from .structural_compiler import StructuralCompiler
from .budget_manager import (
    BudgetManager,
    BudgetConfig,
    StepPolicy,
    get_budget_manager,
    reset_budget_manager,
)
from .token_policy import (
    get_tokens_for_step,
    get_step_description,
    STEP_TOKEN_POLICIES,
)

__all__ = [
    "FASTOrchestratorV2",
    "run_fast_v2_workflow",
    "TaskGraph", 
    "validate_llm_files",
    "LLMOutputIntegrityError",
    "StructuralCompiler",
    # Budget management
    "BudgetManager",
    "BudgetConfig",
    "StepPolicy",
    "get_budget_manager",
    "reset_budget_manager",
    # Token policy (step-specific token allocation)
    "get_tokens_for_step",
    "get_step_description",
    "STEP_TOKEN_POLICIES",
]

