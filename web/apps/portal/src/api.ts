import axios from 'axios';

// Base API URL for FastAPI backend (defaults to same-origin /api in production)
let baseApiUrl = import.meta.env.VITE_API_URL || '/api';
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

function readAccessToken(): string | null {
  // AuthContext writes to sessionStorage; some older flows also used localStorage.
  return sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
}

function clearAccessTokens(): void {
  sessionStorage.removeItem('access_token');
  localStorage.removeItem('access_token');
}

// Automatically inject JWT token into requests if available
apiClient.interceptors.request.use((config) => {
  const token = readAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});


// Intercept 401s to clear stale access tokens and avoid repetitive unauthorized requests
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      if (readAccessToken()) {
        clearAccessTokens();
      }
    }
    return Promise.reject(error);
  }
);
