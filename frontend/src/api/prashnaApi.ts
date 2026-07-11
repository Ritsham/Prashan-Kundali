import { apiClient } from './client';
import type { PrashnaPayload, PrashnaResponse } from '../types/prashna';

export const prashnaApi = {
  generatePrashna: async (payload: PrashnaPayload): Promise<PrashnaResponse> => {
    const response = await apiClient.post('/api/prashna', payload);
    return response.data;
  },
  
  geocodePlace: async (query: string): Promise<any> => {
    const response = await apiClient.get(`/api/geocode?query=${encodeURIComponent(query)}&limit=6`);
    return response.data;
  }
};
