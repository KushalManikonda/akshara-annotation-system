import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/auth';

interface SidebarItem {
  label: string;
  path: string;
  icon: string;
}

interface DashboardLayoutProps {
  navItems: SidebarItem[];
  title: string;
}

export default function DashboardLayout({ navItems, title }: DashboardLayoutProps) {
  const { user, logout } = useAuthStore();
  const location = useLocation();

  return (
    <div className="dashboard-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div style={{ padding: '0 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '40px',
            height: '40px',
            background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%)',
            borderRadius: 'var(--radius-md)',
            fontSize: '1.25rem',
            boxShadow: '0 4px 14px 0 rgba(99, 102, 241, 0.39)',
          }}>
            🎙️
          </div>
          <span style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)' }}>
            Akshara
          </span>
        </div>

        <nav className="sidebar-nav" style={{ flex: 1, marginTop: '1rem' }}>
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`sidebar-link ${location.pathname === item.path ? 'active' : ''}`}
            >
              <span style={{ width: '20px', textAlign: 'center' }}>{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>

        <div style={{
          padding: '1rem',
          background: 'rgba(15, 23, 42, 0.4)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-glass)',
        }}>
          <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)' }}>
            {user?.username}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            {user?.role}
          </div>
          <button
            onClick={() => logout()}
            className="btn btn-secondary"
            style={{ width: '100%', fontSize: '0.75rem', padding: '0.5rem' }}
          >
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="header">
          <div>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700, margin: 0 }}>
              {user?.username || title}
            </h1>
            <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: '0.875rem' }}>
              Welcome back to your workspace.
            </p>
          </div>
        </header>

        <div className="animate-fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
