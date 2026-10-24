import { useState, useEffect } from 'react';
import { useI18n } from '../contexts/I18nContext';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../api';
import { Upload, ArrowLeft } from 'lucide-react';

interface Submission {
  id: string;
  student_name: string;
  student_email: string;
  exam_title: string;
  submitted_at: string;
  status: 'ungraded' | 'ai_graded' | 'teacher_graded' | 'returned' | 'pending_approval' | 'graded';
  score: number | null;
  feedback: string | null;
  question_count: number;
  has_ai_grades: boolean;
}

export function AIGradingUpload() {
  const { t } = useI18n();
  const { user } = useAuth();
  const { success: showSuccess, error: showError } = useToast();

  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedSubmission, setSelectedSubmission] = useState<Submission | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'grade'>('list');

  useEffect(() => {
    loadSubmissions();
  }, []);

  const loadSubmissions = async () => {
    try {
      const response = await apiClient.get('/ai/submissions');
      setSubmissions(response.data || []);
    } catch (err: any) {
      console.error('Failed to load submissions:', err);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('teacher_id', user!.id);

      await apiClient.post('/ai/grade/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      showSuccess(t('ai_grading.upload_success'));
      setUploading(false);
      (e.target as HTMLInputElement).value = '';
      loadSubmissions();
    } catch (err: any) {
      showError(t('ai_grading.upload_error') + ': ' + (err.response?.data?.detail || err.message));
      setUploading(false);
    }
  };

  const handleAIGrade = async (submissionId: string) => {
    setLoading(true);
    try {
      await apiClient.post(`/ai/grade/${submissionId}`);
      showSuccess(t('ai_grading.ai_grade_success'));
      setLoading(false);
      loadSubmissions();
    } catch (err: any) {
      showError('AI grading failed: ' + (err.response?.data?.detail || err.message));
      setLoading(false);
    }
  };

  const handleDownload = async (submissionId: string) => {
    try {
      const response = await apiClient.get(`/ai/submissions/${submissionId}/download`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data as BlobPart]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `submission-${submissionId}.pdf`);
      document.body.appendChild(link);
      (link as HTMLAnchorElement).click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      showError('Download failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleReturnToStudent = async (submissionId: string) => {
    setLoading(true);
    try {
      await apiClient.post(`/ai/submissions/${submissionId}/return`);
      showSuccess(t('ai_grading.return_success'));
      setLoading(false);
      loadSubmissions();
    } catch (err: any) {
      showError('Failed to return exam: ' + (err.response?.data?.detail || err.message));
      setLoading(false);
    }
  };

  const ungradedCount = submissions.filter(s => s.status === 'ungraded').length;

  if (viewMode === 'grade' && selectedSubmission) {
    return (
      <div style={{ padding: '1rem', maxWidth: '800px', margin: '0 auto' }}>
        <button
          onClick={() => { setViewMode('list'); setSelectedSubmission(null); }}
          style={{ marginBottom: '1rem', padding: '0.5rem 1rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <ArrowLeft size={16} />
          {t('nav.back')}
        </button>
        <h2 style={{ marginBottom: '1rem', color: 'var(--text-color)' }}>{t('ai_grading.grade_submission', { name: selectedSubmission.student_name })}</h2>
        <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
          <p><strong>{t('ai_grading.exam')}:</strong> {selectedSubmission.exam_title}</p>
          <p><strong>{t('ai_grading.student')}:</strong> {selectedSubmission.student_name} ({selectedSubmission.student_email})</p>
          <p><strong>{t('ai_grading.submitted')}:</strong> {selectedSubmission.submitted_at ? new Date(selectedSubmission.submitted_at).toLocaleDateString() : '—'}</p>
          <p><strong>{t('ai_grading.questions')}:</strong> {selectedSubmission.question_count}</p>
          <div style={{ marginTop: '1.5rem', display: 'flex', gap: '0.75rem' }}>
            <button
              onClick={() => handleAIGrade(selectedSubmission!.id)}
              disabled={loading}
              style={{ padding: '0.75rem 1.5rem', backgroundColor: loading ? '#94a3b8' : '#10b981', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 600 }}
            >
              {loading ? t('ai_grading.processing') : t('ai_grading.use_ai_grade')}
            </button>
            <button
              onClick={() => handleDownload(selectedSubmission!.id)}
              style={{ padding: '0.75rem 1.5rem', backgroundColor: '#3b82f6', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 600 }}
            >
              {t('ai_grading.download')}
            </button>
            <button
              onClick={() => handleReturnToStudent(selectedSubmission!.id)}
              style={{ padding: '0.75rem 1.5rem', backgroundColor: '#8b5cf6', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 600 }}
            >
              {t('ai_grading.return_to_student')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '1rem', maxWidth: '1000px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-color)' }}>{t('ai_grading.title')}</h1>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.zip,.txt,.json"
            onChange={handleUpload}
            style={{ display: 'none' }}
          />
          <button
            onClick={() => (document.querySelector('input[type="file"]') as HTMLInputElement)?.click()}
            disabled={uploading}
            style={{ padding: '0.75rem 1.5rem', backgroundColor: uploading ? '#94a3b8' : 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: uploading ? 'not-allowed' : 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <Upload size={18} />
            {t('ai_grading.upload_exam')}
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <div style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem', color: '#f59e0b' }}>{ungradedCount}</div>
          <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>{t('ai_grading.ungraded')}</div>
        </div>
        <div style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem', color: '#10b981' }}>{submissions.filter(s => s.status === 'ai_graded' || s.status === 'pending_approval').length}</div>
          <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>{t('ai_grading.ai_graded')}</div>
        </div>
        <div style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem', color: '#3b82f6' }}>{submissions.filter(s => s.status === 'teacher_graded' || s.status === 'graded').length}</div>
          <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>{t('ai_grading.teacher_graded')}</div>
        </div>
      </div>

      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
        <h3 style={{ margin: '0 0 1rem', fontSize: '1.1rem', color: 'var(--text-color)' }}>{t('ai_grading.submissions_list')}</h3>
        {submissions.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>{t('ai_grading.no_submissions')}</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {submissions.map(sub => (
              <div key={sub.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)' }}>
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--text-color)' }}>{sub.student_name}</div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{sub.exam_title} • {sub.question_count} {t('ai_grading.questions')}</div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{sub.submitted_at ? new Date(sub.submitted_at).toLocaleDateString() : '—'}</div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <span style={{ padding: '0.2rem 0.6rem', borderRadius: '999px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: sub.status === 'ungraded' ? '#fef3c7' : (sub.status === 'ai_graded' || sub.status === 'pending_approval') ? '#d1fae5' : '#dbeafe', color: sub.status === 'ungraded' ? '#92400e' : (sub.status === 'ai_graded' || sub.status === 'pending_approval') ? '#065f46' : '#1e40af' }}>
                    {t('ai_grading.status_' + sub.status)}
                  </span>
                  <button
                    onClick={() => { setSelectedSubmission(sub); setViewMode('grade'); }}
                    style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontSize: '0.85rem' }}
                  >
                    {t('ai_grading.review')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default AIGradingUpload;
