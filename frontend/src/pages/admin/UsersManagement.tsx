import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { usersApi } from '../../services/api';
import { formatDateIndian } from '../../utils/time';
import toast from 'react-hot-toast';

type ModalMode = 'add' | 'edit' | 'password' | null;

const ROLE_COLORS: Record<string, { bg: string; color: string }> = {
  ADMIN:      { bg: 'rgba(99,102,241,0.15)',  color: '#818cf8' },
  ANNOTATOR:  { bg: 'rgba(16,185,129,0.15)',  color: '#34d399' },
  REVIEWER:   { bg: 'rgba(245,158,11,0.15)',  color: '#fbbf24' },
  SUPER_ADMIN:{ bg: 'rgba(239,68,68,0.15)',   color: '#f87171' },
};

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '0.75rem',
  background: 'rgba(15,23,42,0.4)',
  border: '1px solid var(--border-glass)',
  borderRadius: 'var(--radius-md)',
  color: 'white', boxSizing: 'border-box',
};

export default function UsersManagement() {
  const queryClient = useQueryClient();
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [selectedUser, setSelectedUser] = useState<any>(null);

  const [formData, setFormData] = useState({ name: '', email: '', password: '', role: 'ANNOTATOR', is_active: true });
  const [pwData, setPwData] = useState({ newPassword: '', confirm: '' });

  const { data: users, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.getAll,
  });

  const openAdd = () => {
    setFormData({ name: '', email: '', password: '', role: 'ANNOTATOR', is_active: true });
    setSelectedUser(null);
    setModalMode('add');
  };

  const openEdit = (user: any) => {
    setFormData({ name: user.username, email: user.email || '', password: '', role: user.role, is_active: user.is_active });
    setSelectedUser(user);
    setModalMode('edit');
  };

  const openPassword = (user: any) => {
    setPwData({ newPassword: '', confirm: '' });
    setSelectedUser(user);
    setModalMode('password');
  };

  const closeModal = () => { setModalMode(null); setSelectedUser(null); };

  const createMutation = useMutation({
    mutationFn: (data: any) => usersApi.create({ username: data.name, email: data.email, password: data.password, role: data.role, is_active: true }),
    onSuccess: () => { toast.success('User created!'); closeModal(); queryClient.invalidateQueries({ queryKey: ['users'] }); },
    onError: (err: any) => {
      const detail = err.response?.data?.detail;
      toast.error(Array.isArray(detail) ? detail[0]?.msg : (detail || 'Failed to create user'));
    }
  });

  const updateMutation = useMutation({
    mutationFn: (data: any) => usersApi.update(selectedUser.id, { username: data.name, email: data.email, role: data.role, is_active: data.is_active }),
    onSuccess: () => { toast.success('User updated!'); closeModal(); queryClient.invalidateQueries({ queryKey: ['users'] }); },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed to update user'),
  });

  const deleteMutation = useMutation({
    mutationFn: (userId: string) => usersApi.delete(userId),
    onSuccess: () => { toast.success('User deleted.'); queryClient.invalidateQueries({ queryKey: ['users'] }); },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed to delete user'),
  });

  const setPasswordMutation = useMutation({
    mutationFn: ({ userId, pw }: { userId: string; pw: string }) => usersApi.adminSetPassword(userId, pw),
    onSuccess: () => { toast.success('Password updated!'); closeModal(); },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed to update password'),
  });

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (modalMode === 'add') createMutation.mutate(formData);
    else if (modalMode === 'edit') updateMutation.mutate(formData);
  };

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (pwData.newPassword !== pwData.confirm) { toast.error('Passwords do not match'); return; }
    if (pwData.newPassword.length < 6) { toast.error('Password must be at least 6 characters'); return; }
    setPasswordMutation.mutate({ userId: selectedUser.id, pw: pwData.newPassword });
  };

  if (isLoading) return <div style={{ padding: '2rem' }}>Loading users...</div>;
  if (error) return <div style={{ padding: '2rem', color: 'red' }}>Error loading users</div>;

  return (
    <div className="card glass-panel" style={{ minHeight: '600px', position: 'relative' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.25rem', margin: 0 }}>Users Management</h2>
        <button className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }} onClick={openAdd}>
          + Add new user
        </button>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-glass)', color: 'var(--text-muted)' }}>
              <th style={{ padding: '1rem' }}>Name</th>
              <th style={{ padding: '1rem' }}>Email</th>
              <th style={{ padding: '1rem' }}>Role</th>
              <th style={{ padding: '1rem' }}>Activity Status</th>
              <th style={{ padding: '1rem' }}>Account</th>
              <th style={{ padding: '1rem' }}>Joined</th>
              <th style={{ padding: '1rem' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users?.map((user: any) => {
              const roleStyle = ROLE_COLORS[user.role] || { bg: 'rgba(100,100,100,0.2)', color: '#ccc' };
              const actStatus = user.activity_status || (!user.last_login ? 'Never Logged In' : 'Offline');
              const actColor = actStatus === 'Online' ? '#10b981' : actStatus === 'Never Logged In' ? '#8b5cf6' : '#9ca3af';

              return (
                <tr key={user.id} style={{ borderBottom: '1px solid var(--border-glass)' }}>
                  <td style={{ padding: '1rem', fontWeight: 600 }}>{user.username}</td>
                  <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{user.email}</td>
                  <td style={{ padding: '1rem' }}>
                    <span style={{ padding: '0.25rem 0.6rem', borderRadius: '9999px', fontSize: '0.75rem', background: roleStyle.bg, color: roleStyle.color, fontWeight: 600 }}>
                      {user.role}
                    </span>
                  </td>
                  <td style={{ padding: '1rem' }}>
                    <span style={{
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      background: `${actColor}22`,
                      color: actColor,
                    }}>
                      {actStatus}
                    </span>
                  </td>
                  <td style={{ padding: '1rem' }}>
                    <span style={{ color: user.is_active ? '#34d399' : '#ef4444', fontWeight: 500, fontSize: '0.875rem' }}>
                      {user.is_active ? 'Enabled' : 'Disabled'}
                    </span>
                  </td>
                  <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>
                    {formatDateIndian(user.created_at)}
                  </td>
                  <td style={{ padding: '1rem' }}>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem' }}
                        onClick={() => openEdit(user)}
                      >✏️ Edit</button>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem', color: '#60a5fa', borderColor: 'rgba(96,165,250,0.3)' }}
                        onClick={() => openPassword(user)}
                      >🔑 Password</button>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem', color: '#ef4444', borderColor: 'rgba(239,68,68,0.3)' }}
                        onClick={() => { if (window.confirm(`Delete "${user.username}"? This cannot be undone.`)) deleteMutation.mutate(user.id); }}
                        disabled={deleteMutation.isPending}
                      >🗑️ Delete</button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Add / Edit Modal */}
      {(modalMode === 'add' || modalMode === 'edit') && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="card glass-panel" style={{ width: '100%', maxWidth: '420px', padding: '2rem' }}>
            <h3 style={{ margin: '0 0 1.5rem 0' }}>{modalMode === 'add' ? 'Add a user' : `Edit "${selectedUser?.username}"`}</h3>
            <form onSubmit={handleFormSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }}>Username</label>
                <input required type="text" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} style={inputStyle} />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }}>Email</label>
                <input required type="email" value={formData.email} onChange={e => setFormData({ ...formData, email: e.target.value })} style={inputStyle} />
              </div>
              {modalMode === 'add' && (
                <div>
                  <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }}>Password</label>
                  <input required type="password" value={formData.password} onChange={e => setFormData({ ...formData, password: e.target.value })} style={inputStyle} />
                </div>
              )}
              <div>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }}>Role</label>
                <select value={formData.role} onChange={e => setFormData({ ...formData, role: e.target.value })} style={{ ...inputStyle, outline: 'none' }}>
                  <option value="ADMIN">Admin</option>
                  <option value="ANNOTATOR">Annotator</option>
                  <option value="REVIEWER">Reviewer</option>
                </select>
              </div>
              {modalMode === 'edit' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <input type="checkbox" id="is_active" checked={formData.is_active} onChange={e => setFormData({ ...formData, is_active: e.target.checked })} style={{ transform: 'scale(1.2)' }} />
                  <label htmlFor="is_active" style={{ fontSize: '0.875rem', cursor: 'pointer' }}>Active account</label>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '0.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={closeModal}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>
                  {createMutation.isPending || updateMutation.isPending ? 'Saving...' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Set Password Modal */}
      {modalMode === 'password' && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="card glass-panel" style={{ width: '100%', maxWidth: '380px', padding: '2rem' }}>
            <h3 style={{ margin: '0 0 0.5rem 0' }}>Set Password</h3>
            <p style={{ margin: '0 0 1.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>Setting new password for <strong>{selectedUser?.username}</strong></p>
            <form onSubmit={handlePasswordSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }}>New Password</label>
                <input required type="password" value={pwData.newPassword} onChange={e => setPwData({ ...pwData, newPassword: e.target.value })} style={inputStyle} />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }}>Confirm Password</label>
                <input required type="password" value={pwData.confirm} onChange={e => setPwData({ ...pwData, confirm: e.target.value })} style={inputStyle} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '0.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={closeModal}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={setPasswordMutation.isPending}>
                  {setPasswordMutation.isPending ? 'Saving...' : 'Set Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
