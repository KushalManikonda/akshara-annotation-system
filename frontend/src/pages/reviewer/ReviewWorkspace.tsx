import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useEffect, useRef } from 'react';
import toast from 'react-hot-toast';
import { api, API_BASE_URL } from '../../services/api';
import { useAuthStore } from '../../store/auth';
import VersionHistoryPanel from '../../components/VersionHistoryPanel';
import WaveformPlayer from '../../components/WaveformPlayer';
import type { WaveformPlayerRef } from '../../components/WaveformPlayer';

export default function ReviewWorkspace() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, token } = useAuthStore();
  
  const [segments, setSegments] = useState<any[]>([]);
  const [originalSegments, setOriginalSegments] = useState<any[]>([]);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [comments, setComments] = useState('');
  const waveformRef = useRef<WaveformPlayerRef>(null);

  const { data: task, isLoading: isTaskLoading } = useQuery({
    queryKey: ['audio', id],
    queryFn: async () => {
      const res = await api.get(`/audio/${id}`);
      return res.data;
    },
    enabled: !!id,
  });

  const audioUrl = token && id ? `${API_BASE_URL}/audio/${id}/stream?token=${token}` : (task?.audio_url || '');

  useEffect(() => {
    if (task?.reviewed_by_me) {
      toast.error('You have already reviewed this task.');
      navigate('/reviewer/history');
    }
  }, [task, navigate]);

  const { data: annotation, isLoading: isAnnotationsLoading } = useQuery({
    queryKey: ['annotation', id],
    queryFn: async () => {
      try {
        const res = await api.get(`/annotations/audio/${id}`);
        return res.data;
      } catch (err) {
        return null;
      }
    },
    enabled: !!id,
    retry: false,
  });

  const effectiveAnnotation = annotation || (task ? {
    id: `auto-${task.id}`,
    audio_id: task.id,
    transcript: task.original_transcript || '[]',
    time_taken: 0
  } : null);

  useEffect(() => {
    if (effectiveAnnotation && segments.length === 0) {
      let parsed = [];
      const textToParse = effectiveAnnotation.transcript || effectiveAnnotation.transcription || '';
      try {
        parsed = JSON.parse(textToParse);
        if (!Array.isArray(parsed)) {
          parsed = [{ id: 'seg-0', transcript: textToParse, start: 0, end: 10 }];
        } else {
          parsed = parsed.map((s: any, i: number) => ({ ...s, id: s.id || `seg-${i}` }));
        }
      } catch (e) {
        parsed = [{ id: 'seg-0', transcript: textToParse, start: 0, end: 10 }];
      }
      setSegments(parsed);
      setOriginalSegments(JSON.parse(JSON.stringify(parsed))); // Deep copy
    }
  }, [effectiveAnnotation, segments.length]);

  const wordCount = comments.trim() ? comments.trim().split(/\s+/).filter(Boolean).length : 0;

  const reviewMutation = useMutation({
    mutationFn: async ({ action }: { action: 'approve' | 'reject' }) => {
      if (action === 'reject' && wordCount < 10) {
        toast.error("Please enter a review comment of at least 10 words before returning this annotation.");
        throw new Error("Please enter a review comment of at least 10 words before returning this annotation.");
      }

      let newText = '';
      if (isModified) {
        newText = segments.map(s => {
          if (!s.transcript || !s.transcript.trim()) return '';
          return `${s.start.toFixed(2)} - ${s.end.toFixed(2)}: ${s.transcript.trim()}`;
        }).filter(Boolean).join('\n');
      }

      await api.post('/annotations/review', {
        audio_id: id,
        reviewer_id: user?.id,
        review_status: action === 'approve' ? 'APPROVED' : 'REJECTED',
        review_comments: comments || undefined,
        corrected_transcript: isModified ? newText : undefined
      });
      
      return true;
    },
    onSuccess: (_data, variables) => {
      toast.success(`Annotation ${variables.action}d successfully!`);
      queryClient.invalidateQueries({ queryKey: ['audio'] });
      queryClient.invalidateQueries({ queryKey: ['annotations'] });
      queryClient.invalidateQueries({ queryKey: ['annotation', id] });
      navigate('/reviewer');
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.message || 'Failed to submit review');
    }
  });

  const handleSegmentChange = (index: number, field: string, val: any) => {
    const newSegments = [...segments];
    newSegments[index][field] = val;
    setSegments(newSegments);
  };

  const handleRegionUpdate = (regionId: string, start: number, end: number) => {
    setSegments(prev => prev.map(s => s.id === regionId ? { ...s, start, end } : s));
  };

  if (isTaskLoading || isAnnotationsLoading) return <div style={{ padding: '2rem' }}>Loading review data...</div>;
  if (!task || !effectiveAnnotation) return <div style={{ padding: '2rem', color: 'red' }}>Task not found</div>;

  const isModified = JSON.stringify(segments) !== JSON.stringify(originalSegments);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-main)' }}>
      
      {/* Top Bar */}
      <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-glass)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button className="btn btn-secondary" onClick={() => navigate('/reviewer')}>
          ← Back to Queue
        </button>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button className="btn btn-secondary" onClick={() => setShowVersionHistory(true)}>⏳ Version History</button>
          <button 
            className="btn btn-secondary"
            style={{ color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.3)' }}
            disabled={reviewMutation.isPending}
            onClick={() => reviewMutation.mutate({ action: 'reject' })}
          >
            ❌ Reject
          </button>
          <button 
            className="btn btn-primary"
            style={{ background: 'var(--color-success)' }}
            disabled={reviewMutation.isPending}
            onClick={() => reviewMutation.mutate({ action: 'approve' })}
          >
            {reviewMutation.isPending ? 'Processing...' : '✅ Approve'}
          </button>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        
        {/* Left Pane: Audio, Waveform & Review Panel */}
        <div style={{ width: '50%', borderRight: '1px solid var(--border-glass)', display: 'flex', flexDirection: 'column', padding: '1rem', overflowY: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div>
              <h2 style={{ margin: '0 0 0.25rem 0', fontSize: '1.25rem' }}>Review Task #{id?.slice(0, 8)}...</h2>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                {task.original_filename}
              </div>
            </div>
          </div>

          {audioUrl ? (
            <WaveformPlayer
              ref={waveformRef}
              audioUrl={audioUrl}
              regions={segments.map(s => ({ id: s.id, start: s.start || 0, end: s.end || (s.start || 0) + 5 }))}
              onRegionUpdate={handleRegionUpdate}
              onRegionClicked={(id) => {
                const index = segments.findIndex(s => s.id === id);
                if (index >= 0) {
                  document.getElementById(`segment-card-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
              }}
            />
          ) : (
            <div style={{ padding: '1rem', background: 'rgba(239,68,68,0.1)', color: '#ef4444', borderRadius: 'var(--radius-md)' }}>
              Audio file is missing or unavailable.
            </div>
          )}

          {/* Reviewer Comments Panel */}
          <div className="card glass-panel" style={{ marginTop: '2rem', padding: '1.5rem' }}>
             <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem' }}>Reviewer Comments</h3>
             {isModified && (
                <div style={{ fontSize: '0.875rem', color: 'var(--color-primary)', marginBottom: '1rem' }}>
                  * You have edited the annotator's transcription.
                </div>
             )}
             <textarea 
               value={comments}
               onChange={(e) => setComments(e.target.value)}
               placeholder="Add a mandatory comment of at least 10 words if returning/rejecting..."
               style={{
                 width: '100%',
                 height: '100px',
                 padding: '0.75rem',
                 background: 'rgba(0,0,0,0.2)',
                 border: '1px solid var(--border-glass)',
                 borderRadius: 'var(--radius-md)',
                 color: 'var(--text-main)',
                 fontFamily: 'var(--font-sans)',
                 resize: 'vertical'
               }}
             />
             <div style={{
               display: 'flex',
               justifyContent: 'space-between',
               marginTop: '0.5rem',
               fontSize: '0.75rem',
               color: wordCount >= 10 ? '#34d399' : '#f59e0b'
             }}>
               <span>Word count: {wordCount} / 10 required for return</span>
               {wordCount < 10 && <span style={{ color: '#ef4444' }}>Min 10 words required to return task</span>}
             </div>
          </div>
        </div>

        {/* Right Pane: Transcripts */}
        <div style={{ width: '50%', background: 'rgba(15, 23, 42, 0.3)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-glass)', textAlign: 'center', fontWeight: 600, color: 'var(--primary-main)', background: 'rgba(59, 130, 246, 0.05)' }}>
            Transcript Review
          </div>
          
          <div style={{ flex: 1, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {segments.map((seg, idx) => {
              const originalSeg = originalSegments[idx] || {};
              const isTranscriptModified = seg.transcript !== originalSeg.transcript;
              
              return (
                <div key={seg.id} id={`segment-card-${seg.id}`} className="card glass-panel" style={{ padding: '1rem', border: '1px solid var(--border-glass)' }}>
                  
                  {/* Segment Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'var(--primary-main)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 'bold' }}>
                        {idx + 1}
                      </div>
                      <input 
                        type="number" step="0.1" 
                        value={seg.start} onChange={e => handleSegmentChange(idx, 'start', parseFloat(e.target.value))}
                        style={{ background: 'rgba(0,0,0,0.3)', border: 'none', color: 'white', padding: '0.25rem 0.5rem', borderRadius: '4px', width: '80px', fontFamily: 'monospace' }} 
                      />
                      <select 
                        value={seg.speaker || ''} 
                        onChange={e => handleSegmentChange(idx, 'speaker', e.target.value)}
                        style={{ background: 'transparent', color: 'var(--text-main)', border: 'none', outline: 'none' }}
                      >
                        <option value="Speaker 0 (Female)">Speaker 0 (Female)</option>
                        <option value="Speaker 1 (Male)">Speaker 1 (Male)</option>
                      </select>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <input 
                        type="number" step="0.1" 
                        value={seg.end} onChange={e => handleSegmentChange(idx, 'end', parseFloat(e.target.value))}
                        style={{ background: 'rgba(0,0,0,0.3)', border: 'none', color: 'white', padding: '0.25rem 0.5rem', borderRadius: '4px', width: '80px', fontFamily: 'monospace' }} 
                      />
                    </div>
                  </div>

                  {/* Dual Sections: Original Transcript vs Annotated View */}
                  <div style={{ display: 'flex', gap: '1rem' }}>
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', textTransform: 'uppercase' }}>Original Transcript</div>
                      <div style={{
                        width: '100%',
                        height: '100px',
                        background: 'rgba(255,255,255,0.02)',
                        border: '1px dashed var(--border-glass)',
                        color: 'var(--text-muted)',
                        padding: '0.75rem',
                        borderRadius: 'var(--radius-sm)',
                        overflowY: 'auto',
                        whiteSpace: 'pre-wrap'
                      }}>
                        {originalSeg.transcript || ''}
                      </div>
                    </div>

                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', textTransform: 'uppercase' }}>Annotated View</div>
                      <textarea
                        value={seg.transcript || ''}
                        onChange={(e) => handleSegmentChange(idx, 'transcript', e.target.value)}
                        style={{
                          width: '100%',
                          height: '100px',
                          background: 'rgba(0,0,0,0.2)',
                          border: '1px solid var(--border-glass)',
                          color: isTranscriptModified ? 'var(--color-primary)' : 'var(--text-main)',
                          padding: '0.75rem',
                          borderRadius: 'var(--radius-sm)',
                          resize: 'vertical',
                          fontFamily: 'var(--font-sans)'
                        }}
                      />
                    </div>
                  </div>

                </div>
              );
            })}
          </div>
        </div>
      </div>

      {showVersionHistory && id && (
        <VersionHistoryPanel 
          audioId={id} 
          isReviewer={true} 
          onClose={() => setShowVersionHistory(false)} 
        />
      )}
    </div>
  );
}
