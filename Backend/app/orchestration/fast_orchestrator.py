# app/orchestration/fast_orchestrator.py
"""
FAST v2 Orchestrator - Main Entry Point (OPTION A: Integrated with Existing Handlers)

Hybrid Adaptive FAST v2 Orchestrator
-----------------------------------
- Uses EXISTING handlers (step_backend_routers, step_frontend_mock, etc.)
- Adds V2 safety features: dependency barriers, integrity checks, self-healing
- Deterministic step ordering based on task graph
- Integrated fallback + healing for critical steps
"""
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any

from app.core.constants import WorkflowStep, WSMessageType
from app.core.exceptions import RateLimitError
from app.core.types import StepResult, ChatMessage
from app.core.config import settings
from app.core.logging import log

from .task_graph import TaskGraph
from .step_contracts import StepContracts
from .critical_step_barriers import CriticalStepBarriers
from .artifact_contracts import default_contracts
from .llm_output_integrity import LLMOutputIntegrity
from .structural_compiler import StructuralCompiler
from .fallback_router_agent import FallbackRouterAgent
from .fallback_api_agent import FallbackAPIAgent
from .checkpoint import CheckpointManagerV2
from .budget_manager import BudgetManager, get_budget_manager


# Map V2 step names to WorkflowStep constants
STEP_NAME_MAP = {
    "analysis": WorkflowStep.ANALYSIS,
    "architecture": WorkflowStep.ARCHITECTURE,
    "frontend_mock": WorkflowStep.FRONTEND_MOCK,
    "backend_models": WorkflowStep.BACKEND_MODELS,
    "contracts": WorkflowStep.CONTRACTS,
    "backend_routers": WorkflowStep.BACKEND_ROUTERS,
    "backend_main": WorkflowStep.BACKEND_MAIN,
    "frontend_integration": WorkflowStep.FRONTEND_INTEGRATION,
    "screenshot_verify": WorkflowStep.SCREENSHOT_VERIFY,
    "testing_backend": WorkflowStep.TESTING_BACKEND,
    "testing_frontend": WorkflowStep.TESTING_FRONTEND,
    "preview_final": WorkflowStep.PREVIEW_FINAL,
}


class FASTOrchestratorV2:
    """
    FAST v2 Orchestrator - Uses existing handlers with V2 safety features.
    
    Key Features:
    1. Dependency barriers - Steps run only when dependencies complete
    2. Pre-step validation - Check critical files before testing steps
    3. Self-healing - Auto-repair critical files on failure
    4. Fallback agents - Template-based fallback for routers/API client
    5. Checkpointing - Save progress after each successful step
    """
    
    # Critical steps that need extra validation and healing
    CRITICAL_STEPS = {"backend_routers", "backend_main", "frontend_integration"}

    def __init__(
        self,
        project_id: str,
        manager: Any,
        project_path: Path,
        user_request: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize FAST V2 orchestrator.
        
        Uses same signature as FastWorkflowEngine for drop-in replacement.
        """
        self.project_id = project_id
        self.manager = manager
        self.project_path = project_path
        self.user_request = user_request
        self.provider = provider or settings.llm.default_provider
        self.model = model or settings.llm.default_model
        self.chat_history: List[ChatMessage] = []
        self.current_turn = 1
        self.max_turns = settings.workflow.max_turns

        # V2 Components
        self.graph = TaskGraph()
        self.contracts = StepContracts()
        self.artifact_contracts = default_contracts()
        self.integrity = LLMOutputIntegrity()
        self.compiler = StructuralCompiler()
        
        # Fallback agents
        self.fallback_router = FallbackRouterAgent()
        self.fallback_api = FallbackAPIAgent()
        
        # V2: Healing pipeline for self-repair
        from app.orchestration.healing_pipeline import HealingPipeline
        self.healer = HealingPipeline(project_path=project_path)
        
        # V2: Cross-step context for inter-step memory
        from app.orchestration.context import CrossStepContext
        self.cross_ctx = CrossStepContext.get_or_create(project_id)
        self.cross_ctx.reset()  # Fresh start for new workflow
        
        # Checkpointing
        checkpoint_dir = self.project_path / ".fast_checkpoints"
        self.checkpoint = CheckpointManagerV2(str(checkpoint_dir))
        
        # V2: Budget management for cost control (~30 INR per run)
        # Use per-project budget tracking so frontend can display per-project costs
        self.budget = get_budget_manager(project_id)

        # State tracking
        self.completed_steps: List[str] = []
        self.failed_steps: List[str] = []
        self.step_results: Dict[str, dict] = {}

    async def run(self) -> None:
        """
        Execute the FAST V2 workflow.
        
        Uses existing handlers but with V2's dependency barriers and safety features.
        """
        # Import handlers here to avoid circular imports
        from app.handlers import (
            step_analysis,
            step_architecture,
            step_frontend_mock,
            step_screenshot_verify,
            step_contracts,
            step_backend_models,
            step_backend_routers,
            step_backend_main,
            step_testing_backend,
            step_frontend_integration,
            step_testing_frontend,
            step_preview_final,
        )
        from app.orchestration.utils import broadcast_to_project

        HANDLERS = {
            "analysis": step_analysis,
            "architecture": step_architecture,
            "frontend_mock": step_frontend_mock,
            "screenshot_verify": step_screenshot_verify,
            "contracts": step_contracts,
            "backend_models": step_backend_models,
            "backend_routers": step_backend_routers,
            "backend_main": step_backend_main,
            "frontend_integration": step_frontend_integration,
            "testing_backend": step_testing_backend,
            "testing_frontend": step_testing_frontend,
            "preview_final": step_preview_final,
        }

        log("FAST-V2", f"🚀 Starting FAST V2 workflow for {self.project_id}")
        start_time = datetime.now()
        
        # V2 FEATURE: Start budget tracking for this run
        self.budget.start_run()
        self.budget.log_status("[FAST-V2]")

        await broadcast_to_project(
            self.manager,
            self.project_id,
            {
                "type": "WORKFLOW_UPDATE",
                "projectId": self.project_id,
                "message": "Starting FAST V2 workflow with dependency barriers...",
                "mode": "fast_v2",
                "budget": self.budget.get_usage_summary(),
            }
        )

        try:
            for step in self.graph.get_steps():
                log("FAST-V2", f"═══ Step: {step} ═══")

                # ════════════════════════════════════════════════════════
                # V2 FEATURE #1: DEPENDENCY BARRIER
                # ════════════════════════════════════════════════════════
                if not self.graph.is_ready(step, self.completed_steps):
                    blocking = self.graph.get_blocking(step, self.completed_steps)
                    log("FAST-V2", f"⏳ {step} waiting for: {blocking}")
                    
                    # Check if any blocking step has failed
                    if any(b in self.failed_steps for b in blocking):
                        log("FAST-V2", f"❌ {step} blocked by failed dependency")
                        self.failed_steps.append(step)
                        self.step_results[step] = {"status": "blocked", "blocked_by": blocking}
                        continue
                    
                    # Skip if dependencies not complete
                    continue

                # ════════════════════════════════════════════════════════
                # V2 FEATURE #2: BUDGET CHECK BEFORE STEP EXECUTION
                # ════════════════════════════════════════════════════════
                allowed_attempts = self.budget.allowed_attempts_for_step(step)
                step_policy = self.budget.get_step_policy(step)
                
                if allowed_attempts == 0:
                    if step_policy.skippable:
                        log("FAST-V2", f"💰 {step} skipped - budget insufficient (skippable)")
                        self.step_results[step] = {"status": "skipped", "reason": "budget_exhausted"}
                        continue
                    else:
                        log("FAST-V2", f"🛑 {step} cannot run - budget exhausted (critical step)")
                        self.failed_steps.append(step)
                        self.step_results[step] = {"status": "failed", "reason": "budget_exhausted"}
                        # Stop workflow on critical budget exhaustion
                        log("FAST-V2", f"🛑 Stopping workflow - budget exhausted for critical step {step}")
                        self.budget.log_status("[FAST-V2]")
                        break
                else:
                    log("FAST-V2", f"💰 Budget allows {allowed_attempts} attempts for {step}")

                # ════════════════════════════════════════════════════════
                # V2 FEATURE #3: PRE-STEP CRITICAL FILE VALIDATION
                # ════════════════════════════════════════════════════════
                if step in ["testing_backend", "testing_frontend", "preview_final"]:
                    if not self._validate_critical_files(step):
                        log("FAST-V2", f"⚠️ {step} skipped - critical files missing")
                        # Try to heal before skipping
                        if not self._attempt_healing(step):
                            self.failed_steps.append(step)
                            self.step_results[step] = {"status": "failed", "reason": "critical_files_missing"}
                            log("FAST-V2", f"🛑 Stopping - critical files missing for {step}")
                            break

                # ════════════════════════════════════════════════════════
                # EXECUTE STEP USING EXISTING HANDLER
                # ════════════════════════════════════════════════════════
                handler = HANDLERS.get(step)
                if not handler:
                    log("FAST-V2", f"⚠️ No handler for step: {step}")
                    continue

                try:
                    log("FAST-V2", f"▶️ Executing: {step}")
                    step_start = datetime.now()

                    result = await handler(
                        project_id=self.project_id,
                        user_request=self.user_request,
                        manager=self.manager,
                        project_path=self.project_path,
                        chat_history=self.chat_history,
                        provider=self.provider,
                        model=self.model,
                        current_turn=self.current_turn,
                        max_turns=self.max_turns,
                    )

                    duration = (datetime.now() - step_start).total_seconds()

                    # ════════════════════════════════════════════════════════
                    # V2 FEATURE #4: POST-STEP VALIDATION FOR CRITICAL STEPS  
                    # ════════════════════════════════════════════════════════
                    if step in self.CRITICAL_STEPS:
                        if not self._validate_step_output(step):
                            log("FAST-V2", f"⚠️ {step} output validation failed, trying healing...")
                            if self._attempt_healing(step):
                                log("FAST-V2", f"✅ {step} healed successfully")
                            else:
                                log("FAST-V2", f"❌ {step} healing failed")
                                self.failed_steps.append(step)
                                self.step_results[step] = {"status": "failed", "reason": "validation_failed"}
                                log("FAST-V2", f"🛑 Stopping - validation failed for {step}")
                                break

                    # ════════════════════════════════════════════════════════
                    # V2 FEATURE #5: CHECKPOINT ON SUCCESS
                    # ════════════════════════════════════════════════════════
                    self._save_checkpoint(step)
                    
                    # ════════════════════════════════════════════════════════
                    # V2 FEATURE #6: REGISTER BUDGET USAGE
                    # ════════════════════════════════════════════════════════
                    # Extract token usage from result if available
                    input_tokens = 0
                    output_tokens = 0
                    if hasattr(result, 'token_usage') and result.token_usage:
                        input_tokens = result.token_usage.get('input', 0)
                        output_tokens = result.token_usage.get('output', 0)
                    elif hasattr(result, 'usage') and result.usage:
                        input_tokens = getattr(result.usage, 'prompt_tokens', 0)
                        output_tokens = getattr(result.usage, 'completion_tokens', 0)
                    
                    # Use step policy estimates as fallback if no actual usage reported
                    if input_tokens == 0 and output_tokens == 0:
                        policy = self.budget.get_step_policy(step)
                        input_tokens = policy.est_input_tokens
                        output_tokens = policy.est_output_tokens
                    
                    self.budget.register_usage(
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        step=step,
                        agent=f"handler_{step}",
                        is_retry=False,
                    )
                    log("FAST-V2", f"💰 Registered usage: {input_tokens:,} in / {output_tokens:,} out")

                    log("FAST-V2", f"✅ {step} completed in {duration:.1f}s")
                    self.completed_steps.append(step)
                    self.step_results[step] = {
                        "status": result.status if hasattr(result, 'status') else "ok",
                        "duration": duration,
                        "budget": self.budget.get_usage_summary(),
                    }
                    
                    # V2 FEATURE #7: Record to cross-step context
                    self._record_step_context(step, result)
                    
                    self.current_turn += 1

                except RateLimitError as e:
                    # ════════════════════════════════════════════════════════
                    # CRITICAL: STOP IMMEDIATELY ON RATE LIMIT
                    # ════════════════════════════════════════════════════════
                    log("FAST-V2", f"🛑 Stopping - Rate Limit Exceeded: {e}")
                    self.failed_steps.append(step)
                    self.step_results[step] = {"status": "failed", "reason": "rate_limit", "error": str(e)}
                    self.budget.log_status("[FAST-V2]")
                    break

                except Exception as e:
                    log("FAST-V2", f"❌ {step} failed (retries exhausted): {e}")
                    
                    self.failed_steps.append(step)
                    self.step_results[step] = {"status": "error", "error": str(e)}
                    
                    # ════════════════════════════════════════════════════════
                    # STOP ON FAILURE (As requested: do not auto-heal crashes)
                    # ════════════════════════════════════════════════════════
                    log("FAST-V2", f"🛑 Stopping - step {step} failed")
                    self.budget.log_status("[FAST-V2]")
                    break

                await asyncio.sleep(0.2)

            # ════════════════════════════════════════════════════════
            # WORKFLOW COMPLETE
            # ════════════════════════════════════════════════════════
            total_duration = (datetime.now() - start_time).total_seconds()
            success = len(self.failed_steps) == 0

            log("FAST-V2", f"{'✅' if success else '⚠️'} FAST V2 completed in {total_duration:.1f}s")
            log("FAST-V2", f"   Completed: {len(self.completed_steps)}/{len(self.graph.get_steps())}")
            log("FAST-V2", f"   Failed: {self.failed_steps}")
            
            # V2 FEATURE: Final budget summary
            self.budget.log_status("[FAST-V2]")
            budget_summary = self.budget.get_usage_summary()
            log("FAST-V2", f"   Budget: ₹{budget_summary['used_inr']:.2f} / ₹{budget_summary['max_inr']:.2f}")

            await broadcast_to_project(
                self.manager,
                self.project_id,
                {
                    "type": WSMessageType.WORKFLOW_COMPLETE if success else WSMessageType.WORKFLOW_FAILED,
                    "projectId": self.project_id,
                    "message": f"FAST V2 completed in {total_duration:.1f}s",
                    "duration": total_duration,
                    "completed": self.completed_steps,
                    "failed": self.failed_steps,
                    "budget": budget_summary,
                },
            )

        except Exception as e:
            log("FAST-V2", f"❌ Workflow failed: {e}")
            await broadcast_to_project(
                self.manager,
                self.project_id,
                {
                    "type": WSMessageType.WORKFLOW_FAILED,
                    "projectId": self.project_id,
                    "error": str(e),
                },
            )

    def _validate_critical_files(self, step: str) -> bool:
        """
        Validate critical files exist before running testing/preview steps.
        
        V2 Feature: Pre-flight check to prevent wasted Docker builds.
        """
        checks = {
            "testing_backend": [
                self.project_path / "backend" / "app" / "main.py",
                self.project_path / "backend" / "app" / "models.py",
            ],
            "testing_frontend": [
                self.project_path / "backend" / "app" / "main.py",
                self.project_path / "frontend" / "src" / "lib" / "api.js",
            ],
            "preview_final": [
                self.project_path / "backend" / "app" / "main.py",
                self.project_path / "docker-compose.yml",
            ],
        }
        
        required_files = checks.get(step, [])
        for file_path in required_files:
            if not file_path.exists():
                log("FAST-V2", f"   Missing: {file_path}")
                return False
        
        # Check routers directory has files
        routers_dir = self.project_path / "backend" / "app" / "routers"
        if routers_dir.exists():
            router_files = [f for f in routers_dir.glob("*.py") if f.name != "__init__.py"]
            if not router_files:
                log("FAST-V2", f"   Missing: router files in {routers_dir}")
                return False
        else:
            log("FAST-V2", f"   Missing: {routers_dir}")
            return False
        
        return True

    def _validate_step_output(self, step: str) -> bool:
        """
        Validate the output of a critical step.
        
        V2 Feature: Post-step validation using structural compiler.
        """
        # Get primary entity for dynamic validation
        entities = self.cross_ctx._ctx.get("entities", [])
        primary_entity = entities[0] if entities else "item"
        from app.orchestration.utils import pluralize
        primary_plural = pluralize(primary_entity)

        if step == "backend_routers":
            # Dynamic router path based on primary entity
            router_path = self.project_path / "backend" / "app" / "routers" / f"{primary_plural}.py"
            
            # Fallback: check ALL routers if specific one missing
            if not router_path.exists():
                routers_dir = self.project_path / "backend" / "app" / "routers"
                if routers_dir.exists() and any(f.suffix == ".py" and f.stem != "__init__" for f in routers_dir.iterdir()):
                    return True # Found some router, good enough
                return False
                
            content = router_path.read_text(encoding="utf-8")
            return self.compiler.router_is_complete(content)
        
        if step == "frontend_integration":
            api_path = self.project_path / "frontend" / "src" / "lib" / "api.js"
            if not api_path.exists():
                return False
            content = api_path.read_text(encoding="utf-8")
            
            # Dynamic validation
            entities = self.cross_ctx._ctx.get("entities", [])
            primary_entity = entities[0] if entities else "Note"
            return self.compiler.api_is_complete(content, entity_name=primary_entity)
        
        if step == "backend_main":
            main_path = self.project_path / "backend" / "app" / "main.py"
            if not main_path.exists():
                return False
            content = main_path.read_text(encoding="utf-8")
            return "include_router" in content
        
        return True

    def _attempt_healing(self, step: str) -> bool:
        """
        Attempt to heal a failed step using the healing pipeline.
        
        V2 Feature: Self-healing via HealingPipeline with LLM regeneration + fallback templates.
        """
        log("FAST-V2", f"🔧 Attempting healing for {step}...")
        
        # Use the V2 healing pipeline
        result = self.healer.attempt_heal(step)
        
        if result:
            log("FAST-V2", f"   ✅ Healing succeeded for {step}")
            return True
        
        log("FAST-V2", f"   ❌ Healing failed for {step}")
        return False

    def _save_checkpoint(self, step: str):
        """Save a checkpoint after successful step completion."""
        try:
            # Get dynamic paths
            entities = self.cross_ctx._ctx.get("entities", [])
            primary_entity = entities[0] if entities else "item"
            from app.orchestration.utils import pluralize
            primary_plural = pluralize(primary_entity)

            # Collect relevant files for this step
            files = {}
            step_files = {
                "backend_models": ["backend/app/models.py", "backend/app/database.py"],
                "backend_routers": [f"backend/app/routers/{primary_plural}.py"],
                "backend_main": ["backend/app/main.py"],
                "frontend_integration": ["frontend/src/lib/api.js"],
            }
            
            for rel_path in step_files.get(step, []):
                full_path = self.project_path / rel_path
                if full_path.exists():
                    files[rel_path] = full_path.read_text(encoding="utf-8")
            
            if files:
                self.checkpoint.save(step, files)
        except Exception as e:
            log("FAST-V2", f"   ⚠️ Checkpoint failed: {e}")

    def _record_step_context(self, step: str, result: Any):
        """
        V2 Feature: Record step completion to cross-step context.
        
        This allows later steps to know what earlier steps produced.
        """
        try:
            summary = {}
            
            # Extract relevant info based on step type
            if step == "analysis":
                # Extract entities from analysis result
                if hasattr(result, 'entities'):
                    self.cross_ctx.set_entities(result.entities)
                    summary = {"entities": result.entities}
            
            elif step == "architecture":
                # Extract architecture summary
                arch_path = self.project_path / "architecture.md"
                if arch_path.exists():
                    arch_content = arch_path.read_text(encoding="utf-8")[:500]
                    self.cross_ctx.set_architecture(arch_content)
                    summary = {"architecture": "MongoDB + Beanie ODM"}
            
            elif step == "backend_models":
                # Record model info
                models_path = self.project_path / "backend" / "app" / "models.py"
                if models_path.exists():
                    entities = self.cross_ctx._ctx.get("entities", [])
                    primary = entities[0] if entities else "Item"
                    summary = {"models": f"{primary.capitalize()} model with CRUD support"}
            
            elif step == "backend_routers":
                # Record router endpoints
                entities = self.cross_ctx._ctx.get("entities", [])
                primary = entities[0] if entities else "item"
                from app.orchestration.utils import pluralize
                plural = pluralize(primary)
                summary = {"endpoints": f"GET/POST/PUT/DELETE /api/{plural}"}
            
            elif step == "contracts":
                # Record contract summary
                contracts_path = self.project_path / "contracts.md"
                if contracts_path.exists():
                    summary = {"contracts": "API contracts defined"}
            
            # Record to cross-step context
            self.cross_ctx.record_step_completion(step, summary)
            log("FAST-V2", f"   📝 Recorded context for {step}")
            
        except Exception as e:
            log("FAST-V2", f"   ⚠️ Context recording failed: {e}")


# ════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION (matches FastWorkflowEngine signature)
# ════════════════════════════════════════════════════════
async def run_fast_v2_workflow(
    project_id: str,
    manager: Any,
    project_path: Path,
    user_request: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> None:
    """
    Convenience function to run FAST V2 workflow.
    
    Matches FastWorkflowEngine's run_fast_workflow signature.
    """
    engine = FASTOrchestratorV2(
        project_id=project_id,
        manager=manager,
        project_path=project_path,
        user_request=user_request,
        provider=provider,
        model=model,
    )
    await engine.run()
