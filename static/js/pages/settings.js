/* ── Settings Page Logic ── */

document.addEventListener('DOMContentLoaded', () => {
  applyToggle('kvModeSetting', 'aiStructuring', true, 'kvLabel');
  applyToggle('tableModeSetting', 'tableMode', false, 'tableLabel');
  applyToggle('showAnnotatedImgSetting', 'showAnnotatedImage', true, 'annLabel');
  applyToggle('autoClassifySetting', 'autoClassify', true, 'classLabel');
  
  // Load path
  const pathInput = document.getElementById('serverBulkPathInput');
  if (pathInput) {
    pathInput.value = localStorage.getItem('serverBulkPath') || 'data/';
  }
});

function applyToggle(elId, key, defaultVal, labelId) {
  const el = document.getElementById(elId);
  if (!el) return;
  const raw = localStorage.getItem(key);
  const val = raw === null ? defaultVal : raw === 'true';
  el.checked = val;
  if (labelId) document.getElementById(labelId).textContent = val ? 'ON' : 'OFF';
}

function saveSetting(key, isEnabled) {
  localStorage.setItem(key, isEnabled ? 'true' : 'false');
  // Update status labels
  const map = { aiStructuring: 'kvLabel', tableMode: 'tableLabel', showAnnotatedImage: 'annLabel', autoClassify: 'classLabel' };
  if (map[key] && document.getElementById(map[key])) {
    document.getElementById(map[key]).textContent = isEnabled ? 'ON' : 'OFF';
  }
  showToast(`✅ ${key} → ${isEnabled ? 'Enabled' : 'Disabled'}`);
}
