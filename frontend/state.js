export const AppState = {
  session: null,
  activeMode: '', // 'lagna' or 'prashna'
  activeChart: null,

  setMode(mode) {
    this.activeMode = mode;
    document.dispatchEvent(new CustomEvent('astro:modeChanged', { detail: mode }));
  },

  setSession(newSession) {
    this.session = newSession;
    if (newSession) {
      localStorage.setItem('supabase_token', newSession.access_token);
    } else {
      localStorage.removeItem('supabase_token');
    }
    document.dispatchEvent(new CustomEvent('astro:authChanged', { detail: newSession }));
  }
};