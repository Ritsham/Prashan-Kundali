const form = document.getElementById("consultation-form");
const submitBtn = document.getElementById("submit-btn");
const resultPanel = document.getElementById("result-panel");
const resultStatus = document.getElementById("result-status");
const resultTitle = document.getElementById("result-title");
const resultMessage = document.getElementById("result-message");
const resultDetails = document.getElementById("result-details");
const refreshStatusBtn = document.getElementById("refresh-status-btn");
const clearStatusBtn = document.getElementById("clear-status-btn");
const topicEl = document.getElementById("topic");
const dateLabel = document.getElementById("date-label");
const timeLabel = document.getElementById("time-label");
const placeLabel = document.getElementById("place-label");
const placeSearchInput = document.getElementById("place_search");
const placeResultsEl = document.getElementById("place-results");
let _placeDebounce = null;

placeSearchInput.addEventListener("input", () => {
  document.getElementById("place_of_birth").value = "";
  clearTimeout(_placeDebounce);
  const q = placeSearchInput.value.trim();
  if (q.length < 2) { placeResultsEl.innerHTML = ""; return; }
  placeResultsEl.innerHTML = `<div class="place-result" style="padding: 12px; color: #6f6153; background: #fff; border-bottom: 1px solid #efe5d8;">Searching…</div>`;
  _placeDebounce = setTimeout(searchPlace, 400);
});

async function searchPlace() {
  const query = placeSearchInput.value.trim();
  if (query.length < 2) return;
  try {
    const res = await fetch(`/api/geocode?query=${encodeURIComponent(query)}&limit=6`);
    const data = await res.json();
    renderPlaceResults(data.results);
  } catch (error) {
    placeResultsEl.innerHTML = `<div class="place-result" style="padding: 12px; color: #6f6153; background: #fff; border-bottom: 1px solid #efe5d8;">Search failed</div>`;
  }
}

function renderPlaceResults(results) {
  if (!results || !results.length) { placeResultsEl.innerHTML = `<div class="place-result" style="padding: 12px; color: #6f6153; background: #fff; border-bottom: 1px solid #efe5d8;">No results found.</div>`; return; }
  placeResultsEl.innerHTML = results.map((item, index) => `
      <button type="button" class="place-result" style="width: 100%; text-align: left; padding: 12px; border: none; border-bottom: 1px solid #efe5d8; background: #fff; cursor: pointer; color: #241f1a;" data-index="${index}">
        <strong style="display: block; font-size: 14px; margin-bottom: 4px;">${escapeHtml(item.place_name)}</strong>
        <span style="display: block; font-size: 12px; color: #6f6153;">Lat: ${item.latitude}, Lon: ${item.longitude}</span>
      </button>`
  ).join("");

  placeResultsEl.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      const place = results[Number(button.dataset.index)];
      document.getElementById("place_of_birth").value = `${place.place_name} (Lat: ${place.latitude}, Lon: ${place.longitude})`;
      placeSearchInput.value = place.place_name;
      placeResultsEl.innerHTML = "";
    });
  });
}

document.addEventListener("click", (e) => {
  if (placeResultsEl && !e.target.closest("#place_search") && !e.target.closest("#place-results")) {
    placeResultsEl.innerHTML = "";
  }
});
const queueActive = document.getElementById("queue-active");
const queueAvailable = document.getElementById("queue-available");
const queueWaiting = document.getElementById("queue-waiting");
const queueOpen = document.getElementById("queue-open");
const queueNote = document.getElementById("queue-note");
const LATEST_REQUEST_KEY = "latest_consultation_request_id";

function value(id) {
  return document.getElementById(id).value.trim();
}

function escapeHtml(raw) {
  return String(raw || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function loadConsultantProfile() {
  try {
    const res = await fetch("/api/consultation/profile");
    if (!res.ok) return;
    const data = await res.json();
    const c = data.consultant;
    document.getElementById("consultant-name").textContent = c.name;
    document.getElementById("consultant-photo").src = c.photo_url;
    document.getElementById("consultant-bio").textContent = c.bio;
    document.getElementById("consultant-experience").textContent = c.experience;
    document.getElementById("consultant-systems").textContent = (c.systems || []).join(", ");
    document.getElementById("consultant-languages").textContent = (c.languages || []).join(", ");
    document.getElementById("consultant-type").textContent = c.consultation_type;
    document.getElementById("positioning").textContent = data.positioning;
  } catch (err) {
    console.error("Failed to load consultant profile", err);
  }
}

async function loadQueueStatus() {
  try {
    const res = await fetch("/api/consultation/request-status", { cache: "no-store" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not load queue.");

    queueActive.textContent = `${data.active_count}/${data.max_active}`;
    queueAvailable.textContent = data.available_slots;
    queueWaiting.textContent = data.waiting_count;
    queueOpen.textContent = data.can_request_active_slot ? "Open" : "Full";
    queueNote.textContent = data.can_request_active_slot
      ? "Slots are currently available. New requests will enter active review."
      : "All active slots are full. New requests will enter the waiting queue.";
  } catch (err) {
    queueActive.textContent = "--/20";
    queueAvailable.textContent = "--";
    queueWaiting.textContent = "--";
    queueOpen.textContent = "--";
    queueNote.textContent = "Live queue is temporarily unavailable. You can still submit a request.";
  }
}

function updateTopicFields() {
  const isPrashna = topicEl.value === "Prashna";
  dateLabel.textContent = isPrashna ? "Date of Question" : "Date of Birth";
  timeLabel.textContent = isPrashna ? "Time of Question" : "Time of Birth";
  placeLabel.textContent = isPrashna ? "Place of Question" : "Place of Birth";
  if (placeSearchInput) {
    placeSearchInput.placeholder = isPrashna ? "Where the question is being asked" : "Search city...";
  }
}

function renderRequestStatus(request, message, slotAvailable = true) {
  resultStatus.textContent = request.status;
  resultStatus.className = `status-pill ${request.status}`;
  resultTitle.textContent = slotAvailable ? "Your request is active" : "Added to waiting queue";
  if (request.status === "accepted") resultTitle.textContent = "Your request is accepted";
  if (request.status === "in_progress") resultTitle.textContent = "Consultation is in progress";
  if (request.status === "completed") resultTitle.textContent = "Consultation completed";
  if (request.status === "rejected") resultTitle.textContent = "Request rejected";
  if (request.status === "cancelled") resultTitle.textContent = "Request cancelled";
  if (request.status === "waiting_queue") resultTitle.textContent = "Added to waiting queue";

  resultMessage.textContent = message || statusMessageFor(request.status);
  resultDetails.innerHTML = `
    <div><strong>Request ID:</strong> ${escapeHtml(request.id)}</div>
    <div><strong>Request status:</strong> ${escapeHtml(request.status)}</div>
    <div><strong>Queue number:</strong> ${request.queue_number ? escapeHtml(request.queue_number) : "Active slot"}</div>
    <div><strong>Submitted question:</strong> ${escapeHtml(request.question)}</div>
    <div><strong>Consultant name:</strong> Rupesh Kumar</div>
    <div><strong>Scheduled date/time:</strong> ${request.scheduled_at ? escapeHtml(request.scheduled_at) : "Not scheduled yet"}</div>
    <div><strong>Meeting link:</strong> ${request.meeting_link ? `<a href="${escapeHtml(request.meeting_link)}" target="_blank">${escapeHtml(request.meeting_link)}</a>` : "Not added yet"}</div>
  `;
  resultPanel.classList.add("show");
}

function statusMessageFor(status) {
  if (status === "waiting_queue") {
    return "Currently, all consultation slots are full. You are in the waiting queue and will be notified when your turn comes.";
  }
  if (status === "accepted") {
    return "Your consultation request has been accepted. Please check the scheduled time and meeting link once added.";
  }
  if (status === "in_progress") {
    return "Your consultation is currently in progress.";
  }
  if (status === "completed") {
    return "Your consultation has been completed.";
  }
  if (status === "rejected") {
    return "Your consultation request was rejected. Please contact support if you need clarification.";
  }
  if (status === "cancelled") {
    return "Your consultation request was cancelled.";
  }
  return "Your consultation request has been received. The consultant will review it soon.";
}

async function loadLatestRequestStatus() {
  const requestId = localStorage.getItem(LATEST_REQUEST_KEY);
  if (!requestId) return;

  try {
    const res = await fetch(`/api/consultation/request/${encodeURIComponent(requestId)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not load latest request.");
    renderRequestStatus(data.request);
  } catch (err) {
    resultStatus.textContent = "not found";
    resultStatus.className = "status-pill waiting_queue";
    resultTitle.textContent = "Could not load saved request";
    resultMessage.textContent = err.message;
    resultDetails.innerHTML = `<div><strong>Saved request ID:</strong> ${escapeHtml(requestId)}</div>`;
    resultPanel.classList.add("show");
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitBtn.disabled = true;
  submitBtn.textContent = "Submitting...";

  const payload = {
    name: value("name"),
    phone: value("phone"),
    email: value("email"),
    date_of_birth: value("date_of_birth"),
    time_of_birth: value("time_of_birth"),
    place_of_birth: value("place_of_birth") || value("place_search"),
    topic: value("topic"),
    question: value("question")
  };

  try {
    const res = await fetch("/api/consultation/request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to submit consultation request.");
    }

    const request = data.request;
    localStorage.setItem(LATEST_REQUEST_KEY, request.id);
    renderRequestStatus(request, data.message, data.slot_available);
    loadQueueStatus();
    form.reset();
    sessionStorage.removeItem("consultation_form_state");
    updateTopicFields();
  } catch (err) {
    resultStatus.textContent = "error";
    resultStatus.className = "status-pill waiting_queue";
    resultTitle.textContent = "Could not submit request";
    resultMessage.textContent = err.message;
    resultDetails.innerHTML = "";
    resultPanel.classList.add("show");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Book Consultation";
  }
});

refreshStatusBtn.addEventListener("click", loadLatestRequestStatus);
clearStatusBtn.addEventListener("click", () => {
  localStorage.removeItem(LATEST_REQUEST_KEY);
  resultPanel.classList.remove("show");
});
topicEl.addEventListener("change", updateTopicFields);

loadConsultantProfile();
loadQueueStatus();
loadLatestRequestStatus();
updateTopicFields();
setInterval(loadQueueStatus, 15000);

// Form state preservation
const STATE_KEY = 'consultation_form_state';
function saveFormState() {
  const state = {
    name: value("name"),
    phone: value("phone"),
    email: value("email"),
    date_of_birth: value("date_of_birth"),
    time_of_birth: value("time_of_birth"),
    place_search: value("place_search"),
    place_of_birth: value("place_of_birth"),
    topic: value("topic"),
    question: value("question")
  };
  sessionStorage.setItem(STATE_KEY, JSON.stringify(state));
}

function loadFormState() {
  const saved = sessionStorage.getItem(STATE_KEY);
  if (saved) {
    try {
      const state = JSON.parse(saved);
      document.getElementById("name").value = state.name || "";
      document.getElementById("phone").value = state.phone || "";
      document.getElementById("email").value = state.email || "";
      document.getElementById("date_of_birth").value = state.date_of_birth || "";
      document.getElementById("time_of_birth").value = state.time_of_birth || "";
      document.getElementById("place_search").value = state.place_search || "";
      document.getElementById("place_of_birth").value = state.place_of_birth || "";
      if (state.topic) document.getElementById("topic").value = state.topic;
      document.getElementById("question").value = state.question || "";
      updateTopicFields();
    } catch (e) {}
  }
}

form.addEventListener("input", saveFormState);
loadFormState();
