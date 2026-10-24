import { useState, useEffect, useCallback } from 'react';
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

const DEFAULT_CLASSES = [
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
];

export function TeacherClasses() {
  const { t } = useI18n();
  const { success: showSuccess, error: showError } = useToast();
  const [classes, setClasses] = useState<any[]>(() => {
    try {
      const saved = localStorage.getItem('pe_teacher_classes');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch {
      // ignore
    }
    return DEFAULT_CLASSES;
  });
  const [newClassName, setNewClassName] = useState('');
  const [registeredStudents, setRegisteredStudents] = useState<StudentRosterItem[]>([]);

  // Selected class for roster view
  const [selectedClass, setSelectedClass] = useState<any | null>(null);
  const [rosterStudents, setRosterStudents] = useState<StudentRosterItem[]>([]);
  const [resettingId, setResettingId] = useState<string | null>(null);

  const loadRegisteredStudents = useCallback(async () => {
    try {
      const res = await apiClient.get('/auth/teacher/students');
      if (Array.isArray(res.data)) {
        const mapped: StudentRosterItem[] = res.data.map((s: any) => ({
          id: s.id,
          name: s.full_name || s.username || s.email,
          email: s.email,
          iep_multiplier: 1.0,
          force_password_reset: Boolean(s.force_password_reset),
        }));
        setRegisteredStudents(mapped);
      }
    } catch {
      // ignore if not approved yet
    }
  }, []);

  useEffect(() => {
    void loadRegisteredStudents();
  }, [loadRegisteredStudents]);

  useEffect(() => {
    try {
      localStorage.setItem('pe_teacher_classes', JSON.stringify(classes));
    } catch {
      // ignore
    }
  }, [classes]);

  const handleCreateClass = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClassName.trim()) return;

    const newClass = {
      id: Date.now(),
      name: newClassName.trim(),
      students: registeredStudents,
    };
    setClasses(prev => [...prev, newClass]);
    setNewClassName('');
    showSuccess(`Class "${newClass.name}" created!`);
  };

  const handleOpenRoster = (cls: any) => {
    setSelectedClass(cls);
    const existing: StudentRosterItem[] = cls.students || [];
    const mergedMap = new Map<string, StudentRosterItem>();
    for (const s of existing) mergedMap.set(s.email || s.id, s);
    for (const s of registeredStudents) mergedMap.set(s.email || s.id, s);
    setRosterStudents(Array.from(mergedMap.values()));
  };

  const handleQuickReset = async (student: StudentRosterItem) => {
    if (!window.confirm(`Reset password for ${student.name}?\n\nThe student can immediately type their email at login and set a new password.`)) {
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
          {t('teacher_classes.title')}
        </h1>
        <p style={{ margin: '0.25rem 0 0', color: 'var(--text-muted)' }}>
          {t('teacher_classes.subtitle')}
        </p>
      </div>

      <div style={{ padding: '1.25rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', marginBottom: '1.5rem' }}>
        <h3 style={{ margin: '0 0 0.75rem', fontSize: '1rem', fontWeight: 600, color: 'var(--text-color)' }}>
          {t('teacher_classes.create_new_class')}
        </h3>
        <form onSubmit={handleCreateClass} style={{ display: 'flex', gap: '0.75rem' }}>
          <input
            type="text"
            value={newClassName}
            onChange={e => setNewClassName(e.target.value)}
            placeholder={t('teacher_classes.class_name_placeholder')}
            style={{ flex: 1, padding: '0.65rem 0.85rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
          />
          <button type="submit" style={{ padding: '0.65rem 1.25rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 600 }}>
            {t('teacher_classes.create_class')}
          </button>
        </form>
      </div>

      <div style={{ display: 'grid', gap: '1rem' }}>
        {classes.map(cls => {
          const studentCount = Math.max((cls.students || []).length, registeredStudents.length);
          return (
            <div key={cls.id} style={{ padding: '1.25rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: '0 0 0.25rem 0', fontSize: '1.05rem', color: 'var(--text-color)' }}>{cls.name}</h3>
                <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.85rem' }}>{studentCount} {t('teacher_classes.enrolled_students')}</p>
              </div>
              <div>
                <button
                  onClick={() => handleOpenRoster(cls)}
                  style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--bg-color)', color: 'var(--primary-color)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 600, fontSize: '0.85rem' }}
                >
                  👥 {t('teacher_classes.manage_roster')}
                </button>
              </div>
            </div>
          );
        })}
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
                  {selectedClass.name}
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
                ⚡ <strong>{t('teacher_classes.emergency_reset_title')}</strong> {t('teacher_classes.emergency_reset_desc')} <em>{t('admin.reset_password')}</em>.
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
                            <CheckCircle2 size={12} /> {t('common.10')}
                          </span>
                        )}
                        <button
                          onClick={() => handleQuickReset(student)}
                          disabled={resettingId === student.id}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                            padding: '0.4rem 0.75rem',
                            backgroundColor: '#f59e0b',
                            color: '#fff',
                            border: 'none',
                            borderRadius: 'var(--radius-md)',
                            cursor: resettingId === student.id ? 'not-allowed' : 'pointer',
                            fontWeight: 600,
                            fontSize: '0.8rem',
                          }}
                        >
                          <KeyRound size={14} />
                          {resettingId === student.id ? t('common.loading') : t('admin.reset_password')}
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
