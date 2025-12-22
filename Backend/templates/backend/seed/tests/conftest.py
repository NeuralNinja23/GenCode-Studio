import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db, close_db


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="function")
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
def client(async_client):
    """
    Sync wrapper for async_client to support standard pytest assertions.
    """
    return async_client

@pytest.fixture(scope="session", autouse=True)
def assert_api_routes_exist():
    """
    FAIL FAST: Verify API routes are registered before any tests run.
    This catches wiring issues immediately.
    
    Contract-driven: Checks for ANY /api/* routes (excluding /api/health, /api/openapi.json).
    No longer assumes specific entities like /api/tasks.
    """
    routes = {route.path for route in app.routes}
    
    # Find all API routes (exclude utility endpoints)
    api_routes = {
        r for r in routes 
        if r.startswith("/api/") 
        and r not in {"/api/health", "/api/openapi.json", "/api/docs", "/api/redoc"}
    }
    
    assert api_routes, (
        f"CRITICAL: No API routes registered in main.py. "
        f"Found routes: {sorted(routes)}"
    )


@pytest.fixture(scope="function", autouse=True)
async def db_connection():
    await init_db()
    yield
    await close_db()

