import axios from 'axios';

// Create a base axios instance
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to attach auth token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('supabase_token'); // Or get from your auth state
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
