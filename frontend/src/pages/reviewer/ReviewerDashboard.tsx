import { useQuery } from '@tanstack/react-query';
import { audioApi } from '../../services/api';
import { useAuthStore } from '../../store/auth';
import { useNavigate } from 'react-router-dom';

export default function ReviewerDashboard() {
  const { user } = useAuthStore();
  const navigate = useNavigate();

  // We could fetch pending annotations directly, but for now we'll fetch all audio 
  // and filter by ANNOTATED status to simulate the review queue.
  const { data: allAudio, isLoading } = useQuery({
    queryKey: ['audio'],
    queryFn: () => audioApi.getAll(),
  });

  if (isLoading) return <div style={{ padding: '2rem' }}>Loading review queue...</div>;

  const reviewTasks = allAudio?.filter((a: any) => a.status === 'SUBMITTED' && !a.reviewed_by_me) || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div className="card interactive" style={{ background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(52, 211, 153, 0.1) 100%)' }}>
        <h2 style={{ margin: '0 0 1rem 0', fontSize: '1.25rem' }}>Welcome, {user?.username}</h2>
        <p style={{ margin: 0, color: 'var(--text-muted)' }}>There are <strong>{reviewTasks.length}</strong> annotations waiting for your review.</p>
      </div>

      <div className="card glass-panel" style={{ minHeight: '400px' }}>
        <h3 style={{ margin: '0 0 1.5rem 0', fontSize: '1.125rem' }}>Review Queue</h3>
        
        {reviewTasks.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>✨</div>
            <p>Inbox zero! No annotations pending review.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {reviewTasks.map((task: any) => (
              <div 
                key={task.id} 
                className="card interactive"
                style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  padding: '1rem 1.5rem',
                  background: 'rgba(30, 41, 59, 0.3)'
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{task.original_filename}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Annotated by: {task.annotator_username || task.assigned_to_user?.username || task.assigned_to} • Language: {task.language} • {task.reviewed_count ?? 0}/{task.total_reviewers ?? 1} reviewers reviewed
                  </div>
                </div>
                <button 
                  className="btn btn-primary"
                  style={{ background: 'var(--color-success)' }}
                  onClick={() => navigate(`/reviewer/review/${task.id}`)}
                >
                  Start Review
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
