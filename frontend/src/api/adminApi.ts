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
  [key: string]: number | string | undefined;
}

export interface AdminAstrologerApplication {
  id: string;
  user_id?: string;
  name: string;
  email?: string;
  phone?: string;
  experience?: number | string;
  expertise?: string;
  bio?: string;
  additional_information?: string;
  state?: string;
  country?: string;
  status: string;
  proofs?: Array<{
    id?: string;
    type?: string;
    url?: string;
    filename?: string;
    mime_type?: string;
  }>;
  created_at?: string;
}

export interface AdminAuditLog {
  id?: string;
  actor_user_id?: string;
  entity_type: string;
  entity_id: string;
  action: string;
  before_json?: Record<string, unknown> | null;
  after_json?: Record<string, unknown> | null;
  created_at?: string;
}

export interface AstrologerApplicationUpdate {
  status: 'approved' | 'rejected' | 'pending' | 'needs_more_information' | 'suspended';
  message?: string;
  reapply_allowed?: boolean;
  reapply_after_days?: number;
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
  payment_status?: string;
  quoted_price?: number | null;
  amount?: number | null;
  currency?: string;
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
    const response = await apiClient.get('/api/admin/metrics');
    return response.data as AdminMetrics;
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
  },

  getAstrologerApplications: async () => {
    const response = await apiClient.get('/api/admin/astrologers/applications');
    return response.data as { applications: AdminAstrologerApplication[] };
  },

  updateAstrologerApplication: async (applicationId: string, updateData: AstrologerApplicationUpdate) => {
    const response = await apiClient.post(
      `/api/admin/astrologers/applications/${encodeURIComponent(applicationId)}`,
      updateData,
    );
    return response.data as { status?: string; message?: string };
  },

  getAuditLogs: async (params?: { limit?: number; entity_type?: string }) => {
    const response = await apiClient.get('/api/admin/audit-logs', { params });
    return response.data as { logs: AdminAuditLog[] };
  }
};
