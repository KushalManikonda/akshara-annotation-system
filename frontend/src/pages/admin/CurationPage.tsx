// frontend/src/pages/admin/CurationPage.tsx
//
// Admin-only Curation page for running the three-language ASR pipeline.
// Flow: Language select → Audio upload → Pipeline run → Status poll → Submit to queue
//
// Preserves all existing styling conventions (CSS variables, glass-panel, btn classes).

import { useState, useRef, useCallback, useEffect } from 'react';
import { api } from '../../services/api';
import ImportTranscriptModal from '../../components/admin/ImportTranscriptModal';

// ── Types ─────────────────────────────────────────────────────────────────────

type Language = 'hindi' | 'english' | 'telugu';

type PipelineStatus =
  | 'IDLE'
  | 'UPLOADING'
  | 'PENDING'
  | 'PROCESSING'
  | 'TRANSCRIBING'
  | 'COMPLETED'
  | 'FAILED'
  | 'SUBMITTED';

interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
}

interface CurationState {
  audioId: string | null;
  filename: string;
  duration: number;
  pipelineStatus: PipelineStatus;
  error: string | null;
  segments: TranscriptSegment[];
  segmentsCount: number;
  startedAt: string | null;
  completedAt: string | null;
}

const LANGUAGE_CONFIG: Record<Language, { label: string; color: string; modelInfo: string }> = {
  hindi: { label: 'Hindi', color: '#f97316', modelInfo: 'VAD: Pyannote speaker-diarization 3.1\nPreprocessing: SAM-Audio\nASR: AI4Bharat IndicConformer' },
  english: { label: 'English', color: '#3b82f6', modelInfo: 'VAD: Not used\nPreprocessing: Denoising/noise-reduction\nASR: OpenAI Whisper' },
  telugu: { label: 'Telugu', color: '#8b5cf6', modelInfo: 'VAD: Silero VAD\nPreprocessing: Mono/16kHz\nASR: AI4Bharat IndicConformer' },
};

const STATUS_CONFIG: Record<PipelineStatus, { label: string; color: string; pulse: boolean }> = {
  IDLE:         { label: 'Idle',                 color: '#6b7280', pulse: false },
  UPLOADING:    { label: 'Uploading…',           color: '#f59e0b', pulse: true },
  PENDING:      { label: 'Uploaded',             color: '#3b82f6', pulse: false },
  PROCESSING:   { label: 'Processing…',          color: '#f59e0b', pulse: true },
  TRANSCRIBING: { label: 'Transcribing…',        color: '#8b5cf6', pulse: true },
  COMPLETED:    { label: 'Transcript Generated', color: '#10b981', pulse: false },
  FAILED:       { label: 'Failed',               color: '#ef4444', pulse: false },
  SUBMITTED:    { label: 'Ready for Annotation', color: '#10b981', pulse: false },
};

// ── Helper: format seconds as mm:ss ──────────────────────────────────────────
function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

// ── Status Badge ──────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: PipelineStatus }) {
  const cfg = STATUS_CONFIG[status];
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.4rem',
      padding: '0.3rem 0.9rem',
      borderRadius: '99px',
      fontSize: '0.8rem',
      fontWeight: 600,
      background: `${cfg.color}22`,
      color: cfg.color,
      border: `1px solid ${cfg.color}44`,
    }}>
      {cfg.pulse && (
        <span style={{
          display: 'inline-block',
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          background: cfg.color,
          animation: 'pulse 1.2s ease-in-out infinite',
        }} />
      )}
      {cfg.label}
    </span>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function CurationPage() {
  const [selectedLanguage, setSelectedLanguage] = useState<Language | null>(null);
  const [curation, setCuration] = useState<CurationState>({
    audioId: null,
    filename: '',
    duration: 0,
    pipelineStatus: 'IDLE',
    error: null,
    segments: [],
    segmentsCount: 0,
    startedAt: null,
    completedAt: null,
  });
  const [isDragging, setIsDragging] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Status polling ──────────────────────────────────────────────────────────
  const startPolling = useCallback((audioId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await api.get(`/curation/${audioId}/status`);
        const ps = data.pipeline_status as PipelineStatus;

        setCuration(prev => ({
          ...prev,
          pipelineStatus: ps,
          segmentsCount: data.segments_count ?? prev.segmentsCount,
          segments: data.transcript_preview ?? prev.segments,
          startedAt: data.started_at ?? prev.startedAt,
          completedAt: data.completed_at ?? prev.completedAt,
          error: data.error ?? null,
        }));

        if (ps === 'COMPLETED' || ps === 'FAILED') {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch {
        // Ignore polling errors — will retry next interval
      }
    }, 3000);
  }, []);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  // ── File upload handler ─────────────────────────────────────────────────────
  const handleFileUpload = useCallback(async (file: File) => {
    if (!selectedLanguage) {
      alert('Please select a language first.');
      return;
    }

    setCuration({
      audioId: null,
      filename: file.name,
      duration: 0,
      pipelineStatus: 'UPLOADING',
      error: null,
      segments: [],
      segmentsCount: 0,
      startedAt: null,
      completedAt: null,
    });

    try {
      const formData = new FormData();
      formData.append('audio_file', file);
      formData.append('language', selectedLanguage);

      const { data } = await api.post('/curation/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setCuration(prev => ({
        ...prev,
        audioId: data.audio_id,
        filename: data.filename ?? file.name,
        duration: data.duration ?? 0,
        pipelineStatus: 'PENDING',
        error: null,
      }));
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? 'Upload failed. Please try again.';
      setCuration(prev => ({ ...prev, pipelineStatus: 'FAILED', error: msg }));
    }
  }, [selectedLanguage]);

  // ── Run pipeline ────────────────────────────────────────────────────────────
  const handleRunPipeline = useCallback(async () => {
    if (!curation.audioId) return;
    setCuration(prev => ({ ...prev, pipelineStatus: 'PROCESSING', error: null }));
    try {
      await api.post(`/curation/${curation.audioId}/run`);
      startPolling(curation.audioId);
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? 'Failed to start pipeline.';
      setCuration(prev => ({ ...prev, pipelineStatus: 'FAILED', error: msg }));
    }
  }, [curation.audioId, startPolling]);

  // ── Submit to annotation queue ──────────────────────────────────────────────
  const handleSubmit = useCallback(async () => {
    if (!curation.audioId) return;
    try {
      await api.post(`/curation/${curation.audioId}/submit`);
      setCuration(prev => ({ ...prev, pipelineStatus: 'SUBMITTED' }));
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? 'Failed to submit to annotation queue.';
      setCuration(prev => ({ ...prev, error: msg }));
    }
  }, [curation.audioId]);

  // ── Reset ───────────────────────────────────────────────────────────────────
  const handleReset = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    setCuration({
      audioId: null,
      filename: '',
      duration: 0,
      pipelineStatus: 'IDLE',
      error: null,
      segments: [],
      segmentsCount: 0,
      startedAt: null,
      completedAt: null,
    });
    setSelectedLanguage(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // ── Drag-and-drop handlers ──────────────────────────────────────────────────
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFileUpload(file);
  };

  const isProcessing = ['UPLOADING', 'PROCESSING', 'TRANSCRIBING'].includes(curation.pipelineStatus);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(1.3); }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>Curation Pipeline</h1>
          <p style={{ margin: '0.25rem 0 0', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Upload audio, run the ASR pipeline, and add to the annotation queue.
          </p>
        </div>
        <button 
          className="btn btn-secondary" 
          style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-glass)' }}
          onClick={() => setShowImportModal(true)}
        >
          📥 Import Transcript (Local Audio)
        </button>
      </div>

      {showImportModal && (
        <ImportTranscriptModal 
          onClose={() => setShowImportModal(false)}
          onSuccess={() => {
            // Handle success if needed, e.g. reload a list or show a message
          }}
        />
      )}

      {/* Language Selection */}
      <div className="card glass-panel" style={{ padding: '1.5rem' }}>
        <h2 style={{ margin: '0 0 1.25rem', fontSize: '1rem', fontWeight: 600 }}>
          1. Select Language
        </h2>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          {(Object.entries(LANGUAGE_CONFIG) as [Language, typeof LANGUAGE_CONFIG[Language]][]).map(([lang, cfg]) => (
            <button
              key={lang}
              disabled={isProcessing}
              onClick={() => {
                if (!isProcessing) setSelectedLanguage(lang);
              }}
              style={{
                flex: 1,
                minWidth: '140px',
                padding: '1.25rem 1rem',
                border: selectedLanguage === lang
                  ? `2px solid ${cfg.color}`
                  : '2px solid var(--border-glass)',
                borderRadius: '0.75rem',
                background: selectedLanguage === lang
                  ? `${cfg.color}18`
                  : 'rgba(255,255,255,0.04)',
                cursor: isProcessing ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s ease',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '0.5rem',
                color: selectedLanguage === lang ? cfg.color : 'var(--text-muted)',
                fontFamily: 'var(--font-sans)',
                opacity: isProcessing ? 0.6 : 1,
              }}
            >
              <span style={{ fontSize: '1.5rem', fontWeight: 600, flex: 1, display: 'flex', alignItems: 'center' }}>{cfg.label}</span>
              <div style={{
                fontSize: '10px',
                textAlign: 'center',
                whiteSpace: 'pre-line',
                lineHeight: '1.4',
                color: selectedLanguage === lang ? cfg.color : 'var(--text-muted)'
              }}>
                {cfg.modelInfo}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Audio Upload */}
      <div className="card glass-panel" style={{ padding: '1.5rem', opacity: selectedLanguage ? 1 : 0.5 }}>
        <h2 style={{ margin: '0 0 1.25rem', fontSize: '1rem', fontWeight: 600 }}>
          2. Upload Audio
          {selectedLanguage && (
            <span style={{
              marginLeft: '0.75rem',
              fontSize: '0.75rem',
              fontWeight: 500,
              color: LANGUAGE_CONFIG[selectedLanguage].color,
            }}>
              ({LANGUAGE_CONFIG[selectedLanguage].label} pipeline will be used)
            </span>
          )}
        </h2>

        {/* Drop zone */}
        <div
          onDragEnter={() => selectedLanguage && setIsDragging(true)}
          onDragOver={(e) => { e.preventDefault(); selectedLanguage && setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={selectedLanguage ? handleDrop : undefined}
          onClick={() => selectedLanguage && !isProcessing && fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${isDragging ? 'var(--color-primary)' : 'var(--border-glass)'}`,
            borderRadius: '0.75rem',
            padding: '2.5rem',
            textAlign: 'center',
            cursor: selectedLanguage && !isProcessing ? 'pointer' : 'not-allowed',
            transition: 'all 0.2s ease',
            background: isDragging ? 'rgba(99,102,241,0.08)' : 'transparent',
          }}
        >
          <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>
            {isProcessing ? '⏳' : '🎵'}
          </div>
          {curation.filename && curation.pipelineStatus !== 'IDLE' ? (
            <>
              <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{curation.filename}</div>
              {curation.duration > 0 && (
                <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                  Duration: {formatTime(curation.duration)}
                </div>
              )}
            </>
          ) : (
            <>
              <div style={{ fontWeight: 500, marginBottom: '0.25rem' }}>
                {selectedLanguage ? 'Drop audio file here or click to browse' : 'Select a language first'}
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Supported: WAV, MP3, FLAC
              </div>
            </>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".wav,.mp3,.flac"
          style={{ display: 'none' }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFileUpload(file);
          }}
        />
      </div>

      {/* Pipeline Status & Controls */}
      {curation.pipelineStatus !== 'IDLE' && (
        <div className="card glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem' }}>
            <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>3. Pipeline Status</h2>
            <StatusBadge status={curation.pipelineStatus} />
          </div>

          {/* Status timeline */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
            {(['PENDING', 'PROCESSING', 'TRANSCRIBING', 'COMPLETED'] as PipelineStatus[]).map((step, idx, arr) => {
              const steps: PipelineStatus[] = ['PENDING', 'PROCESSING', 'TRANSCRIBING', 'COMPLETED'];
              const currentIdx = steps.indexOf(curation.pipelineStatus);
              const stepIdx = steps.indexOf(step);
              const isDone = stepIdx < currentIdx || (curation.pipelineStatus === 'COMPLETED' && stepIdx <= currentIdx);
              const isActive = step === curation.pipelineStatus;
              const cfg = STATUS_CONFIG[step];
              return (
                <div key={step} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    padding: '0.25rem 0.75rem',
                    borderRadius: '99px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    background: isDone || isActive ? `${cfg.color}22` : 'rgba(255,255,255,0.04)',
                    color: isDone || isActive ? cfg.color : 'var(--text-muted)',
                    border: `1px solid ${isDone || isActive ? cfg.color + '44' : 'transparent'}`,
                  }}>
                    {isDone && !isActive ? '✓ ' : ''}{STATUS_CONFIG[step].label}
                  </div>
                  {idx < arr.length - 1 && (
                    <div style={{ width: '1.5rem', height: '1px', background: 'var(--border-glass)' }} />
                  )}
                </div>
              );
            })}
          </div>

          {/* Error */}
          {curation.error && (
            <div style={{
              padding: '1rem',
              background: 'rgba(239,68,68,0.1)',
              border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: '0.5rem',
              color: '#ef4444',
              fontSize: '0.875rem',
              marginBottom: '1rem',
            }}>
              ❌ {curation.error}
            </div>
          )}

          {/* Segment count when processing */}
          {curation.segmentsCount > 0 && (
            <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
              Generated <strong>{curation.segmentsCount}</strong> transcript segments
            </div>
          )}

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            {curation.pipelineStatus === 'PENDING' && (
              <button
                className="btn btn-primary"
                onClick={handleRunPipeline}
                style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}
              >
                🚀 Run ASR Pipeline
              </button>
            )}

            {curation.pipelineStatus === 'FAILED' && curation.audioId && (
              <button
                className="btn btn-primary"
                onClick={handleRunPipeline}
                style={{ background: 'linear-gradient(135deg, #f59e0b, #ef4444)' }}
              >
                🔄 Retry Pipeline
              </button>
            )}

            {curation.pipelineStatus === 'COMPLETED' && (
              <button
                className="btn btn-primary"
                onClick={handleSubmit}
                style={{ background: 'linear-gradient(135deg, #10b981, #3b82f6)' }}
              >
                ✅ Add to Annotation Queue
              </button>
            )}

            {curation.pipelineStatus === 'SUBMITTED' && (
              <div style={{ color: '#10b981', fontWeight: 600, padding: '0.5rem 0' }}>
                ✅ Successfully added to annotation queue!
              </div>
            )}

            <button className="btn btn-secondary" onClick={handleReset}>
              Start Over
            </button>
          </div>
        </div>
      )}

      {/* Transcript Preview */}
      {curation.segments.length > 0 && (
        <div className="card glass-panel" style={{ padding: '1.5rem' }}>
          <h2 style={{ margin: '0 0 1.25rem', fontSize: '1rem', fontWeight: 600 }}>
            4. Transcript Preview
            <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>
              (first {curation.segments.length} of {curation.segmentsCount} segments)
            </span>
          </h2>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-glass)', color: 'var(--text-muted)' }}>
                  <th style={{ textAlign: 'left', padding: '0.5rem 0.75rem 0.75rem 0', width: '70px' }}>#</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem 1rem 0.75rem', width: '120px' }}>Start</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem 1rem 0.75rem', width: '120px' }}>End</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem 0 0.75rem' }}>Text</th>
                </tr>
              </thead>
              <tbody>
                {curation.segments.map((seg, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '0.75rem 0.75rem 0.75rem 0', color: 'var(--text-muted)' }}>{i + 1}</td>
                    <td style={{ padding: '0.75rem 1rem', fontFamily: 'monospace', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      {formatTime(seg.start)}
                    </td>
                    <td style={{ padding: '0.75rem 1rem', fontFamily: 'monospace', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      {formatTime(seg.end)}
                    </td>
                    <td style={{ padding: '0.75rem 0' }}>{seg.text}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
