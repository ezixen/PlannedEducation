import axios from 'axios';

// Base API URL for FastAPI backend (defaults to port 8000 in dev)
let baseApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
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

// Automatic fallback between port 8000 and 8002 in local dev if connection fails
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (!originalRequest || (originalRequest as any)._portRetry) {
      return Promise.reject(error);
    }

    const currentBase = apiClient.defaults.baseURL || API_URL;
    const isLocal = currentBase.includes('localhost') || currentBase.includes('127.0.0.1');
    const isNetworkError = !error.response && (error.code === 'ERR_NETWORK' || !error.status);

    if (isLocal && isNetworkError) {
      let altBase: string | null = null;
      if (currentBase.includes(':8000')) {
        altBase = currentBase.replace(':8000', ':8002');
      } else if (currentBase.includes(':8002')) {
        altBase = currentBase.replace(':8002', ':8000');
      }

      if (altBase) {
        (originalRequest as any)._portRetry = true;
        originalRequest.baseURL = altBase;
        try {
          const res = await axios(originalRequest);
          apiClient.defaults.baseURL = altBase;
          return res;
        } catch {
          // If fallback port also fails, return original error
        }
      }
    }
    return Promise.reject(error);
  }
);

