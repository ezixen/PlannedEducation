import { useState } from 'react';
import type { ProctoringConsentRequest } from '../services/proctoring';
import { useI18n } from '../contexts/I18nContext';

interface GDPRConsentModalProps {
  examId: string;
  onConsentGiven: (consent: ProctoringConsentRequest) => void;
  onClose: () => void;
  isOpen: boolean;
}

export function GDPRConsentModal({ examId, onConsentGiven, onClose, isOpen }: GDPRConsentModalProps) {
  const { t } = useI18n();
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
      setError(t('proctoring.consent_required'));
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
          {t('proctoring.gdpr_title')}
        </h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
          {t('proctoring.gdpr_desc')}
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
              {t('proctoring.activities_title')}
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
                    {t('proctoring.camera_title')}
                  </strong>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    {t('proctoring.camera_desc')}
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
                    {t('proctoring.mic_title')}
                  </strong>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    {t('proctoring.mic_desc')}
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
                    {t('proctoring.screen_title')}
                  </strong>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    {t('proctoring.screen_desc')}
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
                    {t('proctoring.storage_title')}
                  </strong>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    {t('proctoring.storage_desc')}
                  </span>
                </div>
              </label>
            </div>
          </div>

          <div style={{ marginBottom: '1.5rem', padding: '1rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px' }}>
            <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem' }}>{t('proctoring.rights_title')}</h4>
            <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              <li>{t('proctoring.right_withdraw')}</li>
              <li>{t('proctoring.right_access')}</li>
              <li>{t('proctoring.right_delete')}</li>
              <li>{t('proctoring.right_portability')}</li>
              <li>{t('proctoring.right_automated')}</li>
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
              {t('common.2')}
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
              {loading ? t('proctoring.submitting') : t('proctoring.submit_consent')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
