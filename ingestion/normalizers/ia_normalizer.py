import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from ingestion.models.canonical import (
    CanonicalArchiveRecord,
    CreatorItem,
    IngestionProvenance,
    MediaAsset,
    ProvenanceItem,
    SourceRawRecord,
)
from ingestion.normalizers.base import RecordNormalizer


class InternetArchiveNormalizer(RecordNormalizer):
    """Normalizes raw Internet Archive (archive.org) API metadata into CanonicalArchiveRecord."""

    ADAPTER_VERSION = "1.0.0"

    def normalize(self, raw_record: SourceRawRecord) -> CanonicalArchiveRecord:
        data = raw_record.raw_data
        metadata = data.get("metadata", data)
        files = data.get("files", [])

        # 1. Source Identification & URLs
        source = raw_record.source or "internet_archive"
        source_id = raw_record.source_id or metadata.get("identifier", "")
        source_url = raw_record.source_url or f"https://archive.org/details/{source_id}"

        # 2. Title Extraction
        title_raw = metadata.get("title") or "Untitled Internet Archive Item"
        title = str(title_raw[0]) if isinstance(title_raw, list) and title_raw else str(title_raw)

        # 3. Description Extraction
        description: Optional[str] = None
        desc_raw = metadata.get("description")
        if isinstance(desc_raw, list) and desc_raw:
            description = " ".join([str(d) for d in desc_raw])
        elif isinstance(desc_raw, str) and desc_raw:
            description = desc_raw

        # 4. Creators
        creators: List[CreatorItem] = []
        creator_raw = metadata.get("creator") or metadata.get("author") or metadata.get("artist") or []
        if isinstance(creator_raw, list):
            for c in creator_raw:
                c_name = str(c).strip()
                if c_name:
                    creators.append(CreatorItem(name=c_name, role="creator"))
        elif isinstance(creator_raw, str) and creator_raw.strip():
            creators.append(CreatorItem(name=creator_raw.strip(), role="creator"))

        primary_creator = creators[0].name if creators else None

        # 5. Date Parsing
        date_raw = None
        date_start = None
        date_end = None
        date_is_circa = False

        raw_date = metadata.get("date") or metadata.get("year") or metadata.get("publicdate")
        if isinstance(raw_date, list) and raw_date:
            date_raw = str(raw_date[0])
        elif isinstance(raw_date, str):
            date_raw = raw_date

        if date_raw:
            if "c" in date_raw.lower() or "circa" in date_raw.lower():
                date_is_circa = True
            years = re.findall(r"\b(1\d{3}|20\d{2})\b", date_raw)
            if years:
                date_start = f"{years[0]}-01-01"
                date_end = f"{years[-1]}-12-31"

        # 6. Location Extraction
        locations: List[str] = []
        raw_loc = metadata.get("coverage") or metadata.get("place") or []
        if isinstance(raw_loc, list):
            locations = [str(l).strip() for l in raw_loc if str(l).strip()]
        elif isinstance(raw_loc, str) and raw_loc.strip():
            locations = [raw_loc.strip()]

        primary_location = locations[0] if locations else None

        # 7. Language
        language = "English"
        raw_lang = metadata.get("language")
        if isinstance(raw_lang, list) and raw_lang:
            language = str(raw_lang[0])
        elif isinstance(raw_lang, str):
            language = raw_lang

        # 8. Record & Media Type Determination
        mediatype = str(metadata.get("mediatype", "")).lower()
        if mediatype in ["texts", "book"]:
            record_type = "book"
            media_type = "document"
        elif mediatype in ["image", "photo"]:
            record_type = "photograph"
            media_type = "image"
        elif mediatype in ["audio", "sound"]:
            record_type = "audio"
            media_type = "audio"
        elif mediatype in ["movies", "film", "video"]:
            record_type = "video"
            media_type = "video"
        else:
            record_type = "document"
            media_type = "document"

        # 9. Subjects
        subjects: List[str] = []
        raw_subj = metadata.get("subject") or metadata.get("topic") or []
        if isinstance(raw_subj, list):
            for s in raw_subj:
                s_str = str(s).strip()
                if ";" in s_str:
                    subjects.extend([sub.strip() for sub in s_str.split(";") if sub.strip()])
                elif s_str:
                    subjects.append(s_str)
        elif isinstance(raw_subj, str) and raw_subj.strip():
            # Could be semicolon or comma separated
            if ";" in raw_subj:
                subjects = [s.strip() for s in raw_subj.split(";") if s.strip()]
            else:
                subjects = [raw_subj.strip()]

        # 10. Rights & License
        rights: Dict[str, Any] = {}
        license_url = metadata.get("licenseurl") or metadata.get("rights")
        if license_url:
            rights = {"statement": str(license_url)}

        # 11. Media Assets & Media URL
        media_assets: List[MediaAsset] = []
        primary_media_url: Optional[str] = None
        server = data.get("server", "ia800000.us.archive.org")
        dir_path = data.get("dir", f"items/{source_id}").strip("/")

        # Check files array for best primary file (e.g. Text PDF, Original PDF, or High-res scan)
        pdf_file = None
        txt_file = None
        image_file = None

        if isinstance(files, list):
            for f in files:
                if not isinstance(f, dict):
                    continue
                name = f.get("name", "")
                fmt = f.get("format", "").lower()

                if name.endswith(".pdf") or "pdf" in fmt:
                    if not pdf_file or "text" in fmt:
                        pdf_file = f
                elif name.endswith("_djvu.txt") or "text" in fmt:
                    txt_file = f
                elif name.endswith((".jpg", ".png", ".jp2")) and "thumb" not in name.lower():
                    if not image_file:
                        image_file = f

        selected_file = pdf_file or txt_file or image_file

        if selected_file:
            file_name = selected_file.get("name", "")
            primary_media_url = f"https://archive.org/download/{source_id}/{file_name}"
            mime_type = "application/pdf" if file_name.endswith(".pdf") else "text/plain" if file_name.endswith(".txt") else "image/jpeg"
            size = selected_file.get("size")
            size_int = int(size) if size and str(size).isdigit() else None
            sha256 = selected_file.get("sha256") or selected_file.get("sha1")

            media_assets.append(
                MediaAsset(
                    asset_id=f"{source_id}_{file_name}",
                    asset_role="primary",
                    media_type=media_type,
                    mime_type=mime_type,
                    url=primary_media_url,
                    file_size_bytes=size_int,
                    checksum_sha256=sha256,
                )
            )
        elif source_id:
            # Standard download pattern
            primary_media_url = f"https://archive.org/download/{source_id}/{source_id}.pdf"
            media_assets.append(
                MediaAsset(
                    asset_id=f"{source_id}_default",
                    asset_role="primary",
                    media_type=media_type,
                    mime_type="application/pdf",
                    url=primary_media_url,
                )
            )

        # 12. External IDs
        external_ids: Dict[str, str] = {}
        if metadata.get("identifier"):
            external_ids["archive_org_id"] = str(metadata["identifier"])
        if metadata.get("isbn"):
            external_ids["isbn"] = str(metadata["isbn"])
        if metadata.get("oclc-id"):
            external_ids["oclc"] = str(metadata["oclc-id"])
        if metadata.get("ark"):
            external_ids["ark"] = str(metadata["ark"])

        # 13. Provenance
        provenance = IngestionProvenance(
            imported_at=datetime.utcnow(),
            adapter_version=self.ADAPTER_VERSION,
            original_source_id=source_id,
            original_source_url=source_url,
        )

        provenance_records = [
            ProvenanceItem(field="title", value=title, source="SOURCE"),
            ProvenanceItem(field="creators", value=[c.model_dump() for c in creators], source="SOURCE"),
            ProvenanceItem(field="date", value=date_raw, source="SOURCE"),
        ]

        return CanonicalArchiveRecord(
            source=source,
            source_id=source_id,
            external_ids=external_ids,
            title=title,
            description=description,
            creator=primary_creator,
            creators=creators,
            date=date_raw,
            date_raw=date_raw,
            date_start=date_start,
            date_end=date_end,
            date_is_circa=date_is_circa,
            location=primary_location,
            locations=locations,
            language=language,
            record_type=record_type,
            media_type=media_type,
            media_url=primary_media_url,
            media_assets=media_assets,
            subjects=subjects,
            rights=rights,
            source_url=source_url,
            raw_metadata=raw_record.raw_data,
            provenance=provenance,
            provenance_records=provenance_records,
        )
