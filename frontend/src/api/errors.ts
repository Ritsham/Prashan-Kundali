import axios from 'axios';

export type ApiErrorShape = {
  code: string;
  message: string;
  requestId?: string;
  details?: unknown;
  status?: number;
};

export class ApiError extends Error {
  code: string;
  requestId?: string;
  details?: unknown;
  status?: number;

  constructor(error: ApiErrorShape) {
    super(error.message);
    this.name = 'ApiError';
    this.code = error.code;
    this.requestId = error.requestId;
    this.details = error.details;
    this.status = error.status;
  }
}

export function normalizeApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (axios.isAxiosError(error)) {
    const payload = error.response?.data as { error?: { code?: string; message?: string; request_id?: string; details?: unknown }; detail?: unknown } | undefined;
    const backendError = payload?.error;
    const detailMessage = typeof payload?.detail === 'string' ? payload.detail : undefined;
    return new ApiError({
      code: backendError?.code || (error.response?.status === 429 ? 'rate_limited' : 'request_failed'),
      message: backendError?.message || detailMessage || error.message || 'Request failed.',
      requestId: backendError?.request_id || error.response?.headers?.['x-request-id'],
      details: backendError?.details || payload?.detail,
      status: error.response?.status,
    });
  }
  if (error instanceof Error) {
    return new ApiError({ code: 'client_error', message: error.message });
  }
  return new ApiError({ code: 'client_error', message: 'Something went wrong.' });
}

export function apiErrorMessage(error: unknown): string {
  const normalized = normalizeApiError(error);
  if (normalized.status === 401) return 'Please sign in to continue.';
  if (normalized.status === 403) return 'You do not have permission to perform this action.';
  if (normalized.status === 429) return 'Too many attempts. Please wait a moment and try again.';
  return normalized.message;
}
