import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../api';

export function ExamEditor() {
  const { id } = useParams<{ id: string }>();
  const [exam, setExam] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // New Question Form
  const [qType, setQType] = useState('multiple_choice');
  const [qText, setQText] = useState('');

  useEffect(() => {
    fetchExam();
  }, [id]);

  const fetchExam = async () => {
    try {
      // For now, get all exams and filter. (In a real app, add a GET /exams/{id} endpoint)
      const response = await apiClient.get('/exams/');
      const found = response.data.find((e: any) => e.id === Number(id));
      setExam(found);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const addQuestion = async () => {
    if (!qText) return;
    try {
      await apiClient.post(`/exams/${id}/questions`, {
        question_type: qType,
        text: qText,
        points: 1
      });
      setQText('');
      fetchExam();
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) return <div>Loading exam...</div>;
  if (!exam) return <div>Exam not found.</div>;

  return (
    <div>
      <Link to="/teacher-exams" style={{ color: '#3b82f6', textDecoration: 'none', marginBottom: '1rem', display: 'inline-block' }}>&larr; Back to Exams</Link>
      <h1 style={{ marginBottom: '0.5rem' }}>{exam.title}</h1>
      <p style={{ color: 'gray', marginBottom: '2rem' }}>SEB Config Key: {exam.seb_config_key ? 'Enabled (Locked Down)' : 'Not Set (Insecure)'}</p>

      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', marginBottom: '2rem' }}>
        <h3>Add Question</h3>
        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', alignItems: 'flex-start' }}>
          <select value={qType} onChange={e => setQType(e.target.value)} style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
            <option value="multiple_choice">Multiple Choice</option>
            <option value="essay">Essay / Free Text</option>
            <option value="dynamic_math">Dynamic Math (Variables)</option>
          </select>
          <input 
            type="text" 
            placeholder="Question text..." 
            value={qText} 
            onChange={e => setQText(e.target.value)} 
            style={{ padding: '0.5rem', flex: 1, borderRadius: '4px', border: '1px solid var(--border-color)' }}
          />
          <button onClick={addQuestion} style={{ padding: '0.5rem 1rem', backgroundColor: '#10b981', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Add</button>
        </div>
      </div>

      <h3>Question Bank ({exam.questions?.length || 0})</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
        {exam.questions?.map((q: any, idx: number) => (
          <div key={q.id} style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
            <strong>{idx + 1}. {q.text}</strong>
            <div style={{ color: 'gray', fontSize: '0.9rem', marginTop: '0.5rem' }}>
              Type: <span style={{ textTransform: 'capitalize' }}>{q.question_type.replace('_', ' ')}</span> | Points: {q.points}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
