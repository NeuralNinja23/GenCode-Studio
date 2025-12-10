# app/handlers/contracts.py
"""
Step 5: Marcus creates API contracts AFTER seeing the frontend mock.

Workflow order: Analysis (1) → Architecture (2) → Frontend Mock (3) → 
Screenshot Verify (4) → Contracts (5) → Backend Models (6) → ...

GenCode Studio pattern:
- Frontend with mock data is already built
- Now we define API contracts based on what the frontend needs
- This ensures the backend is built to serve the exact data the frontend expects
"""
from pathlib import Path
from typing import Any, Dict, List

from app.core.types import ChatMessage, StepResult
from app.core.constants import WorkflowStep, DEFAULT_MAX_TOKENS
from app.core.exceptions import RateLimitError
from app.handlers.base import broadcast_status, broadcast_agent_log
from app.core.logging import log
from app.orchestration.state import WorkflowStateManager
from app.llm import call_llm
from app.llm.prompts import MARCUS_PROMPT
from app.persistence import persist_agent_output
from app.utils.parser import normalize_llm_output


from app.persistence.validator import validate_file_output
from app.orchestration.utils import pluralize



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
    
    # Get intent context
    intent = WorkflowStateManager.get_intent(project_id) or {}
    entities_list = intent.get("entities", ["item"])
    primary_entity = entities_list[0] if entities_list else "item"
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
📋 YOUR TASK
═══════════════════════════════════════════════════════

Create `contracts.md` that defines:

1. **Data Models** - Match the shapes in mock.js EXACTLY
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
        raw = await call_llm(
            prompt=contracts_prompt,
            system_prompt=MARCUS_PROMPT,
            provider=provider,
            model=model,
            max_tokens=DEFAULT_MAX_TOKENS,
        )

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
    )
