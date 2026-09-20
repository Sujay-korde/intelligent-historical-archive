import hashlib
import os
from pathlib import Path
from typing import AsyncIterator
import aiofiles

from storage.base import StorageProvider, StoredFileMetadata


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str = "./storage/data", base_url_prefix: str = "/api/v1/storage"):
        self.base_dir = Path(base_dir).resolve()
        self.base_url_prefix = base_url_prefix.rstrip("/")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, storage_key: str) -> Path:
        # Sanitize storage_key to avoid path traversal
        clean_key = storage_key.strip("/\\")
        target_path = (self.base_dir / clean_key).resolve()
        if not str(target_path).startswith(str(self.base_dir)):
            raise ValueError(f"Invalid storage key: {storage_key}")
        return target_path

    async def save_stream(
        self, stream: AsyncIterator[bytes], destination_key: str, content_type: str
    ) -> StoredFileMetadata:
        target_path = self._resolve_path(destination_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        sha256 = hashlib.sha256()
        total_bytes = 0

        async with aiofiles.open(target_path, "wb") as f:
            async for chunk in stream:
                if chunk:
                    sha256.update(chunk)
                    total_bytes += len(chunk)
                    await f.write(chunk)

        return StoredFileMetadata(
            storage_key=destination_key,
            file_size_bytes=total_bytes,
            content_type=content_type,
            checksum_sha256=sha256.hexdigest(),
        )

    async def get_stream(self, storage_key: str) -> AsyncIterator[bytes]:
        target_path = self._resolve_path(storage_key)
        if not target_path.exists():
            raise FileNotFoundError(f"Storage file not found: {storage_key}")

        async def file_iterator():
            async with aiofiles.open(target_path, "rb") as f:
                while chunk := await f.read(64 * 1024):  # 64KB chunks
                    yield chunk

        return file_iterator()

    async def exists(self, storage_key: str) -> bool:
        target_path = self._resolve_path(storage_key)
        return target_path.exists()

    async def delete_file(self, storage_key: str) -> bool:
        target_path = self._resolve_path(storage_key)
        if target_path.exists():
            target_path.unlink()
            return True
        return False

    def get_access_url(self, storage_key: str, expires_in: int = 3600) -> str:
        clean_key = storage_key.strip("/\\").replace("\\", "/")
        return f"{self.base_url_prefix}/{clean_key}"

    def get_local_path(self, storage_key: str) -> Path:
        return self._resolve_path(storage_key)
