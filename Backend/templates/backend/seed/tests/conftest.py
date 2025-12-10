import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import connect_to_mongo as connect_db
# Disconnect is minimal in new session.py, we can just pass or add a helper if needed.
# For now, let's just mock disconnect or add it to session.py
async def disconnect_db(): pass

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

