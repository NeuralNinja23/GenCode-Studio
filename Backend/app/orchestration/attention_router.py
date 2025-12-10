# app/orchestration/attention_router.py
"""
Attention-based routing for project classification using scaled dot-product attention.

This module implements the actual attention mechanism from transformer architecture:
    Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) * V

to route user requests to appropriate project archetypes and UI vibes.
"""
import math
import numpy as np
from typing import List, Dict, Optional
import aiohttp
import asyncio
from app.core.config import settings
from app.core.logging import log


# ═══════════════════════════════════════════════════════
# PROJECT ARCHETYPES - The canonical project patterns
# ═══════════════════════════════════════════════════════

PROJECT_ARCHETYPES = [
    {
        "id": "admin_dashboard",
        "description": "Internal admin dashboard with CRUD operations, data tables, charts and statistics for managing business data"
    },
    {
        "id": "saas_app",
        "description": "Multi-tenant SaaS application with user authentication, subscription management, billing and team collaboration features"
    },
    {
        "id": "content_platform",
        "description": "Blog, CMS or content publishing platform with post management, categories, tags and media library"
    },
    {
        "id": "landing_page",
        "description": "Marketing website or landing page for product showcase, lead generation with call-to-action forms"
    },
    {
        "id": "realtime_collab",
        "description": "Real-time collaboration tool with chat, messaging, whiteboard or collaborative editing features"
    },
    {
        "id": "ecommerce_store",
        "description": "E-commerce store with product catalog, shopping cart, checkout, inventory and order management"
    },
    {
        "id": "project_management",
        "description": "Project or task management system with boards, lists, assignments, timelines and team coordination"
    },
]


# ═══════════════════════════════════════════════════════
# UI VIBES - Design aesthetic patterns
# ═══════════════════════════════════════════════════════

UI_VIBES = [
    {
        "id": "dark_hacker",
        "description": "Dark background with neon accents, high contrast terminal-style UI, cyberpunk aesthetic with glow effects"
    },
    {
        "id": "minimal_light",
        "description": "Light clean background with lots of whitespace, subtle neutral colors, minimalist professional design"
    },
    {
        "id": "playful_colorful",
        "description": "Soft gradients, rounded shapes, vibrant playful colors, friendly and approachable design language"
    },
    {
        "id": "enterprise_neutral",
        "description": "Neutral blues and grays, serious corporate professional look, traditional business software aesthetic"
    },
    {
        "id": "modern_gradient",
        "description": "Bold color gradients, glassmorphism effects, modern web3 style with depth and layering"
    },
]


# ═══════════════════════════════════════════════════════
# EMBEDDING PROVIDER - Get text embeddings for attention
# ═══════════════════════════════════════════════════════

# FIX #7: Cache with size limit and TTL to prevent memory leak
from collections import OrderedDict
import time

_embedding_cache: OrderedDict[str, tuple[List[float], float]] = OrderedDict()
_CACHE_MAX_SIZE = 1000  # Maximum entries
_CACHE_TTL_SECONDS = 3600  # 1 hour TTL

# FIX #18: Shared HTTP session for connection pooling
_http_session: Optional[aiohttp.ClientSession] = None


async def _get_http_session() -> aiohttp.ClientSession:
    """Get or create shared HTTP session for connection pooling."""
    global _http_session
    if _http_session is None or _http_session.closed:
        timeout = aiohttp.ClientTimeout(total=30)
        _http_session = aiohttp.ClientSession(timeout=timeout)
    return _http_session


async def close_http_session() -> None:
    """Close the shared HTTP session. Call during app shutdown."""
    global _http_session
    if _http_session is not None and not _http_session.closed:
        await _http_session.close()
        _http_session = None


def _cache_get(key: str) -> Optional[List[float]]:
    """Get from cache if exists and not expired."""
    if key not in _embedding_cache:
        return None
    embedding, timestamp = _embedding_cache[key]
    if time.time() - timestamp > _CACHE_TTL_SECONDS:
        del _embedding_cache[key]
        return None
    # Move to end (LRU)
    _embedding_cache.move_to_end(key)
    return embedding


def _cache_set(key: str, value: List[float]) -> None:
    """Set cache with eviction if full."""
    # Evict oldest if at capacity
    while len(_embedding_cache) >= _CACHE_MAX_SIZE:
        _embedding_cache.popitem(last=False)
    _embedding_cache[key] = (value, time.time())


async def get_embedding(text: str) -> List[float]:
    """
    Get text embedding using the configured LLM provider.
    
    Currently supports:
    - Google Gemini (text-embedding-004)
    - OpenAI (text-embedding-3-small)
    
    Returns:
        List of floats representing the embedding vector
        
    Raises:
        Exception if embedding generation fails
    """
    # Check cache first (with TTL)
    cached = _cache_get(text)
    if cached is not None:
        return cached
    
    provider = settings.llm.default_provider
    
    try:
        if provider == "gemini":
            embedding = await _get_gemini_embedding(text)
        elif provider == "openai":
            embedding = await _get_openai_embedding(text)
        else:
            # Fallback: Use simple hash-based embedding (not recommended for production)
            log("ATTENTION_ROUTER", f"Provider '{provider}' doesn't support embeddings, using fallback")
            embedding = _get_fallback_embedding(text)
        
        # Cache the result (with size limit)
        _cache_set(text, embedding)
        return embedding
        
    except Exception as e:
        log("ATTENTION_ROUTER", f"Embedding failed: {e}, using fallback")
        return _get_fallback_embedding(text)


async def _get_gemini_embedding(text: str) -> List[float]:
    """Get embedding from Google Gemini API."""
    api_key = settings.llm.gemini_api_key
    if not api_key:
        raise Exception("GEMINI_API_KEY not configured for embeddings")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={api_key}"
    
    payload = {
        "model": "models/text-embedding-004",
        "content": {
            "parts": [{"text": text}]
        }
    }
    
    # FIX #18: Use shared session for connection pooling
    session = await _get_http_session()
    async with session.post(url, json=payload) as response:
        if response.status != 200:
            error_text = await response.text()
            raise Exception(f"Gemini embedding API error {response.status}: {error_text[:200]}")
        
        data = await response.json()
        embedding = data.get("embedding", {}).get("values", [])
        
        if not embedding:
            raise Exception("No embedding values in Gemini response")
        
        return embedding


async def _get_openai_embedding(text: str) -> List[float]:
    """Get embedding from OpenAI API."""
    api_key = settings.llm.openai_api_key
    if not api_key:
        raise Exception("OPENAI_API_KEY not configured for embeddings")
    
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "text-embedding-3-small",
        "input": text
    }
    
    # FIX #18: Use shared session for connection pooling
    session = await _get_http_session()
    async with session.post(url, json=payload, headers=headers) as response:
        if response.status != 200:
            error_text = await response.text()
            raise Exception(f"OpenAI embedding API error {response.status}: {error_text[:200]}")
        
        data = await response.json()
        embedding = data.get("data", [{}])[0].get("embedding", [])
        
        if not embedding:
            raise Exception("No embedding in OpenAI response")
        
        return embedding


def _get_fallback_embedding(text: str, dim: int = 768) -> List[float]:
    """
    Fallback embedding using simple hash-based approach.
    NOT recommended for production - just ensures the system doesn't crash.
    """
    import hashlib
    
    # Create a deterministic "embedding" from text hash
    text_hash = hashlib.sha256(text.encode()).digest()
    
    # Expand to desired dimension
    np.random.seed(int.from_bytes(text_hash[:4], 'big'))
    embedding = np.random.randn(dim).tolist()
    
    return embedding


# ═══════════════════════════════════════════════════════
# SCALED DOT-PRODUCT ATTENTION (The real transformer equation)
# ═══════════════════════════════════════════════════════

def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """
    Numerically stable softmax implementation.
    
    Args:
        x: Input array
        axis: Axis along which to compute softmax
        
    Returns:
        Softmax probabilities
    """
    # Subtract max for numerical stability
    x = x - np.max(x, axis=axis, keepdims=True)
    exp_x = np.exp(x)
    return exp_x / np.sum(exp_x, axis=axis, keepdims=True)


def scaled_dot_product_attention(
    Q: np.ndarray,
    K: np.ndarray,
    V: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute scaled dot-product attention.
    
    This is the core attention mechanism from "Attention is All You Need":
        Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) * V
    
    Where:
        - Q: Query vectors (what we're searching for)
        - K: Key vectors (what we're searching in)
        - V: Value vectors (what we return)
        - d_k: Dimension of key vectors (for scaling)
    
    Args:
        Q: Query matrix of shape (n_queries, d_k)
        K: Key matrix of shape (n_keys, d_k)
        V: Value matrix of shape (n_keys, d_v)
        
    Returns:
        Tuple of:
            - Attention output of shape (n_queries, d_v)
            - Attention weights of shape (n_queries, n_keys)
    """
    # Get the dimension of keys for scaling
    d_k = K.shape[-1]
    
    # Compute attention scores: QK^T / sqrt(d_k)
    # This measures similarity between query and each key
    scores = (Q @ K.T) / math.sqrt(d_k)
    
    # Apply softmax to get attention weights (probabilities)
    weights = softmax(scores, axis=-1)
    
    # Apply attention weights to values
    output = weights @ V
    
    return output, weights


# ═══════════════════════════════════════════════════════
# ROUTING FUNCTIONS - Apply attention to classify requests
# ═══════════════════════════════════════════════════════

async def _route(text: str, options: List[Dict]) -> Dict:
    """
    Route a text query to the most relevant option using attention.
    
    Args:
        text: User's request text (the query)
        options: List of option dicts with 'id' and 'description' keys
        
    Returns:
        Dict with:
            - top: ID of the highest-scoring option
            - weights: List of all options ranked by score
    """
    # Get query embedding (Q)
    try:
        q_embedding = await get_embedding(text)
        q = np.array(q_embedding, dtype=np.float32)[None, :]  # Shape: (1, d)
    except Exception as e:
        log("ATTENTION_ROUTER", f"Failed to get query embedding: {e}")
        # Return first option as fallback
        return {
            "top": options[0]["id"] if options else None,
            "weights": [{"id": opt["id"], "weight": 1.0 / len(options)} for opt in options]
        }
    
    # Get key embeddings (K) for all option descriptions
    try:
        description_embeddings = await asyncio.gather(
            *[get_embedding(opt["description"]) for opt in options]
        )
        K = np.vstack([np.array(emb, dtype=np.float32) for emb in description_embeddings])
        V = K  # In this case, values are the same as keys
    except Exception as e:
        log("ATTENTION_ROUTER", f"Failed to get option embeddings: {e}")
        return {
            "top": options[0]["id"] if options else None,
            "weights": [{"id": opt["id"], "weight": 1.0 / len(options)} for opt in options]
        }
    
    # Apply scaled dot-product attention
    _, attention_weights = scaled_dot_product_attention(q, K, V)
    weights = attention_weights[0]  # Shape: (n_options,)
    
    # Rank options by attention weight
    sorted_indices = np.argsort(weights)[::-1]  # Descending order
    
    ranked = [
        {
            "id": options[i]["id"],
            "weight": float(weights[i]),
            "description": options[i]["description"]
        }
        for i in sorted_indices
    ]
    
    top_choice = ranked[0]["id"] if ranked else None
    
    log("ATTENTION_ROUTER", f"Routed to '{top_choice}' with weight {ranked[0]['weight']:.3f}")
    
    return {
        "top": top_choice,
        "weights": ranked
    }


async def compute_archetype_routing(user_request: str) -> Dict:
    """
    Route user request to the most fitting project archetype using attention.
    
    Args:
        user_request: The user's project description
        
    Returns:
        Dict with 'top' archetype ID and ranked 'weights'
    """
    log("ATTENTION_ROUTER", f"Computing archetype for: '{user_request[:50]}...'")
    return await _route(user_request, PROJECT_ARCHETYPES)


async def compute_ui_vibe_routing(user_request: str) -> Dict:
    """
    Route user request to the most fitting UI vibe using attention.
    
    Args:
        user_request: The user's project description
        
    Returns:
        Dict with 'top' vibe ID and ranked 'weights'
    """
    log("ATTENTION_ROUTER", f"Computing UI vibe for: '{user_request[:50]}...'")
    return await _route(user_request, UI_VIBES)
