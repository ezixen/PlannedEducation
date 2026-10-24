import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api';
import { useI18n } from '../contexts/I18nContext';
import { OCRProcessor } from '../components/OCRProcessor';
import { STTProcessor } from '../components/STTProcessor';
import { MODULE_LANGUAGES } from '../services/packages';

export function TeacherExams() {
  const { t, locale } = useI18n();
  const [exams, setExams] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [newTitle, setNewTitle] = useState('');

  const defaultLang = MODULE_LANGUAGES.find(l => l.code === locale) || MODULE_LANGUAGES[0];
  const [examLanguage, setExamLanguage] = useState(defaultLang.code);
  const [examCountry, setExamCountry] = useState(defaultLang.defaultCountry);

  useEffect(() => {
    void fetchExams();
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
      const langObj = MODULE_LANGUAGES.find(l => l.code === examLanguage) || MODULE_LANGUAGES[0];
      const langTag = `[${examLanguage.toUpperCase()} - ${langObj.name} | ${examCountry}]`;
      const res = await apiClient.post('/exams/', {
        title: newTitle,
        description: langTag,
        duration_minutes: 60,
      });
      if (res.data?.id) {
        localStorage.setItem(
          `pe_exam_meta_${res.data.id}`,
          JSON.stringify({
            language: examLanguage,
            language_name: langObj.name,
            country: examCountry,
          })
        );
      }
      setNewTitle('');
      void fetchExams();
    } catch (e) {
      console.error(e);
    }
  };

  const getExamLanguageInfo = (exam: any) => {
    try {
      const raw = localStorage.getItem(`pe_exam_meta_${exam.id}`);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed.language) {
          return {
            code: String(parsed.language).toUpperCase(),
            name: String(parsed.language_name || parsed.language),
            country: String(parsed.country || ''),
          };
        }
      }
    } catch {
      // ignore
    }
    const desc = String(exam.description || '');
    const m = desc.match(/^\[([A-Za-z-]+)\s*-\s*([^|\]]+)(?:\|\s*([^\]]+))?\]/);
    if (m) {
      return {
        code: m[1].trim().toUpperCase(),
        name: m[2].trim(),
        country: (m[3] || '').trim(),
      };
    }
    return { code: 'EN', name: 'English', country: 'usa' };
  };

  if (loading) return <div>{t('common.loading')}</div>;

  return (
    <div>
      <h1>{t('exams.manage_title')}</h1>
      <p style={{ color: 'gray', marginBottom: '2rem' }}>{t('exams.manage_subtitle')}</p>

      <div style={{ marginBottom: '2rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          type="text"
          placeholder={t('exams.new_title_placeholder')}
          value={newTitle}
          onChange={e => setNewTitle(e.target.value)}
          style={{ padding: '0.5rem', flex: 1, minWidth: '220px', borderRadius: '4px', border: '1px solid var(--border-color)' }}
        />
        <select
          aria-label={t('settings.tab_language')}
          value={examLanguage}
          onChange={e => {
            const code = e.target.value;
            const found = MODULE_LANGUAGES.find(l => l.code === code);
            setExamLanguage(code);
            if (found) setExamCountry(found.defaultCountry);
          }}
          style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
        >
          {MODULE_LANGUAGES.map(l => (
            <option key={l.code} value={l.code}>
              🌐 {l.name} ({l.code.toUpperCase()})
            </option>
          ))}
        </select>
        <input
          type="text"
          value={examCountry}
          onChange={e => setExamCountry(e.target.value)}
          style={{ width: '130px', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}
        />
        <button onClick={createExam} style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
          {t('exams.create_button')}
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {exams.length === 0 ? (
          <p>{t('common.no_exams_yet')}</p>
        ) : (
          exams.map(exam => {
            const langInfo = getExamLanguageInfo(exam);
            return (
              <div key={exam.id} style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.35rem' }}>
                    <h3 style={{ margin: 0 }}>{exam.title}</h3>
                    <span style={{ padding: '0.15rem 0.5rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: 'rgba(59, 130, 246, 0.15)', color: '#3b82f6' }}>
                      🌐 {langInfo.code} — {langInfo.name}
                    </span>
                    {langInfo.country && (
                      <span style={{ padding: '0.15rem 0.5rem', borderRadius: '9999px', fontSize: '0.75rem', backgroundColor: 'rgba(16, 185, 129, 0.15)', color: '#10b981' }}>
                        📁 {langInfo.country}
                      </span>
                    )}
                  </div>
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
            );
          })
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
