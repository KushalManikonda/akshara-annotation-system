import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { analyticsApi } from '../../services/api';

type Tab = 'annotators' | 'reviewers';

// ── Medal ─────────────────────────────────────────────────────────────────────
function Medal({ rank }: { rank: number }) {
  if (rank === 1) return <span style={{ fontSize: '1.25rem' }}>🥇</span>;
  if (rank === 2) return <span style={{ fontSize: '1.25rem' }}>🥈</span>;
  if (rank === 3) return <span style={{ fontSize: '1.25rem' }}>🥉</span>;
  return <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>#{rank}</span>;
}

// ── Quality Badge ─────────────────────────────────────────────────────────────
function QualityBadge({ value }: { value: number }) {
  const color = value >= 80 ? '#10b981' : value >= 50 ? '#f59e0b' : '#ef4444';
  const label = value >= 80 ? 'High' : value >= 50 ? 'Medium' : 'Low';
  return (
    <span style={{
      fontSize: '0.75rem', fontWeight: 600, padding: '0.2rem 0.5rem',
      borderRadius: '4px', background: `${color}22`, color
    }}>
      {label} {value.toFixed(0)}%
    </span>
  );
}

export default function Leaderboard() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>('annotators');

  const { data: annotators, isLoading: annotatorsLoading } = useQuery({
    queryKey: ['analytics', 'leaderboard', 'annotators'],
    queryFn: analyticsApi.getAnnotatorLeaderboard,
    refetchInterval: 60_000,
  });

  const { data: reviewers, isLoading: reviewersLoading } = useQuery({
    queryKey: ['analytics', 'leaderboard', 'reviewers'],
    queryFn: analyticsApi.getReviewerLeaderboard,
    refetchInterval: 60_000,
  });

  const isLoading = activeTab === 'annotators' ? annotatorsLoading : reviewersLoading;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>🏆 Leaderboard</h1>
          <p style={{ margin: '0.25rem 0 0', color: 'var(--text-muted)', fontSize: '0.875rem' }}>Ranked by volume and quality</p>
        </div>
        <button className="btn btn-secondary" onClick={() => navigate('/admin')}>
          ← Back to Dashboard
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-glass)', paddingBottom: '0' }}>
        {(['annotators', 'reviewers'] as Tab[]).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '0.75rem 1.5rem',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === tab ? '2px solid var(--primary-main)' : '2px solid transparent',
              color: activeTab === tab ? 'var(--primary-main)' : 'var(--text-muted)',
              fontWeight: activeTab === tab ? 600 : 400,
              cursor: 'pointer',
              textTransform: 'capitalize',
              fontSize: '0.9375rem',
              transition: 'all 0.15s ease',
            }}
          >
            {tab === 'annotators' ? '✏️ Annotators' : '🔍 Reviewers'}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="card glass-panel" style={{ padding: '1.5rem' }}>
        {isLoading ? (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '3rem' }}>Loading leaderboard...</div>
        ) : activeTab === 'annotators' ? (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-glass)', color: 'var(--text-muted)' }}>
                <th style={{ textAlign: 'left', padding: '0.5rem 1rem 0.75rem 0', width: '60px' }}>Rank</th>
                <th style={{ textAlign: 'left', padding: '0.5rem 1rem 0.75rem' }}>Annotator</th>
                <th style={{ textAlign: 'right', padding: '0.5rem 1rem 0.75rem' }}>Submitted</th>
                <th style={{ textAlign: 'right', padding: '0.5rem 1rem 0.75rem' }}>Approved</th>
                <th style={{ textAlign: 'right', padding: '0.5rem 1rem 0.75rem' }}>Returned</th>
                <th style={{ textAlign: 'center', padding: '0.5rem 1rem 0.75rem' }}>Quality</th>
              </tr>
            </thead>
            <tbody>
              {annotators?.length === 0 && (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>No annotators yet.</td></tr>
              )}
              {annotators?.map((user: any, i: number) => {
                const quality = typeof user.quality_pct === 'number'
                  ? user.quality_pct
                  : (user.submitted > 0 ? (user.approved / user.submitted) * 100 : 0);
                return (
                  <tr key={user.username} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.15s' }}>
                    <td style={{ padding: '0.875rem 1rem 0.875rem 0' }}><Medal rank={i + 1} /></td>
                    <td style={{ padding: '0.875rem 1rem', fontWeight: 600 }}>
                      <div>{user.username}</div>
                    </td>
                    <td style={{ padding: '0.875rem 1rem', textAlign: 'right' }}>{(user.submitted ?? 0).toLocaleString()}</td>
                    <td style={{ padding: '0.875rem 1rem', textAlign: 'right', color: '#10b981', fontWeight: 600 }}>{user.approved ?? 0}</td>
                    <td style={{ padding: '0.875rem 1rem', textAlign: 'right', color: '#f59e0b' }}>{user.returned ?? 0}</td>
                    <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                      <QualityBadge value={quality} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-glass)', color: 'var(--text-muted)' }}>
                <th style={{ textAlign: 'left', padding: '0.5rem 1rem 0.75rem 0', width: '60px' }}>Rank</th>
                <th style={{ textAlign: 'left', padding: '0.5rem 1rem 0.75rem' }}>Reviewer</th>
                <th style={{ textAlign: 'right', padding: '0.5rem 1rem 0.75rem' }}>Total Reviews</th>
                <th style={{ textAlign: 'right', padding: '0.5rem 1rem 0.75rem' }}>Approvals</th>
                <th style={{ textAlign: 'right', padding: '0.5rem 1rem 0.75rem' }}>Rejections/Returns</th>
                <th style={{ textAlign: 'center', padding: '0.5rem 1rem 0.75rem' }}>Quality</th>
              </tr>
            </thead>
            <tbody>
              {reviewers?.length === 0 && (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>No reviewers yet.</td></tr>
              )}
              {reviewers?.map((user: any, i: number) => {
                const quality = typeof user.quality_pct === 'number'
                  ? user.quality_pct
                  : (user.total_reviews > 0 ? (user.approvals / user.total_reviews) * 100 : 0);
                return (
                  <tr key={user.username} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '0.875rem 1rem 0.875rem 0' }}><Medal rank={i + 1} /></td>
                    <td style={{ padding: '0.875rem 1rem', fontWeight: 600 }}>{user.username}</td>
                    <td style={{ padding: '0.875rem 1rem', textAlign: 'right', fontWeight: 600 }}>{user.total_reviews ?? 0}</td>
                    <td style={{ padding: '0.875rem 1rem', textAlign: 'right', color: '#10b981' }}>{user.approvals ?? 0}</td>
                    <td style={{ padding: '0.875rem 1rem', textAlign: 'right', color: '#ef4444' }}>{user.rejections ?? 0}</td>
                    <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                      <QualityBadge value={quality} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
