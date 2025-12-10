# app/workflow/healing_pipeline.py
"""
FAST v2 Healing Pipeline

Coordinates the self-healing process:
1. Error attribution (which artifact failed?)
2. Self-healing attempt (LLM regeneration)
3. Fallback to templates (last resort)

Usage:
    healer = HealingPipeline(project_path, llm_caller)
    
    if step_failed:
        result = healer.attempt_heal(step_name)
        if result == "SELF_HEALED":
            # Files were written directly
        elif result:
            # result contains the generated code
        else:
            # Healing failed
"""
from pathlib import Path
from typing import Optional, Callable

from app.core.logging import log
from app.workflow.error_router import ErrorRouter
from app.workflow.self_healing_manager import SelfHealingManager
from app.workflow.engine_v2.fallback_router_agent import FallbackRouterAgent
from app.workflow.engine_v2.fallback_api_agent import FallbackAPIAgent


class HealingPipeline:
    """
    Coordinates:
    - error mapping (step → artifact)
    - self-healing attempts
    - fallback agents
    - retry logic
    """
    
    def __init__(
        self, 
        project_path: Path,
        llm_caller: Optional[Callable[[str], str]] = None,
    ):
        self.project_path = project_path
        self.llm_caller = llm_caller
        
        self.error_router = ErrorRouter()
        self.healing_manager = SelfHealingManager(
            project_path=project_path,
            llm_caller=llm_caller,
        )
        
        # Fallback agents for direct template generation
        self.fallback_router = FallbackRouterAgent()
        self.fallback_api = FallbackAPIAgent()

    # -------------------------------------------------------------
    def attempt_heal(self, step: str) -> Optional[str]:
        """
        Attempt to heal a failed step.
        
        Returns:
            - "SELF_HEALED" if self-healing wrote files directly
            - Generated code string if fallback agent succeeded
            - None if all healing options failed
        """
        artifact = self.error_router.route(step)

        if artifact == "noop":
            log("HEAL", f"⚠️ No repair route for step: {step}")
            return None

        log("HEAL", f"🔧 Attempting to heal {step} → {artifact}")

        # Attempt explicit self-healing first
        healed = self.healing_manager.repair(artifact)
        if healed:
            log("HEAL", f"✅ Self-healing succeeded for {artifact}")
            return "SELF_HEALED"

        log("HEAL", f"⚠️ Self-healing failed for {artifact}, trying fallback agent")

        # Final fallback - direct template
        fallback_code = self._fallback(step)
        if fallback_code:
            log("HEAL", f"✅ Fallback agent succeeded for {step}")
            return fallback_code

        log("HEAL", f"❌ All healing options exhausted for {step}")
        return None

    # -------------------------------------------------------------
    def _fallback(self, step: str) -> Optional[str]:
        """Use step-specific fallback agent with DYNAMIC entity names."""
        step_lower = step.lower()
        
        if "router" in step_lower:
            # DYNAMIC: Discover primary entity
            entity_name, model_name = self._discover_primary_entity()
            entity_plural = entity_name + "s" if not entity_name.endswith("s") else entity_name
            
            code = self.fallback_router.generate_for_entity(entity_name, model_name)
            # Write to DYNAMIC path
            router_path = self.project_path / "backend" / "app" / "routers" / f"{entity_plural}.py"
            router_path.parent.mkdir(parents=True, exist_ok=True)
            router_path.write_text(code, encoding="utf-8")
            log("HEAL", f"📋 Fallback router written: {entity_plural}.py ({len(code)} chars)")
            return code

        if "integration" in step_lower or "api" in step_lower:
            # DYNAMIC: Discover primary entity for API endpoints
            entity_name, model_name = self._discover_primary_entity()
            entity_plural = entity_name + "s" if not entity_name.endswith("s") else entity_name
            
            code = self.fallback_api.generate_for_entity(entity_name, entity_plural)
            # Write directly
            api_path = self.project_path / "frontend" / "src" / "lib" / "api.js"
            api_path.parent.mkdir(parents=True, exist_ok=True)
            api_path.write_text(code, encoding="utf-8")
            log("HEAL", f"📋 Fallback API client written for {entity_plural} ({len(code)} chars)")
            return code

        log("HEAL", f"⚠️ No fallback agent for {step}")
        return None
    
    def _discover_primary_entity(self) -> tuple:
        """
        Discover primary entity from models.py.
        Returns: (entity_name, model_name) e.g. ("task", "Task")
        """
        import re
        models_path = self.project_path / "backend" / "app" / "models.py"
        
        if models_path.exists():
            try:
                content = models_path.read_text(encoding="utf-8")
                matches = re.findall(r"class\s+(\w+)\s*\(\s*Document\s*\)", content)
                if matches:
                    model_name = matches[0]
                    log("HEAL", f"🔍 Discovered primary model: {model_name}")
                    return (model_name.lower(), model_name)
            except Exception as e:
                log("HEAL", f"⚠️ Error reading models.py: {e}")
        
        log("HEAL", "⚠️ Using default entity 'item'")
        return ("item", "Item")

    # -------------------------------------------------------------
    def can_heal(self, step: str) -> bool:
        """Check if a step can be healed."""
        return self.error_router.is_repairable(step)

    # -------------------------------------------------------------
    def get_healing_options(self, step: str) -> list:
        """Get available healing options for a step."""
        options = []
        
        if self.error_router.is_repairable(step):
            options.append("self_healing")
            options.append("fallback_template")
        
        return options

    # -------------------------------------------------------------
    def heal_all(self, failed_steps: list) -> dict:
        """
        Attempt to heal all failed steps in priority order.
        
        Returns:
            Dict of {step: result} for each step
        """
        results = {}
        
        # Sort by repair priority
        ordered_steps = self.error_router.get_repair_order(failed_steps)
        
        for step in ordered_steps:
            result = self.attempt_heal(step)
            results[step] = {
                "healed": result is not None,
                "method": "self_healed" if result == "SELF_HEALED" else "fallback" if result else "failed",
            }
        
        return results
