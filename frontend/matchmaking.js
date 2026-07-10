import { AppState } from './state.js';
import { API } from './api.js';
import { initAuth } from './auth.js';
import { showFlash } from './flash.js';
import { KundaliChart } from './chart-engine.js';
import { DashaWidget } from './dasha-engine.js';

const form = document.querySelector("#match-form");
const statusEl = document.querySelector("#match-status");
const resultEl = document.querySelector("#match-result");
const submitBtn = document.querySelector("#btn-generate-match");
let activeMatchId = "";
let activeReport = null;
const BOOKING_CONTEXT_KEY = "matchmaking_booking_context";

initAuth();
disableNameAutofill();
initPlaceSearch("boy");
initPlaceSearch("girl");

document.addEventListener("astro:authChanged", (event) => {
  const signedIn = Boolean(event.detail);
  document.querySelector("#btn-login-header")?.classList.toggle("hidden", signedIn);
  document.querySelector("#btn-logout")?.classList.toggle("hidden", !signedIn);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!AppState.session && !localStorage.getItem("supabase_token")) {
    document.querySelector("#auth-modal")?.classList.remove("hidden");
    return;
  }

  const payload = formPayload(new FormData(form));
  const locationError = validateSelectedPlaces(payload);
  if (locationError) {
    statusEl.textContent = locationError;
    showFlash(locationError, "error");
    return;
  }
  resultEl.classList.add("hidden");
  statusEl.textContent = "Generating charts, calculating Koota scores, and checking Doshas...";
  submitBtn.disabled = true;

  try {
    const data = await API.post("/api/matchmaking/requests", payload);
    activeMatchId = data.match_id;
    activeReport = data.report;
    renderResult(data.match_id, data.report);
    statusEl.textContent = "Match report generated.";
    showFlash("Match report generated successfully.", "success");
  } catch (error) {
    statusEl.textContent = error.message;
  } finally {
    submitBtn.disabled = false;
  }
});

function formPayload(fd) {
  return {
    boy: participantPayload(fd, "boy"),
    girl: participantPayload(fd, "girl"),
  };
}

function participantPayload(fd, prefix) {
  return {
    name: String(fd.get(`${prefix}_person_entry`) || fd.get(`${prefix}_name`) || "").trim(),
    date_of_birth: String(fd.get(`${prefix}_date_of_birth`) || ""),
    time_of_birth: String(fd.get(`${prefix}_time_of_birth`) || ""),
    birth_place: String(fd.get(`${prefix}_place_name`) || fd.get(`${prefix}_birth_place`) || "").trim(),
    latitude: numberOrNull(fd.get(`${prefix}_latitude`)),
    longitude: numberOrNull(fd.get(`${prefix}_longitude`)),
    selected_place_name: String(fd.get(`${prefix}_place_name`) || "").trim(),
    gender: String(fd.get(`${prefix}_gender`) || ""),
    birth_time_accuracy: String(fd.get(`${prefix}_birth_time_accuracy`) || "exact"),
  };
}

function disableNameAutofill() {
  form.querySelectorAll("[data-person-name]").forEach((input) => {
    input.setAttribute("autocomplete", "one-time-code");
    input.setAttribute("aria-autocomplete", "none");
    input.setAttribute("data-lpignore", "true");
    input.setAttribute("data-1p-ignore", "");
    input.readOnly = true;

    input.addEventListener("focus", () => {
      input.setAttribute("autocomplete", "one-time-code");
      window.setTimeout(() => {
        input.readOnly = false;
      }, 150);
    });

    input.addEventListener("blur", () => {
      input.readOnly = true;
    });

    input.addEventListener("keydown", () => {
      input.readOnly = false;
    });

    input.addEventListener("pointerdown", () => {
      window.setTimeout(() => {
        input.readOnly = false;
      }, 150);
    });
  });
}

function initPlaceSearch(prefix) {
  const input = form.querySelector(`[data-place-input="${prefix}"]`);
  const resultsEl = form.querySelector(`[data-place-results="${prefix}"]`);
  const nameInput = form.querySelector(`[data-place-name="${prefix}"]`);
  const latInput = form.querySelector(`[data-place-latitude="${prefix}"]`);
  const lonInput = form.querySelector(`[data-place-longitude="${prefix}"]`);
  if (!input || !resultsEl) return;

  let debounceId = 0;
  input.addEventListener("input", () => {
    nameInput.value = "";
    latInput.value = "";
    lonInput.value = "";
    clearTimeout(debounceId);
    const query = input.value.trim();
    if (query.length < 2) {
      resultsEl.classList.add("hidden");
      resultsEl.innerHTML = "";
      return;
    }
    debounceId = setTimeout(() => searchPlaces(prefix, query), 350);
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(`[data-place-results="${prefix}"]`) && event.target !== input) {
      resultsEl.classList.add("hidden");
    }
  });
}

async function searchPlaces(prefix, query) {
  const resultsEl = form.querySelector(`[data-place-results="${prefix}"]`);
  resultsEl.classList.remove("hidden");
  resultsEl.innerHTML = `<div class="match-place-loading">Searching places...</div>`;
  try {
    const data = await API.get(`/api/geocode?query=${encodeURIComponent(query)}&limit=8`, false);
    const results = Array.isArray(data.results) ? data.results : [];
    if (!results.length) {
      resultsEl.innerHTML = `<div class="match-place-empty">No place found. Try city, state, country.</div>`;
      return;
    }
    renderPlaceResults(prefix, results);
  } catch (error) {
    resultsEl.innerHTML = `<div class="match-place-empty">${escapeHtml(error.message || "Place search failed.")}</div>`;
  }
}

function renderPlaceResults(prefix, results) {
  const resultsEl = form.querySelector(`[data-place-results="${prefix}"]`);
  resultsEl.innerHTML = results.map((place, index) => `
    <button type="button" class="match-place-option" data-index="${index}">
      <strong>${escapeHtml(place.place_name)}</strong>
      <span>${escapeHtml(place.latitude)}, ${escapeHtml(place.longitude)} · ${escapeHtml(place.source || place.type || "place")}</span>
    </button>
  `).join("");
  resultsEl.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => selectPlace(prefix, results[Number(button.dataset.index)]));
  });
}

function selectPlace(prefix, place) {
  const input = form.querySelector(`[data-place-input="${prefix}"]`);
  const resultsEl = form.querySelector(`[data-place-results="${prefix}"]`);
  const nameInput = form.querySelector(`[data-place-name="${prefix}"]`);
  const latInput = form.querySelector(`[data-place-latitude="${prefix}"]`);
  const lonInput = form.querySelector(`[data-place-longitude="${prefix}"]`);
  input.value = place.place_name;
  nameInput.value = place.place_name;
  latInput.value = place.latitude;
  lonInput.value = place.longitude;
  resultsEl.innerHTML = `
    <div class="match-selected-place">
      <strong>${escapeHtml(place.place_name)}</strong>
      <span>${escapeHtml(place.latitude)}, ${escapeHtml(place.longitude)}</span>
    </div>
  `;
  resultsEl.classList.remove("hidden");
}

function validateSelectedPlaces(payload) {
  for (const role of ["boy", "girl"]) {
    const person = payload[role];
    if (!Number.isFinite(person.latitude) || !Number.isFinite(person.longitude) || !person.selected_place_name) {
      return `Please select the ${role}'s birth place from the dropdown so latitude and longitude are saved correctly.`;
    }
  }
  return "";
}

function numberOrNull(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function renderResult(matchId, report) {
  const summary = report.summary;
  const ashtakoota = report.ashtakoota;
  const boy = report.charts.boy;
  const girl = report.charts.girl;
  resultEl.innerHTML = `
    <div class="result-topline">
      <div>
        <p class="eyebrow">Match Result</p>
        <h2>${escapeHtml(summary.overall_result)}</h2>
        <p>${escapeHtml(summary.final_recommendation)}</p>
      </div>
      <div class="score-ring">
        <strong>${escapeHtml(String(ashtakoota.total_score))}</strong>
        <span>/ 36</span>
      </div>
    </div>

    <div class="match-tabs" role="tablist" aria-label="Matchmaking report sections">
      <button type="button" class="match-tab active" data-match-tab="analysis">System Analysis</button>
      <button type="button" class="match-tab" data-match-tab="charts">Charts & Positions</button>
    </div>

    <div class="match-tab-panel active" data-match-panel="analysis">
      <div class="match-snapshot-grid">
        ${chartSnapshot("Boy", boy)}
        ${chartSnapshot("Girl", girl)}
      </div>

      <div class="match-section">
        <h3>8 Koota Breakdown</h3>
        <div class="koota-table">
          ${ashtakoota.kootas.map(kootaRow).join("")}
        </div>
      </div>

      <div class="match-section">
        <h3>Dosha Analysis</h3>
        <div class="dosha-grid">
          ${report.doshas.map(doshaCard).join("")}
        </div>
      </div>

      <div class="match-section match-summary-grid">
        <div>
          <h3>Strengths</h3>
          <ul>${summary.strengths.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </div>
        <div>
          <h3>Areas of Concern</h3>
          <ul>${(summary.areas_of_concern.length ? summary.areas_of_concern : ["No major concern from the basic checks."]).map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </div>
      </div>
    </div>

    <div class="match-tab-panel" data-match-panel="charts">
      ${renderDossier(report)}
    </div>

    <div class="consult-match-card">
      <div>
        <p class="eyebrow">Astrologer Consultation</p>
        <h3>Consult an Astrologer About This Match</h3>
        <p>Book Rupesh Kumar for this match. He will receive the complete Marriage Compatibility Case File: couple details, D1/D9/Moon chart summaries, planetary positions, Guna Milan, Dosha analysis, 7th house review points, karakas, Navamsa notes, and your question automatically.</p>
      </div>
      <label>Ask a follow-up question
        <textarea id="match-question" placeholder="Example: Please review Mangal Dosha and long-term marriage stability."></textarea>
      </label>
      <div class="consult-actions">
        <button type="button" class="btn-submit" id="btn-book-match">Book Consultant</button>
      </div>
      <div id="consultant-booking-panel" class="consultant-booking-panel hidden"></div>
      <p id="consult-status"></p>
    </div>

    <p class="match-disclaimer">${escapeHtml(report.disclaimer)} Personal values, mutual understanding, family context, health, consent, communication, and practical compatibility should also be considered.</p>
  `;
  resultEl.classList.remove("hidden");
  resultEl.scrollIntoView({ behavior: "smooth", block: "start" });

  // Initialize Canvas Charts
  const canvases = resultEl.querySelectorAll('.kundali-canvas');
  const dossier = report.dossier || {};
  const chartsData = dossier.charts_to_send || {};
  const mandatory = chartsData.mandatory || [];
  const chartPairsData = [
    { boy: mandatory[0], girl: mandatory[1] },
    { boy: mandatory[2], girl: mandatory[3] },
    { boy: mandatory[4], girl: mandatory[5] },
    { boy: mandatory[6], girl: mandatory[7] },
  ];

  canvases.forEach(canvas => {
    const person = canvas.dataset.person;
    const index = parseInt(canvas.dataset.chartIndex, 10);
    const pair = chartPairsData[index];
    if (pair && pair[person] && pair[person].chart) {
      new KundaliChart(canvas, pair[person].chart, { 
        responsive: true,
        darkTheme: false,
        lineColor: '#C8A261',
        textColor: '#211C4D'
      });
    }
  });

  // Mount 5-level Vimshottari Dasha Widgets
  const boyDashaEl = resultEl.querySelector('#dasha-mount-boy');
  const girlDashaEl = resultEl.querySelector('#dasha-mount-girl');

  const boyDashas = report.charts?.boy?.dashas;
  const girlDashas = report.charts?.girl?.dashas;
  console.debug('[Matchmaking] Boy dashas:', boyDashas);
  console.debug('[Matchmaking] Girl dashas:', girlDashas);

  if (boyDashaEl) {
    new DashaWidget(boyDashaEl, boyDashas, { personLabel: 'Boy' }).render();
  }
  if (girlDashaEl) {
    new DashaWidget(girlDashaEl, girlDashas, { personLabel: 'Girl' }).render();
  }

  resultEl.querySelector("#btn-book-match").addEventListener("click", () => openConsultantBooking(matchId, report));
  resultEl.querySelectorAll("[data-match-tab]").forEach((button) => {
    button.addEventListener("click", () => switchMatchTab(button.dataset.matchTab));
  });
}

function switchMatchTab(tab) {
  resultEl.querySelectorAll("[data-match-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.matchTab === tab);
  });
  resultEl.querySelectorAll("[data-match-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.matchPanel === tab);
  });
}

function chartSnapshot(label, chart) {
  return `
    <article class="match-chart-card">
      <h3>${label}: ${escapeHtml(chart.birth.name || "")}</h3>
      <dl>
        <div><dt>Lagna</dt><dd>${escapeHtml(chart.lagna.sign || "")} ${escapeHtml(chart.lagna.formatted_degree || "")}</dd></div>
        <div><dt>Moon Sign</dt><dd>${escapeHtml(chart.moon.sign || "")}</dd></div>
        <div><dt>Nakshatra</dt><dd>${escapeHtml(chart.moon.nakshatra || "")}, Pada ${escapeHtml(String(chart.moon.pada || ""))}</dd></div>
        <div><dt>Place</dt><dd>${escapeHtml(chart.birth.place_name || "")}</dd></div>
      </dl>
    </article>
  `;
}

function kootaRow(item) {
  return `
    <div class="koota-row">
      <strong>${escapeHtml(item.name)}</strong>
      <span>${escapeHtml(String(item.score))}/${escapeHtml(String(item.max_score))}</span>
      <em class="${escapeHtml(item.status)}">${escapeHtml(item.status)}</em>
      <p>${escapeHtml(item.interpretation)}</p>
    </div>
  `;
}

function doshaCard(item) {
  return `
    <article class="dosha-card severity-${escapeHtml(item.severity)}">
      <div>
        <h4>${escapeHtml(item.name)}</h4>
        <span>${escapeHtml(item.severity)}</span>
      </div>
      <p>${escapeHtml(item.explanation)}</p>
      ${item.review_recommended ? "<strong>Astrologer review recommended</strong>" : "<strong>No major issue detected in this basic check</strong>"}
    </article>
  `;
}

function renderDossier(report) {
  const dossier = report.dossier || {};
  const couple = dossier.couple_information || {};
  const charts = dossier.charts_to_send || {};
  const mandatory = charts.mandatory || [];

  // Group charts into pairs: [Boy X, Girl X] rendered side by side
  const chartPairs = [
    { label: "D1 Lagna Chart", purpose: "Marriage promise, 7th house & planetary placements", boy: mandatory[0], girl: mandatory[1] },
    { label: "D9 Navamsa Chart", purpose: "Marriage strength, spouse indications & long-term compatibility", boy: mandatory[2], girl: mandatory[3] },
    { label: "Moon Chart", purpose: "Emotional compatibility, Guna Milan & marriage happiness", boy: mandatory[4], girl: mandatory[5] },
    { label: "Bhava Chalit Chart", purpose: "House cusps & planet occupation by house", boy: mandatory[6], girl: mandatory[7] },
  ];

  return `
    <div class="match-section">
      <h3>Marriage Compatibility Case File</h3>
      <p class="dossier-note">${escapeHtml(dossier.astrologer_note || "This complete case file is sent to the astrologer during booking.")}</p>
      <div class="match-summary-grid">
        ${personInfoCard("Boy", couple.boy)}
        ${personInfoCard("Girl", couple.girl)}
      </div>
    </div>

    ${chartPairs.map((pair, index) => chartPairSection(pair, index)).join("")}

    <div class="match-section">
      <h3>Vimshottari Dasha</h3>
      <p class="dasha-intro-note">5-level drill-down: Mahadasha → Antardasha → Pratyantardasha → Sookshma → Prana</p>
      <div class="dasha-widget-grid">
        ${dashaTablePlaceholder("boy")}
        ${dashaTablePlaceholder("girl")}
      </div>
    </div>

    <div class="match-section">
      <h3>Planetary Position Table</h3>
      <div class="match-summary-grid">
        ${planetTable("Boy", dossier.planetary_positions?.boy || [])}
        ${planetTable("Girl", dossier.planetary_positions?.girl || [])}
      </div>
    </div>

    <div class="match-section">
      <h3>Detailed Guna Milan</h3>
      <div class="koota-table">
        ${(dossier.complete_guna_milan || []).map(gunaDossierRow).join("")}
      </div>
    </div>

    <div class="match-section">
      <h3>Detailed Dosha Analysis</h3>
      <div class="dosha-grid">
        ${(dossier.dosha_analysis || []).map(detailedDoshaCard).join("")}
      </div>
    </div>

    <div class="match-section">
      <h3>Marriage House, Karakas & Navamsa</h3>
      <div class="dossier-card-grid">
        ${analysisCard("Boy 7th House", dossier.marriage_house_analysis?.boy)}
        ${analysisCard("Girl 7th House", dossier.marriage_house_analysis?.girl)}
        ${analysisCard("Boy Karakas", dossier.marriage_karakas?.boy)}
        ${analysisCard("Girl Karakas", dossier.marriage_karakas?.girl)}
        ${analysisCard("Boy Navamsa", dossier.navamsa_analysis?.boy)}
        ${analysisCard("Girl Navamsa", dossier.navamsa_analysis?.girl)}
      </div>
    </div>

    <div class="match-section">
      <h3>Compatibility Indicators</h3>
      <div class="dossier-card-grid">
        ${(dossier.compatibility_indicators || []).map(indicatorCard).join("")}
      </div>
    </div>
  `;
}

function chartPairSection(pair, index) {
  const boy = pair.boy || {};
  const girl = pair.girl || {};
  const boyName = boy.name || `Boy ${pair.label}`;
  const girlName = girl.name || `Girl ${pair.label}`;
  return `
    <div class="match-section chart-pair-section">
      <div class="chart-pair-header">
        <h3>${escapeHtml(pair.label)}</h3>
        <p class="chart-pair-purpose">${escapeHtml(pair.purpose)}</p>
      </div>
      <div class="chart-pair-grid">
        <div class="chart-pair-block">
          <div class="chart-pair-label">♂ Boy</div>
          ${chartMeta(boy)}
          ${boy.chart ? `<canvas class="responsive-canvas kundali-canvas" data-person="boy" data-chart-index="${index}"></canvas>` : emptyChartPlaceholder()}
        </div>
        <div class="chart-pair-block">
          <div class="chart-pair-label">♀ Girl</div>
          ${chartMeta(girl)}
          ${girl.chart ? `<canvas class="responsive-canvas kundali-canvas" data-person="girl" data-chart-index="${index}"></canvas>` : emptyChartPlaceholder()}
        </div>
      </div>
    </div>
  `;
}

function chartMeta(item) {
  if (!item || typeof item !== "object") return "";
  const parts = [];
  if (item.lagna) {
    const lagnaSign = typeof item.lagna === "object" ? (item.lagna.sign || "") : String(item.lagna);
    if (lagnaSign) parts.push(`<span class="chart-meta-pill"><strong>Lagna:</strong> ${escapeHtml(lagnaSign)}</span>`);
  }
  if (item.moon && item.moon.sign) {
    parts.push(`<span class="chart-meta-pill"><strong>Moon:</strong> ${escapeHtml(item.moon.sign || "")}, ${escapeHtml(item.moon.nakshatra || "")} P${escapeHtml(String(item.moon.pada || ""))}</span>`);
  }
  if (item.seventh_house && item.seventh_house.seventh_house) {
    parts.push(`<span class="chart-meta-pill"><strong>7th:</strong> ${escapeHtml(item.seventh_house.seventh_house)} · Lord ${escapeHtml(item.seventh_house.seventh_lord || "")}</span>`);
  }
  if (item.moon_sign) {
    parts.push(`<span class="chart-meta-pill"><strong>Moon:</strong> ${escapeHtml(item.moon_sign || "")}</span>`);
  }
  if (parts.length === 0) return "";
  return `<div class="chart-meta-row">${parts.join("")}</div>`;
}

function emptyChartPlaceholder() {
  return `<div class="chart-empty-placeholder"><span>Chart data unavailable</span></div>`;
}

function personInfoCard(label, person = {}) {
  return `
    <article class="match-chart-card">
      <h3>${escapeHtml(label)} Information</h3>
      <dl>
        ${infoRow("Name", person.name)}
        ${infoRow("DOB", person.date_of_birth)}
        ${infoRow("Birth Time", person.time_of_birth)}
        ${infoRow("Birth Place", person.birth_place)}
        ${infoRow("Age", person.age ?? "Not available")}
        ${infoRow("Time Accuracy", person.birth_time_accuracy)}
      </dl>
    </article>
  `;
}

// Canvas Engine is now used for charts instead of getNorthIndianSVG.

function chartDossierCard(item = {}) {
  // Used only as fallback; main chart display is via chartPairSection
  return `
    <article class="dossier-card">
      <h4>${escapeHtml(item.name || "")}</h4>
      <p>${escapeHtml(item.purpose || "")}</p>
    </article>
  `;
}

function optionalDossierCard(item = {}) {
  return `
    <article class="dossier-card">
      <h4>${escapeHtml(item.name || "")}</h4>
      <p><strong>${escapeHtml(item.status || "")}</strong></p>
      <p>${escapeHtml(item.purpose || "")}</p>
    </article>
  `;
}

function dashaTablePlaceholder(person) {
  // Returns an empty mount-point div; actual DashaWidget is mounted after the HTML is inserted into the DOM.
  return `<div class="dasha-widget-mount" id="dasha-mount-${escapeHtml(person)}"></div>`;
}

function planetTable(label, rows) {
  return `
    <div class="planet-position-card">
      <h4>${escapeHtml(label)} Positions</h4>
      <div class="planet-position-table">
        <div class="planet-position-head">Planet</div>
        <div class="planet-position-head">Sign</div>
        <div class="planet-position-head">House</div>
        <div class="planet-position-head">Nakshatra</div>
        ${rows.map(row => `
          <div>${escapeHtml(row.planet)}</div>
          <div>${escapeHtml(row.sign)}</div>
          <div>${escapeHtml(row.house)}</div>
          <div>${escapeHtml(row.nakshatra)} Pada ${escapeHtml(row.pada)}${row.retrograde ? " · R" : ""}</div>
        `).join("")}
      </div>
    </div>
  `;
}

function gunaDossierRow(item = {}) {
  return `
    <div class="koota-row">
      <strong>${escapeHtml(item.name)}</strong>
      <span>${escapeHtml(item.obtained)}/${escapeHtml(item.maximum)}</span>
      <em class="${escapeHtml(item.remarks)}">${escapeHtml(item.remarks)}</em>
      <p>${escapeHtml(item.explanation)}</p>
    </div>
  `;
}

function detailedDoshaCard(item = {}) {
  return `
    <article class="dosha-card severity-${escapeHtml(item.severity || "none")}">
      <div>
        <h4>${escapeHtml(item.name || "")}</h4>
        <span>${escapeHtml(item.severity || "none")}</span>
      </div>
      <p><strong>Present:</strong> ${item.present ? "Yes" : "No"}</p>
      <p>${escapeHtml(item.reason || "")}</p>
      <p><strong>Effective result:</strong> ${escapeHtml(item.effective_result || "")}</p>
    </article>
  `;
}

function analysisCard(title, data = {}) {
  return `
    <article class="dossier-card">
      <h4>${escapeHtml(title)}</h4>
      <dl>
        ${Object.entries(data || {}).map(([key, value]) => infoRow(humanize(key), Array.isArray(value) ? value.join(", ") : value)).join("")}
      </dl>
    </article>
  `;
}

function indicatorCard(item = {}) {
  return `
    <article class="dossier-card">
      <h4>${escapeHtml(item.name || "")}</h4>
      <p><strong>${escapeHtml(item.status || "")}</strong></p>
      <p>${escapeHtml(item.remarks || "")}</p>
    </article>
  `;
}

function infoRow(label, value) {
  return `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value ?? "Not available")}</dd></div>`;
}

function humanize(value) {
  return String(value || "").replaceAll("_", " ").replace(/\b\w/g, char => char.toUpperCase());
}

async function openConsultantBooking(matchId, report) {
  const status = resultEl.querySelector("#consult-status");
  const question = resultEl.querySelector("#match-question").value.trim();
  if (question.length < 3) {
    status.textContent = "Please type your question before booking the consultant.";
    showFlash("Please type your question before booking.", "error");
    return;
  }
  sessionStorage.setItem(BOOKING_CONTEXT_KEY, JSON.stringify({
    matchId,
    report,
    question,
    savedAt: new Date().toISOString(),
  }));
  window.location.assign(`/matchmaking-booking.html?match_id=${encodeURIComponent(matchId)}`);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
