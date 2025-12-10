# app/api/providers.py
"""
LLM provider management routes.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from app.core.config import settings

router = APIRouter(prefix="/api/providers", tags=["Providers"])


class ProviderInfo(BaseModel):
    name: str
    available: bool
    models: List[str]


@router.get("")
async def list_providers():
    """List available LLM providers."""
    providers = []
    
    if settings.llm.gemini_api_key:
        providers.append(ProviderInfo(
            name="gemini",
            available=True,
            models=["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],
        ))
    
    if settings.llm.openai_api_key:
        providers.append(ProviderInfo(
            name="openai",
            available=True,
            models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        ))
    
    if settings.llm.anthropic_api_key:
        providers.append(ProviderInfo(
            name="anthropic",
            available=True,
            models=["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
        ))
    
    return {
        "providers": [p.model_dump() for p in providers],
        "default_provider": settings.llm.default_provider,
        "default_model": settings.llm.default_model,
    }


@router.get("/available")
async def get_available_providers():
    """Get list of available providers (those with API keys configured)."""
    available = []
    
    if settings.llm.gemini_api_key:
        available.append({
            "id": "gemini",
            "name": "Google Gemini",
            "models": ["gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],
            "requiresApiKey": True,
            "costPer1kTokens": 0.0,
        })
    
    if settings.llm.openai_api_key:
        available.append({
            "id": "openai",
            "name": "OpenAI",
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
            "requiresApiKey": True,
            "costPer1kTokens": 0.01,
        })
    
    if settings.llm.anthropic_api_key:
        available.append({
            "id": "anthropic",
            "name": "Anthropic Claude",
            "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
            "requiresApiKey": True,
            "costPer1kTokens": 0.015,
        })
    
    # Ollama is always available (local, no API key needed)
    available.append({
        "id": "ollama",
        "name": "Ollama (Local)",
        "models": ["qwen2.5-coder:7b", "llama3.1:8b", "codellama:7b"],
        "requiresApiKey": False,
        "costPer1kTokens": 0.0,
    })
    
    return {"providers": available}


@router.get("/current")
async def get_current_provider():
    """Get current default provider and model."""
    return {
        "provider": settings.llm.default_provider,
        "model": settings.llm.default_model,
    }


class SetProviderRequest(BaseModel):
    provider: str
    model: str


# Runtime storage for current provider (in-memory, resets on restart)
_current_provider = {"provider": None, "model": None}


@router.post("/set")
async def set_provider(data: SetProviderRequest):
    """Set the current provider and model."""
    global _current_provider
    
    # Validate provider exists
    valid_providers = ["gemini", "openai", "anthropic", "ollama"]
    if data.provider not in valid_providers:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid provider: {data.provider}")
    
    # Update runtime settings
    _current_provider["provider"] = data.provider
    _current_provider["model"] = data.model
    
    # Update settings object (runtime only - doesn't persist to env)
    settings.llm.default_provider = data.provider
    settings.llm.default_model = data.model
    
    return {
        "success": True,
        "provider": data.provider,
        "model": data.model,
    }
