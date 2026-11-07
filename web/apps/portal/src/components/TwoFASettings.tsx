import { useState, useEffect } from 'react';
import QRCode from 'qrcode';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { useI18n } from '../contexts/I18nContext';
import { apiClient } from '../api';

const recoveryGridStyle: React.CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '0.5rem',
  marginBottom: '1rem',
  maxWidth: '100%',
};

const recoveryCodeStyle: React.CSSProperties = {
  backgroundColor: 'var(--bg-color)',
  padding: '0.5rem 0.65rem',
  borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--border-color)',
  fontSize: '0.85rem',
  wordBreak: 'break-all',
  maxWidth: '100%',
  flex: '1 1 7rem',
  boxSizing: 'border-box',
  textAlign: 'center',
};

export function TwoFASettings() {
  const { t } = useI18n();
  const { user, refreshUser } = useAuth();
  const { success: showSuccess, error: showError, info: showInfo } = useToast();

  const [totpEnabled, setTotpEnabled] = useState(false);
  const [setupSecret, setSetupSecret] = useState<string>('');
  const [setupQrCodeUri, setSetupQrCodeUri] = useState<string>('');
  const [qrDataUrl, setQrDataUrl] = useState<string>('');
  const [setupRecoveryCodes, setSetupRecoveryCodes] = useState<string[]>([]);
  const [showSetup, setShowSetup] = useState(false);
  const [totpCode, setTotpCode] = useState('');
  const [recoveryCode, setRecoveryCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [setupStep, setSetupStep] = useState<'idle' | 'verify' | 'complete'>('idle');

  useEffect(() => {
    if (user) {
      setTotpEnabled(user.totp_enabled || false);
    }
  }, [user]);

  // Encode otpauth:// URI into a real QR (Google Authenticator compatible)
  useEffect(() => {
    if (!setupQrCodeUri) {
      setQrDataUrl('');
      return;
    }
    let cancelled = false;
    QRCode.toDataURL(setupQrCodeUri, {
      width: 200,
      margin: 2,
      errorCorrectionLevel: 'M',
      color: { dark: '#111827', light: '#ffffff' },
    })
      .then((url) => {
        if (!cancelled) setQrDataUrl(url);
      })
      .catch(() => {
        if (!cancelled) setQrDataUrl('');
      });
    return () => {
      cancelled = true;
    };
  }, [setupQrCodeUri]);

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
    <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', maxWidth: '100%', overflow: 'hidden' }}>
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

      {showSetup && setupStep === 'verify' && (
        <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', maxWidth: '100%', boxSizing: 'border-box' }}>
          <h4>{t('twofa.2')}</h4>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
            {t('twofa.scan_qr_desc')}
          </p>
          <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
            {qrDataUrl ? (
              <img
                src={qrDataUrl}
                alt={t('twofa.qr_alt')}
                width={200}
                height={200}
                style={{ maxWidth: '100%', height: 'auto', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', background: '#fff' }}
              />
            ) : (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{t('twofa.qr_ready')}</p>
            )}
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
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', flexWrap: 'wrap' }}>
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
          <div style={recoveryGridStyle}>
            {setupRecoveryCodes.map((code, i) => (
              <code key={i} style={recoveryCodeStyle}>
                {code}
              </code>
            ))}
          </div>
          <button onClick={() => setSetupStep('complete')} style={buttonStyle}>
            {t('twofa.8')}
          </button>
        </div>
      )}

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
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: 0 }}>
            {t('twofa.codes_one_time_hint')}
          </p>
        </div>
      )}
    </div>
  );
}
