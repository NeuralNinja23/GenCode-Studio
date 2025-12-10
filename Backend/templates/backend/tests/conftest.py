import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db import connect_db, disconnect_db

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="module")
async def async_client():
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

# Alias for compatibility - Derek's prompts use 'client'
@pytest.fixture(scope="module")
async def client(async_client):
    """Alias for async_client - use either name in tests."""
    return async_client

@pytest.fixture(scope="module", autouse=True)
async def db_connection():
    await connect_db()
    yield
    await disconnect_db()

