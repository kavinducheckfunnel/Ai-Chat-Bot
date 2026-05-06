<template>
  <div class="flex flex-col h-full gap-6 p-6">

    <!-- Header -->
    <div class="flex items-center justify-between gap-4 shrink-0">
      <div class="flex items-center gap-4">
        <button class="flex items-center gap-1.5 h-9 px-3 rounded-xl border border-border bg-background text-muted-foreground hover:bg-muted text-sm font-medium transition-colors" @click="$router.back()">
          <ArrowLeft class="h-4 w-4" /> Back
        </button>
        <div>
          <h1 class="text-xl font-semibold text-foreground">God View</h1>
          <p class="text-xs text-muted-foreground font-mono">{{ sessionId?.slice(0, 20) }}…</p>
        </div>
      </div>
      <div class="flex items-center gap-2.5">
        <div v-if="session?.channel && session.channel !== 'website'" class="flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold" :class="channelClass(session.channel)">
          {{ channelLabel(session.channel) }}
        </div>
        <div class="flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold" :class="session?.takeover_active ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'">
          <span class="h-1.5 w-1.5 rounded-full bg-current animate-pulse"></span>
          {{ session?.takeover_active ? 'You are in control' : 'AI is handling' }}
        </div>
        <Button v-if="!session?.takeover_active" size="sm" @click="takeover" :disabled="actionLoading" class="gap-2">
          <Eye class="h-3.5 w-3.5" /> Take Over
        </Button>
        <Button v-else variant="outline" size="sm" @click="release" :disabled="actionLoading" class="gap-2 border-red-200 bg-red-50 text-red-600 hover:bg-red-100">
          <LogOut class="h-3.5 w-3.5" /> Release to AI
        </Button>
      </div>
    </div>

    <!-- Body -->
    <div class="flex gap-5 flex-1 min-h-0">

      <!-- Info sidebar -->
      <div class="w-60 shrink-0 flex flex-col gap-3 overflow-y-auto">

        <!-- Heat score -->
        <Card>
          <CardContent class="pt-4 pb-4">
            <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-3">Heat Score</p>
            <p class="text-4xl font-black tracking-tighter mb-2" :class="heatTextClass(session?.heat_score || 0)">{{ session?.heat_score || 0 }}%</p>
            <div class="h-1.5 rounded-full bg-muted overflow-hidden">
              <div class="h-full rounded-full transition-[width]" :style="{ width: (session?.heat_score || 0) + '%', background: heatColor(session?.heat_score || 0) }"></div>
            </div>
          </CardContent>
        </Card>

        <!-- EMA scores -->
        <Card>
          <CardContent class="pt-4 pb-4">
            <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-3">EMA Scores</p>
            <div class="flex flex-col gap-2.5">
              <div v-for="ema in emaRows" :key="ema.label" class="flex items-center gap-2">
                <span class="text-[11px] text-muted-foreground w-10 shrink-0">{{ ema.label }}</span>
                <div class="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                  <div class="h-full rounded-full" :style="{ width: ema.value + '%', background: ema.color }"></div>
                </div>
                <span class="text-[11px] font-semibold text-foreground w-7 text-right">{{ ema.value }}%</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- Session info -->
        <Card>
          <CardContent class="pt-4 pb-4">
            <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-3">Session Info</p>
            <div class="flex flex-col divide-y divide-border">
              <div class="flex justify-between items-center py-2 text-xs">
                <span class="text-muted-foreground">State</span>
                <span class="inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold" :class="stateClass(session?.conversation_state)">{{ session?.conversation_state?.replace('_', ' ') }}</span>
              </div>
              <div class="flex justify-between items-center py-2 text-xs">
                <span class="text-muted-foreground">Messages</span>
                <span class="font-semibold text-foreground">{{ session?.message_count }}</span>
              </div>
              <div class="flex justify-between items-center py-2 text-xs">
                <span class="text-muted-foreground">Email</span>
                <span class="font-mono text-[11px] text-foreground truncate max-w-[100px]">{{ session?.lead_email || '—' }}</span>
              </div>
              <div class="flex justify-between items-center py-2 text-xs">
                <span class="text-muted-foreground">Closing</span>
                <span :class="session?.closing_triggered ? 'text-emerald-600 font-semibold' : 'text-muted-foreground'">{{ session?.closing_triggered ? 'Triggered' : 'Not yet' }}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <!-- Chat panel -->
      <div class="flex-1 flex flex-col rounded-xl border border-border bg-background overflow-hidden min-h-0">

        <!-- Chat history -->
        <div class="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-3.5" ref="chatContainer">
          <div v-if="loading" class="flex justify-center py-10">
            <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
          <template v-else>
            <div
              v-for="(msg, i) in chatHistory"
              :key="i"
              class="flex flex-col max-w-[75%]"
              :class="msg.role === 'user' ? 'self-end items-end' : 'self-start items-start'"
            >
              <span class="text-[10px] font-bold uppercase tracking-wider mb-1" :class="msgRoleClass(msg)">
                {{ msgRoleLabel(msg) }}
              </span>
              <p class="text-sm leading-relaxed px-3.5 py-2.5 rounded-xl m-0" :class="msgBubbleClass(msg)">
                {{ msg.message || msg.content }}
              </p>
            </div>
            <p v-if="!chatHistory.length" class="text-sm text-muted-foreground text-center py-10">No chat history yet.</p>
          </template>
        </div>

        <!-- Admin input (takeover active) -->
        <div v-if="session?.takeover_active" class="border-t border-border bg-muted/20 p-4 flex flex-col gap-2.5">
          <div class="flex items-center gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs font-semibold text-red-600">
            <Eye class="h-3.5 w-3.5 shrink-0" />
            You are controlling this conversation — AI is paused
          </div>
          <div v-if="cannedResponses.length" class="flex flex-wrap gap-1.5">
            <button
              v-for="cr in cannedResponses" :key="cr.id"
              class="rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs text-primary hover:bg-primary/20 transition-colors whitespace-nowrap max-w-[180px] overflow-hidden text-ellipsis"
              @click="adminMessage = cr.body"
              :title="cr.body"
            >{{ cr.title }}</button>
          </div>
          <div class="flex gap-2">
            <textarea
              v-model="adminMessage"
              class="flex-1 resize-none rounded-xl border border-border bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              style="font-family: inherit;"
              placeholder="Type a message to the visitor…"
              rows="2"
              @keydown.enter.ctrl="sendAdminMessage"
            ></textarea>
            <button
              class="w-11 shrink-0 rounded-xl bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              @click="sendAdminMessage"
              :disabled="!adminMessage.trim() || sending"
            >
              <Loader2 v-if="sending" class="h-4 w-4 animate-spin" />
              <Send v-else class="h-4 w-4" />
            </button>
          </div>
          <p class="text-[10px] text-muted-foreground">Ctrl+Enter to send · Click a quick reply above to insert</p>
        </div>

        <!-- AI active notice -->
        <div v-else class="border-t border-border px-5 py-3.5 text-xs text-muted-foreground text-center">
          AI is handling this conversation. Click "Take Over" to send messages manually.
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useAdminApi } from '../composables/useAdminApi'
import { ArrowLeft, Eye, LogOut, Loader2, Send } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'

const route = useRoute()
const api = useAdminApi()

const sessionId = route.params.id
const session = ref(null)
const chatHistory = ref([])
const loading = ref(true)
const actionLoading = ref(false)
const adminMessage = ref('')
const sending = ref(false)
const chatContainer = ref(null)
const cannedResponses = ref([])

const emaRows = computed(() => [
  { label: 'Intent', value: Math.round((session.value?.intent_ema  || 0) * 100), color: '#6366F1' },
  { label: 'Budget', value: Math.round((session.value?.budget_ema  || 0) * 100), color: '#22C55E' },
  { label: 'Urgency',value: Math.round((session.value?.urgency_ema || 0) * 100), color: '#F97316' },
])

async function loadSession() {
  loading.value = true
  try {
    const data = await api.getSession(sessionId)
    session.value = data
    chatHistory.value = data.chat_history || []
    if (data.client_id) {
      try {
        const client = await api.getClient(data.client_id)
        cannedResponses.value = client.canned_responses || []
      } catch {}
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
    await nextTick()
    scrollToBottom()
  }
}

async function takeover() {
  actionLoading.value = true
  try {
    await api.takeoverSession(sessionId)
    session.value = { ...session.value, takeover_active: true }
  } catch (e) { alert(e.message) } finally { actionLoading.value = false }
}

async function release() {
  actionLoading.value = true
  try {
    await api.releaseSession(sessionId)
    session.value = { ...session.value, takeover_active: false }
  } catch (e) { alert(e.message) } finally { actionLoading.value = false }
}

async function sendAdminMessage() {
  const msg = adminMessage.value.trim()
  if (!msg || sending.value) return
  sending.value = true
  try {
    await api.sendMessage(sessionId, msg)
    chatHistory.value.push({ role: 'ai', message: msg, source: 'admin' })
    adminMessage.value = ''
    await nextTick()
    scrollToBottom()
  } catch (e) { alert(e.message) } finally { sending.value = false }
}

function scrollToBottom() {
  if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight
}

function heatTextClass(score) {
  if (score >= 70) return 'text-red-500'
  if (score >= 40) return 'text-orange-500'
  return 'text-primary'
}

function heatColor(score) {
  if (score >= 70) return 'linear-gradient(90deg,#EF4444,#F97316)'
  if (score >= 40) return 'linear-gradient(90deg,#F97316,#EAB308)'
  return 'linear-gradient(90deg,#3B82F6,#06B6D4)'
}

function stateClass(state) {
  const map = { RESEARCH: 'bg-blue-50 text-blue-700', EVALUATION: 'bg-yellow-50 text-yellow-700', OBJECTION: 'bg-red-50 text-red-700', RECOVERY: 'bg-orange-50 text-orange-700', READY_TO_BUY: 'bg-emerald-50 text-emerald-700' }
  return map[state] || 'bg-blue-50 text-blue-700'
}

function channelLabel(ch) {
  return { whatsapp: '💬 WhatsApp', messenger: '💙 Messenger', telegram: '✈️ Telegram' }[ch] || ch
}

function channelClass(ch) {
  const map = { whatsapp: 'border-green-300 bg-green-50 text-green-700', messenger: 'border-blue-300 bg-blue-50 text-blue-700', telegram: 'border-sky-300 bg-sky-50 text-sky-700' }
  return map[ch] || 'border-border bg-muted text-muted-foreground'
}

function msgRoleClass(msg) {
  if (msg.source === 'admin')    return 'text-primary'
  if (msg.source === 'afk_nudge') return 'text-orange-500'
  return 'text-muted-foreground'
}

function msgRoleLabel(msg) {
  if (msg.role === 'user')       return 'Visitor'
  if (msg.source === 'admin')    return 'You (Admin)'
  if (msg.source === 'afk_nudge') return 'AFK Nudge'
  return 'AI'
}

function msgBubbleClass(msg) {
  if (msg.role === 'user')        return 'bg-primary text-primary-foreground rounded-br-sm'
  if (msg.source === 'admin')     return 'bg-primary/10 border border-primary/20 text-primary rounded-bl-sm'
  if (msg.source === 'afk_nudge') return 'bg-orange-50 border border-orange-200 text-orange-900 rounded-bl-sm'
  return 'bg-muted text-foreground rounded-bl-sm'
}

let pollInterval = null
onMounted(() => {
  loadSession()
  pollInterval = setInterval(loadSession, 5000)
})
onUnmounted(() => clearInterval(pollInterval))
</script>
