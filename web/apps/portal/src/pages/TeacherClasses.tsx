import { useState, useEffect } from 'react';
import { Users, KeyRound, X, CheckCircle2 } from 'lucide-react';
import { apiClient } from '../api';
import { useToast } from '../contexts/ToastContext';
import { useI18n } from '../contexts/I18nContext';

interface StudentRosterItem {
  id: string;
  name: string;
  email: string;
  iep_multiplier?: number;
  last_login?: string;
  force_password_reset?: boolean;
}

export function TeacherClasses() {
  const { t } = useI18n();
  const { success: showSuccess, error: showError } = useToast();
  const [classes, setClasses] = useState<any[]>([]);
  const [newClassName, setNewClassName] = useState('');
  
  // Selected class for roster view
  const [selectedClass, setSelectedClass] = useState<any | null>(null);
  const [rosterStudents, setRosterStudents] = useState<StudentRosterItem[]>([]);
  const [resettingId, setResettingId] = useState<string | null>(null);

  useEffect(() => {
    // Initial classes
    setClasses([
      {
        id: 1,
        name: 'Calculus 101 - Fall 2026',
        students: [
          { id: 'student-1', name: 'Alex Johnson', email: 'alex@school.edu', iep_multiplier: 1.0 },
          { id: 'student-2', name: 'Emma Watson', email: 'emma@school.edu', iep_multiplier: 1.5 },
          { id: 'student-3', name: 'Lucas Miller', email: 'lucas@school.edu', iep_multiplier: 1.0 },
          { id: 'student-4', name: 'Sophia Davis', email: 'sophia@school.edu', iep_multiplier: 1.25 },
        ],
      },
      {
        id: 2,
        name: 'AP History - Spring 2027',
        students: [
          { id: 'student-5', name: 'Daniel Brown', email: 'daniel@school.edu', iep_multiplier: 1.0 },
          { id: 'student-6', name: 'Olivia Garcia', email: 'olivia@school.edu', iep_multiplier: 1.0 },
        ],
      },
    ]);
  }, []);

  const handleCreateClass = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClassName.trim()) return;
    
    const newClass = {
      id: Date.now(),
      name: newClassName.trim(),
      students: [],
    };
    setClasses([...classes, newClass]);
    setNewClassName('');
    showSuccess(`Class "${newClass.name}" created!`);
  };

  const handleOpenRoster = (cls: any) => {
    setSelectedClass(cls);
    setRosterStudents(cls.students || []);
  };

  const handleQuickReset = async (student: StudentRosterItem) => {
    if (!window.confirm(`Unlock and reset password for ${student.name}?\n\nThe student can immediately type their email at login and set a new password to take the test.`)) {
      return;
    }

    setResettingId(student.id);
    try {
      const res = await apiClient.post(`/auth/teacher/quick-reset/${student.id}`);
      showSuccess(res.data?.message || `Password reset unlocked for ${student.name}`);
      setRosterStudents(prev =>
        prev.map(s => (s.id === student.id ? { ...s, force_password_reset: true } : s))
      );
    } catch (err: any) {
      showError('Quick reset failed', err.response?.data?.detail || err.message);
    } finally {
      setResettingId(null);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-color)' }}>
          Class Groupings & Student Rosters
        </h1>
        <p style={{ margin: '0.25rem 0 0', color: 'var(--text-muted)' }}>
          Manage your classes, enroll students, and provide instant classroom password unlocks right before exams.
        </p>
      </div>

      <div style={{ padding: '1.25rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', marginBottom: '1.5rem' }}>
        <h3 style={{ margin: '0 0 0.75rem', fontSize: '1rem', fontWeight: 600, color: 'var(--text-color)' }}>
          Create New Class
        </h3>
        <form onSubmit={handleCreateClass} style={{ display: 'flex', gap: '0.75rem' }}>
          <input 
            type="text" 
            value={newClassName}
            onChange={(e) => setNewClassName(e.target.value)}
            placeholder={t("teacher_classes.class_name_placeholder")} 
            style={{ flex: 1, padding: '0.65rem 0.85rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
          />
          <button type="submit" style={{ padding: '0.65rem 1.25rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 600 }}>
            Create Class
          </button>
        </form>
      </div>

      <div style={{ display: 'grid', gap: '1rem' }}>
        {classes.map(cls => (
          <div key={cls.id} style={{ padding: '1.25rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ margin: '0 0 0.25rem 0', fontSize: '1.05rem', color: 'var(--text-color)' }}>{cls.name}</h3>
              <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.85rem' }}>{cls.students.length} Enrolled Students</p>
            </div>
            <div>
              <button
                onClick={() => handleOpenRoster(cls)}
                style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--bg-color)', color: 'var(--primary-color)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 600, fontSize: '0.85rem' }}
              >
                👥 Manage Roster & Passwords
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Classroom Student Roster & Quick Password Reset Modal */}
      {selectedClass && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1100,
            padding: '1rem',
          }}
        >
          <div
            style={{
              backgroundColor: 'var(--sidebar-bg)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--border-color)',
              width: '100%',
              maxWidth: '640px',
              maxHeight: '85vh',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 20px 25px -5px rgba(0,0,0,0.2)',
            }}
          >
            <div
              style={{
                padding: '1rem 1.25rem',
                borderBottom: '1px solid var(--border-color)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                backgroundColor: 'var(--bg-color)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Users size={20} style={{ color: 'var(--primary-color)' }} />
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-color)' }}>
                  {selectedClass.name} — Student Roster
                </h3>
              </div>
              <button
                onClick={() => setSelectedClass(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ padding: '1rem 1.25rem', overflowY: 'auto' }}>
              <div
                style={{
                  padding: '0.75rem',
                  backgroundColor: 'rgba(16, 185, 129, 0.08)',
                  border: '1px solid #10b981',
                  borderRadius: 'var(--radius-md)',
                  color: '#047857',
                  fontSize: '0.825rem',
                  marginBottom: '1rem',
                  lineHeight: 1.4,
                }}
              >
                ⚡ <strong>{t('teacher_classes.emergency_reset_title')}</strong> {t('teacher_classes.emergency_reset_desc')} <em>{t('admin.reset_password')}</em>. The student can then simply type their email at login and set a new password immediately!
              </div>

              {rosterStudents.length === 0 ? (
                <p style={{ textAlign: 'center', color: 'var(--text-muted)', margin: '2rem 0' }}>
                  {t('teacher_dashboard.no_students')}
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                  {rosterStudents.map(student => (
                    <div
                      key={student.id}
                      style={{
                        padding: '0.75rem 1rem',
                        backgroundColor: 'var(--bg-color)',
                        border: '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-md)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, color: 'var(--text-color)', fontSize: '0.95rem' }}>
                          {student.name}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          {student.email}
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        {student.force_password_reset && (
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.2rem',
                              padding: '0.2rem 0.5rem',
                              backgroundColor: '#10b98120',
                              color: '#10b981',
                              borderRadius: '9999px',
                              fontSize: '0.75rem',
                              fontWeight: 600,
                            }}
                          >
                            <CheckCircle2 size={12} /> Unlocked
                          </span>
                        )}

                        <button
                          onClick={() => handleQuickReset(student)}
                          disabled={resettingId === student.id}
                          style={{
                            padding: '0.4rem 0.75rem',
                            backgroundColor: 'rgba(16, 185, 129, 0.12)',
                            color: '#059669',
                            border: '1px solid rgba(16, 185, 129, 0.3)',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '0.8rem',
                            fontWeight: 600,
                            cursor: resettingId === student.id ? 'not-allowed' : 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                          }}
                        >
                          <KeyRound size={14} />
                          {resettingId === student.id ? 'Unlocking...' : '⚡ Reset Pwd for Test'}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
