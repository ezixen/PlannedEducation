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
  role: 'teacher' | 'student' | 'parent' | 'admin' | 'superadmin' | 'teacher_aide';
  is_admin: boolean;
  totp_enabled: boolean;
  teacher_approved?: boolean;
  is_teacher_aide?: boolean;
  allow_student_dms?: boolean;
  is_visible_in_teacher_dm?: boolean;
  ai_provider?: string | null;
  ai_model_name?: string | null;
  ai_base_url?: string | null;
  ai_api_key_encrypted?: string | null;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  loginWithPassword: (
    emailOrUsername: string,
    password: string,
    rememberMe?: boolean,
    totpCode?: string,
  ) => Promise<void>;
  loginWithPasskeyTokens: (accessToken: string, refreshToken?: string | null) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    // F-028: Perform one-time migration of any legacy localStorage access_token into
    // sessionStorage, then immediately purge localStorage so bearer tokens never
    // persist across browser sessions or survive logout.
    const legacyToken = localStorage.getItem('access_token');
    if (legacyToken && !sessionStorage.getItem('access_token')) {
      sessionStorage.setItem('access_token', legacyToken);
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');

    const token = sessionStorage.getItem('access_token');
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const response = await apiClient.get<User>('/auth/me');
      setUser(response.data);
    } catch {
      // Token is invalid or expired — clear it
      sessionStorage.removeItem('access_token');
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const loginWithPassword = async (
    emailOrUsername: string,
    password: string,
    rememberMe: boolean = false,
    totpCode?: string,
  ) => {
    const formData = new URLSearchParams();
    formData.append('username', emailOrUsername);
    formData.append('password', password);
    formData.append('remember_me', rememberMe.toString());
    if (totpCode?.trim()) {
      formData.append('totp_code', totpCode.trim());
    }

    try {
      const response = await apiClient.post<{ access_token: string; refresh_token?: string }>('/auth/token', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      sessionStorage.setItem('access_token', response.data.access_token);
      if (response.data.refresh_token) {
        sessionStorage.setItem('refresh_token', response.data.refresh_token);
      }
      await refreshUser();
    } catch (error: any) {
      // Pass through the original error detail from the API
      const detail = error.response?.data?.detail || 'Login failed';
      throw new Error(detail);
    }
  };

  const loginWithPasskeyTokens = async (
    accessToken: string,
    refreshToken?: string | null,
  ) => {
    sessionStorage.setItem('access_token', accessToken);
    if (refreshToken) {
      sessionStorage.setItem('refresh_token', refreshToken);
    }
    await refreshUser();
  };

  const logout = async () => {
    const accessToken = sessionStorage.getItem('access_token');
    const refreshToken = sessionStorage.getItem('refresh_token');
    if (accessToken) {
      try {
        await apiClient.post(
          '/auth/logout',
          refreshToken ? { refresh_token: refreshToken } : {},
        );
      } catch {
        // Local clear still proceeds if the revoke call fails.
      }
    }
    // F-028: clear tokens from both storages to prevent stale localStorage tokens
    // from being silently re-loaded on the next mount.
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, loginWithPassword, loginWithPasskeyTokens, logout, refreshUser }}
    >
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
