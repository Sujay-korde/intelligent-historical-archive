import type { Metadata } from 'next';
import './globals.css';
import GlobalNav from '../components/GlobalNav';

export const metadata: Metadata = {
  title: 'The Intelligent Historical Archive | Connected Memory',
  description: 'AI-Powered Archival Discovery, Dense Semantic Search, and Relational Knowledge Graphs',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <GlobalNav />
        <main>{children}</main>
        <footer
          style={{
            borderTop: '1px solid var(--color-paper-border)',
            backgroundColor: 'var(--color-paper-surface)',
            padding: '3rem 0',
            marginTop: '5rem',
            color: 'var(--color-ink-muted)',
            fontSize: '0.85rem',
          }}
        >
          <div className="container-editorial" style={{ textAlign: 'center' }}>
            <div
              className="font-display"
              style={{
                fontSize: '1.2rem',
                color: 'var(--color-ink-primary)',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
                marginBottom: '0.5rem',
              }}
            >
              The Intelligent Historical Archive
            </div>
            <p style={{ maxWidth: '600px', margin: '0 auto 1.5rem', lineHeight: 1.6 }}>
              Preserving original historical sources with high-fidelity archival provenance, dense semantic indexing via PostgreSQL pgvector, and Google Gemini knowledge enrichment.
            </p>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '1.5rem', fontSize: '0.8rem' }}>
              <a href="/explore" style={{ color: 'var(--color-accent-oxblood)', textDecoration: 'none' }}>
                Explore Archive
              </a>
              <a href="/connections" style={{ color: 'var(--color-accent-oxblood)', textDecoration: 'none' }}>
                Knowledge Graph
              </a>
              <a href="/collections" style={{ color: 'var(--color-accent-oxblood)', textDecoration: 'none' }}>
                Collections
              </a>
              <a href="/about" style={{ color: 'var(--color-accent-oxblood)', textDecoration: 'none' }}>
                About & Provenance
              </a>
              <a
                href="http://localhost:8000/api/v1/docs"
                target="_blank"
                rel="noreferrer"
                style={{ color: 'var(--color-ink-muted)', textDecoration: 'none' }}
              >
                FastAPI Docs
              </a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
