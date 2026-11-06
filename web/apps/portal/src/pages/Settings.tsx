import { useState, useEffect } from 'react';
import { useI18n } from '../contexts/I18nContext';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { useToast } from '../contexts/ToastContext';
import type { ThemeColor, ThemeRadius } from '../contexts/ThemeContext';
import { apiClient } from '../api';
import { AIKeySettings } from '../components/AIKeySettings';
import { TwoFASettings } from '../components/TwoFASettings';
import { PasskeysSettings } from '../components/PasskeysSettings';
import { I18nSettings } from '../components/I18nSettings';

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

const THEME_OPTIONS: { value: ThemeColor; labelKey: string }[] = [
  { value: 'skyward', labelKey: 'settings.theme_skyward' },
  { value: 'carbon_cyan', labelKey: 'settings.theme_carbon_cyan' },
  { value: 'enterprise_blue', labelKey: 'settings.theme_enterprise_blue' },
  { value: 'blush_silver', labelKey: 'settings.theme_blush_silver' },
  { value: 'matrix_green', labelKey: 'settings.theme_matrix_green' },
  { value: 'black_orange', labelKey: 'settings.theme_black_orange' },
  { value: 'sunset_cabin', labelKey: 'settings.theme_sunset_cabin' },
  { value: 'aurora_night', labelKey: 'settings.theme_aurora_night' },
  { value: 'comic_stage', labelKey: 'settings.theme_comic_stage' },
  { value: 'ocean_calm', labelKey: 'settings.theme_ocean_calm' },
];

const RADIUS_OPTIONS: { value: ThemeRadius; labelKey: string }[] = [
  { value: 'square', labelKey: 'settings.radius_square' },
  { value: 'soft', labelKey: 'settings.radius_soft' },
  { value: 'round', labelKey: 'settings.radius_round' },
];

export function Settings() {
  const { t } = useI18n();
  const { user, refreshUser } = useAuth();
  const { color, setColor, radius, setRadius } = useTheme();
  const { success: showSuccess, error: showError } = useToast();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeSection, setActiveSection] = useState<'personal' | 'appearance' | 'security' | 'passkeys' | 'ai' | 'language' | 'messaging'>('personal');
  const [dmVisible, setDmVisible] = useState(true);
  const [savingDmVisibility, setSavingDmVisibility] = useState(false);

  // Populate fields from context when user loads
  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '');
      setEmail(user.email || '');
      setPhone(user.phone_number || '');
      setDmVisible(Boolean(user.is_visible_in_teacher_dm ?? true));
    }
  }, [user]);

  const isAdminUser = Boolean(user?.is_admin || user?.role === 'admin' || user?.role === 'superadmin');

  const handleToggleDmVisibility = async () => {
    const next = !dmVisible;
    setSavingDmVisibility(true);
    try {
      await apiClient.patch('/auth/admin/settings/dm-visibility', {
        is_visible_in_teacher_dm: next,
      });
      setDmVisible(next);
      await refreshUser?.();
      showSuccess(t('settings.dm_visibility_saved'));
    } catch (err: any) {
      showError(err.response?.data?.detail || err.message || t('settings.visibility_update_failed'));
    } finally {
      setSavingDmVisibility(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();

    if (newPassword && newPassword !== confirmNewPassword) {
      showError(t('settings.passwords_do_not_match'));
      return;
    }

    // Require current password when changing password
    if (newPassword && !currentPassword) {
      showError(t('settings.current_password_required'));
      return;
    }

    const payload: Record<string, string> = {
      full_name: fullName,
      email,
      phone_number: phone,
    };
    if (newPassword) {
      payload.password = newPassword;
      payload.current_password = currentPassword;
    }

    setLoading(true);
    try {
      await apiClient.put('/auth/settings', payload);
      await refreshUser?.();
      setNewPassword('');
      setConfirmNewPassword('');
      showSuccess(t('settings.profile_updated'));
    } catch (err: any) {
      showError(t('settings.profile_update_failed'), err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '1rem', maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-color)', marginBottom: '0.5rem' }}>
          {t('settings.title')}
        </h1>
        <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
          {t('settings.subtitle')}
        </p>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          {t('settings.uuid_label')} <code style={{ backgroundColor: 'var(--bg-color)', padding: '0.125rem 0.375rem', borderRadius: 'var(--radius-sm)', fontSize: '0.8rem' }}>{user?.id}</code>
        </p>
      </div>

      {/* Submenu Navigation */}
      <div className="settings-submenus-bar" role="tablist" aria-label={t('settings.title')}>
        <button
          type="button"
          role="tab"
          aria-selected={activeSection === 'personal'}
          onClick={() => setActiveSection('personal')}
          className={`settings-submenu-btn ${activeSection === 'personal' ? 'active' : ''}`}
        >
          {t('settings.section_personal')}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeSection === 'appearance'}
          onClick={() => setActiveSection('appearance')}
          className={`settings-submenu-btn ${activeSection === 'appearance' ? 'active' : ''}`}
        >
          {t('settings.section_appearance')}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeSection === 'security'}
          onClick={() => setActiveSection('security')}
          className={`settings-submenu-btn ${activeSection === 'security' ? 'active' : ''}`}
        >
          {t('settings.section_security')}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeSection === 'passkeys'}
          onClick={() => setActiveSection('passkeys')}
          className={`settings-submenu-btn ${activeSection === 'passkeys' ? 'active' : ''}`}
        >
          {t('settings.section_passkeys')}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeSection === 'ai'}
          onClick={() => setActiveSection('ai')}
          className={`settings-submenu-btn ${activeSection === 'ai' ? 'active' : ''}`}
        >
          {t('settings.section_ai')}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeSection === 'language'}
          onClick={() => setActiveSection('language')}
          className={`settings-submenu-btn ${activeSection === 'language' ? 'active' : ''}`}
        >
          {t('settings.section_language')}
        </button>
        {isAdminUser && (
          <button
            type="button"
            role="tab"
            aria-selected={activeSection === 'messaging'}
            onClick={() => setActiveSection('messaging')}
            className={`settings-submenu-btn ${activeSection === 'messaging' ? 'active' : ''}`}
          >
            {t('settings.section_messaging')}
          </button>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

        {/* Personal Details section */}
        {activeSection === 'personal' && (
          <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
            <h2 style={{ margin: '0 0 1.5rem', fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-color)' }}>{t('settings.2')}</h2>
            
            <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '500px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                <label style={labelStyle}>
                  {t('settings.3')}
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
                  {t('settings.4')}
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
                {t('settings.5')} <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 400 }}>{t('settings.optional_tag')}</span>
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
              
              <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem', fontWeight: 600, color: 'var(--text-color)' }}>{t('settings.6')}</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: '0 0 1rem' }}>{t('settings.leave_blank_pwd')}</p>

              <label style={labelStyle}>
                {t('login.password_label')}
                <input
                  type="password"
                  value={currentPassword}
                  onChange={e => setCurrentPassword(e.target.value)}
                  minLength={8}
                  maxLength={128}
                  autoComplete="current-password"
                  style={inputStyle}
                />
              </label>

              <label style={labelStyle}>
                {t('login.new_password_label')}
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
                {t('login.confirm_password_label')}
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
                  <small style={{ color: '#ef4444', fontSize: '0.8rem' }}>{t('settings.passwords_not_match')}</small>
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
                {loading ? t('common.14') : t('settings.17')}
              </button>
            </form>
          </div>
        )}

        {/* Appearance section */}
        {activeSection === 'appearance' && (
          <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
            <h2 style={{ margin: '0 0 1.5rem', fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-color)' }}>{t('settings.13')}</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
              {t('settings.appearance_desc')}
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '420px' }}>
              <label style={labelStyle}>
                {t('settings.13.1')}
                <select
                  value={color}
                  onChange={e => setColor(e.target.value as ThemeColor)}
                  style={inputStyle}
                >
                  {THEME_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{t(opt.labelKey)}</option>
                  ))}
                </select>
              </label>

              <label style={labelStyle}>
                {t('settings.border_style')}
                <select
                  value={radius}
                  onChange={e => setRadius(e.target.value as ThemeRadius)}
                  style={inputStyle}
                >
                  {RADIUS_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{t(opt.labelKey)}</option>
                  ))}
                </select>
              </label>
            </div>
          </div>
        )}

        {/* Security section */}
        {activeSection === 'security' && (
          <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
            <h2 style={{ margin: '0 0 1.5rem', fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-color)' }}>{t('settings.section_security')}</h2>
            <TwoFASettings />
          </div>
        )}

        {/* Passkeys (WebAuthn) */}
        {activeSection === 'passkeys' && (
          <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
            <h2 style={{ margin: '0 0 1.5rem', fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-color)' }}>{t('settings.section_passkeys')}</h2>
            <PasskeysSettings />
          </div>
        )}

        {/* AI Key Management */}
        {activeSection === 'ai' && (
          <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
            <h2 style={{ margin: '0 0 1.5rem', fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-color)' }}>{t('settings.section_ai')}</h2>
            <AIKeySettings />
          </div>
        )}

        {/* Language & Regional Settings */}
        {activeSection === 'language' && (
          <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
            <h2 style={{ margin: '0 0 1.5rem', fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-color)' }}>{t('settings.section_language')}</h2>
            <I18nSettings />
          </div>
        )}

        {/* Admin messaging visibility */}
        {activeSection === 'messaging' && isAdminUser && (
          <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
            <h2 style={{ margin: '0 0 0.75rem', fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-color)' }}>
              {t('settings.dm_visibility_title')}
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem', lineHeight: 1.45 }}>
              {t('settings.dm_visibility_desc')}
            </p>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', cursor: 'pointer', fontSize: '0.95rem', color: 'var(--text-color)', fontWeight: 500 }}>
              <input
                type="checkbox"
                checked={dmVisible}
                onChange={handleToggleDmVisibility}
                disabled={savingDmVisibility}
                style={{ width: '18px', height: '18px', cursor: 'pointer' }}
              />
              <span>{t('settings.dm_visibility_toggle')}</span>
            </label>
          </div>
        )}

      </div>
    </div>
  );
}
