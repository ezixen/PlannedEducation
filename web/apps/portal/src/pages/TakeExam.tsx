import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { SecureChat } from '../components/SecureChat';

export function TakeExam() {
  const { user } = useAuth();
  const [examData, setExamData] = useState<any>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    // Mock fetching the randomized exam from /exams/{id}/start
    setTimeout(() => {
      setExamData({
        title: 'Midterm Calculus',
        questions: [
          { question_id: 1, question_type: 'dynamic_math', text: 'Solve for x: 3x + 6 = 15', points: 10 },
          { question_id: 2, question_type: 'multiple_choice', text: 'What is the derivative of x^2?', options: ['2x', 'x', 'x^2', '2'], points: 5 },
          { question_id: 3, question_type: 'short_answer', text: 'Explain the fundamental theorem of calculus in your own words.', points: 15 }
        ]
      });
    }, 1000);
  }, []);

  if (!user || user.role !== 'student') return <div>Unauthorized</div>;

  if (submitted) {
    return (
      <div style={{ textAlign: 'center', marginTop: '4rem' }}>
        <h1 style={{ color: 'var(--primary-color)' }}>Exam Submitted Successfully</h1>
        <p style={{ color: 'gray' }}>Your answers have been cryptographically sealed. You may now close Safe Exam Browser.</p>
      </div>
    );
  }

  if (!examData) return <div style={{ textAlign: 'center', marginTop: '4rem' }}>Loading secure exam payload...</div>;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    // Mock POST to /exams/{id}/submit
    setTimeout(() => {
      setSubmitting(false);
      setSubmitted(true);
    }, 1500);
  };

  return (
    <div style={{ display: 'flex', gap: '2rem', height: 'calc(100vh - 100px)' }}>
      
      {/* Exam Content */}
      <div style={{ flex: 1, overflowY: 'auto', paddingRight: '1rem' }}>
        <h1 style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>{examData.title}</h1>
        
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

              {(q.question_type === 'short_answer' || q.question_type === 'dynamic_math') && (
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
        <SecureChat examId={1} />
      </div>

    </div>
  );
}
