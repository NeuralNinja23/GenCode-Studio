# app/orchestration/healing_pipeline.py
"""
HealingPipeline - High-level healing orchestrator

Coordinates self-healing: error -> strategy -> repair -> evolution
Delegates actual repairs to SelfHealingManager and fallback agents.

Refactored: Uses centralized entity discovery and FallbackModelAgent.
"""

from pathlib import Path
from typing import Optional, Callable, Dict, Tuple
import re

from app.core.logging import log
from app.orchestration.error_router import ErrorRouter
from app.orchestration.self_healing_manager import SelfHealingManager
from app.orchestration.fallback_router_agent import FallbackRouterAgent
from app.orchestration.fallback_api_agent import FallbackAPIAgent
from app.orchestration.fallback_model_agent import FallbackModelAgent

# T-AM Integration for constraint mutation
from app.arbormind.t_am_operators import build_default_tam_operators
from app.arbormind.v_value_schema import VValue

# CENTRALIZED ENTITY DISCOVERY (fallback only)
from app.utils.entity_discovery import discover_primary_entity, get_entity_plural


class HealingPipeline:
    """Coordinates self-healing: error → strategy → repair → evolution"""
    
    def __init__(self, project_path: Path, llm_caller: Optional[Callable[[str, str], str]] = None):
        self.project_path = project_path
        self.llm_caller = llm_caller
        self.error_router = ErrorRouter()
        self.healing_manager = SelfHealingManager(project_path, llm_caller)
        self.tam_ops = build_default_tam_operators()
        self.fallback_router = FallbackRouterAgent()
        self.fallback_api = FallbackAPIAgent()
        self.fallback_model = FallbackModelAgent()
        self.last_repair_decision_id = None
        self.last_archetype = "unknown"
    
    async def attempt_heal(self, step: str, error_log: str = "", archetype: str = "unknown", retries: int = 0) -> Optional[str]:
        """Attempt to heal failed step. Returns SELF_HEALED or generated code."""
        artifact = self.error_router.route(step)
        if artifact == "noop":
            log("HEAL", f"⚠️ No repair route for step {step}")
            return None
        
        # 🎯 SELF-EVOLUTION: ErrorRouter + T-AM
        strategy_id = "generic_fix"
        strategy_params = {}
        repair_decision_id = ""
        
        try:
            result = await self.error_router.decide_repair_strategy(error_log, archetype=archetype, retries=retries)
            strategy_id = result.get("selected", "generic_fix")
            strategy_params = result.get("value", {})
            repair_decision_id = result.get("decision_id", "")
            am_mode = result.get("mode", "standard")
            
            self.last_repair_decision_id = repair_decision_id
            self.last_archetype = archetype
            
            if am_mode != "standard":
                log("HEAL", f"🤖 AM Mode {am_mode.upper()}")
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
        
        # 🎯 T-AM: Mutate strategy after failures
        if retries >= 2:
            strategy_params = self._maybe_mutate_config_after_failures(strategy_params, retries)
        
        log("HEAL", f"🔧 Attempting to heal {step} → {artifact} (Strategy: {strategy_id})")
        
        # 🩹 Attempt explicit self-healing FIRST
        try:
            healed = self.healing_manager.repair(artifact, strategy_id=strategy_id, params=strategy_params)
        except TypeError:
            # Backward compat: repair() doesn't support params yet
            healed = self.healing_manager.repair(artifact)
        
        if healed:
            log("HEAL", f"✅ Self-healing succeeded for {artifact}")
            self._report_healing_outcome(repair_decision_id, success=True, quality_score=8.0, 
                                        details=f"Self-healing succeeded for {artifact} using {strategy_id}")
            return "SELF_HEALED"
        
        log("HEAL", f"⚠️ Self-healing failed for {artifact}, trying fallback agent")
        
        # 🛠️ FALLBACK: DYNAMIC entity from mock.js → contracts → generic
        fallback_code = self._fallback(step)
        if fallback_code:
            log("HEAL", f"✅ Fallback agent succeeded for {step}")
            self._report_healing_outcome(repair_decision_id, success=True, quality_score=6.0,
                                        details=f"Fallback succeeded for {step} after self-healing failed")
            return fallback_code
        
        log("HEAL", f"❌ All healing options exhausted for {step}")
        self._report_healing_outcome(repair_decision_id, success=False, quality_score=2.0,
                                    details=f"All healing options failed for {step}")
        return None
    
    # NOTE: Entity discovery methods (_get_primary_entity_safe, _extract_entity_from_mock, 
    # _max_entity_by_frequency) were removed. Now using centralized discover_primary_entity()
    # from app.utils.entity_discovery. This eliminates duplication and ensures consistency.
    
    # ════════════════════════════════════════════════════════════════════════
    # FALLBACK GENERATION
    # ═════════════════════════════════════════════════════════════════════════
    
    def _fallback(self, step: str) -> Optional[str]:
        """Fallback generation using centralized entity discovery."""
        step_lower = step.lower()
        
        if "router" in step_lower or "implementation" in step_lower or "backend_vertical" in step_lower:
            # Use centralized entity discovery
            entity_name, model_name = discover_primary_entity(self.project_path)
            if not entity_name:
                log("HEAL", "❌ Cannot generate fallback - no entity found!")
                return None
            
            entity_plural = get_entity_plural(entity_name)
            log("HEAL", f"🎯 FALLBACK: {entity_name} → {entity_plural}")
            
            # Models - check if model class is ACTUALLY defined
            models_path = self.project_path / "backend" / "app" / "models.py"
            needs_model = True
            if models_path.exists():
                content = models_path.read_text(encoding='utf-8')
                for line in content.splitlines():
                    stripped = line.lstrip()
                    if not stripped or stripped.startswith('#'):
                        continue
                    if re.match(rf'class\s+{model_name}\s*\(', stripped):
                        needs_model = False
                        log("HEAL", f"✅ Model {model_name} already exists in models.py")
                        break
            
            if needs_model:
                model_code = self.fallback_model.generate_for_entity(entity_name, model_name)
                models_path.parent.mkdir(parents=True, exist_ok=True)
                models_path.write_text(model_code, encoding='utf-8')
                log("HEAL", f"📋 Fallback model written: {model_name} ({len(model_code)} chars)")
            
            # Router - check if valid router already exists
            router_path = self.project_path / "backend" / "app" / "routers" / f"{entity_plural}.py"
            if router_path.exists():
                existing_content = router_path.read_text(encoding='utf-8')
                if re.search(r'router\s*=\s*APIRouter', existing_content):
                    log("HEAL", f"✅ Valid router {entity_plural}.py already exists - skipping")
                    return existing_content
            
            router_code = self.fallback_router.generate_for_entity(entity_name, model_name)
            router_path.parent.mkdir(parents=True, exist_ok=True)
            router_path.write_text(router_code, encoding='utf-8')
            log("HEAL", f"📋 Fallback router written: {entity_plural}.py ({len(router_code)} chars)")
            
            self._generate_fallback_tests(entity_name, entity_plural)
            return router_code
        
        elif "integration" in step_lower or "api" in step_lower:
            # Use centralized entity discovery
            entity_name, model_name = discover_primary_entity(self.project_path)
            if not entity_name:
                log("HEAL", "❌ Cannot generate API fallback - no entity found!")
                return None
            
            entity_plural = get_entity_plural(entity_name)
            api_code = self.fallback_api.generate_for_entity(entity_name, entity_plural)
            api_path = self.project_path / "frontend" / "src" / "lib" / "api.js"
            api_path.parent.mkdir(parents=True, exist_ok=True)
            api_path.write_text(api_code, encoding='utf-8')
            log("HEAL", f"📋 Fallback API client written for {entity_plural} ({len(api_code)} chars)")
            return api_code
        
        log("HEAL", f"⚠️ No fallback agent for step: {step}")
        return None
    
    # NOTE: _generate_fallback_model was removed - now using FallbackModelAgent
    # This consolidates model generation into a single source of truth

    
    def _generate_fallback_tests(self, entity: str, entity_plural: str) -> None:
        """Generate fallback test_api.py to prevent 'no tests ran'."""
        tests_dir = self.project_path / "backend" / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        test_file = tests_dir / "test_api.py"
        
        # Don't overwrite valid tests
        if test_file.exists():
            content = test_file.read_text(encoding='utf-8')
            if re.search(r'async\s+def\s+test_|def\s+test_', content):
                log("HEAL", "✅ Valid test file already exists - skipping")
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
        "name": fake.sentence(),
        "description": fake.paragraph(),
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
            test_file.write_text(test_content, encoding='utf-8')
            log("HEAL", f"📋 Fallback test file written: test_api.py ({len(test_content)} chars)")
        except Exception as e:
            log("HEAL", f"⚠️ Failed to write fallback test file: {e}")
    
    # ════════════════════════════════════════════════════════════════════════
    # T-AM & SELF-EVOLUTION
    # ════════════════════════════════════════════════════════════════════════
    
    def _maybe_mutate_config_after_failures(self, config: Dict, failure_count: int) -> Dict:
        """T-AM: Mutate strategy config after repeated failures."""
        if failure_count < 2:
            return config
        
        try:
            v = VValue.from_dict(config)
            tam = self.tam_ops["INVERT_STRICT_MODE"]
            mutated = tam.apply(v)
            log("HEAL", f"🔮 T-AM mutation after {failure_count} failures: {tam.name}")
            return mutated.to_dict()
        except Exception as e:
            log("HEAL", f"⚠️ T-AM mutation failed: {e}")
            return config
    
    def _report_healing_outcome(self, decision_id: str, success: bool, quality_score: float, details: str) -> None:
        """Report outcome for self-evolution."""
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
    
    # ════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ════════════════════════════════════════════════════════════════════════
    
    def can_heal(self, step: str) -> bool:
        """Check if a step can be healed."""
        return self.error_router.is_repairable(step)
    
    def get_healing_options(self, step: str) -> list:
        """Get available healing options for a step."""
        options = []
        if self.error_router.is_repairable(step):
            options.append("self_healing")
            options.append("fallback_template")
        return options
    
    async def heal_all(self, failed_steps: list) -> dict:
        """Heal all failed steps in priority order."""
        ordered_steps = self.error_router.get_repair_order(failed_steps)
        results = {}
        for step in ordered_steps:
            result = await self.attempt_heal(step, "", self.last_archetype)
            results[step] = {
                "healed": result is not None,
                "method": "self_healed" if result == "SELF_HEALED" else ("fallback" if result else "failed"),
            }
        return results
