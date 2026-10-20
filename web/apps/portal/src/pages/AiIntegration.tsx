import { API_URL } from '../api';
import { ChatGptPanel } from '../components/ChatGptPanel';
import { useI18n } from '../contexts/I18nContext';

export function AiIntegration() {
  const { t } = useI18n();
  const systemPrompt = `You are an expert, objective teacher and AI grader working for the Planned Education platform. Your job is to assist teachers in grading exams, grouping mistakes, and transcribing handwritten math or audio feedback. You must be strictly objective, unbiased, and format your output cleanly. You are processing anonymized data to protect student privacy.`;

  return (
    <div>
      <h1>{t('ai_keys.16')}</h1>
      <p style={{ color: 'gray', marginBottom: '1.5rem' }}>
        {t('ai_keys.17')}
      </p>

      <ChatGptPanel defaultInstructions={systemPrompt} />

      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', marginBottom: '2rem' }}>
        <h3>{t('ai_keys.18')}</h3>
        <p>{t('ai_keys.19')}</p>
        <code style={{ display: 'block', padding: '1rem', backgroundColor: '#000', color: '#10b981', borderRadius: '4px', marginBottom: '1rem' }}>
          GET {API_URL}/anonymizer/exams/&#123;exam_id&#125;/submissions
        </code>
        <p>{t('ai_keys.20')}</p>
        <code style={{ display: 'block', padding: '1rem', backgroundColor: '#000', color: '#10b981', borderRadius: '4px' }}>
          POST {API_URL}/anonymizer/submissions/&#123;submission_id&#125;/grades
        </code>
      </div>

      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', marginBottom: '2rem' }}>
        <h3>{t('ai_keys.21')}</h3>
        <p>{t('ai_keys.22')}</p>
        <blockquote style={{ borderLeft: '4px solid var(--primary-color)', paddingLeft: '1rem', fontStyle: 'italic', color: 'gray' }}>
          "{systemPrompt}"
        </blockquote>
      </div>

      <h3>{t('ai_keys.10')}</h3>
      <div style={{ display: 'grid', gap: '1rem', marginTop: '1rem' }}>
        
        <div style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
          <h4 style={{ margin: '0 0 0.5rem 0', color: '#3b82f6' }}>1. {t('ai_keys.11')}</h4>
          <p style={{ fontSize: '0.9rem', margin: 0 }}>{t('ai_keys.23')}</p>
        </div>

        <div style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
          <h4 style={{ margin: '0 0 0.5rem 0', color: '#10b981' }}>2. {t('ai_keys.13')}</h4>
          <p style={{ fontSize: '0.9rem', margin: 0 }}>{t('ai_keys.24')}</p>
        </div>

        <div style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
          <h4 style={{ margin: '0 0 0.5rem 0', color: '#f59e0b' }}>3. {t('ai_keys.12')}</h4>
          <p style={{ fontSize: '0.9rem', margin: 0 }}>{t('ai_keys.25')}</p>
        </div>

        <div style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
          <h4 style={{ margin: '0 0 0.5rem 0', color: '#ef4444' }}>4. {t('ai_keys.14')}</h4>
          <p style={{ fontSize: '0.9rem', margin: 0 }}>{t('ai_keys.26')}</p>
        </div>

      </div>
    </div>
  );
}
