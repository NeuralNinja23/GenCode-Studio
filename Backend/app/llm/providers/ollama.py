# app/llm/providers/ollama.py
"""
Ollama provider implementation.
"""
import aiohttp
from typing import Optional
from app.core.config import settings


DEFAULT_MODEL = "qwen2.5-coder:7b"


async def call(
    prompt: str,
    system_prompt: str = "",
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 8000,
    stop_sequences: Optional[list] = None,
) -> str:
    """
    Call Ollama API (local).
    
    Args:
        stop_sequences: V2 - sequences that signal completion (prevents truncation)
    
    Returns:
        The generated text
        
    Raises:
        Exception on API errors
    """
    # Ollama runs locally, no API key needed
    model = model or DEFAULT_MODEL
    api_url = f"{settings.llm.ollama_base_url}/api/chat"
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    options = {
        "temperature": temperature,
        "num_predict": max_tokens,
    }
    
    # V2: Add stop sequences to prevent truncation
    if stop_sequences:
        options["stop"] = stop_sequences
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": options,
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            api_url, 
            json=payload,
            timeout=aiohttp.ClientTimeout(total=300)  # Ollama can be slower
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Ollama API error {response.status}: {text[:200]}")
            
            data = await response.json()
            
            try:
                return data["message"]["content"]
            except (KeyError, IndexError) as e:
                raise Exception(f"Failed to parse Ollama response: {e}")
