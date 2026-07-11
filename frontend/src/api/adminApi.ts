import { apiClient } from './client';
import type {
  AstrologySnapshot,
  ConsultationCase,
  ConsultationCaseAdminUpdate,
  ConsultationChartType,
  ConsultationSourceType,
  ConsultationStatus,
} from '../features/consultation/types';

export interface AdminMetrics {
  total_users?: number;
  active_consultations?: number;
  completed_consultations?: number;
  revenue?: number;
}

export interface ConsultationRequest {
  id: string;
  case_id?: string;
  case_status?: ConsultationStatus;
  source_type?: ConsultationSourceType;
  chart_type?: ConsultationChartType;
  name: string;
  phone: string;
  email: string;
  date_of_birth: string;
  time_of_birth: string;
  place_of_birth: string;
  topic: string;
  question: string;
  preferred_date?: string;
  preferred_time?: string;
  consultation_mode?: string;
  additional_message?: string;
  status: ConsultationStatus;
  admin_notes?: string | null;
  meeting_link?: string | null;
  scheduled_at?: string | null;
  created_at: string;
  updated_at?: string;
  astrological_snapshot?: AstrologySnapshot | null;
  chart_snapshot?: AstrologySnapshot | null;
}

export const adminApi = {
  getMetrics: async () => {
    // In a real app we'd need auth headers or a cookie, 
    // assuming apiClient is configured to send them or the backend relies on a session cookie.
    const response = await apiClient.get('/api/admin/metrics');
    return response.data;
  },
  
  getConsultationRequests: async () => {
    const response = await apiClient.get('/api/admin/consultations/requests');
    return response.data;
  },

  updateConsultationStatus: async (id: string, updateData: { status: string; meeting_link?: string }) => {
    const response = await apiClient.put(`/api/admin/consultations/requests/${id}`, updateData);
    return response.data;
  },

  getConsultationCases: async (params?: {
    status?: ConsultationStatus;
    source_type?: ConsultationSourceType;
    chart_type?: ConsultationChartType;
    date?: string;
    user_name?: string;
    case_id?: string;
  }) => {
    const response = await apiClient.get('/api/admin/consultation-cases', { params });
    return response.data as { cases: ConsultationCase[] };
  },

  getConsultationCase: async (caseId: string) => {
    const response = await apiClient.get(`/api/admin/consultation-cases/${encodeURIComponent(caseId)}`);
    return response.data as { case: ConsultationCase };
  },

  updateConsultationCase: async (caseId: string, updateData: ConsultationCaseAdminUpdate) => {
    const response = await apiClient.patch(`/api/admin/consultation-cases/${encodeURIComponent(caseId)}`, updateData);
    return response.data as { case: ConsultationCase; promoted_case?: ConsultationCase | null };
  }
};
