import { useState, useEffect, useCallback, useRef } from 'react';
import { X, Mail, Send, CheckCircle, Lock, Trash2, Users, MessageSquare } from 'lucide-react';
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

interface ChatOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ChatOverlay({ isOpen, onClose }: ChatOverlayProps) {
  const { user } = useAuth();
  const { error: showError, success: showSuccess } = useToast();
  const { t } = useI18n();

  const [activeTab, setActiveTab] = useState<'chats' | 'lounge'>('chats');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<DirectMessage[]>([]);
  const [selectedPartner, setSelectedPartner] = useState<string | null>(null);
  const [partnerName, setPartnerName] = useState<string>('');
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  // Lounge Directory
  const [teachers, setTeachers] = useState<DirectoryItem[]>([]);
  const [admins, setAdmins] = useState<DirectoryItem[]>([]);
  const [adminSupportEmail, setAdminSupportEmail] = useState<string | null>(null);

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

  const fetchUnreadCount = useCallback(async () => {
    try {
      const token = getToken();
      if (!token) return;
      const res = await fetch(`${API_URL}/chat/messages/direct/unread-count`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUnreadCount(data.unread_count);
      }
    } catch {
      // silent
    }
  }, []);

  const fetchDirectory = useCallback(async () => {
    try {
      const token = getToken();
      if (!token) return;
      if (user?.role === 'student') {
        const res = await fetch(`${API_URL}/chat/students/available-teachers`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setTeachers(data.teachers || []);
          setAdmins([]);
          setAdminSupportEmail(null);
        } else {
          setTeachers([]);
          setAdmins([]);
        }
        return;
      }
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
      // Students without available teachers → empty
    }
  }, [user?.role]);

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
      } else {
        showError(t('messages.error_load'));
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
        fetchUnreadCount();
      } else {
        const errData = await res.json().catch(() => null);
        showError(errData?.detail || t('messages.error_send'));
      }
    } catch {
      showError(t('messages.error_send'));
    } finally {
      setSending(false);
    }
  }, [newMessage, selectedPartner, showError, t, fetchConversations, fetchUnreadCount]);

  const deleteMessage = async (messageId: string) => {
    if (!window.confirm(t('messages.confirm_delete'))) return;
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
    }
  };

  const startChatWith = (partnerId: string, name: string) => {
    setSelectedPartner(partnerId);
    setPartnerName(name);
    fetchMessages(partnerId);
    setActiveTab('chats');
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      fetchConversations();
      fetchUnreadCount();
      fetchDirectory();
    }
  }, [isOpen, fetchConversations, fetchUnreadCount, fetchDirectory]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  if (!isOpen) return null;

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.4)', zIndex: -1 }} onClick={onClose} />

      <div
        data-pe-modal="true"
        className="pe-modal-surface"
        style={{
          backgroundColor: 'var(--panel-bg, var(--card-bg, #ffffff))',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-lg)',
          width: '720px',
          height: '700px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 60px rgba(0,0,0,0.4)',
          opacity: 1,
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem 1.25rem', borderBottom: '1px solid var(--border-color)', backgroundColor: 'var(--sidebar-bg, #ffffff)', borderTopLeftRadius: 'var(--radius-lg)', borderTopRightRadius: 'var(--radius-lg)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '50%', backgroundColor: 'var(--primary-color)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Mail size={18} />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-color)' }}>{t('messages.title')}</h2>
              <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {unreadCount > 0 ? `${unreadCount} ${t('messages.unread_count')}` : t('messages.encrypted_desc')}
              </p>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <Lock size={14} style={{ color: 'var(--text-muted)' }} />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{t('messages.encryption')}</span>
            </div>
            <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '0.5rem', borderRadius: 'var(--radius-sm)' }}>
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Tab switcher for teachers & admins */}
        {user?.role !== 'student' && (
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)' }}>
            <button
              onClick={() => setActiveTab('chats')}
              style={{
                flex: 1,
                padding: '0.6rem',
                border: 'none',
                borderBottom: activeTab === 'chats' ? '2px solid var(--primary-color)' : 'none',
                backgroundColor: 'transparent',
                color: activeTab === 'chats' ? 'var(--primary-color)' : 'var(--text-muted)',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                fontSize: '0.85rem',
              }}
            >
              <MessageSquare size={16} /> {t('messages.tab_chats')}
            </button>
            <button
              onClick={() => setActiveTab('lounge')}
              style={{
                flex: 1,
                padding: '0.6rem',
                border: 'none',
                borderBottom: activeTab === 'lounge' ? '2px solid var(--primary-color)' : 'none',
                backgroundColor: 'transparent',
                color: activeTab === 'lounge' ? 'var(--primary-color)' : 'var(--text-muted)',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                fontSize: '0.85rem',
              }}
            >
              <Users size={16} /> {t('messages.tab_lounge')}
            </button>
          </div>
        )}

        {/* Content Area */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {activeTab === 'lounge' ? (
            /* Teacher Lounge Directory View */
            <div style={{ flex: 1, padding: '1.25rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Admin Support Email Banner */}
              <div style={{ padding: '0.9rem 1rem', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--bg-color)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-color)' }}>
                    {t('messages.support_email_title')}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {adminSupportEmail ? (
                      <span>{t('messages.support_email_prefix')} <a href={`mailto:${adminSupportEmail}`} style={{ color: 'var(--primary-color)' }}>{adminSupportEmail}</a></span>
                    ) : (
                      <span>{t('messages.support_not_configured')}</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Teachers Directory */}
              <div>
                <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  {t('messages.colleagues')}
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.5rem' }}>
                  {teachers.map((tch) => (
                    <button
                      key={tch.id}
                      onClick={() => startChatWith(tch.id, tch.name)}
                      style={{
                        padding: '0.75rem',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-color)',
                        backgroundColor: 'var(--bg-color)',
                        color: 'var(--text-color)',
                        textAlign: 'left',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.25rem',
                      }}
                    >
                      <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{tch.name}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {tch.is_aide ? t('messages.role_aide') : t('messages.role_teacher')}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Admins Directory */}
              {admins.length > 0 && (
                <div>
                  <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    {t('messages.administrators')}
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.5rem' }}>
                    {admins.map((adm) => (
                      <button
                        key={adm.id}
                        onClick={() => startChatWith(adm.id, adm.name)}
                        style={{
                          padding: '0.75rem',
                          borderRadius: 'var(--radius-md)',
                          border: '1px solid var(--border-color)',
                          backgroundColor: 'var(--bg-color)',
                          color: 'var(--text-color)',
                          textAlign: 'left',
                          cursor: 'pointer',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.25rem',
                        }}
                      >
                        <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{adm.name}</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--primary-color)' }}>{t('messages.role_admin')}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Chats View */
            <>
              {/* Conversation list */}
              <div style={{ width: '260px', borderRight: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column' }}>
                <div style={{ padding: '0.75rem 1rem' }}>
                  <h3 style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    {t('messages.title')}
                  </h3>
                </div>
                <div style={{ flex: 1, overflowY: 'auto', padding: '0.5rem' }}>
                  {user?.role === 'student' ? (
                    teachers.length === 0 ? (
                      <div style={{ padding: '1.5rem 1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        {t('messages.student_empty_desc')}
                      </div>
                    ) : (
                      teachers.map((tch) => {
                        const isSelected = selectedPartner === tch.id;
                        return (
                          <button
                            key={tch.id}
                            onClick={() => startChatWith(tch.id, tch.name)}
                            style={{
                              width: '100%',
                              padding: '0.75rem',
                              border: 'none',
                              backgroundColor: isSelected ? 'var(--primary-color)' : 'transparent',
                              color: isSelected ? '#fff' : 'var(--text-color)',
                              borderRadius: 'var(--radius-md)',
                              cursor: 'pointer',
                              textAlign: 'left',
                              marginBottom: '0.5rem',
                            }}
                          >
                            <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{tch.name}</span>
                          </button>
                        );
                      })
                    )
                  ) : conversations.length === 0 ? (
                    <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                      {t('messages.no_messages')}
                    </div>
                  ) : (
                    conversations.map((conv) => {
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

              {/* Message Thread */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                {!selectedPartner ? (
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    <Mail size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
                    <h3 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--text-color)' }}>{t('messages.no_conversation')}</h3>
                  </div>
                ) : (
                  <>
                    {/* Partner Header */}
                    <div style={{ padding: '0.6rem 1rem', borderBottom: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-color)' }}>{partnerName}</span>
                    </div>

                    <div style={{ flex: 1, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                      {messages.map((msg) => {
                        const isOwn = msg.sender_id === user?.id;
                        return (
                          <div key={msg.id} style={{ display: 'flex', justifyContent: isOwn ? 'flex-end' : 'flex-start', alignItems: 'flex-end', gap: '0.5rem', marginBottom: '0.25rem' }}>
                            <div style={{ maxWidth: '75%', padding: '0.75rem 1rem', borderRadius: isOwn ? 'var(--radius-md) var(--radius-md) 0 var(--radius-md)' : 'var(--radius-md) var(--radius-md) var(--radius-md) 0', backgroundColor: isOwn ? 'var(--primary-color)' : 'var(--bg-color)', color: isOwn ? '#fff' : 'var(--text-color)', border: isOwn ? 'none' : '1px solid var(--border-color)', position: 'relative' }}>
                              <p style={{ margin: 0, fontSize: '0.9rem', lineHeight: 1.4 }}>{msg.content}</p>
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.4rem', marginTop: '0.35rem', fontSize: '0.65rem', color: isOwn ? 'rgba(255,255,255,0.8)' : 'var(--text-muted)' }}>
                                <span>{formatTimeHm(msg.created_at)}</span>
                                {isOwn && msg.is_read && <CheckCircle size={10} />}
                                <button
                                  onClick={() => deleteMessage(msg.id)}
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
                      })}
                      <div ref={messagesEndRef} />
                    </div>

                    <div style={{ padding: '0.75rem 1rem', borderTop: '1px solid var(--border-color)', backgroundColor: 'var(--sidebar-bg)' }}>
                      <form onSubmit={sendMessage} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <input
                          type="text"
                          placeholder={t('messages.type_message')}
                          value={newMessage}
                          onChange={(e) => setNewMessage(e.target.value)}
                          disabled={loading || sending}
                          style={{ flex: 1, padding: '0.7rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.9rem' }}
                        />
                        <button
                          type="submit"
                          disabled={!newMessage.trim() || !selectedPartner || sending}
                          style={{ padding: '0.7rem 1.25rem', borderRadius: 'var(--radius-md)', border: 'none', backgroundColor: 'var(--primary-color)', color: '#fff', cursor: (!newMessage.trim() || !selectedPartner || sending) ? 'not-allowed' : 'pointer', fontSize: '0.9rem', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                        >
                          <Send size={16} /> {t('messages.send')}
                        </button>
                      </form>
                    </div>
                  </>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
