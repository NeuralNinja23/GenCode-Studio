# app/agents/api_client.py
# GenCode Studio - Multi-Provider API Client
# ✅ CLEAN REWRITE for Single-Key Gemini Setup
# Last Updated: November 12, 2025

import httpx
import asyncio
from typing import List, Dict, Any, Optional
from collections import defaultdict
from dataclasses import dataclass, field

# ✅ Import centralized configuration
from app.agents.config import (
    ChatMessage,
    GEMINI_API_KEY,
    OPENROUTER_API_KEY,
    OPENROUTER_API_URL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_MODEL,
    ENABLE_PROVIDER_FALLBACK,
    get_agent_provider,
    get_agent_model,
)

# ✅ Use the integration adapter for actual LLM calls
from app.lib.integration_adapter import call_llm_with_provider


# ================================================================
# ✅ MODEL + PROVIDER STATS TRACKING
# ================================================================

@dataclass
class ModelStat:
    """Statistics for a specific model"""
    success_count: int = 0
    failure_count: int = 0
    total_tokens: int = 0
    last_used: Optional[str] = None
    error_counts: Dict[str, int] = field(default_factory=dict)


@dataclass
class ProviderStats:
    """Statistics for a provider"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    models: Dict[str, ModelStat] = field(default_factory=dict)


_provider_stats: Dict[str, ProviderStats] = {}
_api_call_counter: Dict[str, int] = defaultdict(int)


def get_provider_stats(provider: str) -> ProviderStats:
    """Get or create stats for a provider"""
    if provider not in _provider_stats:
        _provider_stats[provider] = ProviderStats()
    return _provider_stats[provider]


def record_api_call(provider: str, model: str, success: bool, tokens: int = 0, error: Optional[str] = None):
    """Record API call statistics"""
    stats = get_provider_stats(provider)
    stats.total_calls += 1

    if success:
        stats.successful_calls += 1
    else:
        stats.failed_calls += 1

    if model not in stats.models:
        stats.models[model] = ModelStat()

    model_stat = stats.models[model]
    if success:
        model_stat.success_count += 1
        model_stat.total_tokens += tokens
    else:
        model_stat.failure_count += 1
        if error:
            model_stat.error_counts[error] = model_stat.error_counts.get(error, 0) + 1

    from datetime import datetime, timezone
    model_stat.last_used = datetime.now(timezone.utc).isoformat()


def get_all_stats() -> Dict[str, Any]:
    """Get all provider and model statistics"""
    return {
        "providers": {
            name: {
                "total_calls": stats.total_calls,
                "successful_calls": stats.successful_calls,
                "failed_calls": stats.failed_calls,
                "success_rate": (stats.successful_calls / stats.total_calls * 100) if stats.total_calls > 0 else 0,
                "models": {
                    model_name: {
                        "success_count": m.success_count,
                        "failure_count": m.failure_count,
                        "total_tokens": m.total_tokens,
                        "last_used": m.last_used,
                        "error_counts": dict(m.error_counts),
                    }
                    for model_name, m in stats.models.items()
                },
            }
            for name, stats in _provider_stats.items()
        },
        "api_call_counter": dict(_api_call_counter),
    }


# ================================================================
# ✅ MAIN CHAT FUNCTIONS (ASYNC + SYNC)
# ================================================================

def ensure_gemini_key_loaded():
    """Ensure Gemini API key is loaded in environment"""
    if not GEMINI_API_KEY:
        raise EnvironmentError("❌ GEMINI_API_KEY not found. Please set it in your .env file.")


async def chat_async(
    messages: List[ChatMessage],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    agent: str = "Marcus",
) -> str:
    """
    ✅ Async chat that delegates to integration_adapter
    Uses centralized provider/model configuration
    """
    ensure_gemini_key_loaded()

    resolved_provider = provider or get_agent_provider(agent) or DEFAULT_LLM_PROVIDER
    resolved_model = model or get_agent_model(agent) or DEFAULT_LLM_MODEL
    _api_call_counter[f"{resolved_provider}:{resolved_model}"] += 1

    prompt_message = messages[-1]["content"] if messages else ""
    chat_history = messages[:-1] if len(messages) > 1 else []

    try:
        result = await call_llm_with_provider(
            prompt=prompt_message,
            chat_history=chat_history,
            agent=agent,
            provider=resolved_provider,
            model=resolved_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        record_api_call(resolved_provider, resolved_model, True, tokens=len(result.split()))
        return result

    except Exception as e:
        record_api_call(resolved_provider, resolved_model, False, error=str(e))
        raise


def chat(
    messages: List[ChatMessage],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    agent: str = "Marcus",
) -> str:
    """Sync wrapper for chat_async"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(
        chat_async(messages, provider, model, temperature, max_tokens, agent)
    )


# ================================================================
# ✅ LEGACY COMPATIBILITY WRAPPERS
# ================================================================

async def call_openrouter_async(
    messages: List[ChatMessage],
    model: str = "google/gemini-2.0-flash-exp:free",
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> str:
    """Legacy async call for OpenRouter"""
    return await chat_async(
        messages=messages,
        provider="openrouter",
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        agent="Legacy",
    )


def call_openrouter(
    messages: List[ChatMessage],
    model: str = "google/gemini-2.0-flash-exp:free",
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> str:
    """Legacy sync wrapper for OpenRouter"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(call_openrouter_async(messages, model, temperature, max_tokens))


async def call_gemini_async(
    messages: List[ChatMessage],
    model: str = "gemini-2.5-flash",
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> str:
    """Legacy async call for Gemini"""
    return await chat_async(
        messages=messages,
        provider="gemini",
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        agent="Legacy",
    )


def call_gemini(
    messages: List[ChatMessage],
    model: str = "gemini-2.5-flash",
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> str:
    """Legacy sync wrapper for Gemini"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(call_gemini_async(messages, model, temperature, max_tokens))


# ================================================================
# ✅ UTILITIES
# ================================================================

def get_available_gemini_keys() -> List[str]:
    """Simplified: Return single Gemini key as list for compatibility"""
    return [GEMINI_API_KEY] if GEMINI_API_KEY else []


def select_best_model(provider: str, task_type: str = "general") -> str:
    """Select best model for provider based on usage stats"""
    stats = get_provider_stats(provider)

    defaults = {
        "gemini": {"general": "gemini-2.5-flash"},
        "openai": {"general": "gpt-4o-mini"},
        "anthropic": {"general": "claude-3-sonnet-20240229"},
        "ollama": {"general": "qwen2.5-coder:7b"},
    }

    if stats.models:
        best_model = max(
            stats.models.items(),
            key=lambda x: x[1].success_count - x[1].failure_count,
        )[0]
        return best_model

    return defaults.get(provider, {}).get(task_type, defaults.get(provider, {}).get("general", ""))


def reset_stats():
    """Reset all statistics (useful for testing)"""
    global _provider_stats, _api_call_counter
    _provider_stats = {}
    _api_call_counter = defaultdict(int)
