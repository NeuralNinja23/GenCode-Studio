# app/handlers/backend_routers.py
"""
Step 4: Derek generates FastAPI routers for all aggregate entities.

This step depends on Step 3 (Backend Models) being successful.
Derek reads architecture.md for contracts and models.py for schema details.
"""
import re
from pathlib import Path
from typing import Any, List, Dict

from app.core.types import StepResult
from app.core.constants import WorkflowStep
from app.handlers.base import broadcast_status, broadcast_agent_log
from app.core.logging import log
from app.orchestration.state import WorkflowStateManager
from app.supervision import supervised_agent_call
from app.utils.entity_discovery import EntityPlan
from app.core.failure_boundary import FailureBoundary
from app.core.file_writer import validate_file_output, persist_agent_output
from app.core.step_invariants import StepInvariants, StepInvariantError
from app.core.step_outcome import StepOutcome

@FailureBoundary.enforce
async def step_backend_routers(branch) -> StepResult:
    """
    Step 4: Backend Router Implementation.
    
    Flow:
    1. Load entity plan and models.py
    2. For each AGGREGATE entity, generate its FastAPI router
    """
    from app.arbormind.cognition.branch import Branch
    assert isinstance(branch, Branch)
    
    # Extract context from branch
    project_id = branch.intent["project_id"]
    user_request = branch.intent["user_request"]
    manager = branch.intent["manager"]
    project_path = branch.intent["project_path"]
    
    await broadcast_status(
        manager, project_id, WorkflowStep.BACKEND_ROUTERS,
        f"Derek generating entity routers...",
        4, 9
    )
    
    # ═════════════════════════
    # STEP 4 INVARIANT: Models MUST exist before routers
    # Check both possible locations due to path inconsistency
    # ═════════════════════════
    models_py = project_path / "backend" / "app" / "models.py"
    models_py_alt = project_path / "app" / "models.py"  # Alternative location
    
    if not models_py.exists() and not models_py_alt.exists():
        log("BACKEND_ROUTERS", "❌ models.py not found at backend/app/models.py or app/models.py")
        # ISSUE 2 FIX: This is a FAILURE, not a skip
        # Return with status="failed" so orchestrator knows work was not done
        return StepResult(
            nextstep=None,  # Signal: cannot proceed
            turn=4,
            status="failed",  # CRITICAL: Not "ok" - work was NOT done
            data={"routers_count": 0, "error": "models.py missing - cannot generate routers"},
            error="Backend routers require models.py to exist first"
        )
    
    # Copy models.py to correct location if in alternative path
    if not models_py.exists() and models_py_alt.exists():
        log("BACKEND_ROUTERS", f"📦 Found models.py at {models_py_alt}, copying to {models_py}")
        models_py.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy(models_py_alt, models_py)
    
    # V3: Cumulative token tracking
    step_token_usage = {"input": 0, "output": 0}
    
    # Load entity plan
    try:
        entity_plan = EntityPlan.load(project_path / "entity_plan.json")
        entities = entity_plan.entities
    except Exception as e:
        log("BACKEND_ROUTERS", f"⚠️ Failed to load entity_plan.json: {e}. Skipping (non-fatal).")
        return StepResult(
            nextstep=WorkflowStep.SYSTEM_INTEGRATION,
            turn=5,
            data={"routers_count": 0, "warning": f"entity plan error: {e}"},
        )
    
    # Sort entities by generation_order
    entities_sorted = sorted(entities, key=lambda e: e.generation_order)
    
    # FILTER TO AGGREGATE ENTITIES ONLY FOR ROUTER GENERATION
    aggregate_entities = [e for e in entities_sorted if e.type == "AGGREGATE"]
    
    # V2.1: Use cached architecture from Victoria's output
    from app.orchestration.state import WorkflowStateManager
    arch_cache = await WorkflowStateManager.get_architecture_cache(project_id)
    
    if "backend" in arch_cache:
        architecture_backend = arch_cache["backend"]
        log("BACKEND_ROUTERS", "📦 Using cached architecture (backend.md)")
    else:
        # Fallback to disk read
        arch_backend_path = project_path / "architecture" / "backend.md"
        if arch_backend_path.exists():
            architecture_backend = arch_backend_path.read_text(encoding="utf-8")
            log("BACKEND_ROUTERS", "⚠️ Cache miss - read backend.md from disk")
        else:
            architecture_backend = "Standard CRUD"
            log("BACKEND_ROUTERS", "⚠️ No architecture/backend.md found - using fallback CRUD")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CLEANUP: Remove generic templates to avoid "just copied" confusion
    # ═══════════════════════════════════════════════════════════════════════════
    routers_dir = project_path / "backend" / "app" / "routers"
    if routers_dir.exists():
        for template in ["items.py", "example.py", "tasks.py", "todos.py"]:
            tmpl_path = routers_dir / template
            if tmpl_path.exists():
                try:
                    tmpl_path.unlink()
                    log("BACKEND_ROUTERS", f"🧹 Removed template router: {template}")
                except Exception:
                    pass
    
    # ═════════════════════════════════════════════════════════════════
    # PHASE-1: AUTH BOUNDARY LOCK
    # Filter out system entities (User) - they should NOT have CRUD routers
    # ═════════════════════════════════════════════════════════════════
    from app.core.auth_boundary import should_skip_entity_for_router, get_auth_guidance
    
    # Filter entities before generation
    domain_entities = []
    skipped_entities = []
    
    for entity in aggregate_entities:
        if should_skip_entity_for_router(entity.name):
            log("BACKEND_ROUTERS", f"🔒 Skipping {entity.name} - system entity (use /auth endpoints)")
            skipped_entities.append(entity.name)
        else:
            domain_entities.append(entity)
    
    if skipped_entities:
        log("BACKEND_ROUTERS", f"📊 Phase-1 Auth Boundary: Filtered out {skipped_entities}")
    
    # log("BACKEND_ROUTERS", f"📋 Generating {len(domain_entities)} routers: {[e.name for e in domain_entities]}")
    
    routers_generated = []
    
    # Extract retry/override context
    temperature_override = branch.intent.get("temperature_override")
    is_retry = branch.intent.get("is_retry", False)

    for entity in domain_entities:
        # log("BACKEND_ROUTERS", f"🔧 Generating router for {entity.name}...")
        
        await broadcast_agent_log(
            manager,
            project_id,
            "AGENT:Derek",
            f"Generating {entity.name} router..."
        )
        
        entity_instruction = _build_single_router_prompt(entity, architecture_backend)
        
        try:
            result = await supervised_agent_call(
                project_id=project_id,
                manager=manager,
                agent_name="Derek",
                step_name="Backend Routers",
                base_instructions=entity_instruction,
                project_path=project_path,
                user_request=user_request,
                contracts=architecture_backend,
                temperature_override=temperature_override,
                is_retry=is_retry,
            )

            if not result.get("approved"):
                log("BACKEND_ROUTERS", f"❌ Rejection for {entity.name}")
                raise RuntimeError(f"Backend router for {entity.name} rejected by supervisor: {result.get('error', 'Low quality output')}")
            
            if result.get("token_usage"):
                usage = result.get("token_usage")
                step_token_usage["input"] += usage.get("input", 0)
                step_token_usage["output"] += usage.get("output", 0)
            
            parsed = result.get("output", {})
            
            if "files" in parsed and parsed["files"]:
                # Sanitize router files and auto-correct paths
                for file_obj in parsed["files"]:
                    path_str = str(file_obj.get("path", ""))
                    normalized_path = path_str.replace("\\", "/")
                    
                    # Auto-correct: tasks.py or routers/tasks.py -> backend/app/routers/tasks.py
                    if not normalized_path.startswith("backend/"):
                        # If it just says "tasks.py" or "routers/tasks.py"
                        filename = normalized_path.split("/")[-1]
                        new_path = f"backend/app/routers/{filename}"
                        file_obj["path"] = new_path
                        log("BACKEND_ROUTERS", f"⚠️ Auto-corrected path from {path_str} to {new_path}")
                    
                    content = file_obj.get("content", "")
                    if "routers" in file_obj["path"]:
                        content = re.sub(r'prefix\s*=\s*[\'"][^\'"]+[\'\"]\s*,?', '', content)
                        content = re.sub(r'tags\s*=\s*\[[^\]]+\]\s*,?', '', content)
                        file_obj["content"] = content
                
                validated = validate_file_output(parsed, WorkflowStep.BACKEND_ROUTERS, max_files=5)
                files_written = await persist_agent_output(manager, project_id, project_path, validated, WorkflowStep.BACKEND_ROUTERS)
                
                log("BACKEND_ROUTERS", f"✅ Generated {entity.plural}.py router ({files_written} files)")
                routers_generated.append(entity.plural)
        
        except Exception as e:
            log("BACKEND_ROUTERS", f"❌ Failed to generate router for {entity.name}: {e}")
            # Non-fatal: add to missed list but continue for other entities
            if entity.plural not in routers_generated:
                log("BACKEND_ROUTERS", f"⚠️ Skipping {entity.name} implementation due to error.")
    
    # ATOMIC CHECK
    expected_routers = set(e.plural for e in domain_entities)  # ✅ Use domain_entities (after auth filtering)
    generated_routers = set(routers_generated)
    missing_routers = expected_routers - generated_routers
    
    if missing_routers:
        log("BACKEND_ROUTERS", f"⚠️ MISSING SIGNAL: Routers for {list(missing_routers)} were not generated.")
        # Proceed anyway - Imperfect behavior > no behavior
    
    return StepResult(
        nextstep=WorkflowStep.SYSTEM_INTEGRATION,
        turn=5,  # Routers is step 4
        data={
            "routers_count": len(routers_generated),
            "routers": routers_generated,
        },
        token_usage=step_token_usage,
    )

def _build_single_router_prompt(entity, architecture_backend: str) -> str:
    """Build prompt for generating a single entity's router."""
    from app.orchestration.utils import pluralize
    from app.core.auth_boundary import get_auth_guidance
    
    entity_name = entity.name
    entity_plural = entity.plural
    # Provide full architecture context if small enough to prevent missing relationship context
    if len(architecture_backend) < 8000:
        entity_contract = architecture_backend
    else:
        entity_contract = _extract_entity_contract(architecture_backend, entity_plural)
    
    # Get auth guidance to prevent violations
    auth_guidance = get_auth_guidance()
    
    return f"""
YOU ARE DEREK.
YOU ARE EXECUTING STEP: BACKEND_ROUTERS.
YOU ARE A BACKEND API IMPLEMENTER.

THIS STEP PRODUCES EXECUTABLE FASTAPI ROUTER CODE.
THIS STEP DOES NOT DO ANALYSIS.
THIS STEP DOES NOT DESIGN FEATURES.
THIS STEP DOES NOT INFER DOMAIN BEHAVIOR.

═══════════════════════════════════════════════════════
🔒 STEP IDENTITY — ABSOLUTE LAW
═══════════════════════════════════════════════════════

STEP NAME: BACKEND_ROUTERS

YOU MUST:
- Generate EXACTLY ONE FastAPI router
- Generate code for EXACTLY ONE entity
- Write EXACTLY ONE file

YOU MUST NOT:
- Generate models
- Generate tests
- Generate frontend code
- Generate multiple routers
- Reference other entities
- Modify any existing files
- Reference other pipeline steps

═══════════════════════════════════════════════════════
📌 SOURCE OF TRUTH (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════

ALL API BEHAVIOR MUST BE DERIVED **ONLY** FROM:

 architecture/backend.md.

IF architecture/backend.md lists specific endpoints (e.g., POST /{id}/convert):
→ YOU MUST implement them exactly as described.
→ If the architecture DOES NOT list a standard endpoint (e.g. DELETE), DO NOT IMPLEMENT IT.

IF architecture/backend.md DOES NOT list specific endpoints:
→ Implement minimal standard CRUD as fallback:
  1. GET     "/"        → List all {entity_plural}
  2. GET     "/{id}"    → Get one {entity_name} by ID
  3. POST    "/"        → Create {entity_name}
  4. PUT     "/{id}"    → Update {entity_name}
  5. DELETE  "/{id}"    → Delete {entity_name}

═══════════════════════════════════════════════════════
🏗️ ENTITY CONTRACT (STRICT AUTHORITY)
═══════════════════════════════════════════════════════

{entity_contract}

═══════════════════════════════════════════════════════
🏗️ ENTITY CONTEXT (READ-ONLY)
═══════════════════════════════════════════════════════

ENTITY NAME: {entity_name}
ENTITY PLURAL: {entity_plural}
BASE PATH (INTEGRATION WILL PREFIX): /{entity_plural}

THIS IS AN ENTITY-SCOPED STEP.
DEREK IS CALLED ONCE PER ENTITY.
DO NOT GENERATE MULTIPLE ROUTERS.

═══════════════════════════════════════════════════════
🔒 ENTITY-SCOPED ISOLATION (CRITICAL)
═══════════════════════════════════════════════════════

ALLOWED:
- backend/app/routers/{entity_plural}.py
- Import from app.models ONLY

FORBIDDEN:
- backend/app/models.py
- backend/app/routers for other entities
- main.py, app.py, config.py
- Any file outside backend/app/routers/
- Importing other entity routers

VIOLATION = INVALID OUTPUT.

═══════════════════════════════════════════════════════
🗑️ DELETE ENDPOINT — CRITICAL RULE
═══════════════════════════════════════════════════════

DELETE MUST:
- Return HTTP 204
- Have NO return statement (or return None)

CORRECT:
@router.delete("/{{id}}", status_code=204)
async def delete_item(id: PydanticObjectId):
    obj = await {entity_name}.get(id)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    await obj.delete()
    # NO RETURN

═══════════════════════════════════════════════════════
⚙️ IMPLEMENTATION RULES (STRICT)
═══════════════════════════════════════════════════════

IMPORTS (MANDATORY):
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Body
from beanie import PydanticObjectId
# Import ALL schemas for this entity from models.py
# (e.g. Lead, LeadCreate, LeadUpdate, LeadResponse, plus any others found)
from app.models import {entity_name}, {entity_name}Create, {entity_name}Update, {entity_name}Response
# ❌ NEVER import Enum classes (e.g. StatusEnum). They DO NOT exist. Use Literal/str in your code.

ROUTER:
- router = APIRouter()
- ❌ NO prefix
- ❌ NO tags

DATABASE:
- Use Beanie ASYNC APIs ONLY
- list: await {entity_name}.find_all().to_list()
- get:  await {entity_name}.get(id)

ID HANDLING:
- ALL ID params use PydanticObjectId
- If entity not found → HTTP 404

REQUEST / RESPONSE:
- POST uses {entity_name}Create (or custom schema if architecture says so)
- PUT uses {entity_name}Update
- Use response_model everywhere applicable

ERROR HANDLING:
- 404 for missing entity
- 400 for invalid input (e.g. Lead already converted)
- NO silent failures
- NO try/except swallowing errors

═══════════════════════════════════════════════════════
🔐 AUTHORIZATION & OWNERSHIP (CONDITIONAL)
═══════════════════════════════════════════════════════

ONLY IF architecture/backend.md explicitly defines ownership
(e.g., a `user_id` field):

- POST:
  - Set obj.user_id = request.state.user_id
  - DO NOT accept user_id from request body

- LIST:
  - Filter with .find(user_id=request.state.user_id)

- GET / PUT / DELETE:
  - Verify obj.user_id == request.state.user_id
  - Else → HTTP 403

IF OWNERSHIP IS NOT DEFINED:
→ DO NOT ADD AUTH CHECKS.

ASSUME request.state.user_id EXISTS (middleware handles it).

ASSUME request.state.user_id EXISTS (middleware handles it).

═══════════════════════════════════════════════════════
📄 OUTPUT FORMAT — HDAP ONLY
═══════════════════════════════════════════════════════

YOU MUST OUTPUT EXACTLY ONE FILE:

<<<FILE path="backend/app/routers/{entity_plural}.py">>>
<COMPLETE PYTHON CODE>
<<<END_FILE>>>

RULES:
- NO markdown
- NO explanations
- NO JSON
- NO partial files
- NO missing <<<END_FILE>>>

═══════════════════════════════════════════════════════
🚨 FAILURE CONDITIONS
═══════════════════════════════════════════════════════

THIS STEP FAILS IF:
- Any forbidden file is generated
- More than one file is generated
- Required endpoints are missing
- Code is syntactically invalid

THIS STEP SUCCEEDS IF:
- Exactly one valid router is generated
- All required endpoints exist
- Entity scope is respected

EXECUTE BACKEND_ROUTERS NOW.

"""


def _extract_entity_contract(contracts: str, entity_plural: str) -> str:
    """
    Extract the entity-specific section from architecture.md.
    
    Finds headings like "### Expenses" or "## Expenses" and extracts
    everything until the next heading of same/higher level.
    """
    import re
    
    if not contracts:
        return f"No contract found. Implement standard CRUD for {entity_plural}."
    
    # Normalize entity name for matching (handle "Expense" vs "Expenses")
    entity_singular = entity_plural.rstrip('s')  # Simple singularization
    
    # Try to find section with entity name (case-insensitive)
    pattern = rf"(?:^|\n)(#{1,3})\s+({entity_plural}|{entity_singular})\b"
    match = re.search(pattern, contracts, re.IGNORECASE | re.MULTILINE)
    
    if not match:
        return f"Full contracts (entity section not found):\n\n{contracts[:1500]}"
    
    # Extract heading level and start position
    heading_level = len(match.group(1))  # Number of # chars
    start_pos = match.start()
    
    # Find next heading of same or higher level
    next_heading_pattern = rf"\n#{{{1,{heading_level}}}}\s+"
    next_match = re.search(next_heading_pattern, contracts[start_pos + 1:], re.MULTILINE)
    
    if next_match:
        end_pos = start_pos + 1 + next_match.start()
        entity_section = contracts[start_pos:end_pos]
    else:
        entity_section = contracts[start_pos:]
    
    if len(entity_section) > 3000:
        entity_section = entity_section[:3000] + "\n\n[... contract continues ...]"
    
    return entity_section.strip()
