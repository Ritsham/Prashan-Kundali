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
      document.getElementById("latitude").value = place.latitude;
      document.getElementById("longitude").value = place.longitude;
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
let consultantProfile = null;

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
    consultantProfile = c;
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

function authHeaders(extra = {}) {
  const token = localStorage.getItem("supabase_token");
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra;
}

function loadRazorpayCheckout() {
  return new Promise((resolve, reject) => {
    if (window.Razorpay) {
      resolve();
      return;
    }
    const existing = document.querySelector('script[src="https://checkout.razorpay.com/v1/checkout.js"]');
    if (existing) {
      existing.addEventListener("load", resolve, { once: true });
      existing.addEventListener("error", reject, { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = resolve;
    script.onerror = () => reject(new Error("Could not load Razorpay Checkout."));
    document.head.appendChild(script);
  });
}

function showProcessing(title, message) {
  resultStatus.textContent = "processing";
  resultStatus.className = "status-pill";
  resultTitle.textContent = title;
  resultMessage.textContent = message;
  resultDetails.innerHTML = "";
  resultPanel.classList.add("show");
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
  const status = request.status || request.case_status || "requested";
  const paymentStatus = request.payment_status || request.consultation?.payment_status || "not_paid";
  resultStatus.textContent = paymentStatus === "paid" ? "paid" : status;
  resultStatus.className = `status-pill ${paymentStatus === "paid" ? "paid" : status}`;
  resultTitle.textContent = slotAvailable ? "Your request is active" : "Added to waiting queue";
  if (paymentStatus === "paid") resultTitle.textContent = "Payment confirmed";
  if (request.status === "accepted") resultTitle.textContent = "Your request is accepted";
  if (request.status === "in_progress") resultTitle.textContent = "Consultation is in progress";
  if (request.status === "completed") resultTitle.textContent = "Consultation completed";
  if (request.status === "rejected") resultTitle.textContent = "Request rejected";
  if (request.status === "cancelled") resultTitle.textContent = "Request cancelled";
  if (request.status === "waiting_queue") resultTitle.textContent = "Added to waiting queue";

  resultMessage.textContent = message || statusMessageFor(paymentStatus === "paid" ? "paid" : status);
  const phone = consultantProfile?.contact_phone || consultantProfile?.whatsapp_number || "";
  const whatsapp = consultantProfile?.whatsapp_number || phone;
  const paidContactHtml = paymentStatus === "paid" ? `
    <div class="paid-contact-box">
      <strong>Next step:</strong> Your payment is verified. You can now contact ${escapeHtml(consultantProfile?.name || "the astrologer")} directly to fix your appointment time.
      ${phone ? `<div><strong>Mobile:</strong> <a href="tel:${escapeHtml(phone)}">${escapeHtml(phone)}</a></div>` : `<div><strong>Mobile:</strong> Contact number will be shared by support.</div>`}
      ${whatsapp ? `<div><strong>WhatsApp:</strong> <a href="https://wa.me/${escapeHtml(whatsapp).replace(/[^0-9]/g, "")}" target="_blank" rel="noopener">${escapeHtml(whatsapp)}</a></div>` : ""}
      <div>Call the astrologer, agree on a proper time, and then continue by phone or Google Meet as mutually decided. Your case is also sent to admin for fulfillment tracking.</div>
    </div>
  ` : "";
  resultDetails.innerHTML = `
    ${paidContactHtml}
    <div><strong>Request ID:</strong> ${escapeHtml(request.id || request.case_id)}</div>
    <div><strong>Request status:</strong> ${escapeHtml(status)}</div>
    <div><strong>Payment status:</strong> ${escapeHtml(paymentStatus)}</div>
    <div><strong>Queue number:</strong> ${request.queue_number ? escapeHtml(request.queue_number) : "Active slot"}</div>
    <div><strong>Submitted question:</strong> ${escapeHtml(request.question || request.consultation?.question)}</div>
    <div><strong>Consultant name:</strong> ${escapeHtml(consultantProfile?.name || "Rupesh Kumar")}</div>
    <div><strong>Scheduled date/time:</strong> ${request.scheduled_at ? escapeHtml(request.scheduled_at) : "Not scheduled yet"}</div>
    <div><strong>Meeting link:</strong> ${request.meeting_link ? `<a href="${escapeHtml(request.meeting_link)}" target="_blank">${escapeHtml(request.meeting_link)}</a>` : "Not added yet"}</div>
  `;
  resultPanel.classList.add("show");
}

function statusMessageFor(status) {
  if (status === "paid") {
    return "Your payment is confirmed. Please contact the astrologer directly to decide the appointment time. Admin can now track and fulfill this case.";
  }
  if (status === "pending_payment") {
    return "Your consultation case has been created. Payment is required before the astrologer can fulfill it.";
  }
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
    const res = await fetch(`/api/consultation/request/${encodeURIComponent(requestId)}`, {
      headers: authHeaders(),
    });
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
  submitBtn.textContent = "Creating case...";

    const payload = {
      name: value("name"),
      phone: value("phone"),
      email: value("email"),
      date_of_birth: value("date_of_birth"),
      time_of_birth: value("time_of_birth"),
      place_of_birth: value("place_of_birth") || value("place_search"),
      latitude: document.getElementById("latitude").value ? parseFloat(document.getElementById("latitude").value) : null,
      longitude: document.getElementById("longitude").value ? parseFloat(document.getElementById("longitude").value) : null,
      topic: value("topic"),
      question: value("question"),
      payment_status: "pending",
      quoted_price: consultantProfile?.consultation_fee || null,
      currency: "INR"
    };

    const progressionStr = sessionStorage.getItem("kundali_chart_progression");
    if (progressionStr) {
      try {
        const progression = JSON.parse(progressionStr);
        if (progression.chart) {
          payload.chart_snapshot = progression.chart;
        }
      } catch (e) {
        console.error("Failed to parse chart progression", e);
      }
    }

  try {
    showProcessing("Creating consultation case", "We are saving your details before opening secure payment.");
    const res = await fetch("/api/consultation/request", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to submit consultation request.");
    }

    const request = data.request;
    localStorage.setItem(LATEST_REQUEST_KEY, request.id);
    renderRequestStatus(request, data.message, data.slot_available);

    submitBtn.textContent = "Opening payment...";
    showProcessing("Opening secure payment", "Complete the Razorpay payment to confirm your consultation.");
    await loadRazorpayCheckout();

    const orderRes = await fetch("/api/payments/razorpay/order", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        consultation_case_id: request.id,
        requester_email: payload.email,
        purpose: "consultation"
      }),
    });
    const orderData = await orderRes.json();
    if (!orderRes.ok) {
      throw new Error(orderData.detail || "Could not create payment order.");
    }

    const checkoutResult = await new Promise((resolve, reject) => {
      const razorpay = new window.Razorpay({
        key: orderData.key_id,
        amount: orderData.order.amount,
        currency: orderData.order.currency,
        name: "Shree Lakshmi Astro",
        description: "Astrology consultation",
        order_id: orderData.order.id,
        prefill: {
          name: payload.name,
          email: payload.email,
          contact: payload.phone
        },
        notes: {
          consultation_case_id: request.id
        },
        theme: {
          color: "#8c3d25"
        },
        modal: {
          ondismiss: () => reject(new Error("Payment was closed before completion. Your case is saved as pending payment."))
        },
        handler: resolve
      });
      razorpay.on("payment.failed", (response) => {
        reject(new Error(response?.error?.description || "Payment failed. Please try again."));
      });
      razorpay.open();
    });

    submitBtn.textContent = "Verifying payment...";
    showProcessing("Verifying payment", "Please wait while we confirm your payment securely.");
    const verifyRes = await fetch("/api/payments/razorpay/verify", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        razorpay_order_id: checkoutResult.razorpay_order_id,
        razorpay_payment_id: checkoutResult.razorpay_payment_id,
        razorpay_signature: checkoutResult.razorpay_signature
      }),
    });
    const verifyData = await verifyRes.json();
    if (!verifyRes.ok) {
      throw new Error(verifyData.detail || "Payment verification failed.");
    }

    renderRequestStatus(
      verifyData.case || { ...request, payment_status: "paid", status: "confirmed" },
      "Payment verified. You can now contact the astrologer directly for appointment timing.",
      data.slot_available
    );
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
      latitude: value("latitude"),
      longitude: value("longitude"),
      topic: value("topic"),
      question: value("question")
    };
  sessionStorage.setItem(STATE_KEY, JSON.stringify(state));
}

function loadFormState() {
  const saved = sessionStorage.getItem(STATE_KEY);
  const progressionStr = sessionStorage.getItem("kundali_chart_progression");

  if (progressionStr && !saved) {
    try {
      const progression = JSON.parse(progressionStr);
      const chart = progression.chart;
      if (chart) {
        const topicVal = chart.meta?.chart_type === "prashna" ? "Prashna" : "Other";
        document.getElementById("topic").value = topicVal;
        
        if (chart.question) {
          document.getElementById("question").value = chart.question.question_text || "";
          document.getElementById("place_search").value = chart.question.place_name || "";
          document.getElementById("place_of_birth").value = chart.question.place_name || "";
          document.getElementById("latitude").value = chart.question.latitude || "";
          document.getElementById("longitude").value = chart.question.longitude || "";
          
          if (chart.question.asked_at_local) {
            const dt = chart.question.asked_at_local.split("T");
            if (dt.length >= 2) {
              document.getElementById("date_of_birth").value = dt[0];
              document.getElementById("time_of_birth").value = dt[1].substring(0, 5);
            }
          }
        }
        updateTopicFields();
      }
    } catch (e) {
      console.error("Failed to prefill form from chart progression", e);
    }
  }

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
        document.getElementById("latitude").value = state.latitude || "";
        document.getElementById("longitude").value = state.longitude || "";
        if (state.topic) document.getElementById("topic").value = state.topic;
        document.getElementById("question").value = state.question || "";
        updateTopicFields();
    } catch (e) {}
  }
}

form.addEventListener("input", saveFormState);
loadFormState();
