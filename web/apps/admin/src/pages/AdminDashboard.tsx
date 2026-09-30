import { useAdmin } from '../contexts/AdminContext';

export function AdminDashboard() {
  const { stats, loading, error } = useAdmin();

  if (loading && !stats) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '300px' }}>
        <div style={{ fontSize: '1.2rem', color: 'var(--text-muted)' }}>Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '1rem', backgroundColor: '#fef2f2', border: '1px solid #fecaca', borderRadius: 'var(--radius-md)', color: '#dc2626' }}>
        {error}
      </div>
    );
  }

  const statCards = [
    { label: 'Total Users', value: stats?.totalUsers ?? 0, icon: '👥', color: 'var(--primary-color)' },
    { label: 'Total Exams', value: stats?.totalExams ?? 0, icon: '📝', color: '#8b5cf6' },
    { label: 'Total Submissions', value: stats?.totalSubmissions ?? 0, icon: '📤', color: '#10b981' },
    { label: 'Active Exams', value: stats?.activeExams ?? 0, icon: '🟢', color: '#f59e0b' },
  ];

  return (
    <div>
      <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-color)', marginBottom: '1.5rem' }}>Overview</h2>
      
      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        {statCards.map((stat, idx) => (
          <div key={idx} style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '2rem' }}>{stat.icon}</span>
              <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 500 }}>{stat.label}</span>
            </div>
            <div style={{ fontSize: '2.5rem', fontWeight: 700, color: stat.color, lineHeight: 1 }}>
              {stat.value.toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
        <h3 style={{ margin: '0 0 1rem', fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-color)' }}>Quick Actions</h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
          <a href="/admin/users" style={{ padding: '0.75rem 1.5rem', backgroundColor: 'var(--primary-color)', color: '#fff', borderRadius: 'var(--radius-md)', textDecoration: 'none', fontWeight: 500, fontSize: '0.9rem' }}>
            Manage Users
          </a>
          <a href="/admin/exams" style={{ padding: '0.75rem 1.5rem', backgroundColor: '#3b82f6', color: '#fff', borderRadius: 'var(--radius-md)', textDecoration: 'none', fontWeight: 500, fontSize: '0.9rem' }}>
            View All Exams
          </a>
          <a href="/admin/system" style={{ padding: '0.75rem 1.5rem', backgroundColor: '#6b7280', color: '#fff', borderRadius: 'var(--radius-md)', textDecoration: 'none', fontWeight: 500, fontSize: '0.9rem' }}>
            System Settings
          </a>
        </div>
      </div>
    </div>
  );
}