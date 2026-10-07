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

// Archive System Types
interface ArchiveItem {
  id: string;
  submission_id: string;
  exam_id: string;
  student_id: string;
  teacher_id: string;
  archive_year: number;
  archive_month: number;
  archive_path: string;
  original_size: number;
  compressed_size: number;
  compression_ratio: number;
  compression_algorithm: string;
  status: string;
  submitted_at: string;
  archived_at: string;
  deleted_from_server_at: string | null;
}

interface ArchiveJob {
  id: string;
  job_type: string;
  status: string;
  graduation_year?: number;
  total_items: number;
  processed_items: number;
  failed_items: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  result_summary: any;
}

interface ArchiveStats {
  total_archives: number;
  total_size_bytes: number;
  total_size_mb: number;
  original_size_bytes: number;
  compression_savings_mb: number;
  by_year: Array<{ year: number; count: number; size_mb: number }>;
}

export function AdminDashboard() {
  const { success: showSuccess, error: showError } = useToast();
  const [activeTab, setActiveTab] = useState<'stats' | 'users' | 'exams' | 'archives'>('stats');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [exams, setExams] = useState<AdminExam[]>([]);
  const [userSearch, setUserSearch] = useState('');
  const [examSearch, setExamSearch] = useState('');
  const [userRoleFilter, setUserRoleFilter] = useState<'all' | 'teacher' | 'student' | 'parent'>('all');
  const [examStatusFilter, setExamStatusFilter] = useState<'all' | 'published' | 'draft'>('all');
  
  // Archive System State
  const [archives, setArchives] = useState<ArchiveItem[]>([]);
  const [archiveJobs, setArchiveJobs] = useState<ArchiveJob[]>([]);
  const [archiveStats, setArchiveStats] = useState<ArchiveStats | null>(null);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [archiveJobLoading, setArchiveJobLoading] = useState(false);
  const [archiveYearFilter, setArchiveYearFilter] = useState<number | 'all'>('all');
  const [archiveMonthFilter, setArchiveMonthFilter] = useState<number | 'all'>('all');
  const [archiveTeacherFilter, setArchiveTeacherFilter] = useState<string>('');
  const [archiveStudentFilter, setArchiveStudentFilter] = useState<string>('');
  const [archiveStatusFilter, setArchiveStatusFilter] = useState<'all' | 'active' | 'archived' | 'deleted'>('all');
  const [showCreateJobModal, setShowCreateJobModal] = useState(false);
  const [newJobParams, setNewJobParams] = useState({
    graduation_year: new Date().getFullYear(),
    teacher_id: '',
    student_id: '',
    archive_to_external: false,
    external_storage_path: '',
    delete_after_archive: true,
    compression_level: 3,
  });

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

  // Archive System Functions
  const fetchArchiveStats = async () => {
    try {
      const response = await apiClient.get('/archive/stats');
      setArchiveStats(response.data);
    } catch (err: any) {
      showError('Failed to load archive stats', err.response?.data?.detail || err.message);
    }
  };

  const fetchArchives = async () => {
    setArchiveLoading(true);
    try {
      const params: Record<string, any> = { limit: 100 };
      if (archiveYearFilter !== 'all') params.year = archiveYearFilter;
      if (archiveMonthFilter !== 'all') params.month = archiveMonthFilter;
      if (archiveTeacherFilter) params.teacher_username = archiveTeacherFilter;
      if (archiveStudentFilter) params.student_username = archiveStudentFilter;
      if (archiveStatusFilter !== 'all') params.status = archiveStatusFilter;
      
      const response = await apiClient.get('/archive/list', { params });
      setArchives(response.data);
    } catch (err: any) {
      showError('Failed to load archives', err.response?.data?.detail || err.message);
    } finally {
      setArchiveLoading(false);
    }
  };

  const fetchArchiveJobs = async () => {
    setArchiveJobLoading(true);
    try {
      const response = await apiClient.get('/archive/jobs');
      setArchiveJobs(response.data);
    } catch (err: any) {
      showError('Failed to load archive jobs', err.response?.data?.detail || err.message);
    } finally {
      setArchiveJobLoading(false);
    }
  };

  const handleCreateArchiveJob = async () => {
    try {
      await apiClient.post('/archive/jobs', newJobParams);
      showSuccess('Archive job created');
      setShowCreateJobModal(false);
      fetchArchiveJobs();
    } catch (err: any) {
      showError('Failed to create archive job', err.response?.data?.detail || err.message);
    }
  };

  const handleStartArchiveJob = async (jobId: string) => {
    try {
      await apiClient.post(`/archive/jobs/${jobId}/start`);
      showSuccess('Archive job started');
      fetchArchiveJobs();
    } catch (err: any) {
      showError('Failed to start archive job', err.response?.data?.detail || err.message);
    }
  };

  const handleRestoreArchive = async (archiveId: string) => {
    if (!window.confirm('Restore this archive to server storage?')) return;
    try {
      await apiClient.post('/archive/restore', { archive_id: archiveId, target_location: 'server' });
      showSuccess('Archive restored');
      fetchArchives();
    } catch (err: any) {
      showError('Failed to restore archive', err.response?.data?.detail || err.message);
    }
  };

  const handleDeleteArchive = async (archiveId: string) => {
    if (!window.confirm('Delete this archive from server storage? External backup will be kept.')) return;
    try {
      await apiClient.delete(`/archive/archives/${archiveId}`, { params: { keep_external: true } });
      showSuccess('Archive deleted from server');
      fetchArchives();
    } catch (err: any) {
      showError('Failed to delete archive', err.response?.data?.detail || err.message);
    }
  };

  const handleDownloadArchive = async (archiveId: string) => {
    try {
      const response = await apiClient.get(`/archive/download/${archiveId}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `archive-${archiveId}.zst.enc`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      showSuccess('Archive downloaded');
    } catch (err: any) {
      showError('Failed to download archive', err.response?.data?.detail || err.message);
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
    else if (activeTab === 'archives') {
      fetchArchiveStats();
      fetchArchives();
      fetchArchiveJobs();
    }
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
          { id: 'archives', label: '📦 Archives', count: archives.length },
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

      {/* Archives Tab */}
      {activeTab === 'archives' && (
        <div>
          {/* Archive Stats Cards */}
          {archiveStats && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
              {[
                { label: 'Total Archives', value: archiveStats.total_archives, color: '#8b5cf6', icon: '📦' },
                { label: 'Total Size', value: `${archiveStats.total_size_mb} MB`, color: '#3b82f6', icon: '💾' },
                { label: 'Original Size', value: `${archiveStats.original_size_bytes / (1024*1024)} MB`, color: '#6b7280', icon: '📄' },
                { label: 'Space Saved', value: `${archiveStats.compression_savings_mb} MB`, color: '#10b981', icon: '✨' },
              ].map((stat, i) => (
                <div key={i} style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', textAlign: 'center' }}>
                  <div style={{ fontSize: '2.5rem', fontWeight: 700, color: stat.color }}>{stat.value}</div>
                  <div style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>{stat.icon} {stat.label}</div>
                </div>
              ))}
            </div>
          )}

          {/* Archive Jobs */}
          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>📋 Archive Jobs</h3>
              <button
                onClick={() => setShowCreateJobModal(true)}
                style={{ padding: '0.5rem 1rem', backgroundColor: '#8b5cf6', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500 }}
              >
                + Create Archive Job
              </button>
            </div>

            {archiveJobLoading ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>Loading jobs...</div>
            ) : archiveJobs.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>No archive jobs yet. Create one to archive graduated students' tests.</div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid var(--border-color)' }}>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Job Type</th>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Status</th>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Graduation Year</th>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Progress</th>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Created</th>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Started</th>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Completed</th>
                      <th style={{ padding: '1rem', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {archiveJobs.map(job => (
                      <tr key={job.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '1rem', fontWeight: 500, color: 'var(--text-color)' }}>{job.job_type}</td>
                        <td style={{ padding: '1rem' }}>
                          <span style={{
                            padding: '0.25rem 0.75rem',
                            borderRadius: '9999px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            backgroundColor: 
                              job.status === 'completed' ? '#10b98120' :
                              job.status === 'running' ? '#3b82f620' :
                              job.status === 'failed' ? '#ef444420' : '#f59e0b20',
                            color: 
                              job.status === 'completed' ? '#10b981' :
                              job.status === 'running' ? '#3b82f6' :
                              job.status === 'failed' ? '#ef4444' : '#f59e0b',
                          }}>
                            {job.status}
                          </span>
                        </td>
                        <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{job.graduation_year || 'All'}</td>
                        <td style={{ padding: '1rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <div style={{ flex: 1, height: '6px', backgroundColor: 'var(--border-color)', borderRadius: '3px', overflow: 'hidden' }}>
                              <div style={{ 
                                width: `${job.total_items > 0 ? (job.processed_items / job.total_items) * 100 : 0}%`, 
                                height: '100%', 
                                backgroundColor: job.status === 'failed' ? '#ef4444' : '#8b5cf6',
                                transition: 'width 0.3s ease'
                              }} />
                            </div>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                              {job.processed_items}/{job.total_items} ({job.failed_items} failed)
                            </span>
                          </div>
                        </td>
                        <td style={{ padding: '1rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                          {job.created_at ? new Date(job.created_at).toLocaleString() : '—'}
                        </td>
                        <td style={{ padding: '1rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                          {job.started_at ? new Date(job.started_at).toLocaleString() : '—'}
                        </td>
                        <td style={{ padding: '1rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                          {job.completed_at ? new Date(job.completed_at).toLocaleString() : '—'}
                        </td>
                        <td style={{ padding: '1rem', textAlign: 'right' }}>
                          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                            {job.status === 'pending' && (
                              <button
                                onClick={() => handleStartArchiveJob(job.id)}
                                disabled={archiveJobLoading}
                                style={{
                                  padding: '0.5rem 1rem',
                                  backgroundColor: '#8b5cf6',
                                  color: '#fff',
                                  border: 'none',
                                  borderRadius: 'var(--radius-md)',
                                  cursor: archiveJobLoading ? 'not-allowed' : 'pointer',
                                  fontSize: '0.85rem',
                                }}
                              >
                                Start
                              </button>
                            )}
                            {job.status === 'completed' && job.result_summary && (
                              <button
                                onClick={() => alert(JSON.stringify(job.result_summary, null, 2))}
                                style={{
                                  padding: '0.5rem 1rem',
                                  backgroundColor: 'var(--secondary-color)',
                                  color: '#fff',
                                  border: 'none',
                                  borderRadius: 'var(--radius-md)',
                                  cursor: 'pointer',
                                  fontSize: '0.85rem',
                                }}
                              >
                                View Results
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Create Job Modal */}
          {showCreateJobModal && (
            <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1rem' }}>
              <div style={{ backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', maxWidth: '500px', width: '100%', maxHeight: '90vh', overflow: 'auto' }}>
                <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Create Archive Job</h2>
                  <button onClick={() => setShowCreateJobModal(false)} style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: 'var(--text-muted)' }}>×</button>
                </div>
                <div style={{ padding: '1.5rem' }}>
                  <div style={{ marginBottom: '1rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Graduation Year</label>
                    <select
                      value={newJobParams.graduation_year}
                      onChange={e => setNewJobParams({...newJobParams, graduation_year: parseInt(e.target.value)})}
                      style={{ width: '100%', padding: '0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
                    >
                      {Array.from({length: 10}, (_, i) => new Date().getFullYear() - i).map(y => (
                        <option key={y} value={y}>{y}</option>
                      ))}
                    </select>
                  </div>
                  <div style={{ marginBottom: '1rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Compression Level (1-19, higher = smaller but slower)</label>
                    <input
                      type="number"
                      min={1}
                      max={19}
                      value={newJobParams.compression_level}
                      onChange={e => setNewJobParams({...newJobParams, compression_level: parseInt(e.target.value)})}
                      style={{ width: '100%', padding: '0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
                    />
                  </div>
                  <div style={{ marginBottom: '1rem' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={newJobParams.delete_after_archive}
                        onChange={e => setNewJobParams({...newJobParams, delete_after_archive: e.target.checked})}
                      />
                      <span>Delete from server after archiving (keep external backup)</span>
                    </label>
                  </div>
                  <div style={{ marginBottom: '1rem' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={newJobParams.archive_to_external}
                        onChange={e => setNewJobParams({...newJobParams, archive_to_external: e.target.checked})}
                      />
                      <span>Archive to external storage (USB, network share, etc.)</span>
                    </label>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                    <button onClick={() => setShowCreateJobModal(false)} style={{ padding: '0.625rem 1.25rem', backgroundColor: 'var(--secondary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500 }}>
                      Cancel
                    </button>
                    <button 
                      onClick={handleCreateArchiveJob}
                      disabled={archiveJobLoading}
                      style={{ padding: '0.625rem 1.25rem', backgroundColor: '#8b5cf6', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500 }}
                    >
                      Create Job
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Archived Submissions List */}
          <div style={{ marginTop: '2rem' }}>
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
              <select
                value={archiveYearFilter}
                onChange={e => { setArchiveYearFilter(e.target.value === 'all' ? 'all' : parseInt(e.target.value)); fetchArchives(); }}
                style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
              >
                <option value="all">All Years</option>
                {Array.from({length: 10}, (_, i) => new Date().getFullYear() - i).map(y => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
              <select
                value={archiveMonthFilter}
                onChange={e => { setArchiveMonthFilter(e.target.value === 'all' ? 'all' : parseInt(e.target.value)); fetchArchives(); }}
                style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
              >
                <option value="all">All Months</option>
                {Array.from({length: 12}, (_, i) => i + 1).map(m => (
                  <option key={m} value={m}>{m.toString().padStart(2, '0')}</option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Teacher username..."
                value={archiveTeacherFilter}
                onChange={e => { setArchiveTeacherFilter(e.target.value); fetchArchives(); }}
                style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', minWidth: '150px' }}
              />
              <input
                type="text"
                placeholder="Student username..."
                value={archiveStudentFilter}
                onChange={e => { setArchiveStudentFilter(e.target.value); fetchArchives(); }}
                style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', minWidth: '150px' }}
              />
              <select
                value={archiveStatusFilter}
                onChange={e => { setArchiveStatusFilter(e.target.value as any); fetchArchives(); }}
                style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
              >
                <option value="all">All Statuses</option>
                <option value="active">Active</option>
                <option value="archived">Archived</option>
                <option value="deleted">Deleted from Server</option>
              </select>
            </div>

            {archiveLoading ? (
              <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>Loading archives...</div>
            ) : archives.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>No archives found</div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid var(--border-color)' }}>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Submission ID</th>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Exam</th>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Student</th>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Teacher</th>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Year/Month</th>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Original Size</th>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Compressed</th>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Ratio</th>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Status</th>
                      <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Archived</th>
                      <th style={{ padding: '1rem', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {archives.map(archive => (
                      <tr key={archive.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '1rem', fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--text-color)' }}>{archive.submission_id.slice(0, 12)}...</td>
                        <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{archive.exam_id.slice(0, 8)}...</td>
                        <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{archive.student_id.slice(0, 8)}...</td>
                        <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{archive.teacher_id.slice(0, 8)}...</td>
                        <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{archive.archive_year}/{archive.archive_month.toString().padStart(2, '0')}</td>
                        <td style={{ padding: '1rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>{(archive.original_size / 1024).toFixed(1)} KB</td>
                        <td style={{ padding: '1rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>{(archive.compressed_size / 1024).toFixed(1)} KB</td>
                        <td style={{ padding: '1rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>{archive.compression_ratio.toFixed(1)}x</td>
                        <td style={{ padding: '1rem' }}>
                          <span style={{
                            padding: '0.25rem 0.75rem',
                            borderRadius: '9999px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            backgroundColor: 
                              archive.status === 'active' ? '#10b98120' :
                              archive.status === 'archived' ? '#8b5cf620' : '#ef444420',
                            color: 
                              archive.status === 'active' ? '#10b981' :
                              archive.status === 'archived' ? '#8b5cf6' : '#ef4444',
                          }}>
                            {archive.status}
                          </span>
                        </td>
                        <td style={{ padding: '1rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                          {archive.archived_at ? new Date(archive.archived_at).toLocaleDateString() : '—'}
                        </td>
                        <td style={{ padding: '1rem', textAlign: 'right' }}>
                          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                            <button
                              onClick={() => handleDownloadArchive(archive.id)}
                              style={{ padding: '0.5rem 1rem', backgroundColor: '#3b82f6', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontSize: '0.85rem' }}
                            >
                              Download
                            </button>
                            {archive.status === 'archived' && (
                              <button
                                onClick={() => handleRestoreArchive(archive.id)}
                                style={{ padding: '0.5rem 1rem', backgroundColor: '#10b981', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontSize: '0.85rem' }}
                              >
                                Restore
                              </button>
                            )}
                            {archive.status === 'active' && (
                              <button
                                onClick={() => handleDeleteArchive(archive.id)}
                                style={{ padding: '0.5rem 1rem', backgroundColor: '#ef4444', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontSize: '0.85rem' }}
                              >
                                Archive
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}