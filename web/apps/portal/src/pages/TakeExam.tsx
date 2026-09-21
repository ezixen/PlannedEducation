import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';

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
  const [error, setError] = useState('');

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
          setError(data.detail || 'Failed to start exam');
          return;
        }
        const data: ExamData = await res.json();
        setExamData(data);
      } catch (err: any) {
        setError(err.message || 'Network error');
      }
    };
    startExam();
  }, [id]);

  

  if (error) {
    return <div style={{ color: 'red', textAlign: 'center', marginTop: '4rem' }}>{error}</div>;
  }

  if (submitted) {
    return (
      <div style={{ textAlign: 'center', marginTop: '4rem' }}>
        <h1 style={{ color: 'var(--primary-color)' }}>Exam Submitted Successfully</h1>
        <p style={{ color: 'gray' }}>Your answers have been cryptographically sealed. You may now close Safe Exam Browser.</p>
      </div>
    );
  }

  if (!examData) return <div style={{ textAlign: 'center', marginTop: '4rem' }}>Loading secure exam payload...</div>;

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
        body: JSON.stringify(payload) // ExamSubmitRequest expects list of answers directly? Wait, schema: ExamSubmitRequest is NOT used in the signature directly, it's `answers: list[dict]` but fastAPI expects list of objects! Oh wait, let's check routes_exam.py
      });
      if (res.ok) {
        setSubmitted(true);
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to submit exam');
      }
    } catch (err: any) {
      setError(err.message || 'Network error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'flex', gap: '2rem', height: 'calc(100vh - 100px)' }}>
      
      {/* Exam Content */}
      <div style={{ flex: 1, overflowY: 'auto', paddingRight: '1rem' }}>
        <h1 style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>Secure Exam Mode</h1>
        
        <form onSubmit={handleSubmit}>
          {examData.questions.map((q: any, idx: number) => (
            <div key={q.question_id} style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <h3 style={{ margin: 0 }}>Question {idx + 1}</h3>
                <span style={{ color: 'gray', fontSize: '0.9rem' }}>{q.points} pts</span>
              </div>
              <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>{q.text}</p>
              
              {q.question_type === 'multiple_choice' && q.options && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {q.options.map((opt: string, optIdx: number) => (
                    <label key={optIdx} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                      <input 
                        type="radio" 
                        name={`q_${q.question_id}`} 
                        value={opt}
                        onChange={(e) => setAnswers({...answers, [q.question_id]: e.target.value})}
                        required
                      />
                      {opt}
                    </label>
                  ))}
                </div>
              )}

              {(q.question_type === 'essay' || q.question_type === 'dynamic_math') && (
                <textarea 
                  rows={4}
                  style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', resize: 'vertical' }}
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
            style={{ width: '100%', padding: '1rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: '8px', cursor: submitting ? 'not-allowed' : 'pointer', fontSize: '1.1rem', fontWeight: 'bold' }}>
            {submitting ? 'Encrypting & Submitting...' : 'Submit Exam'}
          </button>
        </form>
      </div>

      {/* Secure Chat Sidebar for raising hand */}
      <div style={{ width: '300px', borderLeft: '1px solid var(--border-color)', paddingLeft: '2rem' }}>
        <h3 style={{ marginBottom: '1rem' }}>Digital Hand Raise</h3>
        <p style={{ fontSize: '0.9rem', color: 'gray', marginBottom: '1rem' }}>Need clarification? Message the teacher without leaving the locked browser.</p>
        <SecureChat examId={id ?? ''} />
      </div>

    </div>
  );
}
