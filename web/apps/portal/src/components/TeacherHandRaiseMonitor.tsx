import { useState, useEffect, useRef, useCallback } from 'react';
import { Hand, Volume2, VolumeX, Send, CheckCircle2, MessageSquare } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { API_URL } from '../api';

export interface HandRaiseMessage {
  id: string;
  sender: string;
  message: string;
  timestamp: Date;
  resolved: boolean;
}

/**
 * Synthesizes a soft, smooth dual-tone chime using Web Audio API.
 * Uses soft sine waves (C5 -> E5) with gentle attack and exponential decay.
 * Zero external assets or network dependencies.
 */
export function playHandRaiseChime() {
  try {
    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextClass) return;
    const ctx = new AudioContextClass();
    const now = ctx.currentTime;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    // Smooth dual note: C5 (523.25 Hz) transitioning to E5 (659.25 Hz)
    osc.frequency.setValueAtTime(523.25, now);
    osc.frequency.setValueAtTime(659.25, now + 0.12);

    // Soft volume: peaks at 0.08, gently decays to 0.001
    gain.gain.setValueAtTime(0.001, now);
    gain.gain.linearRampToValueAtTime(0.08, now + 0.04);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.6);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.65);
  } catch (err) {
    // Gracefully handle browser autoplay policies
    console.debug('Hand-raise chime playback skipped:', err);
  }
}

interface TeacherHandRaiseMonitorProps {
  examId: string;
  examTitle?: string;
  deliveryMode?: 'classroom' | 'different_location';
}

export function TeacherHandRaiseMonitor({ examId, examTitle, deliveryMode = 'different_location' }: TeacherHandRaiseMonitorProps) {
  const { user } = useAuth();
  const { info: showInfo } = useToast();

  const [handRaises, setHandRaises] = useState<HandRaiseMessage[]>([]);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [connected, setConnected] = useState(false);
  const [replyText, setReplyText] = useState<Record<string, string>>({});
  const [activeReplyId, setActiveReplyId] = useState<string | null>(null);

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
          const newEntry: HandRaiseMessage = {
            id: `hr-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
            sender: data.sender,
            message: data.message,
            timestamp: new Date(),
            resolved: false,
          };

          setHandRaises(prev => [newEntry, ...prev]);

          // Play smooth, pleasant chime
          if (soundEnabled) {
            playHandRaiseChime();
          }

          // Trigger noticeable toast warning
          showInfo(`✋ Student ${data.sender} raised their hand: "${data.message}"`, { sticky: true });
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
  }, [examId, user, soundEnabled, showInfo]);

  const handleSendReply = useCallback((studentName: string, handRaiseId: string) => {
    const text = (replyText[handRaiseId] || '').trim();
    if (!text || !ws.current || ws.current.readyState !== WebSocket.OPEN) return;

    // Send the reply message to the exam room
    ws.current.send(`@${studentName}: ${text}`);

    // Mark as resolved and clear text
    setHandRaises(prev => prev.map(hr => hr.id === handRaiseId ? { ...hr, resolved: true } : hr));
    setReplyText(prev => ({ ...prev, [handRaiseId]: '' }));
    setActiveReplyId(null);
  }, [replyText]);

  const toggleResolved = (id: string) => {
    setHandRaises(prev => prev.map(hr => hr.id === id ? { ...hr, resolved: !hr.resolved } : hr));
  };

  const unresolvedCount = handRaises.filter(hr => !hr.resolved).length;

  return (
    <div style={{
      padding: '1.25rem',
      backgroundColor: 'var(--sidebar-bg)',
      borderRadius: 'var(--radius-lg)',
      border: unresolvedCount > 0 ? '2px solid var(--primary-color)' : '1px solid var(--border-color)',
      marginBottom: '1.5rem',
      boxShadow: unresolvedCount > 0 ? '0 4px 12px rgba(59, 130, 246, 0.15)' : 'none',
      transition: 'border-color 0.2s, box-shadow 0.2s',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            width: 34, height: 34, borderRadius: 'var(--radius-md)',
            backgroundColor: unresolvedCount > 0 ? 'var(--primary-color)' : 'var(--border-color)',
            color: '#fff',
          }}>
            <Hand size={18} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-color)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              Digital Hand Raises {examTitle ? `(${examTitle})` : ''}
              {unresolvedCount > 0 && (
                <span style={{
                  backgroundColor: '#ef4444',
                  color: '#fff',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  padding: '0.125rem 0.5rem',
                  borderRadius: '9999px',
                }}>
                  {unresolvedCount} Active
                </span>
              )}
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {deliveryMode === 'classroom'
                ? '🏫 Standard In-Person Classroom Exam (Students raise physical hands in class)'
                : '🌐 Different Location / Remote Exam Package (Live WebSocket notifications enabled)'}
            </span>
          </div>
        </div>

        {/* Status & Audio Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className="icon-btn"
            title={soundEnabled ? 'Chime sound is active (Click to mute)' : 'Chime sound is muted (Click to unmute)'}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.35rem',
              padding: '0.35rem 0.6rem', fontSize: '0.8rem',
              backgroundColor: 'var(--bg-color)', border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-md)', color: soundEnabled ? 'var(--primary-color)' : 'var(--text-muted)',
              cursor: 'pointer',
            }}
          >
            {soundEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
            <span>{soundEnabled ? 'Chime On' : 'Chime Off'}</span>
          </button>

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
            {connected ? 'Live' : 'Connecting'}
          </span>
        </div>
      </div>

      {/* Hand Raises List */}
      {handRaises.length === 0 ? (
        <div style={{
          padding: '1.25rem',
          textAlign: 'center',
          backgroundColor: 'var(--bg-color)',
          borderRadius: 'var(--radius-md)',
          border: '1px dashed var(--border-color)',
          color: 'var(--text-muted)',
          fontSize: '0.9rem',
        }}>
          No digital hand raises currently. Students in remote/different-location testing will appear here automatically when they need assistance.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '380px', overflowY: 'auto' }}>
          {handRaises.map((hr) => (
            <div
              key={hr.id}
              style={{
                padding: '0.875rem 1rem',
                backgroundColor: 'var(--bg-color)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)',
                opacity: hr.resolved ? 0.7 : 1,
                borderLeft: hr.resolved ? '4px solid #10b981' : '4px solid var(--primary-color)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.375rem' }}>
                <span style={{ fontWeight: 600, color: 'var(--text-color)', fontSize: '0.95rem' }}>
                  ✋ {hr.sender}
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {hr.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                  <button
                    onClick={() => toggleResolved(hr.id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: hr.resolved ? '#10b981' : 'var(--text-muted)',
                      padding: 0,
                      display: 'flex',
                      alignItems: 'center',
                    }}
                    title={hr.resolved ? 'Mark unresolved' : 'Mark resolved'}
                  >
                    <CheckCircle2 size={16} />
                  </button>
                </div>
              </div>

              <p style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: 'var(--text-color)', lineHeight: 1.4 }}>
                {hr.message}
              </p>

              {/* Reply Section */}
              {activeReplyId === hr.id ? (
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                  <input
                    type="text"
                    placeholder={`Reply to ${hr.sender}...`}
                    value={replyText[hr.id] || ''}
                    onChange={(e) => setReplyText({ ...replyText, [hr.id]: e.target.value })}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleSendReply(hr.sender, hr.id);
                      }
                    }}
                    style={{
                      flex: 1,
                      padding: '0.4rem 0.6rem',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border-color)',
                      backgroundColor: 'var(--sidebar-bg)',
                      color: 'var(--text-color)',
                      fontSize: '0.85rem',
                    }}
                    autoFocus
                  />
                  <button
                    onClick={() => handleSendReply(hr.sender, hr.id)}
                    style={{
                      padding: '0.4rem 0.75rem',
                      backgroundColor: 'var(--primary-color)',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.85rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                    }}
                  >
                    <Send size={14} /> Send
                  </button>
                  <button
                    onClick={() => setActiveReplyId(null)}
                    style={{
                      padding: '0.4rem 0.6rem',
                      backgroundColor: 'transparent',
                      color: 'var(--text-muted)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.85rem',
                      cursor: 'pointer',
                    }}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
                  <button
                    onClick={() => setActiveReplyId(hr.id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--primary-color)',
                      fontSize: '0.8rem',
                      fontWeight: 500,
                      cursor: 'pointer',
                      padding: 0,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                    }}
                  >
                    <MessageSquare size={13} /> Reply to {hr.sender}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

