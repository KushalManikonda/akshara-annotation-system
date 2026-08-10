import {useEffect, useRef} from 'react';
import type { Segment } from './types';
import { SegmentCard } from './SegmentCard';

interface SegmentListProps {
  segments: Segment[];
  activeSegmentId: string | null;
  isReadOnly?: boolean;
  onUpdateSegment: (id: string, updates: Partial<Segment>) => void;
  onDeleteSegment: (id: string) => void;
  onSplitSegment: (id: string) => void;
  onSegmentClick: (id: string) => void;
}

export function SegmentList({ segments, activeSegmentId, isReadOnly = false, onUpdateSegment, onDeleteSegment, onSplitSegment, onSegmentClick }: SegmentListProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to active segment
  useEffect(() => {
    if (activeSegmentId && containerRef.current) {
      const activeEl = containerRef.current.querySelector(`[data-segment-id="${activeSegmentId}"]`);
      if (activeEl) {
        activeEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [activeSegmentId]);

  if (segments.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
        No segments yet. Click and drag on the waveform to create one.
      </div>
    );
  }

  return (
    <div ref={containerRef} style={{ display: 'flex', flexDirection: 'column', paddingBottom: '2rem' }}>
      {segments.map((seg, idx) => (
        <div key={seg.id} data-segment-id={seg.id}>
          <SegmentCard
            segment={seg}
            index={idx}
            isActive={seg.id === activeSegmentId}
            isReadOnly={isReadOnly}
            onUpdate={onUpdateSegment}
            onDelete={onDeleteSegment}
            onSplit={onSplitSegment}
            onClick={onSegmentClick}
          />
        </div>
      ))}
    </div>
  );
}
