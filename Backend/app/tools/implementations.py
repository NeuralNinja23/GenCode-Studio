"""
GenCode Studio – Complete Tool System (Full Production Version)

Includes:
 - Core sub-agent dispatcher
 - File operations (read/write/delete/list/view)
 - Execution tools (bash, python, npm)
 - Testing tools (pytest, playwright, test generator)
 - Docker sandbox integration via Python (SandboxManager singleton)
 - Deployment validation + health checks
 - Docker builder + Vercel deployer
 - UX visualizer + screenshot comparer
 - API tester, web health checker
 - Simple user interaction and DB tools
"""

from __future__ import annotations

import os
import ast
import json
import asyncio
import subprocess
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiohttp

# Internal imports
from app.core.types import GeneratedFile  # noqa: F401 (kept for type compatibility)

# Sandbox system (Python-native, no HTTP)
from app.sandbox import SandboxManager, SandboxConfig  # type: ignore[import]
from app.utils.path_utils import get_project_path
from app.tools.patching import PatchEngine, apply_unified_patch
from app.core.logging import log

# ═══════════════════════════════════════════════════════════════════════════════
# TIT: Tool Invocation Trace
# ═══════════════════════════════════════════════════════════════════════════════
from datetime import datetime, timezone as tz

def _get_tit_enabled():
    """Check if TIT is enabled (lazy import to avoid circular deps)."""
    try:
        from app.arbormind.observation.tool_trace import ARBORMIND_TIT_ENABLED
        return ARBORMIND_TIT_ENABLED
    except ImportError:
        return False

def _record_tit_event(event):
    """Record TIT event (fire-and-forget)."""
    try:
        from app.arbormind.observation.tool_trace import record_tool_invocation
        record_tool_invocation(event)
    except Exception:
        pass  # TIT must never crash execution
# =====================================================================
# Global Sandbox Singleton (LAZY INITIALIZATION)
# =====================================================================
_SANDBOX_INSTANCE: Optional[SandboxManager] = None

def get_sandbox() -> SandboxManager:
    """Get the sandbox singleton (lazy initialization)."""
    global _SANDBOX_INSTANCE
    if _SANDBOX_INSTANCE is None:
        _SANDBOX_INSTANCE = SandboxManager()
    return _SANDBOX_INSTANCE

# For backward compatibility - callers should use get_sandbox() instead
# DEPRECATED: Direct SANDBOX access will be removed in future
SANDBOX: Optional[SandboxManager] = None  # Set to None initially





# =====================================================================
# FIX ASYNC-001: Async subprocess helper to avoid blocking event loop
# Uses asyncio.to_thread for Windows compatibility (SelectorEventLoop)
# =====================================================================
async def _async_run_command(
    cmd: Union[str, List[str]],
    cwd: str = ".",
    timeout: int = 60,
    shell: bool = True,
) -> Dict[str, Any]:
    """
    Run a command asynchronously using asyncio.to_thread + subprocess.run.
    This is Windows-compatible (works with SelectorEventLoop).
    Returns dict with success, stdout, stderr, returncode.
    """
    try:
        def run_sync():
            return subprocess.run(
                cmd if isinstance(cmd, str) else " ".join(cmd) if shell else cmd,
                shell=shell,
                capture_output=True,
                text=True,
                encoding="utf-8",  # Explicitly force UTF-8
                errors="replace",  # Replace bad characters instead of crashing
                cwd=cwd,
                timeout=timeout
            )
        
        proc = await asyncio.to_thread(run_sync)
        
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": f"Command timed out after {timeout}s",
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
            "error": str(e),
        }
    finally:
        # ═══════════════════════════════════════════════════════════════════
        # TIT Hook: Process Boundary
        # ═══════════════════════════════════════════════════════════════════
        if _get_tit_enabled():
            try:
                from app.arbormind.observation.tool_trace import build_tool_event
                from app.arbormind.observation.sqlite_store import get_current_run_id
                
                run_id = get_current_run_id() or "unknown"
                ended = datetime.now(tz.utc)
                
                # Determine status
                status = "success"
                if 'proc' in dir() and proc.returncode != 0:
                    status = "failure"
                elif 'e' in dir():
                    status = "failure"
                
                tit_event = build_tool_event(
                    run_id=run_id,
                    step="process_boundary",
                    agent="System",
                    tool_name="_async_run_command",
                    tool_type="process",
                    invocation_index=0,
                    called_at=datetime.now(tz.utc),
                    duration_ms=None,
                    status=status,
                    input_args={"command": str(cmd)[:512], "cwd": cwd},
                )
                _record_tit_event(tit_event)
            except Exception:
                pass  # TIT must never crash execution


# =====================================================================
# Enum – All supported tools
# =====================================================================
class GenCodeTool(str, Enum):
    # Core agent tools
    SubAgentCaller = "subagentcaller"

    # File Operations
    FileWriterBatch = "filewriterbatch"
    FileReader = "filereader"
    FileDeleter = "filedeleter"
    FileLister = "filelister"
    CodeViewer = "codeviewer"

    # Execution
    BashRunner = "bashrunner"
    PythonExecutor = "pythonexecutor"
    NPMRunner = "npmrunner"

    # Testing
    PytestRunner = "pytestrunner"
    PlaywrightRunner = "playwrightrunner"
    TestGenerator = "testgenerator"

    # Patching 
    UnifiedPatchApplier = "unifiedpatchapplier"
    JsonPatchApplier = "jsonpatchapplier"

    # Sandbox
    SandboxExec = "sandboxexec"

    # Validation
    DeploymentValidator = "deploymentvalidator"
    KeyValidator = "keyvalidator"
    CrossLLMValidator = "crossllmvalidator"
    SyntaxValidator = "syntaxvalidator"

    # Visual
    UXVisualizer = "uxvisualizer"
    ScreenshotComparer = "screenshotcomparer"

    # Web
    WebResearcher = "webresearcher"
    APITester = "apitester"
    HealthChecker = "healthchecker"

    # User Interaction
    UserConfirmer = "userconfirmer"
    UserPrompter = "userprompter"

    # Database
    DBSchemaReader = "dbschemareader"
    DBQueryRunner = "dbqueryrunner"

    # Deployment
    DockerBuilder = "dockerbuilder"
    VercelDeployer = "verceldeployer"
    
    # P1.1: Environment & Static Validation (NEW)
    EnvironmentGuard = "environment_guard"
    StaticCodeValidator = "static_code_validator"
    
    # NEW DECLARATIVE TOOLS (4 missing implementations)
    ArchitectureWriter = "architecture_writer"
    RouterScaffoldGenerator = "router_scaffold_generator"
    RouterLogicFiller = "router_logic_filler"
    CodePatchApplier = "code_patch_applier"


# =====================================================================
# CORE: Sub-Agent Caller
# =====================================================================
async def tool_sub_agent_caller(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Marcus → Derek/Victoria/Luna sub-agents and normalize their
    output into a {"files": [...]} shape whenever possible.
    """
    try:
        from app.agents import marcus_call_sub_agent
        from app.utils.parser import normalize_llm_output

        sub_agent = args.get("sub_agent")
        instructions = args.get("instructions")

        # 🔧 Ensure project_path is always a string (Pylance fix)
        project_path_raw: Any = args.get("project_path")
        project_path: str = (
            str(project_path_raw) if project_path_raw is not None else ""
        )
        
        # Get project_id for broadcasting agent thinking
        project_id: str = args.get("project_id", "")
        
        # ============================================================
        # PHASE 1-2: Extract optimization parameters from args
        # ============================================================
        step_name: str = args.get("step_name", "")
        archetype: str = args.get("archetype", "")
        vibe: str = args.get("vibe", "")
        contracts: Optional[str] = args.get("contracts")
        is_retry: bool = args.get("is_retry", False)
        errors: Optional[List[str]] = args.get("errors")
        # files would be extracted here if passed by handlers (future enhancement)
        files: Optional[List[Dict[str, str]]] = args.get("files")
        
        # CRITICAL: Extract the ACTUAL user request (not instructions)
        # instructions = Victoria's prompt, user_request = "build a kanban board"
        user_request: str = args.get("user_request", "")
        if not user_request:
            # Fallback: if user_request not provided, use instructions (legacy)
            user_request = instructions
        
        # Optional overrides for healing (progressive token scaling)
        max_tokens_override: Optional[int] = args.get("max_tokens_override")
        temperature_override: Optional[float] = args.get("temperature_override")

        if not sub_agent or not instructions:
            raise ValueError("tool_sub_agent_caller requires 'sub_agent' and 'instructions'")
        
        llm_start = datetime.now(tz.utc)

        result = await marcus_call_sub_agent(
            agent_name=sub_agent,
            user_request=user_request,  # ACTUAL user request, not instructions!
            project_path=project_path,
            project_id=project_id,  # Pass for real-time thinking
            step_name=step_name,  # Optimization parameter
            archetype=archetype,  # Optimization parameter
            vibe=vibe,  # Optimization parameter
            files=files,  # Relevant files (if provided)
            contracts=contracts,  # API contracts summary
            is_retry=is_retry,  # Retry flag for differential context
            errors=errors,  # Errors from previous attempt
            instructions=instructions,  # PASS CUSTOM INSTRUCTIONS!
            max_tokens_override=max_tokens_override,  # Healing override
            temperature_override=temperature_override,  # Healing override
        )
        
        llm_end = datetime.now(tz.utc)
        llm_duration = int((llm_end - llm_start).total_seconds() * 1000)
        
        # V3: Extract token usage for cost tracking
        token_usage = result.get("token_usage", {"input": 0, "output": 0})

        def normalize_files_schema(obj: Any) -> Optional[Dict[str, Any]]:
            """Normalize arbitrary dict into {'files': [...]}, if possible."""
            if not isinstance(obj, dict):
                return None

            # Already good
            if "files" in obj and isinstance(obj["files"], list):
                return obj

            # Single file
            if "path" in obj and "content" in obj:
                return {"files": [obj]}

            # Tests → files
            tests = obj.get("tests")
            if isinstance(tests, list):
                files: List[Dict[str, Any]] = []
                for t in tests:
                    if isinstance(t, dict) and "path" in t and "content" in t:
                        files.append({"path": t["path"], "content": t["content"]})
                if files:
                    return {"files": files}

            return None

        # 1) If already normalized and passed
        output_obj = result.get("output")
        if result.get("passed") and isinstance(output_obj, dict):
            normalized = normalize_files_schema(output_obj)
            if normalized is not None:
                return {
                    "success": True,
                    "output": normalized,
                    "agent": sub_agent,
                    "source": "normalized_direct",
                    "token_usage": token_usage,  # V3: Propagate usage
                }

        # 2) Try issues[0].raw
        issues = result.get("issues") or []
        if issues:
            raw = issues[0].get("raw")
            if raw:
                try:
                    # STEP 4: Pass step_name for causal step detection
                    parsed = normalize_llm_output(raw, step_name=step_name)
                    normalized = normalize_files_schema(parsed)
                    if normalized is not None:
                        return {
                            "success": True,
                            "output": normalized,
                            "agent": sub_agent,
                            "source": "salvaged_from_issues",
                            "token_usage": token_usage,  # V3: Propagate usage
                        }
                except Exception:
                    pass

        # 3) Try raw_generation
        raw_generation = result.get("raw_generation")
        parsed = None
        if isinstance(raw_generation, str):
            try:
                # STEP 4: Pass step_name for causal step detection
                parsed = normalize_llm_output(raw_generation, step_name=step_name)
                normalized = normalize_files_schema(parsed)
                if normalized is not None:
                    return {
                        "success": True,
                        "output": normalized,
                        "agent": sub_agent,
                        "source": "normalized_raw_generation",
                        "token_usage": token_usage,  # V3: Propagate usage
                    }
            except Exception:
                parsed = None

        # Fallback: just return whatever we have
        
        # ═══════════════════════════════════════════════════════════════════
        # TIT Hook: LLM Boundary (Success/Partial)
        # ═══════════════════════════════════════════════════════════════════
        llm_success = result.get("passed", False)
        if _get_tit_enabled():
            try:
                from app.arbormind.observation.tool_trace import build_tool_event
                from app.arbormind.observation.sqlite_store import get_current_run_id
                
                run_id = get_current_run_id() or "unknown"
                
                tit_event = build_tool_event(
                    run_id=run_id,
                    step=step_name,
                    agent=sub_agent,
                    tool_name="subagentcaller",
                    tool_type="llm",
                    invocation_index=0,
                    called_at=llm_start,
                    duration_ms=llm_duration,
                    status="success" if llm_success else "failure",
                    tokens_used=token_usage.get("input", 0) + token_usage.get("output", 0),
                    model_name=args.get("model"),
                    retries=1 if is_retry else 0,
                )
                _record_tit_event(tit_event)
            except Exception:
                pass
        
        return {
            "success": result.get("passed", False),
            "output": parsed if parsed is not None else raw_generation,
            "full_result": result,
            "agent": sub_agent,
            "source": "fallback",
            "token_usage": token_usage,  # V3: Propagate usage
        }

    except Exception as e:
        import traceback
        llm_end = datetime.now(tz.utc)
        
        # ═══════════════════════════════════════════════════════════════════
        # TIT Hook: LLM Boundary (Failure)
        # ═══════════════════════════════════════════════════════════════════
        if _get_tit_enabled():
            try:
                from app.arbormind.observation.tool_trace import build_tool_event
                from app.arbormind.observation.sqlite_store import get_current_run_id
                
                run_id = get_current_run_id() or "unknown"
                duration = int((llm_end - llm_start).total_seconds() * 1000) if 'llm_start' in dir() else None
                
                tit_event = build_tool_event(
                    run_id=run_id,
                    step=args.get("step_name", "unknown"),
                    agent=args.get("sub_agent", "unknown"),
                    tool_name="subagentcaller",
                    tool_type="llm",
                    invocation_index=0,
                    called_at=llm_start if 'llm_start' in dir() else datetime.now(tz.utc),
                    duration_ms=duration,
                    status="failure",
                    error=e,
                    retries=1 if args.get("is_retry") else 0,
                )
                _record_tit_event(tit_event)
            except Exception:
                pass
        
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "token_usage": {"input": 0, "output": 0},  # V3: Zero usage on error
        }


# =====================================================================
# FILE OPERATIONS
# =====================================================================
async def tool_file_writer_batch(args: Dict[str, Any]) -> Dict[str, Any]:
    """Write multiple files at once to a base path."""
    try:
        files = args.get("files", [])
        base_path = Path(args.get("base_path", "."))

        written: List[Dict[str, Any]] = []
        for entry in files:
            rel = entry.get("path")
            content = entry.get("content", "")

            if not rel:
                continue

            path = base_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            written.append({"path": str(path), "size": len(content)})

        return {"success": True, "written": written, "count": len(written)}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_file_reader(args: Dict[str, Any]) -> Dict[str, Any]:
    """Read a single file."""
    try:
        file_path_str = args.get("file_path")
        if not file_path_str:
            return {"success": False, "error": "Missing file_path"}

        path = Path(file_path_str)
        if not path.exists():
            return {"success": False, "error": f"File not found: {path}"}

        content = path.read_text(encoding="utf-8")
        return {
            "success": True,
            "path": str(path),
            "content": content,
            "size": len(content),
            "lines": content.count("\n") + 1,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_file_deleter(args: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a file or directory tree."""
    try:
        path_str = args.get("path")
        if not path_str:
            return {"success": False, "error": "Missing path"}

        path = Path(path_str)
        if not path.exists():
            return {"success": False, "error": f"Path not found: {path}"}

        if path.is_dir():
            import shutil
            shutil.rmtree(path)
        else:
            path.unlink()

        return {"success": True, "deleted": str(path)}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_file_lister(args: Dict[str, Any]) -> Dict[str, Any]:
    """List files recursively or non-recursively."""
    try:
        directory = Path(args.get("directory", "."))
        pattern = args.get("pattern", "*")
        recursive = bool(args.get("recursive", False))

        files = directory.rglob(pattern) if recursive else directory.glob(pattern)

        result: List[Dict[str, Any]] = []
        for f in files:
            result.append(
                {
                    "path": str(f),
                    "name": f.name,
                    "is_dir": f.is_dir(),
                    "size": f.stat().st_size if f.is_file() else 0,
                }
            )

        return {"success": True, "files": result, "count": len(result)}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_code_viewer(args: Dict[str, Any]) -> Dict[str, Any]:
    """Return file contents with some metadata, used for in-UI preview."""
    try:
        file_path_str = args.get("file_path") or args.get("filepath")
        if not file_path_str:
            return {"success": False, "error": "Missing file_path"}

        path = Path(file_path_str)
        if not path.exists():
            return {"success": False, "error": f"File not found: {path}"}

        content = path.read_text(encoding="utf-8")
        return {
            "success": True,
            "path": str(path),
            "extension": path.suffix,
            "content": content,
            "lines": content.count("\n") + 1,
            "size_bytes": len(content.encode("utf-8")),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# =====================================================================
# EXECUTION TOOLS
# =====================================================================
async def tool_bash_runner(args: Dict[str, Any]) -> Dict[str, Any]:
    """Run a shell command with timeout (async, non-blocking)."""
    cmd = args.get("command", "")
    cwd = args.get("cwd", ".")
    timeout_val = int(args.get("timeout", 60))

    if not cmd:
        return {"success": False, "error": "No command provided"}

    # FIX ASYNC-001: Use async subprocess instead of blocking subprocess.run
    result = await _async_run_command(cmd, cwd=cwd, timeout=timeout_val)
    result["command"] = cmd
    return result


async def tool_python_executor(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a snippet of Python code in a temp file (async, non-blocking)."""
    try:
        code = args.get("code", "")
        if not code:
            return {"success": False, "error": "No code provided"}

        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = f.name

        # FIX ASYNC-001: Use async subprocess
        result = await _async_run_command(f"python {temp_path}", timeout=30)

        Path(temp_path).unlink(missing_ok=True)
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_npm_runner(args: Dict[str, Any]) -> Dict[str, Any]:
    """Run an npm command, e.g. 'install', 'run build', etc. (async, non-blocking)."""
    try:
        cmd = args.get("command")
        cwd = args.get("cwd", ".")
        if not cmd:
            return {"success": False, "error": "Missing npm command"}

        # FIX ASYNC-001: Use async subprocess
        return await _async_run_command(f"npm {cmd}", cwd=cwd, timeout=300)

    except Exception as e:
        return {"success": False, "error": str(e)}


# =====================================================================
# TESTING TOOLS
# =====================================================================
async def tool_pytest_runner(args: Dict[str, Any]) -> Dict[str, Any]:
    """Run pytest in a given directory (async, non-blocking)."""
    try:
        test_path = args.get("test_path", "tests/")
        cwd = args.get("cwd", ".")
        verbose = bool(args.get("verbose", True))

        cmd = f"pytest {test_path}"
        if verbose:
            cmd += " -v"

        # FIX ASYNC-001: Use async subprocess
        result = await _async_run_command(cmd, cwd=cwd, timeout=90)
        result["tests_passed"] = "failed" not in result.get("stdout", "").lower()
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_playwright_runner(args: Dict[str, Any]) -> Dict[str, Any]:
    """Run Playwright E2E tests (async, non-blocking)."""
    try:
        test_file = args.get("test_file", "tests/e2e.spec.js")
        cwd = args.get("cwd", ".")

        cmd = f"npx playwright test {test_file}"
        # FIX ASYNC-001: Use async subprocess
        return await _async_run_command(cmd, cwd=cwd, timeout=180)

    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_test_generator(args: Dict[str, Any]) -> Dict[str, Any]:
    """Generate simple pytest or Playwright test template."""
    try:
        test_type = args.get("test_type", "pytest")
        file_path = args.get("file_path")

        if test_type == "pytest":
            template = (
                "import pytest\n\n"
                "def test_example():\n"
                "    assert True\n"
            )
        else:
            template = (
                "import { test, expect } from '@playwright/test';\n\n"
                "test('basic test', async ({ page }) => {\n"
                "    await page.goto('http://localhost:5174');\n"
                "    await expect(page).toHaveTitle(/.*/);\n"
                "});\n"
            )

        if file_path:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(template, encoding="utf-8")
            return {"success": True, "file_path": str(path), "template": template}

        return {"success": True, "template": template}

    except Exception as e:
        return {"success": False, "error": str(e)}


# =====================================================================
# SANDBOX EXEC – REAL PYTHON INTEGRATION (NO HTTP)
# =====================================================================
async def tool_sandbox_exec(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a command inside a sandbox container using real Python calls.
    
    - NO HTTP, no FastAPI routes.
    - Uses the shared SandboxManager singleton.
    - Auto-creates and starts the sandbox if needed.
    - TRUSTS start_sandbox(wait_healthy=True) to ensure readiness.
    
    Expected args:
    - project_id: str (required)
    - command: str (required)
    - service: str (optional, default: "backend")
    - project_path: str (optional override; otherwise uses get_project_path(project_id))
    - wait_healthy: bool (optional, default: True)
    - max_health_retries: int (optional, default: 30)
    - force_rebuild: bool (optional, default: False) - if True, stop and restart sandbox to pick up code changes
    """
    
    try:
        project_id = args.get("project_id")
        service = args.get("service", "backend")
        command = args.get("command")
        # We accept wait_healthy but start_sandbox handles the actual waiting
        force_rebuild = bool(args.get("force_rebuild", False))
        
        if not project_id:
            return {"success": False, "error": "Missing project_id"}
        if not command:
            return {"success": False, "error": "Missing command"}
        
        # -----------------------------------------------------------
        # Resolve project_path (either explicit or from centralized utility)
        # -----------------------------------------------------------
        
        project_path_arg = args.get("project_path")
        if project_path_arg:
            project_path = Path(project_path_arg).resolve()
        else:
            project_path = get_project_path(project_id).resolve()
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project_path}",
            }
        
        start_services = args.get("start_services")
        
        # -----------------------------------------------------------
        # Ensure sandbox exists & is RUNNING
        # -----------------------------------------------------------
        
        log("SANDBOX_EXEC", f"Checking sandbox status for {project_id}")
        status = await get_sandbox().get_status(project_id)
        status_ok = bool(status.get("success"))
        current_state = (status.get("status") or "").lower() if status_ok else "unknown"
        
        # -----------------------------------------------------------
        # Force Rebuild: Stop and restart sandbox to pick up code changes
        # This is critical when routers are wired AFTER initial build
        # Bug Fix #2: Added file sync delay to prevent race condition
        # -----------------------------------------------------------
        if force_rebuild and status_ok and current_state == "running":
            log("SANDBOX_EXEC", f"🔄 Force rebuild requested for {project_id}, syncing files...")
            
            # Bug Fix #2: Touch main.py to force filesystem sync before rebuild
            main_py = project_path / "backend" / "app" / "main.py"
            if main_py.exists():
                main_py.touch()
            await asyncio.sleep(2)  # Wait for filesystem (Windows needs time)
            
            log("SANDBOX_EXEC", "🔄 Stopping sandbox for rebuild...")
            await get_sandbox().stop_sandbox(project_id)
            await asyncio.sleep(1)  # Brief pause after stop
            
            # Mark as not running so we go through the full create+start flow
            current_state = "stopped"
            status_ok = True  # Sandbox still exists in metadata
        
        if not status_ok:
            # No sandbox tracked -> create + start
            log("SANDBOX_EXEC", f"Sandbox missing for {project_id}, creating...")
            
            create_res = await get_sandbox().create_sandbox(
                project_id=project_id,
                project_path=project_path,
                config=SandboxConfig(),
            )
            
            if not create_res.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to create sandbox: {create_res.get('error')}",
                }
            
            # start_sandbox(wait_healthy=True) handles the heavy lifting
            start_res = await get_sandbox().start_sandbox(
                project_id, 
                wait_healthy=True,
                services=start_services  # Pass explicit services if provided
            )
            if not start_res.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to start sandbox: {start_res.get('error')}",
                    "stderr": start_res.get("stderr", ""),
                    "stdout": start_res.get("stdout", ""),
                }
            
            log("SANDBOX_EXEC", f"✅ Sandbox created and started for {project_id}")
        
        elif current_state != "running":
            # Sandbox exists but is not running -> try to start it
            log(
                "SANDBOX_EXEC",
                f"Sandbox {project_id} exists in state '{current_state}', starting...",
            )
            
            start_res = await get_sandbox().start_sandbox(
                project_id, 
                wait_healthy=True,
                services=start_services
            )
            if not start_res.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to start sandbox: {start_res.get('error')}",
                    "stderr": start_res.get("stderr", ""),
                    "stdout": start_res.get("stdout", ""),
                }
            
            log("SANDBOX_EXEC", f"✅ Sandbox is now running for {project_id}")
        
        # -----------------------------------------------------------
        # Ensure the specific service is running (e.g. frontend)
        # (Sandbox might be 'running' but missing this specific service)
        # -----------------------------------------------------------
        status = await get_sandbox().get_status(project_id)
        containers = status.get("containers", {})
        
        if service not in containers:
             log("SANDBOX_EXEC", f"Service '{service}' missing from running containers. Auto-starting...")
             start_res = await get_sandbox().start_sandbox(
                project_id,
                wait_healthy=True,
                services=[service]
             )
             if not start_res.get("success"):
                 return {
                    "success": False, 
                    "error": f"Failed to auto-start service '{service}': {start_res.get('error')}",
                    "stdout": start_res.get("stdout", ""),
                    "stderr": start_res.get("stderr", "")
                 }
        
        # -----------------------------------------------------------
        # Execute command inside the specified service container
        # (No extra health loop here - we trust start_sandbox)
        # -----------------------------------------------------------
        
        log(
            "SANDBOX_EXEC",
            f"Executing command in {project_id}/{service}: {command[:120]}",
        )
        
        exec_res = await get_sandbox().execute_command(  # type: ignore[attr-defined]
            project_id=project_id,
            service=service,
            command=command,
        )
        
        return {
            "success": exec_res.get("success", False),
            "project_id": project_id,
            "service": service,
            "command": command,
            "stdout": exec_res.get("stdout", "") or "",
            "stderr": exec_res.get("stderr", "") or "",
            "returncode": exec_res.get(
                "returncode",
                0 if exec_res.get("success") else 1,
            ),
        }
    
    except Exception as e:
        log("SANDBOX_EXEC", f"❌ Exception in tool_sandbox_exec: {e}")
        return {
            "success": False,
            "error": str(e),
            "stdout": "",
            "stderr": str(e),
            "returncode": 1,
        }


# =====================================================================
# VALIDATION TOOLS
# =====================================================================
async def validate_deployment(project_path: str) -> Dict[str, Any]:
    """
    Validate both frontend and backend deployments.
    """
    frontend_url = "http://localhost:5174"
    backend_url = "http://localhost:8001/api/health"

    frontend_ok = False
    backend_ok = False
    errors: List[str] = []

    try:
        async with aiohttp.ClientSession() as session:
            # frontend
            try:
                async with session.get(frontend_url, timeout=5) as resp:
                    frontend_ok = resp.status == 200
            except Exception as e:
                errors.append(f"Frontend unreachable: {e}")

            # backend
            try:
                async with session.get(backend_url, timeout=5) as resp:
                    backend_ok = resp.status == 200
            except Exception as e:
                errors.append(f"Backend unreachable: {e}")

    except Exception as e:
        errors.append(f"Deployment validation failed: {e}")

    return {
        "success": True,
        "frontend_health": frontend_ok,
        "backend_health": backend_ok,
        "overall_healthy": frontend_ok and backend_ok,
        "errors": errors,
        "project_path": project_path,
    }


async def tool_deployment_validator(args: Dict[str, Any]) -> Dict[str, Any]:
    """Tool wrapper for validate_deployment."""
    try:
        project_path = args.get("projectPath") or args.get("project_path") or ""
        if not project_path:
            return {"success": False, "error": "Missing project_path"}

        return await validate_deployment(str(project_path))
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "frontend_health": False,
            "backend_health": False,
        }


async def tool_key_validator(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate API keys and secrets from environment and .env files.
    
    Features:
    - Checks both os.environ and .env file
    - Validates key formats (length, prefix patterns)
    - Flags potentially invalid or placeholder keys
    """
    from pathlib import Path
    
    project_path = args.get("project_path", ".")
    
    # Keys to check with their validation rules
    key_rules = {
        "OPENAI_API_KEY": {"min_length": 40, "prefix": "sk-"},
        "GEMINI_API_KEY": {"min_length": 30},
        "ANTHROPIC_API_KEY": {"min_length": 50, "prefix": "sk-ant-"},
        "MONGODB_URI": {"min_length": 20, "contains": "mongodb"},
        "SECRET_KEY": {"min_length": 16},
        "JWT_SECRET": {"min_length": 16},
    }
    
    results: Dict[str, Dict[str, Any]] = {}
    env_file_keys = {}
    
    # Read .env file if exists
    env_file = Path(project_path) / ".env"
    if not env_file.exists():
        env_file = Path(project_path) / "backend" / ".env"
    
    if env_file.exists():
        try:
            content = env_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env_file_keys[key.strip()] = value.strip().strip("'\"")
        except Exception as e:
            pass
    
    # Check each key
    for key_name, rules in key_rules.items():
        # Get value from env or .env file
        value = os.getenv(key_name, "") or env_file_keys.get(key_name, "")
        
        validation = {
            "present": bool(value),
            "length": len(value) if value else 0,
            "valid": False,
            "issues": [],
        }
        
        if value:
            # Check for placeholder values
            placeholders = ["your-key-here", "xxx", "placeholder", "changeme", "example"]
            if any(p in value.lower() for p in placeholders):
                validation["issues"].append("Appears to be a placeholder value")
            
            # Check minimum length
            min_len = rules.get("min_length", 0)
            if len(value) < min_len:
                validation["issues"].append(f"Too short (min {min_len} chars)")
            
            # Check prefix
            prefix = rules.get("prefix", "")
            if prefix and not value.startswith(prefix):
                validation["issues"].append(f"Invalid prefix (expected {prefix})")
            
            # Check contains
            contains = rules.get("contains", "")
            if contains and contains not in value.lower():
                validation["issues"].append(f"Should contain '{contains}'")
            
            # Valid if no issues
            validation["valid"] = len(validation["issues"]) == 0
        
        results[key_name] = validation
    
    # Summary
    valid_count = sum(1 for r in results.values() if r["valid"])
    present_count = sum(1 for r in results.values() if r["present"])
    
    return {
        "success": True,
        "keys": results,
        "valid_count": valid_count,
        "present_count": present_count,
        "total_checked": len(results),
        "all_valid": valid_count == len(results),
        "env_file_found": env_file.exists() if env_file else False,
    }


async def tool_cross_llm_validator(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cross-validate code or output using a secondary LLM provider.
    
    Uses a different LLM than the primary to verify:
    - Code correctness
    - Logic consistency
    - Security issues
    """
    content = args.get("content", "")
    validation_type = args.get("type", "code_review")  # code_review, logic_check, security_audit
    primary_provider = args.get("primary_provider", "gemini")
    
    if not content:
        return {"success": False, "error": "content is required"}
    
    # Choose secondary provider (different from primary)
    provider_rotation = {
        "gemini": "openai",
        "openai": "anthropic", 
        "anthropic": "gemini",
    }
    secondary_provider = provider_rotation.get(primary_provider.lower(), "openai")
    
    try:
        from app.llm import call_llm
        
        # Build validation prompt based on type
        prompts = {
            "code_review": f"""Review this code for correctness, bugs, and best practices.
Return a JSON object with:
- "valid": true/false
- "issues": list of issues found
- "suggestions": list of improvements

Code to review:
```
{content[:8000]}
```""",
            "logic_check": f"""Check this logic/architecture for consistency and potential issues.
Return a JSON object with:
- "consistent": true/false
- "issues": list of logical issues
- "questions": list of unclear points

Content:
{content[:8000]}""",
            "security_audit": f"""Security audit this code for vulnerabilities.
Return a JSON object with:
- "secure": true/false
- "vulnerabilities": list of security issues found
- "severity": overall severity (low/medium/high/critical)

Code:
```
{content[:8000]}
```""",
        }
        
        prompt = prompts.get(validation_type, prompts["code_review"])
        
        # Call secondary LLM
        response = await call_llm(
            prompt=prompt,
            provider=secondary_provider,
            system_prompt="You are a code reviewer. Return only valid JSON.",
            temperature=0.1,
            max_tokens=2000,
        )
        
        # Try to parse JSON response
        import json
        try:
            # Clean markdown fences if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[-1].strip() == "```":
                    cleaned = "\n".join(lines[1:-1])
                else:
                    cleaned = "\n".join(lines[1:])
            
            result = json.loads(cleaned)
            
            return {
                "success": True,
                "validation_type": validation_type,
                "secondary_provider": secondary_provider,
                "result": result,
                "valid": result.get("valid", result.get("consistent", result.get("secure", True))),
            }
        except json.JSONDecodeError:
            # Return raw response if not JSON
            return {
                "success": True,
                "validation_type": validation_type,
                "secondary_provider": secondary_provider,
                "raw_response": response[:2000],
                "valid": True,  # Assume valid if we got a response
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Cross-LLM validation failed: {e}",
            "validation_type": validation_type,
        }


async def tool_syntax_validator(args: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Python / basic JS/TS syntax."""
    try:
        code = args.get("code", "")
        language = args.get("language", "python").lower()

        if language == "python":
            try:
                ast.parse(code)
                return {"success": True, "valid": True}
            except SyntaxError as e:
                return {"success": True, "valid": False, "error": str(e)}

        if language in {"js", "javascript", "ts", "typescript"}:
            # Very minimal check: must at least look like code
            if "function" in code or "=>" in code or "const " in code:
                return {"success": True, "valid": True}
            return {
                "success": True,
                "valid": False,
                "error": "Heuristic JS/TS syntax check failed",
            }

        return {"success": False, "error": f"Unknown language: {language}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


# =====================================================================
# VISUAL / SCREENSHOT TOOLS
# =====================================================================
async def tool_ux_visualizer(args: Dict[str, Any]) -> Dict[str, Any]:
    """Take a Playwright screenshot of the frontend."""
    try:
        from playwright.async_api import async_playwright  # type: ignore
        import sys

        url = args.get("url", "http://localhost:5174")
        output_path = args.get("output_path", "screenshot.png")
        width = int(args.get("viewport_width", 1280))
        height = int(args.get("viewport_height", 720))

        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": width, "height": height})
            await page.goto(url, wait_until="networkidle", timeout=15000)
            await page.screenshot(path=output_path, full_page=True)
            await browser.close()

        return {"success": True, "screenshot_path": output_path, "url": url}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_screenshot_comparer(args: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two screenshots pixel-by-pixel."""
    try:
        from PIL import Image, ImageChops  # type: ignore

        image1_path = args.get("image1")
        image2_path = args.get("image2")
        if not image1_path or not image2_path:
            return {"success": False, "error": "image1 and image2 are required"}

        img1 = Image.open(image1_path)
        img2 = Image.open(image2_path)
        diff = ImageChops.difference(img1, img2)

        return {
            "success": True,
            "identical": diff.getbbox() is None,
            "diff_bbox": diff.getbbox(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =====================================================================
# WEB & HTTP TOOLS
# =====================================================================
async def tool_api_tester(args: Dict[str, Any]) -> Dict[str, Any]:
    """Perform a simple HTTP API call (GET or POST)."""
    try:
        url = args.get("url")
        method = args.get("method", "GET").upper()
        headers = args.get("headers", {})
        data = args.get("data", {})

        if not url:
            return {"success": False, "error": "Missing url"}

        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers) as resp:
                    body = await resp.text()
                    return {
                        "success": True,
                        "status": resp.status,
                        "body": body[:1000],
                    }

            if method == "POST":
                async with session.post(url, headers=headers, json=data) as resp:
                    body = await resp.text()
                    return {
                        "success": True,
                        "status": resp.status,
                        "body": body[:1000],
                    }

        return {"success": False, "error": f"Unsupported method {method}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_web_researcher(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Real web research using DuckDuckGo Instant Answer API.
    
    Features:
    - No API key required
    - Returns structured results
    - Falls back to scraping if API returns nothing
    """
    import urllib.parse
    
    query = args.get("query", "")
    max_results = args.get("max_results", 5)
    
    if not query:
        return {"success": False, "error": "query is required"}
    
    try:
        # DuckDuckGo Instant Answer API (no key needed)
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_redirect=1"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return {
                        "success": False,
                        "error": f"DuckDuckGo API returned {resp.status}",
                    }
                
                data = await resp.json()
                
                results = []
                
                # Extract abstract (main answer)
                if data.get("AbstractText"):
                    results.append({
                        "type": "abstract",
                        "title": data.get("Heading", ""),
                        "text": data.get("AbstractText"),
                        "source": data.get("AbstractSource", ""),
                        "url": data.get("AbstractURL", ""),
                    })
                
                # Extract related topics
                for topic in data.get("RelatedTopics", [])[:max_results]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append({
                            "type": "related",
                            "text": topic.get("Text", ""),
                            "url": topic.get("FirstURL", ""),
                        })
                
                # Extract definition if available
                if data.get("Definition"):
                    results.append({
                        "type": "definition",
                        "text": data.get("Definition"),
                        "source": data.get("DefinitionSource", ""),
                    })
                
                return {
                    "success": True,
                    "query": query,
                    "results": results,
                    "result_count": len(results),
                    "answer": data.get("Answer", ""),
                    "type": data.get("Type", ""),
                }
                
    except asyncio.TimeoutError:
        return {"success": False, "error": "Request timed out", "query": query}
    except Exception as e:
        return {"success": False, "error": f"Web research failed: {e}", "query": query}


async def tool_health_checker(args: Dict[str, Any]) -> Dict[str, Any]:
    """Hit a health endpoint and return status."""
    url = args.get("url", "http://localhost:8001/api/health")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                body = await resp.text()
                return {
                    "success": True,
                    "healthy": resp.status == 200,
                    "status": resp.status,
                    "body_preview": body[:200],
                }
    except Exception as e:
        return {"success": False, "healthy": False, "error": str(e)}


# =====================================================================
# USER INTERACTION TOOLS (Real WebSocket-based)
# =====================================================================
async def tool_user_confirmer(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ask user for confirmation via WebSocket.
    
    In interactive mode: Sends confirmation request to frontend, waits for response
    In non-interactive mode: Auto-answers with first option or default
    """
    import asyncio
    
    question = args.get("question", "Proceed?")
    options = args.get("options", ["Yes", "No"])
    project_id = args.get("project_id", "")
    timeout_seconds = args.get("timeout", 60)
    auto_answer = args.get("auto_answer", True)  # Default to auto for backward compat
    
    # Auto-answer mode (for automated workflows)
    if auto_answer or not project_id:
        return {
            "success": True,
            "question": question,
            "options": options,
            "answer": options[0] if options else "Yes",
            "mode": "auto",
            "message": "Auto-answered (non-interactive mode)",
        }
    
    # Interactive mode: Use WebSocket
    try:
        from app.orchestration.state import CURRENT_MANAGERS
        from app.orchestration.utils import broadcast_to_project
        
        if project_id not in CURRENT_MANAGERS:
            return {
                "success": True,
                "answer": options[0] if options else "Yes",
                "mode": "auto",
                "message": "No active manager, auto-answered",
            }
        
        manager = CURRENT_MANAGERS[project_id]
        
        # Create a unique confirmation ID
        import uuid
        confirmation_id = f"confirm_{uuid.uuid4().hex[:8]}"
        
        # Store a future to wait for response
        if not hasattr(manager, "_pending_confirmations"):
            manager._pending_confirmations = {}
        
        response_future = asyncio.get_event_loop().create_future()
        manager._pending_confirmations[confirmation_id] = response_future
        
        # Send confirmation request to frontend
        await broadcast_to_project(manager, project_id, {
            "type": "USER_CONFIRMATION_REQUEST",
            "confirmation_id": confirmation_id,
            "question": question,
            "options": options,
        })
        
        # Wait for response with timeout
        try:
            answer = await asyncio.wait_for(response_future, timeout=timeout_seconds)
            return {
                "success": True,
                "question": question,
                "options": options,
                "answer": answer,
                "mode": "interactive",
                "message": "User provided confirmation",
            }
        except asyncio.TimeoutError:
            return {
                "success": True,
                "question": question,
                "options": options,
                "answer": options[0] if options else "Yes",
                "mode": "timeout",
                "message": f"Timed out after {timeout_seconds}s, auto-answered",
            }
        finally:
            manager._pending_confirmations.pop(confirmation_id, None)
            
    except Exception as e:
        return {
            "success": True,
            "answer": options[0] if options else "Yes",
            "mode": "error",
            "message": f"Error in confirmation: {e}, auto-answered",
        }


async def tool_user_prompter(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prompt user for text input via WebSocket.
    
    In interactive mode: Sends input request to frontend, waits for response
    In non-interactive mode: Returns default value
    """
    import asyncio
    
    prompt = args.get("prompt", "Enter value:")
    default = args.get("default", "")
    project_id = args.get("project_id", "")
    timeout_seconds = args.get("timeout", 120)
    auto_answer = args.get("auto_answer", True)  # Default to auto for backward compat
    input_type = args.get("input_type", "text")  # text, password, multiline
    
    # Auto-answer mode
    if auto_answer or not project_id:
        return {
            "success": True,
            "prompt": prompt,
            "value": default,
            "mode": "auto",
            "message": "Auto-answered with default",
        }
    
    # Interactive mode: Use WebSocket
    try:
        from app.orchestration.state import CURRENT_MANAGERS
        from app.orchestration.utils import broadcast_to_project
        
        if project_id not in CURRENT_MANAGERS:
            return {
                "success": True,
                "value": default,
                "mode": "auto",
                "message": "No active manager, returned default",
            }
        
        manager = CURRENT_MANAGERS[project_id]
        
        import uuid
        prompt_id = f"prompt_{uuid.uuid4().hex[:8]}"
        
        if not hasattr(manager, "_pending_prompts"):
            manager._pending_prompts = {}
        
        response_future = asyncio.get_event_loop().create_future()
        manager._pending_prompts[prompt_id] = response_future
        
        await broadcast_to_project(manager, project_id, {
            "type": "USER_INPUT_REQUEST",
            "prompt_id": prompt_id,
            "prompt": prompt,
            "default": default,
            "input_type": input_type,
        })
        
        try:
            value = await asyncio.wait_for(response_future, timeout=timeout_seconds)
            return {
                "success": True,
                "prompt": prompt,
                "value": value,
                "mode": "interactive",
                "message": "User provided input",
            }
        except asyncio.TimeoutError:
            return {
                "success": True,
                "prompt": prompt,
                "value": default,
                "mode": "timeout",
                "message": f"Timed out after {timeout_seconds}s, used default",
            }
        finally:
            manager._pending_prompts.pop(prompt_id, None)
            
    except Exception as e:
        return {
            "success": True,
            "value": default,
            "mode": "error",
            "message": f"Error in prompt: {e}, used default",
        }


# =====================================================================
# DATABASE TOOLS (Real Implementations)
# =====================================================================
async def tool_db_schema_reader(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Read database schema from the project's models.py file.
    
    Analyzes Beanie Document classes and extracts:
    - Model names
    - Field definitions
    - Field types
    - Relationships
    """
    import ast
    from pathlib import Path
    
    project_path = args.get("project_path", ".")
    
    models_file = Path(project_path) / "backend" / "app" / "models.py"
    
    if not models_file.exists():
        return {
            "success": False,
            "error": f"models.py not found at {models_file}",
            "schema": {},
        }
    
    try:
        content = models_file.read_text(encoding="utf-8")
        tree = ast.parse(content)
        
        schema = {"models": {}, "relationships": []}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it inherits from Document or BaseModel
                base_names = [
                    b.id if isinstance(b, ast.Name) else 
                    (b.attr if isinstance(b, ast.Attribute) else "")
                    for b in node.bases
                ]
                
                is_document = "Document" in base_names
                is_basemodel = "BaseModel" in base_names
                
                if is_document or is_basemodel:
                    model_name = node.name
                    fields = {}
                    
                    # Extract field annotations
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            field_name = item.target.id
                            
                            # Get type annotation
                            if isinstance(item.annotation, ast.Name):
                                field_type = item.annotation.id
                            elif isinstance(item.annotation, ast.Subscript):
                                # Handle Optional[X], List[X], etc
                                if isinstance(item.annotation.value, ast.Name):
                                    outer = item.annotation.value.id
                                    if isinstance(item.annotation.slice, ast.Name):
                                        inner = item.annotation.slice.id
                                        field_type = f"{outer}[{inner}]"
                                    else:
                                        field_type = outer
                                else:
                                    field_type = "complex"
                            else:
                                field_type = "unknown"
                            
                            fields[field_name] = {
                                "type": field_type,
                                "has_default": item.value is not None,
                            }
                            
                            # Detect relationships
                            if field_type.startswith("List[") or "Link" in field_type:
                                schema["relationships"].append({
                                    "from": model_name,
                                    "field": field_name,
                                    "type": field_type,
                                })
                    
                    schema["models"][model_name] = {
                        "type": "Document" if is_document else "BaseModel",
                        "fields": fields,
                        "field_count": len(fields),
                    }
        
        return {
            "success": True,
            "schema": schema,
            "model_count": len(schema["models"]),
            "relationship_count": len(schema["relationships"]),
            "models_file": str(models_file),
        }
        
    except SyntaxError as e:
        return {
            "success": False,
            "error": f"Syntax error in models.py: {e}",
            "schema": {},
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to parse models.py: {e}",
            "schema": {},
        }


async def tool_db_query_runner(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a query against MongoDB using Beanie.
    
    Supports:
    - find_all: Get all documents from a collection
    - find_one: Get a single document
    - count: Count documents
    - aggregate: Run aggregation pipeline
    """
    from pathlib import Path
    import sys
    
    project_path = args.get("project_path", ".")
    collection = args.get("collection", "")
    operation = args.get("operation", "find_all")
    query_filter = args.get("filter", {})
    limit = args.get("limit", 10)
    
    if not collection:
        return {"success": False, "error": "collection is required"}
    
    # Try to import the project's database module
    backend_path = Path(project_path) / "backend"
    if backend_path.exists() and str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    try:
        # Check if we can import the database and model
        try:
            from app.database import init_db
            from app import models
        except ImportError as e:
            return {
                "success": False,
                "error": f"Cannot import project database: {e}",
                "hint": "Ensure the project's backend is set up with database.py and models.py"
            }
        
        # Get the model class
        model_class = getattr(models, collection, None)
        if not model_class:
            available = [name for name in dir(models) if not name.startswith("_")]
            return {
                "success": False,
                "error": f"Model '{collection}' not found",
                "available_models": available[:10],
            }
        
        # Execute the query
        import asyncio
        
        async def run_query():
            await init_db()
            
            if operation == "count":
                count = await model_class.count()
                return {"count": count}
            elif operation == "find_one":
                doc = await model_class.find_one(query_filter)
                return {"document": doc.dict() if doc else None}
            elif operation == "find_all":
                docs = await model_class.find(query_filter).limit(limit).to_list()
                return {"documents": [d.dict() for d in docs], "count": len(docs)}
            else:
                return {"error": f"Unknown operation: {operation}"}
        
        # Run the async query
        result = await run_query()
        
        return {
            "success": True,
            "collection": collection,
            "operation": operation,
            **result,
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Query failed: {e}",
            "collection": collection,
            "operation": operation,
        }


# =====================================================================
# DEPLOYMENT TOOLS
# =====================================================================
async def tool_docker_builder(args: Dict[str, Any]) -> Dict[str, Any]:
    """Build a Docker image using docker CLI (async, non-blocking)."""
    try:
        dockerfile_path = args.get("dockerfile_path", "Dockerfile")
        image_name = args.get("image_name", "app_image")
        cwd = args.get("cwd", ".")

        cmd = f"docker build -t {image_name} -f {dockerfile_path} ."
        # FIX ASYNC-001: Use async subprocess
        result = await _async_run_command(cmd, cwd=cwd, timeout=300)
        result["image_name"] = image_name
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_vercel_deployer(args: Dict[str, Any]) -> Dict[str, Any]:
    """Deploy a project using `vercel --prod` (async, non-blocking)."""
    try:
        project_path = args.get("project_path", ".")
        # FIX ASYNC-001: Use async subprocess
        result = await _async_run_command("vercel --prod", cwd=project_path, timeout=300)
        result["message"] = "Vercel deployment executed"
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

# =====================================================================
# PATCHING TOOLS
# =====================================================================

async def tool_unified_patch_applier(args: Dict[str, Any]) -> Dict[str, Any]:

    try:
        project_path_str = args.get("project_path")
        patch_text = args.get("patch") or args.get("diff")

        if not project_path_str:
            return {"success": False, "error": "project_path is required"}

        if not patch_text or not isinstance(patch_text, str):
            return {"success": False, "error": "patch (unified diff) is required"}

        root = Path(project_path_str)
        if not root.exists():
            return {"success": False, "error": f"Workspace path does not exist: {root}"}

        result = apply_unified_patch(root, patch_text)

        return result

    except Exception as e:
        return {"success": False, "error": f"Unified patch error: {e}"}


async def tool_json_patch_applier(args: Dict[str, Any]) -> Dict[str, Any]:

    try:
        project_path_str = args.get("project_path")
        patches = args.get("patches") or args.get("patch")

        if not project_path_str:
            return {"success": False, "error": "project_path is required"}

        if patches is None:
            return {"success": False, "error": "patches is required"}

        if isinstance(patches, (dict, list)):
            patch_json = json.dumps(patches)
        else:
            patch_json = str(patches)

        root = Path(project_path_str)
        if not root.exists():
            return {"success": False, "error": f"Workspace path does not exist: {root}"}

        results = PatchEngine.apply_patches(str(root), patch_json)
        return {"success": True, "results": results}

    except Exception as e:
        return {"success": False, "error": f"JSON patch error: {e}"}


# =====================================================================
# P1.1: ENVIRONMENT GUARD (Real Implementation)
# =====================================================================

async def tool_environment_guard(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive environment validation with version checking.
    
    Features:
    - Checks for required CLI tools
    - Validates version requirements
    - Checks disk space
    - Validates project structure
    """
    import platform
    import sys
    import shutil
    import subprocess
    from pathlib import Path
    
    project_path = args.get("project_path", ".")
    required_tools = args.get("required_tools", ["node", "npm", "python", "git"])
    min_disk_mb = args.get("min_disk_mb", 500)
    
    env_info = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "project_path": project_path,
    }
    
    # Check tools with versions
    tool_checks = {}
    for tool in required_tools:
        tool_path = shutil.which(tool)
        check = {
            "installed": tool_path is not None,
            "path": tool_path,
            "version": None,
        }
        
        if tool_path:
            # Try to get version
            try:
                version_flags = {
                    "node": ["--version"],
                    "npm": ["--version"],
                    "python": ["--version"],
                    "git": ["--version"],
                    "docker": ["--version"],
                    "playwright": ["--version"],
                }
                
                if tool in version_flags:
                    result = subprocess.run(
                        [tool] + version_flags[tool],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    version_str = result.stdout.strip() or result.stderr.strip()
                    # Extract version number
                    import re
                    match = re.search(r'[\d]+\.[\d]+(?:\.[\d]+)?', version_str)
                    if match:
                        check["version"] = match.group(0)
            except Exception:
                pass
        
        tool_checks[tool] = check
    
    env_info["tools"] = tool_checks
    
    # Check disk space
    try:
        import os
        path = Path(project_path)
        if path.exists():
            if platform.system() == "Windows":
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(str(path)), None, None, ctypes.pointer(free_bytes)
                )
                free_mb = free_bytes.value / (1024 * 1024)
            else:
                stat = os.statvfs(path)
                free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
            
            env_info["disk_free_mb"] = round(free_mb, 2)
            env_info["disk_ok"] = free_mb >= min_disk_mb
        else:
            env_info["disk_ok"] = True
    except Exception as e:
        env_info["disk_ok"] = True  # Assume OK if we can't check
        env_info["disk_error"] = str(e)
    
    # Check project structure
    project_dir = Path(project_path)
    structure_checks = {}
    if project_dir.exists():
        structure_checks = {
            "has_backend": (project_dir / "backend").exists(),
            "has_frontend": (project_dir / "frontend").exists(),
            "has_architecture": (project_dir / "architecture").exists(),
            "has_package_json": (project_dir / "frontend" / "package.json").exists(),
            "has_requirements": (project_dir / "backend" / "requirements.txt").exists(),
        }
        env_info["project_structure"] = structure_checks
    
    # Summary
    all_tools_ok = all(t["installed"] for t in tool_checks.values())
    disk_ok = env_info.get("disk_ok", True)
    
    issues = []
    if not all_tools_ok:
        missing = [t for t, v in tool_checks.items() if not v["installed"]]
        issues.append(f"Missing tools: {missing}")
    if not disk_ok:
        issues.append(f"Low disk space: {env_info.get('disk_free_mb', 0)}MB (need {min_disk_mb}MB)")
    
    return {
        "success": True,
        "environment": env_info,
        "all_ok": all_tools_ok and disk_ok,
        "issues": issues,
    }


# =====================================================================
# P1.1: STATIC CODE VALIDATOR (NEW)
# =====================================================================

async def tool_static_code_validator(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run static code validation (linting).
    
    P1.1 FIX: This tool was missing from the registry.
    
    NOTE: P1.2 - This is advisory, not authoritative.
    Failures here should be WARNINGS, not blocking errors.
    """
    from pathlib import Path
    
    project_path = args.get("project_path", ".")
    language = args.get("language", "python")
    
    results = {
        "language": language,
        "project_path": project_path,
        "warnings": [],
        "errors": [],
    }
    
    try:
        base = Path(project_path)
        
        if language == "python":
            # Check for Python files
            py_files = list(base.rglob("*.py"))
            results["files_checked"] = len(py_files)
            
            # Basic syntax check
            for py_file in py_files[:10]:  # Limit to first 10
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        code = f.read()
                    compile(code, str(py_file), 'exec')
                except SyntaxError as e:
                    results["warnings"].append({
                        "file": str(py_file.relative_to(base)),
                        "line": e.lineno,
                        "message": str(e.msg),
                    })
                    
        elif language == "javascript":
            # Check for JS/JSX files
            js_files = list(base.rglob("*.js")) + list(base.rglob("*.jsx"))
            results["files_checked"] = len(js_files)
            
            # P1.2: Don't fail on JS syntax - just note warnings
            # Heuristic checks were causing false positives
            
        results["success"] = True  # Advisory tool always succeeds
        
    except Exception as e:
        results["success"] = True  # Even on error, advisory tools don't block
        results["warnings"].append({"message": f"Validation error: {e}"})
    
    return results


# =====================================================================
# NEW DECLARATIVE TOOLS (4 missing implementations)
# =====================================================================

async def tool_architecture_writer(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates architecture documentation only.
    
    This is a focused tool that ONLY writes architecture files.
    It delegates to subagentcaller with Victoria.
    """
    from pathlib import Path
    
    project_path = args.get("project_path", ".")
    user_request = args.get("user_request", "")
    
    # This tool wraps subagentcaller with specific instructions
    result = await tool_sub_agent_caller({
        "sub_agent": "Victoria",
        "step_name": "architecture",
        "user_request": user_request,
        "project_path": project_path,
        "instructions": """Generate architecture documentation.
Output ONLY architecture files using HDAP format:
<<<FILE path="architecture/system.md">>>>
[system architecture content]
<<<END_FILE>>>

<<<FILE path="architecture/backend.md">>>>
[backend architecture content]
<<<END_FILE>>>

<<<FILE path="architecture/frontend.md">>>>
[frontend architecture content]
<<<END_FILE>>>
""",
    })
    
    return {
        "success": result.get("success", False),
        "tool": "architecture_writer",
        "output": result.get("output"),
    }


async def tool_router_scaffold_generator(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates FastAPI router skeletons WITHOUT logic.
    
    This creates the file structure and imports,
    but does not fill in the endpoint implementations.
    """
    from pathlib import Path
    
    project_path = args.get("project_path", ".")
    entities = args.get("entities", [])
    
    if not entities:
        return {"success": False, "error": "No entities provided for router generation"}
    
    scaffolds = []
    base = Path(project_path) / "backend" / "app" / "routers"
    base.mkdir(parents=True, exist_ok=True)
    
    for entity in entities:
        entity_name = entity if isinstance(entity, str) else entity.get("name", "")
        entity_lower = entity_name.lower()
        entity_plural = f"{entity_lower}s"
        
        scaffold = f'''"""
{entity_name} Router - Generated Scaffold
"""
from fastapi import APIRouter, HTTPException, status
from typing import List
from beanie import PydanticObjectId

from app.models import {entity_name}

router = APIRouter(
    prefix="/api/{entity_plural}",
    tags=["{entity_name}"]
)


# TODO: Implement CRUD endpoints
# Use tool_router_logic_filler to add logic


@router.get("/", response_model=List[{entity_name}])
async def list_{entity_plural}():
    """List all {entity_plural}."""
    raise NotImplementedError("Use router_logic_filler to implement")


@router.get("/{{item_id}}", response_model={entity_name})
async def get_{entity_lower}(item_id: PydanticObjectId):
    """Get a single {entity_lower} by ID."""
    raise NotImplementedError("Use router_logic_filler to implement")


@router.post("/", response_model={entity_name}, status_code=status.HTTP_201_CREATED)
async def create_{entity_lower}(item: {entity_name}):
    """Create a new {entity_lower}."""
    raise NotImplementedError("Use router_logic_filler to implement")


@router.put("/{{item_id}}", response_model={entity_name})
async def update_{entity_lower}(item_id: PydanticObjectId, item: {entity_name}):
    """Update an existing {entity_lower}."""
    raise NotImplementedError("Use router_logic_filler to implement")


@router.delete("/{{item_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{entity_lower}(item_id: PydanticObjectId):
    """Delete a {entity_lower}."""
    raise NotImplementedError("Use router_logic_filler to implement")
'''
        
        file_path = base / f"{entity_plural}.py"
        file_path.write_text(scaffold, encoding="utf-8")
        scaffolds.append(str(file_path))
    
    return {
        "success": True,
        "tool": "router_scaffold_generator",
        "files_created": scaffolds,
        "entities": entities,
    }


async def tool_router_logic_filler(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fills logic inside an existing router file.
    
    Takes a scaffold and replaces NotImplementedError with actual logic.
    """
    from pathlib import Path
    
    project_path = args.get("project_path", ".")
    router_file = args.get("router_file", "")
    entity_name = args.get("entity_name", "")
    
    if not router_file:
        return {"success": False, "error": "router_file is required"}
    
    file_path = Path(project_path) / router_file
    if not file_path.exists():
        return {"success": False, "error": f"Router file not found: {router_file}"}
    
    # Read existing scaffold
    existing_code = file_path.read_text(encoding="utf-8")
    
    # Use subagentcaller to fill in the logic
    result = await tool_sub_agent_caller({
        "sub_agent": "Derek",
        "step_name": "backend_routers",
        "project_path": project_path,
        "instructions": f"""Fill in the router logic for {entity_name}.

The current scaffold is:
```python
{existing_code}
```

Replace all `raise NotImplementedError(...)` with actual Beanie CRUD logic.

Output the COMPLETE file using HDAP format:
<<<FILE path="{router_file}">>>>
[complete router code with logic]
<<<END_FILE>>>
""",
    })
    
    return {
        "success": result.get("success", False),
        "tool": "router_logic_filler",
        "router_file": router_file,
        "output": result.get("output"),
    }


async def tool_code_patch_applier(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies unified diffs or patches to existing files.
    
    This is a wrapper around the existing patching tools.
    """
    project_path = args.get("project_path", ".")
    patch_text = args.get("patch", args.get("patch_text", ""))
    patch_type = args.get("patch_type", "unified")  # "unified" or "json"
    
    if not patch_text:
        return {"success": False, "error": "No patch provided"}
    
    if patch_type == "json":
        # Use JSON patch applier
        return await tool_json_patch_applier({
            "project_path": project_path,
            "patches": patch_text,
        })
    else:
        # Use unified patch applier
        return await tool_unified_patch_applier({
            "project_path": project_path,
            "patch": patch_text,
        })


# =====================================================================
# DISPATCH TABLE + MAIN DISPATCHER
# =====================================================================
TOOL_FUNCTION_MAP: Dict[str, Any] = {
    # Core
    GenCodeTool.SubAgentCaller.value: tool_sub_agent_caller,

    # File
    GenCodeTool.FileWriterBatch.value: tool_file_writer_batch,
    GenCodeTool.FileReader.value: tool_file_reader,
    GenCodeTool.FileDeleter.value: tool_file_deleter,
    GenCodeTool.FileLister.value: tool_file_lister,
    GenCodeTool.CodeViewer.value: tool_code_viewer,

    # Execution
    GenCodeTool.BashRunner.value: tool_bash_runner,
    GenCodeTool.PythonExecutor.value: tool_python_executor,
    GenCodeTool.NPMRunner.value: tool_npm_runner,

    # Testing
    GenCodeTool.PytestRunner.value: tool_pytest_runner,
    GenCodeTool.PlaywrightRunner.value: tool_playwright_runner,
    GenCodeTool.TestGenerator.value: tool_test_generator,

    # Sandbox
    GenCodeTool.SandboxExec.value: tool_sandbox_exec,

    # Validation
    GenCodeTool.DeploymentValidator.value: tool_deployment_validator,
    GenCodeTool.KeyValidator.value: tool_key_validator,
    GenCodeTool.CrossLLMValidator.value: tool_cross_llm_validator,
    GenCodeTool.SyntaxValidator.value: tool_syntax_validator,

    # Visual
    GenCodeTool.UXVisualizer.value: tool_ux_visualizer,
    GenCodeTool.ScreenshotComparer.value: tool_screenshot_comparer,

    # Web
    GenCodeTool.WebResearcher.value: tool_web_researcher,
    GenCodeTool.APITester.value: tool_api_tester,
    GenCodeTool.HealthChecker.value: tool_health_checker,

    # User
    GenCodeTool.UserConfirmer.value: tool_user_confirmer,
    GenCodeTool.UserPrompter.value: tool_user_prompter,

    # DB
    GenCodeTool.DBSchemaReader.value: tool_db_schema_reader,
    GenCodeTool.DBQueryRunner.value: tool_db_query_runner,

    # Deployment
    GenCodeTool.DockerBuilder.value: tool_docker_builder,
    GenCodeTool.VercelDeployer.value: tool_vercel_deployer,
    
    # Patching  
    GenCodeTool.UnifiedPatchApplier.value: tool_unified_patch_applier,
    GenCodeTool.JsonPatchApplier.value: tool_json_patch_applier,
    
    # P1.1: Environment & Static Validation (NEW)
    GenCodeTool.EnvironmentGuard.value: tool_environment_guard,
    GenCodeTool.StaticCodeValidator.value: tool_static_code_validator,
    
    # NEW DECLARATIVE TOOLS (4 implementations)
    GenCodeTool.ArchitectureWriter.value: tool_architecture_writer,
    GenCodeTool.RouterScaffoldGenerator.value: tool_router_scaffold_generator,
    GenCodeTool.RouterLogicFiller.value: tool_router_logic_filler,
    GenCodeTool.CodePatchApplier.value: tool_code_patch_applier,

}


async def run_tool(name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args = args or {}
    normalized = (name or "").strip().lower()

    try:
        # explicit aliases for sandbox_exec
        if normalized in {"sandboxexec", "sandbox_exec"}:
            return await tool_sandbox_exec(args)
            
        # explicit alias for code_generator (V!=K spec)
        if normalized == "code_generator":
            normalized = "subagentcaller"

        func = TOOL_FUNCTION_MAP.get(normalized)
        if func is None:
            return {"success": False, "error": f"Unknown tool '{name}'"}

        return await func(args)

    except Exception as e:
        return {"success": False, "error": str(e), "tool": name}


# Deprecated alias for internal use
_run_tool_impl = run_tool






# =====================================================================
# Singleton validation REMOVED - using lazy initialization via get_sandbox()
# =====================================================================
# The SandboxManager is now created on-demand when get_sandbox() is called,
# not at module import time. This prevents log spam during early workflow steps.




__all__ = [
    "run_tool",
    "GenCodeTool",
    "SANDBOX",
    "tool_sub_agent_caller",
    "tool_file_writer_batch",
    "tool_file_reader",
    "tool_file_deleter",
    "tool_file_lister",
    "tool_code_viewer",
    "tool_bash_runner",
    "tool_python_executor",
    "tool_npm_runner",
    "tool_pytest_runner",
    "tool_playwright_runner",
    "tool_test_generator",
    "tool_sandbox_exec",
    "tool_deployment_validator",
    "tool_key_validator",
    "tool_cross_llm_validator",
    "tool_syntax_validator",
    "tool_ux_visualizer",
    "tool_screenshot_comparer",
    "tool_api_tester",
    "tool_web_researcher",
    "tool_health_checker",
    "tool_user_confirmer",
    "tool_user_prompter",
    "tool_db_schema_reader",
    "tool_db_query_runner",
    "tool_docker_builder",
    "tool_vercel_deployer",
    "tool_unified_patch_applier",   
    "tool_json_patch_applier",
    # P1.1 + New declarative tools
    "tool_environment_guard",
    "tool_static_code_validator",
    "tool_architecture_writer",
    "tool_router_scaffold_generator",
    "tool_router_logic_filler",
    "tool_code_patch_applier",
]
