import { apiClient } from './client';
import type { ConsultationCase, ConsultationCasePayload } from '../features/consultation/types';

export interface BookingPayload {
  name: string;
  phone: string;
  email: string;
  date_of_birth: string;
  time_of_birth: string;
  place_of_birth: string;
  latitude: number | null;
  longitude: number | null;
  topic: string;
  question: string;
  gender?: string;
  preferred_date?: string;
  preferred_time?: string;
  consultation_mode?: string;
  additional_message?: string;
  payment_status?: string;
  chart_snapshot?: ConsultationCasePayload['astrology_snapshot'] | Record<string, unknown> | null;
}

export type { ConsultationCase, ConsultationCasePayload };

export const bookingApi = {
  createConsultationCase: async (payload: ConsultationCasePayload) => {
    const response = await apiClient.post('/api/consultation-cases', payload);
    return response.data as { case: ConsultationCase; slot_available: boolean; message: string; duplicate?: boolean };
  },

  createConsultationRequest: async (payload: BookingPayload) => {
    const response = await apiClient.post('/api/consultation/request', payload);
    return response.data;
  },
  
  getConsultantProfile: async () => {
    const response = await apiClient.get('/api/consultation/profile');
    return response.data;
  },
  
  getQueueStatus: async () => {
    const response = await apiClient.get('/api/consultation/request-status');
    return response.data;
  },

  getRequestStatus: async (requestId: string) => {
    const response = await apiClient.get(`/api/consultation/request/${encodeURIComponent(requestId)}`);
    return response.data;
  },

  getConsultationCase: async (caseId: string) => {
    const response = await apiClient.get(`/api/consultation-cases/${encodeURIComponent(caseId)}`);
    return response.data as { case: ConsultationCase };
  }
};
