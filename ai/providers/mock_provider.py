import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel

from ai.interfaces.extractor import AIEnrichmentProvider
from ai.models.enrichment import (
    AIEnrichmentResult,
    AIEntity,
    AIMetadata,
    AIResponseEnvelope,
    AISummary,
    EntityType,
    TokenUsage,
)

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(AIEnrichmentProvider):
    """
    Deterministic, zero-dependency offline AI enrichment provider.
    Extracts metadata, entities (PERSON, ORGANIZATION, LOCATION, EVENT, DATE, TOPIC),
    and archival summaries using rule-based historical heuristic NLP.
    """
    provider_name: str = "MockLLM"
    model_name: str = "mock-historical-nlp-v1"
    model_version: str = "1.0.0"

    def _extract_entities_from_text(self, text: str) -> List[AIEntity]:
        entities: List[AIEntity] = []
        seen_names = set()

        def add_entity(name: str, etype: EntityType, conf: float, desc: Optional[str] = None):
            clean_name = name.strip()
            if clean_name and clean_name.lower() not in seen_names and len(clean_name) > 1:
                seen_names.add(clean_name.lower())
                entities.append(
                    AIEntity(
                        name=clean_name,
                        entity_type=etype,
                        confidence=conf,
                        description=desc,
                    )
                )

        # 1. PERSON: Historical honorifics or capitalized two-word names
        person_matches = re.findall(
            r"\b(?:Mr\.|Dr\.|Lord|Sir|President|Governor|General|Rev\.|Pastor)?\s*([A-Z][a-z]+ [A-Z][a-z]+)\b",
            text,
        )
        for p in person_matches[:6]:
            add_entity(p, EntityType.PERSON, 0.90, "Identified historical individual")

        # 2. ORGANIZATION: Societies, congresses, committees, universities
        org_matches = re.findall(
            r"\b([A-Z][a-zA-Z\s]+(?:University|Commission|Committee|Department|Congress|Assembly|Institute|Society|Association|Union|Confederacy))\b",
            text,
        )
        for org in org_matches[:5]:
            add_entity(org, EntityType.ORGANIZATION, 0.92, "Historical institution or governing body")

        # 3. LOCATION: Nations, territories, states, cities
        loc_patterns = [
            r"\b(United States|America|Great Britain|United Kingdom|England|France|Germany|Spain|Virginia|Massachusetts|New York|Pennsylvania|Carolina|Georgia|Washington|Richmond|Philadelphia|Boston|London|Paris)\b",
            r"\b(India|Maharashtra|Pune|Bombay|Delhi|Bengal|Calcutta|Madras)\b",
        ]
        for pat in loc_patterns:
            for loc in re.findall(pat, text):
                add_entity(loc, EntityType.LOCATION, 0.95, "Geographic location")

        # 4. EVENT: Wars, battles, conventions, treaties
        event_matches = re.findall(
            r"\b(?:The\s+)?([A-Z][a-zA-Z\s]+(?:War|Battle|Revolution|Convention|Treaty|Rebellion|Campaign|Proclamation|Address))\b",
            text,
        )
        for ev in event_matches[:4]:
            add_entity(ev, EntityType.EVENT, 0.88, "Historical event or milestone")

        # 5. DATE: 4-digit years or centuries
        year_matches = re.findall(r"\b(1[6-9]\d{2}|20\d{2})\b", text)
        for yr in set(year_matches[:4]):
            add_entity(yr, EntityType.DATE, 0.98, f"Historical year {yr}")

        # 6. TOPIC: Conceptual historical domains
        topic_keywords = {
            "Civil Rights & Abolition": ["liberty", "freedom", "slavery", "abolition", "emancipation", "equality", "rights"],
            "Constitutional Law & Governance": ["constitution", "government", "legislature", "statute", "union", "sovereignty", "policy"],
            "Military Strategy & Conflict": ["war", "army", "forces", "battle", "troops", "command", "conflict", "fort"],
            "Economy & Trade": ["trade", "commerce", "revenue", "agriculture", "industry", "tariff", "economic"],
            "Education & Science": ["education", "school", "university", "scientific", "knowledge", "scholarship"],
        }
        for domain, kws in topic_keywords.items():
            if any(kw in text.lower() for kw in kws):
                add_entity(domain, EntityType.TOPIC, 0.85, f"Thematic domain: {domain}")

        return entities

    def _determine_historical_period(self, text: str, year_matches: List[str]) -> str:
        if year_matches:
            latest_yr = int(max(year_matches))
            if latest_yr < 1775:
                return "Colonial Era (Pre-1775)"
            elif latest_yr <= 1789:
                return "American Revolution & Founding (1775–1789)"
            elif latest_yr <= 1860:
                return "Early Republic & Antebellum Period (1790–1860)"
            elif latest_yr <= 1865:
                return "American Civil War Era (1861–1865)"
            elif latest_yr <= 1900:
                return "Reconstruction & Gilded Age (1866–1900)"
            elif latest_yr <= 1945:
                return "Early 20th Century & World Wars (1901–1945)"
            else:
                return "Post-War & Modern Era (1946–Present)"

        lower = text.lower()
        if "civil war" in lower or "confederacy" in lower or "union" in lower:
            return "American Civil War Era (1861–1865)"
        elif "revolution" in lower or "independence" in lower:
            return "Revolutionary Era"
        return "Historical Archival Record"

    async def extract_metadata(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> AIResponseEnvelope[AIMetadata]:
        start = time.perf_counter()
        ctx = context or {}

        # Heuristic fields
        years = re.findall(r"\b(1[6-9]\d{2}|20\d{2})\b", text)
        entities = self._extract_entities_from_text(text)

        person_entities = [e.name for e in entities if e.entity_type == EntityType.PERSON]
        org_entities = [e.name for e in entities if e.entity_type == EntityType.ORGANIZATION]
        loc_entities = [e.name for e in entities if e.entity_type == EntityType.LOCATION]
        topic_entities = [e.name for e in entities if e.entity_type == EntityType.TOPIC]

        # Determine document type
        doc_type = "Historical Document"
        lower = text.lower()
        if "speech" in lower or "oration" in lower or "address" in lower:
            doc_type = "Historical Address / Speech"
        elif "letter" in lower or "correspondence" in lower:
            doc_type = "Correspondence / Letter"
        elif "treaty" in lower or "convention" in lower:
            doc_type = "Treaty / Legal Instrument"
        elif "map" in lower or "atlas" in lower:
            doc_type = "Cartographic Record / Map"

        meta = AIMetadata(
            title=ctx.get("title") or (person_entities[0] + " - " + doc_type if person_entities else None),
            creator=person_entities[0] if person_entities else (org_entities[0] if org_entities else None),
            date=years[0] if years else None,
            location=loc_entities[0] if loc_entities else None,
            organization=org_entities[0] if org_entities else None,
            document_type=doc_type,
            language="English",
            subjects=topic_entities[:4],
            topics=topic_entities,
            historical_period=self._determine_historical_period(text, years),
            confidence=0.90,
        )

        latency = (time.perf_counter() - start) * 1000
        words = len(text.split())

        return AIResponseEnvelope(
            data=meta,
            provider=self.provider_name,
            model=self.model_name,
            model_version=self.model_version,
            confidence=0.90,
            usage=TokenUsage(prompt_tokens=words, completion_tokens=80, total_tokens=words + 80),
            latency_ms=round(latency, 2),
            provenance="AI",
        )

    async def extract_entities(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> AIResponseEnvelope[List[AIEntity]]:
        start = time.perf_counter()
        entities = self._extract_entities_from_text(text)
        latency = (time.perf_counter() - start) * 1000
        words = len(text.split())

        avg_conf = (
            sum(e.confidence for e in entities) / len(entities) if entities else 1.0
        )

        return AIResponseEnvelope(
            data=entities,
            provider=self.provider_name,
            model=self.model_name,
            model_version=self.model_version,
            confidence=round(avg_conf, 2),
            usage=TokenUsage(prompt_tokens=words, completion_tokens=len(entities) * 15, total_tokens=words + len(entities) * 15),
            latency_ms=round(latency, 2),
            provenance="AI",
        )

    async def summarize(
        self, text: str, max_length: int = 300
    ) -> AIResponseEnvelope[AISummary]:
        start = time.perf_counter()
        first_sentences = re.split(r"(?<=[.!?])\s+", text.strip())[:3]
        summary_text = " ".join(first_sentences) if first_sentences else "Historical document archive record."
        if len(summary_text) > max_length:
            summary_text = summary_text[: max_length - 3] + "..."

        # Key points extraction
        key_points = []
        for s in first_sentences[:3]:
            clean_s = s.strip()
            if len(clean_s) > 15:
                key_points.append(clean_s)

        summary_obj = AISummary(
            summary=summary_text,
            key_points=key_points,
            confidence=0.92,
        )

        latency = (time.perf_counter() - start) * 1000
        words = len(text.split())

        return AIResponseEnvelope(
            data=summary_obj,
            provider=self.provider_name,
            model=self.model_name,
            model_version=self.model_version,
            confidence=0.92,
            usage=TokenUsage(prompt_tokens=words, completion_tokens=len(summary_text.split()), total_tokens=words + len(summary_text.split())),
            latency_ms=round(latency, 2),
            provenance="AI",
        )

    async def enrich(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> AIResponseEnvelope[AIEnrichmentResult]:
        start = time.perf_counter()

        meta_res = await self.extract_metadata(text, context)
        ent_res = await self.extract_entities(text, context)
        sum_res = await self.summarize(text)

        enrichment_result = AIEnrichmentResult(
            metadata=meta_res.data,
            entities=ent_res.data,
            summary=sum_res.data,
        )

        latency = (time.perf_counter() - start) * 1000
        total_tokens = meta_res.usage.total_tokens + ent_res.usage.total_tokens + sum_res.usage.total_tokens

        return AIResponseEnvelope(
            data=enrichment_result,
            provider=self.provider_name,
            model=self.model_name,
            model_version=self.model_version,
            confidence=round((meta_res.confidence + ent_res.confidence + sum_res.confidence) / 3.0, 2),
            usage=TokenUsage(total_tokens=total_tokens),
            latency_ms=round(latency, 2),
            provenance="AI",
        )

    # Backwards compatibility helper for existing code calling extract_structured
    async def extract_structured(
        self, prompt: str, schema: Type[T], context: Optional[Dict[str, Any]] = None
    ) -> Any:
        from ai.base import AIResponse
        ctx = context or {}
        text = ctx.get("text", prompt)

        res = await self.enrich(text, context)

        # Convert to older schema if necessary
        try:
            from ai.base import ExtractedEnrichment, ExtractedMetadata as OldMeta, ExtractedEntity as OldEnt
            if schema == ExtractedEnrichment:
                old_entities = [
                    OldEnt(
                        name=e.name,
                        entity_type=e.entity_type.value,
                        description=e.description,
                        authority_uri=e.authority_uri,
                        confidence=e.confidence,
                    )
                    for e in res.data.entities
                ]
                old_meta = OldMeta(
                    summary=res.data.summary.summary if res.data.summary else "",
                    suggested_title=res.data.metadata.title,
                    historical_period=res.data.metadata.historical_period,
                    topics=res.data.metadata.topics,
                    geographic_references=[e.name for e in res.data.entities if e.entity_type == EntityType.LOCATION],
                    confidence=res.data.metadata.confidence,
                )
                data_obj = ExtractedEnrichment(metadata=old_meta, entities=old_entities)
                return AIResponse(
                    data=data_obj,
                    usage=res.usage,
                    model_name=self.model_name,
                    latency_ms=res.latency_ms,
                )
        except Exception:
            pass

        return AIResponse(
            data=res.data,
            usage=res.usage,
            model_name=self.model_name,
            latency_ms=res.latency_ms,
        )
