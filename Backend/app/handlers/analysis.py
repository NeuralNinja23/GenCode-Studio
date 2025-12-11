# app/handlers/analysis.py
"""
Step 1: Marcus analyzes user intent.

This matches the legacy workflows.py step_analysis logic exactly.
"""
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.core.types import ChatMessage, StepResult
from app.core.constants import WorkflowStep
from app.core.exceptions import RateLimitError
from app.handlers.base import broadcast_status, broadcast_agent_log
from app.core.logging import log
from app.orchestration.state import WorkflowStateManager
from app.llm import call_llm
from app.llm.prompts import MARCUS_PROMPT
from app.utils.parser import normalize_llm_output
from app.attention import (
    compute_archetype_routing,
    compute_ui_vibe_routing,
)


# FIX #12: Extract entity patterns to constant - used in both main flow and fallback
ENTITY_PATTERNS: List[Tuple[str, List[str]]] = [
    ("bug", ["bug tracking", "bug tracker", "issue tracker"]),
    ("note", ["notes app", "note taking", "notepad"]),
    ("task", ["task management", "task manager", "todo", "to-do"]),
    ("product", ["e-commerce", "store", "shop", "marketplace"]),
    ("post", ["blog", "blogging"]),
    ("article", ["article", "cms", "content management"]),
    ("query", ["database", "chat with database", "sql"]),
    ("recipe", ["recipe", "cooking", "food"]),
    ("expense", ["expense", "budget", "finance tracker"]),
    ("contact", ["contact", "crm", "customer relationship"]),
    ("event", ["event", "calendar", "scheduling"]),
    ("message", ["chat", "messaging", "communication"]),
    ("file", ["file manager", "storage", "upload"]),
    ("ticket", ["ticketing", "support ticket", "help desk", "customer support"]),
    ("order", ["order management", "orders", "fulfillment"]),
    ("invoice", ["invoice", "billing", "payment"]),
    ("project", ["project management", "projects"]),
    ("user", ["user management", "users", "authentication"]),
]


def _detect_primary_entity(user_request: str) -> str:
    """
    Detect primary entity from user request using dynamic pattern matching.
    
    Issue #8 Fix: Uses multiple strategies for robust entity extraction:
    1. Known entity patterns (e.g., "ticketing tool" → "ticket")
    2. Dynamic extraction from "X tracker/manager/tool" patterns
    3. Fallback to default "item"
    """
    import re
    request_lower = user_request.lower()
    
    # Strategy 1: Check known entity patterns first
    for entity, keywords in ENTITY_PATTERNS:
        if any(kw in request_lower for kw in keywords):
            return entity
    
    # Strategy 2: Dynamic extraction - "X tracker/manager/system/tool/dashboard/app"
    # Pattern: word + (tracker|manager|system|tool|dashboard|app)
    match = re.search(r'(\w+)\s*(?:tracker|manager|management|system|tool|dashboard|app|application)', request_lower)
    if match:
        word = match.group(1)
        # Skip common non-entity words
        if word not in ["the", "a", "an", "my", "your", "our", "this", "that", "web", "full", "stack", "simple", "basic", "modern", "new"]:
            # Singularize if plural (basic heuristic)
            if word.endswith("ing"):
                # "ticketing" → "ticket", "tracking" → "track"
                word = word[:-3] if word.endswith("ting") else word[:-3]
            elif word.endswith("s") and len(word) > 3:
                word = word[:-1]
            return word
    
    # Strategy 3: Look for "manage/track/create/build X" pattern
    match = re.search(r'(?:manage|track|create|build|store|list)\s+(?:a\s+)?(?:list\s+of\s+)?(\w+)', request_lower)
    if match:
        word = match.group(1)
        if word not in ["the", "a", "an", "my", "your", "our", "items", "data", "things"]:
            # Singularize
            if word.endswith("s") and len(word) > 3:
                word = word[:-1]
            return word
    
    # Strategy 4: Look for nouns after "with" (e.g., "with ticket list, filters")
    match = re.search(r'with[:\s]+(\w+)\s*(?:list|management|tracking)', request_lower)
    if match:
        return match.group(1)
    
    return "item"  # Final fallback



async def step_analysis(
    project_id: str,
    user_request: str,
    manager: Any,
    project_path: Path,
    chat_history: List[ChatMessage],
    provider: str,
    model: str,
    current_turn: int,
    max_turns: int,
) -> StepResult:
    """
    Step 1: Marcus analyzes the user request.
    
    Extracts:
    - Domain (e-commerce, productivity, social, etc.)
    - Goal (what the user wants)
    - Core entities (nouns that need database tables/collections)
    - Core features (what actions can users perform?)
    - Tech stack recommendations
    
    Returns:
        StepResult with next step = ARCHITECTURE
        
    Raises:
        RateLimitError: If rate limited - workflow should stop
    """
    await broadcast_status(
        manager, project_id, WorkflowStep.ANALYSIS,
        f"Turn {current_turn}/{max_turns}: Marcus analyzing requirements...",
        current_turn, max_turns
    )
    
    intent_prompt = f"""Analyze this user request and extract key information.

USER REQUEST:
{user_request}

═══════════════════════════════════════════════════════
⚠️ CRITICAL: ENTITY DETECTION RULES
═══════════════════════════════════════════════════════

The PRIMARY ENTITY is the main THING the user creates, manages, or interacts with.
It is NOT "user" or "project" - those are SUPPORTING entities.

EXAMPLES:
- "Bug tracking system" → PRIMARY: "bug" (not user, not project)
- "Notes app" → PRIMARY: "note"
- "Task management" → PRIMARY: "task"
- "E-commerce store" → PRIMARY: "product"
- "Blog platform" → PRIMARY: "post" or "article"
- "Chat with database" → PRIMARY: "query" or "conversation"
- "Recipe manager" → PRIMARY: "recipe"
- "Expense tracker" → PRIMARY: "expense"

The entities array should be ordered: [PRIMARY, ...secondary]
The FIRST entity in the array is the most important one!

═══════════════════════════════════════════════════════

Return ONLY this JSON structure:
{{
  "thinking": "Step-by-step analysis: What is the USER trying to build? What is the MAIN thing they will create/manage? That is the PRIMARY entity...",
  "domain": "e-commerce|productivity|social|developer-tools|finance|health|etc",
  "goal": "short summary of what user wants",
  "coreFeatures": ["feature1", "feature2", "feature3"],
  "entities": ["PRIMARY_ENTITY_FIRST", "secondary1", "secondary2"],
  "frontendStack": "React + Vite + Tailwind",
  "backendStack": "FastAPI + MongoDB"
}}

REMEMBER: The FIRST entity must be the PRIMARY thing the user creates/manages!
NO explanations. ONLY JSON."""

    # Broadcast Marcus is thinking
    await broadcast_agent_log(
        manager,
        project_id,
        "AGENT:Marcus",
        f'Analyzing request: "{user_request[:100]}..."'
    )
    
    try:
        # Use step-specific token allocation
        from app.orchestration.token_policy import get_tokens_for_step
        analysis_tokens = get_tokens_for_step(WorkflowStep.ANALYSIS, is_retry=False)
        
        raw = await call_llm(
            prompt=intent_prompt,
            system_prompt=MARCUS_PROMPT,
            provider=provider,
            model=model,
            max_tokens=analysis_tokens,
        )
        
        try:
            intent = normalize_llm_output(raw)
        except Exception:
            intent = {}
        
        # Broadcast Thinking
        thinking = intent.get("thinking")
        if thinking:
             await broadcast_agent_log(
                manager,
                project_id,
                "AGENT:Marcus",
                "Marcus is analyzing...",
                data={"thinking": thinking}
            )

        if intent and intent.get("domain") and intent.get("entities"):
            # 🔥 NEW: Attention-based routing using scaled dot-product attention
            try:
                archetype = await compute_archetype_routing(user_request)
                ui_vibe = await compute_ui_vibe_routing(user_request)
                
                intent["archetypeRouting"] = archetype
                intent["uiVibeRouting"] = ui_vibe
                
                await broadcast_agent_log(
                    manager,
                    project_id,
                    "AGENT:Marcus",
                    f"Classified as: {archetype.get('top', 'unknown')} · {ui_vibe.get('top', 'unknown')} vibe"
                )
            except Exception as e:
                log("ANALYSIS", f"Attention routing failed: {e}", project_id=project_id)
            
            await WorkflowStateManager.set_intent(project_id, intent)
        else:
            # Smart fallback - use shared entity detection function
            primary_entity = _detect_primary_entity(user_request)
            
            log("ANALYSIS", f"Fallback entity detection: '{primary_entity}' from request", project_id=project_id)
            
            intent = {
                "domain": "general",
                "goal": user_request[:100],
                "entities": [primary_entity],
                "coreFeatures": ["create", "read", "update", "delete"],
                "frontendStack": "React + Vite + Tailwind",
                "backendStack": "FastAPI + MongoDB"
            }
            
            # Apply attention routing to fallback intent too
            try:
                archetype = await compute_archetype_routing(user_request)
                ui_vibe = await compute_ui_vibe_routing(user_request)
                intent["archetypeRouting"] = archetype
                intent["uiVibeRouting"] = ui_vibe
            except Exception as e:
                log("ANALYSIS", f"Attention routing failed in fallback: {e}", project_id=project_id)
            
            await WorkflowStateManager.set_intent(project_id, intent)
        
        await WorkflowStateManager.set_original_request(project_id, user_request)
        
        # Broadcast Marcus's reasoning
        domain = intent.get('domain', 'unknown')
        goal = intent.get('goal', '')
        features = intent.get('coreFeatures', [])
        
        reasoning = f"Identified domain: {domain}. Goal: {goal}. "
        reasoning += f"Key features: {', '.join(features[:3])}. "
        reasoning += "Proceeding to architecture planning."
        
        await broadcast_agent_log(
            manager,
            project_id,
            "AGENT:Marcus",
            reasoning
        )
        
        
        
        chat_history.append({"role": "assistant", "content": raw})
        
    except RateLimitError:
        # Rate limit exhausted - RE-RAISE to stop workflow
        log("ANALYSIS", "Rate limit exhausted - stopping workflow", project_id=project_id)
        raise
        
    except Exception as e:
        # Other errors - use defaults and continue
        log("ANALYSIS", f"Analysis failed: {e}, using defaults", project_id=project_id)
        
        # Smart fallback - use shared entity detection function (FIX #12)
        primary_entity = _detect_primary_entity(user_request)
        
        log("ANALYSIS", f"Fallback entity: '{primary_entity}'", project_id=project_id)
        
        fallback_intent = {
            "domain": "general",
            "goal": user_request[:100],
            "entities": [primary_entity],
            "coreFeatures": ["create", "read", "update", "delete"],
            "frontendStack": "React + Vite + Tailwind",
            "backendStack": "FastAPI + MongoDB"
        }
        
        # Apply attention routing to exception fallback too
        try:
            archetype = await compute_archetype_routing(user_request)
            ui_vibe = await compute_ui_vibe_routing(user_request)
            fallback_intent["archetypeRouting"] = archetype
            fallback_intent["uiVibeRouting"] = ui_vibe
        except Exception as e:
            log("ANALYSIS", f"Attention routing failed in exception fallback: {e}", project_id=project_id)
        
        await WorkflowStateManager.set_intent(project_id, fallback_intent)
        await WorkflowStateManager.set_original_request(project_id, user_request)
    
    return StepResult(
        nextstep=WorkflowStep.ARCHITECTURE,
        turn=current_turn + 1,
    )
