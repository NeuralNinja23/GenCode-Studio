import pytest

@pytest.mark.asyncio
async def test_healthz(async_client):
    response = await async_client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True

@pytest.mark.asyncio
async def test_api_health(async_client):
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
