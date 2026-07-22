export type ConsultationSourceType = 'prashna' | 'direct_consultation' | 'matchmaking';

export type ConsultationChartType = 'prashna' | 'lagna' | 'matchmaking';

export type ConsultationStatus =
  | 'requested'
  | 'pending_payment'
  | 'confirmed'
  | 'active'
  | 'refunded'
  | 'pending'
  | 'reviewed'
  | 'accepted'
  | 'scheduled'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'rejected'
  | 'waiting_queue';

export interface PlanetaryPosition {
  name: string;
  longitude?: number;
  sign?: string;
  sign_index?: number;
  house?: number | string;
  formatted_degree?: string;
  nakshatra?: string;
  pada?: number | string;
  retrograde?: boolean;
  [key: string]: unknown;
}

export type ChartSignMap = Record<string, string[]>;

export interface ChartData {
  id?: string;
  meta?: Record<string, unknown>;
  question?: Record<string, unknown>;
  lagna?: Record<string, unknown>;
  signs?: ChartSignMap;
  planets?: PlanetaryPosition[];
  kp_system?: Record<string, unknown>;
  dashas?: DashaData;
  divisional_charts?: Record<string, ChartSignMap>;
  transit?: Record<string, unknown>;
  interpretation?: InterpretationData;
  [key: string]: unknown;
}

export type DashaData = Record<string, unknown>;

export type InterpretationData =
  | string
  | {
      title?: string;
      domain?: string;
      confidence?: string;
      verdict?: Record<string, unknown>;
      answer?: {
        text?: string;
        mode?: string;
        provider?: string;
        model?: string;
        note?: string;
        [key: string]: unknown;
      };
      [key: string]: unknown;
    };

export interface AstrologySnapshot {
  chart_id?: string;
  chart_type: ConsultationChartType;
  chart?: ChartData;
  interpretation?: InterpretationData;
  divisional_charts?: Record<string, ChartSignMap>;
  planetary_positions?: PlanetaryPosition[];
  house_positions?: Record<string, unknown> | unknown[];
  aspects?: Record<string, unknown> | unknown[];
  yogas?: Record<string, unknown> | unknown[];
  dashas?: DashaData;
  kp_system?: Record<string, unknown>;
  calculation_metadata?: Record<string, unknown>;
  question_context?: Record<string, unknown>;
  source_result?: Record<string, unknown>;
  additional_calculations?: Record<string, unknown>;
}

export interface UserConsultationDetails {
  full_name: string;
  email: string;
  mobile_number: string;
  gender?: string;
  date_of_birth?: string;
  time_of_birth?: string;
  place?: string;
  latitude?: number | null;
  longitude?: number | null;
  timezone?: string;
}

export interface ConsultationDetails {
  question: string;
  additional_message?: string;
  preferred_date?: string;
  preferred_time?: string;
  consultation_mode?: string;
  payment_status?: string;
  quoted_price?: number | null;
  currency?: string;
}

export interface ConsultationCasePayload {
  source_type: ConsultationSourceType;
  chart_type: ConsultationChartType;
  user: UserConsultationDetails;
  consultation: ConsultationDetails;
  astrology_snapshot: AstrologySnapshot;
  idempotency_key?: string;
}

export interface ConsultationCase extends ConsultationCasePayload {
  id?: string;
  case_id: string;
  user_id?: string | null;
  case_status: ConsultationStatus;
  status?: ConsultationStatus;
  source_type: ConsultationSourceType;
  chart_type: ConsultationChartType;
  name?: string;
  phone?: string;
  email?: string;
  date_of_birth?: string;
  time_of_birth?: string;
  place_of_birth?: string;
  topic?: string;
  question?: string;
  preferred_date?: string;
  preferred_time?: string;
  consultation_mode?: string;
  additional_message?: string | null;
  chart_snapshot?: AstrologySnapshot | null;
  astrological_snapshot?: AstrologySnapshot | null;
  booking_status?: string;
  admin_notes?: string | null;
  assigned_astrologer?: string | null;
  meeting_link?: string | null;
  scheduled_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConsultationCaseAdminUpdate {
  case_status?: ConsultationStatus;
  admin_notes?: string;
  assigned_astrologer?: string;
  meeting_link?: string;
  scheduled_at?: string;
}
