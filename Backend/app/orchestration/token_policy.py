# app/orchestration/token_policy.py
"""
Step-specific token allocation policies.

Different workflow steps have different complexity requirements:
- Analysis/Planning: Lower tokens (mostly text)
- Code Generation: Higher tokens (complete files)
- Backend Implementation: Highest tokens (Models + Routers + Manifest)
- Testing: Medium-high tokens (multiple test files)

This replaces the one-size-fits-all DEFAULT_MAX_TOKENS approach.
"""

# ═══════════════════════════════════════════════════════
# STEP-SPECIFIC TOKEN BUDGETS
# ═══════════════════════════════════════════════════════

STEP_TOKEN_POLICIES = {
    # ───────────────────────────────────────────────────
    # LOW COMPLEXITY STEPS (Analysis, Planning)
    # ───────────────────────────────────────────────────
    "analysis": {
        "max_tokens": 8000,      # Initial analysis
        "retry_tokens": 10000,   # Retry with more detail
        "description": "Requirement analysis and clarification"
    },
    
    "contracts": {
        "max_tokens": 8000,      # Contract definition from mock data
        "retry_tokens": 10000,   # Retry with more endpoints
        "description": "API contract generation from frontend mock"
    },
    
    "screenshot_verify": {
        "max_tokens": 8000,      # Visual QA analysis
        "retry_tokens": 10000,   # More detailed critique
        "description": "UI/UX review and visual QA"
    },
    
    # ───────────────────────────────────────────────────
    # MEDIUM COMPLEXITY STEPS (Architecture, Frontend)
    # ───────────────────────────────────────────────────
    # Issue #6 Fix: Increased tokens to prevent Victoria output truncation
    # Issue #8 Fix: Further increased since architecture often contains detailed UI tokens JSON
    "architecture": {
        "max_tokens": 20000,     # System design + UI design system (increased from 16000)
        "retry_tokens": 24000,   # More detailed architecture (increased from 20000)
        "description": "Architecture planning and UI design system"
    },
    
    "frontend_mock": {
        "max_tokens": 12000,     # Pages + Components with mock data
        "retry_tokens": 16000,   # More components or refinement
        "description": "Frontend UI with mock data (no API calls)"
    },
    
    "frontend_integration": {
        "max_tokens": 12000,     # Replace mock with API calls
        "retry_tokens": 16000,   # Fix API integration issues
        "description": "Replace mock data with real API calls"
    },
    
    "refine": {
        "max_tokens": 12000,     # Code refinements
        "retry_tokens": 14000,   # More extensive fixes
        "description": "Post-workflow refinements and polish"
    },
    
    # ───────────────────────────────────────────────────
    # HIGH COMPLEXITY STEPS (Backend Code Generation)
    # ───────────────────────────────────────────────────
    "backend_models": {
        "max_tokens": 10000,     # Models.py only
        "retry_tokens": 14000,   # More complex models with relations
        "description": "Database models (Beanie Documents)"
    },
    
    "backend_routers": {
        "max_tokens": 14000,     # Complete CRUD routers
        "retry_tokens": 18000,   # More endpoints or error handling
        "description": "API routers with full CRUD operations"
    },
    
    "backend_implementation": {
        "max_tokens": 20000,     # ATOMIC: Models + Routers + Manifest
        "retry_tokens": 24000,   # Retry with more space for completeness
        "description": "Complete backend vertical (Models + Routers + Manifest)"
    },
    
    "system_integration": {
        "max_tokens": 8000,      # Wire up routers in main.py
        "retry_tokens": 10000,   # Fix integration issues
        "description": "System integration (main.py + requirements)"
    },
    
    # ───────────────────────────────────────────────────
    # TESTING STEPS (Need space for multiple test files)
    # ───────────────────────────────────────────────────
    "testing_backend": {
        "max_tokens": 12000,     # Pytest test files
        "retry_tokens": 16000,   # More comprehensive tests
        "description": "Backend testing with pytest"
    },
    
    "testing_frontend": {
        "max_tokens": 14000,     # Playwright E2E tests
        "retry_tokens": 18000,   # More test scenarios
        "description": "Frontend E2E testing with Playwright"
    },
    
    "preview_final": {
        "max_tokens": 8000,      # Final preview and polish
        "retry_tokens": 10000,   # Additional refinements
        "description": "Final preview and application polish"
    },
    
    "complete": {
        "max_tokens": 6000,      # Workflow completion summary
        "retry_tokens": 8000,    # Extended summary if needed
        "description": "Workflow completion and summary"
    },
}


# ═══════════════════════════════════════════════════════
# DEFAULT FALLBACK (For steps not in the policy map)
# ═══════════════════════════════════════════════════════

DEFAULT_FALLBACK_TOKENS = 10000
DEFAULT_RETRY_TOKENS = 12000


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
        "backend implementation": "backend_implementation",
        "backend vertical": "backend_implementation",
        
        # Screenshot/UI Review variations
        "ui screenshot review": "screenshot_verify",
        "ui_screenshot_review": "screenshot_verify",  # Underscore version
        "screenshot review": "screenshot_verify",
        "screenshot_review": "screenshot_verify",
        
        # Testing variations
        "testing backend": "testing_backend",
        "testing frontend": "testing_frontend",
        "backend test diagnosis": "testing_backend",
        "backend_test_diagnosis": "testing_backend",
        "backend testing fix": "testing_backend",
        "backend_testing_fix": "testing_backend",
        
        # Integration variations
        "frontend integration": "frontend_integration",
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
