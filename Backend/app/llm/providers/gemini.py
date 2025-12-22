# app/llm/providers/gemini.py
"""
Google Gemini provider implementation.
"""
import aiohttp
from typing import Optional
from app.core.config import settings


DEFAULT_MODEL = "gemini-2.0-flash-exp"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


async def call(
    prompt: str,
    system_prompt: str = "",
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 8000,
    stop_sequences: Optional[list] = None,
) -> str:
    """
    Call Google Gemini API.
    
    Args:
        stop_sequences: V2 - sequences that signal completion (prevents truncation)
    
    Returns:
        The generated text
        
    Raises:
        Exception on API errors
    """
    api_key = settings.llm.gemini_api_key
    if not api_key:
        raise Exception("GEMINI_API_KEY not configured")
    
    model = model or DEFAULT_MODEL
    url = f"{API_URL}/{model}:generateContent?key={api_key}"
    
    # Build content structure - Gemini expects specific format
    contents = []
    contents.append({"role": "user", "parts": [{"text": prompt}]})
    
    # Build generation config
    # PHASE 3 FIX: Token Expansion Enforcement
    # Gemini 2.0 Flash allows 8k output by default, but we can request more if model supports it
    # We trust max_tokens passed from adapter/budget_manager (up to 20k for routers)
    generation_config = {
        "temperature": 0.2, # Reduced from 0.7 for more deterministic code
        "maxOutputTokens": max_tokens, 
        # 🚨 REMOVED: "responseMimeType": "application/json" was FORCING JSON output
        # This was the ROOT CAUSE of Victoria outputting JSON instead of HDAP files!
        # Agents should output HDAP format (<<<FILE>>>...<<<END_FILE>>>), not JSON.
    }
    
    # V2: Add stop sequences to prevent truncation
    if stop_sequences:
        generation_config["stopSequences"] = stop_sequences[:4]  # Gemini allows max 4
    
    payload = {
        "contents": contents,
        "generationConfig": generation_config,
    }
    
    # Add system instruction separately (Gemini's preferred format)
    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as response:
            text = await response.text()
            
            if response.status == 429:
                print(f"[GEMINI] 429 Rate limit response: {text[:500]}")
                raise Exception(f"Rate limited (429): {text[:200]}")
            
            if response.status == 403:
                print(f"[GEMINI] 403 Forbidden response: {text[:500]}")
                raise Exception(f"API key invalid or quota exceeded (403): {text[:200]}")
            
            if response.status == 400:
                print(f"[GEMINI] 400 Bad request: {text[:500]}")
                raise Exception(f"Bad request (400): {text[:200]}")
            
            if response.status != 200:
                print(f"[GEMINI] Error {response.status}: {text[:500]}")
                raise Exception(f"Gemini API error {response.status}: {text[:200]}")
            
            # Parse the JSON response
            import json
            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                print(f"[GEMINI] Failed to parse JSON: {text[:500]}")
                raise Exception(f"Failed to parse Gemini response: {e}")
            
            # Extract text from response
            try:
                candidates = data.get("candidates", [])
                if not candidates:
                    raise Exception("No candidates in response")
                
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if not parts:
                    raise Exception("No parts in response")
                
                text_content = parts[0].get("text", "")
                
                # V3: Extract usage metadata for accurate cost tracking
                usage_metadata = data.get("usageMetadata", {})
                usage = {
                    "input": usage_metadata.get("promptTokenCount", 0),
                    "output": usage_metadata.get("candidatesTokenCount", 0),
                    "total": usage_metadata.get("totalTokenCount", 0),
                }
                
                # Return dict with both text and usage
                return {
                    "text": text_content,
                    "usage": usage,
                }
            except (KeyError, IndexError) as e:
                raise Exception(f"Failed to parse Gemini response: {e}")
