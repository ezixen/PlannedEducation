import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiClient } from '../api';

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
  const checks = [
    { label: 'At least 8 characters', ok: password.length >= 8 },
    { label: 'Uppercase letter', ok: /[A-Z]/.test(password) },
    { label: 'Lowercase letter', ok: /[a-z]/.test(password) },
    { label: 'Number', ok: /\d/.test(password) },
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
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      await apiClient.post('/auth/register', {
        full_name: fullName,
        username,
        email,
        password,
      });
      navigate('/login');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-color)' }}>
      <div style={{ padding: '2rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)', width: '100%', maxWidth: '420px', textAlign: 'center' }}>
        <h1 style={{ marginBottom: '0.5rem' }}>Planned Education</h1>
        <p style={{ marginBottom: '2rem', color: 'gray' }}>Create a new account</p>

        {error && (
          <div style={{ color: '#ef4444', marginBottom: '1rem', padding: '0.5rem', backgroundColor: '#fee2e2', borderRadius: '4px' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', textAlign: 'left' }}>
          <label>
            Full Name
            <input
              type="text"
              value={fullName}
              onChange={e => setFullName(e.target.value)}
              required
              maxLength={128}
              autoComplete="name"
              style={inputStyle}
            />
          </label>

          <label>
            Username
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              minLength={3}
              maxLength={64}
              pattern="[a-zA-Z0-9_.-]+"
              title="Letters, numbers, underscores, dots and hyphens only"
              autoComplete="username"
              style={inputStyle}
            />
          </label>

          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              maxLength={255}
              autoComplete="email"
              style={inputStyle}
            />
          </label>

          <label>
            Password
            <input
              type="password"
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

          <label>
            Confirm Password
            <input
              type="password"
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
              <small style={{ color: '#ef4444' }}>Passwords do not match</small>
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
            {loading ? 'Creating account…' : 'Register'}
          </button>
        </form>

        <p style={{ marginTop: '1.5rem', fontSize: '0.9rem' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: 'var(--primary-color)' }}>Sign in here</Link>
        </p>
      </div>
    </div>
  );
}
