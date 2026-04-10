/* ── Dashboard Page Logic ── */

let currentData = null;
let _ocrBoxes = [];
let _imgNaturalW = 1, _imgNaturalH = 1;
let _imageVisible = true;
let stepTimer = null;

const fileInput = document.getElementById('fileInput');
const processBtn = document.getElementById('processBtn');
const uploadZone = document.getElementById('uploadZone');
const tooltip = document.getElementById('ocrTooltip') || { style: {} };

// ── Initializers ──
document.addEventListener('DOMContentLoaded', () => {
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            if (fileInput.files[0]) setFile(fileInput.files[0]);
        });
    }

    if (uploadZone) {
        uploadZone.addEventListener('dragover', e => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });
        uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
        uploadZone.addEventListener('drop', e => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            if (e.dataTransfer.files[0]) {
                const dt = new DataTransfer();
                dt.items.add(e.dataTransfer.files[0]);
                fileInput.files = dt.files;
                setFile(e.dataTransfer.files[0]);
            }
        });
    }
});

// ── Settings Helpers ──
const getIsKvMode = () => (localStorage.getItem('aiStructuring') || 'true') === 'true';
const getIsTableMode = () => localStorage.getItem('tableMode') === 'true';
const getShowAnnotatedImage = () => (localStorage.getItem('showAnnotatedImage') || 'true') === 'true';
const getAutoClassify = () => (localStorage.getItem('autoClassify') || 'true') === 'true';

function setFile(file) {
    document.getElementById('fileChipName').textContent = file.name;
    document.getElementById('fileChipWrap').style.display = 'block';
    processBtn.disabled = false;
}

function clearFile() {
    fileInput.value = '';
    document.getElementById('fileChipWrap').style.display = 'none';
    processBtn.disabled = true;
}

// ── core logic ──
function uploadFile() {
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('extract_kv', getIsKvMode());
    formData.append('extract_tables_only', getIsTableMode());
    formData.append('annotate_image', getShowAnnotatedImage());
    formData.append('auto_classify', getAutoClassify());

    document.getElementById('uploadHero').classList.add('hidden');
    document.getElementById('processingOverlay').classList.remove('hidden');
    document.getElementById('resultsWrap').classList.remove('show');
    document.getElementById('errorBanner').classList.add('hidden');

    animateSteps();

    fetch('/process', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            clearInterval(stepTimer);
            markStepsDone();
            document.getElementById('processingOverlay').classList.add('hidden');
            if (data.status === 'success') {
                currentData = data;
                displayResults(data);
                showToast('✅ Document processed successfully!');
            } else {
                showError(data.message || 'Processing failed');
                document.getElementById('uploadHero').classList.remove('hidden');
            }
        })
        .catch(err => {
            clearInterval(stepTimer);
            document.getElementById('processingOverlay').classList.add('hidden');
            document.getElementById('uploadHero').classList.remove('hidden');
            showError(err.message);
        });
}

function animateSteps() {
    const isKv = getIsKvMode();
    const isClass = getAutoClassify();
    const steps = ['step1', 'step2'];
    if (isClass) steps.push('step3');
    if (isKv) steps.push('step4');

    document.getElementById('step3').style.display = isClass ? 'flex' : 'none';
    document.getElementById('step4').style.display = isKv ? 'flex' : 'none';

    let i = 0;
    ['step1', 'step2', 'step3', 'step4'].forEach(s => {
        const el = document.getElementById(s);
        if (el) el.className = 'process-step nexus-deboss';
    });
    document.getElementById(steps[0]).classList.add('active');

    stepTimer = setInterval(() => {
        i++;
        if (i < steps.length) {
            document.getElementById(steps[i - 1]).classList.remove('active');
            document.getElementById(steps[i - 1]).classList.add('done');
            document.getElementById(steps[i]).classList.add('active');
        }
    }, 2500);
}

function markStepsDone() {
    const isKv = getIsKvMode();
    const isClass = getAutoClassify();
    const steps = ['step1', 'step2'];
    if (isClass) steps.push('step3');
    if (isKv) steps.push('step4');

    steps.forEach(s => {
        const el = document.getElementById(s);
        if (el) el.className = 'process-step done';
    });
}

function displayResults(data) {
    const kvPairs = data.key_value_pairs || {};
    const tables = data.tables || [];
    const rawText = data.raw_text || '';

    // Key-value pairs
    if (Object.keys(kvPairs).length > 0) {
        const cont = document.getElementById('kvContainer');
        cont.innerHTML = '';
        Object.keys(kvPairs).sort().forEach(key => {
            const div = document.createElement('div');
            div.className = 'kv-item nexus-deboss';
            const val = String(kvPairs[key]);
            const isArabic = /[\u0600-\u06FF]/.test(val + key);
            div.innerHTML = `<div class="kv-key" ${isArabic ? 'dir="rtl"' : ''}>${esc(key)}</div>
                           <div class="kv-value" ${isArabic ? 'dir="rtl" style="text-align:right"' : ''}>${esc(val)}</div>`;
            div.onclick = () => editSingleKV(key, kvPairs[key]);
            cont.appendChild(div);
        });
        document.getElementById('kvSection').style.display = 'block';
    }

    // Tables
    if (tables.length > 0) {
        const cont = document.getElementById('tableContainer');
        cont.innerHTML = '';
        tables.forEach((table, idx) => {
            if (table.headers && table.rows) {
                const wrap = document.createElement('div');
                wrap.className = 'data-table-wrap nexus-emboss';
                let html = `<div class="data-table-head">
                    <span>📊 ${esc(table.name || `Table ${idx + 1}`)}</span>
                    <button class="btn btn-ghost btn-sm" onclick="editTable(${idx})">Edit</button>
                  </div><table class="data-table"><thead><tr>`;
                table.headers.forEach(h => html += `<th>${esc(String(h))}</th>`);
                html += '</tr></thead><tbody>';
                table.rows.forEach(row => {
                    html += '<tr>';
                    if (Array.isArray(row)) row.forEach(cell => html += `<td>${esc(String(cell))}</td>`);
                    html += '</tr>';
                });
                html += '</tbody></table>';
                wrap.innerHTML = html;
                cont.appendChild(wrap);
            }
        });
        if (cont.children.length > 0) document.getElementById('tableSection').style.display = 'block';
    }

    if (rawText) {
        document.getElementById('rawText').textContent = rawText;
        document.getElementById('rawSection').style.display = 'block';
    }

    const t = data.timings || {};
    const prep = parseFloat(t.preprocessing || 0);
    const ext = parseFloat(t.structured_extraction || t.text_extraction || 0);
    const llm = parseFloat(t.structuring || t.llm_structuring || 0);
    const total = (prep + ext + llm).toFixed(2);
    
    document.getElementById('timePre').textContent = prep.toFixed(2) + 's';
    document.getElementById('timeExt').textContent = ext.toFixed(2) + 's';
    document.getElementById('timeLLM').textContent = llm.toFixed(2) + 's';
    document.getElementById('timeTotal').textContent = total + 's';

    if (data.annotated_image && getShowAnnotatedImage()) {
        renderAnnotatedImage('data:image/jpeg;base64,' + data.annotated_image, data.ocr_boxes || []);
    } else {
        document.getElementById('imageViewerSection').style.display = 'none';
        document.getElementById('resultsBody').classList.remove('with-image');
    }

    document.getElementById('resultsWrap').classList.add('show');

    if (data.doc_type) {
        const badge = document.getElementById('docTypeBadge');
        badge.textContent = data.doc_type;
        badge.style.display = 'inline-flex';
    }
}

function renderAnnotatedImage(src, boxes) {
    _ocrBoxes = boxes;
    const img = document.getElementById('annotatedImg');
    const canvas = document.getElementById('ocrCanvas');

    img.onload = () => {
        _imgNaturalW = img.naturalWidth;
        _imgNaturalH = img.naturalHeight;
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
    };
    img.src = src;

    document.getElementById('imageViewerSection').style.display = 'block';
    document.getElementById('resultsBody').classList.add('with-image');

    canvas.addEventListener('mousemove', onCanvasHover);
    canvas.addEventListener('mouseleave', () => { if (tooltip) tooltip.style.display = 'none'; });
}

function onCanvasHover(e) {
    const canvas = document.getElementById('ocrCanvas');
    const rect = canvas.getBoundingClientRect();
    const scaleX = _imgNaturalW / rect.width;
    const scaleY = _imgNaturalH / rect.height;
    const mx = (e.clientX - rect.left) * scaleX;
    const my = (e.clientY - rect.top) * scaleY;

    let hit = null;
    for (const box of _ocrBoxes) {
        if (mx >= box.x && mx <= box.x + box.w && my >= box.y && my <= box.y + box.h) {
            if (!hit || box.matched_key) hit = box;
        }
    }

    if (hit) {
        const label = hit.matched_key
            ? `🔑 ${hit.matched_key}\n📝 "${hit.text}"\n✅ conf: ${(hit.conf * 100).toFixed(0)}%`
            : `📝 "${hit.text}"\n✅ conf: ${(hit.conf * 100).toFixed(0)}%`;
        tooltip.textContent = label;
        tooltip.style.display = 'block';
        tooltip.style.left = (e.clientX + 14) + 'px';
        tooltip.style.top = (e.clientY - 10) + 'px';
    } else {
        tooltip.style.display = 'none';
    }
}

function toggleImagePanel() {
    const section = document.getElementById('imageViewerSection');
    const body = document.getElementById('resultsBody');
    _imageVisible = !_imageVisible;
    section.style.display = _imageVisible ? 'block' : 'none';
    body.classList.toggle('with-image', _imageVisible);
}

function editSingleKV(key, value) {
    const newVal = prompt(`Edit value for "${key}":`, value);
    if (newVal !== null) {
        currentData.key_value_pairs[key] = newVal;
        displayResults(currentData);
    }
}

function resetUpload() {
    clearFile();
    document.getElementById('uploadHero').classList.remove('hidden');
    document.getElementById('resultsWrap').classList.remove('show');
    document.getElementById('errorBanner').classList.add('hidden');
    ['kvSection', 'tableSection', 'rawSection'].forEach(id => document.getElementById(id).style.display = 'none');
    document.getElementById('imageViewerSection').style.display = 'none';
    document.getElementById('resultsBody').classList.remove('with-image');
    document.getElementById('annotatedImg').src = '';
    _ocrBoxes = [];
    currentData = null;
}

function showError(msg) {
    const el = document.getElementById('errorBanner');
    el.textContent = '⚠ ' + msg;
    el.classList.remove('hidden');
}

function esc(s) {
    const m = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(s).replace(/[&<>"']/g, c => m[c]);
}
