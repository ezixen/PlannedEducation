import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../api';

interface AnonymizedSubmission {
  anonymous_student_ref: string;
  submission_id: string;
  answers: Array<{
    question_id: string;
    question_text: string;
    student_response: string;
    points_possible: number;
    correct_answer: string | null;
    rubric: string | null;
  }>;
}

interface AIGrade {
  question_id: string;
  score: number;
  feedback: string;
  confidence: number;
}

interface SubmissionWithAIGrades extends AnonymizedSubmission {
  ai_grades?: Record<string, AIGrade>;
  teacher_approved?: boolean;
}

export function TeacherDashboard() {
  const { examId } = useParams<{ examId: string }>();
  const { success: showSuccess, error: showError, info: showInfo } = useToast();

  const [submissions, setSubmissions] = useState<SubmissionWithAIGrades[]>([]);
  const [loading, setLoading] = useState(true);
  const [generatingGrades, setGeneratingGrades] = useState<string | null>(null);
  const [selectedSubmission, setSelectedSubmission] = useState<SubmissionWithAIGrades | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [groupedMistakes, setGroupedMistakes] = useState<Record<string, string[]>>({});

  useEffect(() => {
    if (examId) {
      fetchSubmissions();
    }
  }, [examId]);

  const fetchSubmissions = async () => {
    if (!examId) return;
    setLoading(true);
    try {
      const response = await apiClient.get(`/anonymizer/exams/${examId}/submissions`);
      setSubmissions(response.data.map((s: AnonymizedSubmission) => ({ ...s, ai_grades: {}, teacher_approved: false })));
    } catch (err: any) {
      showError('Failed to fetch submissions.', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const generateAIGrades = async (submission: SubmissionWithAIGrades) => {
    setGeneratingGrades(submission.submission_id);
    try {
      // In a real implementation, this would call an external AI service
      // For now, we'll simulate AI grading
      const aiGrades: Record<string, AIGrade> = {};
      
      for (const answer of submission.answers) {
        // Simulate AI grading logic
        const isCorrect = answer.student_response.toLowerCase().trim() === 
          (answer.correct_answer || '').toLowerCase().trim();
        
        aiGrades[answer.question_id] = {
          question_id: answer.question_id,
          score: isCorrect ? answer.points_possible : 0,
          feedback: isCorrect 
            ? 'Correct answer. Well done!' 
            : `Incorrect. The correct answer is: ${answer.correct_answer || 'N/A'}. ${answer.rubric ? `Rubric: ${answer.rubric}` : ''}`,
          confidence: isCorrect ? 0.95 : 0.85,
        };
      }
      
      setSubmissions(prev => prev.map(s => 
        s.submission_id === submission.submission_id 
          ? { ...s, ai_grades: aiGrades }
          : s
      ));
      
      showSuccess('AI grades generated successfully!');
    } catch (err: any) {
      showError('Failed to generate AI grades.', err.response?.data?.detail || err.message);
    } finally {
      setGeneratingGrades(null);
    }
  };

  const applyAIGrades = async (submission: SubmissionWithAIGrades) => {
    if (!submission.ai_grades) return;
    
    try {
      const grades = Object.values(submission.ai_grades).map(g => ({
        question_id: g.question_id,
        score: g.score,
        feedback: g.feedback,
      }));
      
      await apiClient.post(`/anonymizer/submissions/${submission.submission_id}/grades`, {
        feedback: grades.map(g => g.feedback).join('\n\n'),
        score: grades.reduce((sum, g) => sum + g.score, 0),
      });
      
      setSubmissions(prev => prev.map(s => 
        s.submission_id === submission.submission_id 
          ? { ...s, teacher_approved: true }
          : s
      ));
      
      showSuccess('Grades applied successfully!');
    } catch (err: any) {
      showError('Failed to apply grades.', err.response?.data?.detail || err.message);
    }
  };

  const groupSimilarMistakes = () => {
    const groups: Record<string, string[]> = {};
    
    submissions.forEach(sub => {
      sub.answers.forEach(answer => {
        if (answer.student_response && !answer.student_response.toLowerCase().includes((answer.correct_answer || '').toLowerCase())) {
          // Simple grouping by question and similar response pattern
          const key = `${answer.question_id}:${answer.student_response.substring(0, 50)}`;
          if (!groups[key]) groups[key] = [];
          groups[key].push(`${sub.anonymous_student_ref} (Q${sub.answers.indexOf(answer) + 1})`);
        }
      });
    });
    
    setGroupedMistakes(groups);
    showInfo(`Found ${Object.keys(groups).length} mistake groups`);
  };

  const handleViewSubmission = (submission: SubmissionWithAIGrades) => {
    setSelectedSubmission(submission);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setSelectedSubmission(null);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '300px' }}>
        <div style={{ fontSize: '1.2rem', color: 'var(--text-muted)' }}>Loading submissions...</div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-color)', marginBottom: '0.25rem' }}>
            AI Grading Dashboard
          </h1>
          <p style={{ color: 'var(--text-muted)' }}>Review and approve AI-generated grades for exam submissions</p>
        </div>
        <button
          onClick={groupSimilarMistakes}
          style={{ padding: '0.625rem 1.25rem', backgroundColor: '#8b5cf6', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500 }}
        >
          🔍 Group Similar Mistakes
        </button>
      </div>

      {/* Mistake Groups Panel */}
      {Object.keys(groupedMistakes).length > 0 && (
        <div style={{ marginBottom: '1.5rem', padding: '1rem', backgroundColor: '#fef3c7', border: '1px solid #fcd34d', borderRadius: 'var(--radius-md)' }}>
          <h4 style={{ margin: '0 0 0.5rem', color: '#92400e' }}>Similar Mistake Groups</h4>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {Object.entries(groupedMistakes).map(([key, students]) => (
              <span key={key} style={{ padding: '0.25rem 0.75rem', backgroundColor: '#fff', borderRadius: '9999px', fontSize: '0.8rem', border: '1px solid #fcd34d' }}>
                {key}: {students.join(', ')}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Submissions List */}
      <div style={{ backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Student</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Questions</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>AI Grades</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Status</th>
                <th style={{ padding: '1rem', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {submissions.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No submissions found for this exam.
                  </td>
                </tr>
              ) : (
                submissions.map(submission => (
                  <tr key={submission.submission_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '1rem', fontWeight: 500, color: 'var(--text-color)' }}>
                      {submission.anonymous_student_ref}
                    </td>
                    <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>
                      {submission.answers.length} questions
                    </td>
                    <td style={{ padding: '1rem' }}>
                      {submission.ai_grades && Object.keys(submission.ai_grades).length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                          {Object.values(submission.ai_grades).map(grade => (
                            <span key={grade.question_id} style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <span style={{ 
                                width: '8px', 
                                height: '8px', 
                                borderRadius: '50%', 
                                backgroundColor: grade.confidence > 0.9 ? '#10b981' : grade.confidence > 0.7 ? '#f59e0b' : '#ef4444' 
                              }} />
                              Q{submission.answers.findIndex(a => a.question_id === grade.question_id) + 1}: {grade.score}/{submission.answers.find(a => a.question_id === grade.question_id)?.points_possible || 0} ({Math.round(grade.confidence * 100)}%)
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Not generated</span>
                      )}
                    </td>
                    <td style={{ padding: '1rem' }}>
                      {submission.teacher_approved ? (
                        <span style={{ display: 'inline-block', padding: '0.25rem 0.75rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: '#10b98120', color: '#10b981' }}>
                          ✓ Approved
                        </span>
                      ) : submission.ai_grades && Object.keys(submission.ai_grades).length > 0 ? (
                        <span style={{ display: 'inline-block', padding: '0.25rem 0.75rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: '#f59e0b20', color: '#f59e0b' }}>
                          Pending Review
                        </span>
                      ) : (
                        <span style={{ display: 'inline-block', padding: '0.25rem 0.75rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: '#6b728020', color: '#6b7280' }}>
                          Not Graded
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '1rem', textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                        {!submission.ai_grades || Object.keys(submission.ai_grades).length === 0 ? (
                          <button
                            onClick={() => generateAIGrades(submission)}
                            disabled={generatingGrades === submission.submission_id}
                            style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: generatingGrades === submission.submission_id ? 'not-allowed' : 'pointer', fontWeight: 500, fontSize: '0.85rem' }}
                          >
                            {generatingGrades === submission.submission_id ? 'Generating...' : 'Generate AI Grades'}
                          </button>
                        ) : !submission.teacher_approved ? (
                          <>
                            <button
                              onClick={() => handleViewSubmission(submission)}
                              style={{ padding: '0.5rem 1rem', backgroundColor: '#3b82f6', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500, fontSize: '0.85rem' }}
                            >
                              Review
                            </button>
                            <button
                              onClick={() => applyAIGrades(submission)}
                              style={{ padding: '0.5rem 1rem', backgroundColor: '#10b981', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500, fontSize: '0.85rem' }}
                            >
                              Apply All
                            </button>
                          </>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Completed</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Review Modal */}
      {showModal && selectedSubmission && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1rem' }}>
          <div style={{ backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', maxWidth: '800px', width: '100%', maxHeight: '90vh', overflow: 'auto' }}>
            <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Review AI Grades - {selectedSubmission.anonymous_student_ref}</h2>
              <button onClick={handleCloseModal} style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: 'var(--text-muted)' }}>×</button>
            </div>
            <div style={{ padding: '1.5rem' }}>
              {selectedSubmission.answers.map((answer, idx) => {
                const aiGrade = selectedSubmission.ai_grades?.[answer.question_id];
                return (
                  <div key={answer.question_id} style={{ marginBottom: '1.5rem', padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                      <h4 style={{ margin: 0, fontSize: '1rem' }}>Question {idx + 1} ({answer.points_possible} pts)</h4>
                      {aiGrade && (
                        <span style={{ 
                          padding: '0.25rem 0.5rem', 
                          borderRadius: '9999px', 
                          fontSize: '0.75rem', 
                          fontWeight: 600,
                          backgroundColor: aiGrade.score === answer.points_possible ? '#10b98120' : '#ef444420',
                          color: aiGrade.score === answer.points_possible ? '#10b981' : '#ef4444'
                        }}>
                          AI: {aiGrade.score}/{answer.points_possible} ({Math.round(aiGrade.confidence * 100)}%)
                        </span>
                      )}
                    </div>
                    <p style={{ margin: '0.5rem 0', color: 'var(--text-color)' }}>{answer.question_text}</p>
                    <div style={{ marginTop: '0.5rem', padding: '0.75rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                      <strong>Student Response:</strong>
                      <pre style={{ margin: '0.5rem 0 0', whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{answer.student_response || '(empty)'}</pre>
                    </div>
                    {answer.correct_answer && (
                      <div style={{ marginTop: '0.5rem', padding: '0.75rem', backgroundColor: '#10b98110', borderRadius: 'var(--radius-sm)', border: '1px solid #10b98130' }}>
                        <strong>Correct Answer:</strong>
                        <pre style={{ margin: '0.5rem 0 0', whiteSpace: 'pre-wrap', fontFamily: 'inherit', color: '#10b981' }}>{answer.correct_answer}</pre>
                      </div>
                    )}
                    {answer.rubric && (
                      <div style={{ marginTop: '0.5rem', padding: '0.75rem', backgroundColor: '#3b82f610', borderRadius: 'var(--radius-sm)', border: '1px solid #3b82f630' }}>
                        <strong>Rubric:</strong>
                        <pre style={{ margin: '0.5rem 0 0', whiteSpace: 'pre-wrap', fontFamily: 'inherit', color: '#3b82f6' }}>{answer.rubric}</pre>
                      </div>
                    )}
                    {aiGrade && (
                      <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#8b5cf610', borderRadius: 'var(--radius-sm)', border: '1px solid #8b5cf630' }}>
                        <strong>AI Feedback:</strong>
                        <pre style={{ margin: '0.5rem 0 0', whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{aiGrade.feedback}</pre>
                        <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                          Confidence: {Math.round(aiGrade.confidence * 100)}%
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
              <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                <button onClick={handleCloseModal} style={{ padding: '0.625rem 1.25rem', backgroundColor: 'var(--secondary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500 }}>
                  Close
                </button>
                <button 
                  onClick={() => { applyAIGrades(selectedSubmission!); handleCloseModal(); }}
                  style={{ padding: '0.625rem 1.25rem', backgroundColor: '#10b981', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500 }}
                >
                  Apply All Grades
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}