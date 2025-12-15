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
    from app.utils.entity_discovery import EntityPlan
    from app.handlers.base import broadcast_agent_log
    from app.handlers.backend_models import step_backend_models
    import re
    
    # V3: Cumulative token tracking
    step_token_usage = {"input": 0, "output": 0}
    
    # 0. Generate Models First (Multi-entity models phase)
    log("BACKEND", "🏗️ Generating database models first...")
    models_result = await step_backend_models(
        project_id, user_request, manager, project_path,
        chat_history, provider, model, current_turn, max_turns
    )
    
    if models_result.status == "error":
        log("BACKEND", f"❌ Model generation failed: {models_result.error}")
        return models_result

    # Accumulate token usage
    if models_result.token_usage:
        step_token_usage["input"] += models_result.token_usage.get("input", 0)
        step_token_usage["output"] += models_result.token_usage.get("output", 0)
    
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
    
    # FIX #5: FILTER TO AGGREGATE ENTITIES ONLY FOR ROUTER GENERATION
    # EMBEDDED entities don't need routers - they're nested in other models!
    aggregate_entities = [e for e in entities_sorted if e.type == "AGGREGATE"]
    embedded_entities = [e for e in entities_sorted if e.type == "EMBEDDED"]
    
    if embedded_entities:
        log("BACKEND", f"🔒 Skipping {len(embedded_entities)} EMBEDDED entities (no routers needed): {[e.name for e in embedded_entities]}")
    
    log("BACKEND", f"📋 Generating {len(aggregate_entities)} routers for AGGREGATE entities: {[e.name for e in aggregate_entities]}")
    
    # Load contracts
    try:
        contracts = (project_path / "contracts.md").read_text(encoding="utf-8")
    except Exception:
        contracts = "Standard CRUD"
    
    # Generate each router
    routers_generated = []
    
    for entity in aggregate_entities:
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
                step_name="Backend Implementation",
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
   - 🚨 CRITICAL: Define endpoints at root ('/').
     - `@router.get("/")` (List)
     - `@router.post("/")` (Create)
     - `@router.get("/{{id}}")` (Get One)
     - `@router.put("/{{id}}")` (Update)
     - `@router.delete("/{{id}}")` (Delete)

═══════════════════════════════════════════════════════════
🚨 NON-NEGOTIABLE API RESPONSE CONTRACT
═══════════════════════════════════════════════════════════
These rules are MANDATORY. Violations cause test failures.

1. **STATUS CODES (Strict)**:
   - GET /  → 200
   - POST / → 201 (use `status_code=status.HTTP_201_CREATED`)
   - GET /{{id}} → 200 (or 404 if not found)
   - PUT /{{id}} → 200 (or 404 if not found)
   - DELETE /{{id}} → 204 No Content (use `status_code=status.HTTP_204_NO_CONTENT`)

2. **RESPONSE SHAPE (Strict)**:
   - GET / must return a LIST of objects: `[{{"id": "...", "title": "...", "status": "..."}}]`
   - POST / must return the created object: `{{"id": "...", "title": "...", "status": "..."}}`
   - GET /{{id}} must return the object: `{{"id": "...", "title": "...", "status": "..."}}`
   - PUT /{{id}} must return the updated object: `{{"id": "...", "title": "...", "status": "..."}}`
   - DELETE /{{id}} must return NOTHING (empty response body)
   
   🚨 Do NOT wrap responses in `{{"data": ...}}`. Return flat objects/arrays directly.
   
3. **FIELD NAMES (Strict)**:
   - Use "id" (string) NOT "_id"
   - Use "title" (string)
   - Use "status" (string, either "active" or "completed")

4. **FILTERING (Mandatory)**:
   - GET / must accept `?status=active` or `?status=completed` query param
   - Filter server-side and return only matching items
   - Return 200 with empty list for invalid status values

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
    
    CONTRACT-AWARE: Extracts entity-specific section from contracts.md
    and includes it in Derek's prompt so he knows exact requirements
    (pagination, filters, query params, response format).
    """
    import re
    from app.orchestration.utils import pluralize
    
    entity_name = entity.name
    entity_plural = entity.plural
    
    # Extract entity-specific contract section
    entity_contract = _extract_entity_contract(contracts, entity_plural)
    
    return f"""Generate a FastAPI router for the {entity_name} entity.

ENTITY: {entity_name}
ENDPOINT PREFIX: /api/{entity_plural}

═══════════════════════════════════════════════════════
CONTRACT SPECIFICATION FOR {entity_name.upper()}
═══════════════════════════════════════════════════════

{entity_contract}

═══════════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════════

Generate a complete FastAPI router that implements the EXACT specification above.

🚨 CRITICAL REQUIREMENTS:

1. **Import model**: `from app.models import {entity_name}`

2. **Create router**: `router = APIRouter()` (NO prefix or tags)

3. **PATH DEFINITIONS** (THIS IS CRITICAL - READ CAREFULLY):
   
   ✅ CORRECT - Use these paths:
   ```python
   @router.get("/", ...)           # List all {entity_plural}
   @router.post("/", ...)          # Create new {entity_name}
   @router.get("/{{id}}", ...)      # Get one {entity_name}
   @router.put("/{{id}}", ...)      # Update {entity_name}
   @router.delete("/{{id}}", ...)   # Delete {entity_name}
   ```
   
   ❌ WRONG - DO NOT use these paths:
   ```python
   @router.get("/{entity_plural}", ...)         # WRONG - creates /api/{entity_plural}/{entity_plural}
   @router.post("/{entity_plural}", ...)        # WRONG - double prefix
   @router.get("/{entity_plural}/{{id}}", ...)   # WRONG - triple nesting
   ```
   
   **WHY:** The main.py includes the router with `prefix='/api/{entity_plural}'`
   So path "/" becomes "/api/{entity_plural}/" automatically!
   
   **REMEMBER:** Always use "/" and "/{{id}}" - NEVER use "/{entity_plural}"

4. **Implement ALL endpoints from the contract** with EXACT signatures:
   - If contract shows pagination (page, limit), implement it
   - If contract shows filters (category, status, search), implement them
   - If contract shows query params, add them as FastAPI Query() parameters
   - Use the EXACT response format from contract (data/total/page/limit wrapper)

5. **Response Format** (from contract):
   - List endpoints: {{"data": [...], "total": int, "page": int, "limit": int}}
   - Single item: {{"data": {{...}}}}
   - Errors: {{"error": {{"code": str, "message": str}}}}

6. **Implementation**:
   - Use Beanie async methods (await {entity_name}.find_all(), etc.)
   - For pagination: use .skip((page-1)*limit).limit(limit)
   - For filters: use Beanie query filters
   - Return proper HTTP status codes (200, 201, 404, etc.)
   - Use HTTPException for errors

═══════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════

Return ONLY valid JSON:

{{
  "thinking": "I will implement {entity_name} router following the contract specification, including pagination/filters...",
  "files": [
    {{
      "path": "backend/app/routers/{entity_plural}.py",
      "content": "from fastapi import APIRouter, Query, HTTPException\\nfrom app.models import {entity_name}\\n\\nrouter = APIRouter()\\n..."
    }}
  ]
}}

Generate the complete, contract-compliant router now!
"""


def _extract_entity_contract(contracts: str, entity_plural: str) -> str:
    """
    Extract the entity-specific section from contracts.md.
    
    Finds headings like "### Expenses" or "## Expenses" and extracts
    everything until the next heading of same/higher level.
    
    Returns the full specification for that entity including all endpoints.
    """
    import re
    
    if not contracts:
        return f"No contract found. Implement standard CRUD for {entity_plural}."
    
    # Normalize entity name for matching (handle "Expense" vs "Expenses")
    entity_singular = entity_plural.rstrip('s')  # Simple singularization
    
    # Try to find section with entity name (case-insensitive)
    # Patterns: "### Expenses", "## Expenses", "### Expense", etc.
    pattern = rf"(?:^|\n)(#{1,3})\s+({entity_plural}|{entity_singular})\b"
    match = re.search(pattern, contracts, re.IGNORECASE | re.MULTILINE)
    
    if not match:
        # Fallback: return first 1500 chars (general context)
        return f"Full contracts (entity section not found):\n\n{contracts[:1500]}"
    
    # Extract heading level and start position
    heading_level = len(match.group(1))  # Number of # chars
    start_pos = match.start()
    
    # Find next heading of same or higher level (fewer # chars)
    # E.g., if we matched "### Expenses", stop at next ##, ###, or #
    next_heading_pattern = rf"\n#{{{1,{heading_level}}}}\s+"
    next_match = re.search(next_heading_pattern, contracts[start_pos + 1:], re.MULTILINE)
    
    if next_match:
        end_pos = start_pos + 1 + next_match.start()
        entity_section = contracts[start_pos:end_pos]
    else:
        # No next heading - take rest of document
        entity_section = contracts[start_pos:]
    
    # Trim to reasonable length (leave room for rest of prompt)
    if len(entity_section) > 3000:
        entity_section = entity_section[:3000] + "\n\n[... contract continues ...]"
    
    return entity_section.strip()



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
        # ═══════════════════════════════════════════════════════════
        # USE CENTRALIZED WIRING UTILS
        # This ensures both routers AND models are wired correctly.
        # ═══════════════════════════════════════════════════════════
        from app.orchestration.wiring_utils import wire_router, wire_model
        
        for router in existing_routers:
            wire_router(project_path, router)
        
        # ═══════════════════════════════════════════════════════════
        # WIRE MODELS (CRITICAL - Fixes Beanie 500 Error)
        # Without this, init_beanie() gets an empty list and all
        # collection operations fail with 500 Server Error.
        #
        # BUG FIX: Use extract_all_models_from_models_py instead of
        # discover_primary_entity. The old approach discovered entities
        # from mock.js (e.g., "Category") but Derek might generate
        # different models (e.g., "Expense"), causing ImportError crashes.
        #
        # FIX #7: FILTER OUT EMBEDDED MODELS (2025-12-15)
        # Use extract_document_models_only() instead of extract_all_models_from_models_py()
        # to prevent wiring embedded BaseModel classes to Beanie.
        # Only AGGREGATE entities (Document) should be wired!
        # ═══════════════════════════════════════════════════════════
        from app.utils.entity_discovery import extract_document_models_only
        
        actual_models = extract_document_models_only(project_path)
        for model_name in actual_models:
            wire_model(project_path, model_name)
            log("BACKEND", f"🔗 Wired AGGREGATE model: {model_name}")
        
        # Re-read content for audit log injection
        content = main_py_path.read_text(encoding="utf-8")
        
        # ---------------------------------------------------------------------------
        # INJECT ROUTE AUDIT LOG
        # ---------------------------------------------------------------------------
        audit_marker = "print(\"📊 [Route Audit] Registered Routes:\")"
        if audit_marker not in content:
            log("BACKEND", "📊 Injecting Runtime Route Audit Log into main.py")
            content += "\n\n" + """# ---------------------------------------------------------------------------
# ROUTE AUDIT LOG
# ---------------------------------------------------------------------------
print("📊 [Route Audit] Registered Routes:")
for route in app.routes:
    if hasattr(route, "path") and hasattr(route, "methods"):
        methods = ", ".join(route.methods)
        print(f"   - {methods} {route.path}")
"""
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
