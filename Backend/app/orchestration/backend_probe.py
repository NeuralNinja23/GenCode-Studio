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
        """Get base URL, dynamically detecting port for Docker mode."""
        if self._base_url:
            return self._base_url
        
        # For Docker mode, try to get dynamic port from SandboxManager
        if self.mode == ProbeMode.DOCKER and self.project_id:
            try:
                from app.tools.implementations import SANDBOX
                url = await SANDBOX.get_backend_url(self.project_id)
                if url:
                    self._base_url = url
                    return url
            except Exception:
                pass
        
        # Fallback to default port
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
        
        base_url = await self._get_base_url()
        url = f"{base_url}{path}"
        
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
                
                return response.status_code == expected_status
        except Exception:
            return False
    
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
