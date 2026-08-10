import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { useAuthStore } from '../../store/auth';
import { usersApi } from '../../services/api';

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '0.75rem',
  background: 'rgba(15,23,42,0.4)',
  border: '1px solid var(--border-glass)',
  borderRadius: 'var(--radius-md)',
  color: 'var(--text-muted)',
  boxSizing: 'border-box',
};

const editableInputStyle: React.CSSProperties = {
  ...inputStyle,
  color: 'var(--text-main)',
};

export default function AdminSettings() {
  const { user } = useAuthStore();
  const [showPwModal, setShowPwModal] = useState(false);
  const [pwData, setPwData] = useState({ current: '', newPw: '', confirm: '' });

  const changePwMutation = useMutation({
    mutationFn: () => usersApi.changePassword(pwData.current, pwData.newPw),
    onSuccess: () => {
      toast.success('Password changed successfully!');
      setShowPwModal(false);
      setPwData({ current: '', newPw: '', confirm: '' });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to change password');
    },
  });

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (pwData.newPw !== pwData.confirm) {
      toast.error('New passwords do not match');
      return;
    }
    if (pwData.newPw.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }
    changePwMutation.mutate();
  };

  return (
    <div className="card glass-panel" style={{ minHeight: '600px' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.25rem', margin: 0 }}>Platform Settings</h2>
        <p style={{ color: 'var(--text-muted)' }}>Manage your preferences and system configuration.</p>
      </div>

      <div style={{ display: 'grid', gap: '2rem', maxWidth: '600px' }}>

        {/* Profile Settings */}
        <div style={{ padding: '1.5rem', background: 'rgba(30,41,59,0.4)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-glass)' }}>
          <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem' }}>Admin Profile</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.25rem', color: 'var(--text-muted)' }}>Username</label>
              <input type="text" value={user?.username || ''} disabled style={inputStyle} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.25rem', color: 'var(--text-muted)' }}>Email</label>
              <input type="text" value={user?.email || ''} disabled style={inputStyle} />
            </div>
            <button
              className="btn btn-secondary"
              style={{ alignSelf: 'flex-start' }}
              onClick={() => setShowPwModal(true)}
            >
              🔑 Change Password
            </button>
          </div>
        </div>

        {/* System Settings */}
        <div style={{ padding: '1.5rem', background: 'rgba(30,41,59,0.4)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-glass)' }}>
          <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem' }}>System Configuration</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 500 }}>Maintenance Mode</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Disable access for annotators and reviewers</div>
              </div>
              <input type="checkbox" style={{ transform: 'scale(1.2)' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 500 }}>Auto-Assign Tasks</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Automatically assign new audio to available annotators</div>
              </div>
              <input type="checkbox" defaultChecked style={{ transform: 'scale(1.2)' }} />
            </div>
          </div>
        </div>
      </div>

      {/* Change Password Modal */}
      {showPwModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.6)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }}>
          <div className="card glass-panel" style={{ width: '100%', maxWidth: '380px', padding: '2rem' }}>
            <h3 style={{ margin: '0 0 1.5rem 0' }}>Change Password</h3>
            <form onSubmit={handlePasswordSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }}>Current Password</label>
                <input
                  required type="password"
                  value={pwData.current}
                  onChange={e => setPwData({ ...pwData, current: e.target.value })}
                  style={editableInputStyle}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }}>New Password</label>
                <input
                  required type="password"
                  value={pwData.newPw}
                  onChange={e => setPwData({ ...pwData, newPw: e.target.value })}
                  style={editableInputStyle}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }}>Confirm New Password</label>
                <input
                  required type="password"
                  value={pwData.confirm}
                  onChange={e => setPwData({ ...pwData, confirm: e.target.value })}
                  style={editableInputStyle}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '0.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => { setShowPwModal(false); setPwData({ current: '', newPw: '', confirm: '' }); }}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={changePwMutation.isPending}>
                  {changePwMutation.isPending ? 'Saving...' : 'Change Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
