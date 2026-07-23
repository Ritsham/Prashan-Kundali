import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm";

let supabaseInstance = null;

const AUTH_LAST_SEEN_KEY = "astro_auth_last_seen_at";
const AUTH_MAX_IDLE_MS = 30 * 24 * 60 * 60 * 1000;

function isValidSupabaseUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && url.hostname.endsWith(".supabase.co");
  } catch {
    return false;
  }
}

function rememberAuthenticatedVisit() {
  localStorage.setItem(AUTH_LAST_SEEN_KEY, String(Date.now()));
}

async function enforceThirtyDaySignin(client, session) {
  if (!session) return null;
  const lastSeenAt = Number(localStorage.getItem(AUTH_LAST_SEEN_KEY) || "0");
  if (lastSeenAt && Date.now() - lastSeenAt > AUTH_MAX_IDLE_MS) {
    await client.auth.signOut();
    localStorage.removeItem("supabase_token");
    localStorage.removeItem(AUTH_LAST_SEEN_KEY);
    return null;
  }
  rememberAuthenticatedVisit();
  return session;
}

export async function getSupabase() {
  if (supabaseInstance) return supabaseInstance;

  const response = await fetch("/api/config");
  const config = await response.json();
  if (!isValidSupabaseUrl(config.supabaseUrl) || !config.supabaseAnonKey) {
    throw new Error("Authentication is not configured correctly. Please update SUPABASE_URL and SUPABASE_ANON_KEY for this deployment.");
  }

  supabaseInstance = createClient(config.supabaseUrl, config.supabaseAnonKey);
  supabaseInstance.auth.onAuthStateChange((_event, session) => {
    if (session?.access_token) {
      localStorage.setItem("supabase_token", session.access_token);
      rememberAuthenticatedVisit();
    } else {
      localStorage.removeItem("supabase_token");
      localStorage.removeItem(AUTH_LAST_SEEN_KEY);
    }
  });
  return supabaseInstance;
}

export async function requireAuth() {
  const supabase = await getSupabase();
  const { data: { session: rawSession } } = await supabase.auth.getSession();
  const session = await enforceThirtyDaySignin(supabase, rawSession);
  if (!session) {
    window.location.href = "./index.html";
    return null;
  }
  localStorage.setItem("supabase_token", session.access_token);
  return { supabase, session };
}

export async function getAccessToken() {
  const auth = await requireAuth();
  return auth?.session?.access_token || null;
}

export async function initLogout(buttonId = "btn-logout") {
  const button = document.getElementById(buttonId);
  if (!button) return;
  button.addEventListener("click", async () => {
    const supabase = await getSupabase();
    await supabase.auth.signOut();
    localStorage.removeItem("supabase_token");
    window.location.href = "./index.html";
  });
}
