# app/supervision/supervisor.py
"""
Marcus supervision of agent output.
"""
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List



from app.core.logging import log, log_section, log_files, log_result
from app.llm import call_llm
from app.llm.prompts import MARCUS_SUPERVISION_PROMPT
# NOTE: Quality tracking kept, cost tracking moved to BudgetManager
from app.tracking.quality import track_quality_score
from app.tracking.snapshots import save_snapshot
from app.tracking.memory import remember_success, get_memory_hint
# NOTE: Removed DEFAULT_MAX_TOKENS - now using get_tokens_for_step() from token_policy

# V2 Modules for enhanced reliability
from app.orchestration.prompt_adapter import PromptAdapter
from app.orchestration.llm_output_integrity import LLMOutputIntegrity

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
    
    log_section("MARCUS", f"🔍 REVIEWING {agent_name}'s {step_name} OUTPUT", project_id)
    
    # Build file summary for Marcus
    files = agent_output.get("files", [])
    log_files("MARCUS", files, project_id)
    
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
        try:
            from app.learning.failure_store import get_failure_store
            store = get_failure_store()
            store.record_failure(
                archetype="generic", 
                agent=agent_name,
                step=step_name,
                error_type="preflight_validation",
                description=f"Pre-flight failed: {rejection_reasons[0]}",
                code_snippet="" # Can't easily isolate snippet without parsing, but error desc is good
            )
        except Exception:
            pass

        # Fix formatting for pre-flight errors
        fixed_reasons = [f"- {r}" for r in rejection_reasons]
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
    # LAYER 1.5: TIERED REVIEW (Smart Filtering)
    # ═══════════════════════════════════════════════════════
    # Check if files actually need LLM review
    
    from app.supervision.tiered_review import get_review_level, ReviewLevel
    
    needs_full_review = False
    
    if not files:
        # No files? Might be analysis/plan - review it (unless it's just a message)
        if agent_output.get("message") and not agent_output.get("files"):
             needs_full_review = False # Just a message, no review needed usually
        else:
             needs_full_review = True
    else:
        for f in files:
            level = get_review_level(f.get("path", ""))
            if level == ReviewLevel.FULL:
                needs_full_review = True
                break
    
    if not needs_full_review:
        log("SUPERVISION", "⏭️ Skipping full review (Tiered Strategy): No critical files modified", project_id)
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
    elif "backend" in step_name.lower() and "implementation" in step_name.lower():
        # DYNAMIC FIX: For backend implementation, evaluate against CONTRACTS only
        # Derek implements CRUD for detected entity, not the user's full vision
        step_context = f"""
⚠️ IMPORTANT: This is the BACKEND_IMPLEMENTATION step.
- Derek implements STANDARD CRUD operations for the entity defined in contracts
- Complex business logic (NLP, AI, external APIs, etc.) is NOT expected here
- The user request describes the FINAL product vision, not what Derek builds now
- Only evaluate if Derek's code correctly implements the API contracts below
- Focus on: proper FastAPI routes, Beanie models, correct CRUD operations

EVALUATE AGAINST THESE API CONTRACTS:
{contracts[:2000] if contracts else "No contracts provided - evaluate basic CRUD structure"}
"""
        # Don't include raw user request for backend - prevents scope confusion
        user_context = ""  # Contracts provide the evaluation criteria instead
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

{f"API CONTRACTS (for reference):{chr(10)}{contracts[:1000]}" if contracts and user_context else ""}

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
        
        response = await call_llm(
            prompt=review_prompt,
            system_prompt=MARCUS_SUPERVISION_PROMPT,
            max_tokens=review_tokens,
        )
        
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
                
        except Exception:
            # Try extracting JSON with regex as fallback (greedy match for outermost braces)
            import re
            
            # Use non-greedy matching to find JSON objects
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                except json.JSONDecodeError as json_err:
                    log("MARCUS", f"⚠️ JSON decode failed in regex extraction: {json_err}", project_id=project_id)
                    pass
            
            # If still not parsed, try a more aggressive approach
            if not result:
                # Look for key fields and construct result manually
                approved_match = re.search(r'"approved"\s*:\s*(true|false)', response, re.IGNORECASE)
                score_match = re.search(r'"quality_score"\s*:\s*(\d+)', response)
                thinking_match = re.search(r'"thinking"\s*:\s*"([^"]*(?:\\"[^"]*)*)"', response)
                feedback_match = re.search(r'"feedback"\s*:\s*"([^"]*(?:\\"[^"]*)*)"', response)
                
                # Try to extract issues array
                issues_extracted = []
                issues_array_match = re.search(r'"issues"\s*:\s*\[([^\]]*)\]', response)
                if issues_array_match:
                    # Try to extract individual issue strings
                    issues_str = issues_array_match.group(1)
                    issue_strings = re.findall(r'"([^"]+)"', issues_str)
                    issues_extracted = issue_strings[:10]  # Limit to 10 issues
                
                # If no issues found in array but thinking contains rejection reasons, extract them
                if not issues_extracted and thinking_match:
                    thinking_text = thinking_match.group(1)
                    # Look for numbered issues or bullet points in thinking
                    numbered_issues = re.findall(r'(?:\d+\.\s*|\-\s*|\*\s*)([A-Z][^.!?\n]{20,100}[.!?])', thinking_text)
                    if numbered_issues:
                        issues_extracted = numbered_issues[:5]
                    # Fallback: extract sentences with "missing", "broken", "error", "incorrect"
                    elif "missing" in thinking_text.lower() or "broken" in thinking_text.lower():
                        issues_extracted = ["See thinking for detailed issues - JSON parsing failed"]
                
                if approved_match or score_match:
                    result = {
                        "approved": approved_match.group(1).lower() == "true" if approved_match else True,
                        "quality_score": int(score_match.group(1)) if score_match else 7,
                        "thinking": thinking_match.group(1).replace('\\"', '"') if thinking_match else "Reconstructed from partial parse",
                        "issues": issues_extracted,
                        "feedback": feedback_match.group(1).replace('\\"', '"') if feedback_match else ("Issues found - see thinking for details" if issues_extracted else ""),
                        "corrections": []
                    }
                    log("MARCUS", "✅ Reconstructed review from partial response", project_id=project_id)
        
        # Final fallback
        if not result or not isinstance(result, dict):
            log("MARCUS", f"⚠️ Could not parse review, response: {response[:300]}", project_id=project_id)
            result = {"approved": True, "quality_score": 7, "issues": [], "feedback": "", "corrections": [], "thinking": "Unable to parse response"}
        
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
                log("MARCUS", f"⚠️ All {len(warnings)} issues are warnings (not critical) - approving with notes", project_id=project_id)
                approved = True
                quality = max(quality, 7)  # Bump quality if it was low just for warnings
                result["approved"] = True
                result["quality_score"] = quality
                result["warnings"] = warnings  # Store for logging
                result["issues"] = []  # Clear issues since they're just warnings
            else:
                # There are critical issues - keep rejection
                log("MARCUS", f"❌ Found {len(critical_issues)} critical issues (+ {len(warnings)} warnings)", project_id=project_id)
                result["critical_issues"] = critical_issues
                result["warnings"] = warnings

        
        # NOTE: Marcus's thinking is broadcast to UI (below) but not logged to server console
        # This reduces log noise while keeping the user-facing feature
        
        # Log the result
        log_result("MARCUS", approved, quality, issues if not approved else None, project_id)
        
        if not approved and feedback:
            log("MARCUS", f"Feedback: {feedback[:300]}", project_id=project_id)
        
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
        
        return result
        
    except Exception as e:
        # FIX: Don't auto-approve on error - this was silently passing broken code
        log("MARCUS", f"⚠️ Review failed: {e} - marking as NOT approved", project_id=project_id)
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
    Categorize Marcus's issues into 'critical' or 'warning' using Universal Attention.
    """
    from app.arbormind.router import ArborMindRouter
    _router = ArborMindRouter()
    
    options = [
        {"id": "warning", "description": "Style preference, suggestion, best practice, optimization, maintainability, naming convention, optional improvement, placeholder text, mock data, future todo"},
        {"id": "critical", "description": "Syntax error, bug, broken functionality, missing requirement, crash, infinite loop, undefined variable, import error, potential security vulnerability, test failure"}
    ]
    
    # Use attention to classify
    result = await _router.route(query=issue, options=options)
    
    # Default to critical if confidence is low, otherwise use selection
    # But for "warning", we want to be sure. If unsure, treat as critical.
    if result["selected"] == "warning" and result["confidence"] > 0.15:
        return "warning"
        
    return "critical"


async def postprocess_marcus_issues(quality: int, issues: List[str]):
    """
    Split issues into critical (must fix) and warnings (nice-to-have).
    
    Returns: (critical_issues, warnings)
    """
    critical = []
    warnings = []
    
    for issue in issues or []:
        # Use semantic attention routing
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
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Call an agent with Marcus supervision and auto-retry.
    
    PHASE 1-2 OPTIMIZATION: Now passes optimization parameters to reduce token usage.
    
    Flow:
    1. Build progressive context
    2. Call agent with optimized parameters
    3. Marcus reviews output
    4. If rejected, retry with minimal feedback (differential)
    5. After max_retries, return best effort
    
    Returns:
        Dict with: output, approved, attempt, quality
    """
    from app.tools import run_tool
    from app.orchestration.utils import broadcast_to_project
    
    # ============================================================
    # PRIORITY 1: Check for rate limiting BEFORE making LLM calls
    # ============================================================
    # Rate limits are now handled by BudgetManager and LLMAdapter throwing exceptions
    
    # Rate limits are now handled by BudgetManager and LLMAdapter throwing exceptions
    
    # ============================================================
    # PHASE 1-2: Build Context for Agent
    # ============================================================
    # NOTE: context_optimizer has been removed - context is now simplified
    
    # Extract archetype and vibe from user request
    archetype = _extract_archetype(user_request)
    
    # Extract vibe (simple heuristic for now)
    vibe = "minimal_light"  # Default
    if any(word in user_request.lower() for word in ["dark", "hacker", "terminal"]):
        vibe ="dark_hacker"
    elif any(word in user_request.lower() for word in ["vibrant", "colorful", "modern"]):
        vibe = "vibrant_modern"
    
    # Map step_name to workflow step identifier for context routing
    step_id = step_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
    
    # ============================================================
    # CRITICAL: Read and Filter Project Files
    # ============================================================
    from app.llm.prompt_management import filter_files_for_step
    import os
    
    # FIX ASYNC-002: Use asyncio.to_thread to avoid blocking event loop for large projects
    def _read_project_files(project_path: Path, project_id: str) -> list:
        """Synchronous file reading, to be called via asyncio.to_thread."""
        files = []
        try:
            for root, _, filenames in os.walk(project_path):
                for filename in filenames:
                    # Only include source code files
                    if filename.endswith(('.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.md')):
                        file_path = Path(root) / filename
                        rel_path = file_path.relative_to(project_path)
                        
                        # Skip large or generated files
                        if any(skip in str(rel_path) for skip in ['node_modules', 'dist', '__pycache__', '.git']):
                            continue
                        
                        try:
                            content = file_path.read_text(encoding="utf-8", errors="ignore")
                            if len(content) < 50000:  # Skip very large files
                                files.append({
                                    "path": str(rel_path).replace("\\", "/"),
                                    "content": content
                                })
                        except Exception:
                            pass
        except Exception:
            pass
        return files
    
    # Read ALL project files (non-blocking)
    all_files = await asyncio.to_thread(_read_project_files, project_path, project_id)
    
    # Filter files to only those relevant for this step
    relevant_files = filter_files_for_step(step_id, all_files)
    
    log("OPTIMIZATION", f"Filtered {len(all_files)} files → {len(relevant_files)} relevant for {step_name}", project_id=project_id)
    
    current_instructions = base_instructions
    last_output = {}
    last_review = None
    errors_from_previous = []  # For differential retry
    last_supervisor_decision_id = ""  # For self-evolution tracking
    
    # V2: Initialize adaptive prompt adapter and integrity checker
    prompt_adapter = PromptAdapter()
    integrity_checker = LLMOutputIntegrity()
    
    for attempt in range(1, max_retries + 1):
        log_section("SUPERVISION", f"🔄 {agent_name} - {step_name} (Attempt {attempt}/{max_retries})", project_id)
        
        await broadcast_to_project(
            manager,
            project_id,
            {
                "type": "AGENT_LOG",
                "scope": "SUPERVISION",
                "message": f"🔄 {agent_name} working on {step_name} (attempt {attempt}/{max_retries})",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        try:
            # ============================================================
            # PHASE 1-2: Call agent with OPTIMIZATION PARAMETERS
            # ============================================================
            
            tool_result = await run_tool(
                name="subagentcaller",
                args={
                    "sub_agent": agent_name,
                    "instructions": current_instructions,
                    "project_path": str(project_path),
                    "project_id": project_id,
                    # NEW OPTIMIZATION PARAMETERS:
                    "step_name": step_id,  # For context filtering
                    "archetype": archetype,  # For archetype-aware generation
                    "vibe": vibe,  # For UI vibe awareness
                    "files": relevant_files,  # CRITICAL: Filtered files!
                    "contracts": contracts[:500] if contracts else "",  # Summary only
                    "is_retry": (attempt > 1),  # Flag for differential context
                    "errors": errors_from_previous if attempt > 1 else None,  # Differential retry
                },
            )
            
            raw_output = tool_result.get("output", {})
            
            # V3: Extract token usage for cost tracking
            step_token_usage = tool_result.get("token_usage", {"input": 0, "output": 0})
            
            if isinstance(raw_output, dict):
                parsed = raw_output
            else:
                # Use robust parser to handle markdown fences, chatter, etc.
                from app.utils.parser import normalize_llm_output
                # Ensure raw_output is a string
                parsed = normalize_llm_output(str(raw_output))
            
            last_output = parsed
            
            # ════════════════════════════════════════════════════════
            # V2 FEATURE: LLM OUTPUT INTEGRITY CHECK (before Marcus)
            # ════════════════════════════════════════════════════════
            # Check for truncation, unbalanced brackets, etc. BEFORE expensive review
            files_content = "\n".join([f.get("content", "") for f in parsed.get("files", [])])
            if files_content and not integrity_checker.validate(files_content):
                issues = integrity_checker.get_issues(files_content)
                log("V2-INTEGRITY", f"⚠️ Output integrity failed: {issues}", project_id=project_id)
                prompt_adapter.record_failure(step_name)
                errors_from_previous = issues[:3]
                if attempt < max_retries:
                    # Use adapted prompt for retry
                    hint = prompt_adapter.get_context_hint(step_name)
                    current_instructions = prompt_adapter.adapt(step_name, base_instructions)
                    if hint:
                        current_instructions += f"\n\n{hint}"
                    continue
                # Last attempt - proceed to Marcus review anyway
            
            # FIX #6: If no files, this is a FAILURE, not a success
            if "files" not in parsed or not parsed["files"]:
                log("SUPERVISION", f"⚠️ {agent_name} produced no files - NOT approved", project_id=project_id)
                # Don't return approved=True here - this was allowing empty output through!
                # Instead, let the retry loop handle it
                if attempt >= max_retries:
                    return {"output": parsed, "approved": False, "attempt": attempt, "error": "No files generated", "token_usage": step_token_usage}
                # Continue to next attempt
                continue
            
            # Marcus reviews
            review = await marcus_supervise(
                project_id=project_id,
                manager=manager,
                agent_name=agent_name,
                step_name=step_name,
                agent_output=parsed,
                contracts=contracts,
                user_request=user_request,
            )
            last_review = review
            
            if review["approved"]:
                quality = review.get("quality_score", 7)
                track_quality_score(project_id, agent_name, quality, True)
                await save_snapshot(project_id, project_path, step_name, agent_name, quality, True)
                
                if quality >= 7:
                    # Store in existing memory system
                    remember_success(agent_name, step_name, user_request[:100], 
                                   {"file_count": len(parsed.get("files", []))}, quality)
                    
                    # ═══════════════════════════════════════════════════════
                    # LEARNING: Store successful pattern for future improvement
                    # ═══════════════════════════════════════════════════════
                    try:
                        from app.learning import learn_from_success
                        
                        # Extract archetype from user request (first key words)
                        archetype = _extract_archetype(user_request)
                        
                        learn_from_success(
                            archetype=archetype,
                            agent=agent_name,
                            step=step_name,
                            quality_score=quality,
                            files=parsed.get("files", []),
                            entity_type=parsed.get("entity", ""),
                            user_request=user_request,
                        )
                    except Exception as learn_error:
                        log("LEARNING", f"⚠️ Pattern storage failed (non-fatal): {learn_error}")
                    
                    # ═══════════════════════════════════════════════════════
                    # SELF-EVOLUTION: Report supervisor decision outcome as SUCCESS
                    # ═══════════════════════════════════════════════════════
                    # If we had a supervisor decision from a previous retry, report success
                    if attempt > 1 and 'last_supervisor_decision_id' in dir() and last_supervisor_decision_id:
                        try:
                            from app.arbormind import report_routing_outcome
                            report_routing_outcome(
                                last_supervisor_decision_id, 
                                True, 
                                quality, 
                                f"Retry succeeded after {attempt} attempts"
                            )
                            log("EVOLUTION", "📈 Reported success for supervisor decision")
                        except Exception:
                            pass
                
                return {"output": parsed, "approved": True, "attempt": attempt, "quality": quality, "token_usage": step_token_usage}
            
            # Not approved - check quality gate (FIX #4)
            quality = review.get("quality_score", 4)
            track_quality_score(project_id, agent_name, quality, False)  # Track rejection
            
            # ════════════════════════════════════════════════════════
            # FAILURE LEARNING: Record Intermediate Failure (Logic/Style)
            # ════════════════════════════════════════════════════════
            # Capture the mistake even if we fix it later!
            try:
                from app.learning.failure_store import get_failure_store
                store = get_failure_store()
                
                issues = review.get("issues", [])
                feedback = review.get("feedback", "")
                
                if issues:
                    store.record_failure(
                        archetype=archetype,
                        agent=agent_name,
                        step=step_name,
                        error_type="supervision_rejection",
                        description=f"Rejected (Score {quality}): {issues[0][:100]}",
                        code_snippet=str(issues[:2]), # Store issues as the snippet context
                        fix_summary=feedback[:100]
                    )
            except Exception as e:
                log("LEARNING", f"⚠️ Failed to record intermediate failure: {e}")

            from app.supervision.quality_gate import check_quality_gate
            should_block, block_reason = await check_quality_gate(
                project_id, step_name, quality, False, attempt, max_retries
            )
            if should_block:
                log("SUPERVISION", f"🚫 Quality gate blocked: {block_reason}", project_id=project_id)
                # Don't proceed - let the workflow handle this

            
            # Not approved - build retry instructions
            
            # Not approved - build retry instructions
            
            if attempt < max_retries:
                feedback = review.get("feedback", "")
                issues = review.get("issues", [])
                
                # ════════════════════════════════════════════════════════
                # PHASE 3.1: AM-Driven Repair Strategy (C-AM -> E-AM -> T-AM)
                # ════════════════════════════════════════════════════════
                try:
                    from app.orchestration.error_router import ErrorRouter
                    from app.arbormind import report_routing_outcome
                    
                    # Use the advanced AM Router
                    error_router = ErrorRouter()
                    
                    # Synthesize error context
                    error_context = f"Step: {step_name}\nAttempts: {attempt}\nIssues: {str(issues[:3])}"
                    
                    # Decide strategy with escalation (Standard -> Exploratory -> Transformational)
                    repair_decision = await error_router.decide_repair_strategy(
                        error_log=error_context, 
                        archetype=archetype,
                        retries=attempt,
                        max_retries=max_retries,
                        context={"current_value": {}} # Context for mutation if needed
                    )
                    
                    log("SUPERVISION", f"🧠 Repair Strategy: {repair_decision.get('mode', 'standard').upper()} -> {repair_decision.get('selected')}", project_id=project_id)
                    
                    # Store decision ID for later outcome reporting
                    last_supervisor_decision_id = repair_decision.get("decision_id", "")
                    
                    # Extract control parameters from the decision value
                    config = repair_decision.get("value", {})
                    
                    # Apply AM specific modes
                    if repair_decision.get("mode") == "exploratory":
                         # Inject foreign patterns into instructions
                         patterns = repair_decision.get("patterns", [])
                         if patterns:
                             hint_text = "\n\n💡 FOREIGN PATTERN SUGGESTION (E-AM):\n"
                             for p in patterns:
                                 hint_text += f"- From {p.get('archetype')}: {p.get('description', '')}\n"
                             current_instructions += hint_text
                             log("SUPERVISION", f"   Updated instructions with {len(patterns)} foreign patterns")

                    elif repair_decision.get("mode") == "transformational":
                         # Apply mutation to constraints (instructions)
                         mutation = repair_decision.get("mutation", {})
                         desc = mutation.get("description", "")
                         if desc:
                             current_instructions += f"\n\n🔮 CONSTRAINT MUTATION (T-AM):\n{desc}\n(You are authorized to bypass previous constraints)"
                             log("SUPERVISION", f"   Applied constraint mutation: {desc}")
                    
                    # Standard control flags
                    force_healer = config.get("force_healer", False)
                    if config.get("retry_on_fail") == 0:
                        force_healer = True
                        
                    regenerate_context = config.get("regenerate_context", False)
                    
                    # Check Force Healer
                    if force_healer:
                        log("SUPERVISION", "🩹 Policy suggests delegating to Healer immediately")
                        if last_supervisor_decision_id:
                             try:
                                 report_routing_outcome(last_supervisor_decision_id, True, 6.0, "Delegated to healer")
                             except Exception as e:
                                 log("SUPERVISION", f"Failed to report routing outcome: {e}")
                        
                        return {
                             "output": parsed, 
                             "approved": False, 
                             "attempt": attempt, 
                             "quality": quality, 
                             "issues": issues,
                             "feedback": "Supervisor policy delegated to healer",
                             "force_healer": True 
                        }
                    
                    # Check Context Regeneration
                    if regenerate_context:
                        log("SUPERVISION", "🔄 Policy requests context regeneration/reset")
                        prompt_adapter.record_failure(step_name)
                        errors_from_previous = []

                except Exception as e:
                    log("SUPERVISION", f"⚠️ AM routing failed: {e}, falling back to standard retry", project_id=project_id)
                    force_healer = False
                    last_supervisor_decision_id = ""

                corrections = review.get("corrections", [])
                
                # ============================================================
                # PHASE 4 OPTIMIZATION: Differential Retry
                # ============================================================
                # Store errors for next attempt (will be sent instead of full instructions)
                errors_from_previous = issues[:5]  # Top 5 issues only
                
                # Build correction text
                correction_text = ""
                for c in corrections[:5]:
                    if isinstance(c, dict):
                        correction_text += f"\n  ❌ {c.get('file', 'unknown')}: {c.get('problem', '')} → {c.get('fix', '')}"
                
                # Memory hint
                memory_hint = get_memory_hint(agent_name, step_name)
                
                current_quality = review.get("quality_score", 4)
                strict_warning = ""
                if current_quality < 5:
                    strict_warning = "\n🛑 CRITICAL WARNING: YOUR QUALITY SCORE IS BELOW 5/10. IMPROVE IMMEDIATELY OR WORKFLOW WILL FAIL.\n"

                # ============================================================
                # PHASE 4: MINIMAL RETRY INSTRUCTIONS (not full base_instructions!)
                # ============================================================
                # On retry, only send what changed (errors), not the full prompt
                retry_addition = f"""

⚠️ SUPERVISOR REJECTION (Quality: {current_quality}/10) - FIX THESE ISSUES:
{strict_warning}
Feedback: {feedback}

Issues: {chr(10).join(f'  {i+1}. {issue}' for i, issue in enumerate(issues[:5]))}

Corrections: {correction_text}

{memory_hint}

⚡ CRITICAL: Generate COMPLETE, CORRECTED files.
"""
                # NOTE: On retry, the agent call will use is_retry=True
                # which triggers differential context in marcus_call_sub_agent
                
                # V2: Record failure and use adapted prompt
                prompt_adapter.record_failure(step_name)
                adapted_base = prompt_adapter.adapt(step_name, base_instructions)
                hint = prompt_adapter.get_context_hint(step_name)
                if hint:
                    retry_addition += f"\n{hint}\n"
                
                current_instructions = adapted_base + retry_addition
                
                log("SUPERVISION", f"⚠️ {agent_name} will retry with {len(issues)} issues to fix", project_id=project_id)
            
        except Exception as e:
            log("SUPERVISION", f"❌ {agent_name} failed: {e}", project_id=project_id)
            
            if "rate limit" in str(e).lower():
                await asyncio.sleep(5)
            
            if attempt >= max_retries:
                return {"output": last_output, "approved": False, "attempt": attempt, "error": str(e), "token_usage": step_token_usage if 'step_token_usage' in dir() else {"input": 0, "output": 0}}
    
    # Max retries reached
    quality = last_review.get("quality_score", 5) if last_review else 5
    await save_snapshot(project_id, project_path, step_name, agent_name, quality, False)
    
    # PHASE 1 CHANGE: Critical steps fail hard
    # We don't want to proceed with broken router or integration code
    CRITICAL_STEPS = {"backend_implementation", "system_integration", "frontend_integration", "architecture"}
    normalized_step = step_name.lower().replace(" ", "_").strip()
    
    # Check if this is a critical step
    is_critical = any(crit in normalized_step for crit in CRITICAL_STEPS)
    
    # Strict Quality Gate for Critical Steps
    MIN_QUALITY = 5
    if is_critical and quality < MIN_QUALITY:
         log("SUPERVISION", f"❌ {step_name} failed quality gate (q={quality}), discarding output", project_id=project_id)
         
         # ════════════════════════════════════════════════════════
         # FAILURE LEARNING: Record this critical failure 
         # ════════════════════════════════════════════════════════
         try:
             from app.learning.failure_store import get_failure_store
             store = get_failure_store()
             
             # Extract error details from last review
             issues = last_review.get("issues", []) if last_review else ["Unknown critical failure"]
             feedback = last_review.get("feedback", "") if last_review else ""
             
             store.record_failure(
                 archetype=archetype,
                 agent=agent_name,
                 step=step_name,
                 error_type="quality_gate_failure",
                 description=f"Failed quality gate (Score {quality}). Issues: {'; '.join(str(i) for i in issues[:3])}",
                 code_snippet=str(issues[:1]) if issues else "",
                 fix_summary=feedback[:200]
             )
         except Exception as e:
             log("LEARNING", f"⚠️ Failed to record failure: {e}")
             
         return {"output": None, "approved": False, "attempt": max_retries, "error": f"Failed quality gate (Score {quality})", "token_usage": step_token_usage if 'step_token_usage' in dir() else {"input": 0, "output": 0}}

         # Return empty files to signal failure to orchestrator (which will trigger healing)
         return {
             "output": {"files": [], "message": f"Quality gate failed ({quality}/10)"}, 
             "approved": False, 
             "attempt": max_retries, 
             "quality": quality,
             "error": "quality_gate_failed"
         }
    
    # For non-critical steps (or if quality >= 5), return best effort
    # But still filter out syntactically broken files
    final_output = last_output
    if last_review and not last_review.get("approved"):
        # Even for best effort, don't persist SyntaxErrors
        if any(issue for issue in last_review.get("issues", []) if "syntax error" in issue.lower() or "truncated" in issue.lower()):
             log("SUPERVISION", "⚠️ Dropping broken files from best-effort output", project_id=project_id)
             # Try to filter files if possible, or drop all if unsure
             final_output = {**last_output, "files": []} 
    
    return {"output": final_output, "approved": False, "attempt": max_retries, "quality": quality, "token_usage": step_token_usage if 'step_token_usage' in dir() else {"input": 0, "output": 0}}
