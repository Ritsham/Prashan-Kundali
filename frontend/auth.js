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
    // Dynamically inject the authentication modal HTML if it does not exist in the DOM
    if (!document.getElementById("auth-modal")) {
      const modalHTML = `
      <div id="auth-modal" class="auth-modal hidden">
        <div class="auth-backdrop" id="auth-backdrop"></div>
        <div class="auth-panel">
          <button
            type="button"
            id="btn-close-auth"
            class="btn-close-auth"
            aria-label="Close modal"
          >
            &times;
          </button>
          <h1>Welcome to Kundali Studio</h1>
          <p>
            Sign in with your Google account to perform readings, consult
            astrologers, and track saved transits.
          </p>
          <button type="button" id="btn-login-google" class="btn-google-login">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                fill="#4285F4"
              />
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                fill="#34A853"
              />
              <path
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                fill="#FBBC05"
              />
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#EA4335"
              />
            </svg>
            Sign in with Google
          </button>
          <div
            id="auth-debug-box"
            style="
              margin-top: 20px;
              font-size: 11px;
              color: #9ca3af;
              text-align: left;
              border-top: 1px solid rgba(46, 43, 95, 0.08);
              padding-top: 10px;
              width: 100%;
              white-space: pre-wrap;
              word-break: break-all;
            "
          >
            Initializing script...
          </div>
        </div>
      </div>`;
      const tempDiv = document.createElement("div");
      tempDiv.innerHTML = modalHTML.trim();
      document.body.appendChild(tempDiv.firstChild);
    }

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