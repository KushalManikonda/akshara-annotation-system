// frontend/src/pages/Login.tsx
//
// Login page — Phase 1 placeholder with full visual design.
// Functionality wires up in Phase 4 (after API layer exists).

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import '../index.css';

export default function Login() {
  const navigate = useNavigate();
  const { login, isLoading, isAuthenticated, error, clearError, user } = useAuthStore();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && user) {
      const role = user.role;
      if (role === 'SUPER_ADMIN' || role === 'PLATFORM') navigate('/superadmin');
      else if (role === 'ADMIN') navigate('/admin');
      else if (role === 'REVIEWER') navigate('/reviewer');
      else navigate('/annotator');
    }
  }, [isAuthenticated, user, navigate]);

  // Clear errors when typing
  useEffect(() => {
    if (error) clearError();
  }, [username, password]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;
    await login(username.trim(), password.trim());
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1rem',
      position: 'relative',
      overflow: 'hidden',
    }}>
      <div style={{
        width: '100%',
        maxWidth: '400px',
        position: 'relative',
        zIndex: 1,
      }}>
        {/* Logo & Title */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '64px',
            height: '64px',
            background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%)',
            borderRadius: 'var(--radius-xl)',
            fontSize: '2rem',
            marginBottom: '1rem',
            boxShadow: '0 4px 14px 0 rgba(99, 102, 241, 0.39)',
          }}>
            🎙️
          </div>
          <h1 style={{
            fontSize: '2rem',
            fontWeight: 700,
            color: 'var(--text-main)',
            letterSpacing: '-0.02em',
            marginBottom: '0.25rem',
          }}>
            Akshara
          </h1>
          <p style={{
            color: 'var(--text-muted)',
            fontSize: '0.875rem',
          }}>
            Multilingual Speech Annotation Platform
          </p>
        </div>

        {/* Login Card */}
        <div className="card glass-panel" style={{ padding: '2rem' }}>
          <form onSubmit={handleSubmit}>
            {/* Error message */}
            {error && (
              <div style={{
                background: 'rgba(239,68,68,0.1)',
                border: '1px solid rgba(239,68,68,0.3)',
                borderRadius: 'var(--radius-md)',
                padding: '0.75rem',
                marginBottom: '1rem',
                color: '#ef4444',
                fontSize: '0.875rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}>
                ⚠️ {error}
              </div>
            )}

            {/* Username field */}
            <div className="input-group">
              <label className="input-label" htmlFor="login-username">
                Username
              </label>
              <input
                id="login-username"
                type="text"
                className="input-field"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                autoFocus
                disabled={isLoading}
              />
            </div>

            {/* Password field */}
            <div className="input-group" style={{ marginBottom: '1.5rem' }}>
              <label className="input-label" htmlFor="login-password">
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  className="input-field"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  disabled={isLoading}
                  style={{ width: '100%', paddingRight: '40px' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '1rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--text-muted)',
                    fontSize: '1rem',
                    padding: '2px',
                  }}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? '🙈' : '👁️'}
                </button>
              </div>
            </div>

            {/* Submit button */}
            <button
              type="submit"
              className="btn btn-primary"
              id="login-submit"
              disabled={isLoading || !username.trim() || !password.trim()}
              style={{ width: '100%', fontSize: '1rem' }}
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p style={{
          textAlign: 'center',
          marginTop: '2rem',
          color: 'var(--text-muted)',
          fontSize: '0.75rem',
        }}>
          Akshara v2.0 · Secure Login
        </p>
      </div>
    </div>
  );
}
