# app/orchestration/token_policy.py
"""
Step-specific token allocation policies.

════════════════════════════════════════════════════════════════════════════════
ARCHITECTURAL INVARIANT: Hard Token Caps
════════════════════════════════════════════════════════════════════════════════

CAUSAL STEPS:
- max_tokens is a HARD CAP, not a suggestion
- NO retry_tokens (causal steps don't retry - they fail or succeed)
- If agent can't fit in the cap → step FAILS
- Output must be concise and complete

EVIDENCE STEPS:
- Can have retry_tokens for infrastructure failures
- May retry on environment issues, NOT on code issues

This prevents:
- Stochastic truncation (unlimited tokens = random cutoff)
- Token waste on doomed generations
- Hidden costs from healing/retry loops
════════════════════════════════════════════════════════════════════════════════
"""

# ═══════════════════════════════════════════════════════
# STEP CLASSIFICATION (Canonical source of truth)
# ═══════════════════════════════════════════════════════

CAUSAL_STEPS = {
    "architecture", 
    "backend_models",
    "backend_routers",
    "frontend_mock",
    "system_integration",
    }

EVIDENCE_STEPS = {
    "testing_backend",
    "testing_frontend",
    "preview_final",
}

# ═══════════════════════════════════════════════════════
# STEP-SPECIFIC TOKEN BUDGETS (HARD CAPS)
# ═══════════════════════════════════════════════════════

STEP_TOKEN_POLICIES = {
    # ───────────────────────────────────────────────────
    # CAUSAL STEPS: STRICT LIMITS, NO RETRY
    # ───────────────────────────────────────────────────
    
    "architecture": {
        "max_tokens": 8000,       # Architecture plan with UI design system (increased to avoid truncation)
        "retry_tokens": None,     # CAUSAL: No retry
        "description": "Architecture planning and UI design system",
        "is_causal": True,
    },
    
    "backend_models": {
        "max_tokens": 8000,       # models.py with multiple entities - needs larger budget
        "retry_tokens": None,     # CAUSAL: No retry
        "description": "Database models (Beanie Documents)",
        "is_causal": True,
    },
    
    "backend_routers": {
        "max_tokens": 12000,      # Multiple routers with full CRUD - INCREASED to prevent truncation
        "retry_tokens": None,     # CAUSAL: No retry  
        "description": "API routers with CRUD operations",
        "is_causal": True,
    },
    
    "frontend_mock": {
        "max_tokens": 12000,      # Frontend components need more tokens - INCREASED
        "retry_tokens": None,     # CAUSAL: No retry
        "description": "Frontend page/component with mock data",
        "is_causal": True,
    },
    
    "system_integration": {
        "max_tokens": 6000,       # Wire up routers in main.py - INCREASED from 3000
        "retry_tokens": None,     # CAUSAL: No retry
        "description": "System integration (main.py only)",
        "is_causal": True,
    },
    
    # ───────────────────────────────────────────────────
    # EVIDENCE STEPS: Can have retry for infra issues
    # ───────────────────────────────────────────────────
    "testing_backend": {
        "max_tokens": 12000,      # Test generation + execution - INCREASED from 6000
        "retry_tokens": 14000,    # EVIDENCE: Can retry on infra failure
        "description": "Backend testing with pytest",
        "is_causal": False,
    },
    
    "testing_frontend": {
        "max_tokens": 10000,      # E2E test generation - complete test file with HDAP markers
        "retry_tokens": 12000,    # EVIDENCE: Can retry on infra failure
        "description": "Frontend E2E testing - OBSERVATION ONLY",
        "is_causal": False,
    },
    
    "preview_final": {
        "max_tokens": 4000,       # Final preview summary - INCREASED from 2000
        "retry_tokens": 5000,     # EVIDENCE: Can retry on infra failure
        "description": "Final preview and summary",
        "is_causal": False,
    },
    
    "refine": {
        "max_tokens": 2500,       # Single file refinement
        "retry_tokens": None,     # Treated as causal (modifies code)
        "description": "Post-workflow refinements - ONE FILE",
        "is_causal": True,
    },
    
    "complete": {
        "max_tokens": 1500,       # Summary only
        "retry_tokens": None,     # No retry needed
        "description": "Workflow completion summary",
        "is_causal": False,
    },
}


# ═══════════════════════════════════════════════════════
# DEFAULT FALLBACK (Conservative for unknown steps)
# ═══════════════════════════════════════════════════════

DEFAULT_FALLBACK_TOKENS = 2000   # Conservative default
DEFAULT_RETRY_TOKENS = None      # Unknown steps don't retry


# ═══════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════

def get_tokens_for_step(step_name: str, is_retry: bool = False) -> int:
    """
    Get appropriate token allocation for a workflow step.
    
    Args:
        step_name: Workflow step identifier (e.g., "backend_implementation")
        is_retry: Whether this is a retry attempt (gets more tokens)
    
    Returns:
        Token limit for this step
    
    Example:
        >>> get_tokens_for_step("backend_implementation", is_retry=False)
        20000
        >>> get_tokens_for_step("backend_implementation", is_retry=True)
        24000
        >>> get_tokens_for_step("analysis", is_retry=False)
        8000
    """
    # Step name aliases - map human-readable names to policy keys
    # This handles both space-separated AND underscore-separated versions
    STEP_ALIASES = {
        # Frontend Mock variations (from different sources)
        "frontend (mock data)": "frontend_mock",
        "frontend mock": "frontend_mock",
        "frontend mock data": "frontend_mock",
        "frontend_mock_data": "frontend_mock",  # From supervisor.py step_id transform
        
        # Backend variations
        "backend implementation": "backend_routers",
        "backend vertical": "backend_routers",
        
        # Testing variations
        "testing backend": "testing_backend",
        "testing frontend": "testing_frontend",
        "backend test diagnosis": "testing_backend",
        "backend_test_diagnosis": "testing_backend",
        "backend testing fix": "testing_backend",
        "backend_testing_fix": "testing_backend",
        "test_file_generation": "testing_backend",
        "test file generation": "testing_backend",
        "e2e_test_generation": "testing_frontend",
        "e2e test generation": "testing_frontend",
        
        # Integration variations
        "system integration": "system_integration",
    }
    
    # Normalize step name (remove extra spaces, lowercase)
    normalized_step = step_name.lower().strip()
    
    # Check aliases first
    if normalized_step in STEP_ALIASES:
        normalized_step = STEP_ALIASES[normalized_step]
    else:
        # Fallback: replace spaces with underscores and remove parentheses
        normalized_step = normalized_step.replace(" ", "_").replace("(", "").replace(")", "")
    
    # Look up policy
    policy = STEP_TOKEN_POLICIES.get(normalized_step)
    
    if policy:
        return policy["retry_tokens"] if is_retry else policy["max_tokens"]
    
    # Fallback for unknown steps
    return DEFAULT_RETRY_TOKENS if is_retry else DEFAULT_FALLBACK_TOKENS


def get_step_description(step_name: str) -> str:
    """Get human-readable description of a workflow step."""
    normalized_step = step_name.lower().replace(" ", "_").strip()
    policy = STEP_TOKEN_POLICIES.get(normalized_step)
    return policy.get("description", "Unknown step") if policy else "Unknown step"


def get_all_policies() -> dict:
    """Get all token policies (for debugging/monitoring)."""
    return STEP_TOKEN_POLICIES.copy()


# ═══════════════════════════════════════════════════════
# BACKWARDS COMPATIBILITY
# ═══════════════════════════════════════════════════════

# For code that still uses DEFAULT_MAX_TOKENS, provide sensible defaults
DEFAULT_MAX_TOKENS = DEFAULT_FALLBACK_TOKENS
TEST_FILE_MIN_TOKENS = 12000  # For test generation (pytest/playwright)


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPERATURE MANAGEMENT (Lower = Consistent, Higher = Creative)
# ═══════════════════════════════════════════════════════════════════════════════

STEP_TEMPERATURES = {
    # Low temperatures for critical code generation
    "backend_models": 0.15,          # Data models need consistency
    "backend_routers": 0.15,         # API routes need correctness
    "system_integration": 0.1,       # Critical wiring, be very careful
    "testing_backend": 0.1,          # Tests need precision
    "testing_frontend": 0.15,        # E2E tests need to be accurate
    
    # Medium temperatures for design/architecture
    "architecture": 0.3,             # Allow some creativity in design
    "frontend_mock": 0.4,            # UI can be more creative
    
    # Higher temperatures for analysis/planning
    "refine": 0.25,                  # Refinements need balance
}

RETRY_TEMPERATURE_REDUCTION = 0.1  # Lower temperature on retry (more conservative)


def get_temperature(step_name: str, is_retry: bool = False, failure_reason: str = "") -> float:
    """
    Get appropriate temperature for a workflow step.
    
    Args:
        step_name: Workflow step identifier
        is_retry: Whether this is a retry attempt
        failure_reason: Reason for previous failure (if retry)
    
    Returns:
        Temperature value (0.0-1.0)
    
    Examples:
        >>> get_temperature("backend_implementation")
        0.2
        >>> get_temperature("backend_implementation", is_retry=True)
        0.1
        >>> get_temperature("backend_implementation", is_retry=True, failure_reason="truncated output")
        0.05
    """
    # Normalize step name
    normalized_step = step_name.lower().strip().replace(" ", "_")
    
    # Get base temperature
    base_temp = STEP_TEMPERATURES.get(normalized_step, 0.3)
    
    # Reduce on retry
    if is_retry:
        base_temp = max(0.05, base_temp - RETRY_TEMPERATURE_REDUCTION)
    
    # Further reduce for specific failure types
    if failure_reason:
        reason_lower = failure_reason.lower()
        
        if "truncated" in reason_lower or "incomplete" in reason_lower:
            # Be very concise for truncation issues
            base_temp = max(0.05, base_temp - 0.1)
        elif "syntax" in reason_lower or "error" in reason_lower:
            # Be very careful for syntax issues
            base_temp = max(0.05, base_temp - 0.05)
    
    return round(base_temp, 2)


def get_retry_parameters(step_name: str, base_tokens: int, failure_reason: str = "") -> dict:
    """
    Get adjusted parameters for retry attempts.
    
    Increases tokens and reduces temperature for better results.
    
    Args:
        step_name: Workflow step being retried
        base_tokens: Original token limit
        failure_reason: Why the previous attempt failed
    
    Returns:
        {
            "max_tokens": int,
            "temperature": float,
            "retry_multiplier": float
        }
    
    Examples:
        >>> get_retry_parameters("backend_implementation", 30000, "output truncated")
        {"max_tokens": 40000, "temperature": 0.05, "retry_multiplier": 1.33}
    """
    from app.orchestration.token_policy import get_tokens_for_step
    
    # Get retry tokens (uses policy's retry_tokens value)
    retry_tokens = get_tokens_for_step(step_name, is_retry=True)
    
    # Get adjusted temperature
    retry_temp = get_temperature(step_name, is_retry=True, failure_reason=failure_reason)
    
    # Calculate multiplier
    multiplier = retry_tokens / base_tokens if base_tokens > 0 else 1.5
    
    return {
        "max_tokens": retry_tokens,
        "temperature": retry_temp,
        "retry_multiplier": round(multiplier, 2),
        "reason_analyzed": bool(failure_reason)
    }

