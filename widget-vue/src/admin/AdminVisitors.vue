<template>
  <div class="av-page">
    <div class="av-header">
      <div>
        <h1 class="av-title">Visitors</h1>
        <p class="av-sub">Browse every visitor across any tenant — cross-tenant explorer</p>
      </div>
      <div class="av-actions">
        <!-- Tenant picker: superadmin operates one client at a time -->
        <select v-model="selectedClientId" class="av-client-select" @change="onClientChange">
          <option value="">Select a client…</option>
          <option v-for="c in clients" :key="c.id" :value="c.id">
            {{ c.name }}
          </option>
        </select>
      </div>
    </div>

    <div v-if="loadingClients" class="av-loading">
      <div class="av-spinner"></div>
    </div>

    <div v-else-if="!selectedClient" class="av-empty">
      <div class="av-empty-icon">
        <svg width="42" height="42" fill="none" viewBox="0 0 24 24">
          <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <circle cx="9" cy="7" r="4" stroke="currentColor" stroke-width="1.5"/>
        </svg>
      </div>
      <p class="av-empty-msg">Pick a client above to see their visitors</p>
    </div>

    <!--
      PortalVisitors expects :client as a prop and calls
      api.getClientVisitors(client.id) which works cross-tenant via the
      /api/admin/clients/<id>/visitors/ endpoint. Re-keying on client id
      forces a clean unmount/mount whenever the tenant picker changes so
      we don't show stale rows from the previous tenant.
    -->
    <PortalVisitors v-else :key="selectedClient.id" :client="selectedClient" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'
import PortalVisitors from '../portal/PortalVisitors.vue'

const api = useAdminApi()
const clients = ref([])
const loadingClients = ref(true)
const selectedClientId = ref('')

const selectedClient = computed(() =>
  clients.value.find(c => c.id === selectedClientId.value) || null
)

const STORAGE_KEY = 'cf_admin_visitors_last_client'

function onClientChange() {
  try { localStorage.setItem(STORAGE_KEY, selectedClientId.value || '') } catch {}
}

onMounted(async () => {
  try {
    clients.value = (await api.getClients()) || []
    // Restore last selected so the page remembers context across visits
    const last = localStorage.getItem(STORAGE_KEY)
    if (last && clients.value.some(c => c.id === last)) {
      selectedClientId.value = last
    } else if (clients.value.length === 1) {
      // Convenience: auto-pick if only one tenant exists
      selectedClientId.value = clients.value[0].id
    }
  } catch (e) {
    console.error(e)
  } finally {
    loadingClients.value = false
  }
})
</script>

<style scoped>
.av-page { padding: 24px 32px; }

.av-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 24px; gap: 16px; flex-wrap: wrap;
}

.av-title { font-size: 22px; font-weight: 700; color: var(--cf-text-primary); letter-spacing: -0.4px; }
.av-sub { font-size: 13px; color: var(--cf-text-muted); margin-top: 4px; }

.av-actions { display: flex; gap: 8px; align-items: center; }

.av-client-select {
  background: var(--cf-bg-input);
  border: 1px solid var(--cf-border-default);
  border-radius: 8px;
  padding: 8px 32px 8px 12px;
  font-size: 13px;
  color: var(--cf-text-primary);
  outline: none;
  font-family: inherit;
  appearance: none;
  min-width: 220px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='none' viewBox='0 0 24 24'%3E%3Cpath d='M6 9l6 6 6-6' stroke='%2364748B' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  cursor: pointer;
}
.av-client-select:focus { border-color: #6366F1; }

.av-loading { display: flex; justify-content: center; padding: 60px; }
.av-spinner {
  width: 32px; height: 32px;
  border: 3px solid var(--cf-border-default); border-top-color: #6366F1;
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.av-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 80px 20px; text-align: center; gap: 14px;
  color: var(--cf-text-muted);
}
.av-empty-icon {
  width: 80px; height: 80px;
  background: var(--cf-bg-surface);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: var(--cf-text-muted);
}
.av-empty-msg { font-size: 14px; }

@media (max-width: 768px) {
  .av-page { padding: 16px; }
  .av-header { flex-direction: column; }
  .av-client-select { width: 100%; }
}
</style>
