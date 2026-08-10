import { useQuery } from '@tanstack/react-query';
import { audioApi } from '../../services/api';
import { useAuthStore } from '../../store/auth';
import { useNavigate } from 'react-router-dom';
import { formatDurationHoursMins } from '../../utils/time';

export default function AnnotatorHistory() {
  const { user } = useAuthStore();
  const navigate = useNavigate();

  const { data: allAudio, isLoading } = useQuery({
    queryKey: ['audio'],
    queryFn: () => audioApi.getAll(),
  });

  if (isLoading) return <div style={{ padding: '2rem' }}>Loading history...</div>;

  // Filter tasks assigned to this user that have been submitted, approved, or returned
  const myHistory = allAudio?.filter((a: any) => 
    a.assigned_to === user?.id && 
    (a.status === 'SUBMITTED' || a.status === 'COMPLETED' || a.status === 'REWORK_REQUIRED' || a.status === 'IN_PROGRESS')
  ) || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div className="card glass-panel" style={{ minHeight: '600px' }}>
        <h2 style={{ margin: '0 0 1.5rem 0', fontSize: '1.25rem' }}>My Annotation History</h2>
        
        {myHistory.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            <p>You haven't submitted any annotations yet.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-glass)', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '1rem' }}>File</th>
                  <th style={{ padding: '1rem' }}>Dataset</th>
                  <th style={{ padding: '1rem' }}>Language</th>
                  <th style={{ padding: '1rem' }}>Duration</th>
                  <th style={{ padding: '1rem' }}>Lifecycle & Reviewer Feedback</th>
                  <th style={{ padding: '1rem' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {myHistory.map((task: any) => {
                  const statusLabel = 
                    task.status === 'COMPLETED' ? 'APPROVED / SUCCESS' :
                    task.status === 'REWORK_REQUIRED' ? 'RETURNED (Awaiting Rework)' :
                    task.status === 'IN_PROGRESS' ? 'REWORK IN PROGRESS' :
                    'SUBMITTED / UNDER REVIEW';
                  
                  const statusColor = 
                    task.status === 'COMPLETED' ? '#34d399' :
                    task.status === 'REWORK_REQUIRED' ? '#ef4444' :
                    task.status === 'IN_PROGRESS' ? '#60a5fa' : '#fbbf24';

                  return (
                    <tr key={task.id} style={{ borderBottom: '1px solid var(--border-glass)' }}>
                      <td style={{ padding: '1rem', fontWeight: 500 }}>{task.original_filename}</td>
                      <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{task.dataset_name || 'Dataset'}</td>
                      <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{task.language}</td>
                      <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{formatDurationHoursMins(task.duration)}</td>
                      <td style={{ padding: '1rem' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                          <span style={{
                            padding: '0.25rem 0.6rem',
                            borderRadius: '9999px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            width: 'fit-content',
                            background: `${statusColor}22`,
                            color: statusColor,
                          }}>
                            {statusLabel}
                          </span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            {task.reviewed_count ?? 0}/{task.total_reviewers ?? 1} reviewers approved
                          </span>
                          {task.last_reviewer_comment && (
                            <div style={{
                              marginTop: '0.25rem',
                              padding: '0.5rem 0.75rem',
                              borderRadius: '6px',
                              background: 'rgba(239, 68, 68, 0.1)',
                              borderLeft: '3px solid #ef4444',
                              fontSize: '0.8125rem',
                              color: 'var(--text-main)',
                            }}>
                              <strong style={{ color: '#ef4444' }}>Reviewer Feedback: </strong>
                              "{task.last_reviewer_comment}"
                            </div>
                          )}
                        </div>
                      </td>
                      <td style={{ padding: '1rem' }}>
                        <button 
                          className="btn btn-secondary"
                          onClick={() => navigate(`/annotator/task/${task.id}`)}
                        >
                          {task.status === 'REWORK_REQUIRED' || task.status === 'IN_PROGRESS' ? '✏️ Rework' : '👁️ View'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
