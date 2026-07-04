const form = document.getElementById("consultation-form");
const submitBtn = document.getElementById("submit-btn");
const resultPanel = document.getElementById("result-panel");
const resultStatus = document.getElementById("result-status");
const resultTitle = document.getElementById("result-title");
const resultMessage = document.getElementById("result-message");
const resultDetails = document.getElementById("result-details");
const refreshStatusBtn = document.getElementById("refresh-status-btn");
const clearStatusBtn = document.getElementById("clear-status-btn");
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
    place_of_birth: value("place_of_birth"),
    topic: value("topic"),
    question: value("question"),
    preferred_time: value("preferred_time"),
    payment_status: value("payment_status"),
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
    form.reset();
  } catch (err) {
    resultStatus.textContent = "error";
    resultStatus.className = "status-pill waiting_queue";
    resultTitle.textContent = "Could not submit request";
    resultMessage.textContent = err.message;
    resultDetails.innerHTML = "";
    resultPanel.classList.add("show");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Request Consultation";
  }
});

refreshStatusBtn.addEventListener("click", loadLatestRequestStatus);
clearStatusBtn.addEventListener("click", () => {
  localStorage.removeItem(LATEST_REQUEST_KEY);
  resultPanel.classList.remove("show");
});

loadConsultantProfile();
loadLatestRequestStatus();
