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
MAX_FILES_PER_STEP = 10
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

═══════════════════════════════════════════════════════
🚨 CRITICAL: UI TOKENS JSON IS REQUIRED
═══════════════════════════════════════════════════════

Your architecture.md MUST include this UI Tokens JSON block (Derek needs it!):

## UI Tokens (machine readable)

```json
{{
  "vibe": "{ui_vibe}",
  "classes": {{
    "pageBg": "<tailwind classes for page background>",
    "card": "<tailwind classes for cards>",
    "primaryButton": "<tailwind classes for primary buttons>",
    "secondaryButton": "<tailwind classes for secondary buttons>",
    "mutedText": "<tailwind classes for muted text>"
  }}
}}
```

WITHOUT this JSON block, Derek cannot implement the correct design!

═══════════════════════════════════════════════════════
ARCHITECTURE REQUIREMENTS
═══════════════════════════════════════════════════════

INCLUDE:
1. Tech Stack (React + FastAPI + MongoDB)
2. Frontend Component Hierarchy
3. Backend Module Structure
4. Database Schema Overview
5. API Endpoints Summary
6. Folder Structure
7. UI Design System (CRITICAL!)
   - The UI vibe is '{ui_vibe}' - design system MUST align with this aesthetic
   - The project archetype is '{archetype}' - use appropriate layouts
   - MUST include UI Tokens JSON block (see above)

CRITICAL OUTPUT RULES:
- You MUST follow your system prompt (Victoria) which requires {{ "thinking": "...", "files": [{{ "path": "architecture.md", "content": "full markdown architecture plan here" }}] }}
- Do NOT return "architecturePlan": "..." format.
- ONLY return {{ "thinking": "...", "files": [...] }} with architecture.md.
- INCLUDE the UI Tokens JSON block in your architecture.md!"""

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
                            log("ARCHITECTURE", "UI Tokens JSON found but missing 'classes' key - generating fallback")
                            # Fall through to fallback generation
                            json_match = None
                    
                    # Fallback: Generate default UI tokens based on detected vibe
                    if not json_match:
                        log("ARCHITECTURE", f"⚠️ No UI Tokens found - generating fallback tokens for vibe: {ui_vibe}")
                        
                        # Default tokens per vibe
                        vibe_tokens = {
                            "dark_hacker": {
                                "vibe": "dark_hacker",
                                "classes": {
                                    "pageBg": "min-h-screen bg-slate-950 text-slate-100",
                                    "card": "bg-slate-900/60 border border-slate-800 rounded-2xl shadow-lg p-6",
                                    "primaryButton": "bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold px-4 py-2 rounded-lg transition-all hover:scale-105",
                                    "secondaryButton": "border border-slate-700 hover:bg-slate-800 text-slate-100 px-4 py-2 rounded-lg transition-all",
                                    "mutedText": "text-slate-400 text-sm"
                                }
                            },
                            "minimal_light": {
                                "vibe": "minimal_light",
                                "classes": {
                                    "pageBg": "min-h-screen bg-white text-slate-900",
                                    "card": "bg-gray-50 border border-gray-200 rounded-xl shadow-sm p-6",
                                    "primaryButton": "bg-blue-600 hover:bg-blue-500 text-white font-semibold px-4 py-2 rounded-lg transition-all hover:scale-105",
                                    "secondaryButton": "border border-gray-300 hover:bg-gray-100 text-slate-700 px-4 py-2 rounded-lg transition-all",
                                    "mutedText": "text-gray-500 text-sm"
                                }
                            },
                            "modern_gradient": {
                                "vibe": "modern_gradient",
                                "classes": {
                                    "pageBg": "min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white",
                                    "card": "bg-white/10 backdrop-blur-lg border border-white/20 rounded-2xl shadow-xl p-6",
                                    "primaryButton": "bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-400 hover:to-pink-400 text-white font-semibold px-4 py-2 rounded-lg transition-all hover:scale-105",
                                    "secondaryButton": "border border-white/30 hover:bg-white/10 text-white px-4 py-2 rounded-lg transition-all",
                                    "mutedText": "text-slate-300 text-sm"
                                }
                            },
                            "enterprise_neutral": {
                                "vibe": "enterprise_neutral",
                                "classes": {
                                    "pageBg": "min-h-screen bg-gray-100 text-gray-900",
                                    "card": "bg-white border border-gray-200 rounded-lg shadow p-6",
                                    "primaryButton": "bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-4 py-2 rounded-md transition-all",
                                    "secondaryButton": "border border-gray-300 hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-md transition-all",
                                    "mutedText": "text-gray-500 text-sm"
                                }
                            },
                            "playful_colorful": {
                                "vibe": "playful_colorful",
                                "classes": {
                                    "pageBg": "min-h-screen bg-gradient-to-br from-yellow-50 via-pink-50 to-cyan-50 text-slate-800",
                                    "card": "bg-white border-2 border-pink-200 rounded-3xl shadow-lg p-6",
                                    "primaryButton": "bg-gradient-to-r from-pink-500 to-orange-500 hover:from-pink-400 hover:to-orange-400 text-white font-bold px-6 py-3 rounded-full transition-all hover:scale-110",
                                    "secondaryButton": "border-2 border-purple-300 hover:bg-purple-50 text-purple-600 px-4 py-2 rounded-full transition-all",
                                    "mutedText": "text-slate-500 text-sm"
                                }
                            }
                        }
                        
                        # Get tokens for detected vibe, default to dark_hacker
                        tokens_obj = vibe_tokens.get(ui_vibe, vibe_tokens["dark_hacker"])
                        
                        # Write the fallback tokens
                        design_dir = project_path / "frontend" / "src" / "design"
                        design_dir.mkdir(parents=True, exist_ok=True)
                        
                        tokens_path = design_dir / "tokens.json"
                        tokens_path.write_text(json.dumps(tokens_obj, indent=2), encoding="utf-8")
                        log("ARCHITECTURE", f"✅ Wrote FALLBACK design tokens to {tokens_path}")
                        
                        # Write theme.ts
                        theme_ts = f"""// Auto-generated FALLBACK UI Tokens (Victoria didn't generate them)
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
                        log("ARCHITECTURE", f"✅ Wrote FALLBACK design theme to {theme_path}")
            except Exception as e:
                log("ARCHITECTURE", f"Failed to generate design tokens: {e}")
        
        # NOTE: Architecture context now stored via CrossStepContext in FASTOrchestratorV2
        
        chat_history.append({"role": "assistant", "content": str(parsed)})
        
    except RateLimitError:
        log("ARCHITECTURE", "Rate limit exhausted - stopping workflow", project_id=project_id)
        raise
        
    except Exception as e:
        log("ARCHITECTURE", f"Victoria failed: {e}", project_id=project_id)
        raise e  # 🛑 Stop the workflow if architecture fails

    # GENCODE STUDIO PATTERN: After architecture, go to Frontend Mock (not Contracts)
    # This creates the "aha moment" for users before building backend
    return StepResult(
        nextstep=WorkflowStep.FRONTEND_MOCK,
        turn=current_turn + 1,
    )

