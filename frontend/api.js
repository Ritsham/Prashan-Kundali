import { AppState } from './state.js';
import { showFlash } from './flash.js';

export const API = {
  async request(endpoint, options = {}, requireAuth = true) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    
    if (requireAuth) {
      const token = AppState.session?.access_token || localStorage.getItem('supabase_token');
      if (!token) throw new Error("Authentication required. Please sign in.");
      headers.Authorization = `Bearer ${token}`;
    }

    try {
      const response = await fetch(endpoint, { ...options, headers });
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(this.formatError(data.detail) || "API Request Failed");
      }
      return data;
    } catch (err) {
      console.error(`[API Error] ${endpoint}:`, err);
      showFlash(err.message, 'error');
      throw err;
    }
  },

  get(endpoint, auth = true) {
    return this.request(endpoint, { method: 'GET' }, auth);
  },

  post(endpoint, body, auth = true) {
    return this.request(endpoint, { method: 'POST', body: JSON.stringify(body) }, auth);
  },

  formatError(detail) {
    if (!detail) return "An unknown error occurred.";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map(item => {
        if (typeof item === "string") return item;
        const field = Array.isArray(item.loc) ? item.loc.filter(part => part !== "body").join(".") : "";
        return [field, item.msg].filter(Boolean).join(": ");
      }).filter(Boolean).join(" ");
    }
    return detail.msg || detail.message || JSON.stringify(detail);
  }
};