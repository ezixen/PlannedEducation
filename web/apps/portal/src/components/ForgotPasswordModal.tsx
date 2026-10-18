import { useState } from 'react';
import { KeyRound, Send, CheckCircle2, X } from 'lucide-react';
import { apiClient } from '../api';
import { useToast } from '../contexts/ToastContext';

interface ForgotPasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultEmail?: string;
}

export function ForgotPasswordModal({ isOpen, onClose, defaultEmail = '' }: ForgotPasswordModalProps) {
  const { success: showSuccess, error: showError } = useToast();
  const [activeTab, setActiveTab] = useState<'recovery_code' | 'request_supervisor'>('recovery_code');

  // Recovery code tab state
  const [recEmail, setRecEmail] = useState(defaultEmail);
  const [recoveryCode, setRecoveryCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [recSubmitting, setRecSubmitting] = useState(false);
  const [recSuccess, setRecSuccess] = useState(false);

  // Supervisor request tab state
  const [supIdentifier, setSupIdentifier] = useState(defaultEmail);
  const [targetRole, setTargetRole] = useState<'teacher' | 'parent' | 'admin'>('teacher');
  const [supNote, setSupNote] = useState('');
  const [supSubmitting, setSupSubmitting] = useState(false);
  const [supSuccess, setSupSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSelfReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      showError('Passwords do not match');
      return;
    }
    setRecSubmitting(true);
    try {
      await apiClient.post('/auth/password-reset/confirm', {
        email: recEmail.trim().toLowerCase(),
        recovery_code: recoveryCode.trim(),
        new_password: newPassword,
      });
      setRecSuccess(true);
      showSuccess('Password reset successfully! You can now log in.');
    } catch (err: any) {
      showError('Reset failed', err.response?.data?.detail || err.message);
    } finally {
      setRecSubmitting(false);
    }
  };

  const handleSupervisorRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setSupSubmitting(true);
    try {
      await apiClient.post('/notifications/request-password-reset', {
        identifier: supIdentifier.trim(),
        target_role: targetRole,
        note: supNote.trim() || undefined,
      });
      setSupSuccess(true);
      showSuccess('Request sent to supervisor!');
    } catch (err: any) {
      showError('Request failed', err.response?.data?.detail || err.message);
    } finally {
      setSupSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
        zIndex: 1100,
      }}
    >
      <div
        style={{
          backgroundColor: 'var(--sidebar-bg)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-color)',
          width: '100%',
          maxWidth: '520px',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '1rem 1.25rem',
            borderBottom: '1px solid var(--border-color)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            backgroundColor: 'var(--bg-color)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <KeyRound size={20} style={{ color: 'var(--primary-color)' }} />
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-color)' }}>
              Password Recovery & Reset
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-muted)',
              padding: '0.25rem',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Global Warning Notice */}
        <div
          style={{
            margin: '1rem 1.25rem 0.5rem',
            padding: '0.75rem',
            backgroundColor: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid #f59e0b',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.85rem',
            color: '#d97706',
            lineHeight: 1.4,
          }}
        >
          <strong>💡 Saved your recovery codes?</strong> You received 5 one-time recovery codes at registration.
          Unless you have run out of codes, you can reset your password immediately by yourself without waiting for anyone!
        </div>

        {/* Tab Switcher */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)', margin: '0.5rem 1.25rem 0' }}>
          <button
            type="button"
            onClick={() => setActiveTab('recovery_code')}
            style={{
              flex: 1,
              padding: '0.65rem',
              backgroundColor: 'transparent',
              border: 'none',
              borderBottom: activeTab === 'recovery_code' ? '2px solid var(--primary-color)' : '2px solid transparent',
              color: activeTab === 'recovery_code' ? 'var(--primary-color)' : 'var(--text-muted)',
              fontWeight: 600,
              fontSize: '0.875rem',
              cursor: 'pointer',
            }}
          >
            🔑 Use Recovery Code (Instant)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('request_supervisor')}
            style={{
              flex: 1,
              padding: '0.65rem',
              backgroundColor: 'transparent',
              border: 'none',
              borderBottom: activeTab === 'request_supervisor' ? '2px solid var(--primary-color)' : '2px solid transparent',
              color: activeTab === 'request_supervisor' ? 'var(--primary-color)' : 'var(--text-muted)',
              fontWeight: 600,
              fontSize: '0.875rem',
              cursor: 'pointer',
            }}
          >
            🙋 Ask Teacher / Parent
          </button>
        </div>

        {/* Tab 1: Instant Reset with Recovery Code */}
        {activeTab === 'recovery_code' && (
          <div style={{ padding: '1.25rem' }}>
            {recSuccess ? (
              <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
                <CheckCircle2 size={40} style={{ color: '#10b981', marginBottom: '0.75rem' }} />
                <h4 style={{ margin: '0 0 0.5rem', color: 'var(--text-color)' }}>Password Reset Complete!</h4>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                  Your password has been successfully updated. You may now log in with your new password.
                </p>
                <button
                  type="button"
                  onClick={onClose}
                  style={{
                    padding: '0.65rem 1.5rem',
                    backgroundColor: 'var(--primary-color)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  Proceed to Login
                </button>
              </div>
            ) : (
              <form onSubmit={handleSelfReset} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-color)', marginBottom: '0.25rem' }}>
                    Registered Email
                  </label>
                  <input
                    type="email"
                    required
                    value={recEmail}
                    onChange={(e) => setRecEmail(e.target.value)}
                    placeholder="you@school.edu"
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-color)',
                      backgroundColor: 'var(--bg-color)',
                      color: 'var(--text-color)',
                      fontSize: '0.9rem',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-color)', marginBottom: '0.25rem' }}>
                    One-Time Recovery Code
                  </label>
                  <input
                    type="text"
                    required
                    value={recoveryCode}
                    onChange={(e) => setRecoveryCode(e.target.value)}
                    placeholder="e.g. a1b2c3d4"
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-color)',
                      backgroundColor: 'var(--bg-color)',
                      color: 'var(--text-color)',
                      fontFamily: 'monospace',
                      fontSize: '0.95rem',
                      boxSizing: 'border-box',
                    }}
                  />
                  <small style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                    Each code can only be used once.
                  </small>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-color)', marginBottom: '0.25rem' }}>
                      New Password
                    </label>
                    <input
                      type="password"
                      required
                      minLength={8}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="••••••••"
                      style={{
                        width: '100%',
                        padding: '0.6rem',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-color)',
                        backgroundColor: 'var(--bg-color)',
                        color: 'var(--text-color)',
                        fontSize: '0.9rem',
                        boxSizing: 'border-box',
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-color)', marginBottom: '0.25rem' }}>
                      Confirm Password
                    </label>
                    <input
                      type="password"
                      required
                      minLength={8}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="••••••••"
                      style={{
                        width: '100%',
                        padding: '0.6rem',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-color)',
                        backgroundColor: 'var(--bg-color)',
                        color: 'var(--text-color)',
                        fontSize: '0.9rem',
                        boxSizing: 'border-box',
                      }}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={recSubmitting}
                  style={{
                    width: '100%',
                    padding: '0.7rem',
                    backgroundColor: 'var(--primary-color)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    cursor: recSubmitting ? 'not-allowed' : 'pointer',
                    fontWeight: 600,
                    marginTop: '0.5rem',
                  }}
                >
                  {recSubmitting ? 'Resetting...' : 'Reset Password Immediately'}
                </button>
              </form>
            )}
          </div>
        )}

        {/* Tab 2: Request from Supervisor */}
        {activeTab === 'request_supervisor' && (
          <div style={{ padding: '1.25rem' }}>
            {supSuccess ? (
              <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
                <CheckCircle2 size={40} style={{ color: '#10b981', marginBottom: '0.75rem' }} />
                <h4 style={{ margin: '0 0 0.5rem', color: 'var(--text-color)' }}>Request Sent to Supervisor!</h4>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1.5rem', lineHeight: 1.4 }}>
                  Your request has been dispatched. Your teacher, parent, or administrator will receive an in-platform notification with a one-click button to reset your password and provide you with a temporary password.
                </p>
                <button
                  type="button"
                  onClick={onClose}
                  style={{
                    padding: '0.65rem 1.5rem',
                    backgroundColor: 'var(--primary-color)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  Done
                </button>
              </div>
            ) : (
              <form onSubmit={handleSupervisorRequest} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                <div
                  style={{
                    padding: '0.75rem',
                    backgroundColor: 'rgba(239, 68, 68, 0.08)',
                    border: '1px solid #ef4444',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.85rem',
                    color: '#b91c1c',
                    lineHeight: 1.4,
                  }}
                >
                  <strong>⚠️ Before requesting assistance:</strong> Did you check your 5 one-time recovery codes from registration? If you still have them, switch to the <em>🔑 Use Recovery Code</em> tab to reset your password immediately without needing to wait for a teacher or parent!
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-color)', marginBottom: '0.25rem' }}>
                    Your Username or Registered Email
                  </label>
                  <input
                    type="text"
                    required
                    value={supIdentifier}
                    onChange={(e) => setSupIdentifier(e.target.value)}
                    placeholder="username or email@school.edu"
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-color)',
                      backgroundColor: 'var(--bg-color)',
                      color: 'var(--text-color)',
                      fontSize: '0.9rem',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-color)', marginBottom: '0.25rem' }}>
                    Who would you like to request help from?
                  </label>
                  <select
                    value={targetRole}
                    onChange={(e) => setTargetRole(e.target.value as any)}
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-color)',
                      backgroundColor: 'var(--bg-color)',
                      color: 'var(--text-color)',
                      fontSize: '0.9rem',
                      boxSizing: 'border-box',
                    }}
                  >
                    <option value="teacher">My Teacher (Recommended for students)</option>
                    <option value="parent">My Parent (For students with linked parents)</option>
                    <option value="admin">School Administrator (For teachers or general staff)</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-color)', marginBottom: '0.25rem' }}>
                    Optional Message / Note to Supervisor
                  </label>
                  <textarea
                    rows={2}
                    value={supNote}
                    onChange={(e) => setSupNote(e.target.value)}
                    placeholder="e.g. I ran out of recovery codes and cannot access my account for 4th period math."
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-color)',
                      backgroundColor: 'var(--bg-color)',
                      color: 'var(--text-color)',
                      fontSize: '0.85rem',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>

                <button
                  type="submit"
                  disabled={supSubmitting}
                  style={{
                    width: '100%',
                    padding: '0.7rem',
                    backgroundColor: 'var(--primary-color)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    cursor: supSubmitting ? 'not-allowed' : 'pointer',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem',
                    marginTop: '0.5rem',
                  }}
                >
                  <Send size={16} />
                  {supSubmitting ? 'Dispatching Request...' : 'Send Request Inside Platform'}
                </button>
              </form>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
