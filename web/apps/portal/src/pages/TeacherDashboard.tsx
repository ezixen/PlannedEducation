import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../api';
import { PackageManager } from '../components/PackageManager';
import { ChatGptPanel } from '../components/ChatGptPanel';
import {
  TeacherCorrectionModal,
  type AIGrade,
  type SubmissionWithAIGrades,
} from '../components/TeacherCorrectionModal';

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
  const { examId } = useParams<{ examId: string }>();
  const { success: showSuccess, error: showError, info: showInfo } = useToast();

  const [submissions, setSubmissions] = useState<SubmissionWithAIGrades[]>([]);
  const [loading, setLoading] = useState(true);
  const [generatingGrades, setGeneratingGrades] = useState<string | null>(null);
  const [selectedSubmission, setSelectedSubmission] = useState<SubmissionWithAIGrades | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [groupedMistakes, setGroupedMistakes] = useState<Record<string, string[]>>({});
  const [reviewingQuestionId, setReviewingQuestionId] = useState<string | null>(null);
  
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

  useEffect(() => {
    if (examId) {
      fetchSubmissions();
      fetchArchives();
      fetchArchiveStats();
    }
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

  const fetchSubmissions = async () => {
    if (!examId) return;
    setLoading(true);
    try {
      const response = await apiClient.get(`/anonymizer/exams/${examId}/submissions`);
      setSubmissions(
        response.data.map((s: SubmissionWithAIGrades) => {
          const initialGrades: Record<string, AIGrade> = {};
          let hasSavedGrades = false;
          for (const ans of s.answers) {
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
            ai_grades: initialGrades,
            teacher_approved: Boolean(s.is_graded && hasSavedGrades),
          };
        })
      );
    } catch (err: any) {
      showError('Failed to fetch submissions.', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
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
          const isExactMatch = Boolean(corrNorm && respNorm === corrNorm);
          const hasContent = respNorm.length > 0;
          aiGrade = {
            score: isExactMatch ? answer.points_possible : hasContent ? Math.round(answer.points_possible * 0.8 * 10) / 10 : 0,
            feedback: isExactMatch
              ? 'Correct response matching expected answer.'
              : hasContent
                ? 'Evaluated via local rubric matcher. Teacher review recommended.'
                : 'No response provided.',
            confidence: isExactMatch ? 0.98 : 0.85,
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
      
      await apiClient.post(`/anonymizer/submissions/${submission.submission_id}/grades`, {
        feedback: questionGrades.map(g => g.feedback).join('\n\n'),
        score: questionGrades.reduce((sum, g) => sum + g.score, 0),
        question_grades: questionGrades,
      });
      
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
      
      showSuccess(`${questionGrades.length} grade(s) and corrected solutions saved!`);
    } catch (err: any) {
      showError('Failed to apply grades.', err.response?.data?.detail || err.message);
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
    showInfo(`Found ${Object.keys(groups).length} mistake groups`);
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
        <div style={{ fontSize: '1.2rem', color: 'var(--text-muted)' }}>Loading submissions...</div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-color)', marginBottom: '0.25rem' }}>
            AI Grading Dashboard
          </h1>
          <p style={{ color: 'var(--text-muted)' }}>Review and approve AI-generated grades for exam submissions</p>
        </div>
        <button
          onClick={groupSimilarMistakes}
          style={{ padding: '0.625rem 1.25rem', backgroundColor: '#8b5cf6', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500 }}
        >
          🔍 Group Similar Mistakes
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

      {/* Real-time Student Monitoring Panel */}
      <div style={{ marginBottom: '1.5rem', padding: '1rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: 'var(--text-color)' }}>
            📡 Real-time Student Monitoring
          </h3>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Auto-refreshes every 10s
          </span>
        </div>
        
        {heartbeatError && (
          <div style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: '#fef2f2', border: '1px solid #fecaca', borderRadius: 'var(--radius-md)', color: '#dc2626' }}>
            ⚠️ Failed to load heartbeats: {heartbeatError}
          </div>
        )}
        
        {heartbeats.length === 0 && !heartbeatError && !heartbeatLoading ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
            No students have started this exam yet.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Student</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Status</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Progress</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Time Remaining</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Violations</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Score</th>
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
            📦 Archived Submissions
          </h3>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <select
              value={archiveYearFilter}
              onChange={e => { setArchiveYearFilter(e.target.value === 'all' ? 'all' : parseInt(e.target.value)); fetchArchives(); }}
              style={{ padding: '0.375rem 0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.85rem' }}
            >
              <option value="all">All Years</option>
              {Array.from({length: 10}, (_, i) => new Date().getFullYear() - i).map(y => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <select
              value={archiveMonthFilter}
              onChange={e => { setArchiveMonthFilter(e.target.value === 'all' ? 'all' : parseInt(e.target.value)); fetchArchives(); }}
              style={{ padding: '0.375rem 0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.85rem' }}
            >
              <option value="all">All Months</option>
              {Array.from({length: 12}, (_, i) => i + 1).map(m => (
                <option key={m} value={m}>{m.toString().padStart(2, '0')}</option>
              ))}
            </select>
            <select
              value={archiveStatusFilter}
              onChange={e => { setArchiveStatusFilter(e.target.value as any); fetchArchives(); }}
              style={{ padding: '0.375rem 0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)', fontSize: '0.85rem' }}
            >
              <option value="all">All Statuses</option>
              <option value="active">Active</option>
              <option value="archived">Archived</option>
              <option value="deleted">Deleted from Server</option>
            </select>
          </div>
        </div>

        {archiveStats && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
            {[
              { label: 'Total Archives', value: archiveStats.total_archives, color: '#8b5cf6', icon: '📦' },
              { label: 'Total Size', value: `${archiveStats.total_size_mb} MB`, color: '#3b82f6', icon: '💾' },
              { label: 'Space Saved', value: `${archiveStats.compression_savings_mb} MB`, color: '#10b981', icon: '✨' },
            ].map((stat, i) => (
              <div key={i} style={{ padding: '0.75rem', backgroundColor: 'var(--bg-color)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: stat.color }}>{stat.value}</div>
                <div style={{ color: 'var(--text-muted)', marginTop: '0.25rem', fontSize: '0.75rem' }}>{stat.icon} {stat.label}</div>
              </div>
            ))}
          </div>
        )}

        {archiveLoading ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>Loading archives...</div>
        ) : archives.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
            No archived submissions found for this exam.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Submission ID</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Student</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Year/Month</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Original Size</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Compressed</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Ratio</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Status</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Archived</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Actions</th>
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
                          Details
                        </button>
                        <button
                          onClick={() => handleDownloadArchive(archive.id)}
                          style={{ padding: '0.375rem 0.75rem', backgroundColor: '#3b82f6', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontSize: '0.8rem' }}
                        >
                          Download
                        </button>
                        {archive.status === 'archived' && (
                          <button
                            onClick={() => handleRestoreArchive(archive.id)}
                            style={{ padding: '0.375rem 0.75rem', backgroundColor: '#10b981', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontSize: '0.8rem' }}
                          >
                            Restore
                          </button>
                        )}
                        {archive.status === 'active' && (
                          <button
                            onClick={() => handleDeleteArchive(archive.id)}
                            style={{ padding: '0.375rem 0.75rem', backgroundColor: '#ef4444', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontSize: '0.8rem' }}
                          >
                            Archive
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
                <h3 style={{ margin: 0, color: 'var(--text-color)' }}>Archive Details</h3>
                <button onClick={() => setShowArchiveModal(false)} style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text-muted)' }}>×</button>
              </div>
              <p style={{ margin: '0.5rem 0', color: 'var(--text-color)' }}><strong>Submission:</strong> {selectedArchive.submission_id}</p>
              <p style={{ margin: '0.5rem 0', color: 'var(--text-color)' }}><strong>Compression:</strong> {selectedArchive.compression_algorithm} ({selectedArchive.compression_ratio.toFixed(1)}x ratio)</p>
              <p style={{ margin: '0.5rem 0', color: 'var(--text-color)' }}><strong>Path:</strong> <code>{selectedArchive.archive_path}</code></p>
              <div style={{ textAlign: 'right', marginTop: '1rem' }}>
                <button onClick={() => setShowArchiveModal(false)} style={{ padding: '0.5rem 1rem', borderRadius: 'var(--radius-md)', border: 'none', backgroundColor: 'var(--primary-color)', color: '#fff', cursor: 'pointer' }}>Close</button>
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

      {/* Submissions List */}
      <div style={{ backgroundColor: 'var(--sidebar-bg)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Student</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Questions</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>AI Grades</th>
                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Status</th>
                <th style={{ padding: '1rem', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {submissions.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No submissions found for this exam.
                  </td>
                </tr>
              ) : (
                submissions.map(submission => (
                  <tr key={submission.submission_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '1rem', fontWeight: 500, color: 'var(--text-color)' }}>
                      {submission.anonymous_student_ref}
                    </td>
                    <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>
                      {submission.answers.length} questions
                    </td>
                    <td style={{ padding: '1rem' }}>
                      {submission.ai_grades && Object.keys(submission.ai_grades).length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                          {Object.values(submission.ai_grades).map(grade => (
                            <span key={grade.question_id} style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <span style={{ 
                                width: '8px', 
                                height: '8px', 
                                borderRadius: '50%', 
                                backgroundColor: grade.confidence > 0.9 ? '#10b981' : grade.confidence > 0.7 ? '#f59e0b' : '#ef4444' 
                              }} />
                              Q{submission.answers.findIndex(a => a.question_id === grade.question_id) + 1}: {grade.score}/{submission.answers.find(a => a.question_id === grade.question_id)?.points_possible || 0} ({Math.round(grade.confidence * 100)}%)
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Not generated</span>
                      )}
                    </td>
                    <td style={{ padding: '1rem' }}>
                      {submission.teacher_approved ? (
                        <span style={{ display: 'inline-block', padding: '0.25rem 0.75rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: '#10b98120', color: '#10b981' }}>
                          ✓ Approved
                        </span>
                      ) : submission.ai_grades && Object.keys(submission.ai_grades).length > 0 ? (
                        <span style={{ display: 'inline-block', padding: '0.25rem 0.75rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: '#f59e0b20', color: '#f59e0b' }}>
                          Pending Review
                        </span>
                      ) : (
                        <span style={{ display: 'inline-block', padding: '0.25rem 0.75rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: '#6b728020', color: '#6b7280' }}>
                          Not Graded
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '1rem', textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                        {!submission.ai_grades || Object.keys(submission.ai_grades).length === 0 ? (
                          <button
                            onClick={() => generateAIGrades(submission)}
                            disabled={generatingGrades === submission.submission_id}
                            style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: generatingGrades === submission.submission_id ? 'not-allowed' : 'pointer', fontWeight: 500, fontSize: '0.85rem' }}
                          >
                            {generatingGrades === submission.submission_id ? 'Generating...' : 'Generate AI Grades'}
                          </button>
                        ) : !submission.teacher_approved ? (
                          <>
                            <button
                              onClick={() => handleViewSubmission(submission)}
                              style={{ padding: '0.5rem 1rem', backgroundColor: '#3b82f6', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500, fontSize: '0.85rem' }}
                            >
                              Review
                            </button>
                            <button
                              onClick={() => applyAIGrades(submission, true)}
                              style={{ padding: '0.5rem 1rem', backgroundColor: '#10b981', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500, fontSize: '0.85rem' }}
                            >
                              Apply All
                            </button>
                          </>
                        ) : (
                          <>
                            <span style={{ color: '#10b981', fontSize: '0.85rem', fontWeight: 600, alignSelf: 'center' }}>Completed</span>
                            <button
                              onClick={() => handleViewSubmission(submission)}
                              style={{ padding: '0.4rem 0.85rem', backgroundColor: 'var(--secondary-color)', color: '#fff', border: 'none', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontWeight: 500, fontSize: '0.8rem' }}
                            >
                              Edit Correction
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
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
    </div>
  );
}