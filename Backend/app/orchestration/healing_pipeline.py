# app/orchestration/healing_pipeline.py
"""
FAST v2 Healing Pipeline (Self-Evolving)

Coordinates the self-healing process:
1. Error attribution (which artifact failed?)
2. Self-healing attempt (LLM regeneration)
3. Fallback to templates (last resort)

SELF-EVOLUTION: Tracks repair strategy decisions and learns from
outcomes to improve future healing attempts.

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
import re

from app.core.logging import log
from app.orchestration.error_router import ErrorRouter
from app.orchestration.self_healing_manager import SelfHealingManager
from app.orchestration.fallback_router_agent import FallbackRouterAgent
from app.orchestration.fallback_api_agent import FallbackAPIAgent

# CENTRALIZED ENTITY DISCOVERY (replaces duplicated method)
from app.utils.entity_discovery import discover_primary_entity, get_entity_plural


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
        
        # Self-evolution tracking
        self._last_repair_decision_id = ""
        self._last_archetype = "unknown"

    # -------------------------------------------------------------
    async def attempt_heal(
        self, 
        step: str, 
        error_log: str = "",
        archetype: str = "unknown",
        retries: int = 0
    ) -> Optional[str]:
        """
        Attempt to heal a failed step.
        
        Args:
            step: The failed step name
            error_log: The error message or log trace
            archetype: Project archetype for self-evolution context
            retries: Current retry count (for AM escalation)
        
        Returns:
            - "SELF_HEALED" if self-healing wrote files directly
            - Generated code string if fallback agent succeeded
            - None if all healing options failed
        """
        artifact = self.error_router.route(step)

        if artifact == "noop":
            log("HEAL", f"⚠️ No repair route for step: {step}")
            return None

        # ════════════════════════════════════════════════════════
        # PHASE 3.2: Attention-Selected Repair Strategy (AM-Enhanced)
        # ════════════════════════════════════════════════════════
        strategy_id = "generic_fix"
        strategy_params = {}
        repair_decision_id = ""
        am_mode = "standard"
        
        if error_log:
            try:
                # Returns dict with 'selected', 'value', 'decision_id', and 'mode'
                result = await self.error_router.decide_repair_strategy(
                    error_log, 
                    archetype=archetype,
                    retries=retries  # Pass retries for AM escalation
                )
                strategy_id = result.get("selected", "generic_fix")
                strategy_params = result.get("value", {})
                repair_decision_id = result.get("decision_id", "")
                am_mode = result.get("mode", "standard")
                
                # Store for outcome reporting
                self._last_repair_decision_id = repair_decision_id
                self._last_archetype = archetype
                
                # Log AM mode if not standard
                if am_mode != "standard":
                    log("HEAL", f"🧠 AM Mode: {am_mode.upper()}")
                    if am_mode == "exploratory" and result.get("source_archetypes"):
                        log("HEAL", f"   📚 Foreign patterns from: {result['source_archetypes']}")
                    if am_mode == "transformational" and result.get("mutation"):
                        log("HEAL", f"   🔮 Mutation: {result['mutation'].get('description', 'N/A')}")
                
                log("HEAL", f"🧠 Attention selected strategy: '{strategy_id}'")
                log("HEAL", f"   ⚙️ Params: {strategy_params}")
                if result.get("evolved"):
                    log("HEAL", "   🧬 Strategy parameters evolved from learning")
            except Exception as e:
                log("HEAL", f"⚠️ Strategy selection failed: {e}")

        log("HEAL", f"🔧 Attempting to heal {step} → {artifact} (Strategy: {strategy_id})")

        # Attempt explicit self-healing first
        try:
            # Pass synthesized parameters to repair manager
            healed = self.healing_manager.repair(
                artifact, 
                strategy_id=strategy_id, 
                params=strategy_params
            )
        except TypeError:
             # Fallback if repair doesn't support params yet
             healed = self.healing_manager.repair(artifact)
             
        if healed:
            log("HEAL", f"✅ Self-healing succeeded for {artifact}")
            
            # SELF-EVOLUTION: Report success
            self._report_healing_outcome(
                repair_decision_id,
                success=True,
                quality_score=8.0,
                details=f"Self-healing succeeded for {artifact} using {strategy_id}"
            )
            
            return "SELF_HEALED"
            
        # ... fallback logic continues ...

        log("HEAL", f"⚠️ Self-healing failed for {artifact}, trying fallback agent")

        # Final fallback - direct template
        fallback_code = self._fallback(step)
        if fallback_code:
            log("HEAL", f"✅ Fallback agent succeeded for {step}")
            
            # SELF-EVOLUTION: Report partial success (fallback worked but self-healing didn't)
            self._report_healing_outcome(
                repair_decision_id,
                success=True,
                quality_score=6.0,
                details=f"Fallback succeeded for {step} after self-healing failed"
            )
            
            return fallback_code

        log("HEAL", f"❌ All healing options exhausted for {step}")
        
        # SELF-EVOLUTION: Report failure
        self._report_healing_outcome(
            repair_decision_id,
            success=False,
            quality_score=2.0,
            details=f"All healing options failed for {step}"
        )
        
        return None
    
    def _report_healing_outcome(
        self,
        decision_id: str,
        success: bool,
        quality_score: float,
        details: str
    ) -> None:
        """
        Report the outcome of a healing attempt for self-evolution.
        """
        if not decision_id:
            return
        
        try:
            self.error_router.report_repair_outcome(
                decision_id=decision_id,
                success=success,
                quality_score=quality_score,
                details=details
            )
        except Exception as e:
            log("HEAL", f"⚠️ Failed to report healing outcome: {e}")

    # -------------------------------------------------------------
    def _fallback(self, step: str) -> Optional[str]:
        """Use step-specific fallback agent with DYNAMIC entity names."""
        step_lower = step.lower()
        
        if "router" in step_lower or "implementation" in step_lower or "backend_vertical" in step_lower:
            # DYNAMIC: Discover primary entity using centralized utility
            entity_name, model_name = discover_primary_entity(self.project_path)
            if not entity_name:
                log("HEAL", "❌ Cannot generate fallback - no entity found!")
                return None
            entity_plural = get_entity_plural(entity_name)
            
            # ════════════════════════════════════════════════════════════
            # FIX: Create models.py FIRST (router imports from it!)
            # Check if model is actually DEFINED, not just if file exists!
            # ════════════════════════════════════════════════════════════
            models_path = self.project_path / "backend" / "app" / "models.py"
            needs_model = True
            if models_path.exists():
                # Check if the model class is actually defined (not in comments!)
                content = models_path.read_text(encoding="utf-8")
                # Process line-by-line to skip comments
                for line in content.splitlines():
                    stripped = line.lstrip()
                    if not stripped or stripped.startswith('#'):
                        continue
                    if re.match(rf'class\s+{model_name}\s*\(\s*Document\s*\)', stripped):
                        needs_model = False
                        log("HEAL", f"✅ Model {model_name} already exists in models.py")
                        break
                if needs_model:
                    log("HEAL", f"⚠️ models.py exists but {model_name} class not found - will generate")
            
            if needs_model:
                model_code = f'''# backend/app/models.py
"""
{model_name} Model - Fallback Template
Generated by HealingPipeline when LLM failed.
"""
from datetime import datetime, timezone
from typing import Optional
from beanie import Document
from pydantic import Field


class {model_name}(Document):
    """Main entity model."""
    title: str = Field(..., description="Title of the {entity_name}")
    content: str = Field(default="", description="Content/description")
    status: str = Field(default="Draft", description="Status: Draft, Active, Completed")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    
    class Settings:
        name = "{entity_plural}"
        
    class Config:
        json_schema_extra = {{
            "example": {{
                "title": "Sample {model_name}",
                "content": "Example content",
                "status": "Draft"
            }}
        }}
'''
                models_path.parent.mkdir(parents=True, exist_ok=True)
                models_path.write_text(model_code, encoding="utf-8")
                log("HEAL", f"📋 Fallback model written: models.py ({len(model_code)} chars)")
            
            # Issue #2 Fix: Check if valid router already exists before overwriting!
            router_path = self.project_path / "backend" / "app" / "routers" / f"{entity_plural}.py"
            
            if router_path.exists():
                existing_content = router_path.read_text(encoding="utf-8")
                # Check if it's a valid router (has APIRouter definition)
                if re.search(r'router\s*=\s*APIRouter\s*\(', existing_content):
                    log("HEAL", f"✅ Valid router {entity_plural}.py already exists ({len(existing_content)} chars) - skipping fallback")
                    return existing_content  # Return existing code, don't overwrite!
                else:
                    log("HEAL", f"⚠️ Router {entity_plural}.py exists but invalid - will overwrite")
            
            # Only write fallback if router doesn't exist or is invalid
            code = self.fallback_router.generate_for_entity(entity_name, model_name)
            router_path.parent.mkdir(parents=True, exist_ok=True)
            router_path.write_text(code, encoding="utf-8")
            log("HEAL", f"📋 Fallback router written: {entity_plural}.py ({len(code)} chars)")
            
            # ════════════════════════════════════════════════════════════
            # Option B: Also generate fallback test file
            # This ensures pytest doesn't fail with "no tests ran"
            # ════════════════════════════════════════════════════════════
            self._generate_fallback_tests(entity_name, entity_plural)
            
            return code

        if "integration" in step_lower or "api" in step_lower:
            # DYNAMIC: Discover primary entity using centralized utility
            entity_name, model_name = discover_primary_entity(self.project_path)
            if not entity_name:
                log("HEAL", "❌ Cannot generate API fallback - no entity found!")
                return None
            entity_plural = get_entity_plural(entity_name)
            
            code = self.fallback_api.generate_for_entity(entity_name, entity_plural)
            # Write directly
            api_path = self.project_path / "frontend" / "src" / "lib" / "api.js"
            api_path.parent.mkdir(parents=True, exist_ok=True)
            api_path.write_text(code, encoding="utf-8")
            log("HEAL", f"📋 Fallback API client written for {entity_plural} ({len(code)} chars)")
            return code

        log("HEAL", f"⚠️ No fallback agent for {step}")
        return None
    
    # NOTE: Removed duplicated _discover_primary_entity() method (82 lines).
    # Now using centralized app.utils.entity_discovery.discover_primary_entity() instead.
    # This ensures consistent discovery logic across the entire codebase.

    # -------------------------------------------------------------
    def _generate_fallback_tests(self, entity: str, entity_plural: str) -> None:
        """
        Generate a fallback test file when healing creates model/router.
        
        This ensures pytest doesn't fail with "no tests ran" when healing
        generates backend files but no test file exists.
        """
        tests_dir = self.project_path / "backend" / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        
        test_file = tests_dir / "test_api.py"
        
        # Don't overwrite existing valid tests
        if test_file.exists():
            content = test_file.read_text(encoding="utf-8")
            if re.search(r'async\s+def\s+test_', content) or re.search(r'def\s+test_', content):
                log("HEAL", "✅ Valid test file already exists - skipping test generation")
                return
        
        test_content = f'''# backend/tests/test_api.py
"""
API Tests - Generated by HealingPipeline fallback
"""
import pytest
from faker import Faker

fake = Faker()


@pytest.mark.anyio
async def test_health_check(client):
    """Test the health check endpoint."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "healthy"


@pytest.mark.anyio
async def test_list_{entity_plural}(client):
    """Test listing {entity_plural}."""
    response = await client.get("/api/{entity_plural}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, (list, dict))


@pytest.mark.anyio
async def test_create_{entity}(client):
    """Test creating a {entity}."""
    {entity}_data = {{
        "title": fake.sentence(),
        "content": fake.paragraph(),
    }}
    response = await client.post("/api/{entity_plural}", json={entity}_data)
    assert response.status_code in [200, 201]


@pytest.mark.anyio
async def test_get_{entity}_not_found(client):
    """Test getting a non-existent {entity} returns 404."""
    fake_id = "507f1f77bcf86cd799439011"
    response = await client.get(f"/api/{entity_plural}/{{fake_id}}")
    assert response.status_code == 404
'''

        try:
            test_file.write_text(test_content, encoding="utf-8")
            log("HEAL", f"📋 Fallback test file written: test_api.py ({len(test_content)} chars)")
        except Exception as e:
            log("HEAL", f"⚠️ Failed to write fallback test file: {e}")

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
    async def heal_all(self, failed_steps: list) -> dict:
        """
        Attempt to heal all failed steps in priority order.
        
        Returns:
            Dict of {step: result} for each step
        """
        results = {}
        
        # Sort by repair priority
        ordered_steps = self.error_router.get_repair_order(failed_steps)
        
        for step in ordered_steps:
            result = await self.attempt_heal(step)
            results[step] = {
                "healed": result is not None,
                "method": "self_healed" if result == "SELF_HEALED" else "fallback" if result else "failed",
            }
        
        return results
