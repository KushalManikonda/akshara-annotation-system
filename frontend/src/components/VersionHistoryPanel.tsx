import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { annotationsApi } from '../services/api';
import toast from 'react-hot-toast';

interface Version {
  id: string;
  version_number: number;
  transcript_snapshot: string;
  submitted_at: string;
  submitted_by: string;
}

import { formatDateIndian } from '../utils/time';

interface VersionHistoryPanelProps {
  audioId: string;
  isReviewer: boolean;
  onClose: () => void;
  onRestored?: () => void;
}

export default function VersionHistoryPanel({ audioId, isReviewer, onClose, onRestored }: VersionHistoryPanelProps) {
  const queryClient = useQueryClient();
  const [selectedVersion, setSelectedVersion] = useState<Version | null>(null);

  const { data: versions, isLoading } = useQuery({
    queryKey: ['versions', audioId],
    queryFn: () => annotationsApi.getVersions(audioId),
  });

  const restoreMutation = useMutation({
    mutationFn: (versionId: string) => annotationsApi.restoreVersion(audioId, versionId),
    onSuccess: () => {
      toast.success('Version restored successfully!');
      queryClient.invalidateQueries({ queryKey: ['audio', audioId] });
      if (onRestored) onRestored();
      onClose();
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to restore version');
    }
  });

  return (
    <div style={{
      position: 'fixed', top: 0, right: 0, bottom: 0, width: '400px',
      background: 'var(--bg-main)', borderLeft: '1px solid var(--border-glass)',
      zIndex: 1000, display: 'flex', flexDirection: 'column',
      boxShadow: '-4px 0 15px rgba(0,0,0,0.2)'
    }}>
      <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-glass)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>Version History</h3>
        <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-main)', cursor: 'pointer' }}>✕</button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
        {isLoading ? (
          <div>Loading versions...</div>
        ) : versions?.length === 0 ? (
          <div style={{ color: 'var(--text-muted)' }}>No previous versions found.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {versions?.map((v: Version) => (
              <div 
                key={v.id} 
                onClick={() => setSelectedVersion(v)}
                style={{ 
                  padding: '0.75rem', 
                  background: selectedVersion?.id === v.id ? 'rgba(59, 130, 246, 0.2)' : 'rgba(30, 41, 59, 0.3)',
                  border: selectedVersion?.id === v.id ? '1px solid var(--color-primary)' : '1px solid var(--border-glass)',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer'
                }}
              >
                <div style={{ fontWeight: 600 }}>Version {v.version_number}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {formatDateIndian(v.submitted_at)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selectedVersion && (
        <div style={{ borderTop: '1px solid var(--border-glass)', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>Preview (Version {selectedVersion.version_number})</div>
            <div style={{ 
              fontSize: '0.75rem', 
              background: 'rgba(0,0,0,0.2)', 
              padding: '0.5rem', 
              borderRadius: '4px',
              maxHeight: '150px',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              fontFamily: 'monospace'
            }}>
              {selectedVersion.transcript_snapshot}
            </div>
          </div>
          
          {!isReviewer && (
            <button 
              className="btn btn-primary"
              disabled={restoreMutation.isPending}
              onClick={() => restoreMutation.mutate(selectedVersion.id)}
            >
              {restoreMutation.isPending ? 'Restoring...' : `Restore to Version ${selectedVersion.version_number}`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
