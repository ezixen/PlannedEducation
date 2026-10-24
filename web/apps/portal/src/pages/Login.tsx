import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { ForgotPasswordModal } from '../components/ForgotPasswordModal';
import { apiClient } from '../api';
import { useI18n } from '../contexts/I18nContext';


export function Login() {
  const { t } = useI18n();
  const { loginWithPassword, refreshUser } = useAuth();
  const { error: showError, success: showSuccess } = useToast();
  const navigate = useNavigate();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [teacherResetActive, setTeacherResetActive] = useState(false);
  const [teacherResetChecking, setTeacherResetChecking] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  const handleCheckTeacherReset = async () => {
    setTeacherResetChecking(true);
    try {
      const res = await apiClient.post('/auth/teacher-reset/check', {
        identifier: email.trim(),
      });
      if (res.data?.teacher_reset_active) {
        setTeacherResetActive(true);
        showSuccess(res.data.message || t('login.teacher_reset_title'));
      } else {
        showError(res.data.message || t('login.no_reset_found'));
      }
    } catch {
      showError(t('errors.9'));
    } finally {
      setTeacherResetChecking(false);
    }
  };


  const handleLocalLogin = async (e: React.FormEvent) => {
    e.preventDefault(); 
    setLoading(true);
    try {
      await loginWithPassword(email, password, rememberMe);
      navigate('/');
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Login failed';
      let message = 'Login failed';
      if (typeof detail === 'string' && (detail.includes('RESET_ACTIVE') || detail.includes('PASSWORD_RESET_ACTIVE'))) {
        setTeacherResetActive(true);
        showSuccess(t('login.account_unlocked'));
        setLoading(false);
        return;
      } else if (detail === 'Invalid email/username or password') {
        message = 'Invalid email or password. Please check your credentials and try again.';
      } else if (detail === 'Account is deactivated. Please contact support.') {
        message = 'This account has been deactivated. Please contact support.';
      } else if (typeof detail === 'string' && (detail.includes('rate limit') || detail.includes('too many') || detail.includes('temporarily locked'))) {
        message = detail;
      } else {
        message = detail;
      }
      showError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleTeacherResetComplete = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      showError(t('errors.7.4'));
      return;
    }
    setLoading(true);
    try {
      const res = await (await import('../api')).apiClient.post('/auth/teacher-reset/complete', {
        identifier: email.trim(),
        new_password: newPassword,
      });
      if (res.data?.access_token) {
        localStorage.setItem('access_token', res.data.access_token);
        await refreshUser();
        showSuccess(t('toast.22'));
        navigate('/');
      }
    } catch (err: any) {
      showError('Password reset failed', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', minHeight: '100dvh', padding: '1rem', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-color)', boxSizing: 'border-box' }}>
      <div style={{ padding: '2rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', width: '100%', maxWidth: '420px', textAlign: 'center', boxSizing: 'border-box' }}>
        <div style={{ marginBottom: '1.5rem' }}>
          <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700, color: 'var(--primary-color)' }}>{t('login.title')}</h1>
          <p style={{ margin: '0.25rem 0 0', color: 'var(--text-muted)', fontSize: '0.9rem' }}>{t('login.subtitle')}</p>
        </div>

        {
          teacherResetActive ? (
            <form onSubmit={handleTeacherResetComplete} style={{ margin: 0, textAlign: 'left' }}>
              <div
                style={{
                  padding: '0.85rem',
                  backgroundColor: 'rgba(16, 185, 129, 0.1)',
                  border: '1px solid #10b981',
                  borderRadius: 'var(--radius-md)',
                  color: '#065f46',
                  fontSize: '0.85rem',
                  marginBottom: '1.25rem',
                  lineHeight: 1.4,
                }}
              >
                🎓 <strong>{t('login.teacher_reset_title')}</strong><br />
                {t('login.teacher_reset_subtitle')}
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-color)', fontSize: '0.9rem', fontWeight: 500 }}>
                  {t('login.email_label')}
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder={t('login.email_placeholder')}
                  style={{ width: '100%', padding: '0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.95rem', boxSizing: 'border-box' }}
                />
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-color)', fontSize: '0.9rem', fontWeight: 500 }}>
                  {t('settings.8')}
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  style={{ width: '100%', padding: '0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.95rem', boxSizing: 'border-box' }}
                />
              </div>

              <div style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-color)', fontSize: '0.9rem', fontWeight: 500 }}>
                  {t('settings.8.1')}
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  style={{ width: '100%', padding: '0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.95rem', boxSizing: 'border-box' }}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                style={{ width: '100%', padding: '0.75rem 1rem', background: loading ? '#94a3b8' : '#10b981', color: 'white', border: 'none', borderRadius: 'var(--radius-md)', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 600, fontSize: '0.95rem', boxSizing: 'border-box' }}
              >
                {loading ? t('login.setting_password') : t('login.set_password')}
              </button>

              <button
                type="button"
                onClick={() => setTeacherResetActive(false)}
                style={{ width: '100%', marginTop: '0.75rem', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.85rem' }}
              >
                {t('login.back_to_login')}
              </button>
            </form>
          ) : (
            <form onSubmit={handleLocalLogin} style={{ margin: 0 }}>
              <div style={{ marginBottom: '1rem', textAlign: 'left' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-color)', fontSize: '0.9rem', fontWeight: 500 }}>{t('login.email_label')}</label>
                <input 
                  type="email" 
                  placeholder={t('login.email_placeholder')}
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  style={{ width: '100%', padding: '0.75rem', marginBottom: '0', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.95rem', boxSizing: 'border-box' }}
                />
              </div>
              
              <div style={{ marginBottom: '1.25rem', textAlign: 'left' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <label style={{ margin: 0, color: 'var(--text-color)', fontSize: '0.9rem', fontWeight: 500 }}>{t('login.password_label')}</label>
                  <button
                    type="button"
                    onClick={() => setShowForgotModal(true)}
                    style={{
                      background: 'none',
                      border: 'none',
                      padding: 0,
                      color: 'var(--primary-color)',
                      fontSize: '0.825rem',
                      cursor: 'pointer',
                      fontWeight: 500,
                    }}
                  >
                    {t('login.forgot_password')}
                  </button>
                </div>
                <div style={{ position: 'relative' }}>
                  <input 
                    type={showPassword ? 'text' : 'password'} 
                    placeholder="••••••••"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                    style={{ width: '100%', padding: '0.75rem', paddingRight: '3rem', marginBottom: '0', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.95rem', boxSizing: 'border-box' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute',
                      right: '0.75rem',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'none',
                      border: 'none',
                      padding: '0.25rem',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                        <line x1="1" y1="1" x2="23" y2="23"></line>
                      </svg>
                    ) : (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                        <circle cx="12" cy="12" r="3"></circle>
                      </svg>
                    )}
                  </button>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-color)' }}>
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={e => setRememberMe(e.target.checked)}
                      style={{ width: '1rem', height: '1rem', accentColor: 'var(--primary-color)' }}
                    />
                    <span>{t('login.remember_me')}</span>
                  </label>
                  <button
                    type="button"
                    onClick={handleCheckTeacherReset}
                    disabled={teacherResetChecking}
                    style={{ background: 'none', border: 'none', padding: 0, color: '#10b981', fontSize: '0.775rem', cursor: 'pointer' }}
                  >
                    {teacherResetChecking ? t('common.loading') : t('login.account_unlocked_btn')}
                  </button>
                </div>
              </div>

              <button 
                type="submit"
                disabled={loading}
                style={{ width: '100%', padding: '0.75rem 1rem', background: loading ? '#94a3b8' : 'var(--primary-color)', color: 'white', border: 'none', borderRadius: 'var(--radius-md)', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 600, fontSize: '0.95rem', boxSizing: 'border-box' }}
              >
                {loading ? t('login.signing_in') : t('login.signin')}
              </button>
            </form>
          )}

        <p style={{ marginTop: '1.5rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          {t('login.no_account')}{' '}
          <Link to="/register" style={{ color: 'var(--primary-color)', fontWeight: 600, textDecoration: 'none' }}>{t('login.create_account')}</Link>
        </p>

        <ForgotPasswordModal
          isOpen={showForgotModal}
          onClose={() => setShowForgotModal(false)}
          defaultEmail={email}
        />
      </div>
    </div>
  );
}
