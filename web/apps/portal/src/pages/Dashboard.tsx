import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { ProctoringToggle } from '../components/ProctoringToggle';

export function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  const cards = user.role === 'teacher' ? [
    {
      title: 'Manage Exams',
      description: 'Create new exams, edit question banks, and configure SEB locks.',
      action: { label: 'Create Exam', onClick: () => navigate('/teacher-exams'), variant: 'primary' },
    },
    {
      title: 'Manage Classes',
      description: 'Group students and configure IEP time accommodations.',
      action: { label: 'View Classes', onClick: () => navigate('/teacher-classes'), variant: 'secondary' },
    },
    {
      title: 'External AI Integrations',
      description: 'Configure automated grading via our secure Anonymizer API.',
      action: { label: 'View AI API', onClick: () => navigate('/ai-integrations'), variant: 'accent' },
    },
  ] : user.role === 'student' ? [
    {
      title: 'Upcoming Exams',
      description: 'You have exams waiting to be taken.',
      action: { label: 'Enter SEB Portal', onClick: () => navigate('/exam'), variant: 'primary' },
    },
  ] : user.role === 'parent' ? [
    {
      title: "Child's Progress",
      description: 'View test scores and teacher feedback.',
      action: { label: 'View Scores', onClick: () => navigate('/parent-dashboard'), variant: 'primary' },
    },
  ] : [];

  return (
    <div>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-color)', marginBottom: '0.5rem' }}>
        Welcome, {user.full_name}
      </h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>Role: <strong style={{ textTransform: 'capitalize' }}>{user.role}</strong></p>
      
      <div style={{ marginTop: '2rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
        {cards.map((card, idx) => (
          <div key={idx} style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', height: '100%' }}>
            <h3 style={{ margin: '0 0 0.5rem', fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-color)' }}>{card.title}</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: 1.5, marginBottom: '1.5rem', flex: 1 }}>{card.description}</p>
            <button 
              onClick={card.action.onClick} 
              style={{ 
                padding: '0.625rem 1.25rem', 
                backgroundColor: card.action.variant === 'primary' ? 'var(--primary-color)' : 
                               card.action.variant === 'secondary' ? '#3b82f6' : 
                               card.action.variant === 'accent' ? '#8b5cf6' : 'var(--primary-color)', 
                color: '#fff', 
                border: 'none', 
                borderRadius: 'var(--radius-md)', 
                cursor: 'pointer',
                fontWeight: 500,
                fontSize: '0.9rem',
                transition: 'background-color 0.15s, opacity 0.15s',
                width: '100%',
              }}>
              {card.action.label}
            </button>
          </div>
        ))}
        
        {user.role === 'student' && (
          <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
            <ProctoringToggle />
          </div>
        )}
      </div>
    </div>
  );
}