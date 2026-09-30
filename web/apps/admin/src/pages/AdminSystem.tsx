import { useState } from 'react';
import { useAdmin } from '../contexts/AdminContext';

export function AdminSystem() {
  const { stats, fetchStats } = useAdmin();
  const [loadingEnv, setLoadingEnv] = useState(false);

  const handleRefreshStats = async () => {
    setLoadingEnv(true);
    try {
      await fetchStats();
    } finally {
      setLoadingEnv(false);
    }
  };

  return (
    <div>
      <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-color)', marginBottom: '1.5rem' }}>System Settings</h2>

      {/* Environment Status */}
      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', marginBottom: '1.5rem' }}>
        <h3 style={{ margin: '0 0 1rem', fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-color)' }}>Environment Status</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
          <div style={{ padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Database</div>
            <div style={{ fontWeight: 600, color: 'var(--text-color)' }}>PostgreSQL</div>
          </div>
          <div style={{ padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Cache / PubSub</div>
            <div style={{ fontWeight: 600, color: 'var(--text-color)' }}>Redis</div>
          </div>
          <div style={{ padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Monitoring</div>
            <div style={{ fontWeight: 600, color: 'var(--text-color)' }}>Prometheus + Grafana</div>
          </div>
          <div style={{ padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Frontend</div>
            <div style={{ fontWeight: 600, color: 'var(--text-color)' }}>React + Vite (PWA)</div>
          </div>
        </div>
      </div>

      {/* System Stats */}
      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-color)' }}>System Statistics</h3>
          <button
            onClick={handleRefreshStats}
            disabled={loadingEnv}
            style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: loadingEnv ? 'not-allowed' : 'pointer', fontWeight: 500, fontSize: '0.85rem' }}
          >
            {loadingEnv ? 'Refreshing...' : 'Refresh Stats'}
          </button>
        </div>
        {stats && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div style={{ padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Total Users</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--primary-color)' }}>{stats.totalUsers.toLocaleString()}</div>
            </div>
            <div style={{ padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Total Exams</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#8b5cf6' }}>{stats.totalExams.toLocaleString()}</div>
            </div>
            <div style={{ padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Total Submissions</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#10b981' }}>{stats.totalSubmissions.toLocaleString()}</div>
            </div>
            <div style={{ padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Active Exams</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#f59e0b' }}>{stats.activeExams.toLocaleString()}</div>
            </div>
          </div>
        )}
      </div>

      {/* Security & Compliance */}
      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', marginBottom: '1.5rem' }}>
        <h3 style={{ margin: '0 0 1rem', fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-color)' }}>Security & Compliance</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
          <div style={{ padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '1.2rem' }}>🔐</span>
              <span style={{ fontWeight: 600, color: 'var(--text-color)' }}>Authentication</span>
            </div>
            <ul style={{ margin: 0, paddingLeft: '1.25rem', color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: 1.8 }}>
              <li>Google SSO (Primary)</li>
              <li>TOTP 2FA (Optional)</li>
              <li>Argon2id Password Hashing</li>
              <li>JWT HS256 (60-min expiry)</li>
            </ul>
          </div>
          <div style={{ padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '1.2rem' }}>🛡️</span>
              <span style={{ fontWeight: 600, color: 'var(--text-color)' }}>Data Protection</span>
            </div>
            <ul style={{ margin: 0, paddingLeft: '1.25rem', color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: 1.8 }}>
              <li>Fernet Encryption (AI Keys)</li>
              <li>TLS 1.3 in Production</li>
              <li>PII Anonymization Pipeline</li>
              <li>Field-Level Encryption</li>
            </ul>
          </div>
          <div style={{ padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '1.2rem' }}>📋</span>
              <span style={{ fontWeight: 600, color: 'var(--text-color)' }}>Compliance</span>
            </div>
            <ul style={{ margin: 0, paddingLeft: '1.25rem', color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: 1.8 }}>
              <li>OWASP ASVS 5.0.0</li>
              <li>OWASP Top 10:2025</li>
              <li>NIST SSDF / 800-63B</li>
              <li>GDPR-Ready (Proctoring)</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Maintenance Actions */}
      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
        <h3 style={{ margin: '0 0 1rem', fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-color)' }}>Maintenance Actions</h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
          <button style={{ padding: '0.75rem 1.5rem', backgroundColor: '#3b82f6', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500, fontSize: '0.9rem' }}>
            Run Database Migrations
          </button>
          <button style={{ padding: '0.75rem 1.5rem', backgroundColor: '#8b5cf6', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500, fontSize: '0.9rem' }}>
            Clear Cache
          </button>
          <button style={{ padding: '0.75rem 1.5rem', backgroundColor: '#f59e0b', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500, fontSize: '0.9rem' }}>
            Rebuild Search Index
          </button>
          <button style={{ padding: '0.75rem 1.5rem', backgroundColor: '#ef4444', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500, fontSize: '0.9rem' }}>
            Emergency Lockdown
          </button>
        </div>
      </div>
    </div>
  );
}