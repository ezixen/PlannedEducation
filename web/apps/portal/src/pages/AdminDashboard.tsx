import { useState, useEffect } from 'react';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../api';

interface AdminStats {
  totalUsers: number;
  totalExams: number;
  totalSubmissions: number;
  activeExams: number;
}

interface AdminUser {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  created_at: string | null;
  last_login: string | null;
}

interface AdminExam {
  id: string;
  title: string;
  teacher_id: string;
  teacher_name: string;
  question_count: number;
  submission_count: number;
  is_published: boolean;
  created_at: string | null;
}

export function AdminDashboard() {
  const { success: showSuccess, error: showError } = useToast();
  const [activeTab, setActiveTab] = useState<'stats' | 'users' | 'exams'>('stats');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [exams, setExams] = useState<AdminExam[]>([]);
  const [userSearch, setUserSearch] = useState('');
  const [examSearch, setExamSearch] = useState('');
  const [userRoleFilter, setUserRoleFilter] = useState<'all' | 'teacher' | 'student' | 'parent'>('all');
  const [examStatusFilter, setExamStatusFilter] = useState<'all' | 'published' | 'draft'>('all');

  const fetchStats = async () => {
    try {
      const response = await apiClient.get('/admin/stats');
      setStats(response.data);
    } catch (err: any) {
      showError('Failed to load stats', err.response?.data?.detail || err.message);
    }
  };

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/admin/users');
      setUsers(response.data);
    } catch (err: any) {
      showError('Failed to load users', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchExams = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/admin/exams');
      setExams(response.data);
    } catch (err: any) {
      showError('Failed to load exams', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleUserActive = async (user: AdminUser) => {
    try {
      await apiClient.patch(`/admin/users/${user.id}`, null, {
        params: { is_active: !user.is_active },
      });
      showSuccess(`User ${!user.is_active ? 'activated' : 'deactivated'}`);
      fetchUsers();
    } catch (err: any) {
      showError('Failed to update user', err.response?.data?.detail || err.message);
    }
  };

  const handleDeleteUser = async (user: AdminUser) => {
    if (!window.confirm(`Are you sure you want to delete user "${user.username}"? This action cannot be undone.`)) {
      return;
    }
    try {
      await apiClient.delete(`/admin/users/${user.id}`);
      showSuccess('User deleted');
      fetchUsers();
    } catch (err: any) {
      showError('Failed to delete user', err.response?.data?.detail || err.message);
    }
  };

  const handleDeleteExam = async (exam: AdminExam) => {
    if (!window.confirm(`Are you sure you want to delete exam "${exam.title}"? This action cannot be undone.`)) {
      return;
    }
    try {
      await apiClient.delete(`/admin/exams/${exam.id}`);
      showSuccess('Exam deleted');
      fetchExams();
    } catch (err: any) {
      showError('Failed to delete exam', err.response?.data?.detail || err.message);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    if (activeTab === 'users') fetchUsers();
    else if (activeTab === 'exams') fetchExams();
  }, [activeTab]);

  const filteredUsers = users.filter(u => {
    const matchesSearch = u.username.toLowerCase().includes(userSearch.toLowerCase()) ||
      u.email.toLowerCase().includes(userSearch.toLowerCase()) ||
      (u.full_name?.toLowerCase().includes(userSearch.toLowerCase()) ?? false);
    const matchesRole = userRoleFilter === 'all' || u.role === userRoleFilter;
    return matchesSearch && matchesRole;
  });

  const filteredExams = exams.filter(e => {
    const matchesSearch = e.title.toLowerCase().includes(examSearch.toLowerCase()) ||
      e.teacher_name.toLowerCase().includes(examSearch.toLowerCase());
    const matchesStatus = examStatusFilter === 'all' ||
      (examStatusFilter === 'published' && e.is_published) ||
      (examStatusFilter === 'draft' && !e.is_published);
    return matchesSearch && matchesStatus;
  });

  const roleBadgeStyle = (role: string) => {
    const colors: Record<string, string> = {
      teacher: '#3b82f6',
      student: '#10b981',
      parent: '#8b5cf6',
    };
    return colors[role] || '#6b7280';
  };

  return (
    <div style={{ padding: '1.5rem' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-color)', marginBottom: '0.25rem' }}>
          Teacher Admin Dashboard
        </h1>
        <p style={{ color: 'var(--text-muted)' }}>
          System oversight tools for teachers. Manage users, monitor exams, and view platform statistics.
        </p>
      </div>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
        {[
          { id: 'stats', label: '📊 Statistics', count: null },
          { id: 'users', label: '👥 Users', count: users.length },
          { id: 'exams', label: '📝 Exams', count: exams.length },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: activeTab === tab.id ? 'var(--primary-color)' : 'transparent',
              color: activeTab === tab.id ? '#fff' : 'var(--text-color)',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            {tab.label}
            {tab.count !== null && (
              <span style={{
                backgroundColor: activeTab === tab.id ? 'rgba(255,255,255,0.2)' : 'var(--bg-color)',
                padding: '0.125rem 0.5rem',
                borderRadius: '9999px',
                fontSize: '0.75rem',
              }}>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Stats Tab */}
      {activeTab === 'stats' && (
        <div>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>Loading statistics...</div>
          ) : stats ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
              {[
                { label: 'Total Users', value: stats.totalUsers, color: '#3b82f6', icon: '👥' },
                { label: 'Total Exams', value: stats.totalExams, color: '#8b5cf6', icon: '📝' },
                { label: 'Total Submissions', value: stats.totalSubmissions, color: '#10b981', icon: '📄' },
                { label: 'Active Exams', value: stats.activeExams, color: '#f59e0b', icon: '🟢' },
              ].map((stat, i) => (
                <div key={i} style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', textAlign: 'center' }}>
                  <div style={{ fontSize: '2.5rem', fontWeight: 700, color: stat.color }}>{stat.value}</div>
                  <div style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>{stat.icon} {stat.label}</div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>No statistics available</div>
          )}
        </div>
      )}

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div>
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Search users..."
              value={userSearch}
              onChange={e => setUserSearch(e.target.value)}
              style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', flex: 1, minWidth: '200px' }}
            />
            <select
              value={userRoleFilter}
              onChange={e => setUserRoleFilter(e.target.value as any)}
              style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
            >
              <option value="all">All Roles</option>
              <option value="teacher">Teachers</option>
              <option value="student">Students</option>
              <option value="parent">Parents</option>
            </select>
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>Loading users...</div>
          ) : filteredUsers.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>No users found</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid var(--border-color)' }}>
                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>User</th>
                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Role</th>
                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Status</th>
                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Created</th>
                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Last Login</th>
                    <th style={{ padding: '1rem', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map(user => (
                    <tr key={user.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: '1rem' }}>
                        <div style={{ fontWeight: 500, color: 'var(--text-color)' }}>{user.username}</div>
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{user.email}</div>
                        {user.full_name && <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{user.full_name}</div>}
                      </td>
                      <td style={{ padding: '1rem' }}>
                        <span style={{
                          padding: '0.25rem 0.75rem',
                          borderRadius: '9999px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          backgroundColor: `${roleBadgeStyle(user.role)}20`,
                          color: roleBadgeStyle(user.role),
                        }}>
                          {user.role}
                        </span>
                      </td>
                      <td style={{ padding: '1rem' }}>
                        <span style={{
                          padding: '0.25rem 0.75rem',
                          borderRadius: '9999px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          backgroundColor: user.is_active ? '#10b98120' : '#ef444420',
                          color: user.is_active ? '#10b981' : '#ef4444',
                        }}>
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td style={{ padding: '1rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        {user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td style={{ padding: '1rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        {user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}
                      </td>
                      <td style={{ padding: '1rem', textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                          <button
                            onClick={() => handleToggleUserActive(user)}
                            disabled={loading}
                            style={{
                              padding: '0.5rem 1rem',
                              backgroundColor: user.is_active ? '#f59e0b' : '#10b981',
                              color: '#fff',
                              border: 'none',
                              borderRadius: 'var(--radius-md)',
                              cursor: loading ? 'not-allowed' : 'pointer',
                              fontSize: '0.85rem',
                            }}
                          >
                            {user.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                          <button
                            onClick={() => handleDeleteUser(user)}
                            disabled={loading}
                            style={{
                              padding: '0.5rem 1rem',
                              backgroundColor: '#ef4444',
                              color: '#fff',
                              border: 'none',
                              borderRadius: 'var(--radius-md)',
                              cursor: loading ? 'not-allowed' : 'pointer',
                              fontSize: '0.85rem',
                            }}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Exams Tab */}
      {activeTab === 'exams' && (
        <div>
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Search exams..."
              value={examSearch}
              onChange={e => setExamSearch(e.target.value)}
              style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', flex: 1, minWidth: '200px' }}
            />
            <select
              value={examStatusFilter}
              onChange={e => setExamStatusFilter(e.target.value as any)}
              style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
            >
              <option value="all">All Exams</option>
              <option value="published">Published (has submissions)</option>
              <option value="draft">Drafts (no submissions)</option>
            </select>
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>Loading exams...</div>
          ) : filteredExams.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>No exams found</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid var(--border-color)' }}>
                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Exam</th>
                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Teacher</th>
                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Questions</th>
                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Submissions</th>
                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Status</th>
                    <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Created</th>
                    <th style={{ padding: '1rem', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredExams.map(exam => (
                    <tr key={exam.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: '1rem' }}>
                        <div style={{ fontWeight: 500, color: 'var(--text-color)' }}>{exam.title}</div>
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>ID: {exam.id.slice(0, 8)}...</div>
                      </td>
                      <td style={{ padding: '1rem', color: 'var(--text-color)' }}>{exam.teacher_name}</td>
                      <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{exam.question_count}</td>
                      <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{exam.submission_count}</td>
                      <td style={{ padding: '1rem' }}>
                        <span style={{
                          padding: '0.25rem 0.75rem',
                          borderRadius: '9999px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          backgroundColor: exam.is_published ? '#10b98120' : '#f59e0b20',
                          color: exam.is_published ? '#10b981' : '#f59e0b',
                        }}>
                          {exam.is_published ? 'Published' : 'Draft'}
                        </span>
                      </td>
                      <td style={{ padding: '1rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        {exam.created_at ? new Date(exam.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td style={{ padding: '1rem', textAlign: 'right' }}>
                        <button
                          onClick={() => handleDeleteExam(exam)}
                          disabled={loading}
                          style={{
                            padding: '0.5rem 1rem',
                            backgroundColor: '#ef4444',
                            color: '#fff',
                            border: 'none',
                            borderRadius: 'var(--radius-md)',
                            cursor: loading ? 'not-allowed' : 'pointer',
                            fontSize: '0.85rem',
                          }}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}