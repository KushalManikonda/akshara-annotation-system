// frontend/src/pages/admin/ExportsPage.tsx
//
// Admin-only Exports page.
// Lists all COMPLETED + APPROVED audio files and allows downloading
// a ZIP export containing:
//   - original_audio.wav
//   - original_transcript.json
//   - annotated_transcript.srt
//
// Reuses existing API patterns (useQuery, axios blob download).

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, API_BASE_URL } from '../../services/api';
import { formatDurationHoursMins } from '../../utils/time';
import { useAuthStore } from '../../store/auth';

// ── Types ─────────────────────────────────────────────────────────────────────

interface AudioItem {
  id: string;
  original_filename: string;
  filename: string;
  language: string;
  duration: number | null;
  status: string;
  uploaded_at: string | null;
  dataset_name?: string;
  annotator_username?: string;
}

// ── Helper: format duration ──────────────────────────────────────────────────

// Replaced by formatDurationHoursMins

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('en-IN', {
      year: 'numeric', month: 'short', day: 'numeric',
    });
  } catch {
    return iso;
  }
}

// ── Download handler ──────────────────────────────────────────────────────────

async function downloadSrtExport(audioId: string, filename: string): Promise<void> {
  const url = `/annotations/${audioId}/export-srt`;
  const response = await api.get(url, { responseType: 'blob' });
  const blob = response.data;
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = objectUrl;
  
  // Try to get filename from content-disposition header if exposed
  let zipName = `export_${filename}.zip`;
  const disposition = response.headers['content-disposition'];
  if (disposition) {
    const match = disposition.match(/filename=([^\s;]+)/);
    if (match) zipName = match[1];
  }
  
  a.download = zipName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(objectUrl);
}

// ── Fetch completed items ─────────────────────────────────────────────────────

async function fetchCompletedItems(): Promise<AudioItem[]> {
  const { data } = await api.get('/audio/');
  // Filter to COMPLETED status only
  return (data as AudioItem[]).filter(
    (item) => (item.status || '').toUpperCase() === 'COMPLETED'
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function ExportsPage() {
  const { token } = useAuthStore();
  const [downloadingIds, setDownloadingIds] = useState<Set<string>>(new Set());
  const [downloadErrors, setDownloadErrors] = useState<Record<string, string>>({});
  const [downloadSuccess, setDownloadSuccess] = useState<Set<string>>(new Set());

  const { data: items, isLoading, error, refetch } = useQuery({
    queryKey: ['exports', 'completed'],
    queryFn: fetchCompletedItems,
    refetchInterval: 60_000,
  });

  const handleDownload = async (item: AudioItem) => {
    setDownloadingIds((prev) => new Set(prev).add(item.id));
    setDownloadErrors((prev) => {
      const next = { ...prev };
      delete next[item.id];
      return next;
    });
    setDownloadSuccess((prev) => {
      const next = new Set(prev);
      next.delete(item.id);
      return next;
    });

    try {
      await downloadSrtExport(item.id, item.original_filename || item.filename);
      setDownloadSuccess((prev) => new Set(prev).add(item.id));
    } catch (err: any) {
      setDownloadErrors((prev) => ({
        ...prev,
        [item.id]: err?.message ?? 'Download failed',
      }));
    } finally {
      setDownloadingIds((prev) => {
        const next = new Set(prev);
        next.delete(item.id);
        return next;
      });
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>Exports</h1>
          <p style={{ margin: '0.25rem 0 0', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Download finalized annotation packages for completed tasks.
          </p>
        </div>
        <button className="btn btn-secondary" onClick={() => refetch()}>
          🔄 Refresh
        </button>
      </div>

      {/* Export format info */}
      <div className="card glass-panel" style={{ padding: '1.25rem 1.5rem', display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Export Format
          </div>
          <div style={{ fontWeight: 600 }}>ZIP Archive</div>
        </div>
        <div style={{ width: '1px', background: 'var(--border-glass)' }} />
        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Contents
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            {[
              { icon: '🎵', label: 'original_audio.wav' },
              { icon: '📄', label: 'original_transcript.json' },
              { icon: '🎬', label: 'annotated_transcript.srt' },
            ].map((f) => (
              <span key={f.label} style={{
                padding: '0.2rem 0.6rem',
                background: 'rgba(255,255,255,0.06)',
                borderRadius: '0.375rem',
                fontSize: '0.8rem',
                fontFamily: 'monospace',
                color: 'var(--text-muted)',
              }}>
                {f.icon} {f.label}
              </span>
            ))}
          </div>
        </div>
        <div style={{ width: '1px', background: 'var(--border-glass)' }} />
        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            SRT Format
          </div>
          <code style={{ fontSize: '0.8rem', color: '#10b981' }}>HH:MM:SS,mmm</code>
        </div>
      </div>

      {/* Main table */}
      <div className="card glass-panel" style={{ padding: '1.5rem' }}>
        <h2 style={{ margin: '0 0 1.25rem', fontSize: '1rem', fontWeight: 600 }}>
          Completed &amp; Approved Annotations
          {items && (
            <span style={{ marginLeft: '0.5rem', color: 'var(--text-muted)', fontWeight: 400, fontSize: '0.875rem' }}>
              ({items.length} {items.length === 1 ? 'item' : 'items'})
            </span>
          )}
        </h2>

        {isLoading ? (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '3rem' }}>
            Loading completed annotations…
          </div>
        ) : error ? (
          <div style={{ color: '#ef4444', padding: '1rem' }}>
            Failed to load data. Please try refreshing.
          </div>
        ) : !items || items.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '3rem',
            color: 'var(--text-muted)',
          }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📭</div>
            <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>No completed annotations yet</div>
            <div style={{ fontSize: '0.875rem' }}>
              Items appear here once they have been reviewed and approved.
            </div>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-glass)', color: 'var(--text-muted)' }}>
                  <th style={{ textAlign: 'left', padding: '0.5rem 1rem 0.75rem 0' }}>Filename</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem 1rem 0.75rem' }}>Language</th>
                  <th style={{ textAlign: 'right', padding: '0.5rem 1rem 0.75rem' }}>Duration</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem 1rem 0.75rem' }}>Annotator</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem 1rem 0.75rem' }}>Date</th>
                  <th style={{ textAlign: 'center', padding: '0.5rem 0 0.75rem', width: '160px' }}>Export</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const isDownloading = downloadingIds.has(item.id);
                  const dlError = downloadErrors[item.id];
                  const dlSuccess = downloadSuccess.has(item.id);
                  return (
                    <tr key={item.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <td style={{ padding: '0.75rem 1rem 0.75rem 0' }}>
                        <div style={{ fontWeight: 500, wordBreak: 'break-all' }}>
                          {item.original_filename || item.filename}
                        </div>
                        {item.dataset_name && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                            📁 {item.dataset_name}
                          </div>
                        )}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', color: 'var(--text-muted)' }}>
                        {item.language || '—'}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', textAlign: 'right', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                        {formatDurationHoursMins(item.duration ?? null)}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', color: 'var(--text-muted)' }}>
                        {item.annotator_username || '—'}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', color: 'var(--text-muted)' }}>
                        {formatDate(item.uploaded_at)}
                      </td>
                      <td style={{ padding: '0.75rem 0', textAlign: 'center' }}>
                        {dlError ? (
                          <div>
                            <div style={{ color: '#ef4444', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                              ❌ {dlError}
                            </div>
                            <button
                              className="btn btn-secondary"
                              style={{ fontSize: '0.7rem', padding: '0.25rem 0.5rem' }}
                              onClick={() => handleDownload(item)}
                            >
                              Retry
                            </button>
                          </div>
                        ) : dlSuccess ? (
                          <span style={{ color: '#10b981', fontSize: '0.875rem', fontWeight: 600 }}>
                            ✅ Downloaded
                          </span>
                        ) : (
                          <button
                            className="btn btn-primary"
                            disabled={isDownloading}
                            onClick={() => handleDownload(item)}
                            style={{
                              fontSize: '0.8rem',
                              padding: '0.4rem 1rem',
                              opacity: isDownloading ? 0.7 : 1,
                              cursor: isDownloading ? 'wait' : 'pointer',
                              background: isDownloading
                                ? 'rgba(99,102,241,0.4)'
                                : 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                            }}
                          >
                            {isDownloading ? (
                              <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                <span style={{
                                  display: 'inline-block',
                                  width: '12px',
                                  height: '12px',
                                  border: '2px solid rgba(255,255,255,0.3)',
                                  borderTop: '2px solid white',
                                  borderRadius: '50%',
                                  animation: 'spin 0.7s linear infinite',
                                }} />
                                Downloading…
                              </span>
                            ) : (
                              '📦 Download ZIP'
                            )}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
