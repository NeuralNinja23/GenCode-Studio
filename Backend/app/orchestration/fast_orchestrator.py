# app/orchestration/fast_orchestrator.py
"""
FAST v2 Orchestrator - Main Entry Point (Gutted for ArborMind)

The Orchestrator is now a "muscle" (execution body).
All cognitive decisions (what to do next, retry, heal) belong to ArborMind.
"""

import asyncio
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
import traceback

from app.core.logging import log, log_section
from app.orchestration.utils import broadcast_to_project, pluralize
from app.orchestration.task_graph import TaskGraph
from app.orchestration.context import CrossStepContext
from app.orchestration.structural_compiler import StructuralCompiler
from app.orchestration.checkpoint import CheckpointManagerV2
from app.orchestration.state import WorkflowStateManager
from app.core.constants import WSMessageType
from app.utils.entity_discovery import discover_primary_entity, extract_all_models_from_models_py
from app.core.guard import OrchestrationGuard
from app.core.step_outcome import StepOutcome, StepExecutionResult
from app.core.types import StepResult

# Phase 9: ArborMind Execution Router + Observation
from app.arbormind.runtime.execution_router import ExecutionRouter
from app.arbormind.observation.observer import record_event

# Phase 10: SQLite Memory for Decision Vectors
# Phase 10: Execution Ledger (Pure Events)
from app.arbormind.observation.execution_ledger import (
    record_run_start,
    record_step_entry,
    record_step_exit,
    record_decision_event,
    record_failure_event,
    record_snapshot,
)

# PHASE 2: Failure Severity System
from app.arbormind.cognition.failures import (
    FailureSeverity,
    get_failure_severity,
    is_fatal,
)

# PHASE 6: Convergence Criteria
from app.arbormind.cognition.convergence import (
    is_converged,
    get_completion_confidence,
    should_preview,
)

# PHASE-0/1: Execution Records and Retry Policy
from app.core.execution_record import StepExecutionRecord
from app.arbormind.core.execution_mode import get_execution_policy, ExecutionMode
from app.arbormind.core.retry_policy import get_retry_prompt

# ═══════════════════════════════════════════════════════════════════════════════
# TOOL PLANNING: Capability-Based Tool Expansion
# ═══════════════════════════════════════════════════════════════════════════════
from app.tools.planner import build_tool_plan
from app.tools.executor import execute_tool_plan
from app.tools.planning import StepFailure

# ═══════════════════════════════════════════════════════════════════════════════
# ARBORMIND LEARNING: Canonical Failure Ingestion (The 7 Requirements)
# ═══════════════════════════════════════════════════════════════════════════════
# ARBORMIND OBSERVATION: Canonical Failure Definitions (Phase 3.5)
# ═══════════════════════════════════════════════════════════════════════════════
from app.arbormind.observation.failure_canon import (
    FailureClass,
    FailureScope,
)
# Note: Ingestion functions removed as per Phase 3 strictness
# from app.arbormind.observation.ingestion import ... (Does not exist in Obs)

# ═══════════════════════════════════════════════════════════════════════════════
# ARBORMIND OBSERVATION: Step State Snapshot (SSS) - Phase 3 Primitive
# ═══════════════════════════════════════════════════════════════════════════════
from app.arbormind.observation.step_state_snapshot import (
    record_step_entry,
    record_step_exit,
)



class FASTOrchestratorV2(OrchestrationGuard):
    """
    FAST v2 Orchestrator - Minimal execution muscle.
    """

    CAUSAL_STEPS = ["architecture", "backend_models", "backend_routers", "frontend_mock", "system_integration"]
    EVIDENCE_STEPS = ["testing_backend", "testing_frontend", "preview_final"]
    CRITICAL_STEPS = ["architecture", "backend_models"]


    def __init__(
        self,
        project_id: str,
        manager: Any,
        project_path: Path,
        user_request: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        resume_from_checkpoint: bool = False,
        is_refinement: bool = False,
    ):
        self.project_id = project_id
        self.manager = manager
        self.project_path = project_path
        self.user_request = user_request
        self.provider = provider
        self.model = model
        self.resume_from_checkpoint = resume_from_checkpoint
        self.is_refinement = is_refinement
        
        self.graph = TaskGraph()
        
        # In refinement mode, we override the graph to just "refine"
        if self.is_refinement:
            self.graph.steps = ["refine"]
            self.completed_steps = [] # Refine always runs

        
        # self.graph initialized above
        self.cross_ctx = CrossStepContext.get_or_create(project_id)
        self.compiler = StructuralCompiler()
        self.checkpoint = CheckpointManagerV2(base_dir=str(project_path / ".fast_checkpoints"))
        
        self.completed_steps = []
        if self.is_refinement:
            self.completed_steps = [] # Explicit clear
            
        self.failed_steps = []
        self.step_results = {}
        self.execution_records = {}  # Phase-0: Track files created by each step
        self.current_turn = 1
        self.max_turns = 15
        self.run_id = None
        self.archetype = "generic"
        # Initialization logging removed - step logs are sufficient

    def _register_usage(self, step: str, result: Any):
        """Extract and register token usage from mixed result types."""
        try:
            usage = None
            if isinstance(result, dict):
                usage = result.get("token_usage")
            elif hasattr(result, "token_usage"): # StepResult
                usage = result.token_usage
            elif hasattr(result, "data") and isinstance(result.data, dict): # StepExecutionResult
                usage = result.data.get("token_usage")
                
            if usage:
                self.budget.register_usage(
                    step=step,
                    input_tokens=usage.get("input", 0),
                    output_tokens=usage.get("output", 0),
                    model=self.model or "gemini-2.0-flash-exp" # Default to flash if not set
                )
        except Exception as e:
            # Non-critical - don't crash workflow on metrics
            pass

    async def run(self):
        """
        Execute the branch.
        Minimal logic, only execution.
        """
        from app.handlers import HANDLERS, STEP_AGENTS
        from app.orchestration.state import CURRENT_MANAGERS
        
        # ArborMind Imports (Phase 2)
        from app.arbormind.cognition.branch import Branch
        from app.arbormind.cognition.tree import ArborMindTree
        from app.arbormind.runtime.runtime import ArborMindRuntime
        from app.arbormind.runtime.observer import observe
        from app.arbormind.cognition.execution_report import ExecutionReport
        from app.arbormind.runtime.execution_router import ExecutionRouter
        from app.arbormind.runtime.decision import ExecutionAction
        from app.orchestration.budget_manager import get_budget_manager

        # 1️⃣ ENTRY POINT — Initialize Tree + Root Branch
        # Create root branch - capture input only
        from app.arbormind.core.archetypes import get_archetype
        
        # Initialize budget for this run
        self.budget = get_budget_manager(self.project_id)
        self.budget.start_run()
        
        archetype = get_archetype("fullstack_software")
        
        root_branch = Branch(
            parent_id=None,
            depth=0,
            assumptions=archetype.as_assumptions(),
            intent={
                "user_request": self.user_request,
                "project_id": self.project_id,
                "project_path": self.project_path,
                "manager": self.manager,
                "provider": self.provider,
                "model": self.model,
                "archetype": self.archetype,
            },
            strategy={},
            agent_roles={}
        )

        tree = ArborMindTree(root=root_branch)
        arbormind = ArborMindRuntime()

        # Phase 3 — inhibition-only cognition
        tree = arbormind.cycle(tree)

        # Then synthesize ONE branch
        from app.arbormind.core.synthesis import synthesize
        branch_to_execute = synthesize(tree)

        start_time = datetime.now()
        
        # Register in global registry for process tracking
        CURRENT_MANAGERS[self.project_id] = self.manager

        try:
            # 📊 ArborMind: Generate unique run ID and record start
            import uuid
            self.run_id = f"run_{uuid.uuid4().hex[:12]}"
            
            # ───────────────────────────────────────────────────────────────
            # 🧠 SQLITE MEMORY: Record run start (non-blocking)
            # ───────────────────────────────────────────────────────────────
            record_run_start(
                run_id=self.run_id,
                project_id=self.project_id
            )
            
            # 🧠 OBSERVATION: Initial SSS
            record_snapshot(
                run_id=self.run_id,
                step="init", 
                stage="ENTRY",
                workspace_hash="0000", # Placeholder for initial scan
                artifacts_hash="0000"
            )
            
            # Start workflow in DB
            await WorkflowStateManager.try_start_workflow(self.project_id)

            # Phase-0: Load state if resuming
            if self.resume_from_checkpoint:
                self._load_execution_state()

            # EXECUTE STEPS IN ORDER
            # NOTE: We use a while loop with index to allow dynamic appending of steps (e.g. refine -> preview)
            steps = self.graph.get_steps()
            step_idx = 0
            
            while step_idx < len(steps):
                step = steps[step_idx]
                step_idx += 1
                # Phase-0: Skip completed steps if resuming
                if self.resume_from_checkpoint and step in self.completed_steps:
                    log("FAST-V2", f"⏭️ Skipping completed step: {step}")
                    continue

                handler = HANDLERS.get(step)
                if not handler:
                    continue

                log("FAST-V2", f"▶️ Executing: {step}")
                step_start = datetime.now()
                
                # 🧠 SQLITE: Record step decision (start) - "I choose to run this tool"
                agent_name = STEP_AGENTS.get(step, "System")
                record_decision_event(
                    run_id=self.run_id,
                    step=step,
                    agent=agent_name,
                    decision="RUN_TOOL",
                    reason=f"Starting step: {step}",
                )
                
                # 📊 METRICS: Start step tracking (Legacy removed)
                step_order = steps.index(step)
                # if self.run_id:
                #     try:
                #         start_step(self.run_id, step, step_order)
                #     except Exception as me:
                #         log("METRICS", f"⚠️ Failed to start step metrics: {me}")

                # ───────────────────────────────────────────────────────────────
                # 📸 PHASE 3: Step State Snapshot - ENTRY (Horizontal Continuity)
                # ───────────────────────────────────────────────────────────────
                try:
                    record_step_entry(self.run_id, step)
                except Exception:
                    pass  # SSS must never crash execution

                try:
                    # ──────────────────────────────────────────────────────────────────
                    # 🧠 PHASE 9: Centralized Decision Making (ExecutionRouter)
                    # ──────────────────────────────────────────────────────────────────
                    router = ExecutionRouter()
                    
                    decision = router.decide(
                        branch=branch_to_execute,
                        context={
                            "expected_outputs": 1,  # Handlers expect at least 1 file
                            "step": step,
                        }
                    )
                    
                    # ──────────────────────────────────────────────────────────────────
                    # 📊 PHASE 9: Observational Recording (Non-blocking)
                    # ──────────────────────────────────────────────────────────────────
                    record_decision_event(
                        run_id=self.run_id,
                        step=step,
                        agent="ROUTER",
                        decision=decision.action.value,
                        reason=decision.reason
                    )
                    
                    # ──────────────────────────────────────────────────────────────────
                    # 🔧 Execute Based on Decision
                    # ──────────────────────────────────────────────────────────────────
                    result = None
                    
                    if decision.action == ExecutionAction.STOP:
                        log("FAST-V2", f"🛑 ExecutionRouter decided to STOP: {decision.reason}")
                        self.failed_steps.append(step)
                        self.step_results[step] = {"status": "stopped", "reason": decision.reason}
                        break
                    
                    elif decision.action == ExecutionAction.HEAL:
                        log("FAST-V2", f"🩹 Healing requested: {decision.reason}")
                        self.failed_steps.append(step)
                        self.step_results[step] = {"status": "healed", "reason": decision.reason}
                        break

                    elif decision.action == ExecutionAction.MUTATE:
                        log("FAST-V2", f"🧬 Mutation requested: {decision.reason}")
                        self.failed_steps.append(step)
                        self.step_results[step] = {"status": "mutated", "reason": decision.reason}
                        break
                    elif decision.action == ExecutionAction.RUN_TOOL:
                        # Phase-1: Take filesystem snapshot BEFORE execution for relative change detection
                        before_snapshot = self._get_project_snapshot()
                        
                        # ═══════════════════════════════════════════════════════
                        # TOOL PLANNING: Build and execute capability-based plan
                        # ═══════════════════════════════════════════════════════
                        # Step → Capabilities → Tools → Ordered Execution
                        try:
                            # Build tool plan from step capabilities
                            tool_plan = await build_tool_plan(
                                step=step,
                                branch=branch_to_execute,
                                goal=f"Execute {step} step for {self.user_request[:100]}...",
                            )
                            
                            log("FAST-V2", f"📋 Tool plan: {' → '.join(tool_plan.tool_names)}")
                            
                            # Execute the tool plan (linear, observable)
                            plan_result = await execute_tool_plan(tool_plan, branch_to_execute)
                            
                            # Extract result for downstream compatibility
                            result = plan_result.final_output
                            
                            # If tool plan failed, wrap for handler compatibility
                            if not plan_result.success:
                                log("FAST-V2", f"❌ Tool plan failed: {plan_result.error}")
                                result = StepExecutionResult(
                                    outcome=StepOutcome.HARD_FAILURE,
                                    data={"error": plan_result.error},
                                    artifacts={},
                                )
                        except StepFailure as sf:
                            log("FAST-V2", f"❌ Step failure: {sf}")
                            result = StepExecutionResult(
                                outcome=StepOutcome.HARD_FAILURE,
                                data={"error": str(sf)},
                                artifacts={},
                            )
                        except Exception as e:
                            # Fallback to legacy handler if tool planning fails
                            log("FAST-V2", f"⚠️ Tool planning failed, falling back to handler: {e}")
                            result = await handler(branch_to_execute)
                        
                        # Register token usage (Budget Manager)
                        self._register_usage(step, result)

                        # Phase-1: Take filesystem snapshot AFTER execution
                        after_snapshot = self._get_project_snapshot()
                        
                        # ═══════════════════════════════════════════════════════
                        # PHASE-0/1: FILE TRACKING AND RETRY LOGIC
                        # ═══════════════════════════════════════════════════════
                        
                        # Get execution policy for this step
                        policy = get_execution_policy(step)
                        
                        # Phase-1: Compute actual files created/modified on disk
                        # This is the "Truth" observed by the Orchestrator
                        files_generated = self._compute_file_delta(before_snapshot, after_snapshot)
                        
                        # Phase-0: Register files created
                        if files_generated:
                            self._register_step_files_from_paths(step, files_generated)
                        
                        # Phase-1: Check if ARTIFACT step produced output
                        if policy.mode == ExecutionMode.ARTIFACT and policy.requires_output:
                            if not files_generated or len(files_generated) == 0:
                                log("FAST-V2", f"⚠️ ARTIFACT step '{step}' produced ZERO files")
                                log("FAST-V2", f"   Policy: requires_output=True, is_fatal={policy.is_fatal}")
                                
                                # Check if retry is allowed
                                if self._should_retry_step(step):
                                    log("FAST-V2", f"🔄 Phase-1: Attempting retry for {step}")
                                    
                                    # Phase-0: Rollback any partial files
                                    self._rollback_step(step)
                                    
                                    # Phase-1: Retry with hardened prompt
                                    # Note: retry also does snapshots inside its loop logic if needed, 
                                    # but here we just take the final result.
                                    retry_before = self._get_project_snapshot()
                                    retry_success, retry_result = await self._retry_step_with_hardened_prompt(
                                        step, handler, branch_to_execute
                                    )
                                    retry_after = self._get_project_snapshot()
                                    
                                    if retry_success:
                                        log("FAST-V2", f"✅ Retry succeeded for {step}")
                                        result = retry_result
                                        
                                        # Register usage for retry
                                        self._register_usage(step, result)
                                        
                                        files_generated = self._compute_file_delta(retry_before, retry_after)
                                        if files_generated:
                                            self._register_step_files_from_paths(step, files_generated)
                                    else:
                                        log("FAST-V2", f"❌ Retry FAILED for {step}")
                                        
                                        # Generate halt artifact
                                        halt_artifact = self._generate_halt_artifact(
                                            step_name=step,
                                            reason="Zero files produced after retry",
                                            attempts=2
                                        )
                                        
                                        # Record failure
                                        self.failed_steps.append(step)
                                        self.step_results[step] = {
                                            "status": "failed",
                                            "reason": "zero_files_after_retry",
                                            "halt_artifact": halt_artifact
                                        }
                                        
                                        # 🧠 ARBORMIND LEARNING: Ingest failure (canonical)
                                        ingest_failure(
                                            run_id=self.run_id,
                                            step=step,
                                            primary_class=FailureClass.F1_INVARIANT_VIOLATION,
                                            scope=FailureScope.STEP_LOCAL,
                                            raw_error="Zero files produced after retry",
                                            agent=agent_name,
                                            retry_index=1,
                                            is_hard_failure=policy.is_fatal,
                                        )
                                        
                                        # Phase-1: If fatal, stop workflow
                                        if policy.is_fatal:
                                            log("FAST-V2", f"🛑 FATAL: {step} failed after retry - HALTING WORKFLOW")
                                            break
                                        else:
                                            log("FAST-V2", f"⚠️ NON-FATAL: {step} failed but continuing")
                                            continue  # Skip to next step
                                else:
                                    # No retry allowed, but empty output
                                    log("FAST-V2", f"❌ {step} produced zero files (no retry allowed)")
                                    
                                    # Generate halt artifact (attempt 1 only)
                                    halt_artifact = self._generate_halt_artifact(
                                        step_name=step,
                                        reason="Zero files produced",
                                        attempts=1
                                    )
                                    
                                    self.failed_steps.append(step)
                                    self.step_results[step] = {
                                        "status": "failed",
                                        "reason": "zero_files",
                                        "halt_artifact": halt_artifact
                                    }
                                    
                                    # 🧠 ARBORMIND LEARNING: Ingest failure (canonical)
                                    # ingest_failure(
                                    #     run_id=self.run_id,
                                    #     step=step,
                                    #     primary_class=FailureClass.F1_INVARIANT_VIOLATION,
                                    #     scope=FailureScope.STEP_LOCAL,
                                    #     raw_error="Zero files produced (no retry allowed)",
                                    #     agent=agent_name,
                                    #     retry_index=0,
                                    #     is_hard_failure=policy.is_fatal,
                                    # )
                                    
                                    if policy.is_fatal:
                                        log("FAST-V2", f"🛑 FATAL: {step} produced zero files - HALTING WORKFLOW")
                                        break
                                    else:
                                        log("FAST-V2", f"⚠️ NON-FATAL: {step} produced zero files but continuing")
                                        continue
                        
                        # ═══════════════════════════════════════════════════════
                        # EXISTING FAILURE HANDLING (after Phase-0/1 checks)
                        # ═══════════════════════════════════════════════════════
                        
                        # 🛑 CRITICAL: FailureBoundary catches exceptions and returns StepExecutionResult
                        # We MUST check if the result indicates failure
                        if isinstance(result, StepExecutionResult):
                            if result.outcome != StepOutcome.SUCCESS:
                                log("FAST-V2", f"⚠️ Step {step} returned failure: {result.outcome.value}")
                                log("FAST-V2", f"   Error: {result.error_details}")
                                
                                # ═══════════════════════════════════════════════════════
                                # PHASE 2: Failure Severity Classification
                                # ═══════════════════════════════════════════════════════
                                # Map StepOutcome to failure code for severity lookup
                                failure_code = {
                                    StepOutcome.HARD_FAILURE: "RepeatedInvariant",
                                    StepOutcome.COGNITIVE_FAILURE: "SupervisorRejection",
                                    StepOutcome.ENVIRONMENT_FAILURE: "InfraTransient",
                                }.get(result.outcome, "QualityWarning")
                                
                                severity = get_failure_severity(failure_code)
                                is_fatal_failure = severity == FailureSeverity.FATAL
                                
                                self.failed_steps.append(step)
                                self.step_results[step] = {
                                    "status": "failed",
                                    "outcome": result.outcome.value,
                                    "error": result.error_details,
                                    "severity": severity.value,  # Track severity
                                }
                                
                                # 🧠 SQLITE: Update decision with failure
                                duration_ms = int((datetime.now() - step_start).total_seconds() * 1000)
                                # 🧠 OBSERVATION: Update decision with failure
                                duration_ms = int((datetime.now() - step_start).total_seconds() * 1000)
                                record_step_exit(
                                    run_id=self.run_id,
                                    step=step,
                                    status="FAILED"
                                )
                                
                                # 🧠 OBSERVATION: Record specific failure details (telemetry)
                                record_failure_event(
                                    run_id=self.run_id,
                                    step=step,
                                    origin="STEP_LOGIC",
                                    signal=result.outcome.value,
                                    message=result.error_details or "Unknown error",
                                )
                                
                                # 🧠 ARBORMIND LEARNING: Ingest canonical failure
                                # Map StepOutcome to FailureClass
                                failure_class_map = {
                                    StepOutcome.HARD_FAILURE: FailureClass.F1_INVARIANT_VIOLATION,
                                    StepOutcome.COGNITIVE_FAILURE: FailureClass.F4_QUALITY_REJECTION,
                                    StepOutcome.ENVIRONMENT_FAILURE: FailureClass.F9_EXTERNAL_FAILURE,
                                }
                                canonical_class = failure_class_map.get(
                                    result.outcome, 
                                    FailureClass.F7_RUNTIME_EXCEPTION
                                )
                                
                                # ingest_failure(
                                #     run_id=self.run_id,
                                #     step=step,
                                #     primary_class=canonical_class,
                                #     scope=FailureScope.STEP_LOCAL if step not in self.CRITICAL_STEPS else FailureScope.CROSS_STEP,
                                #     raw_error=result.error_details or "Unknown error",
                                #     agent=agent_name,
                                #     retry_index=0,
                                #     is_hard_failure=is_fatal_failure or step in self.CRITICAL_STEPS,
                                # )
                                
                                # ═══════════════════════════════════════════════════════
                                # PHASE 2: Only FATAL failures or CRITICAL STEPS stop the workflow
                                # ═══════════════════════════════════════════════════════
                                if is_fatal_failure or step in self.CRITICAL_STEPS:
                                    log("FAST-V2", f"🛑 FATAL: Step {step} failed (or is critical) - stopping workflow")
                                    
                                    # Generate halt artifact before stopping
                                    self._generate_halt_artifact(
                                        step_name=step,
                                        reason=f"Step failed with outcome: {result.outcome.value}",
                                        attempts=1 # Regular failures don't have Phase-1 auto-retries yet
                                    )
                                    
                                    if step in self.CRITICAL_STEPS:
                                        break
                                    elif is_fatal_failure:
                                        break
                                else:
                                    # This handles the User's "Signal, not Stop" requirement
                                    log("FAST-V2", f"⚠️ NON-FATAL SIGNAL: Step {step} failed - continuing branch per stabilization rules")
                                    # Continue to next step
                    
                    duration = (datetime.now() - step_start).total_seconds()

                    # VALIDATE OUTPUT (Gate, not cognition)
                    validation_passed = self._validate_step_output(step)
                    
                    if not validation_passed:
                        log("FAST-V2", f"🛑 Step {step} validation failed. Reporting failure.")
                        self.failed_steps.append(step)
                        self.step_results[step] = {"status": "failed", "reason": "validation_failed"}
                        break # Stop on failure

                    # PERSISTENCE (Muscle)
                    await self._save_checkpoint(step)
                    await self._record_step_context(step, result)
                    
                    self.completed_steps.append(step)
                    self.step_results[step] = {"status": "ok", "duration": duration}

                    # Handle Legacy StepResult flow control (e.g. Refine -> Preview)
                    if isinstance(result, StepResult) and result.nextstep:
                        # Map WorkflowStep enum to string if needed
                        next_step_str = result.nextstep.value if hasattr(result.nextstep, "value") else str(result.nextstep)
                        
                        # Only append if not already in queue and not complete
                        # Note: FAST V2 usually strictly follows graph, but Refine is dynamic
                        if next_step_str not in steps and next_step_str != "complete":
                            log("FAST-V2", f"🔀 Dynamic step transition: {step} -> {next_step_str}")
                            steps.append(next_step_str)
                    

                    
                    # 🧠 SQLITE: Update decision with success and metrics
                    duration_ms = int(duration * 1000)
                    artifacts_count = 0
                    if result and isinstance(result, StepExecutionResult) and result.data:
                         # Extract artifacts count if possible (handlers typically return generated files list)
                         files = result.data.get("files", []) or result.data.get("modified_files", [])
                         artifacts_count = len(files) if isinstance(files, list) else 0

                    update_decision_outcome(
                        run_id=self.run_id,
                        step=step,
                        outcome="success",
                        duration_ms=duration_ms,
                        artifacts_count=artifacts_count
                    )
                    
                    # ───────────────────────────────────────────────────────────────
                    # 📸 PHASE 3: Step State Snapshot - EXIT (Horizontal Continuity)
                    # ───────────────────────────────────────────────────────────────
                    try:
                        record_step_exit(self.run_id, step, self.project_path)
                    except Exception:
                        pass  # SSS must never crash execution
                    
                    if self.run_id:
                        # complete_step(self.run_id, step, True, 1)
                        pass

                except Exception as e:
                    log("FAST-V2", f"❌ {step} failed: {e}")
                    self.failed_steps.append(step)
                    self.step_results[step] = {"status": "error", "error": str(e)}
                    
                    # 🧠 SQLITE: Update decision with exception failure
                    duration_ms = int((datetime.now() - step_start).total_seconds() * 1000)
                    update_decision_outcome(
                        run_id=self.run_id,
                        step=step,
                        outcome="failure",
                        duration_ms=duration_ms,
                        artifacts_count=0
                    )

                    import traceback
                    tb_str = traceback.format_exc()
                    
                    # 🧠 SQLITE: Record failure (telemetry)
                    record_failure(
                        run_id=self.run_id,
                        step=step,
                        failure_type="exception",
                        message=str(e),
                        stack_trace=tb_str,
                    )
                    
                    # 🧠 ARBORMIND LEARNING: Ingest canonical failure (F7 Runtime Exception)
                    ingest_runtime_exception(
                        run_id=self.run_id,
                        step=step,
                        exception_info=f"{str(e)}\n{tb_str}",
                        agent=agent_name,
                    )
                    
                    # ───────────────────────────────────────────────────────────────
                    # 📸 PHASE 3: Step State Snapshot - EXIT on FAILURE
                    # ───────────────────────────────────────────────────────────────
                    try:
                        record_step_exit(self.run_id, step, self.project_path)
                    except Exception:
                        pass  # SSS must never crash execution
                    
                    break # Stop on exception

            # WORKFLOW COMPLETE
            total_duration = (datetime.now() - start_time).total_seconds()
            success = len(self.failed_steps) == 0
            
            # 🧠 SQLITE: Record run completion
            record_run_end(
                run_id=self.run_id,
                status="success" if success else "failure",
                total_steps=len(steps),
                completed_steps=len(self.completed_steps),
                failed_steps=len(self.failed_steps),
            )

            await broadcast_to_project(
                self.manager,
                self.project_id,
                {
                    "type": WSMessageType.WORKFLOW_COMPLETE if success else WSMessageType.WORKFLOW_FAILED,
                    "projectId": self.project_id,
                    "completed": self.completed_steps,
                    "failed": self.failed_steps,
                },
            )

            # 2️⃣ EXECUTION COMPLETION — OBSERVE RESULT
            # Adapt output to ExecutionReport
            report = ExecutionReport(
                success=success,
                artifacts=self.step_results,
                error=None if success else f"Steps failed: {self.failed_steps}",
                metrics={"duration": total_duration}
            )
            
            # Observe
            observe(root_branch, report)
            

        except Exception as e:
            # ArborMind Observe (Crash)
            report = ExecutionReport(
                success=False,
                artifacts=self.step_results if hasattr(self, 'step_results') else {},
                error=str(e),
                metrics={}
            )
            observe(root_branch, report)

            log("FAST-V2", f"❌ Workflow execution crashed: {e}")
            if self.run_id:
                # complete_pipeline_run(self.run_id, False, "crash", str(e))
                pass
        finally:
            from app.orchestration.state import CURRENT_MANAGERS
            CURRENT_MANAGERS.pop(self.project_id, None)
            await WorkflowStateManager.stop_workflow(self.project_id)

    def _validate_step_output(self, step: str) -> bool:
        """Minimal output validation gate."""
        # For now, just return True or implement very basic file existence checks
        # Cognitive validation belongs in ArborMind
        return True

    async def _save_checkpoint(self, step: str):
        """Save a checkpoint after successful step completion."""
        try:
            # Phase-0: Get execution record to persist as metadata
            record = self.execution_records.get(step)
            metadata = {
                "step_summaries": self.cross_ctx._ctx.get("step_summaries", {}),
                "architecture": self.cross_ctx._ctx.get("architecture", "")
            }
            if record:
                metadata["execution_record"] = record.to_dict()

            checkpoint_dir = await self.checkpoint.save_project_snapshot(
                self.project_path, 
                step, 
                run_id=self.run_id,
                **metadata
            )
            # log("FAST-V2", f"   💾 Checkpoint saved: {checkpoint_dir}")
        except Exception as e:
            log("FAST-V2", f"   ⚠️ Checkpoint failed: {e}")

    async def _record_step_context(self, step: str, result: Any):
        """Record step completion to cross-step context."""
        try:
            # 1. Update completed steps list with summary from data
            summary = result.data if hasattr(result, 'data') else {}
            self.cross_ctx.record_step_completion(step, summary=summary)
            
            # 2. Extract and record entities if architecture step
            if step == "architecture":
                # Set specific architecture text for context
                arch_summary = summary.get("architecture_summary") or ""
                self.cross_ctx.set_architecture(arch_summary)

                from app.utils.entity_discovery import discover_entities_from_architecture
                arch_file = self.project_path / "architecture" / "backend.md"
                if arch_file.exists():
                    entities = discover_entities_from_architecture(arch_file)
                    if entities:
                        # Extract entity names from EntitySpec objects
                        entity_names = [e.name for e in entities]
                        self.cross_ctx.set_entities(entity_names)
                        log("FAST-V2", f"   🧠 Recorded entities: {', '.join(entity_names)}")
            
            # 3. Add to workflow state manager for UI resume
            from app.orchestration.state import WorkflowStateManager
            await WorkflowStateManager.save_completed_step(
                self.project_id, 
                step, 
                context=summary
            )
            
            # 4. Cache architecture files after Victoria generates them
            if step == "architecture":
                try:
                    arch_dir = self.project_path / "architecture"
                    arch_cache = {}
                    
                    for arch_file in ["frontend.md", "backend.md", "system.md", "overview.md"]:
                        file_path = arch_dir / arch_file
                        if file_path.exists():
                            arch_cache[arch_file.replace(".md", "")] = file_path.read_text(encoding="utf-8")
                    
                    if arch_cache:
                        await WorkflowStateManager.set_architecture_cache(self.project_id, arch_cache)
                        log("FAST-V2", f"   💾 Cached {len(arch_cache)} architecture files for subsequent steps")
                except Exception as e:
                    log("FAST-V2", f"   ⚠️ Architecture caching failed (non-fatal): {e}")
        except Exception as e:
            log("FAST-V2", f"   ⚠️ Context recording failed: {e}")

    def _load_execution_state(self):
        """
        Phase-0: Rebuild internal state from disk checkpoints.
        Populates self.completed_steps and self.execution_records.
        """
        log("FAST-V2", "🔍 Scanning checkpoints to rebuild state...")
        all_steps = TaskGraph().get_steps()
        
        for step in all_steps:
            # Get latest checkpoint metadata for this step
            checkpoints = self.checkpoint.list_checkpoints(step)
            if not checkpoints:
                continue
                
            # Latest is first in sorted list
            meta = checkpoints[0]
            log("FAST-V2", f"   ✅ Found checkpoint for {step}")
            
            # Record as completed
            if step not in self.completed_steps:
                self.completed_steps.append(step)
            
            # Phase-0: Sync with CrossStepContext
            # Restore all summaries stored in this checkpoint
            checkpoint_summaries = meta.get("step_summaries", {})
            for s_name, s_data in checkpoint_summaries.items():
                self.cross_ctx.record_step_completion(s_name, summary=s_data)
            
            # Restore architecture text
            arch_text = meta.get("architecture")
            if arch_text:
                self.cross_ctx.set_architecture(arch_text)
            
            # Restore entities if architecture exists
            if step == "architecture":
                from app.utils.entity_discovery import discover_entities_from_architecture
                arch_file = self.project_path / "architecture" / "backend.md"
                if arch_file.exists():
                    entities = discover_entities_from_architecture(arch_file)
                    if entities:
                        entity_names = [e.name for e in entities]
                        self.cross_ctx.set_entities(entity_names)
                        log("FAST-V2", f"   🧠 Restored entities: {', '.join(entity_names)}")

            # Rebuild execution record if exists in metadata
            rec_data = meta.get("execution_record")
            if rec_data:
                self.execution_records[step] = StepExecutionRecord.from_dict(rec_data)
                log("FAST-V2", f"   📝 Restored file record for {step} ({len(self.execution_records[step].files_created)} files)")

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE-0/1 HELPER METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def _register_step_files_from_paths(self, step_name: str, file_paths: list):
        """
        Phase-0: Register files created by a step using raw paths.
        """
        record = StepExecutionRecord(step_name=step_name)
        record.files_created = file_paths
        self.execution_records[step_name] = record
        log("FAST-V2", f"   📝 Registered {len(record.files_created)} files for {step_name}")

    def _get_project_snapshot(self) -> dict:
        """Capture a snapshot of the project filesystem for change detection."""
        snapshot = {}
        if not self.project_path.exists():
            return snapshot
            
        # Recursive scan, ignoring heavy/system dirs
        # We only care about source code and architecture artifacts
        ignore_dirs = {
            "node_modules", ".git", "venv", "__pycache__", 
            ".gemini", ".next", "dist", "build", ".pytest_cache"
        }
        
        for path in self.project_path.rglob("*"):
            # Check if any part of the path is in ignore_dirs
            if any(p in path.parts for p in ignore_dirs):
                continue
                
            if path.is_file():
                try:
                    # Store mtime and size as an identity tuple (fast)
                    stat = path.stat()
                    rel_path = str(path.relative_to(self.project_path))
                    snapshot[rel_path] = (stat.st_mtime, stat.st_size)
                except Exception:
                    continue  # Skip files that disappear during scan
        return snapshot

    def _compute_file_delta(self, before: dict, after: dict) -> list:
        """Identify files that were created or modified between snapshots."""
        changed_paths = []
        for path, meta in after.items():
            # If new file or modified existing file
            if path not in before or before[path] != meta:
                changed_paths.append(path)
        return changed_paths

    def _register_step_files(self, step_name: str, files: list):
        """
        Legacy: Register files from dict list.
        """
        paths = [f.get("path") or f.get("file_path") for f in files if isinstance(f, dict)]
        self._register_step_files_from_paths(step_name, paths)

    def _rollback_step(self, step_name: str):
        """
        Phase-0: Delete files created by a failed step.
        Best-effort rollback - continues even if deletions fail.
        """
        record = self.execution_records.get(step_name)
        if not record:
            log("FAST-V2", f"   🗑️ No files to rollback for {step_name}")
            return

        deleted_count = 0
        failed_deletions = []

        for file_path in record.files_created:
            try:
                full_path = self.project_path / file_path
                if full_path.exists():
                    full_path.unlink()
                    deleted_count += 1
            except Exception as e:
                failed_deletions.append((file_path, str(e)))

        log("FAST-V2", f"   🗑️ Rolled back {deleted_count}/{len(record.files_created)} files from {step_name}")
        if failed_deletions:
            log("FAST-V2", f"   ⚠️ Failed to delete {len(failed_deletions)} files (continuing anyway)")

    async def _retry_step_with_hardened_prompt(self, step_name: str, handler, branch):
        """
        Phase-1: Retry a failed step with hardened prompt.
        Returns (success: bool, result: Any)
        """
        from app.handlers import HANDLERS

        log("FAST-V2", f"   🔄 Retrying {step_name} with hardened prompt...")

        # Get hardened retry prompt
        retry_prompt = get_retry_prompt(step_name)

        # Temporarily inject retry prompt into branch
        original_request = branch.intent.get("user_request", "")
        branch.intent["user_request"] = f"{retry_prompt}\n\n{original_request}"
        branch.intent["is_retry"] = True
        branch.intent["temperature_override"] = 0.0  # Deterministic

        try:
            result = await handler(branch)

            # Check if retry succeeded
            if isinstance(result, StepExecutionResult):
                if result.outcome == StepOutcome.SUCCESS:
                    return True, result
                else:
                    return False, result
            else:
                # Legacy StepResult - assume success if no exception
                return True, result

        except Exception as e:
            log("FAST-V2", f"   ❌ Retry failed: {e}")
            return False, None
        finally:
            # Restore original request
            branch.intent["user_request"] = original_request
            branch.intent.pop("is_retry", None)
            branch.intent.pop("temperature_override", None)

    def _generate_halt_artifact(self, step_name: str, reason: str, attempts: int):
        """
        Phase-1: Generate halt artifact for handoff to Phase-2.
        """
        policy = get_execution_policy(step_name)

        halt_artifact = {
            "phase": 1,
            "failed_step": step_name,
            "attempts": attempts,
            "reason": reason,
            "expected": ">=1 file" if policy.requires_output else "valid output",
            "next_phase": "self_healing_required" if attempts > 1 else "retry_available",
            "execution_mode": policy.mode.value,
            "is_fatal": policy.is_fatal,
        }

        # Save to project root
        import json
        halt_file = self.project_path / "phase1_halt.json"
        halt_file.write_text(json.dumps(halt_artifact, indent=2))

        log("FAST-V2", f"   📄 Generated halt artifact: {halt_file}")
        return halt_artifact

    def _should_retry_step(self, step_name: str) -> bool:
        """
        Phase-1: Determine if a step should be retried.
        """
        policy = get_execution_policy(step_name)
        return (
            policy.mode == ExecutionMode.ARTIFACT and
            policy.requires_output and
            policy.max_retries >= 1
        )

async def run_fast_v2_workflow(
    project_id: str,
    manager: Any,
    project_path: Path,
    user_request: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> None:
    engine = FASTOrchestratorV2(
        project_id=project_id,
        manager=manager,
        project_path=project_path,
        user_request=user_request,
        provider=provider,
        model=model,
    )
    await engine.run()
