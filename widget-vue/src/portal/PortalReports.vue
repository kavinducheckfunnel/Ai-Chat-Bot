<template>
  <div class="reports-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Reports</h1>
        <p class="page-sub">Performance overview for your chatbot</p>
      </div>
      <div class="header-right">
        <PortalDateFilter v-model="period" @change="onDateChange" />
        <button class="export-btn" @click="exportCSV" :disabled="exporting" title="Download CSV">
          <svg v-if="!exporting" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          <span v-if="exporting" class="mini-spinner-sm"></span>
          {{ exporting ? 'Exporting…' : 'Export CSV' }}
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tab-nav">
      <button v-for="t in tabs" :key="t.key" class="tab-btn"
              :class="{ active: activeTab === t.key, locked: t.locked }"
              @click="t.locked ? showUpgrade(t.requiredPlan) : (activeTab = t.key)">
        {{ t.label }}
        <svg v-if="t.locked" width="11" height="11" fill="none" viewBox="0 0 24 24" style="margin-left:4px;opacity:.5"><rect x="3" y="11" width="18" height="11" rx="2" stroke="currentColor" stroke-width="2"/><path d="M7 11V7a5 5 0 0110 0v4" stroke="currentColor" stroke-width="2"/></svg>
      </button>
    </div>

    <div v-if="upgradeMsg" class="upgrade-banner">
      ⭐ {{ upgradeMsg }}
      <a href="/portal/billing" class="upgrade-link">Upgrade plan →</a>
      <button class="banner-close" @click="upgradeMsg = ''">✕</button>
    </div>

    <!-- KPI grid (8 cards) — shared layout across all tabs -->
    <div class="kpi-grid" v-if="!loading">
      <div class="kpi-card" v-for="c in kpiCards" :key="c.label">
        <div class="kpi-top">
          <div class="kpi-icon" :class="c.iconClass"><Icon :name="c.icon" /></div>
          <div class="kpi-delta" v-if="c.delta !== null && c.delta !== undefined" :class="deltaCls(c.delta)">
            <span>{{ c.delta > 0 ? '▲' : (c.delta < 0 ? '▼' : '') }} {{ fmtDeltaVal(c.delta, c.unit) }}</span>
            <span class="kpi-delta-sub">vs prev period</span>
          </div>
        </div>
        <div class="kpi-value">{{ c.value }}</div>
        <div class="kpi-label">{{ c.label }}</div>
        <div class="kpi-foot" v-if="c.sub">{{ c.sub }}</div>
      </div>
    </div>
    <div class="kpi-grid" v-else>
      <div class="kpi-card skeleton" v-for="n in 8" :key="n"><div class="sk-line"></div><div class="sk-line short"></div></div>
    </div>

    <template v-if="!loading">
      <!-- ═══════════════ OVERVIEW ═══════════════ -->
      <template v-if="activeTab === 'overview'">
        <div class="card">
          <div class="card-head"><h3 class="card-title">Daily Conversations</h3></div>
          <LineChart :chart="dailyConvChart" />
        </div>
        <div class="section-row">
          <div class="card">
            <h3 class="card-title">Lead Funnel</h3>
            <div class="funnel-list">
              <div class="funnel-row" v-for="s in leadFunnel" :key="s.label">
                <span class="funnel-name"><Icon :name="s.icon" class="inline-ico" /> {{ s.label }}</span>
                <div class="bar-track"><div class="bar-fill" :style="{ width: barPct(s.count, leadFunnel[0].count) + '%', background: s.color }"></div></div>
                <span class="funnel-count">{{ s.count }}</span>
                <span class="funnel-pct">{{ pctOf(s.count, leadFunnel[0].count) }}%</span>
              </div>
            </div>
          </div>
          <div class="card">
            <h3 class="card-title">Conversation Intent States</h3>
            <div class="state-list">
              <div class="state-row" v-for="s in intentStates" :key="s.label">
                <span class="state-dot" :style="{ background: s.color }"></span>
                <span class="state-name">{{ s.label }}</span>
                <div class="bar-track"><div class="bar-fill" :style="{ width: barPct(s.count, intentMax) + '%', background: s.color }"></div></div>
                <span class="state-count">{{ s.count }}</span>
                <span class="state-pct">{{ pctOf(s.count, intentTotal) }}%</span>
              </div>
            </div>
          </div>
        </div>
        <div class="card">
          <h3 class="card-title">Performance Snapshot</h3>
          <div class="snap-grid">
            <div class="snap-item" v-for="s in perfSnapshot" :key="s.label">
              <div class="snap-icon" :class="s.iconClass"><Icon :name="s.icon" /></div>
              <div><div class="snap-value">{{ s.value }}</div><div class="snap-label">{{ s.label }}</div><div class="snap-sub">{{ s.sub }}</div></div>
            </div>
          </div>
        </div>
      </template>

      <!-- ═══════════════ CHATS ═══════════════ -->
      <template v-else-if="activeTab === 'chats'">
        <div class="card">
          <div class="card-head"><h3 class="card-title">Daily Chat Volume</h3>
            <div class="legend"><span class="lg" style="--c:#6366f1">AI</span><span class="lg" style="--c:#22c55e">Human</span><span class="lg" style="--c:#f59e0b">Missed</span></div>
          </div>
          <LineChart :chart="chatVolumeChart" />
        </div>
        <div class="section-row">
          <div class="card">
            <h3 class="card-title">Chat Handling Breakdown</h3>
            <div class="brk-list">
              <div class="brk-row" v-for="b in chatHandling" :key="b.label">
                <span class="brk-name"><Icon :name="b.icon" class="inline-ico" /> {{ b.label }}</span>
                <div class="bar-track"><div class="bar-fill" :style="{ width: barPct(b.count, chatHandlingTotal) + '%', background: b.color }"></div></div>
                <span class="brk-count">{{ b.count }}</span>
                <span class="brk-pct">{{ pctOf(b.count, chatHandlingTotal) }}%</span>
              </div>
            </div>
            <p class="brk-foot">Percentages of total conversations ({{ chatHandlingTotal }})</p>
          </div>
          <div class="card">
            <h3 class="card-title">Conversation Activity</h3>
            <div class="act-list">
              <div class="act-row" v-for="a in conversationActivity" :key="a.label">
                <Icon :name="a.icon" class="inline-ico" />
                <span class="act-name">{{ a.label }}</span>
                <div class="bar-track"><div class="bar-fill" :style="{ width: a.bar + '%', background: '#6366f1' }"></div></div>
                <span class="act-val">{{ a.value }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="card">
          <h3 class="card-title">Recent Conversations</h3>
          <table class="data-table">
            <thead><tr><th>Visitor</th><th>Type</th><th>State</th><th>Heat</th><th>Messages</th><th>Date</th></tr></thead>
            <tbody>
              <tr v-for="s in recentSessions" :key="s.session_id">
                <td>{{ s.lead_email || 'Visitor #' + String(s.session_id).slice(0,6) }}</td>
                <td><span class="badge" :class="s.taken_over_by ? 'b-human' : 'b-ai'">{{ s.taken_over_by ? 'Human' : 'AI' }}</span></td>
                <td><span class="badge" :class="kanbanClass(s.kanban_state)">{{ s.conversation_state || s.kanban_state }}</span></td>
                <td><div class="t-heat"><div class="bar-track sm"><div class="bar-fill" :style="{ width: (s.heat_score||0)+'%', background: heatColor(s.heat_score) }"></div></div><span>{{ Math.round(s.heat_score||0) }}%</span></div></td>
                <td>{{ s.message_count || 0 }}</td>
                <td>{{ formatDateTime(s.created_at) }}</td>
              </tr>
              <tr v-if="!recentSessions.length"><td colspan="6" class="empty-row">No conversations yet.</td></tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- ═══════════════ LEADS ═══════════════ -->
      <template v-else-if="activeTab === 'leads'">
        <div class="card">
          <div class="card-head"><h3 class="card-title">Lead Funnel Trend</h3>
            <div class="legend"><span class="lg" style="--c:#6366f1">Qualified</span><span class="lg" style="--c:#f59e0b">Hot Leads</span><span class="lg" style="--c:#22c55e">Converted</span></div>
          </div>
          <LineChart :chart="leadTrendChart" />
        </div>
        <div class="section-row">
          <div class="card">
            <h3 class="card-title">Lead Pipeline</h3>
            <div class="funnel-list">
              <div class="funnel-row" v-for="s in leadFunnel" :key="s.label">
                <span class="funnel-name"><Icon :name="s.icon" class="inline-ico" /> {{ s.label }}</span>
                <div class="bar-track"><div class="bar-fill" :style="{ width: barPct(s.count, leadFunnel[0].count) + '%', background: s.color }"></div></div>
                <span class="funnel-count">{{ s.count }}</span>
                <span class="funnel-pct">{{ pctOf(s.count, leadFunnel[0].count) }}%</span>
              </div>
            </div>
          </div>
          <div class="card">
            <h3 class="card-title">Lead Quality Snapshot</h3>
            <div class="brk-list">
              <div class="brk-row" v-for="q in leadQuality" :key="q.label">
                <span class="brk-name"><Icon :name="q.icon" class="inline-ico" /> {{ q.label }}</span>
                <div class="bar-track"><div class="bar-fill" :style="{ width: q.bar + '%', background: q.color }"></div></div>
                <span class="brk-pct">{{ q.value }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="card">
          <h3 class="card-title">Recent Leads</h3>
          <table class="data-table">
            <thead><tr><th>Visitor</th><th>Stage</th><th>Source</th><th>Contact</th><th>Heat</th><th>Date</th></tr></thead>
            <tbody>
              <tr v-for="l in recentLeads" :key="l.session_id">
                <td>{{ l.visitor }}</td>
                <td><span class="badge" :class="kanbanClass(l.stage)">{{ l.stage }}</span></td>
                <td>{{ l.source }}</td>
                <td>{{ l.contact }}</td>
                <td><div class="t-heat"><div class="bar-track sm"><div class="bar-fill" :style="{ width: (l.heat||0)+'%', background: heatColor(l.heat) }"></div></div><span>{{ Math.round(l.heat||0) }}%</span></div></td>
                <td>{{ formatDateTime(l.created_at) }}</td>
              </tr>
              <tr v-if="!recentLeads.length"><td colspan="6" class="empty-row">No leads captured yet.</td></tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- ═══════════════ ENGAGEMENT ═══════════════ -->
      <template v-else-if="activeTab === 'engagement'">
        <div class="card">
          <div class="card-head"><h3 class="card-title">Engagement Trend</h3>
            <div class="legend"><span class="lg" style="--c:#6366f1">Page Views</span><span class="lg" style="--c:#3b82f6">Chat Starts</span><span class="lg" style="--c:#f59e0b">Exit Intent</span></div>
          </div>
          <LineChart :chart="engagementChart" />
        </div>
        <div class="section-row">
          <div class="card">
            <h3 class="card-title">Buyer Signal Averages</h3>
            <div class="brk-list">
              <div class="brk-row" v-for="s in signals" :key="s.label">
                <span class="brk-name">{{ s.label }}</span>
                <div class="bar-track"><div class="bar-fill" :style="{ width: s.value + '%', background: s.color }"></div></div>
                <span class="brk-pct" :style="{ color: s.color }">{{ s.value }}%</span>
              </div>
            </div>
          </div>
          <div class="card">
            <h3 class="card-title">Heat Distribution &amp; Pipeline</h3>
            <div class="heat-seg-row">
              <div class="heat-seg hot" :style="{ flex: Math.max(heatDist.hot,1) }"><b>{{ heatDist.hot }}</b><span>HOT</span></div>
              <div class="heat-seg warm" :style="{ flex: Math.max(heatDist.warm,1) }"><b>{{ heatDist.warm }}</b><span>WARM</span></div>
              <div class="heat-seg cold" :style="{ flex: Math.max(heatDist.cold,1) }"><b>{{ heatDist.cold }}</b><span>COLD</span></div>
            </div>
            <div class="avg-heat-line"><span>Avg Heat Score</span><b>{{ analytics.avg_heat_score || 0 }}%</b></div>
            <div class="pipe-list">
              <div class="pipe-row" v-for="k in kanbanBreakdown" :key="k.key">
                <span class="state-dot" :style="{ background: k.color }"></span>
                <span class="pipe-name">{{ k.label }}</span>
                <div class="bar-track"><div class="bar-fill" :style="{ width: barPct(k.count, kanbanMax) + '%', background: k.color }"></div></div>
                <span class="pipe-count">{{ k.count }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="card">
          <h3 class="card-title">Engagement Events &amp; Top Pages</h3>
          <table class="data-table">
            <thead><tr><th>Event / Page</th><th>Views</th><th>Chats Started</th><th>Leads</th><th>Heat</th><th>Avg Heat Score</th></tr></thead>
            <tbody>
              <tr v-for="p in topPages" :key="p.url">
                <td class="tp-url">{{ p.page }}</td>
                <td>{{ p.views }}</td>
                <td>{{ p.chats }}</td>
                <td>{{ p.leads }}</td>
                <td><div class="bar-track sm"><div class="bar-fill" :style="{ width: (p.avg_heat||0)+'%', background: heatColor(p.avg_heat) }"></div></div></td>
                <td>{{ p.avg_heat }}%</td>
              </tr>
              <tr v-if="!topPages.length"><td colspan="6" class="empty-row">No page-view data yet.</td></tr>
            </tbody>
          </table>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, h } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'
import { useToast } from '../composables/useToast'
import PortalDateFilter from './PortalDateFilter.vue'

const props = defineProps({ client: Object })
const api = useAdminApi()
const toast = useToast()

const loading = ref(true)
const exporting = ref(false)
const period = ref('30d')
const dateRange = ref({ period: '30d', dateFrom: null, dateTo: null })
const activeTab = ref('overview')
const analytics = ref({})
const recentSessions = ref([])
const upgradeMsg = ref('')
const metricLimit = ref(-1)

function onDateChange(payload) { dateRange.value = payload; period.value = payload.period; load() }

// ── Icons ───────────────────────────────────────────────────────────────────
const ICONS = {
  chat: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z',
  check: 'M20 6 9 17l-5-5',
  mail: 'M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zM22 6l-10 7L2 6',
  bolt: 'M13 2 3 14h9l-1 8 10-12h-9l1-8z',
  users: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
  clock: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2',
  leadplus: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM19 8v6M22 11h-6',
  fire: 'M12 2c1 3 5 4 5 8a5 5 0 1 1-10 0c0-2 1-3 2-4 0 2 2 2 2 0 0-2-1-3-1-4z',
  target: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12zM12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
  cart: 'M9 22a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM20 22a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM1 1h4l2.7 13.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L23 6H6',
  funnel: 'M22 3H2l8 9.5V19l4 2v-8.5L22 3z',
  percent: 'M19 5 5 19M6.5 6.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM17.5 14.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z',
  trophy: 'M6 9a6 6 0 0 0 12 0V3H6v6zM6 5H3v2a3 3 0 0 0 3 3M18 5h3v2a3 3 0 0 1-3 3M9 21h6M12 15v6',
  bot: 'M12 8V4H8M4 8h16v12H4zM2 14h2M20 14h2M9 13v2M15 13v2',
  eye: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
  exit: 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9',
  tag: 'M20.6 13.4l-7.2 7.2a2 2 0 0 1-2.8 0L2 12V2h10l8.6 8.6a2 2 0 0 1 0 2.8zM7 7h.01',
  activity: 'M22 12h-4l-3 9L9 3l-3 9H2',
  msg: 'M21 11.5a8.4 8.4 0 0 1-9 8.4 8.5 8.5 0 0 1-3.9-.9L3 21l1.9-4.1A8.5 8.5 0 1 1 21 11.5z',
}
const Icon = { props: ['name'], render() { return h('svg', { width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.9, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [h('path', { d: ICONS[this.name] || ICONS.chat })]) } }

// ── Metric helpers ────────────────────────────────────────────────────────────
function val(key) { const m = analytics.value[key]; return (m && typeof m === 'object' && 'value' in m) ? m.value : (m ?? 0) }
function delta(key) { const m = analytics.value[key]; return (m && typeof m === 'object' && 'delta' in m) ? m.delta : 0 }
const leadsData = computed(() => analytics.value.leads || {})
function leadVal(key) { const m = leadsData.value[key]; return (m && typeof m === 'object' && 'value' in m) ? m.value : (m ?? 0) }
function leadDelta(key) { const m = leadsData.value[key]; return (m && typeof m === 'object' && 'delta' in m) ? m.delta : 0 }

function deltaCls(d) { if (!d) return 'd-neutral'; return d > 0 ? 'd-up' : 'd-down' }
function round1(x) { return Math.round((Number(x) || 0) * 10) / 10 }   // 1-decimal, kills float noise
function fmtDeltaVal(d, unit) {
  const a = Math.abs(Number(d) || 0)
  if (unit === '%') return round1(a) + '%'
  if (unit === 's') return Math.round(a) + 's'
  return Math.round(a)
}
function fmtDuration(s) {
  s = Math.max(0, Math.round(s || 0))
  const h2 = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60
  if (h2 > 0) return `${h2}h ${m}m`
  if (m > 0) return `${m}m ${sec}s`
  return `${sec}s`
}
function heatColor(score) { if (!score) return '#334155'; if (score >= 70) return '#ef4444'; if (score >= 40) return '#f59e0b'; return '#6366f1' }
function kanbanClass(s) { return ({ HOT_LEAD: 'b-hot', CONVERTED: 'b-converted', ENGAGED: 'b-engaged', QUALIFIED: 'b-qualified', READY_TO_BUY: 'b-ready', LOST: 'b-lost' })[s] || 'b-new' }
function formatDateTime(ts) { if (!ts) return '—'; const d = new Date(ts); return d.toLocaleDateString([], { month: 'numeric', day: 'numeric', year: 'numeric' }) + '  ' + d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) }
function pctOf(n, total) { return total ? Math.round((n / total) * 1000) / 10 : 0 }
function barPct(n, max) { return max ? Math.max(Math.round((n / max) * 100), n > 0 ? 4 : 0) : 0 }

// ── Feature gating ──────────────────────────────────────────────────────────
const canSeeChatsTab = computed(() => metricLimit.value < 0 || metricLimit.value >= 7)
const canSeeEngagementTab = computed(() => metricLimit.value < 0)
function showUpgrade(plan) { upgradeMsg.value = `This section requires the ${plan} plan or higher.` }
const tabs = computed(() => [
  { key: 'overview', label: 'Overview', locked: false },
  { key: 'chats', label: 'Chats', locked: !canSeeChatsTab.value, requiredPlan: 'Growth' },
  { key: 'leads', label: 'Leads', locked: !canSeeChatsTab.value, requiredPlan: 'Growth' },
  { key: 'engagement', label: 'Engagement', locked: !canSeeEngagementTab.value, requiredPlan: 'Pro' },
])

// ── KPI cards per tab ─────────────────────────────────────────────────────────
const events = computed(() => analytics.value.analytics_events || {})
const kpiCards = computed(() => {
  if (activeTab.value === 'chats') return [
    { label: 'AI Handled', icon: 'bot', iconClass: 'i-indigo', value: val('ai_handled'), delta: delta('ai_handled') },
    { label: 'Human Handoff', icon: 'users', iconClass: 'i-blue', value: val('manual_handled'), delta: delta('manual_handled') },
    { label: 'Opened, No Message', icon: 'mail', iconClass: 'i-amber', value: val('opened_no_message'), delta: delta('opened_no_message') },
    { label: 'AI Resolution Rate', icon: 'bolt', iconClass: 'i-purple', value: round1(val('ai_resolution_rate')) + '%', delta: delta('ai_resolution_rate'), unit: '%' },
    { label: 'Answered Chats', icon: 'check', iconClass: 'i-green', value: val('answered_chats'), delta: delta('answered_chats') },
    { label: 'Avg Chat Duration', icon: 'clock', iconClass: 'i-blue', value: fmtDuration(val('avg_duration_seconds')), delta: null, sub: 'over ' + val('answered_chats') + ' answered chats' },
    { label: 'Avg First Response', icon: 'clock', iconClass: 'i-indigo', value: (val('ai_response_seconds') || 0) + 's', delta: null, sub: 'avg AI reply time' },
    { label: 'Chats per Hour (AI)', icon: 'activity', iconClass: 'i-green', value: val('chats_per_hour') || 0, delta: null, sub: 'throughput during active hours' },
  ]
  if (activeTab.value === 'leads') return [
    { label: 'Leads Captured', icon: 'leadplus', iconClass: 'i-indigo', value: leadVal('captured'), delta: leadDelta('captured') },
    { label: 'Qualified Leads', icon: 'target', iconClass: 'i-blue', value: leadVal('qualified'), delta: leadDelta('qualified') },
    { label: 'Hot Leads', icon: 'fire', iconClass: 'i-red', value: leadVal('hot'), delta: leadDelta('hot') },
    { label: 'Ready to Buy', icon: 'cart', iconClass: 'i-amber', value: leadVal('ready_to_buy'), delta: leadDelta('ready_to_buy') },
    { label: 'Converted Leads', icon: 'check', iconClass: 'i-green', value: leadVal('converted'), delta: leadDelta('converted') },
    { label: 'Lead Capture Rate', icon: 'funnel', iconClass: 'i-purple', value: round1(leadVal('capture_rate')) + '%', delta: leadDelta('capture_rate'), unit: '%' },
    { label: 'Hot Lead Rate', icon: 'percent', iconClass: 'i-amber', value: round1(leadVal('hot_lead_rate')) + '%', delta: leadDelta('hot_lead_rate'), unit: '%' },
    { label: 'Conversion Rate', icon: 'trophy', iconClass: 'i-green', value: round1(leadVal('conversion_rate')) + '%', delta: leadDelta('conversion_rate'), unit: '%' },
  ]
  if (activeTab.value === 'engagement') return [
    { label: 'Page Views', icon: 'eye', iconClass: 'i-indigo', value: events.value.page_views || 0, delta: null },
    { label: 'Chat Start Rate', icon: 'chat', iconClass: 'i-blue', value: round1(val('chat_start_rate')) + '%', delta: delta('chat_start_rate'), unit: '%' },
    { label: 'Opened, No Message', icon: 'mail', iconClass: 'i-amber', value: val('opened_no_message'), delta: delta('opened_no_message') },
    { label: 'Avg Heat Score', icon: 'fire', iconClass: 'i-pink', value: round1(analytics.value.avg_heat_score || 0) + '%', delta: null },
    { label: 'Exit Intent Fired', icon: 'exit', iconClass: 'i-red', value: events.value.exit_intent_count || 0, delta: null },
    { label: 'Pricing Page Visits', icon: 'tag', iconClass: 'i-purple', value: events.value.pricing_page_visits || 0, delta: null },
    { label: 'Leads Captured', icon: 'leadplus', iconClass: 'i-green', value: val('leads_captured'), delta: delta('leads_captured') },
    { label: 'High Heat Conversations', icon: 'fire', iconClass: 'i-red', value: val('high_heat_conversations'), delta: delta('high_heat_conversations') },
  ]
  // overview
  return [
    { label: 'Total Conversations', icon: 'chat', iconClass: 'i-indigo', value: val('total_sessions'), delta: delta('total_sessions') },
    { label: 'Answered Chats', icon: 'check', iconClass: 'i-green', value: val('answered_chats'), delta: delta('answered_chats') },
    { label: 'Opened, No Message', icon: 'mail', iconClass: 'i-amber', value: val('opened_no_message'), delta: delta('opened_no_message') },
    { label: 'AI Resolution Rate', icon: 'bolt', iconClass: 'i-purple', value: round1(val('ai_resolution_rate')) + '%', delta: delta('ai_resolution_rate'), unit: '%' },
    { label: 'Unique Visitors', icon: 'users', iconClass: 'i-blue', value: val('unique_visitors'), delta: delta('unique_visitors') },
    { label: 'Avg Chat Duration', icon: 'clock', iconClass: 'i-blue', value: fmtDuration(val('avg_duration_seconds')), delta: null, sub: 'over ' + val('answered_chats') + ' answered chats' },
    { label: 'Leads Captured', icon: 'leadplus', iconClass: 'i-pink', value: val('leads_captured'), delta: delta('leads_captured') },
    { label: 'Hot Leads', icon: 'fire', iconClass: 'i-amber', value: val('hot_sessions'), delta: delta('hot_sessions') },
  ]
})

// ── Funnels / breakdowns ───────────────────────────────────────────────────
const leadFunnel = computed(() => {
  const lf = analytics.value.lead_funnel || {}
  return [
    { label: 'Chat Started', count: lf.chat_started || 0, color: '#6366f1', icon: 'chat' },
    { label: 'Qualified', count: lf.qualified || 0, color: '#3b82f6', icon: 'target' },
    { label: 'Hot Lead', count: lf.hot_lead || 0, color: '#f59e0b', icon: 'fire' },
    { label: 'Ready to Buy', count: lf.ready_to_buy || 0, color: '#22c55e', icon: 'cart' },
    { label: 'Converted', count: lf.converted || 0, color: '#10b981', icon: 'check' },
  ]
})
const intentStates = computed(() => {
  const f = analytics.value.funnel || {}
  return [
    { label: 'Research', count: f.RESEARCH || 0, color: '#3b82f6' },
    { label: 'Evaluation', count: f.EVALUATION || 0, color: '#6366f1' },
    { label: 'Objection', count: f.OBJECTION || 0, color: '#f59e0b' },
    { label: 'Recovery', count: f.RECOVERY || 0, color: '#ef4444' },
    { label: 'Ready to buy', count: f.READY_TO_BUY || 0, color: '#22c55e' },
  ]
})
const intentTotal = computed(() => intentStates.value.reduce((a, s) => a + s.count, 0))
const intentMax = computed(() => Math.max(...intentStates.value.map(s => s.count), 1))

const perfSnapshot = computed(() => {
  const total = val('total_sessions') || 1
  return [
    { label: 'AI Handled', icon: 'bot', iconClass: 'i-indigo', value: val('ai_handled'), sub: pctOf(val('ai_handled'), total) + '% of conversations' },
    { label: 'Human Handoff', icon: 'users', iconClass: 'i-blue', value: val('manual_handled'), sub: pctOf(val('manual_handled'), total) + '% of conversations' },
    { label: 'Avg First Response', icon: 'clock', iconClass: 'i-green', value: (val('ai_response_seconds') || 0) + 's', sub: 'response time' },
    { label: 'Total Chat Time', icon: 'clock', iconClass: 'i-amber', value: fmtDuration(val('total_duration_seconds')), sub: 'over ' + val('answered_chats') + ' answered chats' },
  ]
})

const chatHandlingTotal = computed(() => val('total_sessions'))
const chatHandling = computed(() => [
  { label: 'AI Handled', icon: 'bot', count: val('ai_handled'), color: '#6366f1' },
  { label: 'Human Handoff', icon: 'users', count: val('manual_handled'), color: '#3b82f6' },
  { label: 'Opened No Message', icon: 'mail', count: val('opened_no_message'), color: '#f59e0b' },
  { label: 'Answered Chats', icon: 'check', count: val('answered_chats'), color: '#22c55e' },
])
const conversationActivity = computed(() => {
  const a = analytics.value
  const dur = val('avg_duration_seconds'), tot = val('total_duration_seconds')
  return [
    { label: 'Avg Messages / Chat', icon: 'msg', value: a.avg_messages_per_chat || 0, bar: Math.min((a.avg_messages_per_chat || 0) * 8, 100) },
    { label: 'Avg First Response', icon: 'clock', value: (val('ai_response_seconds') || 0) + 's', bar: Math.min((val('ai_response_seconds') || 0) * 10, 100) },
    { label: 'Avg Chat Duration', icon: 'clock', value: fmtDuration(dur), bar: tot ? Math.min((dur / (tot || 1)) * 100 * 20, 100) : 0 },
    { label: 'Total Chat Time', icon: 'clock', value: fmtDuration(tot), bar: 100 },
    { label: 'Peak Hours', icon: 'activity', value: a.peak_hours || '—', bar: 60 },
  ]
})

const signals = computed(() => [
  { label: 'Purchase Intent', value: analytics.value.avg_intent || 0, color: '#6366f1' },
  { label: 'Budget Signal', value: analytics.value.avg_budget || 0, color: '#22c55e' },
  { label: 'Urgency Signal', value: analytics.value.avg_urgency || 0, color: '#f59e0b' },
])
const leadQuality = computed(() => {
  const l = leadsData.value
  return [
    { label: 'Avg Heat Score', icon: 'fire', value: (l.avg_heat || 0) + '%', bar: l.avg_heat || 0, color: '#ef4444' },
    { label: 'Purchase Intent', icon: 'bolt', value: (l.avg_intent || 0) + '%', bar: l.avg_intent || 0, color: '#6366f1' },
    { label: 'Budget Signal', icon: 'tag', value: (l.avg_budget || 0) + '%', bar: l.avg_budget || 0, color: '#22c55e' },
    { label: 'Urgency Signal', icon: 'bolt', value: (l.avg_urgency || 0) + '%', bar: l.avg_urgency || 0, color: '#f59e0b' },
    { label: 'Contact Captured', icon: 'leadplus', value: leadVal('contact_captured'), bar: pctOf(leadVal('contact_captured'), val('answered_chats') || 1), color: '#a855f7' },
  ]
})
const heatDist = computed(() => analytics.value.heat_distribution || { hot: 0, warm: 0, cold: 0 })
const kanbanBreakdown = computed(() => {
  const kb = analytics.value.kanban_breakdown || {}
  return [
    { key: 'NEW', label: 'New', count: kb.NEW || 0, color: '#64748b' },
    { key: 'ENGAGED', label: 'Engaged', count: kb.ENGAGED || 0, color: '#3b82f6' },
    { key: 'QUALIFIED', label: 'Qualified', count: kb.QUALIFIED || 0, color: '#a855f7' },
    { key: 'HOT_LEAD', label: 'Hot Lead', count: kb.HOT_LEAD || 0, color: '#f59e0b' },
    { key: 'READY_TO_BUY', label: 'Ready to Buy', count: kb.READY_TO_BUY || 0, color: '#fb923c' },
    { key: 'CONVERTED', label: 'Converted', count: kb.CONVERTED || 0, color: '#22c55e' },
    { key: 'LOST', label: 'Lost', count: kb.LOST || 0, color: '#ef4444' },
  ]
})
const kanbanMax = computed(() => Math.max(...kanbanBreakdown.value.map(k => k.count), 1))
const topPages = computed(() => analytics.value.top_pages || [])
const recentLeads = computed(() => analytics.value.recent_leads || [])

// ── Charts (multi-series SVG line) ──────────────────────────────────────────
function buildChart(rows, series) {
  const W = 920, H = 180, padX = 10, padTop = 12, padBottom = 26
  if (!rows || rows.length < 2) return { empty: true }
  let max = 1
  rows.forEach(r => series.forEach(s => { max = Math.max(max, r[s.key] || 0) }))
  const n = rows.length
  const x = i => padX + (i / (n - 1)) * (W - 2 * padX)
  const y = v => padTop + (1 - (v / max)) * (H - padTop - padBottom)
  const lines = series.map(s => {
    const pts = rows.map((r, i) => `${x(i).toFixed(1)},${y(r[s.key] || 0).toFixed(1)}`)
    return {
      color: s.color,
      poly: pts.join(' '),
      area: s.area ? `${pts.join(' ')} ${x(n - 1).toFixed(1)},${(H - padBottom).toFixed(1)} ${x(0).toFixed(1)},${(H - padBottom).toFixed(1)}` : '',
      dots: rows.map((r, i) => ({ cx: x(i).toFixed(1), cy: y(r[s.key] || 0).toFixed(1) })),
    }
  })
  const step = Math.max(1, Math.floor(n / 6))
  const labels = rows.map((r, i) => ({ left: (x(i) / W * 100), text: r.date })).filter((_, i) => i % step === 0 || i === n - 1)
  return { empty: false, W, H, padBottom, lines, labels, gridYs: [padTop, padTop + (H - padTop - padBottom) / 2, H - padBottom] }
}
const dailyConvChart = computed(() => buildChart(analytics.value.daily_trend, [{ key: 'count', color: '#6366f1', area: true }]))
const chatVolumeChart = computed(() => buildChart(analytics.value.daily_trend, [{ key: 'ai', color: '#6366f1', area: true }, { key: 'human', color: '#22c55e' }, { key: 'missed', color: '#f59e0b' }]))
const leadTrendChart = computed(() => buildChart(analytics.value.lead_funnel_trend, [{ key: 'qualified', color: '#6366f1', area: true }, { key: 'hot', color: '#f59e0b' }, { key: 'converted', color: '#22c55e' }]))
const engagementChart = computed(() => buildChart(analytics.value.engagement_trend, [{ key: 'page_views', color: '#6366f1', area: true }, { key: 'chat_starts', color: '#3b82f6' }, { key: 'exit_intent', color: '#f59e0b' }]))

const LineChart = {
  props: ['chart'],
  setup(p) {
    return () => {
      const c = p.chart
      if (!c || c.empty) return h('div', { class: 'chart-empty' }, 'Not enough data yet.')
      // IMPORTANT: positioning is set INLINE (not via the scoped .chart-x CSS),
      // because this is a render-function component whose elements don't receive
      // PortalReports' scoped-style attribute — so the scoped `position:absolute`
      // never applied and the x-axis labels collapsed inline (bunched together).
      return h('div', { class: 'chart-wrap', style: { position: 'relative' } }, [
        h('svg', { class: 'line-svg', viewBox: `0 0 ${c.W} ${c.H}`, preserveAspectRatio: 'none',
          style: { width: '100%', height: '180px', display: 'block', color: 'var(--cf-border-subtle)' } }, [
          ...c.gridYs.map(gy => h('line', { x1: 0, y1: gy, x2: c.W, y2: gy, stroke: 'currentColor', 'stroke-width': 0.5 })),
          ...c.lines.flatMap(ln => {
            const nodes = []
            if (ln.area) nodes.push(h('polygon', { points: ln.area, fill: ln.color, 'fill-opacity': 0.12 }))
            nodes.push(h('polyline', { points: ln.poly, fill: 'none', stroke: ln.color, 'stroke-width': 2, 'stroke-linejoin': 'round' }))
            ln.dots.forEach(d => nodes.push(h('circle', { cx: d.cx, cy: d.cy, r: 2.4, fill: ln.color })))
            return nodes
          }),
        ]),
        h('div', { class: 'chart-x', style: { position: 'relative', height: '18px', marginTop: '4px' } },
          c.labels.map(l => h('span', {
            style: {
              position: 'absolute',
              left: l.left + '%',
              transform: l.left <= 4 ? 'translateX(0)' : (l.left >= 96 ? 'translateX(-100%)' : 'translateX(-50%)'),
              fontSize: '10.5px',
              color: 'var(--cf-text-muted)',
              whiteSpace: 'nowrap',
            },
          }, l.text))),
      ])
    }
  },
}

// ── Load / export / refresh ──────────────────────────────────────────────────
async function load(silent = false) {
  if (!props.client) return
  if (!silent) loading.value = true
  try {
    const dr = dateRange.value || {}
    const [a, sessions, sub] = await Promise.all([
      api.getPortalAnalytics(props.client.id, period.value, { dateFrom: dr.dateFrom, dateTo: dr.dateTo }),
      api.getPortalSessions(props.client.id, { limit: 12 }),
      api.getSubscription().catch(() => null),
    ])
    analytics.value = a || {}
    recentSessions.value = Array.isArray(sessions) ? sessions : (sessions?.results || [])
    if (sub?.plan?.max_dashboard_metrics != null) metricLimit.value = sub.plan.max_dashboard_metrics
  } catch {} finally { if (!silent) loading.value = false }
}
async function exportCSV() {
  if (!props.client) return
  exporting.value = true
  try { await api.exportAnalyticsCSV(props.client.id, period.value === 'custom' ? '30d' : period.value) }
  catch (e) { toast.error('Export failed: ' + (e.message || 'Unknown error')) }
  finally { exporting.value = false }
}
let refreshTimer = null
function startAutoRefresh() { stopAutoRefresh(); refreshTimer = setInterval(() => { if (document.visibilityState === 'visible') load(true) }, 45000) }
function stopAutoRefresh() { if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null } }
onMounted(() => { load(); startAutoRefresh() })
onUnmounted(stopAutoRefresh)
watch(() => props.client, () => load())
</script>

<style scoped>
* { box-sizing: border-box; }
.reports-page { padding: 26px 30px 40px; font-family: 'Inter', -apple-system, sans-serif; }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 18px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--cf-text-primary); letter-spacing: -.5px; }
.page-sub { font-size: 13px; color: var(--cf-text-muted); margin-top: 3px; }
.header-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.export-btn { display: inline-flex; align-items: center; gap: 7px; padding: 8px 14px; background: var(--cf-bg-surface); border: 1px solid var(--cf-border-default); border-radius: 9px; font-size: 13px; font-weight: 600; color: var(--cf-text-secondary); cursor: pointer; font-family: inherit; }
.export-btn:hover { border-color: #6366f1; color: #a5b4fc; }
.export-btn:disabled { opacity: .5; }
.mini-spinner-sm { width: 13px; height: 13px; border: 2px solid var(--cf-border-default); border-top-color: #6366f1; border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.tab-nav { display: flex; gap: 4px; border-bottom: 1px solid var(--cf-border-subtle); margin-bottom: 22px; }
.tab-btn { display: inline-flex; align-items: center; padding: 11px 16px; background: none; border: none; border-bottom: 2px solid transparent; font-size: 14px; font-weight: 600; color: var(--cf-text-muted); cursor: pointer; margin-bottom: -1px; font-family: inherit; }
.tab-btn:hover { color: var(--cf-text-secondary); }
.tab-btn.active { color: #a5b4fc; border-bottom-color: #6366f1; }

.upgrade-banner { display: flex; align-items: center; gap: 10px; background: rgba(168,85,247,.1); border: 1px solid rgba(168,85,247,.3); border-radius: 10px; padding: 10px 14px; font-size: 13px; color: var(--cf-text-secondary); margin-bottom: 18px; }
.upgrade-link { color: #c084fc; font-weight: 600; text-decoration: none; }
.banner-close { margin-left: auto; background: none; border: none; color: var(--cf-text-muted); cursor: pointer; }

/* KPI grid */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 16px; }
.kpi-card { background: var(--cf-bg-surface-raised); border: 1px solid var(--cf-border-subtle); border-radius: 14px; padding: 16px 18px; min-height: 116px; display: flex; flex-direction: column; }
.kpi-top { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 10px; }
.kpi-icon { width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.i-indigo { background: rgba(99,102,241,.14); color: #a5b4fc; }
.i-blue { background: rgba(59,130,246,.14); color: #60a5fa; }
.i-green { background: rgba(34,197,94,.14); color: #4ade80; }
.i-amber { background: rgba(245,158,11,.14); color: #fbbf24; }
.i-purple { background: rgba(168,85,247,.14); color: #c084fc; }
.i-red { background: rgba(239,68,68,.14); color: #f87171; }
.i-pink { background: rgba(236,72,153,.14); color: #f472b6; }
.kpi-delta { display: flex; flex-direction: column; align-items: flex-end; font-size: 12px; font-weight: 600; }
.kpi-delta-sub { font-size: 10px; color: var(--cf-text-muted); font-weight: 500; }
.d-up { color: #22c55e; }
.d-down { color: #ef4444; }
.d-neutral { color: var(--cf-text-muted); }
.kpi-value { font-size: 26px; font-weight: 800; color: var(--cf-text-primary); letter-spacing: -.5px; line-height: 1.1; }
.kpi-label { font-size: 12.5px; color: var(--cf-text-muted); margin-top: 4px; font-weight: 500; }
.kpi-foot { font-size: 11px; color: var(--cf-text-muted); margin-top: auto; padding-top: 6px; opacity: .8; }
.kpi-card.skeleton { gap: 10px; }
.sk-line { height: 16px; background: var(--cf-skeleton-color, #1e293b); border-radius: 5px; }
.sk-line.short { width: 55%; height: 12px; }

/* Cards / sections */
.card { background: var(--cf-bg-surface-raised); border: 1px solid var(--cf-border-subtle); border-radius: 14px; padding: 18px 20px; margin-bottom: 16px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; flex-wrap: wrap; gap: 8px; }
.card-title { font-size: 15px; font-weight: 700; color: var(--cf-text-primary); margin: 0 0 14px; }
.card-head .card-title { margin: 0; }
.section-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

.legend { display: flex; gap: 14px; }
.lg { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: var(--cf-text-muted); }
.lg::before { content: ''; width: 9px; height: 9px; border-radius: 50%; background: var(--c); }

/* Chart */
.chart-wrap { position: relative; }
.line-svg { width: 100%; height: 180px; color: var(--cf-border-subtle); display: block; }
.grid-line { opacity: .5; }
.chart-x { position: relative; height: 16px; margin-top: 2px; }
.chart-x span { position: absolute; transform: translateX(-50%); font-size: 10.5px; color: var(--cf-text-muted); white-space: nowrap; }
.chart-empty { padding: 50px; text-align: center; color: var(--cf-text-muted); font-size: 13px; }

/* Bars / lists */
.bar-track { flex: 1; height: 8px; background: var(--cf-bg-input, #0f172a); border-radius: 5px; overflow: hidden; }
.bar-track.sm { height: 6px; width: 70px; flex: none; }
.bar-fill { height: 100%; border-radius: 5px; transition: width .4s; }

.funnel-list, .state-list, .brk-list, .act-list, .pipe-list { display: flex; flex-direction: column; gap: 13px; }
.funnel-row, .brk-row { display: grid; grid-template-columns: 130px 1fr auto auto; align-items: center; gap: 12px; }
.state-row, .pipe-row { display: grid; grid-template-columns: 14px 110px 1fr auto auto; align-items: center; gap: 10px; }
.pipe-row { grid-template-columns: 14px 110px 1fr auto; }
.act-row { display: grid; grid-template-columns: 18px 150px 1fr auto; align-items: center; gap: 10px; }
.funnel-name, .brk-name, .state-name, .pipe-name, .act-name { font-size: 13px; color: var(--cf-text-secondary); font-weight: 500; display: inline-flex; align-items: center; gap: 7px; }
.inline-ico { color: var(--cf-text-muted); flex-shrink: 0; }
.funnel-count, .brk-count, .state-count, .pipe-count, .act-val { font-size: 14px; font-weight: 700; color: var(--cf-text-primary); text-align: right; min-width: 32px; }
.funnel-pct, .state-pct, .brk-pct { font-size: 12px; color: var(--cf-text-muted); text-align: right; min-width: 44px; font-variant-numeric: tabular-nums; }
.state-dot { width: 9px; height: 9px; border-radius: 50%; }
.brk-foot { font-size: 11px; color: var(--cf-text-muted); margin: 12px 0 0; }

/* Snapshot grid */
.snap-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.snap-item { display: flex; align-items: center; gap: 12px; background: var(--cf-bg-surface); border: 1px solid var(--cf-border-subtle); border-radius: 11px; padding: 14px; }
.snap-icon { width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.snap-value { font-size: 18px; font-weight: 800; color: var(--cf-text-primary); }
.snap-label { font-size: 12px; color: var(--cf-text-secondary); font-weight: 600; }
.snap-sub { font-size: 11px; color: var(--cf-text-muted); }

/* Heat distribution */
.heat-seg-row { display: flex; gap: 4px; height: 64px; margin-bottom: 12px; }
.heat-seg { border-radius: 9px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #fff; min-width: 56px; }
.heat-seg b { font-size: 20px; font-weight: 800; }
.heat-seg span { font-size: 10px; letter-spacing: .08em; opacity: .9; }
.heat-seg.hot { background: rgba(239,68,68,.85); }
.heat-seg.warm { background: rgba(245,158,11,.8); }
.heat-seg.cold { background: rgba(99,102,241,.55); }
.avg-heat-line { display: flex; justify-content: space-between; font-size: 13px; color: var(--cf-text-muted); padding: 8px 0 14px; border-bottom: 1px solid var(--cf-border-subtle); margin-bottom: 14px; }
.avg-heat-line b { color: var(--cf-text-primary); font-size: 15px; }

/* Tables */
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; color: var(--cf-text-muted); padding: 8px 12px; border-bottom: 1px solid var(--cf-border-subtle); white-space: nowrap; }
.data-table td { font-size: 13px; color: var(--cf-text-secondary); padding: 11px 12px; border-bottom: 1px solid var(--cf-border-subtle); }
.data-table tr:hover td { background: rgba(255,255,255,.02); }
.tp-url { font-family: ui-monospace, monospace; font-size: 12px; }
.t-heat { display: flex; align-items: center; gap: 8px; }
.t-heat span { font-size: 12px; color: var(--cf-text-muted); font-variant-numeric: tabular-nums; }
.empty-row { text-align: center; color: var(--cf-text-muted); padding: 28px; }
.badge { font-size: 10px; font-weight: 700; padding: 3px 9px; border-radius: 6px; text-transform: uppercase; letter-spacing: .04em; }
.b-ai { background: rgba(99,102,241,.16); color: #a5b4fc; }
.b-human { background: rgba(59,130,246,.16); color: #60a5fa; }
.b-hot { background: rgba(239,68,68,.16); color: #f87171; }
.b-converted { background: rgba(34,197,94,.16); color: #4ade80; }
.b-engaged { background: rgba(59,130,246,.16); color: #60a5fa; }
.b-qualified { background: rgba(168,85,247,.16); color: #c084fc; }
.b-ready { background: rgba(251,146,60,.16); color: #fb923c; }
.b-lost { background: rgba(100,116,139,.2); color: var(--cf-text-muted); }
.b-new { background: rgba(100,116,139,.18); color: var(--cf-text-muted); }

@media (max-width: 1100px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } .snap-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 860px) { .section-row { grid-template-columns: 1fr; } }
@media (max-width: 560px) { .reports-page { padding: 18px 14px 32px; } .kpi-grid { grid-template-columns: 1fr 1fr; gap: 10px; } .funnel-row, .brk-row { grid-template-columns: 96px 1fr auto auto; } }
</style>
