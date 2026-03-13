<template>
  <AdminLayout>
    <div class="god-view">
      <div class="gv-header">
        <button @click="$router.back()" class="back-btn">← Back</button>
        <div>
          <h1>God View</h1>
          <p>Session: {{ sessionId?.slice(0, 16) }}...</p>
        </div>
        <div class="header-actions">
          <div class="heat-display" :class="heatClass">🔥 {{ sessionMeta.heat_score }}</div>
          <button
            v-if="!takeover"
            @click="startTakeover"
            class="btn btn-takeover"
          >Take Over</button>
          <button
            v-else
            @click="endTakeover"
            class="btn btn-release"
          >Release to AI</button>
        </div>
      </div>

      <div class="gv-body">
        <!-- Chat history -->
        <div class="chat-panel">
          <div class="chat-messages" ref="chatBox">
            <div
              v-for="(msg, i) in messages"
              :key="i"
              class="msg-row"
              :class="msg.sender"
            >
              <div class="bubble" :class="{ 'admin-injected': msg.admin_injected }">
                <span class="sender-label">{{ msg.sender === 'user' ? 'Visitor' : (msg.admin_injected ? 'You (Admin)' : 'AI') }}</span>
                <p>{{ msg.message }}</p>
              </div>
            </div>
          </div>
          <div v-if="takeover" class="admin-input-row">
            <input
              v-model="adminInput"
              @keydown.enter="sendAdminMsg"
              placeholder="Type a message as AI..."
              class="admin-input"
            />
            <button @click="sendAdminMsg" class="btn btn-send">Send</button>
          </div>
          <div v-else class="takeover-hint">
            Click "Take Over" to reply manually as the AI.
          </div>
        </div>

        <!-- Session meta panel -->
        <div class="meta-panel">
          <h3>Session Info</h3>
          <div class="meta-row"><span>State</span><span class="state-badge">{{ sessionMeta.conversation_state }}</span></div>
          <div class="meta-row"><span>Messages</span><strong>{{ sessionMeta.message_count }}</strong></div>
          <div class="meta-row"><span>Visitor ID</span><code>{{ sessionMeta.visitor_id?.slice(0,12) }}</code></div>

          <h3 style="margin-top:24px">Scores</h3>
          <div class="score-item">
            <div class="score-label">Intent <strong>{{ pct(sessionMeta.intent_ema) }}%</strong></div>
            <div class="score-track"><div class="score-fill intent" :style="{ width: pct(sessionMeta.intent_ema) + '%' }"></div></div>
          </div>
          <div class="score-item">
            <div class="score-label">Budget <strong>{{ pct(sessionMeta.budget_ema) }}%</strong></div>
            <div class="score-track"><div class="score-fill budget" :style="{ width: pct(sessionMeta.budget_ema) + '%' }"></div></div>
          </div>
          <div class="score-item">
            <div class="score-label">Urgency <strong>{{ pct(sessionMeta.urgency_ema) }}%</strong></div>
            <div class="score-track"><div class="score-fill urgency" :style="{ width: pct(sessionMeta.urgency_ema) + '%' }"></div></div>
          </div>

          <h3 style="margin-top:24px">Heat Score</h3>
          <div class="big-heat" :class="heatClass">{{ sessionMeta.heat_score }}</div>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import AdminLayout from './AdminLayout.vue'
import { useAdminApi } from '../composables/useAdminApi.js'

const route = useRoute()
const sessionId = route.params.sessionId
const { takeoverSession, releaseSession, sendAdminMessage, getToken, API_BASE } = useAdminApi()

const messages = ref([])
const takeover = ref(false)
const adminInput = ref('')
const chatBox = ref(null)
const sessionMeta = ref({ heat_score: 0, conversation_state: 'RESEARCH', message_count: 0 })

let socket = null

const heatClass = computed(() => {
  const h = sessionMeta.value.heat_score
  if (h >= 70) return 'hot'
  if (h >= 40) return 'warm'
  return 'cool'
})

const pct = (v) => v ? Math.round(v * 100) : 0

function scrollToBottom() {
  nextTick(() => {
    if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
  })
}

watch(messages, scrollToBottom, { deep: true })

function connectGodView() {
  const wsBase = API_BASE.replace('http://', 'ws://').replace('https://', 'wss://')
  const token = getToken()
  socket = new WebSocket(`${wsBase}/ws/admin/sessions/${sessionId}/?token=${token}`)

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'history') {
      messages.value = (data.messages || []).map(m => ({
        sender: m.role === 'user' ? 'user' : 'ai',
        message: m.message,
        admin_injected: false,
      }))
    } else if (data.type === 'chat_message') {
      messages.value.push({
        sender: data.sender,
        message: data.message,
        admin_injected: data.admin_injected || false,
      })
    } else if (data.type === 'session_update') {
      sessionMeta.value = { ...sessionMeta.value, ...data }
    }
  }
  socket.onclose = () => setTimeout(connectGodView, 3000)
}

async function startTakeover() {
  await takeoverSession(sessionId)
  takeover.value = true
}

async function endTakeover() {
  await releaseSession(sessionId)
  takeover.value = false
}

async function sendAdminMsg() {
  const msg = adminInput.value.trim()
  if (!msg) return
  adminInput.value = ''
  await sendAdminMessage(sessionId, msg)
  // The WS echo will add it to messages
}

onMounted(connectGodView)
onUnmounted(() => socket?.close())
</script>

<style scoped>
.god-view { height: calc(100vh - 80px); display: flex; flex-direction: column; }
.gv-header {
  display: flex; align-items: center; gap: 16px; margin-bottom: 24px;
}
.gv-header > div:nth-child(2) { flex: 1; }
.gv-header h1 { font-size: 1.5rem; font-weight: 700; }
.gv-header p { color: #64748b; font-size: 0.875rem; }
.back-btn { background: #f1f5f9; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-weight: 500; }
.header-actions { display: flex; align-items: center; gap: 12px; }
.heat-display { font-size: 1.125rem; font-weight: 700; padding: 8px 16px; border-radius: 8px; }
.heat-display.hot { background: #fee2e2; color: #991b1b; }
.heat-display.warm { background: #fef3c7; color: #92400e; }
.heat-display.cool { background: #dbeafe; color: #1e40af; }

.btn { padding: 10px 20px; border-radius: 8px; border: none; cursor: pointer; font-weight: 600; font-size: 0.9375rem; }
.btn-takeover { background: #2563eb; color: white; }
.btn-release { background: #ef4444; color: white; }
.btn-send { background: #2563eb; color: white; }

.gv-body { display: grid; grid-template-columns: 1fr 320px; gap: 24px; flex: 1; min-height: 0; }
.chat-panel { display: flex; flex-direction: column; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.chat-messages { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; }

.msg-row { display: flex; }
.msg-row.user { justify-content: flex-end; }
.msg-row.ai { justify-content: flex-start; }

.bubble { max-width: 70%; padding: 10px 14px; border-radius: 12px; }
.msg-row.user .bubble { background: #dbeafe; border-radius: 12px 12px 2px 12px; }
.msg-row.ai .bubble { background: #f1f5f9; border-radius: 12px 12px 12px 2px; }
.bubble.admin-injected { background: #dcfce7; }
.sender-label { font-size: 0.6875rem; font-weight: 700; color: #94a3b8; display: block; margin-bottom: 4px; text-transform: uppercase; }
.bubble p { font-size: 0.9375rem; line-height: 1.5; }

.admin-input-row { display: flex; padding: 12px 16px; gap: 8px; border-top: 1px solid #e2e8f0; }
.admin-input { flex: 1; padding: 10px 14px; border: 1.5px solid #e2e8f0; border-radius: 8px; outline: none; font-size: 0.9375rem; }
.admin-input:focus { border-color: #2563eb; }
.takeover-hint { padding: 12px 16px; text-align: center; color: #94a3b8; font-size: 0.875rem; border-top: 1px solid #f1f5f9; }

.meta-panel { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); overflow-y: auto; }
.meta-panel h3 { font-size: 0.875rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; }
.meta-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f8fafc; font-size: 0.875rem; color: #64748b; }
.meta-row strong, .meta-row code { color: #0f172a; }
.state-badge { background: #f1f5f9; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; color: #475569; }

.score-item { margin-bottom: 12px; }
.score-label { display: flex; justify-content: space-between; font-size: 0.8125rem; color: #64748b; margin-bottom: 4px; }
.score-track { background: #f1f5f9; border-radius: 4px; height: 8px; overflow: hidden; }
.score-fill { height: 100%; border-radius: 4px; transition: width 0.5s; }
.score-fill.intent { background: #6366f1; }
.score-fill.budget { background: #10b981; }
.score-fill.urgency { background: #f59e0b; }

.big-heat { font-size: 3rem; font-weight: 800; text-align: center; padding: 16px; border-radius: 12px; }
.big-heat.hot { background: #fee2e2; color: #991b1b; }
.big-heat.warm { background: #fef3c7; color: #92400e; }
.big-heat.cool { background: #dbeafe; color: #1e40af; }
</style>
