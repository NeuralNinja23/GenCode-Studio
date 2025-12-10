# app/workflow/engine_v2/budget_manager.py
"""
BudgetManager for Gemini 2.5 Flash - Cost Controller for FAST Runs

This module provides per-run budget tracking and enforcement to keep
workflow costs under the target of ~30 INR per run.

Key Features:
- Per-step token estimates and policies
- Dynamic attempt limiting based on remaining budget
- Skippable steps for graceful degradation
- Real token tracking from API responses

Usage:
    budget = BudgetManager()
    budget.start_run()
    
    allowed = budget.allowed_attempts_for_step("frontend_mock")
    if allowed == 0:
        if budget.get_step_policy("frontend_mock").skippable:
            # Skip step
            pass
        else:
            # Critical step - abort
            raise BudgetExhaustedError()
    
    # After LLM call:
    budget.register_usage(input_tokens=5000, output_tokens=3000)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime, timezone
import threading
import threading


@dataclass
class StepPolicy:
    """
    Per-step budget policy.
    
    - skippable: if True, step may be skipped when budget is tight
    - max_attempts: hard cap on LLM retries for this step
    - est_input_tokens / est_output_tokens: rough estimate per attempt,
      used to *plan* how many attempts we can afford.
    """
    skippable: bool = False
    max_attempts: int = 3
    est_input_tokens: int = 4000
    est_output_tokens: int = 2000


@dataclass
class BudgetConfig:
    """
    Global budget config for a single FAST run, using:
    - one model: Gemini 2.5 Flash
    - currency: INR
    """
    
    # Per-run INR cap
    max_inr_per_run: float = 30.0
    
    # FX rate INR -> USD
    usd_to_inr: float = 90.0
    
    # Gemini 2.5 Flash pricing (USD per 1M tokens, conservative side)
    # Using higher estimates to ensure we don't exceed budget
    flash_input_usd_per_mtok: float = 0.30   # Actual: ~$0.15, using 2x buffer
    flash_output_usd_per_mtok: float = 2.50  # Actual: ~$0.60, using 4x buffer
    
    # Step-level policies
    step_policies: Dict[str, StepPolicy] = field(default_factory=lambda: {
        # Deep reasoning / correctness-critical steps
        "analysis": StepPolicy(
            skippable=False,
            max_attempts=2,
            est_input_tokens=5000,
            est_output_tokens=2500,
        ),
        "architecture": StepPolicy(
            skippable=False,
            max_attempts=2,
            est_input_tokens=6000,
            est_output_tokens=3000,
        ),
        "backend_routers": StepPolicy(
            skippable=False,
            max_attempts=3,
            est_input_tokens=6000,
            est_output_tokens=3500,
        ),
        "frontend_integration": StepPolicy(
            skippable=False,
            max_attempts=3,
            est_input_tokens=6000,
            est_output_tokens=3500,
        ),
        
        # Medium complexity, less sensitive
        "frontend_mock": StepPolicy(
            skippable=False,
            max_attempts=2,
            est_input_tokens=5000,
            est_output_tokens=3000,
        ),
        "contracts": StepPolicy(
            skippable=False,
            max_attempts=2,
            est_input_tokens=3500,
            est_output_tokens=2000,
        ),
        "backend_models": StepPolicy(
            skippable=False,
            max_attempts=2,
            est_input_tokens=4000,
            est_output_tokens=2000,
        ),
        "backend_main": StepPolicy(
            skippable=False,
            max_attempts=2,
            est_input_tokens=3000,
            est_output_tokens=1500,
        ),
        
        # Nice-to-have / QA steps that can be skipped if needed
        "screenshot_verify": StepPolicy(
            skippable=True,
            max_attempts=1,
            est_input_tokens=3000,
            est_output_tokens=1500,
        ),
        "testing_backend": StepPolicy(
            skippable=True,
            max_attempts=1,
            est_input_tokens=2500,
            est_output_tokens=1500,
        ),
        "testing_frontend": StepPolicy(
            skippable=True,
            max_attempts=1,
            est_input_tokens=2500,
            est_output_tokens=1500,
        ),
        "preview_final": StepPolicy(
            skippable=True,
            max_attempts=1,
            est_input_tokens=2000,
            est_output_tokens=1000,
        ),
    })


class BudgetManager:
    """
    Cost controller for a single FAST run (Gemini 2.5 Flash only).
    
    - Tracks real usage in USD/INR based on actual token counts
    - Decides how many attempts each step is allowed
    - Allows skipping skippable steps when budget is tight
    """
    
    def __init__(self, config: Optional[BudgetConfig] = None):
        self.config = config or BudgetConfig()
        self._lock = threading.Lock()
        self._reset_run_state()
    
    # ---------------------------------------------------------
    # Run lifecycle
    # ---------------------------------------------------------
    def _reset_run_state(self):
        """Reset state for a new run."""
        self.used_usd: float = 0.0
        self.used_tokens: Dict[str, int] = {"input": 0, "output": 0}
        self.step_usage: Dict[str, Dict[str, int]] = {}  # Per-step tracking
        self.call_log: List[Dict] = []  # Detailed call log
        self.run_started_at: Optional[str] = None
    
    def start_run(self):
        """Reset budget usage for a new FAST run."""
        with self._lock:
            self._reset_run_state()
            self.run_started_at = datetime.now(timezone.utc).isoformat()
    
    # ---------------------------------------------------------
    # Budget math
    # ---------------------------------------------------------
    @property
    def max_usd(self) -> float:
        """Maximum budget in USD."""
        return self.config.max_inr_per_run / self.config.usd_to_inr
    
    def _estimate_cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD for given token counts."""
        c = self.config
        in_usd = (input_tokens / 1_000_000) * c.flash_input_usd_per_mtok
        out_usd = (output_tokens / 1_000_000) * c.flash_output_usd_per_mtok
        return in_usd + out_usd
    
    def _remaining_usd(self) -> float:
        """Remaining budget in USD."""
        return max(self.max_usd - self.used_usd, 0.0)
    
    @property
    def remaining_inr(self) -> float:
        """Remaining budget in INR."""
        return self._remaining_usd() * self.config.usd_to_inr
    
    @property
    def used_inr(self) -> float:
        """Used budget in INR."""
        return self.used_usd * self.config.usd_to_inr
    
    # ---------------------------------------------------------
    # Policies
    # ---------------------------------------------------------
    def get_step_policy(self, step: str) -> StepPolicy:
        """Get policy for a step (with sensible defaults)."""
        return self.config.step_policies.get(
            step,
            StepPolicy(skippable=True, max_attempts=1, est_input_tokens=3000, est_output_tokens=1500)
        )
    
    def allowed_attempts_for_step(self, step: str) -> int:
        """
        Decide how many attempts this step is allowed, given the remaining budget.
        
        Returns a number in [0, policy.max_attempts].
        0 means "no attempts allowed":
          - if skippable=True → orchestrator may skip the step
          - if skippable=False → orchestrator should treat as hard failure / stop
        """
        policy = self.get_step_policy(step)
        
        with self._lock:
            remaining = self._remaining_usd()
            
            # If we have no remaining budget at all
            if remaining <= 0:
                return 0
            
            est_cost = self._estimate_cost_usd(
                policy.est_input_tokens,
                policy.est_output_tokens,
            )
            
            # If our estimate is super small (e.g. tiny prompts), guard against divide by ~0
            if est_cost <= 0:
                return policy.max_attempts
            
            # Safety margin: assume each attempt might cost ~30% more than estimate
            est_cost_with_margin = est_cost * 1.3
            
            # How many of those attempts can we afford?
            theoretical_max = int(remaining // est_cost_with_margin)
            
            if theoretical_max <= 0:
                # Not enough budget even for one attempt
                return 0
            
            return min(policy.max_attempts, theoretical_max)
    
    def can_afford_step(self, step: str) -> bool:
        """Quick check if we can afford at least one attempt of this step."""
        return self.allowed_attempts_for_step(step) > 0
    
    # ---------------------------------------------------------
    # Post-call accounting
    # ---------------------------------------------------------
    def register_usage(
        self, 
        input_tokens: int, 
        output_tokens: int,
        step: str = "",
        agent: str = "",
        is_retry: bool = False,
    ):
        """
        Call this after each ACTUAL Gemini call,
        using the real 'usage' object from the API response.
        """
        with self._lock:
            cost = self._estimate_cost_usd(input_tokens, output_tokens)
            self.used_usd += cost
            self.used_tokens["input"] += input_tokens
            self.used_tokens["output"] += output_tokens
            
            # Track per-step usage
            if step:
                if step not in self.step_usage:
                    self.step_usage[step] = {"input": 0, "output": 0, "calls": 0, "retries": 0}
                self.step_usage[step]["input"] += input_tokens
                self.step_usage[step]["output"] += output_tokens
                self.step_usage[step]["calls"] += 1
                if is_retry:
                    self.step_usage[step]["retries"] += 1
            
            # Log the call
            self.call_log.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "step": step,
                "agent": agent,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
                "is_retry": is_retry,
                "remaining_usd": self._remaining_usd(),
            })
    
    # ---------------------------------------------------------
    # Status and debugging
    # ---------------------------------------------------------
    def get_budget_status(self) -> str:
        """Return human-readable budget status emoji."""
        remaining_pct = (self._remaining_usd() / self.max_usd) * 100 if self.max_usd > 0 else 0
        
        if remaining_pct > 70:
            return "🟢 HEALTHY"
        elif remaining_pct > 40:
            return "🟡 MODERATE"
        elif remaining_pct > 15:
            return "🟠 LOW"
        else:
            return "🔴 CRITICAL"
    
    def get_usage_summary(self) -> dict:
        """Get complete usage summary for logging/debugging."""
        with self._lock:
            return {
                "status": self.get_budget_status(),
                "used_usd": round(self.used_usd, 6),
                "used_inr": round(self.used_inr, 2),
                "remaining_usd": round(self._remaining_usd(), 6),
                "remaining_inr": round(self.remaining_inr, 2),
                "max_usd": round(self.max_usd, 6),
                "max_inr": self.config.max_inr_per_run,
                "tokens": dict(self.used_tokens),
                "by_step": dict(self.step_usage),
                "total_calls": len(self.call_log),
                "run_started_at": self.run_started_at,
            }
    
    def log_status(self, prefix: str = "[BUDGET]"):
        """Print current budget status to console."""
        summary = self.get_usage_summary()
        print(f"{prefix} {summary['status']}")
        print(f"{prefix}   Used: ₹{summary['used_inr']:.2f} / ₹{summary['max_inr']:.2f}")
        print(f"{prefix}   Remaining: ₹{summary['remaining_inr']:.2f}")
        print(f"{prefix}   Tokens: {summary['tokens']['input']:,} in / {summary['tokens']['output']:,} out")


# ============================================================
# PER-PROJECT BUDGET REGISTRY
# ============================================================
# Maintains a separate BudgetManager for each project

_project_budgets: Dict[str, BudgetManager] = {}
_default_budget: Optional[BudgetManager] = None
_global_lock = threading.Lock()


def get_budget_manager(project_id: Optional[str] = None) -> BudgetManager:
    """
    Get or create a BudgetManager instance.
    
    If project_id is provided, returns a per-project instance.
    Otherwise returns a shared default instance.
    """
    global _default_budget, _project_budgets
    
    with _global_lock:
        if project_id:
            if project_id not in _project_budgets:
                _project_budgets[project_id] = BudgetManager()
            return _project_budgets[project_id]
        
        # Fallback to default singleton
        if _default_budget is None:
            _default_budget = BudgetManager()
        return _default_budget


def reset_budget_manager(project_id: Optional[str] = None) -> BudgetManager:
    """Reset a BudgetManager instance."""
    global _default_budget, _project_budgets
    
    with _global_lock:
        if project_id:
            _project_budgets[project_id] = BudgetManager()
            return _project_budgets[project_id]
        
        _default_budget = BudgetManager()
        return _default_budget


def get_all_project_budgets() -> Dict[str, BudgetManager]:
    """Get all tracked project budgets."""
    with _global_lock:
        return _project_budgets.copy()


def get_budget_for_api(project_id: str) -> dict:
    """
    Get budget data formatted for the frontend CostDashboard API.
    
    Returns data in the format expected by CostDashboard.tsx:
    - total_input_tokens, total_output_tokens, total_tokens
    - total_estimated_cost
    - by_step: { step_name: { input, output, calls, retries, agents: {} } }
    - by_agent: { agent_name: { input, output, calls, retries } }
    - by_provider_cost: { agent_name: cost_in_usd }
    - detailed_calls: [ { timestamp, agent, step, input_tokens, output_tokens, is_retry } ]
    """
    with _global_lock:
        if project_id not in _project_budgets:
            return {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "total_estimated_cost": 0.0,
                "by_step": {},
                "by_agent": {},
                "by_provider_cost": {},
                "detailed_calls": [],
            }
        
        budget = _project_budgets[project_id]
        
    summary = budget.get_usage_summary()
    
    # Transform step_usage to the format CostDashboard expects
    by_step = {}
    by_agent: Dict[str, Dict[str, int]] = {}
    by_provider_cost: Dict[str, float] = {}
    
    # Initialize step data from summary
    for step_name, step_data in summary.get("by_step", {}).items():
        by_step[step_name] = {
            "input": step_data.get("input", 0),
            "output": step_data.get("output", 0),
            "calls": step_data.get("calls", 0),
            "retries": step_data.get("retries", 0),
            "cost_usd": 0.0,  # Will be calculated from call_log
            "cost_inr": 0.0,  # INR for display
            "agents": {},  # Per-agent breakdown within step
        }
    
    # Build agent aggregates from call_log and calculate per-step costs
    # Use log copy to avoid concurrency issues during iteration
    with budget._lock:
        log_copy = list(budget.call_log)
        
    for call in log_copy:
        agent = call.get("agent", "unknown")
        call_cost = call.get("cost_usd", 0.0)
        
        if agent not in by_agent:
            by_agent[agent] = {"input": 0, "output": 0, "calls": 0, "retries": 0}
        
        by_agent[agent]["input"] += call.get("input_tokens", 0)
        by_agent[agent]["output"] += call.get("output_tokens", 0)
        by_agent[agent]["calls"] += 1
        if call.get("is_retry", False):
            by_agent[agent]["retries"] += 1
        
        # Track cost per agent
        if agent not in by_provider_cost:
            by_provider_cost[agent] = 0.0
        by_provider_cost[agent] += call_cost
        
        # Add to per-step breakdown (including cost)
        step = call.get("step", "")
        if step:
            # Ensure step exists in by_step
            if step not in by_step:
                by_step[step] = {
                    "input": 0, "output": 0, "calls": 0, "retries": 0,
                    "cost_usd": 0.0, "cost_inr": 0.0, "agents": {}
                }
            
            # Add cost to this step
            by_step[step]["cost_usd"] += call_cost
            by_step[step]["cost_inr"] = by_step[step]["cost_usd"] * budget.config.usd_to_inr
            
            # Per-agent within step
            if agent not in by_step[step]["agents"]:
                by_step[step]["agents"][agent] = {
                    "input": 0, "output": 0, "calls": 0, "retries": 0, "cost_usd": 0.0
                }
            by_step[step]["agents"][agent]["input"] += call.get("input_tokens", 0)
            by_step[step]["agents"][agent]["output"] += call.get("output_tokens", 0)
            by_step[step]["agents"][agent]["calls"] += 1
            by_step[step]["agents"][agent]["cost_usd"] += call_cost
            if call.get("is_retry", False):
                by_step[step]["agents"][agent]["retries"] += 1
    
    return {
        "total_input_tokens": summary["tokens"]["input"],
        "total_output_tokens": summary["tokens"]["output"],
        "total_tokens": summary["tokens"]["input"] + summary["tokens"]["output"],
        "total_estimated_cost": summary["used_usd"],
        "total_cost_inr": summary["used_inr"],
        "max_budget_inr": summary["max_inr"],
        "remaining_inr": summary["remaining_inr"],
        "budget_status": summary["status"],
        "by_step": by_step,
        "by_agent": by_agent,
        "by_provider_cost": by_provider_cost,
        "detailed_calls": budget.call_log,
    }

