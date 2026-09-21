import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { apiClient } from '../api';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'student' | 'teacher' | 'parent';
  is_active: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (googleToken: string) => Promise<void>;
  loginWithPassword: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const response = await apiClient.get('/auth/me');
      setUser(response.data);
    } catch (error) {
      console.error("Failed to fetch user", error);
      localStorage.removeItem('access_token');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  const login = async (googleToken: string) => {
    try {
      const payload = { token: googleToken };
      const response = await apiClient.post('/auth/google', payload);
      localStorage.setItem('access_token', response.data.access_token);
      await fetchUser();
    } catch (error) {
      console.error("Login failed", error);
      throw error;
    }
  };

  const loginWithPassword = async (email: string, password: string) => {
    try {
      // Must use application/x-www-form-urlencoded for OAuth2PasswordRequestForm
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await apiClient.post('/auth/token', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      localStorage.setItem('access_token', response.data.access_token);
      await fetchUser();
    } catch (error: any) {
      console.error("Local login failed", error);
      throw new Error(error.response?.data?.detail || "Local login failed");
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, loginWithPassword, logout }}>
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
