# app/agents/sub_agents.py
"""
Sub-agent wrappers: Derek (backend QA), Luna (frontend QA), Victoria (architecture).

SELF-EVOLVING: File and tool selection decisions are tracked and outcomes
reported to enable learning over time.

Each sub-agent:
 - Uses the integration adapter LLM to generate tests (pytest / Playwright).
 - Writes tests to workspace path.
 - Attempts to run the tests and returns a structured result dict.
"""
import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import log
from app.core.constants import TEST_FILE_MIN_TOKENS
from app.llm.prompts.derek import DEREK_PROMPT
from app.llm.prompts.luna import LUNA_PROMPT
from app.llm import call_llm, call_llm_with_usage  # ✅ Use unified LLM interface with V3 usage tracking

# NOTE: Cost tracking now handled by BudgetManager in orchestrator

# Helper to broadcast agent thinking to frontend
async def _broadcast_agent_thinking(project_id: str, agent_name: str, status: str, content: str) -> None:
    """Broadcast agent thinking to the frontend Terminal."""
    try:
        # Import here to avoid circular imports - using new structure
        from app.orchestration.state import CURRENT_MANAGERS
        from app.orchestration.utils import broadcast_to_project
        
        if project_id in CURRENT_MANAGERS:
            manager = CURRENT_MANAGERS[project_id]
            await broadcast_to_project(
                manager,
                project_id,
                {
                    "type": "AGENT_LOG",
                    "scope": f"AGENT:{agent_name}",
                    "message": content,
                    "data": {"status": status, "agent": agent_name},
                    "timestamp": time.time()
                }
            )
    except Exception as e:

        log("BROADCAST", f"Failed to broadcast: {e}")


async def _llm_generate_tests(
    user_request: str,
    project_path: str,
    agent_name: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = TEST_FILE_MIN_TOKENS  # Use higher limit for test files
) -> Dict[str, Any]:
    """
    Ask LLM to generate tests given the current project files.
    Returns parsed JSON { "tests": [{"path": "...", "content": "..."}], "metadata": {...} }
    """
    provider = provider or settings.llm.default_provider
    model = model or settings.llm.default_model
    
    if system_prompt:
        system_prompt = system_prompt
    else:
        system_prompt = DEREK_PROMPT if agent_name == "Derek" else LUNA_PROMPT


    # Collect lightweight context (file list + a few file contents)
    p = Path(project_path)
    
    # FIX ASYNC-001: Wrap blocking os.walk in thread pool
    def _collect_files_sync():
        file_list = []
        for root, _, files in os.walk(p):
            for f in files:
                if f.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".json")):
                    rel = os.path.relpath(os.path.join(root, f), project_path)
                    file_list.append(rel)
        return file_list

    file_list = await asyncio.to_thread(_collect_files_sync)
    
    sample_context: Dict[str, str] = {}
    for f in file_list[:10]:
        try:
            sample_context[f] = (p / f).read_text(encoding="utf-8")
        except Exception:
            sample_context[f] = "<unreadable>"

    prompt = f"""You are {agent_name}, a QA sub-agent. Generate automated tests for this project.

User request:
{user_request}

Project path: {project_path}
File list (top 50):
{json.dumps(file_list[:50], indent=2)}

OUTPUT FORMAT (HDAP):
You MUST use artifact markers to output test files:

<<<FILE path="tests/test_example.py">>>
import pytest
# Your test code here
<<<END_FILE>>>

Generate complete test files with proper assertions.
"""

    raw = await call_llm(
        prompt=prompt,
        provider=provider,
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens
    )

    # HDAP parsing with strict protocol enforcement
    from app.utils.parser import parse_hdap
    
    parsed = parse_hdap(raw)
    
    if parsed.get("no_hdap_markers"):
        return {
            "error": f"{agent_name} did not use HDAP artifact markers. Protocol violation.",
            "raw": raw
        }
    
    if not parsed["complete"]:
        return {
            "error": f"Truncated test generation output. Incomplete files: {parsed['incomplete_files']}",
            "raw": raw
        }
    
    # Convert HDAP files format to tests format
    tests = parsed.get("files", [])
    if not tests:
        return {"error": "No test files generated", "raw": raw}
    
    return {
        "tests": tests,
        "thinking": "",  # HDAP ignores thinking
        "notes": "",
        "runner": "pytest"
    }


def _write_tests_to_workspace(project_path: str, tests: List[Dict[str, str]]) -> List[Path]:
    """Persist generated tests into workspace and return list of written paths."""
    written: List[Path] = []
    base = Path(project_path)
    for t in tests:
        path = t.get("path")
        content = t.get("content", "")
        if not path:
            continue
        full = base / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        written.append(full)
    return written


async def _run_pytest(project_path: str, test_paths: Optional[List[str]] = None, timeout: int = 60) -> Dict[str, Any]:
    """
    Run pytest programmatically via async subprocess.
    Returns structured dict: passed(bool), failures(list), output(str)
    """
    cmd = ["pytest", "-q"]
    if test_paths:
        cmd.extend(test_paths)
    try:
        # FIX ASYNC-001: Use asyncio.to_thread for Windows compatibility
        def run_pytest_sync():
            return subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        
        proc = await asyncio.to_thread(run_pytest_sync)
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        
        output = stdout + ("\nSTDERR:\n" + stderr if stderr else "")
        passed = proc.returncode == 0
        failures: List[Dict[str, Any]] = []

        # naive parse: look for 'FAILED' lines
        if not passed:
            lines = output.splitlines()
            # collect lines mentioning failed
            for i, line in enumerate(lines):
                if "FAILED" in line or "ERROR" in line:
                    failures.append({"line": i + 1, "text": line})
        return {"passed": passed, "failures": failures, "output": output, "returncode": proc.returncode}
    except subprocess.TimeoutExpired:
        return {"passed": False, "failures": [{"description": "pytest timeout"}], "output": "", "returncode": None}
    except FileNotFoundError:
        return {"passed": False, "failures": [{"description": "pytest not installed"}], "output": "pytest not found on PATH", "returncode": None}
    except Exception as e:
        return {"passed": False, "failures": [{"description": "pytest run failed", "exception": str(e)}], "output": "", "returncode": None}


async def _run_playwright(project_path: str, test_paths: Optional[List[str]] = None, timeout: int = 120) -> Dict[str, Any]:
    """
    Try to run playwright tests via CLI 'playwright test' (async).
    Returns structured dict similar to pytest runner.
    """
    cmd = ["playwright", "test"]
    if test_paths:
        cmd.extend(test_paths)
    try:
        # FIX ASYNC-001: Use asyncio.to_thread for Windows compatibility
        def run_playwright_sync():
            return subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        
        proc = await asyncio.to_thread(run_playwright_sync)
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        
        output = stdout + ("\nSTDERR:\n" + stderr if stderr else "")
        passed = proc.returncode == 0
        failures: List[Dict[str, Any]] = []
        if not passed:
            lines = output.splitlines()
            for i, line in enumerate(lines):
                if "FAILED" in line or "✖" in line:
                    failures.append({"line": i + 1, "text": line})
        return {"passed": passed, "failures": failures, "output": output, "returncode": proc.returncode}
    except subprocess.TimeoutExpired:
        return {"passed": False, "failures": [{"description": "playwright timeout"}], "output": "", "returncode": None}
    except FileNotFoundError:
        return {"passed": False, "failures": [{"description": "playwright not installed"}], "output": "playwright not found on PATH", "returncode": None}
    except Exception as e:
        return {"passed": False, "failures": [{"description": "playwright run failed", "exception": str(e)}], "output": "", "returncode": None}


async def run_sub_agent(
    name: str,
    user_request: str,
    project_path: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generic runner for a sub-agent:
    - Ask LLM to produce tests
    - Persist them
    - Attempt to run them
    - Return structured report
    """
    try:
        gen = await _llm_generate_tests(user_request, project_path, name, provider, model)
        if "error" in gen:
            return {"agent": name, "passed": False, "issues": [{"description": gen.get("error"), "raw": gen.get("raw")}], "raw": gen}

        tests = gen.get("tests", [])
        runner_hint = gen.get("runner", "pytest")
        notes = gen.get("notes", "")

        written = _write_tests_to_workspace(project_path, tests)
        test_paths = [str(p.relative_to(project_path)) for p in written]

        # Run according to runner hint
        if runner_hint and "playwright" in runner_hint.lower():
            run_result = await _run_playwright(project_path, test_paths)
        else:
            run_result = await _run_pytest(project_path, test_paths)

        issues = []
        if not run_result.get("passed"):
            failures = run_result.get("failures", [])
            # Normalize failures
            for f in failures:
                if isinstance(f, dict):
                    issues.append(f)
                else:
                    issues.append({"description": str(f)})
            
            # ════════════════════════════════════════════════════════
            # FAILURE LEARNING: Deprecated
            # ════════════════════════════════════════════════════════
            # Legacy app.learning integration removed.
            # ArborMind now handles learning via the global cycle and memory consolidation.
            pass

        return {
            "agent": name,
            "passed": bool(run_result.get("passed")),
            "issues": issues,
            "output": run_result.get("output", ""),
            "written_tests": test_paths,
            "notes": notes,
            "raw_generation": gen
        }

    except Exception as e:
        return {"agent": name, "passed": False, "issues": [{"description": "sub-agent failure", "exception": str(e)}], "raw_exception": str(e)}


# --- Public wrappers used by workflows.py ---

async def marcus_call_sub_agent(
    agent_name: str,
    user_request: str,
    project_path: str = "",
    project_id: str = "",  # For broadcasting thinking
    step_name: str = "",  # NEW: For context optimization
    archetype: str = "",  # NEW: For archetype awareness
    vibe: str = "",  # NEW: For vibe awareness
    files: Optional[List[Dict[str, str]]] = None,  # NEW: Relevant files only
    contracts: Optional[str] = None,  # NEW: API contracts
    is_retry: bool = False,  # NEW: For retry optimization
    errors: Optional[List[str]] = None,  # NEW: For differential retry
    instructions: Optional[str] = None,  # NEW: Custom base instructions for the agent
    max_tokens_override: Optional[int] = None,  # NEW: Override token policy (for healing)
    temperature_override: Optional[float] = None,  # NEW: Override temperature (for healing)
) -> Dict[str, Any]:
    """
    Marcus uses this to call Derek/Luna/Victoria for code generation.
    
    Uses full agent prompts with HDAP format instructions.
    """
    try:
        # Import full agent prompts (with HDAP instructions)
        from app.llm.prompts.derek import DEREK_PROMPT
        from app.llm.prompts.victoria import VICTORIA_PROMPT
        from app.llm.prompts.luna import LUNA_PROMPT
        from app.llm.prompts.marcus import MARCUS_PROMPT
        from app.llm.prompt_management import build_context

        # Map agent names to their full prompts
        AGENT_PROMPTS = {
            "derek": DEREK_PROMPT,
            "victoria": VICTORIA_PROMPT,
            "luna": LUNA_PROMPT,
            "marcus": MARCUS_PROMPT,
        }

        provider = settings.llm.default_provider
        model = settings.llm.default_model

        # ═══════════════════════════════════════════════════════════════
        # PHASE-1: Check ExecutionMode and Apply Enforcement
        # ═══════════════════════════════════════════════════════════════
        from app.arbormind.core.execution_mode import get_execution_policy, ExecutionMode
        from app.llm.artifact_enforcement import enforce_artifact_mode
        
        execution_policy = get_execution_policy(step_name)
        is_artifact_mode = (execution_policy.mode == ExecutionMode.ARTIFACT)
        
        # Combine global persona with provided instructions to ensure identity + scope
        global_persona = AGENT_PROMPTS.get(agent_name.lower(), DEREK_PROMPT)
        
        # V2: In ARTIFACT mode, strip the redundant protocol part from the persona to reduce confusion
        if is_artifact_mode and agent_name.lower() == "derek":
            # Search for the start of the "Role & Responsibility" section, which follows the protocol
            marker = "📐 ROLE & RESPONSIBILITY"
            if marker in global_persona:
                role_persona = global_persona[global_persona.find(marker):]
                header = f"You are {agent_name.capitalize()}, GenCode Studio's senior full-stack developer.\n\n"
                global_persona = header + role_persona
        
        if instructions:
            base_prompt = f"{global_persona}\n\n═══════════════════════════════════════════════════════\n📥 STEP-SPECIFIC INSTRUCTIONS (OVERRIDING AUTHORITY)\n═══════════════════════════════════════════════════════\n\n{instructions}"
        else:
            base_prompt = global_persona
        
        # File Selection - limit to manageable size
        selected_files = files
        file_mode_decision_id = ""
        
        if files:
            # Limit files to prevent context overflow
            if isinstance(files, list) and len(files) > 5:
                selected_files = files[:5]
            elif isinstance(files, dict) and len(files) > 5:
                selected_files = dict(list(files.items())[:5])
        
        # ════════════════════════════════════════════════════════
        # DYNAMIC TOOL SELECTION (V!=K)
        # ════════════════════════════════════════════════════════
        selected_tools = []
        tool_decision_id = ""
        query = f"{step_name}: {user_request}"
        
        try:
             # Use Attention to select and configure tools
             from app.tools.registry import get_relevant_tools_for_query
             tool_result = await get_relevant_tools_for_query(
                 query, 
                 top_k=3,
                 context_type="agent_tool_selection",
                 archetype=archetype or "unknown",
                 step_name=step_name
             )
             selected_tools = tool_result if isinstance(tool_result, list) else []
             # Check if we got a decision_id back (if registry returns it)
             if isinstance(tool_result, dict):
                 tool_decision_id = tool_result.get("decision_id", "")
                 selected_tools = tool_result.get("tools", [])
        except Exception:
             pass  # Tool selection is optional
        
        # ═══════════════════════════════════════════════════════════════
        # ARTIFACT MODE ENFORCEMENT (Phase-1 Critical Fix)
        # ═══════════════════════════════════════════════════════════════
        if is_artifact_mode:
            
            # Use enforcement layer to build prompts correctly
            prompts = enforce_artifact_mode(
                base_system_prompt=base_prompt,
                user_task=user_request,
                step_name=step_name,
                files=selected_files,
                contracts=contracts
            )
            
            core_prompt = prompts["system_prompt"]  # HDAP rules + agent identity
            dynamic_context = prompts["user_prompt"]  # Task + data ONLY
            
        else:
            # FREEFORM/STRUCTURED modes: use old build_context logic
            from app.llm.prompt_management import build_context
            
            core_prompt = base_prompt  # No HDAP enforcement
            dynamic_context = build_context(
                agent_name=agent_name,
                task=user_request,
                step_name=step_name,
                archetype=archetype,
                vibe=vibe,
                files=selected_files,
                contracts=contracts,
                errors=errors if is_retry else None,
                tools=selected_tools
            )


        # ============================================================
        # MAX TOKENS - Step-specific token policies (Option 3 #7)
        # ============================================================
        # Use centralized token policy system for step-aware allocation
        from app.orchestration.token_policy import get_tokens_for_step
        
        max_tokens = get_tokens_for_step(step_name, is_retry=is_retry)
        
        # Allow override from healing (progressive token scaling)
        if max_tokens_override is not None:
            max_tokens = max_tokens_override
        
        # Allow temperature override from healing
        temperature = 0.7  # Default
        if temperature_override is not None:
            temperature = temperature_override

        log("MARCUS", f"Calling {agent_name} (max_tokens={max_tokens})")
        
        # ============================================================
        # LLM CALL with OPTIMIZED PROMPTS + V3 USAGE TRACKING
        # ============================================================
        llm_result = await call_llm_with_usage(
            prompt=dynamic_context,  # MINIMAL dynamic context
            provider=provider,
            model=model,
            system_prompt=core_prompt,  # CORE static rules (cacheable!)
            temperature=temperature,  # Use override or default
            max_tokens=max_tokens,
        )
        
        # V3: Extract text and usage from result
        raw = llm_result.get("text", "")
        token_usage = llm_result.get("usage", {"input": 0, "output": 0})

        # ONE LINE TOKEN LOG (kept)
        log("TOKENS", f"in={token_usage.get('input', 0)} out={token_usage.get('output', 0)}")

        # ════════════════════════════════════════════════════════
        # HDAP PARSING (strict protocol enforcement)
        # ════════════════════════════════════════════════════════
        from app.utils.parser import parse_hdap
        import json as json_lib  # For Marcus review parsing
        
        hdap_result = parse_hdap(raw)
        
        # Check if this is a Marcus supervision response (JSON with "approved" field)
        # Marcus reviews use JSON for structured metadata, not HDAP for files
        is_marcus_review = False
        review_data = None
        if hdap_result.get("no_hdap_markers"):
            # Try JSON for Marcus review responses
            try:
                # Clean markdown fences if present
                cleaned = raw.strip()
                if cleaned.startswith('```'):
                    lines = cleaned.split('\n')
                    if lines[-1].strip() == '```':
                        cleaned = '\n'.join(lines[1:-1])
                    else:
                        cleaned = '\n'.join(lines[1:])
                
                review_data = json_lib.loads(cleaned)
                if isinstance(review_data, dict) and "approved" in review_data:
                    is_marcus_review = True
            except Exception:
                pass
        
        # Handle Marcus review (JSON is correct for reviews)
        if is_marcus_review and review_data:
            # Broadcast Marcus review to UI
            if project_id:
                approved = review_data.get("approved", False)
                quality = review_data.get("quality_score", "?")
                feedback = review_data.get("feedback", "")
                if approved:
                    msg = f"✅ Approved - Quality: {quality}/10"
                    if feedback:
                        msg += f"\n{feedback[:300]}"
                else:
                    issues = review_data.get("issues", [])
                    msg = f"⚠️ Requesting corrections - Quality: {quality}/10"
                    if issues:
                        msg += "\nIssues: " + ", ".join(str(i)[:100] for i in issues[:3])
                await _broadcast_agent_thinking(project_id, agent_name, "review", msg)
            
            # Return review result (not files)
            return {
                "passed": True,
                "output": review_data,
                "raw_generation": raw,
                "issues": [],
                "token_usage": token_usage,
                "decision_ids": {
                    "file_context": file_mode_decision_id,
                    "tool_selection": tool_decision_id
                }
            }
        
        
        # Check for HDAP protocol violations
        if hdap_result.get("no_hdap_markers"):
            # ═══════════════════════════════════════════════════════════════
            # PHASE-1: Auto-Recovery for ARTIFACT Mode
            # ═══════════════════════════════════════════════════════════════
            if is_artifact_mode and execution_policy.auto_recover:
                
                from app.llm.artifact_enforcement import auto_recover_hdap
                from app.llm import call_llm
                
                recovery_result = await auto_recover_hdap(
                    raw_output=raw,
                    agent_name=agent_name,
                    llm_call_func=call_llm,
                    provider=provider,
                    model=model,
                    max_tokens=max_tokens
                )
                
                if recovery_result.get("recovered"):
                    # Success! Use recovered output
                    files = recovery_result.get("files", [])
                    
                    # Broadcast recovery success
                    if project_id and files:
                        from app.core.logging import log_files
                        file_paths = [f.get("path", "?") for f in files[:5]]
                        msg = f"🔄 Auto-recovered {len(files)} file(s):\n" + "\n".join(f"  • {f}" for f in file_paths)
                        await _broadcast_agent_thinking(project_id, agent_name, "recovery", msg)
                        log_files(agent_name.upper(), files, project_id)
                    
                    # Return successful recovery
                    normalized = {"files": files, "complete": True}
                    return {
                        "passed": True,
                        "output": normalized,
                        "raw_generation": recovery_result["output"],
                        "issues": [],
                        "token_usage": token_usage,
                        "auto_recovered": True,  # Signal that recovery occurred
                        "decision_ids": {
                            "file_context": file_mode_decision_id,
                            "tool_selection": tool_decision_id
                        }
                    }
                else:
                    pass  # Recovery failed - fall through to error return
            
            # Recovery failed or not enabled - return protocol violation
            log("HDAP", f"❌ No HDAP markers from {agent_name}")
            return {
                "passed": False,
                "output": "",
                "raw_generation": raw,
                "issues": [{
                    "description": f"{agent_name} did not use HDAP artifact markers. Expected: <<<FILE path=\"...\">>> content <<<END_FILE>>>",
                    "raw": raw[:500]
                }],
                "token_usage": token_usage,
                "decision_ids": {
                    "file_context": file_mode_decision_id,
                    "tool_selection": tool_decision_id
                }
            }
        
        if not hdap_result["complete"]:
            log("HDAP", f"⚠️ Truncated ({hdap_result['incomplete_files']})")
            return {
                "passed": False,
                "output": "",
                "raw_generation": raw,
                "issues": [{
                    "description": f"Incomplete HDAP output. Missing <<<END_FILE>>> for: {hdap_result['incomplete_files']}",
                    "raw": raw[-500:]
                }],
                "token_usage": token_usage,
                "decision_ids": {
                    "file_context": file_mode_decision_id,
                    "tool_selection": tool_decision_id
                }
            }
        
        files = hdap_result.get("files", [])
        
        # Broadcast file summary
        if project_id and files:
            from app.core.logging import log_files
            
            # Build concise file summary from list of dicts
            file_paths = [f.get("path", "?") for f in files[:5]]
            msg = f"📁 Generated {len(files)} file(s):\n" + "\n".join(f"  • {f}" for f in file_paths)
            if len(files) > 5:
                msg += f"\n  ... and {len(files) - 5} more"
            await _broadcast_agent_thinking(project_id, agent_name, "files", msg)
            log_files(agent_name.upper(), files, project_id)
        
        # Normalize to files schema
        normalized = {"files": files, "complete": hdap_result["complete"]}

        if normalized is not None:
            # Happy path: we got a usable files schema
            
            # ════════════════════════════════════════════════════════
            # SELF-EVOLUTION: Return decision IDs for Supervisor to track
            # ════════════════════════════════════════════════════════
            # We don't report success here yet because we don't know if the code is GOOD.
            # We only know it's valid JSON. The Supervisor (Marcus) will report the 
            # true outcome based on his review and the quality score.
            
            # Robustness: Inject decision_ids into payload so they survive tool unpacking
            if isinstance(normalized, dict):
                normalized["decision_ids"] = {
                    "file_context": file_mode_decision_id,
                    "tool_selection": tool_decision_id
                }

            return {
                "passed": True,
                "output": normalized,
                "raw_generation": raw,
                "issues": [],
                "token_usage": token_usage,  # V3: Return actual usage for cost tracking
                "decision_ids": {
                    "file_context": file_mode_decision_id,
                    "tool_selection": tool_decision_id
                }
            }

        # Fallback: return raw + parsed (if any) for tool_sub_agent_caller to attempt recovery
        issues: List[Dict[str, Any]] = []
        if parsed is not None:
            issues.append({"raw": json.dumps(parsed)})
        else:
            issues.append({"raw": raw})

        # ════════════════════════════════════════════════════════
        # SELF-EVOLUTION: Report FAILURE for attention decisions
        # ════════════════════════════════════════════════════════
        # ════════════════════════════════════════════════════════
        # SELF-EVOLUTION: Legacy removed
        # ════════════════════════════════════════════════════════
        pass

        return {
            "passed": False,
            "output": parsed if parsed is not None else raw,
            "raw_generation": raw,
            "issues": issues,
            "token_usage": token_usage,  # V3: Return actual usage even on failure
            "decision_ids": {
                "file_context": file_mode_decision_id,
                "tool_selection": tool_decision_id
            }
        }

    except Exception as e:
        log("MARCUS", f"Error: {e}")
        return {
            "passed": False,
            "output": "",
            "raw_generation": "",
            "issues": [{"description": str(e), "raw": ""}],
        }
