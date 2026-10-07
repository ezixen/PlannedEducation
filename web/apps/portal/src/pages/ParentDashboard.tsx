import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { API_URL } from '../api';

export function ParentDashboard() {
  const { user } = useAuth();
  
  const [loading, setLoading] = useState(true);
  const [childrenData, setChildrenData] = useState<any[]>([]);

  useEffect(() => {
    
    
    const fetchProgress = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const res = await fetch(`${API_URL}/parents/children-progress`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setChildrenData(data);
        }
      } catch (err) {
        console.error("Failed to fetch children progress", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchProgress();
  }, [user]);

  

  if (loading) return <div>Loading child progress...</div>;

  return (
    <div>
      <h1 style={{ color: 'var(--text-color)', marginBottom: '0.5rem' }}>Parent Portal</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>
        Track your child's academic progress and encouraging teacher feedback securely.
      </p>

      {childrenData.map(child => (
        <div key={child.student_id} style={{ marginBottom: '2rem' }}>
          <h2 style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem', color: 'var(--text-color)' }}>{child.student_name}</h2>
          
          <div style={{ display: 'grid', gap: '1rem', marginTop: '1rem' }}>
            {child.recent_exams.length === 0 && <p style={{ color: 'var(--text-muted)' }}>No completed exams yet.</p>}
            {child.recent_exams.map((exam: any, idx: number) => (
              <div key={idx} style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <h3 style={{ margin: 0, color: 'var(--text-color)' }}>{exam.exam_title}</h3>
                  <span style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'var(--primary-color)' }}>{exam.score}</span>
                </div>
                <div style={{ padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: 'var(--radius-sm)', fontSize: '0.95rem' }}>
                  <strong style={{ color: 'var(--text-color)' }}>Teacher/AI Feedback:</strong><br/>
                  <span style={{ color: 'var(--text-muted)' }}>{exam.feedback}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
