import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { useI18n } from '../contexts/I18nContext';
import { apiClient } from '../api';

export function TwoFASettings() {
  const { t } = useI18n();
  const { user, refreshUser } = useAuth();
  const { success: showSuccess, error: showError, info: showInfo } = useToast();

  const [totpEnabled, setTotpEnabled] = useState(false);
  const [setupSecret, setSetupSecret] = useState<string>('');
  const [setupQrCodeUri, setSetupQrCodeUri] = useState<string>('');
  const [setupRecoveryCodes, setSetupRecoveryCodes] = useState<string[]>([]);
  const [showSetup, setShowSetup] = useState(false);
  const [showRecoveryCodes, setShowRecoveryCodes] = useState(false);
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [totpCode, setTotpCode] = useState('');
  const [recoveryCode, setRecoveryCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [setupStep, setSetupStep] = useState<'idle' | 'verify' | 'complete'>('idle');

  useEffect(() => {
    if (user) {
      setTotpEnabled(user.totp_enabled || false);
    }
  }, [user]);

  const handleSetup = async () => {
    setLoading(true);
    try {
      const response = await apiClient.post('/auth/2fa/setup');
      setSetupSecret(response.data.secret);
      setSetupQrCodeUri(response.data.qr_code_uri);
      setSetupRecoveryCodes(response.data.recovery_codes);
      setShowSetup(true);
      setSetupStep('verify');
      showInfo(t('twofa.setup_info'));
    } catch (err: any) {
      showError(t('twofa.setup_failed'), err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!totpCode || totpCode.length !== 6) {
      showError(t('twofa.invalid_code_length'));
      return;
    }
    setLoading(true);
    try {
      await apiClient.post('/auth/2fa/confirm', { code: totpCode });
      setTotpEnabled(true);
      setShowSetup(false);
      setTotpCode('');
      setSetupStep('idle');
      await refreshUser?.();
      showSuccess(t('twofa.enabled_success'));
    } catch (err: any) {
      showError(t('twofa.invalid_totp'), err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDisable = async () => {
    const code = totpCode || recoveryCode;
    if (!code) {
      showError(t('twofa.code_required'));
      return;
    }
    setLoading(true);
    try {
      await apiClient.post('/auth/2fa/disable', {
        totp_code: totpCode || undefined,
        recovery_code: recoveryCode || undefined,
      });
      setTotpEnabled(false);
      setTotpCode('');
      setRecoveryCode('');
      await refreshUser?.();
      showSuccess(t('twofa.disabled_success'));
    } catch (err: any) {
      showError(t('twofa.invalid_code'), err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerateRecoveryCodes = async () => {
    setLoading(true);
    try {
      const response = await apiClient.post('/auth/2fa/regenerate-recovery-codes', {
        totp_code: totpCode || undefined,
        recovery_code: recoveryCode || undefined,
      });
      setRecoveryCodes(response.data.recovery_codes);
      setShowRecoveryCodes(true);
      showSuccess(t('twofa.recovery_regenerated'));
    } catch (err: any) {
      showError(t('twofa.recovery_regen_failed'), err.response?.data?.detail || err.message);
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

  const buttonStyle: React.CSSProperties = {
    padding: '0.5rem 1.5rem',
    backgroundColor: 'var(--primary-color)',
    color: '#fff',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    fontWeight: 600,
  };

  const secondaryButtonStyle: React.CSSProperties = {
    ...buttonStyle,
    backgroundColor: 'var(--secondary-color)',
  };

  const dangerButtonStyle: React.CSSProperties = {
    ...buttonStyle,
    backgroundColor: '#ef4444',
  };

  if (!totpEnabled && !showSetup) {
    return (
      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
        <h3>{t('twofa.1')}</h3>
        <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
          {t('twofa.intro')}
        </p>
        <button
          onClick={handleSetup}
          disabled={loading}
          style={{ ...buttonStyle, opacity: loading ? 0.7 : 1 }}
        >
          {loading ? t('twofa.setting_up') : t('twofa.1')}
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
      <h3>{t('twofa.1')}</h3>
      {totpEnabled ? (
        <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
          {t('twofa.enabled_manage', { status: t('common.42') })}
        </p>
      ) : (
        <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
          {t('twofa.follow_steps')}
        </p>
      )}

      {/* Setup flow */}
      {showSetup && setupStep === 'verify' && (
        <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
          <h4>{t('twofa.2')}</h4>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
            {t('twofa.scan_qr_desc')}
          </p>
          <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
            <img
              src={`data:image/svg+xml;utf8,${encodeURIComponent(
                `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200"><rect width="200" height="200" fill="#ffffff"/><rect x="16" y="16" width="48" height="48" fill="none" stroke="#111827" stroke-width="8"/><rect x="32" y="32" width="16" height="16" fill="#111827"/><rect x="136" y="16" width="48" height="48" fill="none" stroke="#111827" stroke-width="8"/><rect x="152" y="32" width="16" height="16" fill="#111827"/><rect x="16" y="136" width="48" height="48" fill="none" stroke="#111827" stroke-width="8"/><rect x="32" y="152" width="16" height="16" fill="#111827"/><rect x="80" y="80" width="40" height="40" fill="#111827"/><text x="100" y="192" font-family="monospace" font-size="10" text-anchor="middle" fill="#374151">${t('twofa.qr_ready')}</text></svg>`
              )}`}
              alt={t('twofa.qr_alt')}
              data-uri={setupQrCodeUri ? 'configured' : 'empty'}
              style={{ maxWidth: '100%', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }}
            />
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1rem' }}>
            {t('twofa.manual_secret_desc')} <code style={{ wordBreak: 'break-all' }}>{setupSecret}</code>
          </p>

          <h4>{t('twofa.step2_title')}</h4>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
            {t('twofa.3')}
          </p>
          <input
            type="text"
            value={totpCode}
            onChange={e => setTotpCode(e.target.value)}
            maxLength={6}
            placeholder={t('twofa.totp_placeholder')}
            style={{ ...inputStyle, textAlign: 'center', letterSpacing: '0.5rem', fontSize: '1.25rem', maxWidth: '200px' }}
            autoComplete="one-time-code"
          />
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
            <button onClick={handleConfirm} disabled={loading} style={buttonStyle}>
              {loading ? t('twofa.verifying') : t('twofa.4')}
            </button>
            <button onClick={() => setShowSetup(false)} style={secondaryButtonStyle}>
              {t('common.2')}
            </button>
          </div>

          <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)', margin: '1rem 0' }} />
          <h4>{t('twofa.6')}</h4>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
            <strong>{t('twofa.important_notice')}</strong> {t('twofa.recovery_only_way')}
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: '0.5rem', marginBottom: '1rem' }}>
            {setupRecoveryCodes.map((code, i) => (
              <code key={i} style={{ backgroundColor: 'var(--bg-color)', padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', fontSize: '0.85rem' }}>
                {code}
              </code>
            ))}
          </div>
          <button onClick={() => setSetupStep('complete')} style={buttonStyle}>
            {t('twofa.8')}
          </button>
        </div>
      )}

      {/* 2FA Enabled - Management options */}
      {totpEnabled && !showSetup && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label>
              {t('twofa.totp_label')}
              <input
                type="text"
                value={totpCode}
                onChange={e => setTotpCode(e.target.value)}
                maxLength={6}
                placeholder={t('twofa.totp_placeholder')}
                style={{ ...inputStyle, textAlign: 'center', letterSpacing: '0.5rem', fontSize: '1.25rem', maxWidth: '200px' }}
                autoComplete="one-time-code"
              />
            </label>
            <label>
              {t('twofa.recovery_label')}
              <input
                type="text"
                value={recoveryCode}
                onChange={e => setRecoveryCode(e.target.value.toUpperCase())}
                placeholder={t('twofa.code_placeholder')}
                style={{ ...inputStyle, textTransform: 'uppercase', maxWidth: '200px' }}
              />
            </label>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button
              onClick={handleDisable}
              disabled={loading}
              style={dangerButtonStyle}
            >
              {loading ? t('twofa.disabling') : t('twofa.9')}
            </button>
            <button
              onClick={handleRegenerateRecoveryCodes}
              disabled={loading}
              style={secondaryButtonStyle}
            >
              {loading ? t('twofa.generating') : t('twofa.regenerate_btn')}
            </button>
          </div>

          {showRecoveryCodes && recoveryCodes.length > 0 && (
            <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
              <h4>{t('twofa.new_codes_title')}</h4>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                <strong>{t('twofa.important_notice')}</strong> {t('twofa.old_codes_invalid')}
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: '0.5rem', marginBottom: '1rem' }}>
                {recoveryCodes.map((code, i) => (
                  <code key={i} style={{ backgroundColor: 'var(--sidebar-bg)', padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', fontSize: '0.85rem' }}>
                    {code}
                  </code>
                ))}
              </div>
              <button onClick={() => setShowRecoveryCodes(false)} style={secondaryButtonStyle}>
                {t('admin.done')}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
