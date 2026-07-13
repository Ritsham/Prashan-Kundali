export const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
export const PHONE_RE = /^\+?[0-9 ()-]{6,24}$/;
export const ID_RE = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/;

export function isIsoDate(value?: string | null): boolean {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

export function isTime(value?: string | null): boolean {
  return Boolean(value && /^\d{2}:\d{2}(:\d{2})?$/.test(value));
}

export function validCoordinate(latitude?: number | null, longitude?: number | null): boolean {
  return (
    typeof latitude === 'number' &&
    Number.isFinite(latitude) &&
    latitude >= -90 &&
    latitude <= 90 &&
    typeof longitude === 'number' &&
    Number.isFinite(longitude) &&
    longitude >= -180 &&
    longitude <= 180
  );
}

export function boundedText(value: string | undefined | null, min: number, max: number): boolean {
  const length = (value || '').trim().length;
  return length >= min && length <= max;
}
