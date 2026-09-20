import os
import shutil
import tempfile
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
from backend.app.main import app
from storage.local_storage import LocalStorageProvider
from backend.app.api.deps import get_storage_provider


@pytest.fixture(scope="session")
def temp_storage_dir():
    """Create a temporary directory for file storage during testing."""
    temp_dir = tempfile.mkdtemp(prefix="archive_test_storage_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_storage(temp_storage_dir):
    """Storage provider configured with temp directory."""
    return LocalStorageProvider(base_dir=temp_storage_dir)


@pytest_asyncio.fixture
async def async_client(test_storage) -> AsyncGenerator[AsyncClient, None]:
    """Test HTTP client with overridden storage and DB dependencies."""
    app.dependency_overrides[get_storage_provider] = lambda: test_storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
