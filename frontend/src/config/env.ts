type PublicRuntimeConfig = {
  apiBaseUrl: string;
  supabaseUrl?: string;
  supabaseAnonKey?: string;
};

function cleanUrl(value: string): string {
  return value.trim().replace(/\/+$/, '');
}

function requireValidUrl(name: string, value: string, allowedProtocols: string[]): string {
  const cleaned = cleanUrl(value);
  if (!cleaned) return '';
  try {
    const url = new URL(cleaned);
    if (!allowedProtocols.includes(url.protocol)) {
      throw new Error(`${name} must use ${allowedProtocols.join(' or ')}`);
    }
    return cleaned;
  } catch (error) {
    throw new Error(`${name} is not a valid URL. ${error instanceof Error ? error.message : ''}`.trim());
  }
}

function rejectFrontendSecrets() {
  const env = import.meta.env as Record<string, string | undefined>;
  const forbidden = [
    'VITE_SUPABASE_SERVICE_ROLE_KEY',
    'VITE_RAZORPAY_KEY_SECRET',
    'VITE_RAZORPAY_WEBHOOK_SECRET',
    'VITE_OPENAI_API_KEY',
    'VITE_OPENAI_API_KEYS',
    'VITE_GEMINI_API_KEY',
    'VITE_GEMINI_API_KEYS',
    'VITE_GROQ_API_KEY',
    'VITE_GROQ_API_KEYS',
    'VITE_CEREBRAS_API_KEY',
    'VITE_CEREBRAS_API_KEYS',
    'VITE_OPENROUTER_API_KEY',
    'VITE_OPENROUTER_API_KEYS',
  ];
  const leaked = forbidden.filter((name) => Boolean(env[name]));
  if (leaked.length > 0) {
    throw new Error(`Secret-like frontend environment variables are not allowed: ${leaked.join(', ')}`);
  }
}

rejectFrontendSecrets();

export const publicEnv: PublicRuntimeConfig = {
  apiBaseUrl: requireValidUrl('VITE_API_URL', import.meta.env.VITE_API_URL || '', ['http:', 'https:']),
  supabaseUrl: requireValidUrl('VITE_SUPABASE_URL', import.meta.env.VITE_SUPABASE_URL || '', ['https:']),
  supabaseAnonKey: (import.meta.env.VITE_SUPABASE_ANON_KEY || '').trim() || undefined,
};
