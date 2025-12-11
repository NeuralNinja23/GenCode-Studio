# app/attention/__init__.py
"""
Attention Mechanism Module.
The 'Attention is All You Need' engine for the application.

Now includes:
- Self-Evolution capabilities (learns from routing outcomes)
- Universe of Thought (UoT) operators for creative reasoning
  - C-UoT: Combinational (blend multiple archetypes)
  - E-UoT: Exploratory (inject foreign patterns)
  - T-UoT: Transformational (mutate constraints)
"""
from .router import (
    route_query, 
    compute_archetype_routing, 
    compute_ui_vibe_routing, 
    AttentionRouter,
    # UoT Functions
    UoTMode,
    creative_attention,
    blend_values,
    should_use_combinational_mode,
    ENTROPY_HIGH_THRESHOLD,
    ENTROPY_LOW_THRESHOLD,
    DEFAULT_SCALE_STANDARD,
    DEFAULT_SCALE_COMBINATIONAL,
)
from .evolution import (
    get_evolution_manager,
    evolve_before_routing,
    track_routing_decision,
    report_routing_outcome,
    get_evolution_stats,
    AttentionEvolution,
)
from .explorer import (
    inject_foreign_patterns,
    get_archetype_hints_for_error,
)

__all__ = [
    # Core Router
    "route_query", 
    "compute_archetype_routing", 
    "compute_ui_vibe_routing", 
    "AttentionRouter",
    # UoT (Universe of Thought)
    "UoTMode",
    "creative_attention",
    "blend_values",
    "should_use_combinational_mode",
    "ENTROPY_HIGH_THRESHOLD",
    "ENTROPY_LOW_THRESHOLD",
    "DEFAULT_SCALE_STANDARD",
    "DEFAULT_SCALE_COMBINATIONAL",
    # E-UoT Explorer
    "inject_foreign_patterns",
    "get_archetype_hints_for_error",
    # Evolution Layer
    "get_evolution_manager",
    "evolve_before_routing",
    "track_routing_decision",
    "report_routing_outcome",
    "get_evolution_stats",
    "AttentionEvolution",
]
