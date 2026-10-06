import axios from 'axios';

// Base API URL for FastAPI backend (defaults to port 8001 in dev)
let baseApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8001';
if (typeof window !== 'undefined') {
  if (window.location.hostname === '127.0.0.1' && baseApiUrl.includes('localhost')) {
    baseApiUrl = baseApiUrl.replace('localhost', '127.0.0.1');
  } else if (window.location.hostname === 'localhost' && baseApiUrl.includes('127.0.0.1')) {
    baseApiUrl = baseApiUrl.replace('127.0.0.1', 'localhost');
  }
}
export const API_URL = baseApiUrl;

export const apiClient = axios.create({
  baseURL: API_URL,
});

// Automatically inject JWT token into requests if available
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

