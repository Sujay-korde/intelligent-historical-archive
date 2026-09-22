'use client';

import React, { useState, useEffect } from 'react';
import { ZoomIn, ZoomOut, Maximize2, FileText, Image as ImageIcon, BookOpen, ExternalLink, Volume2, Video as VideoIcon } from 'lucide-react';

interface ArchivalViewerProps {
  title: string;
  recordType?: string;
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
  recordType,
  mediaAssets = [],
  sourceUrl,
  extractedTextPreview = '',
}: ArchivalViewerProps) {
  const [viewMode, setViewMode] = useState<'scan' | 'transcript'>('scan');
  const [zoomLevel, setZoomLevel] = useState(1.0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [textContent, setTextContent] = useState<string>('');
  const [isLoadingText, setIsLoadingText] = useState(false);

  // Intelligently select asset matching recordType or primary role
  const primaryAsset =
    (recordType === 'video'
      ? mediaAssets.find((a) => a.media_type === 'video' || a.mime_type?.includes('video'))
      : recordType === 'audio'
      ? mediaAssets.find((a) => a.media_type === 'audio' || a.mime_type?.includes('audio'))
      : recordType === 'manuscript'
      ? mediaAssets.find((a) => a.media_type === 'manuscript' || a.media_type === 'document' || a.mime_type?.includes('pdf') || a.mime_type?.includes('text'))
      : null) ||
    mediaAssets.find((a) => a.asset_role === 'primary') ||
    mediaAssets[0] ||
    null;

  const rawKey = primaryAsset?.storage_key || primaryAsset?.access_url || '';

  const isVideo = Boolean(
    recordType === 'video' ||
    primaryAsset?.media_type === 'video' ||
    primaryAsset?.mime_type?.includes('video') ||
    rawKey.toLowerCase().match(/\.(mp4|webm|mov|mkv|avi|ogv|m4v)(\?.*)?$/i)
  );
  const isAudio = Boolean(
    !isVideo && (
      recordType === 'audio' ||
      primaryAsset?.media_type === 'audio' ||
      primaryAsset?.mime_type?.includes('audio') ||
      rawKey.toLowerCase().match(/\.(mp3|m4a|wav|ogg|flac|aac)(\?.*)?$/i)
    )
  );
  const isImage = Boolean(
    !isVideo && !isAudio && (
      recordType === 'map' ||
      recordType === 'photograph' ||
      primaryAsset?.media_type === 'image' ||
      primaryAsset?.mime_type?.includes('image') ||
      rawKey.toLowerCase().match(/\.(jpg|jpeg|png|tif|tiff|webp)(\?.*)?$/i)
    )
  );
  const isPdf = Boolean(
    !isVideo && !isAudio && !isImage && (
      primaryAsset?.mime_type?.includes('pdf') ||
      rawKey.toLowerCase().endsWith('.pdf')
    )
  );
  const isText = Boolean(
    !isVideo && !isAudio && !isImage && !isPdf && (
      primaryAsset?.mime_type?.includes('text') ||
      rawKey.toLowerCase().match(/\.(txt|md|text|csv|json)$/i) ||
      recordType === 'manuscript'
    )
  );

  const handleZoomIn = () => setZoomLevel((z) => Math.min(z + 0.25, 2.5));
  const handleZoomOut = () => setZoomLevel((z) => Math.max(z - 0.25, 0.5));
  const handleResetZoom = () => setZoomLevel(1.0);

  let mediaUrl: string | null = null;
  if (rawKey) {
    if (rawKey.startsWith('http://') || rawKey.startsWith('https://')) {
      mediaUrl = rawKey;
    } else if (rawKey.startsWith('/api/v1/media/')) {
      mediaUrl = rawKey;
    } else {
      mediaUrl = `/api/v1/media/${rawKey}`;
    }
  } else if (primaryAsset?.access_url) {
    mediaUrl = primaryAsset.access_url;
  }

  useEffect(() => {
    if (isText && mediaUrl) {
      setIsLoadingText(true);
      fetch(mediaUrl)
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.text();
        })
        .then((txt) => {
          setTextContent(txt);
          setIsLoadingText(false);
        })
        .catch(() => {
          setTextContent(extractedTextPreview || '');
          setIsLoadingText(false);
        });
    }
  }, [isText, mediaUrl, extractedTextPreview]);

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
          backgroundColor: isPdf ? '#525659' : viewMode === 'scan' ? 'var(--color-surface-dark)' : 'var(--color-paper-base)',
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
              <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
                <iframe
                  src={`${mediaUrl}#toolbar=1&navpanes=0`}
                  title={title}
                  style={{
                    width: '100%',
                    height: '100%',
                    flex: 1,
                    border: 'none',
                    backgroundColor: '#FFFFFF',
                  }}
                />
                <div
                  style={{
                    padding: '0.45rem 1rem',
                    backgroundColor: 'var(--color-paper-surface)',
                    borderTop: '1px solid var(--color-paper-border)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: '0.75rem',
                    color: 'var(--color-ink-muted)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <BookOpen size={13} color="var(--color-accent-oxblood)" />
                    <span>Archival Facsimile & Digitized Manuscript Scan</span>
                    {primaryAsset?.file_size_bytes && (
                      <span style={{ opacity: 0.6 }}>
                        • {(primaryAsset.file_size_bytes / (1024 * 1024)).toFixed(1)} MB
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <a
                      href={mediaUrl}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        color: 'var(--color-accent-oxblood)',
                        textDecoration: 'none',
                        fontWeight: 600,
                      }}
                    >
                      <ExternalLink size={12} />
                      <span>Open Fullscreen Scan</span>
                    </a>
                  </div>
                </div>
              </div>
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
            ) : isVideo ? (
              <div
                style={{
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: '#0A0A0A',
                  padding: '1.25rem',
                }}
              >
                <video
                  controls
                  playsInline
                  preload="metadata"
                  style={{
                    maxWidth: '100%',
                    maxHeight: '520px',
                    borderRadius: 'var(--radius-xs)',
                    boxShadow: '0 8px 30px rgba(0,0,0,0.7)',
                    outline: 'none',
                    backgroundColor: '#000000',
                  }}
                >
                  <source src={mediaUrl} type={primaryAsset?.mime_type || 'video/mp4'} />
                  Your browser does not support HTML5 video playback.
                </video>

                {/* Archival Video Metadata & Direct Stream Bar */}
                <div
                  style={{
                    marginTop: '1rem',
                    width: '100%',
                    maxWidth: '680px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.6rem 1rem',
                    backgroundColor: 'rgba(255, 255, 255, 0.08)',
                    borderRadius: 'var(--radius-xs)',
                    fontSize: '0.75rem',
                    color: 'rgba(255, 255, 255, 0.75)',
                    gap: '1rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <VideoIcon size={14} color="var(--color-accent-gold)" />
                    <span>Archival Master ({primaryAsset?.mime_type || 'video/mp4'})</span>
                    {primaryAsset?.file_size_bytes && (
                      <span style={{ opacity: 0.6 }}>
                        • {(primaryAsset.file_size_bytes / (1024 * 1024)).toFixed(1)} MB
                      </span>
                    )}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <a
                      href={mediaUrl}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        color: 'var(--color-accent-gold)',
                        textDecoration: 'none',
                        fontWeight: 500,
                      }}
                    >
                      <ExternalLink size={12} />
                      <span>Direct Stream</span>
                    </a>
                  </div>
                </div>
              </div>
            ) : isText ? (
              <div
                style={{
                  width: '100%',
                  height: '100%',
                  overflowY: 'auto',
                  backgroundColor: '#FAF7F0',
                  padding: '2.5rem 3rem',
                  color: 'var(--color-ink-primary)',
                  fontFamily: 'Cormorant Garamond, Georgia, serif',
                  lineHeight: 1.85,
                }}
              >
                <div
                  style={{
                    borderBottom: '2px solid #D4C5A9',
                    paddingBottom: '1rem',
                    marginBottom: '1.5rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <span
                      style={{
                        fontSize: '0.7rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em',
                        color: 'var(--color-accent-oxblood)',
                        fontWeight: 700,
                      }}
                    >
                      Digitized Manuscript Proclamation & Text
                    </span>
                    <h3
                      className="font-display"
                      style={{
                        fontSize: '1.5rem',
                        color: 'var(--color-ink-primary)',
                        marginTop: '0.2rem',
                      }}
                    >
                      {title}
                    </h3>
                  </div>
                  {mediaUrl && (
                    <a
                      href={mediaUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="btn-archival btn-oxblood"
                      style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}
                    >
                      Raw Transcript
                    </a>
                  )}
                </div>

                {isLoadingText ? (
                  <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--color-ink-muted)' }}>
                    Loading digitized manuscript text...
                  </div>
                ) : (
                  <div
                    style={{
                      fontSize: `${1.05 * zoomLevel}rem`,
                      whiteSpace: 'pre-wrap',
                      textAlign: 'justify',
                      textJustify: 'inter-word',
                      letterSpacing: '0.01em',
                    }}
                  >
                    {textContent || extractedTextPreview || 'No transcribed manuscript text available.'}
                  </div>
                )}
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
