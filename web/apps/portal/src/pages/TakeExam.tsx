import { useParams } from 'react-router-dom';
import { useState } from 'react';
import { useToast } from '../contexts/ToastContext';

import { SecureChat } from '../components/SecureChat';
import { ProctoringSession } from '../components/ProctoringSession';
import { useOfflineExam } from '../hooks/useOfflineExam';

export function TakeExam() {
  const { id } = useParams<{ id: string }>();
  const { error: showError, success: showSuccess, warn: showWarn } = useToast();
  const [submitting] = useState(false);
  
  // Use the new offline exam engine
  const {
    examPackage,
    examState,
    loading,
    initializing,
    timeRemainingFormatted,
    isExamRunning,
    isExamComplete,
    isExamExpired,
    progressPercent,
    currentQuestionIndex,
    totalQuestions,
    startExam,
    saveAnswer,
    submitExam,
    sebViolations,
  } = useOfflineExam({
    examId: id || '',
    onExamFailed: (reason) => {
      showError(`Exam Failed: ${reason}`);
    },
    onExamCompleted: () => {
      showSuccess('Exam completed!');
    },
    onTimeWarning: (minutes) => {
      showWarn(`${minutes} minute${minutes !== 1 ? 's' : ''} remaining!`);
    },
  });

  // Handle exam completion
  if (isExamComplete) {
    return (
      <div style={{ textAlign: 'center', marginTop: '4rem' }}>
        <h1 style={{ color: 'var(--primary-color)', fontSize: '1.75rem', fontWeight: 700 }}>Exam Submitted Successfully</h1>
        <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>Your answers have been cryptographically sealed. You may now close Safe Exam Browser.</p>
      </div>
    );
  }

  if (loading || initializing) {
    return <div style={{ textAlign: 'center', marginTop: '4rem', color: 'var(--text-muted)' }}>Loading secure exam payload...</div>;
  }

  if (!examPackage) {
    return <div style={{ textAlign: 'center', marginTop: '4rem', color: 'var(--text-muted)' }}>Failed to load exam. Please try again.</div>;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await submitExam();
  };

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', minHeight: 'calc(100vh - 100px)' }}>
      
      {/* Exam Content */}
      <div style={{ flex: '1 1 300px', minWidth: 0, overflowY: 'auto' }}>
        {/* Timer & Progress Header */}
        <div style={{ 
          display: 'flex', 
          flexWrap: 'wrap',
          justifyContent: 'space-between', 
          alignItems: 'center',
          gap: '0.75rem',
          padding: '1rem',
          backgroundColor: isExamExpired ? '#fef2f2' : isExamRunning ? '#ecfdf5' : 'var(--sidebar-bg)',
          border: `1px solid ${isExamExpired ? '#fecaca' : isExamRunning ? '#a7f3d0' : 'var(--border-color)'}`,
          borderRadius: 'var(--radius-lg)',
          marginBottom: '1rem',
        }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '1rem' }}>
            <div style={{ 
              fontSize: '1.5rem', 
              fontWeight: 700, 
              fontFamily: 'monospace',
              color: isExamExpired ? '#dc2626' : isExamRunning ? '#059669' : 'var(--text-color)',
            }}>
              {timeRemainingFormatted}
            </div>
            <div style={{ 
              width: '120px', 
              height: '8px', 
              backgroundColor: 'var(--border-color)', 
              borderRadius: '4px',
              overflow: 'hidden',
            }}>
              <div style={{ 
                width: `${progressPercent}%`, 
                height: '100%', 
                backgroundColor: isExamExpired ? '#ef4444' : 'var(--primary-color)',
                transition: 'width 0.3s ease',
              }} />
            </div>
            <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              {progressPercent}% complete
            </span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              Question {currentQuestionIndex + 1} of {totalQuestions}
            </span>
            {!isExamRunning && !isExamComplete && (
              <button
                onClick={startExam}
                style={{
                  padding: '0.625rem 1.25rem',
                  backgroundColor: 'var(--primary-color)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                Start Exam
              </button>
            )}
            {isExamRunning && (
              <button
                onClick={handleSubmit}
                disabled={submitting}
                style={{
                  padding: '0.625rem 1.25rem',
                  backgroundColor: '#ef4444',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  cursor: submitting ? 'not-allowed' : 'pointer',
                  fontWeight: 600,
                }}
              >
                {submitting ? 'Submitting...' : 'Submit Exam'}
              </button>
            )}
          </div>
        </div>
        
        <form onSubmit={handleSubmit}>
          {examPackage.questions.map((q: any, idx: number) => (
            <div key={q.question_id} style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-color)' }}>Question {idx + 1}</h3>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 500 }}>{q.points} pts</span>
              </div>
              <p style={{ fontSize: '1.05rem', marginBottom: '1.5rem', lineHeight: 1.6, color: 'var(--text-color)', wordBreak: 'break-word' }}>{q.text}</p>
              
              {q.question_type === 'multiple_choice' && q.options && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {q.options.map((opt: string, optIdx: number) => (
                    <label key={optIdx} style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', cursor: 'pointer', padding: '0.5rem 0.75rem', backgroundColor: 'var(--bg-color)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', transition: 'background-color 0.15s, border-color 0.15s' }}>
                      <input 
                        type="radio" 
                        name={`q_${q.question_id}`} 
                        value={opt}
                        checked={examState?.answers[q.question_id] === opt}
                        onChange={(e) => saveAnswer(q.question_id, e.target.value)}
                        required
                        style={{ accentColor: 'var(--primary-color)', width: '18px', height: '18px' }}
                      />
                      <span style={{ fontSize: '0.95rem', color: 'var(--text-color)', lineHeight: 1.5, wordBreak: 'break-word' }}>{opt}</span>
                    </label>
                  ))}
                </div>
              )}

              {(q.question_type === 'essay' || q.question_type === 'dynamic_math') && (
                <textarea 
                  rows={5}
                  value={examState?.answers[q.question_id] || ''}
                  onChange={(e) => saveAnswer(q.question_id, e.target.value)}
                  style={{ width: '100%', padding: '0.875rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', resize: 'vertical', fontSize: '0.95rem', lineHeight: 1.6, fontFamily: 'inherit' }}
                  placeholder="Type your answer here..."
                  required
                />
              )}
            </div>
          ))}

          <button 
            type="submit" 
            disabled={submitting || !isExamRunning}
            style={{ width: '100%', padding: '1rem', backgroundColor: isExamRunning ? 'var(--primary-color)' : '#94a3b8', color: '#fff', border: 'none', borderRadius: 'var(--radius-lg)', cursor: isExamRunning ? (submitting ? 'not-allowed' : 'pointer') : 'not-allowed', fontSize: '1.1rem', fontWeight: 600, transition: 'background-color 0.15s, opacity 0.15s' }}>
            {submitting ? 'Encrypting & Submitting...' : isExamRunning ? 'Submit Exam' : 'Start Exam to Enable Submit'}
          </button>
        </form>
      </div>

      {/* Secure Chat Sidebar for raising hand */}
      <div style={{ flex: '1 1 260px', maxWidth: '100%', boxSizing: 'border-box', borderLeft: '1px solid var(--border-color)', paddingLeft: '1rem', display: 'flex', flexDirection: 'column' }}>
        {/* Timer Mini Display */}
        <div style={{ 
          padding: '1rem', 
          backgroundColor: isExamExpired ? '#fef2f2' : isExamRunning ? '#ecfdf5' : 'var(--sidebar-bg)',
          border: `1px solid ${isExamExpired ? '#fecaca' : isExamRunning ? '#a7f3d0' : 'var(--border-color)'}`,
          borderRadius: 'var(--radius-lg)',
          marginBottom: '1.5rem',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>
            Time Remaining
          </div>
          <div style={{ 
            fontSize: '2rem', 
            fontWeight: 700, 
            fontFamily: 'monospace',
            color: isExamExpired ? '#dc2626' : isExamRunning ? '#059669' : 'var(--text-color)',
          }}>
            {timeRemainingFormatted}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
            {isExamExpired ? 'TIME EXPIRED' : isExamRunning ? 'EXAM IN PROGRESS' : 'NOT STARTED'}
          </div>
        </div>

        {/* SEB Violations Warning */}
        {sebViolations.length > 0 && (
          <div style={{ 
            padding: '1rem', 
            backgroundColor: '#fef2f2', 
            border: '1px solid #fecaca', 
            borderRadius: 'var(--radius-lg)',
            marginBottom: '1.5rem',
          }}>
            <h4 style={{ margin: '0 0 0.5rem 0', color: '#dc2626', fontSize: '0.875rem' }}>
              ⚠️ Security Violations Detected
            </h4>
            <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.75rem', color: '#991b1b' }}>
              {sebViolations.slice(-3).map((v, i) => (
                <li key={i}>{v.type} at {new Date(v.timestamp).toLocaleTimeString()}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Proctoring Session */}
        <div style={{ marginBottom: '1.5rem' }}>
          <ProctoringSession 
            examId={id ?? ''} 
            submissionId={examState?.submissionId || ''}
            onSessionComplete={(stats) => {
              console.log('Proctoring session complete:', stats);
            }}
          />
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <h3 style={{ marginBottom: '0.5rem', fontSize: '1rem', fontWeight: 600, color: 'var(--text-color)' }}>Digital Hand Raise</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '1rem' }}>Need clarification? Message the teacher without leaving the locked browser.</p>
        </div>
        <div style={{ flex: 1, minHeight: 0 }}>
          <SecureChat examId={id ?? ''} />
        </div>
      </div>
    </div>
  );
}
