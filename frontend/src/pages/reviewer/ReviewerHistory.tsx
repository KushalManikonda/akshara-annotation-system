import { useQuery } from '@tanstack/react-query';
import { audioApi } from '../../services/api';
import { formatDurationHoursMins } from '../../utils/time';

export default function ReviewerHistory() {

  const { data: allAudio, isLoading } = useQuery({
    queryKey: ['audio'],
    queryFn: () => audioApi.getAll(),
  });

  if (isLoading) return <div style={{ padding: '2rem' }}>Loading history...</div>;

  // Show any task reviewed by this reviewer (approved or rejected)
  const myHistory = allAudio?.filter((a: any) => a.reviewed_by_me) || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div className="card glass-panel" style={{ minHeight: '600px' }}>
        <h2 style={{ margin: '0 0 1.5rem 0', fontSize: '1.25rem' }}>My Review History</h2>
        
        {myHistory.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            <p>You haven't reviewed any annotations yet.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-glass)', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '1rem' }}>File</th>
                  <th style={{ padding: '1rem' }}>Dataset</th>
                  <th style={{ padding: '1rem' }}>Annotator</th>
                  <th style={{ padding: '1rem' }}>Duration</th>
                  <th style={{ padding: '1rem' }}>My Decision</th>
                  <th style={{ padding: '1rem' }}>Consensus Status</th>
                  <th style={{ padding: '1rem' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {myHistory.map((task: any) => (
                  <tr key={task.id} style={{ borderBottom: '1px solid var(--border-glass)' }}>
                    <td style={{ padding: '1rem', fontWeight: 500 }}>{task.original_filename}</td>
                    <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{task.dataset_name || 'Dataset'}</td>
                    <td style={{ padding: '1rem', color: 'var(--text-main)', fontWeight: 500 }}>{task.annotator_username || '—'}</td>
                    <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{formatDurationHoursMins(task.duration)}</td>
                    <td style={{ padding: '1rem' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        <span style={{
                          padding: '0.25rem 0.5rem',
                          borderRadius: '9999px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          width: 'fit-content',
                          background: task.my_review_status === 'APPROVED' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                          color: task.my_review_status === 'APPROVED' ? '#34d399' : '#ef4444',
                        }}>
                          {task.my_review_status === 'APPROVED' ? '✅ Approved' : '❌ Returned'}
                        </span>
                        {task.my_review_status === 'REJECTED' && task.last_reviewer_comment && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            "{task.last_reviewer_comment}"
                          </div>
                        )}
                      </div>
                    </td>
                    <td style={{ padding: '1rem' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        <span style={{
                          padding: '0.25rem 0.5rem',
                          borderRadius: '9999px',
                          fontSize: '0.75rem',
                          width: 'fit-content',
                          background: task.status === 'COMPLETED' ? 'rgba(16, 185, 129, 0.1)' : 
                                      task.status === 'REWORK_REQUIRED' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(245, 158, 11, 0.1)',
                          color: task.status === 'COMPLETED' ? '#34d399' : 
                                 task.status === 'REWORK_REQUIRED' ? '#ef4444' : '#fbbf24',
                        }}>
                          {task.status}
                        </span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          {task.reviewed_count ?? 0}/{task.total_reviewers ?? 1} reviewers reviewed
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '1rem' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 500 }}>
                        ✓ Done
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
