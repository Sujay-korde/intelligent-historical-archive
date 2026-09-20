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

        # 8. Subjects Extraction
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

        # 9. Record & Media Type Determination
        mediatype = str(metadata.get("mediatype", "")).lower()
        title_lower = title.lower()
        desc_lower = (description or "").lower()
        all_subj_text = " ".join(subjects).lower()

        is_manuscript = any(
            k in title_lower or k in desc_lower or k in all_subj_text
            for k in ["manuscript", "holograph", "letter to", "[letter", "diary", "journal", "personal papers"]
        )

        # Check if files explicitly contain video files
        has_video_file = any(
            isinstance(f, dict) and f.get("name", "").lower().endswith((".mp4", ".webm", ".ogv", ".mov", ".mkv", ".avi", ".m4v"))
            for f in (files if isinstance(files, list) else [])
        )

        if mediatype in ["audio", "sound"]:
            record_type = "audio"
            media_type = "audio"
        elif mediatype in ["movies", "movie", "movingimage", "film", "video"] or has_video_file:
            record_type = "video"
            media_type = "video"
        elif mediatype in ["image", "photo"]:
            if "map" in title_lower or "atlas" in title_lower or "cartograph" in all_subj_text:
                record_type = "map"
            else:
                record_type = "photograph"
            media_type = "image"
        elif is_manuscript:
            record_type = "manuscript"
            media_type = "document"
        elif mediatype in ["texts", "book"]:
            record_type = "book"
            media_type = "document"
        else:
            record_type = "document"
            media_type = "document"

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

        # Check files array for best primary file according to media_type
        video_file = None
        audio_file = None
        image_file = None
        pdf_file = None
        txt_file = None

        if isinstance(files, list):
            for f in files:
                if not isinstance(f, dict):
                    continue
                name = f.get("name", "")
                name_lower = name.lower()
                fmt = f.get("format", "").lower()

                # Video selection
                if media_type == "video":
                    if name_lower.endswith((".mp4", ".webm", ".ogv", ".mov", ".mkv", ".avi")) or "mpeg4" in fmt or "video" in fmt or "h.264" in fmt:
                        if not video_file or name_lower.endswith(".mp4"):
                            video_file = f

                # Audio selection
                elif media_type == "audio":
                    if name_lower.endswith((".mp3", ".m4a", ".ogg", ".wav")) or "mp3" in fmt or "audio" in fmt:
                        if not audio_file or "vbr mp3" in fmt or name_lower.endswith(".mp3"):
                            audio_file = f

                # Image selection
                elif media_type == "image":
                    if name_lower.endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff")) and "thumb" not in name_lower:
                        if not image_file or name_lower.endswith((".jpg", ".jpeg")):
                            image_file = f

                # Document / Manuscript selection
                else:
                    if name_lower.endswith(".pdf") or "pdf" in fmt:
                        if not pdf_file or "text" in fmt:
                            pdf_file = f
                    elif name_lower.endswith("_djvu.txt") or "text" in fmt:
                        if not txt_file:
                            txt_file = f
                    elif name_lower.endswith((".jpg", ".png")) and "thumb" not in name_lower:
                        if not image_file:
                            image_file = f

        selected_file = None
        if media_type == "video":
            selected_file = video_file
        elif media_type == "audio":
            selected_file = audio_file
        elif media_type == "image":
            selected_file = image_file
        else:
            selected_file = pdf_file or txt_file or image_file

        if selected_file:
            file_name = selected_file.get("name", "")
            file_lower = file_name.lower()
            primary_media_url = f"https://archive.org/download/{source_id}/{file_name}"
            
            # Determine MIME type accurately
            if file_lower.endswith(".mp4"):
                mime_type = "video/mp4"
            elif file_lower.endswith(".webm"):
                mime_type = "video/webm"
            elif file_lower.endswith(".ogv"):
                mime_type = "video/ogg"
            elif file_lower.endswith(".mov"):
                mime_type = "video/quicktime"
            elif file_lower.endswith(".mkv"):
                mime_type = "video/x-matroska"
            elif file_lower.endswith(".mp3"):
                mime_type = "audio/mpeg"
            elif file_lower.endswith(".m4a"):
                mime_type = "audio/mp4"
            elif file_lower.endswith(".ogg"):
                mime_type = "audio/ogg"
            elif file_lower.endswith(".wav"):
                mime_type = "audio/wav"
            elif file_lower.endswith((".jpg", ".jpeg")):
                mime_type = "image/jpeg"
            elif file_lower.endswith(".png"):
                mime_type = "image/png"
            elif file_lower.endswith(".pdf"):
                mime_type = "application/pdf"
            elif file_lower.endswith(".txt"):
                mime_type = "text/plain"
            else:
                mime_type = "application/octet-stream"

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
            # Fallback based on media_type
            if media_type == "video":
                ext = "mp4"
                mime = "video/mp4"
            elif media_type == "audio":
                ext = "mp3"
                mime = "audio/mpeg"
            elif media_type == "image":
                ext = "jpg"
                mime = "image/jpeg"
            else:
                ext = "pdf"
                mime = "application/pdf"
            primary_media_url = f"https://archive.org/download/{source_id}/{source_id}.{ext}"
            media_assets.append(
                MediaAsset(
                    asset_id=f"{source_id}_default",
                    asset_role="primary",
                    media_type=media_type,
                    mime_type=mime,
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
