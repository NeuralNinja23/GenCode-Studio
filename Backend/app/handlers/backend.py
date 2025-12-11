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

# Centralized entity discovery for dynamic fallback
from app.utils.entity_discovery import discover_primary_entity



# Constants from legacy
MAX_FILES_PER_STEP = 5
MAX_FILE_LINES = 400


from app.persistence.validator import validate_file_output
from app.orchestration.utils import pluralize


def _extract_entity_from_request(user_request: str) -> str:
    """
    Dynamically extract a potential entity name from the user request.
    
    Uses common patterns like "manage X", "X app", "create X" to identify entities.
    Returns None if no clear entity can be extracted.
    """
    import re
    
    if not user_request:
        return None
    
    request_lower = user_request.lower()
    
    # Common patterns to extract entity names
    patterns = [
        r'(?:manage|track|create|build|store|list)\s+(\w+)',  # manage tasks, track bugs
        r'(\w+)\s+(?:app|application|manager|tracker|system)',  # task app, bug tracker
        r'(?:a|an)\s+(\w+)\s+(?:management|tracking|listing)',  # a task management
    ]
    
    skip_words = {'the', 'a', 'an', 'my', 'your', 'web', 'full', 'stack', 'simple', 'basic', 'new'}
    
    def singularize(word: str) -> str:
        """Simple singularization that handles common patterns."""
        word = word.lower().strip()
        # Handle special cases first
        if word.endswith('ies') and len(word) > 4:  # categories -> category
            return word[:-3] + 'y'
        if word.endswith('sses'):  # classes -> class
            return word[:-2]
        if word.endswith('ches') or word.endswith('shes'):  # watches -> watch
            return word[:-2]
        if word.endswith('xes') or word.endswith('zes'):  # boxes -> box
            return word[:-2]
        if word.endswith('s') and len(word) > 2 and not word.endswith('ss'):  # notes -> note
            return word[:-1]
        return word
    
    for pattern in patterns:
        match = re.search(pattern, request_lower)
        if match:
            candidate = match.group(1)
            if candidate not in skip_words and len(candidate) > 2:
                return singularize(candidate)
    
    return None



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
   - Include all CRUD operations
   
2. **backend/app/routers/{primary_entity}s.py** (FastAPI Router)
   - CRUD Endpoints using the Model you just wrote
   - Import `from app.models import {primary_entity_capitalized}`
   - Include proper error handling

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
        
        import re
        
        # Inject Imports - Replace ENTIRE marker line (not just prefix)
        # This prevents leaving " - DO NOT REMOVE THIS LINE" as orphaned code
        if "# @ROUTER_IMPORTS" in content:
            content = re.sub(
                r'^# @ROUTER_IMPORTS.*$',
                f"# @ROUTER_IMPORTS\n{imports_block.rstrip()}",
                content,
                flags=re.MULTILINE
            )
        elif imports_block not in content:
            content = f"{imports_block}\n{content}"
            
        # Inject Routes - Replace ENTIRE marker line
        if "# @ROUTER_REGISTER" in content:
            content = re.sub(
                r'^# @ROUTER_REGISTER.*$',
                f"# @ROUTER_REGISTER\n{routes_block.rstrip()}",
                content,
                flags=re.MULTILINE
            )
        elif routes_block not in content:
            content += f"\n{routes_block}"
            
        main_py_path.write_text(content, encoding="utf-8")
        log("BACKEND", "✅ Main.py wired successfully.")
        
    ensure_workspace_app_package(project_path)
    
    return StepResult(
        nextstep=WorkflowStep.TESTING_BACKEND,
        turn=current_turn + 1,
    )
