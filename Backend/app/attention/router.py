# app/attention/router.py
"""
Attention-based routing for project classification using scaled dot-product attention.

This module implements the actual attention mechanism from transformer architecture:
    Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) * V

to route user requests to appropriate project archetypes and UI vibes.

ARBORMIND (AM) EXTENSION:
- C-AM (Combinational): Blend multiple archetypes using soft attention
- E-AM (Exploratory): Inject foreign patterns when stuck
- T-AM (Transformational): Mutate constraints when fundamentally blocked
"""
import math
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import aiohttp
import asyncio
from app.core.config import settings
from app.core.logging import log


# ═══════════════════════════════════════════════════════
# AM CONFIGURATION - ArborMind Operators
# ═══════════════════════════════════════════════════════

class AMMode(Enum):
    """ArborMind operating modes."""
    STANDARD = "standard"          # Sharp routing (winner-takes-all)
    COMBINATIONAL = "combinational"  # C-AM: Multi-source blending
    EXPLORATORY = "exploratory"      # E-AM: Foreign pattern injection
    TRANSFORMATIONAL = "transformational"  # T-AM: Constraint mutation

# Backward compatibility alias
UoTMode = AMMode

# AM Scale Constants
DEFAULT_SCALE_STANDARD = 20.0       # Sharp decisions (winner-takes-all)
DEFAULT_SCALE_COMBINATIONAL = 2.0   # Soft decisions (multi-source blending)
EPS = 1e-12                          # Epsilon for numerical stability

# AM Entropy Thresholds
ENTROPY_HIGH_THRESHOLD = 1.5        # Above this = consider combinational mode
ENTROPY_LOW_THRESHOLD = 0.5         # Below this = confident single selection

# Self-Evolution Layer Integration
_evolution_enabled = True  # Feature flag for gradual rollout


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

# FIX #7: Cache with Persistent Storage (Phase 4.1)
from collections import OrderedDict
import time
import json
from pathlib import Path

_embedding_cache: OrderedDict[str, tuple[List[float], float]] = OrderedDict()
_CACHE_MAX_SIZE = 5000  # Increased size
_CACHE_TTL_SECONDS = 86400 * 30  # 30 days TTL (embeddings don't rot quickly)

# Persistent storage path
_CACHE_FILE = Path(__file__).parent.parent.parent / "data" / "embeddings.json"

def _load_persistent_cache():
    """Load embeddings from disk on startup."""
    global _embedding_cache
    if _CACHE_FILE.exists():
        try:
            data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            # Convert simple dict to complex cache structure with timestamp
            current_time = time.time()
            for k, v in data.items():
                _embedding_cache[k] = (v, current_time)
            log("ATTENTION_ROUTER", f"Loaded {len(_embedding_cache)} embeddings from disk")
        except Exception as e:
            log("ATTENTION_ROUTER", f"Failed to load embedding cache: {e}")

def _save_persistent_cache_entry(key: str, value: List[float]):
    """Append a single entry to disk (simple append-only log or rewrite)."""
    # For simplicity/safety in async, we'll just queue specific writes or write periodically.
    # But to be safe and simple: We will just write the file when we get a NEW embedding.
    # This might be slow if we get 1000s at once, but for tools/archetypes it's rare.
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Read current (to merge) or just dump full memory cache?
        # Dumping full memory cache is safest to keep sync
        export_data = {k: v[0] for k, v in _embedding_cache.items()}
        
        # Write atomically
        temp_file = _CACHE_FILE.with_suffix(".tmp")
        temp_file.write_text(json.dumps(export_data), encoding="utf-8")
        if _CACHE_FILE.exists():
            _CACHE_FILE.unlink()
        temp_file.rename(_CACHE_FILE)
    except Exception as e:
         log("ATTENTION_ROUTER", f"Failed to save embedding cache: {e}")

# FIX #18: Shared HTTP session for connection pooling
_http_session: Optional[aiohttp.ClientSession] = None


async def _get_http_session() -> aiohttp.ClientSession:
    """Get or create shared HTTP session for connection pooling."""
    global _http_session
    if _http_session is None or _http_session.closed:
        timeout = aiohttp.ClientTimeout(total=30)
        _http_session = aiohttp.ClientSession(timeout=timeout)
        # Load cache on first network use
        _load_persistent_cache()
    return _http_session


async def close_http_session() -> None:
    """Close the shared HTTP session. Call during app shutdown."""
    global _http_session
    if _http_session is not None and not _http_session.closed:
        await _http_session.close()
        _http_session = None


def _cache_get(key: str) -> Optional[List[float]]:
    """Get from cache if exists."""
    if key not in _embedding_cache:
        return None
    embedding, _ = _embedding_cache[key]
    # Move to end (LRU)
    _embedding_cache.move_to_end(key)
    return embedding


def _cache_set(key: str, value: List[float]) -> None:
    """Set cache and persist."""
    # Evict oldest if at capacity
    while len(_embedding_cache) >= _CACHE_MAX_SIZE:
        _embedding_cache.popitem(last=False)
    _embedding_cache[key] = (value, time.time())
    
    # Persist to disk (Phase 4.1)
    _save_persistent_cache_entry(key, value)


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
    
    # Scale factor for Unit Vectors (OpenAI/Gemini embeddings are normalized).
    # Standard 1/sqrt(d_k) makes scores too small (~0.02) leading to flat attention.
    # We multiply by 20.0 to sharpen the distribution (Temperature ~ 0.05).
    scores = (Q @ K.T) * 20.0
    
    # Apply softmax to get attention weights (probabilities)
    weights = softmax(scores, axis=-1)
    
    # Apply attention weights to values
    output = weights @ V
    
    return output, weights


# ═══════════════════════════════════════════════════════
# AM: CREATIVE ATTENTION (C-AM FOUNDATION)
# ═══════════════════════════════════════════════════════

def _l2_normalize(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """L2 normalize vectors along specified axis."""
    norm = np.linalg.norm(x, axis=axis, keepdims=True)
    return x / np.maximum(norm, EPS)


def _softmax_am(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """Numerically stable softmax for AM operations."""
    x_max = np.max(x, axis=axis, keepdims=True)
    e = np.exp(x - x_max)
    return e / np.sum(e, axis=axis, keepdims=True)

# Backward compatibility alias
_softmax_uot = _softmax_am


def creative_attention(
    Q: np.ndarray,
    K: np.ndarray,
    V: List[Dict[str, Any]] = None,
    mode: str = "standard",
    scale_standard: float = DEFAULT_SCALE_STANDARD,
    scale_combinational: float = DEFAULT_SCALE_COMBINATIONAL
) -> Dict[str, Any]:
    """
    Universal Attention operator supporting AM creative modes.
    
    MODES:
    - "standard": Sharp decisions (winner-takes-all, temperature ~0.05)
    - "combinational": Soft decisions (multi-source blending, temperature ~0.5)
    
    The key innovation is the ENTROPY score which indicates when
    a query spans multiple domains and combinational blending is beneficial.
    
    Args:
        Q: Query vector(s) - shape (d_k,) or (1, d_k)
        K: Key matrix - shape (n_options, d_k)
        V: Optional list of value dicts for synthesis
        mode: "standard" or "combinational"
        scale_standard: Temperature scale for sharp routing
        scale_combinational: Temperature scale for soft blending
        
    Returns:
        Dict containing:
            - weights: Attention weights per option
            - scores: Raw similarity scores
            - entropy: Distribution entropy (high = multi-domain)
            - logits: Scaled scores before softmax
            - mode: The mode used
    """
    # Normalize inputs
    Qn = _l2_normalize(np.array(Q, dtype=float).reshape(1, -1))
    Kn = _l2_normalize(np.array(K, dtype=float))
    
    # Compute similarity scores
    scores = (Qn @ Kn.T).reshape(-1)
    
    # Select scale based on mode
    scale = scale_standard if mode == "standard" else scale_combinational
    
    # Apply temperature scaling
    logits = scores * scale
    weights = _softmax_am(logits)
    
    # Compute entropy (for AM mode detection)
    # High entropy = query relevant to multiple options = use combinational
    entropy = -np.sum(weights * np.log(weights + EPS))
    
    result = {
        "weights": weights,
        "scores": scores,
        "entropy": float(entropy),
        "logits": logits,
        "mode": mode,
    }
    
    # If V-values provided, compute blended output
    if V is not None:
        result["blended_value"] = blend_values(weights, V)
    
    return result


def blend_values(weights: np.ndarray, values: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Domain-general V-value synthesis for AM.
    
    Blends multiple value dictionaries based on attention weights.
    Handles:
    - Numeric fields: Weighted average
    - Boolean/String fields: Winner-takes-all (highest weight)
    - Missing keys: Graceful handling
    - Nested dicts: Shallow merge
    
    Args:
        weights: Attention weights per value dict
        values: List of value dictionaries to blend
        
    Returns:
        Blended value dictionary
    """
    if not values:
        return {}
    
    weights = np.array(weights, dtype=float)
    
    # Collect all keys from all value dicts
    keys = set()
    for v in values:
        if isinstance(v, dict):
            keys.update(v.keys())
    
    output = {}
    for k in keys:
        # Extract values for this key from all dicts
        vals = [v.get(k) if isinstance(v, dict) else None for v in values]
        
        # Check if all non-None values are numeric
        non_none_vals = [x for x in vals if x is not None]
        
        if all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in non_none_vals):
            # Numeric blend: weighted average
            nums = np.array([float(x or 0) for x in vals])
            output[k] = float(np.dot(weights, nums))
        else:
            # Non-numeric: winner-takes-all (highest weight)
            idx = int(np.argmax(weights))
            output[k] = vals[idx]
    
    return output


def should_use_combinational_mode(entropy: float) -> bool:
    """
    Determine if combinational mode should be used based on entropy.
    
    High entropy indicates the query is relevant to multiple domains,
    suggesting that blending multiple archetypes would be beneficial.
    """
    threshold = getattr(settings, "uot", None) and settings.uot.entropy_high or ENTROPY_HIGH_THRESHOLD
    return entropy > threshold


# ═══════════════════════════════════════════════════════
# ROUTING FUNCTIONS - Apply attention to classify requests
# ═══════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════
# UNIVERSAL ATTENTION ROUTER (CORE SERVICE)
# ═══════════════════════════════════════════════════════

class AttentionRouter:
    """
    Universal Service for Attention-Based Decision Making.
    
    Implements the "Attention is All You Need" mechanism:
        Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) * V
    
    to route ANY query to the best matching options.
    
    SELF-EVOLVING: Now integrates with the Evolution Layer to:
    1. Apply learned V-vector adjustments before routing
    2. Track decisions for future learning
    """
    
    def __init__(self):
        # We use module-level caching for now, could be instance-based later
        self._evolution_manager = None
    
    def _get_evolution_manager(self):
        """Lazy load evolution manager to avoid circular imports."""
        if self._evolution_manager is None and _evolution_enabled:
            try:
                from app.attention.evolution import get_evolution_manager
                self._evolution_manager = get_evolution_manager()
            except ImportError:
                log("ATTENTION_ROUTER", "⚠️ Evolution module not available")
        return self._evolution_manager

    async def route(
        self,
        query: str,
        options: List[Dict],
        top_k: int = 5,
        min_conf: float = 0.05,
        context_type: str = "general",
        archetype: str = "unknown"
    ) -> Dict:
        """
        Route a query to the best matching options using Global Attention.
        
        Args:
            query: The input text (user request, error log, etc.)
            options: List of dicts with keys 'id' and 'description'
            top_k: Number of top results to return
            min_conf: Minimum confidence threshold to include in results
            
        Returns:
            Dict containing:
                - selected: The best matching option ID
                - confidence: Score of the best match
                - ranked: List of matches with scores and details
                - reasoning: Why this was chosen
        """
        if not options:
            return {"selected": None, "confidence": 0.0, "ranked": [], "reasoning": "No options provided", "decision_id": ""}

        # ═══════════════════════════════════════════════════════
        # SELF-EVOLUTION STEP 1: Evolve options before routing
        # ═══════════════════════════════════════════════════════
        evolved_options = options
        evolution_mgr = self._get_evolution_manager()
        if evolution_mgr:
            try:
                evolved_options = evolution_mgr.evolve_options(
                    context_type=context_type,
                    archetype=archetype,
                    options=options,
                    enhance_from_patterns=True
                )
                log("ATTENTION_ROUTER", f"🧬 Applied evolution to {len(evolved_options)} options")
            except Exception as e:
                log("ATTENTION_ROUTER", f"⚠️ Evolution failed, using static options: {e}")
                evolved_options = options

        # 1. Compute Query Embedding (Q)
        try:
            q_embedding = await get_embedding(query)
            Q = np.array(q_embedding, dtype=np.float32)[None, :]  # Shape: (1, d)
        except Exception as e:
            log("ATTENTION_ROUTER", f"⚠️ Failed to embed query: {e}")
            # Fallback: Random/First choice
            return self._fallback_response(evolved_options, "Embedding failure")

        # 2. Compute Key Embeddings (K)
        # Check if options already have embeddings, else fetch them
        try:
            # Optimization: If an option has 'embedding', use it. Else fetch.
            tasks = []
            for opt in evolved_options:
                if "embedding" in opt and opt["embedding"]:
                    tasks.append(asyncio.sleep(0, result=opt["embedding"])) # Already have it
                else:
                    tasks.append(get_embedding(opt.get("description", opt.get("id", ""))))
            
            description_embeddings = await asyncio.gather(*tasks)
            
            K = np.vstack([np.array(emb, dtype=np.float32) for emb in description_embeddings])
            V = K  # Values are the same as Keys in this context (identity)
            
        except Exception as e:
            log("ATTENTION_ROUTER", f"⚠️ Failed to embed options: {e}")
            return self._fallback_response(evolved_options, "Option embedding failure")

        # 3. Apply Creative Attention (C-AM)
        # -------------------------------------------------------------
        # Use creative_attention which supports:
        # - Standard mode (sharp routing)
        # - Combinational mode (blending) based on entropy
        
        # We need V as list of dicts for blending, but here V matches K for attention scores
        # The blending happens later (Step 6), but we need the weights and ENTROPY now.
        
        # Prepare V-values for creative_attention if available (used for mode decision implicitly)
        V_dicts = [opt.get("value", {}) for opt in evolved_options]
        
        
        # Determine initial mode from settings
        use_combinational = False
        if context_type in ["behavior_synthesis", "creative_generation"]:
            use_combinational = True
            
        # Call Creative Attention
        att_result = creative_attention(
            Q, K, V_dicts, 
            mode="combinational" if use_combinational else "standard"
        )
        
        weights = att_result["weights"]  # Shape: (n_options,)
        entropy = att_result["entropy"]
        
        # HYBRID SWITCH: If entropy is high and we are in standard mode, 
        # we might want to flag this or switch to combinational for the blending step.
        if should_use_combinational_mode(entropy) and settings.am.enable_cam:
             # If we were in standard, but entropy is high, the query is ambiguous/multifaceted.
             # We re-run in combinational mode OR just use the weights (if they are soft enough).
             # Standard mode scale=20 makes weights sharp (one-hot-ish).
             # Combinational mode scale=2 makes weights soft.
             
             # If we want true blending, we need soft weights.
             if not use_combinational:
                  # Rerun with soft scale
                  att_result = creative_attention(Q, K, V_dicts, mode="combinational")
                  weights = att_result["weights"]
                  log("ATTENTION_ROUTER", f"✨ Auto-switched to Combinational Mode (Entropy: {entropy:.2f})")


        # 4. Rank and Filter
        sorted_indices = np.argsort(weights)[::-1]  # Descending
        
        ranked_results = []
        for i in sorted_indices:
            score = float(weights[i])
            if score < min_conf and len(ranked_results) >= 1:
                continue # Skip low confidence tail if we have at least one match
                
            opt = evolved_options[i]
            ranked_results.append({
                "id": opt["id"],
                "score": score,
                "description": opt.get("description", ""),
                "value": opt.get("value", {}), # Pass through the (possibly evolved) value
                "evolved": opt.get("_evolved", False),  # Flag if this was evolved
                "metadata": {k:v for k,v in opt.items() if k not in ["id", "description", "embedding", "value", "_evolved", "_evolution_meta", "_warning", "_warning_meta"]}
            })
            
            if len(ranked_results) >= top_k:
                break
        
        # 5. Select Best
        best_match = ranked_results[0] if ranked_results else None
        selected_id = best_match["id"] if best_match else None
        confidence = best_match["score"] if best_match else 0.0
        
        # 6. V != K: SYNTHESIZE BEHAVIOR (Behavioral Interpolation)
        # We blend the "value" objects of all options based on their attention weights
        synthesized_value = {}
        
        if params_present := [opt.get("value", {}) for opt in evolved_options if opt.get("value")]:
            # Identify all possible keys
            all_keys = set().union(*params_present)
            
            # For "soft" blending, we use the raw softmax weights (before truncation)
            # normalized to sum to 1.0 (softmax already does this, but filtered lists might not)
            
            for key in all_keys:
                weighted_sum = 0.0
                max_weight = -1.0
                best_val = None
                is_numeric = True
                
                for i, opt in enumerate(evolved_options):
                    val = opt.get("value", {}).get(key)
                    if val is None: continue
                    
                    w = float(weights[i])
                    
                    # Track winner-takes-all candidate
                    if w > max_weight:
                        max_weight = w
                        best_val = val
                    
                    # Track weighted sum for numerics
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        weighted_sum += val * w
                    else:
                        is_numeric = False
                
                # Assign final blended value
                if is_numeric:
                    synthesized_value[key] = weighted_sum
                else:
                    synthesized_value[key] = best_val

        # 7. Visualize / Log
        self._log_decision(query, ranked_results, synthesized_value)
        
        # ═══════════════════════════════════════════════════════
        # SELF-EVOLUTION STEP 2: Track decision for learning
        # ═══════════════════════════════════════════════════════
        decision_id = ""
        if evolution_mgr and selected_id:
            try:
                attention_weights_dict = {
                    evolved_options[i]["id"]: float(weights[i]) 
                    for i in range(len(evolved_options))
                }
                decision_id = evolution_mgr.start_tracking(
                    query=query,
                    context_type=context_type,
                    archetype=archetype,
                    selected_option=selected_id,
                    synthesized_value=synthesized_value,
                    attention_weights=attention_weights_dict
                )
            except Exception as e:
                log("ATTENTION_ROUTER", f"⚠️ Failed to track decision: {e}")
        
        return {
            "selected": selected_id,
            "confidence": confidence,
            "ranked": ranked_results,
            "value": synthesized_value, # <--- THE BEHAVIOR OUTPUT (possibly evolved)
            "reasoning": f"Matched '{query[:50]}...' to '{selected_id}' with {confidence:.2%} confidence.",
            "decision_id": decision_id,  # <--- For outcome tracking
            "evolved": any(r.get("evolved") for r in ranked_results)  # <--- Evolution applied flag
        }

    def _fallback_response(self, options: List[Dict], reason: str) -> Dict:
        """Return a safe fallback response."""
        # Fallback value is just the first option's value
        fallback_val = options[0].get("value", {}) if options else {}
        return {
            "selected": options[0]["id"] if options else None,
            "confidence": 0.0,
            "ranked": [{"id": o["id"], "score": 0.0} for o in options],
            "value": fallback_val,
            "reasoning": f"Fallback: {reason}"
        }

    def _log_decision(self, query: str, ranked: List[Dict], value: Dict):
        """Visual logging of the attention distribution and parameters."""
        log("ATTENTION_ROUTER", f"🤖 Routing '{query[:30]}...' (Behavior Synthesis)")
        for r in ranked[:3]: # Show top 3
            bar = "█" * int(r["score"] * 20)
            log("ATTENTION_ROUTER", f"   {bar} {r['score']:.4f} -> {r['id']}")
        
        if value:
            # Show the synthesized parameters
            params_str = ", ".join([f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}" for k,v in value.items()])
            log("ATTENTION_ROUTER", f"   ⚙️ Params: {{{params_str}}}")
        
        if ranked:
            log("ATTENTION_ROUTER", f"✅ Selected: {ranked[0]['id']}")



# Global Instance
_global_router = AttentionRouter()


# ═══════════════════════════════════════════════════════
# LEGACY WRAPPERS (Preserving existing API)
# ═══════════════════════════════════════════════════════

async def compute_archetype_routing(user_request: str) -> Dict:
    """Route to project archetype using the Universal Router."""
    log("ATTENTION_ROUTER", f"Computing archetype for: '{user_request[:50]}...'")
    result = await _global_router.route(
        query=user_request,
        options=PROJECT_ARCHETYPES,
        top_k=5
    )
    
    # Map back to old return format for compatibility
    return {
        "top": result["selected"],
        "weights": [{"id": r["id"], "weight": r["score"], "description": r["description"]} for r in result["ranked"]]
    }


async def compute_ui_vibe_routing(user_request: str) -> Dict:
    """Route to UI vibe using the Universal Router."""
    log("ATTENTION_ROUTER", f"Computing UI vibe for: '{user_request[:50]}...'")
    result = await _global_router.route(
        query=user_request,
        options=UI_VIBES,
        top_k=5
    )
    
    return {
        "top": result["selected"],
        "weights": [{"id": r["id"], "weight": r["score"], "description": r["description"]} for r in result["ranked"]]
    }


# Helper for external usage
async def route_query(
    query: str, 
    options: List[Dict], 
    top_k: int = 5,
    context_type: str = "general",
    archetype: str = "unknown"
) -> Dict:
    """
    Public helper to use the router easily.
    
    Args:
        query: The query to route
        options: List of options with 'id', 'description', and 'value' keys
        top_k: Number of top results to return
        context_type: For self-evolution tracking (e.g., 'tool_selection', 'supervisor_policy')
        archetype: Project archetype for context-aware evolution
        
    Returns:
        Dict with 'selected', 'confidence', 'ranked', 'value', 'decision_id', 'evolved'
    """
    return await _global_router.route(
        query, 
        options, 
        top_k=top_k,
        context_type=context_type,
        archetype=archetype
    )

