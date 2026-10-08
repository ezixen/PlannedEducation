import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../api';

export function PasskeysSettings() {
  const { user, refreshUser } = useAuth();
  const { success: showSuccess, error: showError, info: showInfo } = useToast();

  const [passkeys, setPasskeys] = useState<PasskeyCredential[]>([]);
  const [loading, setLoading] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [registrationOptions, setRegistrationOptions] = useState<WebAuthnRegistrationOptions | null>(null);
  const [showRegisterModal, setShowRegisterModal] = useState(false);

  interface PasskeyCredential {
    credential_id: string;
    public_key: string;
    sign_count: number;
    transports: string[] | null;
    created_at: string;
    last_used_at: string | null;
  }

  interface WebAuthnRegistrationOptions {
    challenge: string;
    rp: { id: string; name: string };
    user: { id: string; name: string; displayName: string };
    pubKeyCredParams: { type: string; alg: number }[];
    timeout: number;
    attestation: string;
    authenticatorSelection: {
      authenticatorAttachment: string;
      residentKey: string;
      userVerification: string;
    };
    extensions: Record<string, any>;
  }

  useEffect(() => {
    if (user) {
      fetchPasskeys();
    }
  }, [user]);

  const fetchPasskeys = async () => {
    try {
      const response = await apiClient.get('/auth/webauthn/credentials');
      setPasskeys(response.data);
    } catch (err: any) {
      console.error('Failed to fetch passkeys:', err);
    }
  };

  const handleRegisterStart = async () => {
    setRegistering(true);
    try {
      const response = await apiClient.post('/auth/webauthn/registration/start');
      setRegistrationOptions(response.data.registration_options);
      setShowRegisterModal(true);
      showInfo('Use your device\'s biometric/PIN to create a passkey');
    } catch (err: any) {
      showError('Failed to start passkey registration.', err.response?.data?.detail || err.message);
    } finally {
      setRegistering(false);
    }
  };

  const handleRegisterFinish = async () => {
    if (!registrationOptions) return;
    
    try {
      // Get the credential from the browser
      const credential = await navigator.credentials.create({
        publicKey: {
          challenge: base64urlToBuffer(registrationOptions.challenge),
          rp: registrationOptions.rp,
          user: registrationOptions.user,
          pubKeyCredParams: registrationOptions.pubKeyCredParams,
          timeout: registrationOptions.timeout,
          attestation: registrationOptions.attestation,
          authenticatorSelection: registrationOptions.authenticatorSelection,
          extensions: registrationOptions.extensions,
        },
      });

      if (!credential) {
        throw new Error('No credential returned');
      }

      // Convert to the format expected by the backend
      const credentialData = {
        id: credential.id,
        rawId: bufferToBase64url(credential.rawId),
        response: {
          clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
          attestationObject: bufferToBase64url(credential.response.attestationObject),
        },
        type: credential.type,
        clientExtensionResults: credential.getClientExtensionResults(),
      };

      await apiClient.post('/auth/webauthn/registration/finish', credentialData);
      showSuccess('Passkey registered successfully!');
      setShowRegisterModal(false);
      fetchPasskeys();
    } catch (err: any) {
      showError('Failed to register passkey.', err.response?.data?.detail || err.message);
    }
  };

  const handleDelete = async (credentialId: string) => {
    if (!window.confirm('Are you sure you want to delete this passkey?')) return;
    
    try {
      await apiClient.delete(`/auth/webauthn/credentials/${credentialId}`);
      showSuccess('Passkey deleted');
      fetchPasskeys();
    } catch (err: any) {
      showError('Failed to delete passkey.', err.response?.data?.detail || err.message);
    }
  };

  const formatTransports = (transports: string[] | null): string => {
    if (!transports || transports.length === 0) return 'Unknown';
    return transports.join(', ');
  };

  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleDateString();
  };

  const base64urlToBuffer = (base64url: string): ArrayBuffer => {
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + (4 - base64.length % 4) % 4, '=');
    const binary = atob(padded);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  };

  const bufferToBase64url = (buffer: ArrayBuffer): string => {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '0.625rem',
    marginTop: '0.25rem',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-color)',
    backgroundColor: 'var(--bg-color)',
    color: 'var(--text-color)',
    fontSize: '0.95rem',
  };

  const buttonStyle: React.CSSProperties = {
    padding: '0.5rem 1.5rem',
    backgroundColor: 'var(--primary-color)',
    color: '#fff',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    fontWeight: 600,
  };

  const secondaryButtonStyle: React.CSSProperties = {
    ...buttonStyle,
    backgroundColor: 'var(--secondary-color)',
  };

  const dangerButtonStyle: React.CSSProperties = {
    ...buttonStyle,
    backgroundColor: '#ef4444',
  };

  return (
    <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
      <h3>Passkeys (WebAuthn)</h3>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
        Passkeys are a phishing-resistant alternative to passwords. Use your device's biometric
        (fingerprint, face ID) or PIN to sign in securely. Passkeys sync across your devices
        via iCloud Keychain, Google Password Manager, or your password manager.
      </p>

      {passkeys.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
          <p style={{ marginBottom: '1rem' }}>No passkeys registered yet.</p>
          <button
            onClick={() => setShowRegisterModal(true)}
            disabled={loading}
            style={{ ...buttonStyle, opacity: loading ? 0.7 : 1 }}
          >
            {loading ? 'Loading…' : 'Register Passkey'}
          </button>
        </div>
      ) : (
        <div>
          <h4 style={{ marginBottom: '1rem' }}>Registered Passkeys ({passkeys.length})</h4>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Created</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Last Used</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Transports</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Sign Count</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {passkeys.map(passkey => (
                  <tr key={passkey.credential_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '0.75rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                      {formatDate(passkey.created_at)}
                    </td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                      {passkey.last_used_at ? formatDate(passkey.last_used_at) : 'Never'}
                    </td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                      {formatTransports(passkey.transports)}
                    </td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace', fontSize: '0.85rem' }}>
                      {passkey.sign_count}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                      <button
                        onClick={() => handleDelete(passkey.credential_id)}
                        style={dangerButtonStyle}
                        style={{ padding: '0.375rem 0.75rem', fontSize: '0.8rem' }}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button
            onClick={() => setShowRegisterModal(true)}
            disabled={loading}
            style={{ ...buttonStyle, marginTop: '1rem' }}
          >
            {loading ? 'Loading…' : 'Add Another Passkey'}
          </button>
        </div>
      )}

      {/* Register Modal */}
      {showRegisterModal && registrationOptions && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1rem' }}>
          <div style={{ backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', maxWidth: '500px', width: '100%', maxHeight: '90vh', overflow: 'auto' }}>
            <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Register Passkey</h2>
              <button onClick={() => setShowRegisterModal(false)} style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: 'var(--text-muted)' }}>×</button>
            </div>
            <div style={{ padding: '1.5rem' }}>
              <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
                Use your device's biometric (fingerprint, face ID) or PIN to create a passkey.
                This passkey will be synced across your devices via iCloud Keychain, Google Password Manager, or your password manager.
              </p>
              <button
                onClick={handleRegisterFinish}
                disabled={registering}
                style={{ width: '100%', padding: '1rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: registering ? 'not-allowed' : 'pointer', fontWeight: 600, fontSize: '1rem' }}
              >
                {registering ? 'Registering…' : 'Create Passkey'}
              </button>
              <button onClick={() => setShowRegisterModal(false)} style={{ width: '100%', padding: '1rem', backgroundColor: 'var(--secondary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 600, marginTop: '0.75rem' }}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}