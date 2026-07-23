#!/usr/bin/env node
/**
 * build.js — Minification build script for frontend_old assets
 * Runs at deploy time. Reads source files from frontend_old/,
 * outputs minified versions back in place (or to a dist/ dir if preferred).
 * Tools used: terser (JS), clean-css-cli (CSS)
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const FRONTEND_DIR = path.join(__dirname, 'frontend_old');
const REACT_FRONTEND_DIR = path.join(__dirname, 'frontend');
const PUBLIC_REACT_DIR = path.join(__dirname, 'public', 'frontend');
const TERSER = 'npx terser';
const CLEANCSS = 'npx cleancss';

const JS_FILES = [
  'app.js',
  'auth.js',
  'auth-shared.js',
  'api.js',
  'state.js',
  'flash.js',
  'analytics.js',
  'chart-engine.js',
  'dasha-engine.js',
  'community.js',
  'community-status.js',
  'consultation.js',
  'consultant.js',
  'matchmaking.js',
  'matchmaking-booking.js',
  'apply.js',
  'profile.js',
  'validation.js',
  'legal-policy.js',
];

const CSS_FILES = [
  'styles.css',
  'community.css',
  'legal-policy.css',
  'validation.css',
];

let jsTotal = 0;
let jsSaved = 0;
let cssTotal = 0;
let cssSaved = 0;

function fmtKB(bytes) {
  return (bytes / 1024).toFixed(1) + 'KB';
}

console.log('\n🚀 Starting minification build...\n');

if (fs.existsSync(path.join(REACT_FRONTEND_DIR, 'package.json'))) {
  try {
    console.log('  Building React frontend for routed workspaces...');
    if (!fs.existsSync(path.join(REACT_FRONTEND_DIR, 'node_modules'))) {
      execSync('npm install', { cwd: REACT_FRONTEND_DIR, stdio: 'inherit' });
    }
    execSync('npm run build', { cwd: REACT_FRONTEND_DIR, stdio: 'inherit' });
    fs.rmSync(PUBLIC_REACT_DIR, { recursive: true, force: true });
    fs.cpSync(path.join(REACT_FRONTEND_DIR, 'dist'), PUBLIC_REACT_DIR, { recursive: true });
    console.log('  ✅ React frontend copied to public/frontend\n');
  } catch (err) {
    console.error(`  ❌ React frontend build failed: ${err.message}`);
    process.exitCode = 1;
  }
}

// ── Minify JS ─────────────────────────────────────────────────────────────────
for (const file of JS_FILES) {
  const filePath = path.join(FRONTEND_DIR, file);
  if (!fs.existsSync(filePath)) continue;

  const originalSize = fs.statSync(filePath).size;
  try {
    execSync(
      `${TERSER} "${filePath}" --compress --mangle --output "${filePath}"`,
      { stdio: 'pipe' }
    );
    const newSize = fs.statSync(filePath).size;
    const saved = originalSize - newSize;
    jsTotal += originalSize;
    jsSaved += saved;
    console.log(
      `  ✅ JS  ${file.padEnd(30)} ${fmtKB(originalSize)} → ${fmtKB(newSize)} (saved ${fmtKB(saved)})`
    );
  } catch (err) {
    console.error(`  ❌ JS  ${file}: ${err.message}`);
  }
}

// ── Minify CSS ────────────────────────────────────────────────────────────────
for (const file of CSS_FILES) {
  const filePath = path.join(FRONTEND_DIR, file);
  if (!fs.existsSync(filePath)) continue;

  const originalSize = fs.statSync(filePath).size;
  try {
    execSync(
      `${CLEANCSS} --output "${filePath}" "${filePath}"`,
      { stdio: 'pipe' }
    );
    const newSize = fs.statSync(filePath).size;
    const saved = originalSize - newSize;
    cssTotal += originalSize;
    cssSaved += saved;
    console.log(
      `  ✅ CSS ${file.padEnd(30)} ${fmtKB(originalSize)} → ${fmtKB(newSize)} (saved ${fmtKB(saved)})`
    );
  } catch (err) {
    console.error(`  ❌ CSS ${file}: ${err.message}`);
  }
}

console.log('\n─────────────────────────────────────────────────────────────────────');
console.log(`  JS  total saved : ${fmtKB(jsSaved)} of ${fmtKB(jsTotal)}`);
console.log(`  CSS total saved : ${fmtKB(cssSaved)} of ${fmtKB(cssTotal)}`);
console.log(`  Grand total     : ${fmtKB(jsSaved + cssSaved)} saved`);
console.log('─────────────────────────────────────────────────────────────────────\n');
console.log('✅ Build complete.\n');
