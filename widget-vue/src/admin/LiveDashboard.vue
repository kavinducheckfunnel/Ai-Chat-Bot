<template>
  <div class="dashboard">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Live Dashboard</h1>
        <p class="page-sub">Real-time visitor heat scores and session monitoring</p>
      </div>
      <div class="header-right">
        <div class="live-dot"></div>
        <span class="live-label">Live</span>
        <button class="mute-btn" @click="toggleMute" :title="muted ? 'Unmute notifications' : 'Mute notifications'">
          <svg v-if="!muted" width="15" height="15" fill="none" viewBox="0 0 24 24"><path d="M11 5L6 9H2v6h4l5 4V5z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          <svg v-else width="15" height="15" fill="none" viewBox="0 0 24 24"><path d="M11 5L6 9H2v6h4l5 4V5z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><line x1="23" y1="9" x2="17" y2="15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="17" y1="9" x2="23" y2="15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
        <button class="refresh-btn" @click="loadData" :disabled="loading">
          <svg width="16" height="16" fill="none" viewBox="0 0 24 24" :class="{ spin: loading }"><path d="M23 4v6h-6M1 20v-6h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          Refresh
        </button>
      </div>
    </div>

    <!-- Stats Row -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon stat-blue">
          <svg width="20" height="20" fill="none" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" stroke="currentColor" stroke-width="2"/><circle cx="9" cy="7" r="4" stroke="currentColor" stroke-width="2"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" stroke="currentColor" stroke-width="2"/></svg>
        </div>
        <div>
          <p class="stat-label">Total Clients</p>
          <p class="stat-value">{{ stats.total_clients ?? '—' }}</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-green">
          <svg width="20" height="20" fill="none" viewBox="0 0 24 24"><path d="M22 12h-4l-3 9L9 3l-3 9H2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </div>
        <div>
          <p class="stat-label">Total Sessions</p>
          <p class="stat-value">{{ stats.total_sessions ?? '—' }}</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-red">
          <svg width="20" height="20" fill="none" viewBox="0 0 24 24"><path d="M12 2C6 2 2 8 2 12s4 10 10 10 10-4.5 10-10S18 2 12 2z" stroke="currentColor" stroke-width="2"/><path d="M12 8v4l3 3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </div>
        <div>
          <p class="stat-label">Hot Sessions</p>
          <p class="stat-value">{{ stats.heat_distribution?.hot ?? '—' }}</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-orange">
          <svg width="20" height="20" fill="none" viewBox="0 0 24 24"><path d="M12 2C8.5 2 5.5 4.5 5 8c-.3 2 .5 4 2 5.5L12 22l5-8.5c1.5-1.5 2.3-3.5 2-5.5-.5-3.5-3.5-6-7-6z" stroke="currentColor" stroke-width="2"/></svg>
        </div>
        <div>
          <p class="stat-label">Active Clients</p>
          <p class="stat-value">{{ stats.active_clients ?? '—' }}</p>
        </div>
      </div>
    </div>

    <!-- Analytics Row: Heat Distribution + Daily Trend -->
    <div class="analytics-row">
      <!-- Heat Distribution -->
      <div class="analytics-card">
        <h3 class="analytics-title">Heat Distribution</h3>
        <div class="heat-dist">
          <div class="heat-dist-bar">
            <div class="hd-seg hd-cold" :style="{ flex: heatTotal ? stats.heat_distribution.cold : 1 }"></div>
            <div class="hd-seg hd-warm" :style="{ flex: heatTotal ? stats.heat_distribution.warm : 1 }"></div>
            <div class="hd-seg hd-hot"  :style="{ flex: heatTotal ? stats.heat_distribution.hot  : 1 }"></div>
          </div>
          <div class="heat-dist-legend">
            <div class="hd-item">
              <span class="hd-dot hd-cold"></span>
              <span class="hd-label">Cold</span>
              <span class="hd-count">{{ stats.heat_distribution?.cold ?? 0 }}</span>
            </div>
            <div class="hd-item">
              <span class="hd-dot hd-warm"></span>
              <span class="hd-label">Warm</span>
              <span class="hd-count">{{ stats.heat_distribution?.warm ?? 0 }}</span>
            </div>
            <div class="hd-item">
              <span class="hd-dot hd-hot"></span>
              <span class="hd-label">Hot</span>
              <span class="hd-count">{{ stats.heat_distribution?.hot ?? 0 }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Daily Trend Sparkline -->
      <div class="analytics-card trend-card">
        <h3 class="analytics-title">Sessions — Last 14 Days</h3>
        <div class="sparkline-wrap">
          <svg v-if="stats.daily_trend?.length" class="sparkline" viewBox="0 0 280 60" preserveAspectRatio="none">
            <polyline
              :points="sparklinePoints"
              fill="none"
              stroke="#6366F1"
              stroke-width="2"
              stroke-linejoin="round"
              stroke-linecap="round"
            />
            <polyline
              :points="sparklineAreaPoints"
              fill="url(#sparkGrad)"
              stroke="none"
            />
            <defs>
              <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#6366F1" stop-opacity="0.2"/>
                <stop offset="100%" stop-color="#6366F1" stop-opacity="0"/>
              </linearGradient>
            </defs>
          </svg>
          <p v-else class="no-data">No data yet</p>
        </div>
        <div class="sparkline-labels">
          <span v-if="stats.daily_trend?.length">{{ stats.daily_trend[0].date }}</span>
          <span v-if="stats.daily_trend?.length">{{ stats.daily_trend[stats.daily_trend.length - 1].date }}</span>
        </div>
      </div>
    </div>

    <!-- Sessions Section -->
    <div class="section-header">
      <h2 class="section-title">Recent Sessions</h2>
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
      <svg width="48" height="48" fill="none" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="#CBD5E1" stroke-width="1.5"/></svg>
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
            {{ heatEmoji(session.heat_score) }} {{ session.heat_score }}%
          </div>
          <span class="state-badge" :class="stateClass(session.conversation_state)">
            {{ session.conversation_state.replace('_', ' ') }}
          </span>
        </div>

        <div class="heat-bar-wrap">
          <div class="heat-bar" :style="{ width: session.heat_score + '%', background: heatColor(session.heat_score) }"></div>
        </div>

        <div class="session-metrics">
          <div class="metric">
            <span class="metric-label">Intent</span>
            <div class="mini-bar-wrap">
              <div class="mini-bar intent" :style="{ width: (session.intent_ema * 100) + '%' }"></div>
            </div>
            <span class="metric-val">{{ Math.round(session.intent_ema * 100) }}%</span>
          </div>
          <div class="metric">
            <span class="metric-label">Budget</span>
            <div class="mini-bar-wrap">
              <div class="mini-bar budget" :style="{ width: (session.budget_ema * 100) + '%' }"></div>
            </div>
            <span class="metric-val">{{ Math.round(session.budget_ema * 100) }}%</span>
          </div>
          <div class="metric">
            <span class="metric-label">Urgency</span>
            <div class="mini-bar-wrap">
              <div class="mini-bar urgency" :style="{ width: (session.urgency_ema * 100) + '%' }"></div>
            </div>
            <span class="metric-val">{{ Math.round(session.urgency_ema * 100) }}%</span>
          </div>
        </div>

        <div class="session-footer">
          <span class="visitor-id">{{ session.visitor_id?.slice(0, 12) }}...</span>
          <span class="msg-count">{{ session.message_count }} msgs</span>
        </div>
      </div>
    </div>

    <!-- Session Modal -->
    <div v-if="selectedSession" class="modal-overlay" @click.self="selectedSession = null">
      <div class="modal">
        <div class="modal-header">
          <div>
            <h3>Session Detail</h3>
            <p class="modal-sub">{{ selectedSession.visitor_id }}</p>
          </div>
          <div style="display:flex;gap:8px;align-items:center">
            <button class="godview-btn" @click="openGodView(selectedSession)" title="Take over this session">
              <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/></svg>
              God View
            </button>
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
          <p v-if="!sessionDetail?.chat_history?.length" class="no-history">No chat history available.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()
const router = useRouter()
const sessions = ref([])
const stats = ref({})
const loading = ref(false)
const wsConnected = ref(false)
const activeFilter = ref('all')
const selectedSession = ref(null)
const sessionDetail = ref(null)
const loadingSession = ref(false)
const muted = ref(localStorage.getItem('cf_inbox_muted') === '1')

function toggleMute() {
  muted.value = !muted.value
  localStorage.setItem('cf_inbox_muted', muted.value ? '1' : '0')
}

function playNotificationSound() {
  if (muted.value) return
  try {
    const AudioCtx = window.AudioContext || window['webkitAudioContext']
    const ctx = new AudioCtx()
    const tones = [880, 1100]
    tones.forEach((freq, i) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.type = 'sine'
      osc.frequency.value = freq
      gain.gain.setValueAtTime(0, ctx.currentTime + i * 0.18)
      gain.gain.linearRampToValueAtTime(0.18, ctx.currentTime + i * 0.18 + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.18 + 0.35)
      osc.start(ctx.currentTime + i * 0.18)
      osc.stop(ctx.currentTime + i * 0.18 + 0.35)
    })
    setTimeout(() => ctx.close(), 1200)
  } catch {}
}

const filters = [
  { label: 'All', value: 'all' },
  { label: 'Hot (70+)', value: 'hot' },
  { label: 'Warm (40+)', value: 'warm' },
  { label: 'Cool', value: 'cool' },
]

const filteredSessions = computed(() => {
  if (activeFilter.value === 'hot') return sessions.value.filter(s => s.heat_score >= 70)
  if (activeFilter.value === 'warm') return sessions.value.filter(s => s.heat_score >= 40 && s.heat_score < 70)
  if (activeFilter.value === 'cool') return sessions.value.filter(s => s.heat_score < 40)
  return sessions.value
})

const heatTotal = computed(() => {
  const d = stats.value.heat_distribution
  if (!d) return 0
  return (d.hot || 0) + (d.warm || 0) + (d.cold || 0)
})

// Build SVG polyline points for the 14-day sparkline
const sparklinePoints = computed(() => {
  const trend = stats.value.daily_trend
  if (!trend || trend.length < 2) return ''
  const W = 280, H = 60, PAD = 4
  const counts = trend.map(d => d.count)
  const maxVal = Math.max(...counts, 1)
  return trend.map((d, i) => {
    const x = PAD + (i / (trend.length - 1)) * (W - PAD * 2)
    const y = H - PAD - (d.count / maxVal) * (H - PAD * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})

const sparklineAreaPoints = computed(() => {
  const trend = stats.value.daily_trend
  if (!trend || trend.length < 2) return ''
  const W = 280, H = 60, PAD = 4
  const counts = trend.map(d => d.count)
  const maxVal = Math.max(...counts, 1)
  const pts = trend.map((d, i) => {
    const x = PAD + (i / (trend.length - 1)) * (W - PAD * 2)
    const y = H - PAD - (d.count / maxVal) * (H - PAD * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  return `${pts[0].split(',')[0]},${H} ${pts.join(' ')} ${pts[pts.length - 1].split(',')[0]},${H}`
})

async function loadData() {
  loading.value = true
  try {
    const [statsData, clients] = await Promise.all([
      api.getStats(),
      api.getClients(),
    ])
    stats.value = statsData || {}

    const allSessions = []
    for (const client of (clients || []).slice(0, 10)) {
      try {
        const clientSessions = await api.getClientSessions(client.id)
        allSessions.push(...(clientSessions || []))
      } catch {}
    }
    sessions.value = allSessions.sort((a, b) => b.heat_score - a.heat_score)
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function handleWsMessage(msg) {
  if (msg.type === 'session_update') {
    const incoming = msg.data
    const idx = sessions.value.findIndex(s => s.session_id === incoming.session_id)
    if (idx >= 0) {
      sessions.value[idx] = { ...sessions.value[idx], ...incoming }
    } else {
      sessions.value.unshift(incoming)
      playNotificationSound()
    }
    // Keep sorted by heat
    sessions.value.sort((a, b) => b.heat_score - a.heat_score)
    // Update stats counter
    if (stats.value.total_sessions !== undefined) {
      stats.value.total_sessions = sessions.value.length
    }
  }
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

function openGodView(session) {
  router.push(`/admin/godview/${session.session_id}`)
}

function heatClass(score) {
  if (score >= 70) return 'hot'
  if (score >= 40) return 'warm'
  return 'cool'
}

function heatEmoji(score) {
  if (score >= 70) return '🔥'
  if (score >= 40) return '🟠'
  return '🔵'
}

function heatColor(score) {
  if (score >= 70) return 'linear-gradient(90deg, #EF4444, #F97316)'
  if (score >= 40) return 'linear-gradient(90deg, #F97316, #EAB308)'
  return 'linear-gradient(90deg, #3B82F6, #06B6D4)'
}

function stateClass(state) {
  const map = {
    RESEARCH: 'state-blue',
    EVALUATION: 'state-yellow',
    OBJECTION: 'state-red',
    RECOVERY: 'state-orange',
    READY_TO_BUY: 'state-green',
  }
  return map[state] || 'state-blue'
}

let ws = null
let fallbackInterval = null

function connectWs() {
  ws = api.connectAdminDashboard(handleWsMessage)
  ws.onopen = () => { wsConnected.value = true }
  ws.onclose = () => {
    wsConnected.value = false
    // Reconnect after 5s
    setTimeout(connectWs, 5000)
  }
}

onMounted(async () => {
  await loadData()
  connectWs()
  // Fallback poll every 60s if WS is down
  fallbackInterval = setInterval(() => {
    if (!wsConnected.value) loadData()
  }, 60000)
})

onUnmounted(() => {
  if (ws) ws.close()
  clearInterval(fallbackInterval)
})
</script>

<style scoped>
.dashboard { max-width: 1200px; }

.page-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  margin-bottom: 28px;
}

.page-title { font-size: 24px; font-weight: 700; color: #0F172A; letter-spacing: -0.4px; }
.page-sub { font-size: 14px; color: #64748B; margin-top: 4px; }

.header-right { display: flex; align-items: center; gap: 12px; }

.live-dot {
  width: 8px; height: 8px; border-radius: 50%; background: #22C55E;
  box-shadow: 0 0 0 3px rgba(34,197,94,0.2);
  animation: pulse 2s infinite;
}

@keyframes pulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.5 } }

.live-label { font-size: 13px; font-weight: 500; color: #22C55E; }

.mute-btn {
  background: transparent;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  color: #94A3B8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  transition: background 0.15s, color 0.15s;
}
.mute-btn:hover { background: #F1F5F9; color: #64748B; }

.refresh-btn {
  display: flex; align-items: center; gap: 6px;
  background: white; border: 1px solid #E2E8F0;
  border-radius: 8px; padding: 8px 14px;
  font-size: 13px; font-weight: 500; color: #475569;
  cursor: pointer; transition: all 0.15s; font-family: inherit;
}
.refresh-btn:hover { background: #F8FAFC; border-color: #CBD5E1; }
.refresh-btn:disabled { opacity: 0.5; }

.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Stats */
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }

.stat-card {
  background: white; border: 1px solid #F1F5F9; border-radius: 14px;
  padding: 20px; display: flex; align-items: center; gap: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.stat-icon {
  width: 44px; height: 44px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.stat-blue { background: rgba(59,130,246,0.1); color: #3B82F6; }
.stat-green { background: rgba(34,197,94,0.1); color: #22C55E; }
.stat-orange { background: rgba(249,115,22,0.1); color: #F97316; }
.stat-purple { background: rgba(139,92,246,0.1); color: #8B5CF6; }
.stat-red { background: rgba(239,68,68,0.1); color: #EF4444; }

.stat-label { font-size: 12px; color: #94A3B8; font-weight: 500; }
.stat-value { font-size: 26px; font-weight: 700; color: #0F172A; letter-spacing: -0.5px; }

/* Analytics row */
.analytics-row {
  display: grid; grid-template-columns: 1fr 2fr; gap: 16px; margin-bottom: 32px;
}

.analytics-card {
  background: white; border: 1px solid #F1F5F9; border-radius: 14px;
  padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.analytics-title { font-size: 13px; font-weight: 600; color: #64748B; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.05em; }

/* Heat distribution */
.heat-dist-bar {
  display: flex; height: 12px; border-radius: 6px; overflow: hidden; margin-bottom: 14px; gap: 2px;
}
.hd-seg { border-radius: 6px; transition: flex 0.4s; }
.hd-seg.hd-cold { background: #3B82F6; }
.hd-seg.hd-warm { background: #F97316; }
.hd-seg.hd-hot  { background: #EF4444; }

.heat-dist-legend { display: flex; gap: 20px; }
.hd-item { display: flex; align-items: center; gap: 6px; }
.hd-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.hd-dot.hd-cold { background: #3B82F6; }
.hd-dot.hd-warm { background: #F97316; }
.hd-dot.hd-hot  { background: #EF4444; }
.hd-label { font-size: 12px; color: #64748B; }
.hd-count { font-size: 13px; font-weight: 700; color: #0F172A; }

/* Sparkline */
.trend-card { display: flex; flex-direction: column; }
.sparkline-wrap { flex: 1; min-height: 60px; }
.sparkline { width: 100%; height: 60px; display: block; }
.sparkline-labels {
  display: flex; justify-content: space-between;
  font-size: 11px; color: #94A3B8; margin-top: 4px;
}
.no-data { font-size: 13px; color: #CBD5E1; text-align: center; padding: 16px; }

/* Section header */
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.section-title { font-size: 17px; font-weight: 600; color: #0F172A; }

.filter-tabs { display: flex; gap: 4px; background: #F1F5F9; border-radius: 8px; padding: 3px; }

.filter-tab {
  background: none; border: none; padding: 5px 12px;
  font-size: 13px; font-weight: 500; color: #64748B;
  cursor: pointer; border-radius: 6px; transition: all 0.15s; font-family: inherit;
}
.filter-tab.active { background: white; color: #0F172A; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }

/* Sessions Grid */
.sessions-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }

.session-card {
  background: white; border-radius: 14px; padding: 18px;
  border: 1px solid #F1F5F9; cursor: pointer;
  transition: all 0.15s; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.session-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-color: #E2E8F0; }
.session-card.hot { border-top: 3px solid #EF4444; }
.session-card.warm { border-top: 3px solid #F97316; }
.session-card.cool { border-top: 3px solid #3B82F6; }

.session-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }

.heat-badge {
  font-size: 13px; font-weight: 700; padding: 3px 8px; border-radius: 6px;
}
.heat-badge.hot { background: rgba(239,68,68,0.1); color: #DC2626; }
.heat-badge.warm { background: rgba(249,115,22,0.1); color: #EA580C; }
.heat-badge.cool { background: rgba(59,130,246,0.1); color: #2563EB; }

.state-badge {
  font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.04em;
}
.state-blue { background: #EFF6FF; color: #1D4ED8; }
.state-yellow { background: #FFFBEB; color: #B45309; }
.state-red { background: #FEF2F2; color: #B91C1C; }
.state-orange { background: #FFF7ED; color: #C2410C; }
.state-green { background: #F0FDF4; color: #15803D; }

.heat-bar-wrap {
  background: #F1F5F9; border-radius: 4px; height: 6px; margin-bottom: 16px; overflow: hidden;
}
.heat-bar { height: 100%; border-radius: 4px; transition: width 0.5s; }

.session-metrics { display: flex; flex-direction: column; gap: 8px; margin-bottom: 14px; }

.metric { display: flex; align-items: center; gap: 8px; }
.metric-label { font-size: 11px; color: #94A3B8; width: 42px; flex-shrink: 0; }
.mini-bar-wrap { flex: 1; background: #F1F5F9; border-radius: 3px; height: 5px; overflow: hidden; }
.mini-bar { height: 100%; border-radius: 3px; transition: width 0.5s; }
.intent { background: #6366F1; }
.budget { background: #22C55E; }
.urgency { background: #F97316; }
.metric-val { font-size: 11px; font-weight: 600; color: #475569; width: 28px; text-align: right; }

.session-footer { display: flex; justify-content: space-between; align-items: center; }
.visitor-id { font-size: 11px; color: #94A3B8; font-family: monospace; }
.msg-count { font-size: 11px; color: #94A3B8; }

/* Loading / Empty */
.loading-state, .empty-state {
  display: flex; flex-direction: column; align-items: center;
  gap: 12px; padding: 60px; color: #94A3B8; font-size: 14px;
}

.loader {
  width: 32px; height: 32px;
  border: 3px solid #E2E8F0;
  border-top-color: #6366F1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* Modal */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.5); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
  z-index: 100; padding: 20px;
}

.modal {
  background: white; border-radius: 16px;
  width: 100%; max-width: 600px; max-height: 80vh;
  display: flex; flex-direction: column;
  box-shadow: 0 25px 50px rgba(0,0,0,0.15);
}

.modal-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: 20px 20px 16px;
  border-bottom: 1px solid #F1F5F9;
}
.modal-header h3 { font-size: 16px; font-weight: 600; color: #0F172A; }
.modal-sub { font-size: 12px; color: #94A3B8; font-family: monospace; margin-top: 2px; }

.modal-close {
  background: none; border: none; cursor: pointer; padding: 4px;
  color: #94A3B8; border-radius: 6px; transition: all 0.15s;
}
.modal-close:hover { background: #F1F5F9; color: #475569; }

.godview-btn {
  display: flex; align-items: center; gap: 5px;
  background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.3);
  color: #6366F1; border-radius: 7px; padding: 5px 10px;
  font-size: 12px; font-weight: 600; cursor: pointer;
  transition: all 0.15s; font-family: inherit;
}
.godview-btn:hover { background: #6366F1; color: white; border-color: #6366F1; }

.modal-loading { display: flex; justify-content: center; padding: 40px; }

.chat-history { overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 12px; }

.chat-msg { max-width: 85%; }
.user-msg { align-self: flex-end; }
.ai-msg { align-self: flex-start; }

.msg-role { font-size: 11px; font-weight: 600; color: #94A3B8; margin-bottom: 4px; display: block; }
.user-msg .msg-role { text-align: right; }

.msg-text {
  font-size: 13px; line-height: 1.5; padding: 10px 14px; border-radius: 12px;
}
.user-msg .msg-text { background: #EFF6FF; color: #1E3A8A; border-bottom-right-radius: 4px; }
.ai-msg .msg-text { background: #F8FAFC; color: #334155; border: 1px solid #E2E8F0; border-bottom-left-radius: 4px; }

.no-history { color: #94A3B8; font-size: 13px; text-align: center; padding: 20px; }
</style>
