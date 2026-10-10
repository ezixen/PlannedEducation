import React from 'react';

export interface AnonymizedAnswer {
  question_id: string;
  question_text: string;
  student_response: string;
  points_possible: number;
  correct_answer: string | null;
  rubric: string | null;
  saved_score?: number | null;
  saved_feedback?: string | null;
  saved_corrected_answer?: string | null;
}

export interface AIGrade {
  question_id: string;
  score: number;
  feedback: string;
  confidence: number;
  reasoning?: string;
  teacher_score?: number;
  teacher_feedback?: string;
  teacher_corrected_answer?: string;
  teacher_approved?: boolean;
}

export interface SubmissionWithAIGrades {
  anonymous_student_ref: string;
  submission_id: string;
  is_graded?: boolean;
  total_score?: number | null;
  summary_feedback?: string | null;
  answers: AnonymizedAnswer[];
  ai_grades?: Record<string, AIGrade>;
  teacher_approved?: boolean;
}

interface TeacherCorrectionModalProps {
  submission: SubmissionWithAIGrades;
  reviewingQuestionId: string | null;
  setReviewingQuestionId: (id: string | null) => void;
  onClose: () => void;
  onUpdateGrade: (
    submissionId: string,
    questionId: string,
    field: 'teacher_score' | 'teacher_feedback' | 'teacher_corrected_answer',
    value: number | string
  ) => void;
  onToggleApproval: (submissionId: string, questionId: string, approved: boolean) => void;
  onApproveAllQuestions: (submissionId: string) => void;
  onSaveGrades: (submission: SubmissionWithAIGrades, approveAll?: boolean) => void;
}

const FEEDBACK_CHIPS = [
  'Excellent step-by-step work!',
  'Correct method, minor arithmetic error.',
  'Check sign when moving terms across =.',
  'Partial credit for setting up the equation.',
  'Please review the worked solution on the right.',
];

export const TeacherCorrectionModal: React.FC<TeacherCorrectionModalProps> = ({
  submission,
  reviewingQuestionId,
  setReviewingQuestionId,
  onClose,
  onUpdateGrade,
  onToggleApproval,
  onApproveAllQuestions,
  onSaveGrades,
}) => {
  const totalPossible = submission.answers.reduce((acc, a) => acc + (a.points_possible || 0), 0);
  const currentTotalScore = submission.answers.reduce((acc, a) => {
    const g = submission.ai_grades?.[a.question_id];
    const s = g ? (g.teacher_score ?? g.score) : 0;
    return acc + (Number.isFinite(s) ? s : 0);
  }, 0);

  const approvedCount = submission.ai_grades
    ? Object.values(submission.ai_grades).filter((g) => g.teacher_approved).length
    : 0;

  return (
    <div
      data-testid="teacher-correction-modal"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1rem',
      }}
    >
      <div
        style={{
          backgroundColor: 'var(--sidebar-bg)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-color)',
          maxWidth: '1080px',
          width: '100%',
          maxHeight: '92vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 40px rgba(0,0,0,0.3)',
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid var(--border-color)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1rem',
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--text-color)' }}>
              Review & Correct Exam — {submission.anonymous_student_ref}
            </h2>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Write step-by-step corrections alongside the student&apos;s answers so they can compare side-by-side.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <div
              data-testid="modal-running-score"
              style={{
                padding: '0.4rem 0.85rem',
                borderRadius: '9999px',
                backgroundColor: '#3b82f615',
                border: '1px solid #3b82f640',
                color: 'var(--text-color)',
                fontWeight: 700,
                fontSize: '0.9rem',
              }}
            >
              Score: {Math.round(currentTotalScore * 10) / 10} / {totalPossible} pts
            </div>
            <button
              type="button"
              onClick={() => onApproveAllQuestions(submission.submission_id)}
              style={{
                padding: '0.45rem 0.85rem',
                backgroundColor: '#8b5cf6',
                color: '#fff',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.8rem',
              }}
            >
              ✓ Mark All Approved ({approvedCount}/{submission.answers.length})
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close modal"
              style={{
                background: 'none',
                border: 'none',
                fontSize: '1.5rem',
                cursor: 'pointer',
                color: 'var(--text-muted)',
                lineHeight: 1,
              }}
            >
              ×
            </button>
          </div>
        </div>

        {/* Scrollable Questions List */}
        <div style={{ padding: '1.5rem', overflowY: 'auto', flex: 1 }}>
          {submission.answers.map((answer, idx) => {
            const aiGrade = submission.ai_grades?.[answer.question_id];
            const isReviewing = reviewingQuestionId === answer.question_id;
            const currentScore = aiGrade ? (aiGrade.teacher_score ?? aiGrade.score) : 0;
            const currentFeedback = aiGrade ? (aiGrade.teacher_feedback ?? aiGrade.feedback) : '';
            const currentCorrected =
              aiGrade?.teacher_corrected_answer ??
              answer.saved_corrected_answer ??
              answer.correct_answer ??
              '';

            return (
              <div
                key={answer.question_id}
                data-testid={`teacher-question-card-${idx + 1}`}
                style={{
                  marginBottom: '1.5rem',
                  padding: '1.25rem',
                  backgroundColor: 'var(--bg-color)',
                  borderRadius: 'var(--radius-lg)',
                  border: `1px solid ${aiGrade?.teacher_approved ? '#10b98160' : 'var(--border-color)'}`,
                }}
              >
                {/* Question Header */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '0.75rem',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <h4 style={{ margin: 0, fontSize: '1.05rem', color: 'var(--text-color)' }}>
                      Question {idx + 1} ({answer.points_possible} pts)
                    </h4>
                    {answer.rubric && (
                      <span
                        style={{
                          fontSize: '0.75rem',
                          padding: '0.15rem 0.5rem',
                          borderRadius: '4px',
                          backgroundColor: '#3b82f615',
                          color: '#3b82f6',
                        }}
                      >
                        Rubric: {answer.rubric}
                      </span>
                    )}
                  </div>

                  {aiGrade && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <span
                        style={{
                          padding: '0.25rem 0.6rem',
                          borderRadius: '9999px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          backgroundColor: currentScore === answer.points_possible ? '#10b98120' : '#f59e0b20',
                          color: currentScore === answer.points_possible ? '#10b981' : '#d97706',
                        }}
                      >
                        Score: {currentScore}/{answer.points_possible} (AI Conf: {Math.round(aiGrade.confidence * 100)}%)
                      </span>
                      {aiGrade.teacher_approved ? (
                        <span
                          style={{
                            padding: '0.25rem 0.6rem',
                            borderRadius: '9999px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            backgroundColor: '#10b98120',
                            color: '#10b981',
                          }}
                        >
                          ✓ Teacher Approved
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setReviewingQuestionId(isReviewing ? null : answer.question_id)}
                          style={{
                            padding: '0.25rem 0.65rem',
                            backgroundColor: '#3b82f6',
                            color: '#fff',
                            border: 'none',
                            borderRadius: '9999px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          Review
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Question Prompt */}
                <p
                  style={{
                    margin: '0 0 1rem',
                    fontSize: '0.98rem',
                    fontWeight: 500,
                    color: 'var(--text-color)',
                    lineHeight: 1.5,
                  }}
                >
                  {answer.question_text}
                </p>

                {/* Side-by-Side: Student Response vs Teacher Corrected Solution */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                    gap: '1rem',
                    marginBottom: '1rem',
                  }}
                >
                  {/* Left: Student's Original Submitted Answer */}
                  <div
                    style={{
                      padding: '0.875rem',
                      backgroundColor: 'var(--sidebar-bg)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-color)',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
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
                        📄 Student&apos;s Original Submitted Answer
                      </div>
                      <pre
                        data-testid={`student-original-answer-${idx + 1}`}
                        style={{
                          margin: 0,
                          whiteSpace: 'pre-wrap',
                          fontFamily: 'inherit',
                          fontSize: '0.95rem',
                          color: 'var(--text-color)',
                          lineHeight: 1.5,
                        }}
                      >
                        {answer.student_response || '(empty)'}
                      </pre>
                    </div>

                    {answer.correct_answer && (
                      <div
                        style={{
                          marginTop: '0.85rem',
                          padding: '0.6rem 0.75rem',
                          backgroundColor: '#10b98110',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid #10b98130',
                        }}
                      >
                        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#059669' }}>
                          Reference Answer Key:
                        </div>
                        <pre
                          style={{
                            margin: '0.25rem 0 0',
                            whiteSpace: 'pre-wrap',
                            fontFamily: 'inherit',
                            fontSize: '0.88rem',
                            color: '#10b981',
                          }}
                        >
                          {answer.correct_answer}
                        </pre>
                      </div>
                    )}
                  </div>

                  {/* Right: Teacher's Corrected Version / Worked Solution */}
                  <div
                    style={{
                      padding: '0.875rem',
                      backgroundColor: '#f0fdf4',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid #86efac',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        flexWrap: 'wrap',
                        gap: '0.4rem',
                        marginBottom: '0.5rem',
                      }}
                    >
                      <span
                        style={{
                          fontSize: '0.78rem',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          letterSpacing: '0.04em',
                          color: '#166534',
                        }}
                      >
                        ✍️ Teacher&apos;s Corrected Version (Shown Side-by-Side to Student)
                      </span>
                      <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                        <button
                          type="button"
                          data-testid={`copy-student-work-btn-${idx + 1}`}
                          onClick={() =>
                            onUpdateGrade(
                              submission.submission_id,
                              answer.question_id,
                              'teacher_corrected_answer',
                              `Student wrote: ${answer.student_response || '(empty)'}\nCorrection: ${answer.correct_answer || ''}`
                            )
                          }
                          style={{
                            padding: '0.2rem 0.5rem',
                            fontSize: '0.72rem',
                            borderRadius: '4px',
                            border: '1px solid #16a34a',
                            backgroundColor: '#fff',
                            color: '#15803d',
                            cursor: 'pointer',
                            fontWeight: 600,
                          }}
                        >
                          📋 Annotate Student Work
                        </button>
                        {answer.correct_answer && (
                          <button
                            type="button"
                            onClick={() =>
                              onUpdateGrade(
                                submission.submission_id,
                                answer.question_id,
                                'teacher_corrected_answer',
                                answer.correct_answer || ''
                              )
                            }
                            style={{
                              padding: '0.2rem 0.5rem',
                              fontSize: '0.72rem',
                              borderRadius: '4px',
                              border: '1px solid #16a34a',
                              backgroundColor: '#dcfce7',
                              color: '#166534',
                              cursor: 'pointer',
                              fontWeight: 600,
                            }}
                          >
                            ✨ Use Answer Key
                          </button>
                        )}
                      </div>
                    </div>

                    <textarea
                      data-testid={`teacher-corrected-answer-input-${idx + 1}`}
                      value={currentCorrected}
                      onChange={(e) =>
                        onUpdateGrade(
                          submission.submission_id,
                          answer.question_id,
                          'teacher_corrected_answer',
                          e.target.value
                        )
                      }
                      rows={4}
                      placeholder="Write the corrected step-by-step math solution or corrected answer here..."
                      style={{
                        width: '100%',
                        padding: '0.6rem',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid #86efac',
                        backgroundColor: '#ffffff',
                        color: '#0f172a',
                        fontSize: '0.92rem',
                        fontFamily: 'inherit',
                        resize: 'vertical',
                        boxSizing: 'border-box',
                      }}
                    />
                  </div>
                </div>

                {/* Comfy Teacher Grading & Feedback Controls */}
                {aiGrade && (
                  <div
                    style={{
                      padding: '0.875rem 1rem',
                      backgroundColor: '#fffbeb',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid #fcd34d',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        flexWrap: 'wrap',
                        gap: '0.75rem',
                        marginBottom: '0.75rem',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <label
                          style={{
                            fontSize: '0.85rem',
                            fontWeight: 600,
                            color: '#92400e',
                          }}
                        >
                          Score (0–{answer.points_possible}):
                        </label>
                        <input
                          type="number"
                          data-testid={`teacher-score-input-${idx + 1}`}
                          min={0}
                          max={answer.points_possible}
                          step={0.5}
                          value={currentScore}
                          onChange={(e) =>
                            onUpdateGrade(
                              submission.submission_id,
                              answer.question_id,
                              'teacher_score',
                              parseFloat(e.target.value) || 0
                            )
                          }
                          style={{
                            width: '85px',
                            padding: '0.35rem 0.5rem',
                            border: '1px solid #f59e0b',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '0.95rem',
                            fontWeight: 700,
                            backgroundColor: '#fff',
                            color: '#0f172a',
                          }}
                        />

                        {/* Quick Score Presets */}
                        {[
                          { label: '100% Full', mult: 1 },
                          { label: '75% Method OK', mult: 0.75 },
                          { label: '50% Partial', mult: 0.5 },
                          { label: '0%', mult: 0 },
                        ].map((preset) => (
                          <button
                            key={preset.label}
                            type="button"
                            onClick={() =>
                              onUpdateGrade(
                                submission.submission_id,
                                answer.question_id,
                                'teacher_score',
                                Math.round(answer.points_possible * preset.mult * 2) / 2
                              )
                            }
                            style={{
                              padding: '0.25rem 0.55rem',
                              fontSize: '0.75rem',
                              borderRadius: '9999px',
                              border: '1px solid #f59e0b',
                              backgroundColor: '#fef3c7',
                              color: '#92400e',
                              cursor: 'pointer',
                              fontWeight: 600,
                            }}
                          >
                            {preset.label}
                          </button>
                        ))}
                      </div>

                      <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={Boolean(aiGrade.teacher_approved)}
                          onChange={(e) =>
                            onToggleApproval(submission.submission_id, answer.question_id, e.target.checked)
                          }
                        />
                        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#92400e' }}>
                          Approve this question
                        </span>
                      </label>
                    </div>

                    {/* Teacher Feedback Input + Quick Chips */}
                    <div>
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          flexWrap: 'wrap',
                          gap: '0.35rem',
                          marginBottom: '0.35rem',
                        }}
                      >
                        <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#92400e' }}>
                          Teacher Feedback & Explanation:
                        </label>
                        <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                          {FEEDBACK_CHIPS.map((chip) => (
                            <button
                              key={chip}
                              type="button"
                              onClick={() =>
                                onUpdateGrade(
                                  submission.submission_id,
                                  answer.question_id,
                                  'teacher_feedback',
                                  currentFeedback ? `${currentFeedback} ${chip}` : chip
                                )
                              }
                              style={{
                                padding: '0.15rem 0.45rem',
                                fontSize: '0.7rem',
                                borderRadius: '4px',
                                border: '1px solid #fcd34d',
                                backgroundColor: '#fff',
                                color: '#78350f',
                                cursor: 'pointer',
                              }}
                            >
                              + {chip}
                            </button>
                          ))}
                        </div>
                      </div>
                      <textarea
                        data-testid={`teacher-feedback-input-${idx + 1}`}
                        value={currentFeedback}
                        onChange={(e) =>
                          onUpdateGrade(
                            submission.submission_id,
                            answer.question_id,
                            'teacher_feedback',
                            e.target.value
                          )
                        }
                        rows={2}
                        placeholder="Add constructive feedback explaining where the student went right or wrong..."
                        style={{
                          width: '100%',
                          padding: '0.5rem',
                          border: '1px solid #fcd34d',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '0.88rem',
                          fontFamily: 'inherit',
                          backgroundColor: '#fff',
                          color: '#0f172a',
                          resize: 'vertical',
                          boxSizing: 'border-box',
                        }}
                      />
                    </div>

                    {isReviewing && (
                      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.6rem', justifyContent: 'flex-end' }}>
                        <button
                          type="button"
                          onClick={() => setReviewingQuestionId(null)}
                          style={{
                            padding: '0.35rem 0.75rem',
                            backgroundColor: 'var(--secondary-color)',
                            color: '#fff',
                            border: 'none',
                            borderRadius: 'var(--radius-sm)',
                            cursor: 'pointer',
                            fontSize: '0.8rem',
                          }}
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            onToggleApproval(submission.submission_id, answer.question_id, true);
                            setReviewingQuestionId(null);
                          }}
                          style={{
                            padding: '0.35rem 0.75rem',
                            backgroundColor: '#10b981',
                            color: '#fff',
                            border: 'none',
                            borderRadius: 'var(--radius-sm)',
                            cursor: 'pointer',
                            fontSize: '0.8rem',
                            fontWeight: 600,
                          }}
                        >
                          Approve & Save
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: '1rem 1.5rem',
            borderTop: '1px solid var(--border-color)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '0.75rem',
          }}
        >
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Saving publishes the corrected version &amp; feedback to the student&apos;s exam comparison view.
          </span>
          <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: '0.625rem 1.25rem',
                backgroundColor: 'var(--secondary-color)',
                color: '#fff',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                fontWeight: 500,
              }}
            >
              Close
            </button>
            <button
              type="button"
              data-testid="apply-approved-grades-btn"
              onClick={() => {
                onSaveGrades(submission, true);
                onClose();
              }}
              style={{
                padding: '0.625rem 1.25rem',
                backgroundColor: '#10b981',
                color: '#fff',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              ✓ Approve All &amp; Save Corrected Exam
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

