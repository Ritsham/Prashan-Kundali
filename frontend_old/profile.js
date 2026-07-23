import { requireAuth, initLogout } from "./auth-shared.js";

let profileSession = null;
let profileSupabase = null;
let consultations = [];
let activeReviewRating = 5;

async function initProfile() {
  const auth = await requireAuth();
  if (!auth) return;
  const { supabase, session } = auth;
  profileSession = session;
  profileSupabase = supabase;

  document.dispatchEvent(new CustomEvent("astro:authChanged", { detail: session }));
  initLogout("btn-logout");
  bindProfileMenu(session.user);
  document.getElementById("user-email").innerText = session.user.email;
  renderSavedCharts(session);

  const { data: applications } = await supabase
    .from("community_applications")
    .select("*")
    .eq("user_id", session.user.id)
    .order("created_at", { ascending: false });
  renderCommunityApplications(applications || []);

  await loadConsultations();
}

async function loadConsultations() {
  const { data } = await profileSupabase
    .from("consultation_requests")
    .select("*")
    .eq("user_id", profileSession.user.id)
    .order("created_at", { ascending: false });
  consultations = (data || []).map(withParsedReview);
  renderConsultationSummary(consultations);
  renderConsultations(consultations);
}

function bindProfileMenu(user) {
  const menu = document.getElementById("profile-menu");
  const button = document.getElementById("btn-profile");
  const panel = document.getElementById("profile-menu-panel");
  const profilePage = document.getElementById("btn-profile-page");
  const login = document.getElementById("btn-login-header");
  login?.classList.add("hidden");
  menu?.classList.remove("hidden");
  if (button) {
    button.textContent = userInitial(user);
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const isHidden = panel?.classList.contains("hidden");
      panel?.classList.toggle("hidden", !isHidden);
      button.setAttribute("aria-expanded", String(Boolean(isHidden)));
    });
  }
  profilePage?.addEventListener("click", () => {
    window.location.href = "/profile.html";
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest("#profile-menu")) closeProfileMenu();
  });
}

function closeProfileMenu() {
  document.getElementById("profile-menu-panel")?.classList.add("hidden");
  document.getElementById("btn-profile")?.setAttribute("aria-expanded", "false");
}

function userInitial(user) {
  return (user?.user_metadata?.full_name || user?.user_metadata?.name || user?.email || "U").trim().charAt(0).toUpperCase() || "U";
}

function renderSavedCharts(session) {
  const container = document.getElementById("saved-charts-container");
  if (!container) return;
  const charts = window.SavedCharts?.list(session) || [];
  if (!charts.length) {
    container.innerHTML = '<div class="empty-state">No saved charts yet. Tick "Save chart to my profile" when generating Lagna, Prashna, or Match reports.</div>';
    return;
  }
  container.innerHTML = `<div class="saved-chart-list">${charts.map(savedChartItem).join("")}</div>`;
  container.querySelectorAll("[data-open-saved-chart]").forEach((button) => {
    button.addEventListener("click", () => {
      const chart = charts.find((item) => item.id === button.dataset.openSavedChart);
      window.SavedCharts?.open(chart);
    });
  });
  container.querySelectorAll("[data-delete-saved-chart]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      window.SavedCharts?.remove(button.dataset.deleteSavedChart, session);
      renderSavedCharts(session);
    });
  });
}

function savedChartItem(chart) {
  const created = chart.createdAt ? new Date(chart.createdAt).toLocaleDateString() : "";
  const label = chartTypeLabel(chart.type);
  const meta = [chart.subtitle, created].filter(Boolean).join(" • ");
  return `
    <button type="button" class="saved-chart-item" data-open-saved-chart="${escapeHtml(chart.id)}">
      <span>
        <span class="saved-chart-type">${escapeHtml(label)}</span>
        <strong class="saved-chart-title">${escapeHtml(chart.title)}</strong>
        <span class="saved-chart-meta">${escapeHtml(meta || "Saved chart")}</span>
      </span>
      <span type="button" role="button" tabindex="0" class="saved-chart-delete" data-delete-saved-chart="${escapeHtml(chart.id)}">Remove</span>
    </button>
  `;
}

function chartTypeLabel(type) {
  return type === "lagna" ? "Lagna" : type === "prashna" ? "Prashna" : type === "matchmaking" ? "Match" : "Chart";
}

function renderCommunityApplications(applications) {
  document.getElementById("community-app-container").innerHTML = applications.length
    ? applications.map((application) => {
        const date = new Date(application.created_at).toLocaleDateString();
        const status = String(application.status || "PENDING").toUpperCase();
        return `
        <div class="list-item">
          <div class="item-details">
            <h4>Application ID: ${escapeHtml(String(application.id || "").substring(0, 8).toUpperCase())}</h4>
            <p>Submitted Date: ${escapeHtml(date)}</p>
          </div>
          <div><span class="status-badge ${statusBadgeClass(status)}">${escapeHtml(status)}</span></div>
        </div>
      `;
      }).join("")
    : '<div class="empty-state">No community applications found.</div>';
}

function renderConsultationSummary(items) {
  const total = items.length;
  const pending = items.filter((item) => isPendingStatus(item.status)).length;
  const booked = items.filter((item) => isBookedStatus(item.status)).length;
  const completed = items.filter((item) => isCompletedStatus(item.status)).length;
  const container = document.getElementById("consultation-summary-container");
  if (!container) return;
  container.innerHTML = `
    <div class="profile-stat"><strong>${total}</strong><span>Requested</span></div>
    <div class="profile-stat"><strong>${pending}</strong><span>Pending</span></div>
    <div class="profile-stat"><strong>${booked}</strong><span>Booked</span></div>
    <div class="profile-stat"><strong>${completed}</strong><span>Completed</span></div>
  `;
}

function renderConsultations(items) {
  const container = document.getElementById("consultations-container");
  if (!container) return;
  if (!items.length) {
    container.innerHTML = '<div class="empty-state">No consultation records found.</div>';
    return;
  }
  container.innerHTML = items.map((item) => {
    const date = formatDate(item.created_at);
    const status = consultationStatusLabel(item.status);
    const review = item.user_review_rating ? ` • ${"★".repeat(Number(item.user_review_rating))}` : "";
    return `
      <button type="button" class="list-item" data-open-consultation="${escapeHtml(item.id)}">
        <div class="item-details">
          <h4>${escapeHtml(item.topic ? item.topic.toUpperCase() : "CONSULTATION")}</h4>
          <p>Date: ${escapeHtml(date)} &bull; For: ${escapeHtml(item.name || "User")}${escapeHtml(review)}</p>
        </div>
        <div><span class="status-badge ${statusBadgeClass(status)}">${escapeHtml(status)}</span></div>
      </button>
    `;
  }).join("");
  container.querySelectorAll("[data-open-consultation]").forEach((button) => {
    button.addEventListener("click", () => openConsultationDetail(button.dataset.openConsultation));
  });
}

async function openConsultationDetail(id) {
  const local = consultations.find((item) => item.id === id);
  openConsultationModal(local, true);
  try {
    const response = await fetch(`/api/consultation/request/${encodeURIComponent(id)}`, {
      headers: authHeaders(),
      cache: "no-store",
    });
    const body = await response.json().catch(() => ({}));
    if (response.ok && body.request) {
      const fresh = withParsedReview(body.request);
      consultations = consultations.map((item) => (item.id === fresh.id ? fresh : item));
      openConsultationModal(fresh, false);
    } else {
      openConsultationModal(local, false, body.detail || "Could not load fresh details.");
    }
  } catch (error) {
    openConsultationModal(local, false, error.message || "Could not load fresh details.");
  }
}

function openConsultationModal(item, loading = false, warning = "") {
  if (!item) return;
  const modal = document.getElementById("consultation-modal");
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
  modal.innerHTML = `
    <div class="consultation-modal-panel" role="dialog" aria-modal="true" aria-labelledby="consultation-modal-title">
      <div class="consultation-modal-head">
        <div>
          <p class="saved-chart-type">${escapeHtml(consultationStatusLabel(item.status))}</p>
          <h3 id="consultation-modal-title">${escapeHtml(item.topic || "Consultation")}</h3>
          <p class="saved-chart-meta">Request ID: ${escapeHtml(item.id)}</p>
        </div>
        <button type="button" id="close-consultation-modal" aria-label="Close details">Close</button>
      </div>
      ${loading ? '<p class="review-status">Loading latest details...</p>' : ""}
      ${warning ? `<p class="review-status">${escapeHtml(warning)}</p>` : ""}
      <div class="consultation-detail-grid">
        ${detailBox("Booked on", formatDateTime(item.created_at))}
        ${detailBox("Last updated", formatDateTime(item.updated_at))}
        ${detailBox("Status", consultationStatusLabel(item.status))}
        ${detailBox("Payment", item.payment_status || item.consultation?.payment_status || "not_paid")}
        ${detailBox("Name", item.name || item.user?.full_name || "User")}
        ${detailBox("Phone", item.phone || item.user?.mobile_number || "")}
        ${detailBox("Email", item.email || item.user?.email || "")}
        ${detailBox("Birth date", item.date_of_birth || item.user?.date_of_birth || "")}
        ${detailBox("Birth time", item.time_of_birth || item.user?.time_of_birth || "")}
        ${detailBox("Birth place", item.place_of_birth || item.user?.place || "")}
        ${detailBox("Scheduled", item.scheduled_at || "Not scheduled yet")}
        ${detailBox("Meeting link", item.meeting_link ? `<a href="${escapeAttr(item.meeting_link)}" target="_blank" rel="noopener">Open meeting</a>` : "Not added yet", true)}
        ${detailBox("Completed on", isCompletedStatus(item.status) ? formatDateTime(item.updated_at) : "Not completed yet")}
        ${detailBox("Queue", item.queue_number ? `Waiting #${item.queue_number}` : "Active slot")}
      </div>
      <span class="saved-chart-type">Question</span>
      <div class="consultation-question">${escapeHtml(item.question || item.consultation?.question || "")}</div>
      ${reviewSection(item)}
    </div>
  `;
  modal.querySelector("#close-consultation-modal")?.addEventListener("click", closeConsultationModal);
  modal.addEventListener("mousedown", closeOnBackdrop, { once: true });
  bindReviewControls(item.id);
}

function closeOnBackdrop(event) {
  if (event.target.id === "consultation-modal") closeConsultationModal();
  else document.getElementById("consultation-modal")?.addEventListener("mousedown", closeOnBackdrop, { once: true });
}

function closeConsultationModal() {
  const modal = document.getElementById("consultation-modal");
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
  modal.innerHTML = "";
}

function detailBox(label, value, trustedHtml = false) {
  return `<div class="consultation-detail-box"><span>${escapeHtml(label)}</span><strong>${trustedHtml ? value : escapeHtml(value || "-")}</strong></div>`;
}

function reviewSection(item) {
  if (!isCompletedStatus(item.status)) {
    return '<div class="review-box"><strong>Review</strong><p class="review-status">Review opens after the consultant marks this case completed.</p></div>';
  }
  const rating = Number(item.user_review_rating || 0);
  const text = item.user_review_text || "";
  activeReviewRating = rating || 5;
  return `
    <div class="review-box">
      <strong>Start rating and review</strong>
      ${rating ? `<p class="review-status">Your current rating: ${"★".repeat(rating)}${"☆".repeat(5 - rating)}</p>` : ""}
      <div class="star-rating" id="star-rating" aria-label="Rating">
        ${[1, 2, 3, 4, 5].map((star) => `<button type="button" data-rating="${star}" class="${star <= activeReviewRating ? "active" : ""}" aria-label="${star} star">${star <= activeReviewRating ? "★" : "☆"}</button>`).join("")}
      </div>
      <textarea id="review-text" maxlength="1200" placeholder="Write what went well, what could improve, and whether the consultation helped.">${escapeHtml(text)}</textarea>
      <div class="review-actions">
        <button type="button" id="submit-review">Submit Review</button>
        <span id="review-status" class="review-status"></span>
      </div>
    </div>
  `;
}

function bindReviewControls(id) {
  const ratingWrap = document.getElementById("star-rating");
  const submit = document.getElementById("submit-review");
  if (!ratingWrap || !submit) return;
  ratingWrap.querySelectorAll("[data-rating]").forEach((button) => {
    button.addEventListener("click", () => {
      activeReviewRating = Number(button.dataset.rating);
      ratingWrap.querySelectorAll("[data-rating]").forEach((star) => {
        const value = Number(star.dataset.rating);
        star.classList.toggle("active", value <= activeReviewRating);
        star.textContent = value <= activeReviewRating ? "★" : "☆";
      });
    });
  });
  submit.addEventListener("click", async () => {
    const status = document.getElementById("review-status");
    const text = document.getElementById("review-text").value.trim();
    if (text.length < 5) {
      status.textContent = "Please write a short review.";
      return;
    }
    status.textContent = "Saving review...";
    submit.disabled = true;
    try {
      const response = await fetch(`/api/consultation/request/${encodeURIComponent(id)}/review`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ rating: activeReviewRating, review_text: text }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Could not save review.");
      const updated = withParsedReview(body.request);
      consultations = consultations.map((item) => (item.id === updated.id ? updated : item));
      renderConsultations(consultations);
      openConsultationModal(updated, false);
    } catch (error) {
      status.textContent = error.message || "Could not save review.";
    } finally {
      submit.disabled = false;
    }
  });
}

function withParsedReview(item) {
  const review = extractReview(item.admin_notes);
  return {
    ...item,
    user_review_rating: item.user_review_rating || review?.rating || null,
    user_review_text: item.user_review_text || review?.text || "",
    user_reviewed_at: item.user_reviewed_at || review?.reviewed_at || "",
  };
}

function extractReview(notes) {
  const match = String(notes || "").match(/\[\[USER_REVIEW:(\{.*\})\]\]/s);
  if (!match) return null;
  try {
    return JSON.parse(match[1]);
  } catch {
    return null;
  }
}

function authHeaders(extra = {}) {
  const token = profileSession?.access_token || localStorage.getItem("supabase_token");
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra;
}

function consultationStatusLabel(status) {
  return isCompletedStatus(status) ? "COMPLETED" : isCancelledStatus(status) ? "CANCELLED" : isBookedStatus(status) ? "BOOKED" : "PENDING";
}

function statusBadgeClass(status) {
  const value = String(status || "").toLowerCase();
  return ["approved", "completed", "answered", "booked", "confirmed"].includes(value)
    ? "status-approved"
    : ["rejected", "declined", "cancelled", "canceled"].includes(value)
      ? "status-rejected"
      : "status-pending";
}

function isPendingStatus(status) {
  const value = String(status || "").toLowerCase();
  return !value || ["pending", "requested", "submitted", "waiting", "pending_payment", "waiting_queue"].includes(value);
}

function isBookedStatus(status) {
  return ["booked", "confirmed", "scheduled", "accepted", "assigned", "active", "in_progress"].includes(String(status || "").toLowerCase());
}

function isCompletedStatus(status) {
  return ["completed", "answered", "done"].includes(String(status || "").toLowerCase());
}

function isCancelledStatus(status) {
  return ["declined", "cancelled", "canceled", "rejected", "refunded"].includes(String(status || "").toLowerCase());
}

function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleDateString();
}

function formatDateTime(value) {
  if (!value) return "";
  return new Date(value).toLocaleString();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

document.addEventListener("DOMContentLoaded", initProfile);
