import mimetypes
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from backend.app.api.deps import get_storage_provider
from storage.base import StorageProvider

router = APIRouter()


@router.api_route(
    "/{storage_key:path}",
    methods=["GET", "HEAD"],
    summary="Stream Archival Media Asset",
    description="Streams physical PDF documents, manuscripts, high-resolution scans, images, and audio assets.",
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
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            mime_type = "application/pdf"
        elif ext in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif ext == ".png":
            mime_type = "image/png"
        elif ext in [".txt", ".text"]:
            mime_type = "text/plain; charset=utf-8"
        elif ext == ".mp4":
            mime_type = "video/mp4"
        elif ext == ".mp3":
            mime_type = "audio/mpeg"
        else:
            mime_type = "application/octet-stream"

    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=file_path.name,
        content_disposition_type="inline",
        headers={
            "Cache-Control": "public, max-age=86400",
            "Accept-Ranges": "bytes",
        },
    )
