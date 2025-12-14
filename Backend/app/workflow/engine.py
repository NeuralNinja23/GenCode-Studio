# app/workflow/engine.py
"""
Workflow Engine - The main orchestration loop.

This implements the GenCode Studio FRONTEND-FIRST workflow:
1. Analysis (Marcus) - Understand requirements
2. Architecture (Victoria) - Design system
3. Frontend Mock (Derek) - Create frontend with mock data (aha moment!)
4. Screenshot Verify (Marcus) - Visual QA of frontend
5. Contracts (Marcus) - Define API contracts based on frontend mock
6. Backend Models (Derek) - Create database models
7. Backend Routers (Derek) - Create API endpoints
8. Backend Main (Derek) - Wire up main app
9. Testing Backend (Derek) - Run pytest
10. Frontend Integration (Derek) - Replace mock with real API
11. Testing Frontend (Luna) - Run Playwright
12. Preview (Marcus) - Show running app
"""
import asyncio
import traceback
from pathlib import Path
from typing import Any, List, Optional

from app.core.constants import WorkflowStep, WSMessageType
from app.core.types import ChatMessage, StepResult
from app.core.config import settings
from app.orchestration.state import WorkflowStateManager, CURRENT_MANAGERS
from app.core.logging import log
from app.orchestration.utils import broadcast_to_project
from app.handlers import (
    step_analysis,
    step_architecture,
    step_frontend_mock,  # Frontend-first with mock
    step_screenshot_verify,  # NEW: Visual QA after frontend
    step_contracts,
    step_backend_implementation, # Atomic Backend
    step_system_integration, # Script Integrator
    step_testing_backend,
    step_frontend_integration,  # Replace mock with API
    step_testing_frontend,
    step_preview_final,
    step_refine,
)
# NOTE: Cost tracking now handled by BudgetManager in engine_v2/budget_manager.py


# Step handler registry - GENCODE STUDIO FRONTEND-FIRST ORDER
STEP_HANDLERS = {
    WorkflowStep.ANALYSIS: step_analysis,
    WorkflowStep.ARCHITECTURE: step_architecture,
    WorkflowStep.FRONTEND_MOCK: step_frontend_mock,  # Step 3: Frontend with mock data
    WorkflowStep.SCREENSHOT_VERIFY: step_screenshot_verify,  # Step 4: Visual QA
    WorkflowStep.CONTRACTS: step_contracts,  # Step 5: API contracts from mock
    WorkflowStep.BACKEND_IMPLEMENTATION: step_backend_implementation, # Step 6: Atomic Vertical
    WorkflowStep.SYSTEM_INTEGRATION: step_system_integration, # Step 7: Integrator
    WorkflowStep.TESTING_BACKEND: step_testing_backend,  # Step 8
    WorkflowStep.FRONTEND_INTEGRATION: step_frontend_integration,  # Step 9
    WorkflowStep.TESTING_FRONTEND: step_testing_frontend,  # Step 10
    WorkflowStep.PREVIEW_FINAL: step_preview_final,  # Step 11
    WorkflowStep.REFINE: step_refine,  # Post-workflow refinement
}


class WorkflowEngine:
    """
    The main workflow engine.
    
    Executes the GenCode Studio FRONTEND-FIRST workflow:
    
    1. Analysis (Marcus) - Understand and clarify requirements
    2. Architecture (Victoria) - Design system architecture  
    3. Frontend Mock (Derek) - Create frontend with mock data (aha moment!)
    4. Screenshot Verify (Marcus) - Visual QA of the frontend
    5. Contracts (Marcus) - Define API contracts for backend
    6. Backend Models (Derek) - Create database models
    7. Backend Routers (Derek) - Create API endpoints
    8. Backend Main (Derek) - Wire up the main app
    9. Testing Backend (Derek) - Test backend with pytest
    10. Frontend Integration (Derek) - Replace mock with real API
    11. Testing Frontend (Luna) - E2E tests with Playwright
    12. Preview (Marcus) - Show running application
    """
    
    def __init__(
        self,
        project_id: str,
        manager: Any,
        project_path: Path,
        user_request: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.project_id = project_id
        self.manager = manager
        self.project_path = project_path
        self.user_request = user_request
        self.provider = provider or settings.llm.default_provider
        self.model = model or settings.llm.default_model
        self.chat_history: List[ChatMessage] = []
        self.current_step = WorkflowStep.ANALYSIS
        self.current_turn = 1
        self.max_turns = settings.workflow.max_turns
    
    async def run(self) -> None:
        """Execute the workflow loop."""
        log("WORKFLOW", f"Starting workflow for {self.project_id}", project_id=self.project_id)
        
        # Register manager
        CURRENT_MANAGERS[self.project_id] = self.manager
        # Note: set_running() is called in run_workflow() before engine creation
        
        try:
            while self.current_turn <= self.max_turns:
                handler = STEP_HANDLERS.get(self.current_step)
                
                if not handler:
                    log("WORKFLOW", f"No handler for step {self.current_step}, ending")
                    break
                
                log("WORKFLOW", f"Executing step: {self.current_step} (turn {self.current_turn})")
                
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
                
                # ═══════════════════════════════════════════════════════
                # CHECKPOINT: Save progress after each step completes
                # ═══════════════════════════════════════════════════════
                try:
                    from app.orchestration.checkpoint import save_checkpoint
                    await save_checkpoint(
                        project_id=self.project_id,
                        step_name=self.current_step,
                        turn=self.current_turn,
                        output=result.data if hasattr(result, 'data') else {},
                        context={
                            "user_request": self.user_request,
                            "provider": self.provider,
                            "model": self.model,
                            "current_turn": self.current_turn,
                            "max_turns": self.max_turns,
                        },
                        status="completed" if result.status == "ok" else "failed",
                    )
                except Exception as cp_error:
                    log("WORKFLOW", f"⚠️ Checkpoint save failed (non-fatal): {cp_error}")
                
                # FIX #15: Use configuration instead of magic number
                max_chat_history = settings.workflow.max_chat_history
                if len(self.chat_history) > max_chat_history:
                    # Keep system message (if any) and trim oldest
                    self.chat_history = self.chat_history[-max_chat_history:]
                
                if result.pause:
                    await self._pause_workflow(result)
                    return
                
                self.current_step = result.nextstep
                self.current_turn = result.turn
                
                if self.current_step == WorkflowStep.COMPLETE:
                    break
                
                await asyncio.sleep(0.5)
            
            await self._complete_workflow()
            
        except Exception as e:
            await self._fail_workflow(e)
        finally:
            await self._cleanup()
    
    async def _pause_workflow(self, result: StepResult) -> None:
        """Pause the workflow for user input."""
        log("WORKFLOW", f"Pausing at {self.current_step}")
        
        await WorkflowStateManager.pause_workflow(
            self.project_id,
            self.current_step,
            self.current_turn,
            self.chat_history,
            self.user_request,
            self.project_path,
            self.provider,
            self.model,
        )
        
        await broadcast_to_project(
            self.manager,
            self.project_id,
            {
                "type": WSMessageType.WORKFLOW_PAUSED,
                "projectId": self.project_id,
                "step": self.current_step,
                "message": result.data.get("message", "Waiting for input"),
            },
        )
    
    async def _complete_workflow(self) -> None:
        """Complete the workflow successfully."""
        log("WORKFLOW", "Workflow completed successfully!")
        
        await broadcast_to_project(
            self.manager,
            self.project_id,
            {
                "type": WSMessageType.WORKFLOW_COMPLETE,
                "projectId": self.project_id,
                "totalTurns": self.current_turn,
                "message": "Application generated successfully!",
                # NOTE: Cost tracking now handled by BudgetManager
            },
        )
    
    async def _fail_workflow(self, error: Exception) -> None:
        """Handle workflow failure."""
        log("WORKFLOW", f"Workflow failed: {error}")
        
        await broadcast_to_project(
            self.manager,
            self.project_id,
            {
                "type": WSMessageType.WORKFLOW_FAILED,
                "projectId": self.project_id,
                "step": self.current_step,
                "error": str(error),
                "trace": traceback.format_exc(),
            },
        )
    
    async def _cleanup(self) -> None:
        """Clean up workflow state atomically."""
        CURRENT_MANAGERS.pop(self.project_id, None)
        # FIX #3: Use atomic stop_workflow to prevent race conditions
        await WorkflowStateManager.stop_workflow(self.project_id)
        log("WORKFLOW", "Workflow cleanup complete")


async def run_workflow(
    project_id: str,
    description: str,
    workspaces_path: Path,
    manager: Any,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> None:
    """
    Start a new workflow for a project.
    
    This is the main entry point for starting workflows.
    Uses GenCode Studio FRONTEND-FIRST pattern.
    """
    # ===== GUARD: Atomically check and mark as running (FIX #1) =====
    # This prevents race conditions where two requests both pass is_running check
    can_start = await WorkflowStateManager.try_start_workflow(project_id)
    if not can_start:
        log("WORKFLOW", f"⚠️ Workflow already running for {project_id}, ignoring duplicate request", project_id=project_id)
        return
    
    # Create project directory (Atomic scaffolding)
    final_project_path = workspaces_path / project_id
    
    # FIX ATOMIC-001: Use temporary directory until scaffolding is complete
    # This prevents broken project state if scaffolding fails halfway
    temp_dir_name = f".tmp_scaffold_{project_id}"
    project_path = workspaces_path / temp_dir_name
    if project_path.exists():
        import shutil
        shutil.rmtree(project_path)
    project_path.mkdir(parents=True, exist_ok=True)
    
    # ============================================================
    # NEW SCAFFOLDING POLICY (3-Tier Template System)
    # ============================================================
    # 🔒 A. COPY DIRECTLY (Infrastructure) - Docker, build configs
    # 📋 B. REFERENCE ONLY (Configuration) - package.json, playwright.config, requirements.txt
    #       These are in templates/.../reference/ and read by agents as examples
    # ✨ C. AGENT GENERATED (Source Code) - All app code, frontend/src/**, backend/app/**
    # ============================================================
    
    try:
        import shutil
        base_templates = settings.paths.base_dir / "backend" / "templates"
        
        # ============================================================
        # 👑 GOLDEN SEED SCAFFOLDING (Hybrid Manifest System)
        # ============================================================
        
        # --- Backend Seed ---
        backend_dest = project_path / "backend"
        backend_dest.mkdir(parents=True, exist_ok=True)
        
        backend_seed = base_templates / "backend" / "seed"
        if backend_seed.exists():
            shutil.copytree(backend_seed, backend_dest, dirs_exist_ok=True)
            log("WORKFLOW", "✅ Seeded Backend Infrastructure (DB, Core, Auth)")
        else:
             log("WORKFLOW", "⚠️ Missing Backend Seed Template!")

        # Create routers/__init__.py manually if not in seed (Safety net)
        (backend_dest / "app" / "routers").mkdir(exist_ok=True)
        if not (backend_dest / "app" / "routers" / "__init__.py").exists():
            (backend_dest / "app" / "routers" / "__init__.py").write_text("# Routers package\n", encoding="utf-8")
        
        # --- Seed Test Template (Option C) ---
        # Copy test_api.py.template for Derek to use as reference
        tests_dest = backend_dest / "tests"
        tests_dest.mkdir(parents=True, exist_ok=True)
        
        # Ensure tests/__init__.py exists
        if not (tests_dest / "__init__.py").exists():
            (tests_dest / "__init__.py").write_text("# Tests package\n", encoding="utf-8")
        
        # Copy the template file for Derek to reference
        test_template_src = backend_seed / "tests" / "test_api.py.template"
        if test_template_src.exists():
            test_template_dest = tests_dest / "test_api.py.template"
            shutil.copy2(test_template_src, test_template_dest)
            log("WORKFLOW", "✅ Seeded Test Template (backend/tests/test_api.py.template)")
        
        # --- Frontend Seed ---
        frontend_dest = project_path / "frontend"
        frontend_dest.mkdir(parents=True, exist_ok=True)
        
        frontend_seed = base_templates / "frontend" / "seed"
        if frontend_seed.exists():
            shutil.copytree(frontend_seed, frontend_dest, dirs_exist_ok=True)
            log("WORKFLOW", "✅ Seeded Frontend Infrastructure (API, AuthContext)")
        
        # Copy Base Frontend (Vite Boilerplate) - excluding reference/seed
        # We need the build configs and base structure
        frontend_base = base_templates / "frontend"
        for item in frontend_base.iterdir():
            if item.name in ["seed", "reference"]:
                continue # Skip specialized folders
            if item.is_file():
                shutil.copy2(item, frontend_dest / item.name)
            elif item.is_dir() and item.name == "src":
                # Special merge for src: Don't overwrite seed/src files
                # IMPORTANT: Skip components/ui - these are copied on-demand by component_copier
                # This keeps projects lean (only 5-10 UI components instead of 55+)
                src_dir = frontend_dest / "src"
                for src_item in item.rglob("*"):
                    if src_item.is_file():
                        # Skip ui components - copied on-demand after Derek generates code
                        rel_path = src_item.relative_to(item)
                        if "components/ui" in str(rel_path).replace("\\", "/"):
                            continue
                        dest_path = src_dir / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        if not dest_path.exists():  # Don't overwrite seed files
                            shutil.copy2(src_item, dest_path)
            elif item.is_dir() and item.name == "public":
                 shutil.copytree(item, frontend_dest / "public", dirs_exist_ok=True)

        # --- Seed Frontend Test Template (Option C for Frontend) ---
        # Copy e2e.spec.js.template for Luna to use as reference
        frontend_tests_dest = frontend_dest / "tests"
        frontend_tests_dest.mkdir(parents=True, exist_ok=True)
        
        # Copy the test template file for Luna to reference
        frontend_test_template_src = frontend_seed / "tests" / "e2e.spec.js.template"
        if frontend_test_template_src.exists():
            frontend_test_template_dest = frontend_tests_dest / "e2e.spec.js.template"
            shutil.copy2(frontend_test_template_src, frontend_test_template_dest)
            log("WORKFLOW", "✅ Seeded Frontend Test Template (frontend/tests/e2e.spec.js.template)")

        # --- Docker Infrastructure ---
        # FIX: Align with new template structure (backend/Dockerfile, frontend/Dockerfile)
        
        # 1. Backend Docker Config
        backend_tmpl = base_templates / "backend"
        if (backend_tmpl / "Dockerfile").exists():
             shutil.copy2(backend_tmpl / "Dockerfile", backend_dest / "Dockerfile")
        if (backend_tmpl / ".dockerignore").exists():
             shutil.copy2(backend_tmpl / ".dockerignore", backend_dest / ".dockerignore")
             
        # 2. Frontend Docker Config
        frontend_tmpl = base_templates / "frontend"
        if (frontend_tmpl / "Dockerfile").exists():
             shutil.copy2(frontend_tmpl / "Dockerfile", frontend_dest / "Dockerfile")
        if (frontend_tmpl / ".dockerignore").exists():
             shutil.copy2(frontend_tmpl / ".dockerignore", frontend_dest / ".dockerignore")

        # 3. Root Docker Compose
        docker_tmpl = base_templates / "docker"
        if docker_tmpl.exists():
            if (docker_tmpl / "docker-compose.yml").exists():
                 shutil.copy2(docker_tmpl / "docker-compose.yml", project_path / "docker-compose.yml")
            
            # Create frontend/.env with VITE_API_URL
            frontend_env_content = """# Frontend Environment Variables
# VITE_API_URL=http://localhost:8001/api (Local)
VITE_API_URL=http://localhost:8001/api
"""
            (frontend_dest / ".env").write_text(frontend_env_content, encoding="utf-8")
        
        log("WORKFLOW", f"[{project_id}] Golden Seed Scaffolding Complete")
        
        # FIX ATOMIC-001: Commit atomic scaffolding
        if final_project_path.exists():
            shutil.rmtree(final_project_path)
        shutil.move(str(project_path), str(final_project_path))
        project_path = final_project_path  # Point to real path for engine
            
    except Exception as e:
        log("WORKFLOW", f"Failed to scaffold project: {e}")
        # Cleanup temp
        if project_path.exists() and "tmp_scaffold" in str(project_path):
             try:
                 shutil.rmtree(project_path)
             except Exception as e:
                 log("WORKFLOW", f"Cleanup failed (non-fatal): {e}")
        
        # Don't proceed if scaffolding failed
        await WorkflowStateManager.stop_workflow(project_id)
        return

    # ============================================================
    # ENGINE SELECTION: FAST V2 (Hybrid Adaptive)
    # ============================================================
    # V2: Uses existing handlers + dependency barriers + self-healing
    # ============================================================
    
    from app.orchestration.fast_orchestrator import FASTOrchestratorV2
    
    log("WORKFLOW", f"🚀 Using FAST V2 ENGINE for {project_id}")
    engine = FASTOrchestratorV2(
        project_id=project_id,
        manager=manager,
        project_path=project_path,
        user_request=description,
        provider=provider,
        model=model,
    )
    
    await engine.run()


# Backwards compatibility
async def autonomous_agent_workflow(
    project_id: str,
    description: str,
    workspaces_path: Path,
    manager: Any,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> None:
    """Backwards-compatible wrapper."""
    await run_workflow(project_id, description, workspaces_path, manager, provider, model)


async def resume_workflow(
    project_id: str,
    user_message: str,
    manager: Any,
    workspaces_dir: Path,
) -> None:
    """
    Resume a paused workflow OR start a refine workflow for completed projects.
    
    - If workflow is paused: Resume from saved state
    - If project exists but not paused: Start refine workflow
    - If project doesn't exist: Log warning and return
    """
    paused = await WorkflowStateManager.get_paused_state(project_id)
    
    if paused:
        # Resume from saved state
        log("WORKFLOW", f"Resuming paused workflow for {project_id}")
        await WorkflowStateManager.resume_workflow(project_id)
        
        engine = WorkflowEngine(
            project_id=project_id,
            manager=manager,
            project_path=Path(paused["project_path"]),
            user_request=user_message,
            provider=paused.get("provider"),
            model=paused.get("model"),
        )
        engine.current_step = paused["step"]
        engine.current_turn = paused["turn"]
        engine.chat_history = paused.get("chat_history", [])
        
        await engine.run()
    else:
        # Check if project exists - if so, start refine workflow
        project_path = workspaces_dir / project_id
        
        if project_path.exists():
            log("WORKFLOW", f"Starting refine workflow for {project_id}")
            
            # FIX #4: Use atomic try_start_workflow to prevent race conditions
            can_start = await WorkflowStateManager.try_start_workflow(project_id)
            if not can_start:
                log("WORKFLOW", f"⚠️ Workflow already running for {project_id}, ignoring")
                return
            
            # Start refine workflow (starts at REFINE step)
            engine = WorkflowEngine(
                project_id=project_id,
                manager=manager,
                project_path=project_path,
                user_request=user_message,
                provider=settings.llm.default_provider,
                model=settings.llm.default_model,
            )
            engine.current_step = WorkflowStep.REFINE
            
            await engine.run()
        else:
            log("WORKFLOW", f"No project found for {project_id}, cannot resume/refine")
