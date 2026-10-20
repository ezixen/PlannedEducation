import { useState, useEffect, useRef } from 'react';
import { Bell, Check, Trash2, UserCheck, KeyRound, CheckCheck, RefreshCw } from 'lucide-react';
import { apiClient } from '../api';
import { useToast } from '../contexts/ToastContext';
import { useI18n } from '../contexts/I18nContext';

export interface InAppNotification {
  id: string;
  user_id: string;
  title: string;
  message: string;
  type: string;
  is_read: boolean;
  link?: string | null;
  action_payload?: string | null;
  created_at: string;
}

export function NotificationBell() {
  const { success: showSuccess, error: showError } = useToast();
  const { t } = useI18n();
  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [notifications, setNotifications] = useState<InAppNotification[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [approvedPassResult, setApprovedPassResult] = useState<{ notifId: string; tempPass: string; username: string } | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Poll unread count every 60 seconds (1 minute)
  const fetchUnreadCount = async () => {
    try {
      const res = await apiClient.get('/notifications/unread-count');
      setUnreadCount(res.data.unread_count || 0);
    } catch {
      // Suppress background polling errors silently
    }
  };

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/notifications');
      setNotifications(res.data);
      // Recalculate unread count
      const count = res.data.filter((n: InAppNotification) => !n.is_read).length;
      setUnreadCount(count);
    } catch (err: any) {
      showError('Failed to load notifications', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 60000); // 60s poller
    return () => clearInterval(interval);
  }, []);

  // When dropdown opens, fetch latest notifications
  const handleToggle = () => {
    if (!isOpen) {
      fetchNotifications();
    }
    setIsOpen(!isOpen);
  };

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleMarkAsRead = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiClient.patch(`/notifications/${id}/read`);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err: any) {
      showError('Could not update notification', err.message);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await apiClient.post('/notifications/mark-all-read');
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
      showSuccess('All notifications marked as read');
    } catch (err: any) {
      showError('Failed to mark all as read', err.message);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiClient.delete(`/notifications/${id}`);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      fetchUnreadCount();
    } catch (err: any) {
      showError('Could not delete notification', err.message);
    }
  };

  const handleApproveTeacher = async (notif: InAppNotification, e: React.MouseEvent) => {
    e.stopPropagation();
    setActionLoadingId(notif.id);
    try {
      await apiClient.post(`/notifications/approve-teacher/${notif.id}`);
      showSuccess('Teacher account approved successfully!');
      setNotifications((prev) =>
        prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err: any) {
      showError('Failed to approve teacher', err.response?.data?.detail || err.message);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleApprovePasswordReset = async (notif: InAppNotification, e: React.MouseEvent) => {
    e.stopPropagation();
    setActionLoadingId(notif.id);
    try {
      const res = await apiClient.post(`/notifications/approve-password-reset/${notif.id}`, {});
      const tempPass = res.data.temporary_password;
      let username = 'User';
      if (notif.action_payload) {
        try {
          username = JSON.parse(notif.action_payload).requester_username || 'User';
        } catch {
          // ignore
        }
      }
      setApprovedPassResult({ notifId: notif.id, tempPass, username });
      showSuccess('Password reset approved! Temporary password generated.');
      setNotifications((prev) =>
        prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err: any) {
      showError('Failed to approve password reset', err.response?.data?.detail || err.message);
    } finally {
      setActionLoadingId(null);
    }
  };

  return (
    <div ref={dropdownRef} style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={handleToggle}
        aria-label={t("notifications.title")}
        title="Notifications (updates every minute)"
        style={{
          position: 'relative',
          background: 'var(--sidebar-bg)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          padding: '0.45rem',
          cursor: 'pointer',
          color: 'var(--text-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'background-color 0.15s ease',
        }}
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span
            style={{
              position: 'absolute',
              top: '-4px',
              right: '-4px',
              backgroundColor: '#ef4444',
              color: '#ffffff',
              fontSize: '0.7rem',
              fontWeight: 700,
              minWidth: '18px',
              height: '18px',
              borderRadius: '9999px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '0 4px',
              boxShadow: '0 1px 2px rgba(0,0,0,0.2)',
            }}
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div
          style={{
            position: 'absolute',
            right: 0,
            marginTop: '0.5rem',
            width: '360px',
            maxWidth: 'calc(100vw - 2rem)',
            maxHeight: '480px',
            backgroundColor: 'var(--sidebar-bg)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.2), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: '0.75rem 1rem',
              borderBottom: '1px solid var(--border-color)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              backgroundColor: 'var(--bg-color)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-color)' }}>
                Notifications
              </span>
              {unreadCount > 0 && (
                <span
                  style={{
                    backgroundColor: 'rgba(239, 68, 68, 0.15)',
                    color: '#ef4444',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    padding: '0.1rem 0.4rem',
                    borderRadius: '9999px',
                  }}
                >
                  {unreadCount} new
                </span>
              )}
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                onClick={fetchNotifications}
                title="Refresh"
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--text-muted)',
                  padding: '0.2rem',
                }}
              >
                <RefreshCw size={14} className={loading ? 'spin' : ''} />
              </button>
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  title={t("notifications.mark_all_read")}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--primary-color)',
                    fontSize: '0.75rem',
                    fontWeight: 500,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.2rem',
                  }}
                >
                  <CheckCheck size={14} /> {t("notifications.mark_all_read")}
                </button>
              )}
            </div>
          </div>

          {/* Result Banner if a temporary password was just generated */}
          {approvedPassResult && (
            <div
              style={{
                margin: '0.5rem 0.75rem',
                padding: '0.6rem 0.75rem',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid #10b981',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.8rem',
                color: 'var(--text-color)',
              }}
            >
              <div style={{ fontWeight: 600, color: '#10b981', marginBottom: '0.2rem' }}>
                ✓ Temporary Password Generated
              </div>
              <div>
                User: <strong>{approvedPassResult.username}</strong>
              </div>
              <div style={{ marginTop: '0.25rem' }}>
                Password:{' '}
                <code
                  style={{
                    backgroundColor: 'var(--bg-color)',
                    padding: '0.2rem 0.4rem',
                    borderRadius: '4px',
                    fontWeight: 700,
                    fontSize: '0.85rem',
                  }}
                >
                  {approvedPassResult.tempPass}
                </code>
              </div>
              <button
                onClick={() => setApprovedPassResult(null)}
                style={{
                  marginTop: '0.4rem',
                  fontSize: '0.75rem',
                  padding: '0.2rem 0.5rem',
                  background: 'none',
                  border: '1px solid var(--border-color)',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  color: 'var(--text-muted)',
                }}
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Notification List */}
          <div style={{ overflowY: 'auto', flex: 1, padding: '0.25rem 0' }}>
            {loading && notifications.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                {t("common.14")}
              </div>
            ) : notifications.length === 0 ? (
              <div style={{ padding: '2.5rem 1rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                <Bell size={28} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
                <p style={{ margin: 0, fontSize: '0.85rem' }}>{t("notifications.empty")}</p>
                <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', opacity: 0.8 }}>
                  Updates poll every minute automatically.
                </p>
              </div>
            ) : (
              notifications.map((notif) => {
                const isTeacherApproval = notif.type === 'teacher_approval';
                const isPasswordReset = notif.type === 'password_reset_request';

                return (
                  <div
                    key={notif.id}
                    style={{
                      padding: '0.75rem 1rem',
                      borderBottom: '1px solid var(--border-color)',
                      backgroundColor: notif.is_read ? 'transparent' : 'rgba(37, 99, 235, 0.04)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.35rem',
                      transition: 'background-color 0.15s',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        {!notif.is_read && (
                          <span
                            style={{
                              width: '6px',
                              height: '6px',
                              borderRadius: '50%',
                              backgroundColor: 'var(--primary-color)',
                              flexShrink: 0,
                            }}
                          />
                        )}
                        <span
                          style={{
                            fontWeight: notif.is_read ? 500 : 700,
                            fontSize: '0.85rem',
                            color: 'var(--text-color)',
                          }}
                        >
                          {notif.title}
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', flexShrink: 0 }}>
                        {!notif.is_read && (
                          <button
                            onClick={(e) => handleMarkAsRead(notif.id, e)}
                            title="Mark as read"
                            style={{
                              background: 'none',
                              border: 'none',
                              cursor: 'pointer',
                              color: 'var(--text-muted)',
                              padding: '0.15rem',
                            }}
                          >
                            <Check size={13} />
                          </button>
                        )}
                        <button
                          onClick={(e) => handleDelete(notif.id, e)}
                          title="Delete"
                          style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            color: 'var(--text-muted)',
                            padding: '0.15rem',
                          }}
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>

                    <p
                      style={{
                        margin: 0,
                        fontSize: '0.8rem',
                        color: 'var(--text-muted)',
                        lineHeight: 1.4,
                      }}
                    >
                      {notif.message}
                    </p>

                    {/* Interactive Action Buttons */}
                    {isTeacherApproval && !notif.is_read && (
                      <div style={{ marginTop: '0.35rem' }}>
                        <button
                          onClick={(e) => handleApproveTeacher(notif, e)}
                          disabled={actionLoadingId === notif.id}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.3rem',
                            padding: '0.3rem 0.6rem',
                            backgroundColor: '#10b981',
                            color: '#ffffff',
                            border: 'none',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          <UserCheck size={13} />
                          {actionLoadingId === notif.id ? 'Approving...' : 'Approve Teacher Status'}
                        </button>
                      </div>
                    )}

                    {isPasswordReset && !notif.is_read && (
                      <div style={{ marginTop: '0.35rem' }}>
                        <button
                          onClick={(e) => handleApprovePasswordReset(notif, e)}
                          disabled={actionLoadingId === notif.id}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.3rem',
                            padding: '0.3rem 0.6rem',
                            backgroundColor: 'var(--primary-color)',
                            color: '#ffffff',
                            border: 'none',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          <KeyRound size={13} />
                          {actionLoadingId === notif.id ? t("common.14") : t("notifications.reset_approve_btn")}
                        </button>
                      </div>
                    )}

                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', opacity: 0.75, marginTop: '0.1rem' }}>
                      {new Date(notif.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })},{' '}
                      {new Date(notif.created_at).toLocaleDateString()}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}

