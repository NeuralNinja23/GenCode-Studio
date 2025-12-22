# app/orchestration/backend_probe.py
"""
BackendProbe: Environment-agnostic HTTP testing for backend services.

Supports both:
- ASGI mode: Import app and use ASGITransport (local dev, tests)
- Sandbox mode: HTTP requests to running Docker service

This abstracts away "how do we test the backend" so healing/validation
code doesn't need to know about Docker, ASGI, or environment details.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Tuple
from pathlib import Path


class ProbeMode(Enum):
    """Backend probe execution mode."""
    ASGI = "asgi"           # Import app, use ASGITransport
    DOCKER = "docker"       # HTTP to localhost:8000
    SANDBOX = "sandbox"     # HTTP to backend:8000 (inside Docker network)


class BackendProbe(ABC):
    """Abstract backend probe interface."""
    
    @abstractmethod
    async def check_route(
        self, 
        method: str, 
        path: str, 
        expected_status: int,
        timeout: float = 5.0
    ) -> bool:
        """
        Test if a route returns the expected status code.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Route path (e.g., /api/health)
            expected_status: Expected HTTP status code
            timeout: Request timeout in seconds
        
        Returns:
            True if route returns expected status, False otherwise
        """
        pass
    
    @abstractmethod
    async def is_healthy(self, timeout: float = 5.0) -> bool:
        """Check if backend is healthy via /api/health."""
        pass
    
    @classmethod
    def from_env(cls, mode: ProbeMode, **kwargs) -> 'BackendProbe':
        """Factory method to create probe based on environment."""
        if mode == ProbeMode.ASGI:
            return ASGIBackendProbe(**kwargs)
        elif mode in (ProbeMode.DOCKER, ProbeMode.SANDBOX):
            return HTTPBackendProbe(mode=mode, **kwargs)
        else:
            raise ValueError(f"Unknown probe mode: {mode}")


class HTTPBackendProbe(BackendProbe):
    """HTTP-based backend probe for Docker/Sandbox environments."""
    
    def __init__(self, mode: ProbeMode, project_id: Optional[str] = None):
        """
        Initialize HTTP probe.
        
        Args:
            mode: ProbeMode.DOCKER or ProbeMode.SANDBOX
            project_id: Project ID for dynamic port detection
        """
        self.mode = mode
        self.project_id = project_id
        self._base_url: Optional[str] = None
        
        # For SANDBOX mode, we use fixed internal Docker network URL
        if mode == ProbeMode.SANDBOX:
            self._base_url = "http://backend:8001"
    
    async def _get_base_url(self) -> str:
        """Get the backend base URL dynamically (port detection for Docker)."""
        if self._base_url:
            return self._base_url
        
        from app.core.logging import log
        
        # Try to get backend URL from sandbox manager
        try:
            from app.tools.implementations import get_sandbox
            
            if self.project_id:
                backend_url = await get_sandbox().get_backend_url(self.project_id)
                if backend_url:
                    log("PROBE", f"📍 Detected backend URL: {backend_url}")
                    self._base_url = backend_url
                    return self._base_url
                else:
                    log("PROBE", f"⚠️ get_backend_url returned None for {self.project_id}")
        except Exception as e:
            log("PROBE", f"⚠️ Failed to get backend URL: {e}")
        
        # Fallback to default port
        log("PROBE", f"📍 Falling back to default: http://localhost:8001")
        self._base_url = "http://localhost:8001"
        return self._base_url
    
    async def check_route_detailed(
        self, 
        method: str, 
        path: str, 
        expected_status: int,
        timeout: float = 5.0
    ) -> Tuple[bool, int, str]:
        """Test route via HTTP request and return detailed status."""
        import httpx
        from app.core.logging import log
        
        base_url = await self._get_base_url()
        url = f"{base_url}{path}"
        
        log("PROBE", f"Testing {method} {url} (expecting {expected_status})")
        
        try:
            # follow_redirects=True handles 307 from trailing slash differences
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                if method.upper() == "GET":
                    response = await client.get(url)
                elif method.upper() == "POST":
                    response = await client.post(url, json={})
                elif method.upper() == "PUT":
                    response = await client.put(url, json={})
                elif method.upper() == "DELETE":
                    response = await client.delete(url)
                else:
                    return False, 0, f"Unsupported HTTP method: {method}"
                
                status = response.status_code
                passed = False
                msg = ""
                
                # Check status
                if status == expected_status:
                    log("PROBE", f"  ✅ Got {status} as expected")
                    passed = True
                elif status == 422 and method.upper() in ("POST", "PUT"):
                    log("PROBE", f"  ✅ Got 422 (route exists, validation failed with empty payload)")
                    passed = True
                else:
                    log("PROBE", f"  ❌ Got {status}, expected {expected_status}")
                    log("PROBE", f"     Response: {response.text[:200]}")
                    msg = f"Got {status}, expected {expected_status}"
                    
                return passed, status, msg
                    
        except httpx.ConnectError as e:
            log("PROBE", f"  ❌ Connection failed: {e}")
            log("PROBE", f"     URL: {url}")
            return False, 0, f"Connection failed: {e}"
        except httpx.TimeoutException as e:
            log("PROBE", f"  ❌ Request timeout: {e}")
            return False, 0, f"Request timeout: {e}"
        except Exception as e:
            log("PROBE", f"  ❌ Unknown error: {type(e).__name__}: {e}")
            return False, 0, f"{type(e).__name__}: {e}"

    async def check_route(
        self, 
        method: str, 
        path: str, 
        expected_status: int,
        timeout: float = 5.0
    ) -> bool:
        """Wrapper for backward compatibility."""
        passed, _, _ = await self.check_route_detailed(method, path, expected_status, timeout)
        return passed
    
    async def is_healthy(self, timeout: float = 5.0) -> bool:
        """Check health endpoint."""
        return await self.check_route("GET", "/api/health", 200, timeout)


class ASGIBackendProbe(BackendProbe):
    """ASGI-based backend probe using ASGITransport (like conftest.py)."""
    
    def __init__(self, project_path: Path):
        """
        Initialize ASGI probe.
        
        Args:
            project_path: Path to project workspace
        """
        self.project_path = project_path
        self._app = None
    
    def _get_app(self):
        """Lazy-load FastAPI app."""
        if self._app is None:
            import sys
            backend_path = str(self.project_path / "backend")
            if backend_path not in sys.path:
                sys.path.insert(0, backend_path)
            
            from app.main import app
            self._app = app
        return self._app
    
    async def check_route(
        self, 
        method: str, 
        path: str, 
        expected_status: int,
        timeout: float = 5.0
    ) -> bool:
        """Test route via ASGI transport."""
        import httpx
        from httpx import ASGITransport
        
        try:
            app = self._get_app()
            transport = ASGITransport(app=app)
            
            async with httpx.AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
                if method.upper() == "GET":
                    response = await client.get(path)
                elif method.upper() == "POST":
                    response = await client.post(path, json={})
                elif method.upper() == "PUT":
                    response = await client.put(path, json={})
                elif method.upper() == "DELETE":
                    response = await client.delete(path)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                return response.status_code == expected_status
        except Exception:
            return False
    
    async def is_healthy(self, timeout: float = 5.0) -> bool:
        """Check health endpoint."""
        return await self.check_route("GET", "/api/health", 200, timeout)
