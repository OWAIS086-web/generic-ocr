/* ── Bulk Upload Page Logic ── */

let matrixItems = [];
let done = 0, failed = 0, elapsed = 0;
let matrixActive = false;
const POOL_SIZE = 4;
let cardMap = new Map(); // Track cards by filename

// ── Settings Resolver ──
const getStrategy = () => ({
  kv: (localStorage.getItem('aiStructuring') || 'true') === 'true',
  class: (localStorage.getItem('autoClassify') || 'true') === 'true',
  ann: (localStorage.getItem('showAnnotatedImage') || 'true') === 'true',
  table: (localStorage.getItem('tableMode') || 'false') === 'true',
  path: localStorage.getItem('serverBulkPath') || 'data/'
});

document.addEventListener('DOMContentLoaded', () => {
  applySettingsUI();
  loadRepoMatrix();
});

function applySettingsUI() {
  const s = getStrategy();
  if (s.kv) document.getElementById('pillKV').style.display = 'inline-flex';
  if (s.class) document.getElementById('pillClass').style.display = 'inline-flex';
  if (s.ann) document.getElementById('pillAnn').style.display = 'inline-flex';
  if (s.table) document.getElementById('pillTable').style.display = 'inline-flex';
  document.getElementById('configuredPathDisplay').innerText = s.path;
}

async function loadRepoMatrix() {
  const s = getStrategy();
  const prev = document.getElementById('repoPreview');
  const startBtn = document.getElementById('startBtn');
  try {
    const r = await fetch(`/data-images?path=${encodeURIComponent(s.path)}`);
    const d = await r.json();
    if (d.images?.length) {
      matrixItems = d.images.map(n => ({ name: n, isServer: true }));
      prev.innerHTML = '';
      d.images.slice(0, 8).forEach(n => {
        const line = document.createElement('div');
        line.style.cssText = 'font-family:var(--font-mono); font-size:0.8em; padding:4px 0; opacity:0.7;';
        line.innerText = `📄 ${n}`;
        prev.appendChild(line);
      });
      if (d.images.length > 8) {
        const more = document.createElement('div');
        more.style.cssText = 'opacity:0.4; font-size:0.8em; margin-top:8px;';
        more.innerText = `+ ${d.images.length - 8} more`;
        prev.appendChild(more);
      }
      startBtn.disabled = false;
    } else {
      prev.innerHTML = `<div style="opacity:0.4; font-size:0.9em;">No documents found in ${esc(s.path)}</div>`;
      startBtn.disabled = true;
    }
  } catch (e) {
    prev.innerHTML = '<div style="color:var(--error); font-size:0.9em;">Failed to load documents</div>';
    startBtn.disabled = true;
  }
}

async function startMatrixJob() {
  if (matrixActive || !matrixItems.length) return;
  matrixActive = true;
  cardMap.clear();

  document.getElementById('selectionView').style.display = 'none';
  document.getElementById('dashboardView').style.display = 'block';
  document.getElementById('statManifest').innerText = matrixItems.length;

  const strategy = getStrategy();
  let currentIdx = 0;

  const worker = async () => {
    while (currentIdx < matrixItems.length) {
      const idx = currentIdx++;
      await processDossier(idx, strategy);
    }
  };

  const pool = [];
  for (let i = 0; i < Math.min(POOL_SIZE, matrixItems.length); i++) pool.push(worker());
  await Promise.all(pool);

  matrixActive = false;
  document.getElementById('finishedPanel').style.display = 'block';
  showToast('✅ Processing complete');
}

async function processDossier(idx, s) {
  const item = matrixItems[idx];
  const start = Date.now();
  
  // Create card immediately with loading state
  const cardId = `card-${idx}`;
  createResultCard(cardId, item, s, true);
  
  try {
    const r = await fetch('/process-data-file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: item.name,
        custom_path: s.path,
        extract_kv: s.kv,
        auto_classify: s.class,
        annotate_image: s.ann,
        extract_tables_only: s.table
      })
    });
    const d = await r.json();
    if (d.status === 'success') {
      done++;
      elapsed += (Date.now() - start) / 1000;
      updateResultCard(cardId, d, item, s, false);
    } else throw new Error(d.message);
  } catch (e) {
    failed++;
    updateResultCard(cardId, null, item, s, false, e.message);
  }
  updateDashboard();
}

function createResultCard(cardId, item, s, isLoading) {
  const grid = document.getElementById('mainDossier');
  const card = document.createElement('div');
  card.id = cardId;
  card.className = 'result-card nexus-emboss';
  
  card.innerHTML = `
    <div class="result-image">
      <div style="text-align:center; opacity:0.5;">
        <div style="font-size:2em; margin-bottom:8px;">⏳</div>
        <div style="font-size:0.8em;">Processing...</div>
      </div>
    </div>
    <div class="result-header">
      <div class="result-title">${esc(item.name)}</div>
      <div class="processing-badge">Live</div>
    </div>
  `;
  
  grid.prepend(card);
  cardMap.set(cardId, { item, s });
}

function updateResultCard(cardId, data, item, s, isError, errorMsg) {
  const card = document.getElementById(cardId);
  if (!card) return;

  if (isError || !data) {
    card.innerHTML = `
      <div style="padding:20px; text-align:center;">
        <div style="font-size:2em; margin-bottom:8px;">⚠</div>
        <div style="font-weight:600; font-size:0.9em; margin-bottom:4px;">${esc(item.name)}</div>
        <div style="font-size:0.75em; opacity:0.5; color:var(--error);">${esc(errorMsg || 'Processing failed')}</div>
      </div>
    `;
    return;
  }

  const src = `/stream-bulk-file?path=${encodeURIComponent(s.path)}&filename=${encodeURIComponent(item.name)}`;
  const kv = data.key_value_pairs || {};
  const tables = data.tables || [];
  const rawText = data.raw_text || '';
  const hasAnn = data.annotated_image && s.ann;

  let tabs = '';
  let contents = '';

  // Image tab
  if (hasAnn) {
    tabs += `<button class="result-tab active" onclick="switchTab(this, '${cardId}', 'image')">🖼 Image</button>`;
    contents += `
      <div class="result-content active" data-tab="image">
        <img src="data:image/jpeg;base64,${data.annotated_image}" class="annotated-img" alt="Annotated">
      </div>
    `;
  }

  // KV tab
  if (Object.keys(kv).length > 0 && s.kv) {
    tabs += `<button class="result-tab ${!hasAnn ? 'active' : ''}" onclick="switchTab(this, '${cardId}', 'kv')">🔑 Data</button>`;
    let kvHtml = '<table class="kv-table"><tbody>';
    Object.entries(kv).forEach(([k, v]) => {
      kvHtml += `<tr><td>${esc(k)}</td><td>${esc(String(v))}</td></tr>`;
    });
    kvHtml += '</tbody></table>';
    contents += `<div class="result-content ${!hasAnn ? 'active' : ''}" data-tab="kv">${kvHtml}</div>`;
  }

  // Tables tab
  if (tables.length > 0 && s.table) {
    tabs += `<button class="result-tab" onclick="switchTab(this, '${cardId}', 'tables')">📊 Tables</button>`;
    let tableHtml = '<div class="table-wrapper">';
    tables.forEach((table, idx) => {
      if (table.headers && table.rows) {
        tableHtml += `<div style="margin-bottom:16px;"><div style="font-size:0.75em; font-weight:700; margin-bottom:8px; opacity:0.7;">${esc(table.name || `Table ${idx + 1}`)}</div>`;
        tableHtml += '<table class="data-table"><thead><tr>';
        table.headers.forEach(h => tableHtml += `<th>${esc(String(h))}</th>`);
        tableHtml += '</tr></thead><tbody>';
        table.rows.forEach(row => {
          tableHtml += '<tr>';
          if (Array.isArray(row)) row.forEach(cell => tableHtml += `<td>${esc(String(cell))}</td>`);
          tableHtml += '</tr>';
        });
        tableHtml += '</tbody></table></div>';
      }
    });
    tableHtml += '</div>';
    contents += `<div class="result-content" data-tab="tables">${tableHtml}</div>`;
  }

  // Raw text tab
  if (rawText) {
    tabs += `<button class="result-tab" onclick="switchTab(this, '${cardId}', 'raw')">📄 Text</button>`;
    contents += `<div class="result-content" data-tab="raw"><div class="raw-text">${esc(rawText)}</div></div>`;
  }

  card.innerHTML = `
    <div class="result-image">
      <img src="${src}" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22%3E%3Crect fill=%22%23222%22 width=%22100%22 height=%22100%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22%23666%22 font-size=%2212%22%3E?%3C/text%3E%3C/svg%3E'">
      <div class="result-tag">${esc(data.doc_type || 'Doc')}</div>
    </div>
    <div class="result-header" onclick="toggleExpand('${cardId}')">
      <div>
        <div class="result-title">${esc(item.name)}</div>
        <div class="result-meta">⏱ ${(data.timings?.total || 0).toFixed(2)}s</div>
      </div>
      <button class="expand-btn">▼</button>
    </div>
    ${tabs ? `<div class="result-tabs">${tabs}</div>` : ''}
    ${contents}
  `;
}

function switchTab(btn, cardId, tabName) {
  const card = document.getElementById(cardId);
  if (!card) return;

  // Deactivate all tabs
  card.querySelectorAll('.result-tab').forEach(t => t.classList.remove('active'));
  card.querySelectorAll('.result-content').forEach(c => c.classList.remove('active'));

  // Activate selected tab
  btn.classList.add('active');
  const content = card.querySelector(`[data-tab="${tabName}"]`);
  if (content) content.classList.add('active');
}

function toggleExpand(cardId) {
  const card = document.getElementById(cardId);
  if (!card) return;
  card.classList.toggle('expanded');
}

function updateDashboard() {
  const total = matrixItems.length;
  const progress = (done + failed) / total;
  document.getElementById('statIngested').innerText = done;
  document.getElementById('statErrors').innerText = failed;
  document.getElementById('statLatency').innerText = `${(elapsed / (done || 1)).toFixed(1)}s`;
  document.getElementById('dashPercent').innerText = `${Math.round(progress * 100)}%`;
  document.getElementById('dashCircleFg').style.strokeDashoffset = 276 - (276 * progress);
}

function esc(s) {
  const m = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return String(s).replace(/[&<>"']/g, c => m[c]);
}
