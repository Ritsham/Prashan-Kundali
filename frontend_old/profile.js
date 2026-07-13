import { requireAuth, initLogout } from './auth-shared.js';

async function initProfile() {
    const auth = await requireAuth();
    if (!auth) return;
    const { supabase, session } = auth;
    
    initLogout('btn-logout');

    document.getElementById('user-email').innerText = session.user.email;

    // Fetch community applications
    const { data: communityApps, error: communityErr } = await supabase
        .from('community_applications')
        .select('*')
        .eq('user_id', session.user.id)
        .order('created_at', { ascending: false });

    const commContainer = document.getElementById('community-app-container');
    if (communityApps && communityApps.length > 0) {
        commContainer.innerHTML = '';
        communityApps.forEach(app => {
            const date = new Date(app.created_at).toLocaleDateString();
            const statusClass = app.status === 'APPROVED' ? 'status-approved' : 
                              (app.status === 'REJECTED' ? 'status-rejected' : 'status-pending');
            
            commContainer.innerHTML += `
                <div class="list-item">
                    <div class="item-details">
                        <h4>Application ID: ${app.id.substring(0, 8).toUpperCase()}</h4>
                        <p>Submitted Date: ${date}</p>
                    </div>
                    <div>
                        <span class="status-badge ${statusClass}">${app.status}</span>
                    </div>
                </div>
            `;
        });
    } else {
        commContainer.innerHTML = '<div class="empty-state">No community applications found.</div>';
    }

    // Fetch consultations
    const { data: consultations, error: consErr } = await supabase
        .from('consultation_requests')
        .select('*')
        .eq('user_id', session.user.id)
        .order('created_at', { ascending: false });

    const consContainer = document.getElementById('consultations-container');
    if (consultations && consultations.length > 0) {
        consContainer.innerHTML = '';
        consultations.forEach(cons => {
            const date = new Date(cons.created_at).toLocaleDateString();
            let statusText = cons.status.toUpperCase();
            let statusClass = 'status-pending';
            
            if (cons.status === 'completed' || cons.status === 'answered') {
                statusClass = 'status-approved';
                statusText = 'COMPLETED';
            } else if (cons.status === 'declined' || cons.status === 'cancelled') {
                statusClass = 'status-rejected';
                statusText = 'CANCELLED';
            }

            consContainer.innerHTML += `
                <div class="list-item">
                    <div class="item-details">
                        <h4>${cons.topic ? cons.topic.toUpperCase() : 'CONSULTATION'}</h4>
                        <p>Date: ${date} • For: ${cons.name}</p>
                    </div>
                    <div>
                        <span class="status-badge ${statusClass}">${statusText}</span>
                    </div>
                </div>
            `;
        });
    } else {
        consContainer.innerHTML = '<div class="empty-state">No consultation records found.</div>';
    }
}

document.addEventListener('DOMContentLoaded', initProfile);
