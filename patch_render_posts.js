const fs = require('fs');
let code = fs.readFileSync('frontend/community.js', 'utf8');

const normalRender = `            <div class="post-item">
                <header>
                    <div class="post-meta">
                        <span class="author" title="\${escapeAttr(post.userName)}">\${escapeAttr(post.userName)}</span>
                        <span class="time">\${new Date(post.createdAt).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                    </div>
                </header>
                <div class="post-content">
                    <p>\${escapeAttr(post.content)}</p>
                    \${post.imageBase64 ? \`<img src="\${post.imageBase64}" alt="User uploaded image" />\` : ''}
                </div>
                <footer>
                    <button type="button" data-post-action="thread" data-post-id="\${escapeAttr(post.id)}">Open Responses</button>
                    <button type="button" data-post-action="reaction" data-reaction-type="Helpful" data-post-id="\${escapeAttr(post.id)}">🙏 Helpful</button>
                    <button type="button" data-post-action="reaction" data-reaction-type="Insightful" data-post-id="\${escapeAttr(post.id)}">💡 Insightful</button>
                </footer>
            </div>`;

const customRender = `
            let contentHtml = '';
            if (post.contentType === 'PRASHNA_CASE' || post.contentType === 'LAGNA_CASE') {
                contentHtml = \`
                    <div class="chart-discussion-card" style="border: 1px solid var(--primary-accent); border-radius: 8px; padding: 12px; margin-bottom: 8px; background: rgba(142, 68, 173, 0.1);">
                        <div style="font-size: 0.8rem; text-transform: uppercase; color: var(--primary-accent); margin-bottom: 4px;">🪐 \${post.contentType === 'PRASHNA_CASE' ? 'Prashna Chart' : 'Birth Chart'} shared for discussion</div>
                        <p>\${escapeAttr(post.content)}</p>
                        \${post.chartId ? \`<a href="/\${post.contentType === 'PRASHNA_CASE' ? 'prashna' : 'lagna'}?id=\${post.chartId}" target="_blank" style="color: var(--primary-accent); text-decoration: underline; font-size: 0.9rem;">View Chart Details ↗</a>\` : ''}
                    </div>
                \`;
            } else {
                contentHtml = \`
                    <p>\${escapeAttr(post.content)}</p>
                    \${post.imageBase64 ? \`<img src="\${post.imageBase64}" alt="User uploaded image" />\` : ''}
                \`;
            }

            return \`
            <div class="post-item">
                <header>
                    <div class="post-meta">
                        <span class="author" title="\${escapeAttr(post.userName)}">\${escapeAttr(post.userName)}</span>
                        <span class="time">\${new Date(post.createdAt).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                    </div>
                </header>
                <div class="post-content">
                    \${contentHtml}
                </div>
                <footer>
                    <button type="button" data-post-action="thread" data-post-id="\${escapeAttr(post.id)}">Open Responses</button>
                    <button type="button" data-post-action="reaction" data-reaction-type="Helpful" data-post-id="\${escapeAttr(post.id)}">🙏 Helpful</button>
                    <button type="button" data-post-action="reaction" data-reaction-type="Insightful" data-post-id="\${escapeAttr(post.id)}">💡 Insightful</button>
                </footer>
            </div>\`;
`;

// we need to replace the mapping logic inside renderPosts
code = code.replace(
    `postsFeed.innerHTML = html;`,
    `postsFeed.innerHTML = html;`
); // just checking it exists

// let's replace the whole map block in renderPosts
const mapRegex = /html \+= state\.posts\.map\(\(post\) => `[\s\S]*?`\)\.join\(''\);/;
code = code.replace(mapRegex, `html += state.posts.map((post) => {${customRender}}).join('');`);

// Update normalizePost to pass contentType and chartId
code = code.replace(
    `imageBase64: row.image_base64,`,
    `imageBase64: row.image_base64,\n        contentType: row.content_type,\n        chartId: row.chart_id,`
);

fs.writeFileSync('frontend/community.js', code);
console.log('patched renderPosts');
