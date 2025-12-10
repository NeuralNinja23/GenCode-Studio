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

                is_healthy = await self._check_container_health(container_id, service_name)
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

    async def _check_container_health(self, container_id: str, service_name: str) -> bool:
        """
        Check if a specific container is healthy using `docker inspect`.
        We look at .State.Health.Status if present, otherwise fall back to .State.Status == "running".
        """
        try:
            state = self._inspect_container_state(container_id)
            if not state:
                return False

            health = state.get("Health") or {}
            status = health.get("Status")
            if status == "healthy":
                return True

            # If no healthcheck defined, consider "running" as good enough
            if state.get("Status") == "running":
                return True

            return False

        except Exception as e:
            print(f"[HEALTH] ⚠️ Error checking {service_name} ({container_id}): {e}")
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
        """
        details: Dict[str, Any] = {}
        for service_name, container_info in containers.items():
            cid = container_info.get("id")
            if not cid:
                details[service_name] = {"error": "no container id"}
                continue

            try:
                state = self._inspect_container_state(cid) or {}
                details[service_name] = {
                    "status": state.get("Status"),
                    "health": state.get("Health"),
                    "running": state.get("Status") == "running",
                    "exit_code": state.get("ExitCode"),
                    "started_at": state.get("StartedAt"),
                }
            except Exception as e:
                details[service_name] = {"error": str(e), "running": False}

        return details
