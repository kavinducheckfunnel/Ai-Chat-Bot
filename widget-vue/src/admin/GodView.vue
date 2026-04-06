<template>
  <div class="godview">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <button class="back-btn" @click="$router.back()">
          <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M19 12H5M12 5l-7 7 7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          Back
        </button>
        <div>
          <h1 class="page-title">God View</h1>
          <p class="page-sub font-mono">{{ sessionId?.slice(0, 20) }}...</p>
        </div>
      </div>
      <div class="header-right">
        <div class="status-pill" :class="session?.takeover_active ? 'status-takeover' : 'status-ai'">
          <div class="status-dot"></div>
          {{ session?.takeover_active ? 'You are in control' : 'AI is handling' }}
        </div>
        <button v-if="!session?.takeover_active" class="takeover-btn" @click="takeover" :disabled="actionLoading">
          <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/></svg>
          Take Over
        </button>
        <button v-else class="release-btn" @click="release" :disabled="actionLoading">
          <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          Release to AI
        </button>
      </div>
    </div>

    <div class="godview-body">
      <!-- Session Info Sidebar -->
      <div class="info-panel">
        <div class="info-card">
          <h3 class="info-title">Heat Score</h3>
          <div class="heat-display" :class="heatClass(session?.heat_score || 0)">
            {{ session?.heat_score || 0 }}%
          </div>
          <div class="heat-bar-wrap">
            <div class="heat-bar" :style="{ width: (session?.heat_score || 0) + '%', background: heatColor(session?.heat_score || 0) }"></div>
          </div>
        </div>

        <div class="info-card">
          <h3 class="info-title">EMA Scores</h3>
          <div class="ema-row">
            <span class="ema-label">Intent</span>
            <div class="mini-bar-wrap"><div class="mini-bar intent" :style="{ width: ((session?.intent_ema || 0) * 100) + '%' }"></div></div>
            <span class="ema-val">{{ Math.round((session?.intent_ema || 0) * 100) }}%</span>
          </div>
          <div class="ema-row">
            <span class="ema-label">Budget</span>
            <div class="mini-bar-wrap"><div class="mini-bar budget" :style="{ width: ((session?.budget_ema || 0) * 100) + '%' }"></div></div>
            <span class="ema-val">{{ Math.round((session?.budget_ema || 0) * 100) }}%</span>
          </div>
          <div class="ema-row">
            <span class="ema-label">Urgency</span>
            <div class="mini-bar-wrap"><div class="mini-bar urgency" :style="{ width: ((session?.urgency_ema || 0) * 100) + '%' }"></div></div>
            <span class="ema-val">{{ Math.round((session?.urgency_ema || 0) * 100) }}%</span>
          </div>
        </div>

        <div class="info-card">
          <h3 class="info-title">Session Info</h3>
          <div class="meta-row"><span class="meta-label">State</span><span class="state-badge" :class="stateClass(session?.conversation_state)">{{ session?.conversation_state?.replace('_', ' ') }}</span></div>
          <div class="meta-row"><span class="meta-label">Messages</span><span>{{ session?.message_count }}</span></div>
          <div class="meta-row"><span class="meta-label">Email</span><span class="mono">{{ session?.lead_email || '—' }}</span></div>
          <div class="meta-row"><span class="meta-label">Closing</span><span :class="session?.closing_triggered ? 'text-green' : 'text-gray'">{{ session?.closing_triggered ? 'Triggered' : 'Not yet' }}</span></div>
        </div>
      </div>

      <!-- Chat Panel -->
      <div class="chat-panel">
        <div class="chat-history" ref="chatContainer">
          <div v-if="loading" class="loading-center">
            <div class="loader"></div>
          </div>
          <template v-else>
            <div
              v-for="(msg, i) in chatHistory"
              :key="i"
              class="chat-msg"
              :class="[msg.role === 'user' ? 'user-msg' : 'ai-msg', msg.source === 'admin' ? 'admin-injected' : '', msg.source === 'afk_nudge' ? 'nudge-msg' : '']"
            >
              <span class="msg-role">
                {{ msg.role === 'user' ? 'Visitor' : msg.source === 'admin' ? 'You (Admin)' : msg.source === 'afk_nudge' ? 'AFK Nudge' : 'AI' }}
              </span>
              <p class="msg-text">{{ msg.message || msg.content }}</p>
            </div>
            <p v-if="!chatHistory.length" class="no-msgs">No chat history yet.</p>
          </template>
        </div>

        <!-- Admin Input (only when in takeover) -->
        <div v-if="session?.takeover_active" class="admin-input-area">
          <div class="takeover-notice">
            <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/></svg>
            You are controlling this conversation — AI is paused
          </div>
          <!-- Canned responses quick-replies -->
          <div v-if="cannedResponses.length" class="canned-pills">
            <button
              v-for="cr in cannedResponses"
              :key="cr.id"
              class="canned-pill"
              @click="adminMessage = cr.body"
              :title="cr.body"
            >{{ cr.title }}</button>
          </div>
          <div class="input-row">
            <textarea
              v-model="adminMessage"
              class="admin-textarea"
              placeholder="Type a message to the visitor..."
              rows="2"
              @keydown.enter.ctrl="sendAdminMessage"
            ></textarea>
            <button class="send-btn" @click="sendAdminMessage" :disabled="!adminMessage.trim() || sending">
              <svg v-if="!sending" width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              <div v-else class="btn-loader"></div>
            </button>
          </div>
          <p class="input-hint">Ctrl+Enter to send · Click a quick reply above to insert</p>
        </div>
        <div v-else class="ai-active-notice">
          AI is handling this conversation. Click "Take Over" to send messages manually.
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useAdminApi } from '../composables/useAdminApi'

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

async function loadSession() {
  loading.value = true
  try {
    const data = await api.getSession(sessionId)
    session.value = data
    chatHistory.value = data.chat_history || []
    // Load client's canned responses if available
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
  } catch (e) {
    alert(e.message)
  } finally {
    actionLoading.value = false
  }
}

async function release() {
  actionLoading.value = true
  try {
    await api.releaseSession(sessionId)
    session.value = { ...session.value, takeover_active: false }
  } catch (e) {
    alert(e.message)
  } finally {
    actionLoading.value = false
  }
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
  } catch (e) {
    alert(e.message)
  } finally {
    sending.value = false
  }
}

function scrollToBottom() {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

function heatClass(score) {
  if (score >= 70) return 'hot'
  if (score >= 40) return 'warm'
  return 'cool'
}

function heatColor(score) {
  if (score >= 70) return 'linear-gradient(90deg, #EF4444, #F97316)'
  if (score >= 40) return 'linear-gradient(90deg, #F97316, #EAB308)'
  return 'linear-gradient(90deg, #3B82F6, #06B6D4)'
}

function stateClass(state) {
  const map = { RESEARCH: 'state-blue', EVALUATION: 'state-yellow', OBJECTION: 'state-red', RECOVERY: 'state-orange', READY_TO_BUY: 'state-green' }
  return map[state] || 'state-blue'
}

// Poll for new messages every 5s while on this page
let pollInterval = null
onMounted(() => {
  loadSession()
  pollInterval = setInterval(loadSession, 5000)
})
onUnmounted(() => clearInterval(pollInterval))
</script>

<style scoped>
.godview { height: 100%; display: flex; flex-direction: column; }

.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 24px; flex-shrink: 0;
}
.header-left { display: flex; align-items: center; gap: 16px; }
.header-right { display: flex; align-items: center; gap: 10px; }

.back-btn {
  display: flex; align-items: center; gap: 6px;
  background: white; border: 1px solid #E2E8F0; border-radius: 8px;
  padding: 8px 12px; font-size: 13px; font-weight: 500; color: #475569;
  cursor: pointer; transition: all 0.15s; font-family: inherit;
}
.back-btn:hover { background: #F8FAFC; }

.page-title { font-size: 22px; font-weight: 700; color: #0F172A; }
.page-sub { font-size: 12px; color: #94A3B8; font-family: monospace; }

.status-pill {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600;
}
.status-ai { background: #F0FDF4; color: #15803D; }
.status-takeover { background: rgba(239,68,68,0.1); color: #DC2626; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

.takeover-btn {
  display: flex; align-items: center; gap: 6px;
  background: #6366F1; color: white; border: none; border-radius: 8px;
  padding: 8px 14px; font-size: 13px; font-weight: 600; cursor: pointer;
  transition: all 0.15s; font-family: inherit;
}
.takeover-btn:hover:not(:disabled) { background: #4F46E5; }
.takeover-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.release-btn {
  display: flex; align-items: center; gap: 6px;
  background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA;
  border-radius: 8px; padding: 8px 14px; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all 0.15s; font-family: inherit;
}
.release-btn:hover:not(:disabled) { background: #FEE2E2; }

.godview-body { display: flex; gap: 20px; flex: 1; min-height: 0; }

/* Info Panel */
.info-panel { width: 260px; flex-shrink: 0; display: flex; flex-direction: column; gap: 12px; }

.info-card {
  background: white; border: 1px solid #F1F5F9; border-radius: 14px; padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.info-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #94A3B8; margin-bottom: 12px; }

.heat-display {
  font-size: 36px; font-weight: 800; letter-spacing: -1px; margin-bottom: 8px;
}
.heat-display.hot { color: #DC2626; }
.heat-display.warm { color: #EA580C; }
.heat-display.cool { color: #2563EB; }

.heat-bar-wrap { background: #F1F5F9; border-radius: 4px; height: 6px; overflow: hidden; }
.heat-bar { height: 100%; border-radius: 4px; transition: width 0.5s; }

.ema-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.ema-label { font-size: 11px; color: #94A3B8; width: 42px; flex-shrink: 0; }
.mini-bar-wrap { flex: 1; background: #F1F5F9; border-radius: 3px; height: 5px; overflow: hidden; }
.mini-bar { height: 100%; border-radius: 3px; }
.intent { background: #6366F1; }
.budget { background: #22C55E; }
.urgency { background: #F97316; }
.ema-val { font-size: 11px; font-weight: 600; color: #475569; width: 28px; text-align: right; }

.meta-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #F8FAFC; font-size: 12px; }
.meta-row:last-child { border-bottom: none; }
.meta-label { color: #94A3B8; }
.mono { font-family: monospace; font-size: 11px; }
.text-green { color: #16A34A; font-weight: 600; }
.text-gray { color: #94A3B8; }

.state-badge { font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 20px; }
.state-blue { background: #EFF6FF; color: #1D4ED8; }
.state-yellow { background: #FFFBEB; color: #B45309; }
.state-red { background: #FEF2F2; color: #B91C1C; }
.state-orange { background: #FFF7ED; color: #C2410C; }
.state-green { background: #F0FDF4; color: #15803D; }

/* Chat Panel */
.chat-panel {
  flex: 1; background: white; border: 1px solid #F1F5F9; border-radius: 14px;
  display: flex; flex-direction: column; overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04); min-height: 0;
}

.chat-history { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 14px; }

.loading-center { display: flex; justify-content: center; padding: 40px; }

.chat-msg { max-width: 75%; }
.user-msg { align-self: flex-end; }
.ai-msg { align-self: flex-start; }

.msg-role { font-size: 10px; font-weight: 700; color: #94A3B8; margin-bottom: 4px; display: block; letter-spacing: 0.04em; }
.user-msg .msg-role { text-align: right; }
.admin-injected .msg-role { color: #6366F1; }
.nudge-msg .msg-role { color: #F97316; }

.msg-text { font-size: 13px; line-height: 1.55; padding: 10px 14px; border-radius: 12px; }
.user-msg .msg-text { background: #EFF6FF; color: #1E3A8A; border-bottom-right-radius: 4px; }
.ai-msg .msg-text { background: #F8FAFC; color: #334155; border: 1px solid #E2E8F0; border-bottom-left-radius: 4px; }
.admin-injected .msg-text { background: rgba(99,102,241,0.08); border-color: rgba(99,102,241,0.2); color: #312E81; }
.nudge-msg .msg-text { background: rgba(249,115,22,0.08); border-color: rgba(249,115,22,0.2); color: #7C2D12; }

.no-msgs { text-align: center; color: #94A3B8; font-size: 13px; padding: 40px; }

/* Admin Input */
.admin-input-area { border-top: 1px solid #F1F5F9; padding: 16px; background: #FAFBFF; }

.takeover-notice {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; font-weight: 600; color: #DC2626;
  margin-bottom: 10px; background: #FEF2F2; padding: 6px 10px; border-radius: 6px;
}

.input-row { display: flex; gap: 8px; }

.admin-textarea {
  flex: 1; padding: 10px 12px; border: 1px solid #E2E8F0; border-radius: 10px;
  font-size: 13px; font-family: inherit; resize: none; outline: none;
  transition: border-color 0.15s; background: white;
}
.admin-textarea:focus { border-color: #6366F1; }

.send-btn {
  width: 44px; flex-shrink: 0; background: #6366F1; color: white; border: none;
  border-radius: 10px; cursor: pointer; display: flex; align-items: center;
  justify-content: center; transition: all 0.15s;
}
.send-btn:hover:not(:disabled) { background: #4F46E5; }
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.input-hint { font-size: 10px; color: #CBD5E1; margin-top: 6px; }
.canned-pills { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.canned-pill { padding: 5px 12px; background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.2); border-radius: 20px; font-size: 12px; color: #6366f1; cursor: pointer; transition: all 0.12s; white-space: nowrap; max-width: 180px; overflow: hidden; text-overflow: ellipsis; }
.canned-pill:hover { background: rgba(99,102,241,0.18); }

.ai-active-notice {
  border-top: 1px solid #F1F5F9; padding: 14px 20px;
  font-size: 12px; color: #94A3B8; text-align: center;
}

.loader { width: 24px; height: 24px; border: 2px solid #E2E8F0; border-top-color: #6366F1; border-radius: 50%; animation: spin 0.8s linear infinite; }
.btn-loader { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: white; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
