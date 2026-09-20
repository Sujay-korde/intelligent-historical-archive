'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { Layers, Sparkles, Filter, RotateCcw, BookOpen, AlertCircle, RefreshCw } from 'lucide-react';
import KnowledgeGraphView from '../../components/KnowledgeGraphView';
import { getKnowledgeGraph, GraphResponse } from '../../lib/api';

function ConnectionsContent() {
  const searchParams = useSearchParams();
  const documentId = searchParams.get('document_id') || undefined;
  const initialFocus = searchParams.get('focus') || '';

  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'graph' | 'list'>('graph');

  const fetchGraph = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getKnowledgeGraph(documentId, 150);
      setGraphData(data);
    } catch (err: any) {
      console.error('Failed to load knowledge graph:', err);
      setError(err.message || 'Unable to generate knowledge graph network.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, [documentId]);

  return (
    <div className="container-research" style={{ paddingTop: '2.5rem', paddingBottom: '5rem' }}>
      {/* Page Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-end',
          marginBottom: '1.75rem',
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
            Relational Knowledge Intelligence
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
            Connected Archival Graph
          </h1>
          <p style={{ fontSize: '0.9rem', color: 'var(--color-ink-secondary)', marginTop: '0.2rem' }}>
            Interactive exploration of historical actors, verified correspondence, locations, and citations stored in PostgreSQL.
          </p>
        </div>

        {/* View Mode Toggle: Interactive Canvas vs Accessible List */}
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button
            type="button"
            onClick={() => setViewMode('graph')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.3rem',
              padding: '0.4rem 0.8rem',
              borderRadius: 'var(--radius-xs)',
              border: '1px solid',
              borderColor: viewMode === 'graph' ? 'var(--color-accent-oxblood)' : 'var(--color-paper-border)',
              backgroundColor: viewMode === 'graph' ? 'var(--color-accent-oxblood-subtle)' : 'transparent',
              color: viewMode === 'graph' ? 'var(--color-accent-oxblood)' : 'var(--color-ink-secondary)',
              fontWeight: viewMode === 'graph' ? 600 : 400,
              cursor: 'pointer',
              fontSize: '0.8rem',
            }}
          >
            <Layers size={14} />
            <span>Interactive Canvas</span>
          </button>

          <button
            type="button"
            onClick={() => setViewMode('list')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.3rem',
              padding: '0.4rem 0.8rem',
              borderRadius: 'var(--radius-xs)',
              border: '1px solid',
              borderColor: viewMode === 'list' ? 'var(--color-accent-oxblood)' : 'var(--color-paper-border)',
              backgroundColor: viewMode === 'list' ? 'var(--color-accent-oxblood-subtle)' : 'transparent',
              color: viewMode === 'list' ? 'var(--color-accent-oxblood)' : 'var(--color-ink-secondary)',
              fontWeight: viewMode === 'list' ? 600 : 400,
              cursor: 'pointer',
              fontSize: '0.8rem',
            }}
          >
            <BookOpen size={14} />
            <span>Structured Hierarchy</span>
          </button>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div
          className="shimmer"
          style={{
            height: '680px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--color-paper-border)',
          }}
        />
      )}

      {/* Error State */}
      {error && !loading && (
        <div
          className="archival-panel"
          style={{
            padding: '3rem 2rem',
            textAlign: 'center',
            borderColor: 'var(--color-accent-oxblood)',
            backgroundColor: 'var(--color-accent-oxblood-subtle)',
          }}
        >
          <AlertCircle size={36} color="var(--color-accent-oxblood)" style={{ margin: '0 auto 0.5rem' }} />
          <h3 style={{ color: 'var(--color-accent-oxblood)', fontSize: '1.1rem', fontWeight: 600 }}>
            Unable to Generate Knowledge Network
          </h3>
          <p style={{ color: 'var(--color-ink-secondary)', fontSize: '0.9rem', marginTop: '0.3rem' }}>
            {error}
          </p>
          <button
            type="button"
            onClick={fetchGraph}
            className="btn-archival btn-oxblood"
            style={{ marginTop: '1.25rem' }}
          >
            <RefreshCw size={14} />
            <span>Retry Connection</span>
          </button>
        </div>
      )}

      {/* Interactive Graph View */}
      {!loading && !error && graphData && viewMode === 'graph' && (
        <KnowledgeGraphView initialData={graphData} initialFocus={initialFocus} />
      )}

      {/* Accessible List / Table Fallback View */}
      {!loading && !error && graphData && viewMode === 'list' && (
        <div
          className="archival-panel"
          style={{ padding: '2rem', backgroundColor: '#FFFFFF' }}
        >
          <h3 className="font-display" style={{ fontSize: '1.4rem', marginBottom: '1rem' }}>
            Archival Entities & Verified Relationships
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
            <div>
              <h4
                style={{
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  color: 'var(--color-ink-muted)',
                  marginBottom: '0.75rem',
                }}
              >
                Indexed Entities ({graphData.nodes.length})
              </h4>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {graphData.nodes.map((node) => (
                  <li
                    key={node.id}
                    style={{
                      padding: '0.5rem 0.75rem',
                      border: '1px solid var(--color-paper-border)',
                      borderRadius: 'var(--radius-xs)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <span style={{ fontWeight: 500, color: 'var(--color-ink-primary)' }}>{node.label}</span>
                    <span className="entity-badge entity-topic" style={{ fontSize: '0.7rem' }}>
                      {node.group}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h4
                style={{
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  color: 'var(--color-ink-muted)',
                  marginBottom: '0.75rem',
                }}
              >
                Verified Relationship Edges ({graphData.edges.length})
              </h4>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {graphData.edges.map((edge, i) => {
                  const src = graphData.nodes.find((n) => n.id === edge.source)?.label || edge.source;
                  const tgt = graphData.nodes.find((n) => n.id === edge.target)?.label || edge.target;
                  return (
                    <li
                      key={i}
                      style={{
                        padding: '0.5rem 0.75rem',
                        border: '1px solid var(--color-paper-border)',
                        borderRadius: 'var(--radius-xs)',
                        fontSize: '0.85rem',
                      }}
                    >
                      <span style={{ fontWeight: 600 }}>{src}</span>
                      <span style={{ color: 'var(--color-accent-oxblood)', margin: '0 0.4rem', fontSize: '0.75rem' }}>
                        ── {edge.relationship} ──►
                      </span>
                      <span style={{ fontWeight: 600 }}>{tgt}</span>
                      <span style={{ float: 'right', fontSize: '0.75rem', color: 'var(--color-ink-muted)' }}>
                        {Math.round(edge.confidence * 100)}% conf.
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ConnectionsPage() {
  return (
    <Suspense fallback={<div className="container-research" style={{ padding: '3rem' }}>Loading graph network...</div>}>
      <ConnectionsContent />
    </Suspense>
  );
}
