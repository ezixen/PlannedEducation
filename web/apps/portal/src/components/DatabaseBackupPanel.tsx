import { useState, useEffect } from 'react';
import { Database, Download, Trash2, Clock, ShieldCheck, RefreshCw, PlusCircle } from 'lucide-react';
import { apiClient } from '../api';
import { useToast } from '../contexts/ToastContext';

interface BackupItem {
  filename: string;
  size_bytes: number;
  size_mb: number;
  created_at: string;
  is_auto: boolean;
}

export function DatabaseBackupPanel() {
  const { success: showSuccess, error: showError } = useToast();
  const [backups, setBackups] = useState<BackupItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);

  const fetchBackups = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<BackupItem[]>('/admin/database/backups');
      setBackups(res.data);
    } catch (err: any) {
      showError('Failed to load database backups', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBackups();
  }, []);

  const handleCreateBackup = async () => {
    setCreating(true);
    try {
      const res = await apiClient.post('/admin/database/backup');
      showSuccess(`Database backup created: ${res.data.filename}`);
      await fetchBackups();
    } catch (err: any) {
      showError('Backup failed', err.response?.data?.detail || err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleDownload = (filename: string) => {
    // Download via hidden anchor with blob response
    const link = document.createElement('a');
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    
    // Fetch blob with auth headers
    apiClient.get(`/admin/database/backups/${encodeURIComponent(filename)}/download`, {
      responseType: 'blob',
    }).then(response => {
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
      link.href = blobUrl;
      link.click();
      window.URL.revokeObjectURL(blobUrl);
      link.remove();
      showSuccess(`Downloaded ${filename}`);
    }).catch(err => {
      showError('Download failed', err.response?.data?.detail || err.message);
      link.remove();
    });
  };

  const handleDelete = async (filename: string) => {
    if (!window.confirm(`Are you sure you want to delete backup "${filename}"? This action cannot be undone.`)) {
      return;
    }
    try {
      await apiClient.delete(`/admin/database/backups/${encodeURIComponent(filename)}`);
      showSuccess(`Backup ${filename} deleted`);
      setBackups(prev => prev.filter(b => b.filename !== filename));
    } catch (err: any) {
      showError('Failed to delete backup', err.response?.data?.detail || err.message);
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      const day = String(d.getDate()).padStart(2, '0');
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const year = d.getFullYear();
      const hours = String(d.getHours()).padStart(2, '0');
      const minutes = String(d.getMinutes()).padStart(2, '0');
      return `${day}/${month}/${year} ${hours}:${minutes}`;
    } catch {
      return isoString;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Top Banner & Info */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '1rem',
        }}
      >
        <div
          style={{
            padding: '1.25rem',
            backgroundColor: 'var(--sidebar-bg)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-lg)',
            display: 'flex',
            gap: '1rem',
            alignItems: 'flex-start',
          }}
        >
          <div
            style={{
              padding: '0.75rem',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'rgba(59, 130, 246, 0.1)',
              color: '#3b82f6',
            }}
          >
            <Clock size={24} />
          </div>
          <div>
            <h4 style={{ margin: '0 0 0.25rem', fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-color)' }}>
              Midnight Auto-Backup
            </h4>
            <p style={{ margin: 0, fontSize: '0.825rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
              Active background scheduler generates a full snapshot every night at <strong>00:00 UTC</strong>.
            </p>
          </div>
        </div>

        <div
          style={{
            padding: '1.25rem',
            backgroundColor: 'var(--sidebar-bg)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-lg)',
            display: 'flex',
            gap: '1rem',
            alignItems: 'flex-start',
          }}
        >
          <div
            style={{
              padding: '0.75rem',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              color: '#10b981',
            }}
          >
            <ShieldCheck size={24} />
          </div>
          <div>
            <h4 style={{ margin: '0 0 0.25rem', fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-color)' }}>
              30-Day Retention Policy
            </h4>
            <p style={{ margin: 0, fontSize: '0.825rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
              Daily backups are retained for 30 days and purged automatically. Manual snapshots are preserved indefinitely.
            </p>
          </div>
        </div>
      </div>

      {/* Main Table Card */}
      <div
        style={{
          padding: '1.5rem',
          backgroundColor: 'var(--sidebar-bg)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-color)',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1.25rem',
            flexWrap: 'wrap',
            gap: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Database size={20} style={{ color: 'var(--primary-color)' }} />
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-color)' }}>
              Database Snapshots ({backups.length})
            </h3>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={fetchBackups}
              disabled={loading}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.5rem 0.85rem',
                backgroundColor: 'var(--bg-color)',
                color: 'var(--text-color)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.85rem',
                fontWeight: 500,
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              Refresh
            </button>

            <button
              onClick={handleCreateBackup}
              disabled={creating}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.5rem 1rem',
                backgroundColor: 'var(--primary-color)',
                color: '#ffffff',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: creating ? 'not-allowed' : 'pointer',
              }}
            >
              <PlusCircle size={16} />
              {creating ? 'Creating Snapshot...' : 'Create Backup Now'}
            </button>
          </div>
        </div>

        {loading && backups.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
            Loading backup files...
          </div>
        ) : backups.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
            <p style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>No database backups created yet.</p>
            <p style={{ fontSize: '0.85rem', margin: 0 }}>
              Click <strong>Create Backup Now</strong> above or wait for the automatic midnight run.
            </p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                  <th style={{ padding: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase' }}>
                    Snapshot Filename
                  </th>
                  <th style={{ padding: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase' }}>
                    Type
                  </th>
                  <th style={{ padding: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase' }}>
                    Created (dd/mm/yyyy)
                  </th>
                  <th style={{ padding: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase' }}>
                    Size
                  </th>
                  <th style={{ padding: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase', textAlign: 'right' }}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {backups.map(b => (
                  <tr key={b.filename} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace', color: 'var(--text-color)', fontWeight: 500 }}>
                      {b.filename}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      {b.is_auto ? (
                        <span
                          style={{
                            padding: '0.2rem 0.5rem',
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            color: '#3b82f6',
                            borderRadius: '9999px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                          }}
                        >
                          🕒 Midnight Auto
                        </span>
                      ) : (
                        <span
                          style={{
                            padding: '0.2rem 0.5rem',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            color: '#10b981',
                            borderRadius: '9999px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                          }}
                        >
                          👤 Manual Snapshot
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-muted)' }}>
                      {formatDate(b.created_at)}
                    </td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-muted)' }}>
                      {b.size_mb > 0 ? `${b.size_mb} MB` : `${b.size_bytes} B`}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '0.5rem' }}>
                        <button
                          onClick={() => handleDownload(b.filename)}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            padding: '0.35rem 0.65rem',
                            backgroundColor: 'var(--bg-color)',
                            color: 'var(--primary-color)',
                            border: '1px solid var(--border-color)',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                          title="Download database snapshot"
                        >
                          <Download size={14} /> Download
                        </button>
                        <button
                          onClick={() => handleDelete(b.filename)}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            padding: '0.35rem 0.65rem',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            color: '#ef4444',
                            border: '1px solid rgba(239, 68, 68, 0.2)',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                          title="Delete snapshot"
                        >
                          <Trash2 size={14} /> Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

