import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { useI18n } from '../contexts/I18nContext';

export function Dashboard() {
  const { t } = useI18n();
  const { user } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  const cards = [
    {
      title: t('dashboard.teacher_settings'),
      description: t('dashboard.teacher_settings_desc'),
      action: { label: t('dashboard.open_teacher'), onClick: () => navigate('/teacher-exams'), variant: 'primary' },
    },
    {
      title: t('dashboard.student_settings'),
      description: t('dashboard.student_settings_desc'),
      action: { label: t('dashboard.open_student'), onClick: () => navigate('/exam'), variant: 'secondary' },
    },
    {
      title: t('dashboard.parent_dashboard'),
      description: t('dashboard.parent_dashboard_desc'),
      action: { label: t('dashboard.open_parent'), onClick: () => navigate('/parent-dashboard'), variant: 'accent' },
    },
    {
      title: t('dashboard.admin_dashboard'),
      description: t('dashboard.admin_dashboard_desc'),
      action: { label: t('dashboard.open_admin'), onClick: () => navigate('/admin'), variant: 'primary' },
      roles: ['teacher', 'admin'],
    },
  ];

  return (
    <div style={{ padding: '1rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-color)', marginBottom: '0.5rem' }}>
          {t('dashboard.welcome', { name: user.full_name || 'User' })}
        </h1>
      </div>
      
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', 
        gap: '1rem',
        maxWidth: '100%'
      }}>
        {cards
          .filter(card => !card.roles || card.roles.includes(user.role))
          .map((card, idx) => (
          <div key={idx} style={{ 
            padding: '1.5rem', 
            backgroundColor: 'var(--sidebar-bg)', 
            borderRadius: 'var(--radius-lg)', 
            border: '1px solid var(--border-color)', 
            display: 'flex', 
            flexDirection: 'column', 
            height: '100%',
            minWidth: 0,
            boxSizing: 'border-box'
          }}>
            <h3 style={{ margin: '0 0 0.5rem', fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-color)', wordWrap: 'break-word' }}>{card.title}</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: 1.5, marginBottom: '1.5rem', flex: 1, wordWrap: 'break-word' }}>{card.description}</p>
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
                boxSizing: 'border-box',
                whiteSpace: 'normal',
                overflowWrap: 'break-word'
              }}>
              {card.action.label}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}