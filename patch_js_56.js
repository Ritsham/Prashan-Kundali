const fs = require('fs');
let code = fs.readFileSync('frontend/community.js', 'utf8');

// 1. Add Report button
const reportButton = '<button type="button" data-post-action="report" data-post-id="${escapeAttr(post.id)}" style="color: var(--community-muted);">🚩 Report</button>';
code = code.replace(
    '<button type="button" data-post-action="reaction" data-reaction-type="Insightful" data-post-id="${escapeAttr(post.id)}">💡 Insightful</button>',
    '<button type="button" data-post-action="reaction" data-reaction-type="Insightful" data-post-id="${escapeAttr(post.id)}">💡 Insightful</button>\n                    ' + reportButton
);

// 2. Add Report logic
const reportLogic = `
    if (action.dataset.postAction === 'report') {
        const reason = prompt("Reason for reporting this post?");
        if (reason) {
            try {
                await fetch(\`/api/community/messages/\${postId}/report\`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': \`Bearer \${state.session.access_token}\`
                    },
                    body: JSON.stringify({ reason })
                });
                alert("Post reported successfully.");
            } catch (e) {
                alert("Failed to report post.");
            }
        }
    }
`;
code = code.replace(
    `if (action.dataset.postAction === 'reaction') toggleReaction(postId, action.dataset.reactionType);`,
    `if (action.dataset.postAction === 'reaction') toggleReaction(postId, action.dataset.reactionType);\n        ${reportLogic}`
);

// 3. Add Members Directory Logic
const membersLogic = `
document.getElementById('nav-members')?.addEventListener('click', async (e) => {
    e.preventDefault();
    state.currentChannel = null;
    
    // Render Members Directory in center panel
    const postsFeed = document.getElementById('posts-feed');
    postsFeed.innerHTML = '<p>Loading members...</p>';
    
    // Hide composer
    document.getElementById('form-chat')?.classList.add('hidden');
    document.querySelector('.chat-head h2').textContent = "Members Directory";
    document.querySelector('.chat-head .eyebrow').textContent = "Community";
    
    try {
        const members = await apiGet('/api/community/members');
        let html = '<div class="members-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px;">';
        
        members.forEach(m => {
            html += \`
                <div class="member-card" style="border: 1px solid var(--community-border); padding: 16px; border-radius: 8px; cursor: pointer;" onclick="viewMemberProfile('\${m.user_id}')">
                    <h3 style="margin-top: 0; margin-bottom: 4px;">\${escapeAttr(m.display_name)}</h3>
                    <p style="color: var(--community-muted); font-size: 0.9rem; margin-top: 0;">@\${escapeAttr(m.username)}</p>
                    <p style="font-size: 0.85rem; margin-bottom: 0;">\${m.systems_practiced ? m.systems_practiced.join(', ') : ''}</p>
                </div>
            \`;
        });
        
        html += '</div>';
        postsFeed.innerHTML = html;
        
    } catch (e) {
        postsFeed.innerHTML = '<p>Error loading members.</p>';
    }
});

// View Member Profile
window.viewMemberProfile = async function(userId) {
    document.getElementById('context-eyebrow').textContent = "Profile";
    document.getElementById('context-title').textContent = "Astrologer Details";
    const contextContent = document.getElementById('context-content');
    contextContent.innerHTML = '<p>Loading profile...</p>';
    document.getElementById('context-panel').classList.add('open');
    
    try {
        const p = await apiGet(\`/api/community/members/\${userId}\`);
        contextContent.innerHTML = \`
            <div style="padding: 16px 0;">
                <h3 style="margin: 0 0 4px 0;">\${escapeAttr(p.display_name)}</h3>
                <p style="color: var(--community-muted); margin: 0 0 16px 0;">@\${escapeAttr(p.username)}</p>
                <p><strong>Bio:</strong><br>\${escapeAttr(p.bio || 'No bio provided.')}</p>
                <p><strong>Systems:</strong><br>\${p.systems_practiced ? p.systems_practiced.join(', ') : '-'}</p>
                <p><strong>Experience:</strong><br>\${escapeAttr(p.experience_years || '-')}</p>
                <p><strong>Location:</strong><br>\${escapeAttr(p.state || '')}, \${escapeAttr(p.country || '')}</p>
            </div>
        \`;
    } catch (e) {
        contextContent.innerHTML = '<p>Error loading profile.</p>';
    }
};

// Update author clicking
document.getElementById('posts-feed')?.addEventListener('click', (e) => {
    if (e.target.classList.contains('author')) {
        // Find post id
        const postEl = e.target.closest('.post-item');
        if (postEl) {
            const footer = postEl.querySelector('footer button[data-post-id]');
            if (footer) {
                const postId = footer.dataset.postId;
                const post = state.posts.find(p => p.id === postId);
                // Currently user_name holds the uuid since save_message was using auth.user_id
                if (post && post.userName) { 
                    viewMemberProfile(post.userName);
                }
            }
        }
    }
});
`;

if (!code.includes('nav-members')) {
    code += '\n' + membersLogic;
}
fs.writeFileSync('frontend/community.js', code);
console.log("patched!");
