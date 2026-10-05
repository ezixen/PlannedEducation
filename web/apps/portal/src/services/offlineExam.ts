/**
 * Offline Exam Engine for PlannedEducation
 * Handles fully offline exam execution with IndexedDB persistence,
 * local timer, SEB integration, and auto-submit on time expiry.
 */

import { openDB, type DBSchema, type IDBPDatabase } from 'idb';
import { apiClient } from '../api';

// ── Types ────────────────────────────────────────────────────────────────────

export interface ExamPackage {
  examId: string;
  title: string;
  duration_minutes: number;
  instructions: string;
  questions: ExamQuestion[];
  settings: ExamSettings;
  seb_config_key?: string;
  started_at: number; // Server timestamp when exam was started
  expires_at: number; // Server timestamp when exam must be submitted by
}

export interface ExamQuestion {
  question_id: string;
  question_type: 'multiple_choice' | 'essay' | 'dynamic_math';
  text: string;
  options: string[] | null;
  points: number;
  correct_answer?: string; // Only included if teacher allows
  rubric?: string;
}

export interface ExamSettings {
  shuffle_questions: boolean;
  shuffle_options: boolean;
  show_results_immediately: boolean;
  allow_review: boolean;
  require_seb: boolean;
  time_multiplier: number;
  passing_score: number;
}

export interface OfflineExamState {
  id: string; // `${examId}-${studentId}`
  examId: string;
  studentId: string;
  package: ExamPackage | null;
  answers: Record<string, string>; // questionId -> response
  currentQuestionIndex: number;
  timeRemainingMs: number; // Milliseconds remaining
  timerState: 'running' | 'paused' | 'expired' | 'completed';
  lastTimerTick: number; // Timestamp of last timer update
  startedAt: number; // Local timestamp when exam was started
  lastHeartbeat: number; // Last heartbeat sent to server
  isComplete: boolean;
  submissionId?: string;
  sebViolations: SEBViolation[];
  lastUpdated: number;
}

export interface SEBViolation {
  type: 'exit' | 'minimize' | 'focus_loss' | 'shortcut_blocked' | 'process_detected';
  timestamp: number;
  details?: string;
}

export interface HeartbeatPayload {
  examId: string;
  studentId: string;
  timeRemainingMs: number;
  currentQuestionIndex: number;
  answersCount: number;
  sebViolations: SEBViolation[];
  clientTimestamp: number;
}

export interface ExamStartResponse {
  exam_package: ExamPackage;
  submission_id: string;
  server_time: number;
}

// ── IndexedDB Schema ────────────────────────────────────────────────────────

interface OfflineExamSchema extends DBSchema {
  offlineExams: {
    key: string;
    value: OfflineExamState;
    indexes: { 'by-exam': string; 'by-student': string; 'by-status': string };
  };
  examPackages: {
    key: string;
    value: ExamPackage;
    indexes: { 'by-exam': string };
  };
  heartbeatQueue: {
    key: number;
    value: HeartbeatQueueItem;
    indexes: { 'by-exam': string };
  };
}

interface HeartbeatQueueItem {
  id?: number;
  examId: string;
  studentId: string;
  payload: HeartbeatPayload;
  createdAt: number;
  attempts: number;
}

const DB_NAME = 'plannededucation-offline-exam';
const DB_VERSION = 1;

let dbInstance: IDBPDatabase<OfflineExamSchema> | null = null;

async function getExamDB(): Promise<IDBPDatabase<OfflineExamSchema>> {
  if (dbInstance) return dbInstance;
  
  dbInstance = await openDB<OfflineExamSchema>(DB_NAME, DB_VERSION, {
    upgrade(db) {
      // Offline Exam State Store
      const examStore = db.createObjectStore('offlineExams', { keyPath: 'id' });
      examStore.createIndex('by-exam', 'examId');
      examStore.createIndex('by-student', 'studentId');
      examStore.createIndex('by-status', 'timerState');
      
      // Exam Packages Store (cached for offline use)
      db.createObjectStore('examPackages', { keyPath: 'examId' });
      
      // Heartbeat Queue (for when online)
      const heartbeatStore = db.createObjectStore('heartbeatQueue', { keyPath: 'id', autoIncrement: true });
      heartbeatStore.createIndex('by-exam', 'examId');
    },
  });
  
  return dbInstance;
}

// ── Exam Package Management ────────────────────────────────────────────────

/**
 * Download and cache the full exam package for offline use.
 * Called when student clicks "Start Exam" in SEB.
 */
export async function downloadExamPackage(examId: string): Promise<ExamStartResponse> {
  const response = await apiClient.post(`/exams/${examId}/start`);
  return response.data;
}

export async function cacheExamPackage(pkg: ExamPackage): Promise<void> {
  const db = await getExamDB();
  await db.put('examPackages', pkg);
}

export async function getCachedExamPackage(examId: string): Promise<ExamPackage | undefined> {
  const db = await getExamDB();
  return db.get('examPackages', examId);
}

export async function removeCachedExamPackage(examId: string): Promise<void> {
  const db = await getExamDB();
  await db.delete('examPackages', examId);
}

// ── Offline Exam State Management ──────────────────────────────────────────

export async function saveOfflineExamState(state: OfflineExamState): Promise<void> {
  const db = await getExamDB();
  state.lastUpdated = Date.now();
  await db.put('offlineExams', state);
}

export async function getOfflineExamState(examId: string, studentId: string): Promise<OfflineExamState | undefined> {
  const db = await getExamDB();
  const id = `${examId}-${studentId}`;
  return db.get('offlineExams', id);
}

export async function getAllOfflineExams(studentId: string): Promise<OfflineExamState[]> {
  const db = await getExamDB();
  const all = await db.getAllFromIndex('offlineExams', 'by-student', studentId);
  return all;
}

export async function deleteOfflineExamState(examId: string, studentId: string): Promise<void> {
  const db = await getExamDB();
  const id = `${examId}-${studentId}`;
  await db.delete('offlineExams', id);
}

// ── Timer Management ────────────────────────────────────────────────────────

/**
 * Calculate remaining time based on last timer tick.
 * This works even if the app was closed/restarted.
 */
export function calculateTimeRemaining(state: OfflineExamState): number {
  if (state.timerState !== 'running') {
    return state.timeRemainingMs;
  }
  
  const now = Date.now();
  const elapsed = now - state.lastTimerTick;
  const remaining = Math.max(0, state.timeRemainingMs - elapsed);
  
  return remaining;
}

/**
 * Update timer state with new remaining time.
 * Call this periodically (e.g., every second) while exam is running.
 */
export function tickTimer(state: OfflineExamState): OfflineExamState {
  const remaining = calculateTimeRemaining(state);
  
  const newState = {
    ...state,
    timeRemainingMs: remaining,
    lastTimerTick: Date.now(),
    timerState: remaining <= 0 ? 'expired' : state.timerState,
  };
  
  return newState;
}

/**
 * Start the exam timer.
 */
export function startTimer(state: OfflineExamState, durationMinutes: number, timeMultiplier = 1): OfflineExamState {
  const totalMs = durationMinutes * 60 * 1000 * timeMultiplier;
  
  return {
    ...state,
    timeRemainingMs: totalMs,
    timerState: 'running',
    lastTimerTick: Date.now(),
    startedAt: state.startedAt || Date.now(),
  };
}

/**
 * Pause the timer (e.g., if SEB loses focus but exam isn't failed yet).
 */
export function pauseTimer(state: OfflineExamState): OfflineExamState {
  const remaining = calculateTimeRemaining(state);
  
  return {
    ...state,
    timeRemainingMs: remaining,
    timerState: 'paused',
    lastTimerTick: Date.now(),
  };
}

/**
 * Complete the exam (student clicked submit).
 */
export function completeExam(state: OfflineExamState): OfflineExamState {
  return {
    ...state,
    timerState: 'completed',
    isComplete: true,
    timeRemainingMs: 0,
  };
}

// ── SEB Integration ────────────────────────────────────────────────────────

/**
 * SEB (Safe Exam Browser) integration for cheat detection.
 * Detects: exit, minimize, focus loss, blocked shortcuts, suspicious processes.
 */
export class SEBMonitor {
  private examId: string;
  private onViolation: (violation: SEBViolation) => void;
  private onExamFailed: () => void;
  private visibilityChangeHandler: () => void;
  private beforeUnloadHandler: () => void;
  private keydownHandler: (e: KeyboardEvent) => void;
  private intervalId: number | null = null;
  private isMonitoring = false;
  
  // Blocked shortcuts that could be used to escape SEB
  private blockedShortcuts = [
    { key: 'F4', alt: true },      // Alt+F4 (close window)
    { key: 'Tab', alt: true },     // Alt+Tab (switch apps)
    { key: 'Escape', ctrl: true }, // Ctrl+Escape (Start menu)
    { key: 'Delete', ctrl: true, shift: true }, // Ctrl+Shift+Delete (Task Manager)
    { key: 'F12' },                // F12 (DevTools)
    { key: 'I', ctrl: true, shift: true }, // Ctrl+Shift+I (DevTools)
    { key: 'J', ctrl: true, shift: true }, // Ctrl+Shift+J (DevTools)
    { key: 'C', ctrl: true, shift: true }, // Ctrl+Shift+C (DevTools)
    { key: 'U', ctrl: true },      // Ctrl+U (View Source)
    { key: 'S', ctrl: true },      // Ctrl+S (Save Page)
    { key: 'P', ctrl: true },      // Ctrl+P (Print)
    { key: 'N', ctrl: true },      // Ctrl+N (New Window)
    { key: 'T', ctrl: true },      // Ctrl+T (New Tab)
    { key: 'W', ctrl: true },      // Ctrl+W (Close Tab)
    { key: 'R', ctrl: true },      // Ctrl+R (Reload)
  ];
  
  constructor(
    examId: string,
    onViolation: (violation: SEBViolation) => void,
    onExamFailed: () => void
  ) {
    this.examId = examId;
    this.onViolation = onViolation;
    this.onExamFailed = onExamFailed;
    
    this.visibilityChangeHandler = this.handleVisibilityChange.bind(this);
    this.beforeUnloadHandler = this.handleBeforeUnload.bind(this);
    this.keydownHandler = this.handleKeyDown.bind(this);
  }
  
  start(): void {
    if (this.isMonitoring) return;
    this.isMonitoring = true;
    
    // Page Visibility API - detects minimize, tab switch, SEB exit
    document.addEventListener('visibilitychange', this.visibilityChangeHandler);
    
    // Before unload - detects page close/refresh
    window.addEventListener('beforeunload', this.beforeUnloadHandler);
    
    // Keyboard shortcuts blocking
    document.addEventListener('keydown', this.keydownHandler, true); // Capture phase
    
    // Periodic heartbeat/check
    this.intervalId = window.setInterval(() => this.periodicCheck(), 5000);
    
    console.log('[SEBMonitor] Started monitoring for exam:', this.examId);
  }
  
  stop(): void {
    if (!this.isMonitoring) return;
    this.isMonitoring = false;
    
    document.removeEventListener('visibilitychange', this.visibilityChangeHandler);
    window.removeEventListener('beforeunload', this.beforeUnloadHandler);
    document.removeEventListener('keydown', this.keydownHandler, true);
    
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    
    console.log('[SEBMonitor] Stopped monitoring');
  }
  
  private handleVisibilityChange(): void {
    if (document.hidden) {
      // Page was minimized or tab switched
      this.recordViolation({
        type: 'minimize',
        timestamp: Date.now(),
        details: 'Page hidden - possible minimize or tab switch',
      });
      
      // In strict SEB mode, this fails the exam immediately
      this.failExam('Exam failed: Application minimized or tab switched');
    }
  }
  
  private handleBeforeUnload(): void {
    // Page is being closed/refreshed
    this.recordViolation({
      type: 'exit',
      timestamp: Date.now(),
      details: 'Page unload - browser/tab closed',
    });
    
    this.failExam('Exam failed: Browser or tab closed');
  }
  
  private handleKeyDown(e: KeyboardEvent): void {
    // Check if this is a blocked shortcut
    for (const shortcut of this.blockedShortcuts) {
      const keyMatch = e.key === shortcut.key || e.code === shortcut.key;
      const altMatch = shortcut.alt === undefined || e.altKey === shortcut.alt;
      const ctrlMatch = shortcut.ctrl === undefined || e.ctrlKey === shortcut.ctrl;
      const shiftMatch = shortcut.shift === undefined || e.shiftKey === shortcut.shift;
      
      if (keyMatch && altMatch && ctrlMatch && shiftMatch) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        
        this.recordViolation({
          type: 'shortcut_blocked',
          timestamp: Date.now(),
          details: `Blocked shortcut: ${e.key} (ctrl:${e.ctrlKey}, alt:${e.altKey}, shift:${e.shiftKey})`,
        });
        
        // Don't fail exam for shortcut attempts, just log
        break;
      }
    }
  }
  
  private periodicCheck(): void {
    // Check for suspicious processes (if we have access)
    // This is limited in browser but we can check some things
    
    // Check if we're still in fullscreen (SEB requirement)
    if (document.fullscreenElement === null && this.isMonitoring) {
      // Not in fullscreen - possible SEB exit
      this.recordViolation({
        type: 'exit',
        timestamp: Date.now(),
        details: 'Fullscreen lost - possible SEB exit',
      });
      this.failExam('Exam failed: Fullscreen mode lost');
    }
  }
  
  private recordViolation(violation: SEBViolation): void {
    console.warn('[SEBMonitor] Violation:', violation);
    this.onViolation(violation);
  }
  
  private failExam(reason: string): void {
    console.error('[SEBMonitor] Exam failed:', reason);
    this.stop();
    this.onExamFailed();
  }
}

// ── Heartbeat System ───────────────────────────────────────────────────────

/**
 * Queue heartbeat for sending to server when online.
 * Heartbeats allow teacher to monitor student progress in real-time.
 */
export async function queueHeartbeat(payload: HeartbeatPayload): Promise<void> {
  const db = await getExamDB();
  await db.add('heartbeatQueue', {
    examId: payload.examId,
    studentId: payload.studentId,
    payload,
    createdAt: Date.now(),
    attempts: 0,
  });
}

export async function getPendingHeartbeats(examId: string): Promise<HeartbeatQueueItem[]> {
  const db = await getExamDB();
  return db.getAllFromIndex('heartbeatQueue', 'by-exam', examId);
}

export async function removeHeartbeat(id: number): Promise<void> {
  const db = await getExamDB();
  await db.delete('heartbeatQueue', id);
}

export async function processHeartbeatQueue(): Promise<void> {
  const db = await getExamDB();
  const all = await db.getAll('heartbeatQueue');
  
  for (const item of all) {
    try {
      await apiClient.post(`/exams/${item.examId}/heartbeat`, item.payload);
      await removeHeartbeat(item.id!);
    } catch (error) {
      console.warn('Heartbeat failed, will retry:', error);
      // Update attempts
      await db.put('heartbeatQueue', {
        ...item,
        attempts: item.attempts + 1,
      });
      
      // Remove if too many attempts
      if (item.attempts >= 5) {
        await removeHeartbeat(item.id!);
      }
    }
  }
}

// ── Auto-Submit on Time Expiry ─────────────────────────────────────────────

/**
 * Submit exam answers to server.
 * If offline, queues for later submission.
 */
export async function submitExamOffline(
  examId: string,
  studentId: string,
  answers: Record<string, string>,
  submissionId: string
): Promise<{ success: boolean; queued: boolean; submissionId?: string }> {
  try {
    const response = await apiClient.post(`/exams/${examId}/submit`, {
      submission_id: submissionId,
      answers: Object.entries(answers).map(([qId, resp]) => ({
        question_id: qId,
        response: resp,
      })),
    });
    
    return { success: true, queued: false, submissionId: response.data.submission_id };
  } catch (error) {
    // Queue for offline submission
    const db = await getExamDB();
    await db.put('offlineExams', {
      id: `${examId}-${studentId}`,
      examId,
      studentId,
      package: null,
      answers,
      currentQuestionIndex: 0,
      timeRemainingMs: 0,
      timerState: 'completed',
      lastTimerTick: Date.now(),
      startedAt: Date.now(),
      lastHeartbeat: 0,
      isComplete: true,
      submissionId,
      sebViolations: [],
      lastUpdated: Date.now(),
    });
    
    return { success: true, queued: true };
  }
}

/**
 * Check if exam time has expired and auto-submit if needed.
 * Call this periodically or when app regains focus.
 */
export async function checkAndAutoSubmit(
  examId: string,
  studentId: string
): Promise<{ submitted: boolean; reason?: string }> {
  const state = await getOfflineExamState(examId, studentId);
  
  if (!state || state.isComplete || state.timerState !== 'running') {
    return { submitted: false, reason: 'Exam not running or already complete' };
  }
  
  const remaining = calculateTimeRemaining(state);
  
  if (remaining <= 0) {
    // Time expired - auto submit
    await submitExamOffline(
      examId,
      studentId,
      state.answers,
      state.submissionId || ''
    );
    
    // Update state to completed
    await saveOfflineExamState({
      ...state,
      timerState: 'expired',
      isComplete: true,
      timeRemainingMs: 0,
    });
    
    return { submitted: true, reason: 'Time expired - auto-submitted' };
  }
  
  return { submitted: false };
}

// ── Utility Functions ──────────────────────────────────────────────────────

export function formatTimeRemaining(ms: number): string {
  if (ms <= 0) return '00:00';
  
  const totalSeconds = Math.ceil(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

export function isExamExpired(state: OfflineExamState): boolean {
  return calculateTimeRemaining(state) <= 0;
}

export function getExamProgressPercent(state: OfflineExamState): number {
  if (!state.package || state.package.questions.length === 0) return 0;
  
  const answered = Object.keys(state.answers).filter(
    qId => state.answers[qId] && state.answers[qId].trim() !== ''
  ).length;
  
  return Math.round((answered / state.package.questions.length) * 100);
}