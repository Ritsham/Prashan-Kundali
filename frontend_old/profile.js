import { requireAuth, initLogout } from "./auth-shared.js";

async function initProfile() {
  const auth = await requireAuth();
  if (!auth) return;

  const { supabase, session } = auth;
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

  const { data: consultations } = await supabase
    .from("consultation_requests")
    .select("*")
    .eq("user_id", session.user.id)
    .order("created_at", { ascending: false });
  renderConsultationSummary(consultations || []);
  renderConsultations(consultations || []);
}

function bindProfileMenu(user) {
  const menu = document.getElementById("profile-menu");
  const button = document.getElementById("btn-profile");
  const panel = document.getElementById("profile-menu-panel");
  const profileButton = document.getElementById("btn-profile-page");
  const loginButton = document.getElementById("btn-login-header");

  loginButton?.classList.add("hidden");
  menu?.classList.remove("hidden");
  if (button) {
    button.textContent = userInitial(user);
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const shouldOpen = panel?.classList.contains("hidden");
      panel?.classList.toggle("hidden", !shouldOpen);
      button.setAttribute("aria-expanded", String(Boolean(shouldOpen)));
    });
  }
  profileButton?.addEventListener("click", () => {
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
  return (user?.user_metadata?.full_name || user?.user_metadata?.name || user?.email || "U")
    .trim()
    .charAt(0)
    .toUpperCase() || "U";
}

function renderSavedCharts(session) {
  const container = document.getElementById("saved-charts-container");
  if (!container) return;

  const items = window.SavedCharts?.list(session) || [];
  if (!items.length) {
    container.innerHTML = '<div class="empty-state">No saved charts yet. Tick "Save chart to my profile" when generating Lagna, Prashna, or Match reports.</div>';
    return;
  }

  container.innerHTML = `<div class="saved-chart-list">${items.map(savedChartItem).join("")}</div>`;
  container.querySelectorAll("[data-open-saved-chart]").forEach((button) => {
    button.addEventListener("click", () => {
      const item = items.find((entry) => entry.id === button.dataset.openSavedChart);
      window.SavedCharts?.open(item);
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

function savedChartItem(item) {
  const date = item.createdAt ? new Date(item.createdAt).toLocaleDateString() : "";
  const type = chartTypeLabel(item.type);
  const subtitle = [item.subtitle, date].filter(Boolean).join(" • ");
  return `
    <button type="button" class="saved-chart-item" data-open-saved-chart="${escapeHtml(item.id)}">
      <span>
        <span class="saved-chart-type">${escapeHtml(type)}</span>
        <strong class="saved-chart-title">${escapeHtml(item.title)}</strong>
        <span class="saved-chart-meta">${escapeHtml(subtitle || "Saved chart")}</span>
      </span>
      <span type="button" role="button" tabindex="0" class="saved-chart-delete" data-delete-saved-chart="${escapeHtml(item.id)}">Remove</span>
    </button>
  `;
}

function chartTypeLabel(type) {
  if (type === "lagna") return "Lagna";
  if (type === "prashna") return "Prashna";
  if (type === "matchmaking") return "Match";
  return "Chart";
}

function renderCommunityApplications(items) {
  const container = document.getElementById("community-app-container");
  container.innerHTML = items.length
    ? items.map((item) => {
      const date = new Date(item.created_at).toLocaleDateString();
      const status = String(item.status || "PENDING").toUpperCase();
      return `
        <div class="list-item">
          <div class="item-details">
            <h4>Application ID: ${escapeHtml(String(item.id || "").substring(0, 8).toUpperCase())}</h4>
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
  container.innerHTML = items.length
    ? items.map((item) => {
      const date = new Date(item.created_at).toLocaleDateString();
      const status = consultationStatusLabel(item.status);
      return `
        <div class="list-item">
          <div class="item-details">
            <h4>${escapeHtml(item.topic ? item.topic.toUpperCase() : "CONSULTATION")}</h4>
            <p>Date: ${escapeHtml(date)} &bull; For: ${escapeHtml(item.name || "User")}</p>
          </div>
          <div><span class="status-badge ${statusBadgeClass(status)}">${escapeHtml(status)}</span></div>
        </div>
      `;
    }).join("")
    : '<div class="empty-state">No consultation records found.</div>';
}

function consultationStatusLabel(status) {
  if (isCompletedStatus(status)) return "COMPLETED";
  if (isCancelledStatus(status)) return "CANCELLED";
  if (isBookedStatus(status)) return "BOOKED";
  return "PENDING";
}

function statusBadgeClass(status) {
  const normalized = String(status || "").toLowerCase();
  if (["approved", "completed", "answered", "booked", "confirmed"].includes(normalized)) return "status-approved";
  if (["rejected", "declined", "cancelled", "canceled"].includes(normalized)) return "status-rejected";
  return "status-pending";
}

function isPendingStatus(status) {
  const normalized = String(status || "").toLowerCase();
  return !normalized || ["pending", "requested", "submitted", "waiting"].includes(normalized);
}

function isBookedStatus(status) {
  return ["booked", "confirmed", "scheduled", "accepted", "assigned"].includes(String(status || "").toLowerCase());
}

function isCompletedStatus(status) {
  return ["completed", "answered", "done"].includes(String(status || "").toLowerCase());
}

function isCancelledStatus(status) {
  return ["declined", "cancelled", "canceled", "rejected"].includes(String(status || "").toLowerCase());
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

document.addEventListener("DOMContentLoaded", initProfile);
