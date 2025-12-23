# app/arbormind/core/retry_policy.py
"""
Phase-1 Retry Policy

Hardened retry prompts for ARTIFACT steps that fail to produce output.
These are NOT negotiable, NOT modified at runtime, and step-specific.
"""

# ═══════════════════════════════════════════════════════════════════════════
# RETRY PROMPT REGISTRY (Static, Deterministic)
# ═══════════════════════════════════════════════════════════════════════════

RETRY_PROMPTS = {
    "architecture": """
🚨 RETRY ATTEMPT - PREVIOUS GENERATION FAILED

You FAILED to generate architecture files in the previous attempt.

HARD REQUIREMENTS FOR THIS RETRY:
- You MUST produce EXACTLY 5 architecture files
- File paths MUST be:
  * architecture/overview.md
  * architecture/frontend.md
  * architecture/backend.md
  * architecture/system.md
  * architecture/invariants.md
- Use HDAP markers ONLY (<st<<FILE path="...">>, <<<END_FILE>>>)
- Do NOT explain, summarize, or think aloud
- Zero files = WORKFLOW HALTS

Temperature: 0.0 (deterministic)
This is your FINAL attempt.
""",

    "backend_models": """
🚨 RETRY ATTEMPT - PREVIOUS GENERATION FAILED

You FAILED to generate backend models in the previous attempt.

HARD REQUIREMENTS FOR THIS RETRY:
- You MUST produce AT LEAST ONE models.py file
- File path: backend/app/models.py
- Must contain Beanie Document classes for ALL entities
- Use HDAP markers ONLY
- Do NOT explain or add commentary
- Zero files = WORKFLOW HALTS

The system CANNOT proceed without models.py.
Downstream steps depend on this file existing.

Temperature: 0.0 (deterministic)
This is your FINAL attempt.
""",

    "backend_routers": """
🚨 RETRY ATTEMPT - PREVIOUS GENERATION FAILED

You FAILED to generate backend routers in the previous attempt.

HARD REQUIREMENTS FOR THIS RETRY:
- You MUST produce AT LEAST ONE router file
- File path format: backend/app/routers/{entity_name}.py
- Each router MUST include:
  * FastAPI router with CRUD endpoints
  * GET, POST, PUT, DELETE operations
  * Proper imports and dependencies
- Use HDAP markers ONLY
- Do NOT generate User/Auth routers (system entities)
- Zero files = WORKFLOW HALTS

The system CANNOT proceed without routers.
Frontend integration depends on these files existing.

Temperature: 0.0 (deterministic)
This is your FINAL attempt.
""",

    "frontend_mock": """
🚨 RETRY ATTEMPT - PREVIOUS GENERATION FAILED

You FAILED to generate frontend components in the previous attempt.

HARD REQUIREMENTS FOR THIS RETRY:
- You MUST produce AT LEAST ONE React component file
- Must include pages and/or components
- All files must be valid JSX/TSX
- Use HDAP markers ONLY
- Do NOT explain or add commentary
- Zero files = WORKFLOW HALTS

Temperature: 0.0 (deterministic)
This is your FINAL attempt.
""",

    "testing_backend": """
🚨 RETRY ATTEMPT - PREVIOUS GENERATION FAILED

You FAILED to generate backend tests in the previous attempt.

REQUIREMENTS FOR THIS RETRY:
- Produce AT LEAST ONE test file (if possible)
- File path: backend/tests/test_*.py
- Use HDAP markers ONLY
- If generation is not possible, output minimal stub

Note: This step is non-fatal. Empty output is allowed but discouraged.

Temperature: 0.0 (deterministic)
This is your final attempt.
""",
}


def get_retry_prompt(step_name: str) -> str:
    """
    Get hardened retry prompt for a step.
    
    Args:
        step_name: Step that failed (e.g., "backend_models")
        
    Returns:
        Hardened retry prompt, or generic fallback if step not in registry
    """
    return RETRY_PROMPTS.get(
        step_name,
        f"""
🚨 RETRY ATTEMPT - PREVIOUS GENERATION FAILED

You FAILED to generate output for {step_name} in the previous attempt.

REQUIREMENTS:
- You MUST produce valid HDAP output
- Use <<<FILE path="...">>> and <<<<END_FILE>>> markers
- Do NOT explain or add commentary
- This is your FINAL attempt

Temperature: 0.0 (deterministic)
"""
    )


def has_retry_prompt(step_name: str) -> bool:
    """Check if a step has a defined retry prompt."""
    return step_name in RETRY_PROMPTS
