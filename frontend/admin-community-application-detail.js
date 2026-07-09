import { initAuth } from './auth.js';
import { API } from './api.js';

let session = null;
let appId = null;
let appData = null;

document.addEventListener("DOMContentLoaded", async () => {
    // Extract app ID from URL
    const parts = window.location.pathname.split('/');
    appId = parts[parts.length - 1];
    
    await initAuth();
    
    document.addEventListener('astro:authChanged', async (e) => {
        session = e.detail;
        if (!session) {
            window.location.href = `/?redirect=${encodeURIComponent(window.location.pathname)}`;
            return;
        }
        await loadApplication();
    });
    
    setupActionForm();
});

async function loadApplication() {
    try {
        appData = await API.get(`/api/admin/applications/${appId}`);
        renderApplication();
    } catch (err) {
        console.error("Failed to load application detail", err);
        alert("Failed to load application details.");
    }
}

function renderApplication() {
    document.getElementById("app-id").textContent = appData.id;
    
    const badge = document.getElementById("app-status-badge");
    badge.textContent = appData.status.replace(/_/g, ' ');
    badge.className = `badge ${appData.status}`;
    
    document.getElementById("info-name").textContent = appData.full_name;
    document.getElementById("info-email").textContent = appData.email;
    document.getElementById("info-email-link").href = `mailto:${appData.email}`;
    document.getElementById("info-mobile").textContent = appData.mobile_number;
    document.getElementById("info-location").textContent = `${appData.state}, ${appData.country}`;
    
    document.getElementById("info-type").textContent = appData.applicant_type;
    document.getElementById("info-exp").textContent = appData.experience_range;
    document.getElementById("info-systems").textContent = appData.systems.join(", ") || "None";
    document.getElementById("info-desc").textContent = appData.background_description;
    document.getElementById("info-additional").textContent = appData.additional_information || "No additional information provided initially.";
    
    // Render Proofs
    const proofsContainer = document.getElementById("proofs-container");
    if (!appData.proofs || appData.proofs.length === 0) {
        proofsContainer.innerHTML = "<p>No proofs submitted.</p>";
    } else {
        proofsContainer.innerHTML = appData.proofs.map(p => `
            <div class="proof-item">
                <div style="font-weight: bold; margin-bottom: 0.5rem;">${p.proof_type}</div>
                <div style="font-size: 0.85rem; color: #666; margin-bottom: 0.5rem;">Submitted: ${new Date(p.created_at).toLocaleDateString()}</div>
                ${p.external_url ? `<div><a href="${p.external_url}" target="_blank" style="color: var(--ink-light);">${p.external_url}</a></div>` : ''}
                ${p.file_url ? `
                    <div style="margin-top: 0.5rem;">
                        <button class="btn btn-secondary btn-download" style="width: auto; padding: 0.4rem 0.8rem; font-size: 0.85rem;" data-file="${p.file_url}">
                            Download File (${(p.file_size / 1024).toFixed(1)} KB)
                        </button>
                    </div>
                ` : ''}
            </div>
        `).join('');
        
        // Attach download events. In a real app, generate a signed URL via an API endpoint.
        // For simplicity assuming public bucket or we fetch a signed URL from API.
        // We'll just alert for this demo implementation as Supabase Storage signed URLs require a server call.
        document.querySelectorAll(".btn-download").forEach(btn => {
            btn.addEventListener("click", (e) => {
                alert(`File path: ${e.target.dataset.file}\nIn a complete implementation, this would trigger a signed URL download.`);
            });
        });
    }
    
    // Render Timeline
    const timelineContainer = document.getElementById("timeline-container");
    const timelineHtml = [];
    
    // App created
    timelineHtml.push(`
        <div class="timeline-item">
            <div class="timeline-date">${new Date(appData.created_at).toLocaleString()}</div>
            <div><strong>Application Submitted</strong></div>
        </div>
    `);
    
    // Reviews
    if (appData.reviews && appData.reviews.length > 0) {
        // Sort chronologically
        const reviews = [...appData.reviews].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
        reviews.forEach(r => {
            timelineHtml.push(`
                <div class="timeline-item">
                    <div class="timeline-date">${new Date(r.created_at).toLocaleString()}</div>
                    <div><strong>Status changed:</strong> ${r.previous_status} &rarr; ${r.new_status}</div>
                    ${r.admin_notes ? `<div style="margin-top: 0.5rem; font-size: 0.9rem; color: #555;"><strong>Admin Note:</strong> ${r.admin_notes}</div>` : ''}
                    ${r.applicant_message ? `<div style="margin-top: 0.5rem; font-size: 0.9rem; color: #555; background:#f0f0f0; padding: 0.5rem; border-radius:4px;"><strong>Applicant Response:</strong> ${r.applicant_message}</div>` : ''}
                </div>
            `);
        });
    }
    
    timelineContainer.innerHTML = timelineHtml.join('');
    
    // Adjust action buttons
    if (appData.status === "APPROVED") {
        document.getElementById("btn-suspend").style.display = "block";
    }
}

function setupActionForm() {
    const formContainer = document.getElementById("action-form-container");
    const title = document.getElementById("action-title");
    const actionInput = document.getElementById("action-type");
    const msgLabel = document.getElementById("msg-label");
    const messageInput = document.getElementById("action-message");
    const reapplyGroup = document.getElementById("reapply-group");
    const allowReapplyCb = document.getElementById("allow-reapply");
    const reapplyDaysWrapper = document.getElementById("reapply-days-wrapper");
    const confirmBtn = document.getElementById("btn-confirm-action");
    
    document.querySelectorAll(".action-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            const action = e.target.dataset.action;
            actionInput.value = action;
            formContainer.classList.add("active");
            reapplyGroup.style.display = "none";
            messageInput.required = false;
            
            if (action === "APPROVE") {
                title.textContent = "Approve Application";
                msgLabel.textContent = "Welcome Message (Optional, sent to user)";
                confirmBtn.className = "btn btn-success";
                confirmBtn.textContent = "Approve";
            } else if (action === "NEEDS_MORE_INFORMATION") {
                title.textContent = "Request More Information";
                msgLabel.textContent = "What information do you need? (Required)*";
                messageInput.required = true;
                confirmBtn.className = "btn btn-warning";
                confirmBtn.textContent = "Request Info";
            } else if (action === "REJECT") {
                title.textContent = "Reject Application";
                msgLabel.textContent = "Reason for Rejection (Optional)";
                reapplyGroup.style.display = "block";
                confirmBtn.className = "btn btn-danger";
                confirmBtn.textContent = "Reject";
            } else if (action === "SUSPENDED") {
                title.textContent = "Suspend Access";
                msgLabel.textContent = "Reason for Suspension (Optional)";
                confirmBtn.className = "btn btn-secondary";
                confirmBtn.textContent = "Suspend";
            }
        });
    });
    
    allowReapplyCb.addEventListener("change", (e) => {
        reapplyDaysWrapper.style.display = e.target.checked ? "block" : "none";
    });
    
    document.getElementById("btn-cancel-action").addEventListener("click", () => {
        formContainer.classList.remove("active");
    });
    
    document.getElementById("statusUpdateForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const action = actionInput.value;
        const msg = messageInput.value;
        
        const payload = {
            status: action,
            message: msg
        };
        
        if (action === "REJECT") {
            payload.reapply_allowed = allowReapplyCb.checked;
            payload.reapply_after_days = parseInt(document.getElementById("reapply-days").value, 10);
        }
        
        confirmBtn.disabled = true;
        confirmBtn.textContent = "Updating...";
        
        try {
            await API.post(`/api/admin/applications/${appId}/status`, payload);
            alert("Application status updated successfully.");
            window.location.reload();
        } catch (err) {
            console.error("Failed to update status", err);
            alert("Error: " + err.message);
            confirmBtn.disabled = false;
            confirmBtn.textContent = "Confirm";
        }
    });
}
