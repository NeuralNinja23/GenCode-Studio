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
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import log
from app.core.types import ChatMessage
from app.core.constants import TEST_FILE_MIN_TOKENS
from app.llm.prompts.derek import DEREK_PROMPT
from app.llm.prompts.luna import LUNA_PROMPT
from app.llm.prompts.victoria import VICTORIA_PROMPT
from app.llm import call_llm  # ✅ Use unified LLM interface

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
        print(f"[_broadcast_agent_thinking] Failed to broadcast: {e}")


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
    if system_prompt: system_prompt = system_prompt
    else: system_prompt = DEREK_PROMPT if agent_name == "Derek" else LUNA_PROMPT


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

    prompt = f"""
You are {agent_name}, a QA sub-agent. Generate automated tests for this project.

User request:
{user_request}

Project path: {project_path}
File list (top 50):
{json.dumps(file_list[:50], indent=2)}

Give me a JSON object with:
{{
  "thinking": "Brief reasoning about what tests/code you are generating...",
  "tests": [
    {{
      "path": "tests/test_xyz.py",
      "content": "..."
    }}
  ],
  "notes": "technical details...",
  "runner": "pytest|playwright"
}}

Only output valid JSON.
"""

    raw = await call_llm(
        prompt=prompt,
        provider=provider,
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens
    )

    # safe parse
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("JSON is not an object")
        if "tests" not in parsed:
            return {"error": "LLM did not return JSON dict", "raw": raw}
        return parsed
    except Exception:
        # try extracting a JSON substring
        start = raw.find("{")
        end = raw.rfind("}") + 1
        try:
            parsed = json.loads(raw[start:end])
            return parsed
        except Exception as e:
            return {"error": "Failed to parse LLM output as JSON", "raw": raw, "exception": str(e)}


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
            # FAILURE LEARNING: Feedback loop from Testing → Learning
            # ════════════════════════════════════════════════════════
            try:
                # 1. Identify which generation step likely caused this
                # If backend tests fail, blame backend_implementation
                blame_step = "backend_implementation" if "pytest" in runner_hint else "frontend_integration"
                blame_agent = "Derek" if "pytest" in runner_hint else "Derek" # Derek does both mostly
                
                from app.learning.failure_store import get_failure_store
                from app.learning.pattern_store import get_pattern_store
                
                fail_store = get_failure_store()
                pattern_store = get_pattern_store()
                
                # 2. Record the failure (Logic/Bug)
                # We interpret test failures as logic bugs in the implementation
                fail_desc = f"Test failed: {issues[0].get('text', '')[:100] if issues else 'Unknown failure'}"
                snippet = issues[0].get('text', '') if issues else ""
                
                fail_store.record_failure(
                    archetype="generic", # We don't have archetype here easily, default to generic
                    agent=blame_agent,
                    step=blame_step,
                    error_type="test_failure",
                    description=fail_desc,
                    code_snippet=snippet,
                    fix_summary=""
                )
                
                # 3. Penalize the "successful" pattern (False Positive Correction)
                # If we previously gave this code a 9/10, we now deduct points
                pattern_store.penalize_pattern(
                    archetype="generic",
                    agent=blame_agent,
                    step=blame_step,
                    penalty=3.0 # Heavy penalty for passing review but failing tests
                )
                
            except Exception as e:
                print(f"[LEARNING] Failed to record test feedback: {e}")

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
) -> Dict[str, Any]:
    """
    Marcus uses this to call Derek/Luna/Victoria for code generation.
    
    PHASE 1-2 OPTIMIZATION:
    - Uses core prompts (cacheable system messages)
    - Sends minimal dynamic context (user message)
    - Reduces token usage by 30-50% per call
    """
    try:
        # PHASE 1: Import prompt management (context optimizer removed)
        from app.llm.prompt_management import (
            CORE_RULES,
            build_context,
            get_relevant_files,
        )

        provider = settings.llm.default_provider
        model = settings.llm.default_model

        # ============================================================
        # PHASE 1: Use CORE PROMPT (Static - cacheable by LLM provider)
        # ============================================================
        core_prompt = CORE_RULES.get(agent_name.lower(), "")
        
        # ============================================================
        # PHASE 2: Build MINIMAL DYNAMIC CONTEXT
        # ============================================================
        
        # Query is combination of task + step
        query = f"{step_name}: {user_request}"

        # Smart File Selection using Attention
        # Instead of generic k=5, we use V!=K to decide context width
        selected_files = files
        if files and len(files) > 5:
            try:
                from app.arbormind import arbormind_route
                
                # 1. Determine Context Mode (V!=K)
                FILE_SELECTION_MODES = [
                    {
                        "id": "narrow",
                        "description": "Specific task, single file fix, minor edit, typo, simple feature",
                        "value": {"max_files": 4, "include_tests": False, "expand_context": False, "rank_bias": "similarity"}
                    },
                    {
                        "id": "broad",
                        "description": "General feature implementation, CRUD, API endpoint, component creation",
                        "value": {"max_files": 10, "include_tests": True, "expand_context": True, "rank_bias": "similarity"}
                    },
                    {
                        "id": "architectural",
                        "description": "Complex integration, refactoring, architectural change, debugging across modules, full system review",
                        "value": {"max_files": 15, "include_tests": True, "expand_context": True, "rank_bias": "similarity"}
                    }
                ]
                
                # Get context configuration with self-evolution tracking
                mode_result = await arbormind_route(
                    query, 
                    FILE_SELECTION_MODES,
                    context_type="file_selection_mode",
                    archetype=archetype or "unknown"
                )
                file_mode_decision_id = mode_result.get("decision_id", "")
                
                context_params = mode_result.get("value", {})
                max_files = int(context_params.get("max_files", 5))
                include_tests = context_params.get("include_tests", False)
                expand_context = context_params.get("expand_context", False)
                
                log("ATTENTION", f"🧠 Context Mode: {mode_result['selected']} (limit: {max_files}, expand: {expand_context})")
                if mode_result.get("evolved"):
                    log("ATTENTION", f"   🧬 Mode evolved from learning history")

                # 2. Select Files using dynamic limit
                # If expand_context is True, we might want to ensure we're looking at ALL files, 
                # but 'files' argument passed here is already filtered by get_relevant_files() glob.
                # However, we can re-filter or ensure tests are included.
                
                candidates = files
                if not include_tests:
                    # Filter out test files if likely present
                    candidates = [f for f in files if "test" not in f.get("path", "").lower()]
                
                file_options = []
                for f in candidates:
                    # Description combines path and a snippet of content for embedding
                    desc = f"Path: {f.get('path', '')}\nContent: {f.get('content', '')[:300]}"
                    file_options.append({"id": f.get("path"), "description": desc, "original": f})
                
                log("ATTENTION", f"   Selecting top {max_files} relevant files from {len(candidates)} candidates...")
                
                # If we have fewer candidates than max, take them all
                if len(candidates) <= max_files:
                    selected_files = candidates
                else:
                    result = await arbormind_route(query, file_options, top_k=max_files)
                    
                    # Get the top ranked files
                    top_ids = [r["id"] for r in result["ranked"]]
                    top_ids = top_ids[:max_files]
                    
                    selected_files = [f for f in files if f.get("path") in top_ids]

                
            except Exception as e:
                log("ATTENTION", f"⚠️ File selection failed: {e}, using fallback")
                selected_files = files[:5]
                file_mode_decision_id = ""  # No decision to track
        else:
            file_mode_decision_id = ""  # No attention routing was needed

        
        # Get memory hint (pattern learning) - kept for quality improvement
        memory_hint = None
        try:
            from app.tracking.memory import get_memory_hint
            memory_hint = get_memory_hint(agent_name, step_name) if step_name else None
        except ImportError:
            pass  # Memory module may not exist yet
            
        # ════════════════════════════════════════════════════════
        # DYNAMIC TOOL SELECTION (V!=K)
        # ════════════════════════════════════════════════════════
        selected_tools = []
        tool_decision_id = ""
        try:
             # Use Attention to select and configure tools
             from app.tools.registry import get_relevant_tools_for_query
             log("ATTENTION", f"🧠 Selecting tools for {step_name}...")
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
        except Exception as e:
             log("ATTENTION", f"⚠️ Tool selection failed: {e}")
        
        # Build context string
        dynamic_context = await build_context(
            agent_name=agent_name,
            task=user_request,
            step_name=step_name,
            archetype=archetype,
            vibe=vibe,
            files=selected_files,  # Use smart selected files
            contracts=contracts,
            errors=errors if is_retry else None,
            memory_hint=memory_hint,
            tools=selected_tools # Inject configured tools
        )


        # ============================================================
        # MAX TOKENS - Step-specific token policies (Option 3 #7)
        # ============================================================
        # Use centralized token policy system for step-aware allocation
        from app.orchestration.token_policy import get_tokens_for_step
        
        max_tokens = get_tokens_for_step(step_name, is_retry=is_retry)

        print(f"[marcus_call_sub_agent] Calling {agent_name} (retry={is_retry}) with max_tokens={max_tokens}")
        print(f"[OPTIMIZATION] Core prompt: ~{len(core_prompt)//4} tokens, Context: ~{len(dynamic_context)//4} tokens")
        
        # ============================================================
        # LLM CALL with OPTIMIZED PROMPTS
        # ============================================================
        raw = await call_llm(
            prompt=dynamic_context,  # MINIMAL dynamic context
            provider=provider,
            model=model,
            system_prompt=core_prompt,  # CORE static rules (cacheable!)
            temperature=0.7,
            max_tokens=max_tokens,
        )

        print(f"[marcus_call_sub_agent] Received {len(raw)} chars from {agent_name}")
        
        # NOTE: Cost tracking now handled by BudgetManager at orchestrator level
        # Handlers call budget.register_usage() after receiving the response

        # Try to parse JSON and normalize into {"files": [...]} schema
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None
        
        # Broadcast the agent's ACTUAL thinking (from the thinking field)
        if project_id and parsed and isinstance(parsed, dict):
            from app.core.logging import log_thinking, log_files
            
            thinking = parsed.get("thinking") or parsed.get("notes") or ""
            if thinking:
                # Use centralized logging for thinking
                log_thinking(agent_name.upper(), thinking, project_id, max_lines=15)
                await _broadcast_agent_thinking(project_id, agent_name, "thinking", thinking)
            elif "approved" in parsed:
                # This is Marcus's supervision response - format it nicely
                approved = parsed.get("approved", False)
                quality = parsed.get("quality_score", "?")
                feedback = parsed.get("feedback", "")
                if approved:
                    msg = f"✅ Approved - Quality: {quality}/10"
                    if feedback:
                        msg += f"\n{feedback[:300]}"
                else:
                    issues = parsed.get("issues", [])
                    msg = f"⚠️ Requesting corrections - Quality: {quality}/10"
                    if issues:
                        msg += "\nIssues: " + ", ".join(str(i)[:100] for i in issues[:3])
                await _broadcast_agent_thinking(project_id, agent_name, "review", msg)
            else:
                # Show file count summary using centralized logging
                files = parsed.get("files", [])
                if files:
                    log_files(agent_name.upper(), files, project_id)



        def to_files_schema(obj: Any) -> Optional[Dict[str, Any]]:
            # Already correct
            if isinstance(obj, dict) and "files" in obj and isinstance(obj["files"], list):
                return obj

            # Single file-like object
            if isinstance(obj, dict) and "path" in obj and "content" in obj:
                return {"files": [obj]}

            # Tests schema: {"tests": [ { "path": "...", "content": "..." }, ... ]}
            if isinstance(obj, dict) and "tests" in obj and isinstance(obj["tests"], list):
                files: List[Dict[str, Any]] = []
                for t in obj["tests"]:
                    if isinstance(t, dict) and "path" in t and "content" in t:
                        files.append(
                            {
                                "path": t["path"],
                                "content": t["content"],
                                **{k: v for k, v in t.items() if k not in ("path", "content")},
                            }
                        )
                if files:
                    return {"files": files}

            return None

        if parsed is not None:
            normalized = to_files_schema(parsed)
        else:
            normalized = None

        if normalized is not None:
            # Happy path: we got a usable files schema
            
            # ════════════════════════════════════════════════════════
            # SELF-EVOLUTION: Report SUCCESS for attention decisions
            # ════════════════════════════════════════════════════════
            try:
                from app.arbormind import report_routing_outcome
                
                # File selection mode worked
                if file_mode_decision_id:
                    report_routing_outcome(
                        decision_id=file_mode_decision_id,
                        success=True,
                        quality_score=8.0,
                        details=f"Agent {agent_name} succeeded with file mode"
                    )
                
                # Tool selection worked (if tracked)
                if tool_decision_id:
                    report_routing_outcome(
                        decision_id=tool_decision_id,
                        success=True,
                        quality_score=8.0,
                        details=f"Agent {agent_name} succeeded with selected tools"
                    )
            except Exception as e:
                log("EVOLUTION", f"⚠️ Failed to report success outcome: {e}")
            
            return {
                "passed": True,
                "output": normalized,
                "raw_generation": raw,
                "issues": [],
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
        try:
            from app.arbormind import report_routing_outcome
            
            quality = 3.0  # Low quality - output wasn't parseable
            
            if file_mode_decision_id:
                report_routing_outcome(
                    decision_id=file_mode_decision_id,
                    success=False,
                    quality_score=quality,
                    details=f"Agent {agent_name} failed - output not parseable"
                )
            
            if tool_decision_id:
                report_routing_outcome(
                    decision_id=tool_decision_id,
                    success=False,
                    quality_score=quality,
                    details=f"Agent {agent_name} failed - output not parseable"
                )
        except Exception:
            pass

        return {
            "passed": False,
            "output": parsed if parsed is not None else raw,
            "raw_generation": raw,
            "issues": issues,
        }

    except Exception as e:
        import traceback
        print(f"[marcus_call_sub_agent] Error: {e}")
        print(traceback.format_exc())
        return {
            "passed": False,
            "output": "",
            "raw_generation": "",
            "issues": [{"description": str(e), "raw": ""}],
        }
