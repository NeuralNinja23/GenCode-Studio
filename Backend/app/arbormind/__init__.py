# app/arbormind/__init__.py
"""
ArborMind Framework - Core Package

The ArborMind Framework is a self-evolving attention-based routing system
for autonomous code generation. It provides intelligent decision-making
at every step of the software development lifecycle.

Core Components:
- ArborMindRouter: Universal attention-based routing service
- ArborMindEvolution: Self-evolution layer that learns from outcomes
- arbormind_explore: Foreign pattern injection (E-AM)

Operators:
- C-AM (Combinational): Blend multiple archetypes using soft attention
- E-AM (Exploratory): Inject foreign patterns when stuck
- T-AM (Transformational): Mutate constraints when fundamentally blocked
"""
from .router import (
    # Core Router
    ArborMindRouter,
    arbormind_route,
    compute_archetype_routing,
    compute_ui_vibe_routing,
    
    # AM Functions
    AMMode,
    arbormind_attention,
    arbormind_blend,
    should_use_combinational_mode,
    
    # Constants
    ENTROPY_HIGH_THRESHOLD,
    ENTROPY_LOW_THRESHOLD,
    DEFAULT_SCALE_STANDARD,
    DEFAULT_SCALE_COMBINATIONAL,
    
    # Data
    PROJECT_ARCHETYPES,
    UI_VIBES,
    
    # Utilities
    get_embedding,
    softmax,
    scaled_dot_product_attention,
)
from .evolution import (
    ArborMindEvolution,
    get_evolution_manager,
    evolve_before_routing,
    track_routing_decision,
    report_routing_outcome,
    get_evolution_stats,
)
from .explorer import (
    arbormind_explore,
    get_archetype_hints_for_error,
)

# Backward compatibility alias
inject_foreign_patterns = arbormind_explore

__all__ = [
    # Core Router
    "ArborMindRouter",
    "arbormind_route",
    "compute_archetype_routing",
    "compute_ui_vibe_routing",
    
    # AM (ArborMind) Mode
    "AMMode",
    "arbormind_attention",
    "arbormind_blend",
    "should_use_combinational_mode",
    
    # Constants
    "ENTROPY_HIGH_THRESHOLD",
    "ENTROPY_LOW_THRESHOLD",
    "DEFAULT_SCALE_STANDARD",
    "DEFAULT_SCALE_COMBINATIONAL",
    
    # Data
    "PROJECT_ARCHETYPES",
    "UI_VIBES",
    
    # Utilities
    "get_embedding",
    "softmax",
    "scaled_dot_product_attention",
    
    # E-AM Explorer
    "arbormind_explore",
    "inject_foreign_patterns",  # Backward compatibility alias
    "get_archetype_hints_for_error",
    
    # Evolution Layer
    "ArborMindEvolution",
    "get_evolution_manager",
    "evolve_before_routing",
    "track_routing_decision",
    "report_routing_outcome",
    "get_evolution_stats",
]
