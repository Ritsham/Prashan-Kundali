import { AppState } from "./state.js";
import { showFlash } from "./flash.js";

function clearAuthStorage() {
  localStorage.removeItem("supabase_token");
  localStorage.removeItem("supabase_refresh_token");
  localStorage.removeItem("supabase_expires_at");
  localStorage.removeItem("supabase_user");
  localStorage.removeItem("astro_auth_last_seen_at");

  for (const key of Object.keys(localStorage)) {
    if (key.startsWith("sb-") && key.endsWith("-auth-token")) {
      localStorage.removeItem(key);
    }
  }

  AppState.setSession(null);
}

function authFailureMessage(message = "") {
  const normalized = String(message || "").toLowerCase();
  if (
    normalized.includes("authentication failed") ||
    normalized.includes("invalid token") ||
    normalized.includes("jwt") ||
    normalized.includes("expired")
  ) {
    return "Your sign-in session expired. Please sign in again.";
  }
  return message || "Authentication required. Please sign in.";
}

export const API = {
  async request(path, options = {}, requireAuth = true) {
    const headers = {
      "Content-Type": "application/json",
      ...options.headers,
    };

    if (requireAuth) {
      const token = AppState.session?.access_token || localStorage.getItem("supabase_token");
      if (!token) {
        throw new Error("Authentication required. Please sign in.");
      }
      headers.Authorization = `Bearer ${token}`;
    }

    try {
      const response = await fetch(path, { ...options, headers });
      const payload = await response.json().catch(() => ({}));

      if (!response.ok) {
        const message = this.formatError(payload.detail) || "API request failed";
        if (response.status === 401) {
          clearAuthStorage();
          throw new Error(authFailureMessage(message));
        }
        throw new Error(message);
      }

      return payload;
    } catch (error) {
      console.error(`[API Error] ${path}:`, error);
      showFlash(error.message, "error");
      throw error;
    }
  },

  get(path, requireAuth = true) {
    return this.request(path, { method: "GET" }, requireAuth);
  },

  post(path, body, requireAuth = true) {
    return this.request(path, { method: "POST", body: JSON.stringify(body) }, requireAuth);
  },

  formatError(detail) {
    if (!detail) return "An unknown error occurred.";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (typeof item === "string") return item;
          return [
            Array.isArray(item.loc) ? item.loc.filter((part) => part !== "body").join(".") : "",
            item.msg,
          ]
            .filter(Boolean)
            .join(": ");
        })
        .filter(Boolean)
        .join(" ");
    }
    return detail.msg || detail.message || JSON.stringify(detail);
  },
};
