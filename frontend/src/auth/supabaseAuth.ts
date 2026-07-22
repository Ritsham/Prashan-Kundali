import { publicEnv } from '../config/env';

type SupabaseConfig = {
  supabaseUrl: string;
  supabaseAnonKey: string;
};

export type AuthSession = {
  access_token: string;
  refresh_token?: string;
  expires_at?: number;
  user?: {
    id?: string;
    email?: string;
    role?: 'user' | 'astrologer_pending' | 'astrologer_verified' | 'admin';
    user_metadata?: Record<string, unknown>;
    profile?: Record<string, unknown>;
  };
};

const ACCESS_TOKEN_KEY = 'supabase_token';
const REFRESH_TOKEN_KEY = 'supabase_refresh_token';
const EXPIRES_AT_KEY = 'supabase_expires_at';
const USER_KEY = 'supabase_user';

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

function persistSession(session: AuthSession) {
  localStorage.setItem(ACCESS_TOKEN_KEY, session.access_token);
  if (session.refresh_token) localStorage.setItem(REFRESH_TOKEN_KEY, session.refresh_token);
  if (session.expires_at) localStorage.setItem(EXPIRES_AT_KEY, String(session.expires_at));
  if (session.user) localStorage.setItem(USER_KEY, JSON.stringify(session.user));
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
    user,
  };
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
  persistSession(session);
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
  persistSession(session);
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
