/* ── History Page Logic ── */

function viewRecord(id) {
    const modal = document.getElementById('detailModal');
    const title = document.getElementById('modalTitle');
    const body = document.getElementById('modalBody');

    title.textContent = 'Loading…';
    body.innerHTML = '<div class="flex-center" style="padding:60px 0;"><div class="spinner"></div></div>';
    modal.classList.add('open');

    fetch(`/history/${id}`)
        .then(r => r.json())
        .then(data => {
            if (data.status !== 'success') {
                showToast('⚠ Failed to load record');
                return;
            }
            const r = data.record;
            title.textContent = '📄 ' + r.filename;
            let html = `<div class="badge badge-accent nexus-deboss" style="margin-bottom:16px;">Type: ${esc(r.doc_type || 'General')}</div>`;

            const kv = r.key_value_pairs || {};
            if (Object.keys(kv).length > 0) {
                html += '<div class="section-label" style="margin-bottom:16px;">🔑 Key-Value Pairs</div>';
                html += '<div class="kv-grid">';
                for (const [k, v] of Object.entries(kv)) {
                    const isAr = /[\u0600-\u06FF]/.test(k + v);
                    html += `<div class="kv-item nexus-deboss" style="background:rgba(0,0,0,0.2); border-radius:12px; padding:12px 16px; margin-bottom:8px;">
                      <div class="kv-key" ${isAr ? 'dir="rtl"' : ''} style="font-size:0.75em; opacity:0.6; text-transform:uppercase;">${esc(k)}</div>
                      <div class="kv-value" ${isAr ? 'dir="rtl"' : ''} style="font-weight:700;">${esc(String(v))}</div>
                    </div>`;
                }
                html += '</div><div class="glow-divider" style="margin:24px 0;"></div>';
            }

            if (r.raw_text) {
                html += '<div class="section-label" style="margin-bottom:16px;">📄 Raw OCR Text</div>';
                html += `<div class="raw-text-block nexus-deboss" style="padding:20px; border-radius:12px; white-space:pre-wrap; font-size:0.9em; max-height:400px; overflow-y:auto;">${marked.parse(r.raw_text)}</div>`;
            }

            body.innerHTML = html;
        })
        .catch(e => {
            body.innerHTML = `<p style="color:var(--nexus-red)">⚠ ${e.message}</p>`;
        });
}

function closeModal() {
    document.getElementById('detailModal').classList.remove('open');
}

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('detailModal');
    if (modal) {
        modal.addEventListener('click', e => {
            if (e.target === modal) closeModal();
        });
    }
});

function deleteRecord(id) {
    if (!confirm('Archive this dossier? Data will be permanently purged.')) return;
    fetch(`/history/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(d => {
            if (d.status === 'success') {
                const card = document.getElementById('card-' + id);
                if (card) {
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.9)';
                    setTimeout(() => card.remove(), 400);
                }
                showToast('📂 Dossier archived.');
            } else {
                showToast('⚠ Archiving failed.');
            }
        });
}

function filterHistory() {
    const query = document.getElementById('historySearch').value.toLowerCase();
    const cards = document.querySelectorAll('.dossier-card');
    cards.forEach(c => {
        const name = c.dataset.name;
        const type = c.dataset.type;
        c.style.display = (name.includes(query) || type.includes(query)) ? 'flex' : 'none';
    });
}

function clearAllHistory() {
    if (!confirm('Delete ALL scan history? This cannot be undone.')) return;
    showToast('⏳ Cleaning repository...');
    // Implementation for bulk delete if backend supports it, otherwise reload
    location.reload();
}

function esc(s) {
    const m = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(s).replace(/[&<>"']/g, c => m[c]);
}
