'use client';

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import GlobalNav from '../../components/GlobalNav';
import {
  UploadCloud,
  FileCheck,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  ArrowRight,
  Database,
  Search,
  Sparkles,
  Layers,
  FileText,
  Volume2,
  Video,
  Image as ImageIcon,
  BookOpen,
  Info,
  ExternalLink,
  ShieldCheck,
} from 'lucide-react';
import {
  validateDeposit,
  uploadRecord,
  importExternalRecord,
  DepositValidationResponse,
  IngestResponse,
} from '../../lib/api';

// Curated Indian Historical Records from Internet Archive for quick testing
const INDIAN_HISTORICAL_PRESETS = [
  {
    title: '1838 Composite Map of Bengal, Bahar, Oude & Allahabad',
    identifier: 'dr_composite-map-a-map-of-bengal-bahar-oude--allahabad-with-part-of-agra-13170043',
    recordType: 'map',
    period: '1838 (Company Rule)',
    modality: 'Cartographic / High-Res Scan',
    description: 'Detailed cartographic survey of North & Eastern India published in 1838, depicting Bengal, Bihar, Awadh and Agra provinces.',
  },
  {
    title: 'A Sanskrit Grammar for Beginners (Devanagari & Roman)',
    identifier: 'bub_gb_oRd38Al7HSEC',
    recordType: 'manuscript',
    period: '1870 (Manuscript / Book)',
    modality: 'Digitized Manuscript / Text',
    description: 'Max Müller’s pioneering 1870 philological work on Sanskrit grammar, preserving Devanagari manuscript typography and transliteration.',
  },
  {
    title: 'Jawaharlal Nehru Broadcast on Mahatma Gandhi’s Passing (1948)',
    identifier: '78_nehru-on-gandhis-death_jawaharlal-nehru_gbia7001460a',
    recordType: 'audio',
    period: 'January 30, 1948',
    modality: 'Audio Broadcast / Speech',
    description: 'Historical All India Radio address to the nation ("The light has gone out of our lives, and there is darkness everywhere...").',
  },
  {
    title: 'Archival Video: Historical Indian State & Diplomatic Footage',
    identifier: 'Rajiv.Gandhi.A-04.23',
    recordType: 'video',
    period: '1985 (Archival Newsreel)',
    modality: 'Motion Picture / Newsreel',
    description: 'Archival video newsreel recording diplomatic events and press conference recordings in 20th century Indian history.',
  },
];

export default function DepositPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'upload' | 'external'>('external');

  // External Ingestion State
  const [externalSourceId, setExternalSourceId] = useState('');
  const [externalRecordType, setExternalRecordType] = useState('document');
  const [isValidatingExternal, setIsValidatingExternal] = useState(false);
  const [externalValidation, setExternalValidation] = useState<DepositValidationResponse | null>(null);

  // Upload State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileHash, setFileHash] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [creator, setCreator] = useState('');
  const [dateRaw, setDateRaw] = useState('');
  const [recordType, setRecordType] = useState('document');
  const [language, setLanguage] = useState('English');
  const [description, setDescription] = useState('');
  const [uploadValidation, setUploadValidation] = useState<DepositValidationResponse | null>(null);

  // Ingestion Pipeline Execution State
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState<number>(0);
  const [ingestResult, setIngestResult] = useState<IngestResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Calculate browser SHA-256 for local file
  const computeSHA256 = async (file: File): Promise<string> => {
    const arrayBuffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSelectedFile(file);
    setUploadValidation(null);
    setErrorMessage(null);

    // Auto-suggest title from filename if empty
    if (!title) {
      const cleanName = file.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ');
      setTitle(cleanName);
    }

    // Detect format modality
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    if (['mp3', 'wav', 'm4a', 'ogg'].includes(ext)) {
      setRecordType('audio');
    } else if (['mp4', 'webm', 'mov', 'mkv'].includes(ext)) {
      setRecordType('video');
    } else if (['jpg', 'jpeg', 'png', 'tif', 'tiff', 'webp'].includes(ext)) {
      setRecordType('photograph');
    } else if (ext === 'pdf') {
      setRecordType('document');
    }

    // Compute cryptographic fingerprint & probe deduplication
    try {
      const hash = await computeSHA256(file);
      setFileHash(hash);
      const val = await validateDeposit({ sha256: hash });
      setUploadValidation(val);
    } catch (err: any) {
      console.warn('Could not compute SHA-256 fingerprint:', err);
    }
  };

  const handleValidateExternal = async () => {
    if (!externalSourceId.trim()) return;
    setIsValidatingExternal(true);
    setExternalValidation(null);
    setErrorMessage(null);
    try {
      const res = await validateDeposit({
        source: 'internet_archive',
        source_id: externalSourceId.trim(),
      });
      setExternalValidation(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'Validation failed.');
    } finally {
      setIsValidatingExternal(false);
    }
  };

  const handleExternalImport = async () => {
    if (!externalSourceId.trim()) return;
    setIsProcessing(true);
    setErrorMessage(null);
    setIngestResult(null);
    setProcessingStage(1);

    // Stage progression tracker
    const timer1 = setTimeout(() => setProcessingStage(2), 1500);
    const timer2 = setTimeout(() => setProcessingStage(3), 3500);
    const timer3 = setTimeout(() => setProcessingStage(4), 6500);
    const timer4 = setTimeout(() => setProcessingStage(5), 9000);

    try {
      const res = await importExternalRecord({
        source: 'internet_archive',
        source_id: externalSourceId.trim(),
        record_type: externalRecordType,
      });
      setProcessingStage(6);
      setIngestResult(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'Archival ingestion failed.');
      setProcessingStage(0);
    } finally {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);
      setIsProcessing(false);
    }
  };

  const handleUploadDeposit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMessage('Please select a file to deposit.');
      return;
    }
    if (!title.trim()) {
      setErrorMessage('Document title is required.');
      return;
    }

    setIsProcessing(true);
    setErrorMessage(null);
    setIngestResult(null);
    setProcessingStage(1);

    const timer1 = setTimeout(() => setProcessingStage(2), 1200);
    const timer2 = setTimeout(() => setProcessingStage(3), 3000);
    const timer3 = setTimeout(() => setProcessingStage(4), 5500);
    const timer4 = setTimeout(() => setProcessingStage(5), 8000);

    try {
      const fd = new FormData();
      fd.append('file', selectedFile);
      fd.append('title', title.trim());
      if (creator.trim()) fd.append('creator', creator.trim());
      if (dateRaw.trim()) fd.append('date_raw', dateRaw.trim());
      fd.append('record_type', recordType);
      if (language.trim()) fd.append('language', language.trim());
      if (description.trim()) fd.append('description', description.trim());

      const res = await uploadRecord(fd);
      setProcessingStage(6);
      setIngestResult(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'Archival deposit failed.');
      setProcessingStage(0);
    } finally {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);
      setIsProcessing(false);
    }
  };

  const selectPreset = (preset: typeof INDIAN_HISTORICAL_PRESETS[0]) => {
    setExternalSourceId(preset.identifier);
    setExternalRecordType(preset.recordType);
    setExternalValidation(null);
  };

  const pipelineStages = [
    { num: 1, label: 'Cryptographic Deduplication & Integrity Gate' },
    { num: 2, label: 'Vault Storage & Canonical Entity Ingestion' },
    { num: 3, label: 'Text/Modality Extraction & Multi-layer OCR' },
    { num: 4, label: 'Gemini 2.5 Historical Intelligence Enrichment' },
    { num: 5, label: '768-Dim pgvector Embeddings & Chunking' },
    { num: 6, label: 'Knowledge Graph Cross-Linking & Completion' },
  ];

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <GlobalNav />

      <main style={{ flex: 1, padding: '2.5rem 0' }}>
        <div className="container-research" style={{ maxWidth: '1040px' }}>
          {/* Header */}
          <div style={{ marginBottom: '2.5rem' }}>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.45rem',
                padding: '0.25rem 0.65rem',
                borderRadius: 'var(--radius-full)',
                backgroundColor: 'var(--color-accent-oxblood-subtle)',
                color: 'var(--color-accent-oxblood)',
                fontSize: '0.75rem',
                fontWeight: 600,
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
                marginBottom: '0.75rem',
              }}
            >
              <Database size={13} />
              <span>Custodial Ingestion Layer</span>
            </div>
            <h1
              className="font-display"
              style={{
                fontSize: '2.5rem',
                fontWeight: 600,
                color: 'var(--color-ink-primary)',
                marginBottom: '0.65rem',
                lineHeight: 1.15,
              }}
            >
              Archival Deposit & Historical Source Ingestion
            </h1>
            <p
              style={{
                fontSize: '1.05rem',
                color: 'var(--color-ink-secondary)',
                fontFamily: 'Newsreader, Georgia, serif',
                fontStyle: 'italic',
                maxWidth: '820px',
                lineHeight: 1.6,
              }}
            >
              Deposit primary historical artifacts, high-resolution scans, manuscripts, audio broadcasts, and newsreel footage,
              or ingest canonical records directly from external heritage archives.
            </p>
          </div>

          {/* Tab Navigation */}
          <div
            style={{
              display: 'flex',
              gap: '1rem',
              borderBottom: '2px solid var(--color-paper-border)',
              marginBottom: '2rem',
            }}
          >
            <button
              type="button"
              onClick={() => {
                setActiveTab('external');
                setErrorMessage(null);
                setIngestResult(null);
              }}
              style={{
                padding: '0.75rem 1.5rem',
                fontSize: '0.95rem',
                fontWeight: 600,
                backgroundColor: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'external' ? '3px solid var(--color-accent-oxblood)' : '3px solid transparent',
                color: activeTab === 'external' ? 'var(--color-accent-oxblood)' : 'var(--color-ink-muted)',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '-2px',
                transition: 'all 0.15s ease',
              }}
            >
              <Search size={16} />
              <span>Import from Internet Archive</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setActiveTab('upload');
                setErrorMessage(null);
                setIngestResult(null);
              }}
              style={{
                padding: '0.75rem 1.5rem',
                fontSize: '0.95rem',
                fontWeight: 600,
                backgroundColor: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'upload' ? '3px solid var(--color-accent-oxblood)' : '3px solid transparent',
                color: activeTab === 'upload' ? 'var(--color-accent-oxblood)' : 'var(--color-ink-muted)',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '-2px',
                transition: 'all 0.15s ease',
              }}
            >
              <UploadCloud size={16} />
              <span>Deposit Physical / Digital Asset</span>
            </button>
          </div>

          {/* Error Banner */}
          {errorMessage && (
            <div
              style={{
                padding: '1rem 1.25rem',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: '#FEF2F2',
                border: '1px solid #FCA5A5',
                color: '#991B1B',
                marginBottom: '1.75rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
              }}
            >
              <AlertTriangle size={20} />
              <span style={{ fontSize: '0.9rem' }}>{errorMessage}</span>
            </div>
          )}

          {/* Success / Result Card */}
          {ingestResult && (
            <div
              style={{
                padding: '1.5rem',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: ingestResult.is_duplicate ? '#FFFBEB' : '#F0FDF4',
                border: `1px solid ${ingestResult.is_duplicate ? '#FCD34D' : '#86EFAC'}`,
                marginBottom: '2rem',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
                {ingestResult.is_duplicate ? (
                  <AlertTriangle size={24} color="#D97706" style={{ marginTop: '0.2rem', flexShrink: 0 }} />
                ) : (
                  <CheckCircle2 size={24} color="#16A34A" style={{ marginTop: '0.2rem', flexShrink: 0 }} />
                )}
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                    <h3
                      className="font-display"
                      style={{
                        fontSize: '1.2rem',
                        fontWeight: 600,
                        color: ingestResult.is_duplicate ? '#92400E' : '#166534',
                      }}
                    >
                      {ingestResult.is_duplicate
                        ? 'Archive Custody Notice: Duplicate Record Detected'
                        : 'Ingestion & Processing Complete'}
                    </h3>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        padding: '0.2rem 0.55rem',
                        borderRadius: 'var(--radius-full)',
                        backgroundColor: ingestResult.is_duplicate ? '#FEF3C7' : '#DCFCE7',
                        color: ingestResult.is_duplicate ? '#B45309' : '#15803D',
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                      }}
                    >
                      {ingestResult.is_duplicate ? 'Deduplicated' : 'Indexed & Searchable'}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.9rem', color: 'var(--color-ink-secondary)', marginBottom: '0.75rem', lineHeight: 1.5 }}>
                    {ingestResult.message}
                  </p>

                  {!ingestResult.is_duplicate && (
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(4, 1fr)',
                        gap: '0.75rem',
                        padding: '0.75rem 1rem',
                        backgroundColor: 'rgba(255, 255, 255, 0.8)',
                        borderRadius: 'var(--radius-xs)',
                        border: '1px solid rgba(0, 0, 0, 0.06)',
                        marginBottom: '1rem',
                        fontSize: '0.8rem',
                      }}
                    >
                      <div>
                        <div style={{ color: 'var(--color-ink-muted)' }}>Quality Score</div>
                        <div style={{ fontWeight: 600, color: 'var(--color-ink-primary)' }}>
                          {ingestResult.quality_score.toFixed(1)} / 100
                        </div>
                      </div>
                      <div>
                        <div style={{ color: 'var(--color-ink-muted)' }}>Indexed Chunks</div>
                        <div style={{ fontWeight: 600, color: 'var(--color-ink-primary)' }}>
                          {ingestResult.chunks_count} chunks (768d)
                        </div>
                      </div>
                      <div>
                        <div style={{ color: 'var(--color-ink-muted)' }}>Named Entities</div>
                        <div style={{ fontWeight: 600, color: 'var(--color-ink-primary)' }}>
                          {ingestResult.entities_count} graph nodes
                        </div>
                      </div>
                      <div>
                        <div style={{ color: 'var(--color-ink-muted)' }}>Record Modality</div>
                        <div style={{ fontWeight: 600, color: 'var(--color-ink-primary)', textTransform: 'capitalize' }}>
                          {ingestResult.record_type || 'Document'}
                        </div>
                      </div>
                    </div>
                  )}

                  {ingestResult.document_id && (
                    <a
                      href={`/documents/${ingestResult.document_id}`}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.45rem',
                        padding: '0.5rem 1rem',
                        borderRadius: 'var(--radius-sm)',
                        backgroundColor: 'var(--color-accent-oxblood)',
                        color: '#FFFFFF',
                        fontSize: '0.85rem',
                        fontWeight: 600,
                        textDecoration: 'none',
                        transition: 'opacity 0.15s ease',
                      }}
                    >
                      <span>Open Document in Archival Viewer & Inspector</span>
                      <ArrowRight size={14} />
                    </a>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Processing Progress Tracker Overlay */}
          {isProcessing && (
            <div
              style={{
                padding: '2rem',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--color-paper-surface)',
                border: '1px solid var(--color-paper-border)',
                marginBottom: '2rem',
                boxShadow: 'var(--shadow-md)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <Loader2 size={22} className="animate-spin" color="var(--color-accent-oxblood)" />
                <h3 className="font-display" style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--color-ink-primary)' }}>
                  Ingestion & Intelligent Enrichment Pipeline Active
                </h3>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                {pipelineStages.map((st) => {
                  const isDone = processingStage > st.num;
                  const isCurrent = processingStage === st.num;
                  return (
                    <div
                      key={st.num}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        padding: '0.45rem 0.75rem',
                        borderRadius: 'var(--radius-xs)',
                        backgroundColor: isCurrent
                          ? 'var(--color-accent-oxblood-subtle)'
                          : isDone
                          ? 'rgba(22, 163, 74, 0.08)'
                          : 'transparent',
                        color: isCurrent
                          ? 'var(--color-accent-oxblood)'
                          : isDone
                          ? '#15803D'
                          : 'var(--color-ink-muted)',
                        fontWeight: isCurrent || isDone ? 600 : 400,
                        fontSize: '0.85rem',
                      }}
                    >
                      {isDone ? (
                        <CheckCircle2 size={16} color="#16A34A" />
                      ) : isCurrent ? (
                        <Loader2 size={16} className="animate-spin" color="var(--color-accent-oxblood)" />
                      ) : (
                        <div
                          style={{
                            width: '16px',
                            height: '16px',
                            borderRadius: '50%',
                            border: '1.5px solid var(--color-paper-border)',
                          }}
                        />
                      )}
                      <span>
                        Stage {st.num}: {st.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 1: EXTERNAL INTERNET ARCHIVE IMPORT */}
          {activeTab === 'external' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              {/* Preset Selector */}
              <div
                style={{
                  padding: '1.5rem',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--color-paper-surface)',
                  border: '1px solid var(--color-paper-border)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                  <Sparkles size={16} color="var(--color-accent-gold)" />
                  <h3 className="font-display" style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--color-ink-primary)' }}>
                    Indian Historical Records — Curated Multi-Modal Corpus
                  </h3>
                </div>
                <p style={{ fontSize: '0.85rem', color: 'var(--color-ink-muted)', marginBottom: '1.25rem' }}>
                  Select an archival record across primary formats (Cartographic map, Sanskrit manuscript, Speech broadcast, Historic newsreel footage) to test automated retrieval and processing:
                </p>

                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))',
                    gap: '1rem',
                  }}
                >
                  {INDIAN_HISTORICAL_PRESETS.map((p) => {
                    const isSelected = externalSourceId === p.identifier;
                    return (
                      <div
                        key={p.identifier}
                        onClick={() => selectPreset(p)}
                        style={{
                          padding: '1rem',
                          borderRadius: 'var(--radius-sm)',
                          border: `1.5px solid ${isSelected ? 'var(--color-accent-oxblood)' : 'var(--color-paper-border)'}`,
                          backgroundColor: isSelected ? 'var(--color-accent-oxblood-subtle)' : '#FFFFFF',
                          cursor: 'pointer',
                          transition: 'all 0.15s ease',
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                        }}
                      >
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                            <span
                              style={{
                                fontSize: '0.7rem',
                                fontWeight: 600,
                                textTransform: 'uppercase',
                                color: 'var(--color-accent-oxblood)',
                                letterSpacing: '0.04em',
                              }}
                            >
                              {p.modality}
                            </span>
                            <span style={{ fontSize: '0.7rem', color: 'var(--color-ink-muted)' }}>{p.period}</span>
                          </div>
                          <h4
                            className="font-display"
                            style={{
                              fontSize: '0.95rem',
                              fontWeight: 600,
                              color: 'var(--color-ink-primary)',
                              marginBottom: '0.4rem',
                              lineHeight: 1.3,
                            }}
                          >
                            {p.title}
                          </h4>
                          <p style={{ fontSize: '0.75rem', color: 'var(--color-ink-secondary)', lineHeight: 1.4 }}>
                            {p.description}
                          </p>
                        </div>

                        <div
                          style={{
                            marginTop: '0.75rem',
                            paddingTop: '0.5rem',
                            borderTop: '1px solid rgba(0, 0, 0, 0.05)',
                            fontSize: '0.7rem',
                            fontFamily: 'monospace',
                            color: 'var(--color-ink-muted)',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          ID: {p.identifier}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Identifier Input & Validation */}
              <div
                style={{
                  padding: '2rem',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: '#FFFFFF',
                  border: '1px solid var(--color-paper-border)',
                }}
              >
                <div style={{ marginBottom: '1.25rem' }}>
                  <label
                    style={{
                      display: 'block',
                      fontSize: '0.875rem',
                      fontWeight: 600,
                      color: 'var(--color-ink-primary)',
                      marginBottom: '0.4rem',
                    }}
                  >
                    Archive.org Item Identifier
                  </label>
                  <div style={{ display: 'flex', gap: '0.75rem' }}>
                    <div style={{ position: 'relative', flex: 1 }}>
                      <input
                        type="text"
                        value={externalSourceId}
                        onChange={(e) => {
                          setExternalSourceId(e.target.value);
                          setExternalValidation(null);
                        }}
                        placeholder="e.g. dr_composite-map-a-map-of-bengal-bahar-oude--allahabad-with-part-of-agra-13170043"
                        style={{
                          width: '100%',
                          padding: '0.65rem 0.85rem',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--color-paper-border)',
                          backgroundColor: 'var(--color-paper-surface)',
                          fontSize: '0.9rem',
                          fontFamily: 'monospace',
                          color: 'var(--color-ink-primary)',
                        }}
                      />
                    </div>
                    <button
                      type="button"
                      onClick={handleValidateExternal}
                      disabled={isValidatingExternal || !externalSourceId.trim()}
                      style={{
                        padding: '0.65rem 1.25rem',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--color-paper-border)',
                        backgroundColor: 'var(--color-paper-surface)',
                        color: 'var(--color-ink-primary)',
                        fontSize: '0.85rem',
                        fontWeight: 600,
                        cursor: externalSourceId.trim() ? 'pointer' : 'not-allowed',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.4rem',
                        opacity: externalSourceId.trim() ? 1 : 0.6,
                      }}
                    >
                      {isValidatingExternal ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <ShieldCheck size={14} />
                      )}
                      <span>Probe Custody Check</span>
                    </button>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--color-ink-muted)', marginTop: '0.35rem', display: 'block' }}>
                    Verifies cryptographic provenance and ensures the repository item is not already cataloged.
                  </span>
                </div>

                {/* Validation Feedback */}
                {externalValidation && (
                  <div
                    style={{
                      padding: '0.85rem 1.15rem',
                      borderRadius: 'var(--radius-xs)',
                      backgroundColor: externalValidation.is_duplicate ? '#FFFBEB' : '#F0FDF4',
                      border: `1px solid ${externalValidation.is_duplicate ? '#FCD34D' : '#86EFAC'}`,
                      marginBottom: '1.25rem',
                      fontSize: '0.85rem',
                      color: externalValidation.is_duplicate ? '#92400E' : '#166534',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {externalValidation.is_duplicate ? <AlertTriangle size={16} /> : <CheckCircle2 size={16} />}
                      <span>{externalValidation.message}</span>
                    </div>
                    {externalValidation.existing_document_id && (
                      <a
                        href={`/documents/${externalValidation.existing_document_id}`}
                        style={{
                          fontWeight: 600,
                          color: 'var(--color-accent-oxblood)',
                          textDecoration: 'underline',
                          fontSize: '0.8rem',
                        }}
                      >
                        View Preserved Record &rarr;
                      </a>
                    )}
                  </div>
                )}

                {/* Submit Action */}
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button
                    type="button"
                    onClick={handleExternalImport}
                    disabled={isProcessing || !externalSourceId.trim()}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      padding: '0.75rem 1.75rem',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: 'var(--color-accent-oxblood)',
                      color: '#FFFFFF',
                      fontSize: '0.95rem',
                      fontWeight: 600,
                      border: 'none',
                      cursor: !isProcessing && externalSourceId.trim() ? 'pointer' : 'not-allowed',
                      opacity: !isProcessing && externalSourceId.trim() ? 1 : 0.6,
                      boxShadow: 'var(--shadow-sm)',
                    }}
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        <span>Ingesting & Processing Record...</span>
                      </>
                    ) : (
                      <>
                        <Database size={16} />
                        <span>Import & Execute Pipeline</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: LOCAL PHYSICAL / RESEARCHER DEPOSIT */}
          {activeTab === 'upload' && (
            <form
              onSubmit={handleUploadDeposit}
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '1.75rem',
              }}
            >
              {/* Dropzone */}
              <div
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: '2px dashed var(--color-paper-border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '2.5rem 1.5rem',
                  backgroundColor: selectedFile ? 'var(--color-accent-oxblood-subtle)' : 'var(--color-paper-surface)',
                  textAlign: 'center',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={handleFileChange}
                  accept=".pdf,.jpg,.jpeg,.png,.tif,.tiff,.webp,.mp3,.m4a,.wav,.ogg,.mp4,.webm,.mov"
                  style={{ display: 'none' }}
                />
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
                  <div
                    style={{
                      width: '48px',
                      height: '48px',
                      borderRadius: '50%',
                      backgroundColor: 'var(--color-accent-oxblood-subtle)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--color-accent-oxblood)',
                    }}
                  >
                    <UploadCloud size={24} />
                  </div>
                  <div>
                    <div style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--color-ink-primary)' }}>
                      {selectedFile ? selectedFile.name : 'Select or drop historical artifact file'}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--color-ink-muted)', marginTop: '0.25rem' }}>
                      Supported formats: PDF Documents, High-Res Imagery (TIFF, PNG, JPG), Historical Audio (MP3, WAV), Archival Video (MP4)
                    </div>
                  </div>
                  {selectedFile && (
                    <div
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        fontSize: '0.75rem',
                        fontFamily: 'monospace',
                        color: 'var(--color-ink-secondary)',
                        backgroundColor: '#FFFFFF',
                        padding: '0.35rem 0.75rem',
                        borderRadius: 'var(--radius-xs)',
                        border: '1px solid var(--color-paper-border)',
                      }}
                    >
                      <ShieldCheck size={14} color="#16A34A" />
                      <span>SHA-256: {fileHash ? `${fileHash.slice(0, 16)}...${fileHash.slice(-8)}` : 'Computing...'}</span>
                      <span>({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Upload Pre-Validation Alert */}
              {uploadValidation && (
                <div
                  style={{
                    padding: '0.85rem 1.15rem',
                    borderRadius: 'var(--radius-xs)',
                    backgroundColor: uploadValidation.is_duplicate ? '#FFFBEB' : '#F0FDF4',
                    border: `1px solid ${uploadValidation.is_duplicate ? '#FCD34D' : '#86EFAC'}`,
                    fontSize: '0.85rem',
                    color: uploadValidation.is_duplicate ? '#92400E' : '#166534',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {uploadValidation.is_duplicate ? <AlertTriangle size={16} /> : <CheckCircle2 size={16} />}
                    <span>{uploadValidation.message}</span>
                  </div>
                  {uploadValidation.existing_document_id && (
                    <a
                      href={`/documents/${uploadValidation.existing_document_id}`}
                      style={{
                        fontWeight: 600,
                        color: 'var(--color-accent-oxblood)',
                        textDecoration: 'underline',
                        fontSize: '0.8rem',
                      }}
                    >
                      View Existing Document &rarr;
                    </a>
                  )}
                </div>
              )}

              {/* Provenance Metadata Fields */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, 1fr)',
                  gap: '1.25rem',
                  padding: '2rem',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: '#FFFFFF',
                  border: '1px solid var(--color-paper-border)',
                }}
              >
                <div style={{ gridColumn: 'span 2' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-ink-primary)', marginBottom: '0.35rem' }}>
                    Document / Artifact Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. 1947 Mountbatten Partition Plan Dispatches"
                    style={{
                      width: '100%',
                      padding: '0.65rem 0.85rem',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--color-paper-border)',
                      backgroundColor: 'var(--color-paper-surface)',
                      fontSize: '0.9rem',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-ink-primary)', marginBottom: '0.35rem' }}>
                    Creator / Author / Speaker
                  </label>
                  <input
                    type="text"
                    value={creator}
                    onChange={(e) => setCreator(e.target.value)}
                    placeholder="e.g. Jawaharlal Nehru, Rabindranath Tagore"
                    style={{
                      width: '100%',
                      padding: '0.65rem 0.85rem',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--color-paper-border)',
                      backgroundColor: 'var(--color-paper-surface)',
                      fontSize: '0.9rem',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-ink-primary)', marginBottom: '0.35rem' }}>
                    Historical Era / Date
                  </label>
                  <input
                    type="text"
                    value={dateRaw}
                    onChange={(e) => setDateRaw(e.target.value)}
                    placeholder="e.g. August 14, 1947 or circa 1885"
                    style={{
                      width: '100%',
                      padding: '0.65rem 0.85rem',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--color-paper-border)',
                      backgroundColor: 'var(--color-paper-surface)',
                      fontSize: '0.9rem',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-ink-primary)', marginBottom: '0.35rem' }}>
                    Record Format Modality
                  </label>
                  <select
                    value={recordType}
                    onChange={(e) => setRecordType(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.65rem 0.85rem',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--color-paper-border)',
                      backgroundColor: 'var(--color-paper-surface)',
                      fontSize: '0.9rem',
                    }}
                  >
                    <option value="document">Historical Document (PDF/Text)</option>
                    <option value="manuscript">Manuscript / Treatise</option>
                    <option value="audio">Historical Audio / Speech Broadcast</option>
                    <option value="video">Motion Picture / Newsreel Footage</option>
                    <option value="photograph">Archival Photograph</option>
                    <option value="map">Cartographic Map</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-ink-primary)', marginBottom: '0.35rem' }}>
                    Primary Language
                  </label>
                  <input
                    type="text"
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    placeholder="e.g. English, Sanskrit, Hindi, Bengali"
                    style={{
                      width: '100%',
                      padding: '0.65rem 0.85rem',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--color-paper-border)',
                      backgroundColor: 'var(--color-paper-surface)',
                      fontSize: '0.9rem',
                    }}
                  />
                </div>

                <div style={{ gridColumn: 'span 2' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-ink-primary)', marginBottom: '0.35rem' }}>
                    Historical / Curatorial Context
                  </label>
                  <textarea
                    rows={3}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Provide context, historical provenance, archival notes or condition description..."
                    style={{
                      width: '100%',
                      padding: '0.65rem 0.85rem',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--color-paper-border)',
                      backgroundColor: 'var(--color-paper-surface)',
                      fontSize: '0.9rem',
                      fontFamily: 'inherit',
                    }}
                  />
                </div>
              </div>

              {/* Submit Button */}
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  type="submit"
                  disabled={isProcessing || !selectedFile}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.75rem 1.75rem',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'var(--color-accent-oxblood)',
                    color: '#FFFFFF',
                    fontSize: '0.95rem',
                    fontWeight: 600,
                    border: 'none',
                    cursor: !isProcessing && selectedFile ? 'pointer' : 'not-allowed',
                    opacity: !isProcessing && selectedFile ? 1 : 0.6,
                    boxShadow: 'var(--shadow-sm)',
                  }}
                >
                  {isProcessing ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      <span>Processing Deposit & Indexing...</span>
                    </>
                  ) : (
                    <>
                      <UploadCloud size={16} />
                      <span>Deposit Primary Source</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}
