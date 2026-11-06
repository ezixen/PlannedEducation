import { useState, useEffect } from 'react';
import { apiClient } from '../api';
import { useToast } from '../contexts/ToastContext';
import { useI18n } from '../contexts/I18nContext';
import { Edit, AlertCircle, Image as ImageIcon } from 'lucide-react';

interface OCRWord {
  text: string;
  confidence: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

interface OCRReviewData {
  id: string;
  submission_id: string;
  exam_id: string;
  student_id: string;
  student_name?: string;
  exam_title?: string;
  original_text: string;
  original_confidence: number;
  is_handwritten: boolean;
  image_url?: string | null;
  words?: OCRWord[];
  status: string;
  corrected_text?: string | null;
  review_notes?: string | null;
  reviewed_at?: string | null;
  anonymized: boolean;
  ai_graded: boolean;
  created_at: string;
}

interface OCRReviewProps {
  onComplete?: (correctedText: string) => void;
  initialReview?: OCRReviewData | null;
}

export function OCRReview({ onComplete, initialReview }: OCRReviewProps) {
  const { t } = useI18n();
  const { success: showSuccess, error: showError } = useToast();

  const [review, setReview] = useState<OCRReviewData | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [correctedText, setCorrectedText] = useState('');
  const [reviewNotes, setReviewNotes] = useState('');
  const [status, setStatus] = useState<'pending' | 'reviewing' | 'approved' | 'rejected' | 'corrected'>('pending');
  const [saving, setSaving] = useState(false);
  const [showImage, setShowImage] = useState(true);

  useEffect(() => {
    if (initialReview) {
      setReview(initialReview);
      setCorrectedText(initialReview.corrected_text || initialReview.original_text);
      setStatus((initialReview.status as any) || 'pending');
      if (initialReview.image_url) {
        setImageUrl(initialReview.image_url);
      }
    }
  }, [initialReview]);

  const handleSaveReview = async () => {
    if (!review) return;

    setSaving(true);
    try {
      const updateData: any = {
        status,
        corrected_text: correctedText,
        review_notes: reviewNotes,
      };

      if (review.id) {
        await apiClient.put(`/ocr/review/${review.id}`, updateData);
      } else {
        await apiClient.post('/ocr/review/', {
          submission_id: review.submission_id,
          exam_id: review.exam_id,
          student_id: review.student_id,
          original_text: review.original_text,
          original_confidence: review.original_confidence,
          is_handwritten: review.is_handwritten,
          image_url: review.image_url,
          words_json: JSON.stringify(review.words || []),
          ...updateData,
        });
      }

      showSuccess(t('ocr.review_saved'));
      if (status === 'approved' || status === 'corrected') {
        onComplete?.(correctedText);
      }
    } catch (err: any) {
      showError(t('ocr.save_failed'), err.response?.data?.detail || err.message);
    } finally {
      setSaving(false);
    }
  };

  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.8) return '#10b981'; // green
    if (conf >= 0.6) return '#f59e0b'; // yellow
    return '#ef4444'; // red
  };

  const renderWordCloud = () => {
    if (!review?.words || review.words.length === 0) return null;

    return (
      <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
        <h4 style={{ margin: '0 0 0.75rem', color: 'var(--text-color)', fontSize: '0.95rem' }}>
          {t('ocr.word_confidence')}
        </h4>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          {review.words.map((word, idx) => {
            const color = getConfidenceColor(word.confidence);
            return (
              <span
                key={idx}
                style={{
                  padding: '0.2rem 0.5rem',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: color + '15',
                  color: color,
                  border: '1px solid ' + color + '40',
                  fontSize: '0.85rem',
                  fontWeight: 500,
                }}
                title={`${word.text} (${Math.round(word.confidence * 100)}%)`}
              >
                {word.text}
              </span>
            );
          })}
        </div>
        <p style={{ margin: '0.5rem 0 0', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          {t('ocr.confidence_legend')}
        </p>
      </div>
    );
  };

  if (!review && !initialReview) {
    return (
      <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        <ImageIcon size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
        <p>{t('ocr.no_submission')}</p>
      </div>
    );
  }

  const currentReview = review || initialReview!;

  return (
    <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--text-color)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Edit size={20} /> {t('ocr.review_title')}
          </h3>
          <p style={{ color: 'var(--text-muted)', margin: '0.35rem 0 0', fontSize: '0.9rem' }}>
            {t('ocr.review_desc')}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <span
            style={{
              padding: '0.25rem 0.75rem',
              borderRadius: '9999px',
              fontSize: '0.8rem',
              fontWeight: 600,
              backgroundColor:
                status === 'pending' ? '#f59e0b20' :
                status === 'reviewing' ? '#3b82f620' :
                status === 'approved' ? '#10b98120' :
                status === 'rejected' ? '#ef444420' :
                '#10b98120',
              color:
                status === 'pending' ? '#f59e0b' :
                status === 'reviewing' ? '#3b82f6' :
                status === 'approved' ? '#10b981' :
                status === 'rejected' ? '#ef4444' :
                '#10b981',
              border: '1px solid ' +
                (status === 'pending' ? '#f59e0b40' :
                 status === 'reviewing' ? '#3b82f640' :
                 status === 'approved' ? '#10b98140' :
                 status === 'rejected' ? '#ef444440' :
                 '#10b98140'),
            }}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </span>
          {currentReview.is_handwritten && (
            <span
              style={{
                padding: '0.25rem 0.75rem',
                borderRadius: '9999px',
                fontSize: '0.8rem',
                fontWeight: 600,
                backgroundColor: '#8b5cf620',
                color: '#8b5cf6',
                border: '1px solid #8b5cf640',
              }}
            >
              {t('ocr.handwritten')}
            </span>
          )}
        </div>
      </div>

      {/* Main Content: Image + Text Editor */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {/* Image Preview */}
        {showImage && imageUrl && (
          <div style={{ border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', overflow: 'hidden', backgroundColor: '#000' }}>
            <img
              src={imageUrl}
              alt="Handwritten submission"
              style={{ width: '100%', maxHeight: '400px', objectFit: 'contain', display: 'block' }}
            />
          </div>
        )}

        {/* Text Editor */}
        <div style={{ border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--bg-color)' }}>
          <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h4 style={{ margin: 0, color: 'var(--text-color)', fontSize: '0.95rem' }}>
              {currentReview.is_handwritten ? t('ocr.recognized_text') : t('ocr.digitized_text')}
            </h4>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                type="button"
                onClick={() => setShowImage(!showImage)}
                style={{
                  padding: '0.4rem 0.8rem',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-color)',
                  backgroundColor: 'transparent',
                  color: 'var(--text-color)',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                }}
              >
                {showImage ? t('ocr.hide_image') : t('ocr.show_image')}
              </button>
              <button
                type="button"
                onClick={() => setCorrectedText(currentReview.original_text)}
                style={{
                  padding: '0.4rem 0.8rem',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-color)',
                  backgroundColor: 'transparent',
                  color: 'var(--text-color)',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                }}
              >
                {t('ocr.reset_text')}
              </button>
            </div>
          </div>
          <textarea
            value={correctedText}
            onChange={(e) => setCorrectedText(e.target.value)}
            style={{
              width: '100%',
              minHeight: '200px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.95rem',
              padding: '1rem',
              border: 'none',
              outline: 'none',
              backgroundColor: 'transparent',
              color: 'var(--text-color)',
              resize: 'vertical',
            }}
            placeholder={t('ocr.edit_text_placeholder')}
          />
        </div>

        {/* Review Notes */}
        <div style={{ border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--bg-color)' }}>
          <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-color)' }}>
            <h4 style={{ margin: 0, color: 'var(--text-color)', fontSize: '0.95rem' }}>{t('ocr.review_notes')}</h4>
          </div>
          <textarea
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            style={{
              width: '100%',
              minHeight: '80px',
              fontSize: '0.95rem',
              padding: '1rem',
              border: 'none',
              outline: 'none',
              backgroundColor: 'transparent',
              color: 'var(--text-color)',
              resize: 'vertical',
            }}
            placeholder={t('ocr.notes_placeholder')}
          />
        </div>

        {/* Word Confidence Cloud */}
        {renderWordCloud()}

        {/* Confidence Info */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>
          <AlertCircle size={16} />
          <span>
            {t('ocr.original_confidence', { percent: String(Math.round(currentReview.original_confidence * 100)) })}
          </span>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={() => {
              setStatus('reviewing');
              setSaving(true);
            }}
            disabled={saving}
            style={{
              padding: '0.625rem 1.5rem',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              backgroundColor: '#3b82f6',
              color: '#fff',
              cursor: saving ? 'not-allowed' : 'pointer',
              fontWeight: 600,
              fontSize: '0.95rem',
              opacity: saving ? 0.7 : 1,
            }}
          >
            {saving ? t('ocr.saving') : t('ocr.mark_reviewing')}
          </button>

          <button
            type="button"
            onClick={() => {
              setStatus('approved');
              handleSaveReview();
            }}
            disabled={saving}
            style={{
              padding: '0.625rem 1.5rem',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              backgroundColor: '#10b981',
              color: '#fff',
              cursor: saving ? 'not-allowed' : 'pointer',
              fontWeight: 600,
              fontSize: '0.95rem',
              opacity: saving ? 0.7 : 1,
            }}
          >
            {t('ocr.approve')}
          </button>

          <button
            type="button"
            onClick={() => {
              setStatus('corrected');
              handleSaveReview();
            }}
            disabled={saving}
            style={{
              padding: '0.625rem 1.5rem',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              backgroundColor: '#8b5cf6',
              color: '#fff',
              cursor: saving ? 'not-allowed' : 'pointer',
              fontWeight: 600,
              fontSize: '0.95rem',
              opacity: saving ? 0.7 : 1,
            }}
          >
            {t('ocr.correct_and_approve')}
          </button>

          <button
            type="button"
            onClick={() => {
              setStatus('rejected');
              handleSaveReview();
            }}
            disabled={saving}
            style={{
              padding: '0.625rem 1.5rem',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              backgroundColor: '#ef4444',
              color: '#fff',
              cursor: saving ? 'not-allowed' : 'pointer',
              fontWeight: 600,
              fontSize: '0.95rem',
              opacity: saving ? 0.7 : 1,
            }}
          >
            {t('ocr.reject')}
          </button>
        </div>
      </div>
    </div>
  );
}
