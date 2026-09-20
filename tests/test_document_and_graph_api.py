import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_documents_list_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


@pytest.mark.asyncio
async def test_stats_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert "media_assets" in data
    assert "chunks" in data
    assert "embeddings" in data
    assert "entities" in data
    assert "relationships" in data
    assert data["status"] == "online"


@pytest.mark.asyncio
async def test_graph_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/graph")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
