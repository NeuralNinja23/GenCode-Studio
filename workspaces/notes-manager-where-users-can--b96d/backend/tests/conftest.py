import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db, close_db


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="module")
async def async_client():
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    # follow_redirects=True handles 307 from trailing slash differences
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
        yield client

# Alias for compatibility - Derek's prompts use 'client'
@pytest.fixture(scope="module")
async def client(async_client):
    """Alias for async_client - use either name in tests."""
    return async_client

@pytest.fixture(scope="module", autouse=True)
async def db_connection():
    await init_db()
    yield
    await close_db()
