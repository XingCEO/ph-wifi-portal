'use strict';

// ─── Section navigation ────────────────────────────────────────────────────

const sections = document.querySelectorAll('.section');
const navLinks  = document.querySelectorAll('nav a[data-section]');

function showSection(id) {
  sections.forEach(s => s.classList.toggle('active', s.id === id));
  navLinks.forEach(a => a.classList.toggle('active', a.dataset.section === id));
}

navLinks.forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    showSection(a.dataset.section);
    history.replaceState(null, '', '#' + a.dataset.section);
  });
});

// Initial section from hash
const initialSection = location.hash.slice(1) || 'overview';
showSection(initialSection);

// ─── Stats fetch & render ──────────────────────────────────────────────────

const STATS_URL = '/admin/api/stats';
const REFRESH_MS = 30_000;

let lastData = null;

async function fetchStats() {
  const btn = document.getElementById('btn-refresh');
  btn?.classList.add('spinning');

  try {
    const res = await fetch(STATS_URL, { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    lastData = data;
    renderStats(data);
    renderChart(data.uv_trend || getMockTrend());
    renderTable(data.hotspots || getMockHotspots());
    updateLastRefresh();
  } catch (err) {
    console.warn('[admin] stats fetch failed:', err.message);
    // Use mock data if backend not ready
    if (!lastData) {
      const mock = getMockData();
      renderStats(mock);
      renderChart(mock.uv_trend);
      renderTable(mock.hotspots);
    }
  } finally {
    btn?.classList.remove('spinning');
  }
}

function renderStats(data) {
  setVal('stat-users',   data.today_users   ?? '—');
  setVal('stat-ads',     data.today_ads     ?? '—');
  setVal('stat-revenue', data.today_revenue != null ? '$' + data.today_revenue.toFixed(2) : '—');
  setVal('stat-live',    data.live_users    ?? '—');

  setChange('stat-users-change',   data.users_change);
  setChange('stat-ads-change',     data.ads_change);
  setChange('stat-revenue-change', data.revenue_change);
  setChange('stat-live-change',    null);
}

function setVal(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function setChange(id, pct) {
  const el = document.getElementById(id);
  if (!el) return;
  if (pct == null) { el.textContent = ''; return; }
  const sign = pct >= 0 ? '+' : '';
  el.textContent = `${sign}${pct}% vs yesterday`;
  el.classList.toggle('negative', pct < 0);
}

function updateLastRefresh() {
  const el = document.getElementById('last-refresh');
  if (el) {
    const now = new Date();
    el.textContent = 'Updated ' + now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }
}

// ─── SVG Line Chart ────────────────────────────────────────────────────────

function renderChart(points) {
  // points: [{label: 'Mon', value: 123}, ...]
  const svg = document.getElementById('uv-chart');
  if (!svg) return;

  const W = svg.clientWidth || 600;
  const H = 160;
  const PAD = { top: 10, right: 16, bottom: 28, left: 44 };
  const cW = W - PAD.left - PAD.right;
  const cH = H - PAD.top - PAD.bottom;

  const values = points.map(p => p.value);
  const minV = Math.min(...values) * 0.85;
  const maxV = Math.max(...values) * 1.1 || 10;

  const xStep = cW / (points.length - 1);

  const px = (i) => PAD.left + i * xStep;
  const py = (v) => PAD.top + cH - ((v - minV) / (maxV - minV)) * cH;

  // Build smooth bezier path
  function buildPath(pts) {
    if (pts.length < 2) return '';
    let d = `M ${px(0)} ${py(pts[0].value)}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const x0 = px(i), y0 = py(pts[i].value);
      const x1 = px(i + 1), y1 = py(pts[i + 1].value);
      const cpX = (x0 + x1) / 2;
      d += ` C ${cpX} ${y0}, ${cpX} ${y1}, ${x1} ${y1}`;
    }
    return d;
  }

  const linePath = buildPath(points);
  const areaPath = linePath
    + ` L ${px(points.length - 1)} ${PAD.top + cH}`
    + ` L ${px(0)} ${PAD.top + cH} Z`;

  // Y axis ticks (3)
  const yTicks = [minV, (minV + maxV) / 2, maxV].map(v => ({
    v,
    label: v >= 1000 ? (v / 1000).toFixed(1) + 'k' : Math.round(v).toString(),
    y: py(v),
  }));

  const gradId = 'area-grad-' + Math.random().toString(36).slice(2, 6);

  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('height', H);

  svg.innerHTML = `
    <defs>
      <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#22c55e" stop-opacity="0.18"/>
        <stop offset="100%" stop-color="#22c55e" stop-opacity="0"/>
      </linearGradient>
    </defs>

    ${yTicks.map(t => `
      <line x1="${PAD.left}" y1="${t.y}" x2="${W - PAD.right}" y2="${t.y}"
            stroke="#27272a" stroke-width="1"/>
      <text x="${PAD.left - 6}" y="${t.y + 4}" text-anchor="end"
            fill="#71717a" font-size="10" font-family="Inter, sans-serif">${t.label}</text>
    `).join('')}

    ${points.map((p, i) => `
      <text x="${px(i)}" y="${H - 4}" text-anchor="middle"
            fill="#71717a" font-size="10" font-family="Inter, sans-serif">${p.label}</text>
    `).join('')}

    <path d="${areaPath}" fill="url(#${gradId})"/>
    <path d="${linePath}" fill="none" stroke="#22c55e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>

    ${points.map((p, i) => `
      <circle cx="${px(i)}" cy="${py(p.value)}" r="3.5"
              fill="#09090b" stroke="#22c55e" stroke-width="2"
              class="chart-point" data-label="${p.label}" data-value="${p.value}"
              style="cursor:pointer"/>
    `).join('')}
  `;

  // Tooltip events
  const tooltip = document.getElementById('chart-tooltip');
  svg.querySelectorAll('.chart-point').forEach(dot => {
    dot.addEventListener('mouseenter', e => {
      if (!tooltip) return;
      tooltip.innerHTML = `<strong>${dot.dataset.value}</strong><span>${dot.dataset.label}</span>`;
      tooltip.style.display = 'block';
      posTooltip(e, tooltip);
    });
    dot.addEventListener('mousemove', e => posTooltip(e, tooltip));
    dot.addEventListener('mouseleave', () => {
      if (tooltip) tooltip.style.display = 'none';
    });
  });
}

function posTooltip(e, el) {
  if (!el) return;
  el.style.left = (e.clientX + 12) + 'px';
  el.style.top  = (e.clientY - 36) + 'px';
}

// ─── Hotspot table ────────────────────────────────────────────────────────

function renderTable(hotspots) {
  const tbody = document.getElementById('hotspots-tbody');
  if (!tbody) return;

  tbody.innerHTML = hotspots.map(h => `
    <tr>
      <td class="name">${esc(h.name)}</td>
      <td>${esc(h.location)}</td>
      <td class="uv">${fmtNum(h.today_uv)}</td>
      <td>${fmtNum(h.online)}</td>
      <td>
        <span class="badge ${h.active ? 'active' : 'inactive'}" aria-label="${h.active ? 'Active' : 'Inactive'}">
          <span class="badge-dot" aria-hidden="true"></span>
          ${h.active ? 'Active' : 'Inactive'}
        </span>
      </td>
      <td>
        <button class="btn-action" aria-label="Manage hotspot ${esc(h.name)}"
                onclick="manageHotspot(${h.id})">Manage</button>
      </td>
    </tr>
  `).join('');
}

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function fmtNum(n) {
  if (n == null) return '—';
  return Number(n).toLocaleString('en-US');
}

function manageHotspot(id) {
  window.location.href = `/admin/hotspots/${id}`;
}

// ─── Mock data (dev fallback) ──────────────────────────────────────────────

function getMockData() {
  return {
    today_users:    1234,
    today_ads:      567,
    today_revenue:  12.34,
    live_users:     8,
    users_change:   12,
    ads_change:     7,
    revenue_change: 4,
    uv_trend:       getMockTrend(),
    hotspots:       getMockHotspots(),
  };
}

function getMockTrend() {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  return days.map((label, i) => ({
    label,
    value: 800 + Math.round(Math.sin(i * 0.9) * 300 + i * 60),
  }));
}

function getMockHotspots() {
  return [
    { id: 1, name: 'SM Mall – North Wing',  location: 'Manila',   today_uv: 312, online: 3, active: true  },
    { id: 2, name: 'Jollibee Taft Ave',     location: 'Manila',   today_uv: 189, online: 1, active: true  },
    { id: 3, name: 'Robinson's Galleria',   location: 'Ortigas',  today_uv: 278, online: 2, active: true  },
    { id: 4, name: 'Terminal 3 Arrivals',   location: 'NAIA',     today_uv: 455, online: 2, active: true  },
    { id: 5, name: 'Market! Market!',       location: 'BGC',      today_uv: 0,   online: 0, active: false },
  ];
}

// ─── Refresh button ────────────────────────────────────────────────────────

document.getElementById('btn-refresh')?.addEventListener('click', fetchStats);

// ─── Auto-refresh every 30s ────────────────────────────────────────────────

fetchStats();
setInterval(fetchStats, REFRESH_MS);
