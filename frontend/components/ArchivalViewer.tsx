'use client';

import React, { useState } from 'react';
import { ZoomIn, ZoomOut, Maximize2, FileText, Image as ImageIcon, BookOpen, ExternalLink, Volume2 } from 'lucide-react';

interface ArchivalViewerProps {
  title: string;
  mediaAssets: Array<{
    id: string;
    asset_role: string;
    media_type: string;
    mime_type: string;
    storage_key: string;
    access_url?: string | null;
    file_size_bytes?: number | null;
    page_number?: number | null;
  }>;
  sourceUrl?: string | null;
  extractedTextPreview?: string;
}

export default function ArchivalViewer({
  title,
  mediaAssets = [],
  sourceUrl,
  extractedTextPreview = '',
}: ArchivalViewerProps) {
  const [viewMode, setViewMode] = useState<'scan' | 'transcript'>('scan');
  const [zoomLevel, setZoomLevel] = useState(1.0);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const primaryAsset = mediaAssets[0] || null;
  const isPdf = Boolean(primaryAsset?.mime_type?.includes('pdf') || primaryAsset?.storage_key?.toLowerCase().endsWith('.pdf'));
  const isImage = Boolean(primaryAsset?.mime_type?.includes('image') || primaryAsset?.storage_key?.toLowerCase().match(/\.(jpg|jpeg|png|tif|tiff|webp)$/i));
  const isAudio = Boolean(primaryAsset?.mime_type?.includes('audio') || primaryAsset?.storage_key?.toLowerCase().match(/\.(mp3|m4a|wav|ogg)$/i));

  const handleZoomIn = () => setZoomLevel((z) => Math.min(z + 0.25, 2.5));
  const handleZoomOut = () => setZoomLevel((z) => Math.max(z - 0.25, 0.5));
  const handleResetZoom = () => setZoomLevel(1.0);

  const mediaUrl = primaryAsset ? `/api/v1/media/${primaryAsset.storage_key}` : null;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--color-paper-border)',
        overflow: 'hidden',
        backgroundColor: '#FFFFFF',
      }}
    >
      {/* Viewer Toolbar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'var(--color-paper-surface)',
          padding: '0.6rem 1rem',
          borderBottom: '1px solid var(--color-paper-border)',
          fontSize: '0.8rem',
        }}
      >
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button
            type="button"
            onClick={() => setViewMode('scan')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.3rem',
              padding: '0.3rem 0.65rem',
              borderRadius: 'var(--radius-xs)',
              border: '1px solid',
              borderColor: viewMode === 'scan' ? 'var(--color-accent-oxblood)' : 'var(--color-paper-border)',
              backgroundColor: viewMode === 'scan' ? 'var(--color-accent-oxblood-subtle)' : 'transparent',
              color: viewMode === 'scan' ? 'var(--color-accent-oxblood)' : 'var(--color-ink-secondary)',
              fontWeight: viewMode === 'scan' ? 600 : 400,
              cursor: 'pointer',
            }}
          >
            <BookOpen size={14} />
            <span>Primary Scan</span>
          </button>

          <button
            type="button"
            onClick={() => setViewMode('transcript')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.3rem',
              padding: '0.3rem 0.65rem',
              borderRadius: 'var(--radius-xs)',
              border: '1px solid',
              borderColor: viewMode === 'transcript' ? 'var(--color-accent-oxblood)' : 'var(--color-paper-border)',
              backgroundColor: viewMode === 'transcript' ? 'var(--color-accent-oxblood-subtle)' : 'transparent',
              color: viewMode === 'transcript' ? 'var(--color-accent-oxblood)' : 'var(--color-ink-secondary)',
              fontWeight: viewMode === 'transcript' ? 600 : 400,
              cursor: 'pointer',
            }}
          >
            <FileText size={14} />
            <span>Normalized Text</span>
          </button>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {viewMode === 'scan' && isImage && (
            <>
              <button
                type="button"
                onClick={handleZoomOut}
                title="Zoom Out"
                style={{
                  background: 'none',
                  border: '1px solid var(--color-paper-border)',
                  borderRadius: '3px',
                  padding: '0.25rem 0.4rem',
                  cursor: 'pointer',
                  color: 'var(--color-ink-secondary)',
                }}
              >
                <ZoomOut size={14} />
              </button>
              <span style={{ fontSize: '0.75rem', color: 'var(--color-ink-muted)' }}>
                {Math.round(zoomLevel * 100)}%
              </span>
              <button
                type="button"
                onClick={handleZoomIn}
                title="Zoom In"
                style={{
                  background: 'none',
                  border: '1px solid var(--color-paper-border)',
                  borderRadius: '3px',
                  padding: '0.25rem 0.4rem',
                  cursor: 'pointer',
                  color: 'var(--color-ink-secondary)',
                }}
              >
                <ZoomIn size={14} />
              </button>
            </>
          )}

          {mediaUrl && (
            <a
              href={mediaUrl}
              target="_blank"
              rel="noreferrer"
              title="Open raw media file"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.3rem',
                color: 'var(--color-ink-muted)',
                textDecoration: 'none',
                padding: '0.25rem 0.4rem',
              }}
            >
              <ExternalLink size={14} />
              <span>Full Asset</span>
            </a>
          )}
        </div>
      </div>

      {/* Viewer Canvas */}
      <div
        style={{
          minHeight: '520px',
          height: '620px',
          backgroundColor: viewMode === 'scan' ? 'var(--color-surface-dark)' : 'var(--color-paper-base)',
          position: 'relative',
          overflow: 'auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {viewMode === 'scan' ? (
          mediaUrl ? (
            isPdf ? (
              <iframe
                src={`${mediaUrl}#toolbar=1&navpanes=0`}
                title={title}
                style={{
                  width: '100%',
                  height: '100%',
                  border: 'none',
                }}
              />
            ) : isImage ? (
              <div
                style={{
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  overflow: 'auto',
                  padding: '1.5rem',
                }}
              >
                <img
                  src={mediaUrl}
                  alt={title}
                  style={{
                    maxWidth: '100%',
                    maxHeight: '100%',
                    objectFit: 'contain',
                    transform: `scale(${zoomLevel})`,
                    transformOrigin: 'center center',
                    transition: 'transform 0.15s ease',
                    boxShadow: '0 8px 30px rgba(0,0,0,0.4)',
                  }}
                />
              </div>
            ) : isAudio ? (
              <div
                style={{
                  width: '100%',
                  padding: '3rem 2rem',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: 'var(--color-surface-dark)',
                  color: '#FFFFFF',
                  textAlign: 'center',
                }}
              >
                <div
                  style={{
                    width: '64px',
                    height: '64px',
                    borderRadius: '50%',
                    backgroundColor: 'rgba(153, 117, 48, 0.2)',
                    border: '2px solid var(--color-accent-gold)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '1.25rem',
                    color: 'var(--color-accent-gold)',
                  }}
                >
                  <Volume2 size={32} />
                </div>
                <h4
                  className="font-display"
                  style={{ fontSize: '1.6rem', color: '#FFFFFF', marginBottom: '0.5rem' }}
                >
                  Historical Audio Broadcast & Speech
                </h4>
                <p
                  style={{
                    fontSize: '0.85rem',
                    color: 'rgba(255,255,255,0.7)',
                    maxWidth: '480px',
                    marginBottom: '2rem',
                    lineHeight: 1.5,
                  }}
                >
                  Primary phonographic / magnetic recording preserved in archival master quality ({primaryAsset?.mime_type}).
                </p>
                <audio
                  controls
                  src={mediaUrl}
                  style={{
                    width: '100%',
                    maxWidth: '480px',
                    borderRadius: '24px',
                    outline: 'none',
                  }}
                >
                  Your browser does not support audio playback.
                </audio>
              </div>
            ) : (
              <div style={{ color: 'var(--color-surface-dark-text)', textAlign: 'center', padding: '2rem' }}>
                <FileText size={48} style={{ opacity: 0.5, marginBottom: '1rem' }} />
                <p>Digital archival file ready for inspection.</p>
                <a
                  href={mediaUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-archival btn-oxblood"
                  style={{ marginTop: '1rem' }}
                >
                  Download Asset
                </a>
              </div>
            )
          ) : (
            <div style={{ color: 'var(--color-surface-dark-text)', textAlign: 'center' }}>
              <p style={{ opacity: 0.6 }}>No physical scan asset attached to this record.</p>
            </div>
          )
        ) : (
          /* Normalized OCR / Text Reading Mode */
          <div
            style={{
              padding: '2.5rem 3rem',
              width: '100%',
              height: '100%',
              overflowY: 'auto',
              backgroundColor: '#FFFFFF',
              color: 'var(--color-ink-primary)',
              lineHeight: 1.75,
              fontSize: '1rem',
              fontFamily: 'Cormorant Garamond, Georgia, serif',
            }}
          >
            <h3
              style={{
                fontSize: '1.4rem',
                fontWeight: 600,
                borderBottom: '1px solid var(--color-paper-border)',
                paddingBottom: '0.5rem',
                marginBottom: '1.5rem',
                fontFamily: 'Cormorant Garamond, Georgia, serif',
              }}
            >
              Archival Transcription & Normalized Text
            </h3>
            {extractedTextPreview ? (
              <div style={{ whiteSpace: 'pre-line', fontSize: '1.1rem' }}>
                {extractedTextPreview}
              </div>
            ) : (
              <p style={{ color: 'var(--color-ink-muted)', fontStyle: 'italic' }}>
                Full transcription rendered from physical PDF extraction with OCR ligature normalization.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
