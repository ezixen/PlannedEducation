import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useToast } from '../contexts/ToastContext';

import { SecureChat } from '../components/SecureChat';
import { API_URL } from '../api';

interface ExamQuestion {
  question_id: string;
  question_type: 'multiple_choice' | 'essay' | 'dynamic_math';
  text: string;
  options: string[] | null;
  points: number;
}

interface ExamData {
  submission_id: string;
  questions: ExamQuestion[];
}

export function TakeExam() {
  const { id } = useParams<{ id: string }>();
  const [examData, setExamData] = useState<ExamData | null>(null);
  // Keys are question UUIDs (strings), not numbers
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const { error: showError, success: showSuccess } = useToast();

  useEffect(() => {
    if (!id) return;
    const startExam = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const res = await fetch(`${API_URL}/exams/${id}/start`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!res.ok) {
          const data = await res.json();
          showError('Failed to start exam', data.detail);
          return;
        }
        const data: ExamData = await res.json();
        setExamData(data);
      } catch (err: any) {
        showError('Network error', err.message);
      }
    };
    startExam();
  }, [id, showError]);

  if (submitted) {
    return (
      <div style={{ textAlign: 'center', marginTop: '4rem' }}>
        <h1 style={{ color: 'var(--primary-color)', fontSize: '1.75rem', fontWeight: 700 }}>Exam Submitted Successfully</h1>
        <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>Your answers have been cryptographically sealed. You may now close Safe Exam Browser.</p>
      </div>
    );
  }

  if (!examData) return <div style={{ textAlign: 'center', marginTop: '4rem', color: 'var(--text-muted)' }}>Loading secure exam payload...</div>;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      const token = localStorage.getItem('access_token');
      // Wrap in { answers: [...] } to match backend ExamSubmitRequest schema
      const payload = {
        answers: Object.entries(answers).map(([qId, resp]) => ({
          question_id: qId,   // UUID string — do NOT parseInt
          response: resp,
        })),
      };

      const res = await fetch(`${API_URL}/exams/${id}/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        showSuccess('Exam submitted successfully!');
        setSubmitted(true);
      } else {
        const data = await res.json();
        showError('Failed to submit exam', data.detail);
      }
    } catch (err: any) {
      showError('Network error', err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'flex', gap: '2rem', height: 'calc(100vh - 100px)' }}>
      
      {/* Exam Content */}
      <div style={{ flex: 1, overflowY: 'auto', paddingRight: '1rem' }}>
        <h1 style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem', fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-color)' }}>Secure Exam Mode</h1>
        
        <form onSubmit={handleSubmit}>
          {examData.questions.map((q: any, idx: number) => (
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
                        onChange={(e) => setAnswers({...answers, [q.question_id]: e.target.value})}
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
                  style={{ width: '100%', padding: '0.875rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', resize: 'vertical', fontSize: '0.95rem', lineHeight: 1.6, fontFamily: 'inherit' }}
                  placeholder="Type your answer here..."
                  onChange={(e) => setAnswers({...answers, [q.question_id]: e.target.value})}
                  required
                />
              )}
            </div>
          ))}

          <button 
            type="submit" 
            disabled={submitting}
            style={{ width: '100%', padding: '1rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-lg)', cursor: submitting ? 'not-allowed' : 'pointer', fontSize: '1.1rem', fontWeight: 600, transition: 'background-color 0.15s, opacity 0.15s' }}>
            {submitting ? 'Encrypting & Submitting...' : 'Submit Exam'}
          </button>
        </form>
      </div>

      {/* Secure Chat Sidebar for raising hand */}
      <div style={{ width: '320px', minWidth: '300px', maxWidth: '360px', borderLeft: '1px solid var(--border-color)', paddingLeft: '1.5rem', display: 'flex', flexDirection: 'column' }}>
        <div style={{ marginBottom: '1rem' }}>
          <h3 style={{ marginBottom: '0.5rem', fontSize: '1rem', fontWeight: 600, color: 'var(--text-color)' }}>Digital Hand Raise</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '1rem' }}>Need clarification? Message the teacher without leaving the locked browser.</p>
        </div>
        <div style={{ flex: 1, minHeight: 0 }}>
          <SecureChat examId={id ?? ''} />
        </div>
    </div>
  );
}
