# app/handlers/entity_planning.py
"""
Entity Planning Handler (Phase 2)

Marcus analyzes discovered entities and plans:
1. Relationships between entities
2. Generation order (dependencies first)
3. Validation of entity model

Output: entity_plan.json for downstream steps
"""
import json
from pathlib import Path
from typing import Any, List, Dict

from app.core.types import ChatMessage, StepResult
from app.core.constants import WorkflowStep
from app.core.logging import log
from app.handlers.base import broadcast_status, broadcast_agent_log
from app.utils.entity_specs import EntitySpec, Relationship, EntityPlan
from app.utils.entity_discovery import detect_relationships
from app.llm import call_llm_with_usage
from app.llm.prompts import MARCUS_PROMPT


async def step_entity_planning(
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
    Step: Entity Planning - Marcus plans relationships and generation order.
    
    This step happens after entity discovery and before architecture.
    
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
        StepResult with next step = ARCHITECTURE
    """
    await broadcast_status(
        manager,
        project_id,
        WorkflowStep.ARCHITECTURE,  # Still using architecture for now
        f"Turn {current_turn}/{max_turns}: Marcus planning entity relationships...",
        current_turn,
        max_turns,
    )
    
    # V3: Track token usage
    step_token_usage = None
    
    # Load discovered entities from state
    entities = await _load_discovered_entities(project_id, project_path)
    
    if not entities:
        log("ENTITY_PLANNING", "⚠️ No entities found, skipping entity planning")
        return StepResult(
            nextstep=WorkflowStep.ARCHITECTURE,
            turn=current_turn + 1,
            token_usage=step_token_usage,
        )
    
    log("ENTITY_PLANNING", f"📋 Planning for {len(entities)} entities: {[e.name for e in entities]}")
    
    # Detect basic relationships from contracts
    relationships = detect_relationships(project_path, entities)
    
    # Ask Marcus to validate and enhance relationships
    await broadcast_agent_log(
        manager,
        project_id,
        "AGENT:Marcus",
        f"Analyzing relationships between {len(entities)} entities..."
    )
    
    entity_plan = await marcus_plan_relationships(
        entities=entities,
        relationships=relationships,
        user_request=user_request,
        provider=provider,
        model=model,
    )
    
    # Extract token usage
    step_token_usage = entity_plan.get("token_usage")
    
    # Parse the plan
    try:
        plan_data = entity_plan.get("plan", {})
        
        # Create EntityPlan object
        planned_entities = [
            EntitySpec.from_dict(e) for e in plan_data.get("entities", [])
        ]
        planned_relationships = [
            Relationship(**r) for r in plan_data.get("relationships", [])
        ]
        warnings = plan_data.get("warnings", [])
        
        plan = EntityPlan(
            entities=planned_entities,
            relationships=planned_relationships,
            warnings=warnings
        )
        
        # Save entity plan to disk
        plan_path = project_path / "entity_plan.json"
        plan.save(plan_path)
        
        log("ENTITY_PLANNING", f"✅ Saved entity plan: {len(planned_entities)} entities, {len(planned_relationships)} relationships")
        
        # Broadcast thinking
        thinking = plan_data.get("thinking", "")
        if thinking:
            await broadcast_agent_log(
                manager,
                project_id,
                "AGENT:Marcus",
                "Marcus is analyzing entity relationships...",
                data={"thinking": thinking}
            )
        
        # Broadcast warnings
        if warnings:
            for warning in warnings:
                await broadcast_agent_log(
                    manager,
                    project_id,
                    "AGENT:Marcus",
                    f"⚠️ {warning}"
                )
        
        # Summary message
        summary_parts = [
            f"Planned {len(planned_entities)} entities",
            f"{len(planned_relationships)} relationships detected"
        ]
        if warnings:
            summary_parts.append(f"{len(warnings)} warnings")
        
        await broadcast_agent_log(
            manager,
            project_id,
            "AGENT:Marcus",
            ". ".join(summary_parts) + ". Proceeding to architecture design."
        )
        
    except Exception as e:
        log("ENTITY_PLANNING", f"❌ Failed to parse entity plan: {e}")
        # Fall back to basic plan
        plan = EntityPlan(
            entities=entities,
            relationships=relationships,
            warnings=[f"Failed to parse Marcus plan: {str(e)}"]
        )
        plan_path = project_path / "entity_plan.json"
        plan.save(plan_path)
    
    return StepResult(
        nextstep=WorkflowStep.ARCHITECTURE,
        turn=current_turn + 1,
        data={
            "entities_count": len(plan.entities),
            "relationships_count": len(plan.relationships),
        },
        token_usage=step_token_usage,
    )


async def marcus_plan_relationships(
    entities: List[EntitySpec],
    relationships: List[Relationship],
    user_request: str,
    provider: str,
    model: str,
) -> Dict[str, Any]:
    """
    Call Marcus (LLM) to plan entity relationships and generation order.
    
    Args:
        entities: Discovered entities
        relationships: Pre-detected relationships
        user_request: Original user request
        provider: LLM provider
        model: LLM model
    
    Returns:
        Dict with "plan" and "token_usage"
    """
    from app.core.constants import ENTITY_GENERATION_PRIORITY
    
    # Serialize entities and relationships
    entities_json = json.dumps([e.to_dict() for e in entities], indent=2)
    relationships_json = json.dumps([r.to_dict() for r in relationships], indent=2)
    
    prompt = f"""You are Marcus, an expert in database design and API architecture.

User Request: "{user_request}"

Discovered Entities:
{entities_json}

Pre-Detected Relationships:
{relationships_json}

═══════════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════════

Plan the complete entity relationship model:

1. **Confirm Entities**: Review all discovered entities. Add any missing entities that are implied by the user request.

2. **Define Relationships**: Specify how entities relate to each other:
   - one_to_many: Parent has multiple children (e.g., User → Notes)
   - many_to_many: Both sides can have multiple (e.g., Posts ↔ Tags)
   - one_to_one: One-to-one relationship (rare, e.g., User → Profile)

3. **Foreign Keys**: Specify the foreign key column name (e.g., "user_id")

4. **Generation Order**: Order entities by dependency (1 = first):
   - Auth entities (User, Organization) should be generated first
   - Dependent entities (Notes, Tasks) come after their parents
   - Use this priority guide: {json.dumps(ENTITY_GENERATION_PRIORITY)}

5. **Warnings**: Flag any potential issues (circular dependencies, missing entities, etc.)

═══════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════

Return ONLY valid JSON (no markdown, no explanation):

{{
  "thinking": "Brief analysis of the entity model and relationships...",
  "entities": [
    {{
      "name": "User",
      "plural": "users",
      "description": "System user with authentication",
      "is_primary": true,
      "generation_order": 1,
      "fields": []
    }},
    {{
      "name": "Note",
      "plural": "notes",
      "description": "User's notes",
      "is_primary": false,
      "generation_order": 2,
      "fields": []
    }}
  ],
  "relationships": [
    {{
      "from_entity": "User",
      "to_entity": "Note",
      "type": "one_to_many",
      "foreign_key": "user_id",
      "cascade_delete": true,
      "description": "A user can have many notes"
    }}
  ],
  "warnings": []
}}

IMPORTANT: Return ONLY the JSON object, nothing else.
"""
    
    try:
        # Use Marcus prompt as system prompt
        from app.core.constants import MULTI_ENTITY_BUDGETS
        max_tokens = MULTI_ENTITY_BUDGETS.get("entity_planning", 6000)
        
        llm_result = await call_llm_with_usage(
            prompt=prompt,
            system_prompt=MARCUS_PROMPT,
            provider=provider,
            model=model,
            temperature=0.3,
            max_tokens=max_tokens,
        )
        
        raw = llm_result.get("text", "")
        token_usage = llm_result.get("usage", {"input": 0, "output": 0})
        
        log("TOKENS", f"📊 Entity planning usage: {token_usage.get('input', 0):,} in / {token_usage.get('output', 0):,} out")
        
        # Parse JSON response
        # Clean markdown if present
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        
        plan = json.loads(raw.strip())
        
        return {
            "plan": plan,
            "token_usage": token_usage
        }
        
    except json.JSONDecodeError as e:
        log("ENTITY_PLANNING", f"❌ Failed to parse Marcus response: {e}")
        log("ENTITY_PLANNING", f"   Raw response: {raw[:500]}")
        
        # Fallback to basic plan
        return {
            "plan": {
                "thinking": "Failed to parse Marcus plan; using fallback",
                "entities": [e.to_dict() for e in entities],
                "relationships": [r.to_dict() for r in relationships],
                "warnings": [f"LLM response parsing failed: {str(e)[:200]}"]
            },
            "token_usage": token_usage if 'token_usage' in locals() else {"input": 0, "output": 0}
        }
    except Exception as e:
        log("ENTITY_PLANNING", f"❌ Marcus planning failed: {e}")
        
        return {
            "plan": {
                "thinking": f"Error: {str(e)}",
                "entities": [e.to_dict() for e in entities],
                "relationships": [r.to_dict() for r in relationships],
                "warnings": [f"Planning failed: {str(e)[:200]}"]
            },
            "token_usage": {"input": 0, "output": 0}
        }


async def _load_discovered_entities(project_id: str, project_path: Path) -> List[EntitySpec]:
    """
    Load discovered entities from workflow state or discovery.
    
    Returns:
        List of EntitySpec objects
    """
    from app.orchestration.state import WorkflowStateManager
    from app.utils.entity_discovery import discover_all_entities
    
    # Try to get from workflow state first
    try:
        state_data = await WorkflowStateManager.get_state(project_id)
        if state_data and "discovered_entities" in state_data:
            entities_data = state_data["discovered_entities"]
            return [EntitySpec.from_dict(e) for e in entities_data]
    except Exception as e:
        log("ENTITY_PLANNING", f"Could not load entities from state: {e}")
    
    # Fall back to discovery
    user_request = ""
    try:
        user_request = await WorkflowStateManager.get_original_request(project_id) or ""
    except Exception:
        pass
    
    entities = discover_all_entities(project_path, user_request)
    
    # Save to state for future use
    try:
        state_data = await WorkflowStateManager.get_state(project_id) or {}
        state_data["discovered_entities"] = [e.to_dict() for e in entities]
        await WorkflowStateManager.set_state(project_id, state_data)
    except Exception as e:
        log("ENTITY_PLANNING", f"Could not save entities to state: {e}")
    
    return entities
