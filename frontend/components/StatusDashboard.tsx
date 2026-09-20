'use client';

import React, { useEffect, useState } from 'react';
import { fetchHealthStatus, HealthResponse } from '@/lib/api';

export default function StatusDashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const checkStatus = async () => {
    setLoading(true);
    const data = await fetchHealthStatus();
    setHealth(data);
    setLoading(false);
    setLastUpdated(new Date());
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'healthy':
        return <span className="badge badge-success"><span className="pulse-dot" style={{ backgroundColor: '#10b981' }}></span> Operational</span>;
      case 'degraded':
        return <span className="badge badge-warning"><span className="pulse-dot" style={{ backgroundColor: '#f59e0b' }}></span> Degraded</span>;
      case 'unhealthy':
      case 'offline':
      default:
        return <span className="badge badge-error"><span className="pulse-dot" style={{ backgroundColor: '#f43f5e' }}></span> Offline</span>;
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '1.75rem', marginBottom: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            System Subsystems Status
            {health && getStatusBadge(health.status)}
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            Live health telemetry probe of Backend, Database, pgvector extension, and Storage layer.
          </p>
        </div>
        <button 
          onClick={checkStatus} 
          disabled={loading}
          className="btn btn-outline"
          style={{ fontSize: '0.8rem' }}
        >
          {loading ? 'Probing...' : 'Refresh Status'}
        </button>
      </div>

      <div className="grid-cols-4">
        {/* Backend API Box */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.03)',
          border: '1px solid var(--border-color)',
          borderRadius: '0.75rem',
          padding: '1.25rem',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>FastAPI Backend</span>
            <span className={`badge ${health && health.status !== 'offline' ? 'badge-success' : 'badge-error'}`} style={{ fontSize: '0.65rem' }}>
              {health && health.status !== 'offline' ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
          <p style={{ fontSize: '1.1rem', fontWeight: '600' }}>FastAPI v0.111+</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            Port 8000 • Async Lifespan & CORS Enabled
          </p>
        </div>

        {/* PostgreSQL Database Box */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.03)',
          border: '1px solid var(--border-color)',
          borderRadius: '0.75rem',
          padding: '1.25rem',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>Database</span>
            <span className={`badge ${health?.database.connected ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: '0.65rem' }}>
              {health?.database.connected ? 'CONNECTED' : 'STANDBY'}
            </span>
          </div>
          <p style={{ fontSize: '1.1rem', fontWeight: '600' }}>PostgreSQL 16</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            SQLAlchemy 2.0 Async + Alembic Migrations
          </p>
        </div>

        {/* pgvector Box */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.03)',
          border: '1px solid var(--border-color)',
          borderRadius: '0.75rem',
          padding: '1.25rem',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>Vector Store</span>
            <span className={`badge ${health?.database.pgvector_installed ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: '0.65rem' }}>
              {health?.database.pgvector_installed ? 'ACTIVE' : 'CONFIGURED'}
            </span>
          </div>
          <p style={{ fontSize: '1.1rem', fontWeight: '600' }}>pgvector</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            384-dim Embeddings • Cosine / HNSW index
          </p>
        </div>

        {/* Storage Box */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.03)',
          border: '1px solid var(--border-color)',
          borderRadius: '0.75rem',
          padding: '1.25rem',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>Object Storage</span>
            <span className={`badge ${health?.storage.operational ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: '0.65rem' }}>
              {health?.storage.operational ? 'READY' : 'STANDBY'}
            </span>
          </div>
          <p style={{ fontSize: '1.1rem', fontWeight: '600' }}>{health?.storage.backend.toUpperCase() || 'LOCAL'}</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            Zero-copy Streaming & SHA-256 Checksums
          </p>
        </div>
      </div>

      <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        <span>Environment: <strong>{health?.environment || 'development'}</strong></span>
        <span>Last Probe: {lastUpdated.toLocaleTimeString()}</span>
      </div>
    </div>
  );
}
