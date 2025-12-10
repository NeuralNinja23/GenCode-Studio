# app/orchestration/prompt_adapter.py
"""
FAST v2 Prompt Adapter

Adaptive rewrite system for LLM prompts.
Escalates prompt strictness based on failure history.
Does NOT alter the global pipeline - works within steps only.

Usage:
    adapter = PromptAdapter()
    
    for attempt in range(max_retries):
        adapted_prompt = adapter.adapt(step_name, original_prompt)
        result = call_llm(adapted_prompt)
        
        if not valid(result):
            adapter.record_failure(step_name)
            continue
        
        adapter.record_success(step_name)
        return result
"""
from typing import Dict, Optional


class PromptAdapter:
    """
    Adaptive rewrite system for LLM prompts.
    
    Escalates prompt strictness based on failure history:
    - Attempt 1: Original prompt
    - Attempt 2: Add "IMPORTANT" reminders
    - Attempt 3: Add "MANDATORY STRUCTURE" requirements
    - Attempt 4+: Force deterministic mode with strict rules
    """
    
    def __init__(self):
        self.history: Dict[str, int] = {}

    def record_failure(self, step: str):
        """Record a failure for a step."""
        self.history[step] = self.history.get(step, 0) + 1

    def record_success(self, step: str):
        """Reset failure count on success."""
        self.history[step] = 0

    def get_failure_count(self, step: str) -> int:
        """Get the number of failures for a step."""
        return self.history.get(step, 0)

    def adapt(self, step: str, original_prompt: str) -> str:
        """
        Applies controlled transformations to improve success rate.
        Used only when step fails a contract.

        Adaptation intensity grows with number of failures.
        """
        fails = self.history.get(step, 0)

        if fails == 0:
            return original_prompt

        # Level 1: Add explicit requirements
        if fails == 1:
            return original_prompt + (
                "\n\n⚠️ IMPORTANT (Retry 1):\n"
                "- Do NOT truncate output.\n"
                "- Ensure all required functions exist.\n"
                "- Complete every function body.\n"
                "- Include all necessary imports.\n"
            )

        # Level 2: Add schema requirements
        if fails == 2:
            return original_prompt + (
                "\n\n⚠️ MANDATORY STRUCTURE (Retry 2):\n"
                "- Output must include ALL CRUD functions.\n"
                "- Ensure syntactic correctness.\n"
                "- Follow Beanie ODM strictly.\n"
                "- Every async function must have a complete body.\n"
                "- Include all required imports.\n"
                "- Use proper error handling (try/except or HTTPException).\n"
            )

        # Level 3+: Force deterministic mode inside step
        return (
            "🔴 CRITICAL RETRY (Attempt " + str(fails + 1) + ") - Previous attempts failed.\n"
            "Produce EXACTLY the following structure, no deviations:\n\n"
            + original_prompt
            + "\n\n"
            "🔴 ABSOLUTE RULES:\n"
            "- No omitted functions.\n"
            "- No placeholders or '...' or 'pass' statements.\n"
            "- No comments instead of code.\n"
            "- No truncation.\n"
            "- Output valid, complete, syntactically correct code.\n"
            "- Include COMPLETE implementations for every function.\n"
            "- Every function must have a proper return statement.\n"
        )

    def get_context_hint(self, step: str) -> Optional[str]:
        """Get a context hint based on failure history."""
        fails = self.history.get(step, 0)
        
        if fails == 0:
            return None
        
        step_lower = step.lower()
        
        if "router" in step_lower:
            return (
                "HINT: Ensure router has create, get_all, get_one, update, delete functions. "
                "Use @router decorators and async def. "
                "Import Note from app.models and use PydanticObjectId for IDs."
            )
        
        if "integration" in step_lower or "api" in step_lower:
            return (
                "HINT: Ensure API client exports getNotes, createNote, updateNote, deleteNote. "
                "Use 'export async function' syntax. "
                "Use fetch() with proper error handling."
            )
        
        if "main" in step_lower:
            return (
                "HINT: Ensure main.py includes include_router, lifespan context manager, "
                "and proper CORS middleware setup."
            )
        
        return f"HINT: Previous {fails} attempt(s) failed. Be extra careful with completeness."

    def get_adaptation_level(self, step: str) -> int:
        """Get the current adaptation level (0 = normal, 1-3 = escalating strictness)."""
        fails = self.history.get(step, 0)
        return min(fails, 3)  # Cap at level 3
