import React from 'react';

export interface StudentReviewedQuestion {
  question_id: string;
  question_type: string;
  question_text: string;
  points_possible: number;
  student_response: string;
  score: number | null;
  teacher_feedback: string | null;
  corrected_answer: string | null;
  correct_answer: string | null;
  rubric: string | null;
}

export interface StudentSubmissionDetail {
  submission_id: string;
  exam_id: string;
  exam_title: string;
  started_at: string | null;
  completed_at: string | null;
  is_graded: boolean;
  score: number | null;
  total_possible: number;
  summary_feedback: string;
  questions: StudentReviewedQuestion[];
}

interface StudentSubmissionReviewProps {
  submission: StudentSubmissionDetail | null;
  loading: boolean;
  onRefresh: () => void;
}

export const StudentSubmissionReview: React.FC<StudentSubmissionReviewProps> = ({
  submission,
  loading,
  onRefresh,
}) => {
  const pct =
    submission && submission.is_graded && submission.total_possible > 0 && submission.score !== null
      ? Math.round((submission.score / submission.total_possible) * 100)
      : null;

  return (
    <div
      data-testid="student-submission-review"
      style={{ maxWidth: '1040px', margin: '1.5rem auto', padding: '0 1rem 3rem' }}
    >
      {/* Top Completion & Score Banner */}
      <div
        style={{
          padding: '1.5rem',
          backgroundColor: 'var(--sidebar-bg)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-lg)',
          marginBottom: '1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <h1
              style={{
                color: 'var(--primary-color)',
                fontSize: '1.5rem',
                fontWeight: 700,
                margin: 0,
              }}
            >
              Exam Submitted Successfully
            </h1>
            {submission?.is_graded ? (
              <span
                data-testid="student-grade-status-badge"
                style={{
                  padding: '0.3rem 0.75rem',
                  borderRadius: '9999px',
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  backgroundColor: '#10b98120',
                  color: '#10b981',
                  border: '1px solid #10b98140',
                }}
              >
                ✓ Graded &amp; Corrected by Teacher
              </span>
            ) : (
              <span
                data-testid="student-grade-status-badge"
                style={{
                  padding: '0.3rem 0.75rem',
                  borderRadius: '9999px',
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  backgroundColor: '#f59e0b20',
                  color: '#d97706',
                  border: '1px solid #f59e0b40',
                }}
              >
                ⏳ Submitted — Awaiting Teacher Correction
              </span>
            )}
          </div>
          <p style={{ color: 'var(--text-muted)', marginTop: '0.4rem', marginBottom: 0, fontSize: '0.92rem' }}>
            {submission?.exam_title
              ? `${submission.exam_title} — Compare your original submitted answers alongside your teacher's corrected version below.`
              : 'Your answers have been cryptographically sealed.'}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          {submission?.is_graded && submission.score !== null && (
            <div
              data-testid="student-final-score"
              style={{
                padding: '0.6rem 1.1rem',
                borderRadius: 'var(--radius-md)',
                backgroundColor: '#10b98115',
                border: '1px solid #10b98140',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: '#059669', fontWeight: 700 }}>
                Final Score
              </div>
              <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#047857' }}>
                {submission.score} / {submission.total_possible} pts {pct !== null ? `(${pct}%)` : ''}
              </div>
            </div>
          )}

          <button
            type="button"
            data-testid="refresh-student-submission-btn"
            onClick={onRefresh}
            disabled={loading}
            style={{
              padding: '0.6rem 1.1rem',
              backgroundColor: 'var(--primary-color)',
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontWeight: 600,
              fontSize: '0.88rem',
            }}
          >
            {loading ? 'Refreshing...' : '🔄 Check Teacher Corrections'}
          </button>
        </div>
      </div>

      {/* Per-Question Side-by-Side Comparison */}
      {submission && submission.questions.length > 0 && (
        <div>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-color)', marginBottom: '1rem' }}>
            Side-by-Side Review: Your Original Submission vs. Teacher&apos;s Corrected Version
          </h2>

          {submission.questions.map((q, idx) => {
            const isFullMarks = q.score !== null && q.score >= q.points_possible;
            const isPartialMarks = q.score !== null && q.score > 0 && q.score < q.points_possible;

            return (
              <div
                key={q.question_id}
                data-testid={`student-comparison-card-${idx + 1}`}
                style={{
                  marginBottom: '1.25rem',
                  padding: '1.25rem',
                  backgroundColor: 'var(--sidebar-bg)',
                  borderRadius: 'var(--radius-lg)',
                  border: `1px solid ${
                    !submission.is_graded
                      ? 'var(--border-color)'
                      : isFullMarks
                        ? '#10b98160'
                        : isPartialMarks
                          ? '#f59e0b60'
                          : '#ef444460'
                  }`,
                }}
              >
                {/* Question Header */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                    marginBottom: '0.75rem',
                  }}
                >
                  <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-color)' }}>
                    Question {idx + 1}
                  </h3>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {submission.is_graded && q.score !== null ? (
                      <span
                        data-testid={`student-question-score-${idx + 1}`}
                        style={{
                          padding: '0.25rem 0.7rem',
                          borderRadius: '9999px',
                          fontSize: '0.8rem',
                          fontWeight: 700,
                          backgroundColor: isFullMarks
                            ? '#10b98120'
                            : isPartialMarks
                              ? '#f59e0b20'
                              : '#ef444420',
                          color: isFullMarks ? '#10b981' : isPartialMarks ? '#d97706' : '#ef4444',
                        }}
                      >
                        {isFullMarks
                          ? `✓ Correct (${q.score}/${q.points_possible} pts)`
                          : isPartialMarks
                            ? `◐ Partial Credit (${q.score}/${q.points_possible} pts)`
                            : `✗ Needs Review (${q.score}/${q.points_possible} pts)`}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 500 }}>
                        {q.points_possible} pts
                      </span>
                    )}
                  </div>
                </div>

                {/* Question Prompt */}
                <p
                  style={{
                    fontSize: '1rem',
                    fontWeight: 500,
                    color: 'var(--text-color)',
                    margin: '0 0 1rem',
                    lineHeight: 1.5,
                  }}
                >
                  {q.question_text}
                </p>

                {/* Two-Column Comparison Grid */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                    gap: '1rem',
                  }}
                >
                  {/* Column 1: Student's Original Submitted Answer */}
                  <div
                    data-testid={`student-submitted-col-${idx + 1}`}
                    style={{
                      padding: '1rem',
                      backgroundColor: 'var(--bg-color)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-color)',
                    }}
                  >
                    <div
                      style={{
                        fontSize: '0.78rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                        color: 'var(--text-muted)',
                        marginBottom: '0.5rem',
                      }}
                    >
                      📄 Your Original Submitted Answer
                    </div>
                    <pre
                      style={{
                        margin: 0,
                        whiteSpace: 'pre-wrap',
                        fontFamily: 'inherit',
                        fontSize: '0.95rem',
                        color: 'var(--text-color)',
                        lineHeight: 1.5,
                      }}
                    >
                      {q.student_response || '(No answer submitted)'}
                    </pre>
                  </div>

                  {/* Column 2: Teacher's Corrected Version & Feedback */}
                  <div
                    data-testid={`teacher-corrected-col-${idx + 1}`}
                    style={{
                      padding: '1rem',
                      backgroundColor: submission.is_graded ? '#f0fdf4' : 'var(--bg-color)',
                      borderRadius: 'var(--radius-md)',
                      border: `1px solid ${submission.is_graded ? '#86efac' : 'var(--border-color)'}`,
                    }}
                  >
                    <div
                      style={{
                        fontSize: '0.78rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                        color: submission.is_graded ? '#166534' : 'var(--text-muted)',
                        marginBottom: '0.5rem',
                      }}
                    >
                      ✍️ Teacher&apos;s Corrected Version &amp; Solution
                    </div>

                    {submission.is_graded ? (
                      <>
                        <pre
                          data-testid={`student-view-corrected-answer-${idx + 1}`}
                          style={{
                            margin: 0,
                            whiteSpace: 'pre-wrap',
                            fontFamily: 'inherit',
                            fontSize: '0.95rem',
                            color: '#0f172a',
                            lineHeight: 1.5,
                            fontWeight: 500,
                          }}
                        >
                          {q.corrected_answer || q.correct_answer || 'See teacher feedback below.'}
                        </pre>

                        {q.teacher_feedback && (
                          <div
                            data-testid={`student-view-teacher-feedback-${idx + 1}`}
                            style={{
                              marginTop: '0.85rem',
                              padding: '0.65rem 0.8rem',
                              backgroundColor: '#fefce8',
                              borderRadius: 'var(--radius-sm)',
                              border: '1px solid #fde047',
                              color: '#713f12',
                              fontSize: '0.88rem',
                            }}
                          >
                            <strong>💬 Teacher Feedback:</strong> {q.teacher_feedback}
                          </div>
                        )}
                      </>
                    ) : (
                      <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.9rem', fontStyle: 'italic' }}>
                        Your teacher is currently reviewing your exam. Once graded, the step-by-step corrected solution and feedback will appear right here next to your answer.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

