import { useState, useRef } from 'react';

export function ProctoringToggle() {
  const [enabled, setEnabled] = useState(false);
  const [error, setError] = useState('');
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const toggleProctoring = async () => {
    if (enabled) {
      // Turn off
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
      setEnabled(false);
      setError('');
    } else {
      // Turn on
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setEnabled(true);
        setError('');
      } catch (err) {
        console.error(err);
        setError('Camera/Microphone access denied. Cannot enable proctoring.');
      }
    }
  };

  return (
    <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', marginBottom: '2rem' }}>
      <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: '0 0 1rem 0' }}>
        Optional AI Proctoring
        <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', backgroundColor: '#ef4444', color: '#fff', borderRadius: '12px' }}>GDPR Warning</span>
      </h3>
      
      <p style={{ fontSize: '0.9rem', color: 'gray', marginBottom: '1rem' }}>
        When enabled, this exam will use your webcam and microphone to track eye movement, flag if a second person enters the frame, and monitor background audio. 
        <strong> This is optional and only recommended for remote, take-home exams.</strong>
      </p>

      {error && <div style={{ color: '#ef4444', marginBottom: '1rem' }}>{error}</div>}

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
        <div>
          <button 
            onClick={toggleProctoring}
            style={{ 
              padding: '0.5rem 1rem', 
              backgroundColor: enabled ? '#ef4444' : '#10b981', 
              color: '#fff', 
              border: 'none', 
              borderRadius: '4px', 
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            {enabled ? 'Disable Proctoring' : 'Enable Proctoring'}
          </button>
        </div>
        
        {enabled && (
          <div style={{ width: '200px', height: '150px', backgroundColor: '#000', borderRadius: '8px', overflow: 'hidden' }}>
            <video 
              ref={videoRef} 
              autoPlay 
              muted 
              playsInline 
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
