/**
 * dasha-engine.js
 * Reusable Vimshottari (120-year) Dasha rendering engine.
 * Renders a 5-level drill-down: Mahadasha → Antardasha → Pratyantardasha → Sookshma → Prana
 * into any given container element. Fully self-contained — no global state, no DOM IDs required.
 *
 * Usage:
 *   import { DashaWidget } from './dasha-engine.js';
 *   const widget = new DashaWidget(containerEl, dashaData, { personLabel: 'Boy' });
 *   widget.render();
 */

// ── Constants ────────────────────────────────────────────────────────────────
export const DASHA_NAMES = {
  maha: 'Mahadasha',
  antara: 'Antardasha',
  pratyantara: 'Pratyantardasha',
  sookshma: 'Sookshma Dasha',
  prana: 'Prana Dasha',
};

export const DASHA_LABELS = {
  Ketu: 'Ke', Venus: 'Ve', Sun: 'Su', Moon: 'Mo', Mars: 'Ma',
  Rahu: 'Ra', Jupiter: 'Ju', Saturn: 'Sa', Mercury: 'Me',
};

export const DASHA_YEARS = {
  Ketu: 7, Venus: 20, Sun: 6, Moon: 10, Mars: 7,
  Rahu: 18, Jupiter: 16, Saturn: 19, Mercury: 17,
};

export const DASHA_SEQUENCE = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury'];

// Planet colours (matches chart-engine.js)
const PLANET_COLORS = {
  Sun: '#e65c00', Moon: '#5b8dd9', Mars: '#c0392b', Mercury: '#27ae60',
  Jupiter: '#d4a017', Venus: '#8e44ad', Saturn: '#2980b9', Rahu: '#7f8c8d',
  Ketu: '#a04000',
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function addDashaYears(date, years) {
  return new Date(date.getTime() + years * 365.25 * 24 * 60 * 60 * 1000);
}

function sequenceFrom(lord) {
  const idx = DASHA_SEQUENCE.indexOf(lord);
  return [...DASHA_SEQUENCE.slice(idx), ...DASHA_SEQUENCE.slice(0, idx)];
}

function childDashaRows(parent) {
  const start = new Date(parent.start);
  let cursor = start;
  const parentPath = parent.path || [parent.lord];
  return sequenceFrom(parent.lord).map((lord) => {
    const durationYears = parent.duration_years * DASHA_YEARS[lord] / 120;
    const end = addDashaYears(cursor, durationYears);
    const row = { lord, path: [...parentPath, lord], start: cursor.toISOString(), end: end.toISOString(), duration_years: durationYears };
    cursor = end;
    return row;
  });
}

function nextDashaLevel(level) {
  if (level === 'maha') return 'antara';
  if (level === 'antara') return 'pratyantara';
  if (level === 'pratyantara') return 'sookshma';
  if (level === 'sookshma') return 'prana';
  return 'none';
}

function formatDashaPath(path) {
  return path.map((lord) => DASHA_LABELS[lord] || lord).join('/');
}

function formatDateOnly(value) {
  return new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(value));
}

function formatYears(value) {
  const years = Number(value);
  if (!Number.isFinite(years)) return '';
  if (years >= 1) return years.toFixed(2) + 'y';
  const days = years * 365.25;
  if (days >= 1) return `${days.toFixed(1)}d`;
  return `${(days * 24).toFixed(1)}h`;
}

function esc(value) {
  return String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
}

function normalizeDashaTimeline(timeline, currentMahadasha) {
  if (Array.isArray(timeline) && timeline.length) {
    return timeline.map((p) => ({ ...p, path: p.path || [p.lord] }));
  }
  if (!currentMahadasha) return [];
  return childDashaRows({
    lord: currentMahadasha.lord,
    path: [currentMahadasha.lord],
    start: currentMahadasha.start,
    duration_years: 120,
  }).slice(0, 9);
}

function deriveCurrentPrana(dasha) {
  if (!dasha.current_sookshma || !dasha.event_time) return null;
  const eventTime = new Date(dasha.event_time);
  return childDashaRows(dasha.current_sookshma).find((period) => {
    const s = new Date(period.start);
    const e = new Date(period.end);
    return s <= eventTime && eventTime <= e;
  }) || null;
}

function normalizeDasha(dasha) {
  // Treat empty objects the same as null — nothing to render
  if (!dasha || typeof dasha !== 'object') return null;
  if (!dasha.current_mahadasha && !dasha.mahadasha_timeline) return null;
  const normalized = { ...dasha };
  normalized.current_prana = normalized.current_prana || deriveCurrentPrana(normalized);
  normalized.mahadasha_timeline = normalizeDashaTimeline(normalized.mahadasha_timeline, normalized.current_mahadasha);
  // Still no useful data after normalization → bail
  if (!normalized.mahadasha_timeline || normalized.mahadasha_timeline.length === 0) return null;
  return normalized;
}

// ── DashaWidget Class ─────────────────────────────────────────────────────────
export class DashaWidget {
  /**
   * @param {HTMLElement} container  - Element to render the widget into
   * @param {object}      dashaData  - Dasha object from the API (dashas field)
   * @param {object}      options
   * @param {string}      options.personLabel - e.g. "Boy" or "Girl"
   */
  constructor(container, dashaData, options = {}) {
    this.container = container;
    this.dasha = normalizeDasha(dashaData);
    this.label = options.personLabel || '';
    this.stack = [];
    this._idPrefix = `dw-${Math.random().toString(36).slice(2, 8)}`;
  }

  // Unique element IDs scoped to this widget instance
  _id(suffix) {
    return `${this._idPrefix}-${suffix}`;
  }

  render() {
    if (!this.dasha) {
      this.container.innerHTML = `<div class="dasha-widget-empty">Dasha data not available.</div>`;
      return;
    }
    this.container.innerHTML = this._buildShell();
    this._bindBack();
    this._renderSummary();
    this._renderLevel('maha', this.dasha.mahadasha_timeline || [], []);
  }

  _buildShell() {
    const d = this.dasha;
    return `
      <div class="dasha-widget">
        <div class="dasha-widget-header">
          <span class="dasha-widget-title">${esc(this.label)} — Vimshottari Dasha</span>
          <span class="dasha-widget-subtitle">120-year cycle · 5 levels</span>
        </div>

        <div class="dasha-widget-summary" id="${this._id('summary')}"></div>

        <div class="dasha-widget-drillbar">
          <button type="button" class="dasha-widget-back-btn" id="${this._id('back')}" disabled>← Back</button>
          <div>
            <h4 class="dasha-widget-level-heading" id="${this._id('heading')}">Mahadasha</h4>
            <p class="dasha-widget-path" id="${this._id('path')}">Select a period to drill down.</p>
          </div>
        </div>

        <div class="dasha-widget-table-wrap">
          <table class="dasha-widget-table" id="${this._id('table')}"></table>
        </div>

        <p class="dasha-widget-note">Dates shown are period end dates. Drill-down: Maha → Antara → Pratyantar → Sookshma → Prana.</p>
      </div>
    `;
  }

  _renderSummary() {
    const d = this.dasha;
    const el = this.container.querySelector(`#${this._id('summary')}`);
    if (!el) return;

    const pill = (label, lord, extra) => {
      const color = PLANET_COLORS[lord] || '#555';
      return `
        <div class="dasha-summary-pill">
          <span class="dasha-summary-dot" style="background:${color}"></span>
          <div>
            <strong>${esc(label)}</strong>
            <span>${esc(lord)}</span>
            ${extra ? `<small>${esc(extra)}</small>` : ''}
          </div>
        </div>`;
    };

    const parts = [
      d.current_mahadasha ? pill('Mahadasha', d.current_mahadasha.lord, `${d.current_mahadasha.balance_years}y left`) : '',
      d.current_antardasha ? pill('Antardasha', d.current_antardasha.lord, `Ends ${formatDateOnly(d.current_antardasha.end)}`) : '',
      d.current_pratyantardasha ? pill('Pratyantar', d.current_pratyantardasha.lord, `Ends ${formatDateOnly(d.current_pratyantardasha.end)}`) : '',
      d.current_sookshma ? pill('Sookshma', d.current_sookshma.lord, `Ends ${formatDateOnly(d.current_sookshma.end)}`) : '',
      d.current_prana ? pill('Prana', d.current_prana.lord, `Ends ${formatDateOnly(d.current_prana.end)}`) : '',
    ].filter(Boolean);

    el.innerHTML = `<div class="dasha-summary-pills">${parts.join('')}</div>`;
  }

  _renderLevel(level, rows, parentPath, pushStack = true) {
    if (pushStack) this.stack.push({ level, rows, parentPath });

    const heading = this.container.querySelector(`#${this._id('heading')}`);
    const backBtn = this.container.querySelector(`#${this._id('back')}`);
    const pathEl = this.container.querySelector(`#${this._id('path')}`);
    const table = this.container.querySelector(`#${this._id('table')}`);

    if (heading) heading.textContent = DASHA_NAMES[level] || level;
    if (backBtn) backBtn.disabled = this.stack.length <= 1;
    if (pathEl) {
      pathEl.textContent = parentPath.length
        ? `${formatDashaPath(parentPath)} · ${nextDashaLevel(level) === 'none' ? 'Final level' : 'Click a row to drill deeper'}`
        : 'Click a Mahadasha row to open Antardasha.';
    }

    const next = nextDashaLevel(level);
    const isClickable = next !== 'none';

    if (table) {
      table.innerHTML = `
        <thead>
          <tr>
            <th>Period</th>
            <th>Start</th>
            <th>End</th>
            <th>Duration</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((period, index) => {
            const color = PLANET_COLORS[period.lord] || '#555';
            return `
              <tr data-index="${index}" data-next="${next}" class="${isClickable ? 'dasha-row-clickable' : ''}">
                <td>
                  <span class="dasha-row-dot" style="background:${color}"></span>
                  <strong>${esc(formatDashaPath(period.path || [period.lord]))}</strong>
                  ${isClickable ? '<span class="dasha-row-drill">▶ drill</span>' : ''}
                </td>
                <td>${esc(formatDateOnly(period.start))}</td>
                <td>${esc(formatDateOnly(period.end))}</td>
                <td>${esc(formatYears(period.duration_years))}</td>
              </tr>`;
          }).join('')}
        </tbody>`;

      table.querySelectorAll('tr[data-next]').forEach((row) => {
        row.addEventListener('click', () => {
          const nextLevel = row.dataset.next;
          if (!nextLevel || nextLevel === 'none') return;
          const period = rows[Number(row.dataset.index)];
          this._renderLevel(nextLevel, childDashaRows(period), period.path || [period.lord]);
        });
      });
    }
  }

  _bindBack() {
    const backBtn = this.container.querySelector(`#${this._id('back')}`);
    if (!backBtn) return;
    backBtn.addEventListener('click', () => {
      if (this.stack.length <= 1) return;
      this.stack.pop();
      const prev = this.stack[this.stack.length - 1];
      this._renderLevel(prev.level, prev.rows, prev.parentPath, false);
    });
  }
}
