# app/llm/artifact_enforcement.py
"""
ARTIFACT Execution Mode Enforcement

When ExecutionMode == ARTIFACT:
1. HDAP instructions MUST be in system prompt (immutable rules)
2. Dynamic context contains data only, never protocol
3. Auto-recovery if HDAP markers are missing

Phase-1 Critical: This eliminates prompt-order sensitivity.
"""
from typing import Dict, Any, Optional
from app.core.logging import log


# ═══════════════════════════════════════════════════════════════════════════
# HDAP SYSTEM PROMPT (Protocol Rules - IMMUTABLE)
# ═══════════════════════════════════════════════════════════════════════════
# This MUST be prepended to the system prompt, never the user prompt.

HDAP_PROTOCOL_RULES = """
═══════════════════════════════════════════════════════════════════════════
🚨 CRITICAL OUTPUT PROTOCOL (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════════════════

You MUST output files using HDAP (Human-Definition Artifact Protocol).

FORMAT (MANDATORY):

<<<FILE path="relative/path/to/file.ext">>>
[file content here - complete and valid]
<<<END_FILE>>>

RULES:

1. Your FIRST 3 characters MUST be: <<<
2. Do NOT write explanations, comments, or markdown before the first FILE marker
3. Do NOT use markdown code fences (```), JSON arrays, or any other format
4. Each file MUST end with <<<END_FILE>>>
5. Multiple files: repeat the pattern for each file

EXAMPLE:

<<<FILE path="backend/app/models.py">>>
from beanie import Document

class Task(Document):
    title: str
    status: str
<<<END_FILE>>>

<<<FILE path="backend/app/routers/tasks.py">>>
from fastapi import APIRouter

router = APIRouter()
<<<END_FILE>>>

⚠️ PROTOCOL VIOLATION = REJECTION
═══════════════════════════════════════════════════════════════════════════
"""


def enforce_artifact_mode(
    base_system_prompt: str,
    user_task: str,
    step_name: str,
    files: Optional[Any] = None,
    contracts: Optional[str] = None,
    **kwargs
) -> Dict[str, str]:
    """
    Enforce ARTIFACT mode by building prompts correctly.
    
    Returns:
        {
            "system_prompt": "...",  # Protocol rules + agent identity
            "user_prompt": "..."     # Task + context (NO protocol)
        }
    """
    # ═══════════════════════════════════════════════════════
    # SYSTEM PROMPT: Protocol + Agent Identity (IMMUTABLE)
    # ═══════════════════════════════════════════════════════
    # HDAP rules come FIRST, then agent prompt
    system_prompt = HDAP_PROTOCOL_RULES + "\n\n" + base_system_prompt
    
    # ═══════════════════════════════════════════════════════
    # USER PROMPT: Task + Data (NO protocol instructions)
    # ═══════════════════════════════════════════════════════
    user_parts = []
    
    # Task description
    user_parts.append(f"TASK:\n{user_task}")
    
    # Existing files (if any) - data only, no format instructions
    if files:
        if isinstance(files, dict) and files:
            file_context = []
            for path, content in list(files.items())[:5]:  # Limit to 5 files
                # Truncate file content to prevent context explosion
                truncated_content = content[:2000] if len(content) > 2000 else content
                suffix = "... (truncated)" if len(content) > 2000 else ""
                file_context.append(f"--- {path} ---\n{truncated_content}{suffix}\n")
            if file_context:
                user_parts.append("EXISTING PROJECT FILES:\n" + "\n".join(file_context))
        elif isinstance(files, list) and files:
            file_context = []
            for f in files[:5]:
                path = f.get("path", "unknown")
                content = f.get("content", "")
                # Truncate file content to prevent context explosion
                truncated_content = content[:2000] if len(content) > 2000 else content
                suffix = "... (truncated)" if len(content) > 2000 else ""
                file_context.append(f"--- {path} ---\n{truncated_content}{suffix}\n")
            if file_context:
                user_parts.append("EXISTING PROJECT FILES:\n" + "\n".join(file_context))
    
    # Architecture/contracts (reference only)
    if contracts:
        user_parts.append(f"ARCHITECTURE REFERENCE:\n{contracts[:15000]}")
    
    user_prompt = "\n\n".join(user_parts)
    
    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }


async def auto_recover_hdap(
    raw_output: str,
    agent_name: str,
    llm_call_func: Any,
    provider: str,
    model: str,
    max_tokens: int = 4000
) -> Dict[str, Any]:
    """
    Deterministic HDAP recovery: Single automatic attempt to re-wrap output.
    
    Rules:
    - Only called if HDAP markers are missing
    - Single attempt (no loops)
    - Asks LLM to re-wrap WITHOUT changing content
    
    Returns:
        {
            "success": bool,
            "output": str,  # Re-wrapped output (if successful)
            "recovered": bool
        }
    """
    log("HDAP_RECOVERY", f"🔄 Attempting auto-recovery for {agent_name}")
    
    recovery_prompt = f"""
The previous output did not follow HDAP protocol.

PREVIOUS OUTPUT:
{raw_output[:2000]}

TASK:
Re-output the EXACT same content, but wrap it strictly in HDAP format:

<<<FILE path="...">>>
[content]
<<<END_FILE>>>

RULES:
1. Do NOT change the code/content
2. Do NOT add explanations
3. Start immediately with <<<FILE
4. Use the correct file paths from the output
"""

    recovery_system = HDAP_PROTOCOL_RULES + "\n\nYou are a format converter. Preserve content exactly, only add HDAP markers."
    
    try:
        # Single recovery call
        recovered_raw = await llm_call_func(
            prompt=recovery_prompt,
            system_prompt=recovery_system,
            provider=provider,
            model=model,
            temperature=0.0,  # Deterministic
            max_tokens=max_tokens
        )
        
        # Check if recovery worked
        from app.utils.parser import parse_hdap
        result = parse_hdap(recovered_raw)
        
        if result.get("no_hdap_markers"):
            log("HDAP_RECOVERY", "❌ Recovery failed - still no HDAP markers")
            return {
                "success": False,
                "output": raw_output,
                "recovered": False
            }
        
        if not result.get("complete"):
            log("HDAP_RECOVERY", f"⚠️ Recovery incomplete: {result.get('incomplete_files')}")
            return {
                "success": False,
                "output": recovered_raw,
                "recovered": False
            }
        
        log("HDAP_RECOVERY", f"✅ Recovery successful - {len(result.get('files', []))} files")
        return {
            "success": True,
            "output": recovered_raw,
            "recovered": True,
            "files": result.get("files", [])
        }
        
    except Exception as e:
        log("HDAP_RECOVERY", f"❌ Recovery exception: {e}")
        return {
            "success": False,
            "output": raw_output,
            "recovered": False,
            "error": str(e)
        }
