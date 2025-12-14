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
from app.core.constants import WorkflowStep
from app.handlers.base import broadcast_status, broadcast_agent_log
from app.core.logging import log
from app.tools import run_tool
from app.llm.prompts.derek import DEREK_TESTING_PROMPT
from app.persistence.validator import validate_file_output
from app.core.constants import PROTECTED_SANDBOX_FILES
from app.utils.entity_discovery import discover_primary_entity


# Constants from legacy
MAX_FILES_PER_STEP = 10
MAX_FILE_LINES = 400






# Protected sandbox files - imported from centralized constants


# Centralized entity discovery for dynamic fallback
from app.utils.entity_discovery import extract_entity_from_request as _extract_entity_from_request


# REMOVED: Restrictive allowed prefixes - agents can write to any file except protected ones


def _has_routing_failures(stdout: str, stderr: str, entity_plural: str) -> bool:
    """
    Detect if test failures are due to routing/integration issues (404s).
    
    Args:
        stdout: Test output stdout
        stderr: Test output stderr
        entity_plural: Plural form of the primary entity
    
    Returns:
        True if 404 routing failures detected
    """
    import re
    
    combined_output = (stdout + "\n" + stderr).lower()
    
    # Pattern 1: Direct 404 assertions on entity endpoints
    if re.search(rf'assert 404 == 200.*?/api/{entity_plural}', combined_output):
        return True
    
    # Pattern 2: Generic 404 on entity routes
    if f"/api/{entity_plural}" in combined_output and "404" in combined_output:
        return True
    
    # Pattern 3: "Not Found" errors on entity endpoints
    if f"/api/{entity_plural}" in combined_output and "not found" in combined_output:
        return True
    
    return False


async def _heal_integration_failures(
    project_id: str,
    project_path: Path,
    entity_plural: str,
    failure_output: str,
    attempt: int
) -> bool:
    """
    Policy-driven healing for integration failures.
    
    Uses:
    - HealingPolicy to determine what to heal
    - HealingPipeline to execute repairs
    - BackendProbe to validate fixes
    
    No hardcoded artifact names or URLs - all driven by policy and contracts.
    
    Args:
        project_id: Project ID
        project_path: Path to workspace
        entity_plural: Plural form of entity (from discovery)
        failure_output: Combined stdout/stderr from test failure
        attempt: Current attempt number
    
    Returns:
        True if healing succeeded and validation passed
    """
    from app.orchestration.healing_pipeline import HealingPipeline
    from app.orchestration.healing_policy import HealingPolicy
    from app.orchestration.backend_probe import BackendProbe, ProbeMode
    from app.orchestration.contract_parser import ContractParser
    import asyncio
    
    log("HEAL", f"🧬 Policy-driven healing triggered (attempt {attempt})")
    
    # Initialize components
    policy = HealingPolicy(project_path)
    healer = HealingPipeline(project_path=project_path, llm_caller=None)
    probe = BackendProbe.from_env(ProbeMode.DOCKER, project_id=project_id)
    
    # Classify error type
    error_type = policy.classify_error(
        step="testing_backend",
        error_message=failure_output,
        http_statuses=[404] if "404" in failure_output else None
    )
    
    log("HEAL", f"📊 Classified as: {error_type.value}")
    
    # Get healing actions from policy
    actions = policy.get_healing_actions(
        step="testing_backend",
        error_type=error_type,
        entity_plural=entity_plural,
        http_statuses=[404] if "404" in failure_output else None
    )
    
    if not actions:
        log("HEAL", "⚠️ No healing actions suggested by policy")
        return False
    
    log("HEAL", f"📋 Policy suggests {len(actions)} healing action(s)")
    
    # Try each action in priority order
    for action in actions:
        # Check if we should skip this action (already tried too many times)
        if policy.should_stop_healing(action.artifact, max_attempts=2):
            log("HEAL", f"⏭️ Skipping {action.artifact} (already tried {2} times)")
            continue
        
        log("HEAL", f"🔧 Action: {action.artifact}")
        log("HEAL", f"   Reason: {action.reason}")
        log("HEAL", f"   Requires restart: {action.requires_restart}")
        
        # Map artifact to step name for healing pipeline
        step_map = {
            "backend_vertical": "backend_implementation",
            "system_integration": "system_integration",
            "backend_main": "system_integration",
            "backend_db": "backend_implementation",
        }
        
        step = step_map.get(action.artifact, action.artifact)
        
        # Attempt healing
        try:
            result = await healer.attempt_heal(
                step=step,
                error_log=failure_output[:1000],
                archetype="general",
                retries=attempt
            )
            
            if not result:
                log("HEAL", f"❌ Healing {action.artifact} failed")
                policy.record_repair(action.artifact)
                continue
            
            log("HEAL", f"✅ Healing {action.artifact} completed")
            policy.record_repair(action.artifact)
            
            # Restart service if required
            if action.requires_restart:
                log("HEAL", "🔄 Restarting backend service...")
                try:
                    # CRITICAL FIX: Use the global SANDBOX singleton from implementations.py
                    # This is the SAME instance that created the sandbox during test execution
                    # Creating a new SandboxManager() would have an empty active_sandboxes dict
                    from app.tools.implementations import SANDBOX as sandbox_mgr
                    
                    # Bug Fix #2: Sync files before Docker restart
                    log("HEAL", "📁 Syncing files before restart...")
                    main_py = project_path / "backend" / "app" / "main.py"
                    if main_py.exists():
                        main_py.touch()  # Force filesystem sync
                    await asyncio.sleep(2)  # Wait for Windows filesystem
                    
                    # Stop the running container
                    stop_result = await sandbox_mgr.stop_sandbox(project_id)
                    if not stop_result.get("success"):
                        log("HEAL", f"⚠️ Stop sandbox warning: {stop_result.get('error')}")
                    
                    await asyncio.sleep(1)  # Brief pause after stop
                    
                    # Restart with rebuild to pick up new code
                    start_result = await sandbox_mgr.start_sandbox(
                        project_id=project_id,
                        wait_healthy=True,
                        services=["backend"]  # Only restart backend, not frontend/db
                    )
                    
                    if not start_result.get("success"):
                        log("HEAL", f"⚠️ Service restart failed: {start_result.get('error')}")
                    else:
                        log("HEAL", "✅ Service restarted successfully")
                    
                    await asyncio.sleep(3)  # Wait for service to fully initialize
                except Exception as e:
                    log("HEAL", f"⚠️ Restart failed: {e}")
            
            # Validate using contract-driven probe
            log("HEAL", "🔍 Validating fix via contract routes...")
            
            # Check health first
            if not await probe.is_healthy(timeout=5.0):
                log("HEAL", "❌ Health check failed after healing")
                continue
            
            # Check primary entity routes
            parser = ContractParser(project_path)
            entity_routes = parser.get_primary_entity_routes()
            
            if not entity_routes:
                log("HEAL", "⚠️ No entity routes in contract - assuming success")
                return True
            
            all_passed = True
            for route in entity_routes:
                passed = await probe.check_route(
                    method=route.method,
                    path=route.path,
                    expected_status=route.expected_status,
                    timeout=5.0
                )
                
                if not passed:
                    log("HEAL", f"❌ Route still broken: {route.method} {route.path}")
                    all_passed = False
                    break
            
            if all_passed:
                log("HEAL", "✅ All validation checks passed!")
                return True
            else:
                log("HEAL", "❌ Validation failed - trying next action")
                continue
                
        except Exception as e:
            log("HEAL", f"❌ Healing action failed: {e}")
            policy.record_repair(action.artifact)
            continue
    
    log("HEAL", "🛑 All healing actions exhausted")
    return False


# Centralized file writing utility
from app.lib.file_writer import safe_write_llm_files


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
    
    Derek ALWAYS generates tests from template - this ensures tests are
    project-specific and match the implemented models/routers.
    """
    from app.supervision import supervised_agent_call
    from app.orchestration.utils import pluralize
    from app.handlers.base import broadcast_agent_log
    
    tests_dir = project_path / "backend" / "tests"
    template_file = tests_dir / "test_api.py.template"
    
    # ALWAYS generate tests from template - Derek creates project-specific tests
    log("TESTING", f"📝 Derek generating backend tests from template for entity: {primary_entity}")
    
    primary_entity_plural = pluralize(primary_entity)
    primary_entity_capitalized = primary_entity.capitalize()
    
    # Read the template if it exists
    template_content = ""
    if template_file.exists():
        template_content = template_file.read_text(encoding="utf-8")
        # Replace placeholders with actual entity names
        template_content = template_content.replace("{{ENTITY}}", primary_entity)
        template_content = template_content.replace("{{ENTITY_PLURAL}}", primary_entity_plural)
        template_content = template_content.replace("{{MODEL_NAME}}", primary_entity_capitalized)
        log("TESTING", f"📋 Using test template with entity: {primary_entity}")
    
    # Build Derek's test generation instructions
    test_generation_prompt = f"""Generate the backend test file for this project.

═══════════════════════════════════════════════════════
PROJECT CONTEXT
═══════════════════════════════════════════════════════

User Request: {user_request[:300]}
Primary Entity: {primary_entity_capitalized}
Entity Plural: {primary_entity_plural}
Archetype: {archetype}

═══════════════════════════════════════════════════════
TEST TEMPLATE (CUSTOMIZE THIS FOR THE PROJECT)
═══════════════════════════════════════════════════════

Below is a template. Use it as a STARTING POINT but CUSTOMIZE it:
- Replace placeholder tests with tests specific to {primary_entity_capitalized}
- Add tests for the actual endpoints from contracts.md
- Make tests project-specific, not generic

TEMPLATE:
{template_content if template_content else "No template found - generate standard CRUD tests."}

═══════════════════════════════════════════════════════
REQUIREMENTS
═══════════════════════════════════════════════════════

1. Create backend/tests/test_api.py with working pytest tests
2. MUST include:
   - test_health_check: GET /api/health returns 200 + {{"status": "healthy"}}
   - test_list_{primary_entity_plural}: GET /api/{primary_entity_plural} returns 200
   - test_create_{primary_entity}: POST /api/{primary_entity_plural} returns 200/201
   - test_get_{primary_entity}_not_found: GET /api/{primary_entity_plural}/<fake_id> returns 404

3. Use the `client` fixture from conftest.py (already provided)
4. Use @pytest.mark.anyio decorator for async tests
5. Use Faker for test data when appropriate
6. ALL tests must be async (async def test_...)

🚨 CRITICAL - TEST DATA FIELDS:
- You MUST read the provided `models.py` content below.
- Use EXACTLY the fields defined in the model (e.g. if model has 'content', use 'content'; if 'description', use 'description').
- Do not invent fields. Matching the model schema is MANDATORY.
- Example correct test data (adapt to actual model):
  {{
      "title": fake.sentence(nb_words=4),
      "content": fake.paragraph(nb_sentences=2),
  }}

═══════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════

{{
  "thinking": "Explain how you're customizing the tests for {primary_entity_capitalized}...",
  "files": [
    {{
      "path": "backend/tests/test_api.py",
      "content": "import pytest\\nfrom faker import Faker\\n\\nfake = Faker()\\n\\n@pytest.mark.anyio\\nasync def test_health_check(client):\\n    ..."
    }}
  ]
}}

Generate COMPLETE, WORKING test file now!
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
            base_instructions=test_generation_prompt,
            project_path=project_path,
            user_request=user_request,
            contracts="",
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
    
    test_content = f'''# backend/tests/test_api.py
"""
API Tests - Auto-generated fallback
Generated when Derek failed to create tests.
"""
import pytest
from faker import Faker

fake = Faker()


@pytest.mark.anyio
async def test_health_check(client):
    """Test the health check endpoint."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "healthy"


@pytest.mark.anyio
async def test_list_{entity_plural}(client):
    """Test listing {entity_plural}."""
    response = await client.get("/api/{entity_plural}")
    assert response.status_code == 200
    data = response.json()
    # Response should be a list or have a data array
    assert isinstance(data, (list, dict))


@pytest.mark.anyio
async def test_create_{entity}(client):
    \"\"\"Test creating a {entity}.\"\"\"
    {entity}_data = {{
        \"title\": fake.sentence(nb_words=4),
        \"content\": fake.paragraph(nb_sentences=2),
    }}
    response = await client.post(\"/api/{entity_plural}\", json={entity}_data)
    assert response.status_code in [200, 201]


@pytest.mark.anyio
async def test_get_{entity}_not_found(client):
    """Test getting a non-existent {entity} returns 404."""
    fake_id = "507f1f77bcf86cd799439011"
    response = await client.get(f"/api/{entity_plural}/{{fake_id}}")
    assert response.status_code == 404
'''

    test_file = tests_dir / "test_api.py"
    try:
        test_file.write_text(test_content, encoding="utf-8")
        log("TESTING", f"📋 Fallback test file written: {test_file.name} ({len(test_content)} chars)")
        return True
    except Exception as e:
        log("TESTING", f"❌ Failed to write fallback test file: {e}")
        return False


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
    Step: Derek tests backend using tools only.

    - Uses subagentcaller to ask Derek for fixes.
    - Applies unified diffs or JSON patches via patch tools.
    - Runs backend tests INSIDE sandbox via sandboxexec.
    """
    from app.orchestration.utils import broadcast_to_project

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

    # Ensure tests directory exists so Docker doesn't create it as root
    (project_path / "backend/tests").mkdir(parents=True, exist_ok=True)

    max_attempts = 3
    last_stdout: str = ""
    last_stderr: str = ""
    
    # V3: Cumulative token tracking across all LLM calls in this step
    step_token_usage = {"input": 0, "output": 0}

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
    if entities:
        primary_entity = entities[0]
    else:
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
    test_file_path = project_path / "backend/tests/test_api.py"
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
EXISTING TEST FILE: backend/tests/test_api.py
DO NOT create new test files - fix the routers/models to make existing tests pass.

Additional archetype guidance for {archetype}:
{test_instructions}
"""
        try:
            existing_test_content = test_file_path.read_text(encoding="utf-8")[:1500]
        except Exception:
            pass
    else:
        test_instructions = f"""
⚠️ MISSING TEST FILE: backend/tests/test_api.py
You MUST create this file. Include tests for:
1. /api/health (return 200 OK)
2. /api/{primary_entity_plural} (CREATE and GET list)

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

    for attempt in range(1, max_attempts + 1):
        log(
            "TESTING",
            f"🔁 Backend test attempt {attempt}/{max_attempts} for {project_id}",
        )

        # ------------------------------------------------------------
        # 1) Run tests FIRST to get failure context
        # ------------------------------------------------------------
        if attempt == 1:
            log("TESTING", "🚀 Running initial backend tests to get failure context...")
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
                
                # If tests pass on first try, we're done!
                if sandbox_result.get("success"):
                    log("TESTING", "✅ Backend tests PASSED on first run (no fixes needed)")
                    return StepResult(
                        nextstep=WorkflowStep.FRONTEND_INTEGRATION,
                        turn=current_turn + 1,
                        status="ok",
                        data={"tier": "sandbox", "attempt": 0},
                        token_usage=step_token_usage,  # V3
                    )
            except Exception as e:
                last_stderr = str(e)
                log("TESTING", f"Initial test run failed: {e}")

        # ------------------------------------------------------------
        # 2) Marcus analyzes failure as Backend Critic (before Derek fixes)
        # ------------------------------------------------------------
        failure_snippet = last_stderr or last_stdout or "(No test output captured)"
        if len(failure_snippet) > 2000:
            failure_snippet = failure_snippet[:2000] + "\n… (truncated)"

        # Read architecture.md for Backend Design Patterns
        arch_content = ""
        try:
            arch_file = project_path / "architecture.md"
            if arch_file.exists():
                arch_content = arch_file.read_text(encoding="utf-8")
        except Exception as e:
            log("TESTING", f"Could not read architecture.md: {e}")

        # Read contracts.md for API expectations
        contracts_content = ""
        try:
            contracts_file = project_path / "contracts.md"
            if contracts_file.exists():
                contracts_content = contracts_file.read_text(encoding="utf-8")[:2000]
        except Exception:
            pass

        # ------------------------------------------------------------
        # 👁️ VISIBILITY UPGRADE: Gather Source Code for Marcus
        # ------------------------------------------------------------
        source_context = ""
        
        # 1. Main.py (Router Wiring)
        try:
            main_py = (project_path / "backend/app/main.py").read_text(encoding="utf-8")
            source_context += f"📄 backend/app/main.py (System Wiring):\n```python\n{main_py}\n```\n\n"
        except Exception:
            pass
            
        # 2. Models.py
        try:
            models_py = (project_path / "backend/app/models.py").read_text(encoding="utf-8")
            source_context += f"📄 backend/app/models.py:\n```python\n{models_py}\n```\n\n"
        except Exception:
            pass

        # 3. Routers (API Implementation)
        try:
            routers_dir = project_path / "backend/app/routers"
            if routers_dir.exists():
                for r_file in routers_dir.glob("*.py"):
                    if r_file.name != "__init__.py":
                        r_content = r_file.read_text(encoding="utf-8")
                        source_context += f"📄 backend/app/routers/{r_file.name}:\n```python\n{r_content}\n```\n\n"
        except Exception:
            pass


        # Marcus as Backend Critic - analyze failure and provide structured instructions
        # NOTE: Using string concatenation to avoid "Invalid format specifier" when content contains { }
        marcus_critic_prompt = (
            "You are acting as a BACKEND CRITIC for a failing test.\n\n"
            "PROJECT CONTEXT:\n"
            f"- Primary Entity: {primary_entity}\n"
            f"- Archetype: {archetype}\n"
            f"- User Request: {user_request[:200]}\n\n"
            "═══════════════════════════════════════════════════════\n"
            "📐 BACKEND DESIGN PATTERNS (from architecture.md)\n"
            "═══════════════════════════════════════════════════════\n\n"
            + (arch_content[:3000] if arch_content else "No architecture.md found.") + "\n\n"
            "═══════════════════════════════════════════════════════\n"
            "📋 API CONTRACTS (from contracts.md)\n"
            "═══════════════════════════════════════════════════════\n\n"
            + (contracts_content if contracts_content else "No contracts.md found.") + "\n\n"
            "═══════════════════════════════════════════════════════\n"
            "❌ FAILING TEST OUTPUT\n"
            "═══════════════════════════════════════════════════════\n\n"
            + failure_snippet + "\n\n"
            "═══════════════════════════════════════════════════════\n"
            "🧪 EXISTING TEST FILE (backend/tests/test_api.py)\n"
            "═══════════════════════════════════════════════════════\n\n"
            + existing_test_content + "\n\n"
            "═══════════════════════════════════════════════════════\n"
            "🔍 CURRENT IMPLEMENTATION CODE (Critical for Debugging)\n"
            "═══════════════════════════════════════════════════════\n\n"
            + source_context + "\n\n"
            "═══════════════════════════════════════════════════════\n"
            "YOUR TASK AS BACKEND CRITIC\n"
            "═══════════════════════════════════════════════════════\n\n"
            "Analyze the test failure and provide Derek with STRUCTURED FIX INSTRUCTIONS.\n\n"
            "You MUST identify:\n\n"
            "1. **ROOT CAUSE**: What specific pattern violation or bug caused the failure?\n"
            "   - Is it a model issue (wrong field types, missing defaults)?\n"
            "   - Is it a router issue (wrong status codes, wrong response format)?\n"
            "   - Is it a database issue (ObjectId handling, missing indexes)?\n\n"
            "2. **VIOLATED PATTERNS**: Which Backend Design Patterns are not being followed?\n"
            "   - Response envelope format (\"data\": [...], \"total\": int)\n"
            "   - Error handling ({\"error\": {\"code\": \"...\", \"message\": \"...\"}})\n"
            "   - HTTP status codes (201 for create, 404 for not found)\n"
            "   - Field defaults (Field(default_factory=list) not = [])\n\n"
            f"3. **SPECIFIC FILES TO FIX**: List exact files and what to change:\n"
            f"   - backend/app/models.py: \"Add Field(default_factory=list) for comments field\"\n"
            f"   - backend/app/routers/{primary_entity_plural}.py: \"Return 201 on POST, not 200\"\n\n"
            "4. **CODE CHANGES**: Provide exact code snippets Derek should use.\n\n"
            "OUTPUT FORMAT:\n"
            "Return JSON with this structure:\n\n"
            "{\n"
            "  \"thinking\": \"Analyze the failure systematically. What went wrong? What pattern was violated?\",\n"
            "  \"diagnosis\": {\n"
            "    \"root_cause\": \"Brief description of the core issue\",\n"
            "    \"violated_patterns\": [\"Pattern 1\", \"Pattern 2\"],\n"
            "    \"fix_instructions\": [\n"
            "      {\n"
            "        \"file\": \"backend/app/models.py\",\n"
            "        \"issue\": \"What's wrong\",\n"
            "        \"fix\": \"Exact change to make\"\n"
            "      }\n"
            "    ]\n"
            "  }\n"
            "}\n\n"
            "Be SPECIFIC and ACTIONABLE. Derek will follow your instructions exactly.\n"
        )

        # Have Marcus analyze the failure
        marcus_analysis = None
        try:
            from app.supervision import supervised_agent_call
            
            await broadcast_agent_log(
                manager,
                project_id,
                "AGENT:Marcus",
                f"🔍 Backend test failed (attempt {attempt}). Analyzing failure against design patterns..."
            )
            
            marcus_result = await supervised_agent_call(
                project_id=project_id,
                manager=manager,
                agent_name="Marcus",
                step_name="Backend Test Diagnosis",
                base_instructions=marcus_critic_prompt,
                project_path=project_path,
                user_request=user_request,
                contracts=contracts_content,
                max_retries=0,  # No retries - single attempt only to avoid loop explosion
            )
            
            # V3: Accumulate token usage
            if marcus_result.get("token_usage"):
                usage = marcus_result.get("token_usage")
                step_token_usage["input"] += usage.get("input", 0)
                step_token_usage["output"] += usage.get("output", 0)
            
            # Check if LLM is unavailable due to rate limiting
            if marcus_result.get("skipped") and marcus_result.get("reason") == "rate_limit":
                log("TESTING", "⚠️ LLM unavailable (rate limited), stopping backend testing")
                await broadcast_agent_log(
                    manager,
                    project_id,
                    "AGENT:Marcus",
                    f"⚠️ {marcus_result.get('provider', 'LLM')} rate limited - cannot continue testing"
                )
                raise Exception(
                    f"LLM provider rate limited. Please wait and try again.\n"
                    f"Provider: {marcus_result.get('provider', 'unknown')}"
                )
            
            marcus_analysis = marcus_result.get("output", {})
            diagnosis = marcus_analysis.get("diagnosis", {})
            
            if diagnosis:
                root_cause = diagnosis.get("root_cause", "Unknown")
                fix_instructions = diagnosis.get("fix_instructions", [])
                
                await broadcast_agent_log(
                    manager,
                    project_id,
                    "AGENT:Marcus",
                    f"🎯 Diagnosed: {root_cause[:100]}. Providing {len(fix_instructions)} fix instructions to Derek."
                )
            else:
                await broadcast_agent_log(
                    manager,
                    project_id,
                    "AGENT:Marcus",
                    "⚠️ Could not diagnose specific pattern violation. Derek will analyze directly."
                )
                
        except Exception as e:
            log("TESTING", f"Marcus backend critic analysis failed: {e}")
            await broadcast_agent_log(
                manager,
                project_id,
                "AGENT:Marcus",
                "⚠️ Analysis skipped due to error. Derek will fix directly."
            )

        # ------------------------------------------------------------
        # 3) Build Derek's instructions with Marcus's guidance
        # ------------------------------------------------------------
        marcus_guidance = ""
        if marcus_analysis and marcus_analysis.get("diagnosis"):
            diag = marcus_analysis["diagnosis"]
            marcus_guidance = f"""
═══════════════════════════════════════════════════════
🧠 MARCUS'S DIAGNOSIS (FOLLOW THIS EXACTLY)
═══════════════════════════════════════════════════════

ROOT CAUSE: {diag.get('root_cause', 'Unknown')}

VIOLATED PATTERNS:
{chr(10).join('- ' + p for p in diag.get('violated_patterns', []))}

FIX INSTRUCTIONS:
"""
            for fix in diag.get("fix_instructions", []):
                marcus_guidance += f"""
📁 {fix.get('file', 'unknown')}:
   Issue: {fix.get('issue', 'unknown')}
   Fix: {fix.get('fix', 'unknown')}
"""
            marcus_guidance += """

You MUST follow Marcus's instructions above. He has analyzed the failure against the Backend Design Patterns.
"""

        # NOTE: Using string concatenation to avoid "Invalid format specifier" when content contains { }
        instructions = (
            DEREK_TESTING_PROMPT + "\n"
            + entity_context + "\n\n"
            + marcus_guidance + "\n\n"
            "EXISTING TEST FILE (backend/tests/test_api.py):\n"
            "```python\n"
            + existing_test_content + "\n"
            "```\n\n"
            f"PYTEST OUTPUT FROM ATTEMPT {attempt}:\n\n"
            + failure_snippet + "\n\n"
            "FIX THE ROUTERS/MODELS TO MAKE TESTS PASS. Do NOT rewrite the test file unless absolutely necessary.\n"
        )


        try:
            # Use supervised call to get the fix
            # This ensures Marcus reviews the fix before we try to apply/test it
            from app.supervision import supervised_agent_call
            
            result = await supervised_agent_call(
                project_id=project_id,
                manager=manager,
                agent_name="Derek",
                step_name="Backend Testing Fix",
                base_instructions=instructions,
                project_path=project_path,
                user_request=user_request,
                contracts="", # Contracts not critical for syntax fixes
                max_retries=0,  # No retries - single attempt only to avoid loop explosion
            )
            
            # V3: Accumulate token usage
            if result.get("token_usage"):
                usage = result.get("token_usage")
                step_token_usage["input"] += usage.get("input", 0)
                step_token_usage["output"] += usage.get("output", 0)
            
            # Check if LLM is unavailable due to rate limiting
            if result.get("skipped") and result.get("reason") == "rate_limit":
                log("TESTING", "⚠️ Derek skipped due to rate limiting")
                raise Exception(f"LLM provider rate limited: {result.get('provider', 'unknown')}")

            parsed = result.get("output", {})
            
            # 1) Unified diff patch (preferred)
            diff_text = parsed.get("patch") or parsed.get("diff")
            if isinstance(diff_text, str) and diff_text.strip():
                patch_result = await run_tool(
                    name="unifiedpatchapplier",
                    args={
                        "project_path": str(project_path),
                        "patch": diff_text,
                    },
                )
                log(
                    "TESTING",
                    f"Applied unified backend patch on attempt {attempt}: {patch_result}",
                )

            # 2) JSON multi-file patches
            elif "patches" in parsed:
                patch_result = await run_tool(
                    name="jsonpatchapplier",
                    args={
                        "project_path": str(project_path),
                        "patches": parsed.get("patches"),
                    },
                )
                log(
                    "TESTING",
                    f"Applied JSON backend patches on attempt {attempt}: {patch_result}",
                )

            # 3) Fallback: full file rewrites
            elif parsed.get("files"):
                validated = validate_file_output(
                    parsed,
                    WorkflowStep.TESTING_BACKEND,
                    max_files=MAX_FILES_PER_STEP,
                )

                written_count = await safe_write_llm_files(
                    manager=manager,
                    project_id=project_id,
                    project_path=project_path,
                    files=validated.get("files", []),
                    step_name=WorkflowStep.TESTING_BACKEND,
                )
                
                status = "✅ approved" if result.get("approved") else "⚠️ best effort"
                log(
                    "TESTING",
                    f"Derek wrote {written_count} backend test/impl files on attempt {attempt} ({status})",
                )

        except Exception as e:
            log("TESTING", f"Derek backend fix step failed on attempt {attempt}: {e}")

        # ------------------------------------------------------------
        # 2) Run backend tests inside sandbox via sandboxexec
        # ------------------------------------------------------------
        log(
            "TESTING",
            f"🚀 Running backend tests in sandbox (attempt {attempt}/{max_attempts})",
        )

        try:
            sandbox_result = await run_tool(
                name="sandboxexec",
                args={
                    "project_id": project_id,
                    "service": "backend",
                    "command": "pytest -q",
                    "start_services": ["backend"], # ✅ Only start backend (and implicit DB)
                    "timeout": 300,
                },
            )
        except Exception as e:
            log("TESTING", f"sandboxexec for backend threw exception: {e}")
            raise # Propagate up to handler default filtering

        last_stdout = sandbox_result.get("stdout", "") or ""
        last_stderr = sandbox_result.get("stderr", "") or ""

        if sandbox_result.get("success"):
            log(
                "TESTING",
                f"✅ Backend tests PASSED in sandbox on attempt {attempt}",
            )

            await broadcast_to_project(
                manager,
                project_id,
                {
                    "type": "WORKFLOW_STAGE_COMPLETED",
                    "projectId": project_id,
                    "step": WorkflowStep.TESTING_BACKEND,
                    "attempt": attempt,
                    "tier": "sandbox",
                },
            )
            return StepResult(
                nextstep=WorkflowStep.FRONTEND_INTEGRATION,  # GenCode Studio: Replace mock with API
                turn=current_turn + 1,
                status="ok",
                data={
                    "tier": "sandbox",
                    "attempt": attempt,
                },
                token_usage=step_token_usage,  # V3
            )

        log(
            "TESTING",
            f"❌ Backend tests FAILED in sandbox on attempt {attempt}",
        )

        #═══════════════════════════════════════════════════════════
        # 🧬 ARBORMIND HEALING LOOP: Detect 404s and heal integration
        #═══════════════════════════════════════════════════════════
        if _has_routing_failures(last_stdout, last_stderr, primary_entity_plural):
            log("TESTING", "🔧 Detected 404 routing failures - triggering integration healing")
            
            healed = await _heal_integration_failures(
                project_id=project_id,
                project_path=project_path,
                entity_plural=primary_entity_plural,
                failure_output=last_stdout + "\n" + last_stderr,
                attempt=attempt
            )
            
            if healed:
                log("TESTING", "✅ Integration healed - re-running tests")
                # Re-run tests after healing
                try:
                    sandbox_result = await run_tool(
                        name="sandboxexec",
                        args={
                            "project_id": project_id,
                            "service": "backend",
                            "command": "pytest -q",
                            "start_services": ["backend"],
                            "timeout": 300,
                        },
                    )
                    
                    if sandbox_result.get("success"):
                        log("TESTING", "✅ Tests PASSED after integration healing!")
                        return StepResult(
                            nextstep=WorkflowStep.FRONTEND_INTEGRATION,
                            turn=current_turn + 1,
                            status="ok",
                            data={"tier": "sandbox", "attempt": attempt, "healed": True},
                            token_usage=step_token_usage,  # V3
                        )
                    else:
                        log("TESTING", "⚠️ Tests still failing after healing - will retry Derek fixes")
                except Exception as e:
                    log("TESTING", f"Re-test after healing failed: {e}")
            else:
                log("TESTING", "⚠️ Integration healing did not resolve issue")

        if attempt < max_attempts:
            log(
                "TESTING",
                f"🔁 Backend tests will be retried (attempt {attempt + 1}/{max_attempts}).",
            )
        else:
            error_msg = (
                "Backend tests failed in sandbox after all attempts.\n"
                f"Last sandbox stdout:\n{last_stdout[:2000]}\n\n"
                f"Last sandbox stderr:\n{last_stderr[:2000]}"
            )
            log("ERROR", f"FAILED at {WorkflowStep.TESTING_BACKEND}: {error_msg}")
            raise Exception(error_msg)

    # Defensive: should never reach here
    raise Exception(
        "Backend testing step exited without success or explicit failure. "
        "This indicates a logic error in the backend test loop."
    )
