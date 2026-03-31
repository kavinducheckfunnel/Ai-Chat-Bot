import { createApp } from 'vue'
import './style.css'
import App from './App.vue'

// ── Debug logging ────────────────────────────────────────────────────────────
function cfLog(...args) {
  if (typeof console !== 'undefined') console.log('[CF Widget]', ...args);
}

// ── Read config from the <script> tag ────────────────────────────────────────
// Try document.currentScript first (reliable during synchronous execution),
// then fall back to querying the DOM for any script with data-client-id.
let cfScript = document.currentScript;
if (!cfScript || !cfScript.getAttribute('data-client-id')) {
  cfScript = document.querySelector('script[data-client-id]');
}

window.__CF_CLIENT_ID__ = cfScript ? cfScript.getAttribute('data-client-id') : null;

// Derive the backend origin from the script's own src URL so the widget always
// talks back to the correct server — even when embedded on a third-party site.
try {
  const scriptSrc = cfScript ? cfScript.src : '';
  if (scriptSrc) {
    const url = new URL(scriptSrc);
    window.__CF_BACKEND_URL__ = url.origin;
  }
} catch {
  window.__CF_BACKEND_URL__ = '';
}

cfLog('Client ID:', window.__CF_CLIENT_ID__);
cfLog('Backend URL:', window.__CF_BACKEND_URL__);

// ── Mount the Vue app ────────────────────────────────────────────────────────
function mount() {
  try {
    let mountTarget = document.getElementById('cf-app-root');
    if (!mountTarget) {
      mountTarget = document.createElement('div');
      mountTarget.id = 'cf-app-root';
      // Reset all styles on the root div to avoid WordPress theme interference
      mountTarget.style.cssText = 'all:initial;position:fixed;bottom:0;right:0;z-index:2147483647;';
      document.body.appendChild(mountTarget);
    }
    createApp(App).mount('#cf-app-root');
    cfLog('Mounted successfully');
  } catch (e) {
    cfLog('Mount error:', e);
  }
}

// Guard: ensure document.body exists before mounting.
// WordPress optimization plugins can defer/async scripts, and some insert
// scripts into <head> — in which case document.body may not yet exist.
if (document.body) {
  mount();
} else {
  document.addEventListener('DOMContentLoaded', mount);
  cfLog('Deferred mount — waiting for DOMContentLoaded');
}
