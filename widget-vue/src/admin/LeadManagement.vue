<template>
  <div class="leads-page">

    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Lead Management</h1>
        <p class="page-sub">
          {{ loading ? 'Loading...' : `${totalCount} captured lead${totalCount !== 1 ? 's' : ''}` }}
          <span v-if="hasFilters" class="filter-active-badge">filtered</span>
        </p>
      </div>
      <button class="export-btn" @click="doExport" :disabled="exporting || !leads.length">
        <svg width="14" height="14" fill="none" viewBox="0 0 24 24">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ exporting ? 'Exporting…' : 'Export CSV' }}
      </button>
    </div>

    <!-- Filter bar -->
    <div class="filter-bar">
      <div class="filter-group">
        <label class="filter-label">Client</label>
        <select class="filter-select" v-model="filters.client_id" @change="loadLeads">
          <option value="">All Clients</option>
          <option v-for="c in clients" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <div class="filter-group">
        <label class="filter-label">From</label>
        <input class="filter-input" type="date" v-model="filters.date_from" @change="loadLeads">
      </div>
      <div class="filter-group">
        <label class="filter-label">To</label>
        <input class="filter-input" type="date" v-model="filters.date_to" @change="loadLeads">
      </div>
      <div class="filter-group">
        <label class="filter-label">Min Heat</label>
        <div class="heat-input-wrap">
          <input
            class="filter-input heat-input"
            type="number"
            min="0"
            max="100"
            placeholder="0"
            v-model.number="filters.min_heat"
            @change="loadLeads"
          >
          <span class="heat-pct">%</span>
        </div>
      </div>
      <button v-if="hasFilters" class="clear-btn" @click="clearFilters">
        <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg>
        Clear
      </button>
    </div>

    <!-- Stats strip -->
    <div class="stats-strip">
      <div class="stat-chip">
        <span class="stat-num">{{ totalCount }}</span>
        <span class="stat-lbl">Total Leads</span>
      </div>
      <div class="stat-chip hot">
        <span class="stat-num">{{ hotCount }}</span>
        <span class="stat-lbl">Hot (70+)</span>
      </div>
      <div class="stat-chip warm">
        <span class="stat-num">{{ warmCount }}</span>
        <span class="stat-lbl">Warm (40–69)</span>
      </div>
      <div class="stat-chip cold">
        <span class="stat-num">{{ coldCount }}</span>
        <span class="stat-lbl">Cold (&lt;40)</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="loader"></div>
      <p>Loading leads…</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="!leads.length" class="empty-state">
      <div class="empty-icon">
        <svg width="40" height="40" fill="none" viewBox="0 0 24 24">
          <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" stroke="#CBD5E1" stroke-width="1.5" stroke-linecap="round"/>
          <circle cx="12" cy="7" r="4" stroke="#CBD5E1" stroke-width="1.5"/>
          <path d="M16 3.13a4 4 0 010 7.75" stroke="#CBD5E1" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </div>
      <p class="empty-title">No leads captured yet</p>
      <p class="empty-sub">
        {{ hasFilters ? 'Try adjusting your filters.' : 'Leads appear here when visitors share their email or phone in chat.' }}
      </p>
    </div>

    <!-- Table -->
    <div v-else class="table-wrap">
      <table class="leads-table">
        <thead>
          <tr>
            <th>Contact</th>
            <th>Heat</th>
            <th>Stage</th>
            <th>Client</th>
            <th>Captured</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="lead in leads" :key="lead.session_id" class="lead-row">

            <!-- Contact -->
            <td class="contact-cell">
              <div v-if="lead.lead_email" class="contact-email">
                <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" stroke="currentColor" stroke-width="2"/><polyline points="22,6 12,13 2,6" stroke="currentColor" stroke-width="2"/></svg>
                {{ lead.lead_email }}
              </div>
              <div v-if="lead.lead_phone" class="contact-phone">
                <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.81 19.79 19.79 0 01.01 1.18 2 2 0 012 .01h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z" stroke="currentColor" stroke-width="2"/></svg>
                {{ lead.lead_phone }}
              </div>
            </td>

            <!-- Heat -->
            <td>
              <span class="heat-badge" :class="heatClass(lead.heat_score)">
                {{ heatEmoji(lead.heat_score) }} {{ lead.heat_score }}%
              </span>
              <div class="heat-bar-wrap">
                <div class="heat-bar" :style="{ width: lead.heat_score + '%', background: heatGradient(lead.heat_score) }"></div>
              </div>
            </td>

            <!-- Stage -->
            <td>
              <span class="stage-badge" :class="stageClass(lead.kanban_state)">
                {{ stageLabel(lead.kanban_state) }}
              </span>
            </td>

            <!-- Client -->
            <td class="client-cell">{{ lead.client_name }}</td>

            <!-- Captured -->
            <td class="date-cell">
              <span class="date-rel" :title="formatDate(lead.created_at)">{{ timeAgo(lead.created_at) }}</span>
              <span class="date-abs">{{ formatDate(lead.created_at) }}</span>
            </td>

            <!-- Actions -->
            <td class="action-cell">
              <button class="view-btn" @click="viewChat(lead.session_id)" title="Open full chat in God View">
                <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/></svg>
                View Chat
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()
const router = useRouter()

const leads = ref([])
const clients = ref([])
const loading = ref(false)
const exporting = ref(false)

const filters = ref({
  client_id: '',
  date_from: '',
  date_to: '',
  min_heat: '',
})

// ── Computed stats ────────────────────────────────────────────────────────────

const totalCount = computed(() => leads.value.length)
const hotCount   = computed(() => leads.value.filter(l => l.heat_score >= 70).length)
const warmCount  = computed(() => leads.value.filter(l => l.heat_score >= 40 && l.heat_score < 70).length)
const coldCount  = computed(() => leads.value.filter(l => l.heat_score < 40).length)

const hasFilters = computed(() =>
  filters.value.client_id || filters.value.date_from || filters.value.date_to || filters.value.min_heat !== ''
)

// ── Data loading ──────────────────────────────────────────────────────────────

async function loadLeads() {
  loading.value = true
  try {
    const params = {
      client_id: filters.value.client_id || undefined,
      date_from: filters.value.date_from || undefined,
      date_to:   filters.value.date_to   || undefined,
      min_heat:  filters.value.min_heat !== '' ? filters.value.min_heat : undefined,
    }
    const res = await api.getLeads(params)
    leads.value = res?.leads || []
  } catch (e) {
    console.error('Failed to load leads:', e)
    leads.value = []
  } finally {
    loading.value = false
  }
}

async function loadClients() {
  try {
    const data = await api.getClients()
    clients.value = data || []
  } catch {}
}

function clearFilters() {
  filters.value = { client_id: '', date_from: '', date_to: '', min_heat: '' }
  loadLeads()
}

// ── Export ────────────────────────────────────────────────────────────────────

async function doExport() {
  exporting.value = true
  try {
    const params = {
      client_id: filters.value.client_id || undefined,
      date_from: filters.value.date_from || undefined,
      date_to:   filters.value.date_to   || undefined,
      min_heat:  filters.value.min_heat !== '' ? filters.value.min_heat : undefined,
    }
    await api.exportLeadsCSV(params)
  } catch (e) {
    console.error('Export failed:', e)
  } finally {
    exporting.value = false
  }
}

// ── Navigation ────────────────────────────────────────────────────────────────

function viewChat(sessionId) {
  router.push(`/admin/godview/${sessionId}`)
}

// ── Formatters ────────────────────────────────────────────────────────────────

function heatClass(score) {
  if (score >= 70) return 'hot'
  if (score >= 40) return 'warm'
  return 'cold'
}

function heatEmoji(score) {
  if (score >= 70) return '🔥'
  if (score >= 40) return '🟠'
  return '🔵'
}

function heatGradient(score) {
  if (score >= 70) return 'linear-gradient(90deg,#EF4444,#F97316)'
  if (score >= 40) return 'linear-gradient(90deg,#F97316,#EAB308)'
  return 'linear-gradient(90deg,#3B82F6,#06B6D4)'
}

const STAGE_MAP = {
  NEW:       { label: 'New',       cls: 'stage-new' },
  ENGAGED:   { label: 'Engaged',   cls: 'stage-engaged' },
  HOT_LEAD:  { label: 'Hot Lead',  cls: 'stage-hot' },
  CONVERTED: { label: 'Converted', cls: 'stage-converted' },
  LOST:      { label: 'Lost',      cls: 'stage-lost' },
}

function stageLabel(k) { return STAGE_MAP[k]?.label ?? k }
function stageClass(k) { return STAGE_MAP[k]?.cls ?? '' }

function timeAgo(iso) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1)   return 'just now'
  if (m < 60)  return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24)  return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

onMounted(() => {
  loadClients()
  loadLeads()
})
</script>

<style scoped>
/* ── Layout ── */
.leads-page { display: flex; flex-direction: column; gap: 18px; height: 100%; }

/* ── Header ── */
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.page-title  { font-size: 24px; font-weight: 700; color: #0F172A; letter-spacing: -0.4px; }
.page-sub    { font-size: 14px; color: #64748B; margin-top: 4px; display: flex; align-items: center; gap: 8px; }

.filter-active-badge {
  font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 20px;
  background: rgba(99,102,241,0.12); color: #6366F1; text-transform: uppercase; letter-spacing: 0.05em;
}

.export-btn {
  display: flex; align-items: center; gap: 7px;
  background: #6366F1; color: white; border: none; border-radius: 9px;
  padding: 9px 16px; font-size: 13px; font-weight: 600; cursor: pointer;
  transition: all 0.15s; font-family: inherit;
}
.export-btn:hover:not(:disabled) { background: #4F46E5; }
.export-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Filter bar ── */
.filter-bar {
  display: flex; align-items: flex-end; gap: 12px; flex-wrap: wrap;
  background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px 16px;
}

.filter-group { display: flex; flex-direction: column; gap: 5px; }

.filter-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: #94A3B8;
}

.filter-select, .filter-input {
  height: 36px; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0 10px;
  font-size: 13px; color: #334155; background: #F8FAFC;
  font-family: inherit; outline: none; transition: border-color 0.15s;
}
.filter-select:focus, .filter-input:focus { border-color: #6366F1; background: white; }
.filter-select { padding-right: 28px; }

.heat-input-wrap { position: relative; display: flex; align-items: center; }
.heat-input { width: 70px; padding-right: 24px; }
.heat-pct { position: absolute; right: 9px; font-size: 12px; color: #94A3B8; pointer-events: none; }

.clear-btn {
  display: flex; align-items: center; gap: 5px; align-self: flex-end;
  height: 36px; padding: 0 12px; border-radius: 8px;
  background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2);
  color: #DC2626; font-size: 12px; font-weight: 600; cursor: pointer;
  transition: all 0.15s; font-family: inherit;
}
.clear-btn:hover { background: rgba(239,68,68,0.15); }

/* ── Stats strip ── */
.stats-strip {
  display: flex; gap: 12px; flex-wrap: wrap;
}

.stat-chip {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: white; border: 1px solid #E2E8F0; border-radius: 12px;
  padding: 14px 24px; min-width: 110px; flex: 1;
}
.stat-chip.hot  { background: rgba(239,68,68,0.04);  border-color: rgba(239,68,68,0.2); }
.stat-chip.warm { background: rgba(249,115,22,0.04); border-color: rgba(249,115,22,0.2); }
.stat-chip.cold { background: rgba(59,130,246,0.04); border-color: rgba(59,130,246,0.2); }

.stat-num {
  font-size: 26px; font-weight: 800; color: #0F172A; letter-spacing: -0.5px; line-height: 1;
}
.stat-chip.hot  .stat-num { color: #DC2626; }
.stat-chip.warm .stat-num { color: #EA580C; }
.stat-chip.cold .stat-num { color: #2563EB; }

.stat-lbl {
  font-size: 11px; font-weight: 600; color: #94A3B8; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.05em;
}

/* ── Loading ── */
.loading-state { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 60px; color: #94A3B8; font-size: 14px; }
.loader { width: 32px; height: 32px; border: 3px solid #E2E8F0; border-top-color: #6366F1; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Empty ── */
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 80px 20px; }
.empty-icon  { width: 72px; height: 72px; background: #F8FAFC; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-bottom: 8px; }
.empty-title { font-size: 16px; font-weight: 600; color: #334155; }
.empty-sub   { font-size: 14px; color: #94A3B8; text-align: center; max-width: 360px; }

/* ── Table ── */
.table-wrap {
  flex: 1; overflow: auto;
  background: white; border: 1px solid #E2E8F0; border-radius: 14px;
}

.leads-table {
  width: 100%; border-collapse: collapse;
}

.leads-table thead th {
  position: sticky; top: 0; z-index: 1;
  padding: 11px 16px; text-align: left;
  font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;
  color: #94A3B8; background: #F8FAFC;
  border-bottom: 1px solid #F1F5F9;
}
.leads-table thead th:first-child { border-radius: 14px 0 0 0; }
.leads-table thead th:last-child  { border-radius: 0 14px 0 0; }

.lead-row td {
  padding: 13px 16px; border-bottom: 1px solid #F8FAFC;
  vertical-align: middle;
}
.lead-row:last-child td { border-bottom: none; }
.lead-row:hover td { background: #FAFBFF; }

/* Contact */
.contact-cell { min-width: 180px; }
.contact-email, .contact-phone {
  display: flex; align-items: center; gap: 6px; font-size: 13px;
}
.contact-email { color: #1E293B; font-weight: 500; }
.contact-phone { color: #64748B; font-size: 12px; margin-top: 3px; }

/* Heat badge */
.heat-badge {
  font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 6px;
  display: inline-block; white-space: nowrap;
}
.heat-badge.hot  { background: rgba(239,68,68,0.1);  color: #DC2626; }
.heat-badge.warm { background: rgba(249,115,22,0.1); color: #EA580C; }
.heat-badge.cold { background: rgba(59,130,246,0.1); color: #2563EB; }

.heat-bar-wrap {
  background: #F1F5F9; border-radius: 3px; height: 3px; margin-top: 5px; overflow: hidden; width: 80px;
}
.heat-bar { height: 100%; border-radius: 3px; }

/* Stage badge */
.stage-badge {
  font-size: 11px; font-weight: 700; padding: 3px 9px; border-radius: 20px;
  display: inline-block; white-space: nowrap;
}
.stage-new       { background: #F1F5F9; color: #475569; }
.stage-engaged   { background: rgba(59,130,246,0.1); color: #2563EB; }
.stage-hot       { background: rgba(239,68,68,0.1);  color: #DC2626; }
.stage-converted { background: rgba(22,163,74,0.1);  color: #16A34A; }
.stage-lost      { background: #F1F5F9; color: #94A3B8; }

/* Client */
.client-cell {
  font-size: 13px; font-weight: 500; color: #334155; white-space: nowrap;
}

/* Date */
.date-cell { min-width: 120px; }
.date-rel  { display: block; font-size: 13px; color: #334155; }
.date-abs  { display: block; font-size: 11px; color: #94A3B8; margin-top: 2px; }

/* Action */
.action-cell { text-align: right; white-space: nowrap; }
.view-btn {
  display: inline-flex; align-items: center; gap: 5px;
  background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.25);
  color: #6366F1; border-radius: 7px; padding: 6px 11px;
  font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.15s; font-family: inherit;
}
.view-btn:hover { background: #6366F1; color: white; border-color: #6366F1; }
</style>
