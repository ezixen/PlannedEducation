import { useState, useEffect, useCallback } from 'react';
import { packagesService, type PackageMetadata, type PackageExportRequest, type PackageImportResult } from '../services/packages';
import { downloadBlob } from '../services/packages';
import { useToast } from '../contexts/ToastContext';
import { useI18n } from '../contexts/I18nContext';

interface PackageManagerProps {
  examId?: string;
  onPackageImported?: (examId: string) => void;
}

export function PackageManager({ examId, onPackageImported }: PackageManagerProps) {
  const { t } = useI18n();
  const { success: showSuccess, error: showError } = useToast();
  const [packages, setPackages] = useState<PackageMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [validating, setValidating] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationResult, setValidationResult] = useState<{ valid: boolean; errors: string[]; warnings: string[] } | null>(null);
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportOptions, setExportOptions] = useState<PackageExportRequest>({
    exam_id: examId || '',
    include_answers: true,
    include_rubrics: true,
    include_variables: true,
    format: 'json',
    compress: false,
  });

  const loadPackages = useCallback(async () => {
    setLoading(true);
    try {
      const response = await packagesService.listPackages();
      setPackages(response.packages);
    } catch (err: any) {
      showError('Failed to load packages', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }, [showError]);

  useEffect(() => {
    if (examId) {
      void loadPackages();
    }
  }, [examId, loadPackages]);

  const handleExport = async () => {
    if (!examId) {
      showError('No exam selected for export');
      return;
    }

    setExporting(true);
    try {
      const result = await packagesService.exportPackage({
        ...exportOptions,
        exam_id: examId,
      });

      // Download the file
      if (result.content instanceof Blob) {
        downloadBlob(result.content, result.filename);
      } else {
        // For text content
        const blob = new Blob([result.content], { type: result.media_type });
        downloadBlob(blob, result.filename);
      }

      showSuccess('Package exported successfully!');
      setShowExportModal(false);
    } catch (err: any) {
      showError('Export failed', err.response?.data?.detail || err.message);
    } finally {
      setExporting(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setValidationResult(null);
    }
  };

  const handleValidate = async () => {
    if (!selectedFile) {
      showError('Please select a file first');
      return;
    }

    setValidating(true);
    try {
      const result = await packagesService.validatePackage(selectedFile);
      setValidationResult(result);
      if (result.valid) {
        showSuccess('Package is valid!');
      } else {
        showError('Package validation failed', { key: 'validation-error' });
        console.error('Validation errors:', result.errors.join(', '));
      }
    } catch (err: any) {
      showError('Validation failed', err.response?.data?.detail || err.message);
    } finally {
      setValidating(false);
    }
  };

  const handleImport = async () => {
    if (!selectedFile) {
      showError('Please select a file first');
      return;
    }

    if (validationResult && !validationResult.valid) {
      if (!window.confirm('Package has validation errors. Import anyway?')) {
        return;
      }
    }

    setImporting(true);
    try {
      const result: PackageImportResult = await packagesService.importPackage(selectedFile);
      
      if (result.success) {
        showSuccess(`Package imported! ${result.questions_imported} questions, ${result.rubrics_imported} rubrics.`);
        if (result.exam_id && onPackageImported) {
          onPackageImported(result.exam_id);
        }
        setSelectedFile(null);
        setValidationResult(null);
        loadPackages();
      } else {
        showError('Import failed', { key: 'import-error' });
        console.error('Import errors:', result.errors.join(', '));
      }
    } catch (err: any) {
      showError('Import failed', err.response?.data?.detail || err.message);
    } finally {
      setImporting(false);
    }
  };

  const handleDownload = async (pkg: PackageMetadata) => {
    try {
      const result = await packagesService.downloadPackage(pkg.id, 'json');
      if (result.content instanceof Blob) {
        downloadBlob(result.content, result.filename);
      }
      showSuccess('Package downloaded!');
    } catch (err: any) {
      showError('Download failed', err.response?.data?.detail || err.message);
    }
  };

  return (
    <div style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h2 style={{ margin: 0 }}>{t('packages.manager_title')}</h2>
        {examId && (
          <button
            onClick={() => setShowExportModal(true)}
            disabled={exporting}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#3b82f6',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: exporting ? 'not-allowed' : 'pointer',
            }}
          >
            {exporting ? 'Exporting...' : t('packages.2')}
          </button>
        )}
      </div>

      {/* Export Modal */}
      {showExportModal && (
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
          onClick={() => setShowExportModal(false)}
        >
          <div
            style={{
              backgroundColor: 'var(--card-bg)',
              borderRadius: '12px',
              padding: '2rem',
              maxWidth: '500px',
              width: '90%',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
            }}
            onClick={e => e.stopPropagation()}
          >
            <h3 style={{ margin: '0 0 1.5rem 0' }}>{t('packages.5')}</h3>
            
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={exportOptions.include_answers}
                  onChange={(e) => setExportOptions(prev => ({ ...prev, include_answers: e.target.checked }))}
                />
                {t('packages.5.1')}
              </label>
            </div>
            
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={exportOptions.include_rubrics}
                  onChange={(e) => setExportOptions(prev => ({ ...prev, include_rubrics: e.target.checked }))}
                />
                {t('packages.5.2')}
              </label>
            </div>
            
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={exportOptions.include_variables}
                  onChange={(e) => setExportOptions(prev => ({ ...prev, include_variables: e.target.checked }))}
                />
                {t('packages.5.3')}
              </label>
            </div>
            
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem' }}>{t('packages.5.4')}</label>
              <select
                value={exportOptions.format}
                onChange={(e) => setExportOptions(prev => ({ ...prev, format: e.target.value as 'json' | 'yaml' }))}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
              >
                <option value="json">JSON</option>
                <option value="yaml">YAML</option>
              </select>
            </div>
            
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={exportOptions.compress}
                  onChange={(e) => setExportOptions(prev => ({ ...prev, compress: e.target.checked }))}
                />
                {t('packages.5.7')}
              </label>
            </div>

            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
              <button
                onClick={() => setShowExportModal(false)}
                disabled={exporting}
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
                onClick={handleExport}
                disabled={exporting}
                style={{
                  padding: '0.75rem 1.5rem',
                  backgroundColor: '#3b82f6',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: exporting ? 'not-allowed' : 'pointer',
                  fontWeight: '600',
                }}
              >
                {exporting ? 'Exporting...' : 'Export & Download'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import Section */}
      <div style={{ marginBottom: '2rem', padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
        <h3 style={{ margin: '0 0 1rem 0' }}>{t('packages.import_btn')}</h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.875rem' }}>
          Upload a test package (JSON or YAML) to create a new exam with questions and rubrics.
        </p>
        
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <input
            type="file"
            accept=".json,.yaml,.yml,.json.gz,.yaml.gz,.yml.gz"
            onChange={handleFileSelect}
            style={{ flex: 1, minWidth: '200px' }}
          />
          <button
            onClick={handleValidate}
            disabled={!selectedFile || validating}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#8b5cf6',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: validating || !selectedFile ? 'not-allowed' : 'pointer',
            }}
          >
            {validating ? 'Validating...' : 'Validate'}
          </button>
          <button
            onClick={handleImport}
            disabled={!selectedFile || importing}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#10b981',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: importing || !selectedFile ? 'not-allowed' : 'pointer',
            }}
          >
            {importing ? 'Importing...' : 'Import'}
          </button>
        </div>

        {selectedFile && (
          <p style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Selected: {selectedFile.name} ({Math.round(selectedFile.size / 1024)} KB)
          </p>
        )}

        {validationResult && (
          <div style={{ marginTop: '1rem', padding: '1rem', borderRadius: '6px', backgroundColor: validationResult.valid ? '#ecfdf5' : '#fef2f2', border: `1px solid ${validationResult.valid ? '#a7f3d0' : '#fecaca'}` }}>
            <h4 style={{ margin: '0 0 0.5rem 0', color: validationResult.valid ? '#065f46' : '#991b1b' }}>
              {validationResult.valid ? '✓ Package Valid' : '✗ Package Invalid'}
            </h4>
            {validationResult.errors.length > 0 && (
              <ul style={{ margin: 0, paddingLeft: '1.25rem', color: '#991b1b' }}>
                {validationResult.errors.map((err, i) => (
                  <li key={i} style={{ fontSize: '0.875rem' }}>{err}</li>
                ))}
              </ul>
            )}
            {validationResult.warnings.length > 0 && (
              <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.25rem', color: '#92400e' }}>
                {validationResult.warnings.map((warn, i) => (
                  <li key={i} style={{ fontSize: '0.875rem' }}>{warn}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {/* Packages List */}
      <div>
        <h3 style={{ margin: '0 0 1rem 0' }}>{t('packages.available_title')}</h3>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
            Loading packages...
          </div>
        ) : packages.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
            {t('packages.11')}
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '1rem' }}>
            {packages.map((pkg) => (
              <div
                key={pkg.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '1rem',
                  backgroundColor: 'var(--card-bg)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                }}
              >
                <div>
                  <h4 style={{ margin: '0 0 0.25rem 0' }}>{pkg.name}</h4>
                  <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    v{pkg.version} • {pkg.subject || 'No subject'} • {pkg.grade_level || 'No grade'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                    By {pkg.author} • {new Date(pkg.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={() => handleDownload(pkg)}
                    style={{
                      padding: '0.5rem 1rem',
                      backgroundColor: '#3b82f6',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.875rem',
                    }}
                  >
                    Download
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}