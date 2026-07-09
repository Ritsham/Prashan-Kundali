import { showFlash } from './flash.js';

async function fetchQueue() {
  try {
    const res = await fetch("/api/consultation/queue");
    if (!res.ok) return;
    const data = await res.json();
    renderQueue(data.queue);
  } catch(e) {
    console.error(e);
    showFlash("Failed to load consultation queue: " + e.message, "error");
  }
}

let activeItem = null;
let queueData = [];

function renderQueue(queue) {
  queueData = queue;
  document.getElementById("q-count").textContent = `${queue.length}/20`;
  const list = document.getElementById("queue-list");
  list.innerHTML = "";
  
  if (queue.length === 0) {
    list.innerHTML = "<li class='text-muted' style='padding: 16px; font-size:14px;'>Queue is empty</li>";
    if (activeItem) {
      document.getElementById("main-view").innerHTML = "<div class='empty-state'>Queue is empty.</div>";
      activeItem = null;
    }
    return;
  }

  queue.forEach(item => {
    const li = document.createElement("li");
    li.className = "queue-item" + (activeItem && activeItem.id === item.id ? " active" : "");
    li.innerHTML = `
      <h4>${item.user_name}</h4>
      <p>SLA: ${new Date(item.sla_deadline).toLocaleString()}</p>
    `;
    li.addEventListener("click", () => selectItem(item.id));
    list.appendChild(li);
  });
}

function selectItem(id) {
  const item = queueData.find(i => i.id === id);
  if (!item) return;
  activeItem = item;
  renderQueue(queueData); // update active class
  const snapshot = parseSnapshot(item.astrological_snapshot);
  const matchBlock = snapshot.type === "matchmaking" ? renderMatchmakingCase(snapshot) : renderStandardChartCase(item);
  
  const main = document.getElementById("main-view");
  main.innerHTML = `
    <div class="detail-card">
      <h2>Consultation for ${item.user_name}</h2>
      <p class="text-muted" style="font-size: 13px;">Deadline: ${new Date(item.sla_deadline).toLocaleString()}</p>
      
      <div class="question-box">
        <strong>Question:</strong><br/>
        ${escapeHtml(item.question_text)}
      </div>

      ${matchBlock}

      <h3 style="margin-top: 24px;">Your Answer</h3>
      <textarea id="answer-input" placeholder="Type your astrological reading and answer here..."></textarea>
      
      <div class="actions">
        <button class="btn-primary" onclick="submitAnswer('${item.id}')">Submit Answer</button>
        <button class="btn-danger" onclick="declineQuestion('${item.id}')">Decline (Refund User)</button>
      </div>
      <p id="action-status" style="margin-top: 12px; font-size:14px;"></p>
    </div>
  `;
}

function renderStandardChartCase(item) {
  return `
    <div class="chart-previews">
      <div class="chart-box">
        <strong>Lagna Chart Snapshot</strong><br/>
        (Pre-calculated data available here)
        <pre style="overflow:auto; height: 100px;">${escapeHtml(JSON.stringify(item.astrological_snapshot.houses || item.astrological_snapshot, null, 2))}</pre>
      </div>
      <div class="chart-box">
        <strong>Transits & Dashas</strong><br/>
        (Pre-calculated data available here)
      </div>
    </div>
  `;
}

function renderMatchmakingCase(snapshot) {
  const report = snapshot.report || {};
  const boy = report.participants?.boy || {};
  const girl = report.participants?.girl || {};
  const ashtakoota = report.ashtakoota || {};
  const summary = report.summary || {};
  const dossier = report.dossier || {};
  const boyChart = report.charts?.boy || {};
  const girlChart = report.charts?.girl || {};
  return `
    <div class="question-box">
      <strong>Matchmaking Case Summary:</strong><br/>
      ${escapeHtml(summary.ai_summary || "Matchmaking report attached for review.")}
    </div>
    <div class="chart-previews">
      <div class="chart-box">
        <strong>Boy Details</strong>
        <p>${escapeHtml(boy.name || "")}<br>${escapeHtml(boy.date_of_birth || "")} ${escapeHtml(boy.time_of_birth || "")}<br>${escapeHtml(boy.birth_place || "")}</p>
        <p><strong>Lagna:</strong> ${escapeHtml(boyChart.lagna?.sign || "")}<br><strong>Moon:</strong> ${escapeHtml(boyChart.moon?.sign || "")}, ${escapeHtml(boyChart.moon?.nakshatra || "")} Pada ${escapeHtml(boyChart.moon?.pada || "")}</p>
      </div>
      <div class="chart-box">
        <strong>Girl Details</strong>
        <p>${escapeHtml(girl.name || "")}<br>${escapeHtml(girl.date_of_birth || "")} ${escapeHtml(girl.time_of_birth || "")}<br>${escapeHtml(girl.birth_place || "")}</p>
        <p><strong>Lagna:</strong> ${escapeHtml(girlChart.lagna?.sign || "")}<br><strong>Moon:</strong> ${escapeHtml(girlChart.moon?.sign || "")}, ${escapeHtml(girlChart.moon?.nakshatra || "")} Pada ${escapeHtml(girlChart.moon?.pada || "")}</p>
      </div>
    </div>
    <div class="question-box">
      <strong>Guna Milan:</strong> ${escapeHtml(ashtakoota.total_score || 0)}/${escapeHtml(ashtakoota.max_score || 36)} (${escapeHtml(ashtakoota.category || "")})<br/>
      <strong>Final Recommendation:</strong> ${escapeHtml(summary.final_recommendation || "")}
    </div>
    <div class="chart-box">
      <strong>Dosha Analysis</strong>
      <pre style="overflow:auto; max-height: 220px;">${escapeHtml(JSON.stringify(report.doshas || [], null, 2))}</pre>
    </div>
    ${renderConsultantDossier(dossier)}
  `;
}

function renderConsultantDossier(dossier = {}) {
  if (!Object.keys(dossier || {}).length) return "";
  return `
    <div class="question-box">
      <strong>Marriage Compatibility Case File</strong><br/>
      ${escapeHtml(dossier.astrologer_note || "Full auto-generated dossier attached.")}
    </div>
    <div class="chart-previews">
      ${consultantInfoBox("Boy Information", dossier.couple_information?.boy)}
      ${consultantInfoBox("Girl Information", dossier.couple_information?.girl)}
    </div>
    <div class="chart-box">
      <strong>Charts to Review</strong>
      <pre style="overflow:auto; max-height: 280px;">${escapeHtml(JSON.stringify(dossier.charts_to_send || {}, null, 2))}</pre>
    </div>
    <div class="chart-box">
      <strong>Planetary Positions</strong>
      <pre style="overflow:auto; max-height: 320px;">${escapeHtml(JSON.stringify(dossier.planetary_positions || {}, null, 2))}</pre>
    </div>
    <div class="chart-box">
      <strong>Complete Guna Milan</strong>
      <pre style="overflow:auto; max-height: 260px;">${escapeHtml(JSON.stringify(dossier.complete_guna_milan || [], null, 2))}</pre>
    </div>
    <div class="chart-box">
      <strong>Detailed Dosha, 7th House, Karaka, Navamsa and Indicators</strong>
      <pre style="overflow:auto; max-height: 420px;">${escapeHtml(JSON.stringify({
        dosha_analysis: dossier.dosha_analysis || [],
        marriage_house_analysis: dossier.marriage_house_analysis || {},
        marriage_karakas: dossier.marriage_karakas || {},
        navamsa_analysis: dossier.navamsa_analysis || {},
        compatibility_indicators: dossier.compatibility_indicators || [],
      }, null, 2))}</pre>
    </div>
  `;
}

function consultantInfoBox(title, person = {}) {
  return `
    <div class="chart-box">
      <strong>${escapeHtml(title)}</strong>
      <p>
        ${escapeHtml(person?.name || "")}<br>
        DOB: ${escapeHtml(person?.date_of_birth || "")}<br>
        Time: ${escapeHtml(person?.time_of_birth || "")}<br>
        Place: ${escapeHtml(person?.birth_place || "")}<br>
        Age: ${escapeHtml(person?.age ?? "Not available")}<br>
        Time accuracy: ${escapeHtml(person?.birth_time_accuracy || "")}
      </p>
    </div>
  `;
}

window.submitAnswer = async function(id) {
  const answer = document.getElementById("answer-input").value.trim();
  const status = document.getElementById("action-status");
  if (answer.length < 5) {
    status.className = "status-error";
    status.textContent = "Answer too short.";
    return;
  }
  
  status.textContent = "Submitting...";
  try {
    const res = await fetch(`/api/consultation/${id}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer })
    });
    if (res.ok) {
      status.className = "status-success";
      status.textContent = "Answer submitted successfully!";
      activeItem = null;
      setTimeout(fetchQueue, 1000);
    } else {
      status.className = "status-error";
      status.textContent = "Failed to submit.";
    }
  } catch(e) {
    status.className = "status-error";
    status.textContent = "Error.";
    showFlash("Error submitting answer: " + e.message, "error");
  }
}

window.declineQuestion = async function(id) {
  if(!confirm("Are you sure you want to decline? The user will be refunded.")) return;
  const status = document.getElementById("action-status");
  status.textContent = "Declining...";
  try {
    const res = await fetch(`/api/consultation/${id}/decline`, { method: "POST" });
    if (res.ok) {
      status.className = "status-success";
      status.textContent = "Declined successfully.";
      activeItem = null;
      setTimeout(fetchQueue, 1000);
    } else {
      status.className = "status-error";
      status.textContent = "Failed to decline.";
    }
  } catch(e) {
    status.className = "status-error";
    status.textContent = "Error.";
    showFlash("Error declining case: " + e.message, "error");
  }
}

fetchQueue();
setInterval(fetchQueue, 5000);

function parseSnapshot(value) {
  if (!value) return {};
  if (typeof value === "object") return value;
  try {
    return JSON.parse(value);
  } catch {
    return {};
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
