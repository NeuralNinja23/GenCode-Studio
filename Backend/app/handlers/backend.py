# app/handlers/backend.py
"""
Backend steps: models, routers, and main configuration.

This matches the legacy workflows.py logic exactly.
"""
from pathlib import Path
from typing import Any, List

from app.core.types import ChatMessage, StepResult
from app.core.constants import WorkflowStep
from app.handlers.base import broadcast_status
from app.core.logging import log
from app.orchestration.state import WorkflowStateManager
from app.supervision import supervised_agent_call
from app.persistence import persist_agent_output
from app.persistence.validator import validate_file_output

# Centralized entity discovery for dynamic fallback
from app.utils.entity_discovery import discover_primary_entity
from app.handlers.archetype_guidance import get_full_backend_context, get_archetype_patterns_from_store



# Constants from legacy
MAX_FILES_PER_STEP = 5
MAX_FILE_LINES = 400


async def _validate_integration(project_path: Path, routers: List[str]) -> bool:
    """
    Validate that integrated routes are accessible using contract-driven testing.
    
    Uses:
    - ContractParser to extract expected routes from contracts.md
    - BackendProbe to test routes in environment-agnostic way
    
    No hardcoded /api/notes or /api/cats - everything is contract-derived.
    
    Args:
        project_path: Path to workspace
        routers: List of router names that were integrated (for legacy compat, not used)
    
    Returns:
        True if all contract routes are accessible
    """
    from app.orchestration.contract_parser import ContractParser
    from app.orchestration.backend_probe import BackendProbe, ProbeMode
    
    # Parse expected routes from contracts
    parser = ContractParser(project_path)
    expected_routes = parser.get_expected_routes()
    
    if not expected_routes:
        log("VALIDATION", "⚠️ No contract routes found - validation skipped")
        return True
    
    log("VALIDATION", f"📋 Validating {len(expected_routes)} contract routes")
    
    # ═══════════════════════════════════════════════════════════
    # RESTART DOCKER: Pick up new router code written by backend_implementation
    # Bug Fix #2: Added file sync delay to prevent race condition
    # ═══════════════════════════════════════════════════════════
    try:
        from app.tools.implementations import SANDBOX
        from app.sandbox import SandboxConfig
        import asyncio
        
        # Extract project_id from path
        project_id = project_path.name
        
        log("VALIDATION", "🔄 Syncing files before Docker restart...")
        
        # Bug Fix #2: Ensure files are flushed to disk before Docker sees them
        # Touch main.py to force filesystem sync
        main_py = project_path / "backend" / "app" / "main.py"
        if main_py.exists():
            main_py.touch()  # Updates mtime, forces buffer flush
        
        # Wait for filesystem to catch up (Windows is slower than Linux)
        await asyncio.sleep(2)
        
        log("VALIDATION", "🔄 Restarting Docker to pick up new router code...")
        
        # Check if sandbox exists, create if not
        status = await SANDBOX.get_status(project_id)
        if not status.get("success"):
            log("VALIDATION", "📦 Creating sandbox for first time...")
            create_result = await SANDBOX.create_sandbox(
                project_id=project_id,
                project_path=project_path,
                config=SandboxConfig(),
            )
            if not create_result.get("success"):
                log("VALIDATION", f"⚠️ Sandbox create failed: {create_result.get('error')}")
        else:
            # Stop existing sandbox before restart
            await SANDBOX.stop_sandbox(project_id)
            await asyncio.sleep(1)
        
        # Start with build to pick up new code
        start_result = await SANDBOX.start_sandbox(
            project_id=project_id,
            wait_healthy=True,
            services=["backend"]
        )
        
        if start_result.get("success"):
            log("VALIDATION", "✅ Docker restarted with new code")
            # Extra wait for uvicorn --reload to pick up changes
            await asyncio.sleep(3)
        else:
            log("VALIDATION", f"⚠️ Docker restart failed: {start_result.get('error')}")
            
    except Exception as e:
        log("VALIDATION", f"⚠️ Docker restart error: {e}")
    
    # Create probe for Docker environment (where tests run)
    # Pass project_id for dynamic port detection
    probe = BackendProbe.from_env(ProbeMode.DOCKER, project_id=project_id)
    
    # Test each route
    failures = []
    for route in expected_routes:
        passed = await probe.check_route(
            method=route.method,
            path=route.path,
            expected_status=route.expected_status,
            timeout=5.0
        )
        
        if passed:
            log("VALIDATION", f"  ✅ {route.method} {route.path} → {route.expected_status}")
        else:
            log("VALIDATION", f"  ❌ {route.method} {route.path} failed")
            failures.append(route)
    
    if failures:
        log("VALIDATION", f"❌ {len(failures)} route(s) failed validation")
        return False
    
    log("VALIDATION", "✅ All contract routes validated successfully")
    return True


# NOTE: _extract_entity_from_request was removed
# Now using centralized extract_entity_from_request from entity_discovery
from app.utils.entity_discovery import extract_entity_from_request as _extract_entity_from_request



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
    Step 6: Backend Implementation (Models + Routers).
    
    TWO MODES:
    1. MULTI-ENTITY: If entity_plan.json exists, generate routers per-entity in a loop
    2. SINGLE-ENTITY (Legacy): Atomic generation of everything in one call
    
    The mode is auto-detected based on presence of entity_plan.json.
    """
    await broadcast_status(
        manager, project_id, WorkflowStep.BACKEND_IMPLEMENTATION,
        f"Turn {current_turn}/{max_turns}: Derek implementing backend...",
        current_turn, max_turns
    )
    
    # Check for multi-entity mode
    entity_plan_path = project_path / "entity_plan.json"
    use_multi_entity_mode = entity_plan_path.exists()
    
    if use_multi_entity_mode:
        log("BACKEND", "🔄 Multi-entity mode enabled")
        return await _step_backend_multi_entity(
            project_id, user_request, manager, project_path,
            chat_history, provider, model, current_turn, max_turns
        )
    else:
        log("BACKEND", "📦 Single-entity atomic mode")
        return await _step_backend_single_entity(
            project_id, user_request, manager, project_path,
            chat_history, provider, model, current_turn, max_turns
        )


async def _step_backend_multi_entity(
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
    Multi-entity backend implementation.
    
    Flow:
    1. Load entity_plan.json
    2. For each entity (in generation_order):
       a. Generate router for that entity
       b. Write router file
       c. Wire to main.py
       d. Validate wiring
    3. Return success
    """
    from app.utils.entity_specs import EntityPlan
    from app.handlers.base import broadcast_agent_log
    import re
    
    # V3: Cumulative token tracking
    step_token_usage = {"input": 0, "output": 0}
    
    # Load entity plan
    try:
        entity_plan = EntityPlan.load(project_path / "entity_plan.json")
        entities = entity_plan.entities
        relationships = entity_plan.relationships
    except Exception as e:
        log("BACKEND", f"❌ Failed to load entity_plan.json: {e}")
        return StepResult(
            nextstep=WorkflowStep.SYSTEM_INTEGRATION,
            turn=current_turn + 1,
            status="error",
            error=f"Failed to load entity plan: {str(e)}",
        )
    
    # Sort entities by generation_order
    entities_sorted = sorted(entities, key=lambda e: e.generation_order)
    
    log("BACKEND", f"📋 Generating {len(entities_sorted)} routers: {[e.name for e in entities_sorted]}")
    
    # Load contracts
    try:
        contracts = (project_path / "contracts.md").read_text(encoding="utf-8")
    except Exception:
        contracts = "Standard CRUD"
    
    # Generate each router
    routers_generated = []
    
    for entity in entities_sorted:
        log("BACKEND", f"🔧 Generating router for {entity.name}...")
        
        await broadcast_agent_log(
            manager,
            project_id,
            "AGENT:Derek",
            f"Generating {entity.name} router..."
        )
        
        # Build entity-specific prompt
        entity_instruction = _build_single_router_prompt(entity, contracts)
        
        try:
            result = await supervised_agent_call(
                project_id=project_id,
                manager=manager,
                agent_name="Derek",
                step_name=f"Backend Router: {entity.name}",
                base_instructions=entity_instruction,
                project_path=project_path,
                user_request=user_request,
                contracts=contracts,
                max_retries=1,
            )
            
            # V3: Accumulate token usage
            if result.get("token_usage"):
                usage = result.get("token_usage")
                step_token_usage["input"] += usage.get("input", 0)
                step_token_usage["output"] += usage.get("output", 0)
            
            parsed = result.get("output", {})
            
            # Process files
            if "files" in parsed and parsed["files"]:
                # Sanitize router files
                for file_obj in parsed["files"]:
                    path = file_obj.get("path", "")
                    content = file_obj.get("content", "")
                    
                    # SANITIZER: Remove prefix and tags from APIRouter
                    if "routers" in path:
                        content = re.sub(r'prefix\s*=\s*[\'"][^\'"]+[\'\"]\s*,?', '', content)
                        content = re.sub(r'tags\s*=\s*\[[^\]]+\]\s*,?', '', content)
                        file_obj["content"] = content
                
                validated = validate_file_output(parsed, WorkflowStep.BACKEND_IMPLEMENTATION, max_files=5)
                files_written = await persist_agent_output(manager, project_id, project_path, validated, WorkflowStep.BACKEND_IMPLEMENTATION)
                
                log("BACKEND", f"✅ Generated {entity.plural}.py router ({files_written} files)")
                routers_generated.append(entity.plural)
        
        except Exception as e:
            log("BACKEND", f"❌ Failed to generate {entity.name} router: {e}")
            # Continue with other entities
    
    log("BACKEND", f"✅ Multi-entity backend complete: {len(routers_generated)} routers")
    
    return StepResult(
        nextstep=WorkflowStep.SYSTEM_INTEGRATION,
        turn=current_turn + 1,
        data={
            "mode": "multi_entity",
            "routers_count": len(routers_generated),
            "routers": routers_generated,
        },
        token_usage=step_token_usage,
    )


async def _step_backend_single_entity(
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
    Single-entity atomic backend implementation (LEGACY MODE).
    
    The Agent writes the COMPLETE vertical slice of the feature in one pass.
    """
    # Context Loading
    try:
        contracts = (project_path / "contracts.md").read_text(encoding="utf-8")
    except Exception:
        contracts = "Standard CRUD"
        
    intent = await WorkflowStateManager.get_intent(project_id) or {}
    entities_list = intent.get("entities", [])
    
    # Use centralized discovery as fallback with dynamic last-resort
    if entities_list:
        primary_entity = entities_list[0]
    else:
        entity_name, _ = discover_primary_entity(project_path)
        if entity_name:
            primary_entity = entity_name
        else:
            # Dynamic last resort: extract from user request or use domain-based name
            primary_entity = _extract_entity_from_request(user_request) or "entity"
    
    primary_entity_capitalized = primary_entity.capitalize()
    
    archetype = (intent.get("archetypeRouting") or {}).get("top") or "general"
    domain = intent.get("domain", "general")
    
    # Get archetype-specific backend guidance
    backend_archetype_guidance = get_full_backend_context(
        archetype=archetype,
        entity=primary_entity,
        domain=domain
    )
    
    # Get learned patterns from Pattern Store (pre-training integration)
    pattern_hints = get_archetype_patterns_from_store(archetype, "backend_implementation")
    
    log("BACKEND", f"🔧 Generating backend for archetype: {archetype}")
    
    instruction = f"""Generate the COMPLETE backend feature vertical (Models + Routers) at once.

PROJECT ARCHETYPE: {archetype}
PRIMARY ENTITY: {primary_entity_capitalized}

{backend_archetype_guidance}

{pattern_hints}

═══════════════════════════════════════════════════════
🏗️ ATOMIC IMPLEMENTATION STRATEGY
═══════════════════════════════════════════════════════
You are building the entire feature slice now.
Consistency is key. The Model and Router MUST agree on field names.

🚨 SCHEMA COMPLIANCE RULES (CRITICAL):
1. You MUST use the EXACT field names from the CONTRACTS section below.
2. Do NOT use synonyms (e.g. if contract says 'description', do NOT use 'content' or 'body').
3. Do NOT add required fields that are not in the contract (this breaks frontend).
4. DO NOT define `id` or `_id` fields. Beanie adds them automatically. Defining them triggers a CRITICAL STARTUP CRASH.

FILES TO GENERATE:

1. **backend/app/models.py** (Beanie Models)
   - Class {primary_entity_capitalized}
   - Fields matching Contracts
   - Include all CRUD operations
   - 🚨 CRITICAL: Do NOT define `id` or `_id` fields (Beanie handles this automatically).
   
   2. **backend/app/routers/{primary_entity}s.py** (FastAPI Router)
   - CRUD Endpoints using the Model you just wrote
   - Import `from app.models import {primary_entity_capitalized}`
   - Include proper error handling
   - 🚨 CRITICAL: Do NOT use `prefix` or `tags` in APIRouter(). Just `router = APIRouter()`.
     (The system integrator handles routing prefixes globally)
   - 🚨 CRITICAL: Define endpoints at root ('/') (e.g., `@router.get("/")` NOT `@router.get("/users")`).

═══════════════════════════════════════════════════════════
🚫 FORBIDDEN FILES (DO NOT TOUCH)
═══════════════════════════════════════════════════════════
- backend/app/main.py (The Integrator handles this)
- backend/app/database.py (Seeded)
- backend/app/db.py (Seeded)
- backend/requirements.txt (Put extra dependencies in 'manifest' object instead)

═══════════════════════════════════════════════════════════
📋 CONTRACTS
═══════════════════════════════════════════════════════════
{contracts}

═══════════════════════════════════════════════════════════
📤 OUTPUT FORMAT (CRITICAL - MUST MATCH THIS EXACTLY)
═══════════════════════════════════════════════════════════

Return ONLY valid JSON with this EXACT structure:

{{
  "thinking": "Detailed explanation of your implementation approach for {primary_entity_capitalized}...",
  "manifest": {{
    "dependencies": ["stripe", "redis"],
    "backend_routers": ["{primary_entity}s"],
    "notes": "Any additional context or incomplete work"
  }},
  "files": [
    {{ "path": "backend/app/models.py", "content": "from beanie import Document\\n\\nclass {primary_entity_capitalized}(Document):\\n    ..." }},
    {{ "path": "backend/app/routers/{primary_entity}s.py", "content": "from fastapi import APIRouter\\n\\nrouter = APIRouter()\\n..." }}
  ]
}}

🚨 CRITICAL REQUIREMENTS:
- Each file object MUST have BOTH "path" and "content" fields
- The "path" field MUST be the full file path (e.g., "backend/app/models.py")
- The "content" field MUST have COMPLETE, non-empty code
- DO NOT generate backend/requirements.txt as a file - use manifest.dependencies instead

Generate the complete backend vertical for {primary_entity_capitalized} now!
"""
    # V3: Track token usage for cost reporting
    step_token_usage = None
    
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
        
        # V3: Extract token usage from supervisor result
        step_token_usage = result.get("token_usage")
        
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
            # 🛡️ SYSTEM HARDENING: Sanitize Agent Output
            # We enforce correctness here deterministically to prevent common crashes
            import re
            
            for file_obj in parsed["files"]:
                path = file_obj.get("path", "")
                content = file_obj.get("content", "")
                
                # SANITIZER 1: Beanie Models - Remove explicit 'id' fields
                # Agent often adds 'id: str' or '_id: PydanticObjectId' which crashes Beanie
                if "models.py" in path:
                    content = re.sub(
                        r'(^\s*)(_?id)\s*:', 
                        r'\1# \2: # 🛡️ AUTO-FIXED: Beanie handles IDs', 
                        content, 
                        flags=re.MULTILINE
                    )
                
                # SANITIZER 2: Routers - Remove 'prefix' and 'tags' from APIRouter
                # Agent often adds prefix (e.g., prefix="/users") which clashes with Integrator (result: /api/users/users)
                if "routers" in path:
                    # Remove prefix="..." 
                    content = re.sub(
                        r'prefix\s*=\s*[\'"][^\'"]+[\'\"]\s*,?', 
                        '', 
                        content
                    )
                    # Remove tags=["..."]
                    content = re.sub(
                        r'tags\s*=\s*\[[^\]]+\]\s*,?', 
                        '', 
                        content
                    )
                    
                file_obj["content"] = content

            validated = validate_file_output(parsed, WorkflowStep.BACKEND_IMPLEMENTATION, max_files=5)
            files_written = await persist_agent_output(manager, project_id, project_path, validated, WorkflowStep.BACKEND_IMPLEMENTATION)

            status = "✅ approved" if result.get("approved") else "⚠️ best effort"
            log("BACKEND", f"Derek implemented backend vertical ({files_written} files, {status})")

    except Exception as e:
        log("BACKEND", f"Implementation failed: {e}")

    return StepResult(
        nextstep=WorkflowStep.SYSTEM_INTEGRATION,
        turn=current_turn + 1,
        token_usage=step_token_usage,  # V3: Pass actual usage to orchestrator
    )


def _build_single_router_prompt(entity, contracts: str) -> str:
    """
    Build prompt for generating a single entity's router.
    
    Used in multi-entity mode to generate one router at a time.
    """
    from app.orchestration.utils import pluralize
    
    entity_name = entity.name
    entity_plural = entity.plural
    
    return f"""Generate a FastAPI router for the {entity_name} entity.

ENTITY: {entity_name}
ENDPOINT PREFIX: /api/{entity_plural}

═══════════════════════════════════════════════════════
CONTRACTS (Reference)
═══════════════════════════════════════════════════════

{contracts[:2000]}

═══════════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════════

Generate a complete FastAPI router for {entity_name} with CRUD operations.

REQUIREMENTS:
1. Import the {entity_name} model: `from app.models import {entity_name}`
2. Create router: `router = APIRouter()` (NO prefix or tags)
3. Implement endpoints:
   - GET / - List all {entity_plural}
   - POST / - Create new {entity_name}
   - GET /{{id}} - Get single {entity_name}
   - PUT /{{id}} - Update {entity_name}
   - DELETE /{{id}} - Delete {entity_name}
4. Use proper error handling (HTTPException for not found, etc.)
5. Use Beanie async methods (await {entity_name}.find_all(), etc.)

═══════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════

Return ONLY valid JSON:

{{
  "thinking": "Brief explanation...",
  "files": [
    {{
      "path": "backend/app/routers/{entity_plural}.py",
      "content": "from fastapi import APIRouter\\nfrom app.models import {entity_name}\\n\\nrouter = APIRouter()\\n..."
    }}
  ]
}}

Generate the complete router now!
"""


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
        
        import re
        
        # Build import and route blocks, but ONLY for routers not already registered
        imports_block = ""
        routes_block = ""
        
        for router in existing_routers:
            import_line = f"from app.routers import {router}"
            route_line = f"app.include_router({router}.router, prefix='/api/{router}', tags=['{router}'])"
            
            # Check if this router is already imported/registered (idempotency check)
            # Uses shared utilities for consistency with healing manager
            from app.orchestration.router_utils import is_router_imported, is_router_registered
            router_already_imported = is_router_imported(content, router)
            router_already_registered = is_router_registered(content, router)
            
            if not router_already_imported:
                imports_block += f"{import_line}\n"
            
            if not router_already_registered:
                routes_block += f"{route_line}\n"
        
        # If using markers, we do a CLEAN replacement (removes old registrations within marker blocks)
        # This is the safest approach - markers define the canonical location for registrations
        if "# @ROUTER_IMPORTS" in content:
            # Build fresh import block for ALL routers (marker approach = clean slate)
            all_imports = "\n".join([f"from app.routers import {r}" for r in existing_routers])
            # FIXED: Preserve full marker line (including "- DO NOT REMOVE THIS LINE")
            content = re.sub(
                r'^(# @ROUTER_IMPORTS[^\n]*)\n((?:from app\.routers[^\n]*\n)*)',
                f"\\1\n{all_imports}\n",
                content,
                flags=re.MULTILINE
            )
        elif imports_block:
            # No markers - just prepend new imports
            content = f"{imports_block}\n{content}"
            
        if "# @ROUTER_REGISTER" in content:
            # Build fresh route block for ALL routers (marker approach = clean slate)
            all_routes = "\n".join([
                f"app.include_router({r}.router, prefix='/api/{r}', tags=['{r}'])" 
                for r in existing_routers
            ])
            # FIXED: Preserve full marker line (including "- DO NOT REMOVE THIS LINE")
            content = re.sub(
                r'^(# @ROUTER_REGISTER[^\n]*)\n((?:app\.include_router[^\n]*\n)*)',
                f"\\1\n{all_routes}\n",
                content,
                flags=re.MULTILINE
            )
        elif routes_block:
            # No markers - append only new routes
            content += f"\n{routes_block}"
            
        main_py_path.write_text(content, encoding="utf-8")
        log("BACKEND", "✅ Main.py wired successfully.")
        
        # ════════════════════════════════════════════════════════════
        # POST-INTEGRATION VALIDATION
        # ════════════════════════════════════════════════════════════
        validation_passed = await _validate_integration(project_path, existing_routers)
        if not validation_passed:
            log("BACKEND", "❌ Integration validation failed - routes not accessible")
            # Return with error status to trigger healing
            return StepResult(
                nextstep=WorkflowStep.TESTING_BACKEND,
                turn=current_turn + 1,
                status="error",
                data={"error": "Integration validation failed: routes returned 404"}
            )
        
    ensure_workspace_app_package(project_path)
    
    return StepResult(
        nextstep=WorkflowStep.TESTING_BACKEND,
        turn=current_turn + 1,
    )
