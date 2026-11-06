import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../api';
import { ChatGptPanel } from '../components/ChatGptPanel';
import { useI18n } from '../contexts/I18nContext';
import { useToast } from '../contexts/ToastContext';
import { useSpecialCharacters } from '../contexts/SpecialCharactersContext';
import { packagesService, MODULE_LANGUAGES, type SpecialCharacterSet } from '../services/packages';

function loadSpecialChars(examId: string): SpecialCharacterSet[] {
  try {
    const raw = localStorage.getItem(`pe_exam_special_chars_${examId}`);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function ExamEditor() {
  const { t, locale } = useI18n();
  const { success: showSuccess, error: showError } = useToast();
  const { setCustomCategories, clearCustomCategories } = useSpecialCharacters();
  const { id } = useParams<{ id: string }>();
  const [exam, setExam] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [platformHomeExam, setPlatformHomeExam] = useState(false);
  const [savingDelivery, setSavingDelivery] = useState(false);

  // Module Language & Country metadata
  const defaultLang = MODULE_LANGUAGES.find(l => l.code === locale) || MODULE_LANGUAGES[0];
  const [moduleLang, setModuleLang] = useState(defaultLang.code);
  const [moduleCountry, setModuleCountry] = useState(defaultLang.defaultCountry);
  const [specialCharSets, setSpecialCharSets] = useState<SpecialCharacterSet[]>([]);
  const [newCategory, setNewCategory] = useState('');
  const [newChars, setNewChars] = useState('');

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
      const [response, featureRes] = await Promise.all([
        apiClient.get(`/exams/${id}`),
        apiClient.get('/proctoring/feature-status').catch(() => ({ data: { home_exam_proctoring_enabled: false } })),
      ]);
      setExam(response.data);
      setPlatformHomeExam(Boolean(featureRes.data?.home_exam_proctoring_enabled));
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
      const chars = loadSpecialChars(id);
      setSpecialCharSets(chars);
      setCustomCategories(chars);
    } catch (e) {
      console.error(e);
      setExam(null);
    } finally {
      setLoading(false);
    }
  }, [id, setCustomCategories]);

  useEffect(() => {
    void fetchExam();
    return () => clearCustomCategories();
  }, [fetchExam, clearCustomCategories]);

  const setDeliveryMode = async (homeExamEnabled: boolean) => {
    if (!id) return;
    setSavingDelivery(true);
    try {
      const res = await apiClient.put(`/exams/${id}/delivery-mode`, {
        home_exam_enabled: homeExamEnabled,
      });
      setExam(res.data);
      showSuccess(
        homeExamEnabled ? t('home_exam.exam_enabled_ok') : t('home_exam.exam_classroom_ok'),
      );
    } catch (err: any) {
      console.error(err);
      showError(err.response?.data?.detail || t('home_exam.exam_save_failed'));
    } finally {
      setSavingDelivery(false);
    }
  };

  const persistSpecialChars = (sets: SpecialCharacterSet[]) => {
    if (!id) return;
    localStorage.setItem(`pe_exam_special_chars_${id}`, JSON.stringify(sets));
    // Keep module meta in sync so package export can pick them up
    try {
      const metaRaw = localStorage.getItem(`pe_exam_meta_${id}`);
      const meta = metaRaw ? JSON.parse(metaRaw) : {};
      meta.special_characters = sets;
      localStorage.setItem(`pe_exam_meta_${id}`, JSON.stringify(meta));
    } catch {
      // ignore
    }
    setSpecialCharSets(sets);
    setCustomCategories(sets);
    showSuccess(t('special_chars.module_saved'));
  };

  const handleAddSpecialCharSet = () => {
    const category = newCategory.trim();
    const chars = newChars
      .split(/[\s,]+/)
      .map((c) => c.trim())
      .filter(Boolean);
    if (!category || chars.length === 0) return;
    persistSpecialChars([...specialCharSets, { category, chars }]);
    setNewCategory('');
    setNewChars('');
  };

  const handleRemoveSpecialCharSet = (idx: number) => {
    persistSpecialChars(specialCharSets.filter((_, i) => i !== idx));
  };

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
        special_characters: loadSpecialChars(id),
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
      <p style={{ color: 'gray', marginBottom: '1rem' }}>{exam.seb_config_key ? t('exam_editor.seb_enabled') : t('exam_editor.seb_not_set')}</p>

      <div style={{ padding: '1.25rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', marginBottom: '1.5rem' }}>
        <h3 style={{ margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          {t('home_exam.exam_mode_title')}
          <span style={{ fontSize: '0.7rem', padding: '0.15rem 0.45rem', borderRadius: '9999px', backgroundColor: '#f59e0b', color: '#111' }}>
            {t('home_exam.beta_badge')}
          </span>
        </h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.75rem', lineHeight: 1.45 }}>
          {t('home_exam.exam_mode_desc')}
        </p>
        {!platformHomeExam && (
          <p style={{ fontSize: '0.8rem', color: '#92400e', backgroundColor: '#fffbeb', border: '1px solid #f59e0b', borderRadius: '6px', padding: '0.6rem 0.75rem', marginBottom: '0.75rem' }}>
            {t('home_exam.platform_disabled_hint')}
          </p>
        )}
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            disabled={savingDelivery}
            onClick={() => void setDeliveryMode(false)}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '6px',
              border: exam.home_exam_enabled ? '1px solid var(--border-color)' : '2px solid var(--primary-color)',
              backgroundColor: exam.home_exam_enabled ? 'var(--bg-color)' : 'rgba(59, 130, 246, 0.12)',
              color: 'var(--text-color)',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            {t('home_exam.mode_classroom')}
          </button>
          <button
            type="button"
            disabled={savingDelivery || !platformHomeExam}
            onClick={() => void setDeliveryMode(true)}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '6px',
              border: exam.home_exam_enabled ? '2px solid #f59e0b' : '1px solid var(--border-color)',
              backgroundColor: exam.home_exam_enabled ? 'rgba(245, 158, 11, 0.15)' : 'var(--bg-color)',
              color: 'var(--text-color)',
              cursor: platformHomeExam ? 'pointer' : 'not-allowed',
              fontWeight: 600,
              opacity: platformHomeExam ? 1 : 0.55,
            }}
          >
            {t('home_exam.mode_home')}
          </button>
        </div>
        {exam.home_exam_enabled && (
          <p style={{ fontSize: '0.8rem', color: '#92400e', marginTop: '0.75rem', lineHeight: 1.4 }}>
            {t('home_exam.legal_warning')}
          </p>
        )}
      </div>

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

      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', marginBottom: '2rem' }}>
        <h3 style={{ marginTop: 0 }}>{t('special_chars.module_title')}</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
          {t('special_chars.module_desc')}
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginBottom: '0.75rem' }}>
          <input
            type="text"
            value={newCategory}
            onChange={(e) => setNewCategory(e.target.value)}
            placeholder={t('special_chars.module_category')}
            style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}
          />
          <input
            type="text"
            value={newChars}
            onChange={(e) => setNewChars(e.target.value)}
            placeholder={t('special_chars.module_chars')}
            style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}
          />
          <button
            type="button"
            onClick={handleAddSpecialCharSet}
            style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}
          >
            {t('special_chars.module_add')}
          </button>
        </div>
        {specialCharSets.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {specialCharSets.map((set, idx) => (
              <div
                key={`${set.category}-${idx}`}
                style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'center', padding: '0.65rem 0.75rem', border: '1px solid var(--border-color)', borderRadius: '6px', backgroundColor: 'var(--bg-color)' }}
              >
                <div>
                  <strong>{set.category}</strong>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    {set.chars.join(' ')}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleRemoveSpecialCharSet(idx)}
                  style={{ background: 'none', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '0.35rem 0.65rem', cursor: 'pointer', color: 'var(--error-color)' }}
                >
                  {t('special_chars.module_remove')}
                </button>
              </div>
            ))}
          </div>
        )}
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
