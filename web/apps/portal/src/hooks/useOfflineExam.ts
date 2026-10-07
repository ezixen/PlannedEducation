/**
 * React Hook for Offline Exam Engine
 * Manages exam state, timer, SEB monitoring, and auto-submit
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { useNavigate } from 'react-router-dom';
import {
  type ExamPackage,
  type OfflineExamState,
  type HeartbeatPayload,
  downloadExamPackage,
  cacheExamPackage,
  saveOfflineExamState,
  getOfflineExamState,
  startTimer,
  tickTimer,
  completeExam,
  calculateTimeRemaining,
  SEBMonitor,
  queueHeartbeat,
  processHeartbeatQueue,
  checkAndAutoSubmit,
  submitExamOffline,
  formatTimeRemaining,
  getExamProgressPercent,
  sealExamSubmission,
} from '../services/offlineExam';

interface UseOfflineExamOptions {
  examId: string;
  onExamFailed?: (reason: string) => void;
  onExamCompleted?: () => void;
  onTimeWarning?: (minutesRemaining: number) => void;
}

export function useOfflineExam({ examId, onExamFailed, onExamCompleted, onTimeWarning }: UseOfflineExamOptions) {
  const { user } = useAuth();
  const { error: showError, success: showSuccess, info: showInfo, warn: showWarn } = useToast();
  const navigate = useNavigate();
  
  const [examPackage, setExamPackage] = useState<ExamPackage | null>(null);
  const [examState, setExamState] = useState<OfflineExamState | null>(null);
  const [loading, setLoading] = useState(true);
  const [initializing, setInitializing] = useState(true);
  const [timeWarningShown, setTimeWarningShown] = useState(false);
  
  const timerIntervalRef = useRef<number | null>(null);
  const heartbeatIntervalRef = useRef<number | null>(null);
  const sebMonitorRef = useRef<SEBMonitor | null>(null);
  const autoSubmitCheckRef = useRef<number | null>(null);
  const lastHeartbeatRef = useRef<number>(0);
  
  const studentId = user?.id || '';
  
  // ── Initialize Exam ──────────────────────────────────────────────────────
  
  const initializeExam = useCallback(async () => {
    if (!examId || !studentId) {
      showError('Missing exam or user information');
      navigate('/dashboard');
      return;
    }
    
    setInitializing(true);
    
    try {
      // Try to load existing offline state
      let state = await getOfflineExamState(examId, studentId);
      
      if (state && state.package) {
        // Resume existing exam
        setExamPackage(state.package);
        setExamState(state);
        
        // If exam was running, restart timer
        if (state.timerState === 'running') {
          const remaining = calculateTimeRemaining(state);
          if (remaining > 0) {
            setExamState(prev => prev ? tickTimer(prev) : null);
          } else {
            // Time expired while offline - auto submit
            await checkAndAutoSubmit(examId, studentId);
            const updated = await getOfflineExamState(examId, studentId);
            if (updated) setExamState(updated);
          }
        }
      } else {
        // Fresh start - download exam package
        const response = await downloadExamPackage(examId);
        const pkg = response.exam_package;
        
        // Cache for offline use
        await cacheExamPackage(pkg);
        setExamPackage(pkg);
        
        // Create initial state
        const initialState: OfflineExamState = {
          id: `${examId}-${studentId}`,
          examId,
          studentId,
          studentName: user?.full_name || user?.username || 'Unknown Student',
          package: pkg,
          answers: {},
          answerTimestamps: {},
          currentQuestionIndex: 0,
          timeRemainingMs: 0,
          timerState: 'paused',
          lastTimerTick: Date.now(),
          startedAt: 0,
          lastHeartbeat: 0,
          isComplete: false,
          submissionId: response.submission_id,
          sebViolations: [],
          lastUpdated: Date.now(),
        };
        
        await saveOfflineExamState(initialState);
        setExamState(initialState);
      }
      
      showSuccess('Exam loaded successfully');
    } catch (error: any) {
      showError('Failed to load exam', error.message);
      navigate('/dashboard');
    } finally {
      setLoading(false);
      setInitializing(false);
    }
  }, [examId, studentId, navigate, showError, showSuccess]);
  
  useEffect(() => {
    initializeExam();
  }, [initializeExam]);
  
  // ── Timer Management ─────────────────────────────────────────────────────
  
  const startExam = useCallback(() => {
    if (!examState || !examPackage) return;
    
    const newState = startTimer(
      examState,
      examPackage.duration_minutes,
      examPackage.settings.time_multiplier
    );
    
    setExamState(newState);
    saveOfflineExamState(newState);
    
    // Start timer interval
    timerIntervalRef.current = window.setInterval(() => {
      setExamState(prev => {
        if (!prev) return null;
        const ticked = tickTimer(prev);
        
        // Check for time warnings (5 min, 1 min)
        const remaining = ticked.timeRemainingMs;
        if (remaining <= 5 * 60 * 1000 && remaining > 4 * 60 * 1000 && !timeWarningShown) {
          setTimeWarningShown(true);
          onTimeWarning?.(5);
          showWarn('5 minutes remaining!');
        } else if (remaining <= 1 * 60 * 1000 && remaining > 30 * 1000 && timeWarningShown) {
          onTimeWarning?.(1);
          showWarn('1 minute remaining!');
        }
        
        // Auto-submit on expiry
        if (ticked.timerState === 'expired') {
          handleAutoSubmit();
        }
        
        saveOfflineExamState(ticked);
        return ticked;
      });
    }, 1000);
    
    // Start SEB monitoring if required
    if (examPackage.settings.require_seb) {
      startSEBMonitoring();
    }
    
    // Start heartbeat
    startHeartbeat();
    
    // Start auto-submit check (every 10 seconds)
    autoSubmitCheckRef.current = window.setInterval(() => {
      checkAndAutoSubmit(examId, studentId);
    }, 10000);
    
    showInfo('Exam started! Good luck!');
  }, [examState, examPackage, studentId, onTimeWarning, showWarn, showInfo]);
  
  const handleAutoSubmit = useCallback(async () => {
    if (!examState || examState.isComplete) return;
    
    // Stop timer
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    
    // Seal the exam submission (cryptographically sign and encrypt)
    try {
      const studentName = user?.full_name || user?.username || 'Unknown Student';
      const sealed = await sealExamSubmission(examState, studentName);
      
      // Also submit to server if online
      const result = await submitExamOffline(
        examId,
        studentId,
        examState.answers,
        examState.submissionId || ''
      );
      
      // Update state with sealed submission
      const completedState = {
        ...completeExam(examState),
        sealedSubmission: sealed,
      };
      setExamState(completedState);
      await saveOfflineExamState(completedState);
      
      // Stop monitoring
      stopSEBMonitoring();
      stopHeartbeat();
      if (autoSubmitCheckRef.current) {
        clearInterval(autoSubmitCheckRef.current);
      }
      
      if (result.queued) {
        showInfo('Exam submitted offline. Sealed and queued for sync.');
      } else {
        showSuccess('Exam submitted and sealed successfully!');
      }
      
      onExamCompleted?.();
      
      // Navigate to results or dashboard after a delay
      setTimeout(() => navigate('/dashboard'), 3000);
    } catch (error: any) {
      showError('Failed to seal exam submission', error.message);
      console.error('Seal failed:', error);
    }
  }, [examState, examId, studentId, user, navigate, showInfo, showSuccess, showError, onExamCompleted]);
  
  // ── Answer Management ────────────────────────────────────────────────────
  
  const saveAnswer = useCallback(async (questionId: string, response: string) => {
    if (!examState) return;
    
    const newState = {
      ...examState,
      answers: { ...examState.answers, [questionId]: response },
      answerTimestamps: { ...examState.answerTimestamps, [questionId]: Date.now() },
      lastUpdated: Date.now(),
    };
    
    setExamState(newState);
    await saveOfflineExamState(newState);
  }, [examState]);
  
  const setCurrentQuestion = useCallback((index: number) => {
    if (!examState) return;
    
    const newState = {
      ...examState,
      currentQuestionIndex: index,
      lastUpdated: Date.now(),
    };
    
    setExamState(newState);
    saveOfflineExamState(newState);
  }, [examState]);
  
  // ── SEB Monitoring ───────────────────────────────────────────────────────
  
  const startSEBMonitoring = useCallback(() => {
    if (sebMonitorRef.current) return;
    
    sebMonitorRef.current = new SEBMonitor(
      examId,
      (violation) => {
        // Add violation to state
        setExamState(prev => {
          if (!prev) return null;
          const newState = {
            ...prev,
            sebViolations: [...prev.sebViolations, violation],
            lastUpdated: Date.now(),
          };
          saveOfflineExamState(newState);
          return newState;
        });
        
        showWarn(`Security violation: ${violation.type}`);
      },
      () => {
        // Exam failed due to SEB violation
        handleExamFailed('Exam failed: Security violation detected');
      }
    );
    
    sebMonitorRef.current.start();
  }, [examId, studentId, showWarn]);
  
  const stopSEBMonitoring = useCallback(() => {
    if (sebMonitorRef.current) {
      sebMonitorRef.current.stop();
      sebMonitorRef.current = null;
    }
  }, []);
  
  const handleExamFailed = useCallback((reason: string) => {
    // Stop everything
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    stopSEBMonitoring();
    stopHeartbeat();
    if (autoSubmitCheckRef.current) {
      clearInterval(autoSubmitCheckRef.current);
    }
    
    // Mark exam as failed
    setExamState(prev => {
      if (!prev) return null;
      const failedState = {
        ...prev,
        timerState: 'completed' as const,
        isComplete: true,
        lastUpdated: Date.now(),
      };
      saveOfflineExamState(failedState);
      return failedState;
    });
    
    showError('Exam Failed', { key: 'exam-failed' });
console.error('Exam failed:', reason);
    onExamFailed?.(reason);
    
    // Navigate away after delay
    setTimeout(() => navigate('/dashboard'), 3000);
  }, [showError, navigate, onExamFailed]);
  
  // ── Heartbeat System ─────────────────────────────────────────────────────
  
  const startHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) return;
    
    heartbeatIntervalRef.current = window.setInterval(async () => {
      if (!examState || examState.timerState !== 'running') return;
      
      const payload: HeartbeatPayload = {
        examId,
        studentId,
        timeRemainingMs: calculateTimeRemaining(examState),
        currentQuestionIndex: examState.currentQuestionIndex,
        answersCount: Object.keys(examState.answers).length,
        sebViolations: examState.sebViolations,
        clientTimestamp: Date.now(),
      };
      
      await queueHeartbeat(payload);
      lastHeartbeatRef.current = Date.now();
      
      // Try to process queue if online
      try {
        await processHeartbeatQueue();
      } catch {
        // Ignore - will retry next interval
      }
    }, 30000); // Every 30 seconds
  }, [examId, studentId, examState]);
  
  const stopHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);
  
  // ── Cleanup ──────────────────────────────────────────────────────────────
  
  useEffect(() => {
    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
      if (autoSubmitCheckRef.current) clearInterval(autoSubmitCheckRef.current);
      stopSEBMonitoring();
    };
  }, [stopSEBMonitoring]);
  
  // ── Computed Values ──────────────────────────────────────────────────────
  
  const timeRemaining = examState ? calculateTimeRemaining(examState) : 0;
  const timeRemainingFormatted = formatTimeRemaining(timeRemaining);
  const progressPercent = examState && examPackage ? getExamProgressPercent(examState) : 0;
  const currentQuestion = examPackage && examState 
    ? examPackage.questions[examState.currentQuestionIndex] 
    : null;
  const isExamRunning = examState?.timerState === 'running';
  const isExamComplete = examState?.isComplete === true;
  const isExamExpired = examState ? timeRemaining <= 0 && examState.timerState === 'running' : false;
  
  return {
    // State
    examPackage,
    examState,
    loading,
    initializing,
    
    // Timer
    timeRemaining,
    timeRemainingFormatted,
    isExamRunning,
    isExamComplete,
    isExamExpired,
    
    // Progress
    progressPercent,
    currentQuestion,
    currentQuestionIndex: examState?.currentQuestionIndex || 0,
    totalQuestions: examPackage?.questions.length || 0,
    
    // Actions
    startExam,
    saveAnswer,
    setCurrentQuestion,
    submitExam: handleAutoSubmit,
    
    // SEB
    sebViolations: examState?.sebViolations || [],
    
    // Helpers
    formatTimeRemaining,
  };
}