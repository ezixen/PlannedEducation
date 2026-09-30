/**
 * Offline Sync Service for PlannedEducation
 * Uses IndexedDB via idb library for offline-first data persistence
 * Syncs exam progress, answers, and submissions when online
 */

import { openDB, type DBSchema, type IDBPDatabase } from 'idb';

interface OfflineSchema extends DBSchema {
  examProgress: {
    key: string;
    value: ExamProgress;
    indexes: { 'by-exam': string; 'by-timestamp': number };
  };
  pendingSubmissions: {
    key: string;
    value: PendingSubmission;
    indexes: { 'by-exam': string; 'by-status': string };
  };
  cachedExams: {
    key: string;
    value: CachedExam;
    indexes: { 'by-teacher': string };
  };
  syncQueue: {
    key: number;
    value: SyncOperation;
    indexes: { 'by-type': string; 'by-priority': number };
  };
}

export interface ExamProgress {
  id: string; // `${examId}-${studentId}`
  examId: string;
  studentId: string;
  answers: Record<string, string>; // questionId -> response
  currentQuestionIndex: number;
  timeRemaining: number;
  lastUpdated: number;
  isComplete: boolean;
  submissionId?: string;
}

export interface PendingSubmission {
  id: string; // UUID
  examId: string;
  studentId: string;
  answers: Record<string, string>;
  submissionId?: string;
  status: 'pending' | 'submitting' | 'completed' | 'failed';
  attempts: number;
  createdAt: number;
  lastAttempt?: number;
  error?: string;
}

export interface CachedExam {
  id: string;
  examId: string;
  title: string;
  duration_minutes: number;
  questions: any[];
  teacherId: string;
  cachedAt: number;
  expiresAt: number;
}

export interface SyncOperation {
  id?: number;
  type: 'submit_exam' | 'fetch_exam' | 'sync_progress';
  payload: any;
  priority: number; // lower = higher priority
  status: 'pending' | 'processing' | 'completed' | 'failed';
  createdAt: number;
  attempts: number;
  lastError?: string;
}

const DB_NAME = 'plannededucation-offline';
const DB_VERSION = 1;

let dbInstance: IDBPDatabase<OfflineSchema> | null = null;

export async function getOfflineDB(): Promise<IDBPDatabase<OfflineSchema>> {
  if (dbInstance) return dbInstance;
  
  dbInstance = await openDB<OfflineSchema>(DB_NAME, DB_VERSION, {
    upgrade(db) {
      // Exam Progress Store
      const progressStore = db.createObjectStore('examProgress', { keyPath: 'id' });
      progressStore.createIndex('by-exam', 'examId');
      progressStore.createIndex('by-timestamp', 'lastUpdated');
      
      // Pending Submissions Store
      const submissionStore = db.createObjectStore('pendingSubmissions', { keyPath: 'id' });
      submissionStore.createIndex('by-exam', 'examId');
      submissionStore.createIndex('by-status', 'status');
      
      // Cached Exams Store
      const examStore = db.createObjectStore('cachedExams', { keyPath: 'id' });
      examStore.createIndex('by-teacher', 'teacherId');
      
      // Sync Queue Store
      const syncStore = db.createObjectStore('syncQueue', { keyPath: 'id', autoIncrement: true });
      syncStore.createIndex('by-type', 'type');
      syncStore.createIndex('by-priority', 'priority');
    },
  });
  
  return dbInstance;
}

// ── Exam Progress Functions ────────────────────────────────────────────────

export async function saveExamProgress(progress: ExamProgress): Promise<void> {
  const db = await getOfflineDB();
  progress.lastUpdated = Date.now();
  await db.put('examProgress', progress);
}

export async function getExamProgress(examId: string, studentId: string): Promise<ExamProgress | undefined> {
  const db = await getOfflineDB();
  const id = `${examId}-${studentId}`;
  return db.get('examProgress', id);
}

export async function getAllExamProgress(studentId: string): Promise<ExamProgress[]> {
  const db = await getOfflineDB();
  const all = await db.getAll('examProgress');
  return all.filter(p => p.studentId === studentId);
}

export async function deleteExamProgress(examId: string, studentId: string): Promise<void> {
  const db = await getOfflineDB();
  const id = `${examId}-${studentId}`;
  await db.delete('examProgress', id);
}

// ── Pending Submissions Functions ──────────────────────────────────────────

export async function addPendingSubmission(submission: PendingSubmission): Promise<void> {
  const db = await getOfflineDB();
  await db.put('pendingSubmissions', submission);
}

export async function updatePendingSubmission(id: string, updates: Partial<PendingSubmission>): Promise<void> {
  const db = await getOfflineDB();
  const existing = await db.get('pendingSubmissions', id);
  if (existing) {
    await db.put('pendingSubmissions', { ...existing, ...updates });
  }
}

export async function getPendingSubmissions(studentId: string): Promise<PendingSubmission[]> {
  const db = await getOfflineDB();
  const all = await db.getAll('pendingSubmissions');
  return all.filter(s => s.studentId === studentId);
}

export async function getPendingSubmissionByExam(examId: string, studentId: string): Promise<PendingSubmission | undefined> {
  const db = await getOfflineDB();
  const all = await db.getAllFromIndex('pendingSubmissions', 'by-exam', examId);
  return all.find(s => s.studentId === studentId);
}

export async function removePendingSubmission(id: string): Promise<void> {
  const db = await getOfflineDB();
  await db.delete('pendingSubmissions', id);
}

// ── Cached Exams Functions ─────────────────────────────────────────────────

export async function cacheExam(exam: CachedExam): Promise<void> {
  const db = await getOfflineDB();
  await db.put('cachedExams', exam);
}

export async function getCachedExam(examId: string): Promise<CachedExam | undefined> {
  const db = await getOfflineDB();
  return db.get('cachedExams', examId);
}

export async function getCachedExamsByTeacher(teacherId: string): Promise<CachedExam[]> {
  const db = await getOfflineDB();
  return db.getAllFromIndex('cachedExams', 'by-teacher', teacherId);
}

export async function removeExpiredCachedExams(): Promise<number> {
  const db = await getOfflineDB();
  const now = Date.now();
  const all = await db.getAll('cachedExams');
  let removed = 0;
  
  for (const exam of all) {
    if (exam.expiresAt < now) {
      await db.delete('cachedExams', exam.id);
      removed++;
    }
  }
  
  return removed;
}

// ── Sync Queue Functions ───────────────────────────────────────────────────

export async function enqueueSyncOperation(operation: Omit<SyncOperation, 'id' | 'createdAt' | 'attempts'>): Promise<number> {
  const db = await getOfflineDB();
  const id = await db.add('syncQueue', {
    ...operation,
    createdAt: Date.now(),
    attempts: 0,
  });
  return id;
}

export async function getPendingSyncOperations(limit = 10): Promise<SyncOperation[]> {
  const db = await getOfflineDB();
  const all = await db.getAllFromIndex('syncQueue', 'by-priority');
  return all
    .filter(op => op.status === 'pending')
    .sort((a, b) => a.priority - b.priority)
    .slice(0, limit);
}

export async function updateSyncOperation(id: number, updates: Partial<SyncOperation>): Promise<void> {
  const db = await getOfflineDB();
  const existing = await db.get('syncQueue', id);
  if (existing) {
    await db.put('syncQueue', { ...existing, ...updates });
  }
}

export async function removeSyncOperation(id: number): Promise<void> {
  const db = await getOfflineDB();
  await db.delete('syncQueue', id);
}

// ── High-Level Sync Functions ──────────────────────────────────────────────

export async function queueExamSubmission(
  examId: string,
  studentId: string,
  answers: Record<string, string>
): Promise<void> {
  const submission: PendingSubmission = {
    id: crypto.randomUUID(),
    examId,
    studentId,
    answers,
    status: 'pending',
    attempts: 0,
    createdAt: Date.now(),
  };
  
  await addPendingSubmission(submission);
  await enqueueSyncOperation({
    type: 'submit_exam',
    payload: { submissionId: submission.id },
    priority: 1,
    status: 'pending',
  });
}

export async function queueProgressSync(
  examId: string,
  studentId: string
): Promise<void> {
  await enqueueSyncOperation({
    type: 'sync_progress',
    payload: { examId, studentId },
    priority: 5,
    status: 'pending',
  });
}

export async function processSyncQueue(apiClient: any): Promise<void> {
  const operations = await getPendingSyncOperations(20);
  
  for (const op of operations) {
    await updateSyncOperation(op.id!, { status: 'processing', attempts: op.attempts + 1 });
    
    try {
      switch (op.type) {
        case 'submit_exam': {
          const submission = await getPendingSubmissionByExam(op.payload.examId, op.payload.studentId);
          if (submission) {
            await updatePendingSubmission(submission.id, { status: 'submitting' });
            
            const response = await apiClient.post(`/exams/${op.payload.examId}/submit`, {
              answers: Object.entries(submission.answers).map(([qId, resp]) => ({
                question_id: qId,
                response: resp,
              })),
            });
            
            await updatePendingSubmission(submission.id, { 
              status: 'completed', 
              submissionId: response.data.submission_id 
            });
            await removeSyncOperation(op.id!);
          }
          break;
        }
        
        case 'sync_progress': {
          // Progress is already saved locally, just mark as synced
          await removeSyncOperation(op.id!);
          break;
        }
        
        case 'fetch_exam': {
          // Fetch and cache exam for offline use
          const response = await apiClient.get(`/exams/${op.payload.examId}/start`);
          const cachedExam: CachedExam = {
            id: op.payload.examId,
            examId: op.payload.examId,
            title: response.data.title || 'Untitled Exam',
            duration_minutes: response.data.duration_minutes || 60,
            questions: response.data.questions || [],
            teacherId: response.data.teacher_id || '',
            cachedAt: Date.now(),
            expiresAt: Date.now() + 7 * 24 * 60 * 60 * 1000, // 1 week
          };
          await cacheExam(cachedExam);
          await removeSyncOperation(op.id!);
          break;
        }
      }
    } catch (error: any) {
      await updateSyncOperation(op.id!, { 
        status: 'failed', 
        lastError: error.message,
        attempts: op.attempts + 1 
      });
      
      // Re-queue with lower priority if not too many attempts
      if (op.attempts < 3) {
        await enqueueSyncOperation({
          type: op.type,
          payload: op.payload,
          priority: op.priority + 1,
          status: 'pending',
        });
        await removeSyncOperation(op.id!);
      }
    }
  }
}

// ── Utility Functions ──────────────────────────────────────────────────────

export async function clearAllOfflineData(): Promise<void> {
  const db = await getOfflineDB();
  await db.clear('examProgress');
  await db.clear('pendingSubmissions');
  await db.clear('cachedExams');
  await db.clear('syncQueue');
}

export async function getOfflineStorageStats(): Promise<{
  progressCount: number;
  pendingSubmissions: number;
  cachedExams: number;
  syncQueueSize: number;
}> {
  const db = await getOfflineDB();
  return {
    progressCount: (await db.getAll('examProgress')).length,
    pendingSubmissions: (await db.getAll('pendingSubmissions')).length,
    cachedExams: (await db.getAll('cachedExams')).length,
    syncQueueSize: (await db.getAll('syncQueue')).length,
  };
}

export function isOnline(): boolean {
  return navigator.onLine;
}

export function setupOnlineListener(onOnline: () => void, onOffline: () => void): () => void {
  window.addEventListener('online', onOnline);
  window.addEventListener('offline', onOffline);
  
  return () => {
    window.removeEventListener('online', onOnline);
    window.removeEventListener('offline', onOffline);
  };
}