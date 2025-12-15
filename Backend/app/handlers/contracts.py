# app/handlers/contracts.py
"""
Step 5: Marcus creates API contracts AFTER seeing the frontend mock.

Workflow order: Analysis (1) → Architecture (2) → Frontend Mock (3) → 
Screenshot Verify (4) → Contracts (5) → Backend Implementation (6) → ...

GenCode Studio pattern:
- Frontend with mock data is already built
- Now we define API contracts based on what the frontend needs
- This ensures the backend is built to serve the exact data the frontend expects
"""
from pathlib import Path
from typing import Any, List

from app.core.types import ChatMessage, StepResult
from app.core.constants import WorkflowStep
from app.core.exceptions import RateLimitError
from app.handlers.base import broadcast_status, broadcast_agent_log
from app.core.logging import log
from app.orchestration.state import WorkflowStateManager
from app.llm import call_llm_with_usage
from app.llm.prompts import MARCUS_PROMPT
from app.persistence import persist_agent_output
from app.utils.parser import normalize_llm_output
import re  # CRITICAL: Needed for _remove_embedded_from_contracts and _parse_marcus_classification


from app.persistence.validator import validate_file_output
from app.orchestration.utils import pluralize

# Centralized entity discovery for dynamic fallback
from app.utils.entity_discovery import discover_primary_entity, extract_entity_from_request as _extract_entity_from_request



async def step_contracts(
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
    Step 5: Marcus creates API contracts AFTER the frontend mock is built.
    
    GenCode Studio pattern: We've already seen the frontend with mock data!
    Now we define contracts that match exactly what the frontend needs.
    
    This reads:
    - frontend/src/data/mock.js to understand what data shapes are mocked
    - frontend/src/pages/*.jsx to understand what API calls are expected
    - architecture.md for overall design context
    
    Produces:
    - contracts.md with API endpoints that match the frontend's expectations
    
    Raises:
        RateLimitError: If rate limited - workflow should stop
    """
    await broadcast_status(
        manager, project_id, WorkflowStep.CONTRACTS,
        f"Turn {current_turn}/{max_turns}: Marcus creating API contracts (based on frontend mock)...",
        current_turn, max_turns
    )
    
    # V3: Track token usage for cost reporting
    step_token_usage = None
    
    # Get intent context
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
            # Dynamic last resort: extract from user request
            primary_entity = _extract_entity_from_request(user_request) or "entity"
    
    primary_entity_capitalized = primary_entity.capitalize()
    primary_entity_plural = pluralize(primary_entity)
    features = intent.get("coreFeatures", [])
    
    # ═══════════════════════════════════════════════════════════════════
    # GENCODE STUDIO PATTERN: Read the existing frontend mock data
    # ═══════════════════════════════════════════════════════════════════
    
    # 1. Read mock.js to understand data shapes
    mock_data_content = ""
    mock_file = project_path / "frontend" / "src" / "data" / "mock.js"
    try:
        if mock_file.exists():
            mock_data_content = mock_file.read_text(encoding="utf-8")[:2000]
            log("CONTRACTS", f"Found mock.js with {len(mock_data_content)} chars")
    except Exception as e:
        log("CONTRACTS", f"Could not read mock.js: {e}")
    
    # 2. Read existing pages to understand expected API calls
    frontend_pages_content = ""
    pages_dir = project_path / "frontend" / "src" / "pages"
    try:
        if pages_dir.exists():
            page_snippets = []
            for page_file in pages_dir.glob("*.jsx"):
                content = page_file.read_text(encoding="utf-8")
                # Extract just the relevant parts (imports, API calls, state)
                snippet = content[:600] if len(content) > 600 else content
                page_snippets.append(f"--- {page_file.name} ---\n{snippet}")
            frontend_pages_content = "\n\n".join(page_snippets[:3])  # First 3 pages
    except Exception as e:
        log("CONTRACTS", f"Could not read frontend pages: {e}")
    
    # 3. Read architecture for overall context
    arch_snippet = ""
    try:
        arch_file = project_path / "architecture.md"
        if arch_file.exists():
            arch_snippet = arch_file.read_text(encoding="utf-8")[:1500]
    except Exception:
        pass

    # ═══════════════════════════════════════════════════════════════════
    # LEARNING LOOP: Load successful examples from past classifications
    # (MUST happen BEFORE prompt definition that uses {learned_examples_section})
    # ═══════════════════════════════════════════════════════════════════
    learned_examples_section = ""
    try:
        from app.arbormind.metrics_collector import (
            get_successful_classification_examples,
            get_classification_accuracy_stats
        )
        
        examples = get_successful_classification_examples(limit=5)
        stats = get_classification_accuracy_stats()
        
        if examples:
            examples_text = []
            for ex in examples:
                examples_text.append(f"""
- **{ex['entity']}** classified as **{ex['type']}**
  - Evidence: {ex['mock_evidence']}
""")
            
            learned_examples_section = f"""
Marcus, you have classified {stats['total']} entities so far with {stats['accuracy']:.0f}% accuracy.
Here are {len(examples)} recent successful classifications to learn from:

{''.join(examples_text)}

Use these patterns to guide your classification!
"""
            log("CONTRACTS", f"📚 Loaded {len(examples)} learned examples for Marcus (overall accuracy: {stats['accuracy']:.0f}%)")
        else:
            learned_examples_section = "No learned examples yet. This is your first classification!"
            
    except Exception as learn_err:
        log("CONTRACTS", f"⚠️ Could not load learned examples: {learn_err}")
        learned_examples_section = "(Learning system initializing...)"

    # ═══════════════════════════════════════════════════════════════════
    # CONTRACTS PROMPT - References the frontend mock
    # ═══════════════════════════════════════════════════════════════════
    
    contracts_prompt = f"""
You are Marcus, the technical architect.

═══════════════════════════════════════════════════════
GENCODE STUDIO PATTERN: FRONTEND-FIRST CONTRACTS
═══════════════════════════════════════════════════════

The frontend with mock data has ALREADY been built!
Your job is to create API contracts that match EXACTLY what the frontend expects.

USER REQUEST: {user_request}
PRIMARY ENTITY: {primary_entity_capitalized}
DETECTED ENTITIES: {', '.join(entities_list)}
CORE FEATURES: {', '.join(features)}

═══════════════════════════════════════════════════════
📁 EXISTING FRONTEND MOCK DATA (src/data/mock.js)
═══════════════════════════════════════════════════════

The frontend is using this mock data. Your API must return data in THE SAME SHAPE:

```javascript
{mock_data_content if mock_data_content else "// No mock.js found - define shapes based on entities"}
```

═══════════════════════════════════════════════════════
📄 FRONTEND PAGES (what they expect from API)
═══════════════════════════════════════════════════════

These pages will call your API. Match their expectations:

{frontend_pages_content if frontend_pages_content else "// No pages found - define standard CRUD endpoints"}

═══════════════════════════════════════════════════════
📐 ARCHITECTURE CONTEXT
═══════════════════════════════════════════════════════

{arch_snippet if arch_snippet else "// No architecture found - use standard patterns"}

═══════════════════════════════════════════════════════
🧠 LEARNED EXAMPLES (from past successful classifications)
═══════════════════════════════════════════════════════

{learned_examples_section}

═══════════════════════════════════════════════════════
🎯 ENTITY CLASSIFICATION RULES (CRITICAL!)
═══════════════════════════════════════════════════════

Before creating API endpoints, you MUST classify each entity correctly:

**AGGREGATE Entities** - Create full CRUD endpoints (/api/X):
✅ Appears as TOP-LEVEL array export in mock.js
   Examples: export const mockTasks = [...], export const mockUsers = [...]
✅ Has independent lifecycle (can be created/updated/deleted on its own)
✅ Needs own MongoDB collection
✅ Has unique ID at root level

**EMBEDDED Entities** - DO NOT create endpoints:
🔒 Appears ONLY as nested object or array INSIDE another entity
   Examples: assignee: {{name, avatar}}, tags: [{{name, color}}]
🔒 No top-level export in mock.js
🔒 Part of parent entity, no independent existence
🔒 No separate API routes needed

**CLASSIFICATION EXAMPLES FROM MOCK.JS:**

```javascript
// Example 1: Task is AGGREGATE (top-level export)
export const mockTasks = [
  {{
    id: "1",
    title: "Task 1",
    assignee: {{name: "John", avatar: "..."}},  // ← Assignee is EMBEDDED
    tags: [{{name: "urgent", color: "red"}}]    // ← Tag is EMBEDDED
  }}
]

// Result:
// ✅ Task: AGGREGATE → Create /api/tasks endpoints
// 🔒 Assignee: EMBEDDED → DO NOT create /api/assignees
// 🔒 Tag: EMBEDDED → DO NOT create /api/tags
```

**HOW TO ANALYZE mock.js:**
1. Find all "export const mock___" declarations
2. Those are AGGREGATE entities (create endpoints)
3. Any nested objects/arrays are EMBEDDED (no endpoints)

═══════════════════════════════════════════════════════
📋 YOUR TASK
═══════════════════════════════════════════════════════

**STEP 1: CLASSIFY ENTITIES (MANDATORY OUTPUT)**

Before writing any endpoints, include this section in contracts.md:

## Entity Classification

For each entity found in mock.js, list:
- **Name**: Entity name (e.g., Task, User, Assignee)
- **Type**: AGGREGATE or EMBEDDED
- **Evidence**: Why? (e.g., "top-level export mockTasks" or "nested in Task.assignee")

Example:
```markdown
## Entity Classification

- **Task**
  - Type: AGGREGATE
  - Evidence: Top-level export (mockTasks = [...])
  - Endpoints: Will create /api/tasks

- **Assignee**
  - Type: EMBEDDED
  - Evidence: Nested object in Task.assignee
  - Endpoints: None (nested data only)
```

⚠️ This classification will be VALIDATED by the system.
Incorrect classifications will be automatically corrected.

**STEP 2: CREATE ENDPOINTS (ONLY FOR AGGREGATE ENTITIES)**

Create `contracts.md` that defines:

1. **Entity Classification** (see above - MANDATORY!)

2. **Data Models** - Match the shapes in mock.js EXACTLY
   - Same field names
   - Same types
   - Same optional/required status

2. **REST API Endpoints for {primary_entity_capitalized}** - All endpoints the frontend will call:
   - GET /api/{primary_entity_plural} - List all {primary_entity_plural} (returns array matching mock shape)
   - POST /api/{primary_entity_plural} - Create new {primary_entity} (accepts object, returns created)
   - GET /api/{primary_entity_plural}/{{id}} - Get single {primary_entity}
   - PUT /api/{primary_entity_plural}/{{id}} - Update {primary_entity}
   - DELETE /api/{primary_entity_plural}/{{id}} - Delete {primary_entity}

3. **Response & Error Format (MUST FOLLOW)** - Fixed JSON structure:

```markdown
## Response & Error Format (MUST FOLLOW)

- Successful list responses:
  - 200 OK
  - Body:
    {{
      "data": [<Entity>],
      "total": number,
      "page": number,
      "limit": number
    }}

- Successful single-item responses:
  - 200 OK or 201 Created
  - Body:
    {{ "data": <Entity> }}

- Error responses:
  - 4xx / 5xx
  - Body:
    {{
      "error": {{
        "code": "<MACHINE_READABLE_CODE>",
        "message": "<Human readable message>",
        "details": optional
      }}
    }}

This format MUST be consistent across all endpoints.
Routers and tests will rely on it.
```

4. **Integration Notes** - How frontend will consume this:
   - Document the lib/api.js client pattern
   - Document error handling expectations
   - Document pagination if applicable

═══════════════════════════════════════════════════════
📤 OUTPUT FORMAT
═══════════════════════════════════════════════════════

Return ONLY JSON: 
{{ 
  "thinking": "Analyze the mock data and frontend pages to define matching API contracts...",
  "files": [ {{ "path": "contracts.md", "content": "..." }} ] 
}}
"""

    # Broadcast Marcus started
    await broadcast_agent_log(
        manager,
        project_id,
        "AGENT:Marcus",
        f"Analyzing frontend mock data to define API contracts for {intent.get('domain', 'app')}..."
    )
    
    try:
        # Use step-specific token allocation
        from app.orchestration.token_policy import get_tokens_for_step
        contracts_tokens = get_tokens_for_step(WorkflowStep.CONTRACTS, is_retry=False)
        
        llm_result = await call_llm_with_usage(
            prompt=contracts_prompt,
            system_prompt=MARCUS_PROMPT,
            provider=provider,
            model=model,
            max_tokens=contracts_tokens,
        )
        
        # V3: Extract text and usage
        raw = llm_result.get("text", "")
        step_token_usage = llm_result.get("usage", {"input": 0, "output": 0})
        log("TOKENS", f"📊 Contracts usage: {step_token_usage.get('input', 0):,} in / {step_token_usage.get('output', 0):,} out")

        parsed = normalize_llm_output(raw)
        
        # Broadcast Thinking
        thinking = parsed.get("thinking")
        if thinking:
             await broadcast_agent_log(
                manager,
                project_id,
                "AGENT:Marcus",
                "Marcus is thinking...",
                data={"thinking": thinking}
            )

        try:
            validated = validate_file_output(parsed, WorkflowStep.CONTRACTS, max_files=1)
            await persist_agent_output(manager, project_id, project_path, validated, WorkflowStep.CONTRACTS)
            
            # Clear discovery cache so subsequent steps use contracts.md entity, not mock.js
            from app.utils.entity_discovery import clear_discovery_cache
            clear_discovery_cache(project_path)
            
            # AUTO-GENERATE entity_plan.json from contracts.md for multi-entity backend mode
            try:
                _generate_entity_plan_from_contracts(project_path, project_id)
            except Exception as plan_err:
                log("CONTRACTS", f"Could not auto-generate entity_plan.json: {plan_err}")
            
            await broadcast_agent_log(
                manager,
                project_id,
                "AGENT:Marcus",
                "I've established the API contracts in contracts.md based on the frontend mock data. "
                "The backend will now be built to match these exact specifications."
            )
        except ValueError as e:
            log("AGENT:Marcus", f"Issue validating contracts: {e}. Continuing anyway.", project_id=project_id)

        chat_history.append({"role": "assistant", "content": raw})
        
    except RateLimitError:
        log("CONTRACTS", "Rate limit exhausted - stopping workflow", project_id=project_id)
        raise
        
    except Exception as e:
        log("CONTRACTS", f"Contracts failed: {e}", project_id=project_id)
    
    # Proceed to backend development
    return StepResult(
        nextstep=WorkflowStep.BACKEND_IMPLEMENTATION,
        turn=current_turn + 1,
        token_usage=step_token_usage,  # V3
    )




def _parse_marcus_classification(contracts_content: str) -> dict:
    """
    Parse Marcus's entity classification section from contracts.md.
    
    Looks for "## Entity Classification" section and extracts Marcus's
    classification decisions.
    
    Returns:
        Dict mapping entity names to Marcus's classifications
        Example: {"Task": "AGGREGATE", "Assignee": "EMBEDDED"}
    """
    marcus_classifications = {}
    
    # Find Entity Classification section
    pattern = r'##\s+Entity\s+Classification(.*?)(?=##|\Z)'
    match = re.search(pattern, contracts_content, re.DOTALL | re.IGNORECASE)
    
    if not match:
        return marcus_classifications
    
    section_content = match.group(1)
    
    # Parse each entity
    # Pattern: - **EntityName** followed by Type: AGGREGATE or EMBEDDED
    entity_pattern = r'-\s+\*\*([\w]+)\*\*[^-]*?Type:\s+(AGGREGATE|EMBEDDED)'
    
    for entity_match in re.finditer(entity_pattern, section_content, re.IGNORECASE):
        entity_name = entity_match.group(1)
        entity_type = entity_match.group(2).upper()
        marcus_classifications[entity_name] = entity_type
    
    return marcus_classifications


def _calculate_classification_confidence(
    marcus_classifications: dict,
    final_classifications: dict
) -> dict:
    """
    Calculate how accurate Marcus was compared to code-based classification.
    
    Args:
        marcus_classifications: Marcus's entity type decisions
        final_classifications: Code-validated entity types
    
    Returns:
        Metrics dict with accuracy and details
    """
    if not marcus_classifications:
        return {
            "marcus_entities": {},
            "final_entities": final_classifications,
            "corrections": 0,
            "total": len(final_classifications),
            "confidence": 0.0,
            "status": "no_marcus_classification"
        }
    
    # Count corrections needed
    corrections = 0
    marcus_correct = 0
    details = []
    
    all_entities = set(marcus_classifications.keys()) | set(final_classifications.keys())
    
    for entity_name in all_entities:
        marcus_type = marcus_classifications.get(entity_name, "UNKNOWN")
        final_type = final_classifications.get(entity_name, "UNKNOWN")
        
        if marcus_type == final_type:
            marcus_correct += 1
            details.append(f"   ✅ {entity_name}: {final_type} (Marcus correct)")
        else:
            corrections += 1
            details.append(f"   🔧 {entity_name}: Marcus said {marcus_type}, corrected to {final_type}")
    
    total = len(all_entities)
    confidence = (marcus_correct / total) if total > 0 else 0.0
    
    return {
        "marcus_entities": marcus_classifications,
        "final_entities": final_classifications,
        "corrections": corrections,
        "correct": marcus_correct,
        "total": total,
        "confidence": confidence,
        "details": details,
        "status": "measured"
    }


def _generate_entity_plan_from_contracts(project_path: Path, project_id: str) -> None:
    """
    Auto-generate entity_plan.json by parsing contracts.md.
    
    DYNAMIC DETECTION:
    - CRUD entities: Have POST/PUT/DELETE + standard paths (/api/expenses)
    - Namespaces: Only GET + nested paths (/api/dashboard/stats)
    
    FIX #2, #3, #4: NOW CLASSIFIES ENTITIES AS AGGREGATE OR EMBEDDED!
    - Uses mock.js structure to identify nested vs top-level entities
    - Uses contracts.md patterns to determine CRUD vs readonly
    - Removes embedded entity sections from contracts.md after classification
    
    Only generates entities for true CRUD resources.
    """
    from collections import defaultdict
    from app.utils.entity_discovery import EntitySpec, EntityPlan, singularize
    
    contracts_file = project_path / "contracts.md"
    if not contracts_file.exists():
        log("CONTRACTS", "No contracts.md found - skipping entity_plan.json generation")
        return
    
    content = contracts_file.read_text(encoding="utf-8")
    
    # Parse all API endpoints with full paths
    # Pattern: METHOD /api/path/to/endpoint
    endpoint_pattern = r'(GET|POST|PUT|DELETE|PATCH)\s+`?/api/([^`\s]+)'
    matches = re.findall(endpoint_pattern, content, re.IGNORECASE)
    
    if not matches:
        log("CONTRACTS", "No API endpoints found in contracts.md")
        return
    
    # Group endpoints by base path segment
    # e.g., "expenses", "categories", "dashboard"
    endpoint_groups = defaultdict(lambda: {"methods": set(), "paths": []})
    
    for method, full_path in matches:
        # Extract base segment (first part after /api/)
        parts = full_path.split('/')
        base_segment = parts[0].lower()
        
        # Skip utility endpoints
        if base_segment in ['health', 'docs', 'openapi', 'metrics', 'v1', 'v2']:
            continue
        
        endpoint_groups[base_segment]["methods"].add(method.upper())
        endpoint_groups[base_segment]["paths"].append(full_path)
    
    log("CONTRACTS", f"📋 Found {len(endpoint_groups)} base path segments: {sorted(endpoint_groups.keys())}")
    
    # Analyze each group to determine if it's a CRUD entity or namespace
    crud_entities = []
    namespaces = []
    
    for base_segment, data in endpoint_groups.items():
        methods = data["methods"]
        paths = data["paths"]
        
        # Check if this is a CRUD entity
        has_create = "POST" in methods
        has_update = "PUT" in methods or "PATCH" in methods
        has_delete = "DELETE" in methods
        
        # Check for standard CRUD path patterns (no nesting beyond {id})
        has_standard_paths = any(
            p == base_segment or p == f"{base_segment}/{{id}}" or p.startswith(f"{base_segment}?")
            for p in paths
        )
        
        # CRUD entity if it has write methods or standard CRUD paths
        is_crud = (has_create or has_update or has_delete) or has_standard_paths
        
        if is_crud:
            crud_entities.append(base_segment)
            log("CONTRACTS", f"   ✅ {base_segment}: CRUD entity (methods: {sorted(methods)})")
        else:
            namespaces.append(base_segment)
            log("CONTRACTS", f"   ⏭️ {base_segment}: Namespace/readonly (skipping)")
    
    if not crud_entities:
        log("CONTRACTS", "⚠️ No CRUD entities found - only namespaces detected")
        return
    
    # ═══════════════════════════════════════════════════════════
    # FIX #3: CLASSIFY ENTITIES AS AGGREGATE OR EMBEDDED
    # ═══════════════════════════════════════════════════════════
    log("CONTRACTS", "🔍 Classifying entities (AGGREGATE vs EMBEDDED)...")
    
    # Parse Marcus's classification from contracts.md
    marcus_classifications = _parse_marcus_classification(content)
    
    # Get code-based classification (ground truth)
    from app.utils.entity_classification import classify_project_entities
    entity_types = classify_project_entities(project_path)
    
    # Calculate Marcus's accuracy
    confidence_metrics = _calculate_classification_confidence(
        marcus_classifications,
        entity_types
    )
    
    # Log classification confidence
    if confidence_metrics["status"] == "measured":
        correct = confidence_metrics["correct"]
        total = confidence_metrics["total"]
        confidence_pct = confidence_metrics["confidence"] * 100
        
        log("CONTRACTS", f"📊 Marcus Classification Accuracy: {correct}/{total} correct ({confidence_pct:.0f}%)")
        
        # Log details
        for detail in confidence_metrics["details"]:
            log("CONTRACTS", detail)
        
        if confidence_metrics["corrections"] == 0:
            log("CONTRACTS", "   🎯 Perfect! Marcus got all classifications correct!")
        else:
            log("CONTRACTS", f"   🔧 Code corrected {confidence_metrics['corrections']} classification(s)")
    else:
        log("CONTRACTS", "   ℹ️ Marcus did not provide Entity Classification section")
        log("CONTRACTS", "   (This is OK - code classification is authoritative)")
    
    # ═══════════════════════════════════════════════════════════
    # LEARNING LOOP: Store classification decisions in database
    # ═══════════════════════════════════════════════════════════
    try:
        from app.arbormind.metrics_collector import store_classification_decision
        
        # Store each classification decision for learning
        all_entities = set(marcus_classifications.keys()) | set(entity_types.keys())
        
        for entity_name in all_entities:
            marcus_type = marcus_classifications.get(entity_name)
            final_type = entity_types.get(entity_name, "UNKNOWN")
            
            # Extract evidence from mock.js and contracts
            mock_evidence = f"(structure analysis needed)"
            contracts_evidence = f"endpoints: {endpoint_groups.get(entity_name.lower() + 's', {}).get('methods', set())}"
            
            store_classification_decision(
                project_id=project_id,
                entity_name=entity_name,
                marcus_classification=marcus_type,
                final_classification=final_type,
                mock_evidence=mock_evidence,
                contracts_evidence=contracts_evidence
            )
        
        log("CONTRACTS", f"💾 Stored {len(all_entities)} classification decisions for learning")
        
    except Exception as store_err:
        log("CONTRACTS", f"⚠️ Failed to store classifications: {store_err}")
    
    # Create EntitySpec for each CRUD entity
    entities = []
    for i, plural in enumerate(sorted(crud_entities)):
        singular = singularize(plural)
        entity_name = singular.capitalize()
        
        # Determine entity type from classification
        entity_type = entity_types.get(entity_name, "AGGREGATE")  # Default to AGGREGATE
        
        entities.append(EntitySpec(
            name=entity_name,
            plural=plural,
            type=entity_type,  # NEW: Add classification!
            description=f"Auto-detected from contracts.md ({entity_type} entity)",
            fields=[],  # Fields will be inferred by Derek from contracts.md
            is_primary=(i == 0),  # First entity is primary
            generation_order=i + 1
        ))
    
    # Create and save the plan
    plan = EntityPlan(
        entities=entities,
        relationships=[],  # Relationships can be inferred later
        warnings=[
            f"Auto-generated from contracts.md ({len(crud_entities)} entities, {len(namespaces)} namespaces excluded)"
        ]
    )
    
    plan_path = project_path / "entity_plan.json"
    plan.save(plan_path)
    
    aggregates = [e.name for e in entities if e.type == "AGGREGATE"]
    embedded = [e.name for e in entities if e.type == "EMBEDDED"]
    
    log("CONTRACTS", f"✅ Generated entity_plan.json with {len(entities)} entities:")
    if aggregates:
        log("CONTRACTS", f"   📊 AGGREGATE ({len(aggregates)}): {aggregates}")
    if embedded:
        log("CONTRACTS", f"   🔒 EMBEDDED ({len(embedded)}): {embedded}")
    if namespaces:
        log("CONTRACTS", f"   ℹ️ Excluded {len(namespaces)} namespaces: {sorted(namespaces)}")
    
    # ═══════════════════════════════════════════════════════════
    # FIX #4: REWRITE CONTRACTS.MD TO REMOVE EMBEDDED ENTITIES
    # ═══════════════════════════════════════════════════════════
    if embedded:
        log("CONTRACTS", f"🗑️ Removing {len(embedded)} EMBEDDED entity sections from contracts.md...")
        _remove_embedded_from_contracts(contracts_file, embedded, plan)


def _remove_embedded_from_contracts(
    contracts_path: Path,
    embedded_names: List[str],
    entity_plan: "EntityPlan"
) -> None:
    """
    FIX #4: Remove endpoint sections for EMBEDDED entities from contracts.md.
    
    Example: Remove "### Assignee Endpoints" section if Assignee is EMBEDDED.
    This prevents Derek from generating routers for nested models!
    """
    if not contracts_path.exists():
        return
    
    try:
        import re
        content = contracts_path.read_text(encoding="utf-8")
        original_length = len(content)
        
        # Get plural forms for embedded entities
        embedded_plurals = [
            e.plural for e in entity_plan.entities 
            if e.name in embedded_names
        ]
        
        # Remove sections for embedded entities 
        # Pattern: ### ENTITY Endpoints ... (until next ### or end)
        for entity_name in embedded_names + embedded_plurals:
            # Try multiple patterns
            patterns = [
                rf'###\s+{re.escape(entity_name)}.*?Endpoints.*?(?=###|\Z)',  # ### Assignee Endpoints
                rf'##\s+{re.escape(entity_name)}.*?(?=##|\Z)',  # ## Assignee
                rf'#{1,3}\s+{re.escape(entity_name.capitalize())}.*?(?=#{1,3}|\Z)',  # Capitalized variations
            ]
            
            for pattern in patterns:
                before = len(content)
                content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
                if len(content) < before:
                    removed = before - len(content)
                    log("CONTRACTS", f"   ✂️ Removed {entity_name} section ({removed} chars)")
        
        # Clean up multiple blank lines
        content = re.sub(r'\n{4,}', '\n\n\n', content)
        
        # Write back if changed
        if len(content) < original_length:
            contracts_path.write_text(content, encoding="utf-8")
            removed_total = original_length - len(content)
            log("CONTRACTS", f"   ✅ Rewrote contracts.md (removed {removed_total} chars from embedded entities)")
        else:
            log("CONTRACTS", f"   ℹ️ No embedded entity sections found to remove")
        
    except Exception as e:
        log("CONTRACTS", f"   ⚠️ Failed to rewrite contracts.md: {e}")


