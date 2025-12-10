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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    step_backend_models,
    step_backend_routers,
    step_backend_main,
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
    WorkflowStep.BACKEND_MODELS: step_backend_models,  # Step 6
    WorkflowStep.BACKEND_ROUTERS: step_backend_routers,  # Step 7
    WorkflowStep.BACKEND_MAIN: step_backend_main,  # Step 8
    WorkflowStep.TESTING_BACKEND: step_testing_backend,  # Step 9
    WorkflowStep.FRONTEND_INTEGRATION: step_frontend_integration,  # Step 10: Replace mock with API
    WorkflowStep.TESTING_FRONTEND: step_testing_frontend,  # Step 11
    WorkflowStep.PREVIEW_FINAL: step_preview_final,  # Step 12
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
        
        WorkflowStateManager.pause_workflow(
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
    
    # Create project directory
    project_path = workspaces_path / project_id
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
        # 🔒 A. COPY INFRASTRUCTURE FILES ONLY
        # ============================================================
        
        # --- Backend Infrastructure ---
        backend_tmpl = base_templates / "backend"
        backend_dest = project_path / "backend"
        backend_dest.mkdir(parents=True, exist_ok=True)
        
        # Copy only infrastructure files (NOT app code, NOT requirements.txt)
        # Note: conftest.py is in tests/ directory, not at backend root
        backend_infra_files = ["pytest.ini", "requirements.lock"]
        for fname in backend_infra_files:
            src = backend_tmpl / fname
            if src.exists():
                shutil.copy2(src, backend_dest / fname)
        
        # Create backend/tests directory with conftest and __init__.py
        (backend_dest / "tests").mkdir(exist_ok=True)
        if (backend_tmpl / "tests" / "conftest.py").exists():
            shutil.copy2(backend_tmpl / "tests" / "conftest.py", backend_dest / "tests" / "conftest.py")
        if (backend_tmpl / "tests" / "__init__.py").exists():
            shutil.copy2(backend_tmpl / "tests" / "__init__.py", backend_dest / "tests" / "__init__.py")
        else:
            # Create __init__.py if template doesn't have one (for proper pytest discovery)
            (backend_dest / "tests" / "__init__.py").write_text("# Tests package\n", encoding="utf-8")
        
        # Create empty backend/app directory (agents will populate)
        (backend_dest / "app").mkdir(exist_ok=True)
        (backend_dest / "app" / "__init__.py").write_text("# Generated by GenCode Studio\n", encoding="utf-8")
        
        # Create backend/app/routers directory with __init__.py (required for router imports)
        (backend_dest / "app" / "routers").mkdir(exist_ok=True)
        (backend_dest / "app" / "routers" / "__init__.py").write_text("# Routers package - Derek will add router modules\n", encoding="utf-8")
        
        # log("WORKFLOW", "Copied backend infrastructure (pytest.ini, conftest.py, __init__.py, routers/)")
        
        # --- Frontend Infrastructure ---
        frontend_tmpl = base_templates / "frontend"
        frontend_dest = project_path / "frontend"
        frontend_dest.mkdir(parents=True, exist_ok=True)
        
        # Copy only infrastructure files (NOT package.json, NOT playwright.config)
        frontend_infra_files = [
            "vite.config.js",
            "postcss.config.js",
            "tailwind.config.js",
            "jsconfig.json",
            "index.html",
        ]
        for fname in frontend_infra_files:
            src = frontend_tmpl / fname
            if src.exists():
                shutil.copy2(src, frontend_dest / fname)
        
        # Copy public directory if exists
        if (frontend_tmpl / "public").exists():
            shutil.copytree(frontend_tmpl / "public", frontend_dest / "public", dirs_exist_ok=True)
        
        # log("WORKFLOW", "Copied frontend infrastructure (vite.config, tailwind, etc.)")
        
        # ============================================================
        # 🎨 COPY SHADCN UI LIBRARY (Treated as stable library)
        # ============================================================
        src_dest = frontend_dest / "src"
        src_dest.mkdir(exist_ok=True)
        
        # Copy shadcn/ui components (the only src files we copy)
        ui_src = frontend_tmpl / "src" / "components" / "ui"
        ui_dest = src_dest / "components" / "ui"
        if ui_src.exists():
            shutil.copytree(ui_src, ui_dest, dirs_exist_ok=True)
            # log("WORKFLOW", "Copied shadcn/ui component library (55 components)")
        
        # Copy lib/utils.js (required for shadcn cn() function)
        lib_src = frontend_tmpl / "src" / "lib"
        lib_dest = src_dest / "lib"
        if lib_src.exists():
            shutil.copytree(lib_src, lib_dest, dirs_exist_ok=True)
        
        # Copy base CSS (Tailwind directives + CSS variables)
        if (frontend_tmpl / "src" / "index.css").exists():
            shutil.copy2(frontend_tmpl / "src" / "index.css", src_dest / "index.css")
        
        # Copy main.jsx (React entry point)
        if (frontend_tmpl / "src" / "main.jsx").exists():
            shutil.copy2(frontend_tmpl / "src" / "main.jsx", src_dest / "main.jsx")
        
        # ============================================================
        # ✨ CREATE DIRECTORIES FOR AGENT-GENERATED CODE
        # Derek will generate App.jsx, pages/*, and data/mock.js
        # ============================================================
        (src_dest / "pages").mkdir(exist_ok=True)
        (src_dest / "components").mkdir(exist_ok=True)  # For custom components (not ui/)
        (src_dest / "data").mkdir(exist_ok=True)
        (frontend_dest / "tests").mkdir(exist_ok=True)
        
        # NOTE: App.jsx, Home.jsx, and mock.js are NO LONGER copied
        # Derek generates ALL application source files from scratch
        # Only infrastructure (main.jsx, index.css, shadcn/ui) is templated
        
        # log("WORKFLOW", "Created directories for agent-generated code")

        # ============================================================
        # 🐳 DOCKER INFRASTRUCTURE
        # ============================================================
        docker_tmpl = base_templates / "docker"
        if docker_tmpl.exists():
            # Copy backend Dockerfile
            if (docker_tmpl / "Dockerfile.backend").exists():
                shutil.copy2(docker_tmpl / "Dockerfile.backend", backend_dest / "Dockerfile")
                
            # Copy frontend Dockerfile
            if (docker_tmpl / "Dockerfile.frontend").exists():
                shutil.copy2(docker_tmpl / "Dockerfile.frontend", frontend_dest / "Dockerfile")
                
            # Copy docker-compose
            if (docker_tmpl / "docker-compose.yml").exists():
                 shutil.copy2(docker_tmpl / "docker-compose.yml", project_path / "docker-compose.yml")
            
            # Copy .dockerignore to both backend and frontend
            if (docker_tmpl / ".dockerignore").exists():
                shutil.copy2(docker_tmpl / ".dockerignore", backend_dest / ".dockerignore")
                shutil.copy2(docker_tmpl / ".dockerignore", frontend_dest / ".dockerignore")
            
            # Create frontend/.env with VITE_API_URL
            # This is infrastructure configuration, not generated by agents
            frontend_env_content = """# Frontend Environment Variables
# DO NOT MODIFY - These are configured for the Docker sandbox

# Backend API URL
# In Docker: Uses internal Docker network hostname
# In local dev: Uses localhost
VITE_API_URL=http://localhost:8001/api
"""
            (frontend_dest / ".env").write_text(frontend_env_content, encoding="utf-8")
                 
            # log("WORKFLOW", "Copied Docker infrastructure (Dockerfiles, docker-compose.yml, .dockerignore)")
            
        # ============================================================
        # 📋 COPY REFERENCE TEMPLATES (For agent context)
        # ============================================================
        # Backend reference
        if (backend_tmpl / "reference").exists():
            shutil.copytree(backend_tmpl / "reference", backend_dest / "reference", dirs_exist_ok=True)
            
        # Frontend reference
        if (frontend_tmpl / "reference").exists():
            shutil.copytree(frontend_tmpl / "reference", frontend_dest / "reference", dirs_exist_ok=True)
            
        # log("WORKFLOW", "Copied reference configurations for agent context")
        # 📋 NOTE: Reference configs are NOT copied
        # ============================================================
        # The following are in templates/.../reference/ and will be read by agents:
        # - frontend/reference/package.example.json
        # - frontend/reference/playwright.config.example.js
        # - backend/reference/requirements.example.txt
        # Agents generate real versions of these files during workflow.
        
        # log("WORKFLOW", f"[{project_id}] Scaffolding complete (new 3-tier policy)")
            
    except Exception as e:
        log("WORKFLOW", f"Failed to scaffold project: {e}")

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
    paused = WorkflowStateManager.get_paused_state(project_id)
    
    if paused:
        # Resume from saved state
        log("WORKFLOW", f"Resuming paused workflow for {project_id}")
        WorkflowStateManager.resume_workflow(project_id)
        
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
