# app/handlers/frontend_mock.py
"""
Step 2: Derek creates frontend with MOCK DATA first.


This follows the GenCode Studio pattern:
- Create frontend-first with mock data for immediate "aha moment"
- All mock data goes in src/data/mock.js
- Components are functional but use local state
- Later, the backend will be built based on the architecture contract.
"""
from pathlib import Path
from app.core.failure_boundary import FailureBoundary
from typing import Any, List

from app.core.types import ChatMessage, StepResult
from app.core.constants import WorkflowStep
from app.core.exceptions import RateLimitError
from app.handlers.base import broadcast_status
from app.core.logging import log
from app.orchestration.state import WorkflowStateManager
from app.supervision import supervised_agent_call
from app.orchestration.utils import pluralize
from app.utils.entity_discovery import discover_primary_entity, discover_all_entities
# Phase 7: Validated replacement - simplify logic rather than importing guidance
from app.utils.component_copier import copy_used_components
from app.core.file_writer import validate_file_output, persist_agent_output
from app.core.step_invariants import StepInvariants, StepInvariantError


# Centralized entity discovery for dynamic fallback



# Constants
MAX_FILES_PER_STEP = 12  # Increased to 12 for components + config
MAX_FILE_LINES = 400






@FailureBoundary.enforce
async def step_frontend_mock(branch) -> StepResult:
    """
    Step 2: Derek generates frontend with MOCK DATA first.
    
    This creates the immediate "aha moment" for users - they see a working
    UI before any backend is built. All data is mocked in mock.js.
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
    
    # V3: Track token usage for cost reporting
    step_token_usage = None
    await broadcast_status(
        manager,
        project_id,
        WorkflowStep.FRONTEND_MOCK,
        f"Derek implementing UI...",
        2,
        9,
    )

    # Architecture Bundle: Frontend context ONLY (no backend/overview to prevent scope leak)
    # Try cache first (V2.1: Architecture caching for performance)
    from app.orchestration.state import WorkflowStateManager
    arch_cache = await WorkflowStateManager.get_architecture_cache(project_id)
    
    if "frontend" in arch_cache:
        architecture = arch_cache["frontend"]
        log("FRONTEND_MOCK", "📦 Using cached architecture (frontend.md)")
    else:
        # Fallback to disk read (shouldn't happen in normal flow)
        try:
            frontend_md = (project_path / "architecture" / "frontend.md").read_text(encoding="utf-8")
            architecture = frontend_md
            log("FRONTEND_MOCK", "⚠️ Cache miss - read frontend.md from disk")
        except Exception:
            log("FRONTEND_MOCK", "❌ Architecture file (frontend.md) missing or unreadable.")
            architecture = "No architecture found - use best judgment."

    # Read package.example.json to guide Derek
    package_json_ref = ""
    playwright_config_ref = ""
    try:
        ref_path = project_path / "frontend/reference/package.example.json"
        if ref_path.exists():
            package_json_ref = ref_path.read_text(encoding="utf-8")
            
        pw_path = project_path / "frontend/reference/playwright.config.example.js"
        if pw_path.exists():
            playwright_config_ref = pw_path.read_text(encoding="utf-8")
    except Exception:
        pass

    intent = await WorkflowStateManager.get_intent(project_id) or {}
    # Phase-1: ARCHITECTURE IS TRUTH - Discover authoritative entities
    all_entities = discover_all_entities(project_path)
    if not all_entities:
        log("FRONTEND_MOCK", "❌ No domain entities defined in architecture - fatal grounding error")
        raise StepInvariantError("No domain entities defined in architecture. Architecture must be fixed first.")
    
    primary_entity = all_entities[0].name
    expected_entities_str = ", ".join([e.name for e in all_entities])
    
    primary_entity_capitalized = primary_entity.capitalize()
    primary_entity_plural = pluralize(primary_entity)
    domain = intent.get("domain", "general")
    
    # ═══════════════════════════════════════════════════════
    # ARCHETYPE-AWARE GENERATION (Key for diverse UI patterns)
    # ═══════════════════════════════════════════════════════
    archetype_routing = intent.get("archetypeRouting", {})
    detected_archetype = archetype_routing.get("top", "admin_dashboard") if isinstance(archetype_routing, dict) else "admin_dashboard"
    
    
    # Nuclear Lockdown: Strip any "Backend" or "Model" terminology from reference 
    # to prevent Derek from regressing to full-stack thinking.
    ui_contract = architecture.replace("Backend", "UI-API Structure").replace("Model", "Data Type")
    
    # GROUNDING CHECK: If UI contract is effectively empty or contains No Architecture, stop.
    if not ui_contract or "No architecture found" in ui_contract:
        log("FRONTEND_MOCK", "❌ CRITICAL: UI Contract is empty. Architecture must be generated first.")
        raise StepInvariantError("No frontend architecture found in cache or disk. Victoria must output architecture first.")

    if len(ui_contract) > 2500:
        ui_contract = ui_contract[:2500] + "... (truncated)"
    
    # Get archetype-specific UI guidance (Simplified)
    archetype_guidance = f"""
    ARCHETYPE: {detected_archetype}
    DOMAIN: {domain}
    PRIMARY ENTITY: {primary_entity}
    EXPECTED DOMAIN ENTITIES (AUTHORITATIVE): {expected_entities_str}
    
    Implement a UI that follows best practices for this archetype.
    
    🚨 CRITICAL SEMANTIC CONSTRAINT (NON-NEGOTIABLE):
    You MUST implement UI ONLY.
    
    ❌ FORBIDDEN:
    - NO backend/app/models.py
    - NO backend/app/routers/*.py
    - NO backend/ anything.
    - NO re-interpreting backend schemas.
    - NO trying to "help" by writing the database layer.

    If you write a backend file, your output will be discarded and the run will fail.
    """
    
    # Pre-training patterns (Empty for now - will come from ArborMind learning later)
    pattern_hints = ""
    
    # log("FRONTEND_MOCK", f"🎨 Generating UI for archetype: {detected_archetype}")
    
    # Extract app title from user request
    app_title = user_request.split(".")[0][:50] if "." in user_request else user_request[:50]

    # FRONTEND-FIRST MOCK PROMPT (GenCode Studio Pattern) - CUSTOMIZATION FOCUSED
    frontend_mock_instructions = f"""
YOU ARE EXECUTING STEP: FRONTEND_MOCK

Allowed paths:
- frontend/**

Forbidden paths:
- backend/**
- backend/app/models.py
- backend/app/routers/**
- backend/tests/**

Expected artifacts:
- React UI (JSX/TSX)
- Mock data
- UI components (Business Logic / Composition only)

You must generate FRONTEND FILES ONLY.
If you generate ANY backend file, output is INVALID.

❌ UI LIBRARY INSTRUCTION (CRITICAL):
- DO NOT implement Shadcn UI components (Card, Button, Input, Table, etc.)
- DO NOT generate files like `frontend/src/components/ui/button.jsx`
- ASSUME they exist and import them from `@/components/ui/...`
- ONLY implement custom business-logic components (e.g., `TaskBoard`, `UserList`).
"""

    # Extract retry/override context
    temperature_override = branch.intent.get("temperature_override")
    is_retry = branch.intent.get("is_retry", False)

    # Use supervised call - no retries, ArborMind handles that
    result = await supervised_agent_call(
        project_id=project_id,
        manager=manager,
        agent_name="Derek",
        step_name="Frontend (Mock Data)",
        base_instructions=frontend_mock_instructions,
        project_path=project_path,
        user_request=user_request,
        contracts="",  # No contracts yet - this is frontend-first
        temperature_override=temperature_override,
        is_retry=is_retry,
    )
    
    # V3: Extract token usage for cost tracking
    step_token_usage = result.get("token_usage")
    
    parsed = result.get("output", {})
    files_written = 0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # OUTPUT SCOPE VALIDATION (Step-Scoped Expected Artifacts)
    # ═══════════════════════════════════════════════════════════════════════════
    # Validate that Derek only generated files within his permitted scope
    # This is DIFFERENT from input filtering - we're checking OUTPUT here
    # ═══════════════════════════════════════════════════════════════════════════
    if "files" in parsed and parsed["files"]:
        for file_obj in parsed["files"]:
            path = file_obj.get("path", "")
            
            # Normalize path separators
            normalized_path = path.replace("\\", "/")
            
            # FORBIDDEN: Backend files in frontend step
            if normalized_path.startswith("backend/"):
                raise StepInvariantError(
                    f"SCOPE VIOLATION: frontend_mock attempted to generate backend file: {path}. "
                    f"Only frontend/ files are allowed in this step. "
                    f"Backend files will be generated in backend_models and backend_routers steps."
                )
            
            # Auto-correct common path mistakes (Agent often forgets frontend/ prefix)
            # Use anchored check to avoid double-processing or corruption
            if not normalized_path.startswith("frontend/"):
                is_frontend_core = (
                    normalized_path.startswith("src/") or 
                    normalized_path.startswith("public/") or 
                    normalized_path in ["package.json", "vite.config.js", "tailwind.config.js", "playwright.config.js"]
                )
                if is_frontend_core:
                    old_path = str(path)
                    new_path = f"frontend/{normalized_path}"
                    file_obj["path"] = new_path 
                    normalized_path = new_path
                    log("FRONTEND_MOCK", f"⚠️ Auto-corrected path from {old_path} to {new_path}")
            
            # REQUIRED: Must be frontend files
            if not normalized_path.startswith("frontend/"):
                raise StepInvariantError(
                    f"SCOPE VIOLATION: frontend_mock must ONLY generate files in frontend/ directory. "
                    f"Invalid path: {path}"
                )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE-0/1: Orchestrator handles empty file detection and retry
    # Handler performs validation and testid checks
    # ═══════════════════════════════════════════════════════════════════════════
    try:
        # PREFLIGHT: Check required testids (Relaxed to avoid blocking multi-entity apps)
        required_testids = [
            "page-root",
            "page-title",
            # Entity-specific buttons are checked dynamically in StepInvariants
        ]
        StepInvariants.require_testids(
            parsed,
            "FRONTEND_MOCK",
            required_testids,
            primary_entity=primary_entity,
        )
        
        validated = validate_file_output(parsed, WorkflowStep.FRONTEND_MOCK, max_files=10)
        files_written = await persist_agent_output(
            manager,
            project_id,
            project_path,
            validated,
            WorkflowStep.FRONTEND_MOCK,
        )
        
        if not result.get("approved"):
            log("FRONTEND_MOCK", "⚠️ Rejection from Marcus supervisor (non-fatal)")
            # Still continue - Imperfect behavior > no behavior
            return StepResult(
                nextstep=WorkflowStep.BACKEND_MODELS,
                turn=3,
                status="ok",
                data={"warning": "Supervisor rejection", "error": result.get("error")},
                token_usage=step_token_usage,
            )

        log("FRONTEND_MOCK", f"✅ Frontend mock approved by Marcus ({files_written} files)")
        
        # =========================================================================
        # 📦 JUST-IN-TIME COMPONENT COPYING (Only copy what's needed)
        # =========================================================================
        try:
            copied_count = copy_used_components(project_path)
            log("FRONTEND_MOCK", f"📦 Copied {copied_count} Shadcn components based on imports")
        except Exception as e:
            log("FRONTEND_MOCK", f"⚠️ Component copying failed (non-fatal): {e}")
            
    except StepInvariantError as e:
        log("FRONTEND_MOCK", f"⚠️ Step invariant violated (non-fatal): {e}")
        # Proceed anyway - Signal, not stop
        return StepResult(
            nextstep=WorkflowStep.BACKEND_MODELS,
            turn=3,
            status="ok",
            data={"invariant_error": str(e)},
            token_usage=step_token_usage,
        )
    
    branch.artifacts["frontend_mock_result"] = str(parsed)

    # =========================================================================
    # 🔗 FRONTEND INTEGRATOR (Deterministic Wiring)
    # =========================================================================
    log("FRONTEND", "🔗 Running Frontend Integrator to wire pages...")
    
    app_jsx_path = project_path / "frontend" / "src" / "App.jsx"
    pages_dir = project_path / "frontend" / "src" / "pages"
    
    if app_jsx_path.exists() and pages_dir.exists():
        content = app_jsx_path.read_text(encoding="utf-8")
        
        # Find all page components
        page_files = [f for f in pages_dir.glob("*.jsx")]
        import_lines = []
        route_lines = []
        
        for page in page_files:
            component_name = page.stem # e.g. "HomePage"
            # Import
            import_lines.append(f"import {component_name} from './pages/{component_name}';")
            
            # Route
            if "Home" in component_name:
                    route_lines.append(f'<Route path="/dashboard" element={{<{component_name} />}} />')
            else:
                # Generic route generation strategy
                # e.g. ProjectsPage -> /projects
                route_slug = component_name.lower().replace("page", "")
                route_lines.append(f'<Route path="/{route_slug}" element={{<{component_name} />}} />')

        # Inject
        imports_block = "\n".join(import_lines)
        routes_block = "\n            ".join(route_lines) # Indentation for JSX
        
        if "// @ROUTE_IMPORTS" in content:
            content = content.replace("// @ROUTE_IMPORTS", f"// @ROUTE_IMPORTS\n{imports_block}")
        
        if "{/* @ROUTE_REGISTER" in content:
                content = content.replace(
                    "{/* @ROUTE_REGISTER - Integrator injects new routes here */}", 
                    f"{{/* @ROUTE_REGISTER */}}\n            {routes_block}"
                )
        
        app_jsx_path.write_text(content, encoding="utf-8")
        log("FRONTEND", f"✅ Integrator wired {len(page_files)} pages into App.jsx")

    # Proceed to backend implementation
    return StepResult(
        nextstep=WorkflowStep.BACKEND_MODELS,
        turn=3,
        token_usage=step_token_usage,
    )


