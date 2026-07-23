import { AppState } from "./state.js";
import { API } from "./api.js";
import { showFlash } from "./flash.js";

let supabaseClient = null;
let authConfig = {};

const CANONICAL_PUBLIC_ORIGIN = "https://www.shreelakshmiastro.com";
const SIGNUP_PROFILE_KEY = "astro_pending_signup_profile";
const AUTH_INTENT_KEY = "astro_google_auth_intent";
const AUTH_LAST_SEEN_KEY = "astro_auth_last_seen_at";
const AUTH_MAX_IDLE_MS = 30 * 24 * 60 * 60 * 1000;

const hasHashToken = window.location.hash.includes("access_token=");
const hasStorageToken = Object.keys(localStorage).some((key) => key.startsWith("sb-") && key.endsWith("-auth-token"));
if (hasHashToken || hasStorageToken) {
  updateAuthControls(getStoredSessionUser(), true);
}

export async function initAuth() {
  try {
    const config = await API.get("/api/config", false);
    if (!isValidSupabaseUrl(config.supabaseUrl) || !config.supabaseAnonKey) {
      console.error("CRITICAL: Supabase auth config is invalid!", config.supabaseUrl);
      showFlash("Authentication is not configured correctly. Please update the Supabase URL/key for this deployment.", "error");
      return;
    }

    authConfig = config;
    supabaseClient = window.supabase.createClient(config.supabaseUrl, config.supabaseAnonKey);
    supabaseClient.auth.onAuthStateChange(async (_event, rawSession) => {
      const session = await enforceThirtyDaySignin(rawSession);
      AppState.setSession(session);
      updateAuthControls(session?.user || null, Boolean(session));

      if (session) {
        localStorage.setItem("supabase_token", session.access_token);
        document.querySelector("#auth-modal")?.classList.add("hidden");
        await syncPendingSignupWithBackend(session.user);
        restoreAndSubmitPending();
      } else {
        localStorage.removeItem("supabase_token");
        document.querySelector("#auth-modal")?.classList.add("hidden");
      }
    });

    const { data: { session: rawSession } } = await supabaseClient.auth.getSession();
    const session = await enforceThirtyDaySignin(rawSession);
    AppState.setSession(session);
    updateAuthControls(session?.user || null, Boolean(session));
    if (session) {
      localStorage.setItem("supabase_token", session.access_token);
      await syncPendingSignupWithBackend(session.user);
    }

    ensureAuthModal();
    bindAuthUI();
  } catch (error) {
    console.error("Error initializing Supabase client:", error);
    showFlash(`Authentication initialization failed: ${error.message}`, "error");
  }
}

function bindAuthUI() {
  document.querySelector("#btn-login-google")?.addEventListener("click", () => {
    localStorage.setItem(AUTH_INTENT_KEY, "sign_in");
    localStorage.removeItem(SIGNUP_PROFILE_KEY);
    window.location.assign(buildGoogleOAuthUrl());
  });

  document.querySelector("#btn-signup-google")?.addEventListener("click", () => {
    const profile = collectSignupProfile();
    if (!profile) return;
    localStorage.setItem(AUTH_INTENT_KEY, "sign_up");
    localStorage.setItem(SIGNUP_PROFILE_KEY, JSON.stringify(profile));
    window.location.assign(buildGoogleOAuthUrl());
  });

  document.querySelector("#btn-logout")?.addEventListener("click", async () => {
    localStorage.removeItem(AUTH_LAST_SEEN_KEY);
    localStorage.removeItem(SIGNUP_PROFILE_KEY);
    localStorage.removeItem(AUTH_INTENT_KEY);
    await supabaseClient.auth.signOut();
    closeProfileMenu();
    updateAuthControls(null, false);
  });

  document.querySelector("#btn-login-header")?.addEventListener("click", () => {
    document.querySelector("#auth-modal")?.classList.remove("hidden");
  });
  document.querySelector("#btn-close-auth")?.addEventListener("click", () => {
    document.querySelector("#auth-modal")?.classList.add("hidden");
  });
  document.querySelector("#auth-backdrop")?.addEventListener("click", () => {
    document.querySelector("#auth-modal")?.classList.add("hidden");
  });

  bindProfileMenu();
  document.addEventListener("astro:authChanged", (event) => {
    const session = event.detail;
    updateAuthControls(session?.user || null, Boolean(session));
  });
}

function bindProfileMenu() {
  const profileButton = document.querySelector("#btn-profile");
  const profilePageButton = document.querySelector("#btn-profile-page");

  profileButton?.addEventListener("click", (event) => {
    event.stopPropagation();
    const panel = document.querySelector("#profile-menu-panel");
    const opening = panel?.classList.contains("hidden");
    panel?.classList.toggle("hidden", !opening);
    profileButton.setAttribute("aria-expanded", String(Boolean(opening)));
  });
  profilePageButton?.addEventListener("click", () => {
    window.location.href = "/profile.html";
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest("#profile-menu")) closeProfileMenu();
  });
}

function updateAuthControls(user, isSignedIn) {
  const profileMenu = document.querySelector("#profile-menu");
  const loginButton = document.querySelector("#btn-login-header");
  const profileButton = document.querySelector("#btn-profile");
  profileMenu?.classList.toggle("hidden", !isSignedIn);
  loginButton?.classList.toggle("hidden", isSignedIn);
  if (profileButton) profileButton.textContent = getUserInitial(user);
  if (!isSignedIn) closeProfileMenu();
}

function closeProfileMenu() {
  document.querySelector("#profile-menu-panel")?.classList.add("hidden");
  document.querySelector("#btn-profile")?.setAttribute("aria-expanded", "false");
}

function getUserInitial(user) {
  return (user?.user_metadata?.full_name || user?.user_metadata?.name || user?.email || "U").trim().charAt(0).toUpperCase() || "U";
}

function getStoredSessionUser() {
  for (const [key, value] of Object.entries(localStorage)) {
    if (key.startsWith("sb-") && key.endsWith("-auth-token")) {
      try {
        const session = JSON.parse(value);
        return session?.user || session?.currentSession?.user || null;
      } catch {
        return null;
      }
    }
  }
  return null;
}

async function syncPendingSignupWithBackend(user) {
  if (localStorage.getItem(AUTH_INTENT_KEY) !== "sign_up") {
    localStorage.removeItem(SIGNUP_PROFILE_KEY);
    return;
  }

  const pendingProfile = readPendingSignupProfile();
  if (!pendingProfile.name || !pendingProfile.mobile_number) return;

  try {
    const current = await API.get("/api/auth/me");
    if (current?.user?.profile_exists) {
      localStorage.removeItem(SIGNUP_PROFILE_KEY);
      localStorage.removeItem(AUTH_INTENT_KEY);
      return;
    }
  } catch (error) {
    console.warn("Unable to check existing user profile:", error);
  }

  try {
    await API.post("/api/users/sync", {
      email: user.email,
      name: pendingProfile.name,
      mobile_number: pendingProfile.mobile_number,
    });
    localStorage.removeItem(SIGNUP_PROFILE_KEY);
    localStorage.removeItem(AUTH_INTENT_KEY);
  } catch (error) {
    console.warn("User details sync failed:", error);
  }
}

function isValidSupabaseUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && url.hostname.endsWith(".supabase.co");
  } catch {
    return false;
  }
}

function isLocalhostOrigin(value) {
  try {
    const hostname = new URL(value).hostname;
    return ["localhost", "127.0.0.1", "0.0.0.0"].includes(hostname);
  } catch {
    return false;
  }
}

function getConfiguredPublicOrigin() {
  try {
    const publicSiteUrl = authConfig.publicSiteUrl || "";
    return !publicSiteUrl || isLocalhostOrigin(publicSiteUrl) ? "" : new URL(publicSiteUrl).origin;
  } catch {
    return "";
  }
}

function getBrowserPublicOrigin() {
  const hostname = window.location.hostname;
  return hostname === "shreelakshmiastro.com" || hostname === "www.shreelakshmiastro.com" ? CANONICAL_PUBLIC_ORIGIN : "";
}

function buildAuthRedirectUrl() {
  const origin = getBrowserPublicOrigin() || getConfiguredPublicOrigin() || window.location.origin;
  return new URL(window.location.pathname + window.location.search, origin).toString();
}

function buildGoogleOAuthUrl() {
  const url = new URL("/auth/v1/authorize", authConfig.supabaseUrl);
  url.searchParams.set("provider", "google");
  url.searchParams.set("redirect_to", buildAuthRedirectUrl());
  return url.toString();
}

function rememberAuthenticatedVisit() {
  localStorage.setItem(AUTH_LAST_SEEN_KEY, String(Date.now()));
}

async function enforceThirtyDaySignin(session) {
  if (!session || !supabaseClient) return null;
  const lastSeenAt = Number(localStorage.getItem(AUTH_LAST_SEEN_KEY) || "0");
  if (lastSeenAt && Date.now() - lastSeenAt > AUTH_MAX_IDLE_MS) {
    await supabaseClient.auth.signOut();
    localStorage.removeItem("supabase_token");
    localStorage.removeItem(AUTH_LAST_SEEN_KEY);
    return null;
  }
  rememberAuthenticatedVisit();
  return session;
}

function ensureAuthModal() {
  ensureAuthModalStyles();
  let modal = document.querySelector("#auth-modal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "auth-modal";
    modal.className = "auth-modal hidden";
    document.body.prepend(modal);
  }

  modal.innerHTML = `
    <div class="auth-backdrop" id="auth-backdrop"></div>
    <div class="auth-panel">
      <button type="button" id="btn-close-auth" class="btn-close-auth" aria-label="Close modal">&times;</button>
      <h1>Account access</h1>
      <div class="auth-choice-grid">
        <section>
          <h2>Sign in</h2>
          <p>Existing users continue with Google.</p>
          <button type="button" id="btn-login-google" class="btn-google-login">Sign in with Google</button>
        </section>
        <section>
          <h2>Sign up</h2>
          <p>New users enter these details once, then verify with Google.</p>
          <div id="signup-profile-fields" class="auth-fields">
            <label for="auth-full-name">Full name</label>
            <input id="auth-full-name" type="text" autocomplete="name" maxlength="120" placeholder="Your name" required>
            <label for="auth-mobile-number">Mobile number</label>
            <input id="auth-mobile-number" type="tel" autocomplete="tel" maxlength="24" placeholder="+91 98765 43210" required>
          </div>
          <button type="button" id="btn-signup-google" class="btn-google-login">Continue with Google</button>
        </section>
      </div>
    </div>
  `;
}

function ensureAuthModalStyles() {
  if (document.querySelector("#auth-modal-flow-styles")) return;
  const style = document.createElement("style");
  style.id = "auth-modal-flow-styles";
  style.textContent = `
    .auth-choice-grid {
      display: grid;
      gap: 16px;
    }
    .auth-choice-grid section {
      display: grid;
      gap: 12px;
      padding: 14px;
      border: 1px solid rgba(112, 99, 77, 0.18);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.06);
    }
    .auth-choice-grid h2 {
      margin: 0;
      font-size: 1rem;
    }
    .auth-choice-grid p {
      margin: 0;
    }
    @media (min-width: 720px) {
      .auth-panel {
        width: min(92vw, 760px);
      }
      .auth-choice-grid {
        grid-template-columns: 1fr 1fr;
      }
    }
  `;
  document.head.appendChild(style);
}

function collectSignupProfile() {
  const nameInput = document.querySelector("#auth-full-name");
  const mobileInput = document.querySelector("#auth-mobile-number");
  const name = (nameInput?.value || "").trim();
  const mobileNumber = (mobileInput?.value || "").trim();

  if (!name) {
    showFlash("Please enter your name before continuing.", "error");
    nameInput?.focus();
    return null;
  }
  if (!/^\+?[0-9 ()-]{6,24}$/.test(mobileNumber)) {
    showFlash("Please enter a valid mobile number.", "error");
    mobileInput?.focus();
    return null;
  }
  return { name, mobile_number: mobileNumber };
}

function readPendingSignupProfile() {
  try {
    return JSON.parse(localStorage.getItem(SIGNUP_PROFILE_KEY) || "{}");
  } catch {
    return {};
  }
}

export function savePendingSubmission() {
  const payload = {
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
  sessionStorage.setItem("pending_submission", JSON.stringify(payload));
}

function restoreAndSubmitPending() {
  const raw = sessionStorage.getItem("pending_submission");
  if (!raw) return;

  try {
    const payload = JSON.parse(raw);
    sessionStorage.removeItem("pending_submission");
    AppState.setMode(payload.mode);
    setInputValue("#name", payload.name);
    setInputValue("#question", payload.question);
    setInputValue("#question_domain", payload.question_domain);
    setInputValue("#job_type", payload.job_type);
    const genderInput = document.querySelector(`input[name="gender"][value="${payload.gender}"]`);
    if (genderInput) genderInput.checked = true;
    setInputValue("#birth_date", payload.birth_date);
    setInputValue("#birth_time", payload.birth_time);
    setInputValue("#birth_datetime_local", payload.birth_datetime_local);
    setInputValue("#latitude", payload.latitude);
    setInputValue("#longitude", payload.longitude);
    setInputValue("#place_name", payload.place_name);
    setInputValue("#place_search", payload.place_search);
    setTimeout(() => {
      document.querySelector("#prashna-form")?.dispatchEvent(new Event("submit"));
    }, 600);
  } catch (error) {
    console.error("Error restoring pending submission:", error);
    showFlash(`Failed to restore pending submission: ${error.message}`, "error");
  }
}

function setInputValue(selector, value = "") {
  const input = document.querySelector(selector);
  if (input) input.value = value || "";
}
