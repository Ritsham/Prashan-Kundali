import { getSupabase } from './auth-shared.js';

document.addEventListener('DOMContentLoaded', () => {
    const state = {
        supabase: null,
        session: null,
        channels: [],
        posts: [],
        currentChannel: 'general-discussion',
        ws: null,
        wsChannel: null,
        selectedImageBase64: null,
        activePostId: null,
        oldestCursor: null,
        hasMorePosts: true,
        memberName: 'Astrologer',
        memberRole: 'verified_astrologer',
        savedPosts: new Set(JSON.parse(localStorage.getItem('community_saved_posts') || '[]')),
        currentView: 'home',
        realtimeAvailable: false,
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
    const contextPanel = document.getElementById('context-panel');
    const contextEyebrow = document.getElementById('context-eyebrow');
    const contextTitle = document.getElementById('context-title');
    const contextContent = document.getElementById('context-content');
    const sidebarChannelList = document.getElementById('sidebar-channel-list');
    const sidebarMember = document.getElementById('sidebar-member');
    const workspaceSubtitle = document.getElementById('workspace-subtitle');
    const communitySearch = document.getElementById('community-search');

    init();

    async function init() {
        bindWorkspace();
        landing.classList.add('hidden');
        showStatus('Checking verified community access...');
        state.supabase = await getSupabase();

        const savedToken = localStorage.getItem('supabase_token');

        // Get token from Supabase SDK session. Saved token wins on refresh because it is
        // available before the SDK always finishes restoring browser state.
        const { data } = await state.supabase.auth.getSession();
        state.session = savedToken
            ? { ...(data.session || {}), access_token: savedToken, user: data.session?.user || { user_metadata: {} } }
            : data.session;

        if (state.session?.access_token) {
            await loadCommunity();
        } else {
            showLanding('Please sign in on the main app first, then return here.');
        }
    }


    function bindWorkspace() {
        document.getElementById('open-composer')?.addEventListener('click', openComposer);
        document.getElementById('close-composer')?.addEventListener('click', closeComposer);
        document.getElementById('cancel-composer')?.addEventListener('click', closeComposer);
        document.getElementById('refresh-community')?.addEventListener('click', () => loadPosts(state.currentChannel));
        document.getElementById('close-thread')?.addEventListener('click', closeThread);
        document.getElementById('close-context')?.addEventListener('click', closeContextPanel);
        document.getElementById('nav-members')?.addEventListener('click', renderMembersDirectory);
        document.getElementById('nav-notifications')?.addEventListener('click', renderNotifications);
        document.getElementById('btn-open-members')?.addEventListener('click', renderMembersDirectory);
        document.getElementById('btn-open-pins')?.addEventListener('click', renderSavedPosts);
        document.getElementById('btn-open-info')?.addEventListener('click', renderChannelInfo);
        document.querySelector('.sidebar-foot [data-view="profile"]')?.addEventListener('click', renderProfileSettings);
        document.getElementById('clear-post-image')?.addEventListener('click', clearImage);

        channelFilter?.addEventListener('change', () => {
            selectChannel(channelFilter.value);
        });

        postImage?.addEventListener('change', () => {
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

        postForm?.addEventListener('submit', (event) => {
            event.preventDefault();
            publishPost();
        });

        communitySearch?.addEventListener('input', () => renderSearchResults(communitySearch.value));

        responseForm?.addEventListener('submit', (event) => {
            event.preventDefault();
            publishResponse();
        });

        postsFeed?.addEventListener('click', async (event) => {
            const action = event.target.closest('[data-post-action]');
            if (!action) {
                if (event.target.classList.contains('author')) {
                    const postEl = event.target.closest('.post-item');
                    const postId = postEl?.dataset.postId;
                    const post = state.posts.find((item) => item.id === postId);
                    if (post?.userId) viewMemberProfile(post.userId);
                }
                return;
            }
            const postId = action.dataset.postId;
            if (action.dataset.postAction === 'thread') openThread(postId);
            if (action.dataset.postAction === 'reaction') toggleReaction(postId, action.dataset.reactionType);
            if (action.dataset.postAction === 'save') toggleSavedPost(postId);
        
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


    async function loadCommunity() {
        try {
            showStatus('Loading Astro Community...');
            const token = state.session.access_token;

            const resp = await fetch('/api/community/profile', {
                headers: { 'Authorization': 'Bearer ' + token }
            });

            if (resp.status === 401) {
                showLanding('Your session has expired. Please sign in again on the main app.');
                return;
            }
            if (resp.status === 403) {
                showLanding('Astro Community is available only to approved astrologers. Apply to join or check your application status.');
                return;
            }
            if (!resp.ok) {
                showLanding('Unable to connect to community. Please try again.');
                return;
            }

            const commProfile = await resp.json();
            if (!commProfile || !commProfile.community_access) {
                showLanding('Astro Community is available only to approved astrologers.');
                return;
            }

            state.memberName = commProfile.display_name ||
                state.session?.user?.user_metadata?.full_name ||
                state.session?.user?.email?.split('@')[0] ||
                'Astrologer';
            state.memberRole = commProfile.role || 'verified_astrologer';
            renderMemberSummary();
            await finalizeCommunityLoad();
        } catch (err) {
            console.error('loadCommunity error:', err);
            showLanding('Unable to load community. Please refresh and try again.');
        }
    }

    async function finalizeCommunityLoad() {
        const token = state.session.access_token;
        const channels = await fetch('/api/community/channels', {
            headers: { 'Authorization': 'Bearer ' + token }
        }).then(r => r.json()).catch(() => []);
        state.channels = normalizeChannels(channels);
        if (!state.channels.length) {
            // Use fallback channels if API returns empty
            state.channels = normalizeChannels([]);
        }
        const savedChannel = localStorage.getItem('community_current_channel');
        state.currentChannel = getChannel(savedChannel)?.slug || state.channels[0].slug;
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
        const { data, error } = await state.supabase
            .from('users')
            .select('full_name, role, verification_status, community_access')
            .eq('id', state.session.user.id)
            .single();
            
        if (error) {
            console.error("Supabase user profile fetch error:", error);
            throw new Error(error.message);
        }
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
        renderMemberSummary();
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
        renderSidebarChannels();
        updateWorkspaceHeader();
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
                selectChannel(button.dataset.channel);
            });
        });
    }

    function renderSidebarChannels() {
        if (!sidebarChannelList) return;
        sidebarChannelList.innerHTML = state.channels.map((channel) => `
            <li>
                <button type="button" class="${channel.slug === state.currentChannel ? 'active' : ''}" data-sidebar-channel="${escapeAttr(channel.slug)}">
                    <span># ${escapeHtml(channel.name)}</span>
                    <small>${channel.slug === state.currentChannel ? 'live' : ''}</small>
                </button>
            </li>
        `).join('');
        sidebarChannelList.querySelectorAll('[data-sidebar-channel]').forEach((button) => {
            button.addEventListener('click', () => selectChannel(button.dataset.sidebarChannel));
        });
    }

    function selectChannel(slug) {
        const channel = getChannel(slug);
        if (!channel) return;
        state.currentChannel = channel.slug;
        state.currentView = 'home';
        localStorage.setItem('community_current_channel', channel.slug);
        channelFilter.value = channel.slug;
        postChannel.value = channel.slug;
        updateWorkspaceHeader();
        renderChannelOverview();
        renderSidebarChannels();
        loadPosts(channel.slug);
        connectWebSocket(channel.slug);
        setActiveNav('home');
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
                        <h3>${escapeHtml(post.title)}</h3>
                        <div>${renderMarkdown(post.body)}</div>
                        ${post.chartId ? `<a href="/${post.contentType === 'PRASHNA_CASE' ? 'prashna' : 'lagna'}?id=${post.chartId}" target="_blank" style="color: var(--primary-accent); text-decoration: underline; font-size: 0.9rem;">View Chart Details ↗</a>` : ''}
                    </div>
                `;
            } else {
                contentHtml = `
                    <h3>${escapeHtml(post.title)}</h3>
                    <div>${renderMarkdown(post.body)}</div>
                    ${post.imageBase64 ? `<img src="${post.imageBase64}" alt="User uploaded image" />` : ''}
                `;
            }

            return `
            <article class="post-item discussion-post" id="post-${escapeAttr(post.id)}" data-post-id="${escapeAttr(post.id)}">
                <header>
                    <div class="post-meta">
                        <span class="author" title="${escapeAttr(post.userName)}">${escapeHtml(post.userName)}</span>
                        <span class="role-badge">Verified</span>
                        <span class="time">${new Date(post.createdAt).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                    </div>
                    <span class="channel-pill">${escapeHtml(post.channelName)}</span>
                </header>
                <div class="post-content">
                    ${contentHtml}
                </div>
                <footer>
                    <button type="button" data-post-action="thread" data-post-id="${escapeAttr(post.id)}">Open Responses</button>
                    <button type="button" data-post-action="reaction" data-reaction-type="Helpful" data-post-id="${escapeAttr(post.id)}">🙏 Helpful</button>
                    <button type="button" data-post-action="reaction" data-reaction-type="Insightful" data-post-id="${escapeAttr(post.id)}">💡 Insightful</button>
                    <button type="button" data-post-action="save" data-post-id="${escapeAttr(post.id)}">${state.savedPosts.has(post.id) ? 'Saved' : 'Save'}</button>
                    <button type="button" data-post-action="report" data-post-id="${escapeAttr(post.id)}" style="color: var(--community-muted);">🚩 Report</button>
                </footer>
            </article>`;
}).join('');
        postsFeed.innerHTML = html;
        document.getElementById('btn-load-older')?.addEventListener('click', loadOlderPosts);
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
            sendPost(channel, body, image);
        } else {
            sendPost(channel, body, image);
        }
        closeComposer();
    }

    async function sendPost(channel, content, image) {
        if (state.ws?.readyState === WebSocket.OPEN && state.wsChannel === channel.slug) {
            state.ws.send(JSON.stringify({
                action: 'send_message',
                user_name: state.memberName,
                content,
                image_base64: image,
            }));
            return;
        }
        try {
            const response = await fetch(`/api/community/messages/${encodeURIComponent(channel.apiName)}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${state.session.access_token}`,
                },
                body: JSON.stringify({ content, image_base64: image }),
            });
            const result = await response.json();
            if (!response.ok) throw new Error(formatApiError(result.detail));
            const saved = result.message || result;
            state.posts.push(normalizePost(saved, channel));
            renderPosts();
        } catch (error) {
            showStatus(error.message || 'Unable to publish post.');
        }
    }

    async function openThread(postId) {
        const post = state.posts.find((item) => item.id === postId);
        if (!post) return;
        state.activePostId = postId;
        openContextPanel('Thread', 'Responses', `
            <div class="thread-original">
                <span class="channel-pill">${escapeHtml(post.channelName)}</span>
                <h3>${escapeHtml(post.title)}</h3>
                <div>${renderMarkdown(post.body)}</div>
            </div>
            <div id="context-thread-replies"><p class="muted-line">Loading responses...</p></div>
            <form id="context-response-form" class="thread-response-form">
                <textarea id="context-response-input" rows="4" placeholder="Write a focused response..."></textarea>
                <button type="submit" class="primary-action small">Reply</button>
            </form>
        `);
        const activeReplies = threadReplies || document.getElementById('context-thread-replies');
        const activeResponseForm = responseForm || document.getElementById('context-response-form');
        const activeResponseInput = responseInput || document.getElementById('context-response-input');
        activeResponseForm?.addEventListener('submit', (event) => {
            event.preventDefault();
            publishResponse(activeResponseInput);
        });

        try {
            const replies = await apiGet(`/api/community/threads/${encodeURIComponent(postId)}`);
            activeReplies.innerHTML = replies.length ? replies.map(renderReply).join('') : '<p class="muted-line">No focused responses yet.</p>';
        } catch (error) {
            activeReplies.innerHTML = `<p class="muted-line">${escapeHtml(error.message)}</p>`;
        }
    }

    function closeThread() {
        threadPanel?.classList.remove('open');
        state.activePostId = null;
        if (responseInput) responseInput.value = '';
    }

    function publishResponse(inputEl = responseInput) {
        if (!state.activePostId || !state.ws || state.ws.readyState !== WebSocket.OPEN) return;
        const content = inputEl?.value?.trim();
        if (!content) return;
        state.ws.send(JSON.stringify({
            action: 'send_thread_reply',
            parent_message_id: state.activePostId,
            user_name: state.memberName,
            content,
        }));
        inputEl.value = '';
    }

    
    async function toggleReaction(postId, reactionType) {
        if (state.ws?.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({
                action: 'toggle_reaction',
                message_id: postId,
                reaction_type: reactionType,
                user_id: state.session?.user?.id
            }));
        }
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
        state.wsChannel = channel.slug;
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const token = encodeURIComponent(state.session.access_token);
        state.ws = new WebSocket(`${protocol}//${window.location.host}/api/community/ws/${encodeURIComponent(channel.apiName)}?token=${token}`);

        state.ws.onopen = () => {
            state.realtimeAvailable = true;
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
                const activeReplies = threadReplies || document.getElementById('context-thread-replies');
                const empty = activeReplies?.querySelector('.muted-line');
                if (empty) activeReplies.innerHTML = '';
                activeReplies?.insertAdjacentHTML('beforeend', renderReply(payload.data));
            }
        };
        state.ws.onerror = () => {
            state.realtimeAvailable = false;
        };
        state.ws.onclose = () => {
            state.realtimeAvailable = false;
            state.wsChannel = null;
        };
    }

    function closeSocket() {
        if (state.ws) state.ws.close();
        state.ws = null;
        state.wsChannel = null;
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
        state.currentView = view || 'home';
        setActiveNav(state.currentView);
        const titles = {
            home: 'Home Feed',
            channels: 'Channels',
            charts: 'Chart Discussions',
            astrologers: 'Astrologers',
            notifications: 'Notifications',
            saved: 'Saved Posts',
            dms: 'Direct Messages',
            profile: 'Profile',
        };
        document.getElementById('workspace-title').textContent = titles[view] || 'Home Feed';
        updateWorkspaceHeader();
        if (view === 'home' || view === 'channels') {
            renderChannelOverview();
            renderPosts();
            return;
        }
        if (view === 'saved') {
            renderSavedPosts();
            return;
        }
        if (view === 'dms') {
            renderDirectMessages();
            return;
        }
        if (view === 'profile') {
            renderProfileSettings();
            return;
        }
        if (view === 'astrologers') {
            renderMembersDirectory();
            return;
        }
        if (view === 'notifications') {
            renderNotifications();
            return;
        }
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

    function setActiveNav(view) {
        document.querySelectorAll('[data-view]').forEach((button) => {
            button.classList.toggle('active', button.dataset.view === view);
        });
    }

    function updateWorkspaceHeader() {
        const channel = getChannel(state.currentChannel);
        const title = document.getElementById('workspace-title');
        if (state.currentView === 'home' || state.currentView === 'channels') {
            title.textContent = state.currentView === 'channels' ? 'Channels' : 'Home Feed';
            if (workspaceSubtitle) {
                workspaceSubtitle.textContent = channel
                    ? `#${channel.name} · ${channel.description}`
                    : 'Professional discussions across verified astrologers.';
            }
            return;
        }
        if (workspaceSubtitle) {
            workspaceSubtitle.textContent = 'Search, saved posts, members, and professional updates.';
        }
    }

    function renderMemberSummary() {
        if (!sidebarMember) return;
        const initial = (state.memberName || 'A').charAt(0).toUpperCase();
        sidebarMember.innerHTML = `
            <span class="member-avatar">${escapeHtml(initial)}</span>
            <div>
                <strong>${escapeHtml(state.memberName)}</strong>
                <small>${escapeHtml(formatRole(state.memberRole))}</small>
            </div>
        `;
    }

    function renderSearchResults(query) {
        const term = query.trim().toLowerCase();
        if (!term) {
            if (state.currentView === 'search') {
                state.currentView = 'home';
                updateWorkspaceHeader();
                renderPosts();
            }
            return;
        }
        state.currentView = 'search';
        document.getElementById('workspace-title').textContent = 'Search';
        if (workspaceSubtitle) workspaceSubtitle.textContent = `Results for "${query.trim()}"`;
        const matchingChannels = state.channels.filter((channel) =>
            [channel.name, channel.description, channel.slug].some((value) => String(value || '').toLowerCase().includes(term))
        );
        const matchingPosts = state.posts.filter((post) =>
            [post.title, post.body, post.userName, post.channelName].some((value) => String(value || '').toLowerCase().includes(term))
        );
        postsFeed.innerHTML = `
            <div class="search-results">
                <h2>Channels</h2>
                ${matchingChannels.length ? matchingChannels.map((channel) => `
                    <button type="button" class="search-result-row" data-search-channel="${escapeAttr(channel.slug)}">
                        <strong># ${escapeHtml(channel.name)}</strong>
                        <span>${escapeHtml(channel.description)}</span>
                    </button>
                `).join('') : '<p class="muted-line">No matching channels.</p>'}
                <h2>Posts</h2>
                ${matchingPosts.length ? matchingPosts.map((post) => `
                    <button type="button" class="search-result-row" data-search-post="${escapeAttr(post.id)}">
                        <strong>${escapeHtml(post.title)}</strong>
                        <span>${escapeHtml(post.channelName)} · ${escapeHtml(post.userName)}</span>
                    </button>
                `).join('') : '<p class="muted-line">No matching posts loaded in this channel.</p>'}
            </div>
        `;
        postsFeed.querySelectorAll('[data-search-channel]').forEach((button) => {
            button.addEventListener('click', () => {
                communitySearch.value = '';
                selectChannel(button.dataset.searchChannel);
            });
        });
        postsFeed.querySelectorAll('[data-search-post]').forEach((button) => {
            button.addEventListener('click', () => {
                communitySearch.value = '';
                state.currentView = 'home';
                updateWorkspaceHeader();
                renderPosts();
                document.getElementById(`post-${button.dataset.searchPost}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            });
        });
    }

    function toggleSavedPost(postId) {
        if (state.savedPosts.has(postId)) {
            state.savedPosts.delete(postId);
        } else {
            state.savedPosts.add(postId);
        }
        localStorage.setItem('community_saved_posts', JSON.stringify([...state.savedPosts]));
        if (state.currentView === 'saved') {
            renderSavedPosts();
        } else {
            renderPosts();
        }
    }

    function renderSavedPosts(event) {
        event?.preventDefault();
        state.currentView = 'saved';
        setActiveNav('saved');
        document.getElementById('workspace-title').textContent = 'Saved Posts';
        if (workspaceSubtitle) workspaceSubtitle.textContent = 'Posts you marked for later reference.';
        const saved = state.posts.filter((post) => state.savedPosts.has(post.id));
        if (!saved.length) {
            postsFeed.innerHTML = `
                <div class="empty-feed">
                    <h2>No saved posts yet</h2>
                    <p>Use Save on important discussions to build your personal reference list.</p>
                </div>
            `;
            return;
        }
        const currentPosts = state.posts;
        state.posts = saved;
        renderPosts();
        state.posts = currentPosts;
    }

    function renderDirectMessages() {
        state.currentView = 'dms';
        setActiveNav('dms');
        document.getElementById('workspace-title').textContent = 'Direct Messages';
        if (workspaceSubtitle) workspaceSubtitle.textContent = 'Start focused one-to-one conversations with verified members.';
        postsFeed.innerHTML = `
            <div class="empty-feed">
                <h2>Direct messages are ready for member selection</h2>
                <p>Open Members, choose an astrologer profile, and continue from there as the DM backend is connected.</p>
                <button type="button" class="primary-action small" id="empty-members">Open Members</button>
            </div>
        `;
        document.getElementById('empty-members')?.addEventListener('click', renderMembersDirectory);
    }

    function renderProfileSettings(event) {
        event?.preventDefault();
        state.currentView = 'profile';
        setActiveNav('profile');
        document.getElementById('workspace-title').textContent = 'Profile';
        if (workspaceSubtitle) workspaceSubtitle.textContent = 'Your verified community identity and workspace preferences.';
        postsFeed.innerHTML = `
            <div class="empty-feed profile-settings-card">
                <h2>${escapeHtml(state.memberName)}</h2>
                <p>${escapeHtml(formatRole(state.memberRole))}</p>
                <div class="profile-settings-grid">
                    <span>Access</span><strong>Verified</strong>
                    <span>Last channel</span><strong># ${escapeHtml(getChannel(state.currentChannel)?.name || 'General')}</strong>
                    <span>Saved posts</span><strong>${state.savedPosts.size}</strong>
                </div>
                <button type="button" class="secondary-action small" id="profile-open-info">Open Channel Info</button>
            </div>
        `;
        document.getElementById('profile-open-info')?.addEventListener('click', renderChannelInfo);
    }

    function renderChannelInfo() {
        const channel = getChannel(state.currentChannel);
        openContextPanel('Channel Info', 'Details', `
            <div class="channel-info-panel">
                <span class="channel-pill"># ${escapeHtml(channel.name)}</span>
                <p>${escapeHtml(channel.description)}</p>
                <dl>
                    <dt>Access</dt>
                    <dd>Verified astrologers and approved community members</dd>
                    <dt>Posting</dt>
                    <dd>Discussions, chart context, threads, reactions, and reports</dd>
                    <dt>Moderation</dt>
                    <dd>Admins and moderators can review reports and remove low-quality content</dd>
                </dl>
            </div>
        `);
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
            content: row.content || '',
            body: parts.join('\n').trim() || row.content || '',
            userName: row.user_name || 'Astrologer',
            userId: row.user_id || row.author_id || '',
            channelName: channel.name,
            channelSlug: channel.slug,
            createdAt: row.created_at,
            imageBase64: row.image_base64,
            contentType: row.content_type || 'STANDARD',
            chartId: row.chart_id,
            stars: Number(row.stars || 0),
        };
    }

    async function renderMembersDirectory(event) {
        event?.preventDefault();
        setActiveNav('astrologers');
        closeThread();
        document.getElementById('workspace-title').textContent = 'Members';
        postsFeed.innerHTML = '<p class="muted-line">Loading members...</p>';
        try {
            const members = await apiGet('/api/community/members');
            postsFeed.innerHTML = members.length ? `
                <div class="members-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px;">
                    ${members.map((member) => `
                        <button type="button" class="member-card" data-member-id="${escapeAttr(member.user_id)}" style="text-align: left; border: 1px solid var(--community-border); padding: 16px; border-radius: 8px; cursor: pointer; background: var(--community-card);">
                            <h3 style="margin-top: 0; margin-bottom: 4px;">${escapeHtml(member.display_name || 'Astrologer')}</h3>
                            <p style="color: var(--community-muted); font-size: 0.9rem; margin-top: 0;">@${escapeHtml(member.username || 'member')}</p>
                            <p style="font-size: 0.85rem; margin-bottom: 0;">${escapeHtml(Array.isArray(member.systems_practiced) ? member.systems_practiced.join(', ') : '')}</p>
                        </button>
                    `).join('')}
                </div>
            ` : '<p class="muted-line">No community members found yet.</p>';
            postsFeed.querySelectorAll('[data-member-id]').forEach((button) => {
                button.addEventListener('click', () => viewMemberProfile(button.dataset.memberId));
            });
        } catch (error) {
            postsFeed.innerHTML = `<p class="muted-line">${escapeHtml(error.message)}</p>`;
        }
    }

    async function viewMemberProfile(userId) {
        if (!userId) return;
        openContextPanel('Profile', 'Astrologer Details', '<p class="muted-line">Loading profile...</p>');
        try {
            const profile = await apiGet(`/api/community/members/${encodeURIComponent(userId)}`);
            openContextPanel('Profile', 'Astrologer Details', `
                <div style="padding: 16px 0;">
                    <h3 style="margin: 0 0 4px 0;">${escapeHtml(profile.display_name || 'Astrologer')}</h3>
                    <p style="color: var(--community-muted); margin: 0 0 16px 0;">@${escapeHtml(profile.username || 'member')}</p>
                    <p><strong>Bio:</strong><br>${escapeHtml(profile.bio || 'No bio provided.')}</p>
                    <p><strong>Systems:</strong><br>${escapeHtml(Array.isArray(profile.systems_practiced) ? profile.systems_practiced.join(', ') : '-')}</p>
                    <p><strong>Experience:</strong><br>${escapeHtml(profile.experience_years || '-')}</p>
                    <p><strong>Location:</strong><br>${escapeHtml([profile.state, profile.country].filter(Boolean).join(', ') || '-')}</p>
                </div>
            `);
        } catch (error) {
            openContextPanel('Profile', 'Astrologer Details', `<p class="muted-line">${escapeHtml(error.message)}</p>`);
        }
    }

    async function renderNotifications(event) {
        event?.preventDefault();
        setActiveNav('notifications');
        closeThread();
        document.getElementById('workspace-title').textContent = 'Notifications';
        postsFeed.innerHTML = '<p class="muted-line">Loading notifications...</p>';
        try {
            const notifications = await apiGet('/api/community/notifications');
            postsFeed.innerHTML = notifications.length ? `
                <div class="notifications-list">
                    ${notifications.map((notification) => `
                        <div class="notif-item ${notification.is_read ? 'read' : 'unread'}" style="padding: 12px; border-bottom: 1px solid var(--community-border); ${notification.is_read ? '' : 'background: rgba(142, 68, 173, 0.1);'}">
                            <p style="margin: 0; font-size: 0.95rem;">
                                <strong>${escapeHtml(notification.type || 'Notification')}</strong>
                                ${notification.type === 'REACTION' ? 'on your post' : 'in the community'}
                            </p>
                            <span style="font-size: 0.8rem; color: var(--community-muted);">${formatTime(notification.created_at)}</span>
                        </div>
                    `).join('')}
                </div>
            ` : '<p class="muted-line">No new notifications.</p>';
            await fetch('/api/community/notifications/read', {
                method: 'POST',
                headers: { Authorization: `Bearer ${state.session.access_token}` },
            });
        } catch (error) {
            postsFeed.innerHTML = `<p class="muted-line">${escapeHtml(error.message)}</p>`;
        }
    }

    function openContextPanel(eyebrow, title, html) {
        if (contextEyebrow) contextEyebrow.textContent = eyebrow;
        if (contextTitle) contextTitle.textContent = title;
        if (contextContent) contextContent.innerHTML = html;
        contextPanel?.classList.add('open');
    }

    function closeContextPanel() {
        contextPanel?.classList.remove('open');
        if (state.activePostId) closeThread();
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

    function formatRole(value) {
        return String(value || 'verified_astrologer')
            .replace(/_/g, ' ')
            .replace(/\b\w/g, (char) => char.toUpperCase());
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
