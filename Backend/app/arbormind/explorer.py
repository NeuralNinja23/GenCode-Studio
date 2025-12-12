# app/arbormind/explorer.py
"""
E-AM: Exploratory ArborMind - Foreign Pattern Injection.

When the system is stuck on a problem, this module pulls patterns
from FOREIGN archetypes using the V-Vector store. This is the
"cross-pollination" engine that enables creative problem-solving.

Example:
    If "Admin Dashboard" repair strategies keep failing for a
    RecursionError, the explorer might find that "Gaming" apps
    commonly handle recursion with tail optimization patterns
    and inject that knowledge into the repair attempt.
"""
import numpy as np
from typing import Dict, List, Any, Optional
from app.core.logging import log
from app.core.config import settings


async def arbormind_explore(
    archetype: str,
    error_text: str,
    limit: int = 3
) -> Dict[str, Any]:
    """
    E-AM: Inject patterns from foreign archetypes.
    
    When standard repair strategies fail, this function searches
    for similar error patterns in DIFFERENT archetypes and returns
    the most relevant foreign solutions.
    
    Args:
        archetype: Current project archetype (to exclude)
        error_text: The error message or context
        limit: Maximum number of foreign patterns to return
        
    Returns:
        Dict containing:
            - patterns: List of foreign pattern dicts
            - weights: Attention weights per pattern
            - blended_value: Synthesized config from foreign patterns
            - source_archetypes: Which archetypes contributed
    """
    # Check if E-AM is enabled
    if not settings.am.enable_eam:
        log("E-AM", "⚠️ E-AM disabled in config")
        return {"patterns": [], "blended_value": {}, "source_archetypes": []}
    
    try:
        from app.learning.v_vector_store import get_v_vector_store
        from app.arbormind.router import arbormind_attention, arbormind_blend
        
        store = get_v_vector_store()
        
        # Search for patterns, excluding current archetype
        candidates = await _search_foreign_patterns(
            store, error_text, archetype, limit * 3
        )
        
        if not candidates:
            log("E-AM", f"No foreign patterns found for: {error_text[:50]}...")
            return {"patterns": [], "blended_value": {}, "source_archetypes": []}
        
        # Deduplicate by archetype (keep highest scoring per archetype)
        unique_by_arch = {}
        for c in candidates:
            arch = c.get("archetype", "unknown")
            if arch != archetype:  # Exclude current archetype
                if arch not in unique_by_arch or c.get("score", 0) > unique_by_arch[arch].get("score", 0):
                    unique_by_arch[arch] = c
        
        selected = list(unique_by_arch.values())[:limit]
        
        if not selected:
            return {"patterns": [], "blended_value": {}, "source_archetypes": []}
        
        # Get embeddings for attention computation
        embeddings = [s.get("embedding", []) for s in selected if s.get("embedding")]
        values = [s.get("value", {}) for s in selected]
        
        if not embeddings:
            # No embeddings, just return patterns
            return {
                "patterns": selected,
                "weights": [1.0 / len(selected)] * len(selected),
                "blended_value": values[0] if values else {},
                "source_archetypes": list(unique_by_arch.keys()),
            }
        
        # Create query embedding for the error
        query_embedding = await _get_error_embedding(store, error_text)
        
        # Compute creative attention (combinational mode for blending)
        K = np.array(embeddings)
        att = arbormind_attention(query_embedding, K, values, mode="combinational")
        blended = arbormind_blend(att["weights"], values)
        
        source_archetypes = [s.get("archetype") for s in selected]
        
        log("E-AM", f"🔄 Injected {len(selected)} foreign patterns from: {source_archetypes}")
        
        return {
            "patterns": selected,
            "weights": att["weights"].tolist() if hasattr(att["weights"], "tolist") else list(att["weights"]),
            "blended_value": blended,
            "source_archetypes": source_archetypes,
            "entropy": att.get("entropy", 0),
        }
        
    except Exception as e:
        log("E-AM", f"⚠️ Error injecting foreign patterns: {e}")
        return {"patterns": [], "blended_value": {}, "source_archetypes": [], "error": str(e)}


async def _search_foreign_patterns(
    store,
    query: str,
    exclude_archetype: str,
    limit: int
) -> List[Dict]:
    """
    Search for patterns in the V-vector store, excluding current archetype.
    """
    try:
        # Try to use the store's search if available
        if hasattr(store, 'search_patterns'):
            return await store.search_patterns(
                query=query,
                exclude_archetype=exclude_archetype,
                limit=limit
            )
        
        # Fallback: Get anti-patterns and successful patterns
        store.get_anti_patterns_for_context(
            context_type="repair_strategy",
            archetype=exclude_archetype,
            limit=limit
        )
        
        # Return empty if no patterns found
        return []
        
    except Exception as e:
        log("E-AM", f"⚠️ Pattern search failed: {e}")
        return []


async def _get_error_embedding(store, error_text: str) -> np.ndarray:
    """Get embedding for error text."""
    try:
        from app.arbormind.router import get_embedding
        embedding = await get_embedding(error_text[:500])  # Limit length
        return np.array(embedding)
    except Exception:
        # Fallback to simple hash-based embedding
        import hashlib
        h = hashlib.sha256(error_text.encode()).digest()
        np.random.seed(int.from_bytes(h[:4], 'big'))
        return np.random.randn(768)


def select_best_foreign_pattern(
    patterns: List[Dict],
    weights: List[float],
    current_context: Dict
) -> Optional[Dict]:
    """
    Select the single best foreign pattern based on weights and compatibility.
    
    Args:
        patterns: List of foreign patterns
        weights: Attention weights
        current_context: Current problem context
        
    Returns:
        Best matching pattern or None
    """
    if not patterns:
        return None
    
    # Find pattern with highest weight
    best_idx = np.argmax(weights)
    return patterns[best_idx]


# ═══════════════════════════════════════════════════════
# FOREIGN PATTERN SOURCES
# ═══════════════════════════════════════════════════════

# Predefined foreign pattern sources for common errors
FOREIGN_PATTERN_HINTS = {
    "RecursionError": ["gaming", "data_processing", "compiler"],
    "MemoryError": ["data_dashboard", "ml_pipeline", "batch_processing"],
    "TimeoutError": ["realtime_collab", "streaming", "websocket"],
    "ImportError": ["plugin_system", "microservices", "monorepo"],
    "TypeError": ["typescript_frontend", "api_gateway", "serialization"],
    "ConnectionError": ["distributed_system", "microservices", "cloud_native"],
}


def get_archetype_hints_for_error(error_type: str) -> List[str]:
    """
    Get suggested archetypes that often have solutions for this error type.
    """
    return FOREIGN_PATTERN_HINTS.get(error_type, [])
