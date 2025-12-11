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
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiohttp

# Internal imports
from app.core.types import GeneratedFile  # noqa: F401 (kept for type compatibility)

# Sandbox system (Python-native, no HTTP)
from app.sandbox import SandboxManager, SandboxConfig  # type: ignore[import]
from app.config import WORKSPACES_DIR
from app.lib.patch_writer import apply_patch as apply_unified_patch
from app.lib.patch_engine import PatchEngine
# =====================================================================
# Global Sandbox Singleton
# =====================================================================
SANDBOX: SandboxManager = SandboxManager()


# =====================================================================
# Logging helper (single definition!)
# =====================================================================
from app.core.logging import log


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

        if not sub_agent or not instructions:
            raise ValueError("tool_sub_agent_caller requires 'sub_agent' and 'instructions'")

        result = await marcus_call_sub_agent(
            agent_name=sub_agent,
            user_request=instructions,
            project_path=project_path,
            project_id=project_id,  # Pass for real-time thinking
            step_name=step_name,  # Optimization parameter
            archetype=archetype,  # Optimization parameter
            vibe=vibe,  # Optimization parameter
            files=files,  # Relevant files (if provided)
            contracts=contracts,  # API contracts summary
            is_retry=is_retry,  # Retry flag for differential context
            errors=errors,  # Errors from previous attempt
        )

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
                }

        # 2) Try issues[0].raw
        issues = result.get("issues") or []
        if issues:
            raw = issues[0].get("raw")
            if raw:
                try:
                    parsed = normalize_llm_output(raw)
                    normalized = normalize_files_schema(parsed)
                    if normalized is not None:
                        return {
                            "success": True,
                            "output": normalized,
                            "agent": sub_agent,
                            "source": "salvaged_from_issues",
                        }
                except Exception:
                    pass

        # 3) Try raw_generation
        raw_generation = result.get("raw_generation")
        parsed = None
        if isinstance(raw_generation, str):
            try:
                parsed = normalize_llm_output(raw_generation)
                normalized = normalize_files_schema(parsed)
                if normalized is not None:
                    return {
                        "success": True,
                        "output": normalized,
                        "agent": sub_agent,
                        "source": "normalized_raw_generation",
                    }
            except Exception:
                parsed = None

        # Fallback: just return whatever we have
        return {
            "success": result.get("passed", False),
            "output": parsed if parsed is not None else raw_generation,
            "full_result": result,
            "agent": sub_agent,
            "source": "fallback",
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
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
    - project_path: str (optional override; otherwise deduced from WORKSPACES_DIR / project_id)
    - wait_healthy: bool (optional, default: True)
    - max_health_retries: int (optional, default: 30)
    - force_rebuild: bool (optional, default: False) - if True, stop and restart sandbox to pick up code changes
    """
    
    try:
        project_id = args.get("project_id")
        service = args.get("service", "backend")
        command = args.get("command")
        # We accept wait_healthy but start_sandbox handles the actual waiting
        wait_healthy = bool(args.get("wait_healthy", True))
        force_rebuild = bool(args.get("force_rebuild", False))
        
        if not project_id:
            return {"success": False, "error": "Missing project_id"}
        if not command:
            return {"success": False, "error": "Missing command"}
        
        # -----------------------------------------------------------
        # Resolve project_path (either explicit or from WORKSPACES_DIR)
        # -----------------------------------------------------------
        
        project_path_arg = args.get("project_path")
        if project_path_arg:
            project_path = Path(project_path_arg).resolve()
        else:
            project_path = (WORKSPACES_DIR / project_id).resolve()
        
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
        status = await SANDBOX.get_status(project_id)
        status_ok = bool(status.get("success"))
        current_state = (status.get("status") or "").lower() if status_ok else "unknown"
        
        # -----------------------------------------------------------
        # Force Rebuild: Stop and restart sandbox to pick up code changes
        # This is critical when routers are wired AFTER initial build
        # -----------------------------------------------------------
        if force_rebuild and status_ok and current_state == "running":
            log("SANDBOX_EXEC", f"🔄 Force rebuild requested for {project_id}, stopping sandbox...")
            await SANDBOX.stop_sandbox(project_id)
            # Mark as not running so we go through the full create+start flow
            current_state = "stopped"
            status_ok = True  # Sandbox still exists in metadata
        
        if not status_ok:
            # No sandbox tracked -> create + start
            log("SANDBOX_EXEC", f"Sandbox missing for {project_id}, creating...")
            
            create_res = await SANDBOX.create_sandbox(
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
            start_res = await SANDBOX.start_sandbox(
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
            
            start_res = await SANDBOX.start_sandbox(
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
        status = await SANDBOX.get_status(project_id)
        containers = status.get("containers", {})
        
        if service not in containers:
             log("SANDBOX_EXEC", f"Service '{service}' missing from running containers. Auto-starting...")
             start_res = await SANDBOX.start_sandbox(
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
        
        exec_res = await SANDBOX.execute_command(  # type: ignore[attr-defined]
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
    """Check presence of important API keys."""
    keys = ["OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"]
    results: Dict[str, Dict[str, Any]] = {}

    for key in keys:
        value = os.getenv(key, "")
        results[key] = {
            "present": bool(value),
            "length": len(value) if value else 0,
        }

    return {
        "success": True,
        "keys": results,
        "all_valid": all(info["present"] for info in results.values()),
    }


async def tool_cross_llm_validator(args: Dict[str, Any]) -> Dict[str, Any]:
    """Stub cross-LLM consistency validator (can be extended later)."""
    return {
        "success": True,
        "message": "Cross-LLM validator not implemented yet",
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
    """Basic stub for web research (no external API yet)."""
    query = args.get("query", "")
    return {
        "success": True,
        "query": query,
        "results": [],
        "note": "Web researcher not yet wired to a real search API",
    }


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
# USER INTERACTION TOOLS
# =====================================================================
async def tool_user_confirmer(args: Dict[str, Any]) -> Dict[str, Any]:
    """Ask user a question (auto-answers with first option in non-interactive mode)."""
    question = args.get("question", "Proceed?")
    options = args.get("options", ["Yes", "No"])

    return {
        "success": True,
        "question": question,
        "options": options,
        "answer": options[0] if options else None,
        "message": "User confirmation (auto) response",
    }


async def tool_user_prompter(args: Dict[str, Any]) -> Dict[str, Any]:
    """Prompt the user for input (returns default in non-interactive mode)."""
    prompt = args.get("prompt", "Enter value:")
    default = args.get("default", "")

    return {
        "success": True,
        "prompt": prompt,
        "value": default,
        "message": "User prompt (auto) response",
    }


# =====================================================================
# DATABASE TOOLS (stubs, safe to keep)
# =====================================================================
async def tool_db_schema_reader(args: Dict[str, Any]) -> Dict[str, Any]:
    db_url = args.get("db_url", "")
    return {
        "success": True,
        "schema": {},
        "message": "DB schema reader not implemented yet",
        "db_url": db_url,
    }


async def tool_db_query_runner(args: Dict[str, Any]) -> Dict[str, Any]:
    query = args.get("query", "")
    db_url = args.get("db_url", "")
    return {
        "success": True,
        "results": [],
        "message": "DB query runner not implemented yet",
        "query": query,
        "db_url": db_url,
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

}


async def run_tool(name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args = args or {}
    normalized = (name or "").strip().lower()

    try:
        # explicit aliases for sandbox_exec
        if normalized in {"sandboxexec", "sandbox_exec"}:
            return await tool_sandbox_exec(args)

        func = TOOL_FUNCTION_MAP.get(normalized)
        if func is None:
            return {"success": False, "error": f"Unknown tool '{name}'"}

        return await func(args)

    except Exception as e:
        return {"success": False, "error": str(e), "tool": name}



# =====================================================================
# Simple singleton validation (will raise early if broken)
# =====================================================================
def _validate_singleton() -> None:
    if SANDBOX is None:
        raise RuntimeError("SandboxManager singleton not initialized")


_validate_singleton()


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
]
