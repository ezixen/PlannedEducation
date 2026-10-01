import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { apiClient } from '../api';

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  phone_number: string | null;
  is_active: boolean;
  role: 'teacher' | 'student' | 'parent';
  totp_enabled: boolean;
  ai_provider?: string | null;
  ai_model_name?: string | null;
  ai_base_url?: string | null;
  ai_api_key_encrypted?: string | null;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (googleToken: string) => Promise<void>;
  loginWithPassword: (emailOrUsername: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem('access_token');
    console.log('refreshUser called, token:', token ? 'present' : 'missing');
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      console.log('Calling /auth/me...');
      const response = await apiClient.get<User>('/auth/me');
      console.log('/auth/me response:', response.data);
      setUser(response.data);
    } catch (error) {
      console.error('/auth/me error:', error);
      // Token is invalid or expired — clear it
      localStorage.removeItem('access_token');
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (googleToken: string) => {
    const response = await apiClient.post<{ access_token: string }>('/auth/google', { token: googleToken });
    localStorage.setItem('access_token', response.data.access_token);
    await refreshUser();
  };

  const loginWithPassword = async (emailOrUsername: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', emailOrUsername);
    formData.append('password', password);

    try {
      const response = await apiClient.post<{ access_token: string }>('/auth/token', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      console.log('Login response:', response.data);
      localStorage.setItem('access_token', response.data.access_token);
      console.log('Token stored, calling refreshUser...');
      await refreshUser();
      console.log('refreshUser completed, user:', JSON.stringify(null));
    } catch (error: any) {
      // Pass through the original error detail from the API
      const detail = error.response?.data?.detail || 'Login failed';
      throw new Error(detail);
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, loginWithPassword, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
