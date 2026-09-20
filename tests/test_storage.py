import pytest
import hashlib
from typing import AsyncIterator
from storage.base import StorageProvider, StoredFileMetadata
from storage.local_storage import LocalStorageProvider


async def async_bytes_generator(data: bytes, chunk_size: int = 1024) -> AsyncIterator[bytes]:
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


@pytest.mark.asyncio
async def test_local_storage_lifecycle(temp_storage_dir):
    storage = LocalStorageProvider(base_dir=temp_storage_dir)

    payload = b"Intelligent Historical Archive Document Content 12345"
    expected_hash = hashlib.sha256(payload).hexdigest()
    storage_key = "documents/2026/09/sample_doc.txt"

    # 1. Save stream
    meta: StoredFileMetadata = await storage.save_stream(
        stream=async_bytes_generator(payload),
        destination_key=storage_key,
        content_type="text/plain",
    )

    assert meta.storage_key == storage_key
    assert meta.file_size_bytes == len(payload)
    assert meta.checksum_sha256 == expected_hash
    assert meta.content_type == "text/plain"

    # 2. Check existence
    assert await storage.exists(storage_key) is True
    assert await storage.exists("non_existent_key.pdf") is False

    # 3. Read stream
    read_stream = await storage.get_stream(storage_key)
    collected = b""
    async for chunk in read_stream:
        collected += chunk

    assert collected == payload

    # 4. Access URL
    url = storage.get_access_url(storage_key)
    assert storage_key in url

    # 5. Delete file
    deleted = await storage.delete_file(storage_key)
    assert deleted is True
    assert await storage.exists(storage_key) is False


@pytest.mark.asyncio
async def test_storage_path_traversal_prevention(temp_storage_dir):
    storage = LocalStorageProvider(base_dir=temp_storage_dir)

    with pytest.raises(ValueError, match="Invalid storage key"):
        storage._resolve_path("../../etc/passwd")
