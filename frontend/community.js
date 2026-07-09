import { getSupabase } from './auth-shared.js';
import { showFlash } from './flash.js';

document.addEventListener('DOMContentLoaded', () => {
    const state = {
        supabase: null,
        session: null,
        channels: [],
        posts: [],
        currentChannel: 'general-discussion',
        ws: null,
        selectedImageBase64: null,
        activePostId: null,
        oldestCursor: null,
        hasMorePosts: true,
        memberName: 'Astrologer',
    };

    const landing = document.getElementById('community-landing');
    const app = document.getElementById('community-app');
    const accessNote = document.getElementById('access-note');
    const channelFilter = document.getElementById('channel-filter');
    const postChannel = document.getElementById('post-channel');
    const channelOverview = document.getElementById('channel-overview');
    const postsFeed = document.getElementById('posts-feed');
    const statusPanel = document.getElementById('status-panel');
    const composerPanel = document.getElementById('composer-panel');
    const postForm = document.getElementById('post-form');
    const postTitle = document.getElementById('post-title');
    const postBody = document.getElementById('post-body');
    const postImage = document.getElementById('post-image');
    const imagePreviewWrap = document.getElementById('image-preview-wrap');
    const postImagePreview = document.getElementById('post-image-preview');
    const threadPanel = document.getElementById('thread-panel');
    const threadOriginal = document.getElementById('thread-original');
    const threadReplies = document.getElementById('thread-replies');
    const responseForm = document.getElementById('response-form');
    const responseInput = document.getElementById('response-input');

    init();

    async function init() {
        bindLanding();
        bindWorkspace();

        state.supabase = await getSupabase();
        const { data } = await state.supabase.auth.getSession();
        state.session = data.session;

        state.supabase.auth.onAuthStateChange((_event, session) => {
            state.session = session;
            // DEV BYPASS (Force enabled for developer preview)
            state.channels = normalizeChannels([]);
            state.currentChannel = state.channels[0].slug;
            renderChannels();
            renderPosts();
            showWorkspace();
        });

        if (state.session) {
            await loadCommunity();
        } else {
            // DEV BYPASS
            state.channels = normalizeChannels([]);
            state.currentChannel = state.channels[0].slug;
            renderChannels();
            renderPosts();
            showWorkspace();
        }
    }

    function bindLanding() {
        document.getElementById('landing-sign-in')?.addEventListener('click', signIn);
        document.getElementById('hero-sign-in')?.addEventListener('click', signIn);
    }

    function bindWorkspace() {
        document.getElementById('open-composer')?.addEventListener('click', openComposer);
        document.getElementById('close-composer')?.addEventListener('click', closeComposer);
        document.getElementById('cancel-composer')?.addEventListener('click', closeComposer);
        document.getElementById('refresh-community')?.addEventListener('click', () => loadPosts(state.currentChannel));
        document.getElementById('close-thread')?.addEventListener('click', closeThread);
        document.getElementById('clear-post-image')?.addEventListener('click', clearImage);

        channelFilter.addEventListener('change', () => {
            state.currentChannel = channelFilter.value;
            loadPosts(state.currentChannel);
            connectWebSocket(state.currentChannel);
        });

        document.querySelectorAll('.community-nav button').forEach((button) => {
            button.addEventListener('click', () => {
                document.querySelectorAll('.community-nav button').forEach((btn) => btn.classList.remove('active'));
                button.classList.add('active');
                if (button.dataset.action === 'create') {
                    openComposer();
                    return;
                }
                renderView(button.dataset.view);
            });
        });

        postImage.addEventListener('change', () => {
            const file = postImage.files?.[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (event) => {
                state.selectedImageBase64 = event.target.result;
                postImagePreview.src = state.selectedImageBase64;
                imagePreviewWrap.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        });

        postForm.addEventListener('submit', (event) => {
            event.preventDefault();
            publishPost();
        });

        responseForm.addEventListener('submit', (event) => {
            event.preventDefault();
            publishResponse();
        });

        postsFeed.addEventListener('click', (event) => {
            const action = event.target.closest('[data-post-action]');
            if (!action) return;
            const postId = action.dataset.postId;
            if (action.dataset.postAction === 'thread') openThread(postId);
            if (action.dataset.postAction === 'reaction') toggleReaction(postId, action.dataset.reactionType);
        
    if (action.dataset.postAction === 'report') {
        const reason = prompt("Reason for reporting this post?");
        if (reason) {
            try {
                await fetch(`/api/community/messages/${postId}/report`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${state.session.access_token}`
                    },
                    body: JSON.stringify({ reason })
                });
                alert("Post reported successfully.");
            } catch (e) {
                alert("Failed to report post.");
            }
        }
    }

        });
    }

    async function signIn() {
        await state.supabase.auth.signInWithOAuth({
            provider: 'google',
            options: { redirectTo: `${window.location.origin}/astro-community` },
        });
    }

    
    async function loadCommunity() {
        try {
            showStatus('Checking Astro Community membership...');
            const profile = await getCurrentProfile();
            state.memberName = profile?.display_name || profile?.name || state.session?.user?.user_metadata?.full_name || 'Astrologer';
            
            // Check if community profile exists, if not trigger onboarding
            try {
                const commProfile = await apiGet('/api/community/profile');
                if (!commProfile) {
                    showOnboarding();
                    return; // Pause loading until onboarding finishes
                } else {
                    state.memberName = commProfile.display_name || state.memberName;
                }
            } catch (e) {
                console.error("Profile check failed, assuming no profile.", e);
                showOnboarding();
                return;
            }
            
            await finalizeCommunityLoad();
        } catch (error) {
            console.error(error);
            showLanding(error.message.includes('verified astrologer')
                ? 'Astro Community is available only to approved astrologers. Apply to join or check your application status.'
                : error.message);
        }
    }

    async function finalizeCommunityLoad() {
        state.channels = normalizeChannels(await apiGet('/api/community/channels'));
        if (!state.channels.length) throw new Error('No channels are available yet.');
        state.currentChannel = state.channels[0].slug;
        renderChannels();
        showWorkspace();
        await loadPosts(state.currentChannel);
        connectWebSocket(state.currentChannel);
    }

    let currentStep = 1;
    function showOnboarding() {
        document.getElementById('onboarding-overlay').classList.remove('hidden');
        document.querySelectorAll('.btn-next-step').forEach(btn => {
            btn.onclick = () => {
                document.getElementById('step-' + currentStep).classList.remove('active');
                currentStep++;
                const nextEl = document.getElementById('step-' + currentStep);
                if (nextEl) {
                    nextEl.classList.add('active');
                }
            };
        });
        document.getElementById('btn-finish-onboarding').onclick = async () => {
            const username = document.getElementById('ob-username').value;
            const displayName = document.getElementById('ob-displayname').value;
            const bio = document.getElementById('ob-bio').value;
            const systems = document.getElementById('ob-systems').value.split(',').map(s => s.trim()).filter(Boolean);
            
            try {
                const response = await fetch('/api/community/profile', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${state.session.access_token}`
                    },
                    body: JSON.stringify({
                        username: username || 'user_' + Math.floor(Math.random()*10000),
                        display_name: displayName || state.memberName,
                        bio: bio,
                        state: '',
                        country: '',
                        experience_years: '',
                        specializations: [],
                        languages: [],
                        systems_practiced: systems
                    })
                });
                
                if (response.ok) {
                    document.getElementById('onboarding-overlay').classList.add('hidden');
                    await finalizeCommunityLoad();
                } else {
                    alert("Failed to save profile. Please try again.");
                }
            } catch (e) {
                console.error(e);
                alert("An error occurred saving profile.");
            }
        };
    }

    async function getCurrentProfile() {
        const { data } = await state.supabase
            .from('users')
            .select('name, display_name, role, verification_status')
            .eq('id', state.session.user.id)
            .single();
        return data;
    }

    function showLanding(message) {
        closeSocket();
        app.classList.add('hidden');
        landing.classList.remove('hidden');
        if (message) accessNote.textContent = message;
    }

    function showWorkspace() {
        landing.classList.add('hidden');
        app.classList.remove('hidden');
        statusPanel.classList.add('hidden');
    }

    function showStatus(message) {
        statusPanel.textContent = message;
        statusPanel.classList.remove('hidden');
    }

    function renderChannels() {
        const options = state.channels.map((channel) => `<option value="${escapeAttr(channel.slug)}">${escapeHtml(channel.name)}</option>`).join('');
        channelFilter.innerHTML = options;
        postChannel.innerHTML = options;
        channelFilter.value = state.currentChannel;
        postChannel.value = state.currentChannel;
        renderChannelOverview();
    }

    function renderChannelOverview() {
        channelOverview.innerHTML = state.channels.map((channel) => `
            <button type="button" class="channel-card ${channel.slug === state.currentChannel ? 'active' : ''}" data-channel="${escapeAttr(channel.slug)}">
                <span>${escapeHtml(channel.icon)}</span>
                <strong>${escapeHtml(channel.name)}</strong>
                <small>${escapeHtml(channel.description)}</small>
            </button>
        `).join('');

        channelOverview.querySelectorAll('[data-channel]').forEach((button) => {
            button.addEventListener('click', () => {
                state.currentChannel = button.dataset.channel;
                channelFilter.value = state.currentChannel;
                loadPosts(state.currentChannel);
                connectWebSocket(state.currentChannel);
            });
        });
    }

    async function loadPosts(channelSlug) {
        try {
            closeThread();
            renderChannelOverview();
            showStatus('Loading professional discussions...');
            const channel = getChannel(channelSlug);
            state.oldestCursor = null;
            state.hasMorePosts = true;
            const rows = await apiGet(`/api/community/messages/${encodeURIComponent(channel.apiName)}`);
            if (rows.length > 0) {
                state.oldestCursor = rows[0].created_at;
            }
            if (rows.length < 50) state.hasMorePosts = false;
            state.posts = rows.map((row) => normalizePost(row, channel));
            renderPosts();
            statusPanel.classList.add('hidden');
        } catch (error) {
            console.error(error);
            showStatus(error.message);
        }
    }

    
    async function loadOlderPosts() {
        if (!state.hasMorePosts || !state.oldestCursor) return;
        const channel = getChannel(state.currentChannel);
        try {
            const rows = await apiGet(`/api/community/messages/${encodeURIComponent(channel.apiName)}?cursor=${state.oldestCursor}`);
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

    function renderPosts() {
        if (!state.posts.length) {
            postsFeed.innerHTML = `
                <div class="empty-feed">
                    <h2>No posts in this channel yet</h2>
                    <p>Start a durable discussion with a clear question, chart context, and your astrological reasoning.</p>
                    <button type="button" class="primary-action small" id="empty-create">Create Post</button>
                </div>
            `;
            document.getElementById('empty-create')?.addEventListener('click', openComposer);
            return;
        }

        let html = state.hasMorePosts ? '<button type="button" id="btn-load-older" class="secondary-action small" style="width: 100%; margin-bottom: 14px;">Load Older Messages</button>' : '';
        html += state.posts.map((post) => {
            let contentHtml = '';
            if (post.contentType === 'PRASHNA_CASE' || post.contentType === 'LAGNA_CASE') {
                contentHtml = `
                    <div class="chart-discussion-card" style="border: 1px solid var(--primary-accent); border-radius: 8px; padding: 12px; margin-bottom: 8px; background: rgba(142, 68, 173, 0.1);">
                        <div style="font-size: 0.8rem; text-transform: uppercase; color: var(--primary-accent); margin-bottom: 4px;">🪐 ${post.contentType === 'PRASHNA_CASE' ? 'Prashna Chart' : 'Birth Chart'} shared for discussion</div>
                        <p>${escapeAttr(post.content)}</p>
                        ${post.chartId ? `<a href="/${post.contentType === 'PRASHNA_CASE' ? 'prashna' : 'lagna'}?id=${post.chartId}" target="_blank" style="color: var(--primary-accent); text-decoration: underline; font-size: 0.9rem;">View Chart Details ↗</a>` : ''}
                    </div>
                `;
            } else {
                contentHtml = `
                    <p>${escapeAttr(post.content)}</p>
                    ${post.imageBase64 ? `<img src="${post.imageBase64}" alt="User uploaded image" />` : ''}
                `;
            }

            return `
            <div class="post-item">
                <header>
                    <div class="post-meta">
                        <span class="author" title="${escapeAttr(post.userName)}">${escapeAttr(post.userName)}</span>
                        <span class="time">${new Date(post.createdAt).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                    </div>
                </header>
                <div class="post-content">
                    ${contentHtml}
                </div>
                <footer>
                    <button type="button" data-post-action="thread" data-post-id="${escapeAttr(post.id)}">Open Responses</button>
                    <button type="button" data-post-action="reaction" data-reaction-type="Helpful" data-post-id="${escapeAttr(post.id)}">🙏 Helpful</button>
                    <button type="button" data-post-action="reaction" data-reaction-type="Insightful" data-post-id="${escapeAttr(post.id)}">💡 Insightful</button>
                    <button type="button" data-post-action="report" data-post-id="${escapeAttr(post.id)}" style="color: var(--community-muted);">🚩 Report</button>
                </footer>
            </div>`;
}).join('');
    }

    function openComposer() {
        postChannel.value = state.currentChannel;
        composerPanel.classList.remove('hidden');
        postTitle.focus();
    }

    function closeComposer() {
        composerPanel.classList.add('hidden');
        postForm.reset();
        clearImage();
    }

    function clearImage() {
        state.selectedImageBase64 = null;
        postImage.value = '';
        postImagePreview.src = '';
        imagePreviewWrap.classList.add('hidden');
    }

    function publishPost() {
        const channel = getChannel(postChannel.value);
        const body = [
            `# ${postTitle.value.trim()}`,
            '',
            postBody.value.trim(),
        ].join('\n');
        const image = state.selectedImageBase64;

        if (!state.ws || state.ws.readyState !== WebSocket.OPEN || channel.slug !== state.currentChannel) {
            state.currentChannel = channel.slug;
            channelFilter.value = channel.slug;
            connectWebSocket(channel.slug, () => sendPost(body, image));
        } else {
            sendPost(body, image);
        }
        closeComposer();
    }

    function sendPost(content, image) {
        state.ws.send(JSON.stringify({
            action: 'send_message',
            user_name: state.memberName,
            content,
            image_base64: image,
        }));
    }

    async function openThread(postId) {
        const post = state.posts.find((item) => item.id === postId);
        if (!post) return;
        state.activePostId = postId;
        threadOriginal.innerHTML = `
            <span class="channel-pill">${escapeHtml(post.channelName)}</span>
            <h3>${escapeHtml(post.title)}</h3>
            <div>${renderMarkdown(post.body)}</div>
        `;
        threadReplies.innerHTML = '<p class="muted-line">Loading responses...</p>';
        threadPanel.classList.add('open');

        try {
            const replies = await apiGet(`/api/community/threads/${encodeURIComponent(postId)}`);
            threadReplies.innerHTML = replies.length ? replies.map(renderReply).join('') : '<p class="muted-line">No focused responses yet.</p>';
        } catch (error) {
            threadReplies.innerHTML = `<p class="muted-line">${escapeHtml(error.message)}</p>`;
        }
    }

    function closeThread() {
        threadPanel.classList.remove('open');
        state.activePostId = null;
        responseInput.value = '';
    }

    function publishResponse() {
        if (!state.activePostId || !state.ws || state.ws.readyState !== WebSocket.OPEN) return;
        state.ws.send(JSON.stringify({
            action: 'send_thread_reply',
            parent_message_id: state.activePostId,
            user_name: state.memberName,
            content: responseInput.value.trim(),
        }));
        responseInput.value = '';
    }

    
    async function toggleReaction(postId, reactionType) {
        if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
        state.ws.send(JSON.stringify({
            action: 'toggle_reaction',
            message_id: postId,
            reaction_type: reactionType,
            user_id: state.session?.user?.id
        }));
        try {
            await fetch(`/api/community/messages/${postId}/reactions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${state.session.access_token}`
                },
                body: JSON.stringify({ reaction_type: reactionType })
            });
        } catch (e) { console.error("Reaction API failed", e); }
    }

    function starPost(postId) {
        if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
        state.ws.send(JSON.stringify({ action: 'star_message', message_id: postId }));
    }

    function connectWebSocket(channelSlug, onOpen) {
        closeSocket();
        const channel = getChannel(channelSlug);
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const token = encodeURIComponent(state.session.access_token);
        state.ws = new WebSocket(`${protocol}//${window.location.host}/api/community/ws/${encodeURIComponent(channel.apiName)}?token=${token}`);

        state.ws.onopen = () => {
            if (onOpen) onOpen();
        };
        state.ws.onmessage = (event) => {
            const payload = JSON.parse(event.data);
            if (payload.type === 'new_message') {
                const post = normalizePost(payload.data, channel);
                state.posts.push(post);
                renderPosts();
                document.getElementById(`post-${post.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            if (payload.type === 'message_starred') {
                const post = state.posts.find((item) => item.id === payload.message_id);
                if (post) post.stars += 1;
                renderPosts();
            }
            if (payload.type === 'new_thread_reply' && payload.data.parent_message_id === state.activePostId) {
                const empty = threadReplies.querySelector('.muted-line');
                if (empty) threadReplies.innerHTML = '';
                threadReplies.insertAdjacentHTML('beforeend', renderReply(payload.data));
            }
        };
        state.ws.onerror = () => showFlash('Astro Community connection error.', 'error');
    }

    function closeSocket() {
        if (state.ws) state.ws.close();
        state.ws = null;
    }

    async function apiGet(endpoint) {
        const response = await fetch(endpoint, {
            headers: { Authorization: `Bearer ${state.session.access_token}` },
        });
        const data = await response.json();
        if (!response.ok) throw new Error(formatApiError(data.detail));
        return data;
    }

    function renderView(view) {
        const titles = {
            home: 'Home Feed',
            channels: 'Channels',
            charts: 'Chart Discussions',
            astrologers: 'Astrologers',
            notifications: 'Notifications',
            profile: 'Profile',
        };
        document.getElementById('workspace-title').textContent = titles[view] || 'Home Feed';
        if (view === 'charts') {
            const charts = state.channels.find((channel) => channel.slug === 'chart-discussions');
            if (charts) {
                state.currentChannel = charts.slug;
                channelFilter.value = charts.slug;
                loadPosts(charts.slug);
                connectWebSocket(charts.slug);
            }
        }
    }

    function normalizeChannels(rows) {
        const fallback = [
            ['General Discussion', 'general-discussion', 'Professional discussions across astrology practice.', 'G'],
            ['Vedic Astrology', 'vedic-astrology', 'Classical Vedic principles, yogas, and timing.', 'V'],
            ['Prashna Astrology', 'prashna-astrology', 'Question charts, intent, timing, and judgment.', 'P'],
            ['KP Astrology', 'kp-astrology', 'KP significators, ruling planets, and cuspal analysis.', 'K'],
            ['Chart Discussions', 'chart-discussions', 'Case-based chart interpretation posts.', 'C'],
            ['Techniques & Learning', 'techniques-learning', 'Methods, books, learning notes, and debates.', 'T'],
        ];

        const source = rows?.length
            ? rows.map((row) => [row.name, slugify(row.name), row.description || channelDescription(row.name), row.icon || row.name.charAt(0)])
            : [];
        const merged = [...source];
        fallback.forEach((channel) => {
            if (!merged.some((item) => item[1] === channel[1])) merged.push(channel);
        });

        return merged.map(([name, slug, description, icon]) => ({
            name,
            slug,
            apiName: name,
            description,
            icon,
        }));
    }

    function normalizePost(row, channel) {
        const parts = String(row.content || '').split('\n');
        const first = parts[0]?.startsWith('# ') ? parts.shift().replace('# ', '').trim() : 'Professional Discussion';
        return {
            id: row.id,
            title: first,
            body: parts.join('\n').trim() || row.content || '',
            author: row.user_name || 'Astrologer',
            channelName: channel.name,
            channelSlug: channel.slug,
            createdAt: row.created_at,
            image: row.image_base64,
            stars: Number(row.stars || 0),
        };
    }

    function getChannel(slug) {
        return state.channels.find((channel) => channel.slug === slug) || state.channels[0];
    }

    function renderReply(reply) {
        return `
            <article class="thread-reply">
                <strong>${escapeHtml(reply.user_name || 'Astrologer')}</strong>
                <div>${renderMarkdown(reply.content || '')}</div>
                <time>${formatTime(reply.created_at)}</time>
            </article>
        `;
    }

    function renderMarkdown(value) {
        if (window.marked) return sanitizeHtml(window.marked.parse(value || ''));
        return `<p>${escapeHtml(value || '')}</p>`;
    }

    function sanitizeHtml(html) {
        const template = document.createElement('template');
        template.innerHTML = html;
        template.content.querySelectorAll('script, style, iframe, object, embed').forEach((node) => node.remove());
        template.content.querySelectorAll('*').forEach((node) => {
            [...node.attributes].forEach((attr) => {
                const name = attr.name.toLowerCase();
                const value = attr.value.trim().toLowerCase();
                if (name.startsWith('on') || value.startsWith('javascript:')) {
                    node.removeAttribute(attr.name);
                }
            });
        });
        return template.innerHTML;
    }

    function channelDescription(name) {
        const map = {
            general: 'Professional discussions across astrology practice.',
            vedic: 'Classical Vedic principles, yogas, and timing.',
            prashna: 'Question charts, intent, timing, and judgment.',
            kp: 'KP significators, ruling planets, and cuspal analysis.',
            chart: 'Case-based chart interpretation posts.',
            techniques: 'Methods, books, learning notes, and debates.',
        };
        const key = Object.keys(map).find((item) => name.toLowerCase().includes(item));
        return map[key] || 'Permanent channel for professional posts.';
    }

    function slugify(value) {
        return String(value || '')
            .toLowerCase()
            .replace(/&/g, 'and')
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-|-$/g, '') || 'general-discussion';
    }

    function formatTime(value) {
        if (!value) return '';
        return new Date(value).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    }

    function formatApiError(detail) {
        if (!detail) return 'Unable to load Astro Community.';
        if (typeof detail === 'string') return detail;
        return detail.message || detail.msg || JSON.stringify(detail);
    }

    function escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"']/g, (char) => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
        })[char]);
    }

    function escapeAttr(value) {
        return escapeHtml(value);
    }
});


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
            html += `
                <div class="member-card" style="border: 1px solid var(--community-border); padding: 16px; border-radius: 8px; cursor: pointer;" onclick="viewMemberProfile('${m.user_id}')">
                    <h3 style="margin-top: 0; margin-bottom: 4px;">${escapeAttr(m.display_name)}</h3>
                    <p style="color: var(--community-muted); font-size: 0.9rem; margin-top: 0;">@${escapeAttr(m.username)}</p>
                    <p style="font-size: 0.85rem; margin-bottom: 0;">${m.systems_practiced ? m.systems_practiced.join(', ') : ''}</p>
                </div>
            `;
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
        const p = await apiGet(`/api/community/members/${userId}`);
        contextContent.innerHTML = `
            <div style="padding: 16px 0;">
                <h3 style="margin: 0 0 4px 0;">${escapeAttr(p.display_name)}</h3>
                <p style="color: var(--community-muted); margin: 0 0 16px 0;">@${escapeAttr(p.username)}</p>
                <p><strong>Bio:</strong><br>${escapeAttr(p.bio || 'No bio provided.')}</p>
                <p><strong>Systems:</strong><br>${p.systems_practiced ? p.systems_practiced.join(', ') : '-'}</p>
                <p><strong>Experience:</strong><br>${escapeAttr(p.experience_years || '-')}</p>
                <p><strong>Location:</strong><br>${escapeAttr(p.state || '')}, ${escapeAttr(p.country || '')}</p>
            </div>
        `;
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
            html += `
                <div class="notif-item ${n.is_read ? 'read' : 'unread'}" style="padding: 12px; border-bottom: 1px solid var(--community-border); ${n.is_read ? '' : 'background: rgba(142, 68, 173, 0.1);'}">
                    <p style="margin: 0; font-size: 0.95rem;">
                        <strong>${n.type}</strong> ${n.type === 'REACTION' ? 'on your post' : 'on a thread you follow'}
                    </p>
                    <span style="font-size: 0.8rem; color: var(--community-muted);">${new Date(n.created_at).toLocaleString()}</span>
                </div>
            `;
        });
        
        html += '</div>';
        postsFeed.innerHTML = html;
        
        // Mark read
        await fetch('/api/community/notifications/read', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${state.session.access_token}` }
        });
        
    } catch (e) {
        postsFeed.innerHTML = '<p>Error loading notifications.</p>';
    }
});
