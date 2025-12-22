# app/llm/adapter.py
"""
Unified LLM adapter - single interface for all providers.

NOTE: No fallback logic - if rate limited after 3 attempts, raises RateLimitError to stop workflow.

V2 Enhancement: Stop sequences to prevent truncation.
V3 Enhancement: Token usage tracking for accurate cost reporting.
"""
import asyncio
from typing import Optional, List, Dict, Any, Union
from app.core.config import settings
from app.core.exceptions import LLMError, RateLimitError
from app.core.logging import log


# Type for LLM response with usage data
LLMResponse = Dict[str, Any]  # {"text": str, "usage": {"input": int, "output": int}}


# ═══════════════════════════════════════════════════════════════════════════
# V2: SMART STOP SEQUENCES - Prevent mid-function truncation
# ═══════════════════════════════════════════════════════════════════════════
# These stop sequences force the LLM to complete at natural code boundaries
# instead of cutting off mid-function when hitting token limits.

STOP_SEQUENCES = {
    "python": [],
    "javascript": [],
    "jsx": [],
    "generic": [],
}



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
        return [] # No stop sequences for generic/artifact mode

class LLMAdapter:
    """
    Unified adapter for LLM providers.
    
    Handles:
    - Provider selection
    - SINGLE EXECUTION (ArborMind handles retry via branch continuation)
    - Rate limit handling (raises LLMError)
    
    NO FALLBACK: If the primary provider fails, the request fails.
    NO RETRIES: ArborMind decides if/when to retry via branch continuation.
    """
    
    def __init__(self):
        self.default_provider = settings.llm.default_provider
        self.default_model = settings.llm.default_model
    
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
        return_usage: bool = False,  # V3: Return usage metadata for cost tracking
    ) -> Union[str, LLMResponse]:
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
            return_usage: V3 - if True, return dict with text AND usage metadata
            
        Returns:
            If return_usage=False: The LLM response text (str)
            If return_usage=True: Dict with {"text": str, "usage": {"input": int, "output": int}}
            
        Raises:
            LLMError: If provider fails after all retries
        """
        provider = provider or self.default_provider
        model = model or self.default_model
        
        # V2: Get step-specific stop sequences if step_name provided
        if stop_sequences is None:
            if step_name:
                stop_sequences = get_stop_sequences_for_step(step_name)
                log("LLM", f"Using stop sequences for {step_name}: {stop_sequences[:2]}...")
            else:
                stop_sequences = get_stop_sequences()
        
        # Call provider directly - no fallback
        result = await self._call_provider(
            provider, model, prompt, system_prompt, temperature, max_tokens, stop_sequences
        )
        
        # V3: Handle new dict response format from providers
        if isinstance(result, dict):
            if return_usage:
                return result  # Return full dict with text and usage
            else:
                return result.get("text", "")  # Backward compatible: return just text
        else:
            # Legacy string response (from other providers)
            if return_usage:
                return {"text": result, "usage": {"input": 0, "output": 0}}
            return result
    
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
        """
        Call a specific provider - SINGLE ATTEMPT ONLY.
        
        ArborMind handles retry decisions via branch continuation.
        This adapter is pure execution muscle.
        """
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

        # SINGLE EXECUTION - No retry loop
        # ArborMind decides if/when to retry via branch continuation
        try:
            response = await call_func(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
            )
            return response
        except Exception as e:
            # Report the failure - ArborMind decides what to do next
            raise LLMError(provider, f"Provider error: {e}")




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
        return_usage=False,
    )


async def call_llm_with_usage(
    prompt: str,
    system_prompt: str = "",
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 8000,
    stop_sequences: Optional[List[str]] = None,
    step_name: str = "",
) -> LLMResponse:
    """
    V3: Call LLM and return BOTH text and usage metadata.
    
    Returns:
        Dict with {"text": str, "usage": {"input": int, "output": int}}
    """
    return await _adapter.call(
        prompt=prompt,
        system_prompt=system_prompt,
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stop_sequences=stop_sequences,
        step_name=step_name,
        return_usage=True,
    )
