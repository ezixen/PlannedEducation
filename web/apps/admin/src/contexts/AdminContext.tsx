import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { apiClient } from '../api';

export interface AdminStats {
  totalUsers: number;
  totalExams: number;
  totalSubmissions: number;
  activeExams: number;
}

export interface AdminUser {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  role: 'teacher' | 'student' | 'parent';
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface AdminExam {
  id: string;
  title: string;
  teacher_id: string;
  teacher_name: string;
  question_count: number;
  submission_count: number;
  is_published: boolean;
  created_at: string;
}

interface AdminContextType {
  stats: AdminStats | null;
  users: AdminUser[];
  exams: AdminExam[];
  loading: boolean;
  error: string | null;
  fetchStats: () => Promise<void>;
  fetchUsers: () => Promise<void>;
  fetchExams: () => Promise<void>;
  toggleUserActive: (userId: string, isActive: boolean) => Promise<void>;
  deleteUser: (userId: string) => Promise<void>;
  deleteExam: (examId: string) => Promise<void>;
}

const AdminContext = createContext<AdminContextType | undefined>(undefined);

export function AdminProvider({ children }: { children: ReactNode }) {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [exams, setExams] = useState<AdminExam[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get<AdminStats>('/admin/stats');
      setStats(response.data);
    } catch (err: any) {
      setError('Failed to fetch stats: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get<AdminUser[]>('/admin/users');
      setUsers(response.data);
    } catch (err: any) {
      setError('Failed to fetch users: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchExams = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get<AdminExam[]>('/admin/exams');
      setExams(response.data);
    } catch (err: any) {
      setError('Failed to fetch exams: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }, []);

  const toggleUserActive = useCallback(async (userId: string, isActive: boolean) => {
    try {
      await apiClient.patch(`/admin/users/${userId}`, { is_active: isActive });
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, is_active: isActive } : u));
    } catch (err: any) {
      setError('Failed to update user: ' + (err.response?.data?.detail || err.message));
      throw err;
    }
  }, []);

  const deleteUser = useCallback(async (userId: string) => {
    try {
      await apiClient.delete(`/admin/users/${userId}`);
      setUsers(prev => prev.filter(u => u.id !== userId));
    } catch (err: any) {
      setError('Failed to delete user: ' + (err.response?.data?.detail || err.message));
      throw err;
    }
  }, []);

  const deleteExam = useCallback(async (examId: string) => {
    try {
      await apiClient.delete(`/admin/exams/${examId}`);
      setExams(prev => prev.filter(e => e.id !== examId));
    } catch (err: any) {
      setError('Failed to delete exam: ' + (err.response?.data?.detail || err.message));
      throw err;
    }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchUsers();
    fetchExams();
  }, [fetchStats, fetchUsers, fetchExams]);

  return (
    <AdminContext.Provider value={{
      stats,
      users,
      exams,
      loading,
      error,
      fetchStats,
      fetchUsers,
      fetchExams,
      toggleUserActive,
      deleteUser,
      deleteExam,
    }}>
      {children}
    </AdminContext.Provider>
  );
}

export function useAdmin() {
  const context = useContext(AdminContext);
  if (context === undefined) {
    throw new Error('useAdmin must be used within an AdminProvider');
  }
  return context;
}