'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/navigation';
import { BookOpen, Map, FileText, ExternalLink, ArrowRight, Database, CheckCircle2, AlertCircle } from 'lucide-react';
import { ArchiveStats, getArchiveStats } from '../../lib/api';

export default function CollectionsPage() {
  const [stats, setStats] = useState<ArchiveStats | null>(null);

  useEffect(() => {
    getArchiveStats().then(setStats).catch(() => null);
  }, []);

  return (
    <div className="container-editorial" style={{ paddingTop: '3rem', paddingBottom: '5rem' }}>
      {/* Header */}
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
          Curated Holdings
        </span>
        <h1
          className="font-display"
          style={{
            fontSize: '2.8rem',
            fontWeight: 600,
            color: 'var(--color-ink-primary)',
            marginTop: '0.25rem',
          }}
        >
          Archival Repositories & Collections
        </h1>
        <p
          style={{
            fontSize: '1.05rem',
            color: 'var(--color-ink-secondary)',
            maxWidth: '620px',
            margin: '0.75rem auto 0',
            lineHeight: 1.6,
          }}
        >
          Explore digitized primary holdings organized by institutional partner custody and historical thematic corpora.
        </p>
      </div>

      {/* Institutional Partners */}
      <section style={{ marginBottom: '4rem' }}>
        <h2
          className="font-display"
          style={{
            fontSize: '1.6rem',
            fontWeight: 600,
            color: 'var(--color-ink-primary)',
            borderBottom: '1px solid var(--color-paper-border)',
            paddingBottom: '0.5rem',
            marginBottom: '1.5rem',
          }}
        >
          Connected Institutional Partners
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
          {/* Internet Archive */}
          <div className="archival-panel" style={{ padding: '1.75rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
                  archive.org
                </span>
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.3rem',
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    color: '#2D8A4E',
                    backgroundColor: '#EAF0EC',
                    padding: '0.15rem 0.5rem',
                    borderRadius: 'var(--radius-xs)',
                  }}
                >
                  <CheckCircle2 size={12} />
                  100% Active & Ingested
                </span>
              </div>

              <h3 className="font-display" style={{ fontSize: '1.4rem', fontWeight: 600 }}>
                Internet Archive
              </h3>
              <p style={{ fontSize: '0.875rem', color: 'var(--color-ink-secondary)', lineHeight: 1.6, marginTop: '0.5rem' }}>
                Universal digital library preserving historical books, orations, tracts, and broadcast recordings. Our ingestion pipeline streams original PDFs, extracts ligatures via PyMuPDF, and indexes dense 768d vectors into pgvector.
              </p>
            </div>

            <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--color-paper-border)' }}>
              <a
                href="/explore?q=internet_archive"
                className="btn-archival btn-oxblood"
                style={{ width: '100%', fontSize: '0.825rem' }}
              >
                <span>Browse Internet Archive Records ({stats?.sources?.internet_archive || 2})</span>
                <ArrowRight size={14} />
              </a>
            </div>
          </div>

          {/* Library of Congress */}
          <div className="archival-panel" style={{ padding: '1.75rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
                  loc.gov
                </span>
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.3rem',
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    color: '#997530',
                    backgroundColor: '#F8F3E8',
                    padding: '0.15rem 0.5rem',
                    borderRadius: 'var(--radius-xs)',
                  }}
                >
                  <AlertCircle size={12} />
                  Rate-Controlled Provider
                </span>
              </div>

              <h3 className="font-display" style={{ fontSize: '1.4rem', fontWeight: 600 }}>
                Library of Congress
              </h3>
              <p style={{ fontSize: '0.875rem', color: 'var(--color-ink-secondary)', lineHeight: 1.6, marginTop: '0.5rem' }}>
                The premier national research archive housing rare manuscripts, American memory collections, photographic plates, and historical cartography.
              </p>
            </div>

            <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--color-paper-border)' }}>
              <a
                href="/explore?q=Library+of+Congress"
                className="btn-archival btn-parchment"
                style={{ width: '100%', fontSize: '0.825rem' }}
              >
                <span>Explore LoC Holdings Catalog</span>
                <ArrowRight size={14} />
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Thematic Historical Archives */}
      <section>
        <h2
          className="font-display"
          style={{
            fontSize: '1.6rem',
            fontWeight: 600,
            color: 'var(--color-ink-primary)',
            borderBottom: '1px solid var(--color-paper-border)',
            paddingBottom: '0.5rem',
            marginBottom: '1.5rem',
          }}
        >
          Thematic Archives
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
          {[
            {
              title: 'American Civil War Orations & Papers',
              desc: 'Addresses, pamphlets, and military correspondence between Union statesmen and clergymen from 1861 to 1885.',
              icon: BookOpen,
              query: 'Civil War',
              tag: '14 Records',
            },
            {
              title: 'Historical Scandinavian Cartography',
              desc: 'Rare 18th-century regional maps of Sweden and the Baltic sea, scanned at high resolution with OCR coordinate recognition.',
              icon: Map,
              query: 'map',
              tag: '4 Map Scans',
            },
            {
              title: 'The Abolitionist Movement & Press',
              desc: 'Anti-slavery broadsides, leaflets, and personal correspondence chronicling the struggle for emancipation.',
              icon: FileText,
              query: 'abolition',
              tag: '6 Manuscripts',
            },
          ].map((theme, i) => {
            const Icon = theme.icon;
            return (
              <div
                key={i}
                className="archival-card"
                style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <Icon size={18} color="var(--color-accent-oxblood)" />
                    <span style={{ fontSize: '0.75rem', color: 'var(--color-ink-muted)' }}>{theme.tag}</span>
                  </div>
                  <h3 className="font-display" style={{ fontSize: '1.25rem', fontWeight: 600 }}>
                    {theme.title}
                  </h3>
                  <p style={{ fontSize: '0.825rem', color: 'var(--color-ink-secondary)', lineHeight: 1.5, marginTop: '0.4rem' }}>
                    {theme.desc}
                  </p>
                </div>

                <a
                  href={`/explore?q=${encodeURIComponent(theme.query)}`}
                  style={{
                    color: 'var(--color-accent-oxblood)',
                    fontSize: '0.825rem',
                    fontWeight: 600,
                    textDecoration: 'none',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.3rem',
                    marginTop: '1.25rem',
                  }}
                >
                  <span>Explore Collection</span>
                  <ArrowRight size={13} />
                </a>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
