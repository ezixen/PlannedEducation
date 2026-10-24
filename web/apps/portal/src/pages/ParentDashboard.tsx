import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../api';
import { useI18n } from '../contexts/I18nContext';

export function ParentDashboard() {
  const { t } = useI18n();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [childrenData, setChildrenData] = useState<any[]>([]);

  useEffect(() => {
    const fetchProgress = async () => {
      try {
        const res = await apiClient.get('/parents/children-progress');
        setChildrenData(res.data || []);
      } catch (err) {
        console.error('Failed to fetch children progress', err);
      } finally {
        setLoading(false);
      }
    };

    void fetchProgress();
  }, [user]);

  if (loading) return <div>{t('common.loading')}</div>;

  return (
    <div>
      <h1 style={{ color: 'var(--text-color)', marginBottom: '0.5rem' }}>{t('parent.1')}</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>
        Track your child&apos;s academic progress and encouraging teacher feedback securely.
      </p>

      {childrenData.map((child) => (
        <div key={child.student_id} style={{ marginBottom: '2rem' }}>
          <h2
            style={{
              borderBottom: '1px solid var(--border-color)',
              paddingBottom: '0.5rem',
              color: 'var(--text-color)',
            }}
          >
            {child.student_name}
          </h2>

          <div style={{ display: 'grid', gap: '1rem', marginTop: '1rem' }}>
            {child.recent_exams.length === 0 && (
              <p style={{ color: 'var(--text-muted)' }}>{t('parent.7')}</p>
            )}
            {child.recent_exams.map((exam: any, idx: number) => (
              <div
                key={idx}
                style={{
                  padding: '1.5rem',
                  backgroundColor: 'var(--sidebar-bg)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '0.5rem',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                  }}
                >
                  <h3 style={{ margin: 0, color: 'var(--text-color)' }}>{exam.exam_title}</h3>
                  <span
                    style={{
                      fontSize: '1.15rem',
                      fontWeight: 'bold',
                      color: 'var(--primary-color)',
                    }}
                  >
                    {exam.score !== null && exam.score !== undefined
                      ? `${exam.score}${exam.points_possible ? ` / ${exam.points_possible} pts` : ''}${
                          exam.score_percentage !== null && exam.score_percentage !== undefined
                            ? ` (${exam.score_percentage}%)`
                            : ''
                        }`
                      : 'Awaiting Teacher Grading'}
                  </span>
                </div>
                {(() => {
                  let parsedImageUrl = null;
                  let parsedCorrected = null;
                  let displayFb = exam.feedback || t('parent.no_feedback');

                  if (exam.feedback && exam.feedback.startsWith('{')) {
                    try {
                      const d = JSON.parse(exam.feedback);
                      parsedImageUrl = d.image_url;
                      parsedCorrected = d.corrected_solution;
                      displayFb = d.summary_feedback || displayFb;
                    } catch {}
                  }

                  return (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                      <div
                        style={{
                          padding: '0.85rem 1rem',
                          backgroundColor: 'var(--bg-color)',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '0.9rem',
                        }}
                      >
                        <strong style={{ color: 'var(--text-color)' }}>{t('parent.6')}:</strong>{' '}
                        <span style={{ color: 'var(--text-muted)' }}>{displayFb}</span>
                      </div>

                      {/* Side-by-side Handwritten & Digitized Solution */}
                      {(parsedImageUrl || parsedCorrected) && (
                        <div
                          style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                            gap: '0.75rem',
                            marginTop: '0.25rem',
                          }}
                        >
                          {parsedImageUrl && (
                            <div
                              style={{
                                padding: '0.75rem',
                                backgroundColor: 'var(--bg-color)',
                                borderRadius: 'var(--radius-sm)',
                                border: '1px solid var(--border-color)',
                              }}
                            >
                              <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.4rem', textTransform: 'uppercase' }}>
                                📸 {t('student_dashboard.handwritten_original')}
                              </div>
                              <img
                                src={parsedImageUrl}
                                alt="Handwritten test"
                                style={{ width: '100%', maxHeight: '200px', objectFit: 'contain', borderRadius: '4px', backgroundColor: '#0f172a' }}
                              />
                            </div>
                          )}

                          {parsedCorrected && (
                            <div
                              style={{
                                padding: '0.75rem',
                                backgroundColor: 'var(--bg-color)',
                                borderRadius: 'var(--radius-sm)',
                                border: '1px solid rgba(16, 185, 129, 0.3)',
                              }}
                            >
                              <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#059669', marginBottom: '0.4rem', textTransform: 'uppercase' }}>
                                ✍️ {t('student_dashboard.digitized_correction')}
                              </div>
                              <pre
                                style={{
                                  margin: 0,
                                  whiteSpace: 'pre-wrap',
                                  fontFamily: 'monospace',
                                  fontSize: '0.82rem',
                                  lineHeight: 1.5,
                                  color: 'var(--text-color)',
                                  maxHeight: '180px',
                                  overflowY: 'auto',
                                }}
                              >
                                {parsedCorrected}
                              </pre>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
