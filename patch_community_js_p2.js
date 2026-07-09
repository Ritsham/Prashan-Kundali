const fs = require('fs');
let code = fs.readFileSync('frontend/community.js', 'utf8');

// Pagination state
if (!code.includes('oldestCursor: null')) {
    code = code.replace(
        'activePostId: null,',
        'activePostId: null,\n        oldestCursor: null,\n        hasMorePosts: true,'
    );
}

// Update loadPosts to clear pagination state and fetch initial
code = code.replace(
    'const rows = await apiGet(`/api/community/messages/${encodeURIComponent(channel.apiName)}`);',
    `state.oldestCursor = null;
            state.hasMorePosts = true;
            const rows = await apiGet(\`/api/community/messages/\${encodeURIComponent(channel.apiName)}\`);
            if (rows.length > 0) {
                state.oldestCursor = rows[0].created_at;
            }
            if (rows.length < 50) state.hasMorePosts = false;`
);

// Add loadOlderPosts function
const loadOlderPostsFunc = `
    async function loadOlderPosts() {
        if (!state.hasMorePosts || !state.oldestCursor) return;
        const channel = getChannel(state.currentChannel);
        try {
            const rows = await apiGet(\`/api/community/messages/\${encodeURIComponent(channel.apiName)}?cursor=\${state.oldestCursor}\`);
            if (rows.length > 0) {
                state.oldestCursor = rows[0].created_at;
                const olderPosts = rows.map((row) => normalizePost(row, channel));
                state.posts = [...olderPosts, ...state.posts];
                renderPosts();
            }
            if (rows.length < 50) state.hasMorePosts = false;
        } catch (e) {
            console.error(e);
        }
    }
`;
if (!code.includes('function loadOlderPosts')) {
    code = code.replace('function renderPosts() {', loadOlderPostsFunc + '\n    function renderPosts() {');
}

// Update renderPosts to include reaction buttons and load more button
const renderFooterOld = `                <footer>
                    <button type="button" data-post-action="thread" data-post-id="\${escapeAttr(post.id)}">Open Responses</button>
                    <button type="button" data-post-action="star" data-post-id="\${escapeAttr(post.id)}">Star \${post.stars ? \`(\${post.stars})\` : ''}</button>
                </footer>`;

const renderFooterNew = `                <footer>
                    <button type="button" data-post-action="thread" data-post-id="\${escapeAttr(post.id)}">Open Responses</button>
                    <button type="button" data-post-action="reaction" data-reaction-type="Helpful" data-post-id="\${escapeAttr(post.id)}">🙏 Helpful</button>
                    <button type="button" data-post-action="reaction" data-reaction-type="Insightful" data-post-id="\${escapeAttr(post.id)}">💡 Insightful</button>
                </footer>`;
code = code.replace(renderFooterOld, renderFooterNew);

// Add Load More button to postsFeed if there are more
code = code.replace(
    `        postsFeed.innerHTML = state.posts.map((post) => \``,
    `        let html = state.hasMorePosts ? '<button type="button" id="btn-load-older" class="secondary-action small" style="width: 100%; margin-bottom: 14px;">Load Older Messages</button>' : '';
        html += state.posts.map((post) => \``
);
code = code.replace(
    `        }).join('');`,
    `        }).join('');
        postsFeed.innerHTML = html;
        document.getElementById('btn-load-older')?.addEventListener('click', loadOlderPosts);`
);

// Reaction event handler in postsFeed listener
code = code.replace(
    `if (action.dataset.postAction === 'star') starPost(postId);`,
    `if (action.dataset.postAction === 'reaction') toggleReaction(postId, action.dataset.reactionType);`
);

// Add toggleReaction function
const reactionFunc = `
    async function toggleReaction(postId, reactionType) {
        if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
        state.ws.send(JSON.stringify({
            action: 'toggle_reaction',
            message_id: postId,
            reaction_type: reactionType,
            user_id: state.session?.user?.id
        }));
        try {
            await fetch(\`/api/community/messages/\${postId}/reactions\`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': \`Bearer \${state.session.access_token}\`
                },
                body: JSON.stringify({ reaction_type: reactionType })
            });
        } catch (e) { console.error("Reaction API failed", e); }
    }
`;
if (!code.includes('function toggleReaction')) {
    code = code.replace('function starPost(postId)', reactionFunc + '\n    function starPost(postId)');
}

fs.writeFileSync('frontend/community.js', code);
console.log('patched phase 2 frontend');
