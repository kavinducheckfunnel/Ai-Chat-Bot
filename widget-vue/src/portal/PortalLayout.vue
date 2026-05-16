<template>
  <div class="portal-shell" v-if="ready">
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
  <div v-else class="portal-loading">
    <div class="loading-spinner"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, provide } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAdminApi } from '../composables/useAdminApi'
import PortalSidebar from './PortalSidebar.vue'

const router = useRouter()
const route = useRoute()
const api = useAdminApi()

const client = ref(null)
const ready = ref(false)
const sidebarOpen = ref(false)

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

function onClientUpdated(updated) {
  client.value = { ...client.value, ...updated }
}

onMounted(loadClient)
</script>

<style scoped>
.portal-shell {
  display: flex;
  height: 100vh;
  background: #0a0a0a;
  color: #e2e8f0;
  font-family: 'Inter', -apple-system, sans-serif;
}

.portal-main {
  flex: 1;
  overflow-y: auto;
  background: #0f0f0f;
}

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
  .portal-shell {
    flex-direction: column;
    height: 100vh;
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
