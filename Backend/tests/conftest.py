import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db import connect_db, disconnect_db, is_connected


@pytest_asyncio.fixture(scope="session")
async def db_connection():
    """
    Database connection fixture for GenCode Studio's own tests.
    Connects to MongoDB at session start, disconnects at end.
    """
    await connect_db()
    yield is_connected()
    await disconnect_db()


# FIX TEST-001: Align scope with db_connection to avoid potential state issues
@pytest_asyncio.fixture(scope="session")
async def async_client(db_connection):
    """
    Async HTTP client for testing FastAPI endpoints.
    Depends on db_connection to ensure database is ready.
    Session-scoped to match db_connection fixture.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client
