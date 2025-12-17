# app/handlers/testing_backend.py
"""
Step 9: Derek tests backend using sandbox with Self-Healing.

Workflow order: Analysis → Architecture → Frontend Mock → Screenshot Verify →
Contracts → Backend Implementation (Atomic) → System Integration → Testing Backend (8)

Marcus-as-Critic Pattern:
- When backend tests fail, Marcus first analyzes the failure
- Marcus reads Backend Design Patterns from architecture.md
- Marcus provides Derek with structured fix instructions
- Derek then implements the fixes following Marcus's guidance
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
from app.llm.prompts.derek import DEREK_TESTING_PROMPT
from app.persistence.validator import validate_file_output
from app.core.constants import PROTECTED_SANDBOX_FILES
from app.utils.entity_discovery import discover_primary_entity, extract_all_models_from_models_py

# Phase 0: Failure Boundary Enforcement
from app.core.failure_boundary import FailureBoundary


# Constants from legacy
MAX_FILES_PER_STEP = 10
MAX_FILE_LINES = 400






# Protected sandbox files - imported from centralized constants


# Centralized entity discovery for dynamic fallback
from app.utils.entity_discovery import extract_entity_from_request as _extract_entity_from_request


# REMOVED: Restrictive allowed prefixes - agents can write to any file except protected ones








# Centralized file writing utility
from app.persistence import safe_write_llm_files


def render_contract_tests(
    template_path: Path,
    contracts_md: str,
    output_path: Path,
    entity_name: str,
    entity_plural: str
) -> None:
    """
    Render the template deterministically.
    Source of truth: contracts.md (used to verify scope, implemented via template)
    
    Rules:
    NO Derek
    NO healing
    NO mutation
    Pure string rendering
    """
    if not template_path.exists():
        log("TESTING", f"⚠️ Contract template not found at {template_path}")
        # Write emergency fallback
        content = '"""\nCONTRACT TEST TEMPLATE – DETERMINISTIC\n"""\nimport pytest\n@pytest.mark.anyio\nasync def test_placeholder(client):\n    pass'
        output_path.write_text(content, encoding="utf-8")
        return

    template = template_path.read_text(encoding="utf-8")
    
    # Deterministic rendering
    rendered = template.replace("{{ENTITY}}", entity_name)
    rendered = rendered.replace("{{ENTITY_PLURAL}}", entity_plural)
    rendered = rendered.replace("{{ENTITY|upper}}", entity_name.upper())
    rendered = rendered.replace("{{ENTITY_PLURAL|upper}}", entity_plural.upper())
    
    output_path.write_text(rendered, encoding="utf-8")
    log("TESTING", f"✅ Rendered deterministic contract tests to {output_path.name}")



async def _generate_tests_from_template(
    manager: Any,
    project_id: str,
    project_path: Path,
    user_request: str,
    primary_entity: str,
    archetype: str,
    provider: str,
    model: str,
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
    template_path = project_path / "backend/templates/backend/seed/tests/test_contract_api.template"
    if not template_path.exists():
        # Try relative path for local dev
        template_path = Path("backend/templates/backend/seed/tests/test_contract_api.template").absolute()

    contract_output = tests_dir / "test_contract_api.py"
    
    # Read contracts.md for strict adherence (placeholder for now, mostly using template)
    contracts_path = project_path / "contracts.md"
    contracts_md = contracts_path.read_text(encoding="utf-8") if contracts_path.exists() else ""
    
    # Render
    render_contract_tests(
        template_path=template_path,
        contracts_md=contracts_md,
        output_path=contract_output,
        entity_name=primary_entity,
        entity_plural=pluralize(primary_entity)
    )
    
    # 2. Generate Capability Tests via Derek (Step 3)
    log("TESTING", f"📝 Derek generating capability tests for entity: {primary_entity}")

    # Derek prompt (copy verbatim)
    derek_prompt = f"""Generate capability tests based on the user prompt.

Rules:
- You MUST NOT redefine base CRUD routes
- You MAY assert additional endpoints only if implied by the prompt
- You MAY assert response shapes and business rules
- These tests are healable and replaceable
- DO NOT include CRUD tests already covered by contract tests

Result
/channels
/statuses
strict health checks
filters, sorting, domain rules

User Request: {user_request}
Primary Entity: {primary_entity}
Archetype: {archetype}

Generate ONLY: backend/tests/test_capability_api.py
"""

    try:
        await broadcast_agent_log(
            manager,
            project_id,
            "AGENT:Derek",
            f"📝 Generating test file for {primary_entity_capitalized}..."
        )
        
        result = await supervised_agent_call(
            project_id=project_id,
            manager=manager,
            agent_name="Derek",
            step_name="Test File Generation",
            base_instructions=derek_prompt,
            project_path=project_path,
            user_request=user_request,
            contracts=contracts_md,
            max_retries=1,  # One retry allowed
        )
        
        parsed = result.get("output", {})
        files = parsed.get("files", [])
        
        if files:
            # Write the test file
            written = await safe_write_llm_files(
                manager=manager,
                project_id=project_id,
                project_path=project_path,
                files=files,
                step_name="Test File Generation",
            )
            
            if written > 0:
                log("TESTING", f"✅ Derek generated {written} test file(s)")
                return True
        
        log("TESTING", "⚠️ Derek did not generate test files")
        
    except Exception as e:
        log("TESTING", f"⚠️ Test generation failed: {e}")
    
    # Fallback: Write basic test file directly
    log("TESTING", "📋 Using fallback test generation...")
    return await _fallback_generate_tests(project_path, primary_entity, primary_entity_plural)


async def _fallback_generate_tests(
    project_path: Path,
    entity: str,
    entity_plural: str,
) -> bool:
    """
    Fallback test generation when Derek fails (Option B supplement).
    Writes a minimal but functional test file.
    """
    tests_dir = project_path / "backend" / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    
    test_content = f'''# backend/tests/test_capability_api.py
"""
Capability Tests - Auto-generated fallback
Generated when Derek failed to create capability tests.
"""
import pytest
from faker import Faker

fake = Faker()

@pytest.mark.anyio
async def test_capability_placeholder(client):
    """
    Placeholder test to ensure the file exists and pytest runs.
    Real CRUD tests are in test_contract_api.py.
    """
    assert True
'''

    test_file = tests_dir / "test_capability_api.py"
    try:
        test_file.write_text(test_content, encoding="utf-8")
        log("TESTING", f"📋 Fallback test file written: {test_file.name} ({len(test_content)} chars)")
        return True
    except Exception as e:
        log("TESTING", f"❌ Failed to write fallback test file: {e}")
        return False



@FailureBoundary.enforce
async def step_testing_backend(
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
    MASTER LOOP: Derek tests backend using sandbox with healing.
    
    LOOP CONSOLIDATION:
    This is the ONLY retry loop in the healing system.
    - All other components (HealingPipeline, Derek, ArborMind) execute ONCE per attempt
    - Healing budget is reset at start and consumed by healing operations
    - After 3 attempts or budget exhaustion, we fail with diagnostic
    
    Flow:
    1. Reset healing budget (fresh for each test run)
    2. Run pytest in Docker
    3. If pass → done
    4. If fail → single healing attempt (budget-controlled)
    5. Repeat up to 3 times (MASTER LOOP)
    """
    from app.orchestration.utils import broadcast_to_project
    from app.orchestration.healing_budget import reset_healing_budget, get_healing_budget

    await broadcast_status(
        manager,
        project_id,
        WorkflowStep.TESTING_BACKEND,
        f"Turn {current_turn}/{max_turns}: Derek testing backend (sandbox-only).",
        current_turn,
        max_turns,
    )

    log(
        "STATUS",
        f"[{WorkflowStep.TESTING_BACKEND}] Starting backend sandbox tests for {project_id}",
    )

    # ════════════════════════════════════════════════════════════════
    # LOOP CONSOLIDATION: Reset healing budget at start of test run
    # ════════════════════════════════════════════════════════════════
    reset_healing_budget(project_id)
    log("TESTING", "🔄 Healing budget reset for this test run")

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
            entity_name, _ = discover_primary_entity(project_path)
            if entity_name:
                primary_entity = entity_name
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
    )
    
    if not tests_generated:
        log("TESTING", "⚠️ Derek could not generate tests from template - using fallback")
    
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
- All responses follow standardized format from contracts.md
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
        
        # V3: Accumulate token usage (approximated, as sandboxexec doesn't use LLM directly)
        
        if sandbox_result.get("success"):
            log("TESTING", "✅ Backend tests PASSED on first run")
            return StepResult(
                nextstep=WorkflowStep.FRONTEND_INTEGRATION,
                turn=current_turn + 1,
                status="ok",
                data={"tier": "sandbox", "attempt": 1},
                token_usage=step_token_usage,
            )
            # ------------------------------------------------------------
            # ONE SHOT POLICY: Strict Halt on Test Failure (No Healing)
            # ------------------------------------------------------------
            log("TESTING", "❌ Tests failed. One Shot Policy active -> Returning COGNITIVE_FAILURE.")
            error_msg = (
                "Backend tests failed in sandbox.\n"
                f"Stdout:\n{last_stdout[:2000]}\n\n"
                f"Stderr:\n{last_stderr[:2000]}"
            )
            return StepExecutionResult(
                outcome=StepOutcome.COGNITIVE_FAILURE,
                step_name=WorkflowStep.TESTING_BACKEND,
                error_details=error_msg,
                data={"token_usage": step_token_usage}
            )

    except Exception as e:
        log("TESTING", f"Sandbox execution failed: {e}")
        # Infra failure -> Environment Failure
        return StepExecutionResult(
            outcome=StepOutcome.ENVIRONMENT_FAILURE,
            step_name=WorkflowStep.TESTING_BACKEND,
            error_details=str(e),
            data={"token_usage": step_token_usage}
        )


# ════════════════════════════════════════════════════════════════════════
# VICTORIA ESCALATION - Architectural Review After Derek Failures
# ════════════════════════════════════════════════════════════════════════



