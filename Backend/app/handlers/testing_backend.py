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
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.types import ChatMessage, StepResult
from app.core.constants import WorkflowStep, TEST_FILE_MIN_TOKENS
from app.core.exceptions import RateLimitError
from app.handlers.base import broadcast_status, broadcast_agent_log
from app.core.logging import log
from app.tools import run_tool
from app.llm.prompts.derek import DEREK_TESTING_INSTRUCTIONS
from app.utils.parser import normalize_llm_output


# Constants from legacy
MAX_FILES_PER_STEP = 5
MAX_FILE_LINES = 400


from app.persistence.validator import validate_file_output



# Protected sandbox files - imported from centralized constants
from app.core.constants import PROTECTED_SANDBOX_FILES

# REMOVED: Restrictive allowed prefixes - agents can write to any file except protected ones


async def safe_write_llm_files_for_testing(
    manager: Any,
    project_id: str,
    project_path: Path,
    files: List[Dict[str, Any]],
    step_name: str,
) -> int:
    """Safely write test files with path validation."""
    from app.lib.file_system import get_safe_workspace_path, sanitize_project_id
    from app.orchestration.utils import broadcast_to_project
    
    if not files:
        return 0

    safe_ws = get_safe_workspace_path(project_path.parent, sanitize_project_id(project_path.name))
    safe_ws.mkdir(parents=True, exist_ok=True)

    written: List[Dict[str, Any]] = []

    for entry in files:
        if not isinstance(entry, dict):
            continue

        raw_path = entry.get("path") or entry.get("file") or entry.get("name") or entry.get("filename")
        content = entry.get("content") or entry.get("code") or entry.get("text") or ""

        if not raw_path:
            log("PERSIST", f"[TEST] Skipping file with no path: {entry.keys()}")
            continue

        rel_path = str(raw_path).replace("\\", "/").strip()

        # Only block protected infrastructure files - everything else is allowed
        if rel_path in PROTECTED_SANDBOX_FILES:
            log("PERSIST", f"[TEST] ❌ BLOCKED write to protected sandbox file: {rel_path}")
            continue
            
        # ... (rest of function unchanged, just closing the block for context)
        # Clean filename 
        clean_path = re.sub(r'[<>:"|?*]', "", rel_path)
        if not clean_path:
            log("PERSIST", f"[TEST] Invalid filename after cleaning: '{rel_path}', skipping")
            continue

        abs_path = safe_ws / Path(clean_path)
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            abs_path.write_text(content, encoding="utf-8")
        except Exception as e:
            log("PERSIST", f"[TEST] Failed to write {abs_path}: {e}")
            continue

        size_kb = round(len(content.encode("utf-8")) / 1024, 2)
        log("WRITE", f"[TEST] {abs_path} ({size_kb} KB)")
        written.append({"path": clean_path, "size_kb": size_kb})

    if written:
        await broadcast_to_project(
            manager,
            project_id,
            {
                "type": "WORKSPACE_UPDATED",
                "projectId": project_id,
                "filesWritten": written,
                "step": step_name,
            },
        )

    return len(written)


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

    # ═══════════════════════════════════════════════════════
    # PRE-FLIGHT: Ensure db.py exists (required for conftest.py)
    # ═══════════════════════════════════════════════════════
    db_file = project_path / "backend" / "app" / "db.py"
    if not db_file.exists():
        log("TESTING", "⚠️ backend/app/db.py missing - creating via self-healing...")
        try:
            from app.orchestration.self_healing_manager import SelfHealingManager
            healer = SelfHealingManager(project_path)
            if healer.repair("backend_db"):
                log("TESTING", "✅ Created db.py (connect_db/disconnect_db wrapper)")
            else:
                log("TESTING", "❌ Failed to create db.py - tests may fail")
        except Exception as e:
            log("TESTING", f"❌ Self-healing failed: {e}")

    # Ensure tests directory exists so Docker doesn't create it as root
    (project_path / "backend/tests").mkdir(parents=True, exist_ok=True)

    max_attempts = 3
    last_stdout: str = ""
    last_stderr: str = ""

    # ═══════════════════════════════════════════════════════
    # CRITICAL: Run tests FIRST before calling Derek
    # This ensures Derek has actual failure context, not guessing
    # ═══════════════════════════════════════════════════════
    
    # Get entity context for Derek
    from app.orchestration.state import WorkflowStateManager
    from app.orchestration.utils import pluralize
    
    intent = WorkflowStateManager.get_intent(project_id) or {}
    entities = intent.get("entities", [])
    primary_entity = entities[0] if entities else "item"
    primary_entity_plural = pluralize(primary_entity)
    
    # Get archetype for test guidance
    archetype = (intent.get("archetypeRouting") or {}).get("top") or "general"
    
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
        test_instructions = f"""
Write basic CRUD tests for the primary entity router:

- List, create, get-by-id, delete.
- 404 on unknown id.
- Response envelopes: {{ "data": <object> }} for single, {{ "data": [...], "total": int }} for lists.
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
                f"⚠️ Analysis skipped due to error. Derek will fix directly."
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
            DEREK_TESTING_INSTRUCTIONS + "\n"
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

                written_count = await safe_write_llm_files_for_testing(
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
            last_stdout = ""
            last_stderr = str(e)
            sandbox_result = {"success": False, "stdout": "", "stderr": str(e)}

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
                }
            )

        log(
            "TESTING",
            f"❌ Backend tests FAILED in sandbox on attempt {attempt}",
        )

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
