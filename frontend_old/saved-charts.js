(function () {
  const STORAGE_PREFIX = "kundali_saved_items_v1:";
  const ACTIVE_CHART_KEY = "kundali_active_chart_state_v2";
  const OPEN_MATCH_KEY = "kundali_open_saved_match_v1";
  const MAX_ITEMS = 80;

  let currentSession = null;

  document.addEventListener("astro:authChanged", (event) => {
    currentSession = event.detail || null;
  });

  function userKey(session = currentSession) {
    const user = session?.user || readStoredUser();
    return user?.id || user?.email || localStorage.getItem("supabase_token") || "guest";
  }

  function storageKey(session = currentSession) {
    return `${STORAGE_PREFIX}${userKey(session)}`;
  }

  function readStoredUser() {
    for (const [key, value] of Object.entries(localStorage)) {
      if (!key.startsWith("sb-") || !key.endsWith("-auth-token")) continue;
      try {
        const parsed = JSON.parse(value);
        return parsed?.user || parsed?.currentSession?.user || null;
      } catch {
        return null;
      }
    }
    return null;
  }

  function list(session = currentSession) {
    try {
      const items = JSON.parse(localStorage.getItem(storageKey(session)) || "[]");
      return Array.isArray(items) ? items : [];
    } catch {
      return [];
    }
  }

  function write(items, session = currentSession) {
    localStorage.setItem(storageKey(session), JSON.stringify(items.slice(0, MAX_ITEMS)));
  }

  function save(item, session = currentSession) {
    if (!item?.type || !item?.payload) return { ok: false, reason: "invalid" };
    const now = new Date().toISOString();
    const savedItem = {
      id: item.id || `${item.type}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      title: item.title || "Saved chart",
      subtitle: item.subtitle || "",
      type: item.type,
      sourceId: item.sourceId || "",
      createdAt: item.createdAt || now,
      updatedAt: now,
      payload: item.payload,
    };
    const items = list(session).filter((existing) => {
      return !(existing.type === savedItem.type && existing.sourceId && existing.sourceId === savedItem.sourceId);
    });
    items.unshift(savedItem);
    write(items, session);
    return { ok: true, item: savedItem };
  }

  function remove(id, session = currentSession) {
    write(list(session).filter((item) => item.id !== id), session);
  }

  function saveChart(chart, options = {}) {
    if (!chart) return { ok: false, reason: "missing-chart" };
    const mode = options.mode || chart.meta?.chart_type || "lagna";
    const isLagna = mode === "lagna";
    const question = chart.question || {};
    const name = question.name || "User";
    return save({
      type: isLagna ? "lagna" : "prashna",
      sourceId: chart.id || chart.meta?.id || `${mode}:${question.asked_at_utc || Date.now()}`,
      title: `${name}'s ${isLagna ? "Lagna Kundli" : "Prashna Kundli"}`,
      subtitle: [question.place_name, question.asked_at_local || question.asked_at_utc].filter(Boolean).join(" • "),
      payload: { chart, mode },
    });
  }

  function saveMatch(matchId, report, formData = {}) {
    if (!report) return { ok: false, reason: "missing-report" };
    const boy = report.charts?.boy?.birth?.name || formData.boy?.name || "Boy";
    const girl = report.charts?.girl?.birth?.name || formData.girl?.name || "Girl";
    return save({
      type: "matchmaking",
      sourceId: matchId || `${boy}:${girl}:${Date.now()}`,
      title: `${boy} & ${girl}`,
      subtitle: `Match report${report.ashtakoota?.total_score ? ` • ${report.ashtakoota.total_score}/36` : ""}`,
      payload: { matchId, report },
    });
  }

  function open(item) {
    if (!item?.payload) return;
    if (item.type === "lagna" || item.type === "prashna") {
      const state = {
        chart: item.payload.chart,
        mode: item.payload.mode || item.type,
        savedAt: new Date().toISOString(),
      };
      localStorage.setItem(ACTIVE_CHART_KEY, JSON.stringify(state));
      sessionStorage.setItem("kundali_chart_progression", JSON.stringify(state));
      window.location.href = "/index.html";
      return;
    }
    if (item.type === "matchmaking") {
      sessionStorage.setItem(OPEN_MATCH_KEY, JSON.stringify(item.payload));
      window.location.href = "/matchmaking.html";
    }
  }


  function initChartFormSaveWatcher() {
    const checkbox = document.querySelector("#save-chart-checkbox");
    const form = document.querySelector("#prashna-form");
    const result = document.querySelector("#result");
    if (!checkbox || !form || !result) return;
    let pendingSave = false;
    let lastSavedSource = "";

    form.addEventListener("submit", () => {
      pendingSave = Boolean(checkbox.checked);
      [700, 1600, 3200, 5200, 8200].forEach((delay) => {
        window.setTimeout(trySaveActiveChart, delay);
      });
    }, true);

    function trySaveActiveChart() {
      if (!pendingSave || !checkbox.checked || result.classList.contains("hidden")) return;
      try {
        const state = JSON.parse(localStorage.getItem(ACTIVE_CHART_KEY) || "{}");
        const chart = state.chart;
        const source = chart?.id || chart?.meta?.id || chart?.question?.asked_at_utc || "";
        if (!chart || !source || source === lastSavedSource) return;
        const saved = saveChart(chart, { mode: state.mode || chart.meta?.chart_type || "" });
        if (saved.ok) {
          pendingSave = false;
          checkbox.checked = false;
          lastSavedSource = source;
          const status = document.querySelector("#status");
          if (status) status.textContent = "Chart generated and saved to your profile.";
          document.dispatchEvent(new CustomEvent("saved-chart:created", { detail: saved.item }));
        }
      } catch (error) {
        console.warn("Unable to save generated chart:", error);
      }
    }

    new MutationObserver(() => window.setTimeout(trySaveActiveChart, 80)).observe(result, {
      attributes: true,
      attributeFilter: ["class"],
    });
  }

  document.addEventListener("DOMContentLoaded", initChartFormSaveWatcher);

  window.SavedCharts = {
    list,
    save,
    saveChart,
    saveMatch,
    remove,
    open,
    OPEN_MATCH_KEY,
  };
})();
