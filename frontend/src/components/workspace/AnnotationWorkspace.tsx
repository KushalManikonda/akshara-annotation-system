import {useState, useEffect, useCallback, useRef} from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { TaskHeader } from './TaskHeader';
import { WorkspaceToolbar } from './WorkspaceToolbar';
import { AudioWorkspace } from './AudioWorkspace';
import { TranscriptWorkspace } from './TranscriptWorkspace';
import type { Segment } from './types';
import { audioApi, annotationsApi, queueApi } from '../../services/api';
import toast from 'react-hot-toast';
import { useUndoRedo } from '../../hooks/useUndoRedo';

export function AnnotationWorkspace() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { state: segments, set: setSegments, undo, redo, reset: resetSegments } = useUndoRedo<Segment[]>([]);
  const [activeSegmentId, setActiveSegmentId] = useState<string | null>(null);
  
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [taskStatus, setTaskStatus] = useState<string>('ASSIGNED');
  const [reviewerComment, setReviewerComment] = useState<string | null>(null);
  const [audioFilename, setAudioFilename] = useState<string>('');
  const startTime = useRef(Date.now());

  // Load Task and Annotation Data
  useEffect(() => {
    if (!id) return;
    let isMounted = true;

    const loadData = async () => {
      try {
        setIsLoading(true);
        // We ensure the task is started/locked
        await audioApi.startTask(id);
        const audioDetails = await audioApi.getById(id);
        if (isMounted) {
          setTaskStatus(audioDetails.status);
          setReviewerComment(audioDetails.last_reviewer_comment || null);
          setAudioFilename(audioDetails.original_filename || audioDetails.filename || '');
        }

        let initialSegments: Segment[] = [];
        
        // Try fetching existing annotation first
        const existingAnnotation = await annotationsApi.getByAudio(id);
        
        if (existingAnnotation && existingAnnotation.transcript) {
          try {
            initialSegments = JSON.parse(existingAnnotation.transcript);
          } catch(e) {
            console.error("Failed to parse annotation transcript JSON", e);
          }
        } 
        
        // If no annotation or empty, fallback to audio file's original_transcript (if available)
        if (initialSegments.length === 0 && audioDetails.original_transcript) {
          try {
            const raw = JSON.parse(audioDetails.original_transcript);
            initialSegments = Array.isArray(raw) ? raw : [];
          } catch(e) {}
        }

        // Normalize raw segments to match Segment type robustly
        let mappedSegments = initialSegments.map((s, idx) => ({
          id: (s.id ?? (idx + 1)).toString(),
          start: Number(s.start) || 0,
          end: Number(s.end) || 5,
          speaker: s.speaker || 'Speaker 0 (Female)',
          transcript: s.transcript ?? s.text ?? '',
          done: !!s.done
        }));

        // Default empty segment if absolutely none
        if (mappedSegments.length === 0) {
          mappedSegments = [{
            id: "1",
            start: 0,
            end: 5,
            speaker: 'Speaker 0 (Female)',
            transcript: '',
            done: false
          }];
        }

        if (isMounted) {
          resetSegments(mappedSegments);
          setIsLoading(false);
        }
      } catch (err: any) {
        if (isMounted) {
          toast.error("Failed to load task. You may not have access or lock expired.");
          navigate('/annotator');
        }
      }
    };
    
    loadData();

    return () => { isMounted = false; };
  }, [id, navigate]);

  // Heartbeat Timer (every 30s)
  useEffect(() => {
    if (!id || isLoading) return;
    const intervalId = setInterval(() => {
      queueApi.heartbeat(id).catch(err => {
        console.error("Heartbeat failed", err);
      });
    }, 30000);
    return () => clearInterval(intervalId);
  }, [id, isLoading]);

  // Actions
  const handleSaveDraft = useCallback(async () => {
    if (!id) return;
    setIsSaving(true);
    try {
      const timeTaken = (Date.now() - startTime.current) / 1000;
      await annotationsApi.save({
        audio_id: id,
        transcript: JSON.stringify(segments),
        time_taken: timeTaken
      });
      setHasUnsavedChanges(false);
      toast.success('Draft saved successfully');
    } catch (err) {
      toast.error('Failed to save draft');
    } finally {
      setIsSaving(false);
    }
  }, [id, segments]);

  const handleSubmit = useCallback(async () => {
    if (!id) return;
    
    // Validation
    // Temporarily disabled requirement: SUBMISSION MUST NOT DEPEND ON ALL SEGMENTS BEING MARKED DONE.
    const hasText = segments.some(s => s.transcript.trim().length > 0);
    if (!hasText) {
      toast.error("Transcript cannot be empty.");
      return;
    }

    try {
      // 1. Save final annotation
      const timeTaken = (Date.now() - startTime.current) / 1000;
      await annotationsApi.save({
        audio_id: id,
        transcript: JSON.stringify(segments),
        time_taken: timeTaken
      });
      
      // 2. Patch status to SUBMITTED
      await annotationsApi.submit(id);
      toast.success('Task submitted successfully');
      navigate('/annotator/dashboard');
    } catch (err) {
      toast.error('Failed to submit task');
    }
  }, [id, segments, navigate]);

  const handleAbandon = useCallback(async () => {
    if (!id) return;
    try {
      await audioApi.updateStatus(id, 'UNASSIGNED');
      toast.success('Task abandoned');
      navigate('/annotator/dashboard');
    } catch (err) {
      toast.error('Failed to abandon task');
    }
  }, [id, navigate]);

  // Segment Handlers
  const handleSegmentUpdate = (segId: string, updates: Partial<Segment>) => {
    setSegments(prev => prev.map(s => {
      if (s.id === segId) {
        const updated = { ...s, ...updates };
        return updated;
      }
      return s;
    }));
    setHasUnsavedChanges(true);
    
    // Auto-save on checking "done"
    if (updates.done === true) {
      // Trigger a save after state updates (we use a timeout to let React batch)
      setTimeout(() => {
         document.getElementById('hidden-save-btn')?.click();
      }, 0);
    }
  };

  const handleDeleteSegment = (segId: string) => {
    setSegments(prev => prev.filter(s => s.id !== segId));
    if (activeSegmentId === segId) setActiveSegmentId(null);
    setHasUnsavedChanges(true);
  };

  const handleSplitSegment = (segId: string) => {
    setSegments(prev => {
      const idx = prev.findIndex(s => s.id === segId);
      if (idx === -1) return prev;
      const target = prev[idx];
      const mid = target.start + (target.end - target.start) / 2;
      
      const p1: Segment = { ...target, end: mid };
      const p2: Segment = { ...target, id: 'wavesurfer_' + Math.random().toString(36).substr(2, 9), start: mid };
      
      const newSegs = [...prev];
      newSegs.splice(idx, 1, p1, p2);
      return newSegs.sort((a, b) => a.start - b.start);
    });
    setHasUnsavedChanges(true);
  };

  const handleWaveformRegionUpdate = (segId: string, start: number, end: number) => {
    setSegments(prev => prev.map(s => s.id === segId ? { ...s, start, end } : s).sort((a, b) => a.start - b.start));
    setHasUnsavedChanges(true);
  };

  const handleAddSegment = () => {
    const newId = 'wavesurfer_' + Math.random().toString(36).substr(2, 9);
    setSegments(prev => {
      const activeIdx = activeSegmentId ? prev.findIndex(s => s.id === activeSegmentId) : -1;
      let start = 0;
      let end = 2;
      let insertIndex = prev.length;

      if (activeIdx !== -1) {
        const activeSeg = prev[activeIdx];
        const nextSeg = prev[activeIdx + 1];
        start = activeSeg.end;
        if (nextSeg && nextSeg.start > activeSeg.end) {
          end = Math.min(start + 2, nextSeg.start);
        } else {
          end = start + 2;
        }
        insertIndex = activeIdx + 1;
      } else if (prev.length > 0) {
        start = prev[prev.length - 1].end;
        end = start + 2;
      }

      const newSeg: Segment = {
        id: newId,
        start,
        end,
        transcript: '',
        speaker: activeIdx !== -1 ? prev[activeIdx].speaker : 'Speaker 0 (Female)',
        done: false
      };

      const newSegs = [...prev];
      newSegs.splice(insertIndex, 0, newSeg);
      return newSegs;
    });

    setActiveSegmentId(newId);
    setHasUnsavedChanges(true);
    toast.success('New segment added');
  };

  const handleRevert = async () => {
    if (!id || !window.confirm("Are you sure you want to revert to the original transcript? This will discard your current edits.")) return;
    try {
      const audioDetails = await audioApi.getById(id);
      if (audioDetails.original_transcript) {
        const raw = JSON.parse(audioDetails.original_transcript);
        const original = Array.isArray(raw) ? raw : [];
        setSegments(original);
        setHasUnsavedChanges(true);
        toast.success("Reverted to original transcript.");
      } else {
        toast.error("No original transcript found.");
      }
    } catch (e) {
      toast.error("Failed to revert.");
    }
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+Z for undo, Ctrl+Y or Ctrl+Shift+Z for redo
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        if (e.shiftKey) {
          e.preventDefault();
          redo();
        } else {
          e.preventDefault();
          undo();
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
        e.preventDefault();
        redo();
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'd') {
        e.preventDefault();
        if (activeSegmentId) {
          setSegments(prev => {
            const seg = prev.find(s => s.id === activeSegmentId);
            if (!seg) return prev;
            const duration = seg.end - seg.start;
            const newSeg: Segment = {
              ...seg,
              id: 'wavesurfer_' + Math.random().toString(36).substr(2, 9),
              start: seg.end,
              end: seg.end + duration,
              done: false
            };
            return [...prev, newSeg].sort((a, b) => a.start - b.start);
          });
          setHasUnsavedChanges(true);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undo, redo]);

  const isReadOnly = taskStatus === 'SUBMITTED' || taskStatus === 'COMPLETED';

  if (isLoading) {
    return <div className="container" style={{ textAlign: 'center', paddingTop: '4rem' }}>Loading Workspace...</div>;
  }

  return (
    <div className="container" style={{ maxWidth: '1600px', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <button id="hidden-save-btn" style={{ display: 'none' }} onClick={handleSaveDraft} />
      <TaskHeader taskId={id || ''} hasUnsavedChanges={hasUnsavedChanges} taskStatus={taskStatus} />

      {isReadOnly && (
        <div style={{
          padding: '0.75rem 1.25rem',
          margin: '0.5rem 0',
          background: 'rgba(245, 158, 11, 0.15)',
          borderLeft: '4px solid #f59e0b',
          color: '#fbbf24',
          borderRadius: '4px',
          fontSize: '0.875rem',
          fontWeight: 600,
        }}>
          🔒 Read-Only Mode: This annotation is currently {taskStatus === 'COMPLETED' ? 'fully approved' : 'submitted for review'} and cannot be edited.
        </div>
      )}

      {taskStatus === 'REWORK_REQUIRED' && reviewerComment && (
        <div style={{
          padding: '0.75rem 1.25rem',
          margin: '0.5rem 0',
          background: 'rgba(239, 68, 68, 0.15)',
          borderLeft: '4px solid #ef4444',
          color: '#fca5a5',
          borderRadius: '4px',
          fontSize: '0.875rem',
        }}>
          <strong>⚠️ Returned by Reviewer for Rework: </strong>"{reviewerComment}"
        </div>
      )}

      {!isReadOnly && (
        <WorkspaceToolbar 
          onSave={handleSaveDraft}
          onSubmit={handleSubmit}
          onAbandon={handleAbandon}
          isSaving={isSaving}
          hasUnsavedChanges={hasUnsavedChanges}
        />
      )}
      
      <div style={{ display: 'flex', gap: '1.5rem', flex: 1, minHeight: 0 }}>
        <div style={{ flex: '1 1 60%', minWidth: '400px', display: 'flex', flexDirection: 'column' }}>
          <AudioWorkspace 
            audioId={id || ''}
            filename={audioFilename}
            segments={segments}
            activeSegmentId={activeSegmentId}
            isReadOnly={isReadOnly}
            onSegmentUpdate={handleWaveformRegionUpdate}
            onSegmentClick={setActiveSegmentId}
            onAddSegment={handleAddSegment}
            onRevert={handleRevert}
            onSaveDraft={handleSaveDraft}
          />
        </div>
        
        <div style={{ flex: '1 1 40%', minWidth: '400px' }}>
          <TranscriptWorkspace 
            segments={segments}
            activeSegmentId={activeSegmentId}
            isReadOnly={isReadOnly}
            onUpdateSegment={handleSegmentUpdate}
            onDeleteSegment={handleDeleteSegment}
            onSplitSegment={handleSplitSegment}
            onSegmentClick={setActiveSegmentId}
          />
        </div>
      </div>
    </div>
  );
}
