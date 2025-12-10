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
    Step 6: Derek generates backend models with Marcus supervision and auto-retry.
    
    Workflow order: ... → Contracts (5) → Backend Models (6) → Backend Routers (7) → ...
    """
    await broadcast_status(
        manager, project_id, WorkflowStep.BACKEND_MODELS,
        f"Turn {current_turn}/{max_turns}: Derek creating backend models...",
        current_turn, max_turns
    )
    
    # Read contracts.md so Derek knows the API structure
    try:
        contracts = (project_path / "contracts.md").read_text(encoding="utf-8")
        if len(contracts.strip()) < 10:
            contracts = "No detailed contracts found. Assume standard CRUD for entities."
    except Exception:
        contracts = "No contracts found - use generic CRUD endpoints."
    
    # Get entity-specific information
    intent = WorkflowStateManager.get_intent(project_id) or {}
    entities_list = intent.get("entities", ["item"])
    primary_entity = entities_list[0] if entities_list else "item"
    primary_entity_capitalized = primary_entity.capitalize()
    
    # Get archetype for backend patterns
    archetype = (intent.get("archetypeRouting") or {}).get("top") or "general"
    
    # Build model class names
    model_classes = ", ".join([e.capitalize() for e in entities_list])
    
    backend_instructions = f"""Based on the API contracts below, generate the backend foundation.

PROJECT ARCHETYPE (attention-based): {archetype}

═══════════════════════════════════════════════════════
⚙️ BACKEND PATTERNS BY ARCHETYPE
═══════════════════════════════════════════════════════

Follow these conventions based on the archetype:

- admin_dashboard / project_management:
  - Every main entity SHOULD have:
    - `status: str` (e.g. "open" | "in_progress" | "closed")
    - `created_at: datetime` and `updated_at: datetime` with default_factory
    - Optional `owner_id: str | None` or `assignee_id: str | None`
  - Prefer filters and query-friendly fields (status, priority, tags).

- saas_app:
  - Entities SHOULD be multi-tenant:
    - `organization_id: str` or `tenant_id: str`
  - Include `created_at` / `updated_at`.
  - Prefer fields like `plan`, `role`, `is_active`.

- ecommerce_store:
  - Product-like entities SHOULD include:
    - `price: float`, `currency: str = "USD"`, `in_stock: bool = True`
  - Order-like entities SHOULD include:
    - `items: List[ItemRef]`, `total_amount: float`, `status: str`
  - Always include timestamps.

- realtime_collab:
  - Message / event entities SHOULD include:
    - `user_id: str`, `channel_id: str`, `content: str`
    - `created_at: datetime` (no `updated_at` required unless edits allowed)

If contracts.md conflicts with these patterns, contracts.md WINS.
Otherwise, use these to enrich the models.

═══════════════════════════════════════════════════════
⚠️ CRITICAL: USE PROJECT-SPECIFIC ENTITY NAMES
═══════════════════════════════════════════════════════

Do NOT create generic "Item" models. Create models for:
- **Primary Entity**: {primary_entity_capitalized}
- **All Entities**: {', '.join(entities_list)}
- **Model Classes to Create**: {model_classes}

===== API CONTRACTS (USE THIS!) =====
{contracts}
=====================================

═══════════════════════════════════════════════════════
🚨 CRITICAL: CONTRACT COMPLIANCE
═══════════════════════════════════════════════════════
You MUST implement every field defined in the API CONTRACTS above.
- If contract says "comments: List[Comment]", you MUST create the `Comment` embedded model or class.
- If contract says "priority: str", you MUST add that field.
- Do NOT skip fields or "simplify" the model to just title/content.
- Marcus Review will REJECT your code if fields are missing.

Generate EXACTLY 4 files:

1. **backend/app/database.py** - MongoDB connection using motor
   - Use environment variable MONGO_URL
   - Export `init_db()` async function

2. **backend/app/db.py** - Test wrapper (REQUIRED FOR TESTS!)
   - Import init_db from database.py
   - Export `connect_db()` and `disconnect_db()` functions
   - Tests use: `from app.db import connect_db, disconnect_db`

3. **backend/app/models.py** - Beanie models for EACH entity
   - Create class: `{primary_entity_capitalized}` (not Item!)
   - Include ALL fields relevant to the entity
   - Use datetime objects for date/time fields

4. **backend/requirements.txt** - Python dependencies

═══════════════════════════════════════════════════════
🚨 CRITICAL: backend/app/db.py IS REQUIRED FOR TESTS 🚨
═══════════════════════════════════════════════════════

Tests import: `from app.db import connect_db, disconnect_db`
If you don't generate db.py, ALL TESTS WILL FAIL!

REQUIRED db.py template:
```python
# backend/app/db.py - Test wrapper for database connection
from app.database import init_db

async def connect_db():
    \"\"\"Connect to database (wrapper for init_db).\"\"\"
    await init_db()

async def disconnect_db():
    \"\"\"Disconnect from database.\"\"\"
    pass  # Motor handles connection cleanup automatically

__all__ = ["connect_db", "disconnect_db"]
```

═══════════════════════════════════════════════════════
📦 EXAMPLE MODEL (Use actual entity name!)
═══════════════════════════════════════════════════════

```python
# CORRECT: Use actual entity name "{primary_entity}"
from beanie import Document
from pydantic import Field
from datetime import datetime, timezone
from typing import Optional

class {primary_entity_capitalized}(Document):
    title: str
    content: Optional[str] = None
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "{primary_entity}s"  # MongoDB collection name
```

═══════════════════════════════════════════════════════
📦 REQUIRED DEPENDENCIES
═══════════════════════════════════════════════════════

REQUIRED:
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.9.0
pytest>=9.0.0
pytest-asyncio>=0.24.0
httpx>=0.27.0
motor>=3.6.0
beanie>=1.26.0

CRITICAL: Return EXACTLY this JSON with 4 files:
{{
  "thinking": "Create {primary_entity_capitalized} model with fields for...",
  "files": [
    {{"path": "backend/app/database.py", "content": "..."}},
    {{"path": "backend/app/db.py", "content": "..."}},
    {{"path": "backend/app/models.py", "content": "..."}},
    {{"path": "backend/requirements.txt", "content": "..."}}
  ]
}}
"""
    
    try:
        # Use supervised call with auto-retry
        result = await supervised_agent_call(
            project_id=project_id,
            manager=manager,
            agent_name="Derek",
            step_name="Backend Models",
            base_instructions=backend_instructions,
            project_path=project_path,
            user_request=user_request,
            contracts=contracts,
            max_retries=2,
        )
        
        parsed = result.get("output", {})
        if "files" in parsed and parsed["files"]:
            validated = validate_file_output(parsed, WorkflowStep.BACKEND_MODELS, max_files=4)
            files_written = await persist_agent_output(manager, project_id, project_path, validated, WorkflowStep.BACKEND_MODELS)
            
            status = "✅ approved" if result.get("approved") else "⚠️ best effort"
            log("BACKEND", f"Derek generated {files_written} model files ({status}, attempt {result.get('attempt', 1)})")
        
        chat_history.append({"role": "assistant", "content": str(parsed)})
        
    except RateLimitError:
        log("BACKEND", "Rate limit exhausted - stopping workflow", project_id=project_id)
        raise
        
    except Exception as e:
        log("BACKEND", f"Derek failed: {e}", project_id=project_id)
    
    return StepResult(
        nextstep=WorkflowStep.BACKEND_ROUTERS,
        turn=current_turn + 1,
    )


async def step_backend_routers(
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
    Step 7: Derek generates API routers with dynamic discovery support.
    
    Workflow order: ... → Backend Models (6) → Backend Routers (7) → Backend Main (8) → ...
    """
    await broadcast_status(
        manager,
        project_id,
        WorkflowStep.BACKEND_ROUTERS,
        f"Turn {current_turn}/{max_turns}: Derek creating API endpoints...",
        current_turn,
        max_turns,
    )

    # Read contracts.md so Derek knows the API structure
    try:
        contracts = (project_path / "contracts.md").read_text(encoding="utf-8")
        if len(contracts.strip()) < 10:
            contracts = "No detailed contracts found. Assume standard CRUD for entities."
    except Exception:
        contracts = "No contracts found - use generic CRUD endpoints."
    
    # Read models.py so Derek knows the data models
    try:
        models = (project_path / "backend/app/models.py").read_text(encoding="utf-8")
        if len(models.strip()) < 10:
            models = "No models found."
    except Exception:
        models = "No models found."

    intent = WorkflowStateManager.get_intent(project_id) or {}
    entities_list = intent.get("entities", ["item"])
    primary_entity = entities_list[0] if entities_list else "item"
    primary_entity_capitalized = primary_entity.capitalize()
    primary_entity_plural = pluralize(primary_entity)
    
    # Get archetype for backend routing patterns
    archetype = (intent.get("archetypeRouting") or {}).get("top") or "general"
    
    # Build router file paths
    router_files = [f"backend/app/routers/{pluralize(e)}.py" for e in entities_list]

    router_instructions = f"""Based on the API contracts and models below, generate router files.

PROJECT ARCHETYPE (attention-based): {archetype}

═══════════════════════════════════════════════════════
⚙️ ROUTING & ENDPOINT PATTERNS BY ARCHETYPE
═══════════════════════════════════════════════════════

- admin_dashboard / project_management:
  - Endpoints SHOULD support:
    - Filtering by status, search query, optional date ranges.
    - Pagination via query params: `page`, `limit`.
  - Example: `GET /api/{primary_entity_plural}?status=open&page=1&limit=20`

- saas_app:
  - Endpoints SHOULD be scoped by tenant/organization:
    - Either via query param (`?organization_id=...`)
    - Or via body field on create/update.
  - Protect against returning data across organizations.

- ecommerce_store:
  - Products:
    - `GET /api/products` optionally accepts `category`, `price_min`, `price_max`.
  - Orders:
    - POST for creating order
    - GET for fetching orders by user.

- realtime_collab:
  - Endpoints SHOULD support listing messages by channel and recency:
    - `GET /api/messages?channel_id=...`
    - `POST /api/messages` to send new message.

Use contracts.md as the primary source of truth.
Use archetype patterns to fill in missing behaviour (filters, pagination, etc.).

═══════════════════════════════════════════════════════
🚨 MANDATORY: CREATE PRIMARY ENTITY ROUTER FIRST 🚨
═══════════════════════════════════════════════════════

PRIMARY ENTITY: {primary_entity_capitalized}
REQUIRED FIRST FILE: backend/app/routers/{primary_entity}s.py

The PRIMARY router is NON-NEGOTIABLE - you MUST create:
- backend/app/routers/{primary_entity}s.py

After creating the primary router, you MAY ALSO create secondary routers
for supporting entities (users, projects, comments, etc.) if needed.

═══════════════════════════════════════════════════════
⚠️ ANTI-PATTERNS TO AVOID
═══════════════════════════════════════════════════════

❌ WRONG: Creating Users.py WITHOUT the primary {primary_entity}s.py
❌ WRONG: Creating only generic items.py
❌ WRONG: Skipping the primary entity router

✅ RIGHT: Create {primary_entity}s.py FIRST, then add secondary routers

═══════════════════════════════════════════════════════
📁 ROUTER FILES TO GENERATE
═══════════════════════════════════════════════════════

1. **REQUIRED FIRST**: backend/app/routers/{primary_entity}s.py  
2. (Optional) Additional routers for secondary entities

===== API CONTRACTS =====
{contracts}
=========================

===== MODELS.PY (Import from here) =====
{models}
=====================

═══════════════════════════════════════════════════════
📦 EXAMPLE ROUTER STRUCTURE
═══════════════════════════════════════════════════════

Generate these files (use ACTUAL entity names):

1. **backend/app/routers/{primary_entity}s.py**
   - Router for {primary_entity_capitalized} CRUD operations
   - Import: `from app.models import {primary_entity_capitalized}`
   - Functions: `list_{primary_entity_plural}`, `create_{primary_entity}`, `get_{primary_entity}`, `delete_{primary_entity}`

═══════════════════════════════════════════════════════
📦 EXAMPLE ROUTER (Use actual entity name!)
═══════════════════════════════════════════════════════

```python
# backend/app/routers/{primary_entity}s.py
from fastapi import APIRouter, HTTPException
from typing import List
from app.models import {primary_entity_capitalized}

router = APIRouter()

@router.get("/", response_model=List[{primary_entity_capitalized}])
async def list_{primary_entity_plural}():
    \"\"\"Get all {primary_entity_plural}.\"\"\"
    {primary_entity_plural} = await {primary_entity_capitalized}.find_all().to_list()
    return {primary_entity_plural}

@router.post("/", response_model={primary_entity_capitalized})
async def create_{primary_entity}(data: {primary_entity_capitalized}):
    \"\"\"Create a new {primary_entity}.\"\"\"
    await data.insert()
    return data

@router.get("/{{id}}")
async def get_{primary_entity}(id: str):
    \"\"\"Get {primary_entity} by ID.\"\"\"
    {primary_entity} = await {primary_entity_capitalized}.get(id)
    if not {primary_entity}:
        raise HTTPException(status_code=404, detail="{primary_entity_capitalized} not found")
    return {primary_entity}

@router.delete("/{{id}}")
async def delete_{primary_entity}(id: str):
    \"\"\"Delete a {primary_entity}.\"\"\"
    {primary_entity} = await {primary_entity_capitalized}.get(id)
    if not {primary_entity}:
        raise HTTPException(status_code=404, detail="{primary_entity_capitalized} not found")
    await {primary_entity}.delete()
    return {{"message": "Deleted"}}
```

═══════════════════════════════════════════════════════
⚠️ REQUIREMENTS
═══════════════════════════════════════════════════════

- Each router MUST export a `router` object at module level
- Use async/await for all endpoint functions
- DO NOT hardcode `/api/` prefix - it's added automatically
- Add error handling with HTTPException

CRITICAL: Return EXACTLY this JSON:
{{
  "thinking": "Creating {primary_entity}s router with CRUD endpoints...",
  "files": [
    {{"path": "backend/app/routers/{primary_entity}s.py", "content": "..."}}
  ]
}}

Generate entity-specific router files now!
"""

    try:
        # Use supervised call with auto-retry
        result = await supervised_agent_call(
            project_id=project_id,
            manager=manager,
            agent_name="Derek",
            step_name="Backend Routers",
            base_instructions=router_instructions,
            project_path=project_path,
            user_request=user_request,
            contracts=contracts,
            max_retries=2,
        )

        parsed = result.get("output", {})
        if "files" in parsed and parsed["files"]:
            validated = validate_file_output(
                parsed,
                WorkflowStep.BACKEND_ROUTERS,
                max_files=3,
            )
            files_written = await persist_agent_output(
                manager,
                project_id,
                project_path,
                validated,
                WorkflowStep.BACKEND_ROUTERS,
            )
            
            status = "✅ approved" if result.get("approved") else "⚠️ best effort"
            log("BACKEND", f"Derek generated {files_written} router files ({status}, attempt {result.get('attempt', 1)})")

        chat_history.append({"role": "assistant", "content": str(parsed)})

    except RateLimitError:
        log("BACKEND", "Rate limit exhausted - stopping workflow", project_id=project_id)
        raise
        
    except Exception as e:
        log("BACKEND", f"Derek failed during router generation: {e}")

    return StepResult(
        nextstep=WorkflowStep.BACKEND_MAIN,
        turn=current_turn + 1,
    )


async def step_backend_main(
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
    Step 8: Derek generates the main FastAPI app configuration (dynamic).
    
    Workflow order: ... → Backend Routers (7) → Backend Main (8) → Testing Backend (9) → ...
    """
    await broadcast_status(
        manager,
        project_id,
        WorkflowStep.BACKEND_MAIN,
        f"Turn {current_turn}/{max_turns}: Derek configuring main application...",
        current_turn,
        max_turns,
    )

    # Detect existing routers to inform Derek
    routers_dir = project_path / "backend/app/routers"
    existing_routers = []
    if routers_dir.exists():
        # Normalize to lowercase for Linux/Docker compatibility
        existing_routers = [f.stem.lower() for f in routers_dir.glob("*.py") if f.stem != "__init__"]

    # Get archetype for context
    intent = WorkflowStateManager.get_intent(project_id) or {}
    archetype = (intent.get("archetypeRouting") or {}).get("top") or "general"

    router_imports = "\n".join([f"from app.routers import {r}" for r in existing_routers])
    router_mounts = "\n".join([f"app.include_router({r}.router, prefix='/api/{r}', tags=['{r}'])" for r in existing_routers])

    main_instructions = f"""Generate the MAIN entry point for the FastAPI application.

PROJECT ARCHETYPE: {archetype}

═══════════════════════════════════════════════════════
🚨 CRITICAL: DOCKER IMPORT RULES
═══════════════════════════════════════════════════════
- The Docker WORKDIR is `/app`
- The code lives in `/app/app/...`
- **YOU MUST USE `from app...` IMPORTS**
- ❌ WRONG: `from backend.app.database import init_db`
- ✅ RIGHT: `from app.database import init_db`

═══════════════════════════════════════════════════════
FILES TO GENERATE
═══════════════════════════════════════════════════════

1. **backend/app/main.py**
   - Initialize FastAPI app
   - Add CORS middleware (allow all origins for dev: ["*"])
   - Add Health Check endpoint `/api/health`
   - Include routers for: {', '.join(existing_routers)}
   - Initialize database on startup (`@app.on_event("startup")`)

═══════════════════════════════════════════════════════
📦 EXAMPLE MAIN.PY structure
═══════════════════════════════════════════════════════

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db  # ✅ Correct import
# Import routers dynamically
{router_imports}

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def start_db():
    await init_db()

@app.get("/api/health")
async def health_check():
    return {{"status": "healthy"}}

# Include routers
{router_mounts}
```

CRITICAL: Return JSON with "files": [{{"path": "backend/app/main.py", "content": "..."}}]
"""

    try:
        result = await supervised_agent_call(
            project_id=project_id,
            manager=manager,
            agent_name="Derek",
            step_name="Backend Main",
            base_instructions=main_instructions,
            project_path=project_path,
            user_request=user_request,
            contracts="",
            max_retries=2,
        )

        parsed = result.get("output", {})
        if "files" in parsed and parsed["files"]:
            validated = validate_file_output(parsed, WorkflowStep.BACKEND_MAIN, max_files=1)
            files_written = await persist_agent_output(
                manager, project_id, project_path, validated, WorkflowStep.BACKEND_MAIN
            )
            log("BACKEND", f"Derek generated main.py ({files_written} files)")

        chat_history.append({"role": "assistant", "content": str(parsed)})

    except Exception as e:
        log("BACKEND", f"Failed to generate main.py: {e}")

    # Ensure app package consistency
    ensure_workspace_app_package(project_path)

    return StepResult(
        nextstep=WorkflowStep.TESTING_BACKEND,
        turn=current_turn + 1,
    )
