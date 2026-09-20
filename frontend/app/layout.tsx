import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Intelligent Knowledge Archive | Foundation Console',
  description: 'Scalable Multi-Format Document Ingestion, Processing, and Vector Retrieval Platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header style={{
          borderBottom: '1px solid var(--border-color)',
          background: 'rgba(10, 13, 20, 0.8)',
          backdropFilter: 'blur(8px)',
          position: 'sticky',
          top: 0,
          zIndex: 50,
        }}>
          <div className="container" style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '1rem 1.5rem',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                background: 'var(--gradient-badge)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 'bold',
                color: '#fff',
                fontSize: '1.1rem',
              }}>
                KA
              </div>
              <div>
                <h1 style={{ fontSize: '1.1rem', fontWeight: '700', letterSpacing: '-0.02em' }}>
                  Intelligent Knowledge Archive
                </h1>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  Phase 0 Foundation • PostgreSQL + pgvector + FastAPI + Next.js
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
              <a 
                href="http://127.0.0.1:8000/api/v1/docs" 
                target="_blank" 
                rel="noreferrer"
                className="btn btn-outline"
                style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
              >
                API Docs (FastAPI)
              </a>
              <span className="badge badge-info">v0.1.0</span>
            </div>
          </div>
        </header>

        <main>{children}</main>

        <footer style={{
          borderTop: '1px solid var(--border-color)',
          padding: '2rem 0',
          marginTop: '4rem',
          textAlign: 'center',
          color: 'var(--text-muted)',
          fontSize: '0.85rem',
        }}>
          <div className="container">
            <p>Intelligent Historical Archive System Foundation — All core architecture subsystems initialized</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
