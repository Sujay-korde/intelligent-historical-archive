'use client';

import React from 'react';
import Link from 'next/navigation';
import { ArrowRight, ShieldCheck, Sparkles, Database, Compass, BookOpen } from 'lucide-react';

export default function AboutPage() {
  return (
    <div className="container-editorial" style={{ paddingTop: '3.5rem', paddingBottom: '5rem' }}>
      {/* Title */}
      <div style={{ textAlign: 'center', marginBottom: '3.5rem' }}>
        <span
          style={{
            fontSize: '0.75rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: 'var(--color-accent-oxblood)',
          }}
        >
          Institutional Manifesto
        </span>
        <h1
          className="font-display"
          style={{
            fontSize: '3rem',
            fontWeight: 600,
            color: 'var(--color-ink-primary)',
            marginTop: '0.25rem',
          }}
        >
          On the Archive & Its Method
        </h1>
        <p
          style={{
            fontSize: '1.1rem',
            color: 'var(--color-ink-secondary)',
            maxWidth: '600px',
            margin: '0.75rem auto 0',
            lineHeight: 1.65,
            fontFamily: 'Cormorant Garamond, Georgia, serif',
            fontStyle: 'italic',
          }}
        >
          &ldquo;Preserving the fidelity of primary memory while unlocking connections across centuries through intelligent discovery.&rdquo;
        </p>
      </div>

      {/* Editorial Essay Sections */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '3rem', fontSize: '1.05rem', lineHeight: 1.75, color: 'var(--color-ink-primary)' }}>
        {/* Section I */}
        <section className="archival-panel" style={{ padding: '2.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Database size={20} color="var(--color-accent-oxblood)" />
            <h2 className="font-display" style={{ fontSize: '1.6rem', fontWeight: 600 }}>
              I. The Primacy of Original Sources
            </h2>
          </div>
          <p style={{ color: 'var(--color-ink-secondary)', marginBottom: '1rem' }}>
            Historical archives have long suffered from an unfortunate divide: they are either rigid, tabular database catalogs that resist exploration, or modern digital interfaces that summarize away the primary evidence.
          </p>
          <p style={{ color: 'var(--color-ink-secondary)' }}>
            The Intelligent Historical Archive operates under a strict principle of <strong>immutable provenance</strong>. Physical documents, high-resolution map scans, and full-length pamphlet PDFs are preserved in their authentic digital custody. Raw institutional metadata from the Internet Archive and Library of Congress is never overwritten or degraded.
          </p>
        </section>

        {/* Section II */}
        <section className="archival-panel" style={{ padding: '2.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Sparkles size={20} color="var(--color-accent-gold)" />
            <h2 className="font-display" style={{ fontSize: '1.6rem', fontWeight: 600 }}>
              II. Artificial Intelligence as an Editorial Lens
            </h2>
          </div>
          <p style={{ color: 'var(--color-ink-secondary)', marginBottom: '1rem' }}>
            We do not use artificial intelligence to generate speculative historical narratives or replace scholarly inquiry. Instead, AI serves strictly as a <strong>computational lens for discovery</strong>:
          </p>
          <ul style={{ paddingLeft: '1.5rem', color: 'var(--color-ink-secondary)', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <li>
              <strong>Dense Semantic Indexing</strong>: Google Gemini dense embeddings (768-dimensional float32 vectors stored natively in PostgreSQL pgvector) allow researchers to locate relevant paragraphs even when the query phrasing diverges from 19th-century vernacular.
            </li>
            <li>
              <strong>Entity Recognition & Categorization</strong>: Automated historical actor identification locates people, organizations, locations, and historical events across disparate holdings.
            </li>
            <li>
              <strong>Relational Knowledge Graphs</strong>: By identifying shared actors and documented correspondence, the archive maps latent historical networks that cross collection boundaries.
            </li>
          </ul>
        </section>

        {/* Section III */}
        <section className="archival-panel" style={{ padding: '2.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Compass size={20} color="var(--color-ink-primary)" />
            <h2 className="font-display" style={{ fontSize: '1.6rem', fontWeight: 600 }}>
              III. The Research Experience
            </h2>
          </div>
          <p style={{ color: 'var(--color-ink-secondary)', marginBottom: '1.5rem' }}>
            Every view within this platform is designed to answer a single impulse: <em>to discover another document, person, place, or event.</em> We invite scholars, students, and curious readers to begin with an inquiry and follow the thread of connected memory.
          </p>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <a href="/explore" className="btn-archival btn-oxblood">
              <span>Begin Exploration</span>
              <ArrowRight size={14} />
            </a>
            <a href="/connections" className="btn-archival btn-parchment">
              <span>Open Knowledge Graph</span>
            </a>
          </div>
        </section>
      </div>
    </div>
  );
}
