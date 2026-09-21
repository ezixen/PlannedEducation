import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { ProctoringToggle } from '../components/ProctoringToggle';

export function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  return (
    <div>
      <h1>Welcome, {user.full_name}</h1>
      <p style={{ color: 'gray', textTransform: 'capitalize' }}>Role: {user.role}</p>
      
      <div style={{ marginTop: '2rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
        
        {user.role === 'teacher' && (
          <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <h3>Manage Exams</h3>
            <p>Create new exams, edit question banks, and configure SEB locks.</p>
            <button 
              onClick={() => navigate('/teacher-exams')} 
              style={{ marginTop: '1rem', padding: '0.5rem 1rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
              Create Exam
            </button>
          </div>
        )}

        {user.role === 'student' && (
          <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <h3>Upcoming Exams</h3>
            <p>You have 1 exam waiting to be taken.</p>
            <button 
              onClick={() => navigate('/exam')} 
              style={{ marginTop: '1rem', padding: '0.5rem 1rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', marginBottom: '2rem' }}>
              Enter SEB Portal
            </button>
            <ProctoringToggle />
          </div>
        )}

        {user.role === 'parent' && (
          <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <h3>Child's Progress</h3>
            <p>View test scores and teacher feedback.</p>
            <button 
              onClick={() => navigate('/parent-dashboard')} 
              style={{ marginTop: '1rem', padding: '0.5rem 1rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
              View Scores
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
