import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import type { CredentialResponse } from '@react-oauth/google';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { ForgotPasswordModal } from '../components/ForgotPasswordModal';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

export function Login() {
  const { login, loginWithPassword, refreshUser } = useAuth();
  const { error: showError, success: showSuccess } = useToast();
  const navigate = useNavigate();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [teacherResetActive, setTeacherResetActive] = useState(false);

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    if (!credentialResponse.credential) return;
    setLoading(true);
    try {
      await login(credentialResponse.credential);
      navigate('/');
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Login failed';
      let message = 'Google login failed';
      if (detail === 'Google sign-in is not configured on this server') {
        message = 'Google sign-in is not configured. Please use email login instead.';
      } else if (detail === 'Invalid Google token') {
        message = 'Invalid Google token. Please try again.';
      } else {
        message = detail;
      }
      showError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleLocalLogin = async (e: React.FormEvent) => {
    e.preventDefault(); 
    setLoading(true);
    try {
      await loginWithPassword(email, password);
      navigate('/');
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Login failed';
      let message = 'Login failed';
      if (typeof detail === 'string' && detail.includes('TEACHER_RESET_ACTIVE')) {
        setTeacherResetActive(true);
        showSuccess('Your teacher has unlocked your account! Set your new password to enter.');
        setLoading(false);
        return;
      } else if (detail === 'Invalid email/username or password') {
        message = 'Invalid email or password. Please check your credentials and try again.';
      } else if (detail === 'This account uses Google sign-in. Please use the Google button to log in.') {
        message = 'This account uses Google sign-in. Please use the Google button above.';
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
      showError('Passwords do not match');
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
        showSuccess('Password updated successfully! Welcome to your exam session.');
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
          <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700, color: 'var(--primary-color)' }}>Planned Education</h1>
          <p style={{ margin: '0.25rem 0 0', color: 'var(--text-muted)', fontSize: '0.9rem' }}>Secure exam platform for schools</p>
        </div>

        {GOOGLE_CLIENT_ID ? (
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '1.5rem' }}>
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => showError('Google Authentication Failed. Please try again or use email login.')}
              useOneTap
            />
          </div>
        ) : null}

        {!GOOGLE_CLIENT_ID || ['localhost', '127.0.0.1'].includes(window.location.hostname) ? (
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
                🎓 <strong>Your teacher has unlocked your account for today's test!</strong><br />
                Enter your email and choose your new password below to enter your exam session immediately:
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-color)', fontSize: '0.9rem', fontWeight: 500 }}>
                  Email address
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@school.edu"
                  style={{ width: '100%', padding: '0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.95rem', boxSizing: 'border-box' }}
                />
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-color)', fontSize: '0.9rem', fontWeight: 500 }}>
                  New Password
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
                  Confirm New Password
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
                {loading ? 'Setting Password & Entering…' : 'Set Password & Enter Exam ⚡'}
              </button>

              <button
                type="button"
                onClick={() => setTeacherResetActive(false)}
                style={{ width: '100%', marginTop: '0.75rem', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.85rem' }}
              >
                ← Back to standard login
              </button>
            </form>
          ) : (
            <form onSubmit={handleLocalLogin} style={{ margin: 0 }}>
              <div style={{ marginBottom: '1rem', textAlign: 'left' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-color)', fontSize: '0.9rem', fontWeight: 500 }}>Email address</label>
                <input 
                  type="email" 
                  placeholder="you@school.edu"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  style={{ width: '100%', padding: '0.75rem', marginBottom: '0', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.95rem', boxSizing: 'border-box' }}
                />
              </div>
              
              <div style={{ marginBottom: '1.25rem', textAlign: 'left' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <label style={{ margin: 0, color: 'var(--text-color)', fontSize: '0.9rem', fontWeight: 500 }}>Password</label>
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
                    Forgot password?
                  </button>
                </div>
                <input 
                  type="password" 
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  style={{ width: '100%', padding: '0.75rem', marginBottom: '0', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.95rem', boxSizing: 'border-box' }}
                />
                <div style={{ marginTop: '0.4rem', textAlign: 'right' }}>
                  <button
                    type="button"
                    onClick={() => setTeacherResetActive(true)}
                    style={{ background: 'none', border: 'none', padding: 0, color: '#10b981', fontSize: '0.775rem', cursor: 'pointer' }}
                  >
                    ⚡ Teacher unlocked your account for test?
                  </button>
                </div>
              </div>

              <button 
                type="submit"
                disabled={loading}
                style={{ width: '100%', padding: '0.75rem 1rem', background: loading ? '#94a3b8' : 'var(--primary-color)', color: 'white', border: 'none', borderRadius: 'var(--radius-md)', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 600, fontSize: '0.95rem', boxSizing: 'border-box' }}
              >
                {loading ? 'Signing in…' : 'Sign in'}
              </button>
            </form>
          )
        ) : null}

        <p style={{ marginTop: '1.5rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          Don't have an account?{' '}
          <Link to="/register" style={{ color: 'var(--primary-color)', fontWeight: 600, textDecoration: 'none' }}>Create account</Link>
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
