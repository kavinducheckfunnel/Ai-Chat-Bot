<template>
  <div class="reports-page">

    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Reports</h1>
        <p class="page-sub">Performance overview for your chatbot</p>
      </div>
      <div class="header-right">
        <div class="period-tabs">
          <button v-for="p in periods" :key="p.val" class="period-btn" :class="{ active: period === p.val }" @click="period = p.val">
            {{ p.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- Tab navigation -->
    <div class="tab-nav">
      <button v-for="t in tabs" :key="t.key" class="tab-btn" :class="{ active: activeTab === t.key }" @click="activeTab = t.key">
        {{ t.label }}
      </button>
    </div>

    <!-- ═══════════════════════ OVERVIEW TAB ═══════════════════════ -->
    <template v-if="activeTab === 'overview'">

      <!-- Hero metric cards -->
      <div class="metric-grid" v-if="!loading">
        <div class="metric-card" v-for="m in heroMetrics" :key="m.key">
          <div class="metric-icon" :class="m.iconClass">
            <component :is="m.icon" />
          </div>
          <div class="metric-body">
            <div class="metric-value">{{ m.value }}</div>
            <div class="metric-label">{{ m.label }}</div>
          </div>
          <div class="metric-delta" :class="deltaCls(m.delta, m.invertDelta)">
            <span>{{ formatDelta(m.delta) }}</span>
            <span class="delta-sub">vs prev period</span>
          </div>
        </div>
      </div>
      <div class="metric-grid" v-else>
        <div class="metric-card skeleton" v-for="n in 4" :key="n">
          <div class="sk-icon"></div>
          <div class="sk-body"><div class="sk-val"></div><div class="sk-lbl"></div></div>
        </div>
      </div>

      <!-- Secondary row: duration + missed -->
      <div class="secondary-row" v-if="!loading">
        <div class="secondary-card">
          <div class="sc-label">Avg chat duration</div>
          <div class="sc-value">{{ fmtDuration(val('avg_duration_seconds')) }}</div>
          <div class="sc-delta" :class="deltaCls(delta('avg_duration_seconds'))">{{ formatDelta(delta('avg_duration_seconds')) }} vs prev</div>
        </div>
        <div class="secondary-card">
          <div class="sc-label">Total chat time</div>
          <div class="sc-value">{{ fmtDuration(val('total_duration_seconds')) }}</div>
          <div class="sc-delta" :class="deltaCls(delta('total_duration_seconds'))">{{ formatDelta(delta('total_duration_seconds')) }} vs prev</div>
        </div>
        <div class="secondary-card">
          <div class="sc-label">Missed chats</div>
          <div class="sc-value">{{ val('missed_chats') }}</div>
          <div class="sc-delta" :class="deltaCls(delta('missed_chats'), true)">{{ formatDelta(delta('missed_chats')) }} vs prev</div>
        </div>
        <div class="secondary-card">
          <div class="sc-label">AI resolution rate</div>
          <div class="sc-value">{{ val('ai_resolution_rate') }}%</div>
          <div class="sc-delta" :class="deltaCls(delta('ai_resolution_rate'))">{{ formatDeltaFloat(delta('ai_resolution_rate')) }}% vs prev</div>
        </div>
      </div>
      <div class="secondary-row" v-else>
        <div class="secondary-card skeleton" v-for="n in 4" :key="n"><div class="sk-val"></div><div class="sk-lbl"></div></div>
      </div>

      <!-- Daily trend chart -->
      <div class="card chart-card" v-if="!loading && analytics.daily_trend?.length">
        <div class="card-header-row">
          <h3 class="card-title">Daily chats</h3>
          <span class="chart-total">{{ val('total_sessions') }} total</span>
        </div>
        <div class="chart-wrap">
          <svg :viewBox="`0 0 ${cW} ${cH}`" preserveAspectRatio="none" class="trend-svg">
            <!-- Grid lines -->
            <line v-for="y in gridYs" :key="y" :x1="pad" :y1="y" :x2="cW - pad" :y2="y" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
            <!-- Area fill -->
            <defs>
              <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#6366f1" stop-opacity="0.25"/>
                <stop offset="100%" stop-color="#6366f1" stop-opacity="0"/>
              </linearGradient>
            </defs>
            <polygon v-if="chartPoints.length" :points="areaPolygon" fill="url(#areaGrad)"/>
            <!-- Line -->
            <polyline v-if="chartPoints.length" :points="chartPoints" fill="none" stroke="#6366f1" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
            <!-- Dots -->
            <circle v-for="(pt, i) in chartDots" :key="i" :cx="pt.x" :cy="pt.y" r="3" fill="#6366f1"/>
          </svg>
          <!-- X axis labels -->
          <div class="chart-labels">
            <span v-for="(d, i) in chartLabelDates" :key="i" class="chart-lbl">{{ d }}</span>
          </div>
        </div>
      </div>

      <!-- Funnel + states -->
      <div class="section-row">
        <div class="card funnel-card">
          <h3 class="card-title">Lead funnel</h3>
          <div class="funnel-stages" v-if="!loading">
            <div class="funnel-stage" v-for="stage in funnel" :key="stage.key">
              <div class="stage-info">
                <span class="stage-label">{{ stage.label }}</span>
                <span class="stage-count" :style="{ color: stage.color }">{{ stage.count }}</span>
              </div>
              <div class="stage-bar-wrap">
                <div class="stage-bar" :style="{ width: stageWidth(stage.count) + '%', background: stage.color }"></div>
              </div>
            </div>
          </div>
          <div v-else class="funnel-skeleton"><div class="sk-stage" v-for="n in 4" :key="n"></div></div>
        </div>

        <div class="card states-card">
          <h3 class="card-title">Conversation states</h3>
          <div class="states-list" v-if="!loading">
            <div class="state-row" v-for="s in conversationStates" :key="s.label">
              <span class="state-dot" :style="{ background: s.color }"></span>
              <span class="state-name">{{ s.label }}</span>
              <span class="state-val">{{ s.count }}</span>
            </div>
          </div>
          <div v-else class="states-skeleton"><div class="sk-state" v-for="n in 5" :key="n"></div></div>
        </div>
      </div>

    </template>

    <!-- ═══════════════════════ CHATS TAB ═══════════════════════ -->
    <template v-if="activeTab === 'chats'">

      <!-- Chat type breakdown -->
      <div class="breakdown-grid" v-if="!loading">
        <div class="breakdown-card ai-card">
          <div class="bk-label">Automated (AI)</div>
          <div class="bk-value">{{ val('ai_handled') }}</div>
          <div class="bk-sub">
            <span class="bk-pct">{{ aiPct }}%</span> of total chats
          </div>
          <div class="bk-delta" :class="deltaCls(delta('ai_handled'))">{{ formatDelta(delta('ai_handled')) }} vs prev period</div>
        </div>
        <div class="breakdown-card manual-card">
          <div class="bk-label">Manual (God View)</div>
          <div class="bk-value">{{ val('manual_handled') }}</div>
          <div class="bk-sub">
            <span class="bk-pct">{{ manualPct }}%</span> of total chats
          </div>
          <div class="bk-delta" :class="deltaCls(delta('manual_handled'))">{{ formatDelta(delta('manual_handled')) }} vs prev period</div>
        </div>
        <div class="breakdown-card missed-card">
          <div class="bk-label">Missed</div>
          <div class="bk-value">{{ val('missed_chats') }}</div>
          <div class="bk-sub">
            <span class="bk-pct">{{ missedPct }}%</span> of total chats
          </div>
          <div class="bk-delta" :class="deltaCls(delta('missed_chats'), true)">{{ formatDelta(delta('missed_chats')) }} vs prev period</div>
        </div>
      </div>
      <div class="breakdown-grid" v-else>
        <div class="breakdown-card skeleton" v-for="n in 3" :key="n"><div class="sk-val"></div><div class="sk-lbl"></div></div>
      </div>

      <!-- AI Resolution rate bar -->
      <div class="card res-card" v-if="!loading">
        <div class="card-header-row">
          <h3 class="card-title">AI resolution rate</h3>
          <span class="res-pct-badge">{{ val('ai_resolution_rate') }}%</span>
        </div>
        <div class="res-track">
          <div class="res-fill" :style="{ width: val('ai_resolution_rate') + '%' }"></div>
        </div>
        <p class="res-sub">{{ val('ai_handled') }} of {{ val('total_sessions') }} chats handled entirely by AI without human intervention.</p>
      </div>

      <!-- Duration row -->
      <div class="section-row" v-if="!loading">
        <div class="card dur-card">
          <h3 class="card-title">Avg chat duration</h3>
          <div class="dur-value">{{ fmtDuration(val('avg_duration_seconds')) }}</div>
          <div class="dur-delta" :class="deltaCls(delta('avg_duration_seconds'))">{{ formatDelta(delta('avg_duration_seconds')) }}s vs prev period</div>
        </div>
        <div class="card dur-card">
          <h3 class="card-title">Total chat time</h3>
          <div class="dur-value">{{ fmtDuration(val('total_duration_seconds')) }}</div>
          <div class="dur-delta" :class="deltaCls(delta('total_duration_seconds'))">vs prev {{ fmtDuration(prev('total_duration_seconds')) }}</div>
        </div>
      </div>

      <!-- Placeholder: CSAT, First response, Queue -->
      <div class="card na-card" v-if="!loading">
        <h3 class="card-title">Additional metrics</h3>
        <div class="na-grid">
          <div class="na-item" v-for="m in naMetrics" :key="m.label">
            <div class="na-label">{{ m.label }}</div>
            <div class="na-value">N/A</div>
            <div class="na-hint">{{ m.hint }}</div>
          </div>
        </div>
      </div>

      <!-- Recent sessions -->
      <div class="card recent-card" v-if="!loading">
        <h3 class="card-title">Recent activity</h3>
        <table class="activity-table" v-if="recentSessions.length">
          <thead>
            <tr>
              <th>Visitor</th>
              <th>Type</th>
              <th>State</th>
              <th>Heat</th>
              <th>Messages</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in recentSessions" :key="s.session_id">
              <td>{{ s.lead_email || 'Visitor #' + String(s.session_id).slice(0, 6) }}</td>
              <td><span class="mini-badge" :class="s.taken_over_by ? 'b-manual' : 'b-ai'">{{ s.taken_over_by ? 'Manual' : 'AI' }}</span></td>
              <td><span class="mini-badge" :class="kanbanClass(s.kanban_state)">{{ s.kanban_state }}</span></td>
              <td>
                <div class="mini-heat">
                  <div class="mini-track"><div class="mini-fill" :style="{ width: (s.heat_score || 0) + '%', background: heatColor(s.heat_score) }"></div></div>
                  <span>{{ Math.round(s.heat_score || 0) }}%</span>
                </div>
              </td>
              <td>{{ s.message_count || 0 }}</td>
              <td>{{ formatDate(s.created_at) }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-msg">No sessions yet.</div>
      </div>
      <div class="card recent-card" v-else>
        <div class="table-skeleton"><div class="sk-row" v-for="n in 5" :key="n"></div></div>
      </div>

    </template>

    <!-- ═══════════════════════ ENGAGEMENT TAB ═══════════════════════ -->
    <template v-if="activeTab === 'engagement'">

      <!-- EMA signal scores -->
      <div class="card signals-card" v-if="!loading">
        <h3 class="card-title">Buyer signal averages</h3>
        <div class="signals-grid">
          <div class="signal-item" v-for="sig in signals" :key="sig.label">
            <div class="sig-label">{{ sig.label }}</div>
            <div class="sig-bar-wrap">
              <div class="sig-bar" :style="{ width: sig.value + '%', background: sig.color }"></div>
            </div>
            <div class="sig-value" :style="{ color: sig.color }">{{ sig.value }}%</div>
          </div>
        </div>
      </div>

      <!-- Heat distribution -->
      <div class="section-row" v-if="!loading">
        <div class="card heat-dist-card">
          <h3 class="card-title">Heat distribution</h3>
          <div class="heat-dist">
            <div class="heat-seg hot" :style="{ flex: heatDist.hot }">
              <span class="heat-seg-val">{{ heatDist.hot }}</span>
              <span class="heat-seg-lbl">Hot</span>
            </div>
            <div class="heat-seg warm" :style="{ flex: heatDist.warm }">
              <span class="heat-seg-val">{{ heatDist.warm }}</span>
              <span class="heat-seg-lbl">Warm</span>
            </div>
            <div class="heat-seg cold" :style="{ flex: Math.max(heatDist.cold, 0.1) }">
              <span class="heat-seg-val">{{ heatDist.cold }}</span>
              <span class="heat-seg-lbl">Cold</span>
            </div>
          </div>
          <div class="avg-heat-row">
            <span class="avg-heat-lbl">Avg heat score</span>
            <span class="avg-heat-val" :style="{ color: heatColor(analytics.avg_heat_score) }">{{ analytics.avg_heat_score }}%</span>
          </div>
        </div>

        <div class="card kanban-card">
          <h3 class="card-title">Kanban pipeline</h3>
          <div class="kanban-list">
            <div class="kanban-row" v-for="kb in kanbanBreakdown" :key="kb.key">
              <span class="kanban-dot" :style="{ background: kb.color }"></span>
              <span class="kanban-name">{{ kb.label }}</span>
              <div class="kanban-bar-wrap">
                <div class="kanban-bar" :style="{ width: kanbanWidth(kb.count) + '%', background: kb.color }"></div>
              </div>
              <span class="kanban-val">{{ kb.count }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Engagement events -->
      <div class="card events-card" v-if="!loading">
        <h3 class="card-title">Engagement events</h3>
        <div class="events-grid">
          <div class="event-item" v-for="ev in engagementEvents" :key="ev.label">
            <div class="ev-icon-wrap" :class="ev.cls">
              <component :is="ev.icon" />
            </div>
            <div class="ev-val">{{ ev.value }}</div>
            <div class="ev-label">{{ ev.label }}</div>
          </div>
        </div>
      </div>

      <!-- Leads breakdown -->
      <div class="section-row" v-if="!loading">
        <div class="card leads-card">
          <h3 class="card-title">Leads captured</h3>
          <div class="big-number">{{ val('leads_captured') }}</div>
          <div class="big-delta" :class="deltaCls(delta('leads_captured'))">{{ formatDelta(delta('leads_captured')) }} vs prev period</div>
        </div>
        <div class="card hot-card">
          <h3 class="card-title">Hot leads</h3>
          <div class="big-number" style="color:#ef4444">{{ val('hot_sessions') }}</div>
          <div class="big-delta" :class="deltaCls(delta('hot_sessions'))">{{ formatDelta(delta('hot_sessions')) }} vs prev period</div>
        </div>
      </div>

    </template>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, h } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const props = defineProps({ client: Object })
const api = useAdminApi()

const loading = ref(true)
const period = ref('30d')
const activeTab = ref('overview')
const analytics = ref({})
const recentSessions = ref([])

const periods = [
  { val: 'today', label: 'Today' },
  { val: '7d', label: '7 days' },
  { val: '30d', label: '30 days' },
  { val: '90d', label: '90 days' },
]

const tabs = [
  { key: 'overview', label: 'Overview' },
  { key: 'chats', label: 'Chats' },
  { key: 'engagement', label: 'Engagement' },
]

// ── Metric helpers ───────────────────────────────────────────────────────────
function val(key) {
  const m = analytics.value[key]
  if (m && typeof m === 'object' && 'value' in m) return m.value
  return m ?? 0
}
function delta(key) {
  const m = analytics.value[key]
  if (m && typeof m === 'object' && 'delta' in m) return m.delta
  return 0
}
function prev(key) {
  const m = analytics.value[key]
  if (m && typeof m === 'object' && 'previous' in m) return m.previous
  return 0
}

function formatDelta(d) {
  if (d === 0 || d == null) return '—'
  return d > 0 ? `+${d}` : `${d}`
}
function formatDeltaFloat(d) {
  if (d === 0 || d == null) return '—'
  return d > 0 ? `+${d.toFixed(1)}` : `${d.toFixed(1)}`
}
function deltaCls(d, invert = false) {
  if (d === 0 || d == null) return 'delta-neutral'
  const positive = d > 0
  const good = invert ? !positive : positive
  return good ? 'delta-up' : 'delta-down'
}

function fmtDuration(seconds) {
  if (!seconds) return '—'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

// ── SVG chart ────────────────────────────────────────────────────────────────
const cW = 600
const cH = 100
const pad = 12

const chartDots = computed(() => {
  const trend = analytics.value.daily_trend || []
  if (trend.length < 2) return []
  const maxCount = Math.max(...trend.map(d => d.count), 1)
  return trend.map((d, i) => ({
    x: pad + (i / (trend.length - 1)) * (cW - 2 * pad),
    y: pad + (1 - d.count / maxCount) * (cH - 2 * pad),
  }))
})

const chartPoints = computed(() =>
  chartDots.value.map(p => `${p.x},${p.y}`).join(' ')
)

const areaPolygon = computed(() => {
  const pts = chartDots.value
  if (!pts.length) return ''
  const first = pts[0]
  const last = pts[pts.length - 1]
  return [
    ...pts.map(p => `${p.x},${p.y}`),
    `${last.x},${cH - pad}`,
    `${first.x},${cH - pad}`,
  ].join(' ')
})

const gridYs = computed(() => {
  return [pad, pad + (cH - 2 * pad) / 2, cH - pad]
})

const chartLabelDates = computed(() => {
  const trend = analytics.value.daily_trend || []
  if (!trend.length) return []
  const step = Math.max(1, Math.floor(trend.length / 6))
  return trend.filter((_, i) => i % step === 0 || i === trend.length - 1).map(d => d.date)
})

// ── Funnel / states ──────────────────────────────────────────────────────────
const funnel = computed(() => {
  const kb = analytics.value.kanban_breakdown || {}
  return [
    { key: 'new',       label: 'New',       count: kb.NEW || 0,       color: '#64748b' },
    { key: 'engaged',   label: 'Engaged',   count: kb.ENGAGED || 0,   color: '#6366f1' },
    { key: 'hot',       label: 'Hot lead',  count: kb.HOT_LEAD || 0,  color: '#f59e0b' },
    { key: 'converted', label: 'Converted', count: kb.CONVERTED || 0, color: '#22c55e' },
  ]
})

function stageWidth(count) {
  const max = Math.max(...funnel.value.map(s => s.count), 1)
  return Math.round((count / max) * 100)
}

const conversationStates = computed(() => {
  const f = analytics.value.funnel || {}
  return [
    { label: 'Research',     count: f.RESEARCH     || 0, color: '#64748b' },
    { label: 'Evaluation',   count: f.EVALUATION   || 0, color: '#6366f1' },
    { label: 'Objection',    count: f.OBJECTION    || 0, color: '#f59e0b' },
    { label: 'Recovery',     count: f.RECOVERY     || 0, color: '#ef4444' },
    { label: 'Ready to buy', count: f.READY_TO_BUY || 0, color: '#22c55e' },
  ]
})

// ── Hero metrics config ───────────────────────────────────────────────────────
const IconChat = { render: () => h('svg', { width: 18, height: 18, fill: 'none', viewBox: '0 0 24 24' }, [h('path', { d: 'M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })]) }
const IconUser = { render: () => h('svg', { width: 18, height: 18, fill: 'none', viewBox: '0 0 24 24' }, [h('path', { d: 'M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round' }), h('circle', { cx: '9', cy: '7', r: '4', stroke: 'currentColor', 'stroke-width': '2' })]) }
const IconBolt = { render: () => h('svg', { width: 18, height: 18, fill: 'none', viewBox: '0 0 24 24' }, [h('path', { d: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })]) }
const IconLead = { render: () => h('svg', { width: 18, height: 18, fill: 'none', viewBox: '0 0 24 24' }, [h('polyline', { points: '22 12 18 12 15 21 9 3 6 12 2 12', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })]) }

const heroMetrics = computed(() => [
  { key: 'total_sessions',     label: 'Total chats',       value: val('total_sessions'),     delta: delta('total_sessions'),     icon: IconChat, iconClass: 'ic-indigo',  invertDelta: false },
  { key: 'unique_visitors',    label: 'Unique visitors',   value: val('unique_visitors'),    delta: delta('unique_visitors'),    icon: IconUser, iconClass: 'ic-green',   invertDelta: false },
  { key: 'ai_resolution_rate', label: 'AI resolution rate', value: val('ai_resolution_rate') + '%', delta: delta('ai_resolution_rate'), icon: IconBolt, iconClass: 'ic-amber',   invertDelta: false },
  { key: 'leads_captured',     label: 'Leads captured',    value: val('leads_captured'),     delta: delta('leads_captured'),     icon: IconLead, iconClass: 'ic-purple',  invertDelta: false },
])

// ── Chats tab ────────────────────────────────────────────────────────────────
const total = computed(() => val('total_sessions') || 1)
const aiPct = computed(() => Math.round(val('ai_handled') / total.value * 100))
const manualPct = computed(() => Math.round(val('manual_handled') / total.value * 100))
const missedPct = computed(() => Math.round(val('missed_chats') / total.value * 100))

const naMetrics = [
  { label: 'CSAT score',            hint: 'Requires customer survey integration' },
  { label: 'First response time',   hint: 'Agent timing not yet tracked' },
  { label: 'Queued customers',      hint: 'Queue system not configured' },
  { label: 'Chats per hour (AI)',   hint: 'Hourly rate breakdown coming soon' },
]

// ── Engagement tab ────────────────────────────────────────────────────────────
const signals = computed(() => [
  { label: 'Purchase intent',   value: analytics.value.avg_intent  || 0, color: '#6366f1' },
  { label: 'Budget signal',     value: analytics.value.avg_budget  || 0, color: '#22c55e' },
  { label: 'Urgency signal',    value: analytics.value.avg_urgency || 0, color: '#f59e0b' },
])

const heatDist = computed(() => analytics.value.heat_distribution || { hot: 0, warm: 0, cold: 0 })

const kanbanBreakdown = computed(() => {
  const kb = analytics.value.kanban_breakdown || {}
  const items = [
    { key: 'NEW',       label: 'New',       count: kb.NEW       || 0, color: '#64748b' },
    { key: 'ENGAGED',   label: 'Engaged',   count: kb.ENGAGED   || 0, color: '#6366f1' },
    { key: 'HOT_LEAD',  label: 'Hot lead',  count: kb.HOT_LEAD  || 0, color: '#f59e0b' },
    { key: 'CONVERTED', label: 'Converted', count: kb.CONVERTED || 0, color: '#22c55e' },
    { key: 'LOST',      label: 'Lost',      count: kb.LOST      || 0, color: '#ef4444' },
  ]
  return items
})

function kanbanWidth(count) {
  const max = Math.max(...kanbanBreakdown.value.map(k => k.count), 1)
  return Math.round((count / max) * 100)
}

const IconEye     = { render: () => h('svg', { width: 16, height: 16, fill: 'none', viewBox: '0 0 24 24' }, [h('path', { d: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z', stroke: 'currentColor', 'stroke-width': '2' }), h('circle', { cx: '12', cy: '12', r: '3', stroke: 'currentColor', 'stroke-width': '2' })]) }
const IconDoor    = { render: () => h('svg', { width: 16, height: 16, fill: 'none', viewBox: '0 0 24 24' }, [h('path', { d: 'M18 3H6a1 1 0 00-1 1v16a1 1 0 001 1h12a1 1 0 001-1V4a1 1 0 00-1-1z', stroke: 'currentColor', 'stroke-width': '2' }), h('path', { d: 'M15 12H9m0 0l3-3m-3 3l3 3', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round' })]) }
const IconTag     = { render: () => h('svg', { width: 16, height: 16, fill: 'none', viewBox: '0 0 24 24' }, [h('path', { d: 'M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }), h('line', { x1: '7', y1: '7', x2: '7.01', y2: '7', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round' })]) }

const engagementEvents = computed(() => {
  const ev = analytics.value.analytics_events || {}
  return [
    { label: 'Page views',          value: ev.page_views         || 0, icon: IconEye,  cls: 'ev-indigo' },
    { label: 'Exit intent fired',   value: ev.exit_intent_count  || 0, icon: IconDoor, cls: 'ev-red' },
    { label: 'Pricing page visits', value: ev.pricing_page_visits || 0, icon: IconTag,  cls: 'ev-amber' },
  ]
})

// ── Common helpers ────────────────────────────────────────────────────────────
function heatColor(score) {
  if (!score) return '#1e293b'
  if (score > 70) return '#ef4444'
  if (score > 40) return '#f59e0b'
  return '#6366f1'
}

function kanbanClass(state) {
  if (state === 'HOT_LEAD') return 'b-hot'
  if (state === 'CONVERTED') return 'b-converted'
  if (state === 'ENGAGED') return 'b-engaged'
  return 'b-new'
}

function formatDate(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleDateString()
}

// ── Data loading ──────────────────────────────────────────────────────────────
async function load() {
  if (!props.client) return
  loading.value = true
  try {
    const [a, sessions] = await Promise.all([
      api.getPortalAnalytics(props.client.id, period.value),
      api.getPortalSessions(props.client.id, { limit: 20 }),
    ])
    analytics.value = a || {}
    recentSessions.value = Array.isArray(sessions) ? sessions : (sessions?.results || [])
  } catch {} finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.client, load)
watch(period, load)
</script>

<style scoped>
* { box-sizing: border-box; }

.reports-page {
  padding: 28px 32px;
  font-family: 'Inter', -apple-system, sans-serif;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Header */
.page-header { display: flex; align-items: flex-start; justify-content: space-between; }
.page-title { font-size: 22px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.4px; }
.page-sub { font-size: 13px; color: #475569; margin-top: 3px; }
.header-right { display: flex; gap: 10px; align-items: center; }

.period-tabs { display: flex; gap: 4px; background: #161616; border: 1px solid rgba(255,255,255,0.07); border-radius: 9px; padding: 3px; }
.period-btn { padding: 6px 14px; background: none; border: none; border-radius: 6px; font-size: 12px; font-weight: 500; color: #475569; cursor: pointer; transition: all 0.12s; }
.period-btn:hover { color: #94a3b8; }
.period-btn.active { background: rgba(99,102,241,0.15); color: #a5b4fc; }

/* Tab nav */
.tab-nav { display: flex; gap: 0; border-bottom: 1px solid rgba(255,255,255,0.07); }
.tab-btn { padding: 10px 20px; background: none; border: none; border-bottom: 2px solid transparent; font-size: 13px; font-weight: 500; color: #475569; cursor: pointer; transition: all 0.12s; margin-bottom: -1px; }
.tab-btn:hover { color: #94a3b8; }
.tab-btn.active { color: #a5b4fc; border-bottom-color: #6366f1; }

/* Hero metric cards */
.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }

.metric-card {
  background: #161616;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px;
  padding: 18px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  position: relative;
}

.metric-icon {
  width: 38px; height: 38px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.ic-indigo { background: rgba(99,102,241,0.12); color: #a5b4fc; }
.ic-green  { background: rgba(34,197,94,0.10);  color: #22c55e; }
.ic-amber  { background: rgba(245,158,11,0.10); color: #f59e0b; }
.ic-purple { background: rgba(168,85,247,0.10); color: #c084fc; }

.metric-body { flex: 1; min-width: 0; }
.metric-value { font-size: 26px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.8px; line-height: 1; }
.metric-label { font-size: 11px; color: #475569; font-weight: 500; margin-top: 5px; }

.metric-delta { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
.metric-delta span:first-child { font-size: 13px; font-weight: 600; }
.delta-sub { font-size: 9px; color: #334155; white-space: nowrap; }

/* Delta classes */
.delta-up   span:first-child { color: #22c55e; }
.delta-down span:first-child { color: #ef4444; }
.delta-neutral span:first-child { color: #475569; }
.delta-up   .sc-delta { color: #22c55e; }
.delta-down .sc-delta { color: #ef4444; }
.delta-neutral .sc-delta { color: #475569; }
.delta-up   .bk-delta  { color: #22c55e; }
.delta-down .bk-delta  { color: #ef4444; }
.delta-neutral .bk-delta  { color: #475569; }
.delta-up   .dur-delta { color: #22c55e; }
.delta-down .dur-delta { color: #ef4444; }
.delta-neutral .dur-delta { color: #475569; }
.delta-up   .big-delta { color: #22c55e; }
.delta-down .big-delta { color: #ef4444; }
.delta-neutral .big-delta { color: #475569; }

/* Secondary metric row */
.secondary-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }

.secondary-card {
  background: #161616;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 12px;
  padding: 16px 18px;
}
.sc-label { font-size: 11px; color: #475569; font-weight: 500; margin-bottom: 6px; }
.sc-value { font-size: 22px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.5px; }
.sc-delta  { font-size: 11px; margin-top: 5px; }

/* Chart */
.card {
  background: #161616;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px;
  padding: 20px;
}
.card-title { font-size: 14px; font-weight: 600; color: #e2e8f0; margin-bottom: 16px; }
.card-header-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.card-header-row .card-title { margin-bottom: 0; }
.chart-total { font-size: 12px; color: #475569; }

.chart-wrap { display: flex; flex-direction: column; gap: 6px; }
.trend-svg { width: 100%; height: 80px; overflow: visible; }
.chart-labels { display: flex; justify-content: space-between; padding: 0 4px; }
.chart-lbl { font-size: 10px; color: #334155; }

/* Section row */
.section-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

/* Funnel */
.funnel-stages { display: flex; flex-direction: column; gap: 12px; }
.funnel-stage { display: flex; flex-direction: column; gap: 5px; }
.stage-info { display: flex; justify-content: space-between; align-items: center; }
.stage-label { font-size: 12px; color: #64748b; }
.stage-count { font-size: 14px; font-weight: 700; }
.stage-bar-wrap { height: 6px; background: #1e293b; border-radius: 3px; overflow: hidden; }
.stage-bar { height: 100%; border-radius: 3px; transition: width 0.5s; }

.funnel-skeleton { display: flex; flex-direction: column; gap: 12px; }
.sk-stage { height: 28px; background: #1e293b; border-radius: 6px; }

/* States */
.states-list { display: flex; flex-direction: column; gap: 10px; }
.state-row { display: flex; align-items: center; gap: 9px; }
.state-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.state-name { flex: 1; font-size: 13px; color: #64748b; }
.state-val { font-size: 14px; font-weight: 600; color: #e2e8f0; }
.states-skeleton { display: flex; flex-direction: column; gap: 10px; }
.sk-state { height: 20px; background: #1e293b; border-radius: 4px; }

/* Breakdown grid (Chats tab) */
.breakdown-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.breakdown-card {
  border-radius: 14px;
  padding: 20px;
  border: 1px solid rgba(255,255,255,0.07);
}
.ai-card     { background: rgba(99,102,241,0.06);  border-color: rgba(99,102,241,0.18); }
.manual-card { background: rgba(245,158,11,0.06);  border-color: rgba(245,158,11,0.18); }
.missed-card { background: rgba(239,68,68,0.06);   border-color: rgba(239,68,68,0.18); }
.bk-label { font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px; }
.bk-value { font-size: 36px; font-weight: 700; color: #f1f5f9; letter-spacing: -1.5px; line-height: 1; }
.bk-sub { font-size: 12px; color: #475569; margin-top: 6px; }
.bk-pct { font-weight: 600; color: #94a3b8; }
.bk-delta { font-size: 11px; margin-top: 10px; }

/* Resolution bar */
.res-card {}
.res-pct-badge { font-size: 20px; font-weight: 700; color: #a5b4fc; }
.res-track { height: 8px; background: #1e293b; border-radius: 4px; overflow: hidden; }
.res-fill { height: 100%; background: linear-gradient(90deg, #6366f1, #a5b4fc); border-radius: 4px; transition: width 0.6s ease; }
.res-sub { font-size: 12px; color: #475569; margin-top: 10px; line-height: 1.5; }

/* Duration */
.dur-card {}
.dur-value { font-size: 32px; font-weight: 700; color: #f1f5f9; letter-spacing: -1px; }
.dur-delta { font-size: 12px; margin-top: 8px; }

/* N/A placeholders */
.na-card {}
.na-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.na-item { background: #0f172a; border: 1px solid rgba(255,255,255,0.05); border-radius: 10px; padding: 14px; }
.na-label { font-size: 11px; color: #475569; font-weight: 500; margin-bottom: 6px; }
.na-value { font-size: 22px; font-weight: 700; color: #334155; }
.na-hint  { font-size: 10px; color: #1e293b; margin-top: 5px; line-height: 1.4; }

/* Recent sessions */
.recent-card {}
.activity-table { width: 100%; border-collapse: collapse; }
.activity-table th { padding: 8px 12px; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: #334155; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.06); }
.activity-table td { padding: 10px 12px; font-size: 13px; color: #64748b; border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: middle; }
.activity-table tr:hover td { background: rgba(255,255,255,0.02); }
.activity-table tr:last-child td { border-bottom: none; }

.mini-badge { font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
.b-hot       { background: rgba(239,68,68,0.12);  color: #ef4444; }
.b-converted { background: rgba(34,197,94,0.12);  color: #22c55e; }
.b-engaged   { background: rgba(99,102,241,0.12); color: #a5b4fc; }
.b-new       { background: rgba(71,85,105,0.2);   color: #475569; }
.b-ai        { background: rgba(99,102,241,0.12); color: #a5b4fc; }
.b-manual    { background: rgba(245,158,11,0.12); color: #f59e0b; }

.mini-heat { display: flex; align-items: center; gap: 7px; }
.mini-track { width: 48px; height: 3px; background: #1e293b; border-radius: 2px; overflow: hidden; }
.mini-fill  { height: 100%; border-radius: 2px; }
.mini-heat span { font-size: 11px; color: #475569; font-family: monospace; }

.empty-msg { text-align: center; color: #334155; padding: 24px; font-size: 13px; }
.table-skeleton { display: flex; flex-direction: column; gap: 8px; padding: 8px 0; }
.sk-row { height: 16px; background: #1e293b; border-radius: 4px; }

/* Engagement tab — signals */
.signals-card {}
.signals-grid { display: flex; flex-direction: column; gap: 14px; }
.signal-item { display: flex; align-items: center; gap: 12px; }
.sig-label { font-size: 13px; color: #64748b; width: 130px; flex-shrink: 0; }
.sig-bar-wrap { flex: 1; height: 6px; background: #1e293b; border-radius: 3px; overflow: hidden; }
.sig-bar { height: 100%; border-radius: 3px; transition: width 0.5s; }
.sig-value { font-size: 13px; font-weight: 600; width: 42px; text-align: right; }

/* Heat distribution */
.heat-dist-card {}
.heat-dist { display: flex; height: 48px; border-radius: 10px; overflow: hidden; gap: 2px; margin-bottom: 12px; }
.heat-seg { display: flex; flex-direction: column; align-items: center; justify-content: center; min-width: 28px; transition: flex 0.4s; }
.heat-seg.hot  { background: rgba(239,68,68,0.20); }
.heat-seg.warm { background: rgba(245,158,11,0.20); }
.heat-seg.cold { background: rgba(99,102,241,0.15); }
.heat-seg-val { font-size: 14px; font-weight: 700; color: #e2e8f0; }
.heat-seg-lbl { font-size: 9px; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; }
.avg-heat-row { display: flex; justify-content: space-between; align-items: center; }
.avg-heat-lbl { font-size: 12px; color: #475569; }
.avg-heat-val { font-size: 18px; font-weight: 700; }

/* Kanban */
.kanban-card {}
.kanban-list { display: flex; flex-direction: column; gap: 10px; }
.kanban-row { display: flex; align-items: center; gap: 9px; }
.kanban-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.kanban-name { font-size: 12px; color: #64748b; width: 70px; }
.kanban-bar-wrap { flex: 1; height: 5px; background: #1e293b; border-radius: 3px; overflow: hidden; }
.kanban-bar { height: 100%; border-radius: 3px; transition: width 0.5s; }
.kanban-val { font-size: 13px; font-weight: 600; color: #e2e8f0; width: 28px; text-align: right; }

/* Engagement events */
.events-card {}
.events-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.event-item { text-align: center; padding: 16px; background: #0f172a; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); }
.ev-icon-wrap { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; margin: 0 auto 10px; }
.ev-indigo { background: rgba(99,102,241,0.12); color: #a5b4fc; }
.ev-red    { background: rgba(239,68,68,0.12);  color: #ef4444; }
.ev-amber  { background: rgba(245,158,11,0.12); color: #f59e0b; }
.ev-val    { font-size: 26px; font-weight: 700; color: #f1f5f9; letter-spacing: -1px; }
.ev-label  { font-size: 11px; color: #475569; margin-top: 4px; }

/* Big number */
.leads-card, .hot-card {}
.big-number { font-size: 52px; font-weight: 700; color: #f1f5f9; letter-spacing: -2px; line-height: 1.1; }
.big-delta  { font-size: 13px; font-weight: 600; margin-top: 6px; }

/* Skeletons */
.metric-card.skeleton { gap: 14px; }
.sk-icon { width: 38px; height: 38px; background: #1e293b; border-radius: 10px; }
.sk-body { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.sk-val  { height: 26px; width: 60%; background: #1e293b; border-radius: 4px; }
.sk-lbl  { height: 12px; width: 45%; background: #1e293b; border-radius: 4px; }
.secondary-card.skeleton { display: flex; flex-direction: column; gap: 8px; }
.breakdown-card.skeleton { display: flex; flex-direction: column; gap: 10px; padding: 20px; background: #161616; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; }
</style>
