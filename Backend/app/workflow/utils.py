# app/workflow/utils.py
"""
Workflow utilities - shared helper functions.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional


from app.core.logging import log


async def broadcast_to_project(manager: Any, project_id: str, message: Dict[str, Any]) -> None:
    """Broadcast a message to all clients connected to a project."""
    try:
        if hasattr(manager, 'broadcast'):
            await manager.broadcast(project_id, message)
        elif hasattr(manager, 'send_to_project'):
            await manager.send_to_project(project_id, message)
        else:
            # Fallback - try direct attribute access
            connections = getattr(manager, 'connections', {})
            for ws in connections.get(project_id, []):
                try:
                    await ws.send_json(message)
                except Exception as ws_error:
                    # FIX #10: Log the error instead of silently swallowing it
                    log("BROADCAST", f"Failed to send to websocket: {ws_error}")
    except Exception as e:
        print(f"[broadcast_to_project] Failed to broadcast: {e}")


def pluralize(word: str) -> str:
    """
    Simple English pluralization helper.
    
    Rules:
    - Ends with 'y' (not preceded by vowel) -> replace 'y' with 'ies'
    - Ends with s, x, z, ch, sh -> add 'es'
    - Else -> add 's'
    """
    if not word:
        return ""
    
    word = word.lower()
    
    # Handle 'y' -> 'ies' (unless preceded by vowel like 'boy' -> 'boys', but simple heuristic is ok)
    # Actually, standard rule: consonant + y -> ies
    if word.endswith('y'):
        if len(word) > 1 and word[-2] not in 'aeiou':
            return word[:-1] + 'ies'
            
    # Handle es endings
    if word.endswith(('s', 'x', 'z', 'ch', 'sh')):
        return word + 'es'
        
    return word + 's'
