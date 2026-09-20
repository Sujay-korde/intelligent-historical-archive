'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, BookOpen, Layers, Sparkles, ExternalLink, Calendar, User, Tag, Share2 } from 'lucide-react';
import ArchivalViewer from '../../../components/ArchivalViewer';
import MetadataProvenance from '../../../components/MetadataProvenance';
import RecommendationCard from '../../../components/RecommendationCard';
import {
  DocumentDetailResponse,
  getDocumentDetail,
  getRecommendations,
  RecommendedDocumentItem,
} from '../../../lib/api';

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const documentId = (params?.id as string) || '';

  const [doc, setDoc] = useState<DocumentDetailResponse | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendedDocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!documentId) return;
    setLoading(true);
    setError(null);

    Promise.all([
      getDocumentDetail(documentId),
      getRecommendations(documentId, 4).catch(() => ({ recommendations: [] })),
    ])
      .then(([docData, recData]) => {
        setDoc(docData);
        if (recData && recData.recommendations) {
          setRecommendations(recData.recommendations);
        }
      })
      .catch((err: any) => {
        console.error('Failed to load document:', err);
        setError(err.message || 'Archival document not found.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [documentId]);

  if (loading) {
    return (
      <div className="container-editorial" style={{ paddingTop: '3rem', paddingBottom: '5rem' }}>
        <div className="shimmer" style={{ height: '40px', width: '60%', marginBottom: '1.5rem' }} />
        <div className="shimmer" style={{ height: '500px', width: '100%', marginBottom: '2rem' }} />
        <div className="shimmer" style={{ height: '200px', width: '100%' }} />
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div className="container-editorial" style={{ paddingTop: '4rem', textAlign: 'center' }}>
        <h2 className="font-display" style={{ fontSize: '2rem', color: 'var(--color-accent-oxblood)' }}>
          Archival Record Unavailable
        </h2>
        <p style={{ color: 'var(--color-ink-muted)', margin: '1rem 0 2rem' }}>
          {error || 'Unable to locate the specified historical record.'}
        </p>
        <button
          type="button"
          onClick={() => router.push('/explore')}
          className="btn-archival btn-oxblood"
        >
          Return to Explore
        </button>
      </div>
    );
  }

  const creators = doc.metadata?.creators || [];
  const authorName = creators.map((c) => c.name).join(', ') || 'Archival Record';
  const pubDate = doc.metadata?.date_raw || doc.metadata?.date_start || '19th Century';

  return (
    <div className="container-research" style={{ paddingTop: '2rem', paddingBottom: '5rem' }}>
      {/* Back Navigation Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.5rem',
          fontSize: '0.825rem',
          color: 'var(--color-ink-muted)',
        }}
      >
        <button
          type="button"
          onClick={() => router.back()}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--color-accent-oxblood)',
            fontWeight: 500,
            fontSize: '0.85rem',
          }}
        >
          <ArrowLeft size={15} />
          <span>Back to Explore Results</span>
        </button>

        <div>
          <span>Archival Reference: </span>
          <strong style={{ fontFamily: 'monospace', color: 'var(--color-ink-primary)' }}>
            {doc.source}:{doc.source_id}
          </strong>
        </div>
      </div>

      {/* Document Hero Header */}
      <div style={{ marginBottom: '2.5rem' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.6rem',
            fontSize: '0.8rem',
            color: 'var(--color-ink-muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            marginBottom: '0.4rem',
          }}
        >
          <span style={{ fontWeight: 600, color: 'var(--color-accent-oxblood)' }}>
            {doc.record_type}
          </span>
          <span>•</span>
          <span>{doc.source?.replace('_', ' ')}</span>
          <span>•</span>
          <span>{pubDate}</span>
        </div>

        <h1
          className="font-display"
          style={{
            fontSize: '2.6rem',
            fontWeight: 600,
            lineHeight: 1.2,
            color: 'var(--color-ink-primary)',
            maxWidth: '960px',
          }}
        >
          {doc.title}
        </h1>

        <p
          style={{
            fontSize: '1.1rem',
            color: 'var(--color-ink-secondary)',
            marginTop: '0.5rem',
            fontStyle: 'italic',
            fontFamily: 'Cormorant Garamond, serif',
          }}
        >
          Authored by {authorName}
        </p>
      </div>

      {/* Main 2-Column Split: Hero Scan Viewer (55%) vs Metadata & Provenance (45%) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 1fr)',
          gap: '2.5rem',
          alignItems: 'start',
        }}
      >
        {/* Left: Archival Viewer */}
        <div>
          <ArchivalViewer
            title={doc.title}
            recordType={doc.record_type}
            mediaAssets={doc.media_assets}
            sourceUrl={doc.source_url}
            extractedTextPreview={doc.description || ''}
          />

          {/* Local Knowledge Graph Action Link */}
          <div
            style={{
              marginTop: '1.25rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '1rem 1.25rem',
              backgroundColor: 'var(--color-paper-surface)',
              border: '1px solid var(--color-paper-border)',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Layers size={18} color="var(--color-accent-oxblood)" />
              <div>
                <strong style={{ fontSize: '0.85rem', color: 'var(--color-ink-primary)', display: 'block' }}>
                  Explore Document Knowledge Network
                </strong>
                <span style={{ fontSize: '0.75rem', color: 'var(--color-ink-muted)' }}>
                  Inspect historical correspondence, mentions, and shared actors
                </span>
              </div>
            </div>

            <a
              href={`/connections?document_id=${doc.id}`}
              className="btn-archival btn-oxblood"
              style={{ fontSize: '0.8rem', padding: '0.45rem 0.85rem' }}
            >
              Open Network Graph →
            </a>
          </div>
        </div>

        {/* Right: Metadata & Provenance Rail */}
        <div>
          <MetadataProvenance doc={doc} />
        </div>
      </div>

      {/* "Continue Exploring" Related Archival Documents Carousel */}
      {recommendations.length > 0 && (
        <section style={{ marginTop: '5rem', borderTop: '1px solid var(--color-paper-border)', paddingTop: '2.5rem' }}>
          <div style={{ marginBottom: '1.5rem' }}>
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                color: 'var(--color-accent-oxblood)',
              }}
            >
              Related Archival Artifacts
            </span>
            <h2
              className="font-display"
              style={{
                fontSize: '1.8rem',
                fontWeight: 600,
                color: 'var(--color-ink-primary)',
                marginTop: '0.2rem',
              }}
            >
              Continue Exploring Connected Records
            </h2>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
              gap: '1.5rem',
            }}
          >
            {recommendations.map((rec, i) => (
              <RecommendationCard key={i} item={rec} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
