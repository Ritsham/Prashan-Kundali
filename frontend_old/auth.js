import { AppState } from './state.js';
import { API } from './api.js';
import { showFlash } from './flash.js';

let supabaseClient = null;

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
    if (!config.supabaseUrl || !config.supabaseAnonKey) {
      console.error("CRITICAL: Supabase keys are missing in config!");
      showFlash("CRITICAL: Supabase keys are missing in config!", "error");
      return;
    }
    
    supabaseClient = window.supabase.createClient(config.supabaseUrl, config.supabaseAnonKey);

    supabaseClient.auth.onAuthStateChange(async (event, newSession) => {
      AppState.setSession(newSession);
      
      if (newSession) {
        document.querySelector("#auth-modal")?.classList.add("hidden");
        await syncUserWithBackend(newSession.user);
        restoreAndSubmitPending();
      } else {
        document.querySelector("#auth-modal")?.classList.add("hidden");
      }
    });

    bindAuthUI();
  } catch (err) {
    console.error("Error initializing Supabase client:", err);
    showFlash("Authentication initialization failed: " + err.message, "error");
  }
}

function bindAuthUI() {
  document.querySelector("#btn-login-google")?.addEventListener("click", () => {
    supabaseClient.auth.signInWithOAuth({ provider: "google", options: { redirectTo: window.location.origin }});
  });

  document.querySelector("#btn-logout")?.addEventListener("click", () => supabaseClient.auth.signOut());
  
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
  const name = user.user_metadata?.full_name || user.user_metadata?.name || "Google User";
  try {
    await API.post("/api/users/sync", { email, name });
  } catch (err) {
    console.warn("User details sync failed:", err);
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