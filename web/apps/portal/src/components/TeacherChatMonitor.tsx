import { useState, useEffect, useRef, useCallback } from 'react';
import { MessageSquare, Send } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { useI18n } from '../contexts/I18nContext';
import { API_URL } from '../api';

interface ChatMessage {
  id: string;
  sender: string;
  message: string;
  timestamp: Date;
  isOwn: boolean;
}

interface TeacherChatMonitorProps {
  examId: string;
  examTitle?: string;
}

export function TeacherChatMonitor({ examId, examTitle }: TeacherChatMonitorProps) {
  const { user } = useAuth();
  const { info: showInfo } = useToast();
  const { t } = useI18n();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const [replyText, setReplyText] = useState<string>('');

  const ws = useRef<WebSocket | null>(null);

  // Connect to the exam WebSocket room
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token || !examId) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = API_URL.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}//${host}/chat/exam/${examId}`;

    const socket = new WebSocket(wsUrl);
    ws.current = socket;

    socket.onopen = () => {
      // Authenticate inside WebSocket frame
      socket.send(JSON.stringify({ token }));
      setConnected(true);
    };

    socket.onmessage = (event: MessageEvent) => {
      try {
        const data: { sender: string; message: string } = JSON.parse(event.data);
        const myName = user?.full_name || user?.username;

        // If the message is from a student (not from this teacher)
        if (data.sender && data.sender !== myName) {
          const newEntry: ChatMessage = {
            id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
            sender: data.sender,
            message: data.message,
            timestamp: new Date(),
            isOwn: false,
          };

          setMessages(prev => [...prev, newEntry]);
          showInfo(`💬 New message from ${data.sender}: "${data.message}"`, { sticky: true });
        } else if (data.sender === myName) {
          // Our own message echoed back
          const newEntry: ChatMessage = {
            id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
            sender: data.sender,
            message: data.message,
            timestamp: new Date(),
            isOwn: true,
          };
          setMessages(prev => [...prev, newEntry]);
        }
      } catch {
        // Ignore non-json frames
      }
    };

    socket.onclose = () => setConnected(false);
    socket.onerror = () => setConnected(false);

    return () => {
      socket.close();
    };
  }, [examId, user]);

  const handleSendMessage = useCallback(() => {
    const text = replyText.trim();
    if (!text || !ws.current || ws.current.readyState !== WebSocket.OPEN) return;

    // Send the message to the exam room
    ws.current.send(text);

    // Add to local messages immediately (optimistic update)
    const newEntry: ChatMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      sender: user?.full_name || user?.username || 'You',
      message: text,
      timestamp: new Date(),
      isOwn: true,
    };
    setMessages(prev => [...prev, newEntry]);
    setReplyText('');
  }, [replyText]);

  const unreadCount = messages.filter(m => !m.isOwn).length;

  return (
    <div style={{
      padding: '1.25rem',
      backgroundColor: 'var(--sidebar-bg)',
      borderRadius: 'var(--radius-lg)',
      border: '1px solid var(--border-color)',
      marginBottom: '1.5rem',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            width: 34, height: 34, borderRadius: 'var(--radius-md)',
            backgroundColor: 'var(--primary-color)',
            color: '#fff',
          }}>
            <MessageSquare size={18} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-color)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              {t('teacher_dashboard.chat_title', 'Chat with Students')}
              {examTitle && <span style={{ fontSize: '0.85rem', fontWeight: 400, color: 'var(--text-muted)' }}>({examTitle})</span>}
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              End-to-end encrypted chat with students
            </span>
          </div>
        </div>

        {/* Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{
            display: 'flex', alignItems: 'center', gap: '0.35rem',
            fontSize: '0.8rem', color: connected ? '#10b981' : '#ef4444',
            fontWeight: 500,
          }}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%',
              backgroundColor: connected ? '#10b981' : '#ef4444',
              display: 'inline-block',
            }} />
            {connected ? 'Connected' : 'Connecting'}
          </span>
        </div>
      </div>

      {/* Messages List */}
      {messages.length === 0 ? (
        <div style={{
          padding: '1.25rem',
          textAlign: 'center',
          backgroundColor: 'var(--bg-color)',
          borderRadius: 'var(--radius-md)',
          border: '1px dashed var(--border-color)',
          color: 'var(--text-muted)',
          fontSize: '0.9rem',
        }}>
          No messages yet. Students can send messages from their exam view.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '380px', overflowY: 'auto' }}>
          {messages.map((msg) => (
            <div
              key={msg.id}
              style={{
                padding: '0.875rem 1rem',
                backgroundColor: msg.isOwn ? 'var(--primary-color)' : 'var(--bg-color)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)',
                marginLeft: msg.isOwn ? 'auto' : 0,
                marginRight: msg.isOwn ? 0 : 'auto',
                maxWidth: '80%',
                borderRadius: msg.isOwn ? 'var(--radius-lg) var(--radius-lg) 0 var(--radius-lg)' : 'var(--radius-lg) var(--radius-lg) var(--radius-lg) 0',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.375rem' }}>
                <span style={{ fontWeight: 600, color: msg.isOwn ? '#fff' : 'var(--text-color)', fontSize: '0.95rem' }}>
                  {msg.sender}
                </span>
                <span style={{ fontSize: '0.75rem', color: msg.isOwn ? 'rgba(255,255,255,0.7)' : 'var(--text-muted)' }}>
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              </div>

              <p style={{ margin: '0', fontSize: '0.9rem', color: msg.isOwn ? '#fff' : 'var(--text-color)', lineHeight: 1.4 }}>
                {msg.message}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Send Message */}
      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
        <input
          type="text"
          placeholder="Type a message..."
          value={replyText}
          onChange={(e) => setReplyText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleSendMessage();
            }
          }}
          style={{
            flex: 1,
            padding: '0.6rem 0.75rem',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-color)',
            backgroundColor: 'var(--sidebar-bg)',
            color: 'var(--text-color)',
            fontSize: '0.9rem',
          }}
          autoFocus
        />
        <button
          onClick={handleSendMessage}
          disabled={!replyText.trim() || !connected}
          style={{
            padding: '0.6rem 1.25rem',
            backgroundColor: connected ? 'var(--primary-color)' : 'var(--border-color)',
            color: '#fff',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.9rem',
            fontWeight: 500,
            cursor: connected ? 'pointer' : 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem',
          }}
        >
          <Send size={16} /> Send
        </button>
      </div>
    </div>
  );
}

