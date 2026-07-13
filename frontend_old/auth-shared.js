import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm';

let supabaseInstance = null;

export async function getSupabase() {
    if (supabaseInstance) return supabaseInstance;
    
    const configRes = await fetch('/api/config');
    const config = await configRes.json();
    supabaseInstance = createClient(config.supabaseUrl, config.supabaseAnonKey);
    supabaseInstance.auth.onAuthStateChange((_event, session) => {
        if (session?.access_token) {
            localStorage.setItem('supabase_token', session.access_token);
        } else {
            localStorage.removeItem('supabase_token');
        }
    });
    
    return supabaseInstance;
}

export async function requireAuth() {
    const supabase = await getSupabase();
    const { data: { session } } = await supabase.auth.getSession();
    
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
