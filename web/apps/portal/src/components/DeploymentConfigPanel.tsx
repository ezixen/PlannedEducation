import { useState, useEffect } from 'react';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../api';

export interface DeploymentConfig {
  school_name: string;
  domain: string;
  api_port: number;
  frontend_port: number;
  cors_origins: string;
  allowed_hosts: string;
  environment: string;
  allow_dev_seb_bypass: boolean;
  anonymizer_enabled: boolean;
  anonymizer_language: string;
  smtp_host?: string;
  smtp_port?: number;
  smtp_user?: string;
  smtp_password?: string;
  smtp_use_tls?: boolean;
  smtp_use_ssl?: boolean;
  email_from?: string;
  config_file_path?: string;
  last_modified?: string;
}

export function DeploymentConfigPanel() {
  const { success: showSuccess, error: showError } = useToast();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [restartNotice, setRestartNotice] = useState(false);
  const [config, setConfig] = useState<DeploymentConfig>({
    school_name: 'PlannedEducation School',
    domain: 'localhost',
    api_port: 8000,
    frontend_port: 5173,
    cors_origins: 'http://localhost:5173,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:5175',
    allowed_hosts: 'localhost,127.0.0.1',
    environment: 'development',
    allow_dev_seb_bypass: true,
    anonymizer_enabled: true,
    anonymizer_language: 'en',
    smtp_host: '',
    smtp_port: 587,
    smtp_user: '',
    smtp_password: '',
    smtp_use_tls: true,
    smtp_use_ssl: false,
    email_from: 'PlannedEducation <noreply@localhost>',
  });

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/admin/config');
      setConfig(res.data);
    } catch (err: any) {
      showError('Failed to load deployment config', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setRestartNotice(false);
    try {
      const res = await apiClient.put('/admin/config', config);
      showSuccess('Configuration saved to config/deployment.json and .env');
      if (res.data?.config) {
        setConfig((prev) => ({ ...prev, ...res.data.config }));
      }
      setRestartNotice(true);
    } catch (err: any) {
      showError(err.response?.data?.detail || err.message || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleBackupConfig = async () => {
    const backupJson = JSON.stringify(config, null, 2);
    const dateStr = new Date().toISOString().slice(0, 10);
    const fileName = `plannededucation-config-${dateStr}.json`;

    // Try modern File System Access API first (opens directory/file save picker)
    if ('showSaveFilePicker' in window) {
      try {
        const fileHandle = await (window as any).showSaveFilePicker({
          suggestedName: fileName,
          types: [
            {
              description: 'JSON Configuration File',
              accept: { 'application/json': ['.json'] },
            },
          ],
        });
        const writable = await fileHandle.createWritable();
        await writable.write(backupJson);
        await writable.close();
        showSuccess(`Configuration successfully saved as ${fileName}`);
        return;
      } catch (err: any) {
        // User aborted the file picker or error occurred; if user aborted, don't fallback
        if (err.name === 'AbortError') {
          return;
        }
      }
    }

    // Standard download fallback
    try {
      const blob = new Blob([backupJson], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      showSuccess(`Saved ${fileName} to your downloads folder`);
    } catch (err: any) {
      showError(err.message || 'Could not export configuration');
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
        Loading deployment configuration...
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '900px' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.5rem',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-color)', margin: 0 }}>
            ⚙️ Deployment & Network Configuration
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Manage server domain, ports, network layout, and institutional parameters. Config file is stored at{' '}
            <code style={{ background: 'var(--bg-color)', padding: '0.15rem 0.4rem', borderRadius: '4px' }}>
              {config.config_file_path || 'config/deployment.json'}
            </code>
            .
          </p>
        </div>
        <button
          type="button"
          onClick={handleBackupConfig}
          style={{
            padding: '0.6rem 1.1rem',
            backgroundColor: 'var(--sidebar-bg)',
            color: 'var(--text-color)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          📁 Backup Config File
        </button>
      </div>

      {restartNotice && (
        <div
          style={{
            padding: '1rem',
            marginBottom: '1.5rem',
            backgroundColor: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid #f59e0b',
            borderRadius: 'var(--radius-md)',
            color: '#d97706',
          }}
        >
          <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>⚠️</span> Restart Required to Apply Changes
          </div>
          <p style={{ fontSize: '0.875rem', margin: '0.5rem 0 0 0' }}>
            Changes were saved to <code style={{ fontWeight: 600 }}>config/deployment.json</code> and <code style={{ fontWeight: 600 }}>.env</code>.
            Please restart the platform services (e.g. restart backend & frontend launcher scripts or run{' '}
            <code>systemctl restart plannededucation-backend</code>) for the new domain and port settings to take effect.
          </p>
        </div>
      )}

      <form
        onSubmit={handleSave}
        style={{
          backgroundColor: 'var(--sidebar-bg)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-lg)',
          padding: '1.5rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.25rem',
        }}
      >
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem', color: 'var(--text-color)' }}>
              School / Institution Name
            </label>
            <input
              type="text"
              required
              value={config.school_name}
              onChange={(e) => setConfig({ ...config, school_name: e.target.value })}
              style={{
                width: '100%',
                padding: '0.6rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-color)',
                color: 'var(--text-color)',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem', color: 'var(--text-color)' }}>
              Domain / Server Hostname / IP
            </label>
            <input
              type="text"
              required
              value={config.domain}
              onChange={(e) => setConfig({ ...config, domain: e.target.value })}
              placeholder="e.g. school.example.com or 192.168.1.100"
              style={{
                width: '100%',
                padding: '0.6rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-color)',
                color: 'var(--text-color)',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem', color: 'var(--text-color)' }}>
              Backend API Port
            </label>
            <input
              type="number"
              min={1}
              max={65535}
              required
              value={config.api_port}
              onChange={(e) => setConfig({ ...config, api_port: parseInt(e.target.value, 10) || 8000 })}
              style={{
                width: '100%',
                padding: '0.6rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-color)',
                color: 'var(--text-color)',
              }}
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Default: 8000 (dev) / 8002 (fallback)</span>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem', color: 'var(--text-color)' }}>
              Frontend Web Port
            </label>
            <input
              type="number"
              min={1}
              max={65535}
              required
              value={config.frontend_port}
              onChange={(e) => setConfig({ ...config, frontend_port: parseInt(e.target.value, 10) || 5173 })}
              style={{
                width: '100%',
                padding: '0.6rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-color)',
                color: 'var(--text-color)',
              }}
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Default: 5173 (dev) / 5175 (fallback)</span>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem', color: 'var(--text-color)' }}>
              Environment Mode
            </label>
            <select
              value={config.environment}
              onChange={(e) => setConfig({ ...config, environment: e.target.value })}
              style={{
                width: '100%',
                padding: '0.6rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-color)',
                color: 'var(--text-color)',
              }}
            >
              <option value="development">Development (Local SQLite, test tooling)</option>
              <option value="production">Production (PostgreSQL, hardened security)</option>
              <option value="staging">Staging</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem', color: 'var(--text-color)' }}>
              Allowed Hosts Header (TrustedHost)
            </label>
            <input
              type="text"
              value={config.allowed_hosts}
              onChange={(e) => setConfig({ ...config, allowed_hosts: e.target.value })}
              style={{
                width: '100%',
                padding: '0.6rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-color)',
                color: 'var(--text-color)',
              }}
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Comma-separated hostnames</span>
          </div>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem', color: 'var(--text-color)' }}>
            Allowed CORS Origins
          </label>
          <textarea
            rows={2}
            value={config.cors_origins}
            onChange={(e) => setConfig({ ...config, cors_origins: e.target.value })}
            style={{
              width: '100%',
              padding: '0.6rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-color)',
              color: 'var(--text-color)',
              fontFamily: 'monospace',
              fontSize: '0.85rem',
            }}
          />
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Comma-separated origins (e.g. <code>http://localhost:5173,https://school.example.com</code>)
          </span>
        </div>

        <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.875rem', color: 'var(--text-color)' }}>
            <input
              type="checkbox"
              checked={config.allow_dev_seb_bypass}
              onChange={(e) => setConfig({ ...config, allow_dev_seb_bypass: e.target.checked })}
            />
            Allow Dev SEB Bypass (for testing without Safe Exam Browser)
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.875rem', color: 'var(--text-color)' }}>
            <input
              type="checkbox"
              checked={config.anonymizer_enabled}
              onChange={(e) => setConfig({ ...config, anonymizer_enabled: e.target.checked })}
            />
            Enable PII Anonymizer (Presidio)
          </label>
        </div>

        {/* Outgoing Email / SMTP Section (Optional) */}
        <div style={{ marginTop: '0.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-color)', margin: 0 }}>
              ✉️ Outgoing Email / SMTP Service (Optional)
            </h3>
            <span style={{ fontSize: '0.75rem', backgroundColor: 'var(--bg-color)', color: 'var(--text-muted)', padding: '0.15rem 0.5rem', borderRadius: '9999px', border: '1px solid var(--border-color)' }}>
              100% Optional
            </span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.825rem', marginBottom: '1rem', lineHeight: 1.4 }}>
            Sending emails is completely optional. PlannedEducation operates locally and dispatches all password resets and alerts using instant In-Platform Notifications without any email configuration. You can configure or update your school's SMTP credentials here at any time.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, marginBottom: '0.3rem', color: 'var(--text-color)' }}>
                SMTP Host / Relay
              </label>
              <input
                type="text"
                placeholder="e.g. smtp.gmail.com or mail.school.edu"
                value={config.smtp_host || ''}
                onChange={(e) => setConfig({ ...config, smtp_host: e.target.value })}
                style={{ width: '100%', padding: '0.6rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, marginBottom: '0.3rem', color: 'var(--text-color)' }}>
                SMTP Port
              </label>
              <input
                type="number"
                placeholder="587"
                value={config.smtp_port ?? 587}
                onChange={(e) => setConfig({ ...config, smtp_port: parseInt(e.target.value, 10) || 587 })}
                style={{ width: '100%', padding: '0.6rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, marginBottom: '0.3rem', color: 'var(--text-color)' }}>
                SMTP Username
              </label>
              <input
                type="text"
                placeholder="notifications@school.edu"
                value={config.smtp_user || ''}
                onChange={(e) => setConfig({ ...config, smtp_user: e.target.value })}
                style={{ width: '100%', padding: '0.6rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, marginBottom: '0.3rem', color: 'var(--text-color)' }}>
                SMTP Password / App Password
              </label>
              <input
                type="password"
                placeholder="••••••••••••"
                value={config.smtp_password || ''}
                onChange={(e) => setConfig({ ...config, smtp_password: e.target.value })}
                style={{ width: '100%', padding: '0.6rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, marginBottom: '0.3rem', color: 'var(--text-color)' }}>
                From Sender Email
              </label>
              <input
                type="text"
                placeholder="PlannedEducation &lt;noreply@school.edu&gt;"
                value={config.email_from || ''}
                onChange={(e) => setConfig({ ...config, email_from: e.target.value })}
                style={{ width: '100%', padding: '0.6rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', paddingTop: '1.5rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-color)' }}>
                <input
                  type="checkbox"
                  checked={config.smtp_use_tls ?? true}
                  onChange={(e) => setConfig({ ...config, smtp_use_tls: e.target.checked })}
                />
                Use STARTTLS (Port 587)
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-color)' }}>
                <input
                  type="checkbox"
                  checked={config.smtp_use_ssl ?? false}
                  onChange={(e) => setConfig({ ...config, smtp_use_ssl: e.target.checked })}
                />
                Use SSL (Port 465)
              </label>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
          <button
            type="button"
            onClick={fetchConfig}
            disabled={saving}
            style={{
              padding: '0.65rem 1.25rem',
              backgroundColor: 'transparent',
              color: 'var(--text-muted)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            Reset Form
          </button>
          <button
            type="submit"
            disabled={saving}
            style={{
              padding: '0.65rem 1.5rem',
              backgroundColor: 'var(--primary-color)',
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            {saving ? 'Saving...' : '💾 Save Configuration'}
          </button>
        </div>
      </form>
    </div>
  );
}
