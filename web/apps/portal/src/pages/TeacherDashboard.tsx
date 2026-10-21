import { useState, useEffect, useRef } from 'react';
import { Upload } from 'lucide-react';
import { useParams } from 'react-router-dom';
import { useToast } from '../contexts/ToastContext';
import { useI18n } from '../contexts/I18nContext';
import { apiClient } from '../api';
import { PackageManager } from '../components/PackageManager';
import { ChatGptPanel } from '../components/ChatGptPanel';
import {
  TeacherCorrectionModal,
  type AIGrade,
  type SubmissionWithAIGrades,
} from '../components/TeacherCorrectionModal';
import { TeacherHandRaiseMonitor } from '../components/TeacherHandRaiseMonitor';

interface StudentHeartbeat {
  student_id: string;
  student_name: string;
  submission_id: string;
  started_at: string | null;
  completed_at: string | null;
  is_complete: boolean;
  score: number | null;
}

// Archive System Types
interface ArchiveItem {
  id: string;
  submission_id: string;
  exam_id: string;
  student_id: string;
  teacher_id: string;
  archive_year: number;
  archive_month: number;
  archive_path: string;
  original_size: number;
  compressed_size: number;
  compression_ratio: number;
  compression_algorithm: string;
  status: string;
  submitted_at: string;
  archived_at: string;
  deleted_from_server_at: string | null;
}

interface ArchiveStats {
  total_archives: number;
  total_size_bytes: number;
  total_size_mb: number;
  original_size_bytes: number;
  compression_savings_mb: number;
  by_year: Array<{ year: number; count: number; size_mb: number }>;
}

export function TeacherDashboard() {
  const { t } = useI18n();
  const { examId } = useParams<{ examId: string }>();
  const { success: showSuccess, error: showError, info: showInfo } = useToast();

  const [submissions, setSubmissions] = useState<SubmissionWithAIGrades[]>([]);
  const [loading, setLoading] = useState(true);
  const [generatingGrades, setGeneratingGrades] = useState<string | null>(null);
  const [selectedSubmission, setSelectedSubmission] = useState<SubmissionWithAIGrades | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [groupedMistakes, setGroupedMistakes] = useState<Record<string, string[]>>({});
  const [reviewingQuestionId, setReviewingQuestionId] = useState<string | null>(null);
  const [selectedSubmissions, setSelectedSubmissions] = useState<string[]>([]);
  const [statusFilter, setStatusFilter] = useState<'all' | 'ungraded' | 'pending_approval' | 'graded'>('all');
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  
  // Heartbeat monitoring state
  const [heartbeats, setHeartbeats] = useState<StudentHeartbeat[]>([]);
  const [heartbeatLoading, setHeartbeatLoading] = useState(false);
  const [heartbeatError, setHeartbeatError] = useState<string | null>(null);
  
  // Archive System State
  const [archives, setArchives] = useState<ArchiveItem[]>([]);
  const [archiveStats, setArchiveStats] = useState<ArchiveStats | null>(null);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [archiveYearFilter, setArchiveYearFilter] = useState<number | 'all'>('all');
  const [archiveMonthFilter, setArchiveMonthFilter] = useState<number | 'all'>('all');
  const [archiveStatusFilter, setArchiveStatusFilter] = useState<'all' | 'active' | 'archived' | 'deleted'>('all');
  const [showArchiveModal, setShowArchiveModal] = useState(false);
  const [selectedArchive, setSelectedArchive] = useState<ArchiveItem | null>(null);
  
  // Test Module Preview State
  const [showTestModuleModal, setShowTestModuleModal] = useState(false);
  const [testModuleCount, setTestModuleCount] = useState(5);
  const [testModuleLoading, setTestModuleLoading] = useState(false);

  useEffect(() => {
    fetchSubmissions();
    fetchArchives();
    fetchArchiveStats();
  }, [examId]);

  // Heartbeat polling for real-time monitoring
  useEffect(() => {
    if (!examId) return;
    
    let intervalId: number;
    let isMounted = true;
    
    const fetchHeartbeats = async () => {
      setHeartbeatLoading(true);
      try {
        const response = await apiClient.get(`/exams/${examId}/heartbeats`);
        if (isMounted) {
          setHeartbeats(response.data.heartbeats || []);
          setHeartbeatError(null);
        }
      } catch (err: any) {
        if (isMounted) {
          setHeartbeatError(err.response?.data?.detail || err.message);
        }
      } finally {
        if (isMounted) {
          setHeartbeatLoading(false);
        }
      }
    };
    
    // Initial fetch
    fetchHeartbeats();
    
    // Poll every 10 seconds
    intervalId = window.setInterval(fetchHeartbeats, 10000);
    
    return () => {
      isMounted = false;
      if (intervalId) clearInterval(intervalId);
    };
  }, [examId]);

  const handleQuickResetStudent = async (studentId: string, studentName: string) => {
    if (!window.confirm(t('teacher_dashboard.quick_reset_confirm', { name: studentName }))) return;
    try {
      const res = await apiClient.post(`/auth/teacher/quick-reset/${studentId}`);
      showSuccess(res.data?.message || `Password reset initiated for ${studentName}`);
    } catch (err: any) {
      showError('Reset failed', err.response?.data?.detail || err.message);
    }
  };

  const fetchSubmissions = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/archive/teacher/class-submissions', {
        params: examId ? { exam_id: examId } : {},
      });
      const rawData = response.data || [];
      setSubmissions(
        rawData.map((s: any) => {
          const initialGrades: Record<string, AIGrade> = {};
          let hasSavedGrades = false;
          for (const ans of s.answers || []) {
            if (ans.saved_score !== undefined && ans.saved_score !== null) {
              hasSavedGrades = true;
              initialGrades[ans.question_id] = {
                question_id: ans.question_id,
                score: ans.saved_score,
                feedback: ans.saved_feedback || '',
                confidence: 1.0,
                teacher_score: ans.saved_score,
                teacher_feedback: ans.saved_feedback || '',
                teacher_corrected_answer: ans.saved_corrected_answer ?? ans.correct_answer ?? '',
                teacher_approved: true,
              };
            }
          }
          return {
            ...s,
            anonymous_student_ref: s.anonymous_ref || `Student (${s.student_name || 'Anonymous'})`,
            student_name: s.student_name,
            exam_title: s.exam_title,
            status: s.status,
            archive_id: s.archive_id,
            archive_path: s.archive_path,
            total_possible: s.total_possible,
            ai_grades: initialGrades,
            teacher_approved: Boolean(s.status === 'graded' || (s.score !== null && hasSavedGrades)),
          };
        })
      );
    } catch (err: any) {
      console.error('Failed to fetch class submissions:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAIGradeSelected = async () => {
    if (selectedSubmissions.length === 0) {
      showError('Please select at least one submission.');
      return;
    }
    setGeneratingGrades('batch');
    try {
      const res = await apiClient.post('/archive/teacher/ai-grade', {
        submission_ids: selectedSubmissions,
      });
      showSuccess(res.data.message || `AI graded ${selectedSubmissions.length} submissions into staging.`);
      fetchSubmissions();
      setSelectedSubmissions([]);
    } catch (err: any) {
      showError('AI grading failed', err.response?.data?.detail || err.message);
    } finally {
      setGeneratingGrades(null);
    }
  };

  const handleApproveSelected = async () => {
    if (selectedSubmissions.length === 0) {
      showError('Please select at least one submission to approve.');
      return;
    }
    try {
      const res = await apiClient.post('/archive/teacher/approve', {
        submission_ids: selectedSubmissions,
      });
      showSuccess(res.data.message || `Approved & archived ${selectedSubmissions.length} submissions.`);
      fetchSubmissions();
      fetchArchives();
      fetchArchiveStats();
      setSelectedSubmissions([]);
    } catch (err: any) {
      showError('Approval failed', err.response?.data?.detail || err.message);
    }
  };

  const handleReopenSubmission = async (subId: string) => {
    try {
      const res = await apiClient.post('/archive/teacher/reopen', {
        submission_id: subId,
      });
      showSuccess(res.data.message || 'Submission reopened for review and re-correction.');
      fetchSubmissions();
    } catch (err: any) {
      showError('Failed to reopen', err.response?.data?.detail || err.message);
    }
  };

  const handleUploadOfflineTest = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    if (examId) formData.append('exam_id', examId);
    try {
      const res = await apiClient.post('/archive/teacher/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      showSuccess(res.data.message || 'Test package uploaded to Archive Browser.');
      fetchSubmissions();
    } catch (err: any) {
      showError('Upload failed', err.response?.data?.detail || err.message);
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Archive System Functions
  const fetchArchiveStats = async () => {
    try {
      const response = await apiClient.get('/archive/teacher/stats');
      setArchiveStats(response.data);
    } catch (err: any) {
      console.error('Failed to load archive stats:', err);
    }
  };

  const fetchArchives = async () => {
    setArchiveLoading(true);
    try {
      const params: Record<string, any> = { limit: 100 };
      if (archiveYearFilter !== 'all') params.year = archiveYearFilter;
      if (archiveMonthFilter !== 'all') params.month = archiveMonthFilter;
      if (archiveStatusFilter !== 'all') params.status = archiveStatusFilter;
      
      const response = await apiClient.get('/archive/teacher/my-archives', { params });
      setArchives(response.data);
    } catch (err: any) {
      console.error('Failed to load archives:', err);
    } finally {
      setArchiveLoading(false);
    }
  };

  const handleDownloadArchive = async (archiveId: string) => {
    try {
      const response = await apiClient.get(`/archive/download/${archiveId}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `archive-${archiveId}.zst.enc`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      showSuccess('Archive downloaded');
    } catch (err: any) {
      showError('Failed to download archive', err.response?.data?.detail || err.message);
    }
  };

  const handleRestoreArchive = async (archiveId: string) => {
    if (!window.confirm('Restore this archive to server storage?')) return;
    try {
      await apiClient.post('/archive/restore', { archive_id: archiveId, target_location: 'server' });
      showSuccess('Archive restored');
      fetchArchives();
    } catch (err: any) {
      showError('Failed to restore archive', err.response?.data?.detail || err.message);
    }
  };

  const handleDeleteArchive = async (archiveId: string) => {
    if (!window.confirm('Delete this archive from server storage? External backup will be kept.')) return;
    try {
      await apiClient.delete(`/archive/archives/${archiveId}`, { params: { keep_external: true } });
      showSuccess('Archive deleted from server');
      fetchArchives();
    } catch (err: any) {
      showError('Failed to delete archive', err.response?.data?.detail || err.message);
    }
  };

  const handleViewArchive = (archive: ArchiveItem) => {
    setSelectedArchive(archive);
    setShowArchiveModal(true);
  };

  // Test Module Preview Functions
  const handleOpenTestModuleModal = () => {
    setTestModuleCount(5);
    setShowTestModuleModal(true);
  };

  const handleCloseTestModuleModal = () => {
    setShowTestModuleModal(false);
  };

  const handleOpenTestModules = async () => {
    if (!examId) return;
    if (testModuleCount < 1 || testModuleCount > 25) {
      showError('Please enter a number between 1 and 25');
      return;
    }
    
    setTestModuleLoading(true);
    try {
      // Open multiple tabs with randomized tests
      for (let i = 0; i < testModuleCount; i++) {
        // Open a new tab with the exam in test mode
        const testUrl = `${window.location.origin}/exam/${examId}?test_mode=true&random_seed=${Date.now() + i}`;
        window.open(testUrl, `_blank`);
        
        // Small delay to prevent popup blocking
        if (i < testModuleCount - 1) {
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      }
      showSuccess(`Opened ${testModuleCount} randomized test tabs`);
    } catch (err: any) {
      showError('Failed to open test tabs', err.message);
    } finally {
      setTestModuleLoading(false);
    }
  };

  const generateAIGrades = async (submission: SubmissionWithAIGrades) => {
    setGeneratingGrades(submission.submission_id);
    try {
      const aiGrades: Record<string, AIGrade> = {};
      
      for (const answer of submission.answers) {
        let aiGrade: { score: number; feedback: string; confidence: number; reasoning?: string };
        try {
          // Call AI grading endpoint when provider is configured
          const response = await apiClient.post('/ai/grade', {
            submission_id: submission.submission_id,
            rubric: answer.rubric || 'Grade based on correctness and completeness.',
            student_response: answer.student_response || '',
            question_text: answer.question_text,
            points_possible: answer.points_possible,
          });
          aiGrade = response.data;
        } catch {
          // Deterministic local rubric/answer evaluation fallback (local-first mode)
          const respNorm = (answer.student_response || '').trim().toLowerCase();
          const corrNorm = (answer.correct_answer || '').trim().toLowerCase();
          const hasRubric = Boolean((answer.rubric || '').trim());
          const isExactMatch = Boolean(corrNorm && respNorm === corrNorm);
          const hasContent = respNorm.length > 0;
          const isObjectiveMismatch = Boolean(
            corrNorm && (answer.question_type === 'multiple_choice' || !hasRubric) && !isExactMatch
          );
          aiGrade = {
            score: isExactMatch
              ? answer.points_possible
              : isObjectiveMismatch
                ? 0
                : hasContent
                  ? Math.round(answer.points_possible * 0.8 * 10) / 10
                  : 0,
            feedback: isExactMatch
              ? 'Correct response matching expected answer.'
              : isObjectiveMismatch
                ? `Incorrect response. Expected: ${answer.correct_answer}`
                : hasContent
                  ? 'Evaluated via local rubric matcher. Teacher review recommended.'
                  : 'No response provided.',
            confidence: isExactMatch || isObjectiveMismatch ? 0.98 : 0.85,
            reasoning: 'Deterministic local rubric evaluation.',
          };
        }
        
        aiGrades[answer.question_id] = {
          question_id: answer.question_id,
          score: aiGrade.score,
          feedback: aiGrade.feedback,
          confidence: aiGrade.confidence,
          reasoning: aiGrade.reasoning,
          // Initialize teacher fields with AI suggestions and expected solution
          teacher_score: aiGrade.score,
          teacher_feedback: aiGrade.feedback,
          teacher_corrected_answer: answer.saved_corrected_answer ?? answer.correct_answer ?? '',
          teacher_approved: false,
        };
      }
      
      setSubmissions(prev => prev.map(s => 
        s.submission_id === submission.submission_id 
          ? { ...s, ai_grades: aiGrades }
          : s
      ));
      
      showSuccess('AI grades generated successfully!');
    } catch (err: any) {
      showError('Failed to generate AI grades.', err.response?.data?.detail || err.message);
    } finally {
      setGeneratingGrades(null);
    }
  };

  const applyAIGrades = async (submission: SubmissionWithAIGrades, approveAll = false) => {
    if (!submission.ai_grades) return;
    
    try {
      const allGrades = Object.values(submission.ai_grades);
      const approvedGrades = approveAll
        ? allGrades
        : allGrades.filter(g => g.teacher_approved);
      
      const targetGrades = approvedGrades.length > 0 ? approvedGrades : allGrades;
      if (targetGrades.length === 0) {
        showError('No grades available to apply.');
        return;
      }
      
      const questionGrades = targetGrades.map(g => {
        const answerObj = submission.answers.find(a => a.question_id === g.question_id);
        return {
          question_id: g.question_id,
          score: g.teacher_score ?? g.score,
          feedback: g.teacher_feedback ?? g.feedback,
          corrected_answer: g.teacher_corrected_answer ?? answerObj?.correct_answer ?? '',
        };
      });
      
      const totalScore = questionGrades.reduce((sum, g) => sum + g.score, 0);
      await apiClient.post('/archive/teacher/approve', {
        submission_ids: [submission.submission_id],
        overrides: {
          [submission.submission_id]: {
            score: totalScore,
            feedback: JSON.stringify({
              summary_feedback: questionGrades.map(g => g.feedback).join(' | '),
              question_grades: questionGrades,
            }),
          },
        },
      });
      fetchArchives();
      fetchArchiveStats();
      
      setSubmissions(prev => prev.map(s => {
        if (s.submission_id !== submission.submission_id) return s;
        const updatedGrades: Record<string, AIGrade> = {};
        if (s.ai_grades) {
          for (const [k, v] of Object.entries(s.ai_grades)) {
            updatedGrades[k] = { ...v, teacher_approved: true };
          }
        }
        return { ...s, ai_grades: updatedGrades, teacher_approved: true };
      }));
      
      showSuccess(t('teacher_dashboard.grades_saved', { count: String(questionGrades.length) }));
    } catch (err: any) {
      showError(t('teacher_dashboard.apply_grades_error'), err.response?.data?.detail || err.message);
    }
  };

  const approveAllQuestions = (submissionId: string) => {
    const updateSub = (s: SubmissionWithAIGrades): SubmissionWithAIGrades => {
      if (s.submission_id !== submissionId || !s.ai_grades) return s;
      const nextGrades: Record<string, AIGrade> = {};
      for (const [qid, g] of Object.entries(s.ai_grades)) {
        nextGrades[qid] = { ...g, teacher_approved: true };
      }
      return { ...s, ai_grades: nextGrades };
    };
    setSubmissions(prev => prev.map(updateSub));
    setSelectedSubmission(prev => (prev ? updateSub(prev) : null));
  };

  const toggleGradeApproval = (submissionId: string, questionId: string, approved: boolean) => {
    const updateSub = (s: SubmissionWithAIGrades): SubmissionWithAIGrades => {
      if (s.submission_id !== submissionId || !s.ai_grades) return s;
      const grade = s.ai_grades[questionId];
      if (!grade) return s;
      return {
        ...s,
        ai_grades: {
          ...s.ai_grades,
          [questionId]: { ...grade, teacher_approved: approved }
        }
      };
    };
    setSubmissions(prev => prev.map(updateSub));
    setSelectedSubmission(prev => (prev ? updateSub(prev) : null));
  };

  const updateTeacherGrade = (
    submissionId: string,
    questionId: string,
    field: 'teacher_score' | 'teacher_feedback' | 'teacher_corrected_answer',
    value: number | string
  ) => {
    const updateSub = (s: SubmissionWithAIGrades): SubmissionWithAIGrades => {
      if (s.submission_id !== submissionId || !s.ai_grades) return s;
      const grade = s.ai_grades[questionId];
      if (!grade) return s;
      return {
        ...s,
        ai_grades: {
          ...s.ai_grades,
          [questionId]: { ...grade, [field]: value, teacher_approved: true }
        }
      };
    };
    setSubmissions(prev => prev.map(updateSub));
    setSelectedSubmission(prev => (prev ? updateSub(prev) : null));
  };

  const groupSimilarMistakes = () => {
    const groups: Record<string, string[]> = {};
    
    submissions.forEach(sub => {
      sub.answers.forEach(answer => {
        if (answer.student_response && !answer.student_response.toLowerCase().includes((answer.correct_answer || '').toLowerCase())) {
          // Simple grouping by question and similar response pattern
          const key = `${answer.question_id}:${answer.student_response.substring(0, 50)}`;
          if (!groups[key]) groups[key] = [];
          groups[key].push(`${sub.anonymous_student_ref} (Q${sub.answers.indexOf(answer) + 1})`);
        }
      });
    });
    
    setGroupedMistakes(groups);
    showInfo(t('teacher_dashboard.mistake_groups_found', { count: String(Object.keys(groups).length) }));
  };

  const handleViewSubmission = (submission: SubmissionWithAIGrades) => {
    setSelectedSubmission(submission);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setSelectedSubmission(null);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '300px' }}>
        <div style={{ fontSize: '1.2rem', color: 'var(--text-muted)' }}>{t('common.loading')}</div>
      </div>
    );
  }

  return (
    <div style={{ overflowX: 'hidden' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-color)', marginBottom: '0.25rem', overflowWrap: 'break-word' }}>
            {t('teacher_dashboard.ai_grading_title')}
          </h1>
          <p style={{ color: 'var(--text-muted)' }}>{t('teacher_dashboard.ai_grading_subtitle')}</p>
        </div>
        <button
          onClick={groupSimilarMistakes}
          style={{ padding: '0.625rem 1.25rem', backgroundColor: '#8b5cf6', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500, whiteSpace: 'normal', overflowWrap: 'break-word', maxWidth: '100%' }}
        >
          🔍 {t('teacher_dashboard.group_mistakes')}
        </button>
        <button
          onClick={handleOpenTestModuleModal}
          style={{ padding: '0.625rem 1.25rem', backgroundColor: '#10b981', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500, whiteSpace: 'normal', overflowWrap: 'break-word', maxWidth: '100%' }}
        >
          🧪 {t('teacher_dashboard.test_module')}
        </button>
      </div>

      {/* Embedded ChatGPT Teacher Assistant */}
      <ChatGptPanel
        compact
        quickActionLabel="Insert Anonymized Submissions"
        onBuildQuickPrompt={() =>
          `Please review and suggest grades/feedback for these anonymized student submissions:\n${JSON.stringify(
            submissions.map((s) => ({
              anonymous_student_ref: s.anonymous_student_ref,
              answers: s.answers,
            })),
            null,
            2,
          )}`
        }
      />

      {/* Digital Hand Raise Live Monitor (with sound chime & toast notifications) */}
      {examId && <TeacherHandRaiseMonitor examId={examId} />}

      {/* {t('teacher_dashboard.real_time_monitoring')} Panel */}
      <div style={{ marginBottom: '1.5rem', padding: '1rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: 'var(--text-color)' }}>
            📡 {t('teacher_dashboard.real_time_monitoring')}
          </h3>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {t('teacher_dashboard.auto_refresh')}
          </span>
        </div>
        
        {heartbeatError && (
          <div style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: '#fef2f2', border: '1px solid #fecaca', borderRadius: 'var(--radius-md)', color: '#dc2626' }}>
            ⚠️ {t('teacher_dashboard.heartbeat_error', { error: heartbeatError })}
          </div>
        )}
        
        {heartbeats.length === 0 && !heartbeatError && !heartbeatLoading ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
            {t('teacher_dashboard.no_students')}
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_student')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_status')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_progress')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_time_remaining')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_violations')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_score')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_actions')}</th>
                </tr>
              </thead>
              <tbody>
                {heartbeats.map(hb => (
                  <tr key={hb.student_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '0.75rem', fontWeight: 500, color: 'var(--text-color)' }}>
                      {hb.student_name}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      {hb.is_complete ? (
                        <span style={{ display: 'inline-block', padding: '0.25rem 0.5rem', borderRadius: '9999px', fontSize: '0.7rem', fontWeight: 600, backgroundColor: '#10b98120', color: '#10b981' }}>
                          ✓ Completed
                        </span>
                      ) : hb.started_at ? (
                        <span style={{ display: 'inline-block', padding: '0.25rem 0.5rem', borderRadius: '9999px', fontSize: '0.7rem', fontWeight: 600, backgroundColor: '#3b82f620', color: '#3b82f6' }}>
                          🟢 In Progress
                        </span>
                      ) : (
                        <span style={{ display: 'inline-block', padding: '0.25rem 0.5rem', borderRadius: '9999px', fontSize: '0.7rem', fontWeight: 600, backgroundColor: '#f59e0b20', color: '#f59e0b' }}>
                          ⏳ Not Started
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-muted)' }}>
                      {hb.completed_at ? '100%' : '—'}
                    </td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                      {hb.started_at && !hb.completed_at ? 'In progress' : hb.completed_at ? 'Finished' : '—'}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      <span style={{ 
                        display: 'inline-block', 
                        padding: '0.25rem 0.5rem', 
                        borderRadius: '9999px', 
                        fontSize: '0.7rem', 
                        fontWeight: 600,
                        backgroundColor: '#ef444420',
                        color: '#ef4444'
                      }}>
                        0
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem', fontWeight: 500, color: 'var(--text-color)' }}>
                      {hb.score !== null ? `${hb.score}%` : '—'}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                      <button
                        onClick={() => handleQuickResetStudent(hb.student_id, hb.student_name)}
                        style={{
                          padding: '0.35rem 0.65rem',
                          backgroundColor: '#10b98115',
                          color: '#10b981',
                          border: '1px solid #10b98140',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                        }}
                        title="Reset student password"
                      >
                        ⚡ Reset Password
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Archive Management Panel */}
      <div style={{ marginBottom: '1.5rem', padding: '1rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: 'var(--text-color)' }}>
            📦 {t('teacher_dashboard.archive_title')}
          </h3>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <select
              value={archiveYearFilter}
              onChange={e => { setArchiveYearFilter(e.target.value === 'all' ? 'all' : parseInt(e.target.value)); fetchArchives(); }}
              style={{ padding: '0.375rem 0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.85rem' }}
            >
              <option value="all">{t('teacher_dashboard.filter_all_years')}</option>
              {Array.from({length: 10}, (_, i) => new Date().getFullYear() - i).map(y => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <select
              value={archiveMonthFilter}
              onChange={e => { setArchiveMonthFilter(e.target.value === 'all' ? 'all' : parseInt(e.target.value)); fetchArchives(); }}
              style={{ padding: '0.375rem 0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.85rem' }}
            >
              <option value="all">{t('teacher_dashboard.filter_all_months')}</option>
              {Array.from({length: 12}, (_, i) => i + 1).map(m => (
                <option key={m} value={m}>{m.toString().padStart(2, '0')}</option>
              ))}
            </select>
            <select
              value={archiveStatusFilter}
              onChange={e => { setArchiveStatusFilter(e.target.value as any); fetchArchives(); }}
              style={{ padding: '0.375rem 0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.85rem' }}
            >
              <option value="all">{t('teacher_dashboard.filter_all_statuses')}</option>
              <option value="active">{t('common.34')}</option>
              <option value="archived">{t('common.39')}</option>
              <option value="deleted">{t('teacher_dashboard.filter_deleted')}</option>
            </select>
          </div>
        </div>

        {archiveStats && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
            {[
              { label: t('teacher_dashboard.stat_total_archives'), value: archiveStats.total_archives, color: '#8b5cf6', icon: '📦' },
              { label: t('teacher_dashboard.stat_total_size'), value: `${archiveStats.total_size_mb} MB`, color: '#3b82f6', icon: '💾' },
              { label: t('teacher_dashboard.stat_space_saved'), value: `${archiveStats.compression_savings_mb} MB`, color: '#10b981', icon: '✨' },
            ].map((stat, i) => (
              <div key={i} style={{ padding: '0.75rem', backgroundColor: 'var(--bg-color)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: stat.color }}>{stat.value}</div>
                <div style={{ color: 'var(--text-muted)', marginTop: '0.25rem', fontSize: '0.75rem' }}>{stat.icon} {stat.label}</div>
              </div>
            ))}
          </div>
        )}

        {archiveLoading ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>{t('common.14')}</div>
        ) : archives.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
            {t('teacher_dashboard.no_archives')}
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_submission_id')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_student')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_year_month')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_orig_size')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_compressed')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_ratio')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_status')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('common.39')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_actions')}</th>
                </tr>
              </thead>
              <tbody>
                {archives.map(archive => (
                  <tr key={archive.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--text-color)' }}>
                      {archive.submission_id.slice(0, 12)}...
                    </td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-muted)' }}>{archive.student_id.slice(0, 8)}...</td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-muted)' }}>{archive.archive_year}/{archive.archive_month.toString().padStart(2, '0')}</td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>{(archive.original_size / 1024).toFixed(1)} KB</td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>{(archive.compressed_size / 1024).toFixed(1)} KB</td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>{archive.compression_ratio.toFixed(1)}x</td>
                    <td style={{ padding: '0.75rem' }}>
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: '9999px',
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        backgroundColor: 
                          archive.status === 'active' ? '#10b98120' :
                          archive.status === 'archived' ? '#8b5cf620' : '#ef444420',
                        color: 
                          archive.status === 'active' ? '#10b981' :
                          archive.status === 'archived' ? '#8b5cf6' : '#ef4444',
                      }}>
                        {archive.status}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      {archive.archived_at ? new Date(archive.archived_at).toLocaleDateString() : '—'}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: '0.375rem', justifyContent: 'flex-end' }}>
                        <button
                          onClick={() => handleViewArchive(archive)}
                          style={{ padding: '0.375rem 0.75rem', backgroundColor: 'var(--secondary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontSize: '0.8rem' }}
                        >
                          {t('teacher_dashboard.btn_details')}
                        </button>
                        <button
                          onClick={() => handleDownloadArchive(archive.id)}
                          style={{ padding: '0.375rem 0.75rem', backgroundColor: '#3b82f6', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontSize: '0.8rem' }}
                        >
                          {t('teacher_dashboard.btn_download')}
                        </button>
                        {archive.status === 'archived' && (
                          <button
                            onClick={() => handleRestoreArchive(archive.id)}
                            style={{ padding: '0.375rem 0.75rem', backgroundColor: '#10b981', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontSize: '0.8rem' }}
                          >
                            {t('teacher_dashboard.btn_restore')}
                          </button>
                        )}
                        {archive.status === 'active' && (
                          <button
                            onClick={() => handleDeleteArchive(archive.id)}
                            style={{ padding: '0.375rem 0.75rem', backgroundColor: '#ef4444', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontSize: '0.8rem' }}
                          >
                            {t('teacher_dashboard.btn_archive')}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Archive Details Modal */}
        {showArchiveModal && selectedArchive && (
          <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1rem' }}>
            <div style={{ backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', maxWidth: '500px', width: '100%', padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ margin: 0, color: 'var(--text-color)' }}>{t('teacher_dashboard.archive_details')}</h3>
                <button onClick={() => setShowArchiveModal(false)} style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text-muted)' }}>×</button>
              </div>
              <p style={{ margin: '0.5rem 0', color: 'var(--text-color)' }}><strong>{t('teacher_dashboard.lbl_submission')}:</strong> {selectedArchive.submission_id}</p>
              <p style={{ margin: '0.5rem 0', color: 'var(--text-color)' }}><strong>{t('teacher_dashboard.lbl_compression')}:</strong> {selectedArchive.compression_algorithm} ({selectedArchive.compression_ratio.toFixed(1)}x ratio)</p>
              <p style={{ margin: '0.5rem 0', color: 'var(--text-color)' }}><strong>{t('teacher_dashboard.lbl_path')}:</strong> <code>{selectedArchive.archive_path}</code></p>
              <div style={{ textAlign: 'right', marginTop: '1rem' }}>
                <button onClick={() => setShowArchiveModal(false)} style={{ padding: '0.5rem 1rem', borderRadius: 'var(--radius-md)', border: 'none', backgroundColor: 'var(--primary-color)', color: '#fff', cursor: 'pointer' }}>{t('common.6')}</button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Package Manager */}
      <PackageManager 
        examId={examId} 
        onPackageImported={() => {
          showSuccess('Package imported! New exam created.');
          // Could navigate to new exam or refresh
        }}
      />

      {/* Mistake Groups Panel */}
      {Object.keys(groupedMistakes).length > 0 && (
        <div style={{ marginBottom: '1.5rem', padding: '1rem', backgroundColor: '#fef3c7', border: '1px solid #fcd34d', borderRadius: 'var(--radius-md)' }}>
          <h4 style={{ margin: '0 0 0.5rem', color: '#92400e' }}>Similar Mistake Groups</h4>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {Object.entries(groupedMistakes).map(([key, students]) => (
              <span key={key} style={{ padding: '0.25rem 0.75rem', backgroundColor: '#fff', borderRadius: '9999px', fontSize: '0.8rem', border: '1px solid #fcd34d' }}>
                {key}: {students.join(', ')}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Submissions List / Class Test Archive Browser */}
      <div style={{ backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', overflow: 'hidden', marginBottom: '1.5rem' }}>
        {/* Archive Browser Action Header */}
        <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-color)' }}>
              📑 {t('teacher_dashboard.archived_submissions')}
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              ({submissions.length} total)
            </span>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            {/* Filter Buttons */}
            <div style={{ display: 'flex', borderRadius: 'var(--radius-md)', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
              {(['all', 'ungraded', 'pending_approval', 'graded'] as const).map(f => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setStatusFilter(f)}
                  style={{
                    padding: '0.35rem 0.75rem',
                    fontSize: '0.75rem',
                    border: 'none',
                    backgroundColor: statusFilter === f ? 'var(--primary-color)' : 'var(--bg-color)',
                    color: statusFilter === f ? '#fff' : 'var(--text-muted)',
                    cursor: 'pointer',
                    fontWeight: statusFilter === f ? 600 : 400,
                  }}
                >
                  {f === 'all' ? t('teacher_dashboard.filter_all_statuses') :
                   f === 'ungraded' ? t('teacher_dashboard.status_ungraded') :
                   f === 'pending_approval' ? t('teacher_dashboard.status_pending_approval') :
                   t('teacher_dashboard.status_graded')}
                </button>
              ))}
            </div>

            {/* Batch AI Correction */}
            {selectedSubmissions.length > 0 && (
              <>
                <button
                  type="button"
                  onClick={handleAIGradeSelected}
                  disabled={generatingGrades === 'batch'}
                  style={{
                    padding: '0.4rem 0.85rem',
                    backgroundColor: 'var(--primary-color)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    cursor: generatingGrades === 'batch' ? 'not-allowed' : 'pointer',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                  }}
                >
                  🤖 {t('teacher_dashboard.btn_ai_correct_selected')} ({selectedSubmissions.length})
                </button>
                <button
                  type="button"
                  onClick={handleApproveSelected}
                  style={{
                    padding: '0.4rem 0.85rem',
                    backgroundColor: '#10b981',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                  }}
                >
                  ✓ {t('teacher_dashboard.btn_approve_selected')} ({selectedSubmissions.length})
                </button>
              </>
            )}

            {/* Upload Test Paper */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleUploadOfflineTest}
              style={{ display: 'none' }}
              accept=".json,.txt,.pdf,.zip"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              style={{
                padding: '0.4rem 0.85rem',
                backgroundColor: 'var(--secondary-color)',
                color: '#fff',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
              }}
            >
              <Upload size={14} />
              {t('teacher_dashboard.upload_offline_test')}
            </button>
          </div>
        </div>

        {/* Submissions Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)' }}>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', width: '40px' }}>
                  <input
                    type="checkbox"
                    checked={submissions.length > 0 && selectedSubmissions.length === submissions.length}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedSubmissions(submissions.map(s => s.submission_id));
                      } else {
                        setSelectedSubmissions([]);
                      }
                    }}
                    style={{ cursor: 'pointer' }}
                  />
                </th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_student')}</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_questions')}</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_score')}</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_status')}</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t('teacher_dashboard.col_actions')}</th>
              </tr>
            </thead>
            <tbody>
              {submissions.filter(s => statusFilter === 'all' || s.status === statusFilter).length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    {t('teacher_dashboard.no_submissions')}
                  </td>
                </tr>
              ) : (
                submissions
                  .filter(s => statusFilter === 'all' || s.status === statusFilter)
                  .map(submission => {
                    const isSelected = selectedSubmissions.includes(submission.submission_id);
                    const subStatus = submission.status || (submission.score !== null ? 'graded' : (submission.ai_grades && Object.keys(submission.ai_grades).length > 0 ? 'pending_approval' : 'ungraded'));
                    
                    return (
                      <tr
                        key={submission.submission_id}
                        style={{
                          borderBottom: '1px solid var(--border-color)',
                          backgroundColor: isSelected ? 'var(--primary-color)10' : undefined,
                        }}
                      >
                        <td style={{ padding: '0.75rem 1rem' }}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedSubmissions(prev => [...prev, submission.submission_id]);
                              } else {
                                setSelectedSubmissions(prev => prev.filter(id => id !== submission.submission_id));
                              }
                            }}
                            style={{ cursor: 'pointer' }}
                          />
                        </td>
                        <td style={{ padding: '0.75rem 1rem' }}>
                          <div style={{ fontWeight: 600, color: 'var(--text-color)' }}>
                            {submission.student_name || submission.anonymous_student_ref}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            {submission.anonymous_student_ref} {submission.exam_title ? `• ${submission.exam_title}` : ''}
                          </div>
                        </td>
                        <td style={{ padding: '0.75rem 1rem', color: 'var(--text-muted)' }}>
                          {submission.answers.length} {t('teacher_dashboard.col_questions')}
                        </td>
                        <td style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--text-color)' }}>
                          {submission.score !== null ? `${submission.score} pts` : '—'}
                          {submission.total_possible ? ` / ${submission.total_possible} pts` : ''}
                        </td>
                        <td style={{ padding: '0.75rem 1rem' }}>
                          {subStatus === 'graded' ? (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', padding: '0.25rem 0.65rem', borderRadius: '9999px', fontSize: '0.7rem', fontWeight: 600, backgroundColor: '#10b98120', color: '#10b981' }}>
                              ✓ {t('teacher_dashboard.status_graded')}
                            </span>
                          ) : subStatus === 'pending_approval' ? (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', padding: '0.25rem 0.65rem', borderRadius: '9999px', fontSize: '0.7rem', fontWeight: 600, backgroundColor: '#f59e0b20', color: '#d97706' }}>
                              ⚡ {t('teacher_dashboard.status_pending_approval')}
                            </span>
                          ) : (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', padding: '0.25rem 0.65rem', borderRadius: '9999px', fontSize: '0.7rem', fontWeight: 600, backgroundColor: '#6b728020', color: '#6b7280' }}>
                              ⏳ {t('teacher_dashboard.status_ungraded')}
                            </span>
                          )}
                        </td>
                        <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                          <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                            {subStatus === 'ungraded' && (
                              <>
                                <button
                                  type="button"
                                  onClick={() => generateAIGrades(submission)}
                                  disabled={generatingGrades === submission.submission_id}
                                  style={{
                                    padding: '0.35rem 0.75rem',
                                    backgroundColor: 'var(--primary-color)',
                                    color: '#fff',
                                    border: 'none',
                                    borderRadius: 'var(--radius-md)',
                                    cursor: generatingGrades === submission.submission_id ? 'not-allowed' : 'pointer',
                                    fontWeight: 500,
                                    fontSize: '0.8rem',
                                  }}
                                >
                                  {generatingGrades === submission.submission_id ? t('teacher_dashboard.generating') : '🤖 AI Correct'}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleViewSubmission(submission)}
                                  style={{
                                    padding: '0.35rem 0.75rem',
                                    backgroundColor: '#3b82f6',
                                    color: '#fff',
                                    border: 'none',
                                    borderRadius: 'var(--radius-md)',
                                    cursor: 'pointer',
                                    fontWeight: 500,
                                    fontSize: '0.8rem',
                                  }}
                                >
                                  ✏️ Manual Grade
                                </button>
                              </>
                            )}

                            {subStatus === 'pending_approval' && (
                              <>
                                <button
                                  type="button"
                                  onClick={() => handleViewSubmission(submission)}
                                  style={{
                                    padding: '0.35rem 0.75rem',
                                    backgroundColor: '#3b82f6',
                                    color: '#fff',
                                    border: 'none',
                                    borderRadius: 'var(--radius-md)',
                                    cursor: 'pointer',
                                    fontWeight: 600,
                                    fontSize: '0.8rem',
                                  }}
                                >
                                  ✏️ Review &amp; Correct
                                </button>
                                <button
                                  type="button"
                                  onClick={() => applyAIGrades(submission, true)}
                                  style={{
                                    padding: '0.35rem 0.75rem',
                                    backgroundColor: '#10b981',
                                    color: '#fff',
                                    border: 'none',
                                    borderRadius: 'var(--radius-md)',
                                    cursor: 'pointer',
                                    fontWeight: 600,
                                    fontSize: '0.8rem',
                                  }}
                                >
                                  ✓ Approve &amp; Seal
                                </button>
                              </>
                            )}

                            {subStatus === 'graded' && (
                              <>
                                <button
                                  type="button"
                                  onClick={() => handleViewSubmission(submission)}
                                  style={{
                                    padding: '0.35rem 0.75rem',
                                    backgroundColor: 'var(--secondary-color)',
                                    color: '#fff',
                                    border: 'none',
                                    borderRadius: 'var(--radius-md)',
                                    cursor: 'pointer',
                                    fontWeight: 500,
                                    fontSize: '0.8rem',
                                  }}
                                >
                                  👁️ View
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleReopenSubmission(submission.submission_id)}
                                  style={{
                                    padding: '0.35rem 0.75rem',
                                    backgroundColor: '#f59e0b',
                                    color: '#fff',
                                    border: 'none',
                                    borderRadius: 'var(--radius-md)',
                                    cursor: 'pointer',
                                    fontWeight: 500,
                                    fontSize: '0.8rem',
                                  }}
                                  title="Reopen test to edit and re-correct"
                                >
                                  🔄 Re-correct
                                </button>
                                {submission.archive_id && (
                                  <button
                                    type="button"
                                    onClick={() => handleDownloadArchive(submission.archive_id!)}
                                    style={{
                                      padding: '0.35rem 0.75rem',
                                      backgroundColor: '#6366f1',
                                      color: '#fff',
                                      border: 'none',
                                      borderRadius: 'var(--radius-md)',
                                      cursor: 'pointer',
                                      fontWeight: 500,
                                      fontSize: '0.8rem',
                                    }}
                                    title="Download sealed .zst.enc archive"
                                  >
                                    📦 Download
                                  </button>
                                )}
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
              )}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Comfy Teacher Review & Correction Modal */}
      {showModal && selectedSubmission && (
        <TeacherCorrectionModal
          submission={selectedSubmission}
          reviewingQuestionId={reviewingQuestionId}
          setReviewingQuestionId={setReviewingQuestionId}
          onClose={handleCloseModal}
          onUpdateGrade={updateTeacherGrade}
          onToggleApproval={toggleGradeApproval}
          onApproveAllQuestions={approveAllQuestions}
          onSaveGrades={applyAIGrades}
        />
      )}

      {/* Test Module Preview Modal */}
      {showTestModuleModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1rem' }}>
          <div style={{ backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', maxWidth: '500px', width: '100%', maxHeight: '90vh', overflow: 'auto' }}>
            <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ margin: 0, fontSize: '1.25rem' }}>{t('teacher_dashboard.test_module_title')}</h2>
              <button onClick={handleCloseTestModuleModal} style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: 'var(--text-muted)' }}>×</button>
            </div>
            <div style={{ padding: '1.5rem' }}>
              <p style={{ margin: '0 0 1rem', color: 'var(--text-muted)' }}>{t('teacher_dashboard.test_module_description')}</p>
              
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.85rem' }}>{t('teacher_dashboard.test_count_label')}</label>
                <input
                  type="number"
                  min="1"
                  max="25"
                  value={testModuleCount}
                  onChange={e => setTestModuleCount(Math.min(25, Math.max(1, parseInt(e.target.value) || 1)))}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.85rem' }}
                />
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>{t('teacher_dashboard.test_count_hint')}</p>
              </div>
              
              <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                <button onClick={handleCloseTestModuleModal} style={{ padding: '0.625rem 1.25rem', backgroundColor: 'var(--secondary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500 }}>
                  {t('common.2')}
                </button>
                <button 
                  onClick={handleOpenTestModules}
                  disabled={testModuleLoading}
                  style={{ padding: '0.625rem 1.25rem', backgroundColor: '#10b981', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: testModuleLoading ? 'not-allowed' : 'pointer', fontWeight: 500 }}
                >
                  {testModuleLoading ? t('teacher_dashboard.opening_tests') : t('teacher_dashboard.open_tests')}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
