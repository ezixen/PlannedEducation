import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useI18n } from '../contexts/I18nContext';
import { apiClient } from '../api';
import { FileText, Clock, ShieldCheck, CheckCircle2, ArrowLeft } from 'lucide-react';

interface ExamItem {
  id: string;
  title: string;
  duration_minutes: number;
  created_at?: string;
  seb_required?: boolean;
}

export function StudentDashboard() {
  const { t } = useI18n();
  const navigate = useNavigate();

  const [exams, setExams] = useState<ExamItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchExams();
  }, []);

  const fetchExams = async () => {
    try {
      const response = await apiClient.get('/exams/');
      setExams(response.data || []);
    } catch (err) {
      console.error('Failed to fetch student exams:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '1.5rem', boxSizing: 'border-box' }}>
      {/* Header with Back Button */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
        <button
          onClick={() => navigate('/')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            padding: '0.5rem 0.9rem',
            borderRadius: 'var(--radius-md, 8px)',
            border: '1px solid var(--border-color, #e2e8f0)',
            backgroundColor: 'var(--sidebar-bg, #fff)',
            color: 'var(--text-color, #1e293b)',
            cursor: 'pointer',
            fontSize: '0.9rem',
            fontWeight: 500,
          }}
          aria-label={t('nav.back')}
        >
          <ArrowLeft size={16} />
          {t('nav.back')}
        </button>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-color)' }}>
            {t('student_dashboard.title')}
          </h1>
          <p style={{ margin: '0.25rem 0 0', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            {t('student_dashboard.subtitle')}
          </p>
        </div>
      </div>

      {/* Info Notice Box */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '0.75rem',
          padding: '1rem 1.25rem',
          backgroundColor: 'rgba(59, 130, 246, 0.08)',
          border: '1px solid rgba(59, 130, 246, 0.25)',
          borderRadius: 'var(--radius-lg, 12px)',
          marginBottom: '2rem',
          color: 'var(--text-color)',
          fontSize: '0.875rem',
          lineHeight: 1.5,
        }}
      >
        <ShieldCheck size={20} style={{ color: '#2563eb', flexShrink: 0, marginTop: '2px' }} />
        <div>
          <strong style={{ color: '#1d4ed8' }}>{t('student_dashboard.seb_required')}:</strong>{' '}
          {t('student_dashboard.quick_tips')}
        </div>
      </div>

      {/* Section 1: Upcoming & Active Exams */}
      <div style={{ marginBottom: '2.5rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-color)', marginBottom: '1rem' }}>
          {t('student_dashboard.upcoming_title')}
        </h2>

        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            {t('common.loading')}
          </div>
        ) : exams.length === 0 ? (
          <div
            style={{
              padding: '2.5rem 1.5rem',
              backgroundColor: 'var(--sidebar-bg, #fff)',
              borderRadius: 'var(--radius-lg, 12px)',
              border: '1px dashed var(--border-color, #cbd5e1)',
              textAlign: 'center',
            }}
          >
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1rem',
                color: '#10b981',
              }}
            >
              <FileText size={24} />
            </div>
            <h3 style={{ margin: '0 0 0.5rem', fontSize: '1.1rem', color: 'var(--text-color)' }}>
              {t('student_dashboard.no_upcoming')}
            </h3>
            <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              {t('student_dashboard.seb_hint')}
            </p>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
            {exams.map((exam) => (
              <div
                key={exam.id}
                style={{
                  padding: '1.25rem',
                  backgroundColor: 'var(--sidebar-bg, #fff)',
                  borderRadius: 'var(--radius-lg, 12px)',
                  border: '1px solid var(--border-color, #e2e8f0)',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                }}
              >
                <div>
                  <h3 style={{ margin: '0 0 0.5rem', fontSize: '1.1rem', color: 'var(--text-color)' }}>
                    {exam.title}
                  </h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '0.75rem' }}>
                    <Clock size={15} />
                    {t('student_dashboard.duration', { minutes: String(exam.duration_minutes || 60) })}
                  </div>
                </div>
                <button
                  onClick={() => navigate(`/exam/${exam.id}`)}
                  style={{
                    width: '100%',
                    padding: '0.65rem 1rem',
                    backgroundColor: 'var(--primary-color, #10b981)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 'var(--radius-md, 8px)',
                    fontWeight: 600,
                    fontSize: '0.9rem',
                    cursor: 'pointer',
                    marginTop: '0.5rem',
                  }}
                >
                  {t('student_dashboard.take_exam_btn')}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Section 2: Completed / Graded Exams */}
      <div>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-color)', marginBottom: '1rem' }}>
          {t('student_dashboard.completed_title')}
        </h2>
        <div
          style={{
            padding: '2rem 1.5rem',
            backgroundColor: 'var(--sidebar-bg, #fff)',
            borderRadius: 'var(--radius-lg, 12px)',
            border: '1px solid var(--border-color, #e2e8f0)',
            textAlign: 'center',
            color: 'var(--text-muted)',
            fontSize: '0.9rem',
          }}
        >
          <CheckCircle2 size={32} style={{ color: '#94a3b8', margin: '0 auto 0.75rem' }} />
          <div>{t('student_dashboard.no_completed')}</div>
        </div>
      </div>
    </div>
  );
}
