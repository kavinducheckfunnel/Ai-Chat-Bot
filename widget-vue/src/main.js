import { createApp } from 'vue'
import './style.css'
import App from './App.vue'

// Read the Client (Tenant) ID from the embedded script tag
const cfScript = document.currentScript || document.querySelector('script[data-client-id]');
window.__CF_CLIENT_ID__ = cfScript ? cfScript.getAttribute('data-client-id') : null;

// Only mount if the host div exists (which we can auto-inject if it doesn't)
let mountTarget = document.getElementById('cf-app-root');
if (!mountTarget) {
  mountTarget = document.createElement('div');
  mountTarget.id = 'cf-app-root';
  document.body.appendChild(mountTarget);
}

createApp(App).mount('#cf-app-root')
