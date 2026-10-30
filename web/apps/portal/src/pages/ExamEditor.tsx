import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../api';
import { ChatGptPanel } from '../components/ChatGptPanel';
import { useI18n } from '../contexts/I18nContext';
import { packagesService, MODULE_LANGUAGES } from '../services/packages';

export function ExamEditor() {
  const { t, locale } = useI18n();
  const { id } = useParams<{ id: string }>();
  const [exam, setExam] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Module Language & Country metadata
  const defaultLang = MODULE_LANGUAGES.find(l => l.code === locale) || MODULE_LANGUAGES[0];
  const [moduleLang, setModuleLang] = useState(defaultLang.code);
  const [moduleCountry, setModuleCountry] = useState(defaultLang.defaultCountry);

  // New Question Form
  const [qType, setQType] = useState('multiple_choice');
  const [qText, setQText] = useState('');
  const [qOptions, setQOptions] = useState('Option A, Option B, Option C, Option D');
  const [qCorrectAnswer, setQCorrectAnswer] = useState('Option A');
  const [qRubric, setQRubric] = useState('');
  const [qPoints, setQPoints] = useState(1);

  const fetchExam = useCallback(async () => {
    if (!id) {
      setExam(null);
      setLoading(false);
      return;
    }
    try {
      const response = await apiClient.get(`/exams/${id}`);
      setExam(response.data);
      const raw = localStorage.getItem(`pe_exam_meta_${id}`);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed.language) setModuleLang(parsed.language);
        if (parsed.country) setModuleCountry(parsed.country);
      } else {
        const desc = String(response.data?.description || '');
        const m = desc.match(/^\[([A-Za-z-]+)\s*-\s*([^|\]]+)(?:\|\s*([^\]]+))?\]/);
        if (m) {
          setModuleLang(m[1].trim().toLowerCase());
          if (m[3]) setModuleCountry(m[3].trim().toLowerCase());
        }
      }
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
    if (!qText || !id) return;
    try {
      const parsedOptions =
        qType === 'multiple_choice'
          ? qOptions
              .split(/[\n,]+/)
              .map(s => s.trim())
              .filter(Boolean)
          : null;

      await apiClient.post(`/exams/${id}/questions`, {
        question_type: qType,
        text: qText,
        options_json: parsedOptions && parsedOptions.length > 0 ? JSON.stringify(parsedOptions) : null,
        correct_answer: qCorrectAnswer || null,
        rubric: qRubric || null,
        points: Number(qPoints) || 1,
      });
      setQText('');
      await fetchExam();

      // Auto-sync module to the selected country folder on server
      const langObj = MODULE_LANGUAGES.find(l => l.code === moduleLang);
      await packagesService.exportPackage({
        exam_id: id,
        include_answers: true,
        include_rubrics: true,
        include_variables: true,
        format: 'json',
        compress: false,
        language: moduleLang,
        language_name: langObj?.name || moduleLang,
        country: moduleCountry,
        save_to_server: true,
      });
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) return <div>{t('common.loading')}</div>;
  if (!exam) return <div>{t('errors.5')}</div>;

  const currentLangObj = MODULE_LANGUAGES.find(l => l.code === moduleLang);

  return (
    <div>
      <Link to="/teacher-exams" style={{ color: '#3b82f6', textDecoration: 'none', marginBottom: '1rem', display: 'inline-block' }}>
        &larr; {t('exam_editor.back_to_exams')}
      </Link>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
        <h1 style={{ margin: 0 }}>{exam.title}</h1>
        <span style={{ padding: '0.2rem 0.65rem', borderRadius: '9999px', fontSize: '0.8rem', fontWeight: 600, backgroundColor: 'rgba(59, 130, 246, 0.15)', color: '#3b82f6' }}>
          🌐 {moduleLang.toUpperCase()} — {currentLangObj?.name || moduleLang}
        </span>
        <span style={{ padding: '0.2rem 0.65rem', borderRadius: '9999px', fontSize: '0.8rem', backgroundColor: 'rgba(16, 185, 129, 0.15)', color: '#10b981' }}>
          📁 {moduleCountry}
        </span>
      </div>
      <p style={{ color: 'gray', marginBottom: '2rem' }}>{exam.seb_config_key ? t('exam_editor.seb_enabled') : t('exam_editor.seb_not_set')}</p>

      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', marginBottom: '2rem' }}>
        <h3>{t('exam_editor.add_question')}</h3>
        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
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
            style={{ padding: '0.5rem', flex: 1, minWidth: '240px', borderRadius: '4px', border: '1px solid var(--border-color)' }}
          />
          <button onClick={addQuestion} style={{ padding: '0.5rem 1rem', backgroundColor: '#10b981', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
            {t('exam_editor.add_button')}
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginTop: '0.85rem' }}>
          {qType === 'multiple_choice' && (
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>{t('exam_editor.16')}</label>
              <textarea
                value={qOptions}
                onChange={e => setQOptions(e.target.value)}
                placeholder={t('exam_editor.16')}
                rows={3}
                style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}
              />
            </div>
          )}
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>{t('exam_editor.17')}</label>
            <input
              type="text"
              value={qCorrectAnswer}
              onChange={e => setQCorrectAnswer(e.target.value)}
              placeholder={t('exam_editor.17')}
              style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>{t('exam_editor.18')}</label>
            <input
              type="text"
              value={qRubric}
              onChange={e => setQRubric(e.target.value)}
              placeholder={t('exam_editor.18')}
              style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>{t('exam_editor.19')}</label>
            <input
              type="number"
              min={1}
              max={100}
              value={qPoints}
              onChange={e => setQPoints(Number(e.target.value) || 1)}
              style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}
            />
          </div>
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
