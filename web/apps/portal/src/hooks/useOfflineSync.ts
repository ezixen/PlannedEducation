import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../api';
import {
  getExamProgress,
  saveExamProgress,
  deleteExamProgress,
  queueExamSubmission,
  queueProgressSync,
  processSyncQueue,
  getOfflineStorageStats,
  isOnline,
  setupOnlineListener,
} from '../services/offlineSync';
import type { ExamProgress } from '../services/offlineSync';

export function useOfflineSync(examId?: string) {
  const { user } = useAuth();
  const { info: showInfo, success: showSuccess, error: showError } = useToast();
  
  const [online, setOnline] = useState(navigator.onLine);
  const [syncing, setSyncing] = useState(false);
  const [stats, setStats] = useState({
    progressCount: 0,
    pendingSubmissions: 0,
    cachedExams: 0,
    syncQueueSize: 0,
  });
  const [progress, setProgress] = useState<ExamProgress | null>(null);
  const wasOnline = useRef(navigator.onLine);

  const loadProgress = useCallback(async () => {
    if (!examId || !user) return;
    const p = await getExamProgress(examId, user.id);
    setProgress(p || null);
  }, [examId, user]);

  // Refresh storage stats
  const refreshStats = useCallback(async () => {
    const s = await getOfflineStorageStats();
    setStats(s);
  }, []);

  // Load progress for current exam
  useEffect(() => {
    void loadProgress();
  }, [loadProgress]);

  // Save answer to offline storage
  const saveAnswer = useCallback(async (questionId: string, response: string) => {
    if (!examId || !user) return;
    
    const current = progress || {
      id: `${examId}-${user.id}`,
      examId,
      studentId: user.id,
      answers: {},
      currentQuestionIndex: 0,
      timeRemaining: 0,
      lastUpdated: Date.now(),
      isComplete: false,
    };
    
    const nextProgress = {
      ...current,
      answers: { ...current.answers, [questionId]: response },
      lastUpdated: Date.now(),
    };
    await saveExamProgress(nextProgress);
    setProgress(nextProgress);
    
    // Queue progress sync
    await queueProgressSync(examId, user.id);
  }, [examId, user, progress]);

  // Submit exam (queues for sync if offline)
  const submitExam = useCallback(async (answers: Record<string, string>) => {
    if (!examId || !user) throw new Error('No exam or user');
    
    if (isOnline()) {
      // Try online submission first
      try {
        const response = await apiClient.post(`/exams/${examId}/submit`, {
          answers: Object.entries(answers).map(([qId, resp]) => ({
            question_id: qId,
            response: resp,
          })),
        });
        
        // Clear offline progress on successful submission
        await deleteExamProgress(examId, user.id);
        setProgress(null);
        
        return response.data;
      } catch (error) {
        // Fall through to offline queue
        console.warn('Online submission failed, queuing for offline sync:', error);
      }
    }
    
    // Queue for offline sync
    await queueExamSubmission(examId, user.id, answers);
    showInfo('Exam queued for submission when online');
    
    return { queued: true };
  }, [examId, user, showInfo]);

  // Process sync queue when online
  const sync = useCallback(async () => {
    if (!isOnline() || syncing) return;
    
    setSyncing(true);
    try {
      await processSyncQueue(apiClient);
      await refreshStats();
      showSuccess('Sync completed');
    } catch (error: any) {
      showError('Sync failed', error.message);
    } finally {
      setSyncing(false);
    }
  }, [refreshStats, showError, showSuccess, syncing]);

  // Setup online/offline listeners
  useEffect(() => {
    const cleanup = setupOnlineListener(
      () => {
        setOnline(true);
        showInfo('Back online - syncing...');
      },
      () => {
        setOnline(false);
        showInfo('Offline mode - changes saved locally');
      }
    );
    
    // Initial stats load
    void refreshStats();
    
    return cleanup;
  }, [refreshStats, showInfo]);

  // Sync once per offline-to-online transition; avoid a render-loop after syncing.
  useEffect(() => {
    if (online && !wasOnline.current) {
      void sync();
    }
    wasOnline.current = online;
  }, [online, sync]);

  return {
    online,
    syncing,
    stats,
    progress,
    saveAnswer,
    submitExam,
    sync,
    refreshStats,
  };
}
