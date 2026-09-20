'use client';

import React from 'react';
import Link from 'next/navigation';
import { BookOpen, FileText, Map, User, Calendar, ExternalLink, ArrowUpRight, Sparkles } from 'lucide-react';
import { SearchResultItem } from '../lib/api';

interface SearchResultCardProps {
  item: SearchResultItem;
  highlightQuery?: string;
}

export default function SearchResultCard({ item, highlightQuery = '' }: SearchResultCardProps) {
  const doc = item.document;
  const preview = item.available_preview_information;
  const scorePercent = Math.round(item.relevance_score * 100);

  // Snippet text highlighter helper
  const renderSnippet = (text: string) => {
    if (!highlightQuery || !text) return text;
    const terms = highlightQuery
      .toLowerCase()
      .split(/\s+/)
      .filter((t) => t.length > 2);
    if (!terms.length) return text;

    const pattern = new RegExp(`(${terms.join('|')})`, 'gi');
    const parts = text.split(pattern);

    return parts.map((part, i) =>
      terms.includes(part.toLowerCase()) ? (
        <mark
          key={i}
          style={{
            backgroundColor: 'var(--color-accent-gold-subtle)',
            color: 'var(--color-ink-primary)',
            fontWeight: 600,
            padding: '0 2px',
            borderRadius: '2px',
            borderBottom: '1px solid var(--color-accent-gold-border)',
          }}
        >
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  const getFormatIcon = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'map':
      case 'cartography':
        return <Map size={14} />;
      case 'manuscript':
        return <FileText size={14} />;
      default:
        return <BookOpen size={14} />;
    }
  };

  const getEntityClass = (type?: string | null) => {
    switch (type?.toUpperCase()) {
      case 'PERSON':
        return 'entity-person';
      case 'LOCATION':
        return 'entity-location';
      case 'EVENT':
        return 'entity-event';
      case 'ORGANIZATION':
        return 'entity-org';
      default:
        return 'entity-topic';
    }
  };

  return (
    <article
      className="archival-card"
      style={{
        padding: '1.4rem 1.6rem',
        marginBottom: '1rem',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
      }}
    >
      {/* Top Meta Line: Format, Source, Score */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '0.75rem',
          color: 'var(--color-ink-muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.3rem',
              fontWeight: 600,
              color: 'var(--color-ink-secondary)',
            }}
          >
            {getFormatIcon(doc.record_type)}
            {doc.record_type || 'DOCUMENT'}
          </span>
          <span>•</span>
          <span>{doc.source?.replace('_', ' ') || 'ARCHIVE'}</span>
          {item.page_number && (
            <>
              <span>•</span>
              <span>Page {item.page_number}</span>
            </>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span
            style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              color: 'var(--color-accent-oxblood)',
              backgroundColor: 'var(--color-accent-oxblood-subtle)',
              padding: '0.15rem 0.5rem',
              borderRadius: 'var(--radius-xs)',
            }}
          >
            {scorePercent}% Match
          </span>
        </div>
      </div>

      {/* Document Title */}
      <div>
        <a
          href={`/documents/${doc.id}`}
          className="font-display"
          style={{
            fontSize: '1.35rem',
            fontWeight: 600,
            color: 'var(--color-ink-primary)',
            textDecoration: 'none',
            lineHeight: 1.3,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
          }}
        >
          <span>{doc.title}</span>
          <ArrowUpRight size={16} color="var(--color-accent-oxblood)" />
        </a>
        {doc.description && (
          <p
            style={{
              fontSize: '0.85rem',
              color: 'var(--color-ink-muted)',
              marginTop: '0.2rem',
              display: '-webkit-box',
              WebkitLineClamp: 1,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
          >
            {doc.description}
          </p>
        )}
      </div>

      {/* Matching Snippet with Highlighting */}
      {item.matching_snippet && (
        <div
          style={{
            backgroundColor: 'var(--color-paper-base)',
            borderLeft: '3px solid var(--color-paper-border-dark)',
            padding: '0.65rem 0.9rem',
            fontSize: '0.875rem',
            color: 'var(--color-ink-secondary)',
            lineHeight: 1.55,
            fontFamily: 'Inter, sans-serif',
          }}
        >
          &ldquo;{renderSnippet(item.matching_snippet)}&rdquo;
        </div>
      )}

      {/* Associated Knowledge Entities */}
      {item.entities && item.entities.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--color-ink-muted)' }}>Entities:</span>
          {item.entities.slice(0, 6).map((ent, idx) => (
            <a
              key={idx}
              href={`/connections?focus=${encodeURIComponent(ent.name)}`}
              className={`entity-badge ${getEntityClass(ent.entity_type)}`}
              title={`View ${ent.name} in Knowledge Graph`}
            >
              <span>{ent.name}</span>
              {ent.entity_type && (
                <span style={{ opacity: 0.7, fontSize: '0.65rem' }}>({ent.entity_type})</span>
              )}
            </a>
          ))}
        </div>
      )}

      {/* Match Explanation Context */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingTop: '0.5rem',
          borderTop: '1px solid var(--color-paper-border)',
          fontSize: '0.75rem',
          color: 'var(--color-ink-muted)',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <Sparkles size={13} color="var(--color-accent-gold)" />
          {item.relevance_explanation || 'Ranked using unified Reciprocal Rank Fusion'}
        </span>

        <a
          href={`/documents/${doc.id}`}
          style={{
            color: 'var(--color-accent-oxblood)',
            textDecoration: 'none',
            fontWeight: 600,
            fontSize: '0.8rem',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.2rem',
          }}
        >
          View Research Document →
        </a>
      </div>
    </article>
  );
}
