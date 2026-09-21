import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

export function ParentDashboard() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [childrenData, setChildrenData] = useState<any[]>([]);

  useEffect(() => {
    // Mock fetching child progress
    setTimeout(() => {
      setChildrenData([
        {
          id: 1,
          name: 'Tommy Testtaker',
          recentExams: [
            { title: 'Midterm Calculus', score: '88/100', aiFeedback: 'Great job. Minor errors carrying the 1 in question 4.' },
            { title: 'History Quiz', score: '95/100', aiFeedback: 'Excellent grasp of the material.' }
          ]
        }
      ]);
      setLoading(false);
    }, 1000);
  }, []);

  if (!user || user.role !== 'parent') return <div>Unauthorized</div>;

  if (loading) return <div>Loading child progress...</div>;

  return (
    <div>
      <h1>Parent Portal</h1>
      <p style={{ color: 'gray', marginBottom: '2rem' }}>Track your child's academic progress securely.</p>

      {childrenData.map(child => (
        <div key={child.id} style={{ marginBottom: '2rem' }}>
          <h2 style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>{child.name}</h2>
          
          <div style={{ display: 'grid', gap: '1rem', marginTop: '1rem' }}>
            {child.recentExams.map((exam: any, idx: number) => (
              <div key={idx} style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <h3 style={{ margin: 0 }}>{exam.title}</h3>
                  <span style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'var(--primary-color)' }}>{exam.score}</span>
                </div>
                <div style={{ padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: '4px', fontSize: '0.95rem' }}>
                  <strong>Teacher/AI Feedback:</strong><br/>
                  <span style={{ color: 'gray' }}>{exam.aiFeedback}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
