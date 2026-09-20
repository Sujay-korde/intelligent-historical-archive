import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["name"] == "Intelligent Knowledge Archive"
    assert "docs_url" in data


@pytest.mark.asyncio
async def test_ping_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "pong"


@pytest.mark.asyncio
async def test_health_endpoint_structure(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "storage" in data
    assert "connected" in data["database"]
    assert "pgvector_installed" in data["database"]
    assert "backend" in data["storage"]
    assert "operational" in data["storage"]
