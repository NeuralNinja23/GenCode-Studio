# app/handlers/preview.py
"""
Step 11: Launch preview with dynamic port allocation.

Workflow order: ... → Testing Frontend (10) → Preview Final (11) → COMPLETE
"""
import asyncio
import re
from pathlib import Path
from typing import Any, Dict, List

import aiohttp

from app.core.types import ChatMessage, StepResult
from app.core.constants import WorkflowStep
from app.handlers.base import broadcast_status
from app.core.logging import log
from app.orchestration.utils import broadcast_to_project


async def step_preview_final(
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
    Step 11: Refresh preview on RANDOM free ports for both frontend and backend.
    """
    await broadcast_status(
        manager,
        project_id,
        WorkflowStep.PREVIEW_FINAL,
        f"Turn {current_turn}/{max_turns}: Finalizing preview (Dynamic Ports)...",
        current_turn,
        max_turns,
    )

    log("PREVIEW", "Configuring sandbox for random port access...")

    preview_url = ""
    backend_url = "http://localhost:8001"  # Default fallback

    try:
        # 1) Inject Override File to expose both frontend and backend on random host ports
        override_file = project_path / "docker-compose.override.yml"
        override_content = """
services:
  frontend:
    ports:
      - "0:5174"
  backend:
    ports:
      - "0:8001"
"""
        override_file.write_text(override_content, encoding="utf-8")

        async with aiohttp.ClientSession() as session:
            base_url = "http://localhost:8001/api/sandbox"

            # 2) Stop existing
            try:
                async with session.post(f"{base_url}/{project_id}/stop") as resp:
                    pass
            except Exception as e:
                log("PREVIEW", f"Warning: Stop call failed (ignoring): {e}")
                pass
            
            # 3) Create (Restore state) - 404 is OK if project doesn't exist at path
            try:
                async with session.post(f"{base_url}/{project_id}/create") as resp:
                    if resp.status not in (200, 404):
                        log("PREVIEW", f"Create returned status {resp.status}")
            except Exception as e:
                log("PREVIEW", f"Create call failed (may be already created): {e}")

            # 4) Start (Docker picks the port now)
            async with session.post(
                f"{base_url}/{project_id}/start?wait_healthy=true",
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                data = await resp.json()
                
                # 5) Extract the assigned ports for both services
                detail = data.get("detail", {})
                if isinstance(detail, dict):
                    containers = detail.get("containers", {})
                else:
                    containers = data.get("containers", {})
                
                # Get frontend port
                frontend = containers.get("frontend", {})
                frontend_ports = frontend.get("ports", "")
                match = re.search(r":(\d+)->5174", frontend_ports)
                if match:
                    frontend_port = match.group(1)
                    preview_url = f"http://localhost:{frontend_port}"
                    log("PREVIEW", f"✅ Frontend port: {frontend_port}")
                
                # Get backend port
                backend = containers.get("backend", {})
                backend_ports = backend.get("ports", "")
                match = re.search(r":(\d+)->8001", backend_ports)
                if match:
                    backend_port = match.group(1)
                    backend_url = f"http://localhost:{backend_port}"
                    log("PREVIEW", f"✅ Backend port: {backend_port}")
                    
                    # IMPORTANT: Update the frontend with the correct backend URL
                    # This is a workaround for the browser not being able to access Docker internal hostnames
                    api_js_path = project_path / "frontend" / "src" / "lib" / "api.js"
                    if api_js_path.exists():
                        try:
                            content = api_js_path.read_text(encoding="utf-8")
                            # Replace the default localhost:8001 with the actual dynamic port
                            content = content.replace(
                                '"http://localhost:8001"',
                                f'"http://localhost:{backend_port}"'
                            )
                            api_js_path.write_text(content, encoding="utf-8")
                            log("PREVIEW", f"✅ Updated api.js with backend port {backend_port}")
                        except Exception as e:
                            log("PREVIEW", f"⚠️ Could not update api.js: {e}")
                else:
                    log("PREVIEW", f"⚠️ Could not detect backend port from: {backend_ports}")

            # Fallback if ports weren't detected
            if not preview_url:
                log("PREVIEW", "⚠️ Could not auto-detect frontend port, trying API...")
                try:
                    async with session.get(f"{base_url}/{project_id}/preview") as preview_resp:
                        if preview_resp.status == 200:
                            preview_data = await preview_resp.json()
                            preview_url = preview_data.get("preview_url") or preview_data.get("url") or ""
                            if preview_url:
                                log("PREVIEW", f"✅ Got preview URL from API: {preview_url}")
                except Exception as e:
                    log("PREVIEW", f"Warning: API preview fetch failed: {e}")
                    pass
                
                if not preview_url:
                    preview_url = "http://localhost:5174"

            # 6) Verify Frontend Reachability
            if preview_url:
                log("PREVIEW", f"Waiting for {preview_url}...")
                is_reachable = False
                for i in range(30):
                    try:
                        async with session.get(preview_url, timeout=aiohttp.ClientTimeout(total=1)) as check_resp:
                            if check_resp.status == 200:
                                is_reachable = True
                                break
                    except Exception:
                        pass # Retrying silently
                    await asyncio.sleep(1)

            await broadcast_to_project(
                manager,
                project_id,
                {
                    "type": "PREVIEW_URL_READY",
                    "url": preview_url,
                    "backend_url": backend_url,
                    "message": f"Preview ready on {preview_url} (API: {backend_url})",
                    "stage": "complete",
                    "health": data.get("detail", {}).get("health"),
                },
            )

    except Exception as e:
        log("PREVIEW", f"Final preview setup failed: {e}")

    return StepResult(
        nextstep=WorkflowStep.COMPLETE,
        turn=current_turn + 1,
    )
