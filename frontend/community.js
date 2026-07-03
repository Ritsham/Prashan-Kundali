document.addEventListener('DOMContentLoaded', () => {
    let currentChannel = 'general';
    let userName = localStorage.getItem('astro_community_name') || 'Anonymous Astrologer';
    let ws = null;
    let selectedImageBase64 = null;
    let currentThreadMessageId = null;

    // DOM Elements
    const channelListEl = document.getElementById('channel-list');
    const messagesContainerEl = document.getElementById('messages-container');
    const currentChannelNameEl = document.getElementById('current-channel-name');
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-input');
    const imageUploadInput = document.getElementById('image-upload');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const imagePreview = document.getElementById('image-preview');
    const clearImageBtn = document.getElementById('clear-image-btn');
    const changeNameBtn = document.getElementById('change-name-btn');
    
    const threadSidebar = document.getElementById('thread-sidebar');
    const closeThreadBtn = document.getElementById('close-thread-btn');
    const threadOriginalMessageEl = document.getElementById('thread-original-message');
    const threadRepliesEl = document.getElementById('thread-replies');
    const threadForm = document.getElementById('thread-form');
    const threadInput = document.getElementById('thread-input');

    // Initialize
    init();

    function init() {
        promptForNameIfNeeded();
        fetchChannels();
        connectWebSocket(currentChannel);
    }

    function promptForNameIfNeeded() {
        if (!localStorage.getItem('astro_community_name')) {
            const name = prompt("Welcome to the Astro Community! Please enter your display name:");
            if (name && name.trim()) {
                userName = name.trim();
                localStorage.setItem('astro_community_name', userName);
            }
        }
    }

    changeNameBtn.addEventListener('click', () => {
        const name = prompt("Enter your new display name:", userName);
        if (name && name.trim()) {
            userName = name.trim();
            localStorage.setItem('astro_community_name', userName);
        }
    });

    async function fetchChannels() {
        try {
            const response = await fetch('/api/community/channels');
            const channels = await response.json();
            renderChannels(channels);
        } catch (error) {
            console.error("Failed to fetch channels:", error);
        }
    }

    function renderChannels(channels) {
        channelListEl.innerHTML = '';
        channels.forEach(channel => {
            const li = document.createElement('li');
            li.className = 'channel-item';
            if (channel.name === currentChannel) {
                li.classList.add('active');
            }
            li.textContent = channel.name;
            li.addEventListener('click', () => switchChannel(channel.name));
            channelListEl.appendChild(li);
        });
    }

    async function switchChannel(newChannel) {
        if (newChannel === currentChannel) return;
        currentChannel = newChannel;
        currentChannelNameEl.textContent = `# ${currentChannel}`;
        
        // Update UI active state
        document.querySelectorAll('.channel-item').forEach(el => {
            if (el.textContent === currentChannel) el.classList.add('active');
            else el.classList.remove('active');
        });

        // Close thread if open
        closeThread();
        
        // Reconnect WS
        connectWebSocket(currentChannel);
    }

    function connectWebSocket(channel) {
        if (ws) {
            ws.close();
        }
        messagesContainerEl.innerHTML = ''; // clear messages

        // Fetch history first
        fetchMessages(channel);

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/community/ws/${encodeURIComponent(channel)}`;
        ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };

        ws.onerror = (error) => {
            console.error('WebSocket Error:', error);
        };
    }

    async function fetchMessages(channel) {
        try {
            const response = await fetch(`/api/community/messages/${encodeURIComponent(channel)}`);
            const messages = await response.json();
            messages.forEach(msg => appendMessage(msg, false));
            scrollToBottom();
        } catch (error) {
            console.error("Failed to fetch messages:", error);
        }
    }

    function handleWebSocketMessage(payload) {
        if (payload.type === 'new_message') {
            appendMessage(payload.data, true);
        } else if (payload.type === 'message_deleted') {
            const msgEl = document.getElementById(`msg-${payload.message_id}`);
            if (msgEl) {
                msgEl.classList.add('deleted');
                msgEl.querySelector('.message-content').textContent = 'This message was deleted.';
                const img = msgEl.querySelector('.message-image');
                if (img) img.remove();
            }
        } else if (payload.type === 'message_starred') {
            const starBtn = document.querySelector(`#msg-${payload.message_id} .action-btn.star`);
            if (starBtn) {
                starBtn.classList.add('starred');
                const countSpan = starBtn.querySelector('.star-count');
                if (countSpan) {
                    countSpan.textContent = parseInt(countSpan.textContent || 0) + 1;
                }
            }
        } else if (payload.type === 'new_thread_reply') {
            if (currentThreadMessageId === payload.data.parent_message_id) {
                appendThreadReply(payload.data);
            }
        }
    }

    function createMessageHTML(msg, isThreadReply = false) {
        const timeString = new Date(msg.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        const isMine = msg.user_name === userName;
        
        let actionsHtml = '';
        if (!isThreadReply && !msg.is_deleted) {
            // Escaping quotes for onclick
            const safeContent = msg.content ? msg.content.replace(/`/g, '\\`').replace(/'/g, "\\'").replace(/"/g, '&quot;') : '';
            actionsHtml = `
                <div class="message-actions">
                    <button class="action-btn reply" onclick="openThread('${msg.id}', '${msg.user_name}', \`${safeContent}\`, '${msg.image_base64 || ''}')" title="Reply in Thread">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                    </button>
                    <button class="action-btn star ${msg.stars > 0 ? 'starred' : ''}" onclick="starMessage('${msg.id}')" title="Star/Like">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
                    </button>
                    <button class="action-btn delete" onclick="deleteMessage('${msg.id}')" title="Delete">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    </button>
                </div>
            `;
        }

        const imageHtml = msg.image_base64 && !msg.is_deleted 
            ? `<img src="${msg.image_base64}" class="message-image" alt="Attached Chart/Image">` 
            : '';

        const contentHtml = msg.is_deleted 
            ? '<em>This message was deleted.</em>' 
            : marked.parse(msg.content || '');

        return `
            <div class="message-row ${isMine ? 'mine' : 'theirs'} ${msg.is_deleted ? 'deleted' : ''}" id="msg-${msg.id}">
                <div class="message-bubble">
                    <span class="message-author">${msg.user_name}</span>
                    <div class="message-content">${contentHtml}</div>
                    ${imageHtml}
                    <div class="message-meta">
                        ${msg.stars > 0 && !msg.is_deleted ? `<span style="color:#F1C40F; font-size:11px; margin-right:4px;">★ ${msg.stars}</span>` : ''}
                        <span class="message-time">${timeString}</span>
                    </div>
                    ${actionsHtml}
                </div>
            </div>
        `;
    }

    function appendMessage(msg, smoothScroll = false) {
        messagesContainerEl.insertAdjacentHTML('beforeend', createMessageHTML(msg));
        if (smoothScroll) {
            scrollToBottom();
        }
    }

    function scrollToBottom() {
        messagesContainerEl.scrollTop = messagesContainerEl.scrollHeight;
    }

    // Input Handling
    imageUploadInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                selectedImageBase64 = e.target.result;
                imagePreview.src = selectedImageBase64;
                imagePreviewContainer.style.display = 'flex';
            };
            reader.readAsDataURL(this.files[0]);
        }
    });

    clearImageBtn.addEventListener('click', () => {
        selectedImageBase64 = null;
        imageUploadInput.value = '';
        imagePreviewContainer.style.display = 'none';
    });

    messageForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const content = messageInput.value.trim();
        if (!content && !selectedImageBase64) return;

        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                action: 'send_message',
                user_name: userName,
                content: content,
                image_base64: selectedImageBase64
            }));
            
            messageInput.value = '';
            clearImageBtn.click();
        }
    });

    // Global Functions for inline onclick handlers
    window.deleteMessage = function(id) {
        if (confirm("Delete this message?")) {
            ws.send(JSON.stringify({
                action: 'delete_message',
                message_id: id
            }));
        }
    }

    window.starMessage = function(id) {
        ws.send(JSON.stringify({
            action: 'star_message',
            message_id: id
        }));
    }

    window.openThread = async function(id, author, content, image) {
        currentThreadMessageId = id;
        
        const timeString = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}); // Approximate for display
        const imageHtml = image ? `<img src="${image}" class="message-image">` : '';
        
        threadOriginalMessageEl.innerHTML = `
            <div class="message-header">
                <span class="message-author">${author}</span>
            </div>
            <div class="message-content">${content}</div>
            ${imageHtml}
        `;
        
        threadSidebar.classList.add('open');
        threadRepliesEl.innerHTML = '';
        
        // Fetch thread replies
        try {
            const response = await fetch(`/api/community/threads/${encodeURIComponent(id)}`);
            const replies = await response.json();
            replies.forEach(reply => appendThreadReply(reply));
        } catch (error) {
            console.error("Failed to fetch threads", error);
        }
    }

    function closeThread() {
        threadSidebar.classList.remove('open');
        currentThreadMessageId = null;
    }
    
    closeThreadBtn.addEventListener('click', closeThread);

    threadForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const content = threadInput.value.trim();
        if (!content || !currentThreadMessageId) return;

        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                action: 'send_thread_reply',
                parent_message_id: currentThreadMessageId,
                user_name: userName,
                content: content
            }));
            threadInput.value = '';
        }
    });

    function appendThreadReply(reply) {
        threadRepliesEl.insertAdjacentHTML('beforeend', createMessageHTML(reply, true));
        threadRepliesEl.scrollTop = threadRepliesEl.scrollHeight;
    }
});
