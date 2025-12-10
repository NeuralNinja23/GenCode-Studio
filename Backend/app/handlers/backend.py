# app/handlers/backend.py
"""
Backend steps: models, routers, and main configuration.

This matches the legacy workflows.py logic exactly.
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



# Constants from legacy
MAX_FILES_PER_STEP = 5
MAX_FILE_LINES = 400


from app.persistence.validator import validate_file_output
from app.orchestration.utils import pluralize



def ensure_workspace_app_package(project_path: Path) -> None:
    """
    Ensure the generated backend's `app` directory is a proper package:
    <workspace>/backend/app/__init__.py
    This is what pytest inside Docker needs for `from app.main import app`.
    """
    app_dir = project_path / "backend" / "app"
    app_dir.mkdir(parents=True, exist_ok=True)

    init_file = app_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text(
            "# Auto-created so `from app.main import app` works in sandbox\n",
            encoding="utf-8",
        )


async def step_backend_implementation(
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
    Step 6: Atomic Backend Implementation (Models + Routers + Requirements).
    
    The Agent writes the COMPLETE vertical slice of the feature in one pass.
    """
    await broadcast_status(
        manager, project_id, WorkflowStep.BACKEND_IMPLEMENTATION,
        f"Turn {current_turn}/{max_turns}: Derek implementing backend vertical (Atomic)...",
        current_turn, max_turns
    )
    
    # Context Loading
    try:
        contracts = (project_path / "contracts.md").read_text(encoding="utf-8")
    except Exception:
        contracts = "Standard CRUD"
        
    intent = WorkflowStateManager.get_intent(project_id) or {}
    entities_list = intent.get("entities", ["item"])
    primary_entity = entities_list[0] if entities_list else "item"
    primary_entity_capitalized = primary_entity.capitalize()
    
    archetype = (intent.get("archetypeRouting") or {}).get("top") or "general"
    
    instruction = f"""Generate the COMPLETE backend feature vertical (Models + Routers) at once.

PROJECT ARCHETYPE: {archetype}
PRIMARY ENTITY: {primary_entity_capitalized}

═══════════════════════════════════════════════════════
🏗️ ATOMIC IMPLEMENTATION STRATEGY
═══════════════════════════════════════════════════════
You are building the entire feature slice now.
Consistency is key. The Model and Router MUST agree on field names.

FILES TO GENERATE:

1. **backend/app/models.py** (Beanie Models)
   - Class {primary_entity_capitalized}
   - Fields matching Contracts
   
2. **backend/app/routers/{primary_entity}s.py** (FastAPI Router)
   - CRUD Endpoints using the Model you just wrote.
   - Import `from app.models import {primary_entity_capitalized}`
   
3. **backend/requirements.txt** (Dependencies)
   - Add ONLY extra libs (e.g. `stripe`). 
   - DO NOT list defaults (fastapi, beanie).

═══════════════════════════════════════════════════════════
🚫 FORBIDDEN FILES (DO NOT TOUCH)
═══════════════════════════════════════════════════════════
- backend/app/main.py (The Integrator handles this)
- backend/app/database.py (Seeded)
- backend/app/db.py (Seeded)
- backend/requirements.txt (Put dependencies in 'manifest' object)

═══════════════════════════════════════════════════════════
📋 CONTRACTS
═══════════════════════════════════════════════════════════
{contracts}

CRITICAL: Return JSON with "files": [...] and "manifest": {{ "dependencies": [...], "backend_routers": [...] }}
"""

    try:
        result = await supervised_agent_call(
            project_id=project_id,
            manager=manager,
            agent_name="Derek",
            step_name="Backend Implementation",
            base_instructions=instruction,
            project_path=project_path,
            user_request=user_request,
            contracts=contracts,
            max_retries=2,
        )
        
        parsed = result.get("output", {})
        
        # 1. Process Manifest (Dependencies)
        manifest = parsed.get("manifest", {})
        dependencies = manifest.get("dependencies", [])
        
        if dependencies:
            repo_reqs_path = project_path / "backend/requirements.txt"
            current_reqs = ""
            if repo_reqs_path.exists():
                current_reqs = repo_reqs_path.read_text(encoding="utf-8")
            
            # Merge dependencies
            merged_deps = set(current_reqs.splitlines()) | set(dependencies)
            merged_content = "\n".join(sorted([d for d in merged_deps if d.strip() and not d.startswith("#")]))
            
            repo_reqs_path.write_text(merged_content, encoding="utf-8")
            log("BACKEND", f"📦 Added {len(dependencies)} dependencies from manifest.")

        # 2. Process Files
        if "files" in parsed and parsed["files"]:
            validated = validate_file_output(parsed, WorkflowStep.BACKEND_IMPLEMENTATION, max_files=5)
            files_written = await persist_agent_output(manager, project_id, project_path, validated, WorkflowStep.BACKEND_IMPLEMENTATION)

            status = "✅ approved" if result.get("approved") else "⚠️ best effort"
            log("BACKEND", f"Derek implemented backend vertical ({files_written} files, {status})")

    except Exception as e:
        log("BACKEND", f"Implementation failed: {e}")

    return StepResult(
        nextstep=WorkflowStep.SYSTEM_INTEGRATION,
        turn=current_turn + 1,
    )


async def step_system_integration(
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
    Step 7: System Integration (Script).
    
    Deterministic wiring of agent-generated modules into the Golden Seed.
    """
    await broadcast_status(
        manager, project_id, WorkflowStep.SYSTEM_INTEGRATION,
        f"Turn {current_turn}/{max_turns}: System Integrator wiring modules...",
        current_turn, max_turns
    )
    
    # Detect routers
    routers_dir = project_path / "backend/app/routers"
    existing_routers = []
    if routers_dir.exists():
        existing_routers = [f.stem.lower() for f in routers_dir.glob("*.py") if f.stem != "__init__"]
        
    log("BACKEND", f"🔗 Integrator found {len(existing_routers)} routers to wire.")
    
    main_py_path = project_path / "backend/app/main.py"
    if main_py_path.exists() and existing_routers:
        content = main_py_path.read_text(encoding="utf-8")
        
        imports_block = ""
        routes_block = ""
        
        for router in existing_routers:
            imports_block += f"from app.routers import {router}\n"
            routes_block += f"app.include_router({router}.router, prefix='/api/{router}', tags=['{router}'])\n"
            
        # Inject Imports
        if "# @ROUTER_IMPORTS" in content:
            content = content.replace("# @ROUTER_IMPORTS", f"# @ROUTER_IMPORTS\n{imports_block}")
        elif imports_block not in content:
            content = f"{imports_block}\n{content}"
            
        # Inject Routes
        if "# @ROUTER_REGISTER" in content:
            content = content.replace("# @ROUTER_REGISTER", f"# @ROUTER_REGISTER\n{routes_block}")
        elif routes_block not in content:
            content += f"\n{routes_block}"
            
        main_py_path.write_text(content, encoding="utf-8")
        log("BACKEND", "✅ Main.py wired successfully.")
        
    ensure_workspace_app_package(project_path)
    
    return StepResult(
        nextstep=WorkflowStep.TESTING_BACKEND,
        turn=current_turn + 1,
    )
