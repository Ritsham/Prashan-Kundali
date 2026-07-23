import React from 'react';
import type { AuthSession } from './supabaseAuth';

export type AuthContextValue = {
  session: AuthSession | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, fullName: string) => Promise<void>;
  signInWithGoogle: (intent?: 'sign_in' | 'sign_up', profile?: { fullName: string; mobileNumber: string }) => Promise<void>;
  completeProfile: (name: string, mobileNumber: string) => Promise<void>;
  signOut: () => Promise<void>;
};

export const AuthContext = React.createContext<AuthContextValue | null>(null);
