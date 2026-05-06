<template>
  <div class="flex flex-col h-full">

    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
      <div>
        <h1 class="text-xl font-semibold tracking-tight">Inbox</h1>
        <p class="text-sm text-muted-foreground mt-0.5">Real-time conversations from your website</p>
      </div>
      <div class="flex items-center gap-2">
        <button class="rounded-md border border-border p-2 text-muted-foreground hover:bg-accent transition-colors" @click="toggleMute" :title="muted ? 'Unmute notifications' : 'Mute notifications'">
          <Volume2 v-if="!muted" class="h-4 w-4" />
          <VolumeX v-else class="h-4 w-4" />
        </button>
        <div class="flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-600">
          <div class="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
          Live
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex border-b border-border px-6 shrink-0">
      <button
        v-for="tab in ['all', 'ai', 'hot']" :key="tab"
        class="flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors"
        :class="activeTab === tab ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'"
        @click="activeTab = tab"
      >
        {{ tab === 'all' ? 'All chats' : tab === 'ai' ? 'AI handled' : 'Hot leads' }}
        <span v-if="tab === 'all' && sessions.length" class="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-bold text-muted-foreground">{{ sessions.length }}</span>
        <span v-if="tab === 'hot' && hotCount" class="rounded-full bg-red-100 px-1.5 py-0.5 text-[10px] font-bold text-red-600">{{ hotCount }}</span>
      </button>
    </div>

    <!-- 3-column layout -->
    <div class="flex flex-1 overflow-hidden">

      <!-- Session list -->
      <div class="flex w-72 shrink-0 flex-col border-r border-border overflow-y-auto">
        <div v-if="loading" class="space-y-3 p-3">
          <div v-for="n in 4" :key="n" class="flex items-center gap-3 animate-pulse">
            <div class="h-9 w-9 rounded-full bg-muted shrink-0"></div>
            <div class="flex-1 space-y-2"><div class="h-2.5 rounded bg-muted"></div><div class="h-2 w-3/4 rounded bg-muted"></div></div>
          </div>
        </div>

        <div v-else-if="!filteredSessions.length" class="flex flex-col items-center justify-center h-full gap-3 p-8 text-center">
          <MessageSquare class="h-10 w-10 text-muted-foreground/30" />
          <p class="text-sm font-medium text-foreground">No chats yet</p>
          <p class="text-xs text-muted-foreground">Sessions will appear here once visitors start chatting.</p>
        </div>

        <button
          v-else
          v-for="s in filteredSessions" :key="s.session_id"
          class="flex items-start gap-3 border-b border-border px-4 py-3 text-left transition-colors w-full"
          :class="selectedId === s.session_id ? 'bg-primary/5' : 'hover:bg-muted/40'"
          @click="select(s)"
        >
          <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white" :style="{ background: heatColor(s.heat_score) }">
            {{ initials(s) }}
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-baseline justify-between gap-1">
              <span class="truncate text-sm font-medium text-foreground">{{ s.lead_email || 'Visitor #' + s.session_id.slice(0,6) }}</span>
              <span class="shrink-0 text-[10px] text-muted-foreground">{{ timeAgo(s.updated_at) }}</span>
            </div>
            <p class="truncate text-xs text-muted-foreground mt-0.5">{{ lastMessage(s) }}</p>
            <div class="flex items-center gap-1.5 mt-1.5">
              <span class="rounded px-1.5 py-0.5 text-[9px] font-bold uppercase" :class="{ 'bg-red-100 text-red-700': s.kanban_state === 'HOT_LEAD', 'bg-emerald-100 text-emerald-700': s.kanban_state === 'CONVERTED', 'bg-blue-100 text-blue-700': s.kanban_state === 'ENGAGED', 'bg-muted text-muted-foreground': !['HOT_LEAD','CONVERTED','ENGAGED'].includes(s.kanban_state) }">{{ s.kanban_state }}</span>
              <span class="rounded px-1.5 py-0.5 text-[8px] font-bold uppercase" :class="s.channel === 'whatsapp' ? 'bg-green-100 text-green-700' : s.channel === 'messenger' ? 'bg-blue-100 text-blue-700' : 'bg-primary/10 text-primary'">{{ channelLabel(s.channel) }}</span>
              <div class="ml-auto h-1 rounded-full opacity-60" :style="{ background: heatColor(s.heat_score), width: (s.heat_score / 100 * 40 + 10) + 'px' }"></div>
            </div>
          </div>
        </button>
      </div>

      <!-- Chat panel -->
      <div class="flex flex-1 flex-col overflow-hidden border-r border-border">
        <template v-if="selected">
          <div class="flex items-center justify-between border-b border-border px-5 py-3 shrink-0">
            <div class="flex items-center gap-3">
              <div class="flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold text-white" :style="{ background: heatColor(selected.heat_score) }">{{ initials(selected) }}</div>
              <div>
                <p class="text-sm font-semibold text-foreground">{{ selected.lead_email || 'Visitor #' + selected.session_id.slice(0,6) }}</p>
                <p class="text-[11px] text-muted-foreground">{{ selected.conversation_state }} · Heat {{ Math.round(selected.heat_score || 0) }}%</p>
              </div>
            </div>
            <span class="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase" :class="{ 'bg-red-100 text-red-700': selected.kanban_state === 'HOT_LEAD', 'bg-emerald-100 text-emerald-700': selected.kanban_state === 'CONVERTED', 'bg-blue-100 text-blue-700': selected.kanban_state === 'ENGAGED', 'bg-muted text-muted-foreground': !['HOT_LEAD','CONVERTED','ENGAGED'].includes(selected.kanban_state) }">{{ selected.kanban_state }}</span>
          </div>
          <div class="flex-1 overflow-y-auto p-5 space-y-3" ref="messagesEl">
            <div v-for="(msg, i) in chatHistory" :key="i" class="flex" :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">
              <div class="max-w-[72%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed" :class="msg.role === 'user' ? 'bg-primary text-primary-foreground rounded-br-sm' : 'bg-muted text-foreground rounded-bl-sm'">
                {{ msg.message || msg.content }}
              </div>
            </div>
          </div>
        </template>
        <div v-else class="flex flex-1 flex-col items-center justify-center gap-3 text-muted-foreground">
          <MessageSquare class="h-8 w-8 opacity-30" />
          <p class="text-sm">Select a conversation</p>
        </div>
      </div>

      <!-- Visitor details panel -->
      <div class="flex w-68 shrink-0 flex-col overflow-y-auto" style="min-width:260px;max-width:280px">
        <template v-if="selected">

          <!-- Customer -->
          <div class="border-b border-border p-4">
            <div class="flex items-center gap-3">
              <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white" :style="{ background: heatColor(selected.heat_score) }">{{ initials(selected) }}</div>
              <div>
                <p class="text-sm font-medium text-foreground">{{ selected.lead_email ? selected.lead_email.split('@')[0] : 'Visitor' }}</p>
                <span class="inline-flex items-center gap-1 text-[11px] text-emerald-600"><div class="h-1.5 w-1.5 rounded-full bg-emerald-500"></div>Chatting</span>
              </div>
            </div>
            <div class="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
              <span class="flex items-center gap-1"><MessageSquare class="h-3 w-3"/>{{ selected.message_count || 0 }}</span>
              <span class="ml-auto rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium">First visit</span>
            </div>
          </div>

          <!-- Chat info -->
          <div class="border-b border-border p-4 space-y-2">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Chat info</p>
            <div class="space-y-1.5">
              <div class="flex justify-between text-xs"><span class="text-muted-foreground">Chat ID</span><span class="font-mono text-foreground">{{ selected.session_id.slice(0,10).toUpperCase() }}</span></div>
              <div class="flex justify-between text-xs"><span class="text-muted-foreground">Duration</span><span class="text-foreground">{{ chatDuration }}</span></div>
            </div>
          </div>

          <!-- Visitor info -->
          <div class="border-b border-border p-4 space-y-2">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Visitor info</p>
            <div class="space-y-1.5 text-xs">
              <div v-if="selected.lead_email" class="flex items-center gap-2"><Mail class="h-3 w-3 text-muted-foreground shrink-0" /><span class="truncate text-foreground">{{ selected.lead_email }}</span></div>
              <div v-if="selected.visitor_city || selected.visitor_country" class="flex items-center gap-2"><MapPin class="h-3 w-3 text-muted-foreground shrink-0" /><span class="text-foreground">{{ [selected.visitor_city, selected.visitor_country].filter(Boolean).join(', ') }} {{ countryFlag(selected.visitor_country_code) }}</span></div>
              <div v-if="selected.visitor_timezone" class="flex items-center gap-2"><Clock class="h-3 w-3 text-muted-foreground shrink-0" /><span class="text-foreground">{{ visitorLocalTime }}</span></div>
              <div v-if="selected.visitor_device" class="flex items-center gap-2"><Monitor class="h-3 w-3 text-muted-foreground shrink-0" /><span class="text-foreground capitalize">{{ selected.visitor_device }}<span v-if="selected.visitor_os" class="ml-1 text-muted-foreground">· {{ selected.visitor_os }}</span></span></div>
              <div v-if="selected.visitor_browser" class="flex items-center gap-2"><Globe class="h-3 w-3 text-muted-foreground shrink-0" /><span class="text-foreground">{{ selected.visitor_browser }}</span></div>
            </div>
          </div>

          <!-- Labels -->
          <div class="border-b border-border p-4 space-y-2">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Labels</p>
            <div class="flex flex-wrap gap-1.5">
              <span class="rounded-full px-2 py-0.5 text-[10px] font-medium bg-muted text-muted-foreground">{{ selected.kanban_state.replace('_',' ').toLowerCase() }}</span>
              <span class="rounded-full px-2 py-0.5 text-[10px] font-medium bg-muted text-muted-foreground">{{ selected.conversation_state.replace('_',' ').toLowerCase() }}</span>
              <span v-for="t in (selected.tags || [])" :key="t" class="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                {{ t }}<button class="hover:text-destructive" @click.stop="removeTag(t)">✕</button>
              </span>
            </div>
            <div class="flex gap-1.5 mt-2">
              <input class="h-7 flex-1 rounded-md border border-input bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring" v-model="tagInput" placeholder="Add label…" maxlength="50" @keydown.enter.prevent="addTag" />
              <button class="h-7 rounded-md bg-muted px-2 text-xs font-medium hover:bg-accent disabled:opacity-50" @click="addTag" :disabled="!tagInput.trim()">Add</button>
            </div>
            <p v-if="tagError" class="text-[10px] text-destructive">{{ tagError }}</p>
          </div>

          <!-- Visited pages -->
          <div v-if="selected.page_visits && selected.page_visits.length" class="border-b border-border p-4 space-y-2">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Visited pages <span class="ml-1 text-foreground">{{ selected.page_visits.length }}</span></p>
            <div class="space-y-2">
              <div v-for="(pv, i) in selected.page_visits.slice().reverse()" :key="i" class="flex items-start gap-2">
                <div class="mt-1 h-1.5 w-1.5 rounded-full shrink-0" :class="i === 0 ? 'bg-primary' : 'bg-muted-foreground/40'"></div>
                <div class="min-w-0">
                  <p class="truncate text-[11px] text-foreground">{{ pv.title || pv.url }}</p>
                  <p class="text-[10px] text-muted-foreground">{{ formatDuration(pv.duration_seconds) }}</p>
                </div>
              </div>
            </div>
          </div>

        </template>
        <div v-else class="flex flex-1 flex-col items-center justify-center gap-2 text-muted-foreground">
          <User class="h-8 w-8 opacity-30" />
          <p class="text-sm">Visitor details</p>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { MessageSquare, Volume2, VolumeX, Mail, MapPin, Clock, Monitor, Globe, User } from 'lucide-vue-next'
import { useAdminApi } from '../composables/useAdminApi'

const props = defineProps({ client: Object })
const api = useAdminApi()

const sessions = ref([])
const loading = ref(true)
const activeTab = ref('all')
const selectedId = ref(null)
const messagesEl = ref(null)
let ws = null

const chatDuration = ref('0m 0s')
const visitorLocalTime = ref('')
let durationTimer = null

function updateDuration() {
  const s = selected.value
  if (!s?.created_at) { chatDuration.value = '—'; return }
  const created = new Date(s.created_at).getTime()
  const lastActivity = new Date(s.updated_at || s.created_at).getTime()
  const idleMs = Date.now() - lastActivity
  const IDLE_LIMIT = 10 * 60 * 1000
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
    const fmt = new Intl.DateTimeFormat('en-US', { timeZone: tz, hour: 'numeric', minute: '2-digit', weekday: 'short' })
    visitorLocalTime.value = fmt.format(new Date())
  } catch { visitorLocalTime.value = '' }
}

function startTimers() {
  clearInterval(durationTimer)
  updateDuration()
  updateVisitorClock()
  durationTimer = setInterval(() => { updateDuration(); updateVisitorClock() }, 1000)
}

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
  } catch {} finally { loading.value = false }
}

function select(s) {
  selectedId.value = s.session_id
  nextTick(() => { if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight })
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
  if (!score) return 'hsl(var(--muted-foreground))'
  if (score > 70) return '#ef4444'
  if (score > 40) return '#f59e0b'
  return '#6366f1'
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

function formatDuration(seconds) {
  if (!seconds) return '< 1s'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m === 0) return `${s}s`
  return `${m}m ${s}s`
}

const tagInput = ref('')
const tagError = ref('')

async function addTag() {
  const tag = tagInput.value.trim()
  if (!tag || !selected.value) return
  const existing = selected.value.tags || []
  if (existing.includes(tag)) { tagError.value = 'Tag already exists.'; return }
  tagError.value = ''
  const newTags = [...existing, tag]
  try {
    await api.updateSessionTags(selected.value.session_id, newTags)
    const idx = sessions.value.findIndex(s => s.session_id === selected.value.session_id)
    if (idx !== -1) sessions.value[idx] = { ...sessions.value[idx], tags: newTags }
    tagInput.value = ''
  } catch { tagError.value = 'Failed to save tag.' }
}

async function removeTag(tag) {
  if (!selected.value) return
  const newTags = (selected.value.tags || []).filter(t => t !== tag)
  try {
    await api.updateSessionTags(selected.value.session_id, newTags)
    const idx = sessions.value.findIndex(s => s.session_id === selected.value.session_id)
    if (idx !== -1) sessions.value[idx] = { ...sessions.value[idx], tags: newTags }
  } catch {}
}

function requestNotificationPermission() {
  if ('Notification' in window && Notification.permission === 'default') Notification.requestPermission()
}

function showDesktopNotification(title, body) {
  if (!('Notification' in window) || Notification.permission !== 'granted' || muted.value) return
  try { new Notification(title, { body, icon: '/favicon.ico', tag: 'cf-new-session' }) } catch {}
}

let channelPollTimer = null

function startChannelPolling(sessionId) {
  stopChannelPolling()
  channelPollTimer = setInterval(async () => {
    try {
      const data = await api.getSessionHistory(sessionId)
      const idx = sessions.value.findIndex(s => s.session_id === sessionId)
      if (idx !== -1 && data.chat_history) {
        const current = sessions.value[idx].chat_history || []
        if (data.chat_history.length !== current.length) {
          sessions.value[idx] = { ...sessions.value[idx], chat_history: data.chat_history }
          nextTick(() => { if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight })
        }
      }
    } catch {}
  }, 3000)
}

function stopChannelPolling() {
  if (channelPollTimer) { clearInterval(channelPollTimer); channelPollTimer = null }
}

onMounted(async () => {
  requestNotificationPermission()
  await loadSessions()
  ws = api.connectAdminDashboard((msg) => {
    if (msg.type === 'session_update') {
      const prevCount = sessions.value.length
      loadSessions().then(() => {
        if (sessions.value.length > prevCount) {
          playNotificationSound()
          showDesktopNotification('New visitor', 'A new visitor started a chat on your site.')
        }
      })
    }
  })
  startTimers()
})

onUnmounted(() => {
  if (ws) ws.close()
  clearInterval(durationTimer)
  stopChannelPolling()
})

watch(() => props.client, loadSessions)

watch(selected, (s) => {
  if (s) {
    startTimers()
    if (s.channel && s.channel !== 'website') startChannelPolling(s.session_id)
    else stopChannelPolling()
  } else {
    stopChannelPolling()
  }
  nextTick(() => { if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight })
})
</script>
