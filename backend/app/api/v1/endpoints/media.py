import mimetypes
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from backend.app.api.deps import get_storage_provider
from storage.base import StorageProvider

router = APIRouter()


@router.get(
    "/{storage_key:path}",
    summary="Stream Archival Media Asset",
    description="Streams physical PDF documents, high-resolution scans, images, and audio assets.",
)
async def get_media_asset(
    storage_key: str,
    storage: StorageProvider = Depends(get_storage_provider),
):
    try:
        file_path = storage.get_local_path(storage_key)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid media storage key.",
        )

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media asset '{storage_key}' not found on storage.",
        )

    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        if file_path.suffix.lower() == ".pdf":
            mime_type = "application/pdf"
        elif file_path.suffix.lower() in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif file_path.suffix.lower() == ".png":
            mime_type = "image/png"
        else:
            mime_type = "application/octet-stream"

    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=file_path.name,
        headers={
            "Cache-Control": "public, max-age=86400",
            "Accept-Ranges": "bytes",
        },
    )
