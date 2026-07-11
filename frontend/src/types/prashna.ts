import type { ChartData as ConsultationChartData, InterpretationData } from '../features/consultation/types';

export interface Location {
  latitude: number;
  longitude: number;
  place_name: string;
}

export interface PrashnaPayload {
  name: string;
  question: string;
  location: Location;
  question_domain?: string;
  question_subdomain?: string;
  asked_at_utc?: string;
}

export interface ChartData {
  // Backward-compatible alias for the existing Prashna chart payload.
  [key: string]: unknown;
}

export type PrashnaChartData = ConsultationChartData;

export interface PrashnaResponse {
  chart_id?: string;
  chart: PrashnaChartData;
  interpretation?: InterpretationData;
  status?: string;
}
