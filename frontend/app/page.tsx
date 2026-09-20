import React from 'react';
import StatusDashboard from '@/components/StatusDashboard';
import ArchitectureCard from '@/components/ArchitectureCard';

export default function Home() {
  return (
    <div className="container">
      {/* Hero Section */}
      <section style={{
        padding: '3rem 0 2rem',
        textAlign: 'center',
        position: 'relative',
      }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.35rem 0.9rem',
          background: 'rgba(99, 102, 241, 0.1)',
          border: '1px solid rgba(99, 102, 241, 0.25)',
          borderRadius: '9999px',
          fontSize: '0.8rem',
          color: 'var(--accent-indigo)',
          marginBottom: '1.25rem',
          fontWeight: '500',
        }}>
          <span>✨</span> Phase 0 Foundation Initialized
        </div>

        <h1 style={{
          fontSize: '2.5rem',
          fontWeight: '800',
          letterSpacing: '-0.03em',
          lineHeight: '1.2',
          marginBottom: '1rem',
          background: 'linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #94a3b8 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          Intelligent Historical Knowledge Archive
        </h1>

        <p style={{
          maxWidth: '750px',
          margin: '0 auto 2rem',
          color: 'var(--text-secondary)',
          fontSize: '1.05rem',
          lineHeight: '1.6',
        }}>
          Enterprise-grade archival preservation and hybrid neural search platform. 
          Built on PostgreSQL + pgvector, FastAPI async backend, and Next.js App Router.
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <a
            href="http://127.0.0.1:8000/api/v1/health"
            target="_blank"
            rel="noreferrer"
            className="btn btn-primary"
          >
            Probe Health Endpoint (/api/v1/health)
          </a>
          <a
            href="http://127.0.0.1:8000/api/v1/docs"
            target="_blank"
            rel="noreferrer"
            className="btn btn-outline"
          >
            Interactive OpenAPI Swagger
          </a>
        </div>
      </section>

      {/* Live Subsystem Telemetry */}
      <StatusDashboard />

      {/* Architecture Matrix */}
      <section style={{ marginTop: '3rem' }}>
        <div style={{ marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '700', letterSpacing: '-0.02em' }}>
            System Architecture & Roadmap
          </h2>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Strictly decoupled modular architecture separating Ingestion, Processing, Indexing, and Retrieval.
          </p>
        </div>

        <div className="grid-cols-3">
          <ArchitectureCard
            phase="Phase 0"
            title="Core Foundation"
            description="Complete scaffolding: FastAPI async engine, PostgreSQL + pgvector schema, Alembic migrations, object storage abstraction, and Next.js console."
            technologies={['FastAPI', 'PostgreSQL 16', 'pgvector', 'Alembic', 'Next.js 14', 'TypeScript']}
            status="completed"
          />

          <ArchitectureCard
            phase="Phase 1"
            title="Ingestion Subsystem"
            description="Pluggable ingestion adapters for PDF, Images, Text, and Audio/Video with SHA-256 deduplication and streaming storage."
            technologies={['Multi-Format Adapters', 'Checksum Pipeline', 'Streaming IO', 'Async Tasks']}
            status="upcoming"
          />

          <ArchitectureCard
            phase="Phase 2"
            title="Processing & OCR"
            description="OCR extraction, structural chunking with sliding windows, entity extraction, and vector embedding pipelines."
            technologies={['PyMuPDF', 'pgvector Embeddings', 'Chunking Engine', 'Worker Lease']}
            status="upcoming"
          />

          <ArchitectureCard
            phase="Phase 3"
            title="Knowledge Graph"
            description="Entity normalization, authority resolution (Wikidata/VIAF), relationship modeling, and temporal graph querying."
            technologies={['Relational Graph', 'Entity Linker', 'JSONB Metadata', 'Authority URI']}
            status="upcoming"
          />

          <ArchitectureCard
            phase="Phase 4"
            title="Hybrid Search & RAG"
            description="Reciprocal Rank Fusion (RRF) combining dense semantic vector search with pg_trgm BM25 sparse keyword search."
            technologies={['Dense Vectors', 'pg_trgm Fulltext', 'RRF Ranker', 'Grounded Citations']}
            status="upcoming"
          />

          <ArchitectureCard
            phase="Phase 5"
            title="Archival Explorer UI"
            description="Interactive Next.js timeline viewer, deep document zoom, facet filtering, knowledge graph visualization, and citation inspection."
            technologies={['Next.js App Router', 'Interactive Timelines', 'Facet Search', 'Graph Canvas']}
            status="upcoming"
          />
        </div>
      </section>
    </div>
  );
}
