import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { API_URL } from '../api';

interface ChatMessage {
  sender: string;
  message: string;
}

export function SecureChat({ examId }: { examId: string }) {
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [connected, setConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token || !examId) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = API_URL.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}//${host}/chat/exam/${examId}`;

    const socket = new WebSocket(wsUrl);
    ws.current = socket;

    socket.onopen = () => {
      // Send auth token in first frame — never in URL query params
      socket.send(JSON.stringify({ token }));
      setConnected(true);
    };

    socket.onmessage = (event: MessageEvent) => {
      try {
        const data: ChatMessage = JSON.parse(event.data);
        setMessages(prev => [...prev, data]);
      } catch {
        // Ignore malformed frames
      }
    };

    socket.onclose = () => setConnected(false);
    socket.onerror = () => setConnected(false);

    return () => {
      socket.close();
    };
  }, [examId]);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || !ws.current || ws.current.readyState !== WebSocket.OPEN) return;
    // Enforce client-side 500 char limit (server enforces 2048)
    ws.current.send(trimmed.slice(0, 500));
    setInput('');
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '400px', border: '1px solid var(--border-color)', borderRadius: '8px', overflow: 'hidden' }}>
      <div style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--sidebar-bg)', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <strong>Digital Hand Raise</strong>
        <span style={{
          width: 8, height: 8, borderRadius: '50%',
          backgroundColor: connected ? '#10b981' : '#ef4444',
          display: 'inline-block'
        }} title={connected ? 'Connected' : 'Disconnected'} />
      </div>

      <div style={{ flex: 1, padding: '0.75rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem', backgroundColor: 'var(--bg-color)' }}>
        {messages.map((msg, i) => {
          const isMe = msg.sender === (user?.full_name || user?.username);
          return (
            <div
              key={i}
              style={{
                alignSelf: isMe ? 'flex-end' : 'flex-start',
                backgroundColor: isMe ? 'var(--primary-color, #2563eb)' : 'var(--sidebar-bg)',
                color: isMe ? '#fff' : 'inherit',
                padding: '0.4rem 0.75rem',
                borderRadius: '8px',
                maxWidth: '80%',
                border: '1px solid var(--border-color)',
                wordBreak: 'break-word',
              }}
            >
              <small style={{ display: 'block', opacity: 0.7, fontSize: '0.72rem', marginBottom: '0.15rem' }}>
                {msg.sender}
              </small>
              {msg.message}
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      <div style={{ display: 'flex', padding: '0.5rem', backgroundColor: 'var(--sidebar-bg)', borderTop: '1px solid var(--border-color)', gap: '0.5rem' }}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={connected ? 'Ask a question…' : 'Connecting…'}
          disabled={!connected}
          maxLength={500}
          style={{ flex: 1, padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
        />
        <button
          onClick={sendMessage}
          disabled={!connected || !input.trim()}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: connected ? '#10b981' : '#6b7280',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: connected ? 'pointer' : 'not-allowed',
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
