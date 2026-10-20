import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../api';
import { ChatGptPanel } from '../components/ChatGptPanel';
import { useI18n } from '../contexts/I18nContext';

export function ExamEditor() {
  const { t } = useI18n();
  const { id } = useParams<{ id: string }>();
  const [exam, setExam] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // New Question Form
  const [qType, setQType] = useState('multiple_choice');
  const [qText, setQText] = useState('');

  const fetchExam = useCallback(async () => {
    if (!id) {
      setExam(null);
      setLoading(false);
      return;
    }
    try {
      const response = await apiClient.get(`/exams/${id}`);
      setExam(response.data);
    } catch (e) {
      console.error(e);
      setExam(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void fetchExam();
  }, [fetchExam]);

  const addQuestion = async () => {
    if (!qText) return;
    try {
      await apiClient.post(`/exams/${id}/questions`, {
        question_type: qType,
        text: qText,
        points: 1
      });
      setQText('');
      await fetchExam();
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) return <div>{t('common.loading')}</div>;
  if (!exam) return <div>{t('errors.5')}</div>;

  return (
    <div>
      <Link to="/teacher-exams" style={{ color: '#3b82f6', textDecoration: 'none', marginBottom: '1rem', display: 'inline-block' }}>&larr; {t('exam_editor.back_to_exams')}</Link>
      <h1 style={{ marginBottom: '0.5rem' }}>{exam.title}</h1>
      <p style={{ color: 'gray', marginBottom: '2rem' }}>{exam.seb_config_key ? t('exam_editor.seb_enabled') : t('exam_editor.seb_not_set')}</p>

      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', marginBottom: '2rem' }}>
        <h3>{t('exam_editor.add_question')}</h3>
        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', alignItems: 'flex-start' }}>
          <select value={qType} onChange={e => setQType(e.target.value)} style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
            <option value="multiple_choice">{t('exam_editor.12')}</option>
            <option value="essay">{t('exam_editor.13')}</option>
            <option value="dynamic_math">{t('exam_editor.14')}</option>
          </select>
          <input 
            type="text" 
            placeholder={t('exam_editor.question_type_placeholder')} 
            value={qText} 
            onChange={e => setQText(e.target.value)} 
            style={{ padding: '0.5rem', flex: 1, borderRadius: '4px', border: '1px solid var(--border-color)' }}
          />
          <button onClick={addQuestion} style={{ padding: '0.5rem 1rem', backgroundColor: '#10b981', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>{t('exam_editor.add_button')}</button>
        </div>
      </div>

      <ChatGptPanel
        compact
        quickActionLabel={t('exam_editor.add_question')}
        onBuildQuickPrompt={() => 
          `Draft 3 new ${qType.replace('_', ' ')} questions with answers and rubrics for the exam "${exam.title}".`
        }
      />

      <h3>{t('exam_editor.question_bank')} ({exam.questions?.length || 0})</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
        {exam.questions?.map((q: any, idx: number) => (
          <div key={q.id} style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
            <strong>{idx + 1}. {q.text}</strong>
            <div style={{ color: 'gray', fontSize: '0.9rem', marginTop: '0.5rem' }}>
              {t('exam_editor.type')}: <span style={{ textTransform: 'capitalize' }}>{q.question_type.replace('_', ' ')}</span> | {t('exam_editor.points')}: {q.points}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
