'use client';

import React, { useState } from 'react';
import { Search, Sparkles, Filter, SlidersHorizontal, ArrowRight, X } from 'lucide-react';

interface ArchiveSearchInputProps {
  initialQuery?: string;
  initialType?: 'hybrid' | 'semantic' | 'keyword';
  onSearch: (query: string, searchType: 'hybrid' | 'semantic' | 'keyword', semanticWeight: number, keywordWeight: number) => void;
  showWeights?: boolean;
}

export default function ArchiveSearchInput({
  initialQuery = '',
  initialType = 'hybrid',
  onSearch,
  showWeights = true,
}: ArchiveSearchInputProps) {
  const [query, setQuery] = useState(initialQuery);
  const [searchType, setSearchType] = useState<'hybrid' | 'semantic' | 'keyword'>(initialType);
  const [semanticWeight, setSemanticWeight] = useState(0.7);
  const [showFilters, setShowFilters] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim(), searchType, semanticWeight, 1.0 - semanticWeight);
    }
  };

  const handleSuggestion = (s: string) => {
    setQuery(s);
    onSearch(s, searchType, semanticWeight, 1.0 - semanticWeight);
  };

  return (
    <div style={{ width: '100%' }}>
      <form onSubmit={handleSubmit} style={{ position: 'relative' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            backgroundColor: '#FFFFFF',
            border: '1.5px solid var(--color-paper-border)',
            borderRadius: 'var(--radius-sm)',
            boxShadow: 'var(--shadow-sm)',
            padding: '0.4rem 0.6rem 0.4rem 1rem',
            transition: 'border-color 0.2s',
          }}
        >
          <Search size={20} color="var(--color-ink-muted)" style={{ marginRight: '0.75rem', flexShrink: 0 }} />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search speeches, correspondents, historical events, manuscripts..."
            style={{
              width: '100%',
              border: 'none',
              outline: 'none',
              fontSize: '1.05rem',
              fontFamily: 'Inter, sans-serif',
              backgroundColor: 'transparent',
              color: 'var(--color-ink-primary)',
            }}
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--color-ink-muted)',
                padding: '0.2rem',
                marginRight: '0.5rem',
              }}
            >
              <X size={16} />
            </button>
          )}
          <button
            type="submit"
            className="btn-archival btn-oxblood"
            style={{ padding: '0.65rem 1.4rem', fontSize: '0.9rem', flexShrink: 0 }}
          >
            <span>Search</span>
            <ArrowRight size={15} />
          </button>
        </div>

        {/* Mode Selector & Weight Controls */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginTop: '0.6rem',
            fontSize: '0.8rem',
            color: 'var(--color-ink-secondary)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ fontWeight: 500, color: 'var(--color-ink-muted)' }}>Retrieval Mode:</span>
            {[
              { id: 'hybrid', label: 'Hybrid (RRF)', desc: 'Fused AI + Exact' },
              { id: 'semantic', label: 'Semantic AI', desc: 'Dense 768d Vector' },
              { id: 'keyword', label: 'Exact Keyword', desc: 'PostgreSQL Full-Text' },
            ].map((mode) => (
              <label
                key={mode.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  cursor: 'pointer',
                  fontWeight: searchType === mode.id ? 600 : 400,
                  color: searchType === mode.id ? 'var(--color-accent-oxblood)' : 'var(--color-ink-secondary)',
                }}
              >
                <input
                  type="radio"
                  name="searchType"
                  value={mode.id}
                  checked={searchType === mode.id}
                  onChange={() => setSearchType(mode.id as any)}
                  style={{ accentColor: 'var(--color-accent-oxblood)' }}
                />
                {mode.label}
              </label>
            ))}
          </div>

          {showWeights && searchType === 'hybrid' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--color-ink-muted)' }}>
                Signal Bias: {Math.round(semanticWeight * 100)}% AI / {Math.round((1 - semanticWeight) * 100)}% Exact
              </span>
              <input
                type="range"
                min="0.1"
                max="0.9"
                step="0.1"
                value={semanticWeight}
                onChange={(e) => setSemanticWeight(parseFloat(e.target.value))}
                style={{ width: '80px', accentColor: 'var(--color-accent-oxblood)', cursor: 'pointer' }}
              />
            </div>
          )}
        </div>
      </form>

      {/* Suggested Queries */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          flexWrap: 'wrap',
          marginTop: '0.75rem',
          fontSize: '0.8rem',
        }}
      >
        <span style={{ color: 'var(--color-ink-muted)', fontStyle: 'italic' }}>Suggested Inquiries:</span>
        {[
          'Civil War union speech',
          'Henry Ward Beecher',
          'Abraham Lincoln public services',
          'Swedish historical maps',
          'Abolitionist manuscripts',
        ].map((tag) => (
          <button
            key={tag}
            type="button"
            onClick={() => handleSuggestion(tag)}
            style={{
              background: 'var(--color-paper-surface)',
              border: '1px solid var(--color-paper-border)',
              borderRadius: 'var(--radius-xs)',
              padding: '0.2rem 0.55rem',
              fontSize: '0.75rem',
              color: 'var(--color-ink-secondary)',
              cursor: 'pointer',
              transition: 'background 0.15s',
            }}
          >
            {tag}
          </button>
        ))}
      </div>
    </div>
  );
}
