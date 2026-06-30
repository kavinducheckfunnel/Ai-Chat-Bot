<template>
  <div class="leads-page">
    <!-- Unified header: one title + a view switch (replaces the old separate
         "All leads" and "Pipeline" nav items). -->
    <div class="leads-header">
      <div class="leads-titles">
        <h1 class="leads-title">Leads</h1>
        <p class="leads-sub">Your captured leads — sort &amp; export, or work the pipeline.</p>
      </div>
      <div class="leads-actions">
        <PortalDateFilter v-model="period" @change="onDateChange" />
        <div class="view-toggle" role="tablist" aria-label="Leads view">
          <button :class="{ active: view === 'table' }" @click="setView('table')" role="tab" :aria-selected="view === 'table'">
            <svg width="15" height="15" fill="none" viewBox="0 0 24 24"><path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            Table
          </button>
          <button :class="{ active: view === 'board' }" @click="setView('board')" role="tab" :aria-selected="view === 'board'">
            <svg width="15" height="15" fill="none" viewBox="0 0 24 24"><rect x="3" y="3" width="4" height="18" rx="1" stroke="currentColor" stroke-width="2"/><rect x="10" y="3" width="4" height="13" rx="1" stroke="currentColor" stroke-width="2"/><rect x="17" y="3" width="4" height="8" rx="1" stroke="currentColor" stroke-width="2"/></svg>
            Board
          </button>
        </div>
      </div>
    </div>

    <PortalCustomers v-if="view === 'table'" :client="client" :date-range="dateRange" embedded />
    <PortalKanban v-else :client="client" :date-range="dateRange" embedded />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import PortalCustomers from './PortalCustomers.vue'
import PortalKanban from './PortalKanban.vue'
import PortalDateFilter from './PortalDateFilter.vue'

defineProps({ client: Object })
const route = useRoute()
const view = ref('table')
// Default to all-time so the board shows the full pipeline; tenant can narrow.
const period = ref('all')
const dateRange = ref({ period: 'all', dateFrom: null, dateTo: null })
function onDateChange(payload) { dateRange.value = payload }

function setView(v) {
  view.value = v
  try { localStorage.setItem('cf_leads_view', v) } catch {}
}

onMounted(() => {
  // Deep-link support: /portal/customers?view=board (where /portal/pipeline redirects).
  const q = route.query.view
  if (q === 'board' || q === 'table') { view.value = q; return }
  try { const s = localStorage.getItem('cf_leads_view'); if (s === 'board' || s === 'table') view.value = s } catch {}
})
</script>

<style scoped>
.leads-page { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
.leads-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 28px 32px 0;
  flex-wrap: wrap;
}
.leads-titles { min-width: 0; }
.leads-title { font-size: 22px; font-weight: 700; color: var(--cf-text-primary); margin: 0 0 3px; }
.leads-sub { font-size: 13px; color: var(--cf-text-muted); margin: 0; }
.leads-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }

.view-toggle {
  display: flex;
  background: var(--cf-bg-surface);
  border: 1px solid var(--cf-border-default);
  border-radius: 10px;
  padding: 3px;
  gap: 3px;
  flex-shrink: 0;
}
.view-toggle button {
  display: inline-flex; align-items: center; gap: 6px;
  background: none; border: none; border-radius: 8px;
  padding: 7px 14px; font-size: 13px; font-weight: 600;
  color: var(--cf-text-muted); cursor: pointer;
  transition: all 0.15s; font-family: inherit;
}
.view-toggle button:hover { color: var(--cf-text-secondary); }
.view-toggle button.active { background: var(--cf-bg-item-active, rgba(99,102,241,0.15)); color: #a5b4fc; }

@media (max-width: 600px) {
  .leads-header { padding: 18px 16px 0; }
  .view-toggle button { padding: 7px 12px; }
}
</style>
