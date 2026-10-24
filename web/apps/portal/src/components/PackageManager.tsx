import { useState, useEffect, useCallback } from 'react';
import {
  packagesService,
  downloadBlob,
  MODULE_LANGUAGES,
  type PackageMetadata,
  type PackageExportRequest,
  type PackageImportResult,
  type CurriculumModuleSummary,
} from '../services/packages';
import { useToast } from '../contexts/ToastContext';
import { useI18n } from '../contexts/I18nContext';

interface PackageManagerProps {
  examId?: string;
  onPackageImported?: (examId: string) => void;
}

export function PackageManager({ examId, onPackageImported }: PackageManagerProps) {
  const { t, locale } = useI18n();
  const { success: showSuccess, error: showError } = useToast();
  const [packages, setPackages] = useState<PackageMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [validating, setValidating] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationResult, setValidationResult] = useState<{ valid: boolean; errors: string[]; warnings: string[] } | null>(null);
  const [showExportModal, setShowExportModal] = useState(false);

  const defaultLangObj = MODULE_LANGUAGES.find(l => l.code === locale) || MODULE_LANGUAGES[0];
  const [importLanguage, setImportLanguage] = useState(defaultLangObj.code);
  const [importCountry, setImportCountry] = useState(defaultLangObj.defaultCountry);
  const [saveImportToServer, setSaveImportToServer] = useState(true);

  const [exportOptions, setExportOptions] = useState<PackageExportRequest>({
    exam_id: examId || '',
    include_answers: true,
    include_rubrics: true,
    include_variables: true,
    format: 'json',
    compress: false,
    language: defaultLangObj.code,
    language_name: defaultLangObj.name,
    country: defaultLangObj.defaultCountry,
    subject: 'general',
    grade_level: 'grade-01',
    save_to_server: true,
  });

  // Curriculum Browser State
  const [curriculumModules, setCurriculumModules] = useState<CurriculumModuleSummary[]>([]);
  const [curriculumTotal, setCurriculumTotal] = useState(0);
  const [countriesList, setCountriesList] = useState<string[]>([]);
  const [languagesList, setLanguagesList] = useState<{ code: string; name: string }[]>([]);
  const [gradesList, setGradesList] = useState<string[]>([]);
  const [subjectsList, setSubjectsList] = useState<string[]>([]);
  const [filterCountry, setFilterCountry] = useState('');
  const [filterLanguage, setFilterLanguage] = useState('');
  const [filterGrade, setFilterGrade] = useState('');
  const [filterSubject, setFilterSubject] = useState('');
  const [filterSearch, setFilterSearch] = useState('');
  const [loadingCurriculum, setLoadingCurriculum] = useState(false);

  // Sync saved exam metadata if available
  useEffect(() => {
    if (!examId) return;
    try {
      const raw = localStorage.getItem(`pe_exam_meta_${examId}`);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed.language) {
          const found = MODULE_LANGUAGES.find(l => l.code === parsed.language);
          setExportOptions(prev => ({
            ...prev,
            exam_id: examId,
            language: parsed.language,
            language_name: parsed.language_name || found?.name || parsed.language,
            country: parsed.country || found?.defaultCountry || 'usa',
          }));
        }
      }
    } catch {
      // ignore storage errors
    }
  }, [examId]);

  const loadPackages = useCallback(async () => {
    setLoading(true);
    try {
      const response = await packagesService.listPackages();
      setPackages(response.packages);
    } catch (err: any) {
      showError(t('errors.1'), err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }, [showError, t]);

  const loadCurriculum = useCallback(async () => {
    setLoadingCurriculum(true);
    try {
      const res = await packagesService.listCurriculumModules({
        country: filterCountry || undefined,
        language: filterLanguage || undefined,
        grade_level: filterGrade || undefined,
        subject: filterSubject || undefined,
        search: filterSearch || undefined,
        limit: 24,
        offset: 0,
      });
      setCurriculumModules(res.modules);
      setCurriculumTotal(res.total);
      setCountriesList(res.countries);
      setLanguagesList(res.languages);
      setGradesList(res.grades);
      setSubjectsList(res.subjects);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingCurriculum(false);
    }
  }, [filterCountry, filterLanguage, filterGrade, filterSubject, filterSearch]);

  useEffect(() => {
    void loadPackages();
  }, [loadPackages]);

  useEffect(() => {
    void loadCurriculum();
  }, [loadCurriculum]);

  const handleExport = async () => {
    if (!examId) {
      showError(t('errors.5'));
      return;
    }

    setExporting(true);
    try {
      const langObj = MODULE_LANGUAGES.find(l => l.code === exportOptions.language);
      const result = await packagesService.exportPackage({
        ...exportOptions,
        exam_id: examId,
        language_name: langObj?.name || exportOptions.language,
      });

      if (result.content instanceof Blob) {
        downloadBlob(result.content, result.filename);
      } else {
        const blob = new Blob([result.content], { type: result.media_type });
        downloadBlob(blob, result.filename);
      }

      showSuccess(t('teacher_dashboard.package_exported'));
      setShowExportModal(false);
      void loadCurriculum();
    } catch (err: any) {
      showError(t('errors.1'), err.response?.data?.detail || err.message);
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
    if (!selectedFile) return;

    setValidating(true);
    try {
      const result = await packagesService.validatePackage(selectedFile);
      setValidationResult(result);
      if (result.valid) {
        showSuccess(t('packages.8.1'));
      } else {
        showError(t('packages.8.2'), { key: 'validation-error' });
      }
    } catch (err: any) {
      showError(t('packages.8.2'), err.response?.data?.detail || err.message);
    } finally {
      setValidating(false);
    }
  };

  const handleImport = async () => {
    if (!selectedFile) return;

    setImporting(true);
    try {
      const langObj = MODULE_LANGUAGES.find(l => l.code === importLanguage);
      const result: PackageImportResult = await packagesService.importPackage(selectedFile, {
        language: importLanguage,
        language_name: langObj?.name || importLanguage,
        country: importCountry,
        save_to_server: saveImportToServer,
      });

      if (result.success) {
        showSuccess(`${t('packages.9')}: ${result.questions_imported} ${t('packages.9.1')}`);
        if (result.exam_id) {
          localStorage.setItem(
            `pe_exam_meta_${result.exam_id}`,
            JSON.stringify({
              language: importLanguage,
              language_name: langObj?.name || importLanguage,
              country: importCountry,
            })
          );
          if (onPackageImported) {
            onPackageImported(result.exam_id);
          }
        }
        setSelectedFile(null);
        setValidationResult(null);
        void loadPackages();
        void loadCurriculum();
      } else {
        showError(t('packages.8.2'), { key: 'import-error' });
      }
    } catch (err: any) {
      showError(t('packages.8.2'), err.response?.data?.detail || err.message);
    } finally {
      setImporting(false);
    }
  };

  const handleImportCurriculum = async (mod: CurriculumModuleSummary) => {
    setImporting(true);
    try {
      const result = await packagesService.importCurriculumModule(mod.path);
      if (result.success && result.exam_id) {
        localStorage.setItem(
          `pe_exam_meta_${result.exam_id}`,
          JSON.stringify({
            language: mod.language,
            language_name: mod.language_name,
            country: mod.country,
          })
        );
        showSuccess(`${t('packages.9')}: ${mod.name} (${mod.language_name})`);
        if (onPackageImported) {
          onPackageImported(result.exam_id);
        }
      }
    } catch (err: any) {
      showError(t('errors.1'), err.response?.data?.detail || err.message);
    } finally {
      setImporting(false);
    }
  };

  const handleImportRepoPackage = async (pkg: PackageMetadata) => {
    setImporting(true);
    try {
      const result = await packagesService.importRepositoryPackage(pkg.id);
      if (result.success && result.exam_id) {
        showSuccess(`${t('packages.9')}: ${pkg.name}`);
        if (onPackageImported) {
          onPackageImported(result.exam_id);
        }
      }
    } catch (err: any) {
      showError(t('errors.1'), err.response?.data?.detail || err.message);
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
      showSuccess(t('toast.32'));
    } catch (err: any) {
      showError(t('errors.1'), err.response?.data?.detail || err.message);
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
            {exporting ? t('common.loading') : t('packages.2')}
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
              maxWidth: '520px',
              width: '90%',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
            }}
            onClick={e => e.stopPropagation()}
          >
            <h3 style={{ margin: '0 0 1.5rem 0' }}>{t('packages.5')}</h3>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.35rem', fontSize: '0.85rem' }}>
                  🌐 {t('settings.tab_language')}
                </label>
                <select
                  value={exportOptions.language || 'en'}
                  onChange={e => {
                    const code = e.target.value;
                    const found = MODULE_LANGUAGES.find(l => l.code === code);
                    setExportOptions(prev => ({
                      ...prev,
                      language: code,
                      language_name: found?.name || code,
                      country: found?.defaultCountry || prev.country || 'usa',
                    }));
                  }}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
                >
                  {MODULE_LANGUAGES.map(l => (
                    <option key={l.code} value={l.code}>
                      {l.name} ({l.code.toUpperCase()})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.35rem', fontSize: '0.85rem' }}>
                  📁 {t('common.21')}
                </label>
                <input
                  type="text"
                  value={exportOptions.country || ''}
                  onChange={e => setExportOptions(prev => ({ ...prev, country: e.target.value }))}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
                />
              </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={exportOptions.include_answers}
                  onChange={e => setExportOptions(prev => ({ ...prev, include_answers: e.target.checked }))}
                />
                {t('packages.5.1')}
              </label>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={exportOptions.include_rubrics}
                  onChange={e => setExportOptions(prev => ({ ...prev, include_rubrics: e.target.checked }))}
                />
                {t('packages.5.2')}
              </label>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={exportOptions.include_variables}
                  onChange={e => setExportOptions(prev => ({ ...prev, include_variables: e.target.checked }))}
                />
                {t('packages.5.3')}
              </label>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem' }}>{t('packages.5.4')}</label>
              <select
                value={exportOptions.format}
                onChange={e => setExportOptions(prev => ({ ...prev, format: e.target.value as 'json' | 'yaml' }))}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
              >
                <option value="json">{t('packages.5.5')}</option>
                <option value="yaml">{t('packages.5.6')}</option>
              </select>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={exportOptions.compress}
                  onChange={e => setExportOptions(prev => ({ ...prev, compress: e.target.checked }))}
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
                {exporting ? t('common.loading') : t('teacher_dashboard.export_download')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import Section with Language & Country Folder Selection */}
      <div style={{ marginBottom: '2rem', padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
        <h3 style={{ margin: '0 0 0.75rem 0' }}>{t('packages.import_btn')}</h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.875rem' }}>
          {t('packages.4.1')}
        </p>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem', alignItems: 'center' }}>
          <select
            aria-label={t('settings.tab_language')}
            value={importLanguage}
            onChange={e => {
              const code = e.target.value;
              const found = MODULE_LANGUAGES.find(l => l.code === code);
              setImportLanguage(code);
              if (found) setImportCountry(found.defaultCountry);
            }}
            style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
          >
            {MODULE_LANGUAGES.map(l => (
              <option key={l.code} value={l.code}>
                🌐 {l.name} ({l.code.toUpperCase()})
              </option>
            ))}
          </select>

          <input
            type="text"
            value={importCountry}
            onChange={e => setImportCountry(e.target.value)}
            placeholder="country"
            style={{ width: '140px', padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
          />

          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={saveImportToServer}
              onChange={e => setSaveImportToServer(e.target.checked)}
            />
            📁 {importCountry || 'server'}
          </label>
        </div>

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
            {validating ? t('common.loading') : t('packages.4')}
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
            {importing ? t('common.loading') : t('packages.7')}
          </button>
        </div>

        {selectedFile && (
          <p style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            {selectedFile.name} ({Math.round(selectedFile.size / 1024)} KB)
          </p>
        )}

        {validationResult && (
          <div style={{ marginTop: '1rem', padding: '1rem', borderRadius: '6px', backgroundColor: validationResult.valid ? '#ecfdf5' : '#fef2f2', border: `1px solid ${validationResult.valid ? '#a7f3d0' : '#fecaca'}` }}>
            <h4 style={{ margin: '0 0 0.5rem 0', color: validationResult.valid ? '#065f46' : '#991b1b' }}>
              {validationResult.valid ? `✓ ${t('packages.8')}` : `✗ ${t('packages.8.2')}`}
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

      {/* Curriculum & Country Modules Browser */}
      <div style={{ marginBottom: '2rem', padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <h3 style={{ margin: 0 }}>🌍 {t('packages.available_title')} ({curriculumTotal})</h3>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <select
            value={filterCountry}
            onChange={e => setFilterCountry(e.target.value)}
            style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
          >
            <option value="">📁 ({countriesList.length})</option>
            {countriesList.map(c => (
              <option key={c} value={c}>{c.toUpperCase()}</option>
            ))}
          </select>

          <select
            value={filterLanguage}
            onChange={e => setFilterLanguage(e.target.value)}
            style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
          >
            <option value="">🌐 {t('settings.tab_language')} ({languagesList.length})</option>
            {languagesList.map(l => (
              <option key={l.code} value={l.code}>
                {l.name} ({l.code.toUpperCase()})
              </option>
            ))}
          </select>

          <select
            value={filterGrade}
            onChange={e => setFilterGrade(e.target.value)}
            style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
          >
            <option value="">🎓 ({gradesList.length})</option>
            {gradesList.map(g => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>

          <select
            value={filterSubject}
            onChange={e => setFilterSubject(e.target.value)}
            style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
          >
            <option value="">📚 ({subjectsList.length})</option>
            {subjectsList.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          <input
            type="text"
            value={filterSearch}
            onChange={e => setFilterSearch(e.target.value)}
            placeholder={t('common.21')}
            style={{ flex: 1, minWidth: '160px', padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
          />
        </div>

        {loadingCurriculum ? (
          <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-secondary)' }}>
            {t('common.loading')}
          </div>
        ) : curriculumModules.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-secondary)' }}>
            {t('packages.11')}
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '0.75rem', maxHeight: '420px', overflowY: 'auto' }}>
            {curriculumModules.map(mod => (
              <div
                key={mod.path}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '0.85rem 1rem',
                  backgroundColor: 'var(--card-bg)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  gap: '1rem',
                  flexWrap: 'wrap',
                }}
              >
                <div style={{ flex: 1, minWidth: '220px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.25rem' }}>
                    <h4 style={{ margin: 0 }}>{mod.name}</h4>
                    <span
                      style={{
                        padding: '0.15rem 0.5rem',
                        borderRadius: '9999px',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        backgroundColor: 'rgba(59, 130, 246, 0.15)',
                        color: '#3b82f6',
                      }}
                    >
                      🌐 {mod.language.toUpperCase()} — {mod.language_name}
                    </span>
                    <span
                      style={{
                        padding: '0.15rem 0.5rem',
                        borderRadius: '9999px',
                        fontSize: '0.75rem',
                        backgroundColor: 'rgba(16, 185, 129, 0.15)',
                        color: '#10b981',
                      }}
                    >
                      📁 {mod.country}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                    {mod.subject} • {mod.grade_level} • {mod.question_count} Qs • {mod.total_points} pts
                  </div>
                </div>
                <button
                  onClick={() => handleImportCurriculum(mod)}
                  disabled={importing}
                  style={{
                    padding: '0.45rem 0.95rem',
                    backgroundColor: '#10b981',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: importing ? 'not-allowed' : 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                  }}
                >
                  {t('packages.7')}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Repository Packages List */}
      <div>
        <h3 style={{ margin: '0 0 1rem 0' }}>{t('packages.10')}</h3>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
            {t('common.loading')}
          </div>
        ) : packages.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
            {t('packages.11')}
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '1rem' }}>
            {packages.map(pkg => (
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
                    v{pkg.version} • {pkg.subject || '-'} • {pkg.grade_level || '-'}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={() => handleImportRepoPackage(pkg)}
                    style={{
                      padding: '0.5rem 1rem',
                      backgroundColor: '#10b981',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.875rem',
                    }}
                  >
                    {t('packages.7')}
                  </button>
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
                    {t('packages.12')}
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
