import { useState } from 'react';
import { apiClient } from '../api';
import { useToast } from '../contexts/ToastContext';
import { useI18n } from '../contexts/I18nContext';

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.625rem',
  marginTop: '0.25rem',
  borderRadius: 'var(--radius-md)',
  border: '1px solid var(--border-color)',
  backgroundColor: 'var(--bg-color)',
  color: 'var(--text-color)',
  fontSize: '0.95rem',
};

const labelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '0.375rem',
  fontSize: '0.9rem',
  fontWeight: 500,
  color: 'var(--text-color)',
};

const buttonStyle: React.CSSProperties = {
  padding: '0.625rem 1.5rem',
  backgroundColor: 'var(--primary-color)',
  color: '#fff',
  border: 'none',
  borderRadius: 'var(--radius-md)',
  cursor: 'pointer',
  fontWeight: 600,
  fontSize: '0.95rem',
};

export function STTProcessor() {
  const { success: showSuccess, error: showError } = useToast();
  const { t } = useI18n();
  
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [result, setResult] = useState<{
    text: string;
    language: string;
    language_probability: number;
    duration: number;
    segments?: any[];
    error?: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState('en');
  const [task, setTask] = useState<'transcribe' | 'translate'>('transcribe');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAudioFile(file);
      setResult(null);
    }
  };

  const handleProcess = async () => {
    if (!audioFile) {
      showError(t('stt.select_file_first'));
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', audioFile);
      formData.append('language', language);
      formData.append('task', task);

      const response = await apiClient.post('/stt/transcribe-upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setResult(response.data);
      showSuccess(`${t('stt.transcription_completed')} (${response.data.language}, ${response.data.duration.toFixed(1)}s)`);
    } catch (err: any) {
      showError(t('stt.transcription_failed'), err.response?.data?.detail || err.message);
      setResult({ 
        text: '', 
        language: '', 
        language_probability: 0, 
        duration: 0, 
        error: err.response?.data?.detail || err.message 
      });
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setAudioFile(null);
    setResult(null);
  };

  return (
    <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
      <h3>{t('stt.processor_title')}</h3>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
        {t('stt.processor_desc')}
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '600px' }}>
        {/* File Upload */}
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
            {t('stt.upload_label')}
          </label>
          <input
            type="file"
            accept="audio/*"
            onChange={handleFileChange}
            style={{ ...inputStyle, cursor: 'pointer' }}
            disabled={loading}
          />
          {audioFile && (
            <div style={{ marginTop: '0.5rem', padding: '0.5rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
              <strong>{audioFile.name}</strong> ({(audioFile.size / 1024).toFixed(1)} KB)
            </div>
          )}
        </div>

        {/* Options */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <label style={labelStyle}>
            {t('stt.language_label')}
            <select
              value={language}
              onChange={e => setLanguage(e.target.value)}
              style={inputStyle}
              disabled={loading}
            >
              <option value="en">{t('languages.en')}</option>
              <option value="es">{t('languages.es')}</option>
              <option value="fr">{t('languages.fr')}</option>
              <option value="de">{t('languages.de')}</option>
              <option value="zh">{t('languages.zh')}</option>
              <option value="ja">{t('languages.ja')}</option>
              <option value="ko">{t('languages.ko')}</option>
              <option value="auto">{t('languages.auto')}</option>
            </select>
          </label>

          <label style={labelStyle}>
            {t('stt.task_label')}
            <select
              value={task}
              onChange={e => setTask(e.target.value as 'transcribe' | 'translate')}
              style={inputStyle}
              disabled={loading}
            >
              <option value="transcribe">{t('stt.task_transcribe')}</option>
              <option value="translate">{t('stt.task_translate')}</option>
            </select>
          </label>
        </div>

        {/* Process Button */}
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={handleProcess}
            disabled={loading || !audioFile}
            style={{
              ...buttonStyle,
              opacity: loading || !audioFile ? 0.7 : 1,
              cursor: loading || !audioFile ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? t('stt.transcribing') : t('stt.transcribe_btn')}
          </button>
          {audioFile && (
            <button
              onClick={handleClear}
              disabled={loading}
              style={{
                ...buttonStyle,
                backgroundColor: 'var(--secondary-color)',
              }}
            >
              {t('common.30')}
            </button>
          )}
        </div>

        {/* Result */}
        {result && (
          <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <h4 style={{ margin: 0 }}>{t('stt.result_title')}</h4>
              <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                <span>{t('stt.language_label')}: {result.language} ({Math.round(result.language_probability * 100)}%)</span>
                <span>{t('stt.duration')}: {result.duration.toFixed(1)}s</span>
              </div>
            </div>
            {result.error ? (
              <div style={{ color: '#ef4444', fontSize: '0.9rem' }}>
                {t('common.15')}: {result.error}
              </div>
            ) : (
              <div style={{ 
                whiteSpace: 'pre-wrap', 
                fontFamily: 'monospace', 
                fontSize: '0.9rem',
                lineHeight: 1.6,
                maxHeight: '300px',
                overflowY: 'auto',
              }}>
                {result.text || t('stt.no_speech')}
              </div>
            )}
            {result.segments && result.segments.length > 0 && (
              <details style={{ marginTop: '1rem' }}>
                <summary style={{ cursor: 'pointer', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  {t('stt.show_segments', { count: String(result.segments.length) })}
                </summary>
                <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {result.segments.map((seg: any, i: number) => (
                    <div key={i} style={{ padding: '0.25rem 0', borderBottom: '1px solid var(--border-color)' }}>
                      <strong>[{seg.start.toFixed(1)}s - {seg.end.toFixed(1)}s]</strong> {seg.text}
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
