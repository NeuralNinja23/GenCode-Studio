# app/orchestration/healing_budget.py
"""
Global Healing Budget Controller

Prevents runaway healing by enforcing hard limits on:
- LLM calls during healing
- Critical artifact regenerations
- Docker restarts

DESIGN PRINCIPLE:
Only the testing_backend master loop may retry.
All other components consume budget, they don't create loops.
"""

from dataclasses import dataclass, field
from threading import RLock
from typing import Dict, Optional
from datetime import datetime, timezone

from app.core.logging import log


# ═══════════════════════════════════════════════════════════════════
# HEALING BUDGET
# ═══════════════════════════════════════════════════════════════════

@dataclass
class HealingBudget:
    """
    Global budget for healing operations.

    When exhausted, healing fails fast with clear diagnostic.
    No exceptions, no workarounds.
    """

    # Budget limits (per test run)
    llm_calls_max: int = 6
    critical_regens_max: int = 2
    docker_restarts_max: int = 2

    # Usage counters
    llm_calls_used: int = 0
    critical_regens_used: int = 0
    docker_restarts_used: int = 0

    # Tracking
    started_at: Optional[str] = None
    call_log: list = field(default_factory=list)

    # Thread safety (re-entrant by design)
    _lock: RLock = field(default_factory=RLock)

    # ─────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────

    def reset(self):
        """Reset budget for a new test run."""
        with self._lock:
            self.llm_calls_used = 0
            self.critical_regens_used = 0
            self.docker_restarts_used = 0
            self.call_log.clear()
            self.started_at = datetime.now(timezone.utc).isoformat()
            log("BUDGET", "🔄 Healing budget reset")

    # ─────────────────────────────────────────────────────────
    # Remaining budget (read-only)
    # ─────────────────────────────────────────────────────────

    @property
    def llm_calls_remaining(self) -> int:
        with self._lock:
            return max(0, self.llm_calls_max - self.llm_calls_used)

    @property
    def critical_regens_remaining(self) -> int:
        with self._lock:
            return max(0, self.critical_regens_max - self.critical_regens_used)

    @property
    def docker_restarts_remaining(self) -> int:
        with self._lock:
            return max(0, self.docker_restarts_max - self.docker_restarts_used)

    def can_call_llm(self) -> bool:
        return self.llm_calls_remaining > 0

    def can_regen_critical(self) -> bool:
        return self.critical_regens_remaining > 0

    def can_restart_docker(self) -> bool:
        return self.docker_restarts_remaining > 0

    def is_exhausted(self) -> bool:
        """
        Budget is exhausted when:
        - No LLM calls remain AND
        - No critical regenerations remain
        """
        with self._lock:
            return (
                self.llm_calls_used >= self.llm_calls_max
                and self.critical_regens_used >= self.critical_regens_max
            )

    # ─────────────────────────────────────────────────────────
    # Budget consumption (write)
    # ─────────────────────────────────────────────────────────

    def use_llm_call(self, caller: str = "", reason: str = "") -> bool:
        with self._lock:
            if self.llm_calls_used >= self.llm_calls_max:
                log("BUDGET", f"🛑 LLM call DENIED ({caller}) - budget exhausted")
                return False

            self.llm_calls_used += 1
            self.call_log.append({
                "type": "llm_call",
                "caller": caller,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            log(
                "BUDGET",
                f"📊 LLM call used ({caller}): "
                f"{self.llm_calls_used}/{self.llm_calls_max}",
            )
            return True

    def use_critical_regen(self, artifact: str = "") -> bool:
        with self._lock:
            if self.critical_regens_used >= self.critical_regens_max:
                log("BUDGET", f"🛑 Critical regen DENIED ({artifact}) - budget exhausted")
                return False

            self.critical_regens_used += 1
            self.call_log.append({
                "type": "critical_regen",
                "artifact": artifact,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            log(
                "BUDGET",
                f"🔧 Critical regen used ({artifact}): "
                f"{self.critical_regens_used}/{self.critical_regens_max}",
            )
            return True

    def use_docker_restart(self, reason: str = "") -> bool:
        with self._lock:
            if self.docker_restarts_used >= self.docker_restarts_max:
                log("BUDGET", "🛑 Docker restart DENIED - budget exhausted")
                return False

            self.docker_restarts_used += 1
            self.call_log.append({
                "type": "docker_restart",
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            log(
                "BUDGET",
                f"🐳 Docker restart used: "
                f"{self.docker_restarts_used}/{self.docker_restarts_max}",
            )
            return True

    # ─────────────────────────────────────────────────────────
    # Status & Diagnostics
    # ─────────────────────────────────────────────────────────

    def get_status(self) -> Dict:
        with self._lock:
            return {
                "llm_calls": {
                    "used": self.llm_calls_used,
                    "max": self.llm_calls_max,
                    "remaining": self.llm_calls_remaining,
                },
                "critical_regens": {
                    "used": self.critical_regens_used,
                    "max": self.critical_regens_max,
                    "remaining": self.critical_regens_remaining,
                },
                "docker_restarts": {
                    "used": self.docker_restarts_used,
                    "max": self.docker_restarts_max,
                    "remaining": self.docker_restarts_remaining,
                },
                "exhausted": self.is_exhausted(),
                "started_at": self.started_at,
                "total_operations": len(self.call_log),
            }

    def get_exhaustion_diagnostic(self) -> str:
        status = self.get_status()

        lines = [
            "═══════════════════════════════════════════════════════",
            "🛑 HEALING BUDGET EXHAUSTED",
            "═══════════════════════════════════════════════════════",
            "",
            f"LLM Calls:       {status['llm_calls']['used']}/{status['llm_calls']['max']}",
            f"Critical Regens: {status['critical_regens']['used']}/{status['critical_regens']['max']}",
            f"Docker Restarts: {status['docker_restarts']['used']}/{status['docker_restarts']['max']}",
            "",
            "Recent Operations:",
        ]

        for op in self.call_log[-5:]:
            lines.append(
                f"  • {op['type']}: "
                f"{op.get('caller') or op.get('artifact') or op.get('reason')}"
            )

        lines.extend([
            "",
            "The healing system exhausted its budget without success.",
            "Manual inspection is required.",
            "═══════════════════════════════════════════════════════",
        ])

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# GLOBAL REGISTRY (PER PROJECT)
# ═══════════════════════════════════════════════════════════════════

_project_budgets: Dict[str, HealingBudget] = {}
_registry_lock: RLock = RLock()


def get_healing_budget(project_id: str) -> HealingBudget:
    """Get or create a healing budget for a project."""
    with _registry_lock:
        if project_id not in _project_budgets:
            budget = HealingBudget()
            budget.started_at = datetime.now(timezone.utc).isoformat()
            _project_budgets[project_id] = budget
        return _project_budgets[project_id]


def reset_healing_budget(project_id: str) -> HealingBudget:
    """Reset healing budget at the start of testing_backend."""
    with _registry_lock:
        budget = HealingBudget()
        budget.started_at = datetime.now(timezone.utc).isoformat()
        _project_budgets[project_id] = budget
        log("BUDGET", f"🔄 Healing budget reset for {project_id}")
        return budget


def clear_healing_budget(project_id: str):
    """Remove healing budget after workflow completion."""
    with _registry_lock:
        _project_budgets.pop(project_id, None)


def get_all_budgets() -> Dict[str, HealingBudget]:
    """Return a snapshot of all active budgets."""
    with _registry_lock:
        return dict(_project_budgets)
