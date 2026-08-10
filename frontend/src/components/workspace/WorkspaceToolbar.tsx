
import { Save, Check, XCircle } from 'lucide-react';

interface WorkspaceToolbarProps {
  onSave: () => void;
  onSubmit: () => void;
  onAbandon: () => void;
  isSaving: boolean;
  hasUnsavedChanges: boolean;
}

export function WorkspaceToolbar({ onSave, onSubmit, onAbandon, isSaving, hasUnsavedChanges }: WorkspaceToolbarProps) {
  return (
    <div className="glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', padding: '0.75rem 1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <button className="btn btn-secondary" onClick={onSave} disabled={isSaving || !hasUnsavedChanges}>
          <Save size={16} />
          {isSaving ? 'Saving...' : 'Save Draft'}
        </button>
        {hasUnsavedChanges ? (
          <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Unsaved changes</span>
        ) : (
          <span style={{ fontSize: '0.875rem', color: 'var(--color-accent)' }}>All changes saved</span>
        )}
      </div>

      <div style={{ display: 'flex', gap: '1rem' }}>
        <button className="btn btn-danger" onClick={() => {
          if (window.confirm('Are you sure you want to abandon this task? Your lock will be released.')) {
            onAbandon();
          }
        }}>
          <XCircle size={16} />
          Abandon
        </button>
        <button className="btn btn-primary" onClick={() => {
          if (window.confirm('Are you sure you want to submit? You will not be able to edit this task after submission.')) {
            onSubmit();
          }
        }}>
          <Check size={16} />
          Submit Task
        </button>
      </div>
    </div>
  );
}
