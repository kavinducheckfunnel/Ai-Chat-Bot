import { createApp } from 'vue'
import './style.css'
import App from './App.vue'

// ── Debug logging ────────────────────────────────────────────────────────────
function cfLog(...args) {
  if (typeof console !== 'undefined') console.log('[CF Widget]', ...args);
}

// ── Globals may already be injected by the server (via ?client_id= query param)
// When the script is served as /widget/widget.js?client_id=xxx, the Django view
// prepends:  window.__CF_CLIENT_ID__="xxx"; window.__CF_BACKEND_URL__="...";
// to the JS bytes.  In that case we skip the document.currentScript dance
// entirely — the values are already correct regardless of defer/async/bundling.
if (!window.__CF_CLIENT_ID__) {
  // Fallback: read data-client-id from the <script> tag that loaded us.
  // document.currentScript is reliable for synchronous scripts; fall back to
  // a DOM query for deferred / async cases.
  let cfScript = document.currentScript;
  if (!cfScript || !cfScript.getAttribute('data-client-id')) {
    cfScript = document.querySelector('script[data-client-id]');
  }

  window.__CF_CLIENT_ID__ = cfScript ? cfScript.getAttribute('data-client-id') : null;

  // Derive backend origin from the script's own src so cross-origin embeds
  // always talk to the right server.
  try {
    const scriptSrc = cfScript ? cfScript.src : '';
    if (scriptSrc) {
      const url = new URL(scriptSrc);
      window.__CF_BACKEND_URL__ = url.origin;
    }
  } catch {
    window.__CF_BACKEND_URL__ = '';
  }
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
      mountTarget.style.cssText = 'all:initial;position:fixed;bottom:0;right:0;z-index:2147483647;';
      document.body.appendChild(mountTarget);
    }
    createApp(App).mount('#cf-app-root');
    cfLog('Mounted successfully');
  } catch (e) {
    cfLog('Mount error:', e);
  }
}

if (document.body) {
  mount();
} else {
  document.addEventListener('DOMContentLoaded', mount);
  cfLog('Deferred mount — waiting for DOMContentLoaded');
}
