"""
Health Monitor
Checks and monitors container health status using docker CLI (no docker SDK).
"""

import asyncio
import json
import subprocess
import time
from typing import Dict, Any, Optional


class HealthMonitor:
    """Monitors health of sandbox containers via `docker inspect`."""

    def __init__(self, docker_client: Optional[Any] = None):
        # docker_client kept only for backwards compatibility – not used.
        self.docker_client = docker_client

    async def wait_for_healthy(
        self,
        project_id: str,
        containers: Dict[str, Dict[str, Any]],
        timeout: int = 60,
    ) -> Dict[str, bool]:
        """
        Wait for all containers to become healthy, based on Docker's healthcheck.
        Returns: { service_name: bool }
        """
        start_time = time.monotonic()
        health_status: Dict[str, bool] = {service: False for service in containers.keys()}

        while time.monotonic() - start_time < timeout:
            for service_name, container_info in containers.items():
                if health_status[service_name]:
                    continue  # already healthy

                container_id = container_info.get("id")
                if not container_id:
                    continue
                
                # Pass ports for HTTP health check (Invariant C)
                ports = container_info.get("ports", "")
                is_healthy = await self._check_container_health(container_id, service_name, ports)
                health_status[service_name] = is_healthy

            if all(health_status.values()):
                print(f"[HEALTH] ✅ All services healthy for {project_id}")
                return health_status

            await asyncio.sleep(2)

            # Continue loop until timeout

        # Timeout reached
        unhealthy = [s for s, h in health_status.items() if not h]
        print(f"[HEALTH] ⚠️ Timeout reached. Unhealthy services: {unhealthy}")
        return health_status

    async def _check_container_health(self, container_id: str, service_name: str, ports: str = "") -> bool:
        """
        Check if a specific container is healthy.
        
        INVARIANT C: "Healthy" Means HTTP-Responsive (2025-12-17)
        A service is not healthy until it responds correctly.
        
        For backend services: Perform actual HTTP health check to /api/health
        For other services: Fall back to Docker state check
        """
        try:
            state = self._inspect_container_state(container_id)
            if not state:
                return False

            # First check Docker's built-in healthcheck if present
            health = state.get("Health") or {}
            status = health.get("Status")
            if status == "healthy":
                return True
            
            # Container must at least be running
            if state.get("Status") != "running":
                return False
            
            # ═══════════════════════════════════════════════════════════
            # INVARIANT C: For backend service, verify HTTP responsiveness
            # A "running" container means nothing if the app inside is crashed
            # ═══════════════════════════════════════════════════════════
            if service_name == "backend" and ports:
                http_healthy = await self._check_http_health(ports)
                if not http_healthy:
                    print(f"[HEALTH] ⚠️ Backend container running but HTTP not responsive")
                    return False
                print(f"[HEALTH] ✅ Backend HTTP health check passed")
                return True
            
            # For non-backend services, running is good enough
            return True

        except Exception as e:
            print(f"[HEALTH] ⚠️ Error checking {service_name} ({container_id}): {e}")
            return False
    
    async def _check_http_health(self, ports: str, retries: int = 5, delay: float = 2.0) -> bool:
        """
        Perform actual HTTP health check to the backend /api/health endpoint.
        
        Args:
            ports: Docker ports string like "0.0.0.0:32783->8001/tcp"
            retries: Number of retry attempts
            delay: Seconds to wait between retries
        
        Returns:
            True if HTTP health check passes, False otherwise
        """
        import re
        import httpx
        
        # Extract port from Docker ports string
        match = re.search(r"(?:0\.0\.0\.0|127\.0\.0\.1|::):(\d+)->", ports)
        if not match:
            print(f"[HEALTH] ⚠️ Could not parse port from: {ports}")
            return False
        
        port = match.group(1)
        health_url = f"http://localhost:{port}/api/health"
        
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    response = await client.get(health_url)
                    if response.status_code == 200:
                        return True
                    print(f"[HEALTH] Attempt {attempt+1}/{retries}: Got {response.status_code} from {health_url}")
            except httpx.ConnectError:
                print(f"[HEALTH] Attempt {attempt+1}/{retries}: Connection refused to {health_url}")
            except httpx.TimeoutException:
                print(f"[HEALTH] Attempt {attempt+1}/{retries}: Timeout connecting to {health_url}")
            except Exception as e:
                print(f"[HEALTH] Attempt {attempt+1}/{retries}: Error: {e}")
            
            if attempt < retries - 1:
                await asyncio.sleep(delay)
        
        return False

    def _inspect_container_state(self, container_id: str) -> Optional[Dict[str, Any]]:
        """
        Run `docker inspect` and return the .State dict, or None on failure.
        """
        try:
            result = subprocess.run(
                ["docker", "inspect", container_id],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                print(f"[HEALTH] docker inspect failed for {container_id}: {result.stderr.strip()}")
                return None

            info = json.loads(result.stdout)
            if not info:
                return None

            state = info[0].get("State", {})
            return state
        except Exception as e:
            print(f"[HEALTH] Exception inspecting {container_id}: {e}")
            return None

    async def get_detailed_health(
        self,
        project_id: str,
        containers: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Get detailed health information for all containers.
        Uses docker CLI only.
        
        INVARIANT C: For backend, includes HTTP responsiveness status.
        """
        details: Dict[str, Any] = {}
        for service_name, container_info in containers.items():
            cid = container_info.get("id")
            if not cid:
                details[service_name] = {"error": "no container id"}
                continue

            try:
                state = self._inspect_container_state(cid) or {}
                ports = container_info.get("ports", "")
                
                # Base info from Docker state
                service_details = {
                    "status": state.get("Status"),
                    "health": state.get("Health"),
                    "running": state.get("Status") == "running",
                    "exit_code": state.get("ExitCode"),
                    "started_at": state.get("StartedAt"),
                }
                
                # INVARIANT C: For backend, add HTTP responsiveness check
                if service_name == "backend" and ports and state.get("Status") == "running":
                    http_healthy = await self._check_http_health(ports, retries=2, delay=1.0)
                    service_details["http_responsive"] = http_healthy
                
                details[service_name] = service_details
            except Exception as e:
                details[service_name] = {"error": str(e), "running": False}

        return details
