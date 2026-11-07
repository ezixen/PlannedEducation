import { useState, useEffect, useCallback } from 'react';
import { Users, KeyRound, X, CheckCircle2, UserCheck, ShieldCheck, MessageSquare, Trash2 } from 'lucide-react';
import { apiClient } from '../api';
import { useToast } from '../contexts/ToastContext';
import { useI18n } from '../contexts/I18nContext';
import { InfoTip } from '../components/InfoTip';

interface StudentRosterItem {
  id: string;
  name: string;
  email: string;
  iep_multiplier?: number;
  last_login?: string;
  force_password_reset?: boolean;
  is_teacher_aide?: boolean;
}

interface TeacherAideItem {
  id: string;
  username: string;
  full_name: string | null;
  email: string;
  is_teacher_aide: boolean;
  aide_approved_at: string | null;
}

// F-047: no demo PII roster in the public bundle; start empty and load server roster.
const DEFAULT_CLASSES: Array<{ id: number; name: string; students: StudentRosterItem[] }> = [];

export function TeacherClasses() {
  const { t } = useI18n();
  const { success: showSuccess, error: showError } = useToast();
  const [classes, setClasses] = useState<any[]>(() => {
    try {
      // Clear legacy localStorage roster PII; do not restore names/emails from browser storage.
      localStorage.removeItem('pe_teacher_classes');
    } catch {
      // ignore
    }
    return DEFAULT_CLASSES;
  });
  const [newClassName, setNewClassName] = useState('');
  const [registeredStudents, setRegisteredStudents] = useState<StudentRosterItem[]>([]);

  // Teacher's Aides State
  const [aides, setAides] = useState<TeacherAideItem[]>([]);
  const [nominateIdentifier, setNominateIdentifier] = useState('');
  const [nominating, setNominating] = useState(false);

  // Student DM Setting
  const [allowStudentDms, setAllowStudentDms] = useState(false);
  const [updatingDmPolicy, setUpdatingDmPolicy] = useState(false);

  // Selected class for roster view
  const [selectedClass, setSelectedClass] = useState<any | null>(null);
  const [rosterStudents, setRosterStudents] = useState<StudentRosterItem[]>([]);
  const [resettingId, setResettingId] = useState<string | null>(null);

  const loadRegisteredStudents = useCallback(async () => {
    try {
      // F-039: use the real backend endpoint for teacher student roster
      const res = await apiClient.get<any[]>('/auth/teacher/students');
      if (Array.isArray(res.data)) {
        setRegisteredStudents(
          res.data.map(u => ({
            id: u.id,
            name: u.full_name || u.username,
            email: u.email,
            force_password_reset: u.force_password_reset,
            is_teacher_aide: u.is_teacher_aide,
          }))
        );
      }
    } catch {
      // ignore
    }
  }, []);

  const loadAides = useCallback(async () => {
    try {
      const res = await apiClient.get<TeacherAideItem[]>('/auth/teacher-aide/my-aides');
      if (Array.isArray(res.data)) {
        setAides(res.data);
      }
    } catch {
      // ignore
    }
  }, []);

  const loadTeacherProfile = useCallback(async () => {
    try {
      const res = await apiClient.get<any>('/auth/me');
      if (res.data) {
        setAllowStudentDms(!!res.data.allow_student_dms);
      }
    } catch {
      // ignore
    }
  }, []);

  const loadClasses = useCallback(async () => {
    try {
      const res = await apiClient.get<any[]>('/auth/teacher/classes');
      if (!Array.isArray(res.data)) return;
      setClasses(
        res.data.map((c) => ({
          id: c.id,
          name: c.name,
          students: (c.student_ids || []).map((sid: string) => {
            const known = registeredStudents.find((s) => s.id === sid);
            return known || { id: sid, name: sid, email: '' };
          }),
          student_ids: c.student_ids || [],
          student_count: c.student_count ?? (c.student_ids || []).length,
        })),
      );
    } catch {
      // ignore
    }
  }, [registeredStudents]);

  useEffect(() => {
    loadRegisteredStudents();
    loadAides();
    loadTeacherProfile();
  }, [loadRegisteredStudents, loadAides, loadTeacherProfile]);

  useEffect(() => {
    if (registeredStudents.length >= 0) {
      loadClasses();
    }
  }, [loadClasses, registeredStudents.length]);

  const handleCreateClass = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClassName.trim()) return;
    try {
      const res = await apiClient.post('/auth/teacher/classes', {
        name: newClassName.trim(),
        student_ids: registeredStudents.map((s) => s.id),
      });
      const created = res.data;
      setClasses((prev) => [
        ...prev,
        {
          id: created.id,
          name: created.name,
          students: registeredStudents.filter((s) =>
            (created.student_ids || []).includes(s.id),
          ),
          student_ids: created.student_ids || [],
          student_count: created.student_count,
        },
      ]);
      setNewClassName('');
      showSuccess(t('teacher_classes.class_created', { name: created.name }));
    } catch (err: any) {
      showError(
        t('teacher_classes.class_create_failed'),
        err.response?.data?.detail || err.message,
      );
    }
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
    if (!window.confirm(t('teacher_classes.reset_confirm', { name: student.name }))) {
      return;
    }

    setResettingId(student.id);
    try {
      const res = await apiClient.post(`/auth/teacher/quick-reset/${student.id}`);
      showSuccess(res.data?.message || t('teacher_classes.reset_unlocked', { name: student.name }));
      setRosterStudents(prev =>
        prev.map(s => (s.id === student.id ? { ...s, force_password_reset: true } : s))
      );
    } catch (err: any) {
      showError(t('teacher_classes.reset_failed'), err.response?.data?.detail || err.message);
    } finally {
      setResettingId(null);
    }
  };

  const handleNominateAide = async (userIdOrIdentifier: string, isId = true) => {
    setNominating(true);
    try {
      const payload = isId ? { user_id: userIdOrIdentifier } : { identifier: userIdOrIdentifier };
      const res = await apiClient.post('/auth/teacher-aide/nominate', payload);
      const aideName = res.data.full_name || res.data.username;
      showSuccess(t('teacher_classes.nominated', { name: aideName }));
      loadAides();
      loadRegisteredStudents();
      setNominateIdentifier('');
    } catch (err: any) {
      showError(t('teacher_classes.nominate_failed'), err.response?.data?.detail || err.message);
    } finally {
      setNominating(false);
    }
  };

  const handleRevokeAide = async (userId: string, name: string) => {
    if (!window.confirm(t('teacher_classes.revoke_confirm', { name }))) return;
    try {
      await apiClient.post('/auth/teacher-aide/revoke', { user_id: userId });
      showSuccess(t('teacher_classes.revoked', { name }));
      loadAides();
      loadRegisteredStudents();
    } catch (err: any) {
      showError(t('teacher_classes.revoke_failed'), err.response?.data?.detail || err.message);
    }
  };

  const handleToggleStudentDms = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.checked;
    setUpdatingDmPolicy(true);
    try {
      await apiClient.patch('/auth/teacher/settings/student-dms', { allow_student_dms: val });
      setAllowStudentDms(val);
      showSuccess(val ? t('teacher_classes.dm_enabled') : t('teacher_classes.dm_disabled'));
    } catch (err: any) {
      showError(t('teacher_classes.dm_policy_failed'), err.response?.data?.detail || err.message);
    } finally {
      setUpdatingDmPolicy(false);
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '3rem' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-color)' }}>
          {t('teacher_classes.title')}
        </h1>
        <p style={{ margin: '0.25rem 0 0', color: 'var(--text-muted)' }}>
          {t('teacher_classes.subtitle')}
        </p>
      </div>

      {/* Top Banner Settings Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* Student DM Settings Card */}
        <div style={{ padding: '1.25rem', backgroundColor: 'var(--panel-bg)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <MessageSquare size={18} style={{ color: 'var(--primary-color)' }} />
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: 'var(--text-color)' }}>
              {t('teacher_classes.dm_title')}
            </h3>
            <InfoTip tipKey="info.teacher_classes_dms" />
          </div>
          <p style={{ margin: '0 0 1rem', fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
            {t('teacher_classes.dm_desc')}
          </p>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', cursor: 'pointer', fontSize: '0.9rem', color: 'var(--text-color)', fontWeight: 500 }}>
            <input
              type="checkbox"
              checked={allowStudentDms}
              onChange={handleToggleStudentDms}
              disabled={updatingDmPolicy}
              style={{ width: '18px', height: '18px', cursor: 'pointer' }}
            />
            <span>{t('teacher_classes.dm_toggle')}</span>
          </label>
        </div>

        {/* Teacher's Aide Direct Nomination Card */}
        <div style={{ padding: '1.25rem', backgroundColor: 'var(--panel-bg)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <UserCheck size={18} style={{ color: 'var(--primary-color)' }} />
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: 'var(--text-color)' }}>
              {t('teacher_classes.nominate_title')}
            </h3>
          </div>
          <p style={{ margin: '0 0 0.75rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            {t('teacher_classes.nominate_desc')}
          </p>
          <form
            onSubmit={(e) => { e.preventDefault(); if (nominateIdentifier.trim()) handleNominateAide(nominateIdentifier.trim(), false); }}
            style={{ display: 'flex', gap: '0.5rem' }}
          >
            <input
              type="text"
              placeholder={t('teacher_classes.nominate_placeholder')}
              value={nominateIdentifier}
              onChange={(e) => setNominateIdentifier(e.target.value)}
              style={{ flex: 1, padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.85rem' }}
            />
            <button
              type="submit"
              disabled={!nominateIdentifier.trim() || nominating}
              style={{ padding: '0.5rem 1rem', borderRadius: 'var(--radius-md)', border: 'none', backgroundColor: 'var(--primary-color)', color: '#fff', fontWeight: 600, fontSize: '0.85rem', cursor: (!nominateIdentifier.trim() || nominating) ? 'not-allowed' : 'pointer' }}
            >
              {nominating ? t('teacher_classes.nominating') : t('teacher_classes.nominate_btn')}
            </button>
          </form>
        </div>
      </div>

      {/* Approved Teacher's Aides List */}
      {aides.length > 0 && (
        <div style={{ padding: '1.25rem', backgroundColor: 'var(--panel-bg)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <ShieldCheck size={18} style={{ color: '#10b981' }} />
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: 'var(--text-color)' }}>
              {t('teacher_classes.aides_title')} ({aides.length})
            </h3>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '0.75rem' }}>
            {aides.map((a) => (
              <div
                key={a.id}
                style={{ padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--sidebar-bg)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-color)' }}>
                    {a.full_name || a.username}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{a.email}</div>
                </div>
                <button
                  onClick={() => handleRevokeAide(a.id, a.full_name || a.username)}
                  title={t('teacher_classes.revoke_aide')}
                  style={{ background: 'none', border: 'none', color: 'var(--error-color)', cursor: 'pointer', padding: '0.35rem' }}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Create New Class */}
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

      {/* Class List */}
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

      {/* Student Roster Modal */}
      {selectedClass && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.6)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem',
          }}
        >
          <div
            style={{
              backgroundColor: 'var(--panel-bg)',
              borderRadius: 'var(--radius-lg)',
              maxWidth: '680px',
              width: '100%',
              maxHeight: '85vh',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 20px 25px -5px rgba(0,0,0,0.2)',
              border: '1px solid var(--border-color)',
            }}
          >
            <div
              style={{
                padding: '1.25rem',
                borderBottom: '1px solid var(--border-color)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Users size={20} style={{ color: 'var(--primary-color)' }} />
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-color)' }}>
                  {t('teacher_classes.roster_title', { name: selectedClass.name })}
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
                ⚡ <strong>{t('teacher_classes.emergency_reset_title')}</strong> {t('teacher_classes.emergency_reset_desc')}
              </div>

              {rosterStudents.length === 0 ? (
                <p style={{ textAlign: 'center', color: 'var(--text-muted)', margin: '2rem 0' }}>
                  {t('teacher_classes.no_students')}
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
                        <div style={{ fontWeight: 600, color: 'var(--text-color)', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span>{student.name}</span>
                          {student.is_teacher_aide && (
                            <span style={{ fontSize: '0.7rem', padding: '0.1rem 0.4rem', backgroundColor: '#10b98120', color: '#10b981', borderRadius: '4px', fontWeight: 600 }}>
                              {t('teacher_classes.aide_badge')}
                            </span>
                          )}
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
                            <CheckCircle2 size={12} /> {t('teacher_classes.unlocked')}
                          </span>
                        )}

                        {/* Nominate Aide button if not yet aide */}
                        {!student.is_teacher_aide && (
                          <button
                            onClick={() => handleNominateAide(student.id, true)}
                            title={t('teacher_classes.nominate_aide_title')}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.35rem',
                              padding: '0.4rem 0.65rem',
                              backgroundColor: 'var(--sidebar-bg)',
                              color: 'var(--text-color)',
                              border: '1px solid var(--border-color)',
                              borderRadius: 'var(--radius-md)',
                              cursor: 'pointer',
                              fontWeight: 500,
                              fontSize: '0.75rem',
                            }}
                          >
                            <UserCheck size={13} />
                            {t('teacher_classes.nominate_aide_btn')}
                          </button>
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
                          {resettingId === student.id ? t('common.14') : t('admin.reset_password')}
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
