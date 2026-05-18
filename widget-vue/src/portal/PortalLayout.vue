<template>
  <div class="portal-shell" v-if="ready">
    <ToastContainer />
    <ConfirmDialog />

    <!-- Announcement cards (floating overlay, top-right) -->
    <teleport to="body">
      <transition-group name="ann-card" tag="div" class="ann-tray" v-if="announcements.length">
        <div
          v-for="ann in announcements"
          :key="ann.id"
          class="ann-card"
          :class="`ann-${ann.type}`"
        >
          <div class="ann-accent" />
          <div class="ann-icon-wrap">
            <!-- info -->
            <svg v-if="ann.type === 'info'" viewBox="0 0 20 20" fill="none" width="16" height="16"><circle cx="10" cy="10" r="9" stroke="currentColor" stroke-width="1.5"/><line x1="10" y1="9" x2="10" y2="14" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/><circle cx="10" cy="6.5" r="0.75" fill="currentColor"/></svg>
            <!-- warning -->
            <svg v-else-if="ann.type === 'warning'" viewBox="0 0 20 20" fill="none" width="16" height="16"><path d="M10 3L18 17H2L10 3z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><line x1="10" y1="9" x2="10" y2="12.5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/><circle cx="10" cy="14.5" r="0.75" fill="currentColor"/></svg>
            <!-- critical -->
            <svg v-else-if="ann.type === 'critical'" viewBox="0 0 20 20" fill="none" width="16" height="16"><circle cx="10" cy="10" r="9" stroke="currentColor" stroke-width="1.5"/><line x1="10" y1="6" x2="10" y2="11" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/><circle cx="10" cy="13.5" r="0.75" fill="currentColor"/></svg>
            <!-- success -->
            <svg v-else viewBox="0 0 20 20" fill="none" width="16" height="16"><circle cx="10" cy="10" r="9" stroke="currentColor" stroke-width="1.5"/><path d="M6.5 10.5l2.5 2.5 4.5-5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <div class="ann-content">
            <p class="ann-title" v-if="ann.title">{{ ann.title }}</p>
            <p class="ann-body">{{ ann.body }}</p>
            <a v-if="ann.cta_url && ann.cta_label" :href="ann.cta_url" target="_blank" class="ann-cta">
              {{ ann.cta_label }}
              <svg viewBox="0 0 12 12" fill="none" width="10" height="10"><path d="M2.5 9.5l7-7M4 2.5h5.5v5.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </a>
          </div>
          <button v-if="ann.dismissible" class="ann-close" @click="dismiss(ann.id)" aria-label="Dismiss">
            <svg viewBox="0 0 12 12" fill="none" width="11" height="11"><path d="M1 1l10 10M11 1L1 11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
        </div>
      </transition-group>
    </teleport>

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
  background: var(--cf-bg-page);
  color: var(--cf-text-primary);
  font-family: 'Inter', -apple-system, sans-serif;
  overflow: hidden;
  transition: background 0.2s;
}

/* ── Announcement cards (floating tray, teleported to body) ─────────────────── */

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
  background: var(--cf-bg-page);
}

/* ── Loading ─────────────────────────────────────────────────────────────────── */
.portal-loading {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--cf-bg-page);
}

.loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--cf-border-subtle);
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
    background: var(--cf-bg-topbar);
    border-bottom: 1px solid var(--cf-border-subtle);
    position: sticky;
    top: 0;
    z-index: 50;
    flex-shrink: 0;
  }

  .hamburger {
    background: none;
    border: none;
    color: var(--cf-text-secondary);
    cursor: pointer;
    padding: 4px;
    display: flex;
    align-items: center;
    border-radius: 6px;
    transition: background 0.15s;
  }
  .hamburger:hover { background: var(--cf-bg-ghost-hover); }

  .mobile-brand {
    font-size: 15px;
    font-weight: 700;
    color: var(--cf-text-primary);
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

<style>
/* ── Announcement tray (global — teleported outside scoped component) ─────── */
.ann-tray {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9500;
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 360px;
  pointer-events: none;
}

.ann-card {
  pointer-events: all;
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 16px 16px 0;
  background: rgba(15, 15, 22, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45), 0 2px 8px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

/* Colored left accent stripe */
.ann-accent {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  border-radius: 14px 0 0 14px;
}
.ann-info    .ann-accent  { background: linear-gradient(180deg, #6366f1, #3b82f6); }
.ann-warning .ann-accent  { background: linear-gradient(180deg, #f59e0b, #ef4444); }
.ann-critical .ann-accent { background: linear-gradient(180deg, #ef4444, #dc2626); }
.ann-success .ann-accent  { background: linear-gradient(180deg, #22c55e, #10b981); }

/* Icon badge */
.ann-icon-wrap {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 14px;
}
.ann-info    .ann-icon-wrap { background: rgba(99, 102, 241, 0.15); color: #818cf8; }
.ann-warning .ann-icon-wrap { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.ann-critical .ann-icon-wrap { background: rgba(239, 68, 68, 0.15); color: #f87171; }
.ann-success .ann-icon-wrap { background: rgba(34, 197, 94, 0.15); color: #4ade80; }

/* Content */
.ann-content {
  flex: 1;
  min-width: 0;
  padding-top: 1px;
}
.ann-content .ann-title {
  margin: 0 0 3px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: -0.1px;
  line-height: 1.3;
}
.ann-content .ann-body {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.5;
  opacity: 0.75;
}
.ann-info    .ann-content .ann-title { color: #c7d2fe; }
.ann-warning .ann-content .ann-title { color: #fde68a; }
.ann-critical .ann-content .ann-title { color: #fecaca; }
.ann-success .ann-content .ann-title { color: #bbf7d0; }
.ann-info    .ann-content .ann-body { color: #a5b4fc; }
.ann-warning .ann-content .ann-body { color: #fcd34d; }
.ann-critical .ann-content .ann-body { color: #fca5a5; }
.ann-success .ann-content .ann-body { color: #86efac; }

/* CTA button */
.ann-cta {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 600;
  text-decoration: none;
  transition: opacity 0.15s, transform 0.15s;
  letter-spacing: 0.1px;
}
.ann-cta:hover { opacity: 0.85; transform: translateY(-1px); }
.ann-info    .ann-cta { background: rgba(99, 102, 241, 0.2); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.3); }
.ann-warning .ann-cta { background: rgba(245, 158, 11, 0.2); color: #fde68a; border: 1px solid rgba(245,158,11,0.3); }
.ann-critical .ann-cta { background: rgba(239, 68, 68, 0.2); color: #fecaca; border: 1px solid rgba(239,68,68,0.3); }
.ann-success .ann-cta { background: rgba(34, 197, 94, 0.2); color: #bbf7d0; border: 1px solid rgba(34,197,94,0.3); }

/* Close button */
.ann-close {
  flex-shrink: 0;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  margin: 0 4px 0 0;
  border-radius: 6px;
  color: rgba(255,255,255,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.15s, background 0.15s;
  align-self: flex-start;
  margin-top: 2px;
}
.ann-close:hover { color: rgba(255,255,255,0.8); background: rgba(255,255,255,0.06); }

/* Enter/leave transitions */
.ann-card-enter-active { transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.ann-card-leave-active { transition: all 0.2s ease; }
.ann-card-enter-from  { opacity: 0; transform: translateX(24px) scale(0.97); }
.ann-card-leave-to    { opacity: 0; transform: translateX(16px) scale(0.97); }
.ann-card-move        { transition: transform 0.25s ease; }

/* Mobile */
@media (max-width: 768px) {
  .ann-tray {
    top: auto;
    bottom: 80px;
    right: 12px;
    left: 12px;
    width: auto;
  }
  .ann-card {
    border-radius: 12px;
  }
}
</style>
