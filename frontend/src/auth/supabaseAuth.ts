import { publicEnv } from '../config/env';

type SupabaseConfig = {
  supabaseUrl: string;
  supabaseAnonKey: string;
};

export type AuthSession = {
  access_token: string;
  refresh_token?: string;
  expires_at?: number;
  started_at?: number;
  user?: {
    id?: string;
    email?: string;
    role?: 'user' | 'astrologer_pending' | 'astrologer_verified' | 'admin';
    user_metadata?: Record<string, unknown>;
    profile?: Record<string, unknown>;
    profile_exists?: boolean;
  };
};

type GoogleAuthIntent = 'sign_in' | 'sign_up';

export type PendingSignupProfile = {
  fullName: string;
  mobileNumber: string;
};

const ACCESS_TOKEN_KEY = 'supabase_token';
const REFRESH_TOKEN_KEY = 'supabase_refresh_token';
const EXPIRES_AT_KEY = 'supabase_expires_at';
const USER_KEY = 'supabase_user';
const GOOGLE_OAUTH_STATE_KEY = 'supabase_google_oauth_state';
const GOOGLE_AUTH_INTENT_KEY = 'supabase_google_auth_intent';
const PENDING_SIGNUP_PROFILE_KEY = 'kundali_pending_signup_profile';
const SESSION_LAST_SEEN_AT_KEY = 'kundali_session_last_seen_at';
const MAX_SESSION_AGE_SECONDS = 30 * 24 * 60 * 60;

let cachedConfig: SupabaseConfig | null = null;

async function getConfig(): Promise<SupabaseConfig> {
  if (cachedConfig) return cachedConfig;

  if (publicEnv.supabaseUrl && publicEnv.supabaseAnonKey) {
    cachedConfig = {
      supabaseUrl: publicEnv.supabaseUrl,
      supabaseAnonKey: publicEnv.supabaseAnonKey,
    };
    return cachedConfig;
  }

  const response = await fetch(`${publicEnv.apiBaseUrl}/api/config`);
  if (!response.ok) throw new Error('Unable to load Supabase configuration.');
  const config = await response.json();
  if (!config.supabaseUrl || !config.supabaseAnonKey) {
    throw new Error('Supabase configuration is missing.');
  }
  cachedConfig = {
    supabaseUrl: config.supabaseUrl.replace(/\/$/, ''),
    supabaseAnonKey: config.supabaseAnonKey,
  };
  return cachedConfig;
}

function getSessionLastSeenAt(): number | undefined {
  const lastSeenAt = Number(localStorage.getItem(SESSION_LAST_SEEN_AT_KEY) || 0) || undefined;
  return lastSeenAt || Number(localStorage.getItem('kundali_session_started_at') || 0) || undefined;
}

function isSessionTooOld(lastSeenAt?: number): boolean {
  if (!lastSeenAt) return false;
  const now = Math.floor(Date.now() / 1000);
  return now - lastSeenAt >= MAX_SESSION_AGE_SECONDS;
}

function persistSession(session: AuthSession, options: { markAuthenticated?: boolean } = {}) {
  const lastSeenAt = Math.floor(Date.now() / 1000);
  localStorage.setItem(ACCESS_TOKEN_KEY, session.access_token);
  if (session.refresh_token) localStorage.setItem(REFRESH_TOKEN_KEY, session.refresh_token);
  if (session.expires_at) localStorage.setItem(EXPIRES_AT_KEY, String(session.expires_at));
  localStorage.setItem(SESSION_LAST_SEEN_AT_KEY, String(lastSeenAt));
  localStorage.removeItem('kundali_session_started_at');
  if (session.user) localStorage.setItem(USER_KEY, JSON.stringify(session.user));
  session.started_at = options.markAuthenticated ? lastSeenAt : session.started_at || lastSeenAt;
}

function createStateToken(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
}

function getAuthRedirectUrl(): string {
  const url = new URL(window.location.href);
  url.hash = '';
  return url.toString();
}

export async function enrichSessionWithBackendUser(session: AuthSession): Promise<AuthSession> {
  if (!session.access_token) return session;
  const response = await fetch(`${publicEnv.apiBaseUrl}/api/auth/me`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
  });
  if (!response.ok) return session;
  const data = await response.json();
  const user = data.user || {};
  const enriched = {
    ...session,
    user: {
      ...(session.user || {}),
      id: user.id || session.user?.id,
      email: user.email || session.user?.email,
      role: user.role || session.user?.role || 'user',
      user_metadata: user.metadata || session.user?.user_metadata,
      profile: user.profile || session.user?.profile,
      profile_exists: Boolean(user.profile_exists),
    },
  };
  persistSession(enriched);
  return enriched;
}

export function clearStoredSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(EXPIRES_AT_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(SESSION_LAST_SEEN_AT_KEY);
  localStorage.removeItem('kundali_session_started_at');
  localStorage.removeItem(GOOGLE_AUTH_INTENT_KEY);
  localStorage.removeItem(PENDING_SIGNUP_PROFILE_KEY);
}

export function getStoredSession(): AuthSession | null {
  let accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
  let userJson = localStorage.getItem(USER_KEY);
  let user: AuthSession['user'];
  let refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY) || undefined;
  let expiresAt = Number(localStorage.getItem(EXPIRES_AT_KEY) || 0) || undefined;

  if (!accessToken) {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('sb-') && key.endsWith('-auth-token')) {
        try {
          const raw = localStorage.getItem(key);
          if (raw) {
            const parsed = JSON.parse(raw);
            accessToken = parsed.access_token || parsed.currentSession?.access_token;
            refreshToken = parsed.refresh_token || parsed.currentSession?.refresh_token;
            expiresAt = parsed.expires_at || parsed.currentSession?.expires_at;
            user = parsed.user || parsed.currentSession?.user;
          }
        } catch {}
      }
    }
  }

  if (!accessToken) return null;
  const lastSeenAt = getSessionLastSeenAt();
  if (isSessionTooOld(lastSeenAt)) {
    clearStoredSession();
    return null;
  }
  localStorage.setItem(SESSION_LAST_SEEN_AT_KEY, String(Math.floor(Date.now() / 1000)));
  if (!user && userJson) {
    try {
      user = JSON.parse(userJson);
    } catch {
      user = undefined;
    }
  }
  return {
    access_token: accessToken,
    refresh_token: refreshToken,
    expires_at: expiresAt,
    started_at: lastSeenAt,
    user,
  };
}

export function getPendingSignupProfile(): PendingSignupProfile | null {
  const raw = localStorage.getItem(PENDING_SIGNUP_PROFILE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    const fullName = String(parsed.fullName || '').trim();
    const mobileNumber = String(parsed.mobileNumber || '').trim();
    if (!fullName || !mobileNumber) return null;
    return { fullName, mobileNumber };
  } catch {
    return null;
  }
}

function clearPendingSignupProfile() {
  localStorage.removeItem(PENDING_SIGNUP_PROFILE_KEY);
}

export async function consumeOAuthCallback(): Promise<AuthSession | null> {
  if (typeof window === 'undefined' || !window.location.hash.includes('access_token=')) {
    return null;
  }

  const hash = new URLSearchParams(window.location.hash.slice(1));
  const accessToken = hash.get('access_token') || '';
  if (!accessToken) return getStoredSession();

  const returnedState = hash.get('state') || '';
  const expectedState = localStorage.getItem(GOOGLE_OAUTH_STATE_KEY) || '';
  localStorage.removeItem(GOOGLE_OAUTH_STATE_KEY);
  if (expectedState && returnedState && expectedState !== returnedState) {
    clearStoredSession();
    throw new Error('Google sign in could not be verified. Please try again.');
  }

  const expiresIn = Number(hash.get('expires_in') || 3600);
  const session: AuthSession = {
    access_token: accessToken,
    refresh_token: hash.get('refresh_token') || undefined,
    expires_at: Math.floor(Date.now() / 1000) + expiresIn,
  };
  persistSession(session, { markAuthenticated: true });
  window.history.replaceState(null, document.title, `${window.location.pathname}${window.location.search}`);
  const enriched = await enrichSessionWithBackendUser(session);
  if (localStorage.getItem(GOOGLE_AUTH_INTENT_KEY) === 'sign_up') {
    if (enriched.user?.profile_exists) {
      clearPendingSignupProfile();
      localStorage.removeItem(GOOGLE_AUTH_INTENT_KEY);
      return enriched;
    }
    const pendingProfile = getPendingSignupProfile();
    if (pendingProfile) {
      try {
        const completed = await completeUserProfile(enriched, pendingProfile.fullName, pendingProfile.mobileNumber);
        clearPendingSignupProfile();
        localStorage.removeItem(GOOGLE_AUTH_INTENT_KEY);
        return completed;
      } catch (error) {
        clearStoredSession();
        throw error;
      }
    }
  }
  localStorage.removeItem(GOOGLE_AUTH_INTENT_KEY);
  clearPendingSignupProfile();
  return enriched;
}

export async function signInWithGoogle(
  intent: GoogleAuthIntent = 'sign_in',
  profile?: PendingSignupProfile,
): Promise<void> {
  const config = await getConfig();
  const state = createStateToken();
  localStorage.setItem(GOOGLE_OAUTH_STATE_KEY, state);
  localStorage.setItem(GOOGLE_AUTH_INTENT_KEY, intent);
  if (intent === 'sign_up' && profile) {
    localStorage.setItem(PENDING_SIGNUP_PROFILE_KEY, JSON.stringify({
      fullName: profile.fullName.trim(),
      mobileNumber: profile.mobileNumber.trim(),
    }));
  } else {
    clearPendingSignupProfile();
  }
  const url = new URL('/auth/v1/authorize', config.supabaseUrl);
  url.searchParams.set('provider', 'google');
  url.searchParams.set('redirect_to', getAuthRedirectUrl());
  url.searchParams.set('state', state);
  window.location.assign(url.toString());
}

export async function completeUserProfile(session: AuthSession, name: string, mobileNumber: string): Promise<AuthSession> {
  if (!session.access_token) throw new Error('Authentication required.');
  const email = session.user?.email || '';
  if (!email) throw new Error('Unable to read your Google email. Please sign in again.');
  const response = await fetch(`${publicEnv.apiBaseUrl}/api/users/sync`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${session.access_token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email,
      name: name.trim(),
      mobile_number: mobileNumber.trim(),
    }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    const message = typeof detail === 'string' ? detail : detail?.message;
    throw new Error(message || data.message || 'Unable to save your profile.');
  }
  return enrichSessionWithBackendUser(session);
}

async function authFetch(path: string, init: RequestInit = {}) {
  const config = await getConfig();
  const response = await fetch(`${config.supabaseUrl}/auth/v1${path}`, {
    ...init,
    headers: {
      apikey: config.supabaseAnonKey,
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error_description || data.msg || data.message || 'Authentication failed.');
  }
  return data;
}

function normalizeSession(data: any): AuthSession {
  const expiresIn = Number(data.expires_in || 3600);
  return {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_at: Math.floor(Date.now() / 1000) + expiresIn,
    user: data.user,
  };
}

export async function signInWithPassword(email: string, password: string): Promise<AuthSession> {
  const data = await authFetch('/token?grant_type=password', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  const session = normalizeSession(data);
  persistSession(session, { markAuthenticated: true });
  return enrichSessionWithBackendUser(session);
}

export async function signUpWithPassword(email: string, password: string, fullName: string): Promise<AuthSession | null> {
  const data = await authFetch('/signup', {
    method: 'POST',
    body: JSON.stringify({
      email,
      password,
      data: { full_name: fullName },
    }),
  });
  if (!data.access_token) return null;
  const session = normalizeSession(data);
  persistSession(session, { markAuthenticated: true });
  return enrichSessionWithBackendUser(session);
}

export async function refreshSession(): Promise<AuthSession | null> {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) return getStoredSession();
  const data = await authFetch('/token?grant_type=refresh_token', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  const session = normalizeSession(data);
  persistSession(session);
  return enrichSessionWithBackendUser(session);
}

export async function signOut() {
  const session = getStoredSession();
  try {
    if (session?.access_token) {
      await authFetch('/logout', {
        method: 'POST',
        headers: { Authorization: `Bearer ${session.access_token}` },
        body: JSON.stringify({}),
      });
    }
  } finally {
    clearStoredSession();
  }
}
