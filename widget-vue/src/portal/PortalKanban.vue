<template>
  <div class="flex flex-col h-full p-6 gap-6">

    <!-- Header -->
    <div class="flex items-start justify-between gap-4 shrink-0">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Pipeline</h1>
        <p class="text-sm text-muted-foreground mt-1">Drag sessions to update their stage</p>
      </div>
      <Button variant="outline" size="sm" @click="loadData" :disabled="loading" class="gap-2">
        <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': loading }" />
        Refresh
      </Button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex flex-col items-center gap-3 py-16 text-muted-foreground">
      <Loader2 class="h-6 w-6 animate-spin" />
      <p class="text-sm">Loading pipeline…</p>
    </div>

    <!-- Kanban board -->
    <div v-else class="flex gap-3 flex-1 overflow-x-auto pb-2">
      <div
        v-for="col in columns"
        :key="col.key"
        class="flex-none w-56 flex flex-col rounded-xl border border-border transition-colors"
        :class="dragOverCol === col.key ? 'border-primary bg-primary/5' : 'bg-muted/30'"
        @dragover.prevent
        @drop="onDrop($event, col.key)"
        @dragenter="dragOverCol = col.key"
        @dragleave="dragOverCol = null"
      >
        <!-- Column header -->
        <div class="flex items-center justify-between px-3 py-2.5 rounded-t-xl" :class="col.headerBg">
          <span class="text-xs font-bold text-foreground">{{ col.label }}</span>
          <span class="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-background/60 px-1.5 text-[10px] font-bold text-muted-foreground">
            {{ columnSessions(col.key).length }}
          </span>
        </div>

        <!-- Cards -->
        <div class="flex flex-col gap-2 p-2 flex-1 overflow-y-auto">
          <div
            v-for="session in columnSessions(col.key)"
            :key="session.session_id"
            class="rounded-lg border border-border bg-background p-3 cursor-grab hover:-translate-y-0.5 hover:shadow-sm transition-all active:cursor-grabbing"
            draggable="true"
            @dragstart="onDragStart($event, session)"
            @dragend="dragOverCol = null"
            @click="openSession(session)"
          >
            <div class="flex items-center justify-between mb-1.5">
              <span class="inline-flex rounded-full px-1.5 py-0.5 text-[11px] font-bold" :class="heatBadgeClass(session.heat_score)">
                {{ heatEmoji(session.heat_score) }} {{ Math.round(session.heat_score || 0) }}%
              </span>
            </div>
            <div class="h-1 rounded-full bg-muted overflow-hidden mb-2.5">
              <div class="h-full rounded-full" :style="{ width: (session.heat_score || 0) + '%', background: heatGradient(session.heat_score) }"></div>
            </div>
            <p class="text-xs font-medium text-foreground truncate mb-0.5">
              {{ session.lead_email || (session.visitor_id || 'Anonymous').slice(0, 16) + '…' }}
            </p>
            <p v-if="session.lead_phone" class="text-[11px] text-muted-foreground mb-1">{{ session.lead_phone }}</p>
            <div class="flex items-center justify-between mt-2 pt-1.5 border-t border-border">
              <span class="text-[10px] text-muted-foreground">{{ session.message_count || 0 }} msgs</span>
              <span class="text-[10px] text-muted-foreground">{{ timeAgo(session.updated_at || session.created_at) }}</span>
            </div>
          </div>

          <div v-if="!columnSessions(col.key).length" class="flex items-center justify-center rounded-lg border-2 border-dashed border-border py-5">
            <p class="text-[11px] text-muted-foreground">Drop sessions here</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Session detail modal -->
    <div v-if="selectedSession" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" @click.self="selectedSession = null">
      <div class="bg-background border border-border rounded-xl w-full max-w-md max-h-[85vh] flex flex-col shadow-xl">
        <!-- Header -->
        <div class="flex items-start justify-between px-5 py-4 border-b border-border">
          <div>
            <h3 class="text-sm font-semibold text-foreground truncate max-w-56">{{ selectedSession.lead_email || (selectedSession.visitor_id || '').slice(0, 22) + '…' }}</h3>
            <p class="text-xs text-muted-foreground mt-0.5">{{ selectedSession.conversation_state }}</p>
          </div>
          <button class="rounded-md p-1 text-muted-foreground hover:bg-muted transition-colors" @click="selectedSession = null">
            <X class="h-4 w-4" />
          </button>
        </div>

        <!-- Body -->
        <div class="px-5 py-4 overflow-y-auto flex flex-col gap-4">
          <!-- Meta chips -->
          <div class="flex gap-2">
            <div class="flex-1 rounded-lg border border-border bg-muted/30 p-3 text-center">
              <p class="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">Heat</p>
              <p class="text-sm font-bold" :class="heatTextClass(selectedSession.heat_score)">{{ Math.round(selectedSession.heat_score || 0) }}%</p>
            </div>
            <div class="flex-1 rounded-lg border border-border bg-muted/30 p-3 text-center">
              <p class="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">Stage</p>
              <p class="text-sm font-bold text-foreground">{{ selectedSession.kanban_state || 'NEW' }}</p>
            </div>
            <div class="flex-1 rounded-lg border border-border bg-muted/30 p-3 text-center">
              <p class="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">Messages</p>
              <p class="text-sm font-bold text-foreground">{{ selectedSession.message_count || 0 }}</p>
            </div>
          </div>

          <!-- Move to stage -->
          <div>
            <p class="text-xs font-semibold text-muted-foreground mb-2">Move to stage:</p>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="col in columns"
                :key="col.key"
                class="rounded-md border px-2.5 py-1 text-xs font-medium transition-colors"
                :class="(selectedSession.kanban_state || 'NEW') === col.key ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:bg-muted'"
                @click="moveSession(selectedSession, col.key)"
              >{{ col.label }}</button>
            </div>
          </div>

          <!-- Chat preview -->
          <div v-if="loadingSession" class="flex justify-center py-6">
            <Loader2 class="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
          <div v-else-if="sessionDetail?.chat_history?.length" class="flex flex-col gap-2">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Recent Messages</p>
            <div class="flex flex-col gap-2">
              <div
                v-for="(msg, i) in sessionDetail.chat_history.slice(-6)"
                :key="i"
                class="flex flex-col max-w-[88%]"
                :class="msg.role === 'user' ? 'self-end items-end' : 'self-start items-start'"
              >
                <span class="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">{{ msg.role === 'user' ? 'Visitor' : 'AI' }}</span>
                <p class="text-xs leading-relaxed px-3 py-2 rounded-xl m-0" :class="msg.role === 'user' ? 'bg-primary text-primary-foreground rounded-br-sm' : 'bg-muted text-foreground rounded-bl-sm'">
                  {{ msg.message || msg.content }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { RefreshCw, Loader2, X } from 'lucide-vue-next'
import { useAdminApi } from '../composables/useAdminApi'
import Button from '@/components/ui/Button.vue'

const props = defineProps({ client: Object })
const api = useAdminApi()

const sessions = ref([])
const loading = ref(false)
const dragSession = ref(null)
const dragOverCol = ref(null)
const selectedSession = ref(null)
const sessionDetail = ref(null)
const loadingSession = ref(false)

const columns = [
  { key: 'NEW',       label: 'New',       headerBg: 'bg-slate-100' },
  { key: 'ENGAGED',   label: 'Engaged',   headerBg: 'bg-blue-50' },
  { key: 'HOT_LEAD',  label: 'Hot Lead',  headerBg: 'bg-red-50' },
  { key: 'CONVERTED', label: 'Converted', headerBg: 'bg-emerald-50' },
  { key: 'LOST',      label: 'Lost',      headerBg: 'bg-slate-50' },
]

function columnSessions(key) {
  return sessions.value.filter(s => (s.kanban_state || 'NEW') === key)
}

async function loadData() {
  if (!props.client) return
  loading.value = true
  try {
    const data = await api.getPortalSessions(props.client.id, { limit: 200 })
    sessions.value = Array.isArray(data) ? data : (data?.results || [])
  } catch {} finally {
    loading.value = false
  }
}

function onDragStart(e, session) {
  dragSession.value = session
  e.dataTransfer.effectAllowed = 'move'
}

async function onDrop(e, colKey) {
  dragOverCol.value = null
  if (!dragSession.value) return
  const s = dragSession.value
  dragSession.value = null
  if ((s.kanban_state || 'NEW') === colKey) return
  const idx = sessions.value.findIndex(x => x.session_id === s.session_id)
  if (idx >= 0) sessions.value[idx].kanban_state = colKey
  try {
    await api.updateSession(s.session_id, { kanban_state: colKey })
  } catch {
    if (idx >= 0) sessions.value[idx].kanban_state = s.kanban_state
  }
}

async function moveSession(session, colKey) {
  if ((session.kanban_state || 'NEW') === colKey) return
  const idx = sessions.value.findIndex(x => x.session_id === session.session_id)
  if (idx >= 0) sessions.value[idx].kanban_state = colKey
  session.kanban_state = colKey
  try {
    await api.updateSession(session.session_id, { kanban_state: colKey })
  } catch {}
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

function heatBadgeClass(score) {
  if ((score || 0) >= 75) return 'bg-red-100 text-red-600'
  if ((score || 0) >= 40) return 'bg-orange-100 text-orange-600'
  return 'bg-primary/10 text-primary'
}

function heatTextClass(score) {
  if ((score || 0) >= 75) return 'text-red-500'
  if ((score || 0) >= 40) return 'text-orange-500'
  return 'text-primary'
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

function timeAgo(iso) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  return `${Math.floor(m / 60)}h ago`
}

onMounted(loadData)
watch(() => props.client, loadData)
</script>
