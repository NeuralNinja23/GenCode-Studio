# app/supervision/supervisor.py
"""
Marcus supervision of agent output.
"""
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional



from app.core.logging import log, log_section, log_files, log_result
from app.core.logging import log, log_section, log_files, log_result
from app.llm import call_llm, call_llm_with_usage
from app.llm.prompts import MARCUS_SUPERVISION_PROMPT
from app.tracking.quality import track_quality_score
from app.orchestration.checkpoint import CheckpointManagerV2
from app.arbormind.observation.execution_ledger import record_supervisor_event, get_current_run_id


async def marcus_supervise(
    project_id: str,
    manager: Any,
    agent_name: str,
    step_name: str,
    agent_output: Dict[str, Any],
    contracts: str = "",
    user_request: str = "",
) -> Dict[str, Any]:
    """
    Marcus reviews an agent's output for quality and correctness.
    
    Returns:
        Dict with: approved, quality_score, issues, feedback, corrections
    """
    from app.orchestration.utils import broadcast_to_project
    
    # Build file summary for Marcus
    files = agent_output.get("files", [])
    
    # ═══════════════════════════════════════════════════════
    # LAYER 1: PRE-FLIGHT VALIDATION (0.5s, catches 90% of issues)
    # ═══════════════════════════════════════════════════════
    # This runs BEFORE the expensive LLM review, saving $0.10+ per rejection
    
    from app.validation import preflight_check
    
    # Run pre-flight validation on all files
    cleaned_output, rejection_reasons = preflight_check(agent_output)
    
    # If pre-flight failed, reject immediately
    # If pre-flight failed, reject immediately
    if rejection_reasons:
        log("SUPERVISION", f"❌ Pre-flight failed: {rejection_reasons[0]}", project_id)
        
        # ════════════════════════════════════════════════════════
        # FAILURE LEARNING: Record Pre-Flight Failure (Syntax/Structure)
        # ════════════════════════════════════════════════════════
        # ════════════════════════════════════════════════════════


        # Fix formatting for pre-flight errors
        fixed_reasons = [f"- {r}" for r in rejection_reasons]
        
        # 🧠 SQLITE: Record pre-flight rejection
        _record_verdict(step_name, agent_name, False, 1, rejection_reasons)
        
        # 🧠 ARBORMIND LEARNING: Ingest F2 (Parse Failure) - DISABLED FOR PHASE 3
        # run_id = get_current_run_id()
        # if run_id:
        #     ingest_parse_failure(
        #         run_id=run_id,
        #         step=step_name,
        #         error_message=f"Pre-flight validation failed: {'; '.join(rejection_reasons)}",
        #         agent=agent_name,
        #     )
        
        return {
            "approved": False,
            "quality_score": 1,
            "issues": rejection_reasons,
            "feedback": "Your code failed pre-flight validation:\n" + "\n".join(fixed_reasons) + "\n\nFix these syntax errors immediately.",
            "corrections": []
        }


    # Update output with cleaned code (e.g. fixed newlines)
    parsed = cleaned_output
    files = parsed.get("files", []) # Update files reference

    # ═══════════════════════════════════════════════════════
    # LAYER 1.5: HDAP COMPLETENESS CHECK
    # ═══════════════════════════════════════════════════════
    # Reject if output was truncated (missing END_FILE markers)
    
    is_complete = parsed.get("complete", True)  # Default True for legacy
    incomplete_files = parsed.get("incomplete_files", [])
    
    if not is_complete and incomplete_files:
        log("SUPERVISION", f"❌ REJECTED: Truncated output - incomplete files: {incomplete_files}", project_id)
        
        # 🧠 SQLITE: Record truncation rejection
        issues = [f"Output was truncated. Incomplete files: {', '.join(incomplete_files)}"]
        _record_verdict(step_name, agent_name, False, 1, issues)
        
        # 🧠 ARBORMIND LEARNING: Ingest F3 (Truncation) - DISABLED FOR PHASE 3
        # run_id = get_current_run_id()
        # if run_id:
        #     ingest_truncation(
        #         run_id=run_id,
        #         step=step_name,
        #         error_message=f"Output truncated. Incomplete files: {', '.join(incomplete_files)}",
        #         agent=agent_name,
        #     )
        
        return {
            "approved": False,
            "quality_score": 1,
            "issues": issues,
            "feedback": "Your output was cut off. Each file MUST end with <<<END_FILE>>>. Increase token limit or generate fewer files.",
            "corrections": []
        }

    # ═══════════════════════════════════════════════════════
    # LAYER 1.6: ZERO-FILE CHECK (PHASE 4: Cognitive)
    # ═══════════════════════════════════════════════════════
    # PHASE 4 CHANGE: Zero files is only fatal if step doesn't allow partial
    # Cognition steps (analysis, etc.) may produce no files
    
    from app.supervision.tiered_review import get_review_level, ReviewLevel
    from app.arbormind.cognition.partial_output import allows_partial_output
    
    is_cognition_step = step_name.lower() in ["classification", "routing", "refine"]

    
    if not files and not is_cognition_step:
        # Check if this step allows partial (which includes zero temporarily)
        # Only FATAL if this is a step that absolutely requires output
        step_requires_output = step_name.lower() in [
            "architecture", "backend_models", "frontend_mock", "frontend (mock data)", 
            "backend_routers", "system_integration", "testing_backend"
        ]
        
        if step_requires_output:
            # Zero files in a must-produce step = REJECTION
            log("SUPERVISION", f"❌ REJECTED: Zero files produced in critical step '{step_name}'", project_id)
            
            # 🧠 SQLITE: Record zero-file rejection
            issues = ["No files were generated. This step must produce at least one file."]
            _record_verdict(step_name, agent_name, False, 0, issues)
            
            # 🧠 ARBORMIND LEARNING: Ingest F1 (Invariant Violation - zero files) - DISABLED FOR PHASE 3
            # run_id = get_current_run_id()
            # if run_id:
            #     ingest_invariant_violation(
            #         run_id=run_id,
            #         step=step_name,
            #         error_message="Zero files generated in critical step",
            #         scope=FailureScope.STEP_LOCAL,
            #         agent=agent_name,
            #     )
            
            return {
                "approved": False,
                "quality_score": 0,
                "issues": issues,
                "feedback": "You MUST generate files using <<<FILE: path>>> ... <<<END_FILE>>> markers.",
                "corrections": [],
                "failure_severity": "fatal"  # Phase 2: Mark severity
            }
        else:
            # Non-critical step with zero files - warn but don't fail
            log("SUPERVISION", f"⚠️ WARNING: Zero files in '{step_name}' (non-critical)", project_id)
            # Continue to LLM review to see if there's useful metadata
    
    # ═══════════════════════════════════════════════════════
    # LAYER 1.6: TIERED REVIEW (Smart Filtering)
    # ═══════════════════════════════════════════════════════
    # Check if files actually need LLM review
    
    needs_full_review = False
    
    if not files:
        # Cognition-only step (analysis, classification) - no LLM review needed
        needs_full_review = False
    else:
        for f in files:
            level = get_review_level(f.get("path", ""))
            if level == ReviewLevel.FULL or step_name.lower() == "architecture":
                needs_full_review = True
                break
    
    if not needs_full_review:
        log("SUPERVISION", "⏭️ Skipping full review (Tiered Strategy): No critical files modified", project_id)
        
        # 🧠 SQLITE: Record tiered auto-approval
        _record_verdict(step_name, agent_name, True, 8, [])
        
        return {
            "approved": True,
            "quality_score": 8, # Assume good if it passes pre-flight
            "issues": [],
            "feedback": "Auto-approved via Tiered Review (Pre-flight passed)",
            "corrections": []
        }

    # ═══════════════════════════════════════════════════════
    # LAYER 2: MARCUS LLM REVIEW (The Heavy Lifter)
    # ═══════════════════════════════════════════════════════
    
    # Build COMPLETE file content for Marcus review
    # IMPORTANT: No truncation! Marcus needs full visibility to avoid false rejections
    files_summary = ""
    for i, f in enumerate(files):  # Review ALL files, not just first 5
        path = f.get("path", "unknown")
        content = f.get("content", "")
        files_summary += f"\n--- File {i+1}: {path} ({len(content)} bytes) ---\n" + content + "\n"

    # Also include diff/patch if present
    diff = agent_output.get("diff") or agent_output.get("patch") or ""
    if diff:
         files_summary += f"\n--- PATCH/DIFF ---\n{diff[:2000]}\n"
    
    patches = agent_output.get("patches")
    if patches and isinstance(patches, list):
         files_summary += f"\n--- JSON PATCHES ---\n{json.dumps(patches, indent=2)[:2000]}\n"
    
    # Step-aware evaluation criteria (DYNAMIC: each step has different expectations)
    step_context = ""
    user_context = f"USER REQUEST: {user_request[:500]}"  # Default: include user request
    
    if "Mock" in step_name or "mock" in step_name.lower():
        step_context = """
⚠️ IMPORTANT: This is the FRONTEND_MOCK step.

EXPECTATIONS FOR THIS STEP:
- Using mock data is EXPECTED and CORRECT at this stage
- Placeholder text like "coming soon", "chart placeholder", "loading..." is ALLOWED
- Incomplete features (e.g., charts not implemented yet) are ACCEPTABLE
- DO NOT reject for: "using mock data", "placeholder content", "chart not implemented"

WHAT TO CHECK:
- Component structure and JSX syntax
- Proper data-testid attributes on interactive elements
- UI layout and component organization
- State management for local CRUD operations

WHAT NOT TO CHECK:
- Real API calls (those come in FRONTEND_INTEGRATION step)
- Complete chart implementations (can be placeholder)
- Full feature parity with user request (incremental development)
"""
    elif "backend" in step_name.lower() and "models" in step_name.lower():
        step_context = f"""
⚠️ IMPORTANT: This is the BACKEND_MODELS step.
- Derek generates Beanie Documents and Pydantic schemas in models.py
- Ensure models match the data structures defined in architecture.md
- Check for: PydanticObjectId types, correct field types, Settings class name

EVALUATE AGAINST THE ARCHITECTURE CONTRACT BELOW:
{contracts[:15000] if contracts else "No architecture contract provided"}
"""
        user_context = ""
    elif "backend" in step_name.lower() and "routers" in step_name.lower():
        step_context = f"""
⚠️ IMPORTANT: This is the BACKEND_ROUTERS step.
- Derek implements FastAPI routers using the models generated in Step 3.
- Check for: Correct model imports, Beanie async calls, PydanticObjectId usage in paths.
- DO NOT reject for missing wiring in main.py (that happens in Step 5).

EVALUATE AGAINST THE ARCHITECTURE CONTRACT BELOW:
{contracts[:15000] if contracts else "No architecture contract provided"}
"""
        user_context = ""
    elif "backend" in step_name.lower() and "implementation" in step_name.lower():
        # DYNAMIC FIX: For backend implementation, evaluate against the Architecture Contract
        # Derek implements CRUD for detected entity, not the user's full vision
        step_context = f"""
⚠️ IMPORTANT: This is the BACKEND_IMPLEMENTATION step.
- Derek implements STANDARD CRUD operations for the entity defined in architecture.md
- Complex business logic (NLP, AI, external APIs, etc.) is NOT expected here
- The user request describes the FINAL product vision, not what Derek builds now
- Only evaluate if Derek's code correctly implements the Architecture Contract (Domain Models + Capability Guarantees)
- Focus on: proper FastAPI routes, Beanie models, correct CRUD operations

EVALUATE AGAINST THE ARCHITECTURE CONTRACT BELOW:
{contracts[:15000] if contracts else "No architecture contract provided"}
"""
        # Don't include raw user request for backend - prevents scope confusion
        user_context = ""  # Architecture provides the evaluation criteria instead

    elif "Integration" in step_name:
        step_context = """
⚠️ IMPORTANT: This is the FRONTEND_INTEGRATION step.
- Mock data should now be replaced with real API calls
- Check for: proper API imports, error handling, loading states
"""
    elif "Test" in step_name:
        step_context = """
⚠️ IMPORTANT: This is a TESTING step.
- Tests should be minimal and reliable (smoke tests are OK)
- Don't reject for "not enough tests" - some coverage is better than none
- Focus on: test will run, selectors are valid, no syntax errors
"""
    
    review_prompt = f"""
Review this output from {agent_name} for the {step_name} step.

{user_context}
{step_context}

AGENT OUTPUT:
{files_summary}

{f"API CONTRACTS (for reference):{chr(10)}{contracts[:15000]}" if contracts and user_context else ""}

Evaluate using these checklists:

BACKEND: Check for async def typos, mutable defaults like [], deprecated .dict(), missing DB name
FRONTEND: Check for duplicated API code, empty Dashboard, missing data-testid
TESTS: Tests should run without errors, use valid selectors

⚠️ BE LENIENT: Approve code that will WORK, even if imperfect.
Only REJECT for critical syntax errors or completely broken code.

RESPOND WITH JSON:
{{
  "thinking": "Your detailed analysis of the code quality...",
  "approved": true/false,
  "quality_score": 1-10,
  "issues": ["issue1", "issue2"],
  "feedback": "What to fix",
  "corrections": [{{"file": "...", "problem": "...", "fix": "..."}}]
}}
"""
    
    try:
        # Use step-specific token allocation for Marcus reviews
        from app.orchestration.token_policy import get_tokens_for_step
        # Marcus gets same tokens as the step he's reviewing (needs to understand what was generated)
        review_tokens = get_tokens_for_step(step_name, is_retry=False) if step_name else 10000
        # Cap at reasonable limit for reviews (don't need full generation tokens)
        review_tokens = min(review_tokens, 12000)
        
        llm_result = await call_llm_with_usage(
            prompt=review_prompt,
            system_prompt=MARCUS_SUPERVISION_PROMPT,
            max_tokens=review_tokens,
        )
        response = llm_result.get("text", "")
        usage = llm_result.get("usage", {})

        # Track cost
        if usage:
             try:
                 budget = get_budget_manager(project_id)
                 budget.register_usage(
                     step=f"{step_name}:Review",
                     input_tokens=usage.get("input", 0),
                     output_tokens=usage.get("output", 0),
                     model="gemini-2.0-flash-exp"
                 )
             except Exception:
                 pass # Don't fail on budget tracking
        
        # Use sanitize + parse_json (designed for generic JSON, not just files)
        from app.utils.parser import sanitize_marcus_output, parse_json
        
        result = None
        try:
            # First, sanitize the response (removes markdown fences, LLM chatter, etc.)
            sanitized = sanitize_marcus_output(response)
            result = parse_json(sanitized)
            
            # Validate we got a supervision result, not a files array
            if isinstance(result, dict) and "approved" not in result and "files" in result:
                # parse_json returned files instead of review - this is wrong
                raise ValueError("Got files result instead of review result")
                
        except Exception as e:
            log("MARCUS", f"❌ Failed to parse review: {e}", project_id=project_id)
            raise RuntimeError(f"Marcus review parsing failed. Response: {response[:200]}")
        
        approved = result.get("approved", True)
        quality = result.get("quality_score", 7)
        thinking = result.get("thinking", "")
        issues = result.get("issues", [])
        feedback = result.get("feedback", "")
        
        # ============================================================
        # PRIORITY 4: Categorize issues by severity
        # ============================================================
        # Only reject for CRITICAL issues; warnings are logged but don't block
        if not approved and issues:
            critical_issues, warnings = await postprocess_marcus_issues(quality, issues)
            
            if not critical_issues:
                # All issues are just warnings - upgrade to approved with warnings
                approved = True
                quality = max(quality, 7)  # Bump quality if it was low just for warnings
                result["approved"] = True
                result["quality_score"] = quality
                result["warnings"] = warnings  # Store for logging
                result["issues"] = []  # Clear issues since they're just warnings
            else:
                # There are critical issues - keep rejection
                result["critical_issues"] = critical_issues
                result["warnings"] = warnings

        
        # NOTE: Marcus's thinking is broadcast to UI (below) but not logged to server console
        # This reduces log noise while keeping the user-facing feature
        
        # ONE LINE LOG: Verdict only
        verdict = "✅ Approved" if approved else "❌ Rejected"
        log("SUPERVISION", f"{verdict} ({quality}/10)")
        
        # Broadcast review result
        if approved:
            await broadcast_to_project(
                manager,
                project_id,
                {
                    "type": "AGENT_LOG",
                    "scope": "MARCUS",
                    "message": f"✅ Approved {agent_name}'s work - Quality: {quality}/10",
                    "data": {"thinking": thinking[:500], "quality": quality},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        else:
            await broadcast_to_project(
                manager,
                project_id,
                {
                    "type": "AGENT_LOG",
                    "scope": "MARCUS",
                    "message": f"⚠️ {agent_name} needs corrections ({len(issues)} issues) - Quality: {quality}/10",
                    "data": {"thinking": thinking[:500], "issues": issues[:5], "feedback": feedback},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        
        # 🧠 OBSERVATION: Record Supervisor Event
        run_id = get_current_run_id()
        if run_id:
            record_supervisor_event(
                run_id=run_id,
                step=step_name,
                agent=agent_name,
                verdict="APPROVED" if approved else "REJECTED",
                quality=quality,
                issues=issues if not approved else []
            )
        
        # 🧠 ARBORMIND LEARNING: Ingest F4 (Quality Rejection) if rejected - DISABLED FOR PHASE 3
        # if not approved:
        #     run_id = get_current_run_id()
        #     if run_id:
        #         ingest_quality_rejection(
        #             run_id=run_id,
        #             step=step_name,
        #             rejection_reasons=f"Quality: {quality}/10. Issues: {'; '.join(issues[:5])}",
        #             agent=agent_name,
        #         )
        
        return result
        
    except Exception as e:
        # ============================================================
        # CLASSIFY ERROR TYPE
        # ============================================================
        error_str = str(e).lower()
        is_provider_error = (
            "provider error" in error_str or
            "overloaded" in error_str or
            "503" in error_str or
            "rate limit" in error_str or
            "429" in error_str or
            "unavailable" in error_str
        )
        
        if is_provider_error:
            # TRANSIENT_INFRA_FAILURE: Provider/API issue, not cognitive failure
            # Don't penalize the agent or record as a quality failure
            log("MARCUS", f"⚠️ Review failed: TRANSIENT_INFRA_FAILURE ({str(e)[:100]})", project_id=project_id)
            # 🧠 SQLITE: Record infrastructure failure (as verdict=rejected)
            _record_verdict(step_name, agent_name, False, 3, [str(e)])
            
            # 🧠 ARBORMIND LEARNING: Ingest F9 (External Failure) - DISABLED FOR PHASE 3
            # run_id = get_current_run_id()
            # if run_id:
            #     ingest_external_failure(
            #         run_id=run_id,
            #         step=step_name,
            #         external_error=f"TRANSIENT_INFRA_FAILURE: {str(e)}",
            #         agent=agent_name,
            #     )
            
            return {
                "approved": False,
                "quality_score": 3,
                "issues": [f"Infrastructure error (retryable): {str(e)[:150]}"],
                "feedback": "Temporary infrastructure issue. Please retry - this is not a code quality problem.",
                "corrections": [],
                "thinking": f"TRANSIENT_INFRA_FAILURE: {e}",
                "supervision_error": True,
                "error_type": "TRANSIENT_INFRA_FAILURE"
            }
        else:
            # Genuine supervision error (could be cognitive/parsing issue)
            # Genuine supervision error (could be cognitive/parsing issue)
            log("MARCUS", f"⚠️ Review failed: {e} - marking as NOT approved", project_id=project_id)
            
            # 🧠 SQLITE: Record supervision error
            _record_verdict(step_name, agent_name, False, 3, [f"Supervision error: {e}"])
            
            return {
                "approved": False, 
                "quality_score": 3, 
                "issues": [f"Supervision error: {str(e)[:200]}"], 
                "feedback": "Marcus supervision encountered an error. Please retry.", 
                "corrections": [], 
                "thinking": f"Review error: {e}",
                "supervision_error": True
            }


async def categorize_issue_severity(issue: str) -> str:
    """
    Categorize Marcus's issues into 'critical' or 'warning' using simple heuristics.
    """
    lower_issue = issue.lower()
    
    # Warning patterns - style, suggestions, nice-to-haves
    warning_keywords = [
        "style", "suggest", "optimiz", "convention", "mock", "formatting", 
        "indentation", "comment", "placeholder", "future", "todo", "naming",
        "preference", "maintainability", "readability"
    ]
    
    if any(w in lower_issue for w in warning_keywords):
        return "warning"
    
    # Default to critical for safety
    return "critical"


async def postprocess_marcus_issues(quality: int, issues: List[str]):
    """
    Split issues into critical (must fix) and warnings (nice-to-have).
    
    Returns: (critical_issues, warnings)
    """
    critical = []
    warnings = []
    
    for issue in issues or []:
        severity = await categorize_issue_severity(issue)
        if severity == "critical":
            critical.append(issue)
        else:
            warnings.append(issue)
    
    return critical, warnings



def _extract_archetype(user_request: str) -> str:
    """
    Extract an archetype identifier from the user request.
    
    Examples:
    - "Create a bug tracking system" → "bug_tracking"
    - "Build an admin dashboard" → "admin_dashboard"
    - "Make an e-commerce store" → "ecommerce"
    """
    import re
    
    # Common archetype patterns
    patterns = [
        (r"(admin|management)\s*(dashboard|panel)", "admin_dashboard"),
        (r"(bug|issue)\s*(track|report)", "bug_tracking"),
        (r"(e-?commerce|shop|store)", "ecommerce"),
        (r"(blog|article|post|cms)", "blog_cms"),
        (r"(todo|task|project)\s*(list|manager)?", "task_manager"),
        (r"(chat|messag|real-?time)", "chat_app"),
        (r"(crud|api|backend)", "crud_api"),
        (r"(portfolio|resume|cv)", "portfolio"),
        (r"(social|feed|timeline)", "social_app"),
    ]
    
    request_lower = user_request.lower()
    
    for pattern, archetype in patterns:
        if re.search(pattern, request_lower):
            return archetype
    
    # Fallback: extract first two significant words
    words = re.findall(r'\b[a-z]{3,}\b', request_lower)
    # Filter common words
    stop_words = {"create", "build", "make", "please", "want", "need", "with", "that", "this", "the", "for"}
    significant = [w for w in words if w not in stop_words][:2]
    
    return "_".join(significant) if significant else "generic"


async def supervised_agent_call(
    project_id: str,
    manager: Any,
    agent_name: str,
    step_name: str,
    base_instructions: str,
    project_path: Path,
    user_request: str,
    contracts: str = "",
    temperature_override: Optional[float] = None,
    is_retry: bool = False,
) -> Dict[str, Any]:
    """
    Call an agent with Marcus supervision (ArborMind Muscle).
    """
    from app.tools import run_tool
    from app.llm.prompt_management import filter_files_for_step
    import os

    # 1. Prepare Context (Muscle)
    archetype = _extract_archetype(user_request)
    vibe = "minimal_light"
    if any(word in user_request.lower() for word in ["dark", "hacker", "terminal"]):
        vibe = "dark_hacker"
    
    step_id = step_name.lower().replace(" ", "_").replace("(", "").replace(")", "")


    # Read project files (Muscle - context preparation)
    def _read_files():
        files = []
        for root, _, filenames in os.walk(project_path):
            for filename in filenames:
                if filename.endswith(('.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.md')):
                    file_path = Path(root) / filename
                    rel_path = file_path.relative_to(project_path)
                    if any(skip in str(rel_path) for skip in ['node_modules', 'dist', '__pycache__', '.git']):
                        continue
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        if len(content) < 50000:
                            files.append({"path": str(rel_path).replace("\\", "/"), "content": content})
                    except Exception:
                        pass
        return files
    
    all_files = await asyncio.to_thread(_read_files)
    relevant_files = filter_files_for_step(step_id, all_files)

    log_section("SUPERVISION", f"🔄 {agent_name} - {step_name}", project_id)


    # 2. Execute Sub-Agent (Muscle)
    tool_args = {
        "sub_agent": agent_name,
        "instructions": base_instructions,
        "user_request": user_request,  # CRITICAL: Pass user request to agent
        "project_path": str(project_path),
        "project_id": project_id,
        "step_name": step_id,
        "archetype": archetype,
        "vibe": vibe,
        "files": relevant_files,
        "contracts": contracts[:15000] if contracts else "",
        "temperature_override": temperature_override,
        "is_retry": is_retry,
    }
    
    tool_result = await run_tool(name="subagentcaller", args=tool_args)
    raw_output = tool_result.get("output", {})
    token_usage = tool_result.get("token_usage", {"input": 0, "output": 0})
    
    # 3. Parse and Normalize Output (Muscle)
    if isinstance(raw_output, dict):
        parsed = raw_output
    else:
        from app.utils.parser import normalize_llm_output
        parsed = normalize_llm_output(str(raw_output), step_name=step_id)

    # 4. Verify with Marcus (Law/Gate)
    review = await marcus_supervise(
        project_id=project_id,
        manager=manager,
        agent_name=agent_name,
        step_name=step_name,
        agent_output=parsed,
        contracts=contracts,
        user_request=user_request,
    )

    quality = review.get("quality_score", 7)
    approved = review.get("approved", False)
    
    # 5. Persistence (Muscle)
    if approved:
        ckpt_mgr = CheckpointManagerV2(base_dir=str(project_path / ".fast_checkpoints"))
        await ckpt_mgr.save_project_snapshot(
            project_path,
            step_name,
            agent_name=agent_name,
            quality_score=quality,
            approved=True
        )
        
    return {
        "output": parsed,
        "approved": approved,
        "quality": quality,
        "token_usage": token_usage,
        "error": review.get("issues", ["Verification failed"])[0] if not approved else None
    }

    
