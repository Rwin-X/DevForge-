/* ============================================================
   YearGrid — script.js
   No framework. LocalStorage. 360 days. Precision.
   ============================================================ */

'use strict';

// ── Constants ──────────────────────────────────────────────
const STORAGE_KEY = 'yeargrid_data_v1';
const TOTAL_DAYS  = 360;

const ACTIVITIES = ['run', 'create', 'learn', 'book'];
const ACT_LABELS = {
  run:    '🏃 Run',
  create: '⚒ Create',
  learn:  '📚 Learn',
  book:   '📖 Book',
};

// ── State ──────────────────────────────────────────────────
let data = {};          // { 'YYYY-MM-DD': Set<activity> | Array }
let startDate = null;   // Day 0 of the 360-day grid
let days = [];          // Array of Date objects, length 360

let activeIndex  = null;
let tooltipTimer = null;

// ── DOM refs ───────────────────────────────────────────────
const gridEl        = document.getElementById('grid');
const monthLabels   = document.getElementById('monthLabels');
const tooltip       = document.getElementById('tooltip');
const modalOverlay  = document.getElementById('modalOverlay');
const modalDate     = document.getElementById('modalDate');
const modalClose    = document.getElementById('modalClose');
const btnSave       = document.getElementById('btnSave');
const btnClearDay   = document.getElementById('btnClearDay');
const btnResetAll   = document.getElementById('btnResetAll');
const currentYear   = document.getElementById('currentYear');
const headerProgress= document.getElementById('headerProgress');

const checks = {
  run:    document.getElementById('checkRun'),
  create: document.getElementById('checkCreate'),
  learn:  document.getElementById('checkLearn'),
  book:   document.getElementById('checkBook'),
};

// ── Stats DOM ──────────────────────────────────────────────
const statEls = {
  tracked:       document.getElementById('statTracked'),
  run:           document.getElementById('statRun'),
  create:        document.getElementById('statCreate'),
  learn:         document.getElementById('statLearn'),
  book:          document.getElementById('statBook'),
  currentStreak: document.getElementById('statCurrentStreak'),
  longestStreak: document.getElementById('statLongestStreak'),
  completion:    document.getElementById('statCompletion'),
};

// ── Init ───────────────────────────────────────────────────
function init() {
  // Load data from localStorage
  loadData();

  // Compute start date: beginning of the "360-day window"
  // Start from: today minus (today's dayOfWeek) to align to Monday
  computeDays();

  // Set header year
  currentYear.textContent = new Date().getFullYear();

  // Build grid
  renderGrid();
  renderMonthLabels();
  updateStats();
  updateHeaderProgress();

  // Event listeners
  modalClose.addEventListener('click', closeModal);
  modalOverlay.addEventListener('click', (e) => {
    if (e.target === modalOverlay) closeModal();
  });
  btnSave.addEventListener('click', saveDay);
  btnClearDay.addEventListener('click', clearDay);
  btnResetAll.addEventListener('click', resetAll);

  // Close modal on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });
}

// ── Data persistence ───────────────────────────────────────
function loadData() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      // Convert arrays back to Sets
      data = {};
      for (const [date, acts] of Object.entries(parsed)) {
        data[date] = new Set(Array.isArray(acts) ? acts : []);
      }
    }
  } catch (e) {
    data = {};
  }
}

function saveData() {
  // Convert Sets to arrays for JSON
  const serializable = {};
  for (const [date, acts] of Object.entries(data)) {
    serializable[date] = [...acts];
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(serializable));
}

// ── Day computation ────────────────────────────────────────
function computeDays() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Find the Monday at or before today so the grid aligns properly
  // day 0=Sun,1=Mon...6=Sat → adjust to Mon-start
  const dow = today.getDay(); // 0=Sun
  const daysFromMon = (dow === 0) ? 6 : dow - 1;

  // End of grid: this Monday + remaining days to fill 360
  // Grid has 7 rows × N cols. We want 360 cells total.
  // Let's anchor: last cell is today's week's Sunday (or slightly ahead)
  // More natural: start = today - (TOTAL_DAYS - 1) days, then align to Mon

  // Calculate grid start: go back TOTAL_DAYS-1 days from today, snap to nearest Monday
  const rawStart = new Date(today);
  rawStart.setDate(rawStart.getDate() - (TOTAL_DAYS - 1));

  // Snap rawStart to Monday (go backwards to find the previous/current Monday)
  const rawDow = rawStart.getDay();
  const snapBack = (rawDow === 0) ? 6 : rawDow - 1;
  startDate = new Date(rawStart);
  startDate.setDate(startDate.getDate() - snapBack);

  // Build 360+ days array (we'll render exactly enough columns to show ~360 meaningful days)
  // Total cells = 7 rows. Columns = ceil((today_index + 1) / 7) + some past columns
  // Simpler: just render from startDate until we have >= 360 cells covering today
  days = [];
  const cur = new Date(startDate);
  // Compute total cells needed: from startDate to today + fill to end of week
  const msPerDay = 86400000;
  const totalFromStart = Math.floor((today - startDate) / msPerDay) + 1;
  // Round up to multiple of 7
  const totalCells = Math.ceil(totalFromStart / 7) * 7;
  // But cap at a reasonable max
  const cellCount = Math.max(TOTAL_DAYS + 6, totalCells + 7);

  for (let i = 0; i < cellCount; i++) {
    days.push(new Date(cur));
    cur.setDate(cur.getDate() + 1);
  }
}

function dateKey(date) {
  // Returns YYYY-MM-DD
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function todayKey() {
  return dateKey(new Date());
}

function isToday(date) {
  return dateKey(date) === todayKey();
}

function isFuture(date) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return date > today;
}

// ── Grid rendering ─────────────────────────────────────────
function renderGrid() {
  gridEl.innerHTML = '';

  days.forEach((day, idx) => {
    const cell = document.createElement('div');
    cell.className = 'day-cell';
    cell.dataset.index = idx;

    if (isFuture(day)) cell.classList.add('future');
    if (isToday(day))  cell.classList.add('today');

    applyColor(cell, day);

    // Hover: tooltip
    cell.addEventListener('mouseenter', (e) => showTooltip(e, day));
    cell.addEventListener('mousemove',  (e) => moveTooltip(e));
    cell.addEventListener('mouseleave', hideTooltip);

    // Click: open modal (not for future)
    cell.addEventListener('click', () => {
      if (!isFuture(day)) openModal(day, idx);
    });

    gridEl.appendChild(cell);
  });
}

function applyColor(cell, day) {
  const key  = dateKey(day);
  const acts = data[key] ? [...data[key]] : [];
  const order = ['run', 'create', 'learn', 'book'];
  const sorted = order.filter(a => acts.includes(a));

  if (sorted.length === 0) {
    cell.removeAttribute('data-acts');
  } else {
    cell.setAttribute('data-acts', sorted.join('-'));
  }
}

function refreshCell(day) {
  const cells = gridEl.querySelectorAll('.day-cell');
  const idx = days.findIndex(d => dateKey(d) === dateKey(day));
  if (idx >= 0 && cells[idx]) {
    applyColor(cells[idx], day);
  }
}

// ── Month labels ───────────────────────────────────────────
function renderMonthLabels() {
  monthLabels.innerHTML = '';

  // cell width + gap
  const cellWidth = 14 + 3; // --cell-size + --cell-gap

  let lastMonth = -1;
  days.forEach((day, idx) => {
    const col = Math.floor(idx / 7);
    const row = idx % 7;

    if (row === 0 && day.getMonth() !== lastMonth) {
      lastMonth = day.getMonth();
      const span = document.createElement('span');
      span.className = 'month-label';
      span.textContent = day.toLocaleString('en', { month: 'short' }).toUpperCase();
      span.style.marginLeft = col === 0 ? '0' : `${(cellWidth)}px`;
      // Actually, just set a min-width and let them flow
      span.style.minWidth = `${cellWidth * 4}px`;
      monthLabels.appendChild(span);
    }
  });
}

// ── Tooltip ────────────────────────────────────────────────
function showTooltip(e, day) {
  const key  = dateKey(day);
  const acts = data[key] ? [...data[key]] : [];
  const order = ['run', 'create', 'learn', 'book'];
  const sorted = order.filter(a => acts.includes(a));

  const dateStr = day.toLocaleDateString('en', {
    weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'
  }).toUpperCase();

  let html = `<div class="tooltip-date">${dateStr}</div>`;

  if (sorted.length === 0) {
    html += `<div class="tooltip-empty">No activities logged</div>`;
  } else {
    html += `<div class="tooltip-acts">`;
    sorted.forEach(a => {
      html += `<div class="tooltip-act-item">
        <span class="tooltip-dot ${a}"></span>
        <span>${ACT_LABELS[a]}</span>
      </div>`;
    });
    html += `</div>`;
  }

  if (isToday(day)) html += `<div style="margin-top:6px;font-size:9px;color:var(--text-muted);letter-spacing:.1em">TODAY</div>`;

  tooltip.innerHTML = html;
  moveTooltip(e);
  tooltip.classList.add('visible');
}

function moveTooltip(e) {
  const pad = 14;
  const tw  = tooltip.offsetWidth  || 180;
  const th  = tooltip.offsetHeight || 80;
  let   x   = e.clientX + pad;
  let   y   = e.clientY + pad;

  if (x + tw > window.innerWidth  - 10) x = e.clientX - tw - pad;
  if (y + th > window.innerHeight - 10) y = e.clientY - th - pad;

  tooltip.style.left = `${x}px`;
  tooltip.style.top  = `${y}px`;
}

function hideTooltip() {
  tooltip.classList.remove('visible');
}

// ── Modal ──────────────────────────────────────────────────
function openModal(day, idx) {
  activeIndex = idx;

  // Set date label
  modalDate.textContent = day.toLocaleDateString('en', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
  });

  // Load existing data
  const key  = dateKey(day);
  const acts = data[key] || new Set();
  ACTIVITIES.forEach(a => {
    checks[a].checked = acts.has(a);
  });

  modalOverlay.classList.add('active');
  // Focus first checkbox for a11y
  setTimeout(() => checks.run.closest('label').focus(), 50);
}

function closeModal() {
  modalOverlay.classList.remove('active');
  activeIndex = null;
}

function saveDay() {
  if (activeIndex === null) return;
  const day = days[activeIndex];
  const key = dateKey(day);

  const selected = new Set();
  ACTIVITIES.forEach(a => {
    if (checks[a].checked) selected.add(a);
  });

  if (selected.size === 0) {
    delete data[key];
  } else {
    data[key] = selected;
  }

  saveData();
  refreshCell(day);
  updateStats();
  updateHeaderProgress();
  closeModal();
}

function clearDay() {
  if (activeIndex === null) return;
  const day = days[activeIndex];
  const key = dateKey(day);
  delete data[key];
  saveData();
  refreshCell(day);
  updateStats();
  updateHeaderProgress();
  closeModal();
}

function resetAll() {
  const confirmed = window.confirm(
    'Reset ALL data?\n\nThis will permanently erase your 360-day log.\nThis cannot be undone.'
  );
  if (!confirmed) return;
  data = {};
  saveData();
  renderGrid();
  updateStats();
  updateHeaderProgress();
}

// ── Statistics ─────────────────────────────────────────────
function updateStats() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Count only days within our 360-day window up to today
  let tracked = 0, runC = 0, createC = 0, learnC = 0, bookC = 0;

  const gridDays = days.filter(d => !isFuture(d));

  gridDays.forEach(d => {
    const key  = dateKey(d);
    const acts = data[key];
    if (acts && acts.size > 0) {
      tracked++;
      if (acts.has('run'))    runC++;
      if (acts.has('create')) createC++;
      if (acts.has('learn'))  learnC++;
      if (acts.has('book'))   bookC++;
    }
  });

  statEls.tracked.textContent = tracked;
  statEls.run.textContent     = runC;
  statEls.create.textContent  = createC;
  statEls.learn.textContent   = learnC;
  statEls.book.textContent    = bookC;

  // Streaks — consecutive days with ANY activity (going backwards from today)
  const sortedPast = gridDays
    .slice()
    .sort((a, b) => b - a); // newest first

  let currentStreak = 0;
  let longestStreak = 0;
  let tempStreak    = 0;
  let onStreak      = true;

  // Walk backwards from today
  for (let i = 0; i < sortedPast.length; i++) {
    const d   = sortedPast[i];
    const key = dateKey(d);
    const has = data[key] && data[key].size > 0;

    // Check if this day is consecutive with the previous one
    if (i > 0) {
      const prev  = sortedPast[i - 1];
      const diff  = Math.round((prev - d) / 86400000);
      if (diff !== 1) {
        // Gap — break temp streak
        if (tempStreak > longestStreak) longestStreak = tempStreak;
        tempStreak = 0;
        if (onStreak) {
          onStreak      = false;
          currentStreak = 0;
        }
      }
    }

    if (has) {
      tempStreak++;
      if (onStreak) currentStreak++;
    } else {
      if (tempStreak > longestStreak) longestStreak = tempStreak;
      tempStreak = 0;
      if (onStreak) {
        // Allow one-day gap only if it's not today
        if (i === 0) {
          // Today is empty — streak might continue from yesterday
          // don't break yet
        } else {
          onStreak      = false;
          currentStreak = 0;
        }
      }
    }
  }
  if (tempStreak > longestStreak) longestStreak = tempStreak;

  // Recalculate current streak properly
  currentStreak = computeCurrentStreak(sortedPast);
  if (currentStreak > longestStreak) longestStreak = currentStreak;

  statEls.currentStreak.innerHTML = `${currentStreak} <span class="streak-unit">days</span>`;
  statEls.longestStreak.innerHTML = `${longestStreak} <span class="streak-unit">days</span>`;

  const pct = gridDays.length > 0 ? Math.round((tracked / Math.min(TOTAL_DAYS, gridDays.length)) * 100) : 0;
  statEls.completion.innerHTML = `${pct}<span class="streak-unit">%</span>`;
}

function computeCurrentStreak(sortedPastDays) {
  // sortedPastDays is newest-first, no future days
  if (sortedPastDays.length === 0) return 0;

  let streak = 0;
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Start from today or yesterday (allow today to not yet be logged)
  let cursor = new Date(today);

  for (let i = 0; i < sortedPastDays.length; i++) {
    const d   = sortedPastDays[i];
    const key = dateKey(d);
    const has = data[key] && data[key].size > 0;

    const diff = Math.round((cursor - d) / 86400000);

    if (diff === 0) {
      // This is the cursor day
      if (has) {
        streak++;
        cursor.setDate(cursor.getDate() - 1);
      }
      // If today is empty, we'll check yesterday next iteration
      else if (dateKey(d) === dateKey(today)) {
        // Move cursor to yesterday
        cursor.setDate(cursor.getDate() - 1);
        continue;
      } else {
        break; // Gap found
      }
    } else if (diff === 1) {
      // cursor already moved but skipped this day — means a gap
      break;
    } else {
      break;
    }
  }

  return streak;
}

function updateHeaderProgress() {
  const pastDays = days.filter(d => !isFuture(d));
  const tracked  = pastDays.filter(d => {
    const key = dateKey(d);
    return data[key] && data[key].size > 0;
  }).length;
  const pct = pastDays.length > 0 ? Math.round((tracked / Math.min(TOTAL_DAYS, pastDays.length)) * 100) : 0;
  headerProgress.textContent = `${tracked} tracked · ${pct}% complete`;
}

// ── Boot ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
