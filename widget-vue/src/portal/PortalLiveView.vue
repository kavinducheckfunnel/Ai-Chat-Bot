<template>
  <div class="flex flex-col gap-6 p-6">

    <!-- Header -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Live View</h1>
        <p class="text-sm text-muted-foreground mt-1">Real-time sessions from your chatbot</p>
      </div>
      <div class="flex items-center gap-3">
        <div v-if="wsConnected" class="flex items-center gap-2">
          <div class="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_0_3px_rgba(34,197,94,0.2)] animate-pulse"></div>
          <span class="text-xs font-semibold text-emerald-600">Live</span>
        </div>
        <Button variant="outline" size="sm" @click="loadData" :disabled="loading" class="gap-2">
          <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': loading }" />
          Refresh
        </Button>
      </div>
    </div>

    <!-- Stat cards -->
    <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <Card>
        <CardContent class="pt-4 pb-4">
          <div class="flex items-center gap-3">
            <div class="h-9 w-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <MessageSquare class="h-4 w-4" />
            </div>
            <div>
              <p class="text-xs text-muted-foreground">Total Sessions</p>
              <p class="text-xl font-bold tracking-tight text-foreground">{{ sessions.length }}</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent class="pt-4 pb-4">
          <div class="flex items-center gap-3">
            <div class="h-9 w-9 rounded-lg bg-red-100 text-red-500 flex items-center justify-center shrink-0">
              <Flame class="h-4 w-4" />
            </div>
            <div>
              <p class="text-xs text-muted-foreground">Hot (75+)</p>
              <p class="text-xl font-bold tracking-tight text-red-500">{{ hotCount }}</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent class="pt-4 pb-4">
          <div class="flex items-center gap-3">
            <div class="h-9 w-9 rounded-lg bg-orange-100 text-orange-500 flex items-center justify-center shrink-0">
              <Clock class="h-4 w-4" />
            </div>
            <div>
              <p class="text-xs text-muted-foreground">Warm (40–74)</p>
              <p class="text-xl font-bold tracking-tight text-orange-500">{{ warmCount }}</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent class="pt-4 pb-4">
          <div class="flex items-center gap-3">
            <div class="h-9 w-9 rounded-lg bg-blue-100 text-blue-500 flex items-center justify-center shrink-0">
              <Users class="h-4 w-4" />
            </div>
            <div>
              <p class="text-xs text-muted-foreground">Avg Heat</p>
              <p class="text-xl font-bold tracking-tight text-foreground">{{ avgHeat }}%</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Filter tabs + section title -->
    <div class="flex items-center justify-between gap-4">
      <h2 class="text-sm font-semibold">Sessions</h2>
      <div class="flex rounded-lg border border-border overflow-hidden">
        <button
          v-for="f in filters" :key="f.value"
          class="px-3.5 py-1.5 text-xs font-medium transition-colors"
          :class="activeFilter === f.value ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'"
          @click="activeFilter = f.value"
        >{{ f.label }}</button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading && !sessions.length" class="flex flex-col items-center gap-3 py-16 text-muted-foreground">
      <Loader2 class="h-6 w-6 animate-spin" />
      <p class="text-sm">Loading sessions…</p>
    </div>

    <!-- Empty -->
    <div v-else-if="!filteredSessions.length" class="flex flex-col items-center gap-2 py-16 text-muted-foreground">
      <MessageSquare class="h-8 w-8 opacity-30" />
      <p class="text-sm">No sessions found</p>
    </div>

    <!-- Sessions grid -->
    <div v-else class="grid gap-3" style="grid-template-columns: repeat(auto-fill, minmax(260px, 1fr))">
      <div
        v-for="session in filteredSessions"
        :key="session.session_id"
        class="rounded-xl border bg-card p-4 cursor-pointer hover:-translate-y-0.5 hover:shadow-md transition-all"
        :class="heatBorderClass(session.heat_score)"
        @click="openSession(session)"
      >
        <!-- Top row -->
        <div class="flex items-center justify-between mb-2.5">
          <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold" :class="heatBadgeClass(session.heat_score)">
            {{ heatEmoji(session.heat_score) }} {{ Math.round(session.heat_score || 0) }}%
          </span>
          <span class="inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide" :class="stateClass(session.conversation_state)">
            {{ (session.conversation_state || 'NEW').replace(/_/g, ' ') }}
          </span>
        </div>

        <!-- Heat bar -->
        <div class="h-1.5 rounded-full bg-muted overflow-hidden mb-3.5">
          <div class="h-full rounded-full" :style="{ width: (session.heat_score || 0) + '%', background: heatGradient(session.heat_score) }"></div>
        </div>

        <!-- Signal bars -->
        <div class="space-y-1.5 mb-3">
          <div v-for="sig in sessionSignals(session)" :key="sig.label" class="flex items-center gap-2">
            <span class="text-[10px] text-muted-foreground w-10 shrink-0">{{ sig.label }}</span>
            <div class="flex-1 h-1 rounded-full bg-muted overflow-hidden">
              <div class="h-full rounded-full" :style="{ width: sig.value + '%', background: sig.color }"></div>
            </div>
            <span class="text-[10px] font-mono text-muted-foreground w-7 text-right">{{ sig.value }}%</span>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-between pt-2 border-t border-border">
          <span class="text-[11px] font-mono text-muted-foreground truncate">{{ (session.lead_email || session.visitor_id || 'anon').slice(0, 20) }}</span>
          <span class="text-[11px] text-muted-foreground">{{ session.message_count || 0 }} msgs</span>
        </div>
      </div>
    </div>

    <!-- Chat history modal -->
    <div v-if="selectedSession" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" @click.self="selectedSession = null">
      <div class="bg-background border border-border rounded-xl w-full max-w-lg max-h-[80vh] flex flex-col shadow-xl">
        <div class="flex items-start justify-between px-5 py-4 border-b border-border">
          <div>
            <h3 class="text-base font-semibold">Chat History</h3>
            <p class="text-xs text-muted-foreground font-mono mt-0.5">{{ selectedSession.lead_email || (selectedSession.visitor_id || '').slice(0, 30) || 'Anonymous' }}</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="inline-flex rounded-full px-2 py-0.5 text-xs font-bold" :class="heatBadgeClass(selectedSession.heat_score)">
              {{ heatEmoji(selectedSession.heat_score) }} {{ Math.round(selectedSession.heat_score || 0) }}%
            </span>
            <button class="rounded-md p-1 text-muted-foreground hover:bg-muted transition-colors" @click="selectedSession = null">
              <X class="h-4 w-4" />
            </button>
          </div>
        </div>
        <div v-if="loadingSession" class="flex justify-center items-center py-12">
          <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
        <div v-else class="flex flex-col gap-3 overflow-y-auto px-5 py-4">
          <div
            v-for="(msg, i) in sessionDetail?.chat_history || []"
            :key="i"
            class="flex flex-col max-w-[88%]"
            :class="msg.role === 'user' ? 'self-end items-end' : 'self-start items-start'"
          >
            <span class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">{{ msg.role === 'user' ? 'Visitor' : 'AI' }}</span>
            <p class="text-sm leading-relaxed px-3.5 py-2.5 rounded-xl m-0" :class="msg.role === 'user' ? 'bg-primary text-primary-foreground rounded-br-sm' : 'bg-muted text-foreground rounded-bl-sm'">
              {{ msg.message || msg.content }}
            </p>
          </div>
          <p v-if="!sessionDetail?.chat_history?.length" class="text-sm text-muted-foreground text-center py-6">No messages yet.</p>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { RefreshCw, MessageSquare, Flame, Clock, Users, Loader2, X } from 'lucide-vue-next'
import { useAdminApi } from '../composables/useAdminApi'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'

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
  { label: 'All',      value: 'all' },
  { label: 'Hot (75+)', value: 'hot' },
  { label: 'Warm (40+)', value: 'warm' },
  { label: 'Cool',     value: 'cool' },
]

const filteredSessions = computed(() => {
  if (activeFilter.value === 'hot')  return sessions.value.filter(s => (s.heat_score || 0) >= 75)
  if (activeFilter.value === 'warm') return sessions.value.filter(s => (s.heat_score || 0) >= 40 && (s.heat_score || 0) < 75)
  if (activeFilter.value === 'cool') return sessions.value.filter(s => (s.heat_score || 0) < 40)
  return sessions.value
})

const hotCount  = computed(() => sessions.value.filter(s => (s.heat_score || 0) >= 75).length)
const warmCount = computed(() => sessions.value.filter(s => (s.heat_score || 0) >= 40 && (s.heat_score || 0) < 75).length)
const avgHeat   = computed(() => {
  if (!sessions.value.length) return 0
  return Math.round(sessions.value.reduce((sum, s) => sum + (s.heat_score || 0), 0) / sessions.value.length)
})

function sessionSignals(s) {
  return [
    { label: 'Intent',  value: Math.round((s.intent_ema  || 0) * 100), color: '#6366f1' },
    { label: 'Budget',  value: Math.round((s.budget_ema  || 0) * 100), color: '#22c55e' },
    { label: 'Urgency', value: Math.round((s.urgency_ema || 0) * 100), color: '#f97316' },
  ]
}

async function loadData() {
  if (!props.client) return
  loading.value = true
  try {
    const data = await api.getPortalSessions(props.client.id, { limit: 100 })
    const list = Array.isArray(data) ? data : (data?.results || [])
    sessions.value = list.sort((a, b) => (b.heat_score || 0) - (a.heat_score || 0))
  } catch {} finally {
    loading.value = false
  }
}

function handleWsMessage(msg) {
  if (msg.type !== 'session_update') return
  const incoming = msg.data
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

function heatBorderClass(score) {
  if ((score || 0) >= 75) return 'border-t-2 border-t-red-400'
  if ((score || 0) >= 40) return 'border-t-2 border-t-orange-400'
  return 'border-t-2 border-t-primary/40'
}

function heatBadgeClass(score) {
  if ((score || 0) >= 75) return 'bg-red-100 text-red-600'
  if ((score || 0) >= 40) return 'bg-orange-100 text-orange-600'
  return 'bg-primary/10 text-primary'
}

function heatEmoji(score) {
  if ((score || 0) >= 75) return '🔥'
  if ((score || 0) >= 40) return '🟠'
  return '🔵'
}

function heatGradient(score) {
  if ((score || 0) >= 75) return 'linear-gradient(90deg,#EF4444,#F97316)'
  if ((score || 0) >= 40) return 'linear-gradient(90deg,#F97316,#EAB308)'
  return 'linear-gradient(90deg,#6366F1,#8B5CF6)'
}

function stateClass(state) {
  const map = {
    RESEARCH: 'bg-blue-100 text-blue-600',
    EVALUATION: 'bg-yellow-100 text-yellow-600',
    OBJECTION: 'bg-red-100 text-red-600',
    RECOVERY: 'bg-orange-100 text-orange-600',
    READY_TO_BUY: 'bg-emerald-100 text-emerald-600',
  }
  return map[state] || 'bg-blue-100 text-blue-600'
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
