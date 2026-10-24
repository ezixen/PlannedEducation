import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiClient } from '../api';
import { useI18n } from '../contexts/I18nContext';

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.5rem',
  borderRadius: '4px',
  border: '1px solid var(--border-color)',
  marginTop: '0.25rem',
  backgroundColor: 'var(--bg-color)',
  color: 'var(--text-color)',
};

function PasswordStrength({ password }: { password: string }) {
  const { t } = useI18n();
  const checks = [
    { label: t('register.9.1'), ok: password.length >= 8 },
    { label: t('register.9.2'), ok: /[A-Z]/.test(password) },
    { label: t('register.9.3'), ok: /[a-z]/.test(password) },
    { label: t('register.9.4'), ok: /\d/.test(password) },
    { label: t('register.9.5'), ok: /[!@#$%^&*(),.?":{}|<>]/.test(password) },
  ];
  if (!password) return null;
  return (
    <ul style={{ textAlign: 'left', fontSize: '0.8rem', margin: '0.25rem 0 0', padding: '0 0 0 1.2rem' }}>
      {checks.map(c => (
        <li key={c.label} style={{ color: c.ok ? '#10b981' : '#ef4444' }}>
          {c.ok ? '✓' : '✗'} {c.label}
        </li>
      ))}
    </ul>
  );
}

export function Register() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState<'student' | 'teacher' | 'parent'>('student');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedCodes, setCopiedCodes] = useState(false);
  const [registeredData, setRegisteredData] = useState<{
    recovery_codes: string[];
    message: string;
    role: string;
  } | null>(null);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError(t('errors.7.4'));
      return;
    }

    setLoading(true);
    try {
      const res = await apiClient.post('/auth/register', {
        full_name: fullName,
        username,
        email,
        password,
        role,
      });

      if (res.data?.recovery_codes && res.data.recovery_codes.length > 0) {
        setRegisteredData({
          recovery_codes: res.data.recovery_codes,
          message: res.data.message || '',
          role,
        });
      } else {
        navigate('/login');
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ')
          : (err.message || t('errors.9'));
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyCodes = () => {
    if (!registeredData) return;
    const text = registeredData.recovery_codes.join('\n');
    navigator.clipboard.writeText(text);
    setCopiedCodes(true);
    setTimeout(() => setCopiedCodes(false), 3000);
  };

  const handlePrintCodes = () => {
    window.print();
  };

  if (registeredData) {
    return (
      <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-color)', padding: '1rem' }}>
        <div style={{ padding: '2rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)', width: '100%', maxWidth: '480px', textAlign: 'center' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>🔐</div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-color)', marginBottom: '0.5rem' }}>
            Save Your Recovery Codes
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1.25rem' }}>
            {registeredData.message}
          </p>

          <div
            style={{
              padding: '0.85rem',
              backgroundColor: 'rgba(239, 68, 68, 0.08)',
              border: '1px solid #ef4444',
              borderRadius: '6px',
              color: '#b91c1c',
              fontSize: '0.85rem',
              marginBottom: '1.25rem',
              textAlign: 'left',
              lineHeight: 1.4,
            }}
          >
            <strong>⚠️ {t('register.critical_codes_title')}:</strong> {t('register.critical_codes_body')}
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
              gap: '0.5rem',
              padding: '1rem',
              backgroundColor: 'var(--bg-color)',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              marginBottom: '1.25rem',
            }}
          >
            {registeredData.recovery_codes.map((code, idx) => (
              <div
                key={idx}
                style={{
                  fontFamily: 'monospace',
                  fontSize: '1rem',
                  fontWeight: 600,
                  letterSpacing: '0.05em',
                  padding: '0.4rem',
                  backgroundColor: 'var(--sidebar-bg)',
                  border: '1px dashed var(--border-color)',
                  borderRadius: '4px',
                  color: 'var(--primary-color)',
                }}
              >
                {code}
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', justifyContent: 'center' }}>
            <button
              type="button"
              onClick={handleCopyCodes}
              style={{
                padding: '0.6rem 1rem',
                backgroundColor: 'var(--sidebar-bg)',
                color: 'var(--text-color)',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.85rem',
              }}
            >
              {copiedCodes ? t('register.copied') : t('register.copy_codes')}
            </button>
            <button
              type="button"
              onClick={handlePrintCodes}
              style={{
                padding: '0.6rem 1rem',
                backgroundColor: 'var(--sidebar-bg)',
                color: 'var(--text-color)',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.85rem',
              }}
            >
              {t('register.print_codes')}
            </button>
          </div>

          <button
            type="button"
            onClick={() => navigate('/login')}
            style={{
              width: '100%',
              padding: '0.75rem 1rem',
              backgroundColor: 'var(--primary-color, #2563eb)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.95rem',
            }}
          >
            {t('register.proceed_login')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-color)', padding: '1rem' }}>
      <div style={{ padding: '2rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)', width: '100%', maxWidth: '420px', textAlign: 'center' }}>
        <h1 style={{ marginBottom: '0.5rem', color: 'var(--text-color)' }}>{t('login.title')}</h1>
        <p style={{ marginBottom: '1.5rem', color: 'var(--text-muted)' }}>{t('register.subtitle')}</p>

        {error && (
          <div style={{ color: '#ef4444', marginBottom: '1rem', padding: '0.5rem', backgroundColor: '#fee2e2', borderRadius: 'var(--radius-sm)' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', textAlign: 'left' }}>
          <label style={{ color: 'var(--text-color)' }}>
            {t('register.account_role')}
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as any)}
              style={inputStyle}
            >
              <option value="student">{t('register.role_student')}</option>
              <option value="teacher">{t('register.role_teacher')}</option>
              <option value="parent">{t('register.role_parent')}</option>
            </select>
          </label>

          {role === 'teacher' && (
            <div
              style={{
                padding: '0.6rem 0.75rem',
                backgroundColor: 'rgba(59, 130, 246, 0.08)',
                border: '1px solid #3b82f6',
                borderRadius: '4px',
                fontSize: '0.8rem',
                color: 'var(--text-color)',
                lineHeight: 1.4,
              }}
            >
              ℹ️ <strong>{t('register.teacher_verification_title')}:</strong> {t('register.teacher_verification_body')}
            </div>
          )}

          <label style={{ color: 'var(--text-color)' }}>
            {t('register.full_name_label')}
            <input
              type="text"
              name="full_name"
              value={fullName}
              onChange={e => setFullName(e.target.value)}
              required
              maxLength={128}
              autoComplete="name"
              style={inputStyle}
            />
          </label>

          <label style={{ color: 'var(--text-color)' }}>
            {t('register.username_label')}
            <input
              type="text"
              name="username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              minLength={3}
              maxLength={64}
              pattern="[a-zA-Z0-9_.-]+"
              title={t("register.username_rules")}
              autoComplete="username"
              style={inputStyle}
            />
          </label>

          <label style={{ color: 'var(--text-color)' }}>
            {t('register.email_label')}
            <input
              type="email"
              name="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              maxLength={255}
              autoComplete="email"
              style={inputStyle}
            />
          </label>

          <label style={{ color: 'var(--text-color)' }}>
            {t('register.password_label')}
            <input
              type="password"
              name="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={8}
              maxLength={128}
              autoComplete="new-password"
              style={inputStyle}
            />
            <PasswordStrength password={password} />
          </label>

          <label style={{ color: 'var(--text-color)' }}>
            {t('register.confirm_password_label')}
            <input
              type="password"
              name="confirm_password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              required
              minLength={8}
              maxLength={128}
              autoComplete="new-password"
              style={{
                ...inputStyle,
                borderColor: confirmPassword && confirmPassword !== password ? '#ef4444' : 'var(--border-color)',
              }}
            />
            {confirmPassword && confirmPassword !== password && (
              <small style={{ color: '#ef4444' }}>{t('errors.7.4')}</small>
            )}
          </label>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '0.5rem 1rem',
              background: loading ? '#94a3b8' : 'var(--primary-color, #2563eb)',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer',
              marginTop: '0.5rem',
              fontWeight: 600,
            }}
          >
            {loading ? t('register.creating') : t('register.register_button')}
          </button>
        </form>

        <p style={{ marginTop: '1.5rem', fontSize: '0.9rem' }}>
          {t('register.already_have')}{' '}
          <Link to="/login" style={{ color: 'var(--primary-color)' }}>{t('register.sign_in')}</Link>
        </p>
      </div>
    </div>
  );
}
