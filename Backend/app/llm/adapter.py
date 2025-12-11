# app/llm/adapter.py
"""
Unified LLM adapter - single interface for all providers.

NOTE: No fallback logic - if rate limited after 3 attempts, raises RateLimitError to stop workflow.

V2 Enhancement: Stop sequences to prevent truncation.
"""
import asyncio
from typing import Optional, List, Dict, Any
from app.core.config import settings
from app.core.exceptions import LLMError, RateLimitError


# ═══════════════════════════════════════════════════════════════════════════
# V2: SMART STOP SEQUENCES - Prevent mid-function truncation
# ═══════════════════════════════════════════════════════════════════════════
# These stop sequences force the LLM to complete at natural code boundaries
# instead of cutting off mid-function when hitting token limits.

STOP_SEQUENCES = {
    "python": [
        "\n\n@router.",      # New route decorator - safe to stop before next route
        "\n\nclass ",        # New class definition
        "\n\n# ═══",         # Section separator comment
        "\n\n# ---",         # Another common separator
    ],
    "javascript": [
        "\n\nexport ",       # New export statement
        "\n\n// ═══",        # Section separator
        "\n\nimport ",       # New import block (shouldn't appear mid-file)
        "\n\nfunction ",     # New function declaration
        "\n\nconst ",        # New const at module level
    ],
    "jsx": [
        "\n\nexport ",       # Export statement
        "\n\n// ═══",        # Section separator
        "\n\nfunction ",     # Component function
        "\n\nconst ",        # New const
    ],
    "generic": [
        "\n\n```",           # End of code block
        "\n\n---",           # Markdown separator
        "\n\n\n",            # Triple newline (natural break)
    ],
}
# USER REQUEST UPDATE: Ensure strict stops on file ends
STOP_SEQUENCES["python"].extend(["```", "```json", "<<END>>"])
STOP_SEQUENCES["javascript"].extend(["```", "```json", "<<END>>"])
STOP_SEQUENCES["jsx"].extend(["```", "```json", "<<END>>"])



def get_stop_sequences(file_type: str = "default") -> List[str]:
    """Get appropriate stop sequences for a file type."""
    return STOP_SEQUENCES.get(file_type, STOP_SEQUENCES["generic"])


def get_stop_sequences_for_step(step_name: str) -> List[str]:
    """
    Get appropriate stop sequences based on workflow step.
    
    Prevents Derek from generating incomplete functions by stopping
    at natural code boundaries like route decorators, class definitions, etc.
    
    Args:
        step_name: Workflow step name (e.g., "Backend Routers", "backend_routers")
    
    Returns:
        List of stop sequences for the LLM
    """
    step_lower = step_name.lower()
    
    # Backend Python files - routers, models, main.py
    if any(keyword in step_lower for keyword in ["router", "backend", "model", "main", "database"]):
        return STOP_SEQUENCES["python"]
    
    # Frontend JSX components and pages
    elif any(keyword in step_lower for keyword in ["page", "component", "frontend_mock"]):
        return STOP_SEQUENCES["jsx"]
    
    # Frontend JavaScript - API client, etc.
    elif any(keyword in step_lower for keyword in ["integration", "api", "lib"]):
        return STOP_SEQUENCES["javascript"]
    
    # Generic (markdown, contracts, etc.)
    else:
        return STOP_SEQUENCES["generic"]

class LLMAdapter:
    """
    Unified adapter for LLM providers.
    
    Handles:
    - Provider selection
    - Retries with exponential backoff (3 attempts)
    - Rate limit handling
    
    NO FALLBACK: If the primary provider fails, the request fails.
    """
    
    def __init__(self):
        self.default_provider = settings.llm.default_provider
        self.default_model = settings.llm.default_model
        self.max_retries = settings.llm.max_retries
    
    async def call(
        self,
        prompt: str,
        system_prompt: str = "",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 8000,
        stop_sequences: Optional[List[str]] = None,
        step_name: str = "",  # V2: For step-specific stop sequences
    ) -> str:
        """
        Call an LLM provider with automatic retry.
        
        Args:
            prompt: The user/assistant prompt
            system_prompt: System instructions
            provider: Provider name (gemini, openai, anthropic, ollama)
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
            stop_sequences: V2 - sequences that signal completion (prevents truncation)
            step_name: V2 - workflow step name for auto-selecting appropriate stop sequences
            
        Returns:
            The LLM response text
            
        Raises:
            LLMError: If provider fails after all retries
        """
        provider = provider or self.default_provider
        model = model or self.default_model
        
        # V2: Get step-specific stop sequences if step_name provided
        if stop_sequences is None:
            if step_name:
                stop_sequences = get_stop_sequences_for_step(step_name)
                print(f"[LLM] Using stop sequences for {step_name}: {stop_sequences[:2]}...")
            else:
                stop_sequences = get_stop_sequences()
        
        # Call provider directly - no fallback
        return await self._call_provider(
            provider, model, prompt, system_prompt, temperature, max_tokens, stop_sequences
        )
    
    async def _call_provider(
        self,
        provider: str,
        model: Optional[str],
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        stop_sequences: Optional[List[str]] = None,
    ) -> str:
        """Call a specific provider with retry logic."""
        # Import here to avoid circular imports
        from .providers import gemini, openai, anthropic, ollama
        
        provider_map = {
            "gemini": gemini.call,
            "openai": openai.call,
            "anthropic": anthropic.call,
            "ollama": ollama.call,
        }
        
        if provider not in provider_map:
            raise LLMError(provider, f"Unknown provider: {provider}")
        
        call_func = provider_map[provider]
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = await call_func(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop_sequences=stop_sequences,  # V2: Pass stop sequences
                )
                
                # NOTE: Token tracking now handled by BudgetManager at orchestrator level
                # The adapter returns the response, and handlers call budget.register_usage()
                
                return response
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Rate limit - wait and retry
                if "rate" in error_str or "429" in error_str:
                    wait_time = (attempt + 1) * 5
                    print(f"[LLM] Rate limited (attempt {attempt + 1}/{self.max_retries}), waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                # Network error - shorter retry
                elif "network" in error_str or "connection" in error_str:
                    print(f"[LLM] Network error (attempt {attempt + 1}/{self.max_retries}), retrying...")
                    await asyncio.sleep(2)
                else:
                    # Unknown error - don't retry, fail immediately
                    raise LLMError(provider, f"Provider error: {e}")
        
        # All retries exhausted due to rate limiting - raise specific error to STOP workflow
        raise RateLimitError(provider, self.max_retries)




# Singleton instance
_adapter = LLMAdapter()


async def call_llm(
    prompt: str,
    system_prompt: str = "",
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 8000,
    stop_sequences: Optional[List[str]] = None,
    step_name: str = "",  # V2: For step-specific stop sequences
) -> str:
    """Convenience function for calling LLM with V2 stop sequences support."""
    return await _adapter.call(
        prompt=prompt,
        system_prompt=system_prompt,
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stop_sequences=stop_sequences,
        step_name=step_name,
    )

