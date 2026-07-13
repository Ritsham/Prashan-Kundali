import { AppState } from './state.js';
import { API } from './api.js';
import { initAuth } from './auth.js?v=oauth-prod-2';
import { showFlash } from './flash.js';

const BOOKING_CONTEXT_KEY = "matchmaking_booking_context";
const DRAFT_KEY = "matchmaking_consultation_draft";
const root = document.querySelector("#booking-root");

initAuth();

document.addEventListener("astro:authChanged", (event) => {
  const signedIn = Boolean(event.detail);
  document.querySelector("#btn-login-header")?.classList.toggle("hidden", signedIn);
  document.querySelector("#btn-logout")?.classList.toggle("hidden", !signedIn);
});

document.addEventListener("DOMContentLoaded", loadBookingPage);

async function loadBookingPage() {
  const context = readContext();
  if (!context?.matchId || !context?.report) {
    root.innerHTML = `
      <div class="empty-booking-state">
        <h2>No match report found</h2>
        <p>Please generate a Kundali Match Making report first, then click Book Consultant.</p>
        <a class="btn-secondary" href="/matchmaking.html">Back to Match Making</a>
      </div>
    `;
    return;
  }

  try {
    const [profile, queue] = await Promise.all([
      API.get("/api/consultation/profile", false),
      API.get("/api/consultation/request-status", false),
    ]);
    renderBooking(context, profile.consultant, queue);
  } catch (error) {
    root.innerHTML = `<div class="match-place-empty">${escapeHtml(error.message)}</div>`;
  }
}

function renderBooking(context, consultant, queue) {
  const report = context.report;
  const boy = report.participants.boy;
  const girl = report.participants.girl;
  const draft = readDraft();
  const canBook = Boolean(queue.can_request_active_slot);
  const defaultEmail = draft?.contactEmail || AppState.session?.user?.email || localStorage.getItem("matchmaking_notify_email") || "";
  const selectedQuestion = draft?.question || context.question || "";

  root.innerHTML = `
    <div class="booking-page-grid">
      <article class="consultant-profile-mini booking-profile">
        <img src="${escapeHtml(consultant?.photo_url || "")}" alt="${escapeHtml(consultant?.name || "Rupesh Kumar")}" />
        <div>
          <p class="eyebrow">Selected Consultant</p>
          <h4>${escapeHtml(consultant?.name || "Rupesh Kumar")}</h4>
          <p>${escapeHtml(consultant?.title || "Founder Astrologer / Primary Consultant")}</p>
          <p><strong>Active queue:</strong> ${escapeHtml(queue.active_count || 0)}/${escapeHtml(queue.max_active || 20)}</p>
          <p><strong>Waiting:</strong> ${escapeHtml(queue.waiting_count || 0)}</p>
        </div>
      </article>

      <article class="match-booking-summary booking-summary">
        <h4>Match details shared with admin and consultant</h4>
        <p><strong>Boy:</strong> ${escapeHtml(boy.name)} · ${escapeHtml(boy.date_of_birth)} ${escapeHtml(boy.time_of_birth)} · ${escapeHtml(boy.birth_place)}</p>
        <p><strong>Girl:</strong> ${escapeHtml(girl.name)} · ${escapeHtml(girl.date_of_birth)} ${escapeHtml(girl.time_of_birth)} · ${escapeHtml(girl.birth_place)}</p>
        <p><strong>Guna Milan:</strong> ${escapeHtml(report.ashtakoota.total_score)}/${escapeHtml(report.ashtakoota.max_score)} · ${escapeHtml(report.summary.overall_result)}</p>
      </article>
    </div>

    <div class="booking-form-block">
      <label>Your question for Rupesh Kumar
        <textarea id="booking-question">${escapeHtml(selectedQuestion)}</textarea>
      </label>
      <div class="booking-contact-grid">
        <label>Email for confirmation / slot notification
          <input id="booking-email" type="email" value="${escapeHtml(defaultEmail)}" placeholder="you@example.com" />
        </label>
        <label>WhatsApp / phone
          <input id="booking-phone" value="${escapeHtml(draft?.phone || "")}" placeholder="+91..." />
        </label>
      </div>
    </div>

    ${canBook ? `
      <div class="queue-ok-box">Slot available. You can book now because active requests are below ${escapeHtml(queue.max_active || 20)}.</div>
      <div class="consult-actions">
        <button type="button" class="btn-submit" id="btn-book-now">Book Now</button>
        <button type="button" class="btn-secondary" id="btn-save-draft">Save Draft</button>
        ${draft ? `<button type="button" class="btn-secondary" id="btn-remove-draft">Remove Existing Draft</button>` : ""}
      </div>
    ` : `
      <div class="queue-full-box">Rupesh Kumar's queue is full. Save this draft with your email and we will keep it ready for slot notification.</div>
      <div class="consult-actions">
        <button type="button" class="btn-submit" id="btn-save-draft">Save Draft for Slot Notification</button>
        ${draft ? `<button type="button" class="btn-secondary" id="btn-remove-draft">Remove Existing Draft</button>` : ""}
      </div>
    `}
    <p id="booking-status"></p>
  `;

  root.querySelector("#btn-book-now")?.addEventListener("click", () => bookNow(context));
  root.querySelector("#btn-save-draft")?.addEventListener("click", () => saveDraft(context));
  root.querySelector("#btn-remove-draft")?.addEventListener("click", removeDraft);
}

async function bookNow(context) {
  if (!AppState.session && !localStorage.getItem("supabase_token")) {
    document.querySelector("#auth-modal")?.classList.remove("hidden");
    return;
  }

  const status = root.querySelector("#booking-status");
  const button = root.querySelector("#btn-book-now");
  const payload = bookingPayload(context);
  if (!payload.contact_email) {
    status.textContent = "Please enter an email for booking confirmation.";
    return;
  }
  if (payload.question.length < 3) {
    status.textContent = "Please enter your question for the consultant.";
    return;
  }

  button.disabled = true;
  status.textContent = "Sending booking request to admin...";
  try {
    const data = await API.post(`/api/matchmaking/requests/${encodeURIComponent(context.matchId)}/consultation`, payload);
    localStorage.removeItem(DRAFT_KEY);
    status.textContent = data.message || "Booking request sent to admin.";
    showFlash("Booking request sent to admin.", "success");
  } catch (error) {
    status.textContent = error.message;
    button.disabled = false;
  }
}

function bookingPayload(context) {
  return {
    question: root.querySelector("#booking-question")?.value.trim() || "",
    contact_email: root.querySelector("#booking-email")?.value.trim() || "",
    phone: root.querySelector("#booking-phone")?.value.trim() || "",
    preferred_slot: "",
    report_snapshot: context.report,
  };
}

function saveDraft(context) {
  const payload = bookingPayload(context);
  if (!payload.contact_email) {
    root.querySelector("#booking-status").textContent = "Enter an email before saving draft for slot notification.";
    return;
  }
  const report = context.report;
  localStorage.setItem(DRAFT_KEY, JSON.stringify({
    matchId: context.matchId,
    question: payload.question,
    contactEmail: payload.contact_email,
    phone: payload.phone,
    preferredSlot: payload.preferred_slot,
    boyName: report.participants.boy.name,
    girlName: report.participants.girl.name,
    savedAt: new Date().toISOString(),
  }));
  localStorage.setItem("matchmaking_notify_email", payload.contact_email);
  root.querySelector("#booking-status").textContent = "Draft saved. Your match booking details are preserved on this browser.";
  showFlash("Draft saved.", "success");
}

function removeDraft() {
  localStorage.removeItem(DRAFT_KEY);
  root.querySelector("#booking-status").textContent = "Existing draft removed.";
  showFlash("Draft removed.", "success");
}

function readContext() {
  try {
    const raw = sessionStorage.getItem(BOOKING_CONTEXT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function readDraft() {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
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
