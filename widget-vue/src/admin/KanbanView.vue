<template>
  <div class="flex flex-col h-full p-6 gap-6">

    <!-- Header -->
    <div class="flex items-start justify-between">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Lead Kanban</h1>
        <p class="text-sm text-muted-foreground mt-1">Drag sessions to update their pipeline stage</p>
      </div>
      <Button variant="outline" size="sm" @click="loadData" :disabled="loading">
        <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': loading }" />
        Refresh
      </Button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex flex-col items-center gap-3 py-20 text-muted-foreground">
      <Loader2 class="h-8 w-8 animate-spin text-primary" />
      <p class="text-sm">Loading sessions…</p>
    </div>

    <!-- Board -->
    <div v-else class="flex gap-3 flex-1 overflow-x-auto pb-2">
      <div
        v-for="col in columns"
        :key="col.key"
        class="flex-none w-56 flex flex-col rounded-xl border-2 transition-colors duration-150"
        :class="dragOverCol === col.key ? 'border-primary bg-primary/5' : 'border-transparent bg-muted/50'"
        @dragover.prevent
        @drop="onDrop($event, col.key)"
        @dragenter="dragOverCol = col.key"
        @dragleave="dragOverCol = null"
      >
        <!-- Column header -->
        <div class="flex items-center justify-between rounded-t-xl px-3 py-2.5" :class="col.headerBg">
          <span class="text-xs font-bold text-foreground">{{ col.label }}</span>
          <span class="rounded-full bg-background/80 px-2 py-0.5 text-[11px] font-bold text-muted-foreground">
            {{ columnSessions(col.key).length }}
          </span>
        </div>

        <!-- Cards -->
        <div class="flex flex-1 flex-col gap-2 overflow-y-auto p-2">
          <div
            v-for="session in columnSessions(col.key)"
            :key="session.session_id"
            class="group cursor-grab rounded-lg border border-border bg-background p-3 shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5 active:cursor-grabbing"
            draggable="true"
            @dragstart="onDragStart($event, session)"
            @dragend="dragOverCol = null"
            @click="openSession(session)"
          >
            <!-- Heat + Live badge -->
            <div class="flex items-center justify-between mb-2">
              <span
                class="inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 text-[10px] font-bold"
                :class="{
                  'bg-red-100 text-red-700': session.heat_score >= 70,
                  'bg-orange-100 text-orange-700': session.heat_score >= 40 && session.heat_score < 70,
                  'bg-blue-100 text-blue-700': session.heat_score < 40,
                }"
              >
                {{ heatEmoji(session.heat_score) }} {{ session.heat_score }}%
              </span>
              <span v-if="session.takeover_active" class="rounded text-[10px] font-bold px-1.5 py-0.5 bg-red-100 text-red-600 animate-pulse">Live</span>
            </div>

            <!-- Heat bar -->
            <div class="mb-2.5 h-1 w-full rounded-full bg-muted overflow-hidden">
              <div class="h-full rounded-full" :style="{ width: session.heat_score + '%', background: heatColor(session.heat_score) }" />
            </div>

            <!-- Info -->
            <p class="truncate text-xs font-semibold text-foreground">{{ session.client_name }}</p>
            <p class="text-[10px] font-mono text-muted-foreground mt-0.5">{{ session.visitor_id?.slice(0, 14) }}…</p>
            <p v-if="session.lead_email" class="truncate text-[11px] text-primary mt-0.5">{{ session.lead_email }}</p>

            <!-- Footer -->
            <div class="mt-2 flex items-center justify-between border-t border-border pt-2">
              <span class="text-[10px] text-muted-foreground">{{ session.message_count }} msgs</span>
              <span class="text-[10px] text-muted-foreground">{{ timeAgo(session.updated_at) }}</span>
            </div>
          </div>

          <!-- Empty drop zone -->
          <div v-if="!columnSessions(col.key).length" class="flex items-center justify-center rounded-lg border-2 border-dashed border-border py-5 text-xs text-muted-foreground">
            Drop here
          </div>
        </div>
      </div>
    </div>

    <!-- Session detail dialog -->
    <Dialog :open="!!selectedSession" @close="selectedSession = null">
      <template v-if="selectedSession">
        <DialogHeader>
          <DialogTitle>{{ selectedSession.visitor_id?.slice(0, 20) }}…</DialogTitle>
          <p class="text-sm text-muted-foreground">{{ selectedSession.client_name }}</p>
        </DialogHeader>
        <div class="px-6 pb-6 space-y-5">
          <!-- Meta chips -->
          <div class="flex gap-3">
            <div class="flex-1 rounded-lg bg-muted p-3 text-center">
              <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Heat</p>
              <p class="text-lg font-bold text-foreground mt-1">{{ selectedSession.heat_score }}%</p>
            </div>
            <div class="flex-1 rounded-lg bg-muted p-3 text-center">
              <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">State</p>
              <p class="text-lg font-bold text-foreground mt-1">{{ selectedSession.conversation_state }}</p>
            </div>
            <div class="flex-1 rounded-lg bg-muted p-3 text-center">
              <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Messages</p>
              <p class="text-lg font-bold text-foreground mt-1">{{ selectedSession.message_count }}</p>
            </div>
          </div>
          <!-- Move stage -->
          <div>
            <p class="text-xs font-semibold text-muted-foreground mb-2">Move to stage:</p>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="col in columns"
                :key="col.key"
                class="rounded-md px-3 py-1.5 text-xs font-medium transition-colors border"
                :class="selectedSession.kanban_state === col.key
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-muted text-muted-foreground border-border hover:bg-accent'"
                @click="moveSession(selectedSession, col.key)"
              >
                {{ col.label }}
              </button>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" @click="goGodView(selectedSession)">
            <Eye class="h-4 w-4" />
            God View
          </Button>
          <Button variant="ghost" size="sm" @click="selectedSession = null">Close</Button>
        </DialogFooter>
      </template>
    </Dialog>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { RefreshCw, Loader2, Eye } from 'lucide-vue-next'
import { useAdminApi } from '../composables/useAdminApi'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import DialogHeader from '@/components/ui/DialogHeader.vue'
import DialogTitle from '@/components/ui/DialogTitle.vue'
import DialogFooter from '@/components/ui/DialogFooter.vue'

const api = useAdminApi()
const router = useRouter()
const sessions = ref([])
const loading = ref(false)
const dragSession = ref(null)
const dragOverCol = ref(null)
const selectedSession = ref(null)

const columns = [
  { key: 'NEW',       label: 'New',       headerBg: 'bg-slate-100' },
  { key: 'ENGAGED',   label: 'Engaged',   headerBg: 'bg-blue-50' },
  { key: 'HOT_LEAD',  label: 'Hot Lead',  headerBg: 'bg-red-50' },
  { key: 'CONVERTED', label: 'Converted', headerBg: 'bg-green-50' },
  { key: 'LOST',      label: 'Lost',      headerBg: 'bg-slate-100' },
]

function columnSessions(key) {
  return sessions.value.filter(s => (s.kanban_state || 'NEW') === key)
}

async function loadData() {
  loading.value = true
  try {
    sessions.value = await api.getKanban() || []
  } catch (e) {
    console.error(e)
  } finally {
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
  if (s.kanban_state === colKey) return
  const idx = sessions.value.findIndex(x => x.session_id === s.session_id)
  if (idx >= 0) sessions.value[idx].kanban_state = colKey
  try {
    await api.updateSession(s.session_id, { kanban_state: colKey })
  } catch {
    if (idx >= 0) sessions.value[idx].kanban_state = s.kanban_state
  }
}

async function moveSession(session, colKey) {
  if (session.kanban_state === colKey) return
  const idx = sessions.value.findIndex(x => x.session_id === session.session_id)
  if (idx >= 0) sessions.value[idx].kanban_state = colKey
  session.kanban_state = colKey
  try {
    await api.updateSession(session.session_id, { kanban_state: colKey })
  } catch {}
}

function openSession(s) { selectedSession.value = s }

function goGodView(s) {
  selectedSession.value = null
  router.push(`/admin/godview/${s.session_id}`)
}

function heatEmoji(score) {
  if (score >= 70) return '🔥'
  if (score >= 40) return '🟠'
  return '🔵'
}

function heatColor(score) {
  if (score >= 70) return 'linear-gradient(90deg,#EF4444,#F97316)'
  if (score >= 40) return 'linear-gradient(90deg,#F97316,#EAB308)'
  return 'linear-gradient(90deg,#3B82F6,#06B6D4)'
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
</script>
