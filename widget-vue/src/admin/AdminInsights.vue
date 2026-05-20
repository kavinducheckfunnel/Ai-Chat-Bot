<template>
  <div class="ai-page">
    <div class="ai-header">
      <div>
        <h1 class="ai-title">Platform Insights</h1>
        <p class="ai-sub">Cross-tenant aggregates — sessions, leads, conversion, channel mix, top performers</p>
      </div>
      <button class="ai-refresh" :disabled="loading" @click="load">
        <svg width="14" height="14" fill="none" viewBox="0 0 24 24">
          <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Refresh
      </button>
    </div>

    <div v-if="loading" class="ai-loading">
      <div class="ai-spinner"></div>
    </div>

    <template v-else-if="stats">
      <!-- ── KPI strip ──────────────────────────────────────────────── -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <p class="kpi-label">Total Clients</p>
          <p class="kpi-value">{{ stats.total_clients }}</p>
          <p class="kpi-sub">{{ stats.active_clients }} active</p>
        </div>
        <div class="kpi-card">
          <p class="kpi-label">Total Sessions</p>
          <p class="kpi-value">{{ formatNum(stats.total_sessions) }}</p>
          <p class="kpi-sub">{{ stats.total_messages }} messages</p>
        </div>
        <div class="kpi-card">
          <p class="kpi-label">Hot Leads</p>
          <p class="kpi-value hot">{{ stats.heat_distribution?.hot ?? 0 }}</p>
          <p class="kpi-sub">heat ≥ 70%</p>
        </div>
        <div class="kpi-card">
          <p class="kpi-label">Leads Captured</p>
          <p class="kpi-value lead">{{ stats.leads_captured }}</p>
          <p class="kpi-sub">{{ captureRate }}% capture rate</p>
        </div>
        <div class="kpi-card">
          <p class="kpi-label">Avg Msgs / Session</p>
          <p class="kpi-value">{{ stats.avg_messages_per_session }}</p>
          <p class="kpi-sub">engagement depth</p>
        </div>
      </div>

      <!-- ── Daily trend + heat distribution ───────────────────────── -->
      <div class="two-col">
        <div class="card wide">
          <h3 class="card-title">Sessions — Last 14 Days</h3>
          <div class="spark-wrap">
            <svg v-if="hasTrend" class="spark" viewBox="0 0 400 90" preserveAspectRatio="none">
              <defs>
                <linearGradient id="aiSparkGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#6366F1" stop-opacity="0.3"/>
                  <stop offset="100%" stop-color="#6366F1" stop-opacity="0"/>
                </linearGradient>
              </defs>
              <polyline :points="sparkAreaPoints" fill="url(#aiSparkGrad)" stroke="none"/>
              <polyline :points="sparkLinePoints" fill="none" stroke="#6366F1" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
            </svg>
            <p v-else class="no-data">No sessions yet in the last 14 days.</p>
          </div>
          <div v-if="hasTrend" class="spark-labels">
            <span>{{ stats.daily_trend[0].date }}</span>
            <span>{{ stats.daily_trend[stats.daily_trend.length - 1].date }}</span>
          </div>
        </div>

        <div class="card">
          <h3 class="card-title">Heat Distribution</h3>
          <div class="heat-bar">
            <div class="hd-hot"  :style="{ flex: stats.heat_distribution.hot  || 0.001 }"></div>
            <div class="hd-warm" :style="{ flex: stats.heat_distribution.warm || 0.001 }"></div>
            <div class="hd-cold" :style="{ flex: stats.heat_distribution.cold || 0.001 }"></div>
          </div>
          <div class="heat-legend">
            <div class="hl-item"><span class="dot hot"></span>Hot<strong>{{ stats.heat_distribution.hot }}</strong></div>
            <div class="hl-item"><span class="dot warm"></span>Warm<strong>{{ stats.heat_distribution.warm }}</strong></div>
            <div class="hl-item"><span class="dot cold"></span>Cold<strong>{{ stats.heat_distribution.cold }}</strong></div>
          </div>
        </div>
      </div>

      <!-- ── Kanban funnel + Channel breakdown ─────────────────────── -->
      <div class="two-col">
        <div class="card">
          <h3 class="card-title">Pipeline (Kanban)</h3>
          <div class="bar-list">
            <div v-for="col in kanbanCols" :key="col.key" class="bar-row">
              <span class="bar-label">{{ col.label }}</span>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: kanbanWidth(col.key) + '%', background: col.color }"></div>
              </div>
              <span class="bar-count">{{ stats.kanban_breakdown?.[col.key] || 0 }}</span>
            </div>
          </div>
        </div>

        <div class="card">
          <h3 class="card-title">Channel Mix</h3>
          <div class="bar-list">
            <div v-for="ch in channels" :key="ch.key" class="bar-row">
              <span class="bar-label">{{ ch.label }}</span>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: channelWidth(ch.key) + '%', background: ch.color }"></div>
              </div>
              <span class="bar-count">{{ stats.channel_breakdown?.[ch.key] || 0 }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Top clients table ─────────────────────────────────────── -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Top Clients — Last 30 Days</h3>
          <span class="card-sub">{{ stats.top_clients?.length ?? 0 }} client{{ (stats.top_clients?.length ?? 0) === 1 ? '' : 's' }} with activity</span>
        </div>
        <div v-if="!stats.top_clients?.length" class="empty-msg">
          No client activity in the last 30 days.
        </div>
        <table v-else class="top-table">
          <thead>
            <tr>
              <th>Client</th>
              <th>Sessions</th>
              <th>Hot</th>
              <th>Leads</th>
              <th>Capture %</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in stats.top_clients" :key="c.client_id">
              <td class="client-cell">{{ c.client_name }}</td>
              <td>{{ c.sessions }}</td>
              <td><span class="hot-badge">{{ c.hot }}</span></td>
              <td>{{ c.leads }}</td>
              <td class="rate-cell">{{ c.sessions ? Math.round(c.leads / c.sessions * 100) : 0 }}%</td>
              <td>
                <button v-if="c.client_id" class="view-btn" @click="$router.push(`/admin/clients/${c.client_id}/insights`)">
                  Insights →
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()
const stats = ref(null)
const loading = ref(true)

const kanbanCols = [
  { key: 'NEW',       label: 'New',       color: '#94A3B8' },
  { key: 'CONTACTED', label: 'Contacted', color: '#3B82F6' },
  { key: 'QUALIFIED', label: 'Qualified', color: '#F97316' },
  { key: 'CONVERTED', label: 'Converted', color: '#22C55E' },
  { key: 'LOST',      label: 'Lost',      color: '#EF4444' },
]

const channels = [
  { key: 'website',   label: 'Website',   color: '#6366F1' },
  { key: 'whatsapp',  label: 'WhatsApp',  color: '#25D366' },
  { key: 'messenger', label: 'Messenger', color: '#0084FF' },
  { key: 'telegram',  label: 'Telegram',  color: '#0088CC' },
]

const captureRate = computed(() => {
  if (!stats.value?.total_sessions) return 0
  return Math.round(stats.value.leads_captured / stats.value.total_sessions * 100)
})

const hasTrend = computed(() => (stats.value?.daily_trend?.length || 0) >= 2)

const sparkPointsArr = computed(() => {
  const t = stats.value?.daily_trend
  if (!t || t.length < 2) return []
  const W = 400, H = 90, PAD = 4
  const maxVal = Math.max(...t.map(d => d.count), 1)
  return t.map((d, i) => {
    const x = PAD + (i / (t.length - 1)) * (W - PAD * 2)
    const y = H - PAD - (d.count / maxVal) * (H - PAD * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
})

const sparkLinePoints = computed(() => sparkPointsArr.value.join(' '))

const sparkAreaPoints = computed(() => {
  const pts = sparkPointsArr.value
  if (!pts.length) return ''
  const first = pts[0].split(',')[0]
  const last = pts[pts.length - 1].split(',')[0]
  return `${first},90 ${pts.join(' ')} ${last},90`
})

function kanbanWidth(key) {
  const breakdown = stats.value?.kanban_breakdown
  if (!breakdown) return 0
  const max = Math.max(...Object.values(breakdown), 1)
  return Math.round((breakdown[key] || 0) / max * 100)
}

function channelWidth(key) {
  const breakdown = stats.value?.channel_breakdown
  if (!breakdown) return 0
  const max = Math.max(...Object.values(breakdown), 1)
  return Math.round((breakdown[key] || 0) / max * 100)
}

function formatNum(n) {
  if (n == null) return 0
  if (n >= 1000) return (n / 1000).toFixed(1).replace('.0', '') + 'k'
  return n
}

async function load() {
  loading.value = true
  try {
    stats.value = await api.getStats()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.ai-page { padding: 24px 32px; max-width: 1200px; }

.ai-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  margin-bottom: 24px; gap: 16px; flex-wrap: wrap;
}
.ai-title { font-size: 22px; font-weight: 700; color: var(--cf-text-primary); letter-spacing: -0.4px; }
.ai-sub { font-size: 13px; color: var(--cf-text-muted); margin-top: 4px; }

.ai-refresh {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--cf-bg-surface); border: 1px solid var(--cf-border-default);
  color: var(--cf-text-secondary); border-radius: 8px;
  padding: 7px 12px; font-size: 13px; font-weight: 500;
  cursor: pointer; font-family: inherit; transition: all 0.15s;
}
.ai-refresh:hover:not(:disabled) { background: var(--cf-bg-ghost-hover); color: var(--cf-text-primary); }
.ai-refresh:disabled { opacity: 0.5; cursor: not-allowed; }

.ai-loading { display: flex; justify-content: center; padding: 80px; }
.ai-spinner {
  width: 32px; height: 32px;
  border: 3px solid var(--cf-border-default); border-top-color: #6366F1;
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* KPI strip */
.kpi-grid {
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px;
  margin-bottom: 20px;
}
.kpi-card {
  background: var(--cf-bg-surface); border: 1px solid var(--cf-border-subtle);
  border-radius: 12px; padding: 16px 18px;
}
.kpi-label { font-size: 11px; font-weight: 600; color: var(--cf-text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.kpi-value { font-size: 26px; font-weight: 700; color: var(--cf-text-primary); letter-spacing: -0.5px; margin-top: 4px; }
.kpi-value.hot  { color: #EF4444; }
.kpi-value.lead { color: #6366F1; }
.kpi-sub { font-size: 11px; color: var(--cf-text-secondary); margin-top: 4px; }

/* Two-column rows */
.two-col { display: grid; grid-template-columns: 2fr 1fr; gap: 14px; margin-bottom: 14px; }

.card {
  background: var(--cf-bg-surface); border: 1px solid var(--cf-border-subtle);
  border-radius: 14px; padding: 20px; margin-bottom: 14px;
}
.card.wide { grid-column: 1 / span 1; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.card-title { font-size: 12px; font-weight: 700; color: var(--cf-text-muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 14px; }
.card-header .card-title { margin-bottom: 0; }
.card-sub { font-size: 11px; color: var(--cf-text-secondary); }

/* Sparkline */
.spark-wrap { min-height: 90px; }
.spark { width: 100%; height: 90px; display: block; }
.spark-labels { display: flex; justify-content: space-between; font-size: 11px; color: var(--cf-text-secondary); margin-top: 6px; }
.no-data { font-size: 13px; color: var(--cf-text-muted); text-align: center; padding: 30px; }

/* Heat distribution */
.heat-bar { display: flex; height: 12px; border-radius: 6px; overflow: hidden; gap: 2px; margin-bottom: 14px; }
.hd-hot  { background: #EF4444; border-radius: 6px; transition: flex 0.4s; }
.hd-warm { background: #F97316; border-radius: 6px; transition: flex 0.4s; }
.hd-cold { background: #3B82F6; border-radius: 6px; transition: flex 0.4s; }
.heat-legend { display: flex; flex-direction: column; gap: 8px; }
.hl-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--cf-text-muted); }
.hl-item strong { color: var(--cf-text-primary); margin-left: auto; }
.dot { width: 9px; height: 9px; border-radius: 50%; }
.dot.hot  { background: #EF4444; }
.dot.warm { background: #F97316; }
.dot.cold { background: #3B82F6; }

/* Bar lists (kanban + channel) */
.bar-list { display: flex; flex-direction: column; gap: 11px; }
.bar-row { display: flex; align-items: center; gap: 10px; }
.bar-label { font-size: 12px; color: var(--cf-text-secondary); width: 78px; flex-shrink: 0; }
.bar-track { flex: 1; background: var(--cf-bg-surface-hover); border-radius: 4px; height: 8px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 4px; transition: width 0.6s; min-width: 2px; }
.bar-count { font-size: 12px; font-weight: 600; color: var(--cf-text-primary); width: 36px; text-align: right; }

/* Top clients table */
.top-table { width: 100%; border-collapse: collapse; }
.top-table th {
  padding: 9px 12px; text-align: left;
  font-size: 11px; font-weight: 600; color: var(--cf-text-muted);
  text-transform: uppercase; letter-spacing: 0.05em;
  border-bottom: 1px solid var(--cf-border-subtle);
}
.top-table td {
  padding: 12px 12px; font-size: 13px; color: var(--cf-text-primary);
  border-bottom: 1px solid var(--cf-border-subtle);
}
.top-table tbody tr:last-child td { border-bottom: none; }
.top-table tbody tr:hover { background: var(--cf-bg-surface-hover); }
.client-cell { font-weight: 600; }
.hot-badge { background: rgba(239,68,68,0.12); color: #EF4444; padding: 2px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; }
.rate-cell { color: var(--cf-text-secondary); font-weight: 600; }
.view-btn {
  background: transparent; border: 1px solid var(--cf-border-default);
  color: var(--cf-text-secondary); padding: 4px 10px; border-radius: 6px;
  font-size: 12px; font-weight: 500; cursor: pointer; font-family: inherit;
  transition: all 0.15s;
}
.view-btn:hover { background: var(--cf-bg-ghost-hover); color: var(--cf-text-primary); border-color: var(--cf-border-strong); }

.empty-msg { padding: 30px; text-align: center; color: var(--cf-text-muted); font-size: 13px; }

@media (max-width: 1024px) {
  .kpi-grid { grid-template-columns: repeat(3, 1fr); }
  .two-col  { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .ai-page { padding: 16px; }
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .top-table { font-size: 12px; }
}
</style>
