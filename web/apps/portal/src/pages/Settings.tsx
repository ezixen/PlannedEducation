import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../api';

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.5rem',
  marginTop: '0.25rem',
  borderRadius: '4px',
  border: '1px solid var(--border-color)',
  backgroundColor: 'var(--bg-color)',
  color: 'var(--text-color)',
};

export function Settings() {
  const { user, refreshUser } = useAuth();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);
  const [loading, setLoading] = useState(false);

  // Populate fields from context when user loads
  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '');
      setEmail(user.email || '');
      setPhone(user.phone_number || '');
    }
  }, [user]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);

    if (newPassword && newPassword !== confirmNewPassword) {
      setMessage({ text: 'New passwords do not match.', ok: false });
      return;
    }

    const payload: Record<string, string> = {
      full_name: fullName,
      email,
      phone_number: phone,
    };
    if (newPassword) {
      payload.password = newPassword;
    }

    setLoading(true);
    try {
      await apiClient.put('/auth/settings', payload);
      // Refresh the auth context so the navbar/header updates
      await refreshUser?.();
      setNewPassword('');

      setConfirmNewPassword('');
      setMessage({ text: 'Profile updated successfully!', ok: true });
    } catch (err: any) {
      setMessage({
        text: err.response?.data?.detail || err.message || 'Failed to update profile.',
        ok: false,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Settings</h1>
      <p style={{ color: 'gray' }}>Manage your account preferences and security.</p>

      <div style={{ marginTop: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

        {/* Profile section */}
        <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <h3>Account Profile</h3>
          <p style={{ color: 'gray', fontSize: '0.9rem', marginBottom: '1rem' }}>
            Your UUID (<code>{user?.id}</code>) cannot be changed.
          </p>

          <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '420px' }}>
            <label>
              Full Name
              <input
                type="text"
                value={fullName}
                onChange={e => setFullName(e.target.value)}
                maxLength={128}
                autoComplete="name"
                style={inputStyle}
              />
            </label>

            <label>
              Email Address
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
              Phone Number <span style={{ color: 'gray', fontSize: '0.85rem' }}>(optional)</span>
              <input
                type="tel"
                value={phone}
                onChange={e => setPhone(e.target.value)}
                maxLength={32}
                autoComplete="tel"
                style={inputStyle}
              />
            </label>

            <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)' }} />
            <h4 style={{ margin: '0 0 0.5rem' }}>Change Password</h4>
            <p style={{ color: 'gray', fontSize: '0.85rem', margin: 0 }}>Leave blank to keep your current password.</p>

            <label>
              New Password
              <input
                type="password"
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
                minLength={8}
                maxLength={128}
                autoComplete="new-password"
                style={inputStyle}
              />
            </label>

            <label>
              Confirm New Password
              <input
                type="password"
                value={confirmNewPassword}
                onChange={e => setConfirmNewPassword(e.target.value)}
                minLength={8}
                maxLength={128}
                autoComplete="new-password"
                style={{
                  ...inputStyle,
                  borderColor: confirmNewPassword && confirmNewPassword !== newPassword ? '#ef4444' : 'var(--border-color)',
                }}
              />
              {confirmNewPassword && confirmNewPassword !== newPassword && (
                <small style={{ color: '#ef4444' }}>Passwords do not match</small>
              )}
            </label>

            {message && (
              <div style={{
                padding: '0.5rem',
                borderRadius: '4px',
                backgroundColor: message.ok ? '#d1fae5' : '#fee2e2',
                color: message.ok ? '#065f46' : '#991b1b',
                fontSize: '0.9rem',
              }}>
                {message.text}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                padding: '0.5rem 1.5rem',
                backgroundColor: loading ? '#94a3b8' : 'var(--primary-color)',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                alignSelf: 'flex-start',
              }}
            >
              {loading ? 'Saving…' : 'Save Changes'}
            </button>
          </form>
        </div>

        {/* Security section placeholder */}
        <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <h3>Security</h3>
          <p style={{ color: 'gray' }}>
            Two-Factor Authentication (TOTP) — coming soon.
          </p>
        </div>

      </div>
    </div>
  );
}
