import { useState } from 'react';
import type { ProctoringConsentRequest } from '../services/proctoring';

interface GDPRConsentModalProps {
  examId: string;
  onConsentGiven: (consent: ProctoringConsentRequest) => void;
  onClose: () => void;
  isOpen: boolean;
}

export function GDPRConsentModal({ examId, onConsentGiven, onClose, isOpen }: GDPRConsentModalProps) {
  const [consentData, setConsentData] = useState({
    camera_consent: false,
    microphone_consent: false,
    screen_recording_consent: false,
    data_processing_consent: false,
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Validate required consents
    if (!consentData.data_processing_consent) {
      setError('Data processing consent is required to proceed.');
      setLoading(false);
      return;
    }

    try {
      await onConsentGiven({
        exam_id: examId,
        ...consentData,
        consent_version: '1.0',
      });
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit consent');
    } finally {
      setLoading(false);
    }
  };

  const toggleConsent = (key: keyof typeof consentData) => {
    setConsentData(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: 'var(--card-bg)',
          borderRadius: '12px',
          padding: '2rem',
          maxWidth: '600px',
          width: '90%',
          maxHeight: '90vh',
          overflowY: 'auto',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        }}
        onClick={e => e.stopPropagation()}
      >
        <h2 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-primary)' }}>
          GDPR Consent for AI Proctoring
        </h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
          This exam uses optional AI proctoring to ensure academic integrity. 
          Please review and consent to the following data processing activities.
        </p>

        {error && (
          <div
            style={{
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              color: '#dc2626',
              padding: '0.75rem',
              borderRadius: '6px',
              marginBottom: '1rem',
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', color: 'var(--text-primary)' }}>
              Data Processing Activities
            </h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={consentData.camera_consent}
                  onChange={() => toggleConsent('camera_consent')}
                  style={{ marginTop: '0.25rem', width: '18px', height: '18px' }}
                />
                <div>
                  <strong style={{ display: 'block', marginBottom: '0.25rem' }}>
                    Camera Access (Face Detection & Eye Tracking)
                  </strong>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    Uses webcam to detect face presence, track eye movements, and identify 
                    if multiple people are in frame. Video is processed locally and only 
                    event metadata is sent to the server.
                  </span>
                </div>
              </label>

              <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={consentData.microphone_consent}
                  onChange={() => toggleConsent('microphone_consent')}
                  style={{ marginTop: '0.25rem', width: '18px', height: '18px' }}
                />
                <div>
                  <strong style={{ display: 'block', marginBottom: '0.25rem' }}>
                    Microphone Access (Background Audio Monitoring)
                  </strong>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    Monitors ambient audio levels to detect unusual sounds or conversations. 
                    Audio is analyzed in real-time locally; only anomaly events are recorded.
                  </span>
                </div>
              </label>

              <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={consentData.screen_recording_consent}
                  onChange={() => toggleConsent('screen_recording_consent')}
                  style={{ marginTop: '0.25rem', width: '18px', height: '18px' }}
                />
                <div>
                  <strong style={{ display: 'block', marginBottom: '0.25rem' }}>
                    Screen Recording (Tab/Window Monitoring)
                  </strong>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    Detects tab switches, window blur, and fullscreen exits. 
                    No actual screen content is recorded or transmitted.
                  </span>
                </div>
              </label>

              <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={consentData.data_processing_consent}
                  onChange={() => toggleConsent('data_processing_consent')}
                  style={{ marginTop: '0.25rem', width: '18px', height: '18px' }}
                  required
                />
                <div>
                  <strong style={{ display: 'block', marginBottom: '0.25rem' }}>
                    Data Processing & Storage (Required)
                  </strong>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    Consent to process and store proctoring event data (timestamps, event types, 
                    severity levels, face counts, gaze coordinates) for the duration of the exam 
                    and 30 days after for review purposes.
                  </span>
                </div>
              </label>
            </div>
          </div>

          <div style={{ marginBottom: '1.5rem', padding: '1rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px' }}>
            <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem' }}>Your Rights (GDPR)</h4>
            <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              <li>Right to withdraw consent at any time</li>
              <li>Right to access your proctoring data</li>
              <li>Right to request data deletion after exam review period</li>
              <li>Right to data portability</li>
              <li>Right to object to automated decision-making</li>
            </ul>
          </div>

          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              style={{
                padding: '0.75rem 1.5rem',
                backgroundColor: 'transparent',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !consentData.data_processing_consent}
              style={{
                padding: '0.75rem 1.5rem',
                backgroundColor: consentData.data_processing_consent ? '#10b981' : '#9ca3af',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                cursor: consentData.data_processing_consent ? 'pointer' : 'not-allowed',
                fontWeight: '600',
              }}
            >
              {loading ? 'Submitting...' : 'Give Consent & Continue'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}