# app/handlers/backend_models.py
"""
Backend Models Handler (Phase 3)

Two-phase model generation:
1. Derek generates model specifications as JSON (not Python code)
2. System merges JSON specs into single models.py

This prevents overwrites and ensures all models are in one file.
"""
import json
from pathlib import Path
from typing import Any, List, Dict

from app.core.types import ChatMessage, StepResult
from app.core.constants import WorkflowStep
from app.core.logging import log
from app.handlers.base import broadcast_status, broadcast_agent_log
from app.utils.entity_discovery import EntitySpec, EntityPlan
from app.core.failure_boundary import FailureBoundary
from app.core.step_invariants import StepInvariants, StepInvariantError


@FailureBoundary.enforce
async def step_backend_models(branch) -> StepResult:
    """
    Step: Backend Models - Generate all models at once.
    
    Two-phase approach:
    1. Derek generates model specifications
    2. System merges into single models.py
    
    Returns:
        StepResult with next step = BACKEND_IMPLEMENTATION (routers)
    """
    from app.arbormind.cognition.branch import Branch
    assert isinstance(branch, Branch)
    
    # Extract context from branch
    project_id = branch.intent["project_id"]
    user_request = branch.intent["user_request"]
    manager = branch.intent["manager"]
    project_path = branch.intent["project_path"]
    provider = branch.intent["provider"]
    model = branch.intent["model"]
    
    await broadcast_status(
        manager,
        project_id,
        WorkflowStep.BACKEND_MODELS,
        f"Derek generating data models...",
        3,
        9,
    )
    
    # V3: Track token usage
    step_token_usage = None
    
    # Load entity plan
    entity_plan_path = project_path / "entity_plan.json"
    if not entity_plan_path.exists():
        log("BACKEND_MODELS", "📋 No entity_plan.json found - synthesizing from detected entities")
        _synthesize_entity_plan(project_path, branch)
        
    try:
        entity_plan = EntityPlan.load(entity_plan_path)
        entities = entity_plan.entities
        relationships = entity_plan.relationships
    except Exception as e:
        log("BACKEND_MODELS", f"❌ Failed to load/synthesize entity plan: {e}")
        raise RuntimeError(f"Missing entity_plan.json and synthesis failed: {e}")
    
    if not entities:
        log("BACKEND_MODELS", "❌ No entities found, cannot generate models")
        raise RuntimeError("No entities found for model generation")
    
    # Phase-1: ARCHITECTURE IS TRUTH
    # We no longer run domain grounding or injection here. 
    # The entities were already extracted via architecture-first priority.
    entity_names = [e.name for e in entities]
    log("BACKEND_MODELS", f"✅ Using authoritative entities: {entity_names}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INVARIANT: Entity names SHOULD be singular.
    # We auto-singularize common plural names to prevent fatal workflow stops.
    # ═══════════════════════════════════════════════════════════════════════════
    for entity in entities:
        if entity.name.endswith("s") and not entity.name.endswith("ss"):
            old_name = entity.name
            new_name = entity.name[:-1]  # Simple singularization
            entity.name = new_name
            log("BACKEND_MODELS", f"⚠️ Auto-singularized entity name: {old_name} -> {new_name}")
    
    # log("BACKEND_MODELS", f"📋 Generating models for {len(entities)} entities")
    
    # Architecture.md is the canonical declaration of intent
    # Architecture Bundle: Backend context (Source of Truth)
    # V2.1: Use cached architecture from Victoria's output
    from app.orchestration.state import WorkflowStateManager
    arch_cache = await WorkflowStateManager.get_architecture_cache(project_id)
    
    contracts_data = {}
    if "backend" in arch_cache:
        contracts_content = arch_cache["backend"]
        contracts_data = {"content": contracts_content[:15000]}
        log("BACKEND_MODELS", "📦 Using cached architecture (backend.md)")
    else:
        # Fallback to disk read
        arch_backend_path = project_path / "architecture" / "backend.md"
        if arch_backend_path.exists():
            try:
                contracts_content = arch_backend_path.read_text(encoding="utf-8")
                contracts_data = {"content": contracts_content[:15000]} 
                log("BACKEND_MODELS", "⚠️ Cache miss - read backend.md from disk")
            except Exception as e:
                log("BACKEND_MODELS", f"Could not read architecture/backend.md: {e}")

    
    
    # Phase A: Derek generates models via supervised call
    await broadcast_agent_log(
        manager,
        project_id,
        "AGENT:Derek",
        f"Generating data models for {', '.join([e.name for e in entities])}..."
    )
    
    model_spec_result = await derek_generate_model_spec(
        entities=entities,
        relationships=relationships,
        contracts=contracts_data,
        project_id=project_id,
        manager=manager,
        project_path=project_path,
        user_request=user_request,
        branch=branch,
    )
    
    # Extract token usage
    step_token_usage = model_spec_result.get("token_usage")
    model_spec = model_spec_result.get("spec", {})
    
    # Phase B: Write models.py
    try:
        models_code = model_spec_result.get("code", "")
        if not models_code:
            raise RuntimeError("Derek returned empty code for models.py")
        
        # Write models.py
        models_path = project_path / "backend" / "app" / "models.py"
        models_path.parent.mkdir(parents=True, exist_ok=True)
        # Ensure we overwrite ANY template/existing file by unlinking first
        if models_path.exists():
            models_path.unlink()
        models_path.write_text(models_code, encoding="utf-8")
        
        # Extract model metadata via regex (since we no longer have JSON spec)
        import re
        model_matches = re.findall(r"class\s+(\w+)\(Document\):", models_code)
        models_count = len(model_matches)
        model_names = model_matches
        expected_entity_count = len(entities)
        
        log("BACKEND_MODELS", f"✅ Generated models.py with {models_count} models: {model_names}")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # INVARIANT 1: At least ONE model MUST be generated for AGGREGATE entities
        # This prevents routers from being generated without models to import
        # ═══════════════════════════════════════════════════════════════════════════
        if models_count == 0:
            log("BACKEND_MODELS", "❌ INVARIANT VIOLATION: Zero models generated for AGGREGATE entities")
            raise RuntimeError(
                "BACKEND_MODELS invariant violated: "
                "At least one Beanie Document model must be generated for AGGREGATE entities. "
                f"Expected models for: {[e.name for e in entities]}"
            )
        
        # ═══════════════════════════════════════════════════════════════════════════
        # INVARIANT 2: No more models than expected entities (prevents duplicates/leaks)
        # This catches embedded entities accidentally becoming top-level Documents
        # ═══════════════════════════════════════════════════════════════════════════
        if models_count > expected_entity_count:
            log("BACKEND_MODELS", f"⚠️ INVARIANT WARNING: {models_count} models > {expected_entity_count} expected entities")
            log("BACKEND_MODELS", f"   Generated: {model_names}")
            log("BACKEND_MODELS", f"   Expected:  {[e.name for e in entities]}")
            # Note: This is a warning, not a hard failure, as extra utility models may be valid
        
        await broadcast_agent_log(
            manager,
            project_id,
            "AGENT:Derek",
            f"Generated {models_count} data models in models.py"
        )
        
    except Exception as e:
        log("BACKEND_MODELS", f"❌ Model generation failed: {e}")
        raise RuntimeError(f"Model generation failed: {str(e)}")
    
    return StepResult(
        nextstep=WorkflowStep.BACKEND_ROUTERS,
        turn=4,  # Backend models phase
        data={
            "models_count": models_count,
            "model_names": model_names,
            "expected_entities": [e.name for e in entities],
        },
        token_usage=step_token_usage,
    )


async def derek_generate_model_spec(
    entities: List[EntitySpec],
    relationships: List[Any],
    contracts: Dict[str, Any],
    project_id: str,
    manager: Any,
    project_path: Path,
    user_request: str,
    branch: Any,
) -> Dict[str, Any]:
    """
    Derek generates model specifications using supervised agent call.
    
    Now uses ARTIFACT enforcement + auto-recovery for consistency.
    
    Args:
        entities: List of entities to model
        relationships: Relationships between entities
        contracts: API contracts data
        project_id: Project ID for broadcasting
        manager: WebSocket manager
        project_path: Path to project
        user_request: Original user request
    
    Returns:
        Dict with "code" (Python model code) and "token_usage"
    """
    from app.supervision import supervised_agent_call
    
    # Serialize entities and relationships
    entities_json = json.dumps([e.to_dict() for e in entities], indent=2)
    relationships_json = json.dumps([r.to_dict() for r in relationships], indent=2)
    contracts_content = contracts.get("content", "")
    contracts_display = contracts_content[:2000] if contracts_content else "No contracts available"

    # Build Derek's instructions
    derek_instructions = f"""
    You are Derek, acting as a BACKEND DATA MODEL IMPLEMENTER.

This step PRODUCES EXECUTABLE BACKEND CODE.
You are generating Beanie Document models and Pydantic schemas.
You are NOT generating routers, tests, or business logic.

═══════════════════════════════════════════════════════
SOURCE OF TRUTH (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════

ALL models MUST be derived ONLY from:
- architecture/backend.md

DO NOT invent entities.
DO NOT invent fields.
DO NOT infer from frontend.
DO NOT assume contracts.

If something is missing, infer conservatively from the USER REQUEST,
but NEVER output empty or partial models.

═══════════════════════════════════════════════════════
🏗️ ENTITIES TO IMPLEMENT
═══════════════════════════════════════════════════════

{entities_json}

═══════════════════════════════════════════════════════
🔗 RELATIONSHIPS TO MODEL
═══════════════════════════════════════════════════════

{relationships_json}

═══════════════════════════════════════════════════════
AGGREGATE COMPLETENESS (HARD REQUIREMENT)
═══════════════════════════════════════════════════════

You MUST generate models for EVERY entity marked as:

Type: AGGREGATE
or
Type: EMBEDDED

Rules:
1. AGGREGATE entities:
   - Must inherit from Beanie `Document`
   - Must have their own collection
   - Must be top-level classes

2. EMBEDDED entities:
   - Must inherit from Pydantic `BaseModel` (NOT `Document`)
   - Must be used as fields within Aggegates
   - DO NOT give them their own collection
   - MUST generate Create/Update schemas just like Aggregates


If architecture/backend.md defines N aggregate entities:
→ You MUST generate N Beanie Document classes
→ You MUST generate Create / Update / Response schemas for EACH

Generating only a subset of aggregates is a FATAL ERROR.

ALL AGGREGATES ARE EQUAL.
DO NOT prioritize a "primary" entity.

═══════════════════════════════════════════════════════
MANDATORY MODEL RULES (STRICT)
═══════════════════════════════════════════════════════

1. Use Beanie + Pydantic v2
2. Imports MUST include:
   from beanie import Document, PydanticObjectId, Indexed
   from pydantic import BaseModel, Field
   from datetime import datetime
   from typing import Optional, List
   from typing_extensions import Literal

3. EVERY AGGREGATE MUST:
   - Inherit from Document
   - Have its own MongoDB collection
   - Include:
       created_at: datetime = Field(default_factory=datetime.utcnow)
       updated_at: datetime = Field(default_factory=datetime.utcnow)

4. ID TYPE RULE (CRITICAL):
   - ALL internal models MUST use PydanticObjectId for `id`
   - NEVER use `id: str` in backend models
   - Conversion to string happens ONLY at API/router layer

5. Validation MUST match architecture EXACTLY:
   - min_length / max_length → Field(...)
   - enums → Use Literal["A", "B"] directly in the field type.
   - ❌ DO NOT create separate class definitions for Enums (no Enum classes).
   - If architecture mentions an Enum, convert it to Literal in the Pydantic model.
   - optional → Optional[] (e.g. `Optional[List[str]] = None` if architecture says Optional)
   - lists → Field(default_factory=list) (unless architecture says Optional, then default to None)
   - UNIQUE FIELDS → Use `Indexed(str, unique=True)`.
     ❌ DO NOT use `Field(..., unique=True)`
     ❌ DO NOT use `unique_items=True` (this is for lists only)

6. Embedded data:
   - Use plain Pydantic models ONLY if explicitly stated
   - Otherwise reference via ObjectId or primitive (e.g. tag names)

7. FORBIDDEN:
   - Routers
   - Business logic
   - Database init
   - Validators (@validator, @model_validator)

═══════════════════════════════════════════════════════
SCHEMA REQUIREMENTS (MANDATORY)
═══════════════════════════════════════════════════════

For EACH AGGREGATE entity X, you MUST generate:

1. class X(Document)
2. class XCreate(BaseModel)
3. class XUpdate(BaseModel) → ALL fields Optional
4. class XResponse(BaseModel)

Rules:
- Create: no id, no system fields
- Update: Optional fields only
- Response: includes id, created_at, updated_at
- NO class body may be empty
- NEVER use `pass`

═══════════════════════════════════════════════════════
OUTPUT FORMAT (HDAP — STRICT)
═══════════════════════════════════════════════════════

<<<FILE path="backend/app/models.py">>>
# complete models.py content
<<<END_FILE>>>

Only ONE file is allowed.
Missing <<<END_FILE>>> = rejection.

THIS STEP IS FATAL IF ANY AGGREGATE ENTITY IS MISSING.
"""

    try:
        # Extract retry/override context
        temperature_override = branch.intent.get("temperature_override")
        is_retry = branch.intent.get("is_retry", False)

        # Use supervised agent call for ARTIFACT enforcement + auto-recovery
        result = await supervised_agent_call(
            project_id=project_id,
            manager=manager,
            agent_name="Derek",
            step_name="Backend Models",
            base_instructions=derek_instructions,
            project_path=project_path,
            user_request=user_request,
            contracts=contracts_content,
            temperature_override=temperature_override,
            is_retry=is_retry,
        )
        
        if not result.get("approved"):
            raise RuntimeError(f"Backend models rejected by supervisor: {result.get('error', 'Low quality output')}")
        
        # Extract token usage
        token_usage = result.get("token_usage", {"input": 0, "output": 0})
        
        # Extract generated files
        parsed = result.get("output", {})
        files = parsed.get("files", [])
        
        # ═══════════════════════════════════════════════════════════════════════════
        # PHASE-0/1: Orchestrator handles empty file detection and retry
        # Handler just extracts and returns the model file content
        # ═══════════════════════════════════════════════════════════════════════════
        
        # Extract Python code from files
        # Look for backend/app/models.py or similar
        model_file = None
        if files:
            model_file = next((f for f in files if "models.py" in f["path"]), None)
            
            # Fallback: Just take the first valid python file
            if not model_file:
                model_file = next((f for f in files if f["path"].endswith(".py")), None)
        
        # Return model content (or empty if no files - orchestrator will handle)
        return {
            "code": model_file["content"] if model_file else "",
            "token_usage": token_usage
        }
        
    except StepInvariantError as e:
        log("BACKEND_MODELS", f"❌ Step invariant violated: {e}")
        raise RuntimeError(f"Backend models step failed inventory check: {e}")
    except Exception as e:
        log("BACKEND_MODELS", f"❌ Derek model spec generation failed: {e}")
        raise




def _synthesize_entity_plan(project_path: Path, branch) -> None:
    """
    Synthesize entity_plan.json from detected entities when it doesn't exist.
    
    This enables the unified two-step flow for ALL projects, even if
    the contracts step didn't create an entity plan.
    """
    import json
    from app.orchestration.utils import pluralize
    from app.utils.entity_discovery import discover_primary_entity, extract_entity_from_request
    
    entities = []
    
    # Try 1: Discover from architecture/backend.md (Direct Authority)
    from app.utils.entity_discovery import discover_all_entities
    entities_specs = discover_all_entities(project_path)
    
    if entities_specs:
        entities = [e.name for e in entities_specs]
    
    # Fallback only if architecture is missing
    if not entities:
        user_request = branch.intent.get("user_request", "")
        entity_name = extract_entity_from_request(user_request)
        if entity_name:
            entities = [entity_name]
    
    # Absolute Fallback
    if not entities:
        entities = ["Item"]
    
    # Build entity plan structure
    # Use discovered specs if available to correct types
    plan_entities = []
    
    if entities_specs:
        # Use specs directly
        for i, spec in enumerate(entities_specs):
            plan_entities.append({
                "name": spec.name.capitalize(),
                "plural": spec.plural,
                "type": spec.type, # Use captured type (AGGREGATE/EMBEDDED)
                "generation_order": i + 1
            })
    else:
        # Fallback for manual/user_request entity names
        for i, e in enumerate(entities):
            plan_entities.append({
                "name": e.capitalize(),
                "plural": pluralize(e),
                "type": "AGGREGATE",
                "generation_order": i + 1
            })

    entity_plan = {
        "entities": plan_entities,
        "relationships": []
    }
    
    # Write to disk
    entity_plan_path = project_path / "entity_plan.json"
    entity_plan_path.write_text(json.dumps(entity_plan, indent=2), encoding="utf-8")
    log("BACKEND_MODELS", f"✅ Synthesized entity_plan.json with {len(entities)} entity(ies)")
