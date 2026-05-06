<template>
  <div class="admin-container">
    <Sidebar />
    <main class="admin-main">

      <!-- Header -->
      <div class="page-header">
        <div>
          <h1 class="page-title">Super Admin</h1>
          <p class="page-sub">Platform intelligence &amp; tenant operations</p>
        </div>
        <div class="header-right">
          <div class="live-badge"><span class="live-dot"></span>Live</div>
          <button class="refresh-btn" @click="loadAll" :disabled="loading">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
            Refresh
          </button>
        </div>
      </div>

      <!-- Tabs -->
      <div class="tab-row">
        <button v-for="t in tabs" :key="t.key" class="tab-btn" :class="{active: activeTab===t.key}" @click="activeTab=t.key">
          {{ t.label }}
          <span v-if="t.key==='alerts' && alertCount > 0" class="tab-badge">{{ alertCount }}</span>
        </button>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div><span>Loading platform data…</span>
      </div>

      <!-- ═══════════ OVERVIEW TAB ═══════════ -->
      <div v-else-if="activeTab==='overview'" class="tab-content">

        <!-- Revenue Strip -->
        <div class="revenue-strip">
          <div v-for="m in revenueMetrics" :key="m.label" class="rev-card" :class="m.cls">
            <div class="rev-icon" v-html="m.icon"></div>
            <div class="rev-body">
              <span class="rev-label">{{ m.label }}</span>
              <span class="rev-value">{{ m.value }}</span>
              <span class="rev-sub" :class="m.subCls">{{ m.sub }}</span>
            </div>
          </div>
        </div>

        <!-- Charts row -->
        <div class="charts-row">
          <!-- MRR Trend -->
          <div class="chart-card wide">
            <div class="chart-header">
              <h3>MRR Trend</h3>
              <span class="chart-sub">Last 6 months</span>
            </div>
            <div class="line-chart-wrap">
              <svg class="line-chart" viewBox="0 0 400 120" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="mrr-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#6366f1" stop-opacity="0.25"/>
                    <stop offset="100%" stop-color="#6366f1" stop-opacity="0"/>
                  </linearGradient>
                </defs>
                <path :d="mrrAreaPath" fill="url(#mrr-grad)"/>
                <path :d="mrrLinePath" fill="none" stroke="#6366f1" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                <circle v-for="(p,i) in mrrPoints" :key="i" :cx="p.x" :cy="p.y" r="3.5" fill="#6366f1"/>
              </svg>
              <div class="line-labels">
                <span v-for="m in revenue.mrr_trend" :key="m.month">{{ m.month.split(' ')[0] }}</span>
              </div>
            </div>
          </div>

          <!-- Plan Distribution -->
          <div class="chart-card">
            <div class="chart-header">
              <h3>Plan Distribution</h3>
              <span class="chart-sub">{{ revenue.total_tenants }} tenants</span>
            </div>
            <div class="donut-wrap">
              <svg viewBox="0 0 120 120" class="donut-svg">
                <circle cx="60" cy="60" r="48" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="18"/>
                <circle v-for="(seg,i) in donutSegments" :key="i"
                  cx="60" cy="60" r="48" fill="none"
                  :stroke="seg.color" stroke-width="18"
                  :stroke-dasharray="`${seg.dash} ${seg.gap}`"
                  :stroke-dashoffset="seg.offset"
                  stroke-linecap="butt"
                  style="transform-origin:center;transform:rotate(-90deg)"
                />
                <text x="60" y="56" text-anchor="middle" class="donut-label-big">{{ revenue.active_tenants }}</text>
                <text x="60" y="70" text-anchor="middle" class="donut-label-sm">active</text>
              </svg>
              <div class="donut-legend">
                <div v-for="d in revenue.plan_distribution" :key="d.plan" class="legend-row">
                  <span class="legend-dot" :style="{background: d.color}"></span>
                  <span class="legend-plan">{{ d.plan }}</span>
                  <span class="legend-count">{{ d.count }}</span>
                  <span class="legend-mrr">${{ d.mrr.toFixed(0) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Bottom stats row -->
        <div class="stats-row">
          <div class="stat-mini" v-for="s in platformStats" :key="s.label">
            <span class="stat-mini-label">{{ s.label }}</span>
            <span class="stat-mini-val">{{ s.value }}</span>
          </div>
        </div>

      </div>

      <!-- ═══════════ HEALTH BOARD TAB ═══════════ -->
      <div v-else-if="activeTab==='health'" class="tab-content">

        <div class="board-controls">
          <input v-model="healthSearch" class="search-input" placeholder="Search tenant…" />
          <div class="risk-filters">
            <button v-for="r in riskFilters" :key="r.val" class="risk-pill"
              :class="{active: riskFilter===r.val, ['rf-'+r.val]: true}"
              @click="riskFilter = riskFilter===r.val ? 'all' : r.val">
              {{ r.label }} <span class="risk-count">{{ riskCount(r.val) }}</span>
            </button>
          </div>
        </div>

        <div class="health-table-wrap">
          <table class="health-table">
            <thead>
              <tr>
                <th @click="sortBy('company')">Tenant <span class="sort-icon">↕</span></th>
                <th @click="sortBy('plan')">Plan</th>
                <th @click="sortBy('sessions_30d')">Sessions 30d</th>
                <th @click="sortBy('plan_price')">MRR</th>
                <th>Stripe</th>
                <th @click="sortBy('health_score')">Health</th>
                <th>Risk</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in filteredTenants" :key="t.tenant_id" class="tenant-row">
                <td>
                  <div class="tenant-info">
                    <div class="tenant-avatar">{{ t.company[0]?.toUpperCase() }}</div>
                    <div>
                      <div class="tenant-name">{{ t.company }}</div>
                      <div class="tenant-email">{{ t.email }}</div>
                    </div>
                  </div>
                </td>
                <td><span class="plan-badge" :class="'plan-'+t.plan.toLowerCase().replace(/\s/g,'')">{{ t.plan }}</span></td>
                <td><span class="session-num">{{ t.sessions_30d }}</span></td>
                <td><span class="mrr-val">${{ t.plan_price.toFixed(0) }}</span></td>
                <td>
                  <span class="stripe-badge" :class="'stripe-'+(t.stripe_status||'none')">{{ t.stripe_status || 'none' }}</span>
                  <span v-if="t.trial_expires_in_days !== null" class="trial-badge">Trial {{ t.trial_expires_in_days }}d</span>
                </td>
                <td>
                  <div class="health-bar-wrap">
                    <div class="health-bar" :style="{width: t.health_score+'%', background: healthColor(t.health_score)}"></div>
                    <span class="health-num">{{ t.health_score }}</span>
                  </div>
                </td>
                <td><span class="risk-badge" :class="'risk-'+t.risk">{{ t.risk.replace(/_/g,' ') }}</span></td>
                <td>
                  <div class="action-btns">
                    <button class="act-btn" title="Impersonate" @click="impersonate(t)">🔑</button>
                    <button class="act-btn" title="Change plan" @click="openPlanModal(t)">⬆️</button>
                    <button class="act-btn" title="Feature overrides" @click="openOverridesModal(t)">🎁</button>
                    <button class="act-btn" title="Extend trial" @click="extendTrial(t)">⏱️</button>
                  </div>
                </td>
              </tr>
              <tr v-if="filteredTenants.length === 0">
                <td colspan="8" class="empty-row">No tenants match the current filter.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ═══════════ ALERTS TAB ═══════════ -->
      <div v-else-if="activeTab==='alerts'" class="tab-content">
        <div v-if="alerts.length === 0" class="empty-panel">
          <svg width="40" height="40" fill="none" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="#22c55e" stroke-width="1.5" stroke-linecap="round"/><polyline points="22 4 12 14.01 9 11.01" stroke="#22c55e" stroke-width="1.5" stroke-linecap="round"/></svg>
          <p>All clear — no lifecycle alerts right now.</p>
        </div>
        <div v-else class="alerts-list">
          <div v-for="(a,idx) in alerts" :key="idx" class="alert-card" :class="'al-'+a.severity">
            <div class="al-icon">
              <span v-if="a.severity==='critical'">🔴</span>
              <span v-else-if="a.severity==='warning'">🟠</span>
              <span v-else>🔵</span>
            </div>
            <div class="al-body">
              <span class="al-company">{{ a.label }}</span>
              <span class="al-msg">{{ a.message }}</span>
            </div>
            <div class="al-actions">
              <button class="al-btn" @click="handleAlertAction(a)">{{ alertActionLabel(a.action) }}</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════ AUDIT LOG TAB ═══════════ -->
      <div v-else-if="activeTab==='audit'" class="tab-content">
        <div class="audit-controls">
          <input v-model="auditSearch" class="search-input" placeholder="Search by tenant…" @input="loadAudit" />
          <select v-model="auditAction" class="sel-input" @change="loadAudit">
            <option value="">All actions</option>
            <option v-for="ac in auditActions" :key="ac" :value="ac">{{ ac }}</option>
          </select>
        </div>
        <div class="audit-table-wrap">
          <table class="audit-table">
            <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Target</th><th>Notes</th></tr></thead>
            <tbody>
              <tr v-for="a in auditLogs" :key="a.id">
                <td class="mono text-muted">{{ fmtDate(a.timestamp) }}</td>
                <td><span class="actor-badge">{{ a.actor }}</span></td>
                <td><span class="action-chip">{{ a.action }}</span></td>
                <td class="text-muted">{{ a.target_label }}</td>
                <td class="text-muted small">{{ a.notes }}</td>
              </tr>
              <tr v-if="auditLogs.length===0"><td colspan="5" class="empty-row">No audit entries found.</td></tr>
            </tbody>
          </table>
          <div class="audit-pagination" v-if="auditTotal > 50">
            <button @click="auditPage--; loadAudit()" :disabled="auditPage<=1">←</button>
            <span>Page {{ auditPage }} of {{ Math.ceil(auditTotal/50) }}</span>
            <button @click="auditPage++; loadAudit()" :disabled="auditPage>=Math.ceil(auditTotal/50)">→</button>
          </div>
        </div>
      </div>

      <!-- ═══════════ ANNOUNCEMENTS TAB ═══════════ -->
      <div v-else-if="activeTab==='announce'" class="tab-content">
        <div class="announce-layout">
          <div class="card">
            <h3 class="card-title">New Announcement</h3>
            <div class="form-field"><label>Title</label><input class="inp" v-model="annForm.title" placeholder="e.g. Scheduled maintenance" /></div>
            <div class="form-field"><label>Message</label><textarea class="inp" v-model="annForm.body" rows="3" placeholder="Details…"></textarea></div>
            <div class="form-row">
              <div class="form-field">
                <label>Type</label>
                <select class="inp" v-model="annForm.type">
                  <option value="info">Info</option>
                  <option value="warning">Warning</option>
                  <option value="feature">New Feature</option>
                  <option value="maintenance">Maintenance</option>
                </select>
              </div>
              <div class="form-field">
                <label>Target</label>
                <select class="inp" v-model="annForm.target">
                  <option value="all">All Tenants</option>
                  <option value="free">Free Plan</option>
                  <option value="paid">Paid Plans</option>
                </select>
              </div>
            </div>
            <div class="form-field"><label>CTA Button (optional)</label>
              <input class="inp" v-model="annForm.cta_label" placeholder="e.g. Learn more" />
              <input class="inp" v-model="annForm.cta_url" placeholder="https://…" style="margin-top:6px" />
            </div>
            <button class="btn-primary" @click="createAnnouncement" :disabled="annSaving">
              {{ annSaving ? 'Sending…' : annSent ? '✓ Sent!' : 'Publish Announcement' }}
            </button>
          </div>
          <div class="card">
            <h3 class="card-title">How it works</h3>
            <ul class="tips-list">
              <li>Banners appear in the tenant portal after next login</li>
              <li>Target "Free Plan" to push upgrade prompts only to free users</li>
              <li>Use "Maintenance" type to warn all tenants of downtime</li>
              <li>CTA button links to any URL — use <code>/portal/billing</code> for upgrade CTAs</li>
            </ul>
          </div>
        </div>
      </div>

    </main>

    <!-- Plan Modal -->
    <div v-if="planModal.open" class="modal-overlay" @click.self="planModal.open=false">
      <div class="modal">
        <h3 class="modal-title">Change Plan — {{ planModal.tenant?.company }}</h3>
        <div class="form-field" style="margin-bottom:12px">
          <label>New Plan</label>
          <select class="inp" v-model="planModal.selectedPlanId">
            <option v-for="p in plans" :key="p.id" :value="p.id">{{ p.name }} — ${{ p.price_monthly }}/mo</option>
          </select>
        </div>
        <div class="form-field" style="margin-bottom:12px">
          <label>Notes</label>
          <input class="inp" v-model="planModal.remarks" placeholder="Reason for change…" />
        </div>
        <div class="modal-actions">
          <button class="btn-ghost" @click="planModal.open=false">Cancel</button>
          <button class="btn-primary" style="width:auto;padding:9px 22px" @click="savePlanChange" :disabled="planModal.saving">
            {{ planModal.saving ? 'Saving…' : 'Confirm Change' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Feature Override Modal -->
    <div v-if="overrideModal.open" class="modal-overlay" @click.self="overrideModal.open=false">
      <div class="modal modal-wide">
        <h3 class="modal-title">Feature Overrides — {{ overrideModal.tenant?.company }}</h3>
        <div class="override-list">
          <div v-if="overrideModal.loading" class="text-muted" style="padding:12px">Loading…</div>
          <div v-else-if="overrideModal.items.length === 0" class="text-muted" style="padding:12px">No overrides set.</div>
          <div v-for="o in overrideModal.items" :key="o.id" class="override-row">
            <span class="ov-feature">{{ o.feature_name }}</span>
            <span :class="o.enabled ? 'ov-on' : 'ov-off'">{{ o.enabled ? 'ENABLED' : 'DISABLED' }}</span>
            <span class="ov-reason">{{ o.reason }}</span>
            <span class="ov-exp">{{ o.expires_at ? 'Exp: '+fmtDate(o.expires_at) : 'No expiry' }}</span>
            <button class="act-btn" @click="deleteOverride(o)">✕</button>
          </div>
        </div>
        <div class="override-add">
          <h4 style="margin-bottom:10px;color:#94a3b8;font-size:13px">Add / Update Override</h4>
          <div class="form-row">
            <select class="inp" v-model="overrideModal.newFeature">
              <option value="">Select feature…</option>
              <option v-for="f in allFeatures" :key="f.key" :value="f.key">{{ f.label }}</option>
            </select>
            <select class="inp" v-model="overrideModal.newEnabled">
              <option :value="true">Enable</option>
              <option :value="false">Disable</option>
            </select>
          </div>
          <div class="form-row">
            <input class="inp" v-model="overrideModal.newReason" placeholder="Reason (e.g. VIP deal)" />
            <input class="inp" type="datetime-local" v-model="overrideModal.newExpiry" title="Expires at (blank = never)" />
          </div>
          <button class="btn-primary" style="width:auto;padding:9px 22px" @click="saveOverride" :disabled="!overrideModal.newFeature || overrideModal.saving">
            {{ overrideModal.saving ? 'Saving…' : 'Grant Override' }}
          </button>
        </div>
        <div class="modal-actions">
          <button class="btn-ghost" @click="overrideModal.open=false">Close</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Sidebar from './Sidebar.vue'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()
const loading = ref(true)
const activeTab = ref('overview')
const tabs = [
  { key: 'overview', label: 'Overview' },
  { key: 'health',   label: 'Health Board' },
  { key: 'alerts',   label: 'Alerts' },
  { key: 'audit',    label: 'Audit Log' },
  { key: 'announce', label: 'Announcements' },
]

// ── Data ─────────────────────────────────────────────────────────────────────
const revenue  = ref({ mrr:0, arr:0, new_mrr:0, churned_mrr:0, net_mrr_growth:0, arpu:0, active_tenants:0, total_tenants:0, past_due:0, trialing:0, plan_distribution:[], mrr_trend:[] })
const tenants  = ref([])
const alerts   = ref([])
const auditLogs = ref([])
const auditTotal = ref(0)
const auditPage = ref(1)
const auditSearch = ref('')
const auditAction = ref('')
const plans = ref([])
const stats = ref({})

const auditActions = ['PLAN_CHANGE','IMPERSONATE_START','FEATURE_OVERRIDE','FEATURE_OVERRIDE_REVOKE','TRIAL_EXTEND','ACCOUNT_SUSPEND','BROADCAST_SEND']

// ── Revenue strip ─────────────────────────────────────────────────────────────
const revenueMetrics = computed(() => [
  { label:'MRR',         value:'$'+fmt(revenue.value.mrr),          sub:'Monthly recurring',     icon:iconDollar, cls:'rev-mrr' },
  { label:'ARR',         value:'$'+fmt(revenue.value.arr),          sub:'Annualised',             icon:iconChart,  cls:'rev-arr' },
  { label:'New MRR',     value:'+$'+fmt(revenue.value.new_mrr),     sub:'This month',             icon:iconUp,     cls:'rev-new',   subCls:'green' },
  { label:'Churned MRR', value:'-$'+fmt(revenue.value.churned_mrr), sub:'This month',             icon:iconDown,   cls:'rev-churn', subCls: revenue.value.churned_mrr > 0 ? 'red' : '' },
  { label:'ARPU',        value:'$'+fmt(revenue.value.arpu),         sub:'Per active tenant',      icon:iconUser,   cls:'rev-arpu' },
  { label:'Past Due',    value:revenue.value.past_due,              sub:'Payment failures',       icon:iconWarn,   cls: revenue.value.past_due > 0 ? 'rev-warn' : 'rev-ok' },
  { label:'Trialing',    value:revenue.value.trialing,              sub:'Active trials',          icon:iconClock,  cls:'rev-trial' },
])

function fmt(n) {
  if (!n && n !== 0) return '0'
  if (n >= 1000) return (n/1000).toFixed(1)+'k'
  return Number(n).toFixed(0)
}

// ── SVG line chart ────────────────────────────────────────────────────────────
const mrrPoints = computed(() => {
  const trend = revenue.value.mrr_trend || []
  if (trend.length < 2) return []
  const vals = trend.map(t => t.mrr)
  const maxV = Math.max(...vals, 1)
  return trend.map((t, i) => ({
    x: (i / (trend.length - 1)) * 380 + 10,
    y: 110 - (t.mrr / maxV) * 100,
  }))
})
const mrrLinePath = computed(() => {
  const pts = mrrPoints.value
  if (!pts.length) return ''
  return pts.map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`)).join(' ')
})
const mrrAreaPath = computed(() => {
  const pts = mrrPoints.value
  if (!pts.length) return ''
  const line = pts.map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`)).join(' ')
  const last = pts[pts.length - 1], first = pts[0]
  return `${line} L ${last.x} 120 L ${first.x} 120 Z`
})

// ── Donut chart ───────────────────────────────────────────────────────────────
const donutSegments = computed(() => {
  const dist = revenue.value.plan_distribution || []
  const total = dist.reduce((s, d) => s + d.count, 0) || 1
  const circum = 2 * Math.PI * 48
  let offset = 0
  return dist.map(d => {
    const dash = (d.count / total) * circum
    const seg = { dash, gap: circum - dash, offset: -offset, color: d.color }
    offset += dash
    return seg
  })
})

// ── Platform stats ────────────────────────────────────────────────────────────
const platformStats = computed(() => [
  { label:'Total Sessions',  value: stats.value.total_sessions  || 0 },
  { label:'Active Clients',  value: stats.value.total_clients   || 0 },
  { label:'Hot Sessions',    value: stats.value.hot_sessions    || 0 },
  { label:'Active Tenants',  value: revenue.value.active_tenants },
  { label:'Total Tenants',   value: revenue.value.total_tenants },
  { label:'Net MRR Growth',  value: '$'+fmt(revenue.value.net_mrr_growth) },
])

// ── Health board ──────────────────────────────────────────────────────────────
const healthSearch = ref('')
const riskFilter   = ref('all')
const sortKey      = ref('health_score')
const sortAsc      = ref(true)

const riskFilters = [
  { val:'churn_risk',    label:'Churn Risk' },
  { val:'payment_issue', label:'Payment Issue' },
  { val:'at_risk',       label:'At Risk' },
  { val:'healthy',       label:'Healthy' },
]
const riskCount  = (val) => tenants.value.filter(t => t.risk === val).length
const alertCount = computed(() => alerts.value.filter(a => a.severity === 'critical').length)

const filteredTenants = computed(() => {
  let ts = [...tenants.value]
  if (riskFilter.value !== 'all') ts = ts.filter(t => t.risk === riskFilter.value)
  if (healthSearch.value) {
    const q = healthSearch.value.toLowerCase()
    ts = ts.filter(t => t.company.toLowerCase().includes(q) || t.email.toLowerCase().includes(q))
  }
  return ts.sort((a, b) => {
    const av = a[sortKey.value], bv = b[sortKey.value]
    return sortAsc.value ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1)
  })
})

function sortBy(key) {
  if (sortKey.value === key) sortAsc.value = !sortAsc.value
  else { sortKey.value = key; sortAsc.value = false }
}
function healthColor(s) {
  if (s >= 70) return '#22c55e'
  if (s >= 40) return '#f59e0b'
  return '#ef4444'
}

// ── Actions ───────────────────────────────────────────────────────────────────
async function impersonate(t) {
  if (!confirm(`Impersonate ${t.company}? A 15-min token will be issued and audit-logged.`)) return
  try {
    const res = await api.impersonateTenant(t.tenant_id)
    localStorage.setItem('cf_impersonate_return_token', localStorage.getItem('cf_access_token'))
    localStorage.setItem('cf_impersonate_return_user', localStorage.getItem('cf_user'))
    localStorage.setItem('cf_impersonating', 'true')
    localStorage.setItem('cf_access_token', res.access)
    window.location.href = '/portal/inbox'
  } catch(e) { alert('Impersonation failed: ' + e.message) }
}

async function extendTrial(t) {
  const days = prompt(`Extend trial for ${t.company} by how many days?`, '14')
  if (!days || isNaN(parseInt(days))) return
  try {
    await api.updateTenant(t.tenant_id, { extend_trial_days: parseInt(days) })
    await loadAll()
  } catch(e) { alert('Failed: ' + e.message) }
}

// ── Plan modal ────────────────────────────────────────────────────────────────
const planModal = ref({ open:false, tenant:null, selectedPlanId:null, remarks:'', saving:false })

function openPlanModal(t) {
  const cur = plans.value.find(p => p.name === t.plan)
  planModal.value = { open:true, tenant:t, selectedPlanId: cur?.id || null, remarks:'', saving:false }
}
async function savePlanChange() {
  if (!planModal.value.selectedPlanId) return
  planModal.value.saving = true
  try {
    await api.assignPlan(planModal.value.tenant.tenant_id, planModal.value.selectedPlanId, planModal.value.remarks)
    planModal.value.open = false
    await loadAll()
  } catch(e) { alert(e.message) } finally { planModal.value.saving = false }
}

// ── Override modal ────────────────────────────────────────────────────────────
const overrideModal = ref({ open:false, tenant:null, items:[], loading:false, saving:false, newFeature:'', newEnabled:true, newReason:'', newExpiry:'' })

const allFeatures = [
  {key:'allow_whatsapp',label:'WhatsApp'},{key:'allow_telegram',label:'Telegram'},
  {key:'allow_messenger',label:'Messenger'},{key:'allow_byok',label:'Custom AI (BYOK)'},
  {key:'allow_hubspot',label:'HubSpot CRM'},{key:'allow_slack',label:'Slack Notifications'},
  {key:'allow_webhooks',label:'Outbound Webhooks'},{key:'allow_god_view',label:'God View / Takeover'},
  {key:'allow_canned_responses',label:'Canned Responses'},{key:'allow_conversation_tags',label:'Conversation Tags'},
  {key:'allow_csv_export',label:'CSV Export'},{key:'allow_voice_input',label:'Voice Input'},
  {key:'allow_image_input',label:'Image Input'},{key:'remove_branding',label:'Remove Branding'},
  {key:'allow_custom_domain',label:'Custom Domain'},{key:'allow_api_access',label:'API Access'},
]

async function openOverridesModal(t) {
  overrideModal.value = { open:true, tenant:t, items:[], loading:true, saving:false, newFeature:'', newEnabled:true, newReason:'', newExpiry:'' }
  try { overrideModal.value.items = await api.getTenantFeatureOverrides(t.tenant_id) }
  catch {} finally { overrideModal.value.loading = false }
}
async function saveOverride() {
  if (!overrideModal.value.newFeature) return
  overrideModal.value.saving = true
  try {
    await api.createFeatureOverride(overrideModal.value.tenant.tenant_id, {
      feature_name: overrideModal.value.newFeature,
      enabled: overrideModal.value.newEnabled,
      reason: overrideModal.value.newReason,
      expires_at: overrideModal.value.newExpiry || null,
    })
    overrideModal.value.items = await api.getTenantFeatureOverrides(overrideModal.value.tenant.tenant_id)
    overrideModal.value.newFeature = ''
    overrideModal.value.newReason  = ''
    overrideModal.value.newExpiry  = ''
  } catch(e) { alert(e.message) } finally { overrideModal.value.saving = false }
}
async function deleteOverride(o) {
  if (!confirm('Remove this override?')) return
  await api.deleteFeatureOverride(overrideModal.value.tenant.tenant_id, o.id)
  overrideModal.value.items = overrideModal.value.items.filter(x => x.id !== o.id)
}

// ── Alerts ────────────────────────────────────────────────────────────────────
function alertActionLabel(action) {
  return { extend_trial:'Extend Trial', contact:'Contact', send_email:'Send Email', upgrade_plan:'Upgrade Plan' }[action] || action
}
function handleAlertAction(a) {
  const t = tenants.value.find(t => t.tenant_id === a.tenant_id)
  if (a.action === 'extend_trial' && t) extendTrial(t)
  else if (a.action === 'upgrade_plan' && t) openPlanModal(t)
  else alert(`Action: ${a.action} for ${a.label}`)
}

// ── Announcements ─────────────────────────────────────────────────────────────
const annForm   = ref({ title:'', body:'', type:'info', target:'all', cta_label:'', cta_url:'' })
const annSaving = ref(false)
const annSent   = ref(false)

async function createAnnouncement() {
  if (!annForm.value.title || !annForm.value.body) return
  annSaving.value = true
  try {
    await api.createAnnouncement(annForm.value)
    annSent.value = true
    annForm.value = { title:'', body:'', type:'info', target:'all', cta_label:'', cta_url:'' }
    setTimeout(() => annSent.value = false, 3000)
  } catch(e) { alert(e.message) } finally { annSaving.value = false }
}

// ── Audit log ─────────────────────────────────────────────────────────────────
async function loadAudit() {
  try {
    const res = await api.getAuditLog({ page: auditPage.value, search: auditSearch.value, action: auditAction.value })
    auditLogs.value  = res.results || []
    auditTotal.value = res.total   || 0
  } catch {}
}

function fmtDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-GB', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' })
}

// ── Load all ──────────────────────────────────────────────────────────────────
async function loadAll() {
  loading.value = true
  try {
    const [rev, health, al, st, pl] = await Promise.all([
      api.getRevenue().catch(() => ({})),
      api.getTenantHealthBoard().catch(() => ({tenants:[]})),
      api.getLifecycleAlerts().catch(() => ({alerts:[]})),
      api.getStats().catch(() => ({})),
      api.getPlans().catch(() => []),
    ])
    revenue.value = { mrr:0, arr:0, new_mrr:0, churned_mrr:0, net_mrr_growth:0, arpu:0, active_tenants:0, total_tenants:0, past_due:0, trialing:0, plan_distribution:[], mrr_trend:[], ...rev }
    tenants.value = health.tenants || []
    alerts.value  = al.alerts     || []
    stats.value   = st            || {}
    plans.value   = Array.isArray(pl) ? pl : []
    await loadAudit()
  } finally { loading.value = false }
}

onMounted(loadAll)

// ── SVG icon snippets ─────────────────────────────────────────────────────────
const iconDollar = `<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>`
const iconChart  = `<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`
const iconUp     = `<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>`
const iconDown   = `<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>`
const iconUser   = `<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`
const iconWarn   = `<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`
const iconClock  = `<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`
</script>

<style scoped>
* { box-sizing: border-box; }
.admin-container { display: flex; min-height: 100vh; background: #0a0a0a; color: #e2e8f0; font-family: 'Inter', -apple-system, sans-serif; }
.admin-main { flex: 1; padding: 28px 32px; overflow-y: auto; }

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.4px; }
.page-sub { font-size: 13px; color: #475569; margin-top: 3px; }
.header-right { display: flex; align-items: center; gap: 10px; }
.live-badge { display: flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600; color: #22c55e; background: rgba(34,197,94,0.08); padding: 5px 12px; border-radius: 20px; border: 1px solid rgba(34,197,94,0.2); }
.live-dot { width: 7px; height: 7px; border-radius: 50%; background: #22c55e; animation: pulse 1.5s infinite; }
.refresh-btn { display: flex; align-items: center; gap: 6px; padding: 7px 14px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 9px; font-size: 12px; color: #94a3b8; cursor: pointer; }
.refresh-btn:hover:not(:disabled) { background: rgba(255,255,255,0.1); }

.tab-row { display: flex; gap: 2px; border-bottom: 1px solid rgba(255,255,255,0.07); margin-bottom: 24px; overflow-x: auto; }
.tab-btn { position: relative; display: flex; align-items: center; gap: 7px; padding: 10px 16px; background: none; border: none; border-bottom: 2px solid transparent; font-size: 13px; font-weight: 500; color: #475569; cursor: pointer; margin-bottom: -1px; white-space: nowrap; transition: color 0.12s; }
.tab-btn:hover { color: #94a3b8; }
.tab-btn.active { color: #a5b4fc; border-bottom-color: #6366f1; }
.tab-badge { background: #ef4444; color: #fff; font-size: 10px; font-weight: 700; border-radius: 10px; padding: 1px 6px; }

.tab-content { animation: fadeIn 0.15s ease; }
@keyframes fadeIn { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:none; } }

.loading-state { display:flex; align-items:center; gap:12px; padding:60px 0; color:#475569; justify-content:center; font-size:14px; }
.spinner { width:24px; height:24px; border:2px solid rgba(255,255,255,0.08); border-top-color:#6366f1; border-radius:50%; animation:spin 0.7s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }

/* Revenue strip */
.revenue-strip { display:grid; grid-template-columns:repeat(7,1fr); gap:10px; margin-bottom:20px; }
.rev-card { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-radius:12px; padding:14px 16px; display:flex; align-items:flex-start; gap:10px; }
.rev-icon { flex-shrink:0; color:#6366f1; margin-top:2px; }
.rev-body { display:flex; flex-direction:column; gap:2px; min-width:0; }
.rev-label { font-size:11px; font-weight:600; color:#475569; text-transform:uppercase; letter-spacing:0.05em; }
.rev-value { font-size:20px; font-weight:700; color:#f1f5f9; line-height:1.2; }
.rev-sub { font-size:11px; color:#475569; }
.rev-sub.green { color:#22c55e; }
.rev-sub.red { color:#ef4444; }
.rev-mrr .rev-icon { color:#6366f1; }
.rev-arr .rev-icon { color:#8b5cf6; }
.rev-new .rev-icon { color:#22c55e; }
.rev-churn .rev-icon { color:#ef4444; }
.rev-arpu .rev-icon { color:#3b82f6; }
.rev-warn { border-color:rgba(239,68,68,0.3)!important; background:rgba(239,68,68,0.05)!important; }
.rev-warn .rev-icon { color:#ef4444; }
.rev-trial .rev-icon { color:#f59e0b; }

/* Charts */
.charts-row { display:grid; grid-template-columns:1fr 320px; gap:16px; margin-bottom:20px; }
.chart-card { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-radius:14px; padding:20px; }
.chart-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.chart-header h3 { font-size:14px; font-weight:600; color:#f1f5f9; }
.chart-sub { font-size:11px; color:#475569; }
.line-chart-wrap { display:flex; flex-direction:column; gap:8px; }
.line-chart { width:100%; height:120px; }
.line-labels { display:flex; justify-content:space-between; font-size:11px; color:#475569; padding:0 6px; }
.donut-label-big { font-size:18px; font-weight:700; fill:#f1f5f9; }
.donut-label-sm { font-size:9px; fill:#475569; }
.donut-wrap { display:flex; align-items:center; gap:16px; }
.donut-svg { width:120px; height:120px; flex-shrink:0; }
.donut-legend { display:flex; flex-direction:column; gap:8px; flex:1; }
.legend-row { display:flex; align-items:center; gap:8px; font-size:12px; }
.legend-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
.legend-plan { flex:1; color:#94a3b8; }
.legend-count { color:#f1f5f9; font-weight:600; width:24px; text-align:right; }
.legend-mrr { color:#22c55e; font-size:11px; width:44px; text-align:right; }

/* Stats row */
.stats-row { display:grid; grid-template-columns:repeat(6,1fr); gap:10px; }
.stat-mini { background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.06); border-radius:10px; padding:12px 14px; display:flex; flex-direction:column; gap:4px; }
.stat-mini-label { font-size:11px; color:#475569; text-transform:uppercase; letter-spacing:0.04em; }
.stat-mini-val { font-size:18px; font-weight:700; color:#f1f5f9; }

/* Health board */
.board-controls { display:flex; gap:12px; align-items:center; margin-bottom:16px; flex-wrap:wrap; }
.search-input { background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1); border-radius:9px; padding:8px 14px; font-size:13px; color:#e2e8f0; width:220px; outline:none; }
.search-input:focus { border-color:rgba(99,102,241,0.4); }
.risk-filters { display:flex; gap:6px; flex-wrap:wrap; }
.risk-pill { padding:5px 12px; border-radius:20px; font-size:12px; font-weight:500; border:1px solid rgba(255,255,255,0.1); background:none; color:#64748b; cursor:pointer; transition:all 0.12s; }
.risk-pill.rf-churn_risk.active { background:rgba(239,68,68,0.15); border-color:#ef4444; color:#fca5a5; }
.risk-pill.rf-payment_issue.active { background:rgba(245,158,11,0.15); border-color:#f59e0b; color:#fcd34d; }
.risk-pill.rf-at_risk.active { background:rgba(249,115,22,0.15); border-color:#f97316; color:#fed7aa; }
.risk-pill.rf-healthy.active { background:rgba(34,197,94,0.15); border-color:#22c55e; color:#86efac; }
.risk-count { font-weight:700; margin-left:4px; }

.health-table-wrap { overflow-x:auto; border-radius:12px; border:1px solid rgba(255,255,255,0.07); }
.health-table { width:100%; border-collapse:collapse; font-size:13px; }
.health-table thead { background:rgba(255,255,255,0.03); }
.health-table th { padding:11px 14px; text-align:left; font-size:11px; font-weight:600; color:#475569; text-transform:uppercase; letter-spacing:0.04em; cursor:pointer; white-space:nowrap; border-bottom:1px solid rgba(255,255,255,0.07); }
.health-table th:hover { color:#94a3b8; }
.health-table td { padding:12px 14px; border-bottom:1px solid rgba(255,255,255,0.04); vertical-align:middle; }
.tenant-row:hover td { background:rgba(255,255,255,0.02); }
.tenant-row:last-child td { border-bottom:none; }
.tenant-info { display:flex; align-items:center; gap:10px; }
.tenant-avatar { width:30px; height:30px; border-radius:8px; background:linear-gradient(135deg,#6366f1,#8b5cf6); display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; color:#fff; flex-shrink:0; }
.tenant-name { font-weight:600; color:#f1f5f9; font-size:13px; }
.tenant-email { font-size:11px; color:#475569; }
.plan-badge { padding:3px 8px; border-radius:5px; font-size:11px; font-weight:600; }
.plan-badge.plan-free { background:rgba(71,85,105,0.2); color:#94a3b8; }
.plan-badge.plan-starter { background:rgba(59,130,246,0.15); color:#93c5fd; }
.plan-badge.plan-growth { background:rgba(139,92,246,0.15); color:#c4b5fd; }
.plan-badge.plan-pro { background:rgba(245,158,11,0.15); color:#fcd34d; }
.plan-badge.plan-enterprise { background:rgba(239,68,68,0.15); color:#fca5a5; }
.session-num { font-weight:600; color:#a5b4fc; }
.mrr-val { font-weight:600; color:#22c55e; }
.stripe-badge { padding:2px 7px; border-radius:4px; font-size:10px; font-weight:600; text-transform:uppercase; }
.stripe-badge.stripe-active { background:rgba(34,197,94,0.12); color:#86efac; }
.stripe-badge.stripe-past_due { background:rgba(239,68,68,0.12); color:#fca5a5; }
.stripe-badge.stripe-trialing { background:rgba(245,158,11,0.12); color:#fcd34d; }
.stripe-badge.stripe-none, .stripe-badge.stripe-canceled { background:rgba(71,85,105,0.15); color:#64748b; }
.trial-badge { margin-left:6px; padding:2px 7px; border-radius:4px; font-size:10px; background:rgba(245,158,11,0.12); color:#fcd34d; }
.health-bar-wrap { display:flex; align-items:center; gap:8px; }
.health-bar { height:6px; border-radius:3px; transition:width 0.3s; min-width:4px; max-width:80px; }
.health-num { font-size:12px; font-weight:600; color:#94a3b8; min-width:24px; }
.risk-badge { padding:3px 8px; border-radius:5px; font-size:11px; font-weight:600; text-transform:capitalize; }
.risk-badge.risk-healthy { background:rgba(34,197,94,0.1); color:#86efac; }
.risk-badge.risk-at_risk { background:rgba(249,115,22,0.1); color:#fed7aa; }
.risk-badge.risk-churn_risk { background:rgba(239,68,68,0.1); color:#fca5a5; }
.risk-badge.risk-payment_issue { background:rgba(245,158,11,0.1); color:#fcd34d; }
.action-btns { display:flex; gap:4px; }
.act-btn { background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08); border-radius:6px; padding:4px 7px; font-size:13px; cursor:pointer; transition:background 0.12s; }
.act-btn:hover { background:rgba(255,255,255,0.12); }
.empty-row { text-align:center; color:#334155; padding:32px; font-size:13px; }
.sort-icon { color:#334155; font-size:10px; }

/* Alerts */
.alerts-list { display:flex; flex-direction:column; gap:10px; }
.alert-card { display:flex; align-items:center; gap:14px; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-radius:12px; padding:14px 18px; }
.alert-card.al-critical { border-color:rgba(239,68,68,0.25); background:rgba(239,68,68,0.05); }
.alert-card.al-warning { border-color:rgba(245,158,11,0.25); background:rgba(245,158,11,0.04); }
.al-icon { font-size:18px; flex-shrink:0; }
.al-body { flex:1; display:flex; flex-direction:column; gap:3px; }
.al-company { font-size:13px; font-weight:600; color:#f1f5f9; }
.al-msg { font-size:12px; color:#64748b; }
.al-actions { flex-shrink:0; }
.al-btn { padding:6px 14px; background:rgba(99,102,241,0.12); border:1px solid rgba(99,102,241,0.25); border-radius:8px; font-size:12px; color:#a5b4fc; cursor:pointer; }
.al-btn:hover { background:rgba(99,102,241,0.22); }
.empty-panel { display:flex; flex-direction:column; align-items:center; gap:12px; padding:60px 0; color:#334155; font-size:14px; }

/* Audit */
.audit-controls { display:flex; gap:10px; margin-bottom:16px; }
.sel-input { background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1); border-radius:9px; padding:8px 12px; font-size:13px; color:#e2e8f0; }
.audit-table-wrap { overflow-x:auto; border-radius:12px; border:1px solid rgba(255,255,255,0.07); }
.audit-table { width:100%; border-collapse:collapse; font-size:13px; }
.audit-table thead { background:rgba(255,255,255,0.03); }
.audit-table th { padding:10px 14px; text-align:left; font-size:11px; font-weight:600; color:#475569; text-transform:uppercase; letter-spacing:0.04em; border-bottom:1px solid rgba(255,255,255,0.07); }
.audit-table td { padding:11px 14px; border-bottom:1px solid rgba(255,255,255,0.04); }
.audit-table tr:last-child td { border-bottom:none; }
.audit-table tr:hover td { background:rgba(255,255,255,0.015); }
.mono { font-family:monospace; font-size:11px; }
.text-muted { color:#475569; }
.small { font-size:11px; }
.actor-badge { padding:2px 7px; background:rgba(99,102,241,0.1); border-radius:4px; color:#a5b4fc; font-size:12px; }
.action-chip { padding:2px 7px; border-radius:4px; font-size:11px; font-weight:600; background:rgba(255,255,255,0.06); color:#94a3b8; }
.audit-pagination { display:flex; align-items:center; gap:12px; padding:12px 16px; justify-content:center; font-size:13px; color:#475569; }
.audit-pagination button { background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:7px; padding:5px 12px; color:#94a3b8; cursor:pointer; }

/* Announcements */
.announce-layout { display:grid; grid-template-columns:1fr 300px; gap:20px; }
.card { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-radius:14px; padding:22px; }
.card-title { font-size:15px; font-weight:600; color:#f1f5f9; margin-bottom:18px; }
.form-field { display:flex; flex-direction:column; gap:6px; }
.form-field label { font-size:12px; color:#64748b; font-weight:500; }
.form-row { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:14px; }
.inp { background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:9px; padding:9px 12px; font-size:13px; color:#e2e8f0; font-family:inherit; width:100%; outline:none; }
.inp:focus { border-color:rgba(99,102,241,0.4); }
.btn-primary { width:100%; padding:10px; background:rgba(99,102,241,0.15); border:1px solid rgba(99,102,241,0.3); border-radius:9px; font-size:13px; font-weight:600; color:#a5b4fc; cursor:pointer; margin-top:14px; }
.btn-primary:hover:not(:disabled) { background:rgba(99,102,241,0.25); }
.btn-primary:disabled { opacity:0.5; cursor:not-allowed; }
.tips-list { padding-left:16px; display:flex; flex-direction:column; gap:10px; margin:0; }
.tips-list li { font-size:13px; color:#64748b; line-height:1.5; }
.tips-list code { background:rgba(99,102,241,0.1); color:#a5b4fc; padding:1px 5px; border-radius:4px; font-size:12px; }

/* Modals */
.modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.75); display:flex; align-items:center; justify-content:center; z-index:1000; }
.modal { background:#161616; border:1px solid rgba(255,255,255,0.1); border-radius:16px; padding:28px; min-width:420px; max-width:92vw; max-height:90vh; overflow-y:auto; }
.modal-wide { min-width:560px; }
.modal-title { font-size:16px; font-weight:700; color:#f1f5f9; margin-bottom:20px; }
.modal-actions { display:flex; justify-content:flex-end; gap:10px; margin-top:20px; }
.btn-ghost { padding:9px 18px; background:none; border:1px solid rgba(255,255,255,0.1); border-radius:9px; font-size:13px; color:#64748b; cursor:pointer; }
.btn-ghost:hover { border-color:rgba(255,255,255,0.2); color:#94a3b8; }
.override-list { display:flex; flex-direction:column; gap:8px; margin-bottom:16px; min-height:40px; }
.override-row { display:flex; align-items:center; gap:10px; background:rgba(255,255,255,0.03); border-radius:8px; padding:8px 12px; font-size:12px; }
.ov-feature { flex:1; color:#a5b4fc; font-weight:600; font-size:12px; }
.ov-on { color:#22c55e; font-weight:700; font-size:11px; }
.ov-off { color:#ef4444; font-weight:700; font-size:11px; }
.ov-reason { color:#64748b; flex:1; font-size:11px; }
.ov-exp { color:#475569; font-size:11px; white-space:nowrap; }
.override-add { border-top:1px solid rgba(255,255,255,0.07); padding-top:16px; }

@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

@media (max-width:1280px) {
  .revenue-strip { grid-template-columns:repeat(4,1fr); }
  .charts-row { grid-template-columns:1fr; }
  .stats-row { grid-template-columns:repeat(3,1fr); }
}
@media (max-width:768px) {
  .admin-main { padding:16px; }
  .revenue-strip { grid-template-columns:repeat(2,1fr); }
  .stats-row { grid-template-columns:repeat(2,1fr); }
  .announce-layout { grid-template-columns:1fr; }
}
</style>
