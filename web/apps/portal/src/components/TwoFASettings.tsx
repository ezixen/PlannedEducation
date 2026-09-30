import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../api';

export function TwoFASettings() {
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
      showInfo('Scan the QR code with your authenticator app, then enter the 6-digit code to verify.');
    } catch (err: any) {
      showError('Failed to initiate 2FA setup.', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!totpCode || totpCode.length !== 6) {
      showError('Please enter a valid 6-digit code.');
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
      showSuccess('2FA enabled successfully! Save your recovery codes.');
    } catch (err: any) {
      showError('Invalid TOTP code. Please try again.', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDisable = async () => {
    const code = totpCode || recoveryCode;
    if (!code) {
      showError('Please enter a TOTP code or recovery code.');
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
      showSuccess('2FA disabled successfully.');
    } catch (err: any) {
      showError('Invalid code. Please try again.', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerateRecoveryCodes = async () => {
    setLoading(true);
    try {
      const response = await apiClient.post('/auth/2fa/regenerate-recovery-codes');
      setRecoveryCodes(response.data.recovery_codes);
      setShowRecoveryCodes(true);
      showSuccess('New recovery codes generated. Old codes are now invalid.');
    } catch (err: any) {
      showError('Failed to regenerate recovery codes.', err.response?.data?.detail || err.message);
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

  if (!totpEnabled) {
    return (
      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
        <h3>Two-Factor Authentication (TOTP)</h3>
        <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
          Add an extra layer of security to your account using an authenticator app
          (Google Authenticator, Authy, Microsoft Authenticator, etc.).
        </p>
        <button
          onClick={handleSetup}
          disabled={loading}
          style={{ ...buttonStyle, opacity: loading ? 0.7 : 1 }}
        >
          {loading ? 'Setting up…' : 'Enable 2FA'}
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
      <h3>Two-Factor Authentication (TOTP)</h3>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
        2FA is <strong>enabled</strong>. You can manage your settings below.
      </p>

      {/* Setup flow */}
      {showSetup && setupStep === 'verify' && (
        <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
          <h4>Step 1: Scan QR Code</h4>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
            Open your authenticator app and scan this QR code:
          </p>
          <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(setupQrCodeUri)}`}
              alt="2FA QR Code"
              style={{ maxWidth: '100%', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }}
            />
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1rem' }}>
            Or enter this secret manually: <code style={{ wordBreak: 'break-all' }}>{setupSecret}</code>
          </p>

          <h4>Step 2: Verify Code</h4>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
            Enter the 6-digit code from your authenticator app:
          </p>
          <input
            type="text"
            value={totpCode}
            onChange={e => setTotpCode(e.target.value)}
            maxLength={6}
            placeholder="123456"
            style={{ ...inputStyle, textAlign: 'center', letterSpacing: '0.5rem', fontSize: '1.25rem', maxWidth: '200px' }}
            autoComplete="one-time-code"
          />
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
            <button onClick={handleConfirm} disabled={loading} style={buttonStyle}>
              {loading ? 'Verifying…' : 'Verify & Enable'}
            </button>
            <button onClick={() => setShowSetup(false)} style={secondaryButtonStyle}>
              Cancel
            </button>
          </div>

          <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)', margin: '1rem 0' }} />
          <h4>Step 3: Save Recovery Codes</h4>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
            <strong>IMPORTANT:</strong> Save these recovery codes in a safe place. They are the ONLY way to recover access if you lose your 2FA device.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: '0.5rem', marginBottom: '1rem' }}>
            {setupRecoveryCodes.map((code, i) => (
              <code key={i} style={{ backgroundColor: 'var(--bg-color)', padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', fontSize: '0.85rem' }}>
                {code}
              </code>
            ))}
          </div>
          <button onClick={() => setSetupStep('complete')} style={buttonStyle}>
            I've Saved My Recovery Codes
          </button>
        </div>
      )}

      {/* 2FA Enabled - Management options */}
      {!showSetup && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label>
              TOTP Code (from authenticator app)
              <input
                type="text"
                value={totpCode}
                onChange={e => setTotpCode(e.target.value)}
                maxLength={6}
                placeholder="123456"
                style={{ ...inputStyle, textAlign: 'center', letterSpacing: '0.5rem', fontSize: '1.25rem', maxWidth: '200px' }}
                autoComplete="one-time-code"
              />
            </label>
            <label>
              Recovery Code (if you lost your device)
              <input
                type="text"
                value={recoveryCode}
                onChange={e => setRecoveryCode(e.target.value.toUpperCase())}
                placeholder="ABCD-EFGH"
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
              {loading ? 'Disabling…' : 'Disable 2FA'}
            </button>
            <button
              onClick={handleRegenerateRecoveryCodes}
              disabled={loading}
              style={secondaryButtonStyle}
            >
              {loading ? 'Generating…' : 'Regenerate Recovery Codes'}
            </button>
          </div>

          {showRecoveryCodes && recoveryCodes.length > 0 && (
            <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
              <h4>New Recovery Codes</h4>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                <strong>IMPORTANT:</strong> Save these recovery codes in a safe place. Old codes are now invalid.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: '0.5rem', marginBottom: '1rem' }}>
                {recoveryCodes.map((code, i) => (
                  <code key={i} style={{ backgroundColor: 'var(--sidebar-bg)', padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', fontSize: '0.85rem' }}>
                    {code}
                  </code>
                ))}
              </div>
              <button onClick={() => setShowRecoveryCodes(false)} style={secondaryButtonStyle}>
                Done
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}