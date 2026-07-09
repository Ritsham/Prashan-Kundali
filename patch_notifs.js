const fs = require('fs');
let code = fs.readFileSync('frontend/community.js', 'utf8');

const notifLogic = `
document.getElementById('nav-notifications')?.addEventListener('click', async (e) => {
    e.preventDefault();
    state.currentChannel = null;
    
    const postsFeed = document.getElementById('posts-feed');
    postsFeed.innerHTML = '<p>Loading notifications...</p>';
    
    document.getElementById('form-chat')?.classList.add('hidden');
    document.querySelector('.chat-head h2').textContent = "Notifications";
    document.querySelector('.chat-head .eyebrow').textContent = "Community";
    
    try {
        const notifs = await apiGet('/api/community/notifications');
        let html = '<div class="notifications-list">';
        
        if (notifs.length === 0) {
            html += '<p>No new notifications.</p>';
        }
        
        notifs.forEach(n => {
            html += \`
                <div class="notif-item \${n.is_read ? 'read' : 'unread'}" style="padding: 12px; border-bottom: 1px solid var(--community-border); \${n.is_read ? '' : 'background: rgba(142, 68, 173, 0.1);'}">
                    <p style="margin: 0; font-size: 0.95rem;">
                        <strong>\${n.type}</strong> \${n.type === 'REACTION' ? 'on your post' : 'on a thread you follow'}
                    </p>
                    <span style="font-size: 0.8rem; color: var(--community-muted);">\${new Date(n.created_at).toLocaleString()}</span>
                </div>
            \`;
        });
        
        html += '</div>';
        postsFeed.innerHTML = html;
        
        // Mark read
        await fetch('/api/community/notifications/read', {
            method: 'POST',
            headers: { 'Authorization': \`Bearer \${state.session.access_token}\` }
        });
        
    } catch (e) {
        postsFeed.innerHTML = '<p>Error loading notifications.</p>';
    }
});
`;

if (!code.includes('nav-notifications')) {
    code += '\n' + notifLogic;
    fs.writeFileSync('frontend/community.js', code);
    console.log("patched!");
}
