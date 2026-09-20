'use client';

import React from 'react';
import Link from 'next/navigation';
import { BookOpen, Sparkles, ArrowRight, Layers } from 'lucide-react';
import { RecommendedDocumentItem } from '../lib/api';

interface RecommendationCardProps {
  item: RecommendedDocumentItem;
}

export default function RecommendationCard({ item }: RecommendationCardProps) {
  const doc = item.document;
  const matchPercent = Math.round(item.score * 100);

  return (
    <div
      className="archival-card"
      style={{
        padding: '1.25rem 1.4rem',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        gap: '0.8rem',
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
            marginBottom: '0.4rem',
          }}
        >
          <span style={{ textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>
            {doc.record_type} • {doc.source?.replace('_', ' ')}
          </span>
          <span
            style={{
              backgroundColor: 'var(--color-accent-gold-subtle)',
              color: 'var(--color-accent-gold)',
              border: '1px solid var(--color-accent-gold-border)',
              padding: '0.15rem 0.45rem',
              borderRadius: 'var(--radius-xs)',
              fontWeight: 600,
            }}
          >
            {matchPercent}% Proximity
          </span>
        </div>

        <a
          href={`/documents/${doc.id}`}
          className="font-display"
          style={{
            fontSize: '1.15rem',
            fontWeight: 600,
            color: 'var(--color-ink-primary)',
            textDecoration: 'none',
            display: 'block',
            lineHeight: 1.3,
          }}
        >
          {doc.title}
        </a>

        {item.explanation && (
          <p
            style={{
              fontSize: '0.8rem',
              color: 'var(--color-ink-secondary)',
              marginTop: '0.4rem',
              lineHeight: 1.45,
            }}
          >
            {item.explanation}
          </p>
        )}
      </div>

      <div>
        {item.shared_entities && item.shared_entities.length > 0 && (
          <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
            {item.shared_entities.map((name, i) => (
              <span
                key={i}
                className="entity-badge entity-person"
                style={{ fontSize: '0.7rem' }}
              >
                {name}
              </span>
            ))}
          </div>
        )}

        <a
          href={`/documents/${doc.id}`}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.3rem',
            fontSize: '0.8rem',
            fontWeight: 600,
            color: 'var(--color-accent-oxblood)',
            textDecoration: 'none',
          }}
        >
          <span>Examine Artifact</span>
          <ArrowRight size={13} />
        </a>
      </div>
    </div>
  );
}
