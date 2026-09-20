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


class LibraryOfCongressNormalizer(RecordNormalizer):
    """Normalizes raw Library of Congress (LOC) API metadata into CanonicalArchiveRecord."""

    ADAPTER_VERSION = "1.0.0"

    def normalize(self, raw_record: SourceRawRecord) -> CanonicalArchiveRecord:
        data = raw_record.raw_data
        item = data.get("item", data)

        # 1. Source Identification & URLs
        source = raw_record.source or "library_of_congress"
        source_id = raw_record.source_id
        source_url = raw_record.source_url or item.get("url") or f"https://www.loc.gov/item/{source_id}/"

        # 2. Title Extraction
        title_raw = item.get("title") or "Untitled Historical Record"
        if isinstance(title_raw, list):
            title = str(title_raw[0]) if title_raw else "Untitled Historical Record"
        else:
            title = str(title_raw)

        # 3. Description Extraction
        description: Optional[str] = None
        notes = item.get("notes") or item.get("summary") or item.get("description")
        if isinstance(notes, list) and notes:
            description = " ".join([str(n) for n in notes[:3]])
        elif isinstance(notes, str) and notes:
            description = notes

        # 4. Creators
        creators: List[CreatorItem] = []
        raw_contribs = item.get("contributors") or item.get("creator") or []
        if isinstance(raw_contribs, list):
            for c in raw_contribs:
                c_name = str(c).strip()
                if c_name:
                    creators.append(CreatorItem(name=c_name, role="creator"))
        elif isinstance(raw_contribs, str) and raw_contribs.strip():
            creators.append(CreatorItem(name=raw_contribs.strip(), role="creator"))

        primary_creator = creators[0].name if creators else None

        # 5. Date Parsing
        date_raw = None
        date_start = None
        date_end = None
        date_is_circa = False

        raw_date = item.get("date") or item.get("dates")
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
        raw_loc = item.get("location") or item.get("place") or []
        if isinstance(raw_loc, list):
            locations = [str(l).strip() for l in raw_loc if str(l).strip()]
        elif isinstance(raw_loc, str) and raw_loc.strip():
            locations = [raw_loc.strip()]

        primary_location = locations[0] if locations else None

        # 7. Language
        language = "English"
        raw_lang = item.get("language")
        if isinstance(raw_lang, list) and raw_lang:
            language = str(raw_lang[0])
        elif isinstance(raw_lang, str):
            language = raw_lang

        # 8. Record & Media Type Determination
        original_formats = item.get("original_format") or item.get("medium") or []
        format_str = " ".join(original_formats).lower() if isinstance(original_formats, list) else str(original_formats).lower()

        if "book" in format_str or "periodical" in format_str:
            record_type = "book"
            media_type = "document"
        elif "manuscript" in format_str:
            record_type = "manuscript"
            media_type = "document"
        elif "photo" in format_str or "image" in format_str:
            record_type = "photograph"
            media_type = "image"
        elif "map" in format_str:
            record_type = "map"
            media_type = "image"
        elif "audio" in format_str or "recording" in format_str:
            record_type = "audio"
            media_type = "audio"
        else:
            record_type = "document"
            media_type = "document"

        # 9. Subjects
        subjects: List[str] = []
        raw_subj = item.get("subjects") or item.get("subject") or []
        if isinstance(raw_subj, list):
            subjects = [str(s).strip() for s in raw_subj if str(s).strip()]
        elif isinstance(raw_subj, str) and raw_subj.strip():
            subjects = [raw_subj.strip()]

        # 10. Rights
        rights: Dict[str, Any] = {}
        rights_info = item.get("rights_information") or item.get("rights") or item.get("rights_advisory")
        if rights_info:
            rights = {"statement": str(rights_info)}

        # 11. Media Assets & Media URL
        media_assets: List[MediaAsset] = []
        primary_media_url: Optional[str] = None

        # Check resources for direct PDF or image downloads
        for res_block in item.get("resources", []):
            if isinstance(res_block, dict):
                pdf_url = res_block.get("pdf")
                if pdf_url:
                    primary_media_url = pdf_url
                    media_assets.append(
                        MediaAsset(
                            asset_id=f"{source_id}_pdf",
                            asset_role="primary",
                            media_type="document",
                            mime_type="application/pdf",
                            url=pdf_url,
                        )
                    )
                    break
                for f_list in res_block.get("files", []):
                    if isinstance(f_list, list):
                        for f in f_list:
                            if isinstance(f, dict) and f.get("url", "").endswith(".pdf"):
                                primary_media_url = f["url"]
                                media_assets.append(
                                    MediaAsset(
                                        asset_id=f"{source_id}_pdf",
                                        asset_role="primary",
                                        media_type="document",
                                        mime_type="application/pdf",
                                        url=f["url"],
                                    )
                                )
                                break

        # If no PDF found, look for image_url
        if not primary_media_url:
            img_url = item.get("image_url")
            if isinstance(img_url, list) and img_url:
                primary_media_url = str(img_url[-1])  # highest resolution usually last
            elif isinstance(img_url, str):
                primary_media_url = img_url

            if primary_media_url:
                media_assets.append(
                    MediaAsset(
                        asset_id=f"{source_id}_img",
                        asset_role="primary",
                        media_type="image" if media_type == "image" else "document",
                        mime_type="image/jpeg",
                        url=primary_media_url,
                    )
                )

        # 12. External IDs
        external_ids: Dict[str, str] = {}
        if item.get("call_number"):
            external_ids["call_number"] = str(item["call_number"])
        if item.get("lccn"):
            external_ids["lccn"] = str(item["lccn"])
        if item.get("control_number"):
            external_ids["control_number"] = str(item["control_number"])

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
