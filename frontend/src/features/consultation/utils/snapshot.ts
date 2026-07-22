import type {
  AstrologySnapshot,
  ChartData,
  ConsultationCasePayload,
  ConsultationChartType,
  ConsultationSourceType,
  UserConsultationDetails,
} from '../types';

type ExistingPrashnaResult = {
  chart_id?: string;
  chart?: ChartData;
  interpretation?: ChartData['interpretation'];
  [key: string]: unknown;
};

type ExistingLocation = {
  latitude?: number | string | null;
  longitude?: number | string | null;
  place_name?: string;
};

export type ExistingPrashnaFormData = {
  name?: string;
  question?: string;
  location?: ExistingLocation;
  [key: string]: unknown;
};

export type ExistingBookingFormData = {
  name?: string;
  phone?: string;
  email?: string;
  date_of_birth?: string;
  time_of_birth?: string;
  place_of_birth?: string;
  latitude?: number | null;
  longitude?: number | null;
  topic?: string;
  question?: string;
  gender?: string;
  preferred_date?: string;
  preferred_time?: string;
  consultation_mode?: string;
  payment_status?: string;
  quoted_price?: number | null;
  currency?: string;
  additional_message?: string;
  chart_snapshot?: unknown;
};

const numberOrNull = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

export const buildAstrologySnapshot = (
  sourceResult: ExistingPrashnaResult | ChartData | null | undefined,
  chartType: ConsultationChartType,
): AstrologySnapshot => {
  const result = (sourceResult || {}) as ExistingPrashnaResult;
  const chart = (result.chart || sourceResult || {}) as ChartData;
  const interpretation = result.interpretation || chart.interpretation;

  return {
    chart_id: result.chart_id || chart.id,
    chart_type: chartType,
    chart,
    interpretation,
    divisional_charts: chart.divisional_charts,
    planetary_positions: chart.planets,
    house_positions: chart.houses as AstrologySnapshot['house_positions'],
    aspects: chart.aspects as AstrologySnapshot['aspects'],
    yogas: chart.yogas as AstrologySnapshot['yogas'],
    dashas: chart.dashas,
    kp_system: chart.kp_system,
    calculation_metadata: chart.meta,
    question_context: chart.question,
    source_result: result,
    additional_calculations: {
      transit: chart.transit,
    },
  };
};

export const buildPrashnaConsultationPayload = (params: {
  result: ExistingPrashnaResult;
  formData: ExistingPrashnaFormData;
  user: Partial<UserConsultationDetails>;
  additional_message?: string;
  preferred_date?: string;
  preferred_time?: string;
  consultation_mode?: string;
  payment_status?: string;
  quoted_price?: number | null;
  currency?: string;
  idempotency_key?: string;
}): ConsultationCasePayload => {
  const { result, formData, user } = params;
  const location = formData.location || {};

  return {
    source_type: 'prashna',
    chart_type: 'prashna',
    user: {
      full_name: user.full_name || formData.name || '',
      email: user.email || '',
      mobile_number: user.mobile_number || '',
      gender: user.gender,
      date_of_birth: user.date_of_birth,
      time_of_birth: user.time_of_birth,
      place: user.place || location.place_name,
      latitude: user.latitude ?? numberOrNull(location.latitude),
      longitude: user.longitude ?? numberOrNull(location.longitude),
      timezone: user.timezone || (result.chart?.question?.timezone as string | undefined),
    },
    consultation: {
      question: formData.question || '',
      additional_message: params.additional_message,
      preferred_date: params.preferred_date,
      preferred_time: params.preferred_time,
      consultation_mode: params.consultation_mode,
      payment_status: params.payment_status,
      quoted_price: params.quoted_price,
      currency: params.currency || 'INR',
    },
    astrology_snapshot: buildAstrologySnapshot(result, 'prashna'),
    idempotency_key: params.idempotency_key,
  };
};

export const buildDirectConsultationPayload = (params: {
  formData: ExistingBookingFormData;
  source_type?: ConsultationSourceType;
  chart_type?: ConsultationChartType;
  astrologyResult?: ExistingPrashnaResult | ChartData | null;
  idempotency_key?: string;
}): ConsultationCasePayload => {
  const { formData } = params;
  const chartType = params.chart_type || (formData.topic === 'Prashna' ? 'prashna' : 'lagna');
  const sourceType = params.source_type || 'direct_consultation';

  return {
    source_type: sourceType,
    chart_type: chartType,
    user: {
      full_name: formData.name || '',
      email: formData.email || '',
      mobile_number: formData.phone || '',
      gender: formData.gender || undefined,
      date_of_birth: formData.date_of_birth,
      time_of_birth: formData.time_of_birth,
      place: formData.place_of_birth,
      latitude: formData.latitude ?? null,
      longitude: formData.longitude ?? null,
    },
    consultation: {
      question: formData.question || '',
      additional_message: formData.additional_message,
      preferred_date: formData.preferred_date,
      preferred_time: formData.preferred_time,
      consultation_mode: formData.consultation_mode,
      payment_status: formData.payment_status,
      quoted_price: formData.quoted_price,
      currency: formData.currency || 'INR',
    },
    astrology_snapshot: buildAstrologySnapshot(
      params.astrologyResult || (formData.chart_snapshot as ExistingPrashnaResult | ChartData | null),
      chartType,
    ),
    idempotency_key: params.idempotency_key,
  };
};
