import { useState } from 'react';
import { useAdmin } from '../contexts/AdminContext';

export function AdminExams() {
  const { exams, loading, error, deleteExam } = useAdmin();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'published' | 'draft'>('all');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const filteredExams = exams.filter(exam => {
    const matchesSearch = exam.title.toLowerCase().includes(search.toLowerCase()) ||
      exam.teacher_name.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'all' || (statusFilter === 'published' ? exam.is_published : !exam.is_published);
    return matchesSearch && matchesStatus;
  });

  const handleDelete = async (examId: string) => {
    if (!confirm('Are you sure you want to delete this exam? This action cannot be undone.')) return;
    setDeletingId(examId);
    try {
      await deleteExam(examId);
    } catch (err) {
      // Error handled in context
    } finally {
      setDeletingId(null);
    }
  };

  if (loading && exams.length === 0) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '300px' }}>
        <div style={{ fontSize: '1.2rem', color: 'var(--text-muted)' }}>Loading exams...</div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-color)' }}>Exam Management</h2>
        
        {/* Filters */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center' }}>
          <input
            type="text"
            placeholder="Search exams..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ padding: '0.625rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.95rem', minWidth: '250px' }}
          />
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value as typeof statusFilter)}
            style={{ padding: '0.625rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.95rem' }}
          >
            <option value="all">All Status</option>
            <option value="published">Published</option>
            <option value="draft">Draft</option>
          </select>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            {filteredExams.length} of {exams.length} exams
          </span>
        </div>
      </div>

      {error && (
        <div style={{ padding: '1rem', backgroundColor: '#fef2f2', border: '1px solid #fecaca', borderRadius: 'var(--radius-md)', color: '#dc2626', marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      {/* Exams Table */}
      <div style={{ backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Exam</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Teacher</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Questions</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Submissions</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Status</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Created</th>
                <th style={{ padding: '1rem', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredExams.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No exams found matching your criteria.
                  </td>
                </tr>
              ) : (
                filteredExams.map(exam => (
                  <tr key={exam.id} style={{ borderBottom: '1px solid var(--border-color)', transition: 'background-color 0.15s' }}>
                    <td style={{ padding: '1rem' }}>
                      <div style={{ fontWeight: 500, color: 'var(--text-color)' }}>
                        {exam.title}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                        {exam.id}
                      </div>
                    </td>
                    <td style={{ padding: '1rem', color: 'var(--text-color)' }}>
                      {exam.teacher_name}
                    </td>
                    <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>
                      {exam.question_count}
                    </td>
                    <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>
                      {exam.submission_count}
                    </td>
                    <td style={{ padding: '1rem' }}>
                      <span
                        style={{
                          display: 'inline-block',
                          padding: '0.25rem 0.75rem',
                          borderRadius: '9999px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          backgroundColor: exam.is_published ? '#10b98120' : '#f59e0b20',
                          color: exam.is_published ? '#10b981' : '#f59e0b',
                        }}
                      >
                        {exam.is_published ? 'Published' : 'Draft'}
                      </span>
                    </td>
                    <td style={{ padding: '1rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                      {new Date(exam.created_at).toLocaleDateString()}
                    </td>
                    <td style={{ padding: '1rem', textAlign: 'right' }}>
                      <button
                        onClick={() => handleDelete(exam.id)}
                        disabled={deletingId === exam.id}
                        style={{
                          padding: '0.5rem 1rem',
                          backgroundColor: deletingId === exam.id ? '#9ca3af' : '#ef4444',
                          color: '#fff',
                          border: 'none',
                          borderRadius: 'var(--radius-md)',
                          cursor: deletingId === exam.id ? 'not-allowed' : 'pointer',
                          fontWeight: 500,
                          fontSize: '0.85rem',
                          transition: 'background-color 0.15s',
                        }}
                      >
                        {deletingId === exam.id ? 'Deleting...' : 'Delete'}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}