import { useState } from 'react';
import { useI18n } from '../contexts/I18nContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../api';

interface CreateUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUserCreated: () => void;
}

export function CreateUserModal({ isOpen, onClose, onUserCreated }: CreateUserModalProps) {
  const { t } = useI18n();
  const { success: showSuccess, error: showError } = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState<'admin' | 'teacher' | 'student' | 'parent'>('admin');
  const [password, setPassword] = useState('');

  // Result state after creation
  const [createdUser, setCreatedUser] = useState<{
    username: string;
    email: string;
    role: string;
    tempPassword?: string;
  } | null>(null);
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleClose = () => {
    setUsername('');
    setEmail('');
    setFullName('');
    setRole('admin');
    setPassword('');
    setCreatedUser(null);
    setCopied(false);
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload: any = {
        username: username.trim(),
        email: email.trim(),
        full_name: fullName.trim() || undefined,
        role,
      };
      if (password.trim()) {
        payload.password = password.trim();
      }

      const res = await apiClient.post('/admin/users', payload);
      showSuccess(`Successfully created ${role} account for ${username}`);
      setCreatedUser({
        username: res.data.username,
        email: res.data.email,
        role: res.data.role,
        tempPassword: res.data.temporary_password,
      });
      onUserCreated();
    } catch (err: any) {
      showError('Failed to create user', err.response?.data?.detail || err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const copyPassword = () => {
    if (createdUser?.tempPassword) {
      navigator.clipboard.writeText(createdUser.tempPassword);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1rem',
      }}
    >
      <div
        style={{
          backgroundColor: 'var(--sidebar-bg, #ffffff)',
          color: 'var(--text-color, #1e293b)',
          borderRadius: 'var(--radius-lg, 12px)',
          border: '1px solid var(--border-color, #e2e8f0)',
          maxWidth: '520px',
          width: '100%',
          padding: '1.75rem',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        }}
      >
        {createdUser ? (
          <div>
            <div style={{ textAlign: 'center', marginBottom: '1.25rem' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>🎉</div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
                {createdUser.role === 'admin' ? t('admin.admin_created') : t('admin.user_created')}
              </h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
                Account for <strong>{createdUser.username}</strong> ({createdUser.email}) is now active.
              </p>
            </div>

            {createdUser.tempPassword ? (
              <div
                style={{
                  backgroundColor: 'var(--bg-color)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  padding: '1rem',
                  marginBottom: '1.25rem',
                }}
              >
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  {t('admin.temp_password_label')}
                </div>
                <div
                  style={{
                    fontFamily: 'monospace',
                    fontSize: '1.1rem',
                    fontWeight: 600,
                    wordBreak: 'break-all',
                    color: 'var(--primary-color)',
                  }}
                >
                  {createdUser.tempPassword}
                </div>
                <button
                  type="button"
                  onClick={copyPassword}
                  style={{
                    marginTop: '0.75rem',
                    width: '100%',
                    padding: '0.5rem',
                    backgroundColor: copied ? '#10b981' : 'var(--primary-color)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    fontWeight: 500,
                  }}
                >
                  {copied ? t('admin.password_copied') : t('admin.copy_password')}
                </button>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem', marginBottom: 0 }}>
                  {t('admin.share_password')}
                </p>
              </div>
            ) : (
              <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', textAlign: 'center', marginBottom: '1.5rem' }}>
                {t('admin.login_immediately')}
              </p>
            )}

            <button
              type="button"
              onClick={handleClose}
              style={{
                width: '100%',
                padding: '0.65rem',
                backgroundColor: 'var(--sidebar-bg)',
                color: 'var(--text-color)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              {t('admin.done_button')}
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
                ➕ {t('admin.create_user_title')}
              </h3>
              <button
                type="button"
                onClick={handleClose}
                style={{
                  background: 'transparent',
                  border: 'none',
                  fontSize: '1.25rem',
                  cursor: 'pointer',
                  color: 'var(--text-muted)',
                }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem' }}>
                  {t('admin.role')} <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as any)}
                  style={{
                    width: '100%',
                    padding: '0.6rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-color)',
                    color: 'var(--text-color)',
                    fontWeight: 500,
                  }}
                >
                  <option value="admin">{t('admin.administrators')}</option>
                  <option value="teacher">{t('admin.teachers')}</option>
                  <option value="student">{t('admin.students')}</option>
                  <option value="parent">{t('admin.parents')}</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem' }}>
                  {t('admin.username')} <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder={t("create_user.username_placeholder")}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.6rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-color)',
                    color: 'var(--text-color)',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem' }}>
                  {t('admin.email')} <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <input
                  type="email"
                  required
                  placeholder={t("create_user.email_placeholder")}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.6rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-color)',
                    color: 'var(--text-color)',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem' }}>
                  {t("admin.full_name")} {t("settings.optional_tag")}
                </label>
                <input
                  type="text"
                  placeholder={t("create_user.fullname_placeholder")}
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.6rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-color)',
                    color: 'var(--text-color)',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem' }}>
                  {t("login.password_label")} {t("settings.optional_tag")}
                </label>
                <input
                  type="password"
                  placeholder={t("create_user.password_placeholder")}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.6rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-color)',
                    color: 'var(--text-color)',
                  }}
                />
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  If empty, a cryptographically secure temporary password will be generated for the user.
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
              <button
                type="button"
                onClick={handleClose}
                disabled={submitting}
                style={{
                  padding: '0.6rem 1.25rem',
                  backgroundColor: 'transparent',
                  color: 'var(--text-muted)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                  fontWeight: 500,
                }}
              >
                {t('common.2')}
              </button>
              <button
                type="submit"
                disabled={submitting}
                style={{
                  padding: '0.6rem 1.5rem',
                  backgroundColor: 'var(--primary-color)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                {submitting ? 'Creating...' : `Create ${role === 'admin' ? 'Administrator' : 'User'}`}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
