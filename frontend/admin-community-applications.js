import { initAuth } from './auth.js';
import { API } from './api.js';

let session = null;
let allApplications = [];
let currentFilter = "ALL";

document.addEventListener("DOMContentLoaded", async () => {
    await initAuth();
    
    document.addEventListener('astro:authChanged', async (e) => {
        session = e.detail;
        if (!session) {
            window.location.href = `/?redirect=${encodeURIComponent(window.location.pathname)}`;
            return;
        }
        
        // Ensure user is admin (optional client side check, server enforces it)
        await loadApplications();
    });
    
    // Tab filtering
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            e.target.classList.add("active");
            currentFilter = e.target.dataset.status;
            renderTable();
        });
    });
    
    // Search
    document.getElementById("search-input").addEventListener("input", renderTable);
});

async function loadApplications() {
    try {
        const apps = await API.get("/api/admin/applications");
        allApplications = apps;
        renderTable();
    } catch (err) {
        console.error("Failed to load applications", err);
        document.getElementById("applications-table-body").innerHTML = 
            `<tr><td colspan="7" style="color: red; text-align: center;">Failed to load applications. Ensure you have admin access.</td></tr>`;
    }
}

function renderTable() {
    const tbody = document.getElementById("applications-table-body");
    const search = document.getElementById("search-input").value.toLowerCase();
    
    let filtered = allApplications;
    
    if (currentFilter !== "ALL") {
        filtered = filtered.filter(app => app.status === currentFilter);
    }
    
    if (search) {
        filtered = filtered.filter(app => 
            app.full_name.toLowerCase().includes(search) || 
            app.email.toLowerCase().includes(search)
        );
    }
    
    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center;">No applications found.</td></tr>`;
        return;
    }
    
    tbody.innerHTML = filtered.map(app => `
        <tr>
            <td>${new Date(app.created_at).toLocaleDateString()}</td>
            <td>
                <strong>${app.full_name}</strong><br/>
                <small style="color: #666;">${app.email}</small><br/>
                <small style="color: #666;">${app.country}</small>
            </td>
            <td>${app.applicant_type}</td>
            <td>
                ${app.experience_range}<br/>
                <small style="color: #666;">${app.systems.join(', ') || 'None specified'}</small>
            </td>
            <td>${app.proofs_count}</td>
            <td><span class="badge ${app.status}">${app.status.replace(/_/g, ' ')}</span></td>
            <td>
                <a href="/admin/community-applications/${app.id}" class="btn-view">Review</a>
            </td>
        </tr>
    `).join('');
}
