import { AppState } from './state.js';
import { API } from './api.js';
import { initAuth, savePendingSubmission } from './auth.js?v=oauth-prod-2';
import { showFlash } from './flash.js';
import { KundaliChart } from './chart-engine.js';
import { DashaWidget } from './dasha-engine.js';

// ==========================================
// 1. GLOBAL STATE & CONSTANTS
// ==========================================
let activeTab = "home";
let _placeDebounce = null;
let consultantBooking = null;
let consultantMessages = [];
let activeChartEntries = [];
let activeChartCodes = [];
let pendingPaletteSlot = null;
let dashaStack = [];
let activeDasha = null;
let activeChart = null;

const PERSISTED_CHART_KEY = "kundali_active_chart_state_v2";
const PERSISTED_RESULT_TAB_KEY = "kundali_active_result_tab";
const PERSISTED_PRASHNA_TAB_KEY = "kundali_active_prashna_tab";
const PERSISTED_WIDGETS_KEY = "kundali_result_widgets";
const PERSISTED_DRAFT_KEY = "kundali_entry_draft_v1";
const PERSISTED_WORKSHEET_KEY = "kundali_worksheet_codes_v1";
const PERSISTED_PRASHNA_JOB_KEY = "kundali_pending_prashna_job_v1";

const signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"];
const signNumbers = { Aries: 1, Taurus: 2, Gemini: 3, Cancer: 4, Leo: 5, Virgo: 6, Libra: 7, Scorpio: 8, Sagittarius: 9, Capricorn: 10, Aquarius: 11, Pisces: 12 };
const planetShort = { Asc: "Asc", Sun: "Su", Moon: "Mo", Mars: "Ma", Mercury: "Me", Jupiter: "Ju", Venus: "Ve", Saturn: "Sa", Rahu: "Ra", Ketu: "Ke" };
const planetClass = { Asc: "p-asc", Sun: "p-sun", Moon: "p-moon", Mars: "p-mars", Mercury: "p-mercury", Jupiter: "p-jupiter", Venus: "p-venus", Saturn: "p-saturn", Rahu: "p-rahu", Ketu: "p-ketu" };
const dashaNames = { maha: "Mahadasha", antara: "Antardasha", pratyantara: "Pratyantardasha", sookshma: "Sookshma Dasha", prana: "Prana Dasha" };
const dashaLabels = { Ketu: "Ke", Venus: "Ve", Sun: "Su", Moon: "Mo", Mars: "Ma", Rahu: "Ra", Jupiter: "Ju", Saturn: "Sa", Mercury: "Me" };
const dashaYears = { Ketu: 7, Venus: 20, Sun: 6, Moon: 10, Mars: 7, Rahu: 18, Jupiter: 16, Saturn: 19, Mercury: 17 };
const dashaSequence = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"];
const questionDomainLabels = { wealth: "Wealth / money", marriage: "Marriage / relationship", child: "Child / progeny", job_career: "Job / career", illness: "Illness / health", foreign: "Foreign / travel", education: "Education" };
const jobTypeLabels = { government: "Government job", private: "Private job" };
const domainChartDefaults = { marriage: ["D1", "D9"], child: ["D1", "D7"], job_career: ["D1", "D10"], education: ["D1", "D24"], wealth: ["D1", "D2", "D4", "D9"], foreign: ["D1", "D4", "D9", "D10"], illness: ["D1", "D3", "D6", "D9", "D30"], default: ["D1", "D9"] };
const worksheetPresets = {
  main: ["D1", "D9"],
  divisional: ["D1", "D2", "D3", "D4", "D6", "D7", "D9", "D10", "D12", "D16", "D20", "D24"],
  career: ["D1", "D9", "D10", "D24"],
  marriage: ["D1", "D7", "D9"],
  health: ["D1", "D3", "D6", "D9", "D30"],
};
const northIndianSlots = Array.from({ length: 12 }, (_, index) => ({ house: index + 1, cls: `slot-${index + 1}` }));

// ==========================================
// 2. DOM ELEMENTS
// ==========================================
const form = document.querySelector("#prashna-form");
const statusEl = document.querySelector("#status");
const resultEl = document.querySelector("#result");
const factsEl = document.querySelector("#facts");
const navHome = document.querySelector("#nav-home");
const navConsultant = document.querySelector("#nav-consultant");
const navPricing = document.querySelector("#nav-pricing");
const navAbout = document.querySelector("#nav-about");
const navCommunity = document.querySelector("#nav-community");
const pricingCard = document.querySelector("#pricing-card");
const aboutPlatform = document.querySelector("#about-platform");
const interpretationCard = document.querySelector("#interpretation-card");
const consultantsCard = document.querySelector("#consultants-card");
const consultantsBody = document.querySelector("#consultants-body");
const interpretationDomain = document.querySelector("#interpretation-domain");
const interpretationTitle = document.querySelector("#interpretation-title");
const interpretationConfidence = document.querySelector("#interpretation-confidence");
const interpretationBody = document.querySelector("#interpretation-body");
const planetTable = document.querySelector("#planet-table");
const divisionalChartsEl = document.querySelector("#divisional-charts");
const topicChartTabs = document.querySelector("#topic-chart-tabs");
const worksheetPresetsEl = document.querySelector("#worksheet-presets");
const widgetControls = document.querySelector(".widget-controls");
const chartPicker = document.querySelector("#chart-picker");
const addChartButton = document.querySelector("#add-chart-button");
const resetWorksheetButton = document.querySelector("#reset-worksheet-button");
const panelPalette = document.querySelector("#panel-palette");
const gridResizers = document.querySelectorAll("[data-resize-col]");
const rowResizers = document.querySelectorAll("[data-resize-row]");
const transitSection = document.querySelector("#transit-section");
const transitFacts = document.querySelector("#transit-facts");
const transitTable = document.querySelector("#transit-table");
const dashaTable = document.querySelector("#dasha-table");
const dashaSummary = document.querySelector("#dasha-summary");
const kpSection = document.querySelector("#kp-section");
const kpChartCanvas = document.querySelector("#kp-chart");
const kpPlanetTable = document.querySelector("#kp-planet-table");
const kpCuspTable = document.querySelector("#kp-cusp-table");
const shareLink = document.querySelector("#share-link");
const resultBackButton = document.querySelector("#result-back-button");
const chartTitle = document.querySelector("#chart-title");
const dashaHeading = document.querySelector("#dasha-heading");
const dashaBackButton = document.querySelector("#dasha-back-button");
const dashaPath = document.querySelector("#dasha-path");
const placeSearchInput = document.querySelector("#place_search");
const placeResultsEl = document.querySelector("#place-results");
const modePanel = document.querySelector("#mode-panel");
const changeModeButton = document.querySelector("#change-mode-button");
const formTitle = document.querySelector("#form-title");
const modeEyebrow = document.querySelector("#mode-eyebrow");
const portalGuidanceDesc = document.querySelector(".guidance-desc");
const questionField = document.querySelector("#question-field");
const questionDomainField = document.querySelector("#question-domain-field");
const jobTypeField = document.querySelector("#job-type-field");
const birthFields = document.querySelector("#birth-fields");
const submitButton = document.querySelector("#submit-button");

// ==========================================
// 3. INITIALIZATION & STATE LISTENERS
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
  initAuth();
  recordVisit();
  bindUIEvents();
  initPricingUI();
  initChatExtend();
  initPaidConsultation();
  resumePendingPrashnaJob();
  
  const savedProgression = localStorage.getItem(PERSISTED_CHART_KEY) || sessionStorage.getItem("kundali_chart_progression");
  let restoredChart = false;
  if (savedProgression && !window.location.hash) {
    try {
      const state = JSON.parse(savedProgression);
      if (state.mode) {
        AppState.setMode(state.mode);
        // Dispatch mode changed event if necessary
        const evt = new CustomEvent('astro:modeChanged', { detail: state.mode });
        document.dispatchEvent(evt);
      }
      if (state.chart) {
        restoredChart = true;
        setTimeout(() => {
          renderChart(state.chart, false);
          restoreResultViewState(state.chart);
          document.documentElement.classList.remove("restoring-chart");
        }, 200);
      }
    } catch(e) {
      document.documentElement.classList.remove("restoring-chart");
    }
  }
  
  if (window.location.hash === "#about-platform") activeTab = "about";
  if (window.location.hash === "#pricing") activeTab = "pricing";
  if (!restoredChart) {
    document.documentElement.classList.remove("restoring-chart");
    restoreEntryDraft();
    updateNavigation(false);
  }
});

function persistChartState() {
  if (!activeChart) return;
  try {
    const payload = {
      chart: activeChart,
      mode: AppState.activeMode || activeChart.meta?.chart_type || "",
      savedAt: new Date().toISOString(),
    };
    localStorage.setItem(PERSISTED_CHART_KEY, JSON.stringify(payload));
    sessionStorage.setItem("kundali_chart_progression", JSON.stringify(payload));
  } catch (error) {
    console.warn("Unable to persist chart state:", error);
  }
}

function clearPersistedChartState() {
  localStorage.removeItem(PERSISTED_CHART_KEY);
  sessionStorage.removeItem("kundali_chart_progression");
  localStorage.removeItem(PERSISTED_RESULT_TAB_KEY);
  localStorage.removeItem(PERSISTED_PRASHNA_TAB_KEY);
  localStorage.removeItem(PERSISTED_WIDGETS_KEY);
  localStorage.removeItem(PERSISTED_DRAFT_KEY);
  localStorage.removeItem(PERSISTED_WORKSHEET_KEY);
}

function persistWorksheetState() {
  if (!activeChart || !activeChartCodes.length) return;
  localStorage.setItem(PERSISTED_WORKSHEET_KEY, JSON.stringify({
    chartId: activeChart.id || activeChart.meta?.id || "",
    codes: activeChartCodes,
  }));
}

function getPersistedWorksheetCodes(chart, entries) {
  try {
    const saved = JSON.parse(localStorage.getItem(PERSISTED_WORKSHEET_KEY) || "{}");
    const chartId = chart?.id || chart?.meta?.id || "";
    if (!saved.codes?.length || saved.chartId !== chartId) return null;
    const available = new Set(entries.map((entry) => entry.code));
    return saved.codes.filter((code) => available.has(code));
  } catch (_error) {
    return null;
  }
}

function persistEntryDraft() {
  if (activeChart) return;
  try {
    const draft = {
      mode: AppState.activeMode,
      fields: {
        name: document.querySelector("#name")?.value || "",
        gender: document.querySelector("#gender")?.value || "",
        question: document.querySelector("#question")?.value || "",
        question_domain: document.querySelector("#question_domain")?.value || "",
        job_type: document.querySelector("#job_type")?.value || "",
        birth_date: document.querySelector("#birth_date")?.value || "",
        birth_time: document.querySelector("#birth_time")?.value || "",
        birth_datetime_local: document.querySelector("#birth_datetime_local")?.value || "",
        asked_at_utc: document.querySelector("#asked_at_utc")?.value || "",
        place_search: document.querySelector("#place_search")?.value || "",
        place_name: document.querySelector("#place_name")?.value || "",
        latitude: document.querySelector("#latitude")?.value || "",
        longitude: document.querySelector("#longitude")?.value || "",
      },
      savedAt: new Date().toISOString(),
    };
    localStorage.setItem(PERSISTED_DRAFT_KEY, JSON.stringify(draft));
  } catch (error) {
    console.warn("Unable to persist entry draft:", error);
  }
}

function restoreEntryDraft() {
  try {
    const raw = localStorage.getItem(PERSISTED_DRAFT_KEY);
    if (!raw) return;
    const draft = JSON.parse(raw);
    if (draft.mode) AppState.setMode(draft.mode);
    Object.entries(draft.fields || {}).forEach(([id, value]) => {
      const field = document.querySelector(`#${id}`);
      if (field && value !== undefined) field.value = value;
    });
    syncDateTimeHidden();
    syncQuestionDomainControls();
    if (draft.fields?.place_name && draft.fields?.latitude && draft.fields?.longitude) {
      placeResultsEl.innerHTML = selectedPlaceMessage({
        place_name: draft.fields.place_name,
        latitude: draft.fields.latitude,
        longitude: draft.fields.longitude,
        source: "saved",
      });
      statusEl.textContent = "Restored your saved entry draft.";
    }
  } catch (error) {
    console.warn("Unable to restore entry draft:", error);
  }
}

function restoreResultViewState(chart) {
  const isPrashna = chart?.meta?.chart_type === "prashna";
  if (isPrashna) {
    const tab = localStorage.getItem(PERSISTED_PRASHNA_TAB_KEY) || "interpretation";
    const button = document.querySelector(`#prashna-tabs-nav .tab-btn[data-prashna-tab-button="${tab}"]`);
    window.switchPrashnaTab?.(tab, button);
    return;
  }

  const tab = localStorage.getItem(PERSISTED_RESULT_TAB_KEY) || "overview";
  const button = document.querySelector(`#result-tabs-nav .tab-btn[data-result-tab-button="${tab}"]`);
  window.switchResultTab?.(tab, button);

  try {
    const widgets = JSON.parse(localStorage.getItem(PERSISTED_WIDGETS_KEY) || "{}");
    if (widgets.showKP && !document.body.classList.contains("show-kp")) toggleResultWidget("kp");
    if (widgets.showPlanetary === false && document.body.classList.contains("show-planetary")) toggleResultWidget("planetary");
  } catch (_error) {}
}

function recordVisit() {
  try {
    const keyName = "kundali_visitor_key";
    let visitorKey = localStorage.getItem(keyName);
    if (!visitorKey) {
      visitorKey = `visitor_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
      localStorage.setItem(keyName, visitorKey);
    }
    fetch("/api/analytics/visit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        visitor_key: visitorKey,
        path: window.location.pathname || "/",
        referrer: document.referrer || "",
      }),
      keepalive: true,
    }).catch(() => {});
  } catch (_err) {
    // Analytics should never block chart usage.
  }
}


document.addEventListener('astro:modeChanged', (e) => {
  const isLagna = e.detail === 'lagna';
  modePanel.classList.add("hidden");
  form.classList.remove("hidden");
  form.classList.toggle("lagna-single-step", isLagna);
  form.classList.toggle("prashna-single-step", !isLagna);
  
  formTitle.textContent = isLagna ? "Lagna Kundli" : "Prashna Kundli";
  modeEyebrow.textContent = isLagna ? "Birth chart mode" : "Question chart mode";
  portalGuidanceDesc?.classList.toggle("hidden", isLagna);
  questionField.classList.toggle("hidden", isLagna);
  questionDomainField.classList.toggle("hidden", isLagna);
  jobTypeField.classList.add("hidden");
  birthFields.classList.toggle("hidden", !isLagna);
  document.querySelector("#question").required = !isLagna;
  document.querySelector("#birth_datetime_local").required = isLagna;
  submitButton.textContent = isLagna ? "Get Kundali" : "Get your Prashana Kundali";
  statusEl.textContent = isLagna ? "Enter birth details, then search and select birthplace." : "Ask your question, then search and select current place.";
  window.nextWizardStep?.(1);
  syncQuestionDomainControls();
  persistEntryDraft();
});

// ==========================================
// 4. CORE UI BINDINGS
// ==========================================
function bindUIEvents() {
  bindMobileNavigation();
  bindMobileResultNavigation();

  modePanel.addEventListener("click", (e) => {
    const matchmakingButton = e.target.closest("button[data-matchmaking-link]");
    if (matchmakingButton) {
      window.location.assign("/matchmaking.html");
      return;
    }
    const button = e.target.closest("button[data-mode]");
    if (button) {
      AppState.setMode(button.dataset.mode);
    }
  });

  changeModeButton.addEventListener("click", () => {
    AppState.setMode("");
    clearPersistedChartState();
    activeChart = null;
    form.reset();
    ["birth_datetime_local", "place_name", "latitude", "longitude"].forEach((id) => {
      const field = document.querySelector(`#${id}`);
      if (field) field.value = "";
    });
    placeResultsEl.innerHTML = "";
    document.body.classList.remove("has-result");
    resultEl.classList.add("hidden");
    form.classList.add("hidden");
    form.classList.remove("lagna-single-step");
    form.classList.remove("prashna-single-step");
    portalGuidanceDesc?.classList.remove("hidden");
    modePanel.classList.remove("hidden");
    statusEl.textContent = "";
  });

  resultBackButton?.addEventListener("click", () => {
    const confirmed = window.confirm("If you go back, this chart progression will be removed. Continue?");
    if (!confirmed) return;
    clearPersistedChartState();
    activeChart = null;
    AppState.activeChart = null;
    AppState.setMode("");
    form.reset();
    ["birth_datetime_local", "place_name", "latitude", "longitude"].forEach((id) => {
      const field = document.querySelector(`#${id}`);
      if (field) field.value = "";
    });
    placeResultsEl.innerHTML = "";
    document.body.classList.remove("has-result", "result-lagna", "result-prashna", "has-interpretation", "show-kp");
    document.body.classList.add("show-planetary");
    resultEl.classList.add("hidden");
    form.classList.add("hidden");
    form.classList.remove("lagna-single-step", "prashna-single-step");
    portalGuidanceDesc?.classList.remove("hidden");
    modePanel.classList.remove("hidden");
    statusEl.textContent = "";
    activeTab = "home";
    updateNavigation(true);
  });

  document.querySelector("#use-now-btn")?.addEventListener("click", () => {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    document.querySelector("#birth_date").value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
    document.querySelector("#birth_time").value = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
    syncDateTimeHidden();
  });

  document.querySelector("#birth_date")?.addEventListener("change", syncDateTimeHidden);
  document.querySelector("#birth_time")?.addEventListener("change", syncDateTimeHidden);
  form.addEventListener("input", persistEntryDraft);
  form.addEventListener("change", persistEntryDraft);
  window.addEventListener("pagehide", persistEntryDraft);
  window.addEventListener("beforeunload", persistEntryDraft);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!AppState.session) {
      savePendingSubmission();
      document.querySelector("#auth-modal").classList.remove("hidden");
      statusEl.textContent = "Please sign in with Google to generate your Kundli.";
      return;
    }
    
    if (!hasValidCoordinates()) {
      statusEl.textContent = "Search and select a place first, or enter manual latitude and longitude.";
      return;
    }

    const payload = buildPayload();
    if (!payload) return;

    statusEl.textContent = AppState.activeMode === "lagna" ? "Generating birth chart..." : "Queued. Preparing your Prashna reading...";

    try {
      const data = AppState.activeMode === "lagna"
        ? await API.post("/api/lagna", payload)
        : await submitQueuedPrashna(payload);
      localStorage.removeItem(PERSISTED_DRAFT_KEY);
      renderChart(data.chart);
      statusEl.textContent = "Chart generated and saved.";
    } catch (error) {
      statusEl.textContent = error.message;
    }
  });

  window.safeNavigate = function(url) {
    if (activeChart) {
      if (confirm("You have an active chart. Do you want to save this progression? Click OK to save, Cancel to discard.")) {
        sessionStorage.setItem("kundali_chart_progression", JSON.stringify({ chart: activeChart, mode: AppState.activeMode }));
      } else {
        sessionStorage.removeItem("kundali_chart_progression");
      }
    }
    window.location.assign(url);
  };

  navHome.addEventListener("click", () => { activeTab = "home"; updateNavigation(true); });
  navConsultant?.addEventListener("click", (e) => { e.preventDefault(); safeNavigate("/consultation.html"); });
  navPricing?.addEventListener("click", () => { activeTab = "pricing"; updateNavigation(true); });
  navAbout?.addEventListener("click", (e) => { e.preventDefault(); safeNavigate("/about.html"); });
  navCommunity?.addEventListener("click", (e) => { e.preventDefault(); safeNavigate("/astro-community"); });

  placeSearchInput.addEventListener("input", () => {
    clearTimeout(_placeDebounce);
    const q = placeSearchInput.value.trim();
    if (q.length < 2) { placeResultsEl.innerHTML = ""; return; }
    placeResultsEl.innerHTML = `<div class="place-result muted">Searching…</div>`;
    _placeDebounce = setTimeout(searchPlace, 400);
  });

  placeSearchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); clearTimeout(_placeDebounce); searchPlace(); }
  });

  document.querySelector("#question_domain")?.addEventListener("change", syncQuestionDomainControls);
  addChartButton.addEventListener("click", () => addWorksheetChart(chartPicker.value));
  resetWorksheetButton.addEventListener("click", () => renderDivisionalCharts(activeChart?.divisional_charts, activeChart));
  worksheetPresetsEl?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-worksheet-preset]");
    if (button) applyWorksheetPreset(button.dataset.worksheetPreset);
  });
  widgetControls?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-widget-toggle]");
    if (button) toggleResultWidget(button.dataset.widgetToggle);
  });

  dashaBackButton.addEventListener("click", () => {
    if (dashaStack.length <= 1) return;
    dashaStack.pop();
    const previous = dashaStack[dashaStack.length - 1];
    renderDashaLevel(previous.level, previous.rows, previous.parentPath, false);
  });

  gridResizers.forEach(resizer => {
    resizer.addEventListener("pointerdown", (event) => startGridResize(event, resizer.dataset.resizeCol));
  });

  rowResizers.forEach(resizer => {
    resizer.addEventListener("pointerdown", (event) => startRowResize(event));
  });

  divisionalChartsEl.addEventListener("contextmenu", (event) => {
    event.preventDefault();
    const chartItem = event.target.closest(".worksheet-item");
    if (chartItem) {
      pendingPaletteSlot = chartItem.dataset.code;
      openPanelPaletteAt(event.clientX, event.clientY);
      return;
    }
    if (event.target === divisionalChartsEl) {
      pendingPaletteSlot = null;
      openPanelPaletteAt(event.clientX, event.clientY);
    }
  });

  document.addEventListener("click", (event) => {
    if (panelPalette.classList.contains("hidden")) return;
    if (event.target.closest("#panel-palette") || event.target.closest("#add-chart-button")) return;
    panelPalette.classList.add("hidden");
  });

  document.querySelector("#gps-button")?.addEventListener("click", async () => {
    if (!navigator.geolocation) {
      statusEl.textContent = "GPS not available in this browser.";
      return;
    }
    const btn = document.querySelector("#gps-button");
    btn.disabled = true;
    btn.textContent = "Locating…";
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        document.querySelector("#latitude").value = lat.toFixed(6);
        document.querySelector("#longitude").value = lon.toFixed(6);
        try {
          const data = await API.get(`/api/reverse_geocode?lat=${lat}&lon=${lon}`);
          const name = data.place_name || `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
          document.querySelector("#place_name").value = name;
          placeSearchInput.value = name;
          placeResultsEl.innerHTML = selectedPlaceMessage({ place_name: name, latitude: lat.toFixed(6), longitude: lon.toFixed(6), source: "GPS" });
          statusEl.textContent = `GPS location: ${name}`;
          persistEntryDraft();
        } catch {
          const fallback = `GPS: ${lat.toFixed(4)}, ${lon.toFixed(4)}`;
          document.querySelector("#place_name").value = fallback;
          placeSearchInput.value = fallback;
          placeResultsEl.innerHTML = selectedPlaceMessage({ place_name: fallback, latitude: lat.toFixed(6), longitude: lon.toFixed(6), source: "GPS" });
          persistEntryDraft();
        }
        btn.disabled = false;
        btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/></svg> GPS`;
      },
      (error) => {
        statusEl.textContent = `GPS error: ${error.message}`;
        btn.disabled = false;
        btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/></svg> GPS`;
      },
      { enableHighAccuracy: true, timeout: 12000 }
    );
  });
}

function bindMobileNavigation() {
  const menuButton = document.querySelector("#mobile-menu-button");
  const closeButton = document.querySelector("#mobile-menu-close");
  const drawer = document.querySelector("#mobile-nav-drawer");
  if (!menuButton || !drawer) return;

  const setOpen = (open) => {
    document.body.classList.toggle("mobile-nav-open", open);
    menuButton.setAttribute("aria-expanded", String(open));
    drawer.setAttribute("aria-hidden", String(!open));
  };

  menuButton.addEventListener("click", () => setOpen(!document.body.classList.contains("mobile-nav-open")));
  closeButton?.addEventListener("click", () => setOpen(false));
  drawer.addEventListener("click", (event) => {
    if (event.target === drawer) setOpen(false);
  });
  drawer.querySelector("[data-mobile-login]")?.addEventListener("click", () => {
    setOpen(false);
    document.querySelector("#auth-modal")?.classList.remove("hidden");
  });
  drawer.querySelectorAll("[data-mobile-nav-link]").forEach((link) => {
    link.addEventListener("click", () => setOpen(false));
  });
}

function bindMobileResultNavigation() {
  const button = document.querySelector("#mobile-result-nav-button");
  const drawer = document.querySelector("#mobile-result-drawer");
  const closeButton = document.querySelector("#mobile-result-close");
  if (!button || !drawer) return;

  const setOpen = (open) => {
    document.body.classList.toggle("mobile-result-nav-open", open);
    button.setAttribute("aria-expanded", String(open));
    drawer.setAttribute("aria-hidden", String(!open));
  };

  button.addEventListener("click", () => setOpen(!document.body.classList.contains("mobile-result-nav-open")));
  closeButton?.addEventListener("click", () => setOpen(false));
  drawer.addEventListener("click", (event) => {
    if (event.target === drawer) setOpen(false);
  });
  drawer.querySelectorAll("[data-mobile-result-target]").forEach((item) => {
    item.addEventListener("click", () => {
      openMobileResultTarget(item.dataset.mobileResultTarget);
      setOpen(false);
    });
  });
}

function openMobileResultTarget(target) {
  const isPrashna = document.body.classList.contains("result-prashna");

  if (target === "prashna-charts") {
    window.switchPrashnaTab?.("charts-positions", document.querySelector('#prashna-tabs-nav [data-prashna-tab-button="charts-positions"]'));
    document.querySelector("#prashna-charts-positions")?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }

  if (target === "interpretation") {
    if (isPrashna) {
      window.switchPrashnaTab?.("interpretation", document.querySelector('#prashna-tabs-nav [data-prashna-tab-button="interpretation"]'));
      document.querySelector("#prashna-interpretation")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      window.switchResultTab?.("predictions", document.querySelector('#result-tabs-nav [data-result-tab-button="predictions"]'));
      interpretationCard?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    return;
  }

  if (target === "planets") {
    if (isPrashna) {
      window.switchPrashnaTab?.("charts-positions", document.querySelector('#prashna-tabs-nav [data-prashna-tab-button="charts-positions"]'));
      document.querySelector("#prashna-charts-positions .technical-table-wrap")?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    if (!document.body.classList.contains("show-planetary")) toggleResultWidget("planetary");
    window.switchResultTab?.("overview", document.querySelector('#result-tabs-nav [data-result-tab-button="overview"]'));
    document.querySelector(".planet-card:not(#kp-section)")?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }

  if (target === "kp") {
    if (!document.body.classList.contains("show-kp")) toggleResultWidget("kp");
    window.switchResultTab?.("overview", document.querySelector('#result-tabs-nav [data-result-tab-button="overview"]'));
    document.querySelector("#kp-section")?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }

  if (target === "charts") {
    if (isPrashna) {
      window.switchPrashnaTab?.("charts-positions", document.querySelector('#prashna-tabs-nav [data-prashna-tab-button="charts-positions"]'));
      document.querySelector("#prashna-charts-positions")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      window.switchResultTab?.("charts", document.querySelector('#result-tabs-nav [data-result-tab-button="charts"]'));
      document.querySelector(".worksheet")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    return;
  }

  if (target === "dashas") {
    if (isPrashna) {
      window.switchPrashnaTab?.("charts-positions", document.querySelector('#prashna-tabs-nav [data-prashna-tab-button="charts-positions"]'));
      document.querySelector("#prashna-dasha-container")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      window.switchResultTab?.("dashas", document.querySelector('#result-tabs-nav [data-result-tab-button="dashas"]'));
      document.querySelector(".dasha-card")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    return;
  }

  if (target === "transits") {
    window.switchResultTab?.("transits", document.querySelector('#result-tabs-nav [data-result-tab-button="transits"]'));
    document.querySelector("#transit-section")?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }

  window.switchResultTab?.("overview", document.querySelector('#result-tabs-nav [data-result-tab-button="overview"]'));
  resultEl?.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ==========================================
// 5. HELPER LOGIC
// ==========================================
function syncDateTimeHidden() {
  const d = document.querySelector("#birth_date").value;
  const t = document.querySelector("#birth_time").value || "00:00:00";
  document.querySelector("#birth_datetime_local").value = d && t ? `${d}T${t}` : "";
}

function buildPayload() {
  const location = {
    latitude: Number(document.querySelector("#latitude").value),
    longitude: Number(document.querySelector("#longitude").value),
    place_name: document.querySelector("#place_name").value.trim(),
  };
  const name = document.querySelector("#name").value.trim();
  
  if (name.length < 1) { statusEl.textContent = "Enter a name before generating."; return null; }

  if (AppState.activeMode === "lagna") {
    const birthTime = document.querySelector("#birth_datetime_local").value;
    if (!birthTime) { statusEl.textContent = "Enter birth date and time."; return null; }
    return { name, gender: document.querySelector("#gender").value, birth_datetime_local: birthTime, location };
  }

  const question = document.querySelector("#question").value.trim();
  if (question.length < 3) { statusEl.textContent = "Enter the Prashna question."; return null; }

  const payload = {
    name, question, location,
    question_domain: document.querySelector("#question_domain").value,
    question_subdomain: document.querySelector("#question_domain").value === "job_career" ? document.querySelector("#job_type").value : "",
  };
  
  const overrideTime = document.querySelector("#asked_at_utc").value.trim();
  if (overrideTime) payload.asked_at_utc = overrideTime;
  
  return payload;
}

async function searchPlace() {
  const query = placeSearchInput.value.trim();
  if (query.length < 2) return;
  statusEl.textContent = "Searching place...";
  
  try {
    const data = await API.get(`/api/geocode?query=${encodeURIComponent(query)}&limit=6`);
    renderPlaceResults(data.results);
    statusEl.textContent = data.results.length ? "Select the correct place result." : "No places found.";
  } catch (error) {
    placeResultsEl.innerHTML = "";
    statusEl.textContent = error.message;
  }
}

function renderPlaceResults(results) {
  if (!results.length) { placeResultsEl.innerHTML = `<div class="place-result muted">No results found.</div>`; return; }
  placeResultsEl.innerHTML = results.map((item, index) => `
      <button type="button" class="place-result" data-index="${index}">
        <strong>${escapeHtml(item.place_name)}</strong>
        <span>${item.latitude}, ${item.longitude} · ${escapeHtml(item.source)}</span>
      </button>`
  ).join("");

  placeResultsEl.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => selectPlace(results[Number(button.dataset.index)]));
  });
}

function selectPlace(place) {
  document.querySelector("#latitude").value = Number(place.latitude).toFixed(6);
  document.querySelector("#longitude").value = Number(place.longitude).toFixed(6);
  document.querySelector("#place_name").value = place.place_name;
  placeSearchInput.value = place.place_name;
  placeResultsEl.innerHTML = selectedPlaceMessage(place);
  statusEl.textContent = "Place selected. Coordinates ready.";
  persistEntryDraft();
}

function selectedPlaceMessage(place) {
  return `
    <div class="selected-place">
      <strong>${escapeHtml(place.place_name)}</strong>
      <span>${place.latitude}, ${place.longitude} · ${escapeHtml(place.source || "selected")}</span>
    </div>`;
}

function hasValidCoordinates() {
  const lat = Number(document.querySelector("#latitude").value);
  const lon = Number(document.querySelector("#longitude").value);
  return Number.isFinite(lat) && Number.isFinite(lon) && document.querySelector("#place_name").value.trim();
}

function updateNavigation(scroll = true) {
  const isHome = activeTab === "home";
  const isConsultant = activeTab === "consultant";
  const isPricing = activeTab === "pricing";
  const isAbout = activeTab === "about";
  const hasResult = document.body.classList.contains("has-result");

  navHome.classList.toggle("active", isHome);
  navConsultant.classList.toggle("active", isConsultant);
  navPricing.classList.toggle("active", isPricing);
  navAbout?.classList.toggle("active", isAbout);
  pricingCard?.classList.toggle("hidden", !isPricing);
  aboutPlatform?.classList.toggle("hidden", !isAbout);

  document.body.classList.toggle("view-home", isHome);
  document.body.classList.toggle("view-consultants", isConsultant);
  document.body.classList.toggle("view-pricing", isPricing);
  document.body.classList.toggle("view-about", isAbout);

  if (scroll) {
    if (isHome && hasResult) {
      resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (isConsultant) {
      consultantsCard.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (isPricing) {
      pricingCard.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (isAbout) {
      aboutPlatform.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }
}

// ==========================================
// 6. CHART RENDERING ENGINE
// ==========================================
function renderChart(chart, switchTab = true) {
  activeChart = chart;
  AppState.activeChart = chart;
  if (!AppState.activeMode && chart.meta?.chart_type) AppState.activeMode = chart.meta.chart_type;
  persistChartState();
  document.body.classList.add("has-result");
  resetResultWidgets();
  resultEl.classList.remove("hidden");
  
  const isLagna = chart.meta.chart_type === "lagna";
  document.body.classList.toggle("result-lagna", isLagna);
  document.body.classList.toggle("result-prashna", !isLagna);
  chartTitle.textContent = `${chart.question.name}'s ${isLagna ? "Lagna Kundli" : "Prashna"}`;
  shareLink.href = `/api/charts/${chart.id}`;

  const facts = [
    fact(isLagna ? "Birth Local" : "Asked Local", `${formatDate(chart.question.asked_at_local || chart.question.asked_at_utc)}<br><small>${chart.question.timezone || ""}</small>`),
    fact(isLagna ? "Birth UTC" : "Asked UTC", formatDate(chart.question.asked_at_utc)),
    fact("Place", `${chart.question.place_name}<br>${chart.question.latitude}, ${chart.question.longitude}`),
    fact("Lagna", `${chart.lagna.sign} ${chart.lagna.formatted_degree}<br>${chart.lagna.nakshatra} Pada ${chart.lagna.pada}`),
    fact("Ayanamsa", `${chart.meta.ayanamsa}<br>${chart.meta.ayanamsa_degrees}°`),
  ];
  
  if (!isLagna) {
    const domainValue = questionDomainLabels[chart.question.domain] || "General / not sure";
    const subdomainValue = chart.question.subdomain ? `<br><small>${jobTypeLabels[chart.question.subdomain] || chart.question.subdomain}</small>` : "";
    facts.splice(2, 0, fact("Question Domain", `${domainValue}${subdomainValue}`));
  }
  factsEl.innerHTML = facts.join("");

  renderConsultants(chart);
  renderDivisionalCharts(chart.divisional_charts, chart);
  renderInterpretation(chart.interpretation, chart);
  renderPlanets(chart.planets);
  renderKPSystem(chart.kp_system, chart.planets);
  renderTransit(chart.transit, isLagna);
  renderDasha(normalizeDasha(chart.dashas, chart.question.asked_at_utc));
  showCompleteResultSections();
  
  if (switchTab) {
    activeTab = "home";
    updateNavigation(true);
    resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
  } else if (activeTab === "home") {
    // Just scroll if they are on home tab already
    resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

async function submitQueuedPrashna(payload) {
  const queued = await API.post("/api/prashna", payload);
  if (!queued.job_id) {
    return queued;
  }
  localStorage.setItem(PERSISTED_PRASHNA_JOB_KEY, queued.job_id);

  const startedAt = Date.now();
  const timeoutMs = 120000;
  while (Date.now() - startedAt < timeoutMs) {
    await delay(1500);
    const job = await API.get(`/api/prashna/jobs/${encodeURIComponent(queued.job_id)}`);
    const progress = Number.isFinite(job.progress) ? ` ${job.progress}%` : "";
    if (job.status === "queued") statusEl.textContent = `Queued.${progress}`;
    if (job.status === "calculating_chart") statusEl.textContent = `Calculating chart.${progress}`;
    if (job.status === "generating_answer") statusEl.textContent = `Generating detailed reading.${progress}`;
    if (job.status === "failed") {
      localStorage.removeItem(PERSISTED_PRASHNA_JOB_KEY);
      throw new Error(job.error || "Reading generation failed. Please try again.");
    }
    if (job.status === "done" && job.chart) {
      localStorage.removeItem(PERSISTED_PRASHNA_JOB_KEY);
      return { chart: job.chart, chart_id: job.chart_id, interpretation: job.interpretation, status: "done" };
    }
  }
  throw new Error("Your reading is still processing. Please refresh shortly to check the result.");
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function resumePendingPrashnaJob() {
  const jobId = localStorage.getItem(PERSISTED_PRASHNA_JOB_KEY);
  if (!jobId) return;
  if (!AppState.session && !localStorage.getItem("supabase_token")) return;
  try {
    statusEl.textContent = "Checking your pending Prashna reading...";
    const data = await pollPrashnaJob(jobId, 30000);
    if (data.chart) {
      renderChart(data.chart);
      statusEl.textContent = "Your pending reading is ready.";
    }
  } catch (_err) {
    statusEl.textContent = "";
  }
}

async function pollPrashnaJob(jobId, timeoutMs) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const job = await API.get(`/api/prashna/jobs/${encodeURIComponent(jobId)}`);
    if (job.status === "failed") {
      localStorage.removeItem(PERSISTED_PRASHNA_JOB_KEY);
      throw new Error(job.error || "Reading generation failed.");
    }
    if (job.status === "done" && job.chart) {
      localStorage.removeItem(PERSISTED_PRASHNA_JOB_KEY);
      return { chart: job.chart, chart_id: job.chart_id, interpretation: job.interpretation, status: "done" };
    }
    await delay(1500);
  }
  return {};
}

function showCompleteResultSections() {
  const isPrashna = document.body.classList.contains("result-prashna");
  
  // Toggle the tab navigation headers
  document.getElementById("result-tabs-nav")?.classList.toggle("hidden", isPrashna);
  document.getElementById("prashna-tabs-nav")?.classList.toggle("hidden", !isPrashna);

  document.querySelectorAll(".result-tab-content").forEach((section) => {
    // Hide standard tabs if in prashna mode, show if in lagna mode (unless already explicitly hidden)
    if (isPrashna) {
      section.style.display = "none";
    } else {
      section.style.display = "";
    }
  });
  
  document.querySelectorAll(".prashna-tab-content").forEach((section) => {
    if (!isPrashna) {
      section.classList.add("hidden");
    }
  });

  if (isPrashna) {
    window.switchPrashnaTab?.("interpretation", document.querySelector("#prashna-tabs-nav .tab-btn"));
  } else {
    window.switchResultTab?.("overview", document.querySelector("#result-tabs-nav .tab-btn"));
  }

  window.showCompleteResultPage?.();
}

function resetResultWidgets() {
  document.body.classList.remove("show-kp");
  document.body.classList.add("show-planetary");
  document.querySelectorAll("[data-widget-toggle]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.widgetToggle === "planetary"));
  });
}

function toggleResultWidget(name) {
  const className = name === "kp" ? "show-kp" : "show-planetary";
  document.body.classList.toggle(className);
  document.querySelectorAll(`[data-widget-toggle="${name}"]`).forEach((button) => {
    button.setAttribute("aria-pressed", String(document.body.classList.contains(className)));
  });
  localStorage.setItem(PERSISTED_WIDGETS_KEY, JSON.stringify({
    showKP: document.body.classList.contains("show-kp"),
    showPlanetary: document.body.classList.contains("show-planetary"),
  }));
  if (name === "kp" && document.body.classList.contains("show-kp")) {
    requestAnimationFrame(renderKPChart);
  }
}

function fact(label, value) {
  return `<div class="fact"><span>${label}</span><strong>${value}</strong></div>`;
}

function renderInterpretation(interpretation, chart = null) {
  if (chart?.meta?.chart_type === "prashna") {
    renderPrashnaInterpretation(interpretation, chart);
    return;
  }
  if (!interpretation) {
    if (chart?.meta?.chart_type !== "prashna") {
      interpretationCard.classList.add("hidden");
      document.body.classList.remove("has-interpretation");
      interpretationBody.innerHTML = "";
      return;
    }
    interpretationCard.classList.remove("hidden");
    document.body.classList.add("has-interpretation");
    interpretationDomain.textContent = "Prashna interpretation";
    interpretationTitle.textContent = "Interpretation Not Generated";
    interpretationConfidence.textContent = "needs refresh";
    interpretationConfidence.dataset.level = "uncertain";
    interpretationBody.innerHTML = `
      <div class="interpretation-answer interpretation-missing">
        <span>Astrologer interpretation</span>
        <section>
          <h4>Interpretation not available for this saved response</h4>
          <p>Generate the Prashna again after restarting the local server so the latest backend can attach the deep reading.</p>
        </section>
      </div>`;
    return;
  }
  
  interpretationCard.classList.remove("hidden");
  document.body.classList.add("has-interpretation");
  interpretationDomain.textContent = `${interpretation.domain || "Prashna"} interpretation`;
  interpretationTitle.textContent = interpretation.title || "Prashna Reading";
  interpretationConfidence.textContent = `${interpretation.confidence || "low"} confidence`;
  interpretationConfidence.dataset.level = interpretation.verdict?.level || "uncertain";

  let answer = "";
  if (interpretation.answer?.text) {
    answer = `<div class="interpretation-answer"><span>Astrologer interpretation</span>${formatAnswerText(interpretation.answer.text)}</div>`;
  } else {
    answer = `<div class="interpretation-answer interpretation-missing"><span>LLM interpretation required</span><section><h4>No local interpretation was generated</h4><p>${escapeHtml(interpretation.answer?.error || interpretation.answer?.note || "Configure Gemini or OpenAI for this Prashna reading.")}</p></section></div>`;
  }
  interpretationBody.innerHTML = answer;
}

function renderPrashnaInterpretation(interpretation, chart) {
  interpretationCard.classList.remove("hidden");
  document.body.classList.add("has-interpretation");
  const domain = questionDomainLabels[chart.question?.domain] || "Prashna";
  interpretationDomain.textContent = `${domain} interpretation`;
  interpretationTitle.textContent = interpretation?.title || `${domain} Prashna Reading`;
  interpretationConfidence.textContent = `${interpretation?.confidence || "medium"} confidence`;
  interpretationConfidence.dataset.level = interpretation?.verdict?.level || "uncertain";

  const normalized = normalizeDasha(chart.dashas, chart.question?.asked_at_utc);
  const activeDasha = [
    normalized?.current_mahadasha?.lord,
    normalized?.current_antardasha?.lord,
    normalized?.current_pratyantardasha?.lord,
  ].filter(Boolean).join(" > ") || "Dasha data not available";
  const moon = chart.planets?.find((p) => p.name === "Moon") || {};
  const domainHouse = prashnaDomainHouse(chart.question?.domain);
  const answerText = interpretation?.answer?.text || "";
  const quickVerdict = interpretation?.verdict?.summary || firstSentence(answerText) || fallbackPrashnaVerdict(chart);

  const interpretationTab = document.getElementById("prashna-interpretation");
  const chartsTab = document.getElementById("prashna-charts-positions");

  interpretationTab.innerHTML = `
    <div class="prashna-reading-content">
      <section class="quick-verdict-box">
        <span>Quick Verdict</span>
        <p>${escapeHtml(quickVerdict)}</p>
      </section>

      <section class="core-analysis-box">
        <h4>Core Analysis</h4>
        <ul>
          <li><strong>Lagna:</strong> ${escapeHtml(chart.lagna?.sign || "-")} ${escapeHtml(chart.lagna?.formatted_degree || "")}, ${escapeHtml(chart.lagna?.nakshatra || "-")} Pada ${escapeHtml(chart.lagna?.pada || "-")}. This shows the immediate body of the question and how strongly the matter can manifest.</li>
          <li><strong>Moon:</strong> ${escapeHtml(moon.sign || "-")} ${escapeHtml(moon.formatted_degree || "")}, house ${escapeHtml(moon.house || "-")}, ${escapeHtml(moon.nakshatra || "-")} Pada ${escapeHtml(moon.pada || "-")}. Moon reflects the querent's mind and the urgency behind the query.</li>
          <li><strong>Question house:</strong> For ${escapeHtml(domain)}, judge mainly the ${domainHouse} along with its lord, occupants, and aspects.</li>
          <li><strong>Dasha timing:</strong> Active Vimshottari sequence is ${escapeHtml(activeDasha)}. Use this period chain for practical timing and event activation.</li>
        </ul>
      </section>

      ${answerText ? `<section class="prashna-full-reading"><h4>Detailed Reading</h4>${formatAnswerText(answerText)}</section>` : `<section class="prashna-full-reading interpretation-missing"><h4>Detailed Reading</h4><p>No local LLM interpretation was generated. The structured Prashna snapshot above is built from the chart data.</p></section>`}
      
      <section class="consult-rupesh-box prashna-consult-cta">
        <div>
          <span>Consult an Astrologer for Deeper Analysis</span>
          <p>Your question, birth/prashna details, time, place, charts and planetary positions will be shared with the astrologer.</p>
        </div>
        <button type="button" class="btn-primary" data-consult-rupesh>Book Consultation</button>
      </section>
    </div>`;

  chartsTab.innerHTML = `
    <div class="prashna-technical-content">
      <section class="technical-section">
        <h3>Divisional Charts</h3>
        <div class="technical-chart-grid">
          ${renderTechnicalChartSlot("D1")}
          ${renderTechnicalChartSlot("D9")}
          ${renderTechnicalChartSlot(chart.question?.domain === "illness" ? "D6" : "D10")}
        </div>
      </section>

      <section class="technical-section">
        <h3>Planetary Positions</h3>
        <div class="technical-table-wrap">
          <table>
            <thead><tr><th>Planet</th><th>Sign</th><th>Degree</th><th>House</th><th>Nakshatra</th><th>Pada</th><th>Motion</th></tr></thead>
            <tbody>${(chart.planets || []).map((p) => `<tr><td>${escapeHtml(p.name)}</td><td>${escapeHtml(p.sign)}</td><td>${escapeHtml(p.formatted_degree)}</td><td>${escapeHtml(p.house)}</td><td>${escapeHtml(p.nakshatra)}</td><td>${escapeHtml(p.pada)}</td><td>${p.retrograde ? "Retrograde" : "Direct"}</td></tr>`).join("")}</tbody>
          </table>
        </div>
      </section>

      <section class="technical-section">
        <h3>Dasha Periods</h3>
        <div id="prashna-dasha-container" class="prashna-dasha-container"></div>
      </section>
    </div>`;

  bindPrashnaInterpretationUI(chart);
}

function bindPrashnaInterpretationUI(chart) {
  const interpretationTab = document.getElementById("prashna-interpretation");
  interpretationTab.querySelector("[data-consult-rupesh]")?.addEventListener("click", () => {
    sessionStorage.setItem("kundali_chart_progression", JSON.stringify({ chart, mode: AppState.activeMode }));
    window.location.assign("/consultation.html");
  });
  
  const chartsTab = document.getElementById("prashna-charts-positions");
  chartsTab.querySelectorAll(".technical-chart-card canvas").forEach((canvas) => {
    const code = canvas.id.replace("prashna-tech-", "").toUpperCase();
    const entry = activeChartEntries.find((item) => item.code.toLowerCase() === code.toLowerCase());
    if (entry) new KundaliChart(canvas, entry.chart, { responsive: true });
  });

  const dashaContainer = chartsTab.querySelector("#prashna-dasha-container");
  if (dashaContainer && chart.dashas) {
    const normalized = normalizeDasha(chart.dashas, chart.question?.asked_at_utc);
    new DashaWidget(dashaContainer, normalized, {
      personLabel: "Prashna",
      variant: "workstation",
    }).render();
  }
}

function renderTechnicalChartSlot(code) {
  const entry = activeChartEntries.find((item) => item.code === code);
  if (!entry) return "";
  return `
    <section class="technical-chart-card">
      <h4>${entry.code} <span>${escapeHtml(entry.title || "")}</span></h4>
      <canvas id="prashna-tech-${entry.code.toLowerCase()}" class="responsive-canvas kundali-canvas"></canvas>
    </section>`;
}

function renderPrashnaTechnicalCharts() {
  interpretationBody.querySelectorAll(".technical-chart-card canvas").forEach((canvas) => {
    const code = canvas.id.replace("prashna-tech-", "").toUpperCase();
    const entry = activeChartEntries.find((item) => item.code.toLowerCase() === code.toLowerCase());
    if (entry) new KundaliChart(canvas, entry.chart, { responsive: true });
  });
}

function firstSentence(text) {
  return String(text || "").replace(/\s+/g, " ").split(/(?<=[.!?])\s+/)[0]?.slice(0, 220) || "";
}

function fallbackPrashnaVerdict(chart) {
  const domain = questionDomainLabels[chart.question?.domain] || "the matter";
  return `The Prashna shows ${domain.toLowerCase()} can be judged from the Lagna, Moon, and relevant house; final timing depends on the active Dasha sequence.`;
}

function prashnaDomainHouse(domain) {
  const map = {
    illness: "6th house for disease, obstacles, treatment, and recovery",
    marriage: "7th house for relationship and marriage outcome",
    child: "5th house for progeny and blessings",
    job_career: "10th house for career status, with 6th house for service/job competition",
    wealth: "2nd and 11th houses for money, income, and gains",
    foreign: "9th and 12th houses for long-distance movement and foreign residence",
    education: "4th and 5th houses for study, learning, and merit",
  };
  return map[domain] || "relevant bhava connected to the question";
}

// ==========================================
// 7. CONSULTANT & CHAT UI
// ==========================================
async function renderConsultants(chart) {
  consultantBooking = null;
  consultantMessages = [];
  consultantsCard.classList.remove("hidden");
  const isLagna = chart.meta.chart_type === "lagna";
  const isPrashna = chart.meta.chart_type === "prashna";

  consultantsBody.innerHTML = `<div class="consultants-loading"><span></span>Loading consultants\u2026</div>`;

  let consultants = [];
  try {
    const data = await API.get("/api/consultants");
    consultants = Array.isArray(data.consultants) ? data.consultants : [];
  } catch {
    consultantsBody.innerHTML = `<p class="consult-error">Could not load consultants. Please refresh.</p>`;
    return;
  }

  if (!consultants.length) {
    consultantsBody.innerHTML = `<p class="consult-error status-error" style="text-align:center; padding: 40px; font-weight: 600;">Currently no consultant is available</p>`;
    return;
  }

  const avatarColors = ["#155d54","#7c3d6b","#4a6c3d","#2d5a8c","#8c5c2d","#3d4a8c","#6b3d3d","#2d8c6b"];
  const makeInitials = (name) => name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);

  const renderCard = (c, idx) => {
    const color = avatarColors[idx % avatarColors.length];
    const initials = makeInitials(c.name);
    const tags = (c.specialties || []).map(s => `<span class="consultant-tag">${escapeHtml(s)}</span>`).join("");
    const exp = c.experience_years ? `${c.experience_years} yrs experience` : "Experienced astrologer";
    return `
      <div class="astrologer-card" data-consultant-id="${escapeHtml(c.id)}" tabindex="0" role="button">
        <div class="astrologer-card-inner">
          <div class="astrologer-avatar" style="background:${color}">${initials}</div>
          <div class="astrologer-info">
            <div class="astrologer-name-row"><h4>${escapeHtml(c.name)}</h4><span class="avail-badge">Available</span></div>
            <p class="astrologer-exp">${escapeHtml(exp)}</p>
            <div class="astrologer-tags">${tags}</div>
          </div>
          <div class="astrologer-chevron"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg></div>
        </div>
        <div class="astrologer-form-wrap" id="form-wrap-${escapeHtml(c.id)}"></div>
      </div>`;
  };

  consultantsBody.innerHTML = `
    <div class="consultants-intro"><p>Select an astrologer to book a one-to-one consultation.</p></div>
    <div class="astrologers-grid">${consultants.map((c, i) => renderCard(c, i)).join("")}</div>
  `;

  consultantsBody.querySelectorAll(".astrologer-card").forEach((card) => {
    const toggle = (e) => {
      if (e && e.target.closest(".astrologer-form-wrap")) return;
      const cId = card.dataset.consultantId;
      const isOpen = card.classList.contains("is-open");
      consultantsBody.querySelectorAll(".astrologer-card.is-open").forEach(c => {
        c.classList.remove("is-open");
        c.querySelector(".astrologer-form-wrap").innerHTML = "";
      });
      if (!isOpen) {
        card.classList.add("is-open");
        const consultant = consultants.find(c => c.id === cId);
        renderConsultationFormInCard(card.querySelector(".astrologer-form-wrap"), cId, consultant, isPrashna, isLagna);
        card.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    };
    card.addEventListener("click", toggle);
  });
}

function renderConsultationFormInCard(wrap, consultantId, consultant, isPrashna, isLagna) {
  const name = consultant?.name || consultantId;
  wrap.innerHTML = `
    <div class="card-form-header">
      <h5>Consult with ${escapeHtml(name)}</h5>
    </div>
    <div class="consultation-options">
      ${isPrashna ? `<button type="button" class="consult-type-btn" data-consult-type="same_prashna" data-cid="${escapeHtml(consultantId)}">Use this Prashna Kundli</button>` : ""}
      ${isLagna ? `<button type="button" class="consult-type-btn" data-consult-type="lagna" data-cid="${escapeHtml(consultantId)}">Use this Lagna Kundli</button>` : ""}
      <button type="button" class="consult-type-btn" data-consult-type="kundali" data-cid="${escapeHtml(consultantId)}">New Kundali question</button>
    </div>
    <div class="chat-entry-wrap"></div>
  `;
  
  wrap.querySelectorAll(".consult-type-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      wrap.querySelectorAll(".consult-type-btn").forEach(b => b.classList.toggle("is-active", b === btn));
      renderChatEntryForm(wrap.querySelector(".chat-entry-wrap"), btn.dataset.consultType, btn.dataset.cid, consultant);
    });
  });
}

function renderChatEntryForm(wrap, type, consultantId, consultant) {
  const isChartBacked = type === "same_prashna" || type === "lagna";
  const cName = consultant?.name || consultantId;
  const chartSummary = isChartBacked && activeChart ? consultationChartSummary(activeChart) : "";

  wrap.innerHTML = `
    <form id="chat-entry-form" class="chat-entry-form">
      <input type="hidden" name="consultation_type" value="${type}" />
      <input type="hidden" name="consultant_id_val" value="${escapeHtml(consultantId)}" />
      ${isChartBacked ? `<div class="consult-chart-preview">${chartSummary}</div>` : kundaliConsultFields()}
      <div class="consult-grid">
        <label>Your name<input name="client_name" required value="${escapeHtml(activeChart?.question?.name || "")}" placeholder="Full name" /></label>
        <label>Email<input name="client_email" type="email" required placeholder="you@example.com" /></label>
      </div>
      <label>Phone / WhatsApp<input name="client_phone" required placeholder="+91…" /></label>
      ${isChartBacked ? `<label class="confirm-share"><input name="confirm_share" type="checkbox" required /> I confirm sharing this chart data with ${escapeHtml(cName)}.</label>` : ""}
      <div class="actions">
        <button type="submit" class="chat-open-btn">Open Chat</button>
      </div>
    </form>
  `;

  wrap.querySelector("#chat-entry-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(event.target);
    const submitBtn = wrap.querySelector(".chat-open-btn");
    submitBtn.disabled = true;
    submitBtn.textContent = "Opening…";

    const payload = {
      consultant_id: String(fd.get("consultant_id_val") || consultantId),
      consultation_type: String(fd.get("consultation_type")),
      client_name: String(fd.get("client_name") || "").trim(),
      client_email: String(fd.get("client_email") || "").trim(),
      client_phone: String(fd.get("client_phone") || "").trim(),
      query_text: "Chat consultation started",
    };
    
    if (isChartBacked) {
      payload.chart_id = activeChart?.id || "";
      payload.chart = activeChart;
    } else {
      payload.birth_details = {
        name: payload.client_name,
        gender: String(fd.get("gender") || ""),
        birth_datetime_local: String(fd.get("birth_datetime_local") || ""),
        place_name: String(fd.get("birth_place_name") || ""),
      };
    }

    try {
      const data = await API.post("/api/consultants/bookings", payload);
      consultantBooking = data.booking;
      consultantMessages = data.messages || [];
      renderChatInterface(wrap, consultant, consultantId);
    } catch (err) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Open Chat";
      wrap.insertAdjacentHTML("beforeend", `<p class="chat-error">${escapeHtml(err.message)}</p>`);
    }
  });
}

function renderChatInterface(wrap, consultant, consultantId) {
  const cName = consultant?.name || consultantId;
  const initials = cName.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
  const typeLabel = consultationTypeLabel(consultantBooking.consultation_type);

  wrap.innerHTML = `
    <div class="chat-ui">
      <div class="chat-topbar">
        <div class="chat-topbar-avatar">${initials}</div>
        <div class="chat-topbar-info">
          <strong>${escapeHtml(cName)}</strong>
          <span>${escapeHtml(typeLabel)} · Ref: ${escapeHtml(consultantBooking.id.slice(0,8))}</span>
        </div>
      </div>
      <div class="chat-messages-area" id="chat-messages-area">
        <div class="chat-system-msg"><span>Consultation started · ${escapeHtml(typeLabel)}</span></div>
        <div class="chat-bubble astrologer">
          <div class="bubble-avatar">${initials}</div>
          <div class="bubble-body">
            <div class="bubble-text">Namaste 🙏 I'm ${escapeHtml(cName)}. Please share your question.</div>
            <div class="bubble-time">Now</div>
          </div>
        </div>
        ${consultantMessages.map(m => renderChatBubble(m, initials)).join("")}
      </div>
      <form id="chat-send-form" class="chat-input-bar">
        <input id="chat-input" name="message_text" autocomplete="off" required placeholder="Type your question..." />
        <button type="submit" class="chat-send-btn">Send</button>
      </form>
    </div>
  `;

  const messagesArea = wrap.querySelector("#chat-messages-area");
  messagesArea.scrollTop = messagesArea.scrollHeight;

  wrap.querySelector("#chat-send-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = wrap.querySelector("#chat-input");
    const text = input.value.trim();
    if (!text || !consultantBooking) return;

    const tempBubble = document.createElement("div");
    tempBubble.className = "chat-bubble user";
    tempBubble.innerHTML = `<div class="bubble-body"><div class="bubble-text">${escapeHtml(text)}</div><div class="bubble-time">Sending…</div></div>`;
    messagesArea.appendChild(tempBubble);
    messagesArea.scrollTop = messagesArea.scrollHeight;
    input.value = "";
    input.focus();

    try {
      const data = await API.post(`/api/consultants/bookings/${consultantBooking.id}/messages`, {
        sender_role: "user", 
        sender_name: consultantBooking.client_name, 
        message_text: text 
      });
      
      consultantMessages = data.messages || [];
      const systemMsg = messagesArea.querySelector(".chat-system-msg");
      const greetBubble = messagesArea.querySelector(".chat-bubble.astrologer");
      messagesArea.innerHTML = "";
      if (systemMsg) messagesArea.appendChild(systemMsg);
      if (greetBubble) messagesArea.appendChild(greetBubble);
      
      consultantMessages.forEach(m => messagesArea.insertAdjacentHTML("beforeend", renderChatBubble(m, initials)));
      messagesArea.scrollTop = messagesArea.scrollHeight;
    } catch {
      tempBubble.querySelector(".bubble-time").textContent = "⚠ Failed";
    }
  });
}

function renderChatBubble(message, astrologerInitials) {
  const isUser = message.sender_role === "user";
  const timeStr = message.created_at ? formatDate(message.created_at) : "";
  if (isUser) {
    return `<div class="chat-bubble user"><div class="bubble-body"><div class="bubble-text">${escapeHtml(message.message_text)}</div><div class="bubble-time">${escapeHtml(timeStr)}</div></div></div>`;
  }
  return `<div class="chat-bubble astrologer"><div class="bubble-avatar">${escapeHtml(astrologerInitials)}</div><div class="bubble-body"><div class="bubble-text">${escapeHtml(message.message_text)}</div><div class="bubble-time">${escapeHtml(timeStr)}</div></div></div>`;
}

function kundaliConsultFields() {
  return `
    <div class="consult-grid">
      <label>Birth date and time
        <div class="dt-picker-group">
          <div class="dt-inputs"><input name="birth_date" type="date" required /><input name="birth_time" type="time" step="1" required /></div>
        </div>
      </label>
      <label>Gender
        <select name="gender"><option value="male">Male</option><option value="female">Female</option><option value="other">Other</option></select>
      </label>
    </div>
    <label>Birth place<input name="birth_place_name" required placeholder="City, state, country" /></label>
  `;
}

function consultationTypeLabel(type) {
  if (type === "same_prashna") return "Same Prashna Kundli";
  if (type === "lagna") return "Use this Lagna Kundli";
  return "Question about Kundli";
}

function consultationChartSummary(chart) {
  const question = chart.question?.text ? `<p><strong>Question:</strong> ${escapeHtml(chart.question.text)}</p>` : "";
  return `<p><strong>Name:</strong> ${escapeHtml(chart.question?.name || "")}</p>${question}<p><strong>Time:</strong> ${escapeHtml(chart.question?.asked_at_local || chart.question?.asked_at_utc || "")}</p><p><strong>Place:</strong> ${escapeHtml(chart.question?.place_name || "")}</p><p><strong>Lagna:</strong> ${escapeHtml(chart.lagna?.sign || "")} ${escapeHtml(chart.lagna?.formatted_degree || "")}</p>`;
}

function formatAnswerText(text) {
  return escapeHtml(text).split(/\n{2,}/).map((paragraph) => {
    const lines = paragraph.split("\n");
    if (lines.length > 1 && lines[0].length <= 42) {
      return `<section><h4>${lines[0]}</h4><p>${lines.slice(1).join("\n").replaceAll("\n", "<br>")}</p></section>`;
    }
    return `<p>${paragraph.replaceAll("\n", "<br>")}</p>`;
  }).join("");
}

function formatSnakeLabel(value) {
  return String(value).replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

// ==========================================
// 8. WORKSHEET / DIVISIONAL CHARTS
// ==========================================
function renderDivisionalCharts(charts, chart) {
  activeChartEntries = normalizeDivisionalChartEntries(charts);
  const preferredCodes = getPersistedWorksheetCodes(chart, activeChartEntries) || getDefaultChartCodes(chart, activeChartEntries);
  activeChartCodes = preferredCodes;
  renderWorksheetPresets();
  renderChartPicker();
  renderTopicTabs();
  renderWorksheet();
  renderPanelPalette();
}

function syncQuestionDomainControls() {
  const isJob = AppState.activeMode === "prashna" && document.querySelector("#question_domain").value === "job_career";
  jobTypeField.classList.toggle("hidden", !isJob);
}

function getDefaultChartCodes(chart, entries) {
  const available = new Set(entries.map((entry) => entry.code));
  const domain = chart?.question?.domain || "default";
  const defaults = domainChartDefaults[domain] || domainChartDefaults.default;
  return defaults.filter((code) => available.has(code));
}

function renderChartPicker() {
  const available = activeChartEntries.filter((entry) => !activeChartCodes.includes(entry.code));
  chartPicker.innerHTML = (available.length ? available : activeChartEntries)
    .map((entry) => `<option value="${entry.code}">${entry.code} ${entry.title}</option>`).join("");
}

function renderWorksheetPresets(activePreset = "main") {
  if (!worksheetPresetsEl) return;
  worksheetPresetsEl.querySelectorAll("[data-worksheet-preset]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.worksheetPreset === activePreset);
  });
}

function applyWorksheetPreset(name) {
  const preset = worksheetPresets[name] || worksheetPresets.main;
  const available = new Set(activeChartEntries.map((entry) => entry.code));
  const selected = preset.filter((code) => available.has(code)).slice(0, 12);
  if (!selected.length) return;
  pendingPaletteSlot = null;
  activeChartCodes = selected;
  persistWorksheetState();
  renderWorksheetPresets(name);
  renderChartPicker();
  renderTopicTabs();
  renderWorksheet();
  renderPanelPalette();
}

function renderTopicTabs() {
  topicChartTabs.innerHTML = activeChartCodes.map((code) => {
    const entry = activeChartEntries.find((item) => item.code === code);
    return `<button type="button" class="chart-tab" data-code="${code}">${code}<span>${entry?.title || ""}</span></button>`;
  }).join("");
  topicChartTabs.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => focusWorksheetChart(button.dataset.code));
  });
}

function renderWorksheet() {
  divisionalChartsEl.dataset.chartCount = String(activeChartCodes.length);
  divisionalChartsEl.innerHTML = activeChartCodes.map((code) => {
    const entry = activeChartEntries.find((item) => item.code === code);
    return `
      <section class="worksheet-item" data-code="${code}" draggable="true">
        <div class="worksheet-item-head">
          <div><strong>${code}</strong><span>${entry?.title || ""}</span></div>
          <button type="button" data-remove="${code}" title="Remove chart">x</button>
        </div>
        <button type="button" class="chart-surface" data-inspect="${code}">
          <canvas id="chart-${code.toLowerCase()}" class="responsive-canvas kundali-canvas"></canvas>
        </button>
      </section>`;
  }).join("");
  
  activeChartCodes.forEach((code) => {
    const entry = activeChartEntries.find((item) => item.code === code);
    if (entry) renderCanvasChart(`#chart-${code.toLowerCase()}`, entry.chart);
  });
  enableWorksheetInteractions();
}

function addWorksheetChart(code) {
  if (pendingPaletteSlot) {
    replaceWorksheetChart(pendingPaletteSlot, code);
    pendingPaletteSlot = null;
    return;
  }
  if (!code || activeChartCodes.includes(code)) {
    const next = activeChartEntries.find((entry) => !activeChartCodes.includes(entry.code));
    if (!next) return;
    code = next.code;
  }
  if (activeChartCodes.length >= 12) {
    showFlash("Worksheet can show up to 12 chart panes. Remove one before adding another.", "error");
    return;
  }
  activeChartCodes.push(code);
  persistWorksheetState();
  panelPalette.classList.add("hidden");
  renderChartPicker();
  renderTopicTabs();
  renderWorksheet();
  renderPanelPalette();
  focusWorksheetChart(code);
}

function replaceWorksheetChart(oldCode, newCode) {
  if (!oldCode || !newCode || oldCode === newCode) {
    panelPalette.classList.add("hidden");
    return;
  }
  const oldIndex = activeChartCodes.indexOf(oldCode);
  if (oldIndex === -1) return;
  const existingIndex = activeChartCodes.indexOf(newCode);
  if (existingIndex !== -1) {
    activeChartCodes[existingIndex] = oldCode;
  }
  activeChartCodes[oldIndex] = newCode;
  persistWorksheetState();
  panelPalette.classList.add("hidden");
  renderChartPicker();
  renderTopicTabs();
  renderWorksheet();
  renderPanelPalette();
  focusWorksheetChart(newCode);
}

function swapWorksheetCharts(sourceCode, targetCode) {
  if (!sourceCode || !targetCode || sourceCode === targetCode) return;
  const sourceIndex = activeChartCodes.indexOf(sourceCode);
  const targetIndex = activeChartCodes.indexOf(targetCode);
  if (sourceIndex === -1 || targetIndex === -1) return;
  [activeChartCodes[sourceIndex], activeChartCodes[targetIndex]] = [activeChartCodes[targetIndex], activeChartCodes[sourceIndex]];
  persistWorksheetState();
  renderTopicTabs();
  renderWorksheet();
}

function focusWorksheetChart(code) {
  const item = divisionalChartsEl.querySelector(`[data-code="${code}"]`);
  if (!item) return;
  item.classList.add("is-focused");
  item.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
  setTimeout(() => item.classList.remove("is-focused"), 900);
}

function enableWorksheetInteractions() {
  divisionalChartsEl.querySelectorAll("[data-remove]").forEach((button) => {
    button.addEventListener("click", () => {
      activeChartCodes = activeChartCodes.filter((code) => code !== button.dataset.remove);
      persistWorksheetState();
      renderChartPicker();
      renderTopicTabs();
      renderWorksheet();
      renderPanelPalette();
    });
  });
  divisionalChartsEl.querySelectorAll(".worksheet-item").forEach((item) => {
    item.addEventListener("dragstart", (event) => {
      event.dataTransfer.setData("text/plain", item.dataset.code);
      event.dataTransfer.effectAllowed = "move";
    });
    item.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      item.classList.add("is-drop-target");
    });
    item.addEventListener("dragleave", () => item.classList.remove("is-drop-target"));
    item.addEventListener("drop", (event) => {
      event.preventDefault();
      item.classList.remove("is-drop-target");
      swapWorksheetCharts(event.dataTransfer.getData("text/plain"), item.dataset.code);
    });
  });
}

function togglePanelPalette() {
  renderPanelPalette();
  if (panelPalette.classList.contains("hidden")) {
    const buttonRect = addChartButton.getBoundingClientRect();
    openPanelPaletteAt(buttonRect.left, buttonRect.bottom);
    return;
  }
  panelPalette.classList.add("hidden");
}

function openPanelPaletteAt(clientX, clientY) {
  renderPanelPalette();
  panelPalette.classList.remove("hidden");
  const worksheetRect = panelPalette.parentElement.getBoundingClientRect();
  const paletteWidth = 420;
  const left = Math.max(8, Math.min(clientX - worksheetRect.left - 24, worksheetRect.width - paletteWidth - 8));
  const top = Math.max(44, Math.min(clientY - worksheetRect.top + 10, worksheetRect.height - 280));
  panelPalette.style.left = `${left}px`;
  panelPalette.style.right = "auto";
  panelPalette.style.top = `${top}px`;
}

function renderPanelPalette() {
  const categories = [
    { title: "Core Charts", codes: ["D1", "D2", "D3", "D4", "D6", "D7", "D9", "D10"] },
    { title: "Varga Detail", codes: ["D12", "D16", "D20", "D24", "D27", "D30", "D40", "D45", "D60"] },
  ];
  panelPalette.innerHTML = categories.map((category) => `
    <section>
      <h4>${category.title}</h4>
      <div class="panel-palette-grid">
        ${category.codes.map((code) => {
          const entry = activeChartEntries.find((item) => item.code === code);
          if (!entry) return "";
          const disabled = pendingPaletteSlot ? code === pendingPaletteSlot : activeChartCodes.includes(code);
          return `<button type="button" data-palette-code="${code}" ${disabled ? "disabled" : ""}><strong>${code}</strong><span>${entry.title}</span></button>`;
        }).join("")}
      </div>
    </section>`).join("");
    
  panelPalette.querySelectorAll("[data-palette-code]").forEach((button) => {
    button.addEventListener("click", () => addWorksheetChart(button.dataset.paletteCode));
  });
}

function startGridResize(event, edge) {
  event.preventDefault();
  const startX = event.clientX;
  const styles = getComputedStyle(document.documentElement);
  const startLeft = parseFloat(styles.getPropertyValue("--work-left")) || 3.8;
  const startMid = parseFloat(styles.getPropertyValue("--work-mid")) || 4.4;
  const startRight = parseFloat(styles.getPropertyValue("--work-right")) || 3.8;
  const totalWidth = resultEl.getBoundingClientRect().width;
  event.target.setPointerCapture(event.pointerId);

  function move(moveEvent) {
    const deltaCols = ((moveEvent.clientX - startX) / totalWidth) * 12;
    let left = startLeft, mid = startMid, right = startRight;
    if (edge === "left") {
      left = clamp(startLeft + deltaCols, 3.1, 5.2);
      mid = clamp(startMid - deltaCols, 3.5, 5.6);
    } else {
      mid = clamp(startMid + deltaCols, 3.5, 5.6);
      right = clamp(startRight - deltaCols, 3.1, 5.2);
    }
    document.documentElement.style.setProperty("--work-left", `${left.toFixed(2)}fr`);
    document.documentElement.style.setProperty("--work-mid", `${mid.toFixed(2)}fr`);
    document.documentElement.style.setProperty("--work-right", `${right.toFixed(2)}fr`);
  }

  function stop() {
    event.target.removeEventListener("pointermove", move);
    event.target.removeEventListener("pointerup", stop);
    event.target.removeEventListener("pointercancel", stop);
  }

  event.target.addEventListener("pointermove", move);
  event.target.addEventListener("pointerup", stop);
  event.target.addEventListener("pointercancel", stop);
}

function startRowResize(event) {
  event.preventDefault();
  const startY = event.clientY;
  const styles = getComputedStyle(document.documentElement);
  const startTop = parseFloat(styles.getPropertyValue("--work-top")) || 1;
  const startBottom = parseFloat(styles.getPropertyValue("--work-bottom")) || 1;
  const totalHeight = resultEl.getBoundingClientRect().height;
  event.target.setPointerCapture(event.pointerId);

  function move(moveEvent) {
    const delta = ((moveEvent.clientY - startY) / totalHeight) * 2;
    const top = clamp(startTop + delta, 0.55, 1.55);
    const bottom = clamp(startBottom - delta, 0.55, 1.55);
    document.documentElement.style.setProperty("--work-top", top.toFixed(2));
    document.documentElement.style.setProperty("--work-bottom", bottom.toFixed(2));
  }

  function stop() {
    event.target.removeEventListener("pointermove", move);
    event.target.removeEventListener("pointerup", stop);
    event.target.removeEventListener("pointercancel", stop);
  }

  event.target.addEventListener("pointermove", move);
  event.target.addEventListener("pointerup", stop);
  event.target.addEventListener("pointercancel", stop);
}

function clamp(value, min, max) { return Math.min(max, Math.max(min, value)); }

function showChartPreview(code) {
  const entry = activeChartEntries.find((item) => item.code === code);
  if (!entry) return;
  const planets = Object.entries(entry.chart)
    .filter(([, bodies]) => bodies.length)
    .map(([sign, bodies]) => `${sign}: ${bodies.join(", ")}`)
    .join("\n");
  window.alert(`${entry.code} ${entry.title}\n\n${planets || "No planets in this chart."}`);
}

function renderCanvasChart(selector, chart) {
  const canvas = document.querySelector(selector);
  if (!canvas || !chart) return;
  new KundaliChart(canvas, chart, { responsive: true });
}

function normalizeDivisionalChartEntries(charts) {
  const order = ["D1", "D2", "D3", "D4", "D6", "D7", "D9", "D10", "D12", "D16", "D20", "D24", "D27", "D30", "D40", "D45", "D60"];
  const titles = { D1: "Rashi / Lagna", D2: "Hora", D3: "Drekkana", D4: "Chaturthamsha", D6: "Shashtamsha", D7: "Saptamsa", D9: "Navamsa", D10: "Dashamsa", D12: "Dwadashamsha", D16: "Shodashamsha", D20: "Vimshamsha", D24: "Chaturvimshamsha", D27: "Bhamsha", D30: "Trimsamsha", D40: "Khavedamsha", D45: "Akshavedamsha", D60: "Shashtiamsha" };
  return order.filter((code) => charts && charts[code]).map((code) => {
    const value = charts[code];
    return { code, title: value.title || titles[code] || "", chart: value.chart || value };
  });
}

function renderNorthChart(selector, chart) {
  const el = document.querySelector(selector);
  const ascSign = signs.find((sign) => (chart[sign] || []).includes("Asc")) || "Aries";
  const ascIndex = signs.indexOf(ascSign);
  el.innerHTML = `
    <svg viewBox="0 0 100 70" aria-hidden="true">
      <rect x="0.75" y="0.75" width="98.5" height="68.5"></rect>
      <path d="M0.75 0.75 L50 35 L99.25 0.75"></path>
      <path d="M0.75 69.25 L50 35 L99.25 69.25"></path>
      <path d="M0.75 0.75 L99.25 69.25"></path>
      <path d="M99.25 0.75 L0.75 69.25"></path>
      <path class="soft" d="M25 17.5 L50 0.75 L75 17.5"></path>
      <path class="soft" d="M25 52.5 L50 69.25 L75 52.5"></path>
      <path class="soft" d="M0.75 35 L25 17.5"></path>
      <path class="soft" d="M0.75 35 L25 52.5"></path>
      <path class="soft" d="M99.25 35 L75 17.5"></path>
      <path class="soft" d="M99.25 35 L75 52.5"></path>
    </svg>
    ${northIndianSlots.map(({ house, cls }) => {
      const sign = signs[(ascIndex + house - 1) % 12];
      const bodies = chart[sign] || [];
      return `<div class="chart-slot ${cls}"><div class="sign-number">${signNumbers[sign]}</div><div class="planet-stack">${bodies.map(renderPlanetToken).join("")}</div></div>`;
    }).join("")}
  `;
}

function renderPlanetToken(name) {
  return `<span class="planet-token ${planetClass[name] || ""}">${planetShort[name] || name}</span>`;
}

function renderPlanets(planets) {
  planetTable.innerHTML = `
    <thead><tr><th>Planet</th><th>Sign</th><th>Degree</th><th>House</th><th>Nakshatra</th><th>Pada</th><th>Motion</th></tr></thead>
    <tbody>${planets.map((p) => `<tr><td>${p.name}</td><td>${p.sign}</td><td>${p.formatted_degree}</td><td>${p.house}</td><td>${p.nakshatra}</td><td>${p.pada}</td><td>${p.retrograde ? "Retrograde" : "Direct"}</td></tr>`).join("")}</tbody>
  `;
}

function renderKPSystem(kp, planets) {
  if (!kpSection || !kpPlanetTable || !kpCuspTable) return;
  if (!kp) {
    kpSection.classList.add("hidden");
    return;
  }
  
  kpSection.classList.remove("hidden");
  requestAnimationFrame(renderKPChart);
  
  // Render Planets Table
  const sigs = kp.planet_significators;
  const planetsData = Object.keys(sigs).map(name => {
    // Find planet object in original chart by name
    const p = planets?.find(x => x.name === name) || {};
    return `
      <tr>
        <td><strong>${name}</strong></td>
        <td>${p.sign_lord || "-"}</td>
        <td>${p.star_lord || "-"}</td>
        <td>${p.sub_lord || "-"}</td>
        <td>${p.sub_sub_lord || "-"}</td>
        <td>${sigs[name].join(", ")}</td>
      </tr>
    `;
  });
  
  kpPlanetTable.innerHTML = `
    <thead>
      <tr>
        <th>Planet</th>
        <th>Sign Lord</th>
        <th>Star Lord</th>
        <th>Sub Lord</th>
        <th>Sub-Sub Lord</th>
        <th>Significators (Houses)</th>
      </tr>
    </thead>
    <tbody>
      ${planetsData.join("")}
    </tbody>
  `;
  
  // Render Cusps Table
  const cuspsData = kp.cusps.map(c => `
    <tr>
      <td><strong>${c.house}</strong></td>
      <td>${c.longitude}°</td>
      <td>${c.sign_lord || "-"}</td>
      <td>${c.star_lord || "-"}</td>
      <td>${c.sub_lord || "-"}</td>
      <td>${c.sub_sub_lord || "-"}</td>
      <td>${kp.house_occupants[c.house].join(", ") || "-"}</td>
    </tr>
  `);
  
  kpCuspTable.innerHTML = `
    <thead>
      <tr>
        <th>Cusp</th>
        <th>Degree</th>
        <th>Sign Lord</th>
        <th>Star Lord</th>
        <th>Sub Lord</th>
        <th>Sub-Sub Lord</th>
        <th>Occupants</th>
      </tr>
    </thead>
    <tbody>
      ${cuspsData.join("")}
    </tbody>
  `;
}

function renderKPChart() {
  const kpChart = activeChartEntries.find((entry) => entry.code === "D1")?.chart;
  if (kpChartCanvas && kpChart) renderCanvasChart("#kp-chart", kpChart);
}

function renderTransit(transit, isLagna) {
  if (!isLagna || !transit) {
    transitSection.classList.add("hidden");
    transitFacts.innerHTML = "";
    transitTable.innerHTML = "";
    return;
  }
  transitSection.classList.remove("hidden");
  transitFacts.innerHTML = [
    fact("Transit Local", `${formatDate(transit.calculated_at_local || transit.calculated_at_utc)}<br><small>${transit.timezone || ""}</small>`),
    fact("Transit UTC", formatDate(transit.calculated_at_utc)),
    fact("Transit Lagna", `${transit.lagna.sign} ${transit.lagna.formatted_degree}<br>${transit.lagna.nakshatra} Pada ${transit.lagna.pada}`),
    fact("House Reference", "Birth Lagna"),
  ].join("");
  renderCanvasChart("#transit-chart", transit.chart);
  transitTable.innerHTML = `
    <thead><tr><th>Planet</th><th>Transit Sign</th><th>Degree</th><th>House from Birth Lagna</th><th>Nakshatra</th><th>Pada</th><th>Motion</th></tr></thead>
    <tbody>${transit.planets.map((p) => `<tr><td>${p.name}</td><td>${p.sign}</td><td>${p.formatted_degree}</td><td>${p.house}</td><td>${p.nakshatra}</td><td>${p.pada}</td><td>${p.retrograde ? "Retrograde" : "Direct"}</td></tr>`).join("")}</tbody>
  `;
}

function renderDasha(dasha) {
  const dashaCard = document.querySelector(".dasha-card");
  if (!dashaCard) return;
  dashaCard.innerHTML = `<div id="main-dasha-widget" class="main-dasha-widget"></div>`;
  new DashaWidget(dashaCard.querySelector("#main-dasha-widget"), dasha, {
    personLabel: "Chart",
    variant: "workstation",
  }).render();
}

function renderDashaLevel(level, rows, parentPath = [], pushStack = true) {
  rows = rows || [];
  if (pushStack) dashaStack.push({ level, rows, parentPath });
  dashaHeading.textContent = dashaNames[level];
  dashaBackButton.disabled = dashaStack.length <= 1;
  dashaPath.textContent = parentPath.length ? `${formatDashaPath(parentPath)} · ${nextDashaLevel(level) === "none" ? "Final level" : "Select a row to continue"}` : "Select a Mahadasha row to open Antardasha.";
  dashaTable.innerHTML = `
    <thead><tr><th>Period</th><th>Start</th><th>End</th><th>Years</th></tr></thead>
    <tbody>${rows.map((period, index) => `
      <tr data-index="${index}" data-next-level="${nextDashaLevel(level)}">
        <td><strong>${formatDashaPath(period.path || [period.lord])}</strong>${nextDashaLevel(level) !== "none" ? "<span>Open next level</span>" : ""}</td>
        <td>${formatDateOnly(period.start)}</td>
        <td>${formatDateOnly(period.end)}</td>
        <td>${formatYears(period.duration_years)}</td>
      </tr>`).join("")}
    </tbody>`;
    
  dashaTable.querySelectorAll("tr").forEach((row) => {
    row.addEventListener("click", () => {
      const next = row.dataset.nextLevel;
      if (next && next !== "none") {
        const period = rows[Number(row.dataset.index)];
        renderDashaLevel(next, childDashaRows(period), period.path || [period.lord]);
      }
    });
  });
}

function defaultRowsForLevel(level) {
  if (level === "maha") return activeDasha.mahadasha_timeline;
  if (level === "antara") return activeDasha.antardasha_timeline;
  if (level === "pratyantara") return activeDasha.pratyantardasha_timeline;
  if (level === "sookshma") return activeDasha.sookshma_timeline;
  return activeDasha.prana_timeline;
}

function childDashaRows(parent) {
  const start = new Date(parent.start);
  let cursor = start;
  const parentPath = parent.path || [parent.lord];
  return sequenceFrom(parent.lord).map((lord) => {
    const durationYears = parent.duration_years * dashaYears[lord] / 120;
    const end = addDashaYears(cursor, durationYears);
    const row = { lord, path: [...parentPath, lord], start: cursor.toISOString(), end: end.toISOString(), duration_years: durationYears };
    cursor = end;
    return row;
  });
}

function deriveCurrentPrana(dasha) {
  if (!dasha.current_sookshma || !dasha.event_time) return null;
  const eventTime = new Date(dasha.event_time);
  return childDashaRows(dasha.current_sookshma).find((period) => {
    const start = new Date(period.start);
    const end = new Date(period.end);
    return start <= eventTime && eventTime <= end;
  }) || null;
}

function normalizeDasha(dasha, eventTime) {
  if (!dasha) return null;
  const normalized = { ...dasha, event_time: dasha.event_time || eventTime };
  normalized.current_prana = normalized.current_prana || deriveCurrentPrana(normalized);
  normalized.mahadasha_timeline = normalizeDashaTimeline(normalized.mahadasha_timeline, normalized.current_mahadasha);
  return normalized;
}

function normalizeDashaTimeline(timeline, currentMahadasha) {
  if (Array.isArray(timeline) && timeline.length) return timeline.map((period) => ({ ...period, path: period.path || [period.lord] }));
  if (!currentMahadasha) return [];
  return childDashaRows({ lord: currentMahadasha.lord, path: [currentMahadasha.lord], start: currentMahadasha.start, duration_years: 120 }).slice(0, 9);
}

function sequenceFrom(lord) {
  const index = dashaSequence.indexOf(lord);
  return [...dashaSequence.slice(index), ...dashaSequence.slice(0, index)];
}

function addDashaYears(date, years) { return new Date(date.getTime() + years * 365.25 * 24 * 60 * 60 * 1000); }
function nextDashaLevel(level) {
  if (level === "maha") return "antara";
  if (level === "antara") return "pratyantara";
  if (level === "pratyantara") return "sookshma";
  if (level === "sookshma") return "prana";
  return "none";
}
function formatDashaPath(path) { return path.map((lord) => dashaLabels[lord] || lord).join("/"); }
function formatDateOnly(value) { return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(value)); }
function formatYears(value) {
  const years = Number(value);
  if (!Number.isFinite(years)) return "";
  if (years >= 1) return years.toFixed(2);
  const days = years * 365.25;
  if (days >= 1) return `${days.toFixed(1)}d`;
  return `${(days * 24).toFixed(1)}h`;
}
function formatDate(value) { return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "medium" }).format(new Date(value)); }
function escapeHtml(value) { return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;"); }

// ==========================================
// 9. PRICING & CHAT EXTEND UI
// ==========================================
window.selectPricingPlan = function(planName) {
  localStorage.setItem("astro_subscription_plan", planName);
  document.querySelectorAll(".pricing-plan-card").forEach((card) => {
    const isCurrent = card.dataset.plan === planName;
    card.classList.toggle("active-plan", isCurrent);
    const btn = card.querySelector(".btn-select-plan");
    if (btn) btn.textContent = isCurrent ? "Current Plan" : (planName === "free" ? "Select Plan" : "Upgrade Plan");
  });
  const alertEl = document.querySelector("#subscription-status-alert");
  if (alertEl) {
    const planLabels = { free: "Free Plan", basic: "Basic Plan (₹29/mo)", premium: "Premium Plan (₹99/mo)" };
    alertEl.textContent = `Successfully updated your subscription to ${planLabels[planName]}!`;
    alertEl.classList.remove("hidden");
    setTimeout(() => alertEl.classList.add("hidden"), 4000);
  }
};

function initPricingUI() {
  const currentPlan = localStorage.getItem("astro_subscription_plan") || "free";
  document.querySelectorAll(".pricing-plan-card").forEach((card) => {
    const isCurrent = card.dataset.plan === currentPlan;
    card.classList.toggle("active-plan", isCurrent);
    const btn = card.querySelector(".btn-select-plan");
    if (btn) btn.textContent = isCurrent ? "Current Plan" : (card.dataset.plan === "free" ? "Select Plan" : "Upgrade Plan");
  });
}

function initChatExtend() {
  const btnSubmit = document.querySelector("#btn-chat-extend-submit");
  const chatInput = document.querySelector("#chat-extend-input");
  const chatHistory = document.querySelector("#chat-extend-history");
  const chatStatus = document.querySelector("#chat-extend-status");

  if (!btnSubmit || !chatInput) return;

  btnSubmit.addEventListener("click", () => {
    const question = chatInput.value.trim();
    if (!question) return;

    const currentPlan = localStorage.getItem("astro_subscription_plan") || "free";
    chatStatus.textContent = "";

    if (currentPlan === "free" || currentPlan === "basic") {
      chatStatus.textContent = "Follow-up questions are only available on the Premium Plan (₹99/month). Directing you to Pricing...";
      setTimeout(() => {
        chatStatus.textContent = "";
        activeTab = "pricing";
        updateNavigation(true);
      }, 2000);
      return;
    }

    chatInput.value = "";
    chatHistory.classList.remove("hidden");
    const userBubble = document.createElement("div");
    userBubble.className = "chat-bubble user";
    userBubble.textContent = question;
    chatHistory.appendChild(userBubble);
    chatHistory.scrollTop = chatHistory.scrollHeight;

    chatStatus.textContent = "AstroAI is reading your chart...";
    btnSubmit.disabled = true;

    setTimeout(() => {
      chatStatus.textContent = "";
      btnSubmit.disabled = false;
      const botBubble = document.createElement("div");
      botBubble.className = "chat-bubble bot";
      botBubble.innerHTML = `<section><h4>AstroAI Advice</h4><p>Analyzing your chart, the current transit of Saturn suggests patience in career matters. Expect opportunities to solidify soon.</p></section>`;
      chatHistory.appendChild(botBubble);
      chatHistory.scrollTop = chatHistory.scrollHeight;
    }, 1500);
  });
}

function initPaidConsultation() {
  const btnStart = document.getElementById("btn-start-consultation");
  const formDetails = document.getElementById("wizard-details-form");
  const formQuestion = document.getElementById("paid-consultation-form");
  const step1 = document.getElementById("wizard-step-1");
  const step2 = document.getElementById("wizard-step-2");
  const step3 = document.getElementById("wizard-step-3");
  const btnBack = document.getElementById("btn-back-to-details");
  const queueStatus = document.getElementById("consultant-queue-status");
  const payBtn = document.getElementById("btn-pay-consultation");
  const statusMsg = document.getElementById("consultation-form-status");
  const placeSearchInput = document.getElementById("cons-place");
  const placeSuggestionsList = document.getElementById("cons-place-suggestions");
  const latInput = document.getElementById("cons-lat");
  const lonInput = document.getElementById("cons-lon");
  
  if (!btnStart) return;

  async function pollQueueStatus() {
    try {
      const data = await API.get("/api/consultation/status", false);
      queueStatus.textContent = `Live Queue: ${data.current_queue_size}/${data.max_capacity} filled`;
      if (!data.can_book) {
        payBtn.disabled = true;
        payBtn.textContent = "Queue Full - Check back later";
        payBtn.style.opacity = "0.5";
        payBtn.style.cursor = "not-allowed";
      } else {
        payBtn.disabled = false;
        payBtn.textContent = "Pay ₹299 & Ask";
        payBtn.style.opacity = "1";
        payBtn.style.cursor = "pointer";
      }
    } catch (err) {
      console.error("Failed to fetch queue status:", err);
      showFlash("Failed to load live queue status: " + err.message, "error");
    }
  }

  pollQueueStatus();
  setInterval(() => {
    if (!document.getElementById("consultants-card").classList.contains("hidden")) {
      pollQueueStatus();
    }
  }, 10000);

  let debounceTimeout;
  placeSearchInput.addEventListener("input", function(e) {
    clearTimeout(debounceTimeout);
    const query = e.target.value.trim();
    if (query.length < 3) { placeSuggestionsList.classList.add("hidden"); return; }
    debounceTimeout = setTimeout(async () => {
      try {
        const data = await API.get(`/api/location/search?query=${encodeURIComponent(query)}`, false);
        placeSuggestionsList.innerHTML = "";
        if (data.results && data.results.length > 0) {
          data.results.forEach(item => {
            const li = document.createElement("li");
            li.innerHTML = `<strong>${escapeHtml(item.place_name)}</strong><br><small>${escapeHtml(item.region_state || '')}</small>`;
            li.style.cursor = "pointer";
            li.addEventListener("click", () => {
              placeSearchInput.value = item.place_name;
              latInput.value = item.latitude;
              lonInput.value = item.longitude;
              placeSuggestionsList.classList.add("hidden");
            });
            placeSuggestionsList.appendChild(li);
          });
          placeSuggestionsList.classList.remove("hidden");
        } else {
          placeSuggestionsList.classList.add("hidden");
        }
      } catch (err) {
        console.error("Location search failed", err);
        showFlash("Location search failed: " + err.message, "error");
      }
    }, 500);
  });
  
  document.addEventListener("click", (e) => {
    if (e.target !== placeSearchInput && e.target !== placeSuggestionsList) placeSuggestionsList.classList.add("hidden");
  });

  btnStart.addEventListener("click", () => {
    if (!AppState.session) {
      document.getElementById("auth-modal").classList.remove("hidden");
      return;
    }
    
    document.getElementById("cons-email").value = AppState.session.user?.email || "verified_user@email.com";
    if (document.getElementById("name").value) {
      document.getElementById("cons-name").value = document.getElementById("name").value;
      const bdt = document.getElementById("birth_datetime_local").value;
      if (bdt.includes('T')) {
        document.getElementById("cons-dob").value = bdt.split('T')[0];
        document.getElementById("cons-time").value = bdt.split('T')[1];
      }
      document.getElementById("cons-gender").value = document.getElementById("gender").value;
      placeSearchInput.value = document.getElementById("place_name").value;
      latInput.value = document.getElementById("latitude").value;
      lonInput.value = document.getElementById("longitude").value;
    }
    step1.style.display = "none";
    step2.style.display = "block";
    step3.style.display = "none";
  });

  formDetails.addEventListener("submit", (e) => {
    e.preventDefault();
    if (!latInput.value || !lonInput.value) { alert("Please select a valid place from the suggestions list."); return; }
    step1.style.display = "none";
    step2.style.display = "none";
    step3.style.display = "block";
  });

  btnBack.addEventListener("click", () => {
    step3.style.display = "none";
    step2.style.display = "block";
  });

  formQuestion.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (payBtn.disabled) return;
    const question = document.getElementById("paid_question").value.trim();
    if (question.length < 3) { statusMsg.textContent = "Question too short."; return; }

    statusMsg.style.color = "var(--color-primary)";
    statusMsg.textContent = "Initiating payment...";
    payBtn.disabled = true;

    setTimeout(async () => {
      statusMsg.textContent = "Payment successful! Booking consultation...";
      const payload = {
        question: question,
        name: document.getElementById("cons-name").value,
        gender: document.getElementById("cons-gender").value,
        whatsapp_no: document.getElementById("cons-whatsapp").value,
        birth_datetime_local: `${document.getElementById("cons-dob").value}T${document.getElementById("cons-time").value}`,
        location: { latitude: parseFloat(latInput.value), longitude: parseFloat(lonInput.value), place_name: placeSearchInput.value },
        payment_ref: "pay_" + Math.random().toString(36).substr(2, 9)
      };

      try {
        await API.post("/api/consultation/book", payload);
        statusMsg.style.color = "green";
        statusMsg.textContent = "Success! The astrologer will answer within 24 hours.";
        formQuestion.reset();
        formDetails.reset();
        setTimeout(() => { step3.style.display = "none"; step1.style.display = "block"; statusMsg.textContent = ""; }, 3000);
        pollQueueStatus();
      } catch (err) {
        statusMsg.style.color = "var(--color-error)";
        statusMsg.textContent = err.message || "Booking failed.";
        payBtn.disabled = false;
      }
    }, 1000);
  });
}


// Share to community logic
let currentShareChart = null;

async function openShareModal() {
    if (!currentShareChart) return;
    
    // Check if user is verified astrologer (just fetch profile, backend enforces)
    try {
        const channels = await apiGet('/api/community/channels');
        const select = document.getElementById('share-channel-select');
        select.innerHTML = channels.map(c => `<option value="${c.slug}"># ${c.name}</option>`).join('');
        document.getElementById('share-community-overlay').classList.remove('hidden');
    } catch (e) {
        alert("You must be an approved Astrologer to share to the community. Please apply first.");
    }
}

document.getElementById('btn-share-community')?.addEventListener('click', openShareModal);

document.getElementById('btn-submit-share')?.addEventListener('click', async () => {
    const channel = document.getElementById('share-channel-select').value;
    const comment = document.getElementById('share-comment').value;
    
    if (!channel || !comment) {
        alert("Please select a channel and add a comment.");
        return;
    }
    
    document.getElementById('btn-submit-share').textContent = 'Sharing...';
    
    try {
        const isLagna = currentShareChart.meta?.chart_type === 'lagna';
        
        // Use a standard API call to post (simulate WS or just standard POST if we add one)
        // Since we only have WS for now, we'll need to create a POST /messages endpoint.
        const res = await fetch(`/api/community/messages/${encodeURIComponent(channel)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${AppState.session.access_token}`
            },
            body: JSON.stringify({
                content: comment,
                content_type: isLagna ? 'LAGNA_CASE' : 'PRASHNA_CASE',
                chart_id: currentShareChart.meta?.id || currentShareChart.id || null
            })
        });
        
        if (res.ok) {
            document.getElementById('share-community-overlay').classList.add('hidden');
            document.getElementById('share-comment').value = '';
            alert('Chart shared to community successfully!');
        } else {
            alert('Failed to share.');
        }
    } catch (e) {
        console.error(e);
        alert('Error sharing chart.');
    } finally {
        document.getElementById('btn-submit-share').textContent = 'Share Post';
    }
});
