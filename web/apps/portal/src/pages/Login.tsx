import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import type { CredentialResponse } from '@react-oauth/google';
import { useAuth } from '../contexts/AuthContext';

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [roleSelection, setRoleSelection] = useState<'student' | 'teacher' | 'parent'>('student');
  const [error, setError] = useState('');

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    if (!credentialResponse.credential) return;
    try {
      setError('');
      await login(credentialResponse.credential, roleSelection);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.');
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-color)' }}>
      <div style={{ padding: '2rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)', width: '100%', maxWidth: '400px', textAlign: 'center' }}>
        <h1 style={{ marginBottom: '1rem' }}>PlannedEducation</h1>
        <p style={{ marginBottom: '2rem', color: 'gray' }}>Sign in to continue</p>

        {error && <div style={{ color: 'red', marginBottom: '1rem', padding: '0.5rem', backgroundColor: '#fee2e2', borderRadius: '4px' }}>{error}</div>}

        <div style={{ marginBottom: '1.5rem', textAlign: 'left' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>If you are new, select your role:</label>
          <select 
            value={roleSelection} 
            onChange={(e) => setRoleSelection(e.target.value as any)}
            style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}
          >
            <option value="student">Student</option>
            <option value="teacher">Teacher</option>
            <option value="parent">Parent/Guardian</option>
          </select>
          <small style={{ color: 'gray', display: 'block', marginTop: '0.5rem' }}>
            Note: Role selection is only used during your very first sign-in.
          </small>
        </div>

        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={() => setError('Google Authentication Failed')}
            useOneTap
          />
        </div>
      </div>
    </div>
  );
}
