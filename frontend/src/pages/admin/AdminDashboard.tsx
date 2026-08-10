import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { analyticsApi } from '../../services/api';
import { formatDurationHoursMins } from '../../utils/time';

// ── Stat Card ─────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="card glass-panel" style={{ padding: '1.5rem' }}>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
        {label}
      </div>
      <div style={{ fontSize: '2.25rem', fontWeight: 700, color: color || 'var(--text-main)', lineHeight: 1 }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>{sub}</div>}
    </div>
  );
}

// ── Progress Bar ──────────────────────────────────────────────────────────────
function ProgressBar({ value, max, color }: { value: number; max: number; color?: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
      <div style={{ flex: 1, background: 'rgba(255,255,255,0.08)', borderRadius: '99px', height: '8px', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color || 'var(--primary-main)', borderRadius: '99px', transition: 'width 0.4s ease' }} />
      </div>
      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', minWidth: '38px', textAlign: 'right' }}>{pct}%</span>
    </div>
  );
}

// ── Funnel Row ────────────────────────────────────────────────────────────────
const FUNNEL_COLORS: Record<string, string> = {
  UNASSIGNED:  '#6b7280',
  ASSIGNED:    '#3b82f6',
  IN_PROGRESS: '#f59e0b',
  SUBMITTED:   '#8b5cf6',
  REWORK_REQUIRED: '#ef4444',
  COMPLETED:   '#10b981',
};

export default function AdminDashboard() {
  const navigate = useNavigate();

  const { data: kpi, isLoading: kpiLoading } = useQuery({
    queryKey: ['analytics', 'global'],
    queryFn: analyticsApi.getGlobal,
    refetchInterval: 60_000,
  });

  const { data: funnel, isLoading: funnelLoading } = useQuery({
    queryKey: ['analytics', 'funnel'],
    queryFn: analyticsApi.getFunnel,
    refetchInterval: 60_000,
  });

  const { data: datasets, isLoading: datasetsLoading } = useQuery({
    queryKey: ['analytics', 'datasets'],
    queryFn: analyticsApi.getDatasets,
    refetchInterval: 60_000,
  });

  const { data: languages } = useQuery({
    queryKey: ['analytics', 'languages'],
    queryFn: analyticsApi.getLanguages,
  });

  if (kpiLoading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', color: 'var(--text-muted)' }}>
      Loading analytics...
    </div>
  );

  const totalAudio = kpi?.total_audio ?? 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>

      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>Platform Analytics</h1>
          <p style={{ margin: '0.25rem 0 0', color: 'var(--text-muted)', fontSize: '0.875rem' }}>Live system-wide metrics · refreshes every 60s</p>
        </div>
        <button className="btn btn-secondary" onClick={() => navigate('/admin/leaderboard')}>
          🏆 View Leaderboard
        </button>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
        <StatCard label="Total Audio Files" value={kpi?.total_audio?.toLocaleString() ?? '—'} />
        <StatCard label="Total Datasets" value={kpi?.total_datasets ?? '—'} />
        <StatCard label="Annotators" value={kpi?.total_annotators ?? '—'} />
        <StatCard label="Reviewers" value={kpi?.total_reviewers ?? '—'} />
        <StatCard
          label="Completion Rate"
          value={`${kpi?.approved_pct?.toFixed(1) ?? '0.0'}%`}
          sub={`${kpi?.approved_count ?? 0} of ${kpi?.total_audio ?? 0} approved`}
          color={kpi?.approved_pct >= 80 ? '#10b981' : kpi?.approved_pct >= 40 ? '#f59e0b' : '#ef4444'}
        />
      </div>

      {/* Two Column: Funnel + Language */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>

        {/* Pipeline Funnel */}
        <div className="card glass-panel" style={{ padding: '1.5rem' }}>
          <h2 style={{ margin: '0 0 1.25rem', fontSize: '1rem', fontWeight: 600 }}>Pipeline Stages</h2>
          {funnelLoading ? (
            <div style={{ color: 'var(--text-muted)' }}>Loading...</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {funnel?.map((stage: any) => (
                <div key={stage.stage}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem', fontSize: '0.875rem' }}>
                    <span style={{ color: FUNNEL_COLORS[stage.stage] || 'var(--text-muted)', fontWeight: 500 }}>
                      {stage.stage}
                    </span>
                    <span style={{ color: 'var(--text-muted)' }}>{stage.count.toLocaleString()}</span>
                  </div>
                  <ProgressBar value={stage.count} max={totalAudio} color={FUNNEL_COLORS[stage.stage]} />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Language Breakdown */}
        <div className="card glass-panel" style={{ padding: '1.5rem' }}>
          <h2 style={{ margin: '0 0 1.25rem', fontSize: '1rem', fontWeight: 600 }}>Languages</h2>
          {!languages || languages.length === 0 ? (
            <div style={{ color: 'var(--text-muted)' }}>No data yet.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {languages.map((lang: any) => (
                <div key={lang.language} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--primary-main)' }} />
                    <span style={{ fontWeight: 500 }}>{lang.language}</span>
                  </div>
                  <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                    <span>{lang.file_count.toLocaleString()} files</span>
                    <span>{formatDurationHoursMins(lang.total_duration_s || 0)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Dataset Progress Table */}
      <div className="card glass-panel" style={{ padding: '1.5rem' }}>
        <h2 style={{ margin: '0 0 1.25rem', fontSize: '1rem', fontWeight: 600 }}>Dataset Progress</h2>
        {datasetsLoading ? (
          <div style={{ color: 'var(--text-muted)' }}>Loading datasets...</div>
        ) : !datasets || datasets.length === 0 ? (
          <div style={{ color: 'var(--text-muted)' }}>No datasets found.</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-glass)', color: 'var(--text-muted)' }}>
                  <th style={{ textAlign: 'left', padding: '0.5rem 1rem 0.75rem 0' }}>Dataset</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem 1rem 0.75rem' }}>Language</th>
                  <th style={{ textAlign: 'right', padding: '0.5rem 1rem 0.75rem' }}>Total</th>
                  <th style={{ textAlign: 'right', padding: '0.5rem 1rem 0.75rem' }}>Approved</th>
                  <th style={{ textAlign: 'right', padding: '0.5rem 1rem 0.75rem' }}>Returned</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem 0 0.75rem 1rem', width: '200px' }}>Progress</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((ds: any) => (
                  <tr key={ds.name} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '0.75rem 1rem 0.75rem 0', fontWeight: 500 }}>{ds.name}</td>
                    <td style={{ padding: '0.75rem 1rem', color: 'var(--text-muted)' }}>{ds.language}</td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>{ds.total_files?.toLocaleString()}</td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'right', color: '#10b981' }}>{ds.approved_files?.toLocaleString()}</td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'right', color: '#f59e0b' }}>
                      {(ds.total_files - ds.approved_files)?.toLocaleString()}
                    </td>
                    <td style={{ padding: '0.75rem 0 0.75rem 1rem' }}>
                      <ProgressBar value={ds.approved_files} max={ds.total_files} color="#10b981" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick Stats Row */}
      {kpi && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem' }}>
          <StatCard label="Approved" value={(kpi.approved_count ?? 0).toLocaleString()} color="#10b981" />
          <StatCard label="Under Review" value={(kpi.submitted_count ?? 0).toLocaleString()} color="#8b5cf6" />
          <StatCard label="Returned" value={(kpi.returned_count ?? 0).toLocaleString()} color="#f59e0b" />
          <StatCard label="In Draft" value={(kpi.draft_count ?? 0).toLocaleString()} color="#6b7280" />
          <StatCard
            label="Total Duration"
            value={formatDurationHoursMins(kpi.total_duration ?? 0)}
            sub={`${formatDurationHoursMins(kpi.approved_duration ?? 0)} approved`}
          />
        </div>
      )}
    </div>
  );
}
