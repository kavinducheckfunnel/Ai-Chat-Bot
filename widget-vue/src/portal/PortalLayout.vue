<template>
  <div class="portal-shell" v-if="ready">
    <PortalSidebar :client="client" />
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

provide('portalClient', client)

async function loadClient() {
  try {
    const c = await api.getPortalClient()
    client.value = c
    // Redirect to onboarding wizard if not yet complete
    if (c && !c.onboarding_complete && route.path !== '/portal/setup') {
      router.push('/portal/setup')
    } else if (!c && route.path !== '/portal/setup') {
      // No client assigned yet — stay on setup
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

/* Mobile: stack sidebar above main content */
@media (max-width: 768px) {
  .portal-shell {
    flex-direction: column;
    height: auto;
    min-height: 100vh;
  }
  .portal-main {
    overflow-y: visible;
  }
}
</style>
