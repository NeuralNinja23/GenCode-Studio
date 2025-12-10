# app/llm/providers/anthropic.py
"""
Anthropic Claude provider implementation.
"""
import aiohttp
from typing import Optional
from app.core.config import settings


DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
API_URL = "https://api.anthropic.com/v1/messages"


async def call(
    prompt: str,
    system_prompt: str = "",
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 8000,
    stop_sequences: Optional[list] = None,
) -> str:
    """
    Call Anthropic Claude API.
    
    Args:
        stop_sequences: V2 - sequences that signal completion (prevents truncation)
    
    Returns:
        The generated text
        
    Raises:
        Exception on API errors
    """
    api_key = settings.llm.anthropic_api_key
    if not api_key:
        raise Exception("ANTHROPIC_API_KEY not configured")
    
    model = model or DEFAULT_MODEL
    
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    
    if system_prompt:
        payload["system"] = system_prompt
    
    # V2: Add stop sequences to prevent truncation
    if stop_sequences:
        payload["stop_sequences"] = stop_sequences
    
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            API_URL,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=120)
        ) as response:
            if response.status == 429:
                raise Exception("Rate limited (429)")
            
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Anthropic API error {response.status}: {text[:200]}")
            
            data = await response.json()
            
            try:
                content = data.get("content", [])
                if not content:
                    raise Exception("No content in response")
                return content[0].get("text", "")
            except (KeyError, IndexError) as e:
                raise Exception(f"Failed to parse Anthropic response: {e}")
