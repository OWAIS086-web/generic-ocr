/* ── Edit Page Logic ── */

let editType = 'kv';
let editData = null;
let tableIndex = null;

function getQ(name) { return new URL(window.location).searchParams.get(name); }

function initEdit() {
    editType   = getQ('type') || 'kv';
    tableIndex = getQ('index');
    const raw  = getQ('data');

    if (!raw) {
        showToast('⚠ No data to edit');
        setTimeout(goBack, 2000);
        return;
    }

    try {
        editData = JSON.parse(decodeURIComponent(raw));
    } catch(e) {
        showToast('⚠ Error parsing data');
        setTimeout(goBack, 2000);
        return;
    }

    if (editType === 'kv') showKVEdit();
    else if (editType === 'table') showTableEdit();
}

function showKVEdit() {
    const title = document.getElementById('pageTitle');
    const subtitle = document.getElementById('pageSubtitle');
    const section = document.getElementById('kvEditSection');
    
    if (title) title.innerHTML = 'Edit <span>Key-Values</span>';
    if (subtitle) subtitle.textContent = 'Modify the extracted key-value pairs';
    if (section) section.style.display = 'block';

    const kv   = editData.key_value_pairs || {};
    const cont = document.getElementById('kvEditContainer');
    if (!cont) return;
    cont.innerHTML = '';

    for (const [key, value] of Object.entries(kv)) {
        const div = document.createElement('div');
        div.className = 'kv-edit-card nexus-emboss';
        div.style.borderRadius = '20px';
        div.style.padding = '24px';
        div.innerHTML = `
            <div class="form-group">
                <label>Key</label>
                <input type="text" class="nexus-deboss" value="${esc(key)}" readonly style="background:rgba(0,0,0,0.2) !important;">
            </div>
            <div class="form-group" style="margin-top:16px;">
                <label>Value</label>
                <textarea class="nexus-deboss" data-key="${esc(key)}" style="background:rgba(0,0,0,0.2) !important; min-height:80px;">${esc(String(value))}</textarea>
            </div>`;
        cont.appendChild(div);
    }
}

function showTableEdit() {
    const title = document.getElementById('pageTitle');
    const subtitle = document.getElementById('pageSubtitle');
    const section = document.getElementById('tableEditSection');

    if (title) title.innerHTML = 'Edit <span>Tables</span>';
    if (subtitle) subtitle.textContent = 'Modify table data and structure';
    if (section) section.style.display = 'block';

    const tables = editData.tables || [];
    const cont   = document.getElementById('tableEditContainer');
    if (!cont) return;
    cont.innerHTML = '';

    tables.forEach((table, idx) => {
        if (tableIndex !== null && tableIndex != idx) return;

        const card = document.createElement('div');
        card.className = 'table-edit-card nexus-emboss';
        card.style.borderRadius = '28px';
        card.style.overflow = 'hidden';

        let html = `<div class="table-edit-head" style="background:rgba(255,255,255,0.03); padding:20px 28px; border-bottom:1px solid rgba(255,255,255,0.05);">
            <span style="font-weight:700; font-size:0.9em; color:var(--text-faint);">📊 ${esc(table.name || 'Table ' + (idx+1))}</span>
            <button class="btn btn-primary btn-sm" onclick="addTableRow(${idx})">+ Add Row</button>
        </div>
        <div class="table-edit-body" style="padding:28px;">
            <div style="margin-bottom:24px;">
                <div class="row-label" style="font-size:0.7em; opacity:0.6; margin-bottom:12px;">Column Headers</div>
                <div class="col-grid">`;

        table.headers.forEach((h, hIdx) => {
            html += `<input type="text" class="table-header-input nexus-deboss"
                       data-table="${idx}" data-index="${hIdx}"
                       value="${esc(String(h))}" placeholder="Header ${hIdx+1}" style="background:rgba(0,0,0,0.2) !important;">`;
        });

        html += `</div></div><div class="row-label" style="font-size:0.7em; opacity:0.6; margin-bottom:12px;">Rows</div>`;

        table.rows.forEach((row, rIdx) => {
            html += `<div class="row-block nexus-deboss" style="padding:20px; border-radius:16px; margin-bottom:16px; background:rgba(0,0,0,0.1) !important;">
                <div class="flex-between" style="margin-bottom:12px;">
                    <div class="row-label" style="font-size:0.65em; opacity:0.5;">Row ${rIdx + 1}</div>
                    <button class="btn btn-ghost btn-sm" style="color:var(--nexus-red); font-size:0.7em;" onclick="deleteTableRow(${idx},${rIdx})">Delete</button>
                </div>
                <div class="col-grid">`;
            row.forEach((cell, cIdx) => {
                html += `<input type="text" class="table-cell-input nexus-deboss"
                           data-table="${idx}" data-row="${rIdx}" data-col="${cIdx}"
                           value="${esc(String(cell))}" placeholder="Cell" style="background:rgba(0,0,0,0.2) !important;">`;
            });
            html += `</div></div>`;
        });

        html += `</div>`;
        card.innerHTML = html;
        cont.appendChild(card);
    });
}

function addTableRow(tableIdx) {
    const table = editData.tables[tableIdx];
    if (!table) return;
    table.rows.push(new Array(table.headers.length).fill(''));
    showTableEdit();
}

function deleteTableRow(tableIdx, rowIdx) {
    if (!confirm('Delete this row?')) return;
    editData.tables[tableIdx].rows.splice(rowIdx, 1);
    showTableEdit();
}

function saveChanges() {
    if (editType === 'kv') {
        document.querySelectorAll('textarea[data-key]').forEach(ta => {
            editData.key_value_pairs[ta.getAttribute('data-key')] = ta.value;
        });
    } else if (editType === 'table') {
        document.querySelectorAll('.table-header-input').forEach(inp => {
            editData.tables[+inp.dataset.table].headers[+inp.dataset.index] = inp.value;
        });
        document.querySelectorAll('.table-cell-input').forEach(inp => {
            editData.tables[+inp.dataset.table].rows[+inp.dataset.row][+inp.dataset.col] = inp.value;
        });
    }

    sessionStorage.setItem('editedData', JSON.stringify(editData));
    showToast('✅ Changes saved locally!');
    setTimeout(goBack, 1000);
}

function goBack() { window.history.back(); }

function esc(s) {
    const m = {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'};
    return String(s).replace(/[&<>"']/g, c => m[c]);
}

window.addEventListener('load', initEdit);
