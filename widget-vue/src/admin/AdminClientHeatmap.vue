<template>
  <div class="ac-page">
    <div class="ac-header">
      <button class="ac-back" @click="$router.push(`/admin/clients/${$route.params.id}`)">
        <svg width="14" height="14" fill="none" viewBox="0 0 24 24">
          <path d="M19 12H5M12 5l-7 7 7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        Back to client
      </button>
      <div v-if="client" class="ac-title-block">
        <h1 class="ac-title">{{ client.name }} — Activity Heatmap</h1>
        <p class="ac-sub">Where visitors clicked, grouped by page (parity with tenant Activity)</p>
      </div>
    </div>

    <div v-if="loading" class="ac-loading">
      <div class="ac-spinner"></div>
    </div>

    <!-- PortalActivity already takes :client and calls /api/admin/clients/<id>/heatmap/ -->
    <PortalActivity v-else-if="client" :client="client" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAdminApi } from '../composables/useAdminApi'
import PortalActivity from '../portal/PortalActivity.vue'

const route = useRoute()
const api = useAdminApi()
const client = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    client.value = await api.getClient(route.params.id)
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.ac-page { padding: 24px 32px; }
.ac-header { display: flex; flex-direction: column; gap: 14px; margin-bottom: 20px; }
.ac-back {
  display: inline-flex; align-items: center; gap: 6px; align-self: flex-start;
  background: var(--cf-bg-surface); border: 1px solid var(--cf-border-default);
  color: var(--cf-text-secondary); border-radius: 8px; padding: 6px 12px;
  font-size: 13px; font-weight: 500; cursor: pointer; font-family: inherit;
  transition: background 0.15s;
}
.ac-back:hover { background: var(--cf-bg-ghost-hover); color: var(--cf-text-primary); }
.ac-title { font-size: 22px; font-weight: 700; color: var(--cf-text-primary); letter-spacing: -0.4px; }
.ac-sub { font-size: 13px; color: var(--cf-text-muted); margin-top: 4px; }
.ac-loading { display: flex; justify-content: center; padding: 60px; }
.ac-spinner {
  width: 32px; height: 32px;
  border: 3px solid var(--cf-border-default); border-top-color: #6366F1;
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .ac-page { padding: 16px; }
}
</style>
