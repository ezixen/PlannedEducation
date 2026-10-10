import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../api';
import { ChatGptPanel } from './ChatGptPanel';

export function AIKeySettings() {
  const { user } = useAuth();
  const { success: showSuccess, error: showError } = useToast();

  const [provider, setProvider] = useState<string>('');
  const [modelName, setModelName] = useState<string>('');
  const [baseUrl, setBaseUrl] = useState<string>('');
  const [apiKey, setApiKey] = useState('');
  const [hasKey, setHasKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showKey, setShowKey] = useState(false);

  useEffect(() => {
    if (user) {
      setProvider(user.ai_provider || 'gemini');
      setModelName(user.ai_model_name || 'gemini-2.5-flash');
      setBaseUrl(user.ai_base_url || '');
      setHasKey(!!user.ai_api_key_encrypted);
    }
  }, [user]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await apiClient.put('/auth/ai-key', {
        ai_provider: provider,
        ai_model_name: modelName,
        ai_base_url: baseUrl,
        ai_api_key: apiKey || undefined,
      });
      showSuccess('AI settings saved successfully!');
    } catch (err: any) {
      showError('Failed to save AI settings.', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteKey = async () => {
    if (!confirm('Are you sure you want to remove your AI API key?')) return;
    setLoading(true);
    try {
      await apiClient.put('/auth/ai-key', { ai_api_key: '' });
      setApiKey('');
      setHasKey(false);
      showSuccess('AI API key removed.');
    } catch (err: any) {
      showError('Failed to remove AI key.', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
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

  return (
    <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
      <h3>AI Provider Settings</h3>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
        Configure your AI provider for automated grading, or sign in with your ChatGPT account directly below.
      </p>

      {user?.role === 'teacher' && (
        <div style={{ marginBottom: '1.5rem' }}>
          <ChatGptPanel compact />
        </div>
      )}

      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '420px' }}>
        <label>
          AI Provider
          <select
            value={provider}
            onChange={e => setProvider(e.target.value)}
            style={inputStyle}
          >
            <option value="chatgpt">ChatGPT Account (Device Sign-In — No API Key)</option>
            <option value="gemini">Google Gemini</option>
            <option value="openrouter">OpenRouter</option>
            <option value="ollama">Ollama (Local)</option>
            <option value="openai">OpenAI (API Key)</option>
          </select>
        </label>

        <label>
          Model Name
          <input
            type="text"
            value={modelName}
            onChange={e => setModelName(e.target.value)}
            placeholder="e.g., gemini-2.5-flash"
            style={inputStyle}
          />
        </label>

        <label>
          Base URL (optional)
          <input
            type="text"
            value={baseUrl}
            onChange={e => setBaseUrl(e.target.value)}
            placeholder="e.g., http://localhost:11434/v1 for Ollama"
            style={inputStyle}
          />
        </label>

        <label>
          API Key {hasKey ? '(set)' : '(not set)'}
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
            <input
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder={hasKey ? '••••••••' : 'Enter API key'}
              style={{ ...inputStyle, flex: 1 }}
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              style={{ padding: '0.625rem 1rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer' }}
            >
              {showKey ? 'Hide' : 'Show'}
            </button>
          </div>
          <small style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
            Your API key is encrypted at rest using Fernet encryption.
          </small>
        </label>

        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
          <button
            type="submit"
            disabled={loading}
            style={{
              padding: '0.625rem 1.5rem',
              backgroundColor: loading ? '#94a3b8' : 'var(--primary-color)',
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontWeight: 600,
            }}
          >
            {loading ? 'Saving…' : 'Save AI Settings'}
          </button>

          {hasKey && (
            <button
              type="button"
              onClick={handleDeleteKey}
              disabled={loading}
              style={{
                padding: '0.625rem 1.5rem',
                backgroundColor: '#ef4444',
                color: '#fff',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontWeight: 600,
              }}
            >
              Remove Key
            </button>
          )}
        </div>
      </form>
    </div>
  );
}