import axios from 'axios';
import { publicEnv } from '../config/env';
import { getStoredSession } from '../auth/supabaseAuth';
import { normalizeApiError } from './errors';

// Create a base axios instance
export const apiClient = axios.create({
  baseURL: publicEnv.apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to attach auth token
apiClient.interceptors.request.use((config) => {
  const token = getStoredSession()?.access_token;
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (config.headers && !config.headers['x-request-id']) {
    const requestId =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
    config.headers['x-request-id'] = `web_${requestId}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(normalizeApiError(error)),
);
