import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

interface TaskHeaderProps {
  taskId: string;
  hasUnsavedChanges: boolean;
  taskStatus?: string;
}

export function TaskHeader({ taskId, hasUnsavedChanges, taskStatus = 'IN_PROGRESS' }: TaskHeaderProps) {
  const navigate = useNavigate();

  const handleBack = () => {
    if (hasUnsavedChanges) {
      if (!window.confirm('You have unsaved changes. Are you sure you want to leave?')) {
        return;
      }
    }
    navigate('/annotator/dashboard');
  };

  const getStatusBadge = () => {
    switch (taskStatus) {
      case 'SUBMITTED':
        return {
          label: 'Submitted',
          bg: 'rgba(245, 158, 11, 0.2)',
          border: '1px solid rgba(245, 158, 11, 0.5)',
          color: '#fbbf24'
        };
      case 'COMPLETED':
        return {
          label: 'Completed',
          bg: 'rgba(72, 187, 120, 0.2)',
          border: '1px solid rgba(72, 187, 120, 0.5)',
          color: '#48bb78'
        };
      case 'REWORK_REQUIRED':
        return {
          label: 'Rework Required',
          bg: 'rgba(239, 68, 68, 0.2)',
          border: '1px solid rgba(239, 68, 68, 0.5)',
          color: '#fca5a5'
        };
      default:
        return {
          label: 'In Progress',
          bg: 'rgba(99, 102, 241, 0.2)',
          border: '1px solid rgba(99, 102, 241, 0.5)',
          color: '#a5b4fc'
        };
    }
  };

  const badge = getStatusBadge();

  return (
    <div className="header" style={{ marginBottom: '1rem', paddingBottom: '0.5rem' }}>
      <div className="flex items-center gap-4">
        <button className="btn btn-secondary" onClick={handleBack}>
          <ArrowLeft size={16} /> Back to Queue
        </button>
        <div>
          <h2 style={{ marginBottom: 0 }}>Task Workspace</h2>
          <p style={{ margin: 0, fontSize: '0.875rem' }}>ID: {taskId}</p>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <span className="glass" style={{
          padding: '0.25rem 0.75rem',
          fontSize: '0.875rem',
          borderRadius: '9999px',
          background: badge.bg,
          border: badge.border,
          color: badge.color,
          fontWeight: 600
        }}>
          {badge.label}
        </span>
      </div>
    </div>
  );
}
