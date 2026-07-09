const fs = require('fs');
let code = fs.readFileSync('frontend/index.html', 'utf8');

code = code.replace(
    '<h2 id="chart-title">Chart</h2>',
    '<div style="display: flex; justify-content: space-between; align-items: center; width: 100%;"><h2 id="chart-title">Chart</h2><button type="button" id="btn-share-community" class="secondary-action small hidden">Share to Community</button></div>'
);

fs.writeFileSync('frontend/index.html', code);
console.log('patched index.html');
