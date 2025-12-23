# app/workflow/engine.py
"""
Workflow Entry Points - Facade for FASTOrchestratorV2.

Phase 2 Refactor:
- WorkflowEngine (Class) REMOVED.
- FASTOrchestratorV2 is the sole execution engine.
- This file provides entry points: run_workflow, resume_workflow.
"""
import asyncio
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings
from app.orchestration.state import WorkflowStateManager, CURRENT_MANAGERS
from app.core.logging import log
from app.orchestration.fast_orchestrator import FASTOrchestratorV2

async def run_workflow(
    project_id: str,
    description: str,
    workspaces_path: Path,
    manager: Any,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> None:
    """
    Start a new workflow for a project using FASTOrchestratorV2.
    """
    # ===== GUARD: Atomically check and mark as running =====
    can_start = await WorkflowStateManager.try_start_workflow(project_id)
    if not can_start:
        log("WORKFLOW", f"⚠️ Workflow already running for {project_id}, ignoring duplicate request", project_id=project_id)
        return
    
    # Create project directory (Atomic scaffolding)
    final_project_path = workspaces_path / project_id
    
    # Use temporary directory until scaffolding is complete
    temp_dir_name = f".tmp_scaffold_{project_id}"
    project_path = workspaces_path / temp_dir_name
    if project_path.exists():
        import shutil
        shutil.rmtree(project_path)
    project_path.mkdir(parents=True, exist_ok=True)
    
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
            # Copy while EXCLUDING agent-owned artifacts
            def agent_artifact_filter(src, names):
                ignored = []
                for name in names:
                    if name == "models.py" and "app" in str(src):
                        ignored.append(name)
                    if "routers" in str(src) and name.endswith(".py") and name != "__init__.py":
                        ignored.append(name)
                return ignored

            shutil.copytree(backend_seed, backend_dest, dirs_exist_ok=True, ignore=agent_artifact_filter)
        else:
             log("WORKFLOW", "⚠️ Missing Backend Seed Template!")

        # Create routers/__init__.py manually if it was filtered out
        (backend_dest / "app" / "routers").mkdir(exist_ok=True, parents=True) 
        if not (backend_dest / "app" / "routers" / "__init__.py").exists():
            (backend_dest / "app" / "routers" / "__init__.py").write_text("# Routers package\n", encoding="utf-8")
        
        # --- Seed Test Template ---
        tests_dest = backend_dest / "tests"
        tests_dest.mkdir(parents=True, exist_ok=True)
        
        if not (tests_dest / "__init__.py").exists():
            (tests_dest / "__init__.py").write_text("# Tests package\n", encoding="utf-8")
        
        test_template_src = backend_seed / "tests" / "test_contract_api.template"
        if test_template_src.exists():
            test_template_dest = tests_dest / "test_contract_api.template"
            shutil.copy2(test_template_src, test_template_dest)
        
        # --- Frontend Seed ---
        frontend_dest = project_path / "frontend"
        frontend_dest.mkdir(parents=True, exist_ok=True)
        
        frontend_seed = base_templates / "frontend" / "seed"
        if frontend_seed.exists():
            shutil.copytree(frontend_seed, frontend_dest, dirs_exist_ok=True)
        
        # Copy Base Frontend (Vite Boilerplate)
        frontend_base = base_templates / "frontend"
        for item in frontend_base.iterdir():
            if item.name in ["seed", "reference"]:
                continue 
            if item.is_file():
                shutil.copy2(item, frontend_dest / item.name)
            elif item.is_dir() and item.name == "src":
                src_dir = frontend_dest / "src"
                for src_item in item.rglob("*"):
                    if src_item.is_file():
                        rel_path = src_item.relative_to(item)
                        # Skip ui components - copied on-demand
                        if "components/ui" in str(rel_path).replace("\\", "/"):
                            continue
                        dest_path = src_dir / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        if not dest_path.exists():  
                            shutil.copy2(src_item, dest_path)
            elif item.is_dir() and item.name == "public":
                 shutil.copytree(item, frontend_dest / "public", dirs_exist_ok=True)

        # --- Frontend Tests Directory ---
        frontend_tests_dest = frontend_dest / "tests"
        frontend_tests_dest.mkdir(parents=True, exist_ok=True)

        # --- Docker Infrastructure ---
        backend_tmpl = base_templates / "backend"
        if (backend_tmpl / "Dockerfile").exists():
             shutil.copy2(backend_tmpl / "Dockerfile", backend_dest / "Dockerfile")
        if (backend_tmpl / ".dockerignore").exists():
             shutil.copy2(backend_tmpl / ".dockerignore", backend_dest / ".dockerignore")
             
        frontend_tmpl = base_templates / "frontend"
        if (frontend_tmpl / "Dockerfile").exists():
             shutil.copy2(frontend_tmpl / "Dockerfile", frontend_dest / "Dockerfile")
        if (frontend_tmpl / ".dockerignore").exists():
             shutil.copy2(frontend_tmpl / ".dockerignore", frontend_dest / ".dockerignore")

        docker_tmpl = base_templates / "docker"
        if docker_tmpl.exists():
            if (docker_tmpl / "docker-compose.yml").exists():
                 shutil.copy2(docker_tmpl / "docker-compose.yml", project_path / "docker-compose.yml")
            
            frontend_env_content = """# Frontend Environment Variables
VITE_API_URL=http://localhost:8001/api
"""
            (frontend_dest / ".env").write_text(frontend_env_content, encoding="utf-8")
        
        # Commit atomic scaffolding
        if final_project_path.exists():
            shutil.rmtree(final_project_path)
        shutil.move(str(project_path), str(final_project_path))
        project_path = final_project_path 
            
    except Exception as e:
        log("WORKFLOW", f"Failed to scaffold project: {e}")
        if project_path.exists() and "tmp_scaffold" in str(project_path):
             try:
                 shutil.rmtree(project_path)
             except Exception as cleanup_err:
                 log("WORKFLOW", f"Cleanup failed (non-fatal): {cleanup_err}")
        
        await WorkflowStateManager.stop_workflow(project_id)
        return

    # Start Engine
    engine = FASTOrchestratorV2(
        project_id=project_id,
        manager=manager,
        project_path=project_path,
        user_request=description,
        provider=provider,
        model=model,
    )
    
    await engine.run()


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
    Resume a paused workflow OR start a refine workflow.
    Uses FASTOrchestratorV2 for execution.
    """
    paused = await WorkflowStateManager.get_paused_state(project_id)
    project_path = workspaces_dir / project_id
    
    is_refinement = False
    provider = settings.llm.default_provider
    model = settings.llm.default_model

    if paused:
        log("WORKFLOW", f"Resuming paused workflow for {project_id}")
        await WorkflowStateManager.resume_workflow(project_id)
        
        if paused.get("step") == "refine":
            is_refinement = True
        
        provider = paused.get("provider") or provider
        model = paused.get("model") or model
    else:
        # Check if project exists - if so, start refine workflow
        if project_path.exists():
            log("WORKFLOW", f"Starting refine workflow for {project_id}")
            is_refinement = True
        else:
            log("WORKFLOW", f"No project found for {project_id}, cannot resume/refine")
            return

    # Atomic start check
    can_start = await WorkflowStateManager.try_start_workflow(project_id)
    if not can_start:
        log("WORKFLOW", f"⚠️ Workflow already running for {project_id}, ignoring")
        return

    # Start engine
    # If refining, is_refinement=True
    # If resuming normal workflow, resume_from_checkpoint=True (unless it was paused at start?)
    # Note: resume_from_checkpoint loads completed steps from disk.
    
    engine = FASTOrchestratorV2(
        project_id=project_id,
        manager=manager,
        project_path=project_path,
        user_request=user_message,
        provider=provider,
        model=model,
        resume_from_checkpoint=not is_refinement, 
        is_refinement=is_refinement,
    )
    
    await engine.run()


async def resume_from_checkpoint_workflow(
    project_id: str,
    description: str,
    workspaces_path: Path,
    manager: Any,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> bool:
    """
    Resume a workflow explicitly from saved checkpoint (UI triggered).
    """
    has_progress = await WorkflowStateManager.has_progress(project_id)
    
    if not has_progress:
        log("WORKFLOW", f"No saved progress for {project_id}, cannot resume")
        return False
    
    project_path = workspaces_path / project_id
    if not project_path.exists():
        log("WORKFLOW", f"Project directory not found: {project_path}")
        return False
    
    # Guard
    can_start = await WorkflowStateManager.try_start_workflow(project_id)
    if not can_start:
        log("WORKFLOW", f"⚠️ Workflow already running for {project_id}")
        return False
    
    log("WORKFLOW", f"🔄 Resuming FAST V2 workflow for {project_id} from checkpoint")
    
    engine = FASTOrchestratorV2(
        project_id=project_id,
        manager=manager,
        project_path=project_path,
        user_request=description,
        provider=provider,
        model=model,
        resume_from_checkpoint=True,
    )
    
    await engine.run()
    return True
