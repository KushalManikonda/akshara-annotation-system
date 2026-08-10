import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { queueApi } from '../../services/api';
import { useAuthStore } from '../../store/auth';

// ── Types ─────────────────────────────────────────────────────────────────────
interface TaskSummary {
  id: string;
  filename: string;
  original_filename: string;
  language: string;
  duration?: number;
  status: string;
  audio_url?: string;
  assigned_at?: string;
}

interface LanguageStat {
  language: string;
  available: number;
}

interface QueueStats {
  total_unassigned: number;
  total_assigned: number;
  total_in_progress: number;
  total_submitted: number;
  total_rework_required: number;
  total_completed_today: number;
  per_language: LanguageStat[];
}

// ── Status styling ────────────────────────────────────────────────────────────
const STATUS_META: Record<string, { label: string; color: string; bg: string; icon: string }> = {
  ASSIGNED:        { label: 'Assigned',        color: '#60a5fa', bg: 'rgba(96,165,250,0.1)',  icon: '📥' },
  IN_PROGRESS:     { label: 'In Progress',     color: '#fbbf24', bg: 'rgba(251,191,36,0.1)',  icon: '⚡' },
  SUBMITTED:       { label: 'Submitted',       color: '#a78bfa', bg: 'rgba(167,139,250,0.1)', icon: '📤' },
  REWORK_REQUIRED: { label: 'Rework Required', color: '#f87171', bg: 'rgba(248,113,113,0.1)', icon: '🔄' },
  COMPLETED:       { label: 'Completed',       color: '#34d399', bg: 'rgba(52,211,153,0.1)',  icon: '✅' },
};

function formatDuration(seconds?: number) {
  if (!seconds) return '—';
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

// ── Task Card ─────────────────────────────────────────────────────────────────
function TaskCard({ task, onContinue }: { task: TaskSummary; onContinue: (id: string) => void }) {
  const meta = STATUS_META[task.status] || { label: task.status, color: '#9ca3af', bg: 'rgba(156,163,175,0.1)', icon: '📋' };
  const isRework = task.status === 'REWORK_REQUIRED';

  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '1rem 1.25rem',
      background: isRework ? 'rgba(248,113,113,0.05)' : 'rgba(30,41,59,0.3)',
      border: `1px solid ${isRework ? 'rgba(248,113,113,0.3)' : 'var(--border-glass)'}`,
      borderRadius: 'var(--radius-md)',
      gap: '1rem',
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, marginBottom: '0.25rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {isRework && <span style={{ marginRight: '0.5rem' }}>⚠️</span>}
          {task.original_filename}
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', gap: '1rem' }}>
          <span>🌐 {task.language}</span>
          <span>⏱️ {formatDuration(task.duration)}</span>
          <span style={{ color: meta.color }}>
            {meta.icon} {meta.label}
          </span>
        </div>
      </div>
      <button
        className="btn btn-primary"
        style={{
          padding: '0.5rem 1rem', fontSize: '0.8125rem', flexShrink: 0,
          ...(isRework ? { background: 'rgba(248,113,113,0.2)', borderColor: 'rgba(248,113,113,0.4)', color: '#f87171' } : {}),
        }}
        onClick={() => onContinue(task.id)}
      >
        {task.status === 'SUBMITTED' ? 'View' : 'Continue →'}
      </button>
    </div>
  );
}

// ── Language Selection Modal ──────────────────────────────────────────────────
function AssignModal({
  stats,
  onClose,
  onAssigned,
}: {
  stats: QueueStats;
  onClose: () => void;
  onAssigned: (task: TaskSummary) => void;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const assignMutation = useMutation({
    mutationFn: (lang: string) => queueApi.assign(lang),
    onSuccess: (task: TaskSummary) => {
      toast.success(`Task assigned: ${task.original_filename}`);
      onAssigned(task);
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'object') {
        if (detail.code === 'REWORK_PENDING') {
          toast.error('You have rework tasks! Please complete those first.');
        } else if (detail.code === 'TOO_MANY_ACTIVE') {
          toast.error('You already have 5 active tasks. Complete some first.');
        } else if (detail.code === 'NO_TASKS_AVAILABLE') {
          toast(detail.message || 'No tasks available for this language.', { icon: '😕' });
        } else {
          toast.error(detail.message || 'Failed to assign task');
        }
      } else {
        toast.error(detail || 'Failed to assign task');
      }
    },
  });

  const handleAssign = () => {
    if (!selected) return;
    assignMutation.mutate(selected);
  };

  const totalAvailable = stats.total_unassigned;

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.7)', display: 'flex',
      alignItems: 'center', justifyContent: 'center', zIndex: 1000,
      padding: '1rem',
    }}>
      <div className="card glass-panel" style={{ width: '100%', maxWidth: '520px', padding: '2rem' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
          <div>
            <h3 style={{ margin: '0 0 0.25rem 0', fontSize: '1.125rem' }}>✨ Generate New Task</h3>
            <p style={{ margin: 0, fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
              {totalAvailable > 0 ? `${totalAvailable} tasks available across all languages` : 'No tasks currently available'}
            </p>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '1.25rem', padding: '0' }}>✕</button>
        </div>

        {/* Language grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '0.625rem', marginBottom: '1.5rem', maxHeight: '300px', overflowY: 'auto' }}>
          {/* Any Language */}
          <button
            onClick={() => setSelected('any')}
            style={{
              padding: '0.875rem 0.75rem', borderRadius: 'var(--radius-md)', cursor: 'pointer',
              background: selected === 'any' ? 'rgba(99,102,241,0.25)' : 'rgba(30,41,59,0.4)',
              border: selected === 'any' ? '1px solid rgba(99,102,241,0.6)' : '1px solid var(--border-glass)',
              color: 'white', textAlign: 'left', transition: 'all 0.15s',
            }}
          >
            <div style={{ fontSize: '1.25rem', marginBottom: '0.25rem' }}>🌐</div>
            <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>Any Language</div>
            <div style={{ fontSize: '0.75rem', color: 'rgba(148,163,184,0.8)', marginTop: '0.125rem' }}>
              {totalAvailable} available
            </div>
          </button>

          {/* Per-language cards */}
          {stats.per_language.map((ls) => {
            const isSelected = selected === ls.language;
            return (
              <button
                key={ls.language}
                onClick={() => setSelected(ls.language)}
                style={{
                  padding: '0.875rem 0.75rem', borderRadius: 'var(--radius-md)', cursor: 'pointer',
                  background: isSelected ? 'rgba(99,102,241,0.25)' : 'rgba(30,41,59,0.4)',
                  border: isSelected ? '1px solid rgba(99,102,241,0.6)' : '1px solid var(--border-glass)',
                  color: 'white', textAlign: 'left', transition: 'all 0.15s',
                }}
              >
                <div style={{ fontSize: '1.25rem', marginBottom: '0.25rem' }}>🎙️</div>
                <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{ls.language}</div>
                <div style={{ fontSize: '0.75rem', marginTop: '0.125rem' }}>
                  <span style={{
                    padding: '0.1rem 0.4rem', borderRadius: '9999px',
                    background: ls.available > 0 ? 'rgba(52,211,153,0.15)' : 'rgba(156,163,175,0.15)',
                    color: ls.available > 0 ? '#34d399' : '#9ca3af',
                    fontWeight: 600,
                  }}>
                    {ls.available} available
                  </span>
                </div>
              </button>
            );
          })}

          {stats.per_language.length === 0 && (
            <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
              😕 No tasks available right now. Check back soon.
            </div>
          )}
        </div>

        {/* Action */}
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button
            className="btn btn-primary"
            disabled={!selected || assignMutation.isPending}
            onClick={handleAssign}
            style={{ minWidth: '130px' }}
          >
            {assignMutation.isPending ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                <span style={{ width: '14px', height: '14px', border: '2px solid rgba(255,255,255,0.3)', borderTop: '2px solid white', borderRadius: '50%', display: 'inline-block', animation: 'spin 0.7s linear infinite' }} />
                Assigning...
              </span>
            ) : 'Assign Task →'}
          </button>
        </div>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// ── Stat Card ─────────────────────────────────────────────────────────────────
function StatCard({ label, value, color, icon }: { label: string; value: number; color: string; icon: string }) {
  return (
    <div style={{
      padding: '1rem 1.25rem',
      background: 'rgba(30,41,59,0.4)',
      border: '1px solid var(--border-glass)',
      borderRadius: 'var(--radius-md)',
      borderLeft: `3px solid ${color}`,
    }}>
      <div style={{ fontSize: '1.25rem', marginBottom: '0.25rem' }}>{icon}</div>
      <div style={{ fontSize: '1.5rem', fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.125rem' }}>{label}</div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function AnnotatorDashboard() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showModal, setShowModal] = useState(false);

  const { data: myTasks, isLoading: tasksLoading } = useQuery({
    queryKey: ['my-tasks'],
    queryFn: queueApi.getMyTasks,
    refetchInterval: 30_000,
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['queue-stats'],
    queryFn: queueApi.getStats,
    refetchInterval: 30_000,
  });

  const handleAssigned = (task: TaskSummary) => {
    setShowModal(false);
    queryClient.invalidateQueries({ queryKey: ['my-tasks'] });
    queryClient.invalidateQueries({ queryKey: ['queue-stats'] });
    navigate(`/annotator/task/${task.id}`);
  };

  const handleContinue = (taskId: string) => navigate(`/annotator/task/${taskId}`);

  const activeTasks = [
    ...(myTasks?.rework_required || []),
    ...(myTasks?.in_progress || []),
    ...(myTasks?.assigned || []),
    ...(myTasks?.submitted || []),
  ];
  const hasRework = (myTasks?.rework_required?.length || 0) > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      {/* Welcome banner */}
      <div className="card" style={{
        background: 'linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(139,92,246,0.1) 100%)',
        border: '1px solid rgba(99,102,241,0.2)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem',
        flexWrap: 'wrap',
      }}>
        <div>
          <h2 style={{ margin: '0 0 0.25rem 0', fontSize: '1.125rem' }}>Welcome back, {user?.username} 👋</h2>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            {activeTasks.length > 0
              ? `You have ${activeTasks.length} active task${activeTasks.length !== 1 ? 's' : ''} in your queue.`
              : 'Your queue is empty. Generate a new task to get started.'}
          </p>
        </div>

        {/* Rework warning banner */}
        {hasRework && (
          <div style={{
            padding: '0.5rem 1rem', borderRadius: 'var(--radius-md)',
            background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)',
            color: '#f87171', fontSize: '0.8125rem', fontWeight: 500,
          }}>
            ⚠️ You have {myTasks.rework_required.length} task{myTasks.rework_required.length !== 1 ? 's' : ''} requiring rework
          </div>
        )}

        {/* Generate button */}
        <button
          className="btn btn-primary"
          style={{ padding: '0.625rem 1.25rem', fontWeight: 600, flexShrink: 0 }}
          onClick={() => setShowModal(true)}
          disabled={statsLoading}
        >
          ✨ Generate / Assign Task
        </button>
      </div>

      {/* Stat cards */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '0.75rem' }}>
          <StatCard label="Assigned"        value={myTasks?.assigned?.length || 0}        color="#60a5fa" icon="📥" />
          <StatCard label="In Progress"     value={myTasks?.in_progress?.length || 0}     color="#fbbf24" icon="⚡" />
          <StatCard label="Submitted"       value={myTasks?.submitted?.length || 0}       color="#a78bfa" icon="📤" />
          <StatCard label="Rework Required" value={myTasks?.rework_required?.length || 0} color="#f87171" icon="🔄" />
          <StatCard label="Completed Today" value={myTasks?.completed_today?.length || 0} color="#34d399" icon="✅" />
        </div>
      )}

      {/* My Tasks */}
      <div className="card glass-panel">
        <h3 style={{ margin: '0 0 1.25rem 0', fontSize: '1rem' }}>My Tasks</h3>

        {tasksLoading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>Loading your tasks...</div>
        ) : activeTasks.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🎉</div>
            <p style={{ margin: 0 }}>All clear! No active tasks. Click <strong>Generate / Assign Task</strong> to get started.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
            {/* Rework tasks appear first with a section label */}
            {(myTasks?.rework_required?.length || 0) > 0 && (
              <>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#f87171', textTransform: 'uppercase', letterSpacing: '0.05em', padding: '0.25rem 0' }}>
                  ⚠️ Needs Rework
                </div>
                {myTasks.rework_required.map((t: TaskSummary) => (
                  <TaskCard key={t.id} task={t} onContinue={handleContinue} />
                ))}
                {activeTasks.length > (myTasks?.rework_required?.length || 0) && (
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', padding: '0.5rem 0 0.25rem 0' }}>
                    Other Tasks
                  </div>
                )}
              </>
            )}
            {myTasks?.in_progress?.map((t: TaskSummary) => <TaskCard key={t.id} task={t} onContinue={handleContinue} />)}
            {myTasks?.assigned?.map((t: TaskSummary) => <TaskCard key={t.id} task={t} onContinue={handleContinue} />)}
            {myTasks?.submitted?.map((t: TaskSummary) => <TaskCard key={t.id} task={t} onContinue={handleContinue} />)}
          </div>
        )}
      </div>

      {/* Queue Overview */}
      {stats && (
        <div className="card glass-panel">
          <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem' }}>Queue Overview</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.5rem' }}>
            {stats.per_language.map((ls: LanguageStat) => (
              <div key={ls.language} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '0.625rem 0.875rem',
                background: 'rgba(30,41,59,0.3)', borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-glass)',
              }}>
                <span style={{ fontSize: '0.875rem' }}>🌐 {ls.language}</span>
                <span style={{
                  fontWeight: 700, fontSize: '0.875rem',
                  color: ls.available > 0 ? '#34d399' : '#9ca3af',
                }}>
                  {ls.available}
                </span>
              </div>
            ))}
            {stats.per_language.length === 0 && (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', gridColumn: '1/-1' }}>
                No tasks available in the queue.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Assignment modal */}
      {showModal && stats && (
        <AssignModal
          stats={stats}
          onClose={() => setShowModal(false)}
          onAssigned={handleAssigned}
        />
      )}
    </div>
  );
}
