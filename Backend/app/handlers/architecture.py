# app/handlers/architecture.py
"""
Step 2: Victoria creates architecture plan with Marcus supervision.

This matches the legacy workflows.py step_architecture logic exactly.
"""
from pathlib import Path
from typing import Any, Dict, List

from app.core.types import ChatMessage, StepResult
from app.core.constants import WorkflowStep
from app.core.exceptions import RateLimitError
from app.handlers.base import broadcast_status
from app.core.logging import log
from app.orchestration.state import WorkflowStateManager
from app.supervision import supervised_agent_call
from app.persistence import persist_agent_output
from app.utils.parser import normalize_llm_output


# Constants from legacy
MAX_FILES_PER_STEP = 5
MAX_FILE_LINES = 400


from app.persistence.validator import validate_file_output



async def step_architecture(
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
    Step 2: Victoria creates architecture plan with Marcus supervision.
    
    Produces:
    - architecture.md with system design
    - Component hierarchy
    - Data flow diagrams
    
    Returns:
        StepResult with next step = FRONTEND_MOCK (GenCode Studio pattern: frontend-first)
        
    Raises:
        RateLimitError: If rate limited - workflow should stop
    """
    await broadcast_status(
        manager, project_id, WorkflowStep.ARCHITECTURE,
        f"Turn {current_turn}/{max_turns}: Victoria planning architecture...",
        current_turn, max_turns
    )
    
    intent = await WorkflowStateManager.get_intent(project_id) or {}
    
    # Extract attention routing results
    archetype_routing = intent.get("archetypeRouting", {})
    ui_vibe_routing = intent.get("uiVibeRouting", {})
    archetype = archetype_routing.get("top", "general")
    ui_vibe = ui_vibe_routing.get("top", "minimal_light")
    
    victoria_instructions = f"""Create a high-level architecture plan for: {user_request}
DETECTED ENTITIES: {', '.join(intent.get('entities', []))}
DOMAIN: {intent.get('domain', 'general')}
PROJECT ARCHETYPE (attention-based routing): {archetype}
UI VIBE (attention-based routing): {ui_vibe}

INCLUDE:
1. Tech Stack (React + FastAPI + MongoDB)
2. Frontend Component Hierarchy
3. Backend Module Structure
4. Database Schema Overview
5. API Endpoints Summary
6. Folder Structure
7. UI Design System (CRITICAL - see your system prompt for details!)
   - The UI vibe has been classified as '{ui_vibe}' - your design system MUST align with this aesthetic
   - The project archetype is '{archetype}' - design layouts and patterns appropriate for this type
   
CRITICAL OUTPUT RULES:
- You MUST follow your system prompt (Victoria) which requires {{ "thinking": "...", "files": [{{ "path": "architecture.md", "content": "full markdown architecture plan here" }}] }}
- Do NOT return "architecturePlan": "..." format.
- ONLY return {{ "thinking": "...", "files": [...] }} with architecture.md."""

    try:
        # Use supervised call with auto-retry
        result = await supervised_agent_call(
            project_id=project_id,
            manager=manager,
            agent_name="Victoria",
            step_name="Architecture",
            base_instructions=victoria_instructions,
            project_path=project_path,
            user_request=user_request,
            contracts="",
            max_retries=2,
        )
        
        parsed = result.get("output", {})
        if isinstance(parsed, dict) and "files" in parsed and parsed["files"]:
            # FIX: Only accept architecture.md from Victoria - discard any contracts.md
            # (Victoria sometimes adds contracts.md despite being told not to)
            parsed["files"] = [f for f in parsed["files"] if f.get("path", "").endswith("architecture.md")]
            
            if not parsed["files"]:
                log("ARCHITECTURE", "⚠️ Victoria produced no architecture.md file")
            else:
                validated = validate_file_output(parsed, WorkflowStep.ARCHITECTURE, max_files=3)
                await persist_agent_output(manager, project_id, project_path, validated, WorkflowStep.ARCHITECTURE)
            
            status = "✅ approved" if result.get("approved") else "⚠️ best effort"
            log("ARCHITECTURE", f"Victoria created architecture plan ({status}, attempt {result.get('attempt', 1)})")

            # 🔥 NEW: Generate design tokens from architecture.md
            try:
                arch_path = project_path / "architecture.md"
                if arch_path.exists():
                    md = arch_path.read_text(encoding="utf-8")
                    import re, json

                    # Try multiple patterns to find UI Tokens JSON
                    json_match = None
                    
                    # Pattern 1: "## UI Tokens" (with optional suffix like "(machine readable)")
                    json_match = re.search(
                        r"##\s*UI\s*Tokens[^\n]*[\s\S]*?```(?:json)?\s*(\{[\s\S]*?\})\s*```",
                        md,
                        re.IGNORECASE,
                    )
                    
                    # Pattern 2: Look for a JSON block with "vibe" and "classes" keys
                    if not json_match:
                        json_match = re.search(
                            r"```(?:json)?\s*(\{[^`]*\"vibe\"[^`]*\"classes\"[^`]*\})\s*```",
                            md,
                            re.IGNORECASE | re.DOTALL,
                        )
                    
                    # Pattern 3: Any JSON block near "design" or "token" in header
                    if not json_match:
                        json_match = re.search(
                            r"##\s*(?:Design|Token)[^\n]*[\s\S]*?```(?:json)?\s*(\{[\s\S]*?\})\s*```",
                            md,
                            re.IGNORECASE,
                        )
                    
                    if json_match:
                        try:
                            tokens_obj = json.loads(json_match.group(1))
                        except json.JSONDecodeError as je:
                            log("ARCHITECTURE", f"Failed to parse UI Tokens JSON: {je}")
                            tokens_obj = None
                        
                        if tokens_obj and "classes" in tokens_obj:
                            design_dir = project_path / "frontend" / "src" / "design"
                            design_dir.mkdir(parents=True, exist_ok=True)

                            # Write tokens.json
                            tokens_path = design_dir / "tokens.json"
                            tokens_path.write_text(json.dumps(tokens_obj, indent=2), encoding="utf-8")
                            log("ARCHITECTURE", f"Wrote design tokens to {tokens_path}")

                            # Write theme.ts (simple typed wrapper)
                            theme_ts = f"""// Auto-generated from architecture.md UI Tokens
import tokensJson from "./tokens.json";

export const tokens = tokensJson as {{
  vibe: string;
  classes: {{
    pageBg: string;
    card: string;
    primaryButton: string;
    secondaryButton?: string;
    mutedText?: string;
    [key: string]: string | undefined;
  }};
}};

export const ui = {{
  pageRoot: tokens.classes.pageBg,
  card: tokens.classes.card,
  primaryButton: tokens.classes.primaryButton,
  secondaryButton: tokens.classes.secondaryButton ?? tokens.classes.primaryButton,
  mutedText: tokens.classes.mutedText ?? "",
}};
"""
                            theme_path = design_dir / "theme.ts"
                            theme_path.write_text(theme_ts, encoding="utf-8")
                            log("ARCHITECTURE", f"Wrote design theme to {theme_path}")
                            
                            # NOTE: Context storage now handled via CrossStepContext in orchestrator
                        else:
                            log("ARCHITECTURE", "UI Tokens JSON found but missing 'classes' key")
                    else:
                        log("ARCHITECTURE", "No UI Tokens JSON block found in architecture.md")
            except Exception as e:
                log("ARCHITECTURE", f"Failed to generate design tokens: {e}")
        
        # NOTE: Architecture context now stored via CrossStepContext in FASTOrchestratorV2
        
        chat_history.append({"role": "assistant", "content": str(parsed)})
        
    except RateLimitError:
        log("ARCHITECTURE", "Rate limit exhausted - stopping workflow", project_id=project_id)
        raise
        
    except Exception as e:
        log("ARCHITECTURE", f"Victoria failed: {e} - continuing anyway", project_id=project_id)
    
    # GENCODE STUDIO PATTERN: After architecture, go to Frontend Mock (not Contracts)
    # This creates the "aha moment" for users before building backend
    return StepResult(
        nextstep=WorkflowStep.FRONTEND_MOCK,
        turn=current_turn + 1,
    )

