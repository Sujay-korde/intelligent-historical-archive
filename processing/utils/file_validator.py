from pathlib import Path
from typing import Optional, Union


class FileValidationError(ValueError):
    """Raised when a file fails integrity or format validation."""
    pass


MAGIC_SIGNATURES = {
    "pdf": [b"%PDF-"],
    "jpeg": [b"\xff\xd8\xff"],
    "jpg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "tiff": [b"II*\x00", b"MM\x00*"],
    "tif": [b"II*\x00", b"MM\x00*"],
    "webp": [b"RIFF"],
}


def validate_file_integrity(
    file_path: Union[str, Path],
    expected_format: Optional[str] = None,
    min_size_bytes: int = 1,
) -> Path:
    """
    Validates that a file exists, is a regular file, is not empty,
    and optionally matches the expected magic byte header signature.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileValidationError(f"File not found: {path}")

    if not path.is_file():
        raise FileValidationError(f"Path is not a regular file: {path}")

    file_size = path.stat().st_size
    if file_size < min_size_bytes:
        raise FileValidationError(f"File is empty (size={file_size} bytes): {path}")

    if expected_format:
        fmt = expected_format.lower().lstrip(".")
        expected_sigs = MAGIC_SIGNATURES.get(fmt)
        if expected_sigs:
            try:
                with open(path, "rb") as f:
                    header = f.read(32)
                
                matched = False
                for sig in expected_sigs:
                    if fmt == "webp":
                        if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
                            matched = True
                            break
                    elif fmt == "pdf":
                        # In some valid PDFs, %PDF might start within first 1024 bytes
                        if sig in header:
                            matched = True
                            break
                    else:
                        if header.startswith(sig):
                            matched = True
                            break

                if not matched:
                    raise FileValidationError(
                        f"File header mismatch for expected format '{fmt}': {path.name}"
                    )
            except OSError as e:
                raise FileValidationError(f"Unable to read file header: {e}")

    return path
