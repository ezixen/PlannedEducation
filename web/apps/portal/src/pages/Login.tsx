import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import type { CredentialResponse } from '@react-oauth/google';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';

export function Login() {
  const { login, loginWithPassword } = useAuth();
  const { error: showError } = useToast();
  const navigate = useNavigate();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    if (!credentialResponse.credential) return;
    try {
      await login(credentialResponse.credential);
      navigate('/');
    } catch (err: any) {
      showError('Login failed. Please try again. ' + (err.response?.data?.detail || ''));
    }
  };

  const handleLocalLogin = async (e: React.FormEvent) => {
    e.preventDefault(); 
    try {
      if (loginWithPassword) {
        await loginWithPassword(email, password);
        navigate('/');
      }
    } catch (err: any) {
      showError('Local login failed. ' + err.message);
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-color)' }}>
      <div style={{ padding: '2rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', width: '100%', maxWidth: '400px', textAlign: 'center' }}>
        <h1 style={{ marginBottom: '1rem', fontSize: '1.5rem', fontWeight: 700, color: 'var(--primary-color)' }}>Planned Education</h1>
        <p style={{ marginBottom: '2rem', color: 'var(--text-muted)' }}>Sign in to continue</p>

        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '1rem' }}>
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={() => showError('Google Authentication Failed. Please try again or use email login.')}
            useOneTap
          />
        </div>

        {window.location.hostname === 'localhost' && (
          <form onSubmit={handleLocalLogin} style={{ marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginBottom: '1rem' }}>Or sign in with email</p>
            
            <input 
              type="email" 
              placeholder="Email address" 
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              style={{ width: '100%', padding: '0.625rem', marginBottom: '0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.95rem' }}
            />
            
            <input 
              type="password" 
              placeholder="Password" 
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              style={{ width: '100%', padding: '0.625rem', marginBottom: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.95rem' }}
            />

            <button 
              type="submit"
              style={{ width: '100%', padding: '0.75rem 1rem', background: 'var(--primary-color)', color: 'white', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 600, fontSize: '0.95rem' }}
            >
              Sign In
            </button>
          </form>
        )}

        <p style={{ marginTop: '1.5rem', fontSize: '0.9rem' }}>
          Don't have an account? <Link to="/register" style={{ color: 'var(--primary-color)', fontWeight: 500 }}>Register here</Link>
        </p>
      </div>
    </div>
  );
}
