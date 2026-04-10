/* ── Quick Sample Page Logic ── */

let stepTimer = null;

function getIsKvMode() {
    const structSetting = localStorage.getItem('aiStructuring');
    return structSetting === null ? true : structSetting === 'true';
}

function getIsTableMode() {
    return localStorage.getItem('tableMode') === 'true';
}

function getShowAnnotatedImage() {
    const s = localStorage.getItem('showAnnotatedImage');
    return s === null ? true : s === 'true';
}

function getAutoClassify() {
    return localStorage.getItem('autoClassify') === 'true';
}

function processImage(filename) {
    // Show processing UI
    document.getElementById('gallerySection').style.display = 'none';
    document.getElementById('processingSection').style.display = 'block';
    document.getElementById('resultSection').style.display = 'none';
    document.getElementById('processingName').textContent = 'Running OCR on: ' + filename;

    // Reset steps
    ['step1','step2','step3','step4'].forEach(s => {
        const el = document.getElementById(s);
        if (el) el.className = 'process-step';
    });
    
    const step1 = document.getElementById('step1');
    if (step1) step1.classList.add('active');

    const isClass = getAutoClassify();
    const isKv = getIsKvMode();
    
    const step3 = document.getElementById('step3');
    const step4 = document.getElementById('step4');
    if (step3) step3.style.display = isClass ? 'inline-flex' : 'none';
    if (step4) step4.style.display = isKv ? 'inline-flex' : 'none';

    let stepIdx = 0;
    const steps = ['step1', 'step2'];
    if (isClass) steps.push('step3');
    if (isKv) steps.push('step4');

    if (stepTimer) clearInterval(stepTimer);
    stepTimer = setInterval(() => {
        stepIdx++;
        if (stepIdx < steps.length) {
            const prev = document.getElementById(steps[stepIdx-1]);
            const curr = document.getElementById(steps[stepIdx]);
            if (prev) {
                prev.classList.remove('active');
                prev.classList.add('done');
            }
            if (curr) curr.classList.add('active');
        }
    }, 2800);

    // Fetch image from /data/ and send as file to /process
    fetch('/data/' + encodeURIComponent(filename))
        .then(r => r.blob())
        .then(blob => {
            const formData = new FormData();
            formData.append('file', blob, filename);
            formData.append('extract_kv', getIsKvMode());
            formData.append('extract_tables_only', getIsTableMode());
            formData.append('annotate_image', getShowAnnotatedImage());
            formData.append('auto_classify', getAutoClassify());
            return fetch('/process', { method: 'POST', body: formData });
        })
        .then(r => r.json())
        .then(data => {
            clearInterval(stepTimer);
            steps.forEach(s => {
                const el = document.getElementById(s);
                if (el) el.className = 'process-step done';
            });
            document.getElementById('processingSection').style.display = 'none';
            document.getElementById('resultSection').style.display = 'block';
            showResult(data, filename);
        })
        .catch(err => {
            clearInterval(stepTimer);
            document.getElementById('processingSection').style.display = 'none';
            document.getElementById('resultSection').style.display = 'block';
            const errorEl = document.getElementById('resultError');
            errorEl.textContent = '⚠ ' + err.message;
            errorEl.classList.remove('hidden');
            document.getElementById('resultImg').src = '/data/' + encodeURIComponent(filename);
            document.getElementById('resultImgName').textContent = filename;
        });
}

function showResult(data, filename) {
    const showImg = getShowAnnotatedImage();
    const previewEl = document.querySelector('.selected-preview');

    if (showImg) {
        document.getElementById('resultImg').src = '/data/' + encodeURIComponent(filename);
        previewEl.style.display = 'flex';
    } else {
        previewEl.style.display = 'none';
    }

    document.getElementById('resultImgName').textContent = filename;
    document.getElementById('resultName').textContent = 'File: ' + filename;
    document.getElementById('resultError').classList.add('hidden');

    if (data.status !== 'success') {
        const errorEl = document.getElementById('resultError');
        errorEl.textContent = '⚠ ' + (data.message || 'Processing failed');
        errorEl.classList.remove('hidden');
        return;
    }

    const kv     = data.key_value_pairs || {};
    const tables = data.tables || [];
    const raw    = data.raw_text || '';
    const t      = data.timings || {};
    const total  = (t.total || 0).toFixed(2);

    document.getElementById('resultTimeBadge').textContent = '⏱ ' + total + 's';
    document.getElementById('rTimePre').textContent   = (t.preprocessing || 0).toFixed(2) + 's';
    document.getElementById('rTimeExt').textContent   = (t.structured_extraction || t.text_extraction || 0).toFixed(2) + 's';
    document.getElementById('rTimeLLM').textContent   = (t.structuring || t.llm_structuring || 0).toFixed(2) + 's';
    document.getElementById('rTimeTotal').textContent = total + 's';
    document.getElementById('resultImgMsg').textContent = Object.keys(kv).length + ' fields, ' + tables.length + ' tables extracted';

    // KV
    const kvCont = document.getElementById('rKvContainer');
    kvCont.innerHTML = '';
    if (Object.keys(kv).length > 0) {
        Object.keys(kv).sort().forEach(key => {
            const div = document.createElement('div');
            div.className = 'kv-item nexus-deboss';
            div.style.padding = '12px 16px';
            div.style.borderRadius = '12px';
            div.style.background = 'rgba(0,0,0,0.2)';
            
            const val = String(kv[key]);
            const isArabic = /[\u0600-\u06FF]/.test(val + key);
            div.innerHTML = `<div class="kv-key" ${isArabic ? 'dir="rtl"' : ''} style="font-size:0.75em; opacity:0.6; text-transform:uppercase;">${esc(key)}</div>
                             <div class="kv-value" ${isArabic ? 'dir="rtl" style="text-align:right"' : ''} style="font-weight:700;">${esc(val)}</div>`;
            kvCont.appendChild(div);
        });
        document.getElementById('rKvSection').style.display = 'block';
    } else {
        document.getElementById('rKvSection').style.display = 'none';
    }

    // Tables
    const tblCont = document.getElementById('rTableContainer');
    tblCont.innerHTML = '';
    if (tables.length > 0) {
        tables.forEach((table, idx) => {
            if (table.headers && Array.isArray(table.headers) && table.rows && Array.isArray(table.rows)) {
                const wrap = document.createElement('div');
                wrap.className = 'data-table-wrap nexus-deboss';
                wrap.style.borderRadius = '16px';
                wrap.style.overflow = 'hidden';
                wrap.style.marginBottom = '20px';
                
                let html = `<div class="data-table-head" style="background:rgba(255,255,255,0.03); padding:12px 20px; border-bottom:1px solid rgba(255,255,255,0.05);">
                              <span style="font-weight:700; font-size:0.9em; color:var(--text-faint);">📊 ${esc(table.name || 'Table ' + (idx+1))}</span>
                            </div>
                            <div style="overflow-x:auto;">
                              <table class="data-table" style="width:100%; border-collapse:collapse;">
                                <thead><tr style="background:rgba(0,0,0,0.2);">`;
                table.headers.forEach(h => html += `<th style="text-align:left; padding:12px 20px; font-size:0.8em; color:var(--text-muted);">${esc(String(h))}</th>`);
                html += '</tr></thead><tbody>';
                table.rows.forEach(row => {
                    html += '<tr style="border-top:1px solid rgba(255,255,255,0.03);">';
                    if (Array.isArray(row)) row.forEach(c => html += `<td style="padding:12px 20px; font-size:0.9em; color:#fff;">${esc(String(c))}</td>`);
                    html += '</tr>';
                });
                html += '</tbody></table></div>';
                wrap.innerHTML = html;
                tblCont.appendChild(wrap);
            }
        });
        document.getElementById('rTableSection').style.display = 'block';
    } else {
        document.getElementById('rTableSection').style.display = 'none';
    }

    // Raw
    const rawCont = document.getElementById('rRawText');
    if (raw) {
        rawCont.innerHTML = typeof marked !== 'undefined' ? marked.parse(raw) : esc(raw);
        document.getElementById('rRawSection').style.display = 'block';
        if (/[\u0600-\u06FF]/.test(raw)) {
            rawCont.setAttribute('dir', 'rtl');
            rawCont.style.textAlign = 'right';
        }
    } else {
        document.getElementById('rRawSection').style.display = 'none';
    }

    showToast('✅ OCR complete for ' + filename);
}

function backToGallery() {
    document.getElementById('gallerySection').style.display = 'block';
    document.getElementById('processingSection').style.display = 'none';
    document.getElementById('resultSection').style.display = 'none';
    ['rKvSection','rTableSection','rRawSection'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
}

function esc(s) {
    const m = {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'};
    return String(s).replace(/[&<>"']/g, c => m[c]);
}

function showToast(msg) {
    const t = document.getElementById('toast');
    if (t) {
        t.textContent = msg;
        t.classList.add('show');
        setTimeout(() => t.classList.remove('show'), 3500);
    } else {
        console.log('Toast:', msg);
    }
}
