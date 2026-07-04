const summaryEl = document.querySelector("#summary");
const caseListEl = document.querySelector("#case-list");
const filterEl = document.querySelector("#case-filter");
const refreshButton = document.querySelector("#refresh-button");
let validationData = null;

const expectedFields = [
  ["expected_lagna_sign", "Lagna Sign"],
  ["expected_lagna_degree", "Lagna Degree"],
  ["expected_moon_sign", "Moon Sign"],
  ["expected_moon_nakshatra", "Moon Nakshatra"],
  ["expected_moon_pada", "Moon Pada"],
  ["expected_mahadasha", "Mahadasha"],
  ["expected_antardasha", "Antardasha"],
];

refreshButton.addEventListener("click", loadCases);
filterEl.addEventListener("input", renderCases);

loadCases();

async function loadCases() {
  summaryEl.innerHTML = fact("Loading", "Validation cases");
  const response = await fetch("/api/validation/cases");
  validationData = await response.json();
  renderSummary();
  renderCases();
}

function renderSummary() {
  const s = validationData.summary;
  summaryEl.innerHTML = [
    fact("Cases", s.total_cases),
    fact("Coverage", `${s.coverage_percent}%`),
    fact("Passed", s.passed_cases),
    fact("Failed", s.failed_cases),
  ].join("");
}

function renderCases() {
  if (!validationData) return;
  const term = filterEl.value.trim().toLowerCase();
  const cases = validationData.cases.filter((item) => {
    const text = `${item.case.case_id} ${item.case.place_name} ${item.case.category} ${item.status}`.toLowerCase();
    return text.includes(term);
  });
  caseListEl.innerHTML = cases.map(renderCaseCard).join("");
  caseListEl.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", saveCase);
  });
}

function renderCaseCard(item) {
  const row = item.case;
  const actual = item.actual;
  return `
    <article class="case-card">
      <div class="case-top">
        <div>
          <h2 class="case-title">${row.case_id}</h2>
          <p class="case-meta">${row.question}<br>${row.place_name} · ${row.asked_at_utc} · ${row.category}</p>
        </div>
        <span class="badge ${item.status}">${item.status}</span>
      </div>
      <div class="case-body">
        <div class="panel">
          <h3>Reference Input</h3>
          <div class="kv">
            <div><span>UTC</span><strong>${row.asked_at_utc}</strong></div>
            <div><span>Latitude</span><strong>${row.latitude}</strong></div>
            <div><span>Longitude</span><strong>${row.longitude}</strong></div>
            <div><span>Ayanamsa</span><strong>Lahiri</strong></div>
            <div><span>House</span><strong>Whole sign</strong></div>
          </div>
        </div>
        <div class="panel">
          <h3>Our Output</h3>
          <div class="actual-grid">
            ${actualItem("Lagna", `${actual.lagna_sign} ${actual.lagna_degree}`)}
            ${actualItem("Lagna Nakshatra", `${actual.lagna_nakshatra} Pada ${actual.lagna_pada}`)}
            ${actualItem("Moon", `${actual.moon_sign} ${actual.moon_degree}`)}
            ${actualItem("Moon Nakshatra", `${actual.moon_nakshatra} Pada ${actual.moon_pada}`)}
            ${actualItem("Maha / Antar", `${actual.mahadasha} / ${actual.antardasha}`)}
            ${actualItem("Pratyantar / Sookshma", `${actual.pratyantardasha} / ${actual.sookshma}`)}
            ${actualItem("Prana", actual.prana)}
            ${actualItem("Ayanamsa", `${actual.ayanamsa_degrees}°`)}
            ${actualItem("Local Ephemeris", actual.ephemeris_core_files_present ? "Yes" : "No")}
          </div>
        </div>
        <div class="panel">
          <h3>Trusted Expected</h3>
          <form class="expected-form" data-case-id="${row.case_id}">
            ${expectedFields.map(([key, label]) => inputField(key, label, row[key] || "")).join("")}
            <label class="wide">Source Notes<textarea name="source_notes" rows="2">${escapeHtml(row.source_notes || "")}</textarea></label>
            ${item.mismatches.length ? `<p class="mismatch">Mismatch: ${item.mismatches.join(", ")}</p>` : ""}
            <button type="submit">Save Expected Values</button>
          </form>
        </div>
      </div>
    </article>
  `;
}

async function saveCase(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form).entries());
  const response = await fetch(`/api/validation/cases/${form.dataset.caseId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    alert("Could not save validation case.");
    return;
  }
  await loadCases();
}

function inputField(name, label, value) {
  return `<label>${label}<input name="${name}" value="${escapeHtml(value)}" /></label>`;
}

function actualItem(label, value) {
  return `<div class="actual-item"><span>${label}</span><strong>${value}</strong></div>`;
}

function fact(label, value) {
  return `<div class="fact"><span>${label}</span><strong>${value}</strong></div>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
