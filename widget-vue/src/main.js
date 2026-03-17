import { createApp } from 'vue'
import './style.css'
import App from './App.vue'

// Read config from the embedded script tag
const cfScript = document.currentScript || document.querySelector('script[data-client-id]');
window.__CF_CLIENT_ID__ = cfScript ? cfScript.getAttribute('data-client-id') : null;

// Derive the backend origin from the script's own src URL so the widget always
// talks back to the correct server — even when embedded on a third-party site.
try {
  const scriptSrc = cfScript ? cfScript.src : '';
  if (scriptSrc) {
    const url = new URL(scriptSrc);
    window.__CF_BACKEND_URL__ = url.origin;   // e.g. "https://yourserver.com"
  }
} catch {
  window.__CF_BACKEND_URL__ = '';
}

// Only mount if the host div exists (which we can auto-inject if it doesn't)
let mountTarget = document.getElementById('cf-app-root');
if (!mountTarget) {
  mountTarget = document.createElement('div');
  mountTarget.id = 'cf-app-root';
  document.body.appendChild(mountTarget);
}

createApp(App).mount('#cf-app-root')
