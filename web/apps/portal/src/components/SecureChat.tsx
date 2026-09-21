import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { API_URL } from '../api';

export function SecureChat({ examId }: { examId: number }) {
  const { user } = useAuth();
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState('');
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    // Convert http/https to ws/wss
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Remove protocol from API_URL
    const host = API_URL.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}//${host}/chat/exam/${examId}?token=${token}`;

    ws.current = new WebSocket(wsUrl);

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages((prev) => [...prev, data]);
    };

    ws.current.onerror = (e) => {
      console.error("WebSocket error:", e);
    };

    return () => {
      ws.current?.close();
    };
  }, [examId]);

  const sendMessage = () => {
    if (!input.trim() || !ws.current) return;
    ws.current.send(input);
    setInput('');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '400px', border: '1px solid var(--border-color)', borderRadius: '8px', overflow: 'hidden' }}>
      <div style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--sidebar-bg)', borderBottom: '1px solid var(--border-color)', fontWeight: 'bold' }}>
        Digital Hand Raise (Teacher Chat)
      </div>
      
      <div style={{ flex: 1, padding: '1rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem', backgroundColor: 'var(--bg-color)' }}>
        {messages.map((msg, i) => {
          const isMe = msg.sender === user?.full_name;
          const isTeacher = msg.role === 'teacher';
          return (
            <div key={i} style={{ 
              alignSelf: isMe ? 'flex-end' : 'flex-start',
              backgroundColor: isTeacher ? '#3b82f6' : 'var(--sidebar-bg)',
              color: isTeacher ? '#fff' : 'inherit',
              padding: '0.5rem 1rem',
              borderRadius: '8px',
              maxWidth: '80%',
              border: '1px solid var(--border-color)'
            }}>
              <small style={{ display: 'block', opacity: 0.8, fontSize: '0.75rem', marginBottom: '0.2rem' }}>
                {msg.sender} {isTeacher && '(Teacher)'}
              </small>
              {msg.message}
            </div>
          );
        })}
      </div>

      <div style={{ display: 'flex', padding: '0.5rem', backgroundColor: 'var(--sidebar-bg)', borderTop: '1px solid var(--border-color)' }}>
        <input 
          type="text" 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Ask a question..."
          style={{ flex: 1, padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}
        />
        <button onClick={sendMessage} style={{ marginLeft: '0.5rem', padding: '0.5rem 1rem', backgroundColor: '#10b981', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
          Send
        </button>
      </div>
    </div>
  );
}
