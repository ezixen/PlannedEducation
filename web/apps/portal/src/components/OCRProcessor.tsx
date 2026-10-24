import { useState } from 'react';
import { apiClient } from '../api';
import { useToast } from '../contexts/ToastContext';
import { useI18n } from '../contexts/I18nContext';
import { Upload, Copy, Download, Trash2 } from 'lucide-react';

interface BulkResultItem {
  filename: string;
  page_index: number;
  text: string;
  confidence: number;
  language: string;
  subject: string;
  error?: string | null;
}

export function OCRProcessor() {
  const { t } = useI18n();
  const { success: showSuccess, error: showError } = useToast();

  const [activeTab, setActiveTab] = useState<'single' | 'bulk'>('single');

  // Single Page State
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [result, setResult] = useState<{
    text: string;
    confidence: number;
    language: string;
    bounding_boxes?: any[];
    error?: string;
  } | null>(null);

  // Bulk Multi-Page State
  const [bulkFiles, setBulkFiles] = useState<File[]>([]);
  const [bulkPreviews, setBulkPreviews] = useState<string[]>([]);
  const [bulkResults, setBulkResults] = useState<BulkResultItem[]>([]);
  const [bulkSubject, setBulkSubject] = useState('math');

  // Common Options
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState('eng');
  const [isMath, setIsMath] = useState(true);

  const handleSingleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
      setResult(null);
    }
  };

  const handleBulkFilesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArr = Array.from(e.target.files);
      setBulkFiles(filesArr);
      const previews = filesArr.map((f) => URL.createObjectURL(f));
      setBulkPreviews(previews);
      setBulkResults([]);
    }
  };

  const handleProcessSingle = async () => {
    if (!imageFile) {
      showError(t('ocr.select_image_first'));
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', imageFile);
      formData.append('language', language);
      formData.append('is_math', isMath.toString());

      const response = await apiClient.post('/ocr/process-upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setResult(response.data);
      showSuccess(t('ocr.completed_confidence', { percent: String(Math.round(response.data.confidence * 100)) }));
    } catch (err: any) {
      showError(t('ocr.processing_failed'), err.response?.data?.detail || err.message);
      setResult({ text: '', confidence: 0, language, error: err.response?.data?.detail || err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleProcessBulk = async () => {
    if (bulkFiles.length === 0) {
      showError(t('ocr.select_image_first'));
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      bulkFiles.forEach((file) => {
        formData.append('files', file);
      });
      formData.append('language', language);
      formData.append('subject', bulkSubject);
      formData.append('is_math', (bulkSubject === 'math' || isMath).toString());

      const response = await apiClient.post('/ocr/bulk-upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setBulkResults(response.data.results || []);
      showSuccess(`${response.data.results?.length || 0} pages digitized successfully!`);
    } catch (err: any) {
      showError(t('ocr.processing_failed'), err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    showSuccess(t('ocr.copy_digitized'));
  };

  const downloadTextFile = (filename: string, content: string) => {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename.replace(/\.[^/.]+$/, '') + '-digitized.txt';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
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
    padding: '0.625rem 1.5rem',
    backgroundColor: 'var(--primary-color)',
    color: '#fff',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '0.95rem',
  };

  return (
    <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
      {/* Header & Tabs */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--text-color)' }}>{t('ocr.1')}</h3>
          <p style={{ color: 'var(--text-muted)', margin: '0.35rem 0 0', fontSize: '0.9rem' }}>
            {t('ocr.desc')}
          </p>
        </div>

        {/* Tab Buttons */}
        <div style={{ display: 'flex', gap: '0.5rem', backgroundColor: 'var(--bg-color)', padding: '0.25rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
          <button
            type="button"
            onClick={() => setActiveTab('single')}
            style={{
              padding: '0.4rem 0.85rem',
              borderRadius: 'var(--radius-sm, 6px)',
              border: 'none',
              backgroundColor: activeTab === 'single' ? 'var(--primary-color)' : 'transparent',
              color: activeTab === 'single' ? '#fff' : 'var(--text-color)',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            {t('ocr.bulk_tab_single')}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('bulk')}
            style={{
              padding: '0.4rem 0.85rem',
              borderRadius: 'var(--radius-sm, 6px)',
              border: 'none',
              backgroundColor: activeTab === 'bulk' ? 'var(--primary-color)' : 'transparent',
              color: activeTab === 'bulk' ? '#fff' : 'var(--text-color)',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            {t('ocr.bulk_tab_bulk')}
          </button>
        </div>
      </div>

      {/* ── Mode 1: Single Page ── */}
      {activeTab === 'single' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '700px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, color: 'var(--text-color)' }}>
              {t('ocr.2')}
            </label>
            <input
              type="file"
              accept="image/*"
              onChange={handleSingleFileChange}
              style={{ ...inputStyle, padding: '0.5rem' }}
              disabled={loading}
            />
            {imagePreview && (
              <div style={{ marginTop: '1rem' }}>
                <img
                  src={imagePreview}
                  alt="Preview"
                  style={{ maxWidth: '100%', maxHeight: '300px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}
                />
              </div>
            )}
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'flex-end' }}>
            <div style={{ flex: '1 1 200px' }}>
              <label style={{ display: 'block', marginBottom: '0.25rem', fontWeight: 500, color: 'var(--text-color)' }}>
                {t('ocr.language_label')}
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                style={inputStyle}
                disabled={loading}
              >
                <option value="eng">{t('ocr.lang_en')}</option>
                <option value="eng+math">{t('ocr.lang_en_math')}</option>
                <option value="math">{t('ocr.lang_math_only')}</option>
                <option value="osd">{t('ocr.lang_auto')}</option>
              </select>
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', paddingBottom: '0.5rem', color: 'var(--text-color)' }}>
              <input
                type="checkbox"
                checked={isMath}
                onChange={(e) => setIsMath(e.target.checked)}
                disabled={loading}
              />
              <span style={{ fontSize: '0.9rem' }}>{t('ocr.math_ocr_desc')}</span>
            </label>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={handleProcessSingle}
              disabled={loading || !imageFile}
              style={{ ...buttonStyle, opacity: loading || !imageFile ? 0.6 : 1 }}
            >
              {loading ? t('ocr.8') : t('ocr.3')}
            </button>
            {imageFile && (
              <button
                onClick={() => { setImageFile(null); setImagePreview(null); setResult(null); }}
                disabled={loading}
                style={{ ...buttonStyle, backgroundColor: 'var(--secondary-color, #64748b)' }}
              >
                {t('ocr.7')}
              </button>
            )}
          </div>

          {result && (
            <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <h4 style={{ margin: 0, color: 'var(--text-color)' }}>{t('ocr.result_title')}</h4>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    {t('ocr.confidence', { percent: String(Math.round(result.confidence * 100)) })}
                  </span>
                  <button
                    onClick={() => copyToClipboard(result.text)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--primary-color)', display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.85rem' }}
                    title={t('ocr.copy_digitized')}
                  >
                    <Copy size={15} />
                    {t('ocr.6')}
                  </button>
                </div>
              </div>
              <div style={{ maxHeight: '300px', overflowY: 'auto', whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.9rem', lineHeight: 1.6, color: 'var(--text-color)' }}>
                {result.text || t('ocr.no_text_detected')}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* ── Mode 2: Bulk Multi-Page Upload ── */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem' }}>
            {/* Subject Selector */}
            <div>
              <label style={{ display: 'block', marginBottom: '0.25rem', fontWeight: 500, color: 'var(--text-color)' }}>
                {t('ocr.bulk_subject')}
              </label>
              <select
                value={bulkSubject}
                onChange={(e) => setBulkSubject(e.target.value)}
                style={inputStyle}
                disabled={loading}
              >
                <option value="math">{t('ocr.subject_math')}</option>
                <option value="chemistry">{t('ocr.subject_chemistry')}</option>
                <option value="physics">{t('ocr.subject_physics')}</option>
                <option value="essay">{t('ocr.subject_essay')}</option>
                <option value="general">{t('ocr.subject_general')}</option>
              </select>
            </div>

            {/* Language Selector */}
            <div>
              <label style={{ display: 'block', marginBottom: '0.25rem', fontWeight: 500, color: 'var(--text-color)' }}>
                {t('ocr.language_label')}
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                style={inputStyle}
                disabled={loading}
              >
                <option value="eng">{t('ocr.lang_en')}</option>
                <option value="eng+math">{t('ocr.lang_en_math')}</option>
                <option value="osd">{t('ocr.lang_auto')}</option>
              </select>
            </div>
          </div>

          {/* Bulk File Input */}
          <div
            style={{
              padding: '2rem',
              border: '2px dashed var(--border-color)',
              borderRadius: 'var(--radius-lg)',
              backgroundColor: 'var(--bg-color)',
              textAlign: 'center',
            }}
          >
            <Upload size={36} style={{ color: 'var(--primary-color)', margin: '0 auto 0.75rem' }} />
            <div style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text-color)', marginBottom: '0.25rem' }}>
              {t('ocr.bulk_select_files')}
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: '0 0 1rem' }}>
              {t('ai_grading.drop_or_browse')}
            </p>
            <input
              type="file"
              multiple
              accept="image/*"
              onChange={handleBulkFilesChange}
              id="bulk-ocr-file-input"
              style={{ display: 'none' }}
              disabled={loading}
            />
            <label
              htmlFor="bulk-ocr-file-input"
              style={{
                ...buttonStyle,
                display: 'inline-block',
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              {t('ocr.bulk_select_files')}
            </label>
          </div>

          {/* Thumbnails of selected photos */}
          {bulkPreviews.length > 0 && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <span style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-color)' }}>
                  {t('ocr.bulk_selected_files', { count: String(bulkPreviews.length) })}
                </span>
                <button
                  type="button"
                  onClick={() => { setBulkFiles([]); setBulkPreviews([]); setBulkResults([]); }}
                  disabled={loading}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                    background: 'none',
                    border: 'none',
                    color: '#ef4444',
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                  }}
                >
                  <Trash2 size={15} />
                  {t('ocr.bulk_clear_all')}
                </button>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
                {bulkPreviews.map((preview, idx) => (
                  <div
                    key={idx}
                    style={{
                      position: 'relative',
                      borderRadius: 'var(--radius-md)',
                      overflow: 'hidden',
                      border: '1px solid var(--border-color)',
                      backgroundColor: 'var(--bg-color)',
                    }}
                  >
                    <img
                      src={preview}
                      alt={`Page ${idx + 1}`}
                      style={{ width: '100%', height: '110px', objectFit: 'cover' }}
                    />
                    <div
                      style={{
                        position: 'absolute',
                        bottom: 0,
                        left: 0,
                        right: 0,
                        padding: '0.2rem 0.4rem',
                        backgroundColor: 'rgba(0,0,0,0.65)',
                        color: '#fff',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        textAlign: 'center',
                      }}
                    >
                      {t('ocr.page_number', { page: String(idx + 1) })}
                    </div>
                  </div>
                ))}
              </div>

              <button
                type="button"
                onClick={handleProcessBulk}
                disabled={loading}
                style={{ ...buttonStyle, width: '100%', padding: '0.75rem' }}
              >
                {loading
                  ? t('ocr.bulk_progress', { current: '1', total: String(bulkFiles.length) })
                  : t('ocr.bulk_upload_btn', { count: String(bulkFiles.length) })}
              </button>
            </div>
          )}

          {/* Bulk Results Gallery */}
          {bulkResults.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
              <h4 style={{ margin: 0, color: 'var(--text-color)' }}>
                {t('ocr.digitized_output')} ({bulkResults.length})
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
                {bulkResults.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '1.25rem',
                      borderRadius: 'var(--radius-lg)',
                      border: '1px solid var(--border-color)',
                      backgroundColor: 'var(--bg-color)',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-color)' }}>
                          {t('ocr.page_number', { page: String(item.page_index) })}: {item.filename}
                        </span>
                        <span style={{ fontSize: '0.8rem', padding: '0.15rem 0.5rem', borderRadius: '999px', backgroundColor: '#10b98120', color: '#10b981', fontWeight: 600 }}>
                          {Math.round(item.confidence * 100)}%
                        </span>
                      </div>
                      <div
                        style={{
                          maxHeight: '180px',
                          overflowY: 'auto',
                          whiteSpace: 'pre-wrap',
                          fontFamily: 'monospace',
                          fontSize: '0.85rem',
                          color: 'var(--text-color)',
                          backgroundColor: 'var(--sidebar-bg)',
                          padding: '0.75rem',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border-color)',
                          marginBottom: '0.75rem',
                        }}
                      >
                        {item.text || t('ocr.no_text_detected')}
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        type="button"
                        onClick={() => copyToClipboard(item.text)}
                        style={{
                          flex: 1,
                          padding: '0.45rem',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border-color)',
                          backgroundColor: 'var(--sidebar-bg)',
                          color: 'var(--text-color)',
                          cursor: 'pointer',
                          fontSize: '0.8rem',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '0.35rem',
                        }}
                      >
                        <Copy size={14} />
                        {t('ocr.copy_digitized')}
                      </button>
                      <button
                        type="button"
                        onClick={() => downloadTextFile(item.filename, item.text)}
                        style={{
                          flex: 1,
                          padding: '0.45rem',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border-color)',
                          backgroundColor: 'var(--sidebar-bg)',
                          color: 'var(--text-color)',
                          cursor: 'pointer',
                          fontSize: '0.8rem',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '0.35rem',
                        }}
                      >
                        <Download size={14} />
                        {t('ocr.download_digitized')}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
