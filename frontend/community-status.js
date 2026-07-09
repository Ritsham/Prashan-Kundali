import { initAuth } from './auth.js';
import { API } from './api.js';

let session = null;
let currentApplication = null;

document.addEventListener("DOMContentLoaded", async () => {
    await initAuth();
    
    document.addEventListener('astro:authChanged', async (e) => {
        session = e.detail;
        if (!session) {
            window.location.href = `/?redirect=${encodeURIComponent(window.location.pathname)}`;
            return;
        }
        await loadStatus();
    });
    
    document.getElementById("btn-support").addEventListener("click", () => {
        const supportNumber = "919876543210"; // Fallback, could be fetched from config
        const email = session.user.email;
        const appId = currentApplication?.id || "N/A";
        const message = `Hello, I need help with my astrologer community application.\n\nApplication ID: ${appId}\nRegistered Email: ${email}`;
        window.open(`https://wa.me/${supportNumber}?text=${encodeURIComponent(message)}`, '_blank');
    });
    
    document.getElementById("btn-reapply").addEventListener("click", () => {
        window.location.href = "/community/apply";
    });
    
    document.getElementById("moreInfoForm").addEventListener("submit", submitMoreInfo);
});

async function loadStatus() {
    try {
        const data = await API.get("/api/community/application/status");
        if (data.status === "NOT_APPLIED") {
            window.location.href = "/community/apply";
            return;
        }
        
        currentApplication = data;
        renderStatus(data);
    } catch (err) {
        console.error("Failed to load status", err);
        alert("Failed to load application status.");
    }
}

function renderStatus(app) {
    document.getElementById("status-card").style.display = "block";
    
    const badge = document.getElementById("status-badge");
    badge.textContent = app.status.replace(/_/g, ' ');
    badge.className = `status-badge ${app.status}`;
    
    document.getElementById("app-id").textContent = app.id.split('-')[0].toUpperCase();
    document.getElementById("app-date").textContent = new Date(app.created_at).toLocaleDateString();
    
    const msgEl = document.getElementById("status-message");
    const titleEl = document.getElementById("status-title");
    
    // Default hiding
    document.getElementById("btn-enter-community").style.display = "none";
    document.getElementById("btn-reapply").style.display = "none";
    document.getElementById("more-info-section").style.display = "none";
    document.getElementById("est-time-row").style.display = "block";
    
    switch (app.status) {
        case "PENDING":
            titleEl.textContent = "Application Under Review";
            msgEl.textContent = "Your application is currently being reviewed.\nMost applications are reviewed within 2–3 days.\nNo further action is required from you at this time.";
            break;
            
        case "NEEDS_MORE_INFORMATION":
            titleEl.textContent = "More Information Required";
            msgEl.innerHTML = `<strong>Admin Message:</strong><br/>${app.applicant_facing_message || "We need some additional information to complete your verification."}`;
            document.getElementById("more-info-section").style.display = "block";
            break;
            
        case "APPROVED":
            titleEl.textContent = "Welcome to the Community";
            msgEl.textContent = "Your application has been approved.\nYou now have access to our private community of astrologers, practitioners, and serious astrology learners.";
            document.getElementById("btn-enter-community").style.display = "inline-block";
            document.getElementById("est-time-row").style.display = "none";
            badge.textContent = "VERIFIED";
            break;
            
        case "REJECTED":
            titleEl.textContent = "Application Not Approved";
            msgEl.textContent = "After reviewing the information provided, we were unable to verify sufficient astrology-related background for community access at this time.";
            document.getElementById("est-time-row").style.display = "none";
            
            if (app.reapply_allowed) {
                const reapplyDate = app.reapply_after ? new Date(app.reapply_after) : new Date();
                if (new Date() >= reapplyDate) {
                    document.getElementById("btn-reapply").style.display = "inline-block";
                } else {
                    msgEl.textContent += `\n\nYou can reapply after ${reapplyDate.toLocaleDateString()}.`;
                }
            }
            break;
            
        case "SUSPENDED":
            titleEl.textContent = "Community Access Suspended";
            msgEl.textContent = "Your access to the community has been suspended. Please contact support for more information.";
            document.getElementById("est-time-row").style.display = "none";
            break;
    }
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);
    
    const token = session.access_token;
    const res = await fetch("/api/community/application/upload-proof", {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
        body: formData
    });
    
    if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to upload file");
    }
    return await res.json();
}

async function submitMoreInfo(e) {
    e.preventDefault();
    const btn = document.getElementById("btn-submit-more-info");
    btn.disabled = true;
    btn.textContent = "Submitting...";
    
    try {
        const text = document.getElementById("more-info-text").value;
        const link = document.getElementById("more-info-link").value;
        const file = document.getElementById("more-info-file").files[0];
        
        let proofData = null;
        if (file || link) {
            proofData = { type: "Additional Information", external_url: link || null };
            if (file) {
                const uploaded = await uploadFile(file);
                proofData.file_url = uploaded.file_url;
                proofData.original_file_name = uploaded.original_file_name;
                proofData.mime_type = uploaded.mime_type;
                proofData.file_size = uploaded.file_size;
            }
        }
        
        const payload = {
            response_text: text,
            proof: proofData
        };
        
        await API.post("/api/community/application/more-info", payload);
        alert("Information submitted successfully!");
        window.location.reload();
    } catch (err) {
        console.error(err);
        alert("Error submitting information: " + err.message);
        btn.disabled = false;
        btn.textContent = "Submit Additional Information";
    }
}
