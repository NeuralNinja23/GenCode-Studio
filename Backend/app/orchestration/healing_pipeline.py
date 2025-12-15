# app/orchestration/healing_pipeline.py
"""
HealingPipeline - High-level healing orchestrator

Coordinates self-healing: error -> strategy -> repair -> evolution
Delegates actual repairs to SelfHealingManager and fallback agents.

Refactored: Uses centralized entity discovery and FallbackModelAgent.
"""

from pathlib import Path
from typing import Optional, Callable, Dict, Tuple
from datetime import datetime
import json
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
from app.utils.entity_discovery import discover_primary_entity, get_entity_plural, extract_all_models_from_models_py


class HealingPipeline:
    """Coordinates self-healing: error → strategy → repair → evolution"""
    
    def __init__(self, project_path: Path, llm_caller: Optional[Callable[[str, str], str]] = None, project_id: Optional[str] = None):
        self.project_path = project_path
        self.project_id = project_id or project_path.name  # LOOP CONSOLIDATION: For budget lookup
        self.llm_caller = llm_caller
        self.error_router = ErrorRouter()
        self.healing_manager = SelfHealingManager(project_path, llm_caller, project_id=self.project_id)
        self.tam_ops = build_default_tam_operators()
        self.fallback_router = FallbackRouterAgent()
        self.fallback_api = FallbackAPIAgent()
        self.fallback_model = FallbackModelAgent()
        self.last_repair_decision_id = None
        self.last_archetype = "unknown"
        
        # PHASE 5: Healing memory - track attempts and prevent duplicates
        self.attempt_history: list = []  # Track all healing attempts
        self.code_hashes: set = set()     # Track code hashes to detect duplicates
        
        # PERSISTENT MEMORY: Load from JSON file
        self.memory_path = project_path / ".gencode" / "healing_memory.json"
        self._load_healing_memory()
    
    async def attempt_heal(
        self, 
        step: str, 
        error_log: str = "", 
        archetype: str = "unknown", 
        test_failures: Optional[str] = None  # Test output feedback for Derek
    ) -> Optional[str]:
        """
        Attempt to heal failed step. Returns SELF_HEALED or generated code.
        
        LOOP CONSOLIDATION:
        - Single attempt, no internal retries
        - Budget-controlled (fails fast when exhausted)
        - ArborMind selects strategy once (no escalation)
        - Caller (testing_backend) is the only retry loop
        """
        from app.orchestration.healing_budget import get_healing_budget
        
        # ════════════════════════════════════════════════════════════════
        # LOOP CONSOLIDATION: Check budget FIRST
        # ════════════════════════════════════════════════════════════════
        budget = get_healing_budget(self.project_id) if hasattr(self, 'project_id') else None
        if budget and budget.is_exhausted():
            log("HEAL", "🛑 Healing budget exhausted - failing fast")
            log("HEAL", budget.get_exhaustion_diagnostic())
            return None
        
        artifact = self.error_router.get_repair_artifact(step)
        if artifact == "noop":
            log("HEAL", f"⚠️ No repair route for step {step}")
            return None
        
        # Store test failures in healing manager for Derek feedback
        if test_failures and hasattr(self.healing_manager, 'latest_test_failures'):
            self.healing_manager.latest_test_failures = test_failures
            log("HEAL", f"📋 Stored {len(test_failures)} chars of test output for Derek")
        
        # ════════════════════════════════════════════════════════════════
        # LOOP CONSOLIDATION: ArborMind SELECTS once (no escalation)
        # Strategy selection is now based on error depth, not retry count
        # ════════════════════════════════════════════════════════════════
        strategy_id = "generic_fix"
        strategy_params = {}
        repair_decision_id = ""
        
        try:
            # Pass error_log for depth analysis, archetype for context
            # retries=0 always - no escalation, just selection
            result = await self.error_router.decide_repair_strategy(
                error_log, 
                archetype=archetype, 
                retries=0,  # LOOP CONSOLIDATION: No escalation
                context={"test_failures": test_failures} if test_failures else None
            )
            strategy_id = result.get("selected", "generic_fix")
            strategy_params = result.get("value", {})
            repair_decision_id = result.get("decision_id", "")
            am_mode = result.get("mode", "standard")
            
            self.last_repair_decision_id = repair_decision_id
            self.last_archetype = archetype
            
            log("HEAL", f"🧠 Strategy selected: '{strategy_id}' (mode: {am_mode})")
            log("HEAL", f"   ⚙️ Params: {strategy_params}")
            if result.get("evolved"):
                log("HEAL", "   🧬 Strategy parameters evolved from learning")
                
        except Exception as e:
            log("HEAL", f"⚠️ Strategy selection failed: {e}")
        
        log("HEAL", f"🔧 Healing {step} → {artifact} (Strategy: {strategy_id})")
        
        # ════════════════════════════════════════════════════════════════
        # SINGLE ATTEMPT: Self-healing (no internal retries)
        # ════════════════════════════════════════════════════════════════
        try:
            healed = await self.healing_manager.repair(artifact, strategy_id=strategy_id, params=strategy_params)
        except TypeError:
            # Backward compat: repair() doesn't support params yet or async
            try:
                healed = await self.healing_manager.repair(artifact)
            except TypeError:
                healed = self.healing_manager.repair(artifact)
        
        if healed:
            log("HEAL", f"✅ Healing succeeded for {artifact}")
            
            # Record successful attempt
            self._record_healing_attempt(step, artifact, strategy_id, "self_heal", success=True)
            
            self._report_healing_outcome(repair_decision_id, success=True, quality_score=8.0, 
                                        details=f"Healing succeeded for {artifact} using {strategy_id}")
            return "SELF_HEALED"
        
        # ════════════════════════════════════════════════════════════════
        # FALLBACK: Only for non-critical/boilerplate files
        # ════════════════════════════════════════════════════════════════
        if not self._is_critical_step(step):
            log("HEAL", f"⚠️ Primary healing failed, trying fallback (non-critical step)")
            fallback_code = self._fallback(step)
            if fallback_code:
                # Check for duplicate fallback code
                if self._is_duplicate_code(fallback_code):
                    log("HEAL", f"⏭️ Skipping fallback - identical to previous attempt")
                    return None
                
                log("HEAL", f"✅ Fallback succeeded for {step}")
                self._record_healing_attempt(step, artifact, strategy_id, "fallback", success=True, code=fallback_code)
                self._report_healing_outcome(repair_decision_id, success=True, quality_score=6.0,
                                            details=f"Fallback succeeded for {step}")
                return fallback_code
        else:
            log("HEAL", f"⚠️ Primary healing failed for CRITICAL step {step} - no fallback allowed")
        
        log("HEAL", f"❌ Healing failed for {step} - outer loop will decide next action")
        self._record_healing_attempt(step, artifact, strategy_id, "none", success=False)
        self._report_healing_outcome(repair_decision_id, success=False, quality_score=2.0,
                                    details=f"Healing failed for {step}")
        return None
    
    # NOTE: Entity discovery methods (_get_primary_entity_safe, _extract_entity_from_mock, 
    # _max_entity_by_frequency) were removed. Now using centralized discover_primary_entity()
    # from app.utils.entity_discovery. This eliminates duplication and ensures consistency.
    
    # ════════════════════════════════════════════════════════════════════════
    # FALLBACK GENERATION (PHASE 3: SELECTIVE - BOILERPLATE ONLY)
    # ═════════════════════════════════════════════════════════════════════════
    
    def _fallback(self, step: str) -> Optional[str]:
        """
        PHASE 3: Selective fallback - ONLY for boilerplate files.
        
        Critical files (models, routers, tests) should NEVER use fallback.
        Only safe boilerplate files (database.py, __init__.py) can use templates.
        
        Returns:
            Generated code if fallback is allowed, None if step needs Derek
        """
        step_lower = step.lower()
        
        # PHASE 3: Check if this step is for a critical file
        if self._is_critical_step(step):
            log("HEAL", f"⚠️ FALLBACK BLOCKED for critical step: {step}")
            log("HEAL", f"   Critical files MUST be generated by Derek")
            return None  # Force Derek retry instead
        
        # PHASE 3: Only allow fallback for boilerplate steps
        if not self._is_boilerplate_step(step):
            log("HEAL", f"⚠️ FALLBACK not applicable for step: {step}")
            return None
        
        log("HEAL", f"✅ Fallback ALLOWED for boilerplate step: {step}")
        
        # Original fallback logic for safe files only
        if "router" in step_lower or "implementation" in step_lower or "backend_vertical" in step_lower:
            # This should not happen since routers are critical, but keep for safety
            log("HEAL", "❌ Router/implementation steps should use Derek, not fallback")
            return None
        
        elif "integration" in step_lower or "api" in step_lower:
            # Frontend API client - boilerplate OK
            #
            # BUG FIX: Use actual models from models.py instead of
            # discover_primary_entity which may return wrong entity from mock.js
            actual_models = extract_all_models_from_models_py(self.project_path)
            if actual_models:
                model_name = actual_models[0]
                entity_name = model_name.lower()
            else:
                # Fallback to discover_primary_entity
                entity_name, model_name = discover_primary_entity(self.project_path)
                if not entity_name:
                    log("HEAL", "❌ Cannot generate fallback - no entity found!")
                    return None
            
            entity_plural = get_entity_plural(entity_name)
            
            api_code = self.fallback_api.generate_for_entity(entity_name, entity_plural)
            api_path = self.project_path / "frontend" / "src" / "lib" / "api.ts"
            api_path.parent.mkdir(parents=True, exist_ok=True)
            api_path.write_text(api_code, encoding='utf-8')
            log("HEAL", f"📋 Fallback API written: api.ts ({len(api_code)} chars)")
            return api_code
        
        log("HEAL", f"⚠️ No fallback handler for step: {step}")
        return None
    
    def _is_critical_step(self, step: str) -> bool:
        """
        PHASE 3: Check if step involves critical files.
        
        Critical steps MUST use Derek, never fallback.
        """
        critical_keywords = [
            "backend_implementation",
            "backend_vertical", 
            "model",
            "router",
            "test",
        ]
        
        step_lower = step.lower()
        return any(keyword in step_lower for keyword in critical_keywords)
    
    def _is_boilerplate_step(self, step: str) -> bool:
        """
        PHASE 3: Check if step involves boilerplate files.
        
        Boilerplate steps CAN use fallback templates safely.
        """
        boilerplate_keywords = [
            "integration",  # Frontend API client
            "api",          # API utilities
            "database",     # Database init
            "db",           # DB utilities
        ]
        
        step_lower = step.lower()
        return any(keyword in step_lower for keyword in boilerplate_keywords)
    
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
    
    # ════════════════════════════════════════════════════════════════════════
    # PHASE 5: HEALING MEMORY HELPERS
    # ════════════════════════════════════════════════════════════════════════
    
    def _record_healing_attempt(
        self, 
        step: str, 
        artifact: str, 
        strategy: str, 
        method: str,  # "self_heal", "fallback", "none"
        success: bool,
        code: Optional[str] = None
    ):
        """
        PHASE 5: Record a healing attempt in memory.
        
        Tracks what was tried to prevent duplicate work.
        """
        from datetime import datetime
        import hashlib
        
        attempt = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "artifact": artifact,
            "strategy": strategy,
            "method": method,
            "success": success,
        }
        
        if code:
            # Hash code to detect duplicates
            code_hash = hashlib.md5(code.encode()).hexdigest()
            attempt["code_hash"] = code_hash
            self.code_hashes.add(code_hash)
        
        self.attempt_history.append(attempt)
        
        # PERSISTENT: Save to disk after each attempt
        self._save_healing_memory()
        
        # Show summary if we have multiple attempts
        if len(self.attempt_history) > 1:
            log("HEAL", f"📊 Healing History: {len(self.attempt_history)} attempts")
    
    def _is_duplicate_code(self, code: str) -> bool:
        """
        PHASE 5: Check if code is identical to a previous attempt.
        
        Returns True if we've already tried this exact code.
        """
        import hashlib
        
        code_hash = hashlib.md5(code.encode()).hexdigest()
        return code_hash in self.code_hashes
    
    def get_healing_summary(self) -> dict:
        """
        PHASE 5: Get summary of healing attempts.
        
        Useful for debugging and metrics.
        """
        if not self.attempt_history:
            return {"total": 0, "successful": 0, "failed": 0}
        
        successful = sum(1 for a in self.attempt_history if a["success"])
        failed = len(self.attempt_history) - successful
        
        methods_used = {}
        for attempt in self.attempt_history:
            method = attempt["method"]
            methods_used[method] = methods_used.get(method, 0) + 1
        
        return {
            "total": len(self.attempt_history),
            "successful": successful,
            "failed": failed,
            "methods_used": methods_used,
            "unique_code_variants": len(self.code_hashes)
        }
    
    # ════════════════════════════════════════════════════════════════════════
    # PERSISTENT MEMORY - Load/Save from JSON
    # ════════════════════════════════════════════════════════════════════════
    
    def _load_healing_memory(self):
        """Load healing memory from JSON file (persistent across runs)."""
        if not self.memory_path.exists():
            log("HEAL", "📂 No healing memory found - starting fresh")
            return
        
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            
            # Restore attempt history
            self.attempt_history = data.get("attempt_history", [])
            
            # Restore code hashes
            self.code_hashes = set(data.get("code_hashes", []))
            
            log("HEAL", f"📂 Loaded healing memory: {len(self.attempt_history)} attempts, {len(self.code_hashes)} code variants")
            
        except Exception as e:
            log("HEAL", f"⚠️ Could not load healing memory: {e}")
            # Start fresh on error
            self.attempt_history = []
            self.code_hashes = set()
    
    def _save_healing_memory(self):
        """Save healing memory to JSON file (persistent across runs)."""
        try:
            self.memory_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "attempt_history": self.attempt_history,
                "code_hashes": list(self.code_hashes),
                "last_updated": datetime.now().isoformat()
            }
            
            self.memory_path.write_text(
                json.dumps(data, indent=2),
                encoding="utf-8"
            )
            
        except Exception as e:
            log("HEAL", f"⚠️ Could not save healing memory: {e}")
    
    def clear_healing_memory(self):
        """
        Clear healing memory (call after successful workflow completion).
        
        This prevents memory from previous runs affecting new projects.
        """
        self.attempt_history = []
        self.code_hashes = set()
        self._save_healing_memory()
        log("HEAL", "🔄 Cleared healing memory")

