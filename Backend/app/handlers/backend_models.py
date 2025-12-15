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
from app.llm import call_llm_with_usage
from app.llm.prompts import DEREK_PROMPT


async def step_backend_models(
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
    Step: Backend Models - Generate all models at once.
    
    Two-phase approach:
    1. Derek generates JSON model specifications
    2. System merges into single models.py
    
    Args:
        project_id: Project identifier
        user_request: Original user request
        manager: WebSocket connection manager
        project_path: Path to project directory
        chat_history: Conversation history
        provider: LLM provider name
        model: LLM model name
        current_turn: Current workflow turn
        max_turns: Maximum turns allowed
    
    Returns:
        StepResult with next step = BACKEND_IMPLEMENTATION (routers)
    """
    await broadcast_status(
        manager,
        project_id,
        WorkflowStep.BACKEND_IMPLEMENTATION,
        f"Turn {current_turn}/{max_turns}: Derek generating data models...",
        current_turn,
        max_turns,
    )
    
    # V3: Track token usage
    step_token_usage = None
    
    # Load entity plan
    try:
        entity_plan = EntityPlan.load(project_path / "entity_plan.json")
        entities = entity_plan.entities
        relationships = entity_plan.relationships
    except FileNotFoundError:
        log("BACKEND_MODELS", "⚠️ No entity_plan.json found, using fallback")
        # Fallback to primary entity
        from app.utils.entity_discovery import discover_all_entities
        entities = discover_all_entities(project_path, user_request)
        relationships = []
    
    if not entities:
        log("BACKEND_MODELS", "❌ No entities found, cannot generate models")
        return StepResult(
            nextstep=WorkflowStep.BACKEND_IMPLEMENTATION,
            turn=current_turn + 1,
            status="error",
            error="No entities found for model generation",
        )
    
    log("BACKEND_MODELS", f"📋 Generating models for {len(entities)} entities")
    
    # Load contracts if available
    contracts_data = {}
    contracts_path = project_path / "contracts.md"
    if contracts_path.exists():
        try:
            contracts_content = contracts_path.read_text(encoding="utf-8")
            contracts_data = {"content": contracts_content[:5000]}  # Limit size
        except Exception as e:
            log("BACKEND_MODELS", f"Could not read contracts: {e}")
    
    # Phase A: Derek generates model specs as JSON
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
        provider=provider,
        model=model,
    )
    
    # Extract token usage
    step_token_usage = model_spec_result.get("token_usage")
    model_spec = model_spec_result.get("spec", {})
    
    # Phase B: System merges specs into Python code
    try:
        models_code = merge_model_specs_to_python(
            model_spec=model_spec,
            entities=entities,
            relationships=relationships
        )
        
        # Write models.py
        models_path = project_path / "backend" / "app" / "models.py"
        models_path.parent.mkdir(parents=True, exist_ok=True)
        models_path.write_text(models_code, encoding="utf-8")
        
        log("BACKEND_MODELS", f"✅ Generated models.py with {len(model_spec.get('models', []))} models")
        
        await broadcast_agent_log(
            manager,
            project_id,
            "AGENT:Derek",
            f"Generated {len(model_spec.get('models', []))} data models in models.py"
        )
        
    except Exception as e:
        log("BACKEND_MODELS", f"❌ Model generation failed: {e}")
        return StepResult(
            nextstep=WorkflowStep.BACKEND_IMPLEMENTATION,
            turn=current_turn + 1,
            status="error",
            error=f"Model generation failed: {str(e)}",
            token_usage=step_token_usage,
        )
    
    return StepResult(
        nextstep=WorkflowStep.BACKEND_IMPLEMENTATION,
        turn=current_turn + 1,
        data={
            "models_count": len(model_spec.get('models', [])),
            "entities": [e.name for e in entities],
        },
        token_usage=step_token_usage,
    )


async def derek_generate_model_spec(
    entities: List[EntitySpec],
    relationships: List[Any],
    contracts: Dict[str, Any],
    provider: str,
    model: str,
) -> Dict[str, Any]:
    """
    Derek generates model specifications as JSON (not Python code).
    
    Args:
        entities: List of entities to model
        relationships: Relationships between entities
        contracts: API contracts data
        provider: LLM provider
        model: LLM model
    
    Returns:
        Dict with "spec" (JSON model spec) and "token_usage"
    """
    from app.core.constants import MULTI_ENTITY_BUDGETS
    
    # Serialize entities and relationships
    entities_json = json.dumps([e.to_dict() for e in entities], indent=2)
    relationships_json = json.dumps([r.to_dict() for r in relationships], indent=2)
    contracts_content = contracts.get("content", "")
    
    prompt = f"""You are Derek, an expert backend developer specializing in data modeling.

═══════════════════════════════════════════════════════
ENTITIES TO MODEL
═══════════════════════════════════════════════════════

{entities_json}

═══════════════════════════════════════════════════════
RELATIONSHIPS
═══════════════════════════════════════════════════════

{relationships_json}

═══════════════════════════════════════════════════════
API CONTRACTS (Reference)
═══════════════════════════════════════════════════════

{contracts_content[:2000] if contracts_content else "No contracts available"}

═══════════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════════

Generate Pydantic/SQLModel model specifications as JSON.

For EACH entity, define:
1. **Fields**: All data fields with types (str, int, bool, Optional[str], datetime, etc.)
2. **Required fields**: Which fields are mandatory
3. **Foreign keys**: For relationships (e.g., user_id for User → Note)
4. **Descriptions**: Brief field descriptions

IMPORTANT RULES:
- Use ONLY fields that make sense for each entity
- Add standard fields: id (int), created_at (datetime), updated_at (datetime)
- For relationships, add foreign key fields (e.g., user_id: int for notes)
- Use proper Python types: str, int, bool, float, datetime, Optional[str]
- Do NOT hallucinate fields - be minimal and realistic

═══════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════

Return ONLY valid JSON (no markdown, no code blocks):

{{
  "thinking": "Brief analysis of the data model...",
  "models": [
    {{
      "name": "User",
      "table_name": "users",
      "description": "System user with authentication",
      "fields": [
        {{"name": "id", "type": "int", "required": true, "description": "Unique identifier", "primary_key": true}},
        {{"name": "email", "type": "str", "required": true, "description": "User email"}},
        {{"name": "username", "type": "str", "required": true, "description": "Username"}},
        {{"name": "password_hash", "type": "str", "required": true, "description": "Hashed password"}},
        {{"name": "created_at", "type": "datetime", "required": true, "description": "Creation timestamp"}},
        {{"name": "updated_at", "type": "datetime", "required": true, "description": "Last update timestamp"}}
      ]
    }},
    {{
      "name": "Note",
      "table_name": "notes",
      "description": "User's notes",
      "fields": [
        {{"name": "id", "type": "int", "required": true, "description": "Unique identifier", "primary_key": true}},
        {{"name": "title", "type": "str", "required": true, "description": "Note title"}},
        {{"name": "content", "type": "str", "required": true, "description": "Note content"}},
        {{"name": "user_id", "type": "int", "required": true, "description": "Foreign key to User", "foreign_key": "users.id"}},
        {{"name": "created_at", "type": "datetime", "required": true, "description": "Creation timestamp"}},
        {{"name": "updated_at", "type": "datetime", "required": true, "description": "Last update timestamp"}}
      ]
    }}
  ]
}}

CRITICAL: Return ONLY the JSON object. No markdown, no explanations, no code fences.
"""
    
    try:
        max_tokens = MULTI_ENTITY_BUDGETS.get("backend_models", 10000)
        
        llm_result = await call_llm_with_usage(
            prompt=prompt,
            system_prompt=DEREK_PROMPT,
            provider=provider,
            model=model,
            temperature=0.2,
            max_tokens=max_tokens,
        )
        
        raw = llm_result.get("text", "")
        token_usage = llm_result.get("usage", {"input": 0, "output": 0})
        
        log("TOKENS", f"📊 Backend models usage: {token_usage.get('input', 0):,} in / {token_usage.get('output', 0):,} out")
        
        # Clean markdown if present
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        
        spec = json.loads(raw.strip())
        
        return {
            "spec": spec,
            "token_usage": token_usage
        }
        
    except json.JSONDecodeError as e:
        log("BACKEND_MODELS", f"❌ Failed to parse Derek response: {e}")
        log("BACKEND_MODELS", f"   Raw response: {raw[:500]}")
        
        # Fallback to minimal spec
        fallback_spec = {
            "thinking": "Failed to parse Derek response; using fallback",
            "models": [
                {
                    "name": entity.name,
                    "table_name": entity.plural,
                    "description": f"{entity.name} model",
                    "fields": [
                        {"name": "id", "type": "int", "required": True, "description": "Unique identifier", "primary_key": True},
                        {"name": "name", "type": "str", "required": True, "description": f"{entity.name} name"},
                        {"name": "created_at", "type": "datetime", "required": True, "description": "Creation timestamp"},
                    ]
                }
                for entity in entities
            ]
        }
        
        return {
            "spec": fallback_spec,
            "token_usage": token_usage if 'token_usage' in locals() else {"input": 0, "output": 0}
        }
    except Exception as e:
        log("BACKEND_MODELS", f"❌ Derek model spec generation failed: {e}")
        raise


def merge_model_specs_to_python(
    model_spec: Dict[str, Any],
    entities: List[EntitySpec],
    relationships: List[Any]
) -> str:
    """
    Convert JSON model spec to Python SQLModel/Pydantic code.
    
    Args:
        model_spec: JSON specification from Derek
        entities: Original entity specs
        relationships: Relationship specs
    
    Returns:
        Complete models.py Python code
    """
    
    # Build imports
    imports = """# backend/app/models.py
\"\"\"
Data Models - Auto-generated by GenCode Studio
\"\"\"
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from beanie import Document

"""
    
    models_code = []
    
    # Build entity type lookup map
    entity_type_map = {e.name: e.type for e in entities}
    
    for model_def in model_spec.get("models", []):
        name = model_def["name"]
        
        # FIX #5: Determine if this entity is AGGREGATE or EMBEDDED
        entity_type = entity_type_map.get(name, "AGGREGATE")  # Default to AGGREGATE
        is_aggregate = (entity_type == "AGGREGATE")
        table_name = model_def.get("table_name", name.lower() + "s")
        description = model_def.get("description", f"{name} model")
        fields_list = model_def.get("fields", [])
        
        # Build field definitions for Document class
        doc_fields = []
        create_fields = []
        response_fields = []
        
        for field in fields_list:
            field_name = field["name"]
            field_type = field["type"]
            required = field.get("required", True)
            desc = field.get("description", "")
            is_primary = field.get("primary_key", False)
            
            # Convert type names
            type_map = {
                "datetime": "datetime",
                "str": "str",
                "int": "int",
                "bool": "bool",
                "float": "float",
            }
            python_type = type_map.get(field_type, field_type)
            
            # Document field (for database)
            if is_primary and field_name == "id":
                # Beanie uses PydanticObjectId for _id, skip manual id field
                continue
            elif field_name in ["created_at", "updated_at"]:
                doc_fields.append(f'    {field_name}: datetime = Field(default_factory=datetime.utcnow, description="{desc}")')
            elif not required:
                doc_fields.append(f'    {field_name}: Optional[{python_type}] = Field(None, description="{desc}")')
            else:
                doc_fields.append(f'    {field_name}: {python_type} = Field(..., description="{desc}")')
            
            # Create schema (exclude id, created_at, updated_at)
            if field_name not in ["id", "created_at", "updated_at"]:
                if not required:
                    create_fields.append(f'    {field_name}: Optional[{python_type}] = None')
                else:
                    create_fields.append(f'    {field_name}: {python_type}')
            
            # Response schema (include all fields)
            if not required:
                response_fields.append(f'    {field_name}: Optional[{python_type}] = None')
            else:
                response_fields.append(f'    {field_name}: {python_type}')
        
        doc_fields_str = "\n".join(doc_fields)
        create_fields_str = "\n".join(create_fields)
        response_fields_str = "\n".join(response_fields)
        
        # Generate model code based on entity type
        if is_aggregate:
            # AGGREGATE: Document class (Beanie collection with Settings)
            model_code = f'''
class {name}(Document):
    """{description} (AGGREGATE - Beanie Document)"""
{doc_fields_str}
    
    class Settings:
        name = "{table_name}"

'''
        else:
            # EMBEDDED: BaseModel (nested object, no Settings)
            model_code = f'''
class {name}(BaseModel):
    """{description} (EMBEDDED - Pydantic BaseModel)"""
{doc_fields_str}

'''
        
        # Always add Create and Response schemas
        model_code += f'''
class {name}Create(BaseModel):
    """Create {name} request"""
{create_fields_str}


class {name}Response(BaseModel):
    """Response for {name}"""
    id: str  # Beanie uses string IDs
{response_fields_str}
    
    class Config:
        from_attributes = True
'''
        
        models_code.append(model_code)
    
    full_code = imports + "\n".join(models_code)
    return full_code
