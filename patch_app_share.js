const fs = require('fs');

// 1. Add Modal HTML
let indexCode = fs.readFileSync('frontend/index.html', 'utf8');
const shareModalHtml = `
    <!-- Share to Community Modal -->
    <div id="share-community-overlay" class="overlay hidden">
        <div class="modal">
            <header>
                <h2>Share to Community</h2>
                <button type="button" class="icon-btn close-btn" onclick="document.getElementById('share-community-overlay').classList.add('hidden')">&times;</button>
            </header>
            <div class="modal-body">
                <div class="form-row">
                    <label>Select Channel</label>
                    <select id="share-channel-select"></select>
                </div>
                <div class="form-row">
                    <label>Add a comment</label>
                    <textarea id="share-comment" rows="3" placeholder="What would you like to discuss about this chart?"></textarea>
                </div>
            </div>
            <footer>
                <button type="button" class="primary-action" id="btn-submit-share">Share Post</button>
            </footer>
        </div>
    </div>
`;
if (!indexCode.includes('share-community-overlay')) {
    indexCode = indexCode.replace('</body>', shareModalHtml + '\n</body>');
    fs.writeFileSync('frontend/index.html', indexCode);
}

// 2. Add Logic to app.js
let appCode = fs.readFileSync('frontend/app.js', 'utf8');
const logic = `
// Share to community logic
let currentShareChart = null;

async function openShareModal() {
    if (!currentShareChart) return;
    
    // Check if user is verified astrologer (just fetch profile, backend enforces)
    try {
        const channels = await apiGet('/api/community/channels');
        const select = document.getElementById('share-channel-select');
        select.innerHTML = channels.map(c => \`<option value="\${c.slug}"># \${c.name}</option>\`).join('');
        document.getElementById('share-community-overlay').classList.remove('hidden');
    } catch (e) {
        alert("You must be an approved Astrologer to share to the community. Please apply first.");
    }
}

document.getElementById('btn-share-community')?.addEventListener('click', openShareModal);

document.getElementById('btn-submit-share')?.addEventListener('click', async () => {
    const channel = document.getElementById('share-channel-select').value;
    const comment = document.getElementById('share-comment').value;
    
    if (!channel || !comment) {
        alert("Please select a channel and add a comment.");
        return;
    }
    
    document.getElementById('btn-submit-share').textContent = 'Sharing...';
    
    try {
        const isLagna = currentShareChart.meta?.chart_type === 'lagna';
        
        // Use a standard API call to post (simulate WS or just standard POST if we add one)
        // Since we only have WS for now, we'll need to create a POST /messages endpoint.
        const res = await fetch(\`/api/community/messages/\${encodeURIComponent(channel)}\`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': \`Bearer \${AppState.session.access_token}\`
            },
            body: JSON.stringify({
                content: comment,
                content_type: isLagna ? 'LAGNA_CASE' : 'PRASHNA_CASE',
                chart_id: currentShareChart.meta?.id || currentShareChart.id || null
            })
        });
        
        if (res.ok) {
            document.getElementById('share-community-overlay').classList.add('hidden');
            document.getElementById('share-comment').value = '';
            alert('Chart shared to community successfully!');
        } else {
            alert('Failed to share.');
        }
    } catch (e) {
        console.error(e);
        alert('Error sharing chart.');
    } finally {
        document.getElementById('btn-submit-share').textContent = 'Share Post';
    }
});
`;

if (!appCode.includes('currentShareChart')) {
    // Inject at the end
    appCode += '\n' + logic;
    
    // Wire currentShareChart in processResult
    appCode = appCode.replace(
        'function processResult(chart) {',
        'function processResult(chart) {\n  currentShareChart = chart;\n  document.getElementById("btn-share-community")?.classList.remove("hidden");'
    );
    
    fs.writeFileSync('frontend/app.js', appCode);
}
console.log('patched share logic');
