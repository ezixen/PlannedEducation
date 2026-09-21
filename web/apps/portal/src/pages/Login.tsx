import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import type { CredentialResponse } from '@react-oauth/google';
import { useAuth } from '../contexts/AuthContext';

export function Login() {
  const { login, loginWithPassword } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  
  // For local testing bypass
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    if (!credentialResponse.credential) return;
    try {
      setError('');
      await login(credentialResponse.credential);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.');
    }
  };

  const handleLocalLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setError('');
      await loginWithPassword(email, password);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Local login failed.');
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-color)' }}>
      <div style={{ padding: '2rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)', width: '100%', maxWidth: '400px', textAlign: 'center' }}>
        <h1 style={{ marginBottom: '1rem' }}>PlannedEducation</h1>
        <p style={{ marginBottom: '2rem', color: 'gray' }}>Sign in to continue</p>

        {error && <div style={{ color: 'red', marginBottom: '1rem', padding: '0.5rem', backgroundColor: '#fee2e2', borderRadius: '4px' }}>{error}</div>}

        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '1rem' }}>
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={() => setError('Google Authentication Failed')}
            useOneTap
          />
        </div>

        {window.location.hostname === 'localhost' && (
          <form onSubmit={handleLocalLogin} style={{ marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
            <p style={{ color: 'gray', fontSize: '0.8rem', marginBottom: '1rem' }}>Local Development Login (test_users.json)</p>
            
            <input 
              type="email" 
              placeholder="Test Email" 
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              style={{ width: '100%', padding: '0.5rem', marginBottom: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}
            />
            
            <input 
              type="password" 
              placeholder="Test Password" 
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              style={{ width: '100%', padding: '0.5rem', marginBottom: '1rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}
            />

            <button 
              type="submit"
              style={{ width: '100%', padding: '0.5rem 1rem', background: 'var(--primary-color, #2563eb)', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              Login Locally
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
