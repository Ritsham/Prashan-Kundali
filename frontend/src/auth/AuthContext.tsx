import React from 'react';
import {
  type AuthSession,
  clearStoredSession,
  completeUserProfile,
  consumeOAuthCallback,
  enrichSessionWithBackendUser,
  getStoredSession,
  refreshSession,
  signInWithPassword,
  signInWithGoogle as signInWithGoogleRequest,
  signOut as signOutRequest,
  signUpWithPassword,
} from './supabaseAuth';
import { AuthContext, type AuthContextValue } from './authContextValue';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = React.useState<AuthSession | null>(() => getStoredSession());
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        const oauthSession = await consumeOAuthCallback();
        if (oauthSession?.access_token) {
          if (!cancelled) setSession(oauthSession);
          if (!cancelled) setLoading(false);
          return;
        }
      } catch {
        clearStoredSession();
        if (!cancelled) setSession(null);
        if (!cancelled) setLoading(false);
        return;
      }

      const stored = getStoredSession();
      if (!stored) {
        setLoading(false);
        return;
      }
      const now = Math.floor(Date.now() / 1000);
      if (stored.expires_at && stored.expires_at - now > 120) {
        try {
          const enriched = await enrichSessionWithBackendUser(stored);
          if (!cancelled) setSession(enriched);
        } catch {
          if (!cancelled) setSession(stored);
        } finally {
          if (!cancelled) setLoading(false);
        }
        return;
      }
      try {
        const refreshed = await refreshSession();
        if (!cancelled) setSession(refreshed);
      } catch {
        clearStoredSession();
        if (!cancelled) setSession(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    boot();
    return () => { cancelled = true; };
  }, []);

  const value = React.useMemo<AuthContextValue>(() => ({
    session,
    loading,
    signIn: async (email: string, password: string) => {
      const next = await signInWithPassword(email, password);
      setSession(next);
    },
    signUp: async (email: string, password: string, fullName: string) => {
      const next = await signUpWithPassword(email, password, fullName);
      setSession(next);
    },
    signInWithGoogle: async (intent, profile) => {
      await signInWithGoogleRequest(intent, profile);
    },
    completeProfile: async (name: string, mobileNumber: string) => {
      if (!session) throw new Error('Authentication required.');
      const next = await completeUserProfile(session, name, mobileNumber);
      setSession(next);
    },
    signOut: async () => {
      await signOutRequest();
      setSession(null);
    },
  }), [session, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
