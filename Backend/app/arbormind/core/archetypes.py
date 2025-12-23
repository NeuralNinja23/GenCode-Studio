"""
ArborMind Archetypes
====================

Archetypes are STRUCTURED PRIORS, not decisions.

Rules:
- Archetypes are DATA ONLY
- Archetypes never route execution
- Archetypes live ONLY inside Branch.assumptions
- Archetypes may be diverged, inhibited, mutated, or abandoned
"""

from typing import Dict, List


class Archetype:
    """
    Immutable archetype template.
    Safe to copy into Branch.assumptions.
    """

    def __init__(
        self,
        name: str,
        description: str,
        default_assumptions: Dict,
        constraints: List[str],
    ):
        self.name = name
        self.description = description
        self.default_assumptions = default_assumptions
        self.constraints = constraints

    def as_assumptions(self) -> Dict:
        """
        Convert archetype into branch-safe assumptions.
        """
        return {
            "archetype": self.name,
            "archetype_description": self.description,
            "archetype_constraints": list(self.constraints),
            **self.default_assumptions,
        }


# ─────────────────────────────────────────────
# CANONICAL ARCHETYPE DEFINITIONS
# ─────────────────────────────────────────────

FULLSTACK_SOFTWARE = Archetype(
    name="fullstack_software",
    description="End-to-end production-grade software system",
    default_assumptions={
        "frontend": True,
        "backend": True,
        "database": True,
        "deployment": True,
        "testing": "comprehensive",
    },
    constraints=[
        "must_be_production_ready",
        "must_include_tests",
        "must_have_clear_architecture",
    ],
)

BACKEND_API = Archetype(
    name="backend_api",
    description="Backend-only API-driven service",
    default_assumptions={
        "frontend": False,
        "backend": True,
        "database": True,
        "testing": "api_level",
    },
    constraints=[
        "no_ui_required",
        "api_contract_mandatory",
    ],
)

FRONTEND_APP = Archetype(
    name="frontend_app",
    description="Frontend-focused application consuming external APIs",
    default_assumptions={
        "frontend": True,
        "backend": False,
        "database": False,
        "testing": "ui_level",
    },
    constraints=[
        "ui_quality_priority",
        "performance_sensitive",
    ],
)

MICROSERVICE = Archetype(
    name="microservice",
    description="Single-responsibility, independently deployable service",
    default_assumptions={
        "frontend": False,
        "backend": True,
        "database": "isolated",
        "testing": "contract_based",
    },
    constraints=[
        "single_responsibility",
        "independent_deployability",
        "strict_api_boundaries",
    ],
)

EVENT_DRIVEN_SYSTEM = Archetype(
    name="event_driven_system",
    description="Asynchronous, event-driven architecture",
    default_assumptions={
        "communication": "async",
        "messaging": True,
        "testing": "event_flow",
    },
    constraints=[
        "eventual_consistency",
        "idempotent_handlers",
    ],
)

# ─────────────────────────────────────────────
# REGISTRY (LOOKUP ONLY)
# ─────────────────────────────────────────────

ARCHETYPES: Dict[str, Archetype] = {
    a.name: a
    for a in [
        FULLSTACK_SOFTWARE,
        BACKEND_API,
        FRONTEND_APP,
        MICROSERVICE,
        EVENT_DRIVEN_SYSTEM,
    ]
}


def get_archetype(name: str) -> Archetype:
    """
    Lookup helper.
    No defaults, no fallback decisions.
    """
    return ARCHETYPES[name]
