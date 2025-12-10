"""
Tracking API endpoints - BudgetManager integration for cost dashboard.
"""

from fastapi import APIRouter
from app.orchestration.budget_manager import (
    get_budget_manager,
    get_budget_for_api,
    get_all_project_budgets,
)

router = APIRouter(prefix="/api/tracking", tags=["tracking"])


@router.get("/health")
async def health():
    """Health check for tracking service."""
    return {"status": "ok", "message": "Tracking service with BudgetManager integration"}


@router.get("/{project_id}/costs")
async def get_project_costs(project_id: str):
    """
    Get cost/token usage data for a project.
    
    Returns data in the format expected by CostDashboard.tsx:
    - total_input_tokens, total_output_tokens, total_tokens
    - total_estimated_cost (in USD)
    - by_step: per-step breakdown with agent details
    - by_agent: per-agent totals
    - by_provider_cost: cost per agent
    - detailed_calls: call log with timestamps
    """
    return get_budget_for_api(project_id)


@router.get("/{project_id}/budget")
async def get_project_budget(project_id: str):
    """
    Get budget status for a project.
    
    Returns current budget status including:
    - used_inr, remaining_inr, max_inr
    - status (HEALTHY, MODERATE, LOW, CRITICAL)
    - tokens used
    """
    budget = get_budget_manager(project_id)
    return budget.get_usage_summary()


@router.get("/projects")
async def list_tracked_projects():
    """List all projects with budget tracking."""
    budgets = get_all_project_budgets()
    return {
        "projects": list(budgets.keys()),
        "count": len(budgets),
    }

