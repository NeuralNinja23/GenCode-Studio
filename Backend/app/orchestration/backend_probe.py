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
from typing import Optional
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
            from app.tools.implementations import SANDBOX
            
            if self.project_id:
                backend_url = await SANDBOX.get_backend_url(self.project_id)
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
    
    async def check_route(
        self, 
        method: str, 
        path: str, 
        expected_status: int,
        timeout: float = 5.0
    ) -> bool:
        """Test route via HTTP request."""
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
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Log actual response
                if response.status_code == expected_status:
                    log("PROBE", f"  ✅ Got {response.status_code} as expected")
                    return True
                else:
                    log("PROBE", f"  ❌ Got {response.status_code}, expected {expected_status}")
                    log("PROBE", f"     Response: {response.text[:200]}")
                    return False
                    
        except httpx.ConnectError as e:
            log("PROBE", f"  ❌ Connection failed: {e}")
            log("PROBE", f"     URL: {url}")
            return False
        except httpx.TimeoutException as e:
            log("PROBE", f"  ❌ Request timeout: {e}")
            return False
        except Exception as e:
            log("PROBE", f"  ❌ Unknown error: {type(e).__name__}: {e}")
            return False
    
    async def is_healthy(self, timeout: float = 5.0) -> bool:
        """Check health endpoint."""
        return await self.check_route("GET", "/api/health", 200, timeout)
    
    async def validate_all_contract_routes(self, contracts_path: Path) -> dict:
        """
        PHASE 4: Validate ALL routes from contracts.md.
        
        This replaces the old approach of only checking /api/health.
        Now we validate every route to ensure they're actually working.
        
        Args:
            contracts_path: Path to contracts.md file
        
        Returns:
            {
                "passed": ["GET /api/tasks", ...],
                "failed": ["POST /api/tasks -> 404", ...],
                "total": 10,
                "success_rate": 0.9
            }
        """
        from app.orchestration.contract_parser import ContractParser
        import httpx
        
        parser = ContractParser(contracts_path.parent)
        routes = parser.get_expected_routes()
        
        if not routes:
            return {
                "passed": [],
                "failed": [],
                "total": 0,
                "success_rate": 1.0  # No routes = 100% pass
            }
        
        passed = []
        failed = []
        base_url = await self._get_base_url()
        
        for route in routes:
            method = route.method
            path = route.path
            
            if not path:
                continue
            
            url = f"{base_url}{path}"
            
            try:
                async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                    # Make minimal request (empty body for POST/PUT)
                    if method.upper() == "GET":
                        response = await client.get(url)
                    elif method.upper() == "POST":
                        response = await client.post(url, json={})
                    elif method.upper() == "PUT":
                        # Use fake ID for PUT requests
                        response = await client.put(url, json={})
                    elif method.upper() == "DELETE":
                        response = await client.delete(url)
                    else:
                        failed.append(f"{method} {path} -> Unsupported method")
                        continue
                    
                    # Accept:
                    # - 2xx (success)
                    # - 422 (validation error is OK - route exists, just needs valid data)
                    # - 400 (bad request is OK - route exists)
                    # Reject:
                    # - 404 (route not found - this is what we're testing for!)
                    # - 500 (server error)
                    
                    if response.status_code == 404:
                        failed.append(f"{method} {path} -> 404 Not Found")
                    elif response.status_code >= 500:
                        failed.append(f"{method} {path} -> {response.status_code} Server Error")
                    else:
                        # 2xx, 3xx, 4xx (except 404) = route exists
                        passed.append(f"{method} {path}")
                        
            except httpx.TimeoutException:
                failed.append(f"{method} {path} -> Timeout")
            except Exception as e:
                failed.append(f"{method} {path} -> {type(e).__name__}")
        
        total = len(routes)
        success_rate = len(passed) / total if total > 0 else 0.0
        
        return {
            "passed": passed,
            "failed": failed,
            "total": total,
            "success_rate": success_rate
        }


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
