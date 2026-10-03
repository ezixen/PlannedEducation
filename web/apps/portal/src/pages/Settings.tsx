import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { useToast } from '../contexts/ToastContext';
import type { ThemeColor, ThemeRadius } from '../contexts/ThemeContext';
import { apiClient } from '../api';
import { AIKeySettings } from '../components/AIKeySettings';
import { TwoFASettings } from '../components/TwoFASettings';
import { OCRProcessor } from '../components/OCRProcessor';
import { STTProcessor } from '../components/STTProcessor';

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.625rem',
  marginTop: '0.25rem',
  borderRadius: 'var(--radius-md)',
  border: '1px solid var(--border-color)',
  backgroundColor: 'var(--bg-color)',
  color: 'var(--text-color)',
  fontSize: '0.95rem',
  boxSizing: 'border-box',
};

const labelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '0.375rem',
  fontSize: '0.9rem',
  fontWeight: 500,
  color: 'var(--text-color)',
};

const THEME_OPTIONS: { value: ThemeColor; label: string }[] = [
  { value: 'skyward', label: 'Skyward' },
  { value: 'carbon_cyan', label: 'Carbon Cyan' },
  { value: 'enterprise_blue', label: 'Enterprise Blue' },
  { value: 'blush_silver', label: 'Blush Silver' },
  { value: 'matrix_green', label: 'Matrix Green' },
  { value: 'black_orange', label: 'Black Orange' },
  { value: 'sunset_cabin', label: 'Sunset Cabin' },
  { value: 'aurora_night', label: 'Aurora Night' },
  { value: 'comic_stage', label: 'Comic Stage' },
  { value: 'ocean_calm', label: 'Ocean Calm' },
];

const RADIUS_OPTIONS: { value: ThemeRadius; label: string }[] = [
  { value: 'square', label: 'Square Edges' },
  { value: 'soft', label: 'Soft Edges' },
  { value: 'round', label: 'Round Edges' },
];

export function Settings() {
  const { user, refreshUser } = useAuth();
  const { color, setColor, radius, setRadius } = useTheme();
  const { success: showSuccess, error: showError } = useToast();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
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

    if (newPassword && newPassword !== confirmNewPassword) {
      showError('New passwords do not match.');
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
      await refreshUser?.();
      setNewPassword('');
      setConfirmNewPassword('');
      showSuccess('Profile updated successfully!');
    } catch (err: any) {
      showError('Failed to update profile.', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '1rem', maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-color)', marginBottom: '0.5rem' }}>
          Settings
        </h1>
        <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
          Manage your account preferences and security.
        </p>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          UUID: <code style={{ backgroundColor: 'var(--bg-color)', padding: '0.125rem 0.375rem', borderRadius: 'var(--radius-sm)', fontSize: '0.8rem' }}>{user?.id}</code>
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

        {/* Personal Details section */}
        <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
          <h2 style={{ margin: '0 0 1.5rem', fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-color)' }}>Personal Details</h2>
          
          <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '500px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
              <label style={labelStyle}>
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
              
              <label style={labelStyle}>
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
            </div>

            <label style={labelStyle}>
              Phone Number <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 400 }}>(optional)</span>
              <input
                type="tel"
                value={phone}
                onChange={e => setPhone(e.target.value)}
                maxLength={32}
                autoComplete="tel"
                style={inputStyle}
              />
            </label>

            <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)', margin: '1rem 0' }} />
            
            <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem', fontWeight: 600, color: 'var(--text-color)' }}>Change Password</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: '0 0 1rem' }}>Leave blank to keep your current password.</p>

            <label style={labelStyle}>
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

            <label style={labelStyle}>
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
                <small style={{ color: '#ef4444', fontSize: '0.8rem' }}>Passwords do not match</small>
              )}
            </label>

            <button
              type="submit"
              disabled={loading}
              style={{
                padding: '0.75rem 1.5rem',
                backgroundColor: loading ? '#94a3b8' : 'var(--primary-color)',
                color: '#fff',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                fontSize: '0.95rem',
                alignSelf: 'flex-start',
                marginTop: '0.5rem',
              }}
            >
              {loading ? 'Saving…' : 'Save Changes'}
            </button>
          </form>
        </div>

        {/* Appearance section */}
        <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
          <h2 style={{ margin: '0 0 1.5rem', fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-color)' }}>Appearance</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
            Customize your app theme and UI style.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '420px' }}>
            <label style={labelStyle}>
              Theme Color
              <select
                value={color}
                onChange={e => setColor(e.target.value as ThemeColor)}
                style={inputStyle}
              >
                {THEME_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </label>

            <label style={labelStyle}>
              Border Style
              <select
                value={radius}
                onChange={e => setRadius(e.target.value as ThemeRadius)}
                style={inputStyle}
              >
                {RADIUS_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </label>
          </div>
        </div>

        {/* Security section */}
        <TwoFASettings />

        {/* AI Key Management */}
        <AIKeySettings />

        {/* OCR Processor */}
        <OCRProcessor />

        {/* Speech-to-Text Processor */}
        <STTProcessor />

      </div>
    </div>
  );
}
