# app/handlers/testing_backend.py
"""
Step 6: Derek runs backend tests with pytest.

Workflow order: ... → System Integration (5) → Testing Backend (6) → Frontend Integration (7)

Execution-Only Pattern:
- Tests are generated and executed in a single-shot.
- No internal healing or iterative loops.
- Failures result in immediate workflow termination.
"""
import re
from pathlib import Path
from typing import Any, Dict, List

from app.core.types import ChatMessage, StepResult
from app.core.step_outcome import StepExecutionResult, StepOutcome
from app.core.constants import WorkflowStep
from app.handlers.base import broadcast_status, broadcast_agent_log
from app.core.logging import log
from app.tools import run_tool
from app.llm.prompts.derek_testing import DEREK_TESTING_PROMPT

from app.core.constants import PROTECTED_SANDBOX_FILES
from app.utils.entity_discovery import discover_primary_entity, extract_all_models_from_models_py

# Phase 0: Failure Boundary Enforcement
from app.core.failure_boundary import FailureBoundary
from app.core.file_writer import safe_write_llm_files
from app.core.step_invariants import StepInvariants, StepInvariantError


# Constants from legacy
MAX_FILES_PER_STEP = 10
MAX_FILE_LINES = 400



# Centralized entity discovery for dynamic fallback
from app.utils.entity_discovery import extract_entity_from_request as _extract_entity_from_request



def render_contract_tests(
    template_path: Path,
    contracts_md: str,
    output_path: Path,
    entity_name: str,
    entity_plural: str
) -> None:
    """
    Render the template deterministically.
    Source of truth: architecture.md (used to verify scope, implemented via template)
    
    Rules:
    NO Derek
    NO healing
    NO mutation
    Pure string rendering
    """
    if not template_path.exists():
        log("TESTING", f"❌ ERROR: Contract template not found at {template_path}")
        raise FileNotFoundError(f"Missing mandatory test template: {template_path}")

    template = template_path.read_text(encoding="utf-8")
    
    # Deterministic rendering
    rendered = template.replace("{{ENTITY}}", entity_name)
    rendered = rendered.replace("{{ENTITY_PLURAL}}", entity_plural)
    rendered = rendered.replace("{{ENTITY|upper}}", entity_name.upper())
    rendered = rendered.replace("{{ENTITY_PLURAL|upper}}", entity_plural.upper())
    
    output_path.write_text(rendered, encoding="utf-8")
    # log("TESTING", f"✅ Rendered deterministic contract tests to {output_path.name}")



async def _generate_tests_from_template(
    manager: Any,
    project_id: str,
    project_path: Path,
    user_request: str,
    primary_entity: str,
    archetype: str,
    provider: str,
    model: str,
    branch: Any,
) -> bool:
    """
    Generate backend tests from template at the START of testing step.
    
    Flow:
    1. Read the test template (from Golden Seed)
    2. Call Derek to generate project-specific tests based on template
    3. Write the test file
    4. Return True if tests were generated successfully
    
    Derek ALWAYS generates capability tests, while contract tests are deterministic.
    """
    from app.supervision import supervised_agent_call
    from app.orchestration.utils import pluralize
    from app.handlers.base import broadcast_agent_log
    
    # Define variables needed throughout the function
    primary_entity_capitalized = primary_entity.capitalize()
    primary_entity_plural = pluralize(primary_entity)
    
    tests_dir = project_path / "backend" / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    
    # CLEANUP: Remove legacy test_api.py to avoid confusion/duplication
    legacy_test_file = tests_dir / "test_api.py"
    if legacy_test_file.exists():
        log("TESTING", "🧹 Cleaning up legacy backend/tests/test_api.py")
        legacy_test_file.unlink()
    
    # 1. Render Contract Tests Deterministically (Step 0-2)
    # Template is seeded by workflow/engine.py to backend/tests/
    template_path = project_path / "backend" / "tests" / "test_contract_api.template"
    if not template_path.exists():
        # Fallback: Try the source templates directory for local dev
        from app.core.config import settings
        template_path = settings.paths.base_dir / "backend" / "templates" / "backend" / "seed" / "tests" / "test_contract_api.template"

    contract_output = tests_dir / "test_contract_api.py"
    
    # Read architecture/backend.md for strict adherence (Architecture Bundle)
    arch_backend_path = project_path / "architecture" / "backend.md"
    arch_legacy_path = project_path / "architecture.md"
    
    
    if arch_backend_path.exists():
        contracts_md = arch_backend_path.read_text(encoding="utf-8")
    else:
        contracts_md = ""
    
    # Render
    render_contract_tests(
        template_path=template_path,
        contracts_md=contracts_md,
        output_path=contract_output,
        entity_name=primary_entity,
        entity_plural=pluralize(primary_entity)
    )
    
    # 2. Generate Capability Tests via Derek (Step 3)
    # log("TESTING", f"📝 Derek generating capability tests for entity: {primary_entity}")

    # Read the actual models.py to get entity schema
    models_content = ""
    models_path = project_path / "backend" / "app" / "models.py"
    if models_path.exists():
        try:
            models_content = models_path.read_text(encoding="utf-8")
        except Exception:
            pass
    
    # Derek prompt with CRITICAL markers-first instruction
    derek_prompt = f"""
═══════════════════════════════════════════════════════
🚨 CRITICAL OUTPUT ORDER (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════

You MUST begin your response with EXACTLY:

<<<FILE path="backend/tests/test_capability_api.py">>>

IMMEDIATELY. Your FIRST 3 characters MUST be: <<<

❌ Do NOT write ANYTHING before this marker.
❌ Do NOT explain, plan, or think first.

Close with: <<<END_FILE>>>

═══════════════════════════════════════════════════════
📏 TEST SIZE RULES (MANDATORY)
═══════════════════════════════════════════════════════

- Maximum 80-100 lines total
- 1 happy-path test per endpoint ONLY
- NO redundant edge cases
- NO comments unless required
- NO fixtures unless reused 3+ times
- Use inline test data

═══════════════════════════════════════════════════════
📋 ACTUAL ENTITY SCHEMA (USE THIS!)
═══════════════════════════════════════════════════════

{models_content if models_content else "No models.py found - use generic test data"}

⚠️ CRITICAL: Look at the {primary_entity.capitalize()} model above.
Use the ACTUAL fields defined there for your test payloads.
DO NOT assume fields like 'title' or 'description' unless you see them.

═══════════════════════════════════════════════════════
📋 TASK
═══════════════════════════════════════════════════════

Generate capability tests based on the user prompt.

Rules:
- You MUST NOT redefine base CRUD routes
- You MAY assert additional endpoints only if implied by the prompt
- These tests complement contract tests (don't duplicate CRUD)
- Use ACTUAL fields from models.py above in your test payloads
- Use faker for realistic test data that matches field types

User Request: {user_request}
Primary Entity: {primary_entity}
Archetype: {archetype}

Generate ONLY: backend/tests/test_capability_api.py

🚨 FORBIDDEN (CRITICAL):
- ❌ Do NOT generate backend/app/models.py
- ❌ Do NOT redefine database schemas
- ❌ Do NOT write any logic outside the tests/ directory
- ❌ CRITICAL: The router prefix is `/api/{primary_entity_plural}`. DO NOT ADD `/v1` or `/v2`.
- ❌ Example: use `/api/leads`, NOT `/api/v1/leads`.
- ❌ Do NOT output the model content I provided for reference.
- ❌ Do NOT use Enum classes in assertions (use strings like "New", not Status.New)

Use the provided schema for REFERENCE ONLY to write valid test payloads.
"""

    try:
        await broadcast_agent_log(
            manager,
            project_id,
            "AGENT:Derek",
            f"📝 Generating test file for {primary_entity_capitalized}..."
        )
        
        # Extract retry/override context
        temperature_override = branch.intent.get("temperature_override")
        is_retry = branch.intent.get("is_retry", False)

        result = await supervised_agent_call(
            project_id=project_id,
            manager=manager,
            agent_name="Derek",
            step_name="Test File Generation",
            base_instructions=derek_prompt,
            project_path=project_path,
            user_request=user_request,
            contracts=contracts_md,
            temperature_override=temperature_override,
            is_retry=is_retry,
        )
        
        parsed = result.get("output", {})
        files = parsed.get("files", [])
        
        # ═══════════════════════════════════════════════════════════════════════════
        # PHASE-0/1: Orchestrator handles empty file detection
        # Handler just processes whatever files were generated
        # ═══════════════════════════════════════════════════════════════════════════
        
        if not files:
            log("TESTING", "⚠️ Derek did not generate test files")
            return False
        
        # Auto-correct paths for test files
        for file_obj in files:
            path_str = str(file_obj.get("path", ""))
            normalized_path = path_str.replace("\\", "/")
            if not normalized_path.startswith("backend/"):
                filename = normalized_path.split("/")[-1]
                new_path = f"backend/tests/{filename}"
                file_obj["path"] = new_path
                log("TESTING", f"⚠️ Auto-corrected path from {path_str} to {new_path}")
        
        
        # Write the test file
        written = await safe_write_llm_files(
            manager=manager,
            project_id=project_id,
            project_path=project_path,
            files=files,
            step_name="Test File Generation",
        )
        
        if written > 0:
            # log("TESTING", f"✅ Derek generated {written} test file(s)")
            return True
        
        log("TESTING", "❌ Test file writing failed")
        return False
        
    except Exception as e:
        # Report failure - ArborMind decides what to do next
        log("TESTING", f"❌ Test generation failed: {e}")
        return False



@FailureBoundary.enforce
async def step_testing_backend(branch) -> StepResult:
    """
    Derek tests backend using sandbox.
    
    ONE SHOT POLICY:
    - Executes ONCE per attempt.
    - No internal retry loops.
    - No internal self-healing.
    - If it fails, it reports failure to ArborMind.
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
    
    from app.orchestration.utils import broadcast_to_project

    await broadcast_status(
        manager,
        project_id,
        WorkflowStep.TESTING_BACKEND,
        f"Derek running backend tests...",
        6,
        9,
    )

    log(
        "STATUS",
        f"[{WorkflowStep.TESTING_BACKEND}] Starting backend sandbox tests for {project_id}",
    )

    log("TESTING", "🔄 Backend testing started (One Shot)")

    # Ensure tests directory exists so Docker doesn't create it as root
    (project_path / "backend/tests").mkdir(parents=True, exist_ok=True)

    last_stdout: str = ""
    last_stderr: str = ""
    
    # V3: Cumulative token tracking across all LLM calls in this step
    step_token_usage = {"input": 0, "output": 0}
    
    # 🔒 INVARIANT 1: Only ONE contract expansion per run to prevent explosion
    expansions_performed = 0

    # ═══════════════════════════════════════════════════════
    # CRITICAL: Run tests FIRST before calling Derek
    # This ensures Derek has actual failure context, not guessing
    # ═══════════════════════════════════════════════════════
    
    # Get entity context for Derek
    from app.orchestration.state import WorkflowStateManager
    from app.orchestration.utils import pluralize
    
    intent = await WorkflowStateManager.get_intent(project_id) or {}
    entities = intent.get("entities", [])
    
    # Use centralized discovery as fallback with dynamic last-resort
    # BUG FIX: For testing, prefer actual models from models.py over
    # discover_primary_entity which may return wrong entity from mock.js
    if entities:
        primary_entity = entities[0]
    else:
        # First try to get actual models from models.py
        actual_models = extract_all_models_from_models_py(project_path)
        if actual_models:
            primary_entity = actual_models[0].lower()
        else:
            # Fallback to discover_primary_entity
            _, entity_singular = discover_primary_entity(project_path)  # Returns (plural, singular)
            if entity_singular:
                primary_entity = entity_singular
            else:
                # Dynamic last resort: extract from user request
                primary_entity = _extract_entity_from_request(user_request) or "entity"
    
    primary_entity_plural = pluralize(primary_entity)
    
    # Get archetype for test guidance
    archetype = (intent.get("archetypeRouting") or {}).get("top") or "general"
    
    # ═══════════════════════════════════════════════════════
    # STEP 1: Derek generates tests from template FIRST
    # Derek ALWAYS creates project-specific tests using the template
    # ═══════════════════════════════════════════════════════
    tests_generated = await _generate_tests_from_template(
        manager=manager,
        project_id=project_id,
        project_path=project_path,
        user_request=user_request,
        primary_entity=primary_entity,
        archetype=archetype,
        provider=provider,
        model=model,
        branch=branch,
    )
    
    
    if not tests_generated:
        # ═══════════════════════════════════════════════════════════════
        # PHASE-1: Testing is NON-FATAL (verification, not requirement)
        # ═══════════════════════════════════════════════════════════════
        log("TESTING", "⚠️ Derek could not generate tests from template - continuing workflow (non-fatal)")
        log("TESTING", "📊 Phase-1 Policy: Tests are verification signals, not blocking requirements")
        
        # Continue workflow - tests are optional in Phase-1
        # ArborMind will observe this as a signal
        return StepResult(
            nextstep=WorkflowStep.FRONTEND_INTEGRATION,
            turn=7,
            status="ok",  # Non-fatal success
            data={
                "tier": "no_tests",
                "test_status": "generation_failed",
                "message": "Test generation failed - proceeding without tests (Phase-1 policy)"
            },
            token_usage=step_token_usage,
        )
    
    
    # Read existing test file to show Derek what's expected
    # Read existing test file to show Derek what's expected
    test_file_path = project_path / "backend/tests/test_capability_api.py"
    test_file_exists = test_file_path.exists()
    existing_test_content = ""
    
    # Build archetype-specific test instructions
    if archetype in ("admin_dashboard", "project_management"):
        test_instructions = f"""
Write pytest tests that focus on:

- CRUD for /api/{primary_entity_plural}
- Filtering by status via query param (?status=open)
- Pagination parameters (?page=1&limit=20)
- Response envelope: {{ "data": [...], "total": int, "page": int, "limit": int }}
- 404 behaviour when accessing missing {primary_entity}.
"""
    elif archetype == "ecommerce_store":
        test_instructions = """
Write pytest tests for product/order style endpoints:

- GET /api/products returns list envelope with "data" and "total".
- POST /api/products can create a product with price & currency.
- GET /api/products/{id} returns 404 for non-existent product.
- All responses follow standardized format from architecture.md
"""
    elif archetype == "saas_app":
        test_instructions = """
Write pytest tests that ensure tenant scoping:

- CRUD endpoints respect organization_id / tenant_id.
- Attempting to fetch data from another organization returns empty or 404.
- Response format follows the standard envelope.
"""
    else:
        test_instructions = """
Write basic CRUD tests for the primary entity router:

- List, create, get-by-id, delete.
- 404 on unknown id.
- Response envelopes: { "data": <object> } for single, { "data": [...], "total": int } for lists.
"""
    
    if test_file_exists:
        test_instructions = f"""
EXISTING TEST FILE: backend/tests/test_capability_api.py
DO NOT create new test files - fix the routers/models to make existing tests pass.
Refer to backend/tests/test_contract_api.py for immutable contracts.

Additional archetype guidance for {archetype}:
{test_instructions}
"""
        try:
            existing_test_content = test_file_path.read_text(encoding="utf-8")[:1500]
        except Exception:
            pass
    else:
        test_instructions = f"""
⚠️ MISSING TEST FILE: backend/tests/test_capability_api.py
You MUST create this file. 
DO NOT duplicate tests from test_contract_api.py (CRUD).
Focus on business logic, filters, and edge cases.

Archetype-specific requirements for {archetype}:
{test_instructions}
"""
        existing_test_content = "(No tests found - you must create them)"

    entity_context = f"""
═══════════════════════════════════════════════════════
PROJECT CONTEXT
═══════════════════════════════════════════════════════

This project is about: {user_request[:200]}

PRIMARY ENTITY: {primary_entity}
ARCHETYPE: {archetype}
- Router: backend/app/routers/{primary_entity_plural}.py
- Model: backend/app/models.py (class {primary_entity.capitalize()})

DO NOT create routers for other entities (e.g., products, users) unless they already exist.
Focus on fixing the {primary_entity} router and related models.

{test_instructions}
"""

    # ------------------------------------------------------------
    # ONE SHOT EXECUTION (No Loop)
    # ------------------------------------------------------------
    log("TESTING", "🚀 Running backend tests in sandbox (One Shot Policy)...")
    try:
        sandbox_result = await run_tool(
            name="sandboxexec",
            args={
                "project_id": project_id,
                "service": "backend",
                "command": "pytest -q",
                "start_services": ["backend"],
                "timeout": 300,
                "force_rebuild": True,  # Ensure Docker rebuilds to pick up newly wired routers
            },
        )
        last_stdout = sandbox_result.get("stdout", "") or ""
        last_stderr = sandbox_result.get("stderr", "") or ""
        
        if sandbox_result.get("success"):
            log("TESTING", "✅ Backend tests PASSED on first run")
            return StepResult(
                nextstep=WorkflowStep.FRONTEND_INTEGRATION,
                turn=7,  # Testing backend is step 6
                status="ok",
                data={"tier": "sandbox", "attempt": 1, "test_status": "passed"},
                token_usage=step_token_usage,
            )

        # ------------------------------------------------------------
        # PHASE 1: NON-FATAL FAILURE
        # ------------------------------------------------------------
        log("TESTING", "⚠️ Backend tests failed. Continuing branch (non-fatal)")
        log("TESTING", f"📋 Test stdout:\n{last_stdout[:2000]}")
        log("TESTING", f"📋 Test stderr:\n{last_stderr[:2000]}")
        return StepResult(
            nextstep=WorkflowStep.FRONTEND_INTEGRATION,
            turn=7,
            status="ok", # Non-fatal success
            data={
                "tier": "sandbox", 
                "test_status": "failed",
                "stdout": last_stdout[:1000],
                "stderr": last_stderr[:1000]
            },
            token_usage=step_token_usage,
        )

    except Exception as e:
        log("TESTING", f"⚠️ Sandbox execution encountered an error (non-fatal): {e}")
        return StepResult(
            nextstep=WorkflowStep.FRONTEND_INTEGRATION,
            turn=7,
            status="ok",
            data={"error": str(e), "test_status": "error"},
            token_usage=step_token_usage,
        )






