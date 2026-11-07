import { useState, useEffect, useCallback, useRef } from 'react';
import { Mail, Send, CheckCircle, Lock, Trash2, Users, AlertCircle, RefreshCw } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { useI18n } from '../contexts/I18nContext';
import { API_URL } from '../api';
import { formatTimeHm } from '../lib/dateTime';

interface DirectMessage {
  id: string;
  sender_id: string;
  recipient_id: string;
  sender_name: string;
  recipient_name: string;
  content: string;
  is_read: boolean;
  deleted_by_sender: boolean;
  deleted_by_recipient: boolean;
  created_at: string;
  updated_at: string;
}

interface Conversation {
  id: string;
  sender_id: string;
  recipient_id: string;
  sender_name: string;
  recipient_name: string;
  content_preview: string | null;
  is_read: boolean;
  created_at: string;
}

interface DirectoryItem {
  id: string;
  name: string;
  role: string;
  email: string | null;
  is_aide: boolean;
}

export function Messages() {
  const { user } = useAuth();
  const { error: showError, success: showSuccess } = useToast();
  const { t } = useI18n();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<DirectMessage[]>([]);
  const [selectedPartner, setSelectedPartner] = useState<string | null>(null);
  const [partnerName, setPartnerName] = useState<string>('');
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);

  // Directory for staff; available teachers for students (opt-in + class)
  const [teachers, setTeachers] = useState<DirectoryItem[]>([]);
  const [admins, setAdmins] = useState<DirectoryItem[]>([]);
  const [availableTeachers, setAvailableTeachers] = useState<DirectoryItem[]>([]);
  const [adminSupportEmail, setAdminSupportEmail] = useState<string | null>(null);
  const [showDirectory, setShowDirectory] = useState(false);
  const isStudent = user?.role === 'student';

  // Confirmation Modal
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [confirmClearChat, setConfirmClearChat] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const getToken = () =>
    sessionStorage.getItem('access_token') || '';

  const fetchConversations = useCallback(async () => {
    try {
      const token = getToken();
      if (!token) return;
      const res = await fetch(`${API_URL}/chat/messages/direct`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch {
      showError(t('messages.error_load'));
    }
  }, [showError, t]);

  const fetchDirectory = useCallback(async () => {
    try {
      const token = getToken();
      if (!token) return;
      const res = await fetch(`${API_URL}/chat/teachers-lounge/directory`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setTeachers(data.teachers || []);
        setAdmins(data.admins || []);
        setAdminSupportEmail(data.admin_support_email || null);
      }
    } catch {
      // Students 403 on staff lounge directory
    }
  }, []);

  const fetchAvailableTeachers = useCallback(async () => {
    try {
      const token = getToken();
      if (!token) return;
      const res = await fetch(`${API_URL}/chat/students/available-teachers`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAvailableTeachers(data.teachers || []);
      } else {
        setAvailableTeachers([]);
      }
    } catch {
      setAvailableTeachers([]);
    }
  }, []);

  const fetchMessages = useCallback(async (partnerId: string) => {
    setLoading(true);
    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/chat/messages/direct/${partnerId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch {
      showError(t('messages.error_load'));
    } finally {
      setLoading(false);
    }
  }, [showError, t]);

  const sendMessage = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedPartner) return;
    setSending(true);
    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/chat/messages/direct`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          recipient_id: selectedPartner,
          content: newMessage.trim(),
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setMessages((prev) => [...prev, data]);
        setNewMessage('');
        fetchConversations();
      } else {
        const err = await res.json().catch(() => null);
        showError(err?.detail || t('messages.error_send'));
      }
    } catch {
      showError(t('messages.error_send'));
    } finally {
      setSending(false);
    }
  }, [newMessage, selectedPartner, showError, t, fetchConversations]);

  const handleDeleteMessage = async (messageId: string) => {
    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/chat/messages/direct/${messageId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setMessages((prev) => prev.filter((m) => m.id !== messageId));
        showSuccess(t('messages.deleted'));
        fetchConversations();
      }
    } catch {
      showError(t('messages.error_delete'));
    } finally {
      setConfirmDeleteId(null);
    }
  };

  const handleClearChat = async () => {
    for (const msg of messages) {
      try {
        const token = getToken();
        await fetch(`${API_URL}/chat/messages/direct/${msg.id}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {
        // continue
      }
    }
    setMessages([]);
    setConfirmClearChat(false);
    showSuccess(t('messages.history_cleared'));
    fetchConversations();
  };

  const startChatWith = (partnerId: string, name: string) => {
    setSelectedPartner(partnerId);
    setPartnerName(name);
    fetchMessages(partnerId);
    setShowDirectory(false);
  };

  useEffect(() => {
    fetchConversations();
    if (isStudent) {
      fetchAvailableTeachers();
    } else {
      fetchDirectory();
    }
  }, [fetchConversations, fetchDirectory, fetchAvailableTeachers, isStudent]);

  const availableTeacherIds = new Set(availableTeachers.map((t) => t.id));
  const studentConversations = isStudent
    ? conversations.filter((conv) => {
        const partnerId = conv.sender_id === user?.id ? conv.recipient_id : conv.sender_id;
        return availableTeacherIds.has(partnerId);
      })
    : conversations;
  const studentPageEmpty =
    isStudent && availableTeachers.length === 0 && studentConversations.length === 0;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '1.5rem' }}>
      {/* Page Title & Status */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ width: '42px', height: '42px', borderRadius: '50%', backgroundColor: 'var(--primary-color)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Mail size={22} />
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--text-color)' }}>
              {t('messages.title')}
            </h1>
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              {t('messages.encrypted_desc')}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            <Lock size={15} />
            <span>{t('messages.encrypted_at_rest')}</span>
          </div>
          {!isStudent && (
            <button
              onClick={() => setShowDirectory(!showDirectory)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem 1rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)',
                backgroundColor: showDirectory ? 'var(--primary-color)' : 'var(--panel-bg)',
                color: showDirectory ? '#fff' : 'var(--text-color)',
                cursor: 'pointer',
                fontWeight: 500,
                fontSize: '0.85rem',
              }}
            >
              <Users size={16} />
              {t('messages.tab_lounge')}
            </button>
          )}
        </div>
      </div>

      {studentPageEmpty && (
        <div
          style={{
            padding: '3rem 1.5rem',
            textAlign: 'center',
            backgroundColor: 'var(--panel-bg)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-muted)',
          }}
        >
          <Mail size={48} style={{ opacity: 0.35, marginBottom: '1rem' }} />
          <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.2rem', color: 'var(--text-color)' }}>
            {t('messages.student_empty_title')}
          </h2>
          <p style={{ margin: 0, maxWidth: '420px', marginInline: 'auto', fontSize: '0.9rem' }}>
            {t('messages.student_empty_desc')}
          </p>
        </div>
      )}

      {/* Admin Support Email Banner */}
      {adminSupportEmail && (
        <div style={{ marginBottom: '1rem', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-color)' }}>
            <strong>{t('messages.support_email_title')}:</strong> {t('messages.support_admin_banner')}{' '}
            <a href={`mailto:${adminSupportEmail}`} style={{ color: 'var(--primary-color)', fontWeight: 600 }}>{adminSupportEmail}</a>
          </div>
        </div>
      )}

      {/* Main Grid — hidden for students when no opted-in class teachers */}
      {!studentPageEmpty && (
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '1.5rem', height: '650px', backgroundColor: 'var(--panel-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
        {/* Left Column: Conversations or Directory */}
        <div style={{ borderRight: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', backgroundColor: 'var(--sidebar-bg)' }}>
            <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-color)' }}>
              {isStudent
                ? t('messages.available_teachers')
                : showDirectory
                  ? t('messages.directory_title')
                  : t('messages.conversations')}
            </span>
            <button
              onClick={() => {
                fetchConversations();
                if (isStudent) fetchAvailableTeachers();
                else fetchDirectory();
              }}
              title={t('messages.refresh')}
              aria-label={t('messages.refresh')}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '0.25rem' }}
            >
              <RefreshCw size={15} />
            </button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '0.75rem' }}>
            {isStudent ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {availableTeachers.length === 0 ? (
                  <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                    {t('messages.no_available_teachers')}
                  </div>
                ) : (
                  availableTeachers.map((tch) => (
                    <button
                      key={tch.id}
                      onClick={() => startChatWith(tch.id, tch.name)}
                      style={{
                        padding: '0.65rem 0.75rem',
                        borderRadius: 'var(--radius-md)',
                        border: selectedPartner === tch.id ? '1px solid var(--primary-color)' : '1px solid var(--border-color)',
                        backgroundColor: selectedPartner === tch.id ? 'var(--primary-color)' : 'var(--bg-color)',
                        color: selectedPartner === tch.id ? '#fff' : 'var(--text-color)',
                        textAlign: 'left',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.2rem',
                      }}
                    >
                      <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{tch.name}</span>
                      <span style={{ fontSize: '0.75rem', opacity: 0.85 }}>
                        {tch.is_aide ? t('messages.role_aide') : t('messages.role_teacher')}
                      </span>
                    </button>
                  ))
                )}
              </div>
            ) : showDirectory ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{t('messages.colleagues')}</span>
                {teachers.map((tch) => (
                  <button
                    key={tch.id}
                    onClick={() => startChatWith(tch.id, tch.name)}
                    style={{
                      padding: '0.65rem 0.75rem',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-color)',
                      backgroundColor: 'var(--bg-color)',
                      color: 'var(--text-color)',
                      textAlign: 'left',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.2rem',
                    }}
                  >
                    <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{tch.name}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{tch.is_aide ? t('messages.role_aide') : t('messages.role_teacher')}</span>
                  </button>
                ))}

                {admins.length > 0 && (
                  <>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: '0.5rem' }}>{t('messages.administrators')}</span>
                    {admins.map((adm) => (
                      <button
                        key={adm.id}
                        onClick={() => startChatWith(adm.id, adm.name)}
                        style={{
                          padding: '0.65rem 0.75rem',
                          borderRadius: 'var(--radius-md)',
                          border: '1px solid var(--border-color)',
                          backgroundColor: 'var(--bg-color)',
                          color: 'var(--text-color)',
                          textAlign: 'left',
                          cursor: 'pointer',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.2rem',
                        }}
                      >
                        <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{adm.name}</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--primary-color)' }}>{t('messages.role_admin')}</span>
                      </button>
                    ))}
                  </>
                )}
              </div>
            ) : studentConversations.length === 0 ? (
              <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                {t('messages.no_messages')}
              </div>
            ) : (
              studentConversations.map((conv) => {
                const partnerId = conv.sender_id === user?.id ? conv.recipient_id : conv.sender_id;
                const displayName = conv.sender_id === user?.id ? conv.recipient_name : conv.sender_name;
                const isSelected = selectedPartner === partnerId;
                return (
                  <button
                    key={conv.id}
                    onClick={() => {
                      setSelectedPartner(partnerId);
                      setPartnerName(displayName);
                      fetchMessages(partnerId);
                    }}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: 'none',
                      backgroundColor: isSelected ? 'var(--primary-color)' : 'transparent',
                      color: isSelected ? '#fff' : 'var(--text-color)',
                      borderRadius: 'var(--radius-md)',
                      cursor: 'pointer',
                      textAlign: 'left',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.25rem',
                      marginBottom: '0.5rem',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{displayName}</span>
                      {!conv.is_read && (
                        <span style={{ fontSize: '0.7rem', backgroundColor: isSelected ? '#fff' : 'var(--primary-color)', color: isSelected ? 'var(--primary-color)' : '#fff', padding: '0.1rem 0.4rem', borderRadius: '10px' }}>
                          {t('messages.badge_new')}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: isSelected ? 'rgba(255,255,255,0.8)' : 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {conv.content_preview || t('messages.no_messages')}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Chat History & Send Box */}
        <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {!selectedPartner ? (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
              <Mail size={56} style={{ opacity: 0.3, marginBottom: '1rem' }} />
              <h3 style={{ margin: 0, fontSize: '1.15rem', color: 'var(--text-color)' }}>
                {t('messages.select_conversation')}
              </h3>
            </div>
          ) : (
            <>
              {/* Partner Header with Clear Chat action */}
              <div style={{ padding: '0.75rem 1.25rem', borderBottom: '1px solid var(--border-color)', backgroundColor: 'var(--sidebar-bg)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text-color)' }}>{partnerName}</span>
                <button
                  onClick={() => setConfirmClearChat(true)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                    padding: '0.35rem 0.75rem',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'transparent',
                    color: 'var(--error-color)',
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                  }}
                >
                  <Trash2 size={13} />
                  {t('messages.clear_chat')}
                </button>
              </div>

              {/* Messages View */}
              <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {messages.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                    {t('messages.no_messages_in_conversation')}
                  </div>
                ) : (
                  messages.map((msg) => {
                    const isOwn = msg.sender_id === user?.id;
                    return (
                      <div key={msg.id} style={{ display: 'flex', justifyContent: isOwn ? 'flex-end' : 'flex-start', alignItems: 'flex-end', gap: '0.5rem', marginBottom: '0.25rem' }}>
                        <div style={{ maxWidth: '75%', padding: '0.75rem 1rem', borderRadius: isOwn ? 'var(--radius-md) var(--radius-md) 0 var(--radius-md)' : 'var(--radius-md) var(--radius-md) var(--radius-md) 0', backgroundColor: isOwn ? 'var(--primary-color)' : 'var(--bg-color)', color: isOwn ? '#fff' : 'var(--text-color)', border: isOwn ? 'none' : '1px solid var(--border-color)', position: 'relative' }}>
                          <p style={{ margin: 0, fontSize: '0.9rem', lineHeight: 1.4 }}>{msg.content}</p>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.4rem', marginTop: '0.35rem', fontSize: '0.65rem', color: isOwn ? 'rgba(255,255,255,0.8)' : 'var(--text-muted)' }}>
                            <span>{formatTimeHm(msg.created_at)}</span>
                            {isOwn && msg.is_read && <CheckCircle size={10} />}
                            <button
                              onClick={() => setConfirmDeleteId(msg.id)}
                              title={t('messages.delete_message_title')}
                              aria-label={t('messages.delete_message_title')}
                              style={{ background: 'none', border: 'none', color: isOwn ? 'rgba(255,255,255,0.8)' : 'var(--text-muted)', cursor: 'pointer', padding: '0 2px' }}
                            >
                              <Trash2 size={11} />
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Send Form */}
              <div style={{ padding: '1rem', borderTop: '1px solid var(--border-color)', backgroundColor: 'var(--sidebar-bg)' }}>
                <form onSubmit={sendMessage} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <input
                    type="text"
                    placeholder={t('messages.type_message')}
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    disabled={loading || sending}
                    style={{ flex: 1, padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.9rem' }}
                  />
                  <button
                    type="submit"
                    disabled={!newMessage.trim() || !selectedPartner || sending}
                    style={{ padding: '0.75rem 1.5rem', borderRadius: 'var(--radius-md)', border: 'none', backgroundColor: 'var(--primary-color)', color: '#fff', cursor: (!newMessage.trim() || !selectedPartner || sending) ? 'not-allowed' : 'pointer', fontSize: '0.9rem', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                  >
                    <Send size={16} /> {t('messages.send')}
                  </button>
                </form>
              </div>
            </>
          )}
        </div>
      </div>
      )}

      {/* Confirmation Modal for Individual Delete */}
      {confirmDeleteId && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 3000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)' }} onClick={() => setConfirmDeleteId(null)} />
          <div style={{ backgroundColor: 'var(--panel-bg)', borderRadius: 'var(--radius-md)', padding: '1.5rem', width: '380px', zIndex: 3001, boxShadow: '0 10px 40px rgba(0,0,0,0.3)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--error-color)', marginBottom: '0.75rem' }}>
              <AlertCircle size={20} />
              <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-color)' }}>{t('messages.delete_confirm_title')}</h3>
            </div>
            <p style={{ margin: '0 0 1.25rem 0', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              {t('messages.delete_confirm_desc')}
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button
                onClick={() => setConfirmDeleteId(null)}
                style={{ padding: '0.5rem 1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', backgroundColor: 'transparent', color: 'var(--text-color)', cursor: 'pointer' }}
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={() => handleDeleteMessage(confirmDeleteId)}
                style={{ padding: '0.5rem 1rem', borderRadius: 'var(--radius-sm)', border: 'none', backgroundColor: 'var(--error-color)', color: '#fff', cursor: 'pointer', fontWeight: 600 }}
              >
                {t('common.delete')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal for Clear Chat History */}
      {confirmClearChat && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 3000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)' }} onClick={() => setConfirmClearChat(false)} />
          <div style={{ backgroundColor: 'var(--panel-bg)', borderRadius: 'var(--radius-md)', padding: '1.5rem', width: '380px', zIndex: 3001, boxShadow: '0 10px 40px rgba(0,0,0,0.3)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--error-color)', marginBottom: '0.75rem' }}>
              <AlertCircle size={20} />
              <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-color)' }}>{t('messages.clear_confirm_title')}</h3>
            </div>
            <p style={{ margin: '0 0 1.25rem 0', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              {t('messages.clear_confirm_desc')}
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button
                onClick={() => setConfirmClearChat(false)}
                style={{ padding: '0.5rem 1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', backgroundColor: 'transparent', color: 'var(--text-color)', cursor: 'pointer' }}
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleClearChat}
                style={{ padding: '0.5rem 1rem', borderRadius: 'var(--radius-sm)', border: 'none', backgroundColor: 'var(--error-color)', color: '#fff', cursor: 'pointer', fontWeight: 600 }}
              >
                {t('messages.clear_history_btn')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
