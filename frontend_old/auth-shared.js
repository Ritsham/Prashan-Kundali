import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm';

let supabaseInstance = null;
const AUTH_LAST_SEEN_KEY = 'astro_auth_last_seen_at';
const AUTH_MAX_IDLE_MS = 7 * 24 * 60 * 60 * 1000;

function isValidSupabaseUrl(value) {
    try {
        const url = new URL(value);
        return url.protocol === 'https:' && url.hostname.endsWith('.supabase.co');
    } catch (_err) {
        return false;
    }
}

function rememberAuthenticatedVisit() {
    localStorage.setItem(AUTH_LAST_SEEN_KEY, String(Date.now()));
}

async function enforceSevenDaySignin(supabase, session) {
    if (!session) return null;
    const lastSeen = Number(localStorage.getItem(AUTH_LAST_SEEN_KEY) || '0');
    if (lastSeen && Date.now() - lastSeen > AUTH_MAX_IDLE_MS) {
        await supabase.auth.signOut();
        localStorage.removeItem('supabase_token');
        localStorage.removeItem(AUTH_LAST_SEEN_KEY);
        return null;
    }
    rememberAuthenticatedVisit();
    return session;
}

export async function getSupabase() {
    if (supabaseInstance) return supabaseInstance;
    
    const configRes = await fetch('/api/config');
    const config = await configRes.json();
    if (!isValidSupabaseUrl(config.supabaseUrl) || !config.supabaseAnonKey) {
        throw new Error('Authentication is not configured correctly. Please update SUPABASE_URL and SUPABASE_ANON_KEY for this deployment.');
    }
    supabaseInstance = createClient(config.supabaseUrl, config.supabaseAnonKey);
    supabaseInstance.auth.onAuthStateChange((_event, session) => {
        if (session?.access_token) {
            localStorage.setItem('supabase_token', session.access_token);
            rememberAuthenticatedVisit();
        } else {
            localStorage.removeItem('supabase_token');
            localStorage.removeItem(AUTH_LAST_SEEN_KEY);
        }
    });
    
    return supabaseInstance;
}

export async function requireAuth() {
    const supabase = await getSupabase();
    const { data: { session: rawSession } } = await supabase.auth.getSession();
    const session = await enforceSevenDaySignin(supabase, rawSession);
    
    if (!session) {
        window.location.href = './index.html';
        return null;
    }
    localStorage.setItem('supabase_token', session.access_token);
    return { supabase, session };
}

export async function getAccessToken() {
    const auth = await requireAuth();
    return auth?.session?.access_token || null;
}

export async function initLogout(buttonId = 'btn-logout') {
    const btn = document.getElementById(buttonId);
    if (!btn) return;
    
    btn.addEventListener('click', async () => {
        const supabase = await getSupabase();
        await supabase.auth.signOut();
        localStorage.removeItem('supabase_token');
        window.location.href = './index.html';
    });
}
