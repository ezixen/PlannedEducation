import { useState, useEffect, useCallback, useRef } from 'react';
import { X, Mail, Send, CheckCircle, Lock } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { useI18n } from '../contexts/I18nContext';
import { API_URL } from '../api';

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

interface ChatOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ChatOverlay({ isOpen, onClose }: ChatOverlayProps) {
  const { user } = useAuth();
  const { error: showError } = useToast();
  const { t } = useI18n();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<DirectMessage[]>([]);
  const [selectedPartner, setSelectedPartner] = useState<string | null>(null);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchConversations = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/messages/direct`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
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
      const res = await fetch(`${API_URL}/messages/direct/unread-count`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUnreadCount(data.unread_count);
      }
    } catch {
      // silent
    }
  }, []);

  const fetchMessages = useCallback(async (partnerId: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/messages/direct/${partnerId}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
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
      const res = await fetch(`${API_URL}/messages/direct`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
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
        showError(t('messages.error_send'));
      }
    } catch {
      showError(t('messages.error_send'));
    } finally {
      setSending(false);
    }
  }, [newMessage, selectedPartner, showError, t, fetchConversations, fetchUnreadCount]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      fetchConversations();
      fetchUnreadCount();
    }
  }, [isOpen, fetchConversations, fetchUnreadCount]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  if (!isOpen) return null;

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.4)', zIndex: -1 }} onClick={onClose} />

      <div style={{ backgroundColor: 'var(--panel-bg)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', width: '640px', height: '720px', maxHeight: '90vh', display: 'flex', flexDirection: 'column', boxShadow: '0 20px 60px rgba(0,0,0,0.4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem 1.25rem', borderBottom: '1px solid var(--border-color)', backgroundColor: 'var(--sidebar-bg)', borderTopLeftRadius: 'var(--radius-lg)', borderTopRightRadius: 'var(--radius-lg)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '50%', backgroundColor: 'var(--primary-color)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Mail size={18} />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-color)' }}>{t('messages.title')}</h2>
              <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>{unreadCount > 0 ? `${unreadCount} ${t('messages.unread_count')}` : t('messages.encrypted_desc')}</p>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Lock size={14} style={{ color: 'var(--text-muted)' }} />
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{t('messages.encryption')}</span>
            <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '0.5rem', borderRadius: 'var(--radius-sm)' }}>
              <X size={20} />
            </button>
          </div>
        </div>

        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          <div style={{ width: '260px', borderRight: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '0.75rem 1rem' }}>
              <h3 style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{t('messages.title')}</h3>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '0.5rem' }}>
              {conversations.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.9rem' }}>{t('messages.no_messages')}</div>
              ) : (
                conversations.map((conv) => (
                  <button key={conv.id} onClick={() => { const partnerId = conv.sender_id === user?.id ? conv.recipient_id : conv.sender_id; setSelectedPartner(partnerId); fetchMessages(partnerId); }} style={{ width: '100%', padding: '0.75rem', border: 'none', backgroundColor: selectedPartner === (conv.sender_id === user?.id ? conv.recipient_id : conv.sender_id) ? 'var(--primary-color)' : 'transparent', color: selectedPartner === (conv.sender_id === user?.id ? conv.recipient_id : conv.sender_id) ? '#fff' : 'var(--text-color)', borderRadius: 'var(--radius-md)', cursor: 'pointer', textAlign: 'left', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{conv.sender_name || conv.recipient_name}</span>
                        {!conv.is_read && (
                          <span style={{ fontSize: '0.7rem', backgroundColor: 'var(--primary-color)', color: '#fff', padding: '0.1rem 0.4rem', borderRadius: '10px' }}>new</span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', width: '200px' }}>{conv.content_preview || t('messages.no_messages')}</div>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{new Date(conv.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                  </button>
                ))
              )}
            </div>
          </div>

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            {!selectedPartner ? (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                <Mail size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
                <h3 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--text-color)' }}>{t('messages.no_conversation')}</h3>
              </div>
            ) : (
              <>
                <div style={{ flex: 1, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {messages.map((msg) => {
                    const isOwn = msg.sender_id === user?.id;
                    return (
                      <div key={msg.id} style={{ display: 'flex', justifyContent: isOwn ? 'flex-end' : 'flex-start', alignItems: 'flex-end', gap: '0.5rem', marginBottom: '0.25rem' }}>
                        {!isOwn && (
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{msg.sender_name}</span>
                        )}
                        <div style={{ maxWidth: '75%', padding: '0.75rem 1rem', borderRadius: isOwn ? 'var(--radius-md) var(--radius-md) 0 var(--radius-md)' : 'var(--radius-md) var(--radius-md) var(--radius-md) 0', backgroundColor: isOwn ? 'var(--primary-color)' : 'var(--bg-color)', color: isOwn ? '#fff' : 'var(--text-color)', border: isOwn ? 'none' : '1px solid var(--border-color)', position: 'relative' }}>
                          <p style={{ margin: 0, fontSize: '0.9rem', lineHeight: 1.4 }}>{msg.content}</p>
                          <div style={{ position: 'absolute', bottom: -18, right: isOwn ? 4 : 'auto', left: !isOwn ? 4 : 'auto', fontSize: '0.65rem', color: isOwn ? 'rgba(255,255,255,0.7)' : 'var(--text-muted)' }}>
                            {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            {isOwn && msg.is_read && (
                              <span style={{ marginLeft: '0.25rem' }}>
                                <CheckCircle size={10} />
                              </span>
                            )}
                          </div>
                        </div>
                        {isOwn && (
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{msg.sender_name}</span>
                        )}
                      </div>
                    );
                  })}
                  <div ref={messagesEndRef} />
                </div>

                <div style={{ padding: '1rem', borderTop: '1px solid var(--border-color)', backgroundColor: 'var(--sidebar-bg)', borderBottomLeftRadius: 'var(--radius-md)' }}>
                  <form onSubmit={sendMessage} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <input type="text" placeholder={t('messages.type_message')} value={newMessage} onChange={(e) => setNewMessage(e.target.value)} disabled={loading || sending} style={{ flex: 1, padding: '0.7rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.9rem' }} />
                    <button type="submit" disabled={!newMessage.trim() || !selectedPartner || sending} style={{ padding: '0.7rem 1.25rem', borderRadius: 'var(--radius-md)', border: 'none', backgroundColor: 'var(--primary-color)', color: '#fff', cursor: (!newMessage.trim() || !selectedPartner || sending) ? 'not-allowed' : 'pointer', fontSize: '0.9rem', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Send size={16} /> {t('messages.send')}
                    </button>
                  </form>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}