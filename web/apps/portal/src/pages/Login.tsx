import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import type { CredentialResponse } from '@react-oauth/google';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

export function Login() {
  const { login, loginWithPassword } = useAuth();
  const { error: showError } = useToast();
  const navigate = useNavigate();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

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
      if (detail === 'Invalid email/username or password') {
        message = 'Invalid email or password. Please check your credentials and try again.';
      } else if (detail === 'This account uses Google sign-in. Please use the Google button to log in.') {
        message = 'This account uses Google sign-in. Please use the Google button above.';
      } else if (detail === 'Account is deactivated. Please contact support.') {
        message = 'This account has been deactivated. Please contact support.';
      } else if (detail.includes('rate limit') || detail.includes('too many')) {
        message = 'Too many login attempts. Please wait a moment and try again.';
      } else {
        message = detail;
      }
      showError(message);
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
            
            <div style={{ marginBottom: '1.5rem', textAlign: 'left' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-color)', fontSize: '0.9rem', fontWeight: 500 }}>Password</label>
              <input 
                type="password" 
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                style={{ width: '100%', padding: '0.75rem', marginBottom: '0', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.95rem', boxSizing: 'border-box' }}
              />
            </div>

            <button 
              type="submit"
              disabled={loading}
              style={{ width: '100%', padding: '0.75rem 1rem', background: loading ? '#94a3b8' : 'var(--primary-color)', color: 'white', border: 'none', borderRadius: 'var(--radius-md)', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 600, fontSize: '0.95rem', boxSizing: 'border-box' }}
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        ) : null}

        <p style={{ marginTop: '1.5rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          Don't have an account?{' '}
          <Link to="/register" style={{ color: 'var(--primary-color)', fontWeight: 600, textDecoration: 'none' }}>Create account</Link>
        </p>
      </div>
    </div>
  );
}
