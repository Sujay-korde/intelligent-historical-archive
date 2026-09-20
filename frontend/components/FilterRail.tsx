'use client';

import React from 'react';
import { Filter, RotateCcw, Calendar, CheckSquare, Square } from 'lucide-react';

export interface FilterState {
  source?: string;
  record_type?: string;
  historical_period?: string;
  entity_name?: string;
  date_start?: string;
  date_end?: string;
}

interface FilterRailProps {
  filters: FilterState;
  onChange: (newFilters: FilterState) => void;
  facets?: Record<string, any>;
  totalResults?: number;
}

export default function FilterRail({
  filters,
  onChange,
  facets = {},
  totalResults,
}: FilterRailProps) {
  const handleToggle = (key: keyof FilterState, value: string) => {
    if (filters[key] === value) {
      const next = { ...filters };
      delete next[key];
      onChange(next);
    } else {
      onChange({ ...filters, [key]: value });
    }
  };

  const handleReset = () => {
    onChange({});
  };

  const hasActiveFilters = Object.values(filters).some(Boolean);

  return (
    <aside
      className="archival-panel"
      style={{
        padding: '1.25rem 1.4rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid var(--color-paper-border)',
          paddingBottom: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Filter size={16} color="var(--color-accent-oxblood)" />
          <span
            style={{
              fontSize: '0.875rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              color: 'var(--color-ink-primary)',
            }}
          >
            Refine Archive
          </span>
        </div>

        {hasActiveFilters && (
          <button
            type="button"
            onClick={handleReset}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--color-accent-oxblood)',
              fontSize: '0.75rem',
              fontWeight: 500,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.25rem',
            }}
          >
            <RotateCcw size={12} />
            Reset
          </button>
        )}
      </div>

      {/* Archival Source Repository */}
      <div>
        <h4
          style={{
            fontSize: '0.8rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--color-ink-muted)',
            marginBottom: '0.6rem',
          }}
        >
          Archival Custody
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          {[
            { id: 'internet_archive', label: 'Internet Archive' },
            { id: 'library_of_congress', label: 'Library of Congress' },
          ].map((src) => {
            const isSelected = filters.source === src.id;
            return (
              <button
                key={src.id}
                type="button"
                onClick={() => handleToggle('source', src.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  background: isSelected ? 'var(--color-paper-elevated)' : 'transparent',
                  border: 'none',
                  padding: '0.3rem 0.4rem',
                  borderRadius: 'var(--radius-xs)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '0.825rem',
                  color: isSelected ? 'var(--color-accent-oxblood)' : 'var(--color-ink-secondary)',
                  fontWeight: isSelected ? 600 : 400,
                }}
              >
                {isSelected ? (
                  <CheckSquare size={14} color="var(--color-accent-oxblood)" />
                ) : (
                  <Square size={14} color="var(--color-paper-border-dark)" />
                )}
                <span>{src.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Historical Period */}
      <div>
        <h4
          style={{
            fontSize: '0.8rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--color-ink-muted)',
            marginBottom: '0.6rem',
          }}
        >
          Historical Period
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          {[
            'American Civil War',
            'Antebellum America',
            'Reconstruction Era',
            '18th Century Nordic',
          ].map((period) => {
            const isSelected = filters.historical_period === period;
            return (
              <button
                key={period}
                type="button"
                onClick={() => handleToggle('historical_period', period)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  background: isSelected ? 'var(--color-paper-elevated)' : 'transparent',
                  border: 'none',
                  padding: '0.3rem 0.4rem',
                  borderRadius: 'var(--radius-xs)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '0.825rem',
                  color: isSelected ? 'var(--color-accent-oxblood)' : 'var(--color-ink-secondary)',
                  fontWeight: isSelected ? 600 : 400,
                }}
              >
                {isSelected ? (
                  <CheckSquare size={14} color="var(--color-accent-oxblood)" />
                ) : (
                  <Square size={14} color="var(--color-paper-border-dark)" />
                )}
                <span>{period}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Record Format / Modality */}
      <div>
        <h4
          style={{
            fontSize: '0.8rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--color-ink-muted)',
            marginBottom: '0.6rem',
          }}
        >
          Record Format
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          {[
            { id: 'book', label: 'Book / Pamphlet' },
            { id: 'manuscript', label: 'Manuscript' },
            { id: 'map', label: 'Cartographic Map' },
            { id: 'audio', label: 'Historical Audio' },
          ].map((fmt) => {
            const isSelected = filters.record_type === fmt.id;
            return (
              <button
                key={fmt.id}
                type="button"
                onClick={() => handleToggle('record_type', fmt.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  background: isSelected ? 'var(--color-paper-elevated)' : 'transparent',
                  border: 'none',
                  padding: '0.3rem 0.4rem',
                  borderRadius: 'var(--radius-xs)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '0.825rem',
                  color: isSelected ? 'var(--color-accent-oxblood)' : 'var(--color-ink-secondary)',
                  fontWeight: isSelected ? 600 : 400,
                }}
              >
                {isSelected ? (
                  <CheckSquare size={14} color="var(--color-accent-oxblood)" />
                ) : (
                  <Square size={14} color="var(--color-paper-border-dark)" />
                )}
                <span>{fmt.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Date Span Range */}
      <div>
        <h4
          style={{
            fontSize: '0.8rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--color-ink-muted)',
            marginBottom: '0.6rem',
          }}
        >
          Date Span (Year)
        </h4>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <input
            type="text"
            placeholder="1800"
            value={filters.date_start || ''}
            onChange={(e) => onChange({ ...filters, date_start: e.target.value })}
            style={{
              width: '50%',
              padding: '0.35rem 0.5rem',
              border: '1px solid var(--color-paper-border)',
              borderRadius: 'var(--radius-xs)',
              fontSize: '0.8rem',
              backgroundColor: '#FFFFFF',
              color: 'var(--color-ink-primary)',
            }}
          />
          <span style={{ color: 'var(--color-ink-muted)', fontSize: '0.8rem' }}>to</span>
          <input
            type="text"
            placeholder="1900"
            value={filters.date_end || ''}
            onChange={(e) => onChange({ ...filters, date_end: e.target.value })}
            style={{
              width: '50%',
              padding: '0.35rem 0.5rem',
              border: '1px solid var(--color-paper-border)',
              borderRadius: 'var(--radius-xs)',
              fontSize: '0.8rem',
              backgroundColor: '#FFFFFF',
              color: 'var(--color-ink-primary)',
            }}
          />
        </div>
      </div>

      {/* Key Historical Figures */}
      <div>
        <h4
          style={{
            fontSize: '0.8rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--color-ink-muted)',
            marginBottom: '0.6rem',
          }}
        >
          Key Figures
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          {[
            'Henry Ward Beecher',
            'Abraham Lincoln',
            'General Ulysses S. Grant',
            'Mahatma Gandhi',
          ].map((ent) => {
            const isSelected = filters.entity_name === ent;
            return (
              <button
                key={ent}
                type="button"
                onClick={() => handleToggle('entity_name', ent)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  background: isSelected ? 'var(--color-paper-elevated)' : 'transparent',
                  border: 'none',
                  padding: '0.3rem 0.4rem',
                  borderRadius: 'var(--radius-xs)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '0.825rem',
                  color: isSelected ? 'var(--color-accent-oxblood)' : 'var(--color-ink-secondary)',
                  fontWeight: isSelected ? 600 : 400,
                }}
              >
                {isSelected ? (
                  <CheckSquare size={14} color="var(--color-accent-oxblood)" />
                ) : (
                  <Square size={14} color="var(--color-paper-border-dark)" />
                )}
                <span>{ent}</span>
              </button>
            );
          })}
        </div>
      </div>
    </aside>
  );
}
