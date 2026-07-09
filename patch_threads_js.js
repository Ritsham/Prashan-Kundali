const fs = require('fs');
let code = fs.readFileSync('frontend/community.js', 'utf8');

// Handle thread click
code = code.replace(
    `if (action.dataset.postAction === 'thread') openThread(postId);`,
    `if (action.dataset.postAction === 'thread') openThread(postId);`
);

// Add openThread function
const threadFunc = `
    async function openThread(postId) {
        state.activePostId = postId;
        const post = state.posts.find(p => p.id === postId);
        if (!post) return;
        
        document.getElementById('context-eyebrow').textContent = "Thread";
        document.getElementById('context-title').textContent = "Responses";
        
        const contextContent = document.getElementById('context-content');
        contextContent.innerHTML = '<p>Loading thread...</p>';
        
        document.getElementById('context-panel').classList.add('open');
        
        try {
            const replies = await apiGet(\`/api/community/messages/\${postId}/replies\`);
            renderThreadView(post, replies);
        } catch (e) {
            console.error(e);
            contextContent.innerHTML = '<p>Error loading thread.</p>';
        }
    }

    function renderThreadView(post, replies) {
        const contextContent = document.getElementById('context-content');
        let html = \`
            <div class="post-item" style="border: none; padding: 0 0 16px 0; border-bottom: 1px solid var(--community-border); border-radius: 0;">
                <div class="post-header">
                    <strong>\${escapeAttr(post.userName)}</strong>
                    <span>\${new Date(post.createdAt).toLocaleString()}</span>
                </div>
                <div class="post-body">
                    <p>\${escapeAttr(post.content)}</p>
                    \${post.imageBase64 ? \`<img src="\${post.imageBase64}" alt="Post image">\` : ''}
                </div>
            </div>
            
            <div class="thread-replies">
                \${replies.map(r => \`
                    <div class="post-item" style="border: none; padding: 12px 0;">
                        <div class="post-header">
                            <strong>\${escapeAttr(r.user_name)}</strong>
                            <span>\${new Date(r.created_at).toLocaleString()}</span>
                        </div>
                        <div class="post-body">
                            <p>\${escapeAttr(r.content)}</p>
                        </div>
                    </div>
                \`).join('')}
            </div>
            
            <form id="form-reply" class="composer" style="margin-top: auto;">
                <textarea id="reply-input" placeholder="Reply to thread..." required rows="2" style="width: 100%; border: 1px solid var(--community-border); border-radius: 6px; padding: 8px; background: transparent; color: #fff;"></textarea>
                <div class="composer-actions">
                    <button type="submit" class="primary-action small">Reply</button>
                    <button type="button" class="secondary-action small" id="btn-follow-thread">Follow</button>
                </div>
            </form>
        \`;
        contextContent.innerHTML = html;
        
        document.getElementById('form-reply').onsubmit = async (e) => {
            e.preventDefault();
            const input = document.getElementById('reply-input');
            const content = input.value;
            input.value = '';
            
            if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                state.ws.send(JSON.stringify({
                    action: 'send_thread_reply',
                    parent_message_id: post.id,
                    user_name: state.memberName,
                    content: content
                }));
            }
            // Optimistically update
            setTimeout(() => openThread(post.id), 500);
        };
        
        document.getElementById('btn-follow-thread').onclick = async () => {
            try {
                const res = await fetch(\`/api/community/threads/\${post.id}/follow\`, {
                    method: 'POST',
                    headers: {
                        'Authorization': \`Bearer \${state.session.access_token}\`
                    }
                });
                if (res.ok) {
                    const data = await res.json();
                    document.getElementById('btn-follow-thread').textContent = data.following ? 'Unfollow' : 'Follow';
                }
            } catch (e) {}
        };
    }
`;

if (!code.includes('function openThread')) {
    code = code.replace('function closeThread()', threadFunc + '\n    function closeThread()');
}

fs.writeFileSync('frontend/community.js', code);
console.log('patched thread JS');
