<template>
  <div class="reports-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Reports</h1>
        <p class="page-sub">Performance overview for your chatbot</p>
      </div>
      <div class="period-tabs">
        <button v-for="p in periods" :key="p.val" class="period-btn" :class="{ active: period === p.val }" @click="period = p.val">
          {{ p.label }}
        </button>
      </div>
    </div>

    <!-- Stat cards -->
    <div class="stat-grid" v-if="!loading">
      <div class="stat-card">
        <div class="stat-icon chat-icon">
          <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div class="stat-value">{{ analytics.total_sessions || 0 }}</div>
        <div class="stat-label">Total chats</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon lead-icon">
          <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="9" cy="7" r="4" stroke="currentColor" stroke-width="2"/></svg>
        </div>
        <div class="stat-value">{{ analytics.leads_captured || 0 }}</div>
        <div class="stat-label">Leads captured</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon heat-icon">
          <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div class="stat-value">{{ avgHeat }}%</div>
        <div class="stat-label">Avg. heat score</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon conv-icon">
          <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><polyline points="20 12 20 22 4 22 4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><rect x="2" y="7" width="20" height="5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 22V7M12 7H7.5a2.5 2.5 0 010-5C11 2 12 7 12 7zM12 7h4.5a2.5 2.5 0 000-5C13 2 12 7 12 7z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </div>
        <div class="stat-value">{{ analytics.hot_sessions || 0 }}</div>
        <div class="stat-label">Hot leads</div>
      </div>
    </div>

    <div class="stat-grid" v-else>
      <div class="stat-card skeleton" v-for="n in 4" :key="n">
        <div class="sk-block big"></div>
        <div class="sk-block small"></div>
      </div>
    </div>

    <!-- Funnel section -->
    <div class="section-row">
      <!-- Kanban funnel -->
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
        <div v-else class="funnel-skeleton">
          <div class="sk-stage" v-for="n in 4" :key="n"></div>
        </div>
      </div>

      <!-- Conversation states -->
      <div class="card states-card">
        <h3 class="card-title">Conversation states</h3>
        <div class="states-list" v-if="!loading">
          <div class="state-row" v-for="s in conversationStates" :key="s.label">
            <span class="state-dot" :style="{ background: s.color }"></span>
            <span class="state-name">{{ s.label }}</span>
            <span class="state-val">{{ s.count }}</span>
          </div>
        </div>
        <div v-else class="states-skeleton">
          <div class="sk-state" v-for="n in 5" :key="n"></div>
        </div>
      </div>
    </div>

    <!-- Recent sessions table -->
    <div class="card recent-card">
      <h3 class="card-title">Recent activity</h3>
      <table class="activity-table" v-if="!loading && recentSessions.length">
        <thead>
          <tr>
            <th>Visitor</th>
            <th>State</th>
            <th>Heat</th>
            <th>Messages</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in recentSessions" :key="s.session_id">
            <td>{{ s.lead_email || 'Visitor #' + s.session_id.slice(0,6) }}</td>
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
      <div v-else-if="!loading" class="empty-msg">No sessions yet.</div>
      <div v-else class="table-skeleton">
        <div class="sk-row" v-for="n in 5" :key="n"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const props = defineProps({ client: Object })
const api = useAdminApi()

const loading = ref(true)
const period = ref('30d')
const analytics = ref({})
const recentSessions = ref([])

const periods = [
  { val: '7d', label: '7 days' },
  { val: '30d', label: '30 days' },
  { val: '90d', label: '90 days' },
]

const avgHeat = computed(() => Math.round(analytics.value.avg_heat_score || 0))

const funnel = computed(() => {
  const kb = analytics.value.kanban_breakdown || {}
  const newCount = kb.NEW || 0
  const engagedCount = kb.ENGAGED || 0
  const hotCount = kb.HOT_LEAD || 0
  const convertedCount = kb.CONVERTED || 0
  return [
    { key: 'new',       label: 'New',       count: newCount,       color: '#64748b' },
    { key: 'engaged',   label: 'Engaged',   count: engagedCount,   color: '#6366f1' },
    { key: 'hot',       label: 'Hot lead',  count: hotCount,       color: '#f59e0b' },
    { key: 'converted', label: 'Converted', count: convertedCount, color: '#22c55e' },
  ]
})

const conversationStates = computed(() => {
  const f = analytics.value.funnel || {}
  return [
    { label: 'Research',     count: f.RESEARCH    || 0, color: '#64748b' },
    { label: 'Evaluation',   count: f.EVALUATION  || 0, color: '#6366f1' },
    { label: 'Objection',    count: f.OBJECTION   || 0, color: '#f59e0b' },
    { label: 'Recovery',     count: f.RECOVERY    || 0, color: '#ef4444' },
    { label: 'Ready to buy', count: f.READY_TO_BUY || 0, color: '#22c55e' },
  ]
})

function stageWidth(count) {
  const max = Math.max(...funnel.value.map(s => s.count), 1)
  return Math.round((count / max) * 100)
}

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

async function load() {
  if (!props.client) return
  loading.value = true
  try {
    const [a, sessions] = await Promise.all([
      api.getPortalAnalytics(props.client.id),
      api.getPortalSessions(props.client.id, { limit: 10 }),
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
  gap: 20px;
}

.page-header { display: flex; align-items: flex-start; justify-content: space-between; }
.page-title { font-size: 22px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.4px; }
.page-sub { font-size: 13px; color: #475569; margin-top: 3px; }

.period-tabs { display: flex; gap: 4px; background: #161616; border: 1px solid rgba(255,255,255,0.07); border-radius: 9px; padding: 3px; }
.period-btn { padding: 6px 14px; background: none; border: none; border-radius: 6px; font-size: 12px; font-weight: 500; color: #475569; cursor: pointer; transition: all 0.12s; }
.period-btn:hover { color: #94a3b8; }
.period-btn.active { background: rgba(99,102,241,0.15); color: #a5b4fc; }

/* Stat cards */
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }

.stat-card {
  background: #161616;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stat-icon {
  width: 36px; height: 36px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
}

.chat-icon { background: rgba(99,102,241,0.12); color: #a5b4fc; }
.lead-icon { background: rgba(34,197,94,0.1); color: #22c55e; }
.heat-icon { background: rgba(245,158,11,0.1); color: #f59e0b; }
.conv-icon { background: rgba(239,68,68,0.1); color: #ef4444; }

.stat-value { font-size: 30px; font-weight: 700; color: #f1f5f9; letter-spacing: -1px; }
.stat-label { font-size: 12px; color: #475569; font-weight: 500; }

/* Skeleton */
.stat-card.skeleton { gap: 14px; }
.sk-block { background: #1e293b; border-radius: 4px; }
.sk-block.big { height: 36px; width: 60%; }
.sk-block.small { height: 12px; width: 45%; }

/* Section row */
.section-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

.card {
  background: #161616;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px;
  padding: 20px;
}

.card-title { font-size: 14px; font-weight: 600; color: #e2e8f0; margin-bottom: 16px; }

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

/* Recent activity */
.recent-card { }

.activity-table { width: 100%; border-collapse: collapse; }
.activity-table th { padding: 8px 12px; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: #334155; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.06); }
.activity-table td { padding: 10px 12px; font-size: 13px; color: #64748b; border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: middle; }
.activity-table tr:hover td { background: rgba(255,255,255,0.02); }
.activity-table tr:last-child td { border-bottom: none; }

.mini-badge { font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
.b-hot { background: rgba(239,68,68,0.12); color: #ef4444; }
.b-converted { background: rgba(34,197,94,0.12); color: #22c55e; }
.b-engaged { background: rgba(99,102,241,0.12); color: #a5b4fc; }
.b-new { background: rgba(71,85,105,0.2); color: #475569; }

.mini-heat { display: flex; align-items: center; gap: 7px; }
.mini-track { width: 48px; height: 3px; background: #1e293b; border-radius: 2px; overflow: hidden; }
.mini-fill { height: 100%; border-radius: 2px; }
.mini-heat span { font-size: 11px; color: #475569; font-family: monospace; }

.empty-msg { text-align: center; color: #334155; padding: 24px; font-size: 13px; }

.table-skeleton { display: flex; flex-direction: column; gap: 8px; padding: 8px 0; }
.sk-row { height: 16px; background: #1e293b; border-radius: 4px; }
</style>
