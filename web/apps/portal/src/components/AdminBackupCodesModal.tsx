import { useState, useEffect } from 'react';
import { ShieldAlert, Printer, Copy, Check, X } from 'lucide-react';
import { apiClient } from '../api';
import { useToast } from '../contexts/ToastContext';

interface AdminBackupCodesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AdminBackupCodesModal({ isOpen, onClose }: AdminBackupCodesModalProps) {
  const { success: showSuccess, error: showError } = useToast();
  const [activeCodesCount, setActiveCodesCount] = useState<number>(0);
  const [hasCodes, setHasCodes] = useState<boolean>(false);
  const [freshCodes, setFreshCodes] = useState<string[] | null>(null);
  const [generating, setGenerating] = useState(false);
  const [copied, setCopied] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await apiClient.get('/admin/backup-codes');
      setHasCodes(res.data.has_backup_codes);
      setActiveCodesCount(res.data.active_codes_count || 0);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
      setFreshCodes(null);
      setCopied(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleGenerateCodes = async () => {
    setGenerating(true);
    try {
      const res = await apiClient.post('/admin/backup-codes/generate');
      setFreshCodes(res.data.recovery_codes);
      setActiveCodesCount(res.data.recovery_codes.length);
      setHasCodes(true);
      showSuccess('Generated 5 emergency backup codes!');
    } catch (err: any) {
      showError('Failed to generate codes', err.response?.data?.detail || err.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleCopy = () => {
    if (!freshCodes) return;
    navigator.clipboard.writeText(freshCodes.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
        zIndex: 1100,
      }}
    >
      <div
        style={{
          backgroundColor: 'var(--sidebar-bg)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-color)',
          width: '100%',
          maxWidth: '520px',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '1rem 1.25rem',
            borderBottom: '1px solid var(--border-color)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            backgroundColor: 'var(--bg-color)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldAlert size={20} style={{ color: '#ef4444' }} />
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-color)' }}>
              Admin Emergency Recovery Codes
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-muted)',
              padding: '0.25rem',
            }}
          >
            <X size={20} />
          </button>
        </div>

        <div style={{ padding: '1.25rem' }}>
          {/* Critical Warning Callout */}
          <div
            style={{
              padding: '0.85rem',
              backgroundColor: 'rgba(239, 68, 68, 0.08)',
              border: '1px solid #ef4444',
              borderRadius: 'var(--radius-md)',
              color: '#b91c1c',
              fontSize: '0.85rem',
              lineHeight: 1.45,
              marginBottom: '1.25rem',
            }}
          >
            <strong>⚠️ CRITICAL OVERSIGHT WARNING:</strong> Administrators must always maintain saved or printed
            emergency backup codes. If an administrator loses access to their credentials or 2FA authenticator, no one
            can approve teachers, reset student passwords, or maintain system oversight!
          </div>

          {/* Current Status */}
          <div
            style={{
              padding: '0.85rem',
              backgroundColor: 'var(--bg-color)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-md)',
              marginBottom: '1.25rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-color)' }}>
                Active Recovery Codes
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                {hasCodes
                  ? `You have ${activeCodesCount} single-use recovery code(s) active.`
                  : 'You do NOT have emergency backup codes configured yet.'}
              </div>
            </div>
            <button
              onClick={handleGenerateCodes}
              disabled={generating}
              style={{
                padding: '0.5rem 0.9rem',
                backgroundColor: 'var(--primary-color)',
                color: '#ffffff',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                cursor: generating ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                fontSize: '0.8rem',
              }}
            >
              {generating ? 'Generating...' : hasCodes ? 'Regenerate Fresh Codes' : 'Generate Codes Now'}
            </button>
          </div>

          {/* Display Fresh Codes */}
          {freshCodes && (
            <div>
              <div
                style={{
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  color: 'var(--text-color)',
                  marginBottom: '0.5rem',
                }}
              >
                Generated One-Time Emergency Codes:
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                  gap: '0.5rem',
                  padding: '1rem',
                  backgroundColor: 'var(--bg-color)',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  marginBottom: '1rem',
                }}
              >
                {freshCodes.map((code, idx) => (
                  <div
                    key={idx}
                    style={{
                      fontFamily: 'monospace',
                      fontSize: '1rem',
                      fontWeight: 700,
                      letterSpacing: '0.05em',
                      padding: '0.4rem',
                      backgroundColor: 'var(--sidebar-bg)',
                      border: '1px dashed var(--border-color)',
                      borderRadius: '4px',
                      color: 'var(--primary-color)',
                      textAlign: 'center',
                    }}
                  >
                    {code}
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
                <button
                  type="button"
                  onClick={handleCopy}
                  style={{
                    padding: '0.6rem 1rem',
                    backgroundColor: 'var(--sidebar-bg)',
                    color: 'var(--text-color)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    fontWeight: 600,
                    fontSize: '0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                  }}
                >
                  {copied ? <Check size={16} /> : <Copy size={16} />}
                  {copied ? 'Copied to Clipboard!' : 'Copy All Codes'}
                </button>
                <button
                  type="button"
                  onClick={handlePrint}
                  style={{
                    padding: '0.6rem 1rem',
                    backgroundColor: 'var(--sidebar-bg)',
                    color: 'var(--text-color)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    fontWeight: 600,
                    fontSize: '0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                  }}
                >
                  <Printer size={16} />
                  Print / Save as PDF
                </button>
              </div>
            </div>
          )}

          <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
            <button
              onClick={onClose}
              style={{
                padding: '0.6rem 1.25rem',
                backgroundColor: 'var(--bg-color)',
                color: 'var(--text-color)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                fontWeight: 500,
              }}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
