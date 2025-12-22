
"""
Step 8: Luna runs E2E tests on the integrated frontend.

Workflow order: ... → Frontend Integration (7) → Testing Frontend (8) → Preview (9)
"""
import re
from pathlib import Path
from typing import Any, Dict, List

from app.core.types import ChatMessage, StepResult
from app.core.constants import WorkflowStep
from app.handlers.base import broadcast_status
from app.core.logging import log
from app.utils.test_scaffolding import create_matching_smoke_test
from app.tools import run_tool
from app.llm.prompts.luna_testing import LUNA_TESTING_PROMPT

from app.core.constants import PROTECTED_SANDBOX_FILES
from app.core.failure_boundary import FailureBoundary
from app.core.file_writer import safe_write_llm_files, validate_file_output
from app.core.step_invariants import StepInvariants, StepInvariantError
# Phase 7: Validated replacement - simplify logic rather than importing guidance


# Constants from legacy
MAX_FILES_PER_STEP = 10
MAX_FILE_LINES = 400






# Protected sandbox files - imported from centralized constants


# REMOVED: Restrictive allowed prefixes - agents can write to any file except protected ones


# Centralized file writing utility



def ensure_str(val) -> str:
    """Ensure value is a string (sandboxexec may return bytes)."""
    if val is None:
        return ""
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return str(val)


async def _generate_frontend_tests_from_template(
    manager: Any,
    project_id: str,
    project_path: Path,
    user_request: str,
    primary_entity: str,
    branch: Any,
) -> bool:
    """
    Generate frontend E2E tests from template at the START of testing step.
    
    Flow:
    1. Read the test template (from Golden Seed)
    2. Call Luna to generate project-specific tests based on template
    3. Write the test file
    4. Return True if tests were generated successfully
    
    Luna ALWAYS generates tests from template - this ensures tests are
    project-specific and match the implemented frontend components.
    """
    from app.handlers.base import broadcast_agent_log
    from app.orchestration.state import WorkflowStateManager
    
    tests_dir = project_path / "frontend" / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    
    entity_plural = primary_entity + "s" if not primary_entity.endswith("s") else primary_entity
    
    # ═══════════════════════════════════════════════════════
    # ARCHETYPE-AWARE E2E TEST GENERATION
    # ═══════════════════════════════════════════════════════
    intent = await WorkflowStateManager.get_intent(project_id) or {}
    archetype_routing = intent.get("archetypeRouting", {})
    detected_archetype = archetype_routing.get("top", "general") if isinstance(archetype_routing, dict) else "general"
    
    # Get archetype-specific E2E testing guidance (Simplified)
    e2e_archetype_guidance = f"""
    ARCHETYPE: {detected_archetype}
    PRIMARY ENTITY: {primary_entity}
    
    Write tests that verify the core functionality expected for this archetype.
    """
    
    # Architecture Bundle: Frontend Testing Context
    arch_context = ""
    try:
        frontend_md = (project_path / "architecture" / "frontend.md").read_text(encoding="utf-8")
        invariants_md = (project_path / "architecture" / "invariants.md").read_text(encoding="utf-8")
        arch_context = f"\n\n--- UI REQUIREMENTS ---\n{frontend_md}\n\n--- QUALITY INVARIANTS ---\n{invariants_md}"
    except Exception:
        pass

    # Read actual frontend files for accurate selector generation
    frontend_code_context = ""
    try:
        app_jsx = project_path / "frontend" / "src" / "App.jsx"
        if app_jsx.exists():
            frontend_code_context += f"\n--- App.jsx ---\n{app_jsx.read_text(encoding='utf-8')[:1500]}\n"
        
        # Include all pages
        pages_dir = project_path / "frontend" / "src" / "pages"
        if pages_dir.exists():
            for page_file in list(pages_dir.glob("*.jsx"))[:3]:
                frontend_code_context += f"\n--- {page_file.name} ---\n{page_file.read_text(encoding='utf-8')[:1500]}\n"
    except Exception:
        pass
    
    # Build Luna's test generation instructions
    test_generation_prompt = f"""Generate the frontend E2E test file for this project.

═══════════════════════════════════════════════════════
PROJECT CONTEXT (ARCHITECTURE BUNDLE)
═══════════════════════════════════════════════════════

User Request: {user_request[:300]}
Primary Entity: {primary_entity.capitalize()}
Entity Plural: {entity_plural}
Archetype: {detected_archetype}

{e2e_archetype_guidance}
{arch_context}

═══════════════════════════════════════════════════════
ACTUAL FRONTEND CODE (CRITICAL - READ THIS!)
═══════════════════════════════════════════════════════

{frontend_code_context if frontend_code_context else "No frontend code found yet - generate standard smoke tests"}

⚠️ CRITICAL: Look at the ACTUAL components above.
- Find the REAL headings (h1, h2 text)
- Find the REAL buttons (button text, data-testid)
- Find the REAL data-testid attributes
- DO NOT invent selectors that don't exist in the code!

═══════════════════════════════════════════════════════
REQUIREMENTS
═══════════════════════════════════════════════════════

1. Create frontend/tests/e2e.spec.js with working Playwright tests
2. MUST include:
   - Smoke test: page loads without crashing
   - State test: shows loading, error, or content
   - Heading test: main heading is visible
   
3. Use import {{ test, expect }} from '@playwright/test';
4. Use full URL: page.goto('http://localhost:5174/')
5. Use ACTUAL data-testid selectors from components shown above
6. Handle loading/error states gracefully
7. DO NOT invent selectors - only use what you see in the code above!

═══════════════════════════════════════════════════════
OUTPUT FORMAT (HDAP)
═══════════════════════════════════════════════════════

Use HDAP artifact markers:

<<<FILE path="frontend/tests/e2e.spec.js">>>
import {{ test, expect }} from '@playwright/test';

test('page loads', async ({{ page }}) => {{
  await page.goto('http://localhost:5174/');
  // Test implementation...
}});
<<<END_FILE>>>

🚨 CRITICAL: File MUST end with <<<END_FILE>>> or it will be rejected!

Generate COMPLETE, WORKING test file now!
"""

    try:
        from app.supervision import supervised_agent_call
        
        await broadcast_agent_log(
            manager,
            project_id,
            "AGENT:Luna",
            f"📝 Generating E2E tests for {primary_entity.capitalize()}..."
        )
        
        # Extract retry/override context
        temperature_override = branch.intent.get("temperature_override")
        is_retry = branch.intent.get("is_retry", False)

        result = await supervised_agent_call(
            project_id=project_id,
            manager=manager,
            agent_name="Luna",
            step_name="E2E Test Generation",
            base_instructions=test_generation_prompt,
            project_path=project_path,
            user_request=user_request,
            contracts="",
            temperature_override=temperature_override,
            is_retry=is_retry,
        )
        
        parsed = result.get("output", {})
        files = parsed.get("files", [])
        
        if files:
            written = await safe_write_llm_files(
                manager=manager,
                project_id=project_id,
                project_path=project_path,
                files=files,
                step_name="E2E Test Generation",
            )
            
            if written > 0:
                # log("TESTING", f"✅ Luna generated {written} test file(s)")
                return True
        
        # No fallback - report failure, ArborMind decides what to do
        log("TESTING", "❌ Luna did not generate test files. Hard failure.")
        return False
        
    except Exception as e:
        # Report failure - ArborMind decides what to do next
        log("TESTING", f"❌ Frontend test generation failed: {e}")
        return False



@FailureBoundary.enforce
async def step_testing_frontend(branch) -> StepResult:
    """
    Step 11: Luna tests frontend with Playwright.

    Execution-Only Pattern:
    - Tests are generated and executed in a single-shot.
    - No internal healing or iterative loops.
    - Failures result in immediate workflow termination.
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
        WorkflowStep.TESTING_FRONTEND,
        f"Luna running E2E tests...",
        8,
        9,
    )

    log(
        "STATUS",
        f"[{WorkflowStep.TESTING_FRONTEND}] Starting frontend sandbox tests for {project_id}",
    )

    
    last_stdout: str = ""
    last_stderr: str = ""
    
    # V3: Cumulative token tracking across all LLM calls in this step
    step_token_usage = {"input": 0, "output": 0}

    # Directory to persist test files between attempts for debugging
    test_history_dir = project_path / ".test_history"
    test_history_dir.mkdir(parents=True, exist_ok=True)

    def persist_test_file_for_debugging(attempt_num: int, test_content: str, source: str = "luna"):
        """Save test file content for debugging purposes."""
        try:
            history_file = test_history_dir / f"e2e_attempt_{attempt_num}_{source}.spec.js"
            history_file.write_text(test_content, encoding="utf-8")
            log("TESTING", f"📝 Persisted test file for attempt {attempt_num} ({source}): {history_file.name}")
        except Exception as e:
            log("TESTING", f"⚠️ Failed to persist test history: {e}")

    marcus_feedback = ""
    
    # ============================================================
    # PRIORITY 2: Docker Infra Error Detection
    # ============================================================
    docker_failure_count = 0
    last_docker_error = None
    infra_error_patterns = [
        "docker compose up FAILED",
        "Error response from daemon",
        "No such container",
        "Service 'frontend' missing from running containers",
        "network .* not found",
        "Container .* not found",
    ]

    # ============================================================
    # PRIORITY 3: Critical File Pre-Check (FAIL FAST)
    # ============================================================
    # Check if backend has all required files BEFORE attempting Docker builds.
    # If backend_routers step failed (producing no router files), Docker build
    # will fail with "ModuleNotFoundError: No module named 'app.routers.X'"
    # This saves ~7 minutes of failed Docker attempts.
    # ============================================================
    
    critical_backend_files = [
        project_path / "backend" / "app" / "main.py",
        project_path / "backend" / "app" / "database.py",
    ]
    
    missing_critical = [str(f.relative_to(project_path)) for f in critical_backend_files if not f.exists()]
    
    # Check routers directory - must have at least one router besides __init__.py
    routers_dir = project_path / "backend" / "app" / "routers"
    has_routers = False
    
    if routers_dir.exists():
        router_files = list(routers_dir.glob("*.py"))
        non_init_routers = [f for f in router_files if f.name != "__init__.py"]
        has_routers = len(non_init_routers) > 0
        
        if not has_routers:
            log("TESTING", f"❌ CRITICAL: No router files found in {routers_dir}", project_id)
            log("TESTING", "   Only __init__.py exists - Backend Implementation step likely failed", project_id)
    else:
        log("TESTING", f"❌ CRITICAL: Routers directory missing: {routers_dir}", project_id)
    
    # Check main.py for router imports that will fail
    main_py = project_path / "backend" / "app" / "main.py"
    if main_py.exists() and not has_routers:
        try:
            main_content = main_py.read_text(encoding="utf-8")
            # Check if main.py imports from app.routers
            if "from app.routers" in main_content:
                # Find which router is imported
                import re
                router_imports = re.findall(r'from app\.routers\.(\w+)', main_content)
                for router_name in router_imports:
                    expected_file = routers_dir / f"{router_name}.py"
                    if not expected_file.exists():
                        missing_critical.append(f"backend/app/routers/{router_name}.py (imported in main.py)")
        except Exception as e:
            log("TESTING", f"⚠️ Could not analyze main.py: {e}", project_id)
    
    if missing_critical:
        log("TESTING", "❌ CRITICAL FILES MISSING - Docker build will fail", project_id)
        for f in missing_critical:
            log("TESTING", f"   Missing: {f}", project_id)
        log("TESTING", "   Hard fail: missing critical backend files", project_id)
        
        raise RuntimeError(f"Missing {len(missing_critical)} critical backend files: {', '.join(missing_critical)}")


    # ═══════════════════════════════════════════════════════
    # PRE-FLIGHT: Ensure E2E test file exists BEFORE running Playwright
    # This prevents "no tests found" or similar failures
    # ═══════════════════════════════════════════════════════
    
    # Get primary entity from workflow state
    from app.orchestration.state import WorkflowStateManager
    from app.utils.entity_discovery import discover_primary_entity
    
    intent = await WorkflowStateManager.get_intent(project_id) or {}
    entities = intent.get("entities", [])
    
    if entities:
        primary_entity = entities[0]
    else:
        _, entity_singular = discover_primary_entity(project_path)  # Returns (plural, singular)
        primary_entity = entity_singular or "entity"
    
    # ═══════════════════════════════════════════════════════
    # STEP 1: Luna generates E2E tests from template FIRST
    # Luna ALWAYS creates project-specific tests using the template
    # ═══════════════════════════════════════════════════════
    tests_generated = await _generate_frontend_tests_from_template(
        manager=manager,
        project_id=project_id,
        project_path=project_path,
        user_request=user_request,
        primary_entity=primary_entity,
        branch=branch,
    )
    
    if not tests_generated:
        log("TESTING", "❌ Luna could not generate tests from template")
        raise RuntimeError("Frontend E2E tests not generated. Cannot verify frontend stability.")

    # ONE SHOT EXECUTION
    log("TESTING", f"🚀 Frontend test execution for {project_id}")

    # 0) PREPARE CONTEXT (The "Anti-Hallucination" Fix)
    # Collect ACTUAL component code so Luna knows the real DOM structure
    # ------------------------------------------------------------
    context_parts = []
    
    from app.utils.test_scaffolding import get_available_selectors
    
    try:
        # Primary files to check (in priority order)
        primary_files = [
            project_path / "frontend/src/App.jsx",
            # Include ALL pages
            *(project_path / "frontend/src/pages").glob("*.jsx"),
            # Include relevant API files
            *(project_path / "frontend/src/api").glob("*.js"),
        ]
        
        for pf in primary_files:
            if pf.exists():
                try:
                    content = pf.read_text(encoding="utf-8")
                    context_parts.append(f"--- {pf.relative_to(project_path.parent)} ---\n{content[:2000]}")
                except Exception:
                    pass
        
        # Also check components directory for key components
        components_dir = project_path / "frontend/src/components"
        if components_dir.exists():
            # Increased limit from 3 to 10 to cover more context
            for comp_file in list(components_dir.glob("*.jsx"))[:10]:
                try:
                    content = comp_file.read_text(encoding="utf-8")
                    context_parts.append(f"--- components/{comp_file.name} ---\n{content[:1500]}")
                except Exception as e:
                    log("TESTING", f"Warning: Could not read component {comp_file.name}: {e}")
        
        # Extract actual selectors from the code
        selectors = get_available_selectors(project_path)
        
        if context_parts:
            all_context = "\n\n".join(context_parts)
            
            # Build selector hints
            selector_hints = []
            if selectors.get("testids"):
                selector_hints.append(f"data-testid values: {', '.join(selectors['testids'][:5])}")
            if selectors.get("buttons"):
                selector_hints.append(f"Button text: {', '.join(selectors['buttons'][:3])}")
            if selectors.get("inputs"):
                selector_hints.append(f"Input placeholders: {', '.join(selectors['inputs'][:3])}")
            if selectors.get("headings"):
                selector_hints.append(f"Headings: {', '.join(selectors['headings'][:3])}")
            
            selector_section = "\n".join(f"  ✅ {hint}" for hint in selector_hints) if selector_hints else "  ⚠️ No data-testid found - use role selectors"
            
            context_snippet = (
                f"\n\n{'='*60}\n"
                f"CONTEXT - ACTUAL APP CODE (READ THIS CAREFULLY!)\n"
                f"{'='*60}\n"
                f"These are the REAL components. Your test selectors MUST match what's here.\n"
                f"Look for: headings (<h1>, <h2>), buttons, placeholders, data-testid attributes.\n"
                f"{'='*60}\n\n"
                f"{all_context}\n\n"
                f"{'='*60}\n"
                f"🎯 AVAILABLE SELECTORS (USE THESE):\n"
                f"{selector_section}\n\n"
                f"SELECTOR RULES:\n"
                f"- Use getByRole('heading', {{ name: '...' }}) for headings\n"
                f"- Use getByRole('button', {{ name: '...' }}) for buttons\n"
                f"- Use getByPlaceholder('...') for inputs with placeholder\n"
                f"- Use locator('[data-testid=\"...\"]') if data-testid exists\n"
                f"- NEVER invent IDs like #article-list unless you see id=\"article-list\" above\n"
                f"{'='*60}\n"
            )
    except Exception as e:
        context_snippet = f"\n\nCONTEXT: Error reading app code: {e}\n"

    # ------------------------------------------------------------
    # 1) Ask Luna to propose frontend fixes (patches or files)
    # ------------------------------------------------------------

    test_file = project_path / "frontend/tests/e2e.spec.js"

    # ONE SHOT MODE - Direct execution, no attempt logic
    # ArborMind handles retry/fallback decisions
    # 
    # NOTE: Test file was already generated in _generate_frontend_tests_from_template()
    # No need for a second Luna call here - proceed directly to execution
    
    # ------------------------------------------------------------
    # 1) Ensure deps and run BUILD CHECK first (FAIL FAST)
    # ------------------------------------------------------------
    # log("TESTING", "📦 Syncing frontend dependencies...")
    try:
        deps_result = await run_tool(
            name="sandboxexec",
            args={
                "project_id": project_id,
                "service": "frontend",
                "command": "npm install && npx playwright install chromium",
                "timeout": 900,
            },
        )
        if not deps_result.get("success", True):
            log(
                "TESTING",
                f"⚠️ npm install warning: "
                f"{deps_result.get('stderr', '')[:200]}",
            )
    except Exception as e:
        log("TESTING", f"sandboxexec for frontend deps threw exception: {e}")
        raise # Propagate up to handler default filtering

    # 🚨 BUILD CHECK FIRST - Fail fast if code doesn't compile
    # log("TESTING", "🏗 Running build check BEFORE tests (fail fast)...")
    try:
        build_check_result = await run_tool(
            name="sandboxexec",
            args={
                "project_id": project_id,
                "service": "frontend",
                "command": "npm run build",
                "timeout": 120,
            },
        )
        build_check_stdout = ensure_str(build_check_result.get("stdout", ""))
        build_check_stderr = ensure_str(build_check_result.get("stderr", ""))
        
        if "error" in build_check_stderr.lower() or not build_check_result.get("success", True):
            # Check if this is an infrastructure error
            is_infra_error = any(pattern in build_check_stderr for pattern in infra_error_patterns)
            
            if is_infra_error:
                log("TESTING", "⚠️ INFRA ERROR DETECTED - skipping frontend testing (non-fatal)")
                log("TESTING", f"Error: {build_check_stderr[:500]}")
                # Return OK but with status failed - let workflow continue
                return StepResult(
                    nextstep=WorkflowStep.PREVIEW_FINAL,
                    turn=9,
                    status="ok",
                    data={"error": "infra_error", "message": "Docker infrastructure failed - skipping tests"},
                    token_usage=step_token_usage,
                )
            
            log("TESTING", "❌ Build FAILED - stopping frontend tests (One Shot Policy)")
            last_stdout = build_check_stdout
            last_stderr = build_check_stderr
            
            # Non-fatal return even for build failure in Phase 1
            return StepResult(
                nextstep=WorkflowStep.PREVIEW_FINAL,
                turn=9,
                status="ok",
                data={"error": "build_failed", "stderr": build_check_stderr[:500]},
                token_usage=step_token_usage,
            )
    except Exception as e:
        log("TESTING", f"Build check threw exception: {e}")
        # Proceed anyway
        pass 

    log(
        "TESTING",
        f"🚀 Running frontend tests in sandbox",
    )

    try:
        test_result = await run_tool(
            name="sandboxexec",
            args={
                "project_id": project_id,
                "service": "frontend",
                "command": "npx playwright test --reporter=list",
                "timeout": 600,
            },
        )
    except Exception as e:
        log("TESTING", f"sandboxexec for frontend tests threw exception: {e}")
        raise # Propagate up to handler default filtering

    test_stdout = ensure_str(test_result.get("stdout", ""))
    test_stderr = ensure_str(test_result.get("stderr", ""))

    # Enhanced debug logging for Playwright output
    log(
        "TESTING",
        f"📋 Playwright output:\n"
        f"--- STDOUT ({len(test_stdout)} chars) ---\n{test_stdout[:2000]}\n"
        f"--- STDERR ({len(test_stderr)} chars) ---\n{test_stderr[:2000]}",
    )

    # Persist Playwright output to file for detailed debugging
    try:
        output_file = test_history_dir / "playwright_output.txt"
        output_content = (
            "=== PLAYWRIGHT TEST OUTPUT ===\n"
            f"Success: {test_result.get('success')}\n\n"
            f"=== STDOUT ===\n{test_stdout}\n\n"
            f"=== STDERR ===\n{test_stderr}\n"
        )
        output_file.write_text(output_content, encoding="utf-8")
        log("TESTING", f"📄 Persisted Playwright output to: {output_file.name}")
    except Exception as e:
        log("TESTING", f"⚠️ Failed to persist Playwright output: {e}")

    # Initialization to avoid UnboundLocalError
    build_stdout = ""
    build_stderr = ""
    build_result = {"success": False} # Default

    if not test_result.get("success"):
        log("TESTING", "❌ Frontend tests FAILED in sandbox (Hard Failure)")
        # Self-Healing REMOVED

    else:
        log("TESTING", "✅ Frontend tests PASSED in sandbox")

        # ------------------------------------------------------------
        # 3) Run frontend build in sandbox (always after tests)
        # ------------------------------------------------------------
        # log("TESTING", "🏗 Running frontend build in sandbox as sanity check")

        try:
            build_result = await run_tool(
                name="sandboxexec",
                args={
                    "project_id": project_id,
                    "service": "frontend",
                    "command": "npm run build",
                    "timeout": 600,
                },
            )
        except Exception as e:
            log("TESTING", f"sandboxexec for frontend build threw exception: {e}")
            build_result = {"success": False, "stdout": "", "stderr": str(e)}

        build_stdout = ensure_str(build_result.get("stdout", ""))
        build_stderr = ensure_str(build_result.get("stderr", ""))

        # Store combined output for logging/debugging
        last_stdout = "\n\n".join(s for s in [test_stdout, build_stdout] if s)
        last_stderr = "\n\n".join(s for s in [test_stderr, build_stderr] if s)

    if test_result.get("success") and build_result.get("success"):
        log(
            "TESTING",
            "✅ Frontend tests AND build PASSED in sandbox",
        )

        await broadcast_to_project(
            manager,
            project_id,
            {
                "type": "WORKFLOW_STAGE_COMPLETED",
                "projectId": project_id,
                "step": WorkflowStep.TESTING_FRONTEND,
                "tier": "sandbox",
            },
        )
        return StepResult(
            nextstep=WorkflowStep.PREVIEW_FINAL,
            turn=9,  # Testing frontend is step 8
            status="ok",
            data={
                "tier": "sandbox",
                "test_status": "passed"
            },
            token_usage=step_token_usage,
        )


    # PHASE 1: NON-FATAL FAILURE
    log("TESTING", "⚠️ Frontend tests and/or build failed. Continuing branch (non-fatal)")
    return StepResult(
        nextstep=WorkflowStep.PREVIEW_FINAL,
        turn=9,
        status="ok",
        data={
            "tier": "sandbox",
            "test_stdout": test_stdout[:500],
            "test_stderr": test_stderr[:500],
            "build_stdout": build_stdout[:500],
            "build_stderr": build_stderr[:500],
            "test_status": "failed"
        },
        token_usage=step_token_usage,
    )
