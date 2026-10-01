import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../api';

interface QuestionBankItem {
  id: string;
  question_type: 'multiple_choice' | 'essay' | 'dynamic_math';
  text: string;
  options: string[] | null;
  correct_answer: string | null;
  rubric: string | null;
  points: number;
  tags: string[];
  difficulty: 'easy' | 'medium' | 'hard';
  estimated_time_minutes: number;
  variables: QuestionVariable[];
  created_at: string;
  updated_at: string;
  is_synced: boolean;
  local_id?: string;
}

interface QuestionVariable {
  name: string;
  type: 'integer' | 'float' | 'choice';
  min?: number;
  max?: number;
  step?: number;
  choices?: string[];
  formula?: string;
}

interface QuestionBankFilters {
  search: string;
  type: 'all' | 'multiple_choice' | 'essay' | 'dynamic_math';
  difficulty: 'all' | 'easy' | 'medium' | 'hard';
  tags: string[];
  showOnlyUnsynced: boolean;
}

export function useQuestionBank() {
  const { user } = useAuth();
  const { success: showSuccess, error: showError, info: showInfo } = useToast();
  
  const [questions, setQuestions] = useState<QuestionBankItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [filters, setFilters] = useState<QuestionBankFilters>({
    search: '',
    type: 'all',
    difficulty: 'all',
    tags: [],
    showOnlyUnsynced: false,
  });
  const [allTags, setAllTags] = useState<string[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionBankItem | null>(null);
  const [showEditor, setShowEditor] = useState(false);

  // Load questions from server
  const loadQuestions = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const response = await apiClient.get('/questions/bank', {
        params: { teacher_id: user.id },
      });
      const serverQuestions = response.data.map((q: any) => ({
        ...q,
        is_synced: true,
        tags: q.tags ? JSON.parse(q.tags) : [],
        variables: q.variables ? JSON.parse(q.variables) : [],
      }));
      setQuestions(serverQuestions);
      
      // Extract all unique tags
      const tags = new Set<string>();
      serverQuestions.forEach((q: QuestionBankItem) => {
        q.tags.forEach(tag => tags.add(tag));
      });
      setAllTags(Array.from(tags).sort());
    } catch (err: any) {
      showError('Failed to load question bank', err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }, [user, showError]);

  useEffect(() => {
    loadQuestions();
  }, [loadQuestions]);

  // Save question locally (to IndexedDB via offline sync)
  const saveQuestion = useCallback(async (question: Partial<QuestionBankItem> & { text: string }) => {
    if (!user) return;
    setSaving(true);
    try {
      const isNew = !question.id || question.id.startsWith('local-');
      
      const payload = {
        ...question,
        id: question.id || `local-${Date.now()}`,
        teacher_id: user.id,
        tags: JSON.stringify(question.tags || []),
        variables: JSON.stringify(question.variables || []),
        options: question.options ? JSON.stringify(question.options) : null,
      };
      
      if (isNew) {
        const response = await apiClient.post('/questions/bank', payload);
        const newQuestion = {
          ...response.data,
          is_synced: true,
          tags: question.tags || [],
          variables: question.variables || [],
        };
        setQuestions(prev => [newQuestion, ...prev]);
        showSuccess('Question created and synced');
      } else {
        await apiClient.put(`/questions/bank/${question.id}`, payload);
        setQuestions(prev => prev.map(q => 
          q.id === question.id ? { ...q, ...question, is_synced: true } : q
        ));
        showSuccess('Question updated and synced');
      }
      
      setShowEditor(false);
      setSelectedQuestion(null);
    } catch (err: any) {
      // If offline, save locally
      if (!navigator.onLine) {
        const isNew = !question.id || question.id.startsWith('local-');
        const localQuestion = {
          ...question,
          id: question.id || `local-${Date.now()}`,
          is_synced: false,
          local_id: question.id?.startsWith('local-') ? question.id : undefined,
        } as QuestionBankItem;
        
        setQuestions(prev => {
          if (isNew) {
            return [localQuestion, ...prev];
          }
          return prev.map(q => q.id === question.id ? { ...q, ...question, is_synced: false } : q);
        });
        showInfo('Saved locally - will sync when online');
      } else {
        showError('Failed to save question', err.response?.data?.detail || err.message);
      }
    } finally {
      setSaving(false);
    }
  }, [user, showSuccess, showError, showInfo]);

  // Delete question
  const deleteQuestion = useCallback(async (questionId: string) => {
    if (!user) return;
    if (!confirm('Are you sure you want to delete this question?')) return;
    
    try {
      if (questionId.startsWith('local-')) {
        // Local only - just remove from state
        setQuestions(prev => prev.filter(q => q.id !== questionId));
        showSuccess('Local question deleted');
      } else {
        await apiClient.delete(`/questions/bank/${questionId}`);
        setQuestions(prev => prev.filter(q => q.id !== questionId));
        showSuccess('Question deleted and synced');
      }
    } catch (err: any) {
      showError('Failed to delete question', err.response?.data?.detail || err.message);
    }
  }, [user, showSuccess, showError]);

  // Sync unsynced questions
  const syncQuestions = useCallback(async () => {
    if (!user || !navigator.onLine) return;
    setSyncing(true);
    try {
      const unsynced = questions.filter(q => !q.is_synced);
      let syncedCount = 0;
      
      for (const question of unsynced) {
        try {
          const payload = {
            ...question,
            teacher_id: user.id,
            tags: JSON.stringify(question.tags),
            variables: JSON.stringify(question.variables),
            options: question.options ? JSON.stringify(question.options) : null,
          };
          
          if (question.id.startsWith('local-')) {
            const response = await apiClient.post('/questions/bank', payload);
            setQuestions(prev => prev.map(q => 
              q.id === question.id ? { ...response.data, is_synced: true } : q
            ));
          } else {
            await apiClient.put(`/questions/bank/${question.id}`, payload);
            setQuestions(prev => prev.map(q => 
              q.id === question.id ? { ...q, is_synced: true } : q
            ));
          }
          syncedCount++;
        } catch (err) {
          console.error(`Failed to sync question ${question.id}:`, err);
        }
      }
      
      if (syncedCount > 0) {
        showSuccess(`Synced ${syncedCount} questions`);
      } else {
        showInfo('All questions already synced');
      }
    } catch (err: any) {
      showError('Sync failed', err.message);
    } finally {
      setSyncing(false);
    }
  }, [user, questions, showSuccess, showError, showInfo]);

  // Filter questions
  const filteredQuestions = questions.filter(q => {
    if (filters.search && !q.text.toLowerCase().includes(filters.search.toLowerCase())) {
      return false;
    }
    if (filters.type !== 'all' && q.question_type !== filters.type) {
      return false;
    }
    if (filters.difficulty !== 'all' && q.difficulty !== filters.difficulty) {
      return false;
    }
    if (filters.tags.length > 0 && !filters.tags.some(tag => q.tags.includes(tag))) {
      return false;
    }
    if (filters.showOnlyUnsynced && q.is_synced) {
      return false;
    }
    return true;
  });

  // Open editor for new or existing question
  const openEditor = useCallback((question?: QuestionBankItem) => {
    if (question) {
      setSelectedQuestion({ ...question });
    } else {
      setSelectedQuestion({
        id: `local-${Date.now()}`,
        question_type: 'multiple_choice',
        text: '',
        options: ['', '', '', ''],
        correct_answer: null,
        rubric: null,
        points: 1,
        tags: [],
        difficulty: 'medium',
        estimated_time_minutes: 5,
        variables: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        is_synced: false,
      });
    }
    setShowEditor(true);
  }, []);

  const closeEditor = useCallback(() => {
    setShowEditor(false);
    setSelectedQuestion(null);
  }, []);

  return {
    questions: filteredQuestions,
    allQuestions: questions,
    allTags,
    loading,
    saving,
    syncing,
    filters,
    setFilters,
    selectedQuestion,
    showEditor,
    openEditor,
    closeEditor,
    saveQuestion,
    deleteQuestion,
    syncQuestions,
    loadQuestions,
  };
}