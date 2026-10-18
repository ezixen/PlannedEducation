import { useState, useEffect } from 'react';
import { UserCheck, UserX, RefreshCw, CheckCircle2 } from 'lucide-react';
import { apiClient } from '../api';
import { useToast } from '../contexts/ToastContext';

export interface PendingTeacher {
  id: string;
  username: string;
  email: string;
  full_name: string | null;
  created_at: string;
  is_active: boolean;
}

export function TeacherApprovalPanel() {
  const { success: showSuccess, error: showError } = useToast();
  const [teachers, setTeachers] = useState<PendingTeacher[]>([]);
  const [loading, setLoading] = useState(false);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const fetchPending = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/admin/pending-teachers');
      setTeachers(res.data);
    } catch (err: any) {
      showError('Failed to load pending teachers', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPending();
  }, []);

  const handleApprove = async (id: string, username: string) => {
    setProcessingId(id);
    try {
      await apiClient.post(`/admin/teachers/${id}/approve`);
      showSuccess(`Approved teacher status for ${username}`);
      setTeachers((prev) => prev.filter((t) => t.id !== id));
    } catch (err: any) {
      showError('Approval failed', err.response?.data?.detail || err.message);
    } finally {
      setProcessingId(null);
    }
  };

  const handleDeny = async (id: string, username: string) => {
    setProcessingId(id);
    try {
      await apiClient.post(`/admin/teachers/${id}/deny`);
      showSuccess(`Declined teacher privileges for ${username} (role set to student)`);
      setTeachers((prev) => prev.filter((t) => t.id !== id));
    } catch (err: any) {
      showError('Denial failed', err.response?.data?.detail || err.message);
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div style={{ maxWidth: '900px' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.25rem',
          flexWrap: 'wrap',
          gap: '0.75rem',
        }}
      >
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-color)', margin: 0 }}>
            🎓 Pending Teacher Approvals
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
            Verify self-registered teachers to protect exam and module integrity. Pending teachers cannot create or publish exams.
          </p>
        </div>
        <button
          onClick={fetchPending}
          disabled={loading}
          style={{
            padding: '0.5rem 0.9rem',
            backgroundColor: 'var(--sidebar-bg)',
            color: 'var(--text-color)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
          }}
        >
          <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
        </button>
      </div>

      {loading && teachers.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          Loading pending teachers...
        </div>
      ) : teachers.length === 0 ? (
        <div
          style={{
            padding: '3rem 1.5rem',
            backgroundColor: 'var(--sidebar-bg)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-lg)',
            textAlign: 'center',
            color: 'var(--text-muted)',
          }}
        >
          <CheckCircle2 size={36} style={{ color: '#10b981', margin: '0 auto 0.75rem' }} />
          <h3 style={{ margin: '0 0 0.25rem', color: 'var(--text-color)', fontSize: '1.1rem' }}>
            All Teachers Verified
          </h3>
          <p style={{ margin: 0, fontSize: '0.85rem' }}>
            There are currently no self-registered teachers awaiting approval.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {teachers.map((t) => (
            <div
              key={t.id}
              style={{
                padding: '1rem 1.25rem',
                backgroundColor: 'var(--sidebar-bg)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '1rem',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-color)' }}>
                    {t.full_name || t.username}
                  </span>
                  <span
                    style={{
                      fontSize: '0.75rem',
                      padding: '0.15rem 0.5rem',
                      backgroundColor: 'rgba(245, 158, 11, 0.1)',
                      color: '#d97706',
                      borderRadius: '9999px',
                      fontWeight: 600,
                    }}
                  >
                    Pending Verification
                  </span>
                </div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                  Username: <strong>{t.username}</strong> • Email: <strong>{t.email}</strong>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
                  Registered on: {new Date(t.created_at).toLocaleDateString()} at{' '}
                  {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <button
                  onClick={() => handleDeny(t.id, t.username)}
                  disabled={processingId === t.id}
                  style={{
                    padding: '0.5rem 0.9rem',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    color: '#ef4444',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    borderRadius: 'var(--radius-md)',
                    cursor: processingId === t.id ? 'not-allowed' : 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                  }}
                >
                  <UserX size={15} />
                  Deny
                </button>
                <button
                  onClick={() => handleApprove(t.id, t.username)}
                  disabled={processingId === t.id}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: '#10b981',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    cursor: processingId === t.id ? 'not-allowed' : 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                  }}
                >
                  <UserCheck size={15} />
                  {processingId === t.id ? 'Approving...' : 'Approve Teacher'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
