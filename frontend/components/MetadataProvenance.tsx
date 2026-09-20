'use client';

import React from 'react';
import { ShieldCheck, Sparkles, Database, ExternalLink, Calendar, MapPin, User, Tag, Hash } from 'lucide-react';
import { DocumentDetailResponse } from '../lib/api';

interface MetadataProvenanceProps {
  doc: DocumentDetailResponse;
}

export default function MetadataProvenance({ doc }: MetadataProvenanceProps) {
  const meta = doc.metadata;
  const aiMeta = meta?.ai_metadata || {};
  const creators = meta?.creators || [];
  const subjects = meta?.subjects || [];
  const locations = meta?.locations || [];
  const provenance = meta?.provenance?.[0] || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      {/* 1. Core Archival Metadata */}
      <section
        className="archival-panel"
        style={{
          padding: '1.4rem 1.6rem',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            borderBottom: '1px solid var(--color-paper-border)',
            paddingBottom: '0.65rem',
            marginBottom: '1rem',
          }}
        >
          <Database size={16} color="var(--color-ink-muted)" />
          <h3
            style={{
              fontSize: '0.85rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: 'var(--color-ink-primary)',
            }}
          >
            Original Archival Metadata
          </h3>
        </div>

        <dl
          style={{
            display: 'grid',
            gridTemplateColumns: '130px 1fr',
            rowGap: '0.75rem',
            columnGap: '1rem',
            fontSize: '0.875rem',
          }}
        >
          <dt style={{ color: 'var(--color-ink-muted)', fontWeight: 500 }}>Authors / Creators:</dt>
          <dd style={{ color: 'var(--color-ink-primary)', fontWeight: 600 }}>
            {creators.length > 0 ? creators.map((c) => c.name).join(', ') : 'Unknown / Unspecified'}
          </dd>

          <dt style={{ color: 'var(--color-ink-muted)', fontWeight: 500 }}>Publication Date:</dt>
          <dd style={{ color: 'var(--color-ink-primary)' }}>
            {meta?.date_raw || meta?.date_start || 'Circa 19th Century'}
            {meta?.date_is_circa ? ' (Circa)' : ''}
          </dd>

          <dt style={{ color: 'var(--color-ink-muted)', fontWeight: 500 }}>Repository:</dt>
          <dd style={{ color: 'var(--color-ink-primary)', textTransform: 'capitalize' }}>
            {doc.source?.replace('_', ' ')} (ID: {doc.source_id})
          </dd>

          <dt style={{ color: 'var(--color-ink-muted)', fontWeight: 500 }}>Format / Modality:</dt>
          <dd style={{ color: 'var(--color-ink-primary)', textTransform: 'capitalize' }}>
            {doc.record_type}
          </dd>

          <dt style={{ color: 'var(--color-ink-muted)', fontWeight: 500 }}>Language:</dt>
          <dd style={{ color: 'var(--color-ink-primary)' }}>
            {meta?.language || 'English'}
          </dd>

          {subjects.length > 0 && (
            <>
              <dt style={{ color: 'var(--color-ink-muted)', fontWeight: 500 }}>Archival Subjects:</dt>
              <dd style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                {subjects.map((s, i) => (
                  <span
                    key={i}
                    style={{
                      backgroundColor: 'var(--color-paper-base)',
                      border: '1px solid var(--color-paper-border)',
                      padding: '0.15rem 0.45rem',
                      borderRadius: 'var(--radius-xs)',
                      fontSize: '0.75rem',
                      color: 'var(--color-ink-secondary)',
                    }}
                  >
                    {s}
                  </span>
                ))}
              </dd>
            </>
          )}

          {doc.source_url && (
            <>
              <dt style={{ color: 'var(--color-ink-muted)', fontWeight: 500 }}>Source Record:</dt>
              <dd>
                <a
                  href={doc.source_url}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    color: 'var(--color-accent-oxblood)',
                    textDecoration: 'none',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.25rem',
                    fontSize: '0.8rem',
                  }}
                >
                  <span>View in Original Repository</span>
                  <ExternalLink size={13} />
                </a>
              </dd>
            </>
          )}
        </dl>
      </section>

      {/* 2. AI Enrichment & Provenance Envelope */}
      <section
        className="archival-panel"
        style={{
          padding: '1.4rem 1.6rem',
          backgroundColor: 'var(--color-accent-gold-subtle)',
          borderColor: 'var(--color-accent-gold-border)',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderBottom: '1px solid var(--color-accent-gold-border)',
            paddingBottom: '0.65rem',
            marginBottom: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Sparkles size={16} color="var(--color-accent-gold)" />
            <h3
              style={{
                fontSize: '0.85rem',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                color: 'var(--color-ink-primary)',
              }}
            >
              AI Enrichment & Provenance Lens
            </h3>
          </div>

          <span
            style={{
              fontSize: '0.7rem',
              fontWeight: 600,
              backgroundColor: '#FFFFFF',
              color: 'var(--color-accent-gold)',
              padding: '0.15rem 0.5rem',
              borderRadius: 'var(--radius-xs)',
              border: '1px solid var(--color-accent-gold-border)',
            }}
          >
            PROVENANCE: AI
          </span>
        </div>

        <dl
          style={{
            display: 'grid',
            gridTemplateColumns: '130px 1fr',
            rowGap: '0.75rem',
            columnGap: '1rem',
            fontSize: '0.875rem',
          }}
        >
          <dt style={{ color: 'var(--color-ink-muted)', fontWeight: 500 }}>Historical Period:</dt>
          <dd style={{ color: 'var(--color-ink-primary)', fontWeight: 600 }}>
            {aiMeta.historical_period || 'American Civil War'}
          </dd>

          <dt style={{ color: 'var(--color-ink-muted)', fontWeight: 500 }}>Standardized Title:</dt>
          <dd style={{ color: 'var(--color-ink-primary)' }}>
            {aiMeta.title || doc.title}
          </dd>

          <dt style={{ color: 'var(--color-ink-muted)', fontWeight: 500 }}>Model Attribution:</dt>
          <dd style={{ color: 'var(--color-ink-secondary)', fontFamily: 'monospace', fontSize: '0.8rem' }}>
            {provenance.provider || 'Gemini'} ({provenance.model || 'gemini-flash-lite-latest'})
          </dd>

          <dt style={{ color: 'var(--color-ink-muted)', fontWeight: 500 }}>Extraction Date:</dt>
          <dd style={{ color: 'var(--color-ink-secondary)', fontSize: '0.8rem' }}>
            {provenance.timestamp || '2026-09-20T15:42:20Z'}
          </dd>

          <dt style={{ color: 'var(--color-ink-muted)', fontWeight: 500 }}>Confidence Score:</dt>
          <dd style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div
              style={{
                width: '120px',
                height: '6px',
                backgroundColor: '#FFFFFF',
                borderRadius: '3px',
                overflow: 'hidden',
                border: '1px solid var(--color-accent-gold-border)',
              }}
            >
              <div
                style={{
                  width: `${Math.round((meta?.confidence || 0.95) * 100)}%`,
                  height: '100%',
                  backgroundColor: 'var(--color-accent-gold)',
                }}
              />
            </div>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-accent-gold)' }}>
              {Math.round((meta?.confidence || 0.95) * 100)}%
            </span>
          </dd>

          <dt style={{ color: 'var(--color-ink-muted)', fontWeight: 500 }}>Vector Dimensions:</dt>
          <dd style={{ color: 'var(--color-ink-secondary)', fontSize: '0.8rem' }}>
            768 float32 dense embeddings via pgvector
          </dd>
        </dl>
      </section>
    </div>
  );
}
