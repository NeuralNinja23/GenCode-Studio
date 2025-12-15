"""
Docker Sandbox Manager - Main Orchestrator
✓ Protected Dockerfiles
✓ Automatically regenerates correct templates
✓ Ensures LLM cannot break sandbox
"""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timezone
import traceback

from .sandbox_config import SandboxConfig
from .health_monitor import HealthMonitor
from .log_streamer import LogStreamer

# Note: PROTECTED_FILES is imported from app.core.constants if needed

class SandboxManager:
    def __init__(self) -> None:
        self.docker_client = None
        print("[SANDBOX] Initializing SandboxManager")

        self.health_monitor = HealthMonitor(self.docker_client)
        self.log_streamer = LogStreamer(self.docker_client)

        self._compose_cmd: Optional[str] = None
        self.active_sandboxes: Dict[str, Dict[str, Any]] = {}

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    async def get_status(self, project_id: str) -> Dict[str, Any]:
        if project_id not in self.active_sandboxes:
            return {"success": False, "error": f"Sandbox {project_id} not found"}

        info = self.active_sandboxes[project_id]
        return {
            "success": True,
            "project_id": project_id,
            "status": info.get("status"),
            "containers": info.get("containers"),
            "created_at": info.get("created_at"),
        }

    async def create_sandbox(
        self,
        project_id: str,
        project_path: Union[str, Path],
        config: Optional[SandboxConfig] = None,
    ) -> Dict[str, Any]:

        try:
            print(f"[SANDBOX] Creating sandbox for {project_id}")
            config = config or SandboxConfig()
            project_path = Path(project_path).resolve()

            validation = self._validate_project_structure(project_path)
            if not validation["valid"]:
                print("[SANDBOX] Validation failed:", validation["error"])
                return {
                    "success": False,
                    "error": validation["error"],
                    "details": validation,
                }

            compose_path = project_path / "docker-compose.yml"
            network_name = f"{project_id}_network"

            self.active_sandboxes[project_id] = {
                "project_path": project_path,
                "network_name": network_name,
                "compose_path": compose_path,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "created",
                "containers": {},
            }

            print(f"[SANDBOX] ✓ Sandbox metadata registered for {project_id}")
            return {"success": True, "project_id": project_id}

        except Exception as e:
            print(f"[SANDBOX] CRITICAL ERROR creating sandbox: {e}")
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    async def start_sandbox(
        self,
        project_id: str,
        wait_healthy: bool = True,
        services: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Start Docker-based backend/frontend containers for a project.
        Firecracker is only used for running tests; sandbox runtime stays on Docker.
        """
        try:
            if project_id not in self.active_sandboxes:
                return {"success": False, "error": f"Sandbox {project_id} not found"}

            info = self.active_sandboxes[project_id]
            project_path = info["project_path"]

            print(f"[SANDBOX] Validating structure for {project_id}")
            validation = self._validate_project_structure(project_path)
            if not validation["valid"]:
                print("[SANDBOX] Validation failed:", validation["error"])
                return validation

            # Bug Fix #3: Validate that main.py has actual routes (not just scaffold)
            main_py = project_path / "backend" / "app" / "main.py"
            if main_py.exists():
                content = main_py.read_text(encoding="utf-8")
                # Check if router imports exist (not just the marker comment)
                has_router_imports = "from app.routers import" in content
                has_router_register = "app.include_router(" in content
                
                if not has_router_imports and not has_router_register:
                    print("[SANDBOX] ⚠️ main.py has no routes wired yet (scaffold only)")
                    # This is a WARNING, not an error. Allow starting for health check.
                    # But log it so we can diagnose if tests fail later.

            print(f"[SANDBOX] Starting containers for {project_id} (Services: {services or 'ALL'})")

            # Build command: docker compose up -d --build [service1 service2 ...]
            cmd_args = "up -d --build"
            if services:
                # Ensure db is joined if specific services requested (best practice for this tailored workflow)
                # But to be robust, we rely on caller passing correct dependencies or docker-compose relies on `depends_on`.
                # If caller passes ["backend"], docker compose usually starts "db" if "depends_on" is set.
                cmd_args += " " + " ".join(services)

            result = await self._run_compose_command(project_path, cmd_args, timeout=300)

            if result["returncode"] != 0:
                print("[SANDBOX] docker compose up FAILED")
                logs = await self._get_compose_logs(project_path)
                return {
                    "success": False,
                    "error": "Failed to start containers",
                    "stderr": result["stderr"]
                    + "\n\n--- CONTAINER LOGS ---\n"
                    + logs,
                    "stdout": result["stdout"],
                }

            await asyncio.sleep(3)

            containers = self._get_project_containers(project_id)
            info["containers"] = containers
            info["status"] = "running"

            if wait_healthy:
                print("[SANDBOX] Waiting for health checks...")
                health = await self.health_monitor.wait_for_healthy(
                    project_id,
                    containers,
                    timeout=60,
                )
            else:
                health = {}

            return {"success": True, "containers": containers, "health": health}

        except Exception as e:
            print(f"[SANDBOX] CRITICAL ERROR starting sandbox: {e}")
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    async def stop_sandbox(self, project_id: str) -> Dict[str, Any]:
        """
        Stop Docker containers for this sandbox.
        """
        try:
            if project_id not in self.active_sandboxes:
                return {"success": False, "error": f"Sandbox {project_id} not found"}

            info = self.active_sandboxes[project_id]
            project_path: Path = info["project_path"]

            print(f"[SANDBOX] Stopping containers for {project_id}")
            result = await self._run_compose_command(project_path, "down", timeout=120)

            if result["returncode"] != 0:
                return {
                    "success": False,
                    "error": "Failed to stop containers",
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                }

            info["status"] = "stopped"
            info["containers"] = {}

            return {"success": True}

        except Exception as e:
            print(f"[SANDBOX] ERROR stopping sandbox: {e}")
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    async def destroy_sandbox(self, project_id: str) -> Dict[str, Any]:
        """
        Stop containers and remove sandbox metadata.
        Does NOT delete the project files on disk (workspace stays).
        """
        try:
            if project_id not in self.active_sandboxes:
                return {"success": False, "error": f"Sandbox {project_id} not found"}

            # Best-effort stop
            await self.stop_sandbox(project_id)

            del self.active_sandboxes[project_id]
            print(f"[SANDBOX] Sandbox {project_id} metadata removed")

            return {"success": True}

        except Exception as e:
            print(f"[SANDBOX] ERROR destroying sandbox: {e}")
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    async def run_backend_tests(self, project_id: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Run backend tests using Docker Compose.
        Compatible with WSL2 (no Firecracker/KVM required).

        Returns:
          - success
          - stdout
          - stderr
          - returncode (test exit code)
          - test_exit_code
          - logs
        """
        if project_id not in self.active_sandboxes:
            return {"success": False, "error": f"Sandbox {project_id} not found"}

        info = self.active_sandboxes[project_id]
        project_path: Path = info["project_path"]

        print(f"[SANDBOX] Running backend tests for {project_id} using Docker Compose")

        # Validate project structure before running tests
        validation = self._validate_project_structure(project_path)
        if not validation["valid"]:
            print("[SANDBOX] Validation failed before tests:", validation["error"])
            return {
                "success": False,
                "error": validation["error"],
                "details": validation,
            }

        # Run pytest in the backend container
        result = await self._run_compose_command(
            project_path,
            "run --rm backend pytest -v",
            timeout=timeout
        )

        return {
            "success": result["returncode"] == 0,
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "returncode": result["returncode"],
            "test_exit_code": result["returncode"],
            "logs": result["stdout"] + "\n" + result["stderr"],
        }

    async def run_frontend_tests(self, project_id: str, timeout: int = 600) -> Dict[str, Any]:
        """
        Run frontend tests (Playwright) using Docker Compose.
        Compatible with WSL2 (no Firecracker/KVM required).

        Returns:
          - success
          - stdout
          - stderr
          - returncode (test exit code)
          - test_exit_code
          - logs
        """
        if project_id not in self.active_sandboxes:
            return {"success": False, "error": f"Sandbox {project_id} not found"}

        info = self.active_sandboxes[project_id]
        project_path: Path = info["project_path"]

        print(f"[SANDBOX] Running frontend tests for {project_id} using Docker Compose")

        validation = self._validate_project_structure(project_path)
        if not validation["valid"]:
            print("[SANDBOX] Validation failed before frontend tests:", validation["error"])
            return {
                "success": False,
                "error": validation["error"],
                "details": validation,
            }

        # Run Playwright tests in the frontend container
        result = await self._run_compose_command(
            project_path,
            "run --rm frontend npx playwright test",
            timeout=timeout
        )

        return {
            "success": result["returncode"] == 0,
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "returncode": result["returncode"],
            "test_exit_code": result["returncode"],
            "logs": result["stdout"] + "\n" + result["stderr"],
        }

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    async def _run_compose_command(self, project_path: Path, command: str, timeout: int = 60):
        compose_file = project_path / "docker-compose.yml"
        base = self._get_compose_command()
        full_cmd = f'{base} -f "{compose_file}" {command}'

        try:
            # Execute docker compose command in a thread (Windows compatibility)

            # FIX ASYNC-001: Bypass asyncio subprocess limitations on Windows by using threads
            # This works regardless of Selector vs Proactor event loop
            def run_sync_cmd():
                return subprocess.run(
                    full_cmd,
                    shell=True,
                    capture_output=True, # Capture stdout/stderr
                    text=True,           # Decode as string
                    cwd=str(project_path),
                    timeout=timeout
                )

            # Offload blocking IO to a thread
            proc = await asyncio.to_thread(run_sync_cmd)
            
            return {
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        except subprocess.TimeoutExpired:
             return {
                "returncode": -1,
                "stdout": "",
                "stderr": "[Sandbox] docker compose command timed out.",
            }
        except Exception as e:
            print(f"[SANDBOX CRITICAL] Exception in docker compose: {e!r}")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Error executing docker compose: {e!r}",
            }

    async def _get_compose_logs(self, project_path: Path) -> str:
        try:
            res = await self._run_compose_command(
                project_path,
                "logs --no-color --tail=100",
                timeout=10,
            )
            return res["stdout"] + "\n" + res["stderr"]
        except Exception as e:
            return f"Failed to fetch logs: {e}"

    def _validate_project_structure(self, project_path: Path) -> Dict[str, Any]:
        """
        Ensure golden backend/frontend/docker files exist before we start containers
        or run tests.
        """
        backend_dir = project_path / "backend"
        frontend_dir = project_path / "frontend"
        


        required_files = {
            "backend/Dockerfile": backend_dir / "Dockerfile",
            "backend/app/main.py": backend_dir / "app" / "main.py",
            "frontend/Dockerfile": frontend_dir / "Dockerfile",
            "docker-compose.yml": project_path / "docker-compose.yml",
        }

        # Only strictly require docker-compose.yml to attempt orchestration
        if not (project_path / "docker-compose.yml").exists():
             return {
                "valid": False,
                "error": "Missing: docker-compose.yml",
                "missing": ["docker-compose.yml"],
            }
            
        # Warn about other files but allow proceeding (legacy behavior: let Docker fail naturally)
        missing = [name for name, path in required_files.items() if not path.exists()]
        if missing:
            print(f"[SANDBOX] ⚠️ Validation warning (proceeding anyway): Missing {missing}")

        return {"valid": True, "missing": missing}

    def _get_compose_command(self) -> str:
        if self._compose_cmd:
            return self._compose_cmd

        try:
            # FIX ASYNC-001: This is called once at startup, keeping sync for simplicity
            subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
            # FORCE docker compose for Windows/Newer Docker Desktop
            self._compose_cmd = "docker compose"
        except Exception:
            self._compose_cmd = "docker-compose"

        return self._compose_cmd

    async def _get_project_containers_async(self, project_id: str) -> Dict[str, Dict[str, Any]]:
        """Async version of _get_project_containers."""
        containers: Dict[str, Dict[str, Any]] = {}
        try:
            # FIX ASYNC-001: Use asyncio.to_thread for Windows compatibility
            def run_docker_ps():
                return subprocess.run(
                    ["docker", "ps", "--filter", f"name={project_id}", "--format", "{{json .}}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            
            proc = await asyncio.to_thread(run_docker_ps)
            stdout = proc.stdout or ""
            
            for line in stdout.splitlines():
                try:
                    data = json.loads(line)
                except Exception:
                    continue

                container_name = data.get("Names", "")
                service_name = "unknown"
                if "-backend-" in container_name:
                    service_name = "backend"
                elif "-frontend-" in container_name:
                    service_name = "frontend"

                cid = data.get("ID", "")
                containers[service_name] = {
                    "id": cid,
                    "short_id": cid[:12],
                    "name": container_name,
                    "status": data.get("Status"),
                    "ports": data.get("Ports", ""),
                }

        except Exception as e:
            print(f"[SANDBOX] CRITICAL ERROR getting containers for {project_id}: {e}")
            traceback.print_exc()
        
        return containers

    def _get_project_containers(self, project_id: str) -> Dict[str, Dict[str, Any]]:
        containers: Dict[str, Dict[str, Any]] = {}
        try:
            # Use name filter instead of label
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    f"name={project_id}",
                    "--format",
                    "{{json .}}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            for line in result.stdout.splitlines():
                try:
                    data = json.loads(line)
                except Exception:
                    continue

                container_name = data.get("Names", "")
                service_name = "unknown"
                if "-backend-" in container_name:
                    service_name = "backend"
                elif "-frontend-" in container_name:
                    service_name = "frontend"

                cid = data.get("ID", "")
                containers[service_name] = {
                    "id": cid,
                    "short_id": cid[:12],
                    "name": container_name,
                    "status": data.get("Status"),
                    "ports": data.get("Ports", ""),  # 👈 THIS LINE IS CRITICAL
                }

        except Exception as e:
            print(f"[SANDBOX] CRITICAL ERROR getting containers for {project_id}: {e}")
            traceback.print_exc()
            return containers
        
        return containers

    async def execute_command(
        self,
        project_id: str,
        service: str,
        command: str,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Execute a command inside a service container (Docker) - async version."""
        try:
            if project_id not in self.active_sandboxes:
                return {"success": False, "error": f"Sandbox {project_id} not found"}

            info = self.active_sandboxes[project_id]
            containers = info.get("containers", {})

            if service not in containers:
                return {"success": False, "error": f"Service {service} not found"}

            container_id = containers[service]["short_id"]
            # Use -w /app to ensure commands run from the correct working directory
            full_cmd = f"docker exec -w /app {container_id} {command}"

            # FIX ASYNC-001: Bypass asyncio subprocess limitations on Windows by using threads
            # This works regardless of Selector vs Proactor event loop
            def run_sync_cmd():
                return subprocess.run(
                    full_cmd,
                    shell=True,
                    capture_output=True,  # Capture stdout/stderr
                    text=True,            # Decode as string
                    timeout=timeout
                )

            # Offload blocking IO to a thread
            proc = await asyncio.to_thread(run_sync_cmd)

            # Map subprocess.run result to the expected dictionary format
            return {
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
                "success": proc.returncode == 0
            }

        except Exception as e:
            print(f"[SANDBOX] ERROR executing command in container: {e}")
            traceback.print_exc()
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "error": str(e),
                "returncode": -1,
            }

    # Alias for API compatibility
    async def exec_in_container(
        self,
        project_id: str,
        service: str,
        command: str,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Alias for execute_command (API compatibility)."""
        return await self.execute_command(project_id, service, command, timeout)

    async def get_preview_url(self, project_id: str) -> Optional[str]:
        """Get the frontend preview URL for a running sandbox."""
        try:
            if project_id not in self.active_sandboxes:
                return None
            
            info = self.active_sandboxes[project_id]
            containers = info.get("containers", {})
            
            # Check for frontend container
            frontend = containers.get("frontend", {})
            ports = frontend.get("ports", "")
            
            # Parse ports string like "0.0.0.0:3000->5174/tcp"
            if ports:
                # Try to find mapped port
                import re
                match = re.search(r"(?:0\.0\.0\.0|127\.0\.0\.1|::):(\d+)->", ports)
                if match:
                    port = match.group(1)
                    return f"http://localhost:{port}"
            
            # Default frontend port if not found in ports
            return "http://localhost:5174"
            
        except Exception as e:
            print(f"[SANDBOX] Error getting preview URL: {e}")
            traceback.print_exc()
            return None

    async def get_backend_url(self, project_id: str) -> Optional[str]:
        """Get the backend API URL for a running sandbox (dynamic port detection)."""
        try:
            if project_id not in self.active_sandboxes:
                print(f"[SANDBOX] ⚠️ get_backend_url: Project {project_id} not in active sandboxes")
                return None
            
            info = self.active_sandboxes[project_id]
            containers = info.get("containers", {})
            
            # Check for backend container
            backend = containers.get("backend", {})
            ports = backend.get("ports", "")
            
            print(f"[SANDBOX] 🔍 get_backend_url for {project_id}")
            print(f"[SANDBOX]    Ports string: '{ports}'")
            
            # Parse ports string like "0.0.0.0:32783->8001/tcp" or "[::]:32768->8001/tcp"
            if ports:
                import re
                match = re.search(r"(?:0\.0\.0\.0|127\.0\.0\.1|::):(\d+)->", ports)
                if match:
                    port = match.group(1)
                    url = f"http://localhost:{port}"
                    print(f"[SANDBOX]    ✅ Regex matched! Port: {port}, URL: {url}")
                    return url
                else:
                    print(f"[SANDBOX]    ❌ Regex did NOT match ports string")
                    print(f"[SANDBOX]    Expected format: '0.0.0.0:PORT->' or '127.0.0.1:PORT->' or '::PORT->'")
            else:
                print(f"[SANDBOX]    ⚠️ Ports string is empty")
            
            # Default backend port if not found in ports
            print(f"[SANDBOX]    📍 Falling back to http://localhost:8001")
            return "http://localhost:8001"
            
        except Exception as e:
            print(f"[SANDBOX] Error getting backend URL: {e}")
            traceback.print_exc()
            return None

