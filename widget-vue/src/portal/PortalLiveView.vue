<template>
  <div class="live-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Live View</h1>
        <p class="page-sub">Real-time sessions from your chatbot</p>
      </div>
      <div class="header-right">
        <div v-if="wsConnected" class="live-indicator">
          <div class="live-dot"></div>
          <span class="live-label">Live</span>
        </div>
        <button class="refresh-btn" @click="loadData" :disabled="loading">
          <svg width="14" height="14" fill="none" viewBox="0 0 24 24" :class="{ spin: loading }">
            <path d="M23 4v6h-6M1 20v-6h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          Refresh
        </button>
      </div>
    </div>

    <!-- Stats -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon stat-purple">
          <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="currentColor" stroke-width="2"/></svg>
        </div>
        <div>
          <p class="stat-label">Total Sessions</p>
          <p class="stat-value">{{ sessions.length }}</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-red">
          <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div>
          <p class="stat-label">Hot (75+)</p>
          <p class="stat-value stat-hot">{{ hotCount }}</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-orange">
          <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </div>
        <div>
          <p class="stat-label">Warm (40–74)</p>
          <p class="stat-value stat-warm">{{ warmCount }}</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-blue">
          <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2"/></svg>
        </div>
        <div>
          <p class="stat-label">Avg Heat</p>
          <p class="stat-value">{{ avgHeat }}%</p>
        </div>
      </div>
    </div>

    <!-- Filter tabs -->
    <div class="section-header">
      <h2 class="section-title">Sessions</h2>
      <div class="filter-tabs">
        <button v-for="f in filters" :key="f.value" class="filter-tab" :class="{ active: activeFilter === f.value }" @click="activeFilter = f.value">
          {{ f.label }}
        </button>
      </div>
    </div>

    <div v-if="loading && !sessions.length" class="loading-state">
      <div class="loader"></div>
      <p>Loading sessions...</p>
    </div>

    <div v-else-if="!filteredSessions.length" class="empty-state">
      <svg width="40" height="40" fill="none" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="rgba(255,255,255,0.15)" stroke-width="1.5"/></svg>
      <p>No sessions found</p>
    </div>

    <div v-else class="sessions-grid">
      <div
        v-for="session in filteredSessions"
        :key="session.session_id"
        class="session-card"
        :class="heatClass(session.heat_score)"
        @click="openSession(session)"
      >
        <div class="session-top">
          <div class="heat-badge" :class="heatClass(session.heat_score)">
            {{ heatEmoji(session.heat_score) }} {{ Math.round(session.heat_score || 0) }}%
          </div>
          <span class="state-badge" :class="stateClass(session.conversation_state)">
            {{ (session.conversation_state || 'NEW').replace(/_/g, ' ') }}
          </span>
        </div>

        <div class="heat-bar-wrap">
          <div class="heat-bar" :style="{ width: (session.heat_score || 0) + '%', background: heatGradient(session.heat_score) }"></div>
        </div>

        <div class="session-metrics">
          <div class="metric">
            <span class="metric-label">Intent</span>
            <div class="mini-bar-wrap">
              <div class="mini-bar intent" :style="{ width: ((session.intent_ema || 0) * 100) + '%' }"></div>
            </div>
            <span class="metric-val">{{ Math.round((session.intent_ema || 0) * 100) }}%</span>
          </div>
          <div class="metric">
            <span class="metric-label">Budget</span>
            <div class="mini-bar-wrap">
              <div class="mini-bar budget" :style="{ width: ((session.budget_ema || 0) * 100) + '%' }"></div>
            </div>
            <span class="metric-val">{{ Math.round((session.budget_ema || 0) * 100) }}%</span>
          </div>
          <div class="metric">
            <span class="metric-label">Urgency</span>
            <div class="mini-bar-wrap">
              <div class="mini-bar urgency" :style="{ width: ((session.urgency_ema || 0) * 100) + '%' }"></div>
            </div>
            <span class="metric-val">{{ Math.round((session.urgency_ema || 0) * 100) }}%</span>
          </div>
        </div>

        <div class="session-footer">
          <span class="visitor-id">{{ (session.lead_email || session.visitor_id || 'anon').slice(0, 18) }}</span>
          <span class="msg-count">{{ session.message_count || 0 }} msgs</span>
        </div>
      </div>
    </div>

    <!-- Chat history modal -->
    <div v-if="selectedSession" class="modal-overlay" @click.self="selectedSession = null">
      <div class="modal">
        <div class="modal-header">
          <div>
            <h3 class="modal-title">Chat History</h3>
            <p class="modal-sub">{{ selectedSession.lead_email || (selectedSession.visitor_id || '').slice(0, 30) || 'Anonymous' }}</p>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <span class="modal-heat" :class="heatClass(selectedSession.heat_score)">
              {{ heatEmoji(selectedSession.heat_score) }} {{ Math.round(selectedSession.heat_score || 0) }}%
            </span>
            <button class="modal-close" @click="selectedSession = null">
              <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            </button>
          </div>
        </div>

        <div v-if="loadingSession" class="modal-loading">
          <div class="loader"></div>
        </div>
        <div v-else class="chat-history">
          <div
            v-for="(msg, i) in sessionDetail?.chat_history || []"
            :key="i"
            class="chat-msg"
            :class="msg.role === 'user' ? 'user-msg' : 'ai-msg'"
          >
            <span class="msg-role">{{ msg.role === 'user' ? 'Visitor' : 'AI' }}</span>
            <p class="msg-text">{{ msg.message || msg.content }}</p>
          </div>
          <p v-if="!sessionDetail?.chat_history?.length" class="no-history">No messages yet.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const props = defineProps({ client: Object })
const api = useAdminApi()
const sessions = ref([])
const loading = ref(false)
const wsConnected = ref(false)
const activeFilter = ref('all')
const selectedSession = ref(null)
const sessionDetail = ref(null)
const loadingSession = ref(false)

const filters = [
  { label: 'All', value: 'all' },
  { label: 'Hot (75+)', value: 'hot' },
  { label: 'Warm (40+)', value: 'warm' },
  { label: 'Cool', value: 'cool' },
]

const filteredSessions = computed(() => {
  if (activeFilter.value === 'hot') return sessions.value.filter(s => (s.heat_score || 0) >= 75)
  if (activeFilter.value === 'warm') return sessions.value.filter(s => (s.heat_score || 0) >= 40 && (s.heat_score || 0) < 75)
  if (activeFilter.value === 'cool') return sessions.value.filter(s => (s.heat_score || 0) < 40)
  return sessions.value
})

const hotCount = computed(() => sessions.value.filter(s => (s.heat_score || 0) >= 75).length)
const warmCount = computed(() => sessions.value.filter(s => (s.heat_score || 0) >= 40 && (s.heat_score || 0) < 75).length)
const avgHeat = computed(() => {
  if (!sessions.value.length) return 0
  return Math.round(sessions.value.reduce((sum, s) => sum + (s.heat_score || 0), 0) / sessions.value.length)
})

async function loadData() {
  if (!props.client) return
  loading.value = true
  try {
    const data = await api.getPortalSessions(props.client.id, { limit: 100 })
    const list = Array.isArray(data) ? data : (data?.results || [])
    sessions.value = list.sort((a, b) => (b.heat_score || 0) - (a.heat_score || 0))
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function handleWsMessage(msg) {
  if (msg.type !== 'session_update') return
  const incoming = msg.data
  // Only update sessions belonging to our client
  if (incoming.client_id && props.client && incoming.client_id !== props.client.id) return
  const idx = sessions.value.findIndex(s => s.session_id === incoming.session_id)
  if (idx >= 0) {
    sessions.value[idx] = { ...sessions.value[idx], ...incoming }
  } else {
    sessions.value.unshift(incoming)
  }
  sessions.value.sort((a, b) => (b.heat_score || 0) - (a.heat_score || 0))
}

async function openSession(session) {
  selectedSession.value = session
  sessionDetail.value = null
  loadingSession.value = true
  try {
    sessionDetail.value = await api.getSession(session.session_id)
  } catch {}
  loadingSession.value = false
}

function heatClass(score) {
  if ((score || 0) >= 75) return 'hot'
  if ((score || 0) >= 40) return 'warm'
  return 'cool'
}

function heatEmoji(score) {
  if ((score || 0) >= 75) return '🔥'
  if ((score || 0) >= 40) return '🟠'
  return '🔵'
}

function heatGradient(score) {
  if ((score || 0) >= 75) return 'linear-gradient(90deg, #EF4444, #F97316)'
  if ((score || 0) >= 40) return 'linear-gradient(90deg, #F97316, #EAB308)'
  return 'linear-gradient(90deg, #6366F1, #8B5CF6)'
}

function stateClass(state) {
  const map = { RESEARCH: 'st-blue', EVALUATION: 'st-yellow', OBJECTION: 'st-red', RECOVERY: 'st-orange', READY_TO_BUY: 'st-green' }
  return map[state] || 'st-blue'
}

let ws = null
let fallbackInterval = null

function connectWs() {
  ws = api.connectAdminDashboard(handleWsMessage)
  ws.onopen = () => { wsConnected.value = true }
  ws.onclose = () => {
    wsConnected.value = false
    setTimeout(connectWs, 5000)
  }
}

onMounted(async () => {
  await loadData()
  connectWs()
  fallbackInterval = setInterval(() => { if (!wsConnected.value) loadData() }, 60000)
})

onUnmounted(() => {
  if (ws) ws.close()
  clearInterval(fallbackInterval)
})

watch(() => props.client, () => loadData())
</script>

<style scoped>
* { box-sizing: border-box; }

.live-page {
  padding: 28px 32px;
  font-family: 'Inter', -apple-system, sans-serif;
  display: flex; flex-direction: column; gap: 0;
}

.page-header {
  display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 24px;
}
.page-title { font-size: 22px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.4px; }
.page-sub { font-size: 13px; color: #475569; margin-top: 3px; }

.header-right { display: flex; align-items: center; gap: 12px; }

.live-indicator { display: flex; align-items: center; gap: 6px; }
.live-dot {
  width: 8px; height: 8px; border-radius: 50%; background: #22c55e;
  box-shadow: 0 0 0 3px rgba(34,197,94,0.2);
  animation: pulse 2s infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
.live-label { font-size: 12px; font-weight: 600; color: #22c55e; }

.refresh-btn {
  display: flex; align-items: center; gap: 6px;
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.09);
  border-radius: 8px; padding: 7px 13px;
  font-size: 13px; font-weight: 500; color: #94a3b8;
  cursor: pointer; transition: all 0.12s; font-family: inherit;
}
.refresh-btn:hover { background: rgba(255,255,255,0.09); color: #f1f5f9; }
.refresh-btn:disabled { opacity: 0.5; }
.spin { animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Stats */
.stats-row {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 28px;
}

.stat-card {
  background: #161616; border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px; padding: 16px;
  display: flex; align-items: center; gap: 12px;
}

.stat-icon {
  width: 40px; height: 40px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.stat-purple { background: rgba(99,102,241,0.12); color: #a5b4fc; }
.stat-red    { background: rgba(239,68,68,0.12); color: #f87171; }
.stat-orange { background: rgba(249,115,22,0.12); color: #fb923c; }
.stat-blue   { background: rgba(59,130,246,0.12); color: #60a5fa; }

.stat-label { font-size: 11px; color: #475569; font-weight: 500; margin-bottom: 3px; }
.stat-value { font-size: 22px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.4px; }
.stat-hot  { color: #ef4444; }
.stat-warm { color: #f97316; }

/* Section header */
.section-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 14px;
}
.section-title { font-size: 15px; font-weight: 600; color: #f1f5f9; }

.filter-tabs { display: flex; gap: 3px; background: rgba(255,255,255,0.04); border-radius: 8px; padding: 3px; }
.filter-tab {
  background: none; border: none; padding: 5px 11px;
  font-size: 12px; font-weight: 500; color: #475569;
  cursor: pointer; border-radius: 6px; transition: all 0.12s; font-family: inherit;
}
.filter-tab.active { background: rgba(255,255,255,0.08); color: #f1f5f9; }

/* Sessions grid */
.sessions-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 14px;
}

.session-card {
  background: #161616; border-radius: 13px; padding: 16px;
  border: 1px solid rgba(255,255,255,0.06); cursor: pointer;
  transition: all 0.15s;
}
.session-card:hover { transform: translateY(-2px); border-color: rgba(255,255,255,0.12); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
.session-card.hot  { border-top: 2px solid #ef4444; }
.session-card.warm { border-top: 2px solid #f97316; }
.session-card.cool { border-top: 2px solid #6366f1; }

.session-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }

.heat-badge { font-size: 12px; font-weight: 700; padding: 3px 7px; border-radius: 6px; }
.heat-badge.hot  { background: rgba(239,68,68,0.12); color: #f87171; }
.heat-badge.warm { background: rgba(249,115,22,0.12); color: #fb923c; }
.heat-badge.cool { background: rgba(99,102,241,0.12); color: #a5b4fc; }

.state-badge {
  font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 20px;
  text-transform: uppercase; letter-spacing: 0.04em;
}
.st-blue   { background: rgba(59,130,246,0.12); color: #60a5fa; }
.st-yellow { background: rgba(234,179,8,0.12); color: #fbbf24; }
.st-red    { background: rgba(239,68,68,0.12); color: #f87171; }
.st-orange { background: rgba(249,115,22,0.12); color: #fb923c; }
.st-green  { background: rgba(34,197,94,0.12); color: #4ade80; }

.heat-bar-wrap { background: rgba(255,255,255,0.05); border-radius: 3px; height: 5px; margin-bottom: 14px; overflow: hidden; }
.heat-bar { height: 100%; border-radius: 3px; transition: width 0.5s; }

.session-metrics { display: flex; flex-direction: column; gap: 7px; margin-bottom: 12px; }
.metric { display: flex; align-items: center; gap: 7px; }
.metric-label { font-size: 10px; color: #334155; width: 40px; flex-shrink: 0; }
.mini-bar-wrap { flex: 1; background: rgba(255,255,255,0.05); border-radius: 2px; height: 4px; overflow: hidden; }
.mini-bar { height: 100%; border-radius: 2px; transition: width 0.5s; }
.intent  { background: #6366f1; }
.budget  { background: #22c55e; }
.urgency { background: #f97316; }
.metric-val { font-size: 10px; font-weight: 600; color: #475569; width: 26px; text-align: right; }

.session-footer { display: flex; justify-content: space-between; align-items: center; }
.visitor-id { font-size: 11px; color: #334155; font-family: monospace; }
.msg-count { font-size: 11px; color: #334155; }

/* Loading / Empty */
.loading-state, .empty-state {
  display: flex; flex-direction: column; align-items: center;
  gap: 10px; padding: 60px; color: #334155; font-size: 13px;
}
.loader {
  width: 28px; height: 28px;
  border: 2px solid rgba(255,255,255,0.08);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

/* Modal */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.75); backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  z-index: 100; padding: 20px;
}

.modal {
  background: #161616; border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px; width: 100%; max-width: 600px; max-height: 80vh;
  display: flex; flex-direction: column;
  box-shadow: 0 25px 60px rgba(0,0,0,0.6);
}

.modal-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: 18px 20px 14px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.modal-title { font-size: 15px; font-weight: 600; color: #f1f5f9; }
.modal-sub { font-size: 11px; color: #475569; font-family: monospace; margin-top: 3px; }

.modal-heat {
  font-size: 12px; font-weight: 700; padding: 3px 8px; border-radius: 6px;
}
.modal-heat.hot  { background: rgba(239,68,68,0.12); color: #f87171; }
.modal-heat.warm { background: rgba(249,115,22,0.12); color: #fb923c; }
.modal-heat.cool { background: rgba(99,102,241,0.12); color: #a5b4fc; }

.modal-close {
  background: none; border: none; cursor: pointer; padding: 4px;
  color: #475569; border-radius: 6px; transition: all 0.12s;
}
.modal-close:hover { background: rgba(255,255,255,0.06); color: #94a3b8; }

.modal-loading { display: flex; justify-content: center; padding: 40px; }

.chat-history {
  overflow-y: auto; padding: 16px 20px;
  display: flex; flex-direction: column; gap: 10px;
}

.chat-msg { max-width: 88%; }
.user-msg { align-self: flex-end; }
.ai-msg { align-self: flex-start; }

.msg-role {
  font-size: 10px; font-weight: 600; color: #334155;
  margin-bottom: 4px; display: block; text-transform: uppercase; letter-spacing: 0.05em;
}
.user-msg .msg-role { text-align: right; }

.msg-text {
  font-size: 13px; line-height: 1.5; padding: 10px 14px; border-radius: 12px; margin: 0;
}
.user-msg .msg-text { background: rgba(99,102,241,0.15); color: #c7d2fe; border-bottom-right-radius: 4px; }
.ai-msg  .msg-text { background: #1e293b; color: #94a3b8; border: 1px solid rgba(255,255,255,0.05); border-bottom-left-radius: 4px; }

.no-history { color: #334155; font-size: 13px; text-align: center; padding: 24px; }
</style>
