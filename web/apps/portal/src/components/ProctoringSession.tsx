import { useState, useEffect } from 'react';
import { useProctoring } from '../hooks/useProctoring';
import { GDPRConsentModal } from './GDPRConsentModal';

interface ProctoringSessionProps {
  examId: string;
  submissionId: string;
  onSessionComplete?: (stats: { violations: number; maxFaces: number; duration: number }) => void;
}

export function ProctoringSession({ examId, submissionId, onSessionComplete }: ProctoringSessionProps) {
  const [showConsentModal, setShowConsentModal] = useState(false);
  const [sessionStarted, setSessionStarted] = useState(false);

  const proctoring = useProctoring({
    examId,
    submissionId,
    onConsentGiven: () => {
      setShowConsentModal(false);
      setSessionStarted(true);
    },
    onSessionStarted: (sessionId) => {
      console.log('Proctoring session started:', sessionId);
    },
    onSessionEnded: () => {
      console.log('Proctoring session ended');
      if (onSessionComplete) {
        onSessionComplete({
          violations: proctoring.violationCount,
          maxFaces: proctoring.maxFaces,
          duration: 0, // Would need to track this
        });
      }
    },
    onViolation: (violation) => {
      console.warn('Proctoring violation:', violation);
    },
  });

  // Sync sessionStarted when existing consent is loaded
  useEffect(() => {
    if (proctoring.consentGiven && !sessionStarted) {
      setSessionStarted(true);
    }
  }, [proctoring.consentGiven, sessionStarted]);

  const handleStartSession = async () => {
    try {
      await proctoring.startSession({
        cameraEnabled: proctoring.cameraEnabled,
        microphoneEnabled: proctoring.microphoneEnabled,
        screenRecordingEnabled: proctoring.screenRecordingEnabled,
      });
    } catch (err) {
      console.error('Failed to start session:', err);
    }
  };

  const handleEndSession = async () => {
    try {
      await proctoring.endSession();
      setSessionStarted(false);
    } catch (err) {
      console.error('Failed to end session:', err);
    }
  };

  if (!proctoring.consentGiven) {
    return (
      <div style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', textAlign: 'center' }}>
        <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.95rem', color: 'var(--text-color)' }}>⚪ AI Proctoring</h4>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
          Review GDPR privacy controls to configure optional proctoring.
        </p>
        <button
          type="button"
          onClick={() => setShowConsentModal(true)}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: 'var(--primary-color)',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '0.85rem',
          }}
        >
          Review Proctoring Consent
        </button>
        <GDPRConsentModal
          examId={examId}
          isOpen={showConsentModal}
          onClose={() => setShowConsentModal(false)}
          onConsentGiven={async (consent) => {
            await proctoring.giveConsent(consent);
          }}
        />
      </div>
    );
  }

  if (!sessionStarted) {
    return (
      <div style={{ padding: '1.5rem', textAlign: 'center' }}>
        <h3 style={{ marginBottom: '1rem' }}>Proctoring Ready</h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
          Consent has been given. Click below to start the proctoring session.
        </p>
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={proctoring.cameraEnabled}
              onChange={(e) => proctoring.startSession({ ...proctoring, cameraEnabled: e.target.checked })}
              disabled={proctoring.sessionActive}
            />
            Camera
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={proctoring.microphoneEnabled}
              onChange={(e) => proctoring.startSession({ ...proctoring, microphoneEnabled: e.target.checked })}
              disabled={proctoring.sessionActive}
            />
            Microphone
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={proctoring.screenRecordingEnabled}
              onChange={(e) => proctoring.startSession({ ...proctoring, screenRecordingEnabled: e.target.checked })}
              disabled={proctoring.sessionActive}
            />
            Screen Monitoring
          </label>
        </div>
        <button
          onClick={handleStartSession}
          disabled={proctoring.sessionActive}
          style={{
            marginTop: '1rem',
            padding: '0.75rem 2rem',
            backgroundColor: '#10b981',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: proctoring.sessionActive ? 'not-allowed' : 'pointer',
            fontWeight: '600',
            opacity: proctoring.sessionActive ? 0.6 : 1,
          }}
        >
          Start Proctoring Session
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h3 style={{ margin: 0 }}>
          {proctoring.sessionActive ? '🔴 Proctoring Active' : '⚪ Proctoring Inactive'}
        </h3>
        {proctoring.sessionActive && (
          <button
            onClick={handleEndSession}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#ef4444',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            End Session
          </button>
        )}
      </div>

      {proctoring.error && (
        <div style={{ color: '#ef4444', marginBottom: '1rem', padding: '0.75rem', backgroundColor: '#fef2f2', borderRadius: '4px' }}>
          {proctoring.error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <div style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: proctoring.violationCount > 0 ? '#ef4444' : '#10b981' }}>
            {proctoring.violationCount}
          </div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Violations</div>
        </div>
        <div style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{proctoring.maxFaces}</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Max Faces Detected</div>
        </div>
        <div style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{proctoring.events.length}</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Events Recorded</div>
        </div>
      </div>

      {proctoring.cameraEnabled && proctoring.videoRef.current && (
        <div style={{ marginBottom: '1.5rem' }}>
          <h4 style={{ marginBottom: '0.5rem' }}>Camera Preview</h4>
          <div style={{ width: '100%', maxWidth: '400px', aspectRatio: '4/3', backgroundColor: '#000', borderRadius: '8px', overflow: 'hidden' }}>
            <video
              ref={proctoring.videoRef}
              autoPlay
              muted
              playsInline
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          </div>
        </div>
      )}

      <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
        <h4 style={{ marginBottom: '0.5rem' }}>Recent Events</h4>
        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
          {proctoring.events.slice(-20).reverse().map((event, index) => (
            <div
              key={index}
              style={{
                padding: '0.5rem',
                marginBottom: '0.25rem',
                backgroundColor: event.severity === 'violation' ? '#fef2f2' : event.severity === 'warning' ? '#fffbeb' : 'var(--sidebar-bg)',
                borderLeft: `3px solid ${event.severity === 'violation' ? '#ef4444' : event.severity === 'warning' ? '#f59e0b' : '#10b981'}`,
                borderRadius: '0 4px 4px 0',
                fontSize: '0.875rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontWeight: '500', textTransform: 'capitalize' }}>{event.event_type.replace(/_/g, ' ')}</span>
                <span style={{ 
                  fontSize: '0.75rem', 
                  padding: '0.125rem 0.375rem', 
                  borderRadius: '4px',
                  backgroundColor: event.severity === 'violation' ? '#fecaca' : event.severity === 'warning' ? '#fde68a' : '#d1fae5',
                  color: event.severity === 'violation' ? '#dc2626' : event.severity === 'warning' ? '#d97706' : '#059669',
                }}>
                  {event.severity}
                </span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                {new Date(event.timestamp).toLocaleTimeString()}
              </div>
              {event.event_data && (
                <pre style={{ fontSize: '0.7rem', marginTop: '0.25rem', overflow: 'auto' }}>
                  {JSON.stringify(event.event_data, null, 2)}
                </pre>
              )}
            </div>
          ))}
          {proctoring.events.length === 0 && (
            <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
              No events recorded yet
            </div>
          )}
        </div>
      </div>
    </div>
  );
}