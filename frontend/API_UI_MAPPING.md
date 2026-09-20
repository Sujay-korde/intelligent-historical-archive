# Frontend-to-Backend API Mapping Specification

**Project**: Intelligent Historical Archive  
**Version**: 1.0.0 (Phase 01 UI Wireframe & Architecture)  
**Date**: September 20, 2026  

---

## 1. Overview & Integration Philosophy

The frontend is designed around the principle of **strict contract alignment**:
- The UI directly consumes existing, verified backend FastAPI endpoints and Pydantic schemas.
- The UI does not invent mock endpoints, fake data shapes, or client-side ranking algorithms.
- Where an endpoint is needed but not yet registered in `backend/app/api/v1/router.py`, it is explicitly identified as an **API Gap** below with the exact underlying repository or service already implemented in the backend.

---

## 2. API-to-UI Mapping Matrix

| UI Feature / Screen | UI Element | Backend Route | HTTP Method | Request Parameters / Body | Response Schema / Data Fields | Current Status |
|---|---|---|---|---|---|---|
| **Global Navigation** | System Status Badge | `/api/v1/health` | `GET` | None | `{"status": "ok", "environment": "...", "database": {"status": "connected"}, "storage": {"status": "available"}}` | **Available** |
| **Global Navigation** | Quick Search Trigger | `/api/v1/search` | `GET` | `q`, `limit=5`, `search_type="hybrid"` | `SearchResponse` (`results[].document.title`, `results[].document.id`) | **Available** |
| **Home (`/`)** | Archive Omnisearch | `/api/v1/search` | `POST` / `GET` | `SearchRequest` (`query`, `limit=10`) | `SearchResponse` (`results`, `total_results`, `facets`) | **Available** |
| **Home (`/`)** | Curated Artifacts Hero | `/api/v1/documents` | `GET` | `page=1`, `page_size=6`, `status="READY"` | `DocumentListResponse` (`items[].title`, `items[].id`, `items[].record_type`) | **Backend Implemented (Needs Route)** |
| **Home (`/`)** | Collection Statistics | `/api/v1/stats` | `GET` | None | Document count, media count, entity count, sources distribution | **Backend Implemented (Needs Route)** |
| **Explore (`/explore`)** | Main Search Stream | `/api/v1/search` | `POST` | `SearchRequest` (`query`, `search_type`, `limit`, `offset`, `source`, `record_type`, `date_start`, `date_end`, `creator`, `subject`, `historical_period`, `entity_name`, `semantic_weight`, `keyword_weight`) | `SearchResponse` (`results[].document`, `results[].relevance_score`, `results[].matching_snippet`, `results[].matched_metadata`, `results[].entities`, `results[].available_preview_information`, `results[].relevance_explanation`, `facets`) | **Available** |
| **Explore (`/explore`)** | Filter Rail Options | `/api/v1/search` (facets) | `POST` | `SearchRequest` (with facet projection) | `SearchResponse.facets` (`sources`, `record_types`, `historical_periods`, `entities`) | **Available** |
| **Explore (`/explore`)** | Query Suggestions | Predefined queries + Search History | Client / `/api/v1/search` | Initial sample queries (`"Civil War speech"`, `"Lincoln public life"`, `"Historical maps"`) | Static + Search Results | **Available** |
| **Document (`/documents/[id]`)** | Document Header & Core Metadata | `/api/v1/documents/{id}` | `GET` | Path `id: UUID` | `DocumentDetailResponse` (`title`, `description`, `source`, `source_id`, `record_type`, `source_url`, `status`, `metadata.creators`, `metadata.date_raw`, `metadata.locations`, `metadata.subjects`, `metadata.ai_metadata`, `metadata.provenance`) | **Backend Implemented (Needs Route)** |
| **Document (`/documents/[id]`)** | Archival Media / Scan Viewer | `/api/v1/media/{storage_key}` | `GET` | Path `storage_key: str` | Binary file stream (`application/pdf`, `image/jpeg`) with range request headers | **Backend Implemented (Needs Route)** |
| **Document (`/documents/[id]`)** | AI Enriched Entities | `/api/v1/documents/{id}` | `GET` | Path `id: UUID` | `DocumentDetailResponse` (`entities_count`, `metadata.ai_metadata`, linked entities) | **Backend Implemented (Needs Route)** |
| **Document (`/documents/[id]`)** | Document Local Knowledge Graph | `/api/v1/graph?document_id={id}` | `GET` | Query `document_id: UUID`, `limit=50` | `GraphResponse` (`nodes[].id`, `nodes[].label`, `nodes[].group`, `edges[].source`, `edges[].target`, `edges[].relationship`, `edges[].confidence`) | **Backend Implemented (Needs Route)** |
| **Document (`/documents/[id]`)** | Related Document Recommendations | `/api/v1/recommendations/{id}` | `GET` | Path `document_id: UUID`, Query `limit=5` | `RecommendationResponse` (`recommendations[].document`, `recommendations[].score`, `recommendations[].semantic_similarity`, `recommendations[].shared_entities`, `recommendations[].shared_subjects`, `recommendations[].explanation`, `recommendations[].preview`) | **Available** |
| **Connections (`/connections`)** | Global Knowledge Graph | `/api/v1/graph` | `GET` | Query `limit=150` | `GraphResponse` (`nodes[].id`, `nodes[].label`, `nodes[].group`, `edges[].source`, `edges[].target`, `edges[].relationship`, `edges[].confidence`) | **Backend Implemented (Needs Route)** |
| **Connections (`/connections`)** | Entity Inspector Drawer | `/api/v1/entities/{id}` or `/api/v1/graph?entity_id={id}` | `GET` | Path / Query parameter | Entity details, associated document references, co-occurring entities | **Backend Implemented (Needs Route)** |
| **Collections (`/collections`)** | Archival Source Directory | `/api/v1/collections` | `GET` | None | Collection list, item counts, supported formats, repository URLs | **Backend Implemented (Needs Route)** |
| **About (`/about`)** | Architecture & Provenance Info | Static + `/api/v1/health` | `GET` | None | System configuration metadata, model identifiers (`gemini-flash-lite-latest`, `gemini-embedding-001`, `pgvector`) | **Available** |

---

## 3. Schema & Field Alignment Details

### 3.1. Unified Search (`POST /api/v1/search`)
```typescript
// TypeScript interface matching backend/app/schemas/search.py
export interface SearchRequest {
  query: string;
  search_type?: "hybrid" | "semantic" | "keyword";
  limit?: number;
  offset?: number;
  source?: string | null;
  record_type?: string | null;
  date_start?: string | null;
  date_end?: string | null;
  creator?: string | null;
  subject?: string | null;
  historical_period?: string | null;
  entity_name?: string | null;
  semantic_weight?: number; // default: 0.7
  keyword_weight?: number;  // default: 0.3
}

export interface SearchResultItem {
  document: {
    id: string; // UUID
    title: string;
    description: string | null;
    source: string;
    source_id: string;
    record_type: string;
    source_url: string | null;
    status: string | null;
  };
  relevance_score: number; // 0.0 to 1.0
  matching_snippet: string;
  matched_metadata: Record<string, any>;
  source: string;
  entities: Array<{
    name: string;
    entity_type: string | null;
    confidence: number | null;
  }>;
  available_preview_information: {
    has_media: boolean;
    media_type: string | null;
    mime_type: string | null;
    storage_key: string | null;
    preview_url: string | null;
    access_url: string | null;
    page_number: number | null;
    file_size_bytes: number | null;
  };
  relevance_explanation: string;
  semantic_rank: number | null;
  keyword_rank: number | null;
  matching_chunk_index: number | null;
  page_number: number | null;
}

export interface SearchResponse {
  query: string;
  search_type: string;
  total_results: number;
  execution_time_ms: number;
  results: SearchResultItem[];
  facets: Record<string, any>;
}
```

### 3.2. Recommendations (`GET /api/v1/recommendations/{document_id}`)
```typescript
// TypeScript interface matching backend/app/schemas/recommendation.py
export interface RecommendedDocumentItem {
  document: {
    id: string;
    title: string;
    description: string | null;
    source: string;
    source_id: string;
    record_type: string;
    source_url: string | null;
    status: string | null;
  };
  score: number;
  semantic_similarity: number;
  shared_entities: string[];
  shared_subjects: string[];
  shared_historical_period: string | null;
  explanation: string;
  preview: {
    has_media: boolean;
    media_type: string | null;
    mime_type: string | null;
    storage_key: string | null;
    access_url: string | null;
  };
}

export interface RecommendationResponse {
  source_document_id: string;
  total_recommendations: number;
  recommendations: RecommendedDocumentItem[];
}
```

### 3.3. Knowledge Graph (`GET /api/v1/graph`)
```typescript
// TypeScript interface matching backend/app/schemas/graph.py
export interface GraphNode {
  id: string;
  label: string;
  group: "PERSON" | "ORGANIZATION" | "LOCATION" | "EVENT" | "DATE" | "TOPIC" | "document";
  metadata: Record<string, any>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  confidence: number;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
```

---

## 4. Backend API Gap Analysis

The backend architecture already contains all underlying repositories, database tables, and service models. To support the full editorial frontend without friction, the following 4 lightweight FastAPI routes should be exposed before final UI assembly:

| Missing Route | Required By Screen | Existing Backend Capability | Minimal Implementation Needed |
|---|---|---|---|
| `GET /api/v1/documents/{id}` | `/documents/[id]` (Research View) | `DocumentRepository.get_by_id(document_id)` in `document_repo.py` + `DocumentDetailResponse` schema | Register FastAPI endpoint in `backend/app/api/v1/endpoints/documents.py` |
| `GET /api/v1/documents` | `/` (Featured Items) & `/explore` (Initial Browse) | `DocumentRepository.list_documents(...)` in `document_repo.py` + `DocumentListResponse` schema | Register FastAPI endpoint with pagination & filtering |
| `GET /api/v1/graph` | `/connections` (Global Graph) & `/documents/[id]` (Local Subgraph) | `GraphService.get_graph(document_id, limit)` in `graph_service.py` + `GraphResponse` schema | Register FastAPI endpoint in `backend/app/api/v1/endpoints/graph.py` |
| `GET /api/v1/media/{storage_key:path}` | `/documents/[id]` (PDF / Image Viewer) | `LocalStorageProvider.get_local_path()` in `local_storage.py` | Mount `FileResponse` or FastAPI StaticFiles handler for `./storage/data/` |
| `GET /api/v1/stats` | `/` (Collection Counters) & `/collections` | Queries on `documents`, `document_media_assets`, `entities` | Expose count summary endpoint |

---

## 5. Verification Checklist for UI Development

- [x] OpenAPI schema validated against `backend/app/main.py`.
- [x] Search request payload matches `SearchRequest`.
- [x] Search response payload matches `SearchResponse`.
- [x] Recommendation response payload matches `RecommendationResponse`.
- [x] Graph response payload matches `GraphResponse`.
- [x] Document detail response payload matches `DocumentDetailResponse`.
- [x] Identified all missing endpoints and traced them to existing backend code.
