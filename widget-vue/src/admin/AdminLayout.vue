<template>
  <div class="layout">
    <ToastContainer />
    <ConfirmDialog />

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

    <!-- Sidebar (drawer on mobile) -->
    <transition name="slide">
      <Sidebar :class="{ 'sidebar-open': sidebarOpen }" @close="sidebarOpen = false" />
    </transition>

    <div class="main" @click="sidebarOpen && (sidebarOpen = false)">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Sidebar from './Sidebar.vue'
import ToastContainer from '../components/ToastContainer.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const sidebarOpen = ref(false)
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--cf-bg-page);
  transition: background 0.2s;
}

.main {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
}

.mobile-topbar {
  display: none;
}

.overlay {
  display: none;
}

@media (max-width: 768px) {
  .layout {
    flex-direction: column;
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

  .hamburger:hover {
    background: var(--cf-bg-ghost-hover);
  }

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
    background: rgba(0,0,0,0.55);
    z-index: 99;
  }

  .main {
    padding: 20px 16px;
    /* full height minus topbar */
    height: calc(100vh - 53px);
    overflow-y: auto;
  }
}

/* Sidebar drawer positioning on mobile */
@media (max-width: 768px) {
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

/* Transition: overlay fade */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* Transition: sidebar slide (only applies on mobile via the deep selector above) */
.slide-enter-active, .slide-leave-active { transition: none; }
</style>
