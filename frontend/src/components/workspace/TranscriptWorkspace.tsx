
import { SegmentList } from './SegmentList';
import { RSMLReference } from './RSMLReference';
import type { Segment } from './types';

interface TranscriptWorkspaceProps {
  segments: Segment[];
  activeSegmentId: string | null;
  isReadOnly?: boolean;
  onUpdateSegment: (id: string, updates: Partial<Segment>) => void;
  onDeleteSegment: (id: string) => void;
  onSplitSegment: (id: string) => void;
  onSegmentClick: (id: string) => void;
}

export function TranscriptWorkspace(props: TranscriptWorkspaceProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="glass-panel" style={{ padding: '1rem 1.5rem', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>RSML Transcription</h3>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          {props.segments.length} segment{props.segments.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingRight: '0.5rem' }}>
        <SegmentList {...props} />
      </div>

      <div style={{ marginTop: 'auto', paddingTop: '1rem' }}>
        <RSMLReference />
      </div>
    </div>
  );
}
