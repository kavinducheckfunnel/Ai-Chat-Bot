<template>
  <div class="customers-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Customers</h1>
        <p class="page-sub">Leads and contacts from your chatbot</p>
      </div>
      <button class="btn-export" @click="exportCSV" :disabled="exporting">
        <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        {{ exporting ? 'Exporting…' : 'Export CSV' }}
      </button>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'all' }" @click="activeTab = 'all'">
        All leads <span class="tab-count">{{ leads.length }}</span>
      </button>
      <button class="tab" :class="{ active: activeTab === 'hot' }" @click="activeTab = 'hot'">
        Hot leads <span class="tab-count hot" v-if="hotLeads.length">{{ hotLeads.length }}</span>
      </button>
      <button class="tab" :class="{ active: activeTab === 'converted' }" @click="activeTab = 'converted'">
        Converted
      </button>
    </div>

    <!-- Filters -->
    <div class="filters-bar">
      <div class="search-wrap">
        <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8" stroke="#475569" stroke-width="2"/><path d="M21 21l-4.35-4.35" stroke="#475569" stroke-width="2" stroke-linecap="round"/></svg>
        <input v-model="search" type="text" class="search-input" placeholder="Search by email or state…" />
      </div>
      <select v-model="sortBy" class="filter-select">
        <option value="-heat_score">Hottest first</option>
        <option value="-created_at">Newest first</option>
        <option value="created_at">Oldest first</option>
      </select>
    </div>

    <!-- Table -->
    <div class="table-wrap">
      <div v-if="loading" class="loading-rows">
        <div class="skeleton-row" v-for="n in 6" :key="n">
          <div class="sk-cell wide"></div>
          <div class="sk-cell"></div>
          <div class="sk-cell"></div>
          <div class="sk-cell narrow"></div>
        </div>
      </div>

      <table v-else class="leads-table">
        <thead>
          <tr>
            <th>Visitor</th>
            <th>State</th>
            <th>Heat</th>
            <th>Messages</th>
            <th>Seen</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="filtered.length === 0">
            <td colspan="5" class="empty-row">No leads match your filters</td>
          </tr>
          <tr v-for="lead in filtered" :key="lead.session_id">
            <td>
              <div class="visitor-cell">
                <div class="visitor-avatar" :style="{ background: heatColor(lead.heat_score) }">
                  {{ lead.lead_email ? lead.lead_email[0].toUpperCase() : '#' }}
                </div>
                <div>
                  <p class="visitor-email">{{ lead.lead_email || 'Anonymous' }}</p>
                  <p class="visitor-phone" v-if="lead.lead_phone">{{ lead.lead_phone }}</p>
                </div>
              </div>
            </td>
            <td><span class="state-badge" :class="kanbanClass(lead.kanban_state)">{{ lead.kanban_state }}</span></td>
            <td>
              <div class="heat-cell">
                <div class="heat-track">
                  <div class="heat-fill" :style="{ width: (lead.heat_score * 100) + '%', background: heatColor(lead.heat_score) }"></div>
                </div>
                <span class="heat-pct">{{ Math.round((lead.heat_score || 0) * 100) }}%</span>
              </div>
            </td>
            <td class="count-cell">{{ lead.message_count || 0 }}</td>
            <td class="time-cell">{{ formatDate(lead.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const props = defineProps({ client: Object })
const api = useAdminApi()

const leads = ref([])
const loading = ref(true)
const activeTab = ref('all')
const search = ref('')
const sortBy = ref('-heat_score')
const exporting = ref(false)

const hotLeads = computed(() => leads.value.filter(l => l.heat_score > 0.65 || l.kanban_state === 'HOT_LEAD'))

const filtered = computed(() => {
  let list = leads.value
  if (activeTab.value === 'hot') list = hotLeads.value
  if (activeTab.value === 'converted') list = list.filter(l => l.kanban_state === 'CONVERTED')
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(l => (l.lead_email || '').toLowerCase().includes(q) || (l.kanban_state || '').toLowerCase().includes(q))
  }
  if (sortBy.value === '-heat_score') list = [...list].sort((a, b) => (b.heat_score || 0) - (a.heat_score || 0))
  if (sortBy.value === '-created_at') list = [...list].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  if (sortBy.value === 'created_at') list = [...list].sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
  return list
})

async function loadLeads() {
  if (!props.client) return
  loading.value = true
  try {
    const data = await api.getPortalSessions(props.client.id, { limit: 200 })
    leads.value = Array.isArray(data) ? data : (data?.results || [])
  } catch {} finally {
    loading.value = false
  }
}

async function exportCSV() {
  if (!props.client) return
  exporting.value = true
  try {
    await api.exportLeadsCSV({ client_id: props.client.id })
  } catch {} finally {
    exporting.value = false
  }
}

function heatColor(score) {
  if (!score) return '#1e293b'
  if (score > 0.7) return '#ef4444'
  if (score > 0.4) return '#f59e0b'
  return '#6366f1'
}

function kanbanClass(state) {
  if (state === 'HOT_LEAD') return 'badge-hot'
  if (state === 'CONVERTED') return 'badge-converted'
  if (state === 'ENGAGED') return 'badge-engaged'
  if (state === 'LOST') return 'badge-lost'
  return 'badge-new'
}

function formatDate(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleDateString()
}

onMounted(loadLeads)
watch(() => props.client, loadLeads)
</script>

<style scoped>
* { box-sizing: border-box; }

.customers-page {
  padding: 28px 32px;
  font-family: 'Inter', -apple-system, sans-serif;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.4px; }
.page-sub { font-size: 13px; color: #475569; margin-top: 3px; }

.btn-export {
  display: flex; align-items: center; gap: 7px;
  padding: 8px 16px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.09);
  border-radius: 9px;
  font-size: 13px; font-weight: 500; color: #94a3b8;
  cursor: pointer; transition: all 0.12s;
}
.btn-export:hover { background: rgba(255,255,255,0.09); color: #f1f5f9; }
.btn-export:disabled { opacity: 0.5; cursor: not-allowed; }

.tabs {
  display: flex; gap: 2px;
  border-bottom: 1px solid rgba(255,255,255,0.07);
  margin-bottom: 16px;
}

.tab {
  display: flex; align-items: center; gap: 7px;
  padding: 9px 16px;
  background: none; border: none;
  border-bottom: 2px solid transparent;
  font-size: 13px; font-weight: 500; color: #475569;
  cursor: pointer; transition: all 0.12s; margin-bottom: -1px;
}
.tab:hover { color: #94a3b8; }
.tab.active { color: #a5b4fc; border-bottom-color: #6366f1; }

.tab-count {
  background: #1e293b; color: #64748b;
  font-size: 10px; font-weight: 700;
  padding: 1px 6px; border-radius: 10px;
}
.tab-count.hot { background: rgba(239,68,68,0.12); color: #ef4444; }

.filters-bar {
  display: flex; gap: 10px; margin-bottom: 14px; align-items: center;
}

.search-wrap {
  flex: 1; display: flex; align-items: center; gap: 9px;
  background: #161616;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 9px;
  padding: 0 12px;
}

.search-input {
  flex: 1; padding: 9px 0;
  background: none; border: none; outline: none;
  font-size: 13px; color: #f1f5f9;
}
.search-input::placeholder { color: #334155; }

.filter-select {
  padding: 9px 12px;
  background: #161616;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 9px;
  font-size: 13px; color: #94a3b8;
  outline: none; cursor: pointer;
}

.table-wrap { overflow-x: auto; }

.leads-table { width: 100%; border-collapse: collapse; }

.leads-table th {
  padding: 10px 14px;
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.06em;
  color: #334155;
  text-align: left;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  white-space: nowrap;
}

.leads-table td {
  padding: 12px 14px;
  font-size: 13px; color: #94a3b8;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  vertical-align: middle;
}

.leads-table tr:hover td { background: rgba(255,255,255,0.02); }

.empty-row { text-align: center; color: #334155; padding: 40px; }

.visitor-cell { display: flex; align-items: center; gap: 10px; }
.visitor-avatar { width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; color: white; flex-shrink: 0; }
.visitor-email { font-size: 13px; font-weight: 500; color: #e2e8f0; }
.visitor-phone { font-size: 11px; color: #475569; margin-top: 2px; }

.state-badge { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
.badge-hot { background: rgba(239,68,68,0.12); color: #ef4444; }
.badge-converted { background: rgba(34,197,94,0.12); color: #22c55e; }
.badge-engaged { background: rgba(99,102,241,0.12); color: #a5b4fc; }
.badge-lost { background: rgba(71,85,105,0.2); color: #475569; }
.badge-new { background: rgba(71,85,105,0.15); color: #64748b; }

.heat-cell { display: flex; align-items: center; gap: 8px; }
.heat-track { width: 60px; height: 4px; background: #1e293b; border-radius: 2px; overflow: hidden; }
.heat-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }
.heat-pct { font-size: 11px; color: #475569; font-family: monospace; width: 30px; }

.count-cell { color: #64748b; font-family: monospace; }
.time-cell { color: #334155; font-size: 12px; }

.loading-rows { display: flex; flex-direction: column; gap: 6px; padding: 8px 0; }
.skeleton-row { display: flex; gap: 16px; padding: 10px 14px; }
.sk-cell { height: 14px; background: #1e293b; border-radius: 4px; flex: 1; }
.sk-cell.wide { flex: 2; }
.sk-cell.narrow { flex: 0.5; }
</style>
