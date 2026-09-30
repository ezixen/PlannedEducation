import { useState } from 'react';
import { apiClient } from '../api';
import { useToast } from '../contexts/ToastContext';

export function OCRProcessor() {
  const { success: showSuccess, error: showError } = useToast();
  
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [result, setResult] = useState<{
    text: string;
    confidence: number;
    language: string;
    bounding_boxes?: any[];
    error?: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState('eng');
  const [isMath, setIsMath] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
      setResult(null);
    }
  };

  const handleProcess = async () => {
    if (!imageFile) {
      showError('Please select an image first.');
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
      showSuccess(`OCR completed with ${Math.round(response.data.confidence * 100)}% confidence`);
    } catch (err: any) {
      showError('OCR processing failed.', err.response?.data?.detail || err.message);
      setResult({ text: '', confidence: 0, language, error: err.response?.data?.detail || err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setImageFile(null);
    setImagePreview(null);
    setResult(null);
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
      <h3>OCR Processor</h3>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
        Extract text from handwritten exam images using Tesseract OCR.
        Supports math expressions and multiple languages.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '600px' }}>
        {/* File Upload */}
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
            Upload Image
          </label>
          <input
            type="file"
            accept="image/*"
            onChange={handleFileChange}
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

        {/* Options */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'flex-end' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.25rem', fontWeight: 500 }}>
              Language
            </label>
            <select
              value={language}
              onChange={e => setLanguage(e.target.value)}
              style={inputStyle}
              disabled={loading}
            >
              <option value="eng">English</option>
              <option value="eng+math">English + Math</option>
              <option value="math">Math Only</option>
              <option value="osd">Auto-detect (OSD)</option>
            </select>
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={isMath}
              onChange={e => setIsMath(e.target.checked)}
              disabled={loading}
            />
            <span>Math-specific OCR (optimized for equations)</span>
          </label>
        </div>

        {/* Process Button */}
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={handleProcess}
            disabled={loading || !imageFile}
            style={{ ...buttonStyle, opacity: loading || !imageFile ? 0.6 : 1 }}
          >
            {loading ? 'Processing...' : 'Process OCR'}
          </button>
          {imageFile && (
            <button
              onClick={handleClear}
              disabled={loading}
              style={{ ...buttonStyle, backgroundColor: 'var(--secondary-color)' }}
            >
              Clear
            </button>
          )}
        </div>

        {/* Result */}
        {result && (
          <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h4 style={{ margin: 0 }}>Result</h4>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Confidence: {Math.round(result.confidence * 100)}%
              </span>
            </div>
            {result.error && (
              <div style={{ color: '#ef4444', marginBottom: '1rem' }}>
                Error: {result.error}
              </div>
            )}
            <div style={{ 
              maxHeight: '300px', 
              overflowY: 'auto', 
              whiteSpace: 'pre-wrap', 
              fontFamily: 'monospace',
              fontSize: '0.9rem',
              lineHeight: 1.6,
              color: 'var(--text-color)'
            }}>
              {result.text || '(No text detected)'}
            </div>
            {result.bounding_boxes && result.bounding_boxes.length > 0 && (
              <details style={{ marginTop: '1rem' }}>
                <summary style={{ cursor: 'pointer', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  Show bounding boxes ({result.bounding_boxes.length} words)
                </summary>
                <pre style={{ marginTop: '0.5rem', fontSize: '0.75rem', maxHeight: '200px', overflow: 'auto' }}>
                  {JSON.stringify(result.bounding_boxes.slice(0, 20), null, 2)}
                  {result.bounding_boxes.length > 20 && '\n... and more'}
                </pre>
              </details>
            )}
          </div>
        )}
      </div>
    </div>
  );
}