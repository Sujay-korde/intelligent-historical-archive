'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight, BookOpen, Map, FileText, Sparkles, ShieldCheck, Database, Layers } from 'lucide-react';
import ArchiveSearchInput from '../components/ArchiveSearchInput';
import { ArchiveStats, DocumentSummary, getArchiveStats, listDocuments } from '../lib/api';

export default function HomePage() {
  const router = useRouter();
  const [stats, setStats] = useState<ArchiveStats | null>(null);
  const [featuredDocs, setFeaturedDocs] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getArchiveStats().catch(() => null),
      listDocuments({ pageSize: 4, status: 'READY' }).catch(() => null),
    ]).then(([s, docsResp]) => {
      if (s) setStats(s);
      if (docsResp && docsResp.items) setFeaturedDocs(docsResp.items);
      setLoading(false);
    });
  }, []);

  const handleSearch = (query: string, searchType: string) => {
    router.push(`/explore?q=${encodeURIComponent(query)}&type=${searchType}`);
  };

  return (
    <div style={{ paddingBottom: '3rem' }}>
      {/* Editorial Masthead & Hero */}
      <section
        style={{
          padding: '4.5rem 1.5rem 3.5rem',
          textAlign: 'center',
          borderBottom: '1px solid var(--color-paper-border)',
          backgroundColor: 'var(--color-paper-base)',
        }}
      >
        <div className="container-editorial">
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              backgroundColor: 'var(--color-accent-gold-subtle)',
              color: 'var(--color-accent-gold)',
              border: '1px solid var(--color-accent-gold-border)',
              padding: '0.25rem 0.75rem',
              borderRadius: 'var(--radius-xs)',
              fontSize: '0.75rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              marginBottom: '1.5rem',
            }}
          >
            <Sparkles size={13} />
            <span>Connected Historical Intelligence</span>
          </div>

          <h1
            className="font-display"
            style={{
              fontSize: '3.4rem',
              fontWeight: 600,
              lineHeight: 1.15,
              color: 'var(--color-ink-primary)',
              letterSpacing: '-0.015em',
              maxWidth: '840px',
              margin: '0 auto 1.25rem',
            }}
          >
            History, connected. Knowledge, discoverable.
          </h1>

          <p
            style={{
              fontSize: '1.1rem',
              lineHeight: 1.65,
              color: 'var(--color-ink-secondary)',
              maxWidth: '660px',
              margin: '0 auto 2.5rem',
            }}
          >
            A living research archive connecting 19th-century speeches, abolitionist manuscripts, civil war records, and rare maps through dense semantic understanding and relational knowledge graphs.
          </p>

          {/* Prominent Archival Omnisearch */}
          <div style={{ maxWidth: '740px', margin: '0 auto' }}>
            <ArchiveSearchInput onSearch={handleSearch} showWeights={false} />
          </div>
        </div>
      </section>

      {/* Selected Curated Archival Objects */}
      <section className="container-research" style={{ marginTop: '3.5rem' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-end',
            marginBottom: '1.5rem',
            borderBottom: '1px solid var(--color-paper-border)',
            paddingBottom: '0.75rem',
          }}
        >
          <div>
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                color: 'var(--color-accent-oxblood)',
              }}
            >
              Primary Sources
            </span>
            <h2
              className="font-display"
              style={{
                fontSize: '2rem',
                fontWeight: 600,
                color: 'var(--color-ink-primary)',
                marginTop: '0.2rem',
              }}
            >
              Curated Archival Objects
            </h2>
          </div>

          <a
            href="/explore"
            style={{
              color: 'var(--color-accent-oxblood)',
              textDecoration: 'none',
              fontWeight: 600,
              fontSize: '0.9rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.3rem',
            }}
          >
            <span>View All Records</span>
            <ArrowRight size={15} />
          </a>
        </div>

        {/* Curated Cards Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '1.5rem',
          }}
        >
          {featuredDocs.length > 0 ? (
            featuredDocs.map((doc) => (
              <div
                key={doc.id}
                className="archival-card"
                style={{
                  padding: '1.5rem',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  minHeight: '220px',
                }}
              >
                <div>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      fontSize: '0.75rem',
                      color: 'var(--color-ink-muted)',
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                      marginBottom: '0.5rem',
                    }}
                  >
                    <span>{doc.record_type}</span>
                    <span>{doc.source?.replace('_', ' ')}</span>
                  </div>

                  <a
                    href={`/documents/${doc.id}`}
                    className="font-display"
                    style={{
                      fontSize: '1.3rem',
                      fontWeight: 600,
                      color: 'var(--color-ink-primary)',
                      textDecoration: 'none',
                      lineHeight: 1.3,
                      display: 'block',
                    }}
                  >
                    {doc.title}
                  </a>

                  {doc.description && (
                    <p
                      style={{
                        fontSize: '0.825rem',
                        color: 'var(--color-ink-secondary)',
                        marginTop: '0.4rem',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                        lineHeight: 1.5,
                      }}
                    >
                      {doc.description}
                    </p>
                  )}
                </div>

                <div style={{ paddingTop: '1rem', borderTop: '1px solid var(--color-paper-border)', marginTop: '1rem' }}>
                  <a
                    href={`/documents/${doc.id}`}
                    style={{
                      color: 'var(--color-accent-oxblood)',
                      textDecoration: 'none',
                      fontSize: '0.825rem',
                      fontWeight: 600,
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.3rem',
                    }}
                  >
                    <span>Examine Artifact</span>
                    <ArrowRight size={13} />
                  </a>
                </div>
              </div>
            ))
          ) : (
            /* Fallback Curated Items if initial load */
            <>
              <div className="archival-card" style={{ padding: '1.5rem' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-ink-muted)', textTransform: 'uppercase' }}>
                  BOOK • INTERNET ARCHIVE
                </div>
                <h3 className="font-display" style={{ fontSize: '1.3rem', margin: '0.4rem 0' }}>
                  The War for the Union
                </h3>
                <p style={{ fontSize: '0.825rem', color: 'var(--color-ink-secondary)', lineHeight: 1.5 }}>
                  Henry Ward Beecher&apos;s historic 1885 lecture delivered at the Brooklyn Academy of Music.
                </p>
                <a href="/explore?q=Beecher" style={{ color: 'var(--color-accent-oxblood)', fontSize: '0.825rem', fontWeight: 600, marginTop: '1rem', display: 'inline-block' }}>
                  Explore Document →
                </a>
              </div>
              <div className="archival-card" style={{ padding: '1.5rem' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-ink-muted)', textTransform: 'uppercase' }}>
                  BIOGRAPHY • INTERNET ARCHIVE
                </div>
                <h3 className="font-display" style={{ fontSize: '1.3rem', margin: '0.4rem 0' }}>
                  Life of Abraham Lincoln
                </h3>
                <p style={{ fontSize: '0.825rem', color: 'var(--color-ink-secondary)', lineHeight: 1.5 }}>
                  Public services, state papers, and speeches during the American Civil War by Henry J. Raymond.
                </p>
                <a href="/explore?q=Lincoln" style={{ color: 'var(--color-accent-oxblood)', fontSize: '0.825rem', fontWeight: 600, marginTop: '1rem', display: 'inline-block' }}>
                  Explore Document →
                </a>
              </div>
              <div className="archival-card" style={{ padding: '1.5rem' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-ink-muted)', textTransform: 'uppercase' }}>
                  MAP • ARCHIVKOPIA
                </div>
                <h3 className="font-display" style={{ fontSize: '1.3rem', margin: '0.4rem 0' }}>
                  Historical Scandinavian Cartography
                </h3>
                <p style={{ fontSize: '0.825rem', color: 'var(--color-ink-secondary)', lineHeight: 1.5 }}>
                  Rare 18th-century Swedish regional map scans processed via OCR with coordinate metadata.
                </p>
                <a href="/explore?q=map" style={{ color: 'var(--color-accent-oxblood)', fontSize: '0.825rem', fontWeight: 600, marginTop: '1rem', display: 'inline-block' }}>
                  Explore Document →
                </a>
              </div>
            </>
          )}
        </div>
      </section>

      {/* Collection Scope & Integrity Highlights */}
      <section
        className="container-research"
        style={{
          marginTop: '4.5rem',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '2rem',
        }}
      >
        <div className="archival-panel" style={{ padding: '1.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <Database size={18} color="var(--color-accent-oxblood)" />
            <h3 className="font-display" style={{ fontSize: '1.3rem', fontWeight: 600 }}>
              Archival Scope & Custody
            </h3>
          </div>
          <p style={{ fontSize: '0.875rem', color: 'var(--color-ink-secondary)', lineHeight: 1.6 }}>
            Connected directly to institutional archives including the Internet Archive and Library of Congress, preserving original catalog numbers, dates, formats, and high-resolution digital facsimiles.
          </p>
          <div style={{ display: 'flex', gap: '1.5rem', marginTop: '1rem', fontSize: '0.8rem', color: 'var(--color-ink-muted)' }}>
            <span><strong>{stats?.documents || 2}</strong> Documents</span>
            <span><strong>{stats?.chunks || 5}</strong> Semantic Chunks</span>
            <span><strong>{stats?.entities || 2}</strong> Historical Actors</span>
          </div>
        </div>

        <div className="archival-panel" style={{ padding: '1.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <Layers size={18} color="var(--color-accent-gold)" />
            <h3 className="font-display" style={{ fontSize: '1.3rem', fontWeight: 600 }}>
              Relational Knowledge Graphs
            </h3>
          </div>
          <p style={{ fontSize: '0.875rem', color: 'var(--color-ink-secondary)', lineHeight: 1.6 }}>
            Historical entities are not isolated rows in a table. Explore how Abraham Lincoln, Henry Ward Beecher, Boston, and Fort Sumter connect through verified correspondence and citations.
          </p>
          <a
            href="/connections"
            style={{
              color: 'var(--color-accent-oxblood)',
              fontSize: '0.825rem',
              fontWeight: 600,
              textDecoration: 'none',
              marginTop: '1rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.3rem',
            }}
          >
            <span>Launch Knowledge Graph</span>
            <ArrowRight size={13} />
          </a>
        </div>
      </section>
    </div>
  );
}
