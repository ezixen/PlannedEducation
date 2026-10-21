import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api';
import { useI18n } from '../contexts/I18nContext';
import { OCRProcessor } from '../components/OCRProcessor';
import { STTProcessor } from '../components/STTProcessor';

export function TeacherExams() {
  const { t } = useI18n();
  const [exams, setExams] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [newTitle, setNewTitle] = useState('');

  useEffect(() => {
    fetchExams();
  }, []);

  const fetchExams = async () => {
    try {
      const response = await apiClient.get('/exams/mine');

      setExams(response.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const createExam = async () => {
    if (!newTitle) return;
    try {
      await apiClient.post('/exams/', { title: newTitle, duration_minutes: 60 });
      setNewTitle('');
      fetchExams();
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) return <div>{t('common.loading')}</div>;

  return (
    <div>
      <h1>{t('exams.manage_title')}</h1>
      <p style={{ color: 'gray', marginBottom: '2rem' }}>{t('exams.manage_subtitle')}</p>

      <div style={{ marginBottom: '2rem', display: 'flex', gap: '1rem' }}>
        <input 
          type="text" 
          placeholder={t('exams.new_title_placeholder')} 
          value={newTitle} 
          onChange={(e) => setNewTitle(e.target.value)} 
          style={{ padding: '0.5rem', flex: 1, borderRadius: '4px', border: '1px solid var(--border-color)' }}
        />
        <button onClick={createExam} style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
          {t('exams.create_button')}
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {exams.length === 0 ? (
          <p>{t('common.no_exams_yet')}</p>
        ) : (
          exams.map(exam => (
            <div key={exam.id} style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: '0 0 0.5rem 0' }}>{exam.title}</h3>
                <small style={{ color: 'gray' }}>{exam.duration_minutes} {t('exams.duration_minutes')} | {exam.questions?.length || 0} {t('exams.questions_count')}</small>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <Link to={`/teacher-exams/${exam.id}`} style={{ padding: '0.5rem 1rem', backgroundColor: '#3b82f6', color: '#fff', textDecoration: 'none', borderRadius: '4px' }}>
                  {t('exams.edit_questions')}
                </Link>
                <Link to={`/teacher-dashboard/${exam.id}`} style={{ padding: '0.5rem 1rem', backgroundColor: '#8b5cf6', color: '#fff', textDecoration: 'none', borderRadius: '4px' }}>
                  {t('exams.ai_grading')}
                </Link>
              </div>
            </div>
          ))
        )}
      </div>

      {/* OCR Processor - Handwritten Math OCR */}
      <div style={{ marginTop: '3rem', padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
        <h3 style={{ margin: '0 0 1rem', fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-color)' }}>{t('ocr.1')}</h3>
        <OCRProcessor />
      </div>

      {/* Speech-to-Text Processor */}
      <div style={{ marginTop: '1.5rem', padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
        <h3 style={{ margin: '0 0 1rem', fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-color)' }}>{t('stt.processor_title')}</h3>
        <STTProcessor />
      </div>

    </div>
  );
}

