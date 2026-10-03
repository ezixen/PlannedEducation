import { useState } from 'react';
import { apiClient } from '../api';
import { useToast } from '../contexts/ToastContext';

export function STTProcessor() {
  const { success: showSuccess, error: showError } = useToast();
  
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
      showError('Please select an audio file first.');
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
      showSuccess(`Transcription completed (${response.data.language}, ${response.data.duration.toFixed(1)}s)`);
    } catch (err: any) {
      showError('Transcription failed.', err.response?.data?.detail || err.message);
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

  return (
    <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
      <h3>Speech-to-Text Processor</h3>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
        Transcribe audio recordings using faster-whisper (local inference).
        Supports multiple languages and translation to English.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '600px' }}>
        {/* File Upload */}
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
            Upload Audio File
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
            Language
            <select
              value={language}
              onChange={e => setLanguage(e.target.value)}
              style={inputStyle}
              disabled={loading}
            >
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="zh">Chinese</option>
              <option value="ja">Japanese</option>
              <option value="ko">Korean</option>
              <option value="auto">Auto-detect</option>
            </select>
          </label>

          <label style={labelStyle}>
            Task
            <select
              value={task}
              onChange={e => setTask(e.target.value as 'transcribe' | 'translate')}
              style={inputStyle}
              disabled={loading}
            >
              <option value="transcribe">Transcribe (same language)</option>
              <option value="translate">Translate to English</option>
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
            {loading ? 'Transcribing…' : 'Transcribe Audio'}
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
              Clear
            </button>
          )}
        </div>

        {/* Result */}
        {result && (
          <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <h4 style={{ margin: 0 }}>Result</h4>
              <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                <span>Language: {result.language} ({Math.round(result.language_probability * 100)}%)</span>
                <span>Duration: {result.duration.toFixed(1)}s</span>
              </div>
            </div>
            {result.error ? (
              <div style={{ color: '#ef4444', fontSize: '0.9rem' }}>
                Error: {result.error}
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
                {result.text || '(no speech detected)'}
              </div>
            )}
            {result.segments && result.segments.length > 0 && (
              <details style={{ marginTop: '1rem' }}>
                <summary style={{ cursor: 'pointer', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  Show segments ({result.segments.length})
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