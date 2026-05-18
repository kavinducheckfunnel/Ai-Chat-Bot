<template>
  <div class="portal-shell" v-if="ready">
    <ToastContainer />
    <ConfirmDialog />

    <!-- Announcement banners (above everything, full-width) -->
    <div v-if="announcements.length" class="announcement-stack">
      <div
        v-for="ann in announcements"
        :key="ann.id"
        class="announcement-bar"
        :class="`ann-${ann.type}`"
      >
        <span class="ann-icon">{{ annIcon(ann.type) }}</span>
        <span class="ann-body">
          <strong v-if="ann.title">{{ ann.title }}: </strong>{{ ann.body }}
          <a v-if="ann.cta_url && ann.cta_label" :href="ann.cta_url" target="_blank" class="ann-cta">{{ ann.cta_label }}</a>
        </span>
        <button v-if="ann.dismissible" class="ann-dismiss" @click="dismiss(ann.id)" aria-label="Dismiss">✕</button>
      </div>
    </div>

    <!-- Body row: sidebar + main content -->
    <div class="portal-body">
      <!-- Mobile top bar -->
      <div class="mobile-topbar">
        <button class="hamburger" @click="sidebarOpen = true" aria-label="Open menu">
          <svg width="20" height="20" fill="none" viewBox="0 0 24 24">
            <path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>
        <span class="mobile-brand">Checkfunnel</span>
      </div>

      <!-- Overlay -->
      <transition name="fade">
        <div v-if="sidebarOpen" class="overlay" @click="sidebarOpen = false" />
      </transition>

      <!-- Sidebar -->
      <PortalSidebar :client="client" :class="{ 'sidebar-open': sidebarOpen }" @close="sidebarOpen = false" />

      <main class="portal-main">
        <router-view :client="client" @client-updated="onClientUpdated" />
      </main>
    </div>
  </div>
  <div v-else class="portal-loading">
    <div class="loading-spinner"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, provide } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAdminApi } from '../composables/useAdminApi'
import PortalSidebar from './PortalSidebar.vue'
import ToastContainer from '../components/ToastContainer.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const router = useRouter()
const route = useRoute()
const api = useAdminApi()

const client = ref(null)
const ready = ref(false)
const sidebarOpen = ref(false)
const announcements = ref([])

provide('portalClient', client)

function annIcon(type) {
  return { info: 'ℹ️', warning: '⚠️', critical: '🚨', success: '✅' }[type] ?? 'ℹ️'
}

async function loadClient() {
  try {
    const c = await api.getPortalClient()
    client.value = c
    if (c && !c.onboarding_complete && route.path !== '/portal/setup') {
      router.push('/portal/setup')
    } else if (!c && route.path !== '/portal/setup') {
      router.push('/portal/setup')
    }
  } catch {
    // token issue — let router guard handle it
  } finally {
    ready.value = true
  }
}

async function loadAnnouncements() {
  try {
    const data = await api.getAnnouncements()
    announcements.value = Array.isArray(data) ? data : []
  } catch {}
}

async function dismiss(id) {
  announcements.value = announcements.value.filter(a => a.id !== id)
  try { await api.dismissAnnouncement(id) } catch {}
}

function onClientUpdated(updated) {
  client.value = { ...client.value, ...updated }
}

onMounted(() => {
  loadClient()
  loadAnnouncements()
})
</script>

<style scoped>
/* ── Shell ──────────────────────────────────────────────────────────────────── */
.portal-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0a0a0a;
  color: #e2e8f0;
  font-family: 'Inter', -apple-system, sans-serif;
  overflow: hidden;
}

/* ── Announcement banners ────────────────────────────────────────────────────── */
.announcement-stack {
  flex-shrink: 0;
  z-index: 200;
}

.announcement-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  font-size: 13px;
  line-height: 1.4;
}
.ann-info     { background: #1e3a5f; border-bottom: 1px solid rgba(37,99,235,0.3); color: #93c5fd; }
.ann-warning  { background: #451a03; border-bottom: 1px solid rgba(217,119,6,0.5); color: #fcd34d; }
.ann-critical { background: #4c0519; border-bottom: 1px solid rgba(220,38,38,0.3); color: #fca5a5; }
.ann-success  { background: #052e16; border-bottom: 1px solid rgba(22,163,74,0.3); color: #86efac; }
.ann-icon { flex-shrink: 0; font-size: 15px; }
.ann-body { flex: 1; }
.ann-body strong { font-weight: 600; }
.ann-cta { margin-left: 8px; text-decoration: underline; font-weight: 600; opacity: 0.9; }
.ann-dismiss {
  background: none; border: none; color: inherit; opacity: 0.6;
  cursor: pointer; font-size: 13px; padding: 2px 6px;
  border-radius: 4px; transition: opacity 0.15s; flex-shrink: 0;
}
.ann-dismiss:hover { opacity: 1; }

/* ── Body row (sidebar + main) ──────────────────────────────────────────────── */
.portal-body {
  display: flex;
  flex: 1;
  min-height: 0;
  position: relative;
}

.portal-main {
  flex: 1;
  overflow-y: auto;
  background: #0f0f0f;
}

/* ── Loading ─────────────────────────────────────────────────────────────────── */
.portal-loading {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0a0a;
}

.loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(255,255,255,0.08);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.mobile-topbar { display: none; }
.overlay { display: none; }

@media (max-width: 768px) {
  .portal-body {
    flex-direction: column;
    overflow: hidden;
  }

  .mobile-topbar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 16px;
    background: #111111;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    position: sticky;
    top: 0;
    z-index: 50;
    flex-shrink: 0;
  }

  .hamburger {
    background: none;
    border: none;
    color: #cbd5e1;
    cursor: pointer;
    padding: 4px;
    display: flex;
    align-items: center;
    border-radius: 6px;
    transition: background 0.15s;
  }
  .hamburger:hover { background: rgba(255,255,255,0.08); }

  .mobile-brand {
    font-size: 15px;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: -0.3px;
  }

  .overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.6);
    z-index: 99;
  }

  .portal-main {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
  }

  :deep(.sidebar) {
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    z-index: 100;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
  }

  :deep(.sidebar.sidebar-open) {
    transform: translateX(0);
  }
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
