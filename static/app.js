const form = document.querySelector("#prashna-form");
const statusEl = document.querySelector("#status");
const resultEl = document.querySelector("#result");
const factsEl = document.querySelector("#facts");
const resultTabs = document.querySelector("#result-tabs");
const chartsViewButton = document.querySelector("#charts-view-button");
const interpretationViewButton = document.querySelector("#interpretation-view-button");
const interpretationCard = document.querySelector("#interpretation-card");
const interpretationDomain = document.querySelector("#interpretation-domain");
const interpretationTitle = document.querySelector("#interpretation-title");
const interpretationConfidence = document.querySelector("#interpretation-confidence");
const interpretationBody = document.querySelector("#interpretation-body");
const planetTable = document.querySelector("#planet-table");
const divisionalChartsEl = document.querySelector("#divisional-charts");
const topicChartTabs = document.querySelector("#topic-chart-tabs");
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
const shareLink = document.querySelector("#share-link");
const chartTitle = document.querySelector("#chart-title");
const dashaHeading = document.querySelector("#dasha-heading");
const dashaBackButton = document.querySelector("#dasha-back-button");
const dashaPath = document.querySelector("#dasha-path");
const placeSearchInput = document.querySelector("#place_search");
const placeSearchButton = document.querySelector("#place-search-button");
const placeResultsEl = document.querySelector("#place-results");
const modePanel = document.querySelector("#mode-panel");
const changeModeButton = document.querySelector("#change-mode-button");
const formTitle = document.querySelector("#form-title");
const modeEyebrow = document.querySelector("#mode-eyebrow");
const questionField = document.querySelector("#question-field");
const questionDomainField = document.querySelector("#question-domain-field");
const jobTypeField = document.querySelector("#job-type-field");
const birthFields = document.querySelector("#birth-fields");
const submitButton = document.querySelector("#submit-button");
let activeDasha = null;
let activeMode = "";
let activeChart = null;
let activeChartEntries = [];
let activeChartCodes = [];
let pendingPaletteSlot = null;
let dashaStack = [];
let activeResultView = "charts";

const signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"];
const signNumbers = { Aries: 1, Taurus: 2, Gemini: 3, Cancer: 4, Leo: 5, Virgo: 6, Libra: 7, Scorpio: 8, Sagittarius: 9, Capricorn: 10, Aquarius: 11, Pisces: 12 };
const planetShort = { Asc: "Asc", Sun: "Su", Moon: "Mo", Mars: "Ma", Mercury: "Me", Jupiter: "Ju", Venus: "Ve", Saturn: "Sa", Rahu: "Ra", Ketu: "Ke" };
const planetClass = { Asc: "p-asc", Sun: "p-sun", Moon: "p-moon", Mars: "p-mars", Mercury: "p-mercury", Jupiter: "p-jupiter", Venus: "p-venus", Saturn: "p-saturn", Rahu: "p-rahu", Ketu: "p-ketu" };
const dashaNames = { maha: "Mahadasha", antara: "Antardasha", pratyantara: "Pratyantardasha", sookshma: "Sookshma Dasha", prana: "Prana Dasha" };
const dashaLabels = { Ketu: "Ke", Venus: "Ve", Sun: "Su", Moon: "Mo", Mars: "Ma", Rahu: "Ra", Jupiter: "Ju", Saturn: "Sa", Mercury: "Me" };
const dashaYears = { Ketu: 7, Venus: 20, Sun: 6, Moon: 10, Mars: 7, Rahu: 18, Jupiter: 16, Saturn: 19, Mercury: 17 };
const dashaSequence = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"];
const questionDomainLabels = {
  wealth: "Wealth / money",
  marriage: "Marriage / relationship",
  child: "Child / progeny",
  job_career: "Job / career",
  illness: "Illness / health",
  foreign: "Foreign / travel",
  education: "Education",
};
const jobTypeLabels = {
  government: "Government job",
  private: "Private job",
};
const domainChartDefaults = {
  marriage: ["D1", "D9"],
  child: ["D1", "D7"],
  job_career: ["D1", "D10"],
  education: ["D1", "D24"],
  wealth: ["D1", "D2", "D4", "D9"],
  foreign: ["D1", "D4", "D9", "D10"],
  illness: ["D1", "D3", "D6", "D9", "D30"],
  default: ["D1", "D9"],
};

const northIndianSlots = Array.from({ length: 12 }, (_, index) => ({ house: index + 1, cls: `slot-${index + 1}` }));

modePanel.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-mode]");
  if (!button) return;
  setMode(button.dataset.mode);
});

changeModeButton.addEventListener("click", () => {
  activeMode = "";
  document.body.classList.remove("has-result");
  resultEl.classList.add("hidden");
  form.classList.add("hidden");
  modePanel.classList.remove("hidden");
  statusEl.textContent = "";
});

placeSearchButton.addEventListener("click", searchPlace);
document.querySelector("#question_domain").addEventListener("change", syncQuestionDomainControls);
addChartButton.addEventListener("click", () => togglePanelPalette());
resetWorksheetButton.addEventListener("click", () => renderDivisionalCharts(activeChart?.divisional_charts, activeChart));
chartsViewButton.addEventListener("click", () => setResultView("charts"));
interpretationViewButton.addEventListener("click", () => setResultView("interpretation"));
gridResizers.forEach((resizer) => {
  resizer.addEventListener("pointerdown", (event) => startGridResize(event, resizer.dataset.resizeCol));
});
rowResizers.forEach((resizer) => {
  resizer.addEventListener("pointerdown", (event) => startRowResize(event));
});
divisionalChartsEl.addEventListener("contextmenu", (event) => {
  event.preventDefault();
  const chartButton = event.target.closest(".chart-surface");
  if (chartButton) {
    showChartPreview(chartButton.dataset.inspect);
    return;
  }
  if (event.target === divisionalChartsEl) {
    openPanelPaletteAt(event.clientX, event.clientY);
  }
});
document.addEventListener("click", (event) => {
  if (panelPalette.classList.contains("hidden")) return;
  if (event.target.closest("#panel-palette") || event.target.closest("#add-chart-button")) return;
  panelPalette.classList.add("hidden");
});
placeSearchInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    searchPlace();
  }
});

dashaBackButton.addEventListener("click", () => {
  if (dashaStack.length <= 1) return;
  dashaStack.pop();
  const previous = dashaStack[dashaStack.length - 1];
  renderDashaLevel(previous.level, previous.rows, previous.parentPath, false);
});

document.querySelector("#gps-button").addEventListener("click", () => {
  if (!navigator.geolocation) {
    statusEl.textContent = "GPS is not available in this browser.";
    return;
  }
  statusEl.textContent = "Requesting GPS location...";
  navigator.geolocation.getCurrentPosition(
    (position) => {
      document.querySelector("#latitude").value = position.coords.latitude.toFixed(6);
      document.querySelector("#longitude").value = position.coords.longitude.toFixed(6);
      if (!document.querySelector("#place_name").value) {
        document.querySelector("#place_name").value = "Current GPS location";
      }
      placeSearchInput.value = document.querySelector("#place_name").value;
      placeResultsEl.innerHTML = selectedPlaceMessage({
        place_name: document.querySelector("#place_name").value,
        latitude: document.querySelector("#latitude").value,
        longitude: document.querySelector("#longitude").value,
        source: "gps",
      });
      statusEl.textContent = "Location captured. Submit when the Prashna question is ready.";
    },
    (error) => {
      statusEl.textContent = `Could not capture GPS: ${error.message}`;
    },
    { enableHighAccuracy: true, timeout: 12000 }
  );
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!activeMode) {
    statusEl.textContent = "Choose Prashna Kundli or Lagna Kundli first.";
    return;
  }
  if (!hasValidCoordinates()) {
    statusEl.textContent = "Search and select a place first, or enter manual latitude and longitude.";
    return;
  }
  statusEl.textContent = activeMode === "lagna" ? "Generating birth chart..." : "Generating chart with server-side timestamp...";

  const payload = buildPayload();
  if (!payload) return;

  try {
    const response = await fetch(activeMode === "lagna" ? "/api/lagna" : "/api/prashna", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(formatApiError(data.detail, "Chart generation failed."));
    }
    renderChart(data.chart);
    statusEl.textContent = "Chart generated and saved.";
  } catch (error) {
    statusEl.textContent = error.message;
  }
});

function setMode(mode) {
  activeMode = mode;
  modePanel.classList.add("hidden");
  form.classList.remove("hidden");
  const isLagna = mode === "lagna";
  formTitle.textContent = isLagna ? "Lagna Kundli" : "Prashna Kundli";
  modeEyebrow.textContent = isLagna ? "Birth chart mode" : "Question chart mode";
  questionField.classList.toggle("hidden", isLagna);
  questionDomainField.classList.toggle("hidden", isLagna);
  jobTypeField.classList.add("hidden");
  birthFields.classList.toggle("hidden", !isLagna);
  document.querySelector("#question").required = !isLagna;
  document.querySelector("#birth_datetime_local").required = isLagna;
  submitButton.textContent = isLagna ? "Generate Lagna Kundli" : "Generate Prashna Kundli";
  statusEl.textContent = isLagna
    ? "Enter birth details, then search and select birthplace."
    : "Ask your question, then search and select current place.";
  syncQuestionDomainControls();
}

function buildPayload() {
  const location = {
    latitude: Number(document.querySelector("#latitude").value),
    longitude: Number(document.querySelector("#longitude").value),
    place_name: document.querySelector("#place_name").value.trim(),
  };
  const name = document.querySelector("#name").value.trim();
  if (name.length < 1) {
    statusEl.textContent = "Enter a name before generating the kundli.";
    return null;
  }

  if (activeMode === "lagna") {
    const birthTime = document.querySelector("#birth_datetime_local").value;
    if (!birthTime) {
      statusEl.textContent = "Enter birth date and time up to minute level.";
      return null;
    }
    return {
      name,
      gender: document.querySelector("#gender").value,
      birth_datetime_local: birthTime,
      location,
    };
  }

  const question = document.querySelector("#question").value.trim();
  if (question.length < 3) {
    statusEl.textContent = "Enter the Prashna question with at least 3 characters.";
    return null;
  }

  const payload = {
    name,
    question,
    question_domain: document.querySelector("#question_domain").value,
    question_subdomain: document.querySelector("#question_domain").value === "job_career" ? document.querySelector("#job_type").value : "",
    location,
  };
  const overrideTime = document.querySelector("#asked_at_utc").value.trim();
  if (overrideTime) payload.asked_at_utc = overrideTime;
  return payload;
}

async function searchPlace() {
  const query = placeSearchInput.value.trim();
  if (query.length < 2) {
    statusEl.textContent = "Enter at least 2 characters for place search.";
    return;
  }

  statusEl.textContent = "Searching place...";
  placeResultsEl.innerHTML = `<div class="place-result muted">Searching ${escapeHtml(query)}...</div>`;
  try {
    const response = await fetch(`/api/geocode?query=${encodeURIComponent(query)}&limit=6`);
    const data = await response.json();
    if (!response.ok) throw new Error(formatApiError(data.detail, "Place search failed."));
    renderPlaceResults(data.results);
    statusEl.textContent = data.results.length ? "Select the correct place result." : "No places found. Try city, state, country.";
  } catch (error) {
    placeResultsEl.innerHTML = "";
    statusEl.textContent = error.message;
  }
}

function renderPlaceResults(results) {
  if (!results.length) {
    placeResultsEl.innerHTML = `<div class="place-result muted">No results found.</div>`;
    return;
  }
  placeResultsEl.innerHTML = results
    .map(
      (item, index) => `
      <button type="button" class="place-result" data-index="${index}">
        <strong>${escapeHtml(item.place_name)}</strong>
        <span>${item.latitude}, ${item.longitude} · ${escapeHtml(item.source)} · ${escapeHtml(item.type || "place")}</span>
      </button>`
    )
    .join("");

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
  statusEl.textContent = "Place selected. Coordinates are ready for kundli calculation.";
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
  return Number.isFinite(lat) && Number.isFinite(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180 && document.querySelector("#place_name").value.trim();
}

function formatApiError(detail, fallback) {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        const field = Array.isArray(item.loc) ? item.loc.filter((part) => part !== "body").join(".") : "";
        return [field, item.msg].filter(Boolean).join(": ");
      })
      .filter(Boolean)
      .join(" ");
  }
  if (typeof detail === "object") {
    return detail.msg || detail.message || JSON.stringify(detail);
  }
  return fallback;
}

function renderChart(chart) {
  activeChart = chart;
  document.body.classList.add("has-result");
  resultEl.classList.remove("hidden");
  const isLagna = chart.meta.chart_type === "lagna";
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

  renderInterpretation(chart.interpretation, chart);
  renderDivisionalCharts(chart.divisional_charts, chart);
  renderPlanets(chart.planets);
  renderTransit(chart.transit, isLagna);
  renderDasha(normalizeDasha(chart.dashas, chart.question.asked_at_utc));
  resultTabs.classList.remove("hidden");
  interpretationViewButton.disabled = !chart.interpretation;
  setResultView("charts");
  resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

function fact(label, value) {
  return `<div class="fact"><span>${label}</span><strong>${value}</strong></div>`;
}

function renderInterpretation(interpretation, chart = null) {
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
          <p>The chart was generated without an interpretation payload. Generate the Prashna again after restarting the local server so the latest backend can attach the deep reading.</p>
        </section>
      </div>
      <div class="interpretation-side">
        <div class="interpretation-verdict" data-level="uncertain">
          <span>Status</span>
          <strong>Backend response did not include chart.interpretation.</strong>
        </div>
        <div class="interpretation-intent">
          <span>Question</span>
          <p>${escapeHtml(chart?.question?.text || "No question text found.")}</p>
        </div>
      </div>
      <div class="interpretation-evidence">
        <div class="evidence-row" data-status="caution">
          <span>Action needed</span>
          <p>Restart the server and submit the question again. Existing saved charts created before interpretation support may not contain the reading.</p>
        </div>
      </div>
    `;
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
    answer = `<div class="interpretation-answer">
        <span>Astrologer interpretation</span>
        ${formatAnswerText(interpretation.answer.text)}
      </div>`;
  } else {
    answer = `<div class="interpretation-answer interpretation-missing">
        <span>LLM interpretation required</span>
        <section>
          <h4>No local interpretation was generated</h4>
          <p>${escapeHtml(interpretation.answer?.error || interpretation.answer?.note || "Configure Gemini or OpenAI for this Prashna reading. The app will not show a hardcoded fallback interpretation.")}</p>
        </section>
      </div>`;
  }
  interpretationBody.innerHTML = `
    ${answer}
  `;
}

function setResultView(view) {
  activeResultView = view === "interpretation" && activeChart?.interpretation ? "interpretation" : "charts";
  document.body.classList.toggle("view-interpretation", activeResultView === "interpretation");
  document.body.classList.toggle("view-charts", activeResultView === "charts");
  chartsViewButton.classList.toggle("is-active", activeResultView === "charts");
  interpretationViewButton.classList.toggle("is-active", activeResultView === "interpretation");
  if (activeResultView === "interpretation") {
    interpretationCard.classList.remove("hidden");
    resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function formatAnswerText(text) {
  return escapeHtml(text)
    .split(/\n{2,}/)
    .map((paragraph) => {
      const lines = paragraph.split("\n");
      if (lines.length > 1 && lines[0].length <= 42) {
        return `<section><h4>${lines[0]}</h4><p>${lines.slice(1).join("\n").replaceAll("\n", "<br>")}</p></section>`;
      }
      return `<p>${paragraph.replaceAll("\n", "<br>")}</p>`;
    })
    .join("");
}

function formatSnakeLabel(value) {
  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function renderDivisionalCharts(charts, chart) {
  activeChartEntries = normalizeDivisionalChartEntries(charts);
  const preferredCodes = getDefaultChartCodes(chart, activeChartEntries);
  activeChartCodes = preferredCodes;
  renderChartPicker();
  renderTopicTabs();
  renderWorksheet();
  renderPanelPalette();
}

function syncQuestionDomainControls() {
  const isJob = activeMode === "prashna" && document.querySelector("#question_domain").value === "job_career";
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
    .map((entry) => `<option value="${entry.code}">${entry.code} ${entry.title}</option>`)
    .join("");
}

function renderTopicTabs() {
  topicChartTabs.innerHTML = activeChartCodes
    .map((code) => {
      const entry = activeChartEntries.find((item) => item.code === code);
      return `<button type="button" class="chart-tab" data-code="${code}">${code}<span>${entry?.title || ""}</span></button>`;
    })
    .join("");
  topicChartTabs.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => focusWorksheetChart(button.dataset.code));
  });
}

function renderWorksheet() {
  divisionalChartsEl.dataset.chartCount = String(activeChartCodes.length);
  divisionalChartsEl.innerHTML = activeChartCodes
    .map((code, index) => {
      const entry = activeChartEntries.find((item) => item.code === code);
      return `
        <section class="worksheet-item" data-code="${code}">
          <div class="worksheet-item-head">
            <div>
              <strong>${code}</strong>
              <span>${entry?.title || ""}</span>
            </div>
            <button type="button" data-remove="${code}" title="Remove chart">x</button>
          </div>
          <button type="button" class="chart-surface" data-inspect="${code}">
            <div id="chart-${code.toLowerCase()}" class="north-chart"></div>
          </button>
        </section>`;
    })
    .join("");
  activeChartCodes.forEach((code) => {
    const entry = activeChartEntries.find((item) => item.code === code);
    if (entry) renderNorthChart(`#chart-${code.toLowerCase()}`, entry.chart);
  });
  enableWorksheetInteractions();
}

function addWorksheetChart(code) {
  if (!code || activeChartCodes.includes(code)) {
    const next = activeChartEntries.find((entry) => !activeChartCodes.includes(entry.code));
    if (!next) return;
    code = next.code;
  }
  activeChartCodes.push(code);
  panelPalette.classList.add("hidden");
  renderChartPicker();
  renderTopicTabs();
  renderWorksheet();
  renderPanelPalette();
  focusWorksheetChart(code);
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
      renderChartPicker();
      renderTopicTabs();
      renderWorksheet();
      renderPanelPalette();
    });
  });
  divisionalChartsEl.querySelectorAll(".chart-surface").forEach((button) => {
    button.addEventListener("click", () => showChartPreview(button.dataset.inspect));
  });
  divisionalChartsEl.querySelectorAll(".worksheet-empty-slot").forEach((button) => {
    button.addEventListener("click", (event) => {
      pendingPaletteSlot = button.dataset.emptySlot;
      openPanelPaletteAt(event.clientX, event.clientY);
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
  panelPalette.innerHTML = categories
    .map((category) => `
      <section>
        <h4>${category.title}</h4>
        <div class="panel-palette-grid">
          ${category.codes
            .map((code) => {
              const entry = activeChartEntries.find((item) => item.code === code);
              if (!entry) return "";
              const active = activeChartCodes.includes(code);
              return `<button type="button" data-palette-code="${code}" ${active ? "disabled" : ""}>
                <strong>${code}</strong>
                <span>${entry.title}</span>
              </button>`;
            })
            .join("")}
        </div>
      </section>`)
    .join("");
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
    let left = startLeft;
    let mid = startMid;
    let right = startRight;
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

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function showChartPreview(code) {
  const entry = activeChartEntries.find((item) => item.code === code);
  if (!entry) return;
  const planets = Object.entries(entry.chart)
    .filter(([, bodies]) => bodies.length)
    .map(([sign, bodies]) => `${sign}: ${bodies.join(", ")}`)
    .join("\n");
  window.alert(`${entry.code} ${entry.title}\n\n${planets || "No planets in this chart."}`);
}

function normalizeDivisionalChartEntries(charts) {
  const order = ["D1", "D2", "D3", "D4", "D6", "D7", "D9", "D10", "D12", "D16", "D20", "D24", "D27", "D30", "D40", "D45", "D60"];
  const titles = {
    D1: "Rashi / Lagna",
    D2: "Hora",
    D3: "Drekkana",
    D4: "Chaturthamsha",
    D6: "Shashtamsha",
    D7: "Saptamsa",
    D9: "Navamsa",
    D10: "Dashamsa",
    D12: "Dwadashamsha",
    D16: "Shodashamsha",
    D20: "Vimshamsha",
    D24: "Chaturvimshamsha",
    D27: "Bhamsha",
    D30: "Trimsamsha",
    D40: "Khavedamsha",
    D45: "Akshavedamsha",
    D60: "Shashtiamsha",
  };
  return order
    .filter((code) => charts && charts[code])
    .map((code) => {
      const value = charts[code];
      return {
        code,
        title: value.title || titles[code] || "",
        chart: value.chart || value,
      };
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
    ${northIndianSlots
      .map(({ house, cls }) => {
      const sign = signs[(ascIndex + house - 1) % 12];
      const bodies = chart[sign] || [];
      return `
        <div class="chart-slot ${cls}">
          <div class="sign-number">${signNumbers[sign]}</div>
          <div class="planet-stack">${bodies.map(renderPlanetToken).join("")}</div>
        </div>`;
    })
    .join("")}
  `;
}

function renderPlanetToken(name) {
  return `<span class="planet-token ${planetClass[name] || ""}">${planetShort[name] || name}</span>`;
}

function renderPlanets(planets) {
  planetTable.innerHTML = `
    <thead>
      <tr>
        <th>Planet</th><th>Sign</th><th>Degree</th><th>House</th><th>Nakshatra</th><th>Pada</th><th>Motion</th>
      </tr>
    </thead>
    <tbody>
      ${planets
        .map(
          (p) => `
          <tr>
            <td>${p.name}</td>
            <td>${p.sign}</td>
            <td>${p.formatted_degree}</td>
            <td>${p.house}</td>
            <td>${p.nakshatra}</td>
            <td>${p.pada}</td>
            <td>${p.retrograde ? "Retrograde" : "Direct"}</td>
          </tr>`
        )
        .join("")}
    </tbody>
  `;
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
  renderNorthChart("#transit-chart", transit.chart);
  transitTable.innerHTML = `
    <thead>
      <tr>
        <th>Planet</th><th>Transit Sign</th><th>Degree</th><th>House from Birth Lagna</th><th>Nakshatra</th><th>Pada</th><th>Motion</th>
      </tr>
    </thead>
    <tbody>
      ${transit.planets
        .map(
          (p) => `
          <tr>
            <td>${p.name}</td>
            <td>${p.sign}</td>
            <td>${p.formatted_degree}</td>
            <td>${p.house}</td>
            <td>${p.nakshatra}</td>
            <td>${p.pada}</td>
            <td>${p.retrograde ? "Retrograde" : "Direct"}</td>
          </tr>`
        )
        .join("")}
    </tbody>
  `;
}

function renderDasha(dasha) {
  if (!dasha) {
    dashaSummary.innerHTML = fact("Dasha", "Not available");
    dashaTable.innerHTML = "";
    return;
  }
  const currentPrana = dasha.current_prana;
  activeDasha = dasha;
  dashaStack = [];
  dashaSummary.innerHTML = [
    dasha.current_mahadasha ? fact("Mahadasha", `${dasha.current_mahadasha.lord}<br>Balance ${dasha.current_mahadasha.balance_years}y`) : "",
    dasha.current_antardasha ? fact("Antardasha", `${dasha.current_antardasha.lord}<br>${formatDate(dasha.current_antardasha.end)}`) : "",
    dasha.current_pratyantardasha ? fact("Pratyantar", `${dasha.current_pratyantardasha.lord}<br>${formatDate(dasha.current_pratyantardasha.end)}`) : "",
    dasha.current_sookshma ? fact("Sookshma", `${dasha.current_sookshma.lord}<br>${formatDate(dasha.current_sookshma.end)}`) : "",
    currentPrana ? fact("Prana", `${currentPrana.lord}<br>${formatDate(currentPrana.end)}`) : "",
  ].filter(Boolean).join("");
  const rows = activeDasha.mahadasha_timeline || [];
  renderDashaLevel("maha", rows, []);
}

function renderDashaLevel(level, rows, parentPath = [], pushStack = true) {
  rows = rows || [];
  if (pushStack) {
    dashaStack.push({ level, rows, parentPath });
  }
  dashaHeading.textContent = dashaNames[level];
  dashaBackButton.disabled = dashaStack.length <= 1;
  dashaPath.textContent = parentPath.length
    ? `${formatDashaPath(parentPath)} · ${nextDashaLevel(level) === "none" ? "Final level" : "Select a row to continue"}`
    : "Select a Mahadasha row to open Antardasha.";
  dashaTable.innerHTML = `
    <thead>
      <tr><th>Period</th><th>Start</th><th>End</th><th>Years</th></tr>
    </thead>
    <tbody>
      ${rows.map((period, index) => `
        <tr data-index="${index}" data-next-level="${nextDashaLevel(level)}">
          <td><strong>${formatDashaPath(period.path || [period.lord])}</strong>${nextDashaLevel(level) !== "none" ? "<span>Open next level</span>" : ""}</td>
          <td>${formatDateOnly(period.start)}</td>
          <td>${formatDateOnly(period.end)}</td>
          <td>${formatYears(period.duration_years)}</td>
        </tr>`).join("")}
    </tbody>
  `;
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
    const row = {
      lord,
      path: [...parentPath, lord],
      start: cursor.toISOString(),
      end: end.toISOString(),
      duration_years: durationYears,
    };
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
  if (Array.isArray(timeline) && timeline.length) {
    return timeline.map((period) => ({
      ...period,
      path: period.path || [period.lord],
    }));
  }
  if (!currentMahadasha) return [];
  return childDashaRows({
    lord: currentMahadasha.lord,
    path: [currentMahadasha.lord],
    start: currentMahadasha.start,
    duration_years: 120,
  }).slice(0, 9);
}

function sequenceFrom(lord) {
  const index = dashaSequence.indexOf(lord);
  return [...dashaSequence.slice(index), ...dashaSequence.slice(0, index)];
}

function addDashaYears(date, years) {
  return new Date(date.getTime() + years * 365.25 * 24 * 60 * 60 * 1000);
}

function nextDashaLevel(level) {
  if (level === "maha") return "antara";
  if (level === "antara") return "pratyantara";
  if (level === "pratyantara") return "sookshma";
  if (level === "sookshma") return "prana";
  return "none";
}

function formatDashaPath(path) {
  return path.map((lord) => dashaLabels[lord] || lord).join("/");
}

function formatDateOnly(value) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(value));
}

function formatYears(value) {
  const years = Number(value);
  if (!Number.isFinite(years)) return "";
  if (years >= 1) return years.toFixed(2);
  const days = years * 365.25;
  if (days >= 1) return `${days.toFixed(1)}d`;
  return `${(days * 24).toFixed(1)}h`;
}

function renderDashaOld(dasha) {
  dashaTable.innerHTML = `
    <thead><tr><th>Mahadasha</th><th>Start</th><th>End</th><th>Years</th></tr></thead>
    <tbody>
      ${dasha.mahadasha_timeline
        .map(
          (period) => `
          <tr>
            <td>${period.lord}</td>
            <td>${formatDate(period.start)}</td>
            <td>${formatDate(period.end)}</td>
            <td>${period.duration_years}</td>
          </tr>`
        )
        .join("")}
    </tbody>
  `;
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(value));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
