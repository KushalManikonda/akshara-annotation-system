// frontend/src/components/LocalAudioPicker.tsx
//
// Browser-side local audio file picker for the local audio model.
// The WAV file is NOT uploaded to the server — the browser reads it
// directly via URL.createObjectURL(), feeding WaveSurfer locally.
//
// Usage:
//   <LocalAudioPicker
//     audioRelativePath="Telugu/telugu1.wav"
//     audioFilename="telugu1.wav"
//     onFileSelected={(objectUrl) => setLocalUrl(objectUrl)}
//     onCleared={() => setLocalUrl(null)}
//   />

import { useRef, useState, useCallback } from 'react';

export interface LocalAudioPickerProps {
  /** Portable relative path hint shown to the user, e.g. "Telugu/telugu1.wav" */
  audioRelativePath: string;
  /** Expected filename, e.g. "telugu1.wav" */
  audioFilename: string;
  /** Called with an object URL whenever a valid file is selected */
  onFileSelected: (objectUrl: string) => void;
  /** Called when the user clears the selected file */
  onCleared?: () => void;
  /** Compact mode for embedding in the waveform toolbar */
  compact?: boolean;
}

export default function LocalAudioPicker({
  audioRelativePath,
  audioFilename,
  onFileSelected,
  onCleared,
  compact = false,
}: LocalAudioPickerProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [nameMismatch, setNameMismatch] = useState(false);
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  const expectedStem = audioFilename.replace(/\.[^.]+$/, '').toLowerCase();

  const handleFile = useCallback(
    (file: File) => {
      // Check stem match (case-insensitive, ignore extension)
      const fileStem = file.name.replace(/\.[^.]+$/, '').toLowerCase();
      const isMismatch = fileStem !== expectedStem;
      setNameMismatch(isMismatch);

      // Revoke previous object URL to avoid memory leaks
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }

      const url = URL.createObjectURL(file);
      setObjectUrl(url);
      setSelectedName(file.name);
      onFileSelected(url);
    },
    [expectedStem, objectUrl, onFileSelected]
  );

  const handleClear = useCallback(() => {
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
    }
    setObjectUrl(null);
    setSelectedName(null);
    setNameMismatch(false);
    if (inputRef.current) inputRef.current.value = '';
    onCleared?.();
  }, [objectUrl, onCleared]);

  const isLoaded = !!objectUrl;

  if (compact) {
    // Compact mode: a single button for use inside the waveform header
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <input
          ref={inputRef}
          type="file"
          accept="audio/*"
          style={{ display: 'none' }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
        />
        {isLoaded ? (
          <>
            <span
              style={{
                fontSize: '0.75rem',
                color: nameMismatch ? '#f59e0b' : '#10b981',
                maxWidth: '140px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
              title={selectedName || ''}
            >
              {nameMismatch ? '⚠️' : '✅'} {selectedName}
            </span>
            <button
              className="btn btn-secondary"
              style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem' }}
              onClick={handleClear}
              title="Clear selected file"
            >
              ✕
            </button>
          </>
        ) : (
          <button
            className="btn btn-secondary"
            style={{ fontSize: '0.75rem', padding: '0.3rem 0.75rem', whiteSpace: 'nowrap' }}
            onClick={() => inputRef.current?.click()}
            title={`Select local WAV file. Expected: ${audioRelativePath}`}
          >
            📂 Select WAV
          </button>
        )}
        {nameMismatch && (
          <span
            style={{ fontSize: '0.7rem', color: '#f59e0b' }}
            title={`Expected: ${audioFilename}`}
          >
            Name mismatch
          </span>
        )}
      </div>
    );
  }

  // Full mode: shown when no stream URL is available
  return (
    <div
      style={{
        padding: '1.25rem 1.5rem',
        background: 'rgba(99, 102, 241, 0.06)',
        border: '1px solid rgba(99, 102, 241, 0.25)',
        borderRadius: '0.75rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.875rem',
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="audio/*"
        style={{ display: 'none' }}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
        }}
      />

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
        <span style={{ fontSize: '1.25rem' }}>🎵</span>
        <div>
          <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>
            Local Audio File Required
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
            This audio is stored on your local machine, not on the server.
          </div>
        </div>
      </div>

      {/* Expected path info */}
      <div
        style={{
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '0.5rem',
          padding: '0.625rem 0.875rem',
          fontSize: '0.8rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.25rem',
        }}
      >
        <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Expected audio file
        </div>
        <code style={{ color: '#a5b4fc', wordBreak: 'break-all' }}>
          {audioRelativePath || audioFilename}
        </code>
      </div>

      {/* Status / action */}
      {isLoaded ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.4rem 0.875rem',
              background: nameMismatch ? 'rgba(245,158,11,0.1)' : 'rgba(16,185,129,0.1)',
              border: `1px solid ${nameMismatch ? 'rgba(245,158,11,0.3)' : 'rgba(16,185,129,0.3)'}`,
              borderRadius: '99px',
              fontSize: '0.8rem',
              color: nameMismatch ? '#f59e0b' : '#10b981',
              fontWeight: 600,
            }}
          >
            {nameMismatch ? '⚠️' : '✅'}
            <span style={{ maxWidth: '220px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {selectedName}
            </span>
          </div>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '0.75rem', padding: '0.3rem 0.75rem' }}
            onClick={handleClear}
          >
            Change file
          </button>
        </div>
      ) : (
        <button
          className="btn btn-primary"
          style={{
            alignSelf: 'flex-start',
            fontSize: '0.85rem',
            padding: '0.5rem 1.25rem',
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
          }}
          onClick={() => inputRef.current?.click()}
        >
          📂 Select local WAV file
        </button>
      )}

      {/* Mismatch warning */}
      {nameMismatch && selectedName && (
        <div
          style={{
            padding: '0.625rem 0.875rem',
            background: 'rgba(245,158,11,0.08)',
            border: '1px solid rgba(245,158,11,0.25)',
            borderRadius: '0.5rem',
            fontSize: '0.8rem',
            color: '#f59e0b',
          }}
        >
          ⚠️ Filename mismatch: selected <strong>{selectedName}</strong> but expected{' '}
          <strong>{audioFilename}</strong>. Audio will still play — verify it is the correct file.
        </div>
      )}

      {/* Instructions */}
      {!isLoaded && (
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
          Select the WAV file from your local audio dataset directory. The file is read
          directly by your browser — it is never uploaded to the server.
        </div>
      )}
    </div>
  );
}
