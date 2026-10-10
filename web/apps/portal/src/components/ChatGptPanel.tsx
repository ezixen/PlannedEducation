/**
 * Embedded ChatGPT Panel for Teachers (ported from EasyLegalAid).
 * Supports OpenAI Device-Code Sign-In ("Sign in with ChatGPT"), live Codex model selection,
 * reasoning effort / verbosity controls, and direct teacher chat without requiring an API key.
 */
import { type FormEvent, useEffect, useRef, useState } from 'react';
import {
  useChatGptSession,
  type ChatGptModelOption,
} from '../contexts/ChatGptSessionContext';

export interface ChatGptPanelProps {
  compact?: boolean;
  defaultInstructions?: string;
  quickActionLabel?: string;
  onBuildQuickPrompt?: () => string;
}

export function ChatGptPanel({
  compact = false,
  defaultInstructions,
  quickActionLabel,
  onBuildQuickPrompt,
}: ChatGptPanelProps) {
  const {
    connected,
    accountId,
    history,
    loading,
    error,
    setError,
    options,
    prefs,
    updatePrefs,
    selectedModel,
    reasoningChoices,
    verbosityChoices,
    loginId,
    userCode,
    verificationUri,
    showDeviceLogin,
    codeCopied,
    loadOptions,
    startDeviceLogin,
    openDevicePage,
    copyUserCode,
    onClearHistory,
    onLogout,
    sendMessage,
  } = useChatGptSession();

  const [input, setInput] = useState('');
  const deviceCodeRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!userCode) return;
    window.setTimeout(() => {
      deviceCodeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 50);
  }, [userCode]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const message = input.trim();
    if (!message) return;
    const previousInput = input;
    setInput('');
    const ok = await sendMessage(message, defaultInstructions);
    if (!ok) {
      setInput(previousInput);
    }
  }

  function handleQuickPrompt() {
    if (!onBuildQuickPrompt) return;
    const built = onBuildQuickPrompt();
    if (built) {
      setInput((prev) => (prev.trim() ? `${prev.trim()}\n\n${built}` : built));
    }
  }

  const selectStyle: React.CSSProperties = {
    width: '100%',
    padding: '0.5rem 0.65rem',
    marginTop: '0.25rem',
    borderRadius: '6px',
    border: '1px solid var(--border-color)',
    backgroundColor: 'var(--bg-color)',
    color: 'var(--text-color)',
    fontSize: '0.9rem',
  };

  const buttonPrimary: React.CSSProperties = {
    padding: '0.55rem 1.1rem',
    backgroundColor: 'var(--primary-color, #2563eb)',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '0.9rem',
  };

  const buttonSecondary: React.CSSProperties = {
    padding: '0.45rem 0.9rem',
    backgroundColor: 'transparent',
    color: 'var(--text-color)',
    border: '1px solid var(--border-color)',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '0.85rem',
  };

  return (
    <div
      className="chatgpt-panel"
      data-testid="chatgpt-panel"
      style={{
        padding: compact ? '1.25rem' : '1.5rem',
        backgroundColor: 'var(--sidebar-bg)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        marginBottom: '1.5rem',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
          marginBottom: '0.75rem',
        }}
      >
        <div>
          <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>ChatGPT Teacher Assistant</span>
            <span
              style={{
                fontSize: '0.75rem',
                padding: '0.15rem 0.55rem',
                borderRadius: '999px',
                backgroundColor: connected ? 'rgba(16, 185, 129, 0.15)' : 'rgba(148, 163, 184, 0.2)',
                color: connected ? '#10b981' : 'var(--text-muted, #64748b)',
                fontWeight: 600,
              }}
            >
              {connected ? 'Connected' : 'Not Connected'}
            </span>
          </h3>
          {!compact && (
            <p style={{ margin: '0.35rem 0 0 0', fontSize: '0.9rem', color: 'var(--text-muted, gray)' }}>
              Sign in directly with your existing ChatGPT account (via OpenAI Device Code) to grade anonymized
              submissions, draft questions, and chat inside PlannedEducation — no API key required.
            </p>
          )}
        </div>
        {connected && (
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={() => void onClearHistory()}
              disabled={loading || history.length === 0}
              style={buttonSecondary}
            >
              New Session / Clear
            </button>
            <button
              type="button"
              onClick={() => void onLogout()}
              disabled={loading}
              style={{ ...buttonSecondary, color: '#ef4444', borderColor: '#ef4444' }}
            >
              Disconnect ChatGPT
            </button>
          </div>
        )}
      </div>

      {error && (
        <div
          role="alert"
          style={{
            padding: '0.75rem 1rem',
            marginBottom: '1rem',
            borderRadius: '6px',
            backgroundColor: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid #ef4444',
            color: '#ef4444',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <span>{error}</span>
          <button
            type="button"
            onClick={() => setError(null)}
            style={{
              background: 'none',
              border: 'none',
              color: '#ef4444',
              cursor: 'pointer',
              fontWeight: 700,
            }}
          >
            Dismiss
          </button>
        </div>
      )}

      {!connected ? (
        <div>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-muted, gray)', margin: '0 0 0.75rem 0' }}>
            In your ChatGPT Security Settings, make sure{' '}
            <strong>&ldquo;Enable device code authentication for Codex&rdquo;</strong> is turned on, then click{' '}
            <strong>Sign in with ChatGPT</strong> below.
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={() => void startDeviceLogin()}
              disabled={loading || Boolean(userCode)}
              style={{
                ...buttonPrimary,
                opacity: loading || Boolean(userCode) ? 0.7 : 1,
              }}
            >
              {userCode ? 'Sign-in in progress…' : 'Sign in with ChatGPT'}
            </button>
          </div>

          {userCode ? (
            <div
              ref={deviceCodeRef}
              role="status"
              aria-live="polite"
              data-testid="chatgpt-device-code-card"
              style={{
                marginTop: '1rem',
                padding: '1.25rem',
                borderRadius: '8px',
                border: '2px solid #10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.08)',
              }}
            >
              <p style={{ margin: '0 0 0.35rem 0', fontWeight: 700 }}>Your ChatGPT Device Code</p>
              <p style={{ margin: '0 0 0.75rem 0', fontSize: '0.9rem', color: 'var(--text-muted, gray)' }}>
                Copy this code, open the ChatGPT device page, paste it there, and return here.
              </p>
              <p
                data-testid="chatgpt-user-code"
                style={{
                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
                  fontSize: '1.85rem',
                  letterSpacing: '0.18em',
                  margin: '0.75rem 0',
                  userSelect: 'all',
                  fontWeight: 700,
                }}
              >
                {userCode}
              </p>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <button type="button" onClick={() => void copyUserCode()} style={buttonPrimary}>
                  {codeCopied ? 'Copied!' : 'Copy Code'}
                </button>
                <button
                  type="button"
                  onClick={() => openDevicePage()}
                  disabled={!verificationUri}
                  style={buttonSecondary}
                >
                  Open ChatGPT Device Page
                </button>
              </div>
              {loginId && (
                <p style={{ margin: '0.75rem 0 0 0', fontSize: '0.85rem', color: 'var(--text-muted, gray)' }}>
                  Waiting for ChatGPT sign-in… Keep this page open after pasting your code.
                </p>
              )}
            </div>
          ) : showDeviceLogin && loading ? (
            <p style={{ marginTop: '0.75rem', fontSize: '0.9rem', color: 'var(--text-muted, gray)' }}>
              Requesting device code from OpenAI…
            </p>
          ) : null}
        </div>
      ) : (
        <div>
          {/* Settings row: Model, Thinking Effort, Answer Length */}
          <div
            style={{
              display: 'grid',
              gap: '0.75rem',
              gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
              marginBottom: '0.75rem',
              padding: '0.85rem',
              borderRadius: '6px',
              backgroundColor: 'var(--bg-color)',
              border: '1px solid var(--border-color)',
            }}
          >
            <label style={{ fontSize: '0.85rem', fontWeight: 600 }}>
              Model
              <select
                aria-label="Model"
                value={prefs.model || options?.default_model || ''}
                disabled={loading || !options?.models.length}
                onChange={(e) => {
                  const modelId = e.target.value;
                  const model = options?.models.find((m) => m.id === modelId);
                  updatePrefs({
                    model: modelId,
                    reasoningEffort: model?.default_reasoning_effort || prefs.reasoningEffort,
                  });
                }}
                style={selectStyle}
              >
                {(options?.models ?? []).map((model: ChatGptModelOption) => (
                  <option key={model.id} value={model.id}>
                    {model.label}
                    {!compact && model.context_window
                      ? ` (${Math.round(model.context_window / 1000)}k ctx)`
                      : ''}
                  </option>
                ))}
              </select>
            </label>

            <label style={{ fontSize: '0.85rem', fontWeight: 600 }}>
              Thinking Effort
              <select
                aria-label="Thinking Effort"
                value={prefs.reasoningEffort}
                disabled={loading}
                onChange={(e) => updatePrefs({ reasoningEffort: e.target.value })}
                style={selectStyle}
              >
                {reasoningChoices.map((effort) => (
                  <option key={effort} value={effort}>
                    {effort}
                  </option>
                ))}
              </select>
            </label>

            <label style={{ fontSize: '0.85rem', fontWeight: 600 }}>
              Answer Length
              <select
                aria-label="Answer Length"
                value={prefs.verbosity}
                disabled={loading}
                onChange={(e) => updatePrefs({ verbosity: e.target.value })}
                style={selectStyle}
              >
                {verbosityChoices.map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '0.5rem',
              marginBottom: '0.75rem',
              fontSize: '0.8rem',
              color: 'var(--text-muted, gray)',
            }}
          >
            <span>
              {accountId ? `Account: ${accountId.slice(0, 12)}… • ` : ''}
              {selectedModel?.context_window
                ? `Context window: ${Math.round(selectedModel.context_window / 1000)}k tokens`
                : 'Ready to chat'}
            </span>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              {quickActionLabel && onBuildQuickPrompt && (
                <button type="button" onClick={handleQuickPrompt} style={buttonSecondary}>
                  {quickActionLabel}
                </button>
              )}
              <button
                type="button"
                onClick={() => void loadOptions(true)}
                disabled={loading}
                style={buttonSecondary}
              >
                Refresh Models
              </button>
            </div>
          </div>

          {/* Chat log */}
          <div
            data-testid="chatgpt-history-log"
            style={{
              maxHeight: compact ? '240px' : '360px',
              overflowY: 'auto',
              padding: '0.85rem',
              borderRadius: '6px',
              backgroundColor: 'var(--bg-color)',
              border: '1px solid var(--border-color)',
              marginBottom: '0.75rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.65rem',
            }}
          >
            {history.length === 0 ? (
              <p style={{ margin: 0, color: 'var(--text-muted, gray)', fontSize: '0.9rem' }}>
                Ask ChatGPT anything you type here — grade anonymized answers, summarize class mistakes, or draft
                new exam questions. Only what you send here is shared with ChatGPT.
              </p>
            ) : (
              history.map((line, index) => (
                <div
                  key={`${line.role}-${index}`}
                  style={{
                    padding: '0.6rem 0.8rem',
                    borderRadius: '6px',
                    backgroundColor:
                      line.role === 'assistant'
                        ? 'rgba(59, 130, 246, 0.08)'
                        : 'rgba(16, 185, 129, 0.08)',
                    border: '1px solid var(--border-color)',
                    whiteSpace: 'pre-wrap',
                    fontSize: '0.9rem',
                  }}
                >
                  <strong style={{ color: line.role === 'assistant' ? '#3b82f6' : '#10b981' }}>
                    {line.role === 'assistant' ? 'ChatGPT' : 'You'}:{' '}
                  </strong>
                  <span>{line.content}</span>
                </div>
              ))
            )}
          </div>

          {/* Input form */}
          <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask ChatGPT to grade anonymized responses, explain rubrics, or draft exam questions…"
              rows={compact ? 2 : 3}
              required
              disabled={loading}
              style={{
                flex: 1,
                minWidth: '220px',
                padding: '0.65rem',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-color)',
                color: 'var(--text-color)',
                fontFamily: 'inherit',
                fontSize: '0.9rem',
                resize: 'vertical',
              }}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              style={{
                ...buttonPrimary,
                alignSelf: 'flex-end',
                opacity: loading || !input.trim() ? 0.65 : 1,
              }}
            >
              {loading ? 'Sending…' : 'Send to ChatGPT'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

