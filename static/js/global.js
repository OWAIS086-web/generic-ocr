/* ── VisionRD Global Utilities ── */

function showToast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

// Common UI Initializer
document.addEventListener('DOMContentLoaded', () => {
    // Shared functionality can go here
});
