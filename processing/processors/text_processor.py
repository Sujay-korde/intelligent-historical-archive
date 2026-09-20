from pathlib import Path
from typing import List

from processing.base import DocumentProcessor, ExtractedContent, ExtractedPage


class TextProcessor(DocumentProcessor):
    """
    Processor for plain text (.txt, .md, .csv) documents.
    """

    def can_process(self, mime_type: str, extension: str) -> bool:
        ext = extension.lower().lstrip(".")
        return "text" in mime_type.lower() or ext in ["txt", "md", "csv", "json"]

    async def extract_content(self, file_path: Path) -> ExtractedContent:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Text file not found: {file_path}")

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        page = ExtractedPage(
            page_number=1,
            text=content.strip(),
            has_images=False,
            ocr_applied=False,
        )

        return ExtractedContent(
            pages=[page],
            total_pages=1,
            full_text=content.strip(),
            detected_language="English",
        )
