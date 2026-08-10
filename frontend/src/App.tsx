// frontend/src/App.tsx
//
// Root application component.
// - Sets up React Router
// - Sets up React Query
// - Sets up Toasts
// - Handles role-based routing

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { useEffect } from 'react';
import { useAuthStore } from './store/auth';
import DashboardLayout from './components/DashboardLayout';
import AdminDashboard from './pages/admin/AdminDashboard';
import UsersManagement from './pages/admin/UsersManagement';
import DatasetsManagement from './pages/admin/DatasetsManagement';
import AdminSettings from './pages/admin/AdminSettings';
import Leaderboard from './pages/admin/Leaderboard';
import AnnotatorDashboard from './pages/annotator/AnnotatorDashboard';
import TaskWorkspace from './pages/annotator/TaskWorkspace';
import AnnotatorHistory from './pages/annotator/AnnotatorHistory';
import ReviewerDashboard from './pages/reviewer/ReviewerDashboard';
import ReviewWorkspace from './pages/reviewer/ReviewWorkspace';
import ReviewerHistory from './pages/reviewer/ReviewerHistory';

// Pages
import Login from './pages/Login';

// Placeholder dashboard pages (built in Phase 5)
function PlaceholderPage({ title }: { title: string }) {
  const { user, logout } = useAuthStore();
  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--color-bg)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '1rem',
      color: 'var(--color-text)',
      fontFamily: 'var(--font-sans)',
    }}>
      <div style={{ fontSize: '3rem' }}>🎙️</div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 600 }}>{title}</h1>
      <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
        Logged in as: <strong>{user?.username}</strong> ({user?.role})
      </p>
      <p style={{ color: 'var(--color-text-dim)', fontSize: '0.8rem' }}>
        Full dashboard coming in Phase 5
      </p>
      <button
        onClick={() => logout()}
        style={{
          marginTop: '1rem',
          padding: '0.5rem 1.5rem',
          background: 'rgba(239,68,68,0.1)',
          border: '1px solid rgba(239,68,68,0.3)',
          borderRadius: '0.5rem',
          color: '#ef4444',
          cursor: 'pointer',
          fontFamily: 'var(--font-sans)',
        }}
      >
        Sign Out
      </button>
    </div>
  );
}

// ── Auth guard ────────────────────────────────────────────────────────────────
function ProtectedRoute({
  children,
  allowedRoles,
}: {
  children: React.ReactNode;
  allowedRoles?: string[];
}) {
  const { isAuthenticated, user } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    // Redirect to their correct dashboard
    const role = user.role;
    if (role === 'SUPER_ADMIN' || role === 'PLATFORM') return <Navigate to="/superadmin" replace />;
    if (role === 'ADMIN') return <Navigate to="/admin" replace />;
    if (role === 'REVIEWER') return <Navigate to="/reviewer" replace />;
    return <Navigate to="/annotator" replace />;
  }

  return <>{children}</>;
}

// ── Query Client ──────────────────────────────────────────────────────────────
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,         // 30s before refetch
      retry: 1,                   // Retry once on failure
      refetchOnWindowFocus: true,
    },
  },
});

// ── Session Restore Spinner ──────────────────────────────────────────────────
function SessionLoader() {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '1.5rem',
      background: 'var(--color-bg)',
      fontFamily: 'var(--font-sans)',
      color: 'var(--color-text)',
    }}>
      <div style={{ fontSize: '2.5rem' }}>🎙️</div>
      <div style={{
        width: '40px',
        height: '40px',
        border: '3px solid rgba(56, 189, 248, 0.2)',
        borderTop: '3px solid var(--primary-main, #38bdf8)',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', margin: 0 }}>
        Restoring session…
      </p>
    </div>
  );
}

// ── Root Component ────────────────────────────────────────────────────────────
export default function App() {
  const { restoreSession, isRestoringSession } = useAuthStore();

  useEffect(() => {
    restoreSession();
  }, []);

  if (isRestoringSession) {
    return <SessionLoader />;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/login" element={<Login />} />

          {/* Annotator dashboard */}
          <Route
            path="/annotator"
            element={
              <ProtectedRoute allowedRoles={['ANNOTATOR']}>
                <DashboardLayout 
                  title="Annotator Dashboard"
                  navItems={[
                    { label: 'Task Queue', path: '/annotator', icon: '🎧' },
                    { label: 'My History', path: '/annotator/history', icon: '⏱️' }
                  ]}
                />
              </ProtectedRoute>
            }
          >
            <Route index element={<AnnotatorDashboard />} />
            <Route path="task/:id" element={<TaskWorkspace />} />
            <Route path="history" element={<AnnotatorHistory />} />
          </Route>

          {/* Reviewer dashboard */}
          <Route
            path="/reviewer"
            element={
              <ProtectedRoute allowedRoles={['REVIEWER']}>
                <DashboardLayout 
                  title="Reviewer Dashboard"
                  navItems={[
                    { label: 'Review Queue', path: '/reviewer', icon: '📋' },
                    { label: 'My History', path: '/reviewer/history', icon: '⏱️' }
                  ]}
                />
              </ProtectedRoute>
            }
          >
            <Route index element={<ReviewerDashboard />} />
            <Route path="review/:id" element={<ReviewWorkspace />} />
            <Route path="history" element={<ReviewerHistory />} />
          </Route>

          {/* Admin dashboard */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={['ADMIN']}>
                <DashboardLayout 
                  title="Admin Dashboard"
                  navItems={[
                    { label: 'Overview', path: '/admin', icon: '📊' },
                    { label: 'Leaderboard', path: '/admin/leaderboard', icon: '🏆' },
                    { label: 'Users', path: '/admin/users', icon: '👥' },
                    { label: 'Datasets', path: '/admin/datasets', icon: '📁' },
                    { label: 'Settings', path: '/admin/settings', icon: '⚙️' }
                  ]}
                />
              </ProtectedRoute>
            }
          >
            <Route index element={<AdminDashboard />} />
            <Route path="users" element={<UsersManagement />} />
            <Route path="datasets" element={<DatasetsManagement />} />
            <Route path="settings" element={<AdminSettings />} />
            <Route path="leaderboard" element={<Leaderboard />} />
          </Route>

          {/* Super Admin dashboard */}
          <Route
            path="/superadmin/*"
            element={
              <ProtectedRoute allowedRoles={['SUPER_ADMIN', 'PLATFORM']}>
                <PlaceholderPage title="Super Admin Control Panel" />
              </ProtectedRoute>
            }
          />

          {/* Catch-all → login */}
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>

        {/* Global toast notifications */}
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: 'var(--color-surface)',
              color: 'var(--color-text)',
              border: '1px solid var(--color-border)',
              fontFamily: 'var(--font-sans)',
              fontSize: '0.875rem',
            },
            success: {
              iconTheme: { primary: '#22c55e', secondary: 'transparent' },
            },
            error: {
              iconTheme: { primary: '#ef4444', secondary: 'transparent' },
            },
          }}
        />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
