<template>
  <div class="inbox-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Inbox</h1>
        <p class="page-sub">Real-time conversations from your website</p>
      </div>
      <div class="header-actions">
        <button class="mute-btn" @click="toggleMute" :title="muted ? 'Unmute notifications' : 'Mute notifications'">
          <svg v-if="!muted" width="16" height="16" fill="none" viewBox="0 0 24 24">
            <path d="M11 5L6 9H2v6h4l5 4V5z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <svg v-else width="16" height="16" fill="none" viewBox="0 0 24 24">
            <path d="M11 5L6 9H2v6h4l5 4V5z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <line x1="23" y1="9" x2="17" y2="15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="17" y1="9" x2="23" y2="15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>
        <div class="live-indicator">
          <span class="live-dot"></span>
          Live
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'all' }" @click="activeTab = 'all'">
        All chats
        <span class="tab-badge" v-if="sessions.length">{{ sessions.length }}</span>
      </button>
      <button class="tab" :class="{ active: activeTab === 'ai' }" @click="activeTab = 'ai'">AI handled</button>
      <button class="tab" :class="{ active: activeTab === 'hot' }" @click="activeTab = 'hot'">
        Hot leads
        <span class="tab-badge hot" v-if="hotCount">{{ hotCount }}</span>
      </button>
    </div>

    <div class="inbox-layout">
      <!-- ── Session list ─────────────────────────────────────────────── -->
      <div class="session-list">
        <div v-if="loading" class="loading-state">
          <div class="skeleton-session" v-for="n in 4" :key="n">
            <div class="sk-avatar"></div>
            <div class="sk-lines"><div class="sk-line"></div><div class="sk-line short"></div></div>
          </div>
        </div>

        <div v-else-if="filteredSessions.length === 0" class="empty-state">
          <svg width="40" height="40" fill="none" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="#334155" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <p>No chats yet</p>
          <span>Sessions will appear here once visitors start chatting.</span>
        </div>

        <button
          v-else
          v-for="s in filteredSessions"
          :key="s.session_id"
          class="session-row"
          :class="{ active: selectedId === s.session_id }"
          @click="select(s)"
        >
          <div class="session-avatar" :style="{ background: heatColor(s.heat_score) }">
            {{ initials(s) }}
          </div>
          <div class="session-meta">
            <div class="session-top-row">
              <span class="session-name">{{ s.lead_email || 'Visitor #' + s.session_id.slice(0,6) }}</span>
              <span class="session-time">{{ timeAgo(s.updated_at) }}</span>
            </div>
            <div class="session-preview">{{ lastMessage(s) }}</div>
            <div class="session-tags">
              <span class="tag" :class="kanbanClass(s.kanban_state)">{{ s.kanban_state }}</span>
              <span class="channel-badge" :class="'ch-' + (s.channel || 'website')">{{ channelLabel(s.channel) }}</span>
              <span class="heat-bar" :style="{ background: heatColor(s.heat_score), width: (s.heat_score / 100 * 60 + 20) + 'px' }"></span>
            </div>
          </div>
        </button>
      </div>

      <!-- ── Chat panel ──────────────────────────────────────────────── -->
      <div class="chat-panel" v-if="selected">
        <div class="chat-panel-header">
          <div class="chat-user-info">
            <div class="chat-avatar" :style="{ background: heatColor(selected.heat_score) }">{{ initials(selected) }}</div>
            <div>
              <p class="chat-name">{{ selected.lead_email || 'Visitor #' + selected.session_id.slice(0,6) }}</p>
              <p class="chat-sub">{{ selected.conversation_state }} · Heat {{ Math.round(selected.heat_score || 0) }}%</p>
            </div>
          </div>
          <span class="kanban-badge" :class="kanbanClass(selected.kanban_state)">{{ selected.kanban_state }}</span>
        </div>

        <div class="messages" ref="messagesEl">
          <div
            v-for="(msg, i) in chatHistory"
            :key="i"
            class="message"
            :class="msg.role === 'user' ? 'user-msg' : 'ai-msg'"
          >
            <div class="bubble">{{ msg.message || msg.content }}</div>
          </div>
        </div>
      </div>

      <div class="chat-panel empty-panel" v-else>
        <svg width="32" height="32" fill="none" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="#1e293b" stroke-width="1.5" stroke-linecap="round"/></svg>
        <p>Select a conversation</p>
      </div>

      <!-- ── Visitor details panel ───────────────────────────────────── -->
      <div class="visitor-panel" v-if="selected">

        <!-- Customer -->
        <div class="vp-section customer-section">
          <div class="vp-customer-header">
            <div class="vp-avatar" :style="{ background: heatColor(selected.heat_score) }">
              {{ initials(selected) }}
            </div>
            <div class="vp-customer-info">
              <p class="vp-customer-name">{{ selected.lead_email ? selected.lead_email.split('@')[0] : 'Visitor' }}</p>
              <span class="status-chip">
                <span class="status-dot-green"></span>
                Chatting
              </span>
            </div>
          </div>

          <!-- Quick stats -->
          <div class="vp-stats-row">
            <div class="vp-stat">
              <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              {{ selected.message_count || 0 }}
            </div>
            <div class="vp-stat">
              <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><path d="M9 12h6M9 16h6M17 21H7a2 2 0 01-2-2V5a2 2 0 012-2h5l5 5v11a2 2 0 01-2 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
              0
            </div>
            <div class="first-visit-badge">First visit</div>
          </div>
        </div>

        <!-- Chat info -->
        <div class="vp-section">
          <div class="vp-section-title">Chat info</div>
          <div class="vp-rows">
            <div class="vp-row">
              <span class="vp-label">Assignee</span>
              <span class="vp-value">
                <span class="assignee-dot">A</span> You
              </span>
            </div>
            <div class="vp-row">
              <span class="vp-label">Chat ID</span>
              <span class="vp-value mono">{{ selected.session_id.slice(0,10).toUpperCase() }}</span>
            </div>
            <div class="vp-row">
              <span class="vp-label">Duration</span>
              <span class="vp-value">{{ chatDuration }}</span>
            </div>
          </div>
        </div>

        <!-- Visitor info -->
        <div class="vp-section">
          <div class="vp-section-title">Visitor info</div>
          <div class="vp-rows">
            <div class="vp-row" v-if="selected.lead_email">
              <span class="vp-label">
                <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" stroke="currentColor" stroke-width="2"/><polyline points="22,6 12,13 2,6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
              </span>
              <span class="vp-value truncate">{{ selected.lead_email }}</span>
            </div>
            <div class="vp-row" v-if="selected.visitor_city || selected.visitor_country">
              <span class="vp-label">
                <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="10" r="3" stroke="currentColor" stroke-width="2"/></svg>
              </span>
              <span class="vp-value">
                {{ [selected.visitor_city, selected.visitor_country].filter(Boolean).join(', ') }}
                {{ countryFlag(selected.visitor_country_code) }}
              </span>
            </div>
            <div class="vp-row" v-if="selected.visitor_timezone">
              <span class="vp-label">
                <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><polyline points="12 6 12 12 16 14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
              </span>
              <span class="vp-value">{{ visitorLocalTime }}</span>
            </div>
          </div>
        </div>

        <!-- Chat tags -->
        <div class="vp-section" v-if="selected.kanban_state">
          <div class="vp-section-title">Chat tags</div>
          <div class="vp-tags-row">
            <span class="vp-tag" :class="kanbanClass(selected.kanban_state)">{{ selected.kanban_state.replace('_', ' ').toLowerCase() }}</span>
            <span class="vp-tag vp-tag-state">{{ selected.conversation_state.replace('_', ' ').toLowerCase() }}</span>
          </div>
        </div>

        <!-- Visited pages -->
        <div class="vp-section" v-if="selected.page_visits && selected.page_visits.length">
          <div class="vp-section-title">Visited pages <span class="vp-count">{{ selected.page_visits.length }}</span></div>
          <div class="vp-pages">
            <div class="vp-page-row" v-for="(pv, i) in selected.page_visits.slice().reverse()" :key="i">
              <span class="page-dot" :class="i === 0 ? 'page-dot-active' : ''"></span>
              <div class="page-info">
                <span class="page-title-text">{{ pv.title || pv.url }}</span>
                <span class="page-duration">{{ formatDuration(pv.duration_seconds) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Visit info -->
        <div class="vp-section">
          <div class="vp-section-title">Visit info</div>
          <div class="vp-rows">
            <div class="vp-row" v-if="selected.visitor_device">
              <span class="vp-label">Device</span>
              <span class="vp-value device-row">
                <span class="device-icon">
                  <!-- Desktop -->
                  <svg v-if="selected.visitor_device === 'desktop'" width="14" height="14" fill="none" viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2" stroke="currentColor" stroke-width="2"/><path d="M8 21h8M12 17v4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                  <!-- Mobile -->
                  <svg v-else-if="selected.visitor_device === 'mobile'" width="14" height="14" fill="none" viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="17" r="1" fill="currentColor"/></svg>
                  <!-- Tablet -->
                  <svg v-else width="14" height="14" fill="none" viewBox="0 0 24 24"><rect x="4" y="2" width="16" height="20" rx="2" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="17" r="1" fill="currentColor"/></svg>
                </span>
                <span>{{ selected.visitor_device }}</span>
                <span v-if="selected.visitor_os" class="os-badge">{{ selected.visitor_os }}</span>
              </span>
            </div>
            <div class="vp-row" v-if="selected.visitor_browser">
              <span class="vp-label">Browser</span>
              <span class="vp-value">{{ selected.visitor_browser }}</span>
            </div>
            <div class="vp-row" v-if="selected.visitor_referrer">
              <span class="vp-label">Referrer</span>
              <span class="vp-value truncate">{{ referrerHost(selected.visitor_referrer) }}</span>
            </div>
            <div class="vp-row" v-if="selected.visitor_ip">
              <span class="vp-label">IP</span>
              <span class="vp-value mono">{{ selected.visitor_ip }}</span>
            </div>
          </div>
        </div>

        <!-- Empty state for new sessions with no data yet -->
        <div class="vp-no-data" v-if="!selected.visitor_country && !selected.visitor_ip && !selected.page_visits?.length">
          <svg width="24" height="24" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="#334155" stroke-width="1.5"/><path d="M12 8v4M12 16h.01" stroke="#334155" stroke-width="2" stroke-linecap="round"/></svg>
          <p>Visitor data will appear<br>after the next chat message.</p>
        </div>

      </div>

      <!-- No session selected -->
      <div class="visitor-panel visitor-panel-empty" v-else>
        <svg width="28" height="28" fill="none" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2M12 11a4 4 0 100-8 4 4 0 000 8z" stroke="#1e293b" stroke-width="1.5" stroke-linecap="round"/></svg>
        <p>Visitor details</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const props = defineProps({ client: Object })
const api = useAdminApi()

const sessions = ref([])
const loading = ref(true)
const activeTab = ref('all')
const selectedId = ref(null)
const messagesEl = ref(null)
let ws = null

// ── Duration timer ────────────────────────────────────────────────────────────
const chatDuration = ref('0m 0s')
const visitorLocalTime = ref('')
let durationTimer = null

function updateDuration() {
  const s = selected.value
  if (!s?.created_at) { chatDuration.value = '—'; return }

  const created = new Date(s.created_at).getTime()
  const lastActivity = new Date(s.updated_at || s.created_at).getTime()
  const idleMs = Date.now() - lastActivity
  const IDLE_LIMIT = 10 * 60 * 1000  // 10 minutes

  // If session has been idle for >10 min, freeze at updated_at - created_at
  const endTime = idleMs > IDLE_LIMIT ? lastActivity : Date.now()
  const elapsed = Math.floor((endTime - created) / 1000)

  const m = Math.floor(elapsed / 60)
  const sec = elapsed % 60
  chatDuration.value = `${m}m ${sec}s`
}

function updateVisitorClock() {
  const tz = selected.value?.visitor_timezone
  if (!tz) { visitorLocalTime.value = ''; return }
  try {
    const now = new Date()
    const fmt = new Intl.DateTimeFormat('en-US', {
      timeZone: tz,
      hour: 'numeric',
      minute: '2-digit',
      weekday: 'short',
    })
    visitorLocalTime.value = fmt.format(now)
  } catch { visitorLocalTime.value = '' }
}

function startTimers() {
  clearInterval(durationTimer)
  updateDuration()
  updateVisitorClock()
  durationTimer = setInterval(() => {
    updateDuration()
    updateVisitorClock()
  }, 1000)
}

// ── Notification sound ────────────────────────────────────────────────────────
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

const selected = computed(() => sessions.value.find(s => s.session_id === selectedId.value) || null)

const chatHistory = computed(() => {
  if (!selected.value?.chat_history) return []
  return selected.value.chat_history.slice(-40)
})

const hotCount = computed(() => sessions.value.filter(s => s.kanban_state === 'HOT_LEAD').length)

const filteredSessions = computed(() => {
  if (activeTab.value === 'ai') return sessions.value.filter(s => !s.takeover_active)
  if (activeTab.value === 'hot') return sessions.value.filter(s => s.kanban_state === 'HOT_LEAD' || s.heat_score > 65)
  return sessions.value
})

async function loadSessions() {
  if (!props.client) return
  loading.value = true
  try {
    const data = await api.getPortalSessions(props.client.id, { limit: 50 })
    sessions.value = Array.isArray(data) ? data : (data?.results || [])
  } catch {} finally {
    loading.value = false
  }
}

function select(s) {
  selectedId.value = s.session_id
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  })
}

function timeAgo(ts) {
  if (!ts) return ''
  const diff = Date.now() - new Date(ts).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m`
  return `${Math.floor(m / 60)}h`
}

function lastMessage(s) {
  const h = s.chat_history
  if (!h || !h.length) return 'No messages yet'
  const last = h[h.length - 1]
  const text = last?.message || last?.content || ''
  return text.slice(0, 60) + (text.length > 60 ? '…' : '')
}

function initials(s) {
  if (s.lead_email) return s.lead_email[0].toUpperCase()
  return '#'
}

function heatColor(score) {
  if (!score) return '#1e293b'
  if (score > 70) return '#ef4444'
  if (score > 40) return '#f59e0b'
  return '#6366f1'
}

function kanbanClass(state) {
  if (state === 'HOT_LEAD') return 'tag-hot'
  if (state === 'CONVERTED') return 'tag-converted'
  if (state === 'ENGAGED') return 'tag-engaged'
  return 'tag-new'
}

function channelLabel(channel) {
  if (channel === 'whatsapp') return 'WhatsApp'
  if (channel === 'messenger') return 'Messenger'
  return 'Web'
}

function countryFlag(code) {
  if (!code || code.length !== 2) return ''
  return [...code.toUpperCase()].map(c => String.fromCodePoint(c.codePointAt(0) + 127397)).join('')
}

function referrerHost(url) {
  if (!url) return ''
  try { return new URL(url).hostname.replace('www.', '') } catch { return url }
}

function formatDuration(seconds) {
  if (!seconds) return '< 1s'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m === 0) return `${s}s`
  return `${m}m ${s}s`
}

onMounted(async () => {
  await loadSessions()
  ws = api.connectAdminDashboard((msg) => {
    if (msg.type === 'session_update') {
      const prevCount = sessions.value.length
      loadSessions().then(() => {
        if (sessions.value.length > prevCount) playNotificationSound()
      })
    }
  })
  startTimers()
})

onUnmounted(() => {
  if (ws) ws.close()
  clearInterval(durationTimer)
})

watch(() => props.client, loadSessions)

watch(selected, (s) => {
  if (s) startTimers()
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  })
})
</script>

<style scoped>
* { box-sizing: border-box; }

.inbox-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 28px 32px 0;
  font-family: 'Inter', -apple-system, sans-serif;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-title { font-size: 22px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.4px; }
.page-sub { font-size: 13px; color: #475569; margin-top: 3px; }

.header-actions { display: flex; align-items: center; gap: 10px; }

.mute-btn {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px; color: #64748b; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  width: 34px; height: 34px; transition: background 0.15s, color 0.15s;
}
.mute-btn:hover { background: rgba(255,255,255,0.1); color: #94a3b8; }

.live-indicator {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 600; color: #22c55e;
  background: rgba(34,197,94,0.08); padding: 5px 12px;
  border-radius: 20px; border: 1px solid rgba(34,197,94,0.2);
}

.live-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #22c55e; animation: pulse 1.5s infinite;
}

.tabs {
  display: flex; gap: 2px;
  border-bottom: 1px solid rgba(255,255,255,0.07);
  margin-bottom: 0;
}

.tab {
  display: flex; align-items: center; gap: 7px;
  padding: 10px 16px; background: none; border: none;
  border-bottom: 2px solid transparent;
  font-size: 13px; font-weight: 500; color: #475569;
  cursor: pointer; transition: all 0.12s; margin-bottom: -1px;
}
.tab:hover { color: #94a3b8; }
.tab.active { color: #a5b4fc; border-bottom-color: #6366f1; }

.tab-badge {
  background: #334155; color: #94a3b8;
  font-size: 10px; font-weight: 700;
  padding: 1px 6px; border-radius: 10px;
}
.tab-badge.hot { background: rgba(239,68,68,0.15); color: #ef4444; }

/* ── 3-column layout ─────────────────────────────────────────────────── */
.inbox-layout {
  display: flex;
  flex: 1;
  gap: 0;
  overflow: hidden;
  border-top: 1px solid rgba(255,255,255,0.07);
}

/* ── Session list ────────────────────────────────────────────────────── */
.session-list {
  width: 280px; min-width: 280px;
  border-right: 1px solid rgba(255,255,255,0.07);
  overflow-y: auto; padding: 8px 0;
}

.loading-state { padding: 12px; display: flex; flex-direction: column; gap: 10px; }
.skeleton-session { display: flex; gap: 10px; align-items: center; }
.sk-avatar { width: 36px; height: 36px; border-radius: 50%; background: #1e293b; flex-shrink: 0; }
.sk-lines { flex: 1; display: flex; flex-direction: column; gap: 7px; }
.sk-line { height: 10px; background: #1e293b; border-radius: 4px; }
.sk-line.short { width: 55%; }

.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100%; padding: 40px 20px; text-align: center; gap: 10px;
}
.empty-state p { font-size: 14px; font-weight: 500; color: #334155; }
.empty-state span { font-size: 12px; color: #1e293b; line-height: 1.5; }

.session-row {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 12px 14px; background: none; border: none;
  width: 100%; text-align: left; cursor: pointer; transition: background 0.12s;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.session-row:hover { background: rgba(255,255,255,0.03); }
.session-row.active { background: rgba(99,102,241,0.08); }

.session-avatar {
  width: 34px; height: 34px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: white; flex-shrink: 0;
}

.session-meta { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.session-top-row { display: flex; justify-content: space-between; align-items: baseline; }
.session-name { font-size: 13px; font-weight: 600; color: #cbd5e1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 160px; }
.session-time { font-size: 10px; color: #475569; flex-shrink: 0; }
.session-preview { font-size: 12px; color: #475569; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.session-tags { display: flex; align-items: center; gap: 6px; margin-top: 2px; }

.tag { font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
.tag-hot { background: rgba(239,68,68,0.12); color: #ef4444; }
.tag-converted { background: rgba(34,197,94,0.12); color: #22c55e; }
.tag-engaged { background: rgba(99,102,241,0.12); color: #a5b4fc; }
.tag-new { background: rgba(71,85,105,0.3); color: #64748b; }
.heat-bar { height: 3px; border-radius: 2px; opacity: 0.6; }
.channel-badge { font-size: 8px; font-weight: 700; padding: 1px 5px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.06em; }
.ch-website  { background: rgba(99,102,241,0.1); color: #a5b4fc; }
.ch-whatsapp { background: rgba(37,211,102,0.12); color: #25d366; }
.ch-messenger { background: rgba(0,132,255,0.12); color: #0084ff; }

/* ── Chat panel ──────────────────────────────────────────────────────── */
.chat-panel {
  flex: 1; display: flex; flex-direction: column; overflow: hidden;
  border-right: 1px solid rgba(255,255,255,0.07);
}

.empty-panel {
  align-items: center; justify-content: center;
  gap: 12px; color: #1e293b; font-size: 14px;
}

.chat-panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.07);
}

.chat-user-info { display: flex; align-items: center; gap: 12px; }

.chat-avatar {
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; color: white;
}

.chat-name { font-size: 14px; font-weight: 600; color: #f1f5f9; }
.chat-sub { font-size: 11px; color: #475569; margin-top: 2px; }

.kanban-badge {
  font-size: 10px; font-weight: 700;
  padding: 3px 10px; border-radius: 20px;
  text-transform: uppercase; letter-spacing: 0.06em;
}

.messages {
  flex: 1; overflow-y: auto; padding: 20px;
  display: flex; flex-direction: column; gap: 10px;
}

.message { display: flex; }
.user-msg { justify-content: flex-end; }
.ai-msg { justify-content: flex-start; }

.bubble {
  max-width: 72%; padding: 10px 14px; border-radius: 14px;
  font-size: 13px; line-height: 1.55;
}
.user-msg .bubble { background: #6366f1; color: white; border-bottom-right-radius: 4px; }
.ai-msg .bubble { background: #1e293b; color: #e2e8f0; border-bottom-left-radius: 4px; }

/* ── Visitor panel ───────────────────────────────────────────────────── */
.visitor-panel {
  width: 272px; min-width: 272px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.visitor-panel-empty {
  align-items: center; justify-content: center; gap: 10px;
  color: #1e293b; font-size: 13px;
}

.vp-section {
  padding: 16px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.customer-section { padding-bottom: 12px; }

.vp-customer-header {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 12px;
}

.vp-avatar {
  width: 40px; height: 40px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; color: white; flex-shrink: 0;
}

.vp-customer-info { display: flex; flex-direction: column; gap: 5px; }
.vp-customer-name { font-size: 14px; font-weight: 600; color: #f1f5f9; }

.status-chip {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11px; font-weight: 500; color: #94a3b8;
}

.status-dot-green {
  width: 6px; height: 6px; border-radius: 50%;
  background: #22c55e; flex-shrink: 0;
}

.vp-stats-row {
  display: flex; align-items: center; gap: 8px;
}

.vp-stat {
  display: flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 500; color: #64748b;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 8px; padding: 4px 10px;
}

.first-visit-badge {
  font-size: 11px; font-weight: 600; color: #6366f1;
  background: rgba(99,102,241,0.1);
  border: 1px solid rgba(99,102,241,0.2);
  border-radius: 20px; padding: 3px 10px;
  margin-left: auto;
}

.vp-section-title {
  font-size: 11px; font-weight: 700; color: #334155;
  text-transform: uppercase; letter-spacing: 0.08em;
  margin-bottom: 10px;
  display: flex; align-items: center; gap: 6px;
}

.vp-count {
  background: #334155; color: #64748b;
  font-size: 10px; padding: 1px 6px; border-radius: 8px;
}

.vp-rows { display: flex; flex-direction: column; gap: 10px; }

.vp-row {
  display: flex; align-items: center; gap: 10px; min-height: 20px;
}

.vp-label {
  color: #475569; font-size: 12px;
  flex-shrink: 0; width: 56px;
  display: flex; align-items: center;
}

.vp-value {
  font-size: 12px; color: #cbd5e1;
  flex: 1; min-width: 0;
}

.vp-value.truncate {
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.vp-value.mono {
  font-family: 'Fira Mono', 'JetBrains Mono', monospace;
  font-size: 11px; color: #94a3b8;
}

.assignee-dot {
  display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 50%;
  background: #f59e0b; color: white;
  font-size: 10px; font-weight: 700; margin-right: 5px;
}

.device-row {
  display: flex; align-items: center; gap: 6px;
}

.device-icon { color: #64748b; display: flex; align-items: center; }

.os-badge {
  font-size: 10px; font-weight: 600; color: #64748b;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 4px; padding: 1px 6px;
}

/* Tags */
.vp-tags-row { display: flex; flex-wrap: wrap; gap: 6px; }

.vp-tag {
  font-size: 11px; font-weight: 600;
  padding: 3px 10px; border-radius: 20px;
  text-transform: capitalize;
}

.vp-tag-state {
  background: rgba(71,85,105,0.3); color: #64748b;
}

/* Visited pages */
.vp-pages { display: flex; flex-direction: column; gap: 10px; }

.vp-page-row {
  display: flex; align-items: flex-start; gap: 8px;
}

.page-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #334155; flex-shrink: 0; margin-top: 4px;
}
.page-dot-active { background: #22c55e; }

.page-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
.page-title-text { font-size: 12px; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.page-duration { font-size: 10px; color: #475569; }

/* No data placeholder */
.vp-no-data {
  padding: 24px 16px; text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
}
.vp-no-data p { font-size: 12px; color: #334155; line-height: 1.6; }

@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }
</style>
