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
      <!-- Session list -->
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
              <span class="heat-bar" :style="{ background: heatColor(s.heat_score), width: (s.heat_score * 60 + 20) + 'px' }"></span>
            </div>
          </div>
        </button>
      </div>

      <!-- Chat detail panel -->
      <div class="chat-panel" v-if="selected">
        <div class="chat-panel-header">
          <div class="chat-user-info">
            <div class="chat-avatar" :style="{ background: heatColor(selected.heat_score) }">{{ initials(selected) }}</div>
            <div>
              <p class="chat-name">{{ selected.lead_email || 'Visitor #' + selected.session_id.slice(0,6) }}</p>
              <p class="chat-sub">{{ selected.conversation_state }} · Heat {{ Math.round((selected.heat_score || 0) * 100) }}%</p>
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
            <div class="bubble">{{ msg.content }}</div>
          </div>
        </div>

        <!-- Lead info footer -->
        <div class="lead-footer" v-if="selected.lead_email || selected.lead_phone">
          <div class="lead-field" v-if="selected.lead_email">
            <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" stroke="#6366f1" stroke-width="2"/><polyline points="22,6 12,13 2,6" stroke="#6366f1" stroke-width="2" stroke-linecap="round"/></svg>
            {{ selected.lead_email }}
          </div>
          <div class="lead-field" v-if="selected.lead_phone">
            <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 014.17 11.6a19.79 19.79 0 01-3.07-8.7A2 2 0 013.09 1h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L7.09 8.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            {{ selected.lead_phone }}
          </div>
        </div>
      </div>

      <div class="chat-panel empty-panel" v-else>
        <svg width="32" height="32" fill="none" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="#1e293b" stroke-width="1.5" stroke-linecap="round"/></svg>
        <p>Select a conversation</p>
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
    // Two-tone "new visitor" chime
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
  if (activeTab.value === 'hot') return sessions.value.filter(s => s.kanban_state === 'HOT_LEAD' || s.heat_score > 0.65)
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
  return last?.content?.slice(0, 60) + (last?.content?.length > 60 ? '…' : '') || ''
}

function initials(s) {
  if (s.lead_email) return s.lead_email[0].toUpperCase()
  return '#'
}

function heatColor(score) {
  if (!score) return '#1e293b'
  if (score > 0.7) return '#ef4444'
  if (score > 0.4) return '#f59e0b'
  return '#6366f1'
}

function kanbanClass(state) {
  if (state === 'HOT_LEAD') return 'tag-hot'
  if (state === 'CONVERTED') return 'tag-converted'
  if (state === 'ENGAGED') return 'tag-engaged'
  return 'tag-new'
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
})

onUnmounted(() => { if (ws) ws.close() })

watch(() => props.client, loadSessions)
watch(selected, () => {
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
  border-radius: 8px;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  transition: background 0.15s, color 0.15s;
}
.mute-btn:hover { background: rgba(255,255,255,0.1); color: #94a3b8; }

.live-indicator {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 600; color: #22c55e;
  background: rgba(34,197,94,0.08);
  padding: 5px 12px;
  border-radius: 20px;
  border: 1px solid rgba(34,197,94,0.2);
}

.live-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #22c55e;
  animation: pulse 1.5s infinite;
}

.tabs {
  display: flex; gap: 2px;
  border-bottom: 1px solid rgba(255,255,255,0.07);
  margin-bottom: 0;
}

.tab {
  display: flex; align-items: center; gap: 7px;
  padding: 10px 16px;
  background: none; border: none;
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

/* Layout */
.inbox-layout {
  display: flex;
  flex: 1;
  gap: 0;
  overflow: hidden;
  border-top: 1px solid rgba(255,255,255,0.07);
}

/* Session list */
.session-list {
  width: 300px;
  min-width: 300px;
  border-right: 1px solid rgba(255,255,255,0.07);
  overflow-y: auto;
  padding: 8px 0;
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
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  transition: background 0.12s;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.session-row:hover { background: rgba(255,255,255,0.03); }
.session-row.active { background: rgba(99,102,241,0.08); }

.session-avatar {
  width: 34px; height: 34px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: white;
  flex-shrink: 0;
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

/* Chat panel */
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.empty-panel {
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #1e293b;
  font-size: 14px;
}

.chat-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
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
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.message { display: flex; }
.user-msg { justify-content: flex-end; }
.ai-msg { justify-content: flex-start; }

.bubble {
  max-width: 72%;
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 13px;
  line-height: 1.55;
}
.user-msg .bubble { background: #6366f1; color: white; border-bottom-right-radius: 4px; }
.ai-msg .bubble { background: #1e293b; color: #e2e8f0; border-bottom-left-radius: 4px; }

.lead-footer {
  padding: 12px 20px;
  border-top: 1px solid rgba(255,255,255,0.07);
  display: flex;
  gap: 20px;
  background: #111111;
}

.lead-field {
  display: flex; align-items: center; gap: 7px;
  font-size: 12px; color: #64748b;
}

@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }
</style>
