<template>
  <div class="p-6 space-y-6">
    <!-- Page header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold tracking-tight">Live Dashboard</h1>
        <p class="text-sm text-muted-foreground">Real-time visitor heat scores and session monitoring</p>
      </div>
      <div class="flex items-center gap-2">
        <button class="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors" @click="toggleMute" :title="muted ? 'Unmute' : 'Mute'">
          <Volume2 v-if="!muted" class="h-4 w-4" />
          <VolumeX v-else class="h-4 w-4" />
        </button>
        <Button variant="outline" size="sm" @click="loadData" :disabled="loading">
          <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': loading }" />
          Refresh
        </Button>
      </div>
    </div>

    <!-- Stat cards -->
    <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <Card v-for="s in statCards" :key="s.label">
        <CardContent class="p-6">
          <div class="flex items-center justify-between">
            <div class="space-y-1">
              <p class="text-sm font-medium text-muted-foreground">{{ s.label }}</p>
              <p class="text-2xl font-bold">{{ s.value ?? '—' }}</p>
            </div>
            <div :class="['flex h-10 w-10 items-center justify-center rounded-lg', s.bg]">
              <component :is="s.icon" :class="['h-5 w-5', s.color]" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Analytics row -->
    <div class="grid gap-4 lg:grid-cols-2">
      <!-- Heat Distribution -->
      <Card>
        <CardHeader class="pb-2">
          <CardTitle class="text-sm font-medium">Heat Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="h-3 w-full overflow-hidden rounded-full flex gap-0.5">
            <div class="rounded-l-full bg-blue-400 transition-all" :style="{ flex: heatTotal ? (stats.heat_distribution?.cold || 0) : 1 }" />
            <div class="bg-amber-400 transition-all" :style="{ flex: heatTotal ? (stats.heat_distribution?.warm || 0) : 1 }" />
            <div class="rounded-r-full bg-red-500 transition-all" :style="{ flex: heatTotal ? (stats.heat_distribution?.hot || 0) : 1 }" />
          </div>
          <div class="mt-3 flex items-center gap-4 text-sm">
            <div class="flex items-center gap-1.5"><span class="h-2 w-2 rounded-full bg-blue-400" />Cold <span class="font-medium">{{ stats.heat_distribution?.cold ?? 0 }}</span></div>
            <div class="flex items-center gap-1.5"><span class="h-2 w-2 rounded-full bg-amber-400" />Warm <span class="font-medium">{{ stats.heat_distribution?.warm ?? 0 }}</span></div>
            <div class="flex items-center gap-1.5"><span class="h-2 w-2 rounded-full bg-red-500" />Hot <span class="font-medium">{{ stats.heat_distribution?.hot ?? 0 }}</span></div>
          </div>
        </CardContent>
      </Card>

      <!-- 14-day sparkline -->
      <Card>
        <CardHeader class="pb-2">
          <CardTitle class="text-sm font-medium">Sessions — Last 14 Days</CardTitle>
        </CardHeader>
        <CardContent>
          <svg v-if="stats.daily_trend?.length" class="h-16 w-full" viewBox="0 0 280 60" preserveAspectRatio="none">
            <defs>
              <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#6366f1" stop-opacity="0.25"/>
                <stop offset="100%" stop-color="#6366f1" stop-opacity="0"/>
              </linearGradient>
            </defs>
            <polyline :points="sparklineAreaPoints" fill="url(#sparkGrad)" stroke="none" />
            <polyline :points="sparklinePoints" fill="none" stroke="#6366f1" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
          </svg>
          <p v-else class="py-4 text-center text-sm text-muted-foreground">No data yet</p>
          <div v-if="stats.daily_trend?.length" class="flex justify-between text-xs text-muted-foreground mt-1">
            <span>{{ stats.daily_trend[0].date }}</span>
            <span>{{ stats.daily_trend[stats.daily_trend.length - 1].date }}</span>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Sessions section -->
    <div>
      <div class="mb-4 flex items-center justify-between">
        <h2 class="text-lg font-semibold">Recent Sessions</h2>
        <div class="flex rounded-lg border p-1 gap-1">
          <button
            v-for="f in heatFilters" :key="f.value"
            @click="activeFilter = f.value"
            :class="['rounded-md px-3 py-1 text-xs font-medium transition-colors', activeFilter === f.value ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground']"
          >{{ f.label }}</button>
        </div>
      </div>

      <div v-if="loading && !sessions.length" class="flex items-center justify-center py-16 gap-3 text-muted-foreground">
        <Loader2 class="h-5 w-5 animate-spin" /> Loading sessions…
      </div>
      <div v-else-if="!filteredSessions.length" class="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <MessageSquare class="h-10 w-10 mb-2 opacity-30" />
        <p class="text-sm">No sessions found</p>
      </div>
      <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <Card
          v-for="session in filteredSessions" :key="session.session_id"
          class="cursor-pointer transition-shadow hover:shadow-md"
          :class="session.heat_score >= 70 ? 'border-red-200' : session.heat_score >= 40 ? 'border-amber-200' : ''"
          @click="openSession(session)"
        >
          <CardContent class="p-4 space-y-3">
            <div class="flex items-center justify-between">
              <Badge :variant="session.heat_score >= 70 ? 'destructive' : session.heat_score >= 40 ? 'warning' : 'secondary'" class="text-xs">
                🔥 {{ session.heat_score }}%
              </Badge>
              <Badge variant="outline" class="text-xs capitalize">{{ session.conversation_state?.replace('_', ' ') }}</Badge>
            </div>

            <div class="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div class="h-full rounded-full transition-all"
                :class="session.heat_score >= 70 ? 'bg-red-500' : session.heat_score >= 40 ? 'bg-amber-400' : 'bg-blue-400'"
                :style="{ width: session.heat_score + '%' }" />
            </div>

            <div class="space-y-1.5">
              <div v-for="m in sessionMetrics(session)" :key="m.label" class="flex items-center gap-2">
                <span class="w-12 text-xs text-muted-foreground">{{ m.label }}</span>
                <div class="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                  <div class="h-full rounded-full" :class="m.color" :style="{ width: m.pct + '%' }" />
                </div>
                <span class="w-8 text-right text-xs font-medium">{{ m.pct }}%</span>
              </div>
            </div>

            <div class="flex items-center justify-between text-xs text-muted-foreground">
              <span class="font-mono truncate max-w-[100px]">{{ session.visitor_id?.slice(0, 10) }}…</span>
              <span>{{ session.message_count }} msgs</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>

    <!-- Session detail dialog -->
    <Dialog :open="!!selectedSession" @update:open="selectedSession = null">
      <DialogHeader>
        <DialogTitle>Session Detail</DialogTitle>
        <p class="text-xs text-muted-foreground font-mono">{{ selectedSession?.visitor_id }}</p>
      </DialogHeader>
      <div class="flex justify-end mb-3">
        <Button size="sm" variant="outline" @click="openGodView(selectedSession)">
          <Eye class="h-3.5 w-3.5" /> God View
        </Button>
      </div>
      <div v-if="loadingSession" class="flex justify-center py-8">
        <Loader2 class="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
      <div v-else class="max-h-[400px] overflow-y-auto space-y-3">
        <div v-for="(msg, i) in sessionDetail?.chat_history || []" :key="i"
          :class="['rounded-lg px-3 py-2 text-sm max-w-[85%]', msg.role === 'user' ? 'ml-auto bg-primary text-primary-foreground' : 'bg-muted']">
          <p class="text-[10px] font-medium mb-1 opacity-60">{{ msg.role === 'user' ? 'Visitor' : 'AI' }}</p>
          <p>{{ msg.message || msg.content }}</p>
        </div>
        <p v-if="!sessionDetail?.chat_history?.length" class="py-4 text-center text-sm text-muted-foreground">No chat history.</p>
      </div>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Users, Activity, Flame, MapPin, RefreshCw, Volume2, VolumeX, Loader2, MessageSquare, Eye } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import DialogHeader from '@/components/ui/DialogHeader.vue'
import DialogTitle from '@/components/ui/DialogTitle.vue'
import { useAdminApi } from '@/composables/useAdminApi'

const api = useAdminApi()
const router = useRouter()
const sessions = ref([])
const stats = ref({})
const loading = ref(false)
const activeFilter = ref('all')
const selectedSession = ref(null)
const sessionDetail = ref(null)
const loadingSession = ref(false)
const muted = ref(localStorage.getItem('cf_inbox_muted') === '1')

const statCards = computed(() => [
  { label: 'Total Clients', value: stats.value.total_clients, icon: Users, bg: 'bg-blue-50', color: 'text-blue-600' },
  { label: 'Total Sessions', value: stats.value.total_sessions, icon: Activity, bg: 'bg-green-50', color: 'text-green-600' },
  { label: 'Hot Sessions', value: stats.value.heat_distribution?.hot, icon: Flame, bg: 'bg-red-50', color: 'text-red-500' },
  { label: 'Active Clients', value: stats.value.active_clients, icon: MapPin, bg: 'bg-orange-50', color: 'text-orange-500' },
])

const heatFilters = [
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
  return d ? (d.hot || 0) + (d.warm || 0) + (d.cold || 0) : 0
})

function sessionMetrics(s) {
  return [
    { label: 'Intent', pct: Math.round((s.intent_ema || 0) * 100), color: 'bg-blue-500' },
    { label: 'Budget', pct: Math.round((s.budget_ema || 0) * 100), color: 'bg-green-500' },
    { label: 'Urgency', pct: Math.round((s.urgency_ema || 0) * 100), color: 'bg-orange-500' },
  ]
}

const sparklinePoints = computed(() => {
  const trend = stats.value.daily_trend
  if (!trend?.length) return ''
  const W = 280, H = 60, PAD = 4
  const max = Math.max(...trend.map(d => d.count), 1)
  return trend.map((d, i) => {
    const x = PAD + (i / (trend.length - 1)) * (W - PAD * 2)
    const y = H - PAD - (d.count / max) * (H - PAD * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})

const sparklineAreaPoints = computed(() => {
  const trend = stats.value.daily_trend
  if (!trend?.length) return ''
  const W = 280, H = 60, PAD = 4
  const max = Math.max(...trend.map(d => d.count), 1)
  const pts = trend.map((d, i) => {
    const x = PAD + (i / (trend.length - 1)) * (W - PAD * 2)
    const y = H - PAD - (d.count / max) * (H - PAD * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  return `${pts[0].split(',')[0]},${H} ${pts.join(' ')} ${pts[pts.length - 1].split(',')[0]},${H}`
})

function toggleMute() {
  muted.value = !muted.value
  localStorage.setItem('cf_inbox_muted', muted.value ? '1' : '0')
}

function playNotificationSound() {
  if (muted.value) return
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    ;[880, 1100].forEach((freq, i) => {
      const osc = ctx.createOscillator(), gain = ctx.createGain()
      osc.connect(gain); gain.connect(ctx.destination)
      osc.frequency.value = freq
      gain.gain.setValueAtTime(0, ctx.currentTime + i * 0.18)
      gain.gain.linearRampToValueAtTime(0.18, ctx.currentTime + i * 0.18 + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.18 + 0.35)
      osc.start(ctx.currentTime + i * 0.18); osc.stop(ctx.currentTime + i * 0.18 + 0.35)
    })
    setTimeout(() => ctx.close(), 1200)
  } catch {}
}

async function loadData() {
  loading.value = true
  try {
    const [statsData, clients] = await Promise.all([api.getStats(), api.getClients()])
    stats.value = statsData || {}
    const all = []
    for (const c of (clients || []).slice(0, 10)) {
      try { all.push(...(await api.getClientSessions(c.id) || [])) } catch {}
    }
    sessions.value = all.sort((a, b) => b.heat_score - a.heat_score)
  } finally { loading.value = false }
}

async function openSession(session) {
  selectedSession.value = session
  loadingSession.value = true
  try { sessionDetail.value = await api.getSession(session.session_id) } catch {}
  finally { loadingSession.value = false }
}

function openGodView(session) {
  selectedSession.value = null
  router.push(`/admin/godview/${session.session_id}`)
}

let ws = null
function connectWs() {
  ws = api.connectAdminDashboard((msg) => {
    if (msg.type === 'stats_update') { stats.value = { ...stats.value, ...msg.data }; return }
    if (msg.type === 'new_session') { if (!sessions.value.find(s => s.session_id === msg.session?.session_id)) { sessions.value = [msg.session, ...sessions.value]; playNotificationSound() } }
    if (msg.type === 'session_update') { const i = sessions.value.findIndex(s => s.session_id === msg.session?.session_id); if (i >= 0) sessions.value[i] = { ...sessions.value[i], ...msg.session } }
  })
}

onMounted(() => { loadData(); connectWs() })
onUnmounted(() => ws?.close())
</script>
