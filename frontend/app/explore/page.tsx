'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { Sparkles, SlidersHorizontal, BookOpen, AlertCircle, RefreshCw } from 'lucide-react';
import ArchiveSearchInput from '../../components/ArchiveSearchInput';
import FilterRail, { FilterState } from '../../components/FilterRail';
import SearchResultCard from '../../components/SearchResultCard';
import { executeSearch, SearchRequest, SearchResponse } from '../../lib/api';

function ExploreContent() {
  const searchParams = useSearchParams();
  const initialQ = searchParams.get('q') || 'Civil War union';
  const initialType = (searchParams.get('type') as any) || 'hybrid';

  const [query, setQuery] = useState(initialQ);
  const [searchType, setSearchType] = useState<'hybrid' | 'semantic' | 'keyword'>(initialType);
  const [semanticWeight, setSemanticWeight] = useState(0.7);
  const [keywordWeight, setKeywordWeight] = useState(0.3);
  const [filters, setFilters] = useState<FilterState>({});
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSearch = async (
    q: string,
    type: 'hybrid' | 'semantic' | 'keyword',
    sWeight: number,
    kWeight: number,
    fState: FilterState
  ) => {
    setLoading(true);
    setError(null);

    const req: SearchRequest = {
      query: q || 'Civil War',
      search_type: type,
      limit: 20,
      offset: 0,
      source: fState.source,
      record_type: fState.record_type,
      historical_period: fState.historical_period,
      entity_name: fState.entity_name,
      date_start: fState.date_start,
      date_end: fState.date_end,
      semantic_weight: sWeight,
      keyword_weight: kWeight,
    };

    try {
      const res = await executeSearch(req);
      setResponse(res);
    } catch (err: any) {
      console.error('Search error:', err);
      setError(err.message || 'An error occurred running archival search.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runSearch(query, searchType, semanticWeight, keywordWeight, filters);
  }, [filters]);

  const handleSearchTrigger = (
    newQ: string,
    newType: 'hybrid' | 'semantic' | 'keyword',
    sWeight: number,
    kWeight: number
  ) => {
    setQuery(newQ);
    setSearchType(newType);
    setSemanticWeight(sWeight);
    setKeywordWeight(kWeight);
    runSearch(newQ, newType, sWeight, kWeight, filters);
  };

  return (
    <div className="container-research" style={{ paddingTop: '2.5rem', paddingBottom: '4rem' }}>
      {/* Top Search & Filter Bar */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ marginBottom: '0.4rem' }}>
          <span
            style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: 'var(--color-accent-oxblood)',
            }}
          >
            Archival Discovery & Vector Retrieval
          </span>
          <h1
            className="font-display"
            style={{
              fontSize: '2.2rem',
              fontWeight: 600,
              color: 'var(--color-ink-primary)',
              marginTop: '0.15rem',
            }}
          >
            Explore Historical Records
          </h1>
        </div>

        <ArchiveSearchInput
          initialQuery={query}
          initialType={searchType}
          onSearch={handleSearchTrigger}
          showWeights={true}
        />
      </div>

      {/* Main Two-Column Research Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '300px 1fr',
          gap: '2rem',
          alignItems: 'start',
        }}
      >
        {/* Left Column: Faceted Filter Rail */}
        <FilterRail
          filters={filters}
          onChange={(newFilters) => setFilters(newFilters)}
          facets={response?.facets}
          totalResults={response?.total_results}
        />

        {/* Right Column: Search Results Stream */}
        <div>
          {/* Results Meta Header */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderBottom: '1px solid var(--color-paper-border)',
              paddingBottom: '0.75rem',
              marginBottom: '1.25rem',
              fontSize: '0.85rem',
              color: 'var(--color-ink-muted)',
            }}
          >
            <div>
              {response ? (
                <span>
                  Found <strong>{response.total_results}</strong> records for &ldquo;
                  <em style={{ color: 'var(--color-ink-primary)' }}>{response.query}</em>
                  &rdquo; (in {response.execution_time_ms.toFixed(1)}ms)
                </span>
              ) : (
                <span>Searching archival records...</span>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem' }}>
              <span>Sorted by:</span>
              <strong style={{ color: 'var(--color-ink-primary)' }}>Reciprocal Rank Fusion (RRF)</strong>
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="shimmer"
                  style={{
                    height: '140px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--color-paper-border)',
                  }}
                />
              ))}
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div
              className="archival-panel"
              style={{
                padding: '2rem',
                textAlign: 'center',
                borderColor: 'var(--color-accent-oxblood)',
                backgroundColor: 'var(--color-accent-oxblood-subtle)',
              }}
            >
              <AlertCircle size={32} color="var(--color-accent-oxblood)" style={{ margin: '0 auto 0.5rem' }} />
              <h3 style={{ color: 'var(--color-accent-oxblood)', fontSize: '1rem', fontWeight: 600 }}>
                Retrieval Notice
              </h3>
              <p style={{ color: 'var(--color-ink-secondary)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                {error}
              </p>
              <button
                type="button"
                onClick={() => runSearch(query, searchType, semanticWeight, keywordWeight, filters)}
                className="btn-archival btn-oxblood"
                style={{ marginTop: '1rem', padding: '0.4rem 0.9rem', fontSize: '0.8rem' }}
              >
                <RefreshCw size={13} />
                <span>Retry Query</span>
              </button>
            </div>
          )}

          {/* Results List */}
          {!loading && !error && response && response.results.length > 0 && (
            <div>
              {response.results.map((item, idx) => (
                <SearchResultCard key={idx} item={item} highlightQuery={query} />
              ))}
            </div>
          )}

          {/* Empty State */}
          {!loading && !error && response && response.results.length === 0 && (
            <div
              className="archival-card"
              style={{
                padding: '3rem 2rem',
                textAlign: 'center',
                backgroundColor: 'var(--color-paper-surface)',
              }}
            >
              <BookOpen size={40} color="var(--color-ink-muted)" style={{ margin: '0 auto 1rem', opacity: 0.6 }} />
              <h3 className="font-display" style={{ fontSize: '1.4rem', fontWeight: 600 }}>
                No Matching Archival Records Found
              </h3>
              <p
                style={{
                  fontSize: '0.875rem',
                  color: 'var(--color-ink-secondary)',
                  maxWidth: '480px',
                  margin: '0.5rem auto 1.5rem',
                  lineHeight: 1.6,
                }}
              >
                No historical materials matched all current filter constraints for &ldquo;{query}&rdquo;. Try clearing filters or switching to Semantic AI mode for conceptual matching.
              </p>
              <button
                type="button"
                onClick={() => setFilters({})}
                className="btn-archival btn-oxblood"
              >
                Clear All Filters
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ExplorePage() {
  return (
    <Suspense fallback={<div className="container-research" style={{ padding: '3rem' }}>Loading archive...</div>}>
      <ExploreContent />
    </Suspense>
  );
}
