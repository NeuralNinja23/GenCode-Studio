# app/orchestration/attention_router.py
"""
Attention Router - Wrapper Module

This module provides backward-compatible access to the ArborMind router.
The attention routing functionality has been moved to app.arbormind.router.

This wrapper exists to prevent breaking existing imports like:
    from app.orchestration.attention_router import route_query
"""
from app.arbormind.router import (
    ArborMindRouter,
    arbormind_route,
    arbormind_attention,
    compute_archetype_routing,
    compute_ui_vibe_routing,
)

# Global router instance for simple queries
_router = ArborMindRouter()


async def route_query(query: str, options: list, top_k: int = 5) -> dict:
    """
    Route a query to the best matching options.
    
    This is a convenience wrapper around ArborMindRouter.route().
    
    Args:
        query: The text query to classify
        options: List of options with 'id' and 'description' keys
        top_k: Number of top results to return
        
    Returns:
        Dict with 'selected', 'confidence', 'ranked', 'value' keys
    """
    return await _router.route(query=query, options=options, top_k=top_k)


# Re-export for backward compatibility
__all__ = [
    "route_query",
    "ArborMindRouter",
    "arbormind_route",
    "arbormind_attention",
    "compute_archetype_routing",
    "compute_ui_vibe_routing",
]
