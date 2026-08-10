import { useState, useEffect } from 'react';
import type { Segment } from './types';
import { RSMLSegmentEditor } from './RSMLSegmentEditor';
import { NormalizedPreview } from './NormalizedPreview';
import { Trash2, SplitSquareHorizontal, CheckCircle2 } from 'lucide-react';

interface SegmentCardProps {
  segment: Segment;
  index: number;
  isActive: boolean;
  isReadOnly?: boolean;
  onUpdate: (id: string, updates: Partial<Segment>) => void;
  onDelete: (id: string) => void;
  onSplit: (id: string) => void;
  onClick: (id: string) => void;
}

const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 1000);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
};

const parseTime = (timeStr: string): number | null => {
  const parts = timeStr.split(':');
  if (parts.length === 2) {
    const mins = parseInt(parts[0], 10);
    const secs = parseFloat(parts[1]);
    if (!isNaN(mins) && !isNaN(secs)) return mins * 60 + secs;
  }
  const raw = parseFloat(timeStr);
  return isNaN(raw) ? null : raw;
};

export function SegmentCard({ segment, index, isActive, isReadOnly = false, onUpdate, onDelete, onSplit, onClick }: SegmentCardProps) {
  const [startStr, setStartStr] = useState(formatTime(segment.start));
  const [endStr, setEndStr] = useState(formatTime(segment.end));
  const isDisabled = segment.done || isReadOnly;

  useEffect(() => {
    setStartStr(formatTime(segment.start));
    setEndStr(formatTime(segment.end));
  }, [segment.start, segment.end]);

  const handleStartChange = (val: string) => {
    setStartStr(val);
    const num = parseTime(val);
    if (num !== null && num < segment.end) onUpdate(segment.id, { start: num });
  };

  const handleEndChange = (val: string) => {
    setEndStr(val);
    const num = parseTime(val);
    if (num !== null && num > segment.start) onUpdate(segment.id, { end: num });
  };

  return (
    <div 
      className={`card segment-card ${isActive ? 'active' : ''} ${segment.done ? 'done' : ''}`}
      onClick={() => onClick(segment.id)}
      style={{ 
        cursor: 'pointer',
        padding: '1rem',
        marginBottom: '1rem',
        borderLeft: isActive ? '4px solid var(--color-primary)' : '4px solid transparent',
        background: segment.done ? 'rgba(72, 187, 120, 0.05)' : (isActive ? 'rgba(99, 102, 241, 0.05)' : 'var(--bg-card)'),
        borderColor: isActive ? 'var(--color-primary)' : (segment.done ? 'rgba(72, 187, 120, 0.3)' : 'var(--border-solid)'),
        transition: 'all var(--transition-fast)'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ 
            background: 'var(--bg-secondary)', 
            color: 'var(--text-muted)', 
            borderRadius: '50%', 
            width: '24px', 
            height: '24px', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            fontSize: '0.75rem',
            fontWeight: 'bold'
          }}>
            {index + 1}
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem', fontFamily: 'monospace', fontSize: '0.85rem' }} onClick={e => e.stopPropagation()}>
            <input 
              type="text" 
              value={startStr} 
              onChange={e => handleStartChange(e.target.value)}
              disabled={isDisabled}
              style={{ width: '65px', background: 'rgba(0,0,0,0.2)', color: 'var(--text-muted)', border: '1px solid var(--border-solid)', borderRadius: '3px', padding: '0.1rem 0.2rem', textAlign: 'center' }}
            />
            <span style={{ color: 'var(--text-muted)' }}>-</span>
            <input 
              type="text" 
              value={endStr} 
              onChange={e => handleEndChange(e.target.value)}
              disabled={isDisabled}
              style={{ width: '65px', background: 'rgba(0,0,0,0.2)', color: 'var(--text-muted)', border: '1px solid var(--border-solid)', borderRadius: '3px', padding: '0.1rem 0.2rem', textAlign: 'center' }}
            />
          </div>
          <select 
            value={segment.speaker} 
            onChange={(e) => onUpdate(segment.id, { speaker: e.target.value })}
            disabled={isDisabled}
            style={{ 
              background: 'rgba(0,0,0,0.2)', 
              color: 'var(--text-main)', 
              border: '1px solid var(--border-solid)',
              borderRadius: 'var(--radius-sm)',
              padding: '0.2rem 0.5rem',
              fontSize: '0.85rem'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <option value="Speaker 0 (Female)" style={{ color: 'black' }}>Speaker 0 (Female)</option>
            <option value="Speaker 0 (Male)" style={{ color: 'black' }}>Speaker 0 (Male)</option>
            <option value="Speaker 1 (Female)" style={{ color: 'black' }}>Speaker 1 (Female)</option>
            <option value="Speaker 1 (Male)" style={{ color: 'black' }}>Speaker 1 (Male)</option>
            <option value="Speaker 2 (Female)" style={{ color: 'black' }}>Speaker 2 (Female)</option>
            <option value="Speaker 2 (Male)" style={{ color: 'black' }}>Speaker 2 (Male)</option>
            <option value="Overlap" style={{ color: 'black' }}>Overlap</option>
            <option value="Unknown" style={{ color: 'black' }}>Unknown</option>
          </select>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }} onClick={(e) => e.stopPropagation()}>
          <button 
            className="btn btn-secondary" 
            style={{ padding: '0.3rem', fontSize: '0.75rem' }}
            onClick={() => onSplit(segment.id)}
            disabled={isDisabled}
            title="Split Segment"
          >
            <SplitSquareHorizontal size={14} />
          </button>
          <button 
            className="btn btn-danger" 
            style={{ padding: '0.3rem', fontSize: '0.75rem' }}
            onClick={() => {
              if (window.confirm('Delete this segment?')) {
                onDelete(segment.id);
              }
            }}
            disabled={isDisabled}
            title="Delete Segment"
          >
            <Trash2 size={14} />
          </button>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', marginLeft: '0.5rem', cursor: isReadOnly ? 'not-allowed' : 'pointer', fontSize: '0.85rem', color: segment.done ? '#48bb78' : 'var(--text-muted)' }}>
            <input 
              type="checkbox" 
              checked={segment.done} 
              onChange={(e) => !isReadOnly && onUpdate(segment.id, { done: e.target.checked })}
              disabled={isDisabled}
              style={{ accentColor: '#48bb78', width: '16px', height: '16px' }}
            />
            {segment.done ? <><CheckCircle2 size={14}/> Done</> : 'Done'}
          </label>
        </div>
      </div>

      <div onClick={(e) => e.stopPropagation()}>
        <RSMLSegmentEditor 
          value={segment.transcript} 
          onChange={(val) => onUpdate(segment.id, { transcript: val })}
          disabled={isDisabled}
          readOnly={isReadOnly}
        />
        
        <div style={{ 
          marginTop: '0.75rem', 
          padding: '0.75rem', 
          background: 'rgba(0,0,0,0.2)', 
          borderRadius: 'var(--radius-md)',
          border: '1px solid rgba(255,255,255,0.05)',
          minHeight: '40px'
        }}>
          <NormalizedPreview value={segment.transcript} />
        </div>
      </div>
    </div>
  );
}
