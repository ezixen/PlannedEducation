import { useState, useEffect } from 'react';
import { useToast } from '../contexts/ToastContext';
import { useI18n } from '../contexts/I18nContext';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../api';

export interface DeploymentConfig {
  school_name: string;
  header_mode: 'text' | 'image' | 'none';
  header_image_url: string | null;
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
  admin_support_email?: string | null;
  home_exam_proctoring_enabled?: boolean;
  config_file_path?: string;
  last_modified?: string;
}

export function DeploymentConfigPanel() {
  const { success: showSuccess, error: showError } = useToast();
  const { t } = useI18n();
  const { user } = useAuth();
  const isSuperadmin = Boolean(user?.is_superadmin || user?.role === 'superadmin');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savingSupportEmail, setSavingSupportEmail] = useState(false);
  const [restartNotice, setRestartNotice] = useState(false);
  const [settingsPath, setSettingsPath] = useState('config/plannededucation.settings.json');
  const [settingsBusy, setSettingsBusy] = useState(false);
  const [config, setConfig] = useState<DeploymentConfig>({
    school_name: 'PlannedEducation School',
    header_mode: 'text',
    header_image_url: null,
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
    admin_support_email: '',
    home_exam_proctoring_enabled: false,
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
      showSuccess(t('deployment.saved_notice'));
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

  const handleSaveSupportEmail = async () => {
    setSavingSupportEmail(true);
    try {
      const res = await apiClient.put('/admin/support-email', {
        admin_support_email: (config.admin_support_email || '').trim(),
      });
      setConfig((prev) => ({
        ...prev,
        admin_support_email: res.data?.admin_support_email ?? prev.admin_support_email,
      }));
      showSuccess(t('deployment.support_email_saved'));
    } catch (err: any) {
      showError(err.response?.data?.detail || err.message || 'Failed to save support email');
    } finally {
      setSavingSupportEmail(false);
    }
  };

  const handleBackupConfig = async () => {
    try {
      const res = await apiClient.get('/admin/config/settings-bundle');
      const backupJson = JSON.stringify(res.data, null, 2);
      const dateStr = new Date().toISOString().slice(0, 10);
      const fileName = `plannededucation-settings-${dateStr}.json`;

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
          showSuccess(t('deployment.settings_saved_local', { name: fileHandle.name || fileName }));
          return;
        } catch (err: any) {
          if (err.name === 'AbortError') return;
        }
      }

      const blob = new Blob([backupJson], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showSuccess(t('deployment.settings_downloaded', { name: fileName }));
    } catch (err: any) {
      showError(err.response?.data?.detail || err.message || t('deployment.settings_export_failed'));
    }
  };

  const handleExportToServerPath = async () => {
    setSettingsBusy(true);
    try {
      const res = await apiClient.post('/admin/config/export-file', {
        path: settingsPath.trim(),
        include_smtp_password: false,
      });
      showSuccess(t('deployment.settings_exported_path', { path: res.data?.path || settingsPath }));
    } catch (err: any) {
      showError(err.response?.data?.detail || err.message || t('deployment.settings_export_failed'));
    } finally {
      setSettingsBusy(false);
    }
  };

  const handleImportFromServerPath = async () => {
    setSettingsBusy(true);
    try {
      const res = await apiClient.post('/admin/config/import-file', {
        path: settingsPath.trim(),
      });
      if (res.data?.config) {
        setConfig((prev) => ({ ...prev, ...res.data.config }));
      }
      setRestartNotice(true);
      showSuccess(t('deployment.settings_imported'));
    } catch (err: any) {
      showError(err.response?.data?.detail || err.message || t('deployment.settings_import_failed'));
    } finally {
      setSettingsBusy(false);
    }
  };

  const handleImportFromLocalFile = async (file: File | null) => {
    if (!file) return;
    setSettingsBusy(true);
    try {
      const text = await file.text();
      const bundle = JSON.parse(text);
      const res = await apiClient.post('/admin/config/import-file', { bundle });
      if (res.data?.config) {
        setConfig((prev) => ({ ...prev, ...res.data.config }));
      }
      setRestartNotice(true);
      showSuccess(t('deployment.settings_imported'));
    } catch (err: any) {
      showError(err.response?.data?.detail || err.message || t('deployment.settings_import_failed'));
    } finally {
      setSettingsBusy(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        {t('common.14')}
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          marginBottom: '1.5rem',
          gap: '1rem',
        }}
      >
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-color)', margin: 0 }}>
            {t('deployment.title')}
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            {t('deployment.subtitle')}{' '}
            <code style={{ background: 'var(--bg-color)', padding: '0.15rem 0.4rem', borderRadius: '4px' }}>
              {config.config_file_path || 'config/deployment.json'}
            </code>
            .
          </p>
        </div>
        <button
          type="button"
          onClick={() => void handleBackupConfig()}
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
          {t('deployment.backup_btn')}
        </button>
      </div>

      <div
        style={{
          marginBottom: '1.5rem',
          padding: '1rem 1.1rem',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          backgroundColor: 'var(--sidebar-bg)',
        }}
      >
        <h3 style={{ margin: '0 0 0.35rem 0', fontSize: '1rem', fontWeight: 600 }}>
          {t('deployment.settings_file_title')}
        </h3>
        <p style={{ margin: '0 0 0.85rem 0', fontSize: '0.825rem', color: 'var(--text-muted)', lineHeight: 1.45 }}>
          {t('deployment.settings_file_desc')}
        </p>
        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 500, marginBottom: '0.35rem' }}>
          {t('deployment.settings_path_label')}
        </label>
        <input
          type="text"
          value={settingsPath}
          onChange={(e) => setSettingsPath(e.target.value)}
          placeholder="config/plannededucation.settings.json"
          style={{
            width: '100%',
            marginBottom: '0.75rem',
            padding: '0.55rem 0.65rem',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-color)',
            backgroundColor: 'var(--bg-color)',
            color: 'var(--text-color)',
            fontFamily: 'monospace',
            fontSize: '0.85rem',
          }}
        />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem', alignItems: 'center' }}>
          <button
            type="button"
            disabled={settingsBusy || !settingsPath.trim()}
            onClick={() => void handleExportToServerPath()}
            style={{
              padding: '0.5rem 0.9rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-color)',
              color: 'var(--text-color)',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            {t('deployment.settings_export_path_btn')}
          </button>
          <button
            type="button"
            disabled={settingsBusy || !settingsPath.trim()}
            onClick={() => void handleImportFromServerPath()}
            style={{
              padding: '0.5rem 0.9rem',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              backgroundColor: 'var(--primary-color)',
              color: '#fff',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            {t('deployment.settings_import_path_btn')}
          </button>
          <label
            style={{
              padding: '0.5rem 0.9rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-color)',
              color: 'var(--text-color)',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.875rem',
            }}
          >
            {t('deployment.settings_import_local_btn')}
            <input
              type="file"
              accept=".json,.peconfig,application/json"
              style={{ display: 'none' }}
              onChange={(e) => {
                const file = e.target.files?.[0] || null;
                void handleImportFromLocalFile(file);
                e.target.value = '';
              }}
            />
          </label>
        </div>
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
            <span>⚠️</span> {t('deployment.restart_notice')}
          </div>
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
              {t('deployment.school_name_label')}
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

          {/* Custom Header Mode Selector */}
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem', color: 'var(--text-color)' }}>
              {t('deployment.header_mode_label')}
            </label>
            <select
              value={config.header_mode || 'text'}
              onChange={(e) => setConfig({ ...config, header_mode: e.target.value as 'text' | 'image' | 'none' })}
              style={{
                width: '100%',
                padding: '0.6rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-color)',
                color: 'var(--text-color)',
              }}
            >
              <option value="text">{t('deployment.header_mode_text')}</option>
              <option value="image">{t('deployment.header_mode_image')}</option>
              <option value="none">{t('deployment.header_mode_none')}</option>
            </select>
          </div>

          {/* Header Image URL (only shown when mode is image) */}
          {(config.header_mode || 'text') === 'image' && (
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem', color: 'var(--text-color)' }}>
                {t('deployment.header_image_url_label')}
              </label>
              <input
                type="text"
                placeholder="https://example.com/school-logo.png"
                value={config.header_image_url || ''}
                onChange={(e) => setConfig({ ...config, header_image_url: e.target.value })}
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
          )}

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem', color: 'var(--text-color)' }}>
              {t('deployment.domain_label')}
            </label>
            <input
              type="text"
              required
              value={config.domain}
              onChange={(e) => setConfig({ ...config, domain: e.target.value })}
              placeholder={t('deployment.domain_placeholder')}
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
              {t('deployment.api_port_label')}
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
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('deployment.api_port_hint')}</span>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem', color: 'var(--text-color)' }}>
              {t('deployment.frontend_port_label')}
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
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('deployment.frontend_port_hint')}</span>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem', color: 'var(--text-color)' }}>
              {t('deployment.environment_label')}
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
              <option value="development">{t('deployment.env_dev')}</option>
              <option value="production">{t('deployment.env_prod')}</option>
              <option value="staging">{t('deployment.env_staging')}</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem', color: 'var(--text-color)' }}>
              {t('deployment.allowed_hosts_label')}
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
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('deployment.allowed_hosts_hint')}</span>
          </div>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.35rem', color: 'var(--text-color)' }}>
            {t('deployment.cors_origins_label')}
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
            {t('deployment.cors_origins_hint')}
          </span>
        </div>

        <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.875rem', color: 'var(--text-color)' }}>
            <input
              type="checkbox"
              checked={config.allow_dev_seb_bypass}
              onChange={(e) => setConfig({ ...config, allow_dev_seb_bypass: e.target.checked })}
            />
            {t('deployment.seb_bypass_label')}
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.875rem', color: 'var(--text-color)' }}>
            <input
              type="checkbox"
              checked={config.anonymizer_enabled}
              onChange={(e) => setConfig({ ...config, anonymizer_enabled: e.target.checked })}
            />
            {t('deployment.anonymizer_label')}
          </label>
        </div>

        {/* Home-exam / remote proctoring — separate optional beta (superadmin gate) */}
        <div style={{ marginTop: '0.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--border-color)' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-color)', margin: '0 0 0.35rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            {t('home_exam.platform_title')}
            <span style={{ fontSize: '0.7rem', padding: '0.15rem 0.45rem', borderRadius: '9999px', backgroundColor: '#f59e0b', color: '#111' }}>
              {t('home_exam.beta_badge')}
            </span>
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.825rem', marginBottom: '0.75rem', lineHeight: 1.45 }}>
            {t('home_exam.platform_desc')}
          </p>
          <p style={{ color: '#92400e', fontSize: '0.8rem', marginBottom: '0.85rem', lineHeight: 1.45, backgroundColor: '#fffbeb', border: '1px solid #f59e0b', borderRadius: '6px', padding: '0.65rem 0.75rem' }}>
            {t('home_exam.legal_warning')}
          </p>
          <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.6rem', cursor: isSuperadmin ? 'pointer' : 'not-allowed', fontSize: '0.875rem', color: 'var(--text-color)', opacity: isSuperadmin ? 1 : 0.7 }}>
            <input
              type="checkbox"
              checked={Boolean(config.home_exam_proctoring_enabled)}
              disabled={!isSuperadmin}
              onChange={(e) => setConfig({ ...config, home_exam_proctoring_enabled: e.target.checked })}
              style={{ marginTop: '0.2rem' }}
            />
            <span>
              <strong>{t('home_exam.platform_toggle')}</strong>
              {!isSuperadmin && (
                <span style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                  {t('home_exam.superadmin_only')}
                </span>
              )}
            </span>
          </label>
        </div>

        {/* Platform support email (superadmin) */}
        <div style={{ marginTop: '0.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--border-color)' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-color)', margin: '0 0 0.35rem' }}>
            {t('deployment.support_email_label')}
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.825rem', marginBottom: '0.75rem', lineHeight: 1.4 }}>
            {t('deployment.support_email_hint')}
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <input
              type="email"
              value={config.admin_support_email || ''}
              onChange={(e) => setConfig({ ...config, admin_support_email: e.target.value })}
              placeholder="support@school.edu"
              style={{ flex: 1, minWidth: '240px', padding: '0.6rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
            />
            <button
              type="button"
              onClick={handleSaveSupportEmail}
              disabled={savingSupportEmail}
              style={{
                padding: '0.6rem 1rem',
                borderRadius: 'var(--radius-md)',
                border: 'none',
                backgroundColor: 'var(--primary-color)',
                color: '#fff',
                fontWeight: 600,
                cursor: savingSupportEmail ? 'not-allowed' : 'pointer',
              }}
            >
              {savingSupportEmail ? t('deployment.saving') : t('deployment.save_btn')}
            </button>
          </div>
        </div>

        {/* Outgoing Email / SMTP Section (Optional) */}
        <div style={{ marginTop: '0.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-color)', margin: 0 }}>
              {t('deployment.section_email')}
            </h3>
            <span style={{ fontSize: '0.75rem', backgroundColor: 'var(--bg-color)', color: 'var(--text-muted)', padding: '0.15rem 0.5rem', borderRadius: '9999px', border: '1px solid var(--border-color)' }}>
              100% Optional
            </span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.825rem', marginBottom: '1rem', lineHeight: 1.4 }}>
            {t('deployment.email_desc')}
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, marginBottom: '0.3rem', color: 'var(--text-color)' }}>
                {t('deployment.smtp_host_label')}
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
                {t('deployment.smtp_port_label')}
              </label>
              <input
                type="number"
                placeholder="587"
                min={1}
                max={65535}
                value={config.smtp_port ?? 587}
                onChange={(e) => setConfig({ ...config, smtp_port: parseInt(e.target.value, 10) || 587 })}
                style={{ width: '100%', padding: '0.6rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, marginBottom: '0.3rem', color: 'var(--text-color)' }}>
                {t('deployment.smtp_user_label')}
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
                {t('deployment.smtp_pass_label')}
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
                {t('deployment.email_from_label')}
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
                {t('deployment.use_tls_label')}
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-color)' }}>
                <input
                  type="checkbox"
                  checked={config.smtp_use_ssl ?? false}
                  onChange={(e) => setConfig({ ...config, smtp_use_ssl: e.target.checked })}
                />
                {t('deployment.use_ssl_label')}
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
            {t('common.29')}
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
            {saving ? t('deployment.saving') : t('deployment.save_btn')}
          </button>
        </div>
      </form>
    </div>
  );
}
