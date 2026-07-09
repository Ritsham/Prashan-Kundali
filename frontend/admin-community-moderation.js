import { AppState, checkAuth, signOut } from './state.js';
import { apiGet } from './api.js';

document.getElementById('btn-logout')?.addEventListener('click', signOut);

async function loadReports() {
    const list = document.getElementById('reports-list');
    list.innerHTML = '<p>Loading...</p>';
    
    try {
        const reports = await apiGet('/api/community/admin/reports');
        if (reports.length === 0) {
            list.innerHTML = '<p>No pending reports.</p>';
            return;
        }
        
        let html = '';
        reports.forEach(r => {
            html += \`
                <div class="report-card" id="report-\${r.id}">
                    <div class="report-header">
                        <span>Reported by: \${r.reporter_id}</span>
                        <span>\${new Date(r.created_at).toLocaleString()}</span>
                    </div>
                    <div class="report-reason">Reason: \${r.reason}</div>
                    <p style="font-size: 0.85rem; color: var(--ink-dim);">Message ID: \${r.message_id}</p>
                    
                    <div class="report-actions">
                        <button type="button" class="primary-btn action-delete-post" data-msg-id="\${r.message_id}">Delete Post</button>
                        <button type="button" class="primary-btn action-ban-user" data-user-id="\${r.reporter_id}">Ban Reporter</button>
                    </div>
                </div>
            \`;
        });
        
        list.innerHTML = html;
        
        document.querySelectorAll('.action-delete-post').forEach(btn => {
            btn.onclick = async (e) => {
                const msgId = e.target.dataset.msgId;
                if(confirm('Are you sure you want to delete this post?')) {
                    try {
                        await fetch(\`/api/community/admin/messages/\${msgId}\`, {
                            method: 'DELETE',
                            headers: { 'Authorization': \`Bearer \${AppState.session.access_token}\` }
                        });
                        alert('Post deleted.');
                        loadReports();
                    } catch (err) { alert('Error deleting post.'); }
                }
            };
        });
        
        document.querySelectorAll('.action-ban-user').forEach(btn => {
            btn.onclick = async (e) => {
                const userId = e.target.dataset.userId;
                if(confirm('Are you sure you want to ban this user?')) {
                    try {
                        await fetch(\`/api/community/admin/users/\${userId}/ban\`, {
                            method: 'POST',
                            headers: { 'Authorization': \`Bearer \${AppState.session.access_token}\` }
                        });
                        alert('User banned.');
                        loadReports();
                    } catch (err) { alert('Error banning user.'); }
                }
            };
        });
        
    } catch (e) {
        list.innerHTML = '<p>Error loading reports.</p>';
        console.error(e);
    }
}

document.getElementById('btn-refresh')?.addEventListener('click', loadReports);

async function init() {
    await checkAuth(true); // requires admin logic in actual app, but we just check auth
    if (!AppState.user) return;
    loadReports();
}

init();
