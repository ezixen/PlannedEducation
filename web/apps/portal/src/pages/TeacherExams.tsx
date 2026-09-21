import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api';

export function TeacherExams() {
  const [exams, setExams] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [newTitle, setNewTitle] = useState('');

  useEffect(() => {
    fetchExams();
  }, []);

  const fetchExams = async () => {
    try {
      const response = await apiClient.get('/exams/');
      setExams(response.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const createExam = async () => {
    if (!newTitle) return;
    try {
      await apiClient.post('/exams/', { title: newTitle, duration_minutes: 60 });
      setNewTitle('');
      fetchExams();
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) return <div>Loading exams...</div>;

  return (
    <div>
      <h1>Manage Exams</h1>
      <p style={{ color: 'gray', marginBottom: '2rem' }}>Create and edit your tests.</p>

      <div style={{ marginBottom: '2rem', display: 'flex', gap: '1rem' }}>
        <input 
          type="text" 
          placeholder="New Exam Title..." 
          value={newTitle} 
          onChange={(e) => setNewTitle(e.target.value)} 
          style={{ padding: '0.5rem', flex: 1, borderRadius: '4px', border: '1px solid var(--border-color)' }}
        />
        <button onClick={createExam} style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
          Create New Exam
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {exams.length === 0 ? (
          <p>You have not created any exams yet.</p>
        ) : (
          exams.map(exam => (
            <div key={exam.id} style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: '0 0 0.5rem 0' }}>{exam.title}</h3>
                <small style={{ color: 'gray' }}>{exam.duration_minutes} minutes | {exam.questions?.length || 0} questions</small>
              </div>
              <div>
                <Link to={`/teacher-exams/${exam.id}`} style={{ padding: '0.5rem 1rem', backgroundColor: '#3b82f6', color: '#fff', textDecoration: 'none', borderRadius: '4px' }}>
                  Edit Editor
                </Link>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
