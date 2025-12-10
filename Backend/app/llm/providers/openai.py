# app/llm/providers/openai.py
"""
OpenAI provider implementation.
"""
import aiohttp
from typing import Optional
from app.core.config import settings


DEFAULT_MODEL = "gpt-4o-mini"
API_URL = "https://api.openai.com/v1/chat/completions"


async def call(
    prompt: str,
    system_prompt: str = "",
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 8000,
    stop_sequences: Optional[list] = None,
) -> str:
    """
    Call OpenAI API.
    
    Args:
        stop_sequences: V2 - sequences that signal completion (prevents truncation)
    
    Returns:
        The generated text
        
    Raises:
        Exception on API errors
    """
    api_key = settings.llm.openai_api_key
    if not api_key:
        raise Exception("OPENAI_API_KEY not configured")
    
    model = model or DEFAULT_MODEL
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    
    # V2: Add stop sequences to prevent truncation
    if stop_sequences:
        payload["stop"] = stop_sequences[:4]  # OpenAI allows max 4
    
    headers = {
        "Authorization": f"Bearer {api_key}",
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
                raise Exception(f"OpenAI API error {response.status}: {text[:200]}")
            
            data = await response.json()
            
            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as e:
                raise Exception(f"Failed to parse OpenAI response: {e}")
