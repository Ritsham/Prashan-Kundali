import { AppState } from './state.js';
import { API } from './api.js';
import { showFlash } from './flash.js';

let supabaseClient = null;
const SIGNUP_PROFILE_KEY = 'astro_pending_signup_profile';
const AUTH_LAST_SEEN_KEY = 'astro_auth_last_seen_at';
const AUTH_MAX_IDLE_MS = 7 * 24 * 60 * 60 * 1000;

// Prevent FOUC (Flash of Unauthenticated Content) by checking localStorage eagerly
const hasToken = !!localStorage.getItem('supabase_token');
if (hasToken) {
  document.querySelector("#btn-logout")?.classList.remove("hidden");
  document.querySelector("#btn-dashboard")?.classList.remove("hidden");
  document.querySelector("#btn-profile")?.classList.remove("hidden");
  document.querySelector("#btn-login-header")?.classList.add("hidden");
}

export async function initAuth() {
  try {
    const config = await API.get("/api/config", false);
    if (!isValidSupabaseUrl(config.supabaseUrl) || !config.supabaseAnonKey) {
      console.error("CRITICAL: Supabase auth config is invalid!", config.supabaseUrl);
      showFlash("Authentication is not configured correctly. Please update the Supabase URL/key for this deployment.", "error");
      return;
    }
    
    supabaseClient = window.supabase.createClient(config.supabaseUrl, config.supabaseAnonKey);

    supabaseClient.auth.onAuthStateChange(async (event, newSession) => {
      newSession = await enforceSevenDaySignin(newSession);
      AppState.setSession(newSession);
      
      if (newSession) {
        document.querySelector("#auth-modal")?.classList.add("hidden");
        await syncUserWithBackend(newSession.user);
        restoreAndSubmitPending();
      } else {
        document.querySelector("#auth-modal")?.classList.add("hidden");
      }
    });

    const { data: { session } } = await supabaseClient.auth.getSession();
    const activeSession = await enforceSevenDaySignin(session);
    AppState.setSession(activeSession);
    if (activeSession) {
      await syncUserWithBackend(activeSession.user);
    }

    ensureAuthModal();
    bindAuthUI();
  } catch (err) {
    console.error("Error initializing Supabase client:", err);
    showFlash("Authentication initialization failed: " + err.message, "error");
  }
}

function bindAuthUI() {
  document.querySelector("#btn-login-google")?.addEventListener("click", async () => {
    const profile = collectSignupProfile();
    if (!profile) return;
    localStorage.setItem(SIGNUP_PROFILE_KEY, JSON.stringify(profile));
    const redirectTo = new URL(window.location.pathname + window.location.search, window.location.origin).toString();
    const { error } = await supabaseClient.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo },
    });
    if (error) showFlash(error.message, "error");
  });

  document.querySelector("#btn-logout")?.addEventListener("click", () => {
    localStorage.removeItem(AUTH_LAST_SEEN_KEY);
    localStorage.removeItem(SIGNUP_PROFILE_KEY);
    supabaseClient.auth.signOut();
  });
  
  document.querySelector("#btn-login-header")?.addEventListener("click", () => {
    document.querySelector("#auth-modal").classList.remove("hidden");
  });

  document.querySelector("#btn-close-auth")?.addEventListener("click", () => {
    document.querySelector("#auth-modal").classList.add("hidden");
  });

  document.querySelector("#auth-backdrop")?.addEventListener("click", () => {
    document.querySelector("#auth-modal").classList.add("hidden");
  });

  // Handle global navbar auth toggles
  document.addEventListener('astro:authChanged', (e) => {
    const session = e.detail;
    document.querySelector("#btn-logout")?.classList.toggle("hidden", !session);
    document.querySelector("#btn-dashboard")?.classList.toggle("hidden", !session);
    document.querySelector("#btn-profile")?.classList.toggle("hidden", !session);
    document.querySelector("#btn-login-header")?.classList.toggle("hidden", !!session);
  });
}

async function syncUserWithBackend(user) {
  const email = user.email;
  const pendingProfile = readPendingSignupProfile();
  const name = pendingProfile.name || user.user_metadata?.full_name || user.user_metadata?.name || "Google User";
  const mobile_number = pendingProfile.mobile_number || "";
  try {
    await API.post("/api/users/sync", { email, name, mobile_number });
    localStorage.removeItem(SIGNUP_PROFILE_KEY);
  } catch (err) {
    console.warn("User details sync failed:", err);
  }
}

function isValidSupabaseUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && url.hostname.endsWith(".supabase.co");
  } catch (_err) {
    return false;
  }
}

function rememberAuthenticatedVisit() {
  localStorage.setItem(AUTH_LAST_SEEN_KEY, String(Date.now()));
}

async function enforceSevenDaySignin(session) {
  if (!session || !supabaseClient) return null;
  const lastSeen = Number(localStorage.getItem(AUTH_LAST_SEEN_KEY) || "0");
  if (lastSeen && Date.now() - lastSeen > AUTH_MAX_IDLE_MS) {
    await supabaseClient.auth.signOut();
    localStorage.removeItem("supabase_token");
    localStorage.removeItem(AUTH_LAST_SEEN_KEY);
    return null;
  }
  rememberAuthenticatedVisit();
  return session;
}

function ensureAuthModal() {
  let modal = document.querySelector("#auth-modal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "auth-modal";
    modal.className = "auth-modal hidden";
    modal.innerHTML = `
      <div class="auth-backdrop" id="auth-backdrop"></div>
      <div class="auth-panel">
        <button type="button" id="btn-close-auth" class="btn-close-auth" aria-label="Close modal">&times;</button>
        <h1>Sign in to continue</h1>
        <p>Enter your details once, then continue with Google.</p>
        <button type="button" id="btn-login-google" class="btn-google-login">Continue with Google</button>
      </div>
    `;
    document.body.prepend(modal);
  }

  const button = modal.querySelector("#btn-login-google");
  if (button && !modal.querySelector("#signup-profile-fields")) {
    button.insertAdjacentHTML("beforebegin", `
      <div id="signup-profile-fields" class="auth-fields">
        <label for="auth-full-name">Full name</label>
        <input id="auth-full-name" type="text" autocomplete="name" maxlength="120" placeholder="Your name" required>
        <label for="auth-mobile-number">Mobile number</label>
        <input id="auth-mobile-number" type="tel" autocomplete="tel" maxlength="24" placeholder="+91 98765 43210" required>
      </div>
    `);
  }
}

function collectSignupProfile() {
  const nameEl = document.querySelector("#auth-full-name");
  const mobileEl = document.querySelector("#auth-mobile-number");
  const name = (nameEl?.value || "").trim();
  const mobile_number = (mobileEl?.value || "").trim();
  const phonePattern = /^\+?[0-9 ()-]{6,24}$/;

  if (!name) {
    showFlash("Please enter your name before continuing.", "error");
    nameEl?.focus();
    return null;
  }
  if (!phonePattern.test(mobile_number)) {
    showFlash("Please enter a valid mobile number.", "error");
    mobileEl?.focus();
    return null;
  }
  return { name, mobile_number };
}

function readPendingSignupProfile() {
  try {
    return JSON.parse(localStorage.getItem(SIGNUP_PROFILE_KEY) || "{}");
  } catch (_err) {
    return {};
  }
}

export function savePendingSubmission() {
  const pendingData = {
    mode: AppState.activeMode,
    name: document.querySelector("#name")?.value || "",
    question: document.querySelector("#question")?.value || "",
    question_domain: document.querySelector("#question_domain")?.value || "",
    job_type: document.querySelector("#job_type")?.value || "",
    gender: document.querySelector('input[name="gender"]:checked')?.value || "male",
    birth_date: document.querySelector("#birth_date")?.value || "",
    birth_time: document.querySelector("#birth_time")?.value || "",
    birth_datetime_local: document.querySelector("#birth_datetime_local")?.value || "",
    latitude: document.querySelector("#latitude")?.value || "",
    longitude: document.querySelector("#longitude")?.value || "",
    place_name: document.querySelector("#place_name")?.value || "",
    place_search: document.querySelector("#place_search")?.value || "",
  };
  sessionStorage.setItem("pending_submission", JSON.stringify(pendingData));
}

function restoreAndSubmitPending() {
  const pendingStr = sessionStorage.getItem("pending_submission");
  if (!pendingStr) return;

  try {
    const data = JSON.parse(pendingStr);
    sessionStorage.removeItem("pending_submission");

    AppState.setMode(data.mode);

    if (document.querySelector("#name")) document.querySelector("#name").value = data.name || "";
    if (document.querySelector("#question")) document.querySelector("#question").value = data.question || "";
    if (document.querySelector("#question_domain")) document.querySelector("#question_domain").value = data.question_domain || "";
    if (document.querySelector("#job_type")) document.querySelector("#job_type").value = data.job_type || "";

    const genderRadio = document.querySelector(`input[name="gender"][value="${data.gender}"]`);
    if (genderRadio) genderRadio.checked = true;

    if (document.querySelector("#birth_date")) document.querySelector("#birth_date").value = data.birth_date || "";
    if (document.querySelector("#birth_time")) document.querySelector("#birth_time").value = data.birth_time || "";
    if (document.querySelector("#birth_datetime_local")) document.querySelector("#birth_datetime_local").value = data.birth_datetime_local || "";
    if (document.querySelector("#latitude")) document.querySelector("#latitude").value = data.latitude || "";
    if (document.querySelector("#longitude")) document.querySelector("#longitude").value = data.longitude || "";
    if (document.querySelector("#place_name")) document.querySelector("#place_name").value = data.place_name || "";
    if (document.querySelector("#place_search")) document.querySelector("#place_search").value = data.place_search || "";

    setTimeout(() => {
      document.querySelector("#prashna-form")?.dispatchEvent(new Event("submit"));
    }, 600);
  } catch (err) {
    console.error("Error restoring pending submission:", err);
    showFlash("Failed to restore pending submission: " + err.message, "error");
  }
}
