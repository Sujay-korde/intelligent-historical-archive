from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
from pydantic import BaseModel


class StoredFileMetadata(BaseModel):
    storage_key: str
    file_size_bytes: int
    content_type: str
    checksum_sha256: str


class StorageProvider(ABC):
    @abstractmethod
    async def save_stream(
        self, stream: AsyncIterator[bytes], destination_key: str, content_type: str, max_bytes: Optional[int] = None
    ) -> StoredFileMetadata:
        """Stream data into storage with hash calculation and zero-copy chunking."""
        pass

    @abstractmethod
    async def get_stream(self, storage_key: str) -> AsyncIterator[bytes]:
        """Stream data out of storage."""
        pass

    @abstractmethod
    async def exists(self, storage_key: str) -> bool:
        """Check if file exists in storage."""
        pass

    @abstractmethod
    async def delete_file(self, storage_key: str) -> bool:
        """Delete file from storage."""
        pass

    @abstractmethod
    def get_access_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL (S3) or secure local proxy URL."""
        pass
