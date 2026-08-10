import { useRef, useEffect, useState } from 'react';
import WaveformPlayer, { type WaveformPlayerRef } from '../WaveformPlayer';
import type { Segment } from './types';
import { useAuthStore } from '../../store/auth';
import { API_BASE_URL } from '../../services/api';
import { Plus, RotateCcw, Keyboard, X } from 'lucide-react';

interface AudioWorkspaceProps {
  audioId: string;
  filename?: string;
  segments: Segment[];
  activeSegmentId: string | null;
  isReadOnly?: boolean;
  onSegmentUpdate: (id: string, start: number, end: number) => void;
  onSegmentClick: (id: string) => void;
  onAddSegment: () => void;
  onRevert: () => void;
  onSaveDraft: () => void;
}

export function AudioWorkspace({
  audioId,
  filename,
  segments,
  activeSegmentId,
  isReadOnly = false,
  onSegmentUpdate,
  onSegmentClick,
  onAddSegment,
  onRevert,
}: AudioWorkspaceProps) {
  const token = useAuthStore(state => state.token);
  const playerRef = useRef<WaveformPlayerRef>(null);
  const [showShortcuts, setShowShortcuts] = useState(false);

  // Derive regions from segments
  const regions = segments.map(s => ({
    id: s.id,
    start: s.start,
    end: s.end,
    color: s.done ? 'rgba(72, 187, 120, 0.25)' : 'rgba(99, 179, 237, 0.25)'
  }));

  const audioUrl = token ? `${API_BASE_URL}/audio/${audioId}/stream?token=${token}` : '';

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger playback hotkeys if user is typing in an input/textarea/select
      const activeEl = document.activeElement;
      if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.tagName === 'SELECT')) {
        return;
      }

      if (e.key === ' ' || e.key.toLowerCase() === 'k') {
        e.preventDefault();
        playerRef.current?.playPause();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        playerRef.current?.skip(-10);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        playerRef.current?.skip(10);
      } else if (e.key === 'Escape') {
        setShowShortcuts(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const shortcutsList = [
    { key: 'Spacebar / K', desc: 'Play / Pause audio playback' },
    { key: '← Left Arrow', desc: 'Seek backward 10 seconds (-10s)' },
    { key: '→ Right Arrow', desc: 'Seek forward 10 seconds (+10s)' },
    { key: 'Ctrl + Z', desc: 'Undo annotation change' },
    { key: 'Ctrl + Y / Ctrl + Shift + Z', desc: 'Redo annotation change' },
    { key: 'Ctrl + D', desc: 'Duplicate current active segment' },
    { key: 'Esc', desc: 'Close shortcuts modal' },
  ];

  return (
    <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', position: 'relative' }}>
      
      {/* Header Toolbar */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        padding: '0.75rem 1rem',
        borderBottom: '1px solid var(--border-solid)' 
      }}>
        <h3 style={{ 
          margin: 0, 
          fontSize: '1rem', 
          display: 'flex', 
          alignItems: 'center', 
          gap: '0.5rem',
          maxWidth: '300px',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap' 
        }}>
          🎵 <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{filename || audioId.split('-')[0]}</span>
        </h3>
        
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-secondary" onClick={onRevert} disabled={isReadOnly} title="Revert to original">
            <RotateCcw size={14} /> Revert
          </button>
          <button className="btn btn-primary" onClick={onAddSegment} disabled={isReadOnly} title="Add new segment">
            <Plus size={14} /> Add Segment
          </button>
          <button className="btn btn-secondary" onClick={() => setShowShortcuts(true)} title="View Keyboard Shortcuts">
            <Keyboard size={14} /> Shortcuts
          </button>
        </div>
      </div>

      {/* Waveform Area */}
      <div style={{ flex: 1, padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {token ? (
          <WaveformPlayer
            ref={playerRef}
            audioUrl={audioUrl}
            regions={regions}
            activeRegionId={activeSegmentId || undefined}
            isReadOnly={isReadOnly}
            onRegionUpdate={onSegmentUpdate}
            onRegionClicked={onSegmentClick}
          />
        ) : (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            Authenticating audio stream...
          </div>
        )}
      </div>

      {/* Keyboard Shortcuts Modal Overlay */}
      {showShortcuts && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 2000,
          padding: '1rem'
        }}>
          <div className="card glass-panel" style={{
            width: '100%',
            maxWidth: '520px',
            padding: '1.75rem',
            background: '#181825',
            border: '1px solid var(--border-glass)',
            boxShadow: '0 12px 32px rgba(0,0,0,0.7)',
            borderRadius: 'var(--radius-lg)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                <Keyboard size={20} style={{ color: 'var(--color-primary)' }} />
                <h3 style={{ margin: 0, fontSize: '1.125rem', fontWeight: 600 }}>Keyboard Shortcuts</h3>
              </div>
              <button 
                onClick={() => setShowShortcuts(false)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 0 }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem', maxHeight: '360px', overflowY: 'auto' }}>
              {shortcutsList.map((item, idx) => (
                <div key={idx} style={{
                  display: 'flex',
                  justify: 'space-between',
                  alignItems: 'center',
                  padding: '0.625rem 0.875rem',
                  background: 'rgba(255, 255, 255, 0.04)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid rgba(255, 255, 255, 0.08)'
                }}>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{item.desc}</span>
                  <span style={{
                    fontFamily: 'monospace',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    background: 'rgba(99, 102, 241, 0.2)',
                    color: '#a5b4fc',
                    border: '1px solid rgba(99, 102, 241, 0.4)',
                    padding: '2px 8px',
                    borderRadius: '4px'
                  }}>
                    {item.key}
                  </span>
                </div>
              ))}
            </div>

            <div style={{ marginTop: '1.5rem', textAlign: 'right' }}>
              <button className="btn btn-primary" onClick={() => setShowShortcuts(false)} style={{ padding: '0.4rem 1.25rem', fontSize: '0.85rem' }}>
                Got it
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
