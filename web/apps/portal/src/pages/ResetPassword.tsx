import { useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { KeyRound, CheckCircle2, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { apiClient } from '../api';
import { useToast } from '../contexts/ToastContext';
import { useI18n } from '../contexts/I18nContext';
import { useAuth } from '../contexts/AuthContext';

export function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useI18n();
  const { error: showError, success: showSuccess } = useToast();
  const { refreshUser } = useAuth();

  const tokenParam = searchParams.get('token') || '';
  const emailParam = searchParams.get('email') || '';

  const [email, setEmail] = useState(emailParam);
  const [token, setToken] = useState(tokenParam);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!token.trim()) {
      showError(t('reset_password.missing_token'));
      return;
    }

    if (newPassword !== confirmPassword) {
      showError(t('forgot_password.passwords_do_not_match'));
      return;
    }

    setSubmitting(true);
    try {
      const res = await apiClient.post('/auth/password-reset/confirm', {
        email: email.trim().toLowerCase(),
        token: token.trim(),
        new_password: newPassword,
      });

      if (res.data?.access_token) {
        localStorage.setItem('access_token', res.data.access_token);
        await refreshUser();
      }

      setSuccess(true);
      showSuccess(t('forgot_password.reset_success_toast'));
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || t('forgot_password.reset_failed_toast');
      showError(t('forgot_password.reset_failed_toast'), detail);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        minHeight: '100dvh',
        padding: '1rem',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'var(--bg-color)',
        boxSizing: 'border-box',
      }}
    >
      <div
        style={{
          padding: '2rem',
          backgroundColor: 'var(--sidebar-bg)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-color)',
          width: '100%',
          maxWidth: '440px',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
          boxSizing: 'border-box',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <div
            style={{
              display: 'inline-flex',
              padding: '0.75rem',
              backgroundColor: 'rgba(37, 99, 235, 0.1)',
              borderRadius: '50%',
              color: 'var(--primary-color)',
              marginBottom: '0.75rem',
            }}
          >
            <KeyRound size={28} />
          </div>
          <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-color)' }}>
            {t('reset_password.title')}
          </h1>
          <p style={{ margin: '0.35rem 0 0', color: 'var(--text-muted)', fontSize: '0.875rem', lineHeight: 1.4 }}>
            {t('reset_password.subtitle')}
          </p>
        </div>

        {success ? (
          <div style={{ textAlign: 'center', padding: '1rem 0' }}>
            <CheckCircle2 size={48} style={{ color: '#10b981', marginBottom: '1rem' }} />
            <h3 style={{ margin: '0 0 0.5rem', color: 'var(--text-color)', fontSize: '1.2rem' }}>
              {t('reset_password.success_title')}
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem', lineHeight: 1.5 }}>
              {t('reset_password.success_desc')}
            </p>
            <button
              type="button"
              onClick={() => navigate('/')}
              style={{
                width: '100%',
                padding: '0.75rem',
                backgroundColor: 'var(--primary-color)',
                color: '#ffffff',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.95rem',
              }}
            >
              {t('dashboard.title')}
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {!tokenParam && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem',
                  backgroundColor: 'rgba(239, 68, 68, 0.08)',
                  border: '1px solid #ef4444',
                  borderRadius: 'var(--radius-md)',
                  color: '#b91c1c',
                  fontSize: '0.85rem',
                }}
              >
                <AlertCircle size={18} style={{ flexShrink: 0 }} />
                <span>{t('reset_password.missing_token')}</span>
              </div>
            )}

            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.85rem',
                  fontWeight: 500,
                  color: 'var(--text-color)',
                  marginBottom: '0.35rem',
                }}
              >
                {t('forgot_password.email_label')}
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t('forgot_password.email_placeholder')}
                style={{
                  width: '100%',
                  padding: '0.7rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-color)',
                  backgroundColor: 'var(--bg-color)',
                  color: 'var(--text-color)',
                  fontSize: '0.95rem',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            {!tokenParam && (
              <div>
                <label
                  style={{
                    display: 'block',
                    fontSize: '0.85rem',
                    fontWeight: 500,
                    color: 'var(--text-color)',
                    marginBottom: '0.35rem',
                  }}
                >
                  Reset Token
                </label>
                <input
                  type="text"
                  required
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="Paste your 32-character reset token here"
                  style={{
                    width: '100%',
                    padding: '0.7rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-color)',
                    color: 'var(--text-color)',
                    fontFamily: 'monospace',
                    fontSize: '0.9rem',
                    boxSizing: 'border-box',
                  }}
                />
              </div>
            )}

            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.85rem',
                  fontWeight: 500,
                  color: 'var(--text-color)',
                  marginBottom: '0.35rem',
                }}
              >
                {t('forgot_password.new_password_label')}
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  style={{
                    width: '100%',
                    padding: '0.7rem',
                    paddingRight: '2.5rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-color)',
                    color: 'var(--text-color)',
                    fontSize: '0.95rem',
                    boxSizing: 'border-box',
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '0.6rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    padding: '0.2rem',
                  }}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.85rem',
                  fontWeight: 500,
                  color: 'var(--text-color)',
                  marginBottom: '0.35rem',
                }}
              >
                {t('forgot_password.confirm_password_label')}
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  required
                  minLength={8}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  style={{
                    width: '100%',
                    padding: '0.7rem',
                    paddingRight: '2.5rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-color)',
                    color: 'var(--text-color)',
                    fontSize: '0.95rem',
                    boxSizing: 'border-box',
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  style={{
                    position: 'absolute',
                    right: '0.6rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    padding: '0.2rem',
                  }}
                >
                  {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              style={{
                width: '100%',
                padding: '0.75rem',
                backgroundColor: 'var(--primary-color)',
                color: '#ffffff',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                cursor: submitting ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                fontSize: '0.95rem',
                marginTop: '0.5rem',
              }}
            >
              {submitting ? t('forgot_password.resetting') : t('forgot_password.reset_button')}
            </button>

            <div style={{ textAlign: 'center', marginTop: '0.5rem' }}>
              <Link
                to="/login"
                style={{
                  color: 'var(--text-muted)',
                  fontSize: '0.85rem',
                  textDecoration: 'none',
                }}
              >
                {t('login.back_to_login')}
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
