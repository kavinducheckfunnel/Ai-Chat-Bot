<template>
  <div id="cf-chat-container">
    <!-- ── Chat Window ─────────────────────────────────────────────────── -->
    <div id="cf-chat-window" v-show="isOpen">
      <!-- Header -->
      <div id="cf-chat-header">
        <div class="header-info">
          <div class="header-avatar" :style="{ background: branding.chatbot_color || '#6366f1' }">
            <img v-if="branding.chatbot_logo_url" :src="branding.chatbot_logo_url" class="header-logo-img" alt="logo" />
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="white">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
            </svg>
          </div>
          <div class="header-text">
            <span class="header-name">{{ branding.chatbot_name || 'AI Assistant' }}</span>
            <span class="header-status"><span class="status-dot"></span>Online</span>
          </div>
        </div>
        <button id="cf-close-btn" @click="toggleWindow" aria-label="Close chat">
          <svg width="16" height="16" fill="none" viewBox="0 0 24 24">
            <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
          </svg>
        </button>
      </div>

      <!-- Messages -->
      <div id="cf-chat-messages" ref="messagesContainer">
        <div
          v-for="(msg, index) in chatMessages"
          :key="index"
          :class="['cf-msg', msg.sender === 'user' ? 'cf-msg-user' : 'cf-msg-ai']"
          :style="msg.sender === 'user' ? { background: branding.chatbot_color || '#6366f1' } : {}"
        >
          <template v-if="msg.type === 'text'">
            <div v-if="msg.sender === 'ai'" v-html="renderMarkdown(msg.text)" class="markdown-body"></div>
            <div v-else>{{ msg.text }}</div>
            <!-- Emoji reactions (AI messages only) -->
            <div v-if="msg.sender === 'ai' && msg.text" class="msg-reactions">
              <button
                class="reaction-btn"
                :class="{ active: msg.reaction === '👍' }"
                @click="react(index, '👍')"
                title="Helpful"
              >👍</button>
              <button
                class="reaction-btn"
                :class="{ active: msg.reaction === '👎' }"
                @click="react(index, '👎')"
                title="Not helpful"
              >👎</button>
            </div>
          </template>
          <template v-else-if="msg.type === 'image'">
            <img :src="msg.src" class="chat-image" alt="Sent image" />
          </template>
          <template v-else-if="msg.type === 'typing'">
            <div class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </template>
        </div>
      </div>

      <!-- Image preview strip -->
      <div v-if="pendingImage" class="image-preview-bar">
        <div class="image-preview-wrap">
          <img :src="pendingImage" class="preview-thumb" alt="" />
          <button class="preview-remove" @click="clearPendingImage">
            <svg width="10" height="10" fill="none" viewBox="0 0 24 24">
              <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- Input area -->
      <div id="cf-chat-input-area">
        <input
          v-if="branding.image_input_enabled"
          ref="fileInput"
          type="file"
          accept="image/*"
          style="display:none"
          @change="handleFileSelect"
        />
        <button
          v-if="branding.image_input_enabled"
          class="media-btn"
          @click="fileInput.click()"
          title="Attach image"
          aria-label="Attach image"
        >
          <svg width="17" height="17" fill="none" viewBox="0 0 24 24">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <button
          v-if="branding.voice_input_enabled"
          class="media-btn"
          :class="{ recording: isRecording }"
          @click="toggleVoice"
          title="Voice input"
          aria-label="Voice input"
        >
          <svg width="17" height="17" fill="none" viewBox="0 0 24 24">
            <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <!-- TTS speaker toggle — only when voice_input_enabled -->
        <button
          v-if="branding.voice_input_enabled"
          class="media-btn"
          :class="{ 'tts-active': ttsEnabled }"
          @click="ttsEnabled = !ttsEnabled"
          :title="ttsEnabled ? 'Mute AI voice' : 'Enable AI voice'"
          aria-label="Toggle AI voice"
        >
          <svg v-if="ttsEnabled" width="17" height="17" fill="none" viewBox="0 0 24 24">
            <path d="M11 5L6 9H2v6h4l5 4V5z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <svg v-else width="17" height="17" fill="none" viewBox="0 0 24 24">
            <path d="M11 5L6 9H2v6h4l5 4V5z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <line x1="23" y1="9" x2="17" y2="15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="17" y1="9" x2="23" y2="15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>
        <input
          type="text"
          id="cf-chat-input"
          v-model="inputValue"
          @keydown.enter.prevent="sendMessage"
          :placeholder="isRecording ? '🎙 Listening...' : 'Type a message…'"
          autocomplete="off"
          :disabled="isTyping"
        />
        <button
          id="cf-send-btn"
          @click="sendMessage"
          :style="{ background: branding.chatbot_color || '#6366f1' }"
          :disabled="isTyping || (!inputValue.trim() && !pendingImage)"
          aria-label="Send message"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>

      <div class="powered-by">Powered by <a href="https://checkfunnels.com" target="_blank" rel="noopener">Checkfunnels</a></div>
    </div>

    <!-- ── Lead Capture Modal ──────────────────────────────────────────── -->
    <div v-if="showLeadForm" class="cf-lead-overlay" @click.self="dismissLeadForm">
      <div class="cf-lead-modal">
        <button class="cf-lead-close" @click="dismissLeadForm">&times;</button>
        <div class="cf-lead-icon">📬</div>
        <h3 class="cf-lead-title">Stay in touch</h3>
        <p class="cf-lead-sub">Leave your contact and we'll follow up with a personalised answer.</p>
        <input v-model="leadEmail" type="email" class="cf-lead-input" placeholder="Your email address" @keydown.enter="submitLead" />
        <input v-model="leadPhone" type="tel" class="cf-lead-input" placeholder="Phone number (optional)" @keydown.enter="submitLead" />
        <button class="cf-lead-submit" :style="{ background: branding.chatbot_color }" @click="submitLead" :disabled="!leadEmail.trim()">
          {{ leadSubmitting ? 'Saving…' : 'Send my details' }}
        </button>
      </div>
    </div>

    <!-- ── Pill Bar (idle state) ──────────────────────────────────────── -->
    <div id="cf-pill-bar" @click="toggleWindow" v-show="!isOpen">
      <div class="pill-icon" :style="{ background: branding.chatbot_color || '#6366f1' }">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
        </svg>
      </div>
      <span class="pill-text">Write a message...</span>
      <div class="pill-send" :style="{ background: branding.chatbot_color || '#6366f1' }">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5">
          <line x1="22" y1="2" x2="11" y2="13"></line>
          <polygon points="22 2 15 22 11 13 2 9 22 2" fill="white" stroke="none"/>
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useTracker } from '../composables/useTracker'
import { marked } from 'marked'

// marked v17+ uses marked.use() — setOptions is removed
marked.use({
  breaks: true,
  renderer: {
    link({ href, text }) {
      return `<a target="_blank" rel="noopener noreferrer" href="${href}">${text || href}</a>`
    },
  },
})
const renderMarkdown = (text) => marked.parse(text || '')

// ── Tracker ───────────────────────────────────────────────────────────────────
const { sessionId, behaviorMatrix, visitorMeta, pageVisits, setNudgeCallback } = useTracker()

// ── State ─────────────────────────────────────────────────────────────────────
const clientId    = window.__CF_CLIENT_ID__ || null
const isOpen      = ref(false)
const isTyping    = ref(false)
const inputValue  = ref('')
const branding    = ref({ chatbot_name: 'AI Assistant', chatbot_color: '#6366f1', chatbot_logo_url: null, voice_input_enabled: false, image_input_enabled: false })
const chatMessages = ref([
  { type: 'text', text: "Hi! 👋 I'm your AI Assistant. How can I help you today?", sender: 'ai' },
])
const messagesContainer  = ref(null)
const fileInput          = ref(null)
const userMessageCount   = ref(0)
const pendingImage       = ref(null)   // base64 data URI of image to send
const isRecording        = ref(false)
const ttsEnabled         = ref(false)  // AI voice readback toggle

// ── Lead capture ──────────────────────────────────────────────────────────────
const showLeadForm   = ref(false)
const leadEmail      = ref('')
const leadPhone      = ref('')
const leadSubmitting = ref(false)
// Persist lead-captured state in localStorage so it survives page reloads
const LEAD_KEY = `cf_lead_captured_${clientId || 'default'}`
const leadCaptured   = ref(!!localStorage.getItem(LEAD_KEY))

// ── WebSocket ─────────────────────────────────────────────────────────────────
let socket = null
let reconnectTimer = null
let reconnectAttempts = 0
const MAX_RECONNECT = 5
const pendingMessages = []

function getApiBase() {
  if (window.__CF_BACKEND_URL__) return window.__CF_BACKEND_URL__
  return ''
}
function getWsBase() {
  if (window.__CF_BACKEND_URL__) return window.__CF_BACKEND_URL__.replace(/^http/, 'ws')
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}`
}

function connectWebSocket() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return
  const globalClientId = clientId || '00000000-0000-0000-0000-000000000000'
  socket = new WebSocket(`${getWsBase()}/ws/chat/${globalClientId}/${sessionId}/`)
  socket.onopen = () => {
    reconnectAttempts = 0
    // Send visitor fingerprint on first connection so the backend can persist it
    socket.send(JSON.stringify({
      type: 'visitor_meta',
      ...visitorMeta.value,
      page_visits: pageVisits.value,
    }))
    while (pendingMessages.length > 0) socket.send(JSON.stringify(pendingMessages.shift()))
  }
  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      removeTypingIndicator()
      isTyping.value = false
      if (data.type === 'ai_message' && data.message) {
        chatMessages.value.push({ type: 'text', text: data.message, sender: 'ai', reaction: null })
        speakText(data.message)
        playChime()
        if (!leadCaptured.value && userMessageCount.value >= 2) {
          setTimeout(() => { showLeadForm.value = true }, 1500)
        }
      }
    } catch {
      removeTypingIndicator()
      isTyping.value = false
    }
  }
  socket.onerror = () => {}
  socket.onclose = (event) => {
    removeTypingIndicator()
    isTyping.value = false
    socket = null
    if (event.code !== 1000 && reconnectAttempts < MAX_RECONNECT) {
      const delay = Math.min(1000 * 2 ** reconnectAttempts, 15000)
      reconnectAttempts++
      reconnectTimer = setTimeout(connectWebSocket, delay)
    }
  }
}

function disconnectWebSocket() {
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
  if (socket) { socket.close(1000, 'Component unmounted'); socket = null }
}

// ── Typing indicator ──────────────────────────────────────────────────────────
const TYPING_MSG_ID = '__typing__'
function showTypingIndicator() {
  chatMessages.value.push({ type: 'typing', sender: 'ai', id: TYPING_MSG_ID })
}
function removeTypingIndicator() {
  const idx = chatMessages.value.findIndex((m) => m.id === TYPING_MSG_ID)
  if (idx !== -1) chatMessages.value.splice(idx, 1)
}

// ── AI response chime ─────────────────────────────────────────────────────────
function playChime() {
  if (!isOpen.value) return
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    [[880, 0], [1100, 0.14], [1320, 0.26]].forEach(([freq, delay]) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.type = 'sine'
      osc.frequency.value = freq
      const t = ctx.currentTime + delay
      gain.gain.setValueAtTime(0, t)
      gain.gain.linearRampToValueAtTime(0.09, t + 0.04)
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.38)
      osc.start(t)
      osc.stop(t + 0.38)
    })
    setTimeout(() => ctx.close(), 1400)
  } catch {}
}

// ── Send message ──────────────────────────────────────────────────────────────
function sendMessage() {
  const text = inputValue.value.trim()
  if ((!text && !pendingImage) || isTyping.value) return

  // If there's a pending image, show it in chat first
  if (pendingImage.value) {
    chatMessages.value.push({ type: 'image', src: pendingImage.value, sender: 'user' })
  }

  const capturedImage = pendingImage.value  // capture before clearing
  const messageText = text || (capturedImage ? '[User sent an image]' : '')
  if (messageText) {
    chatMessages.value.push({ type: 'text', text: messageText, sender: 'user' })
  }

  inputValue.value = ''
  pendingImage.value = null
  isTyping.value = true
  userMessageCount.value++
  showTypingIndicator()

  const payload = {
    message: messageText,
    behavior_matrix: behaviorMatrix,
    page_visits: pageVisits.value,
    // Include base64 image so the server can pass it to the vision model
    ...(capturedImage ? { image_data: capturedImage } : {}),
  }
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload))
  } else {
    pendingMessages.push(payload)
    if (!socket || socket.readyState === WebSocket.CLOSED) connectWebSocket()
  }
}

// ── Image handling ────────────────────────────────────────────────────────────
function handleFileSelect(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (ev) => { pendingImage.value = ev.target.result }
  reader.readAsDataURL(file)
  e.target.value = ''   // reset so same file can be re-selected
}

function clearPendingImage() {
  pendingImage.value = null
}

// ── Voice input (STT) ─────────────────────────────────────────────────────────
let recognition = null
function toggleVoice() {
  if (isRecording.value) {
    recognition?.stop()
    isRecording.value = false
    return
  }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SR) { return }
  recognition = new SR()
  recognition.continuous = false
  recognition.interimResults = false
  recognition.lang = 'en-US'
  recognition.onresult = (e) => {
    inputValue.value = e.results[0][0].transcript
    isRecording.value = false
  }
  recognition.onerror = () => { isRecording.value = false }
  recognition.onend = () => { isRecording.value = false }
  recognition.start()
  isRecording.value = true
}

// ── Voice output (TTS) ────────────────────────────────────────────────────────
function stripMarkdownForTts(text) {
  return (text || '')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')  // [label](url) → label
    .replace(/\*\*([^*]+)\*\*/g, '$1')         // **bold** → bold
    .replace(/\*([^*]+)\*/g, '$1')             // *italic* → italic
    .replace(/^[\d]+\.\s+/gm, '')             // numbered list prefixes
    .replace(/^[-*]\s+/gm, '')                // bullet prefixes
    .replace(/#{1,6}\s+/g, '')                // headings
    .replace(/`{1,3}[^`]*`{1,3}/g, '')       // code
    .trim()
}

function speakText(text) {
  if (!ttsEnabled.value || !window.speechSynthesis) return
  window.speechSynthesis.cancel()
  const clean = stripMarkdownForTts(text)
  if (!clean) return
  const utt = new SpeechSynthesisUtterance(clean)
  utt.rate = 1.05
  utt.pitch = 1.0
  window.speechSynthesis.speak(utt)
}

function stopSpeech() {
  if (window.speechSynthesis) window.speechSynthesis.cancel()
}

// ── Emoji reactions ───────────────────────────────────────────────────────────
function react(index, emoji) {
  const msg = chatMessages.value[index]
  if (!msg) return
  msg.reaction = msg.reaction === emoji ? null : emoji
}

// ── Lead capture ──────────────────────────────────────────────────────────────
function dismissLeadForm() {
  showLeadForm.value = false
  leadCaptured.value = true
  localStorage.setItem(LEAD_KEY, '1')
}

async function submitLead() {
  const email = leadEmail.value.trim()
  if (!email || leadSubmitting.value) return
  leadSubmitting.value = true
  try {
    await fetch(`${getApiBase()}/api/chat/lead/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, email, phone: leadPhone.value.trim() || null }),
    })
  } catch {}
  leadSubmitting.value = false
  leadCaptured.value = true
  localStorage.setItem(LEAD_KEY, '1')
  showLeadForm.value = false
  chatMessages.value.push({ type: 'text', text: "✅ Thanks! We'll be in touch soon.", sender: 'ai', reaction: null })
}

// ── Auto-scroll ───────────────────────────────────────────────────────────────
watch(chatMessages, async () => {
  await nextTick()
  if (messagesContainer.value) messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
}, { deep: true })

// ── Toggle ────────────────────────────────────────────────────────────────────
function toggleWindow() {
  isOpen.value = !isOpen.value
  if (!isOpen.value) stopSpeech()
  if (isOpen.value) {
    connectWebSocket()
    nextTick(() => {
      if (messagesContainer.value) messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    })
  }
}

// ── Nudge callback ────────────────────────────────────────────────────────────
setNudgeCallback((nudgeText) => {
  if (!nudgeText) return
  chatMessages.value.push({ type: 'text', text: nudgeText, sender: 'ai', reaction: null })
  if (!isOpen.value) isOpen.value = true
})

// ── Branding ──────────────────────────────────────────────────────────────────
async function loadBranding() {
  if (!clientId) return
  try {
    const res = await fetch(`${getApiBase()}/api/chat/widget-config/${clientId}/`)
    if (!res.ok) return
    const cfg = await res.json()
    branding.value = cfg
    window.__CF_BRANDING__ = cfg
  } catch {}
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(() => {
  loadBranding()
  connectWebSocket()
})

onBeforeUnmount(() => {
  disconnectWebSocket()
})
</script>

<style scoped>
/* ── Container ──────────────────────────────────────────────────────── */
#cf-chat-container {
  all: initial !important;
  position: fixed !important;
  bottom: 24px !important;
  right: 24px !important;
  z-index: 2147483647 !important;
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
  pointer-events: auto !important;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
  box-sizing: border-box !important;
  direction: ltr !important;
  text-align: left !important;
  line-height: normal !important;
  font-size: 14px !important;
  color: #f1f5f9 !important;
}

/* ── Pill bar (idle) ────────────────────────────────────────────────── */
#cf-pill-bar {
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
  padding: 10px 12px 10px 10px !important;
  background: rgba(17, 17, 17, 0.96) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 100px !important;
  cursor: pointer !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45), 0 2px 8px rgba(0, 0, 0, 0.3) !important;
  transition: transform 0.2s, box-shadow 0.2s !important;
  min-width: 220px !important;
  max-width: 280px !important;
  user-select: none !important;
  animation: cf-pill-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards !important;
}
@keyframes cf-pill-in {
  from { opacity: 0; transform: translateY(12px) scale(0.95); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
#cf-pill-bar:hover { transform: translateY(-2px) !important; box-shadow: 0 12px 40px rgba(0,0,0,0.5), 0 2px 8px rgba(0,0,0,0.3) !important; }

.pill-icon {
  width: 32px !important; height: 32px !important;
  border-radius: 50% !important;
  display: flex !important; align-items: center !important; justify-content: center !important;
  flex-shrink: 0 !important;
}
.pill-text {
  flex: 1 !important;
  font-size: 13px !important;
  color: rgba(255, 255, 255, 0.45) !important;
  font-weight: 400 !important;
  white-space: nowrap !important;
}
.pill-send {
  width: 30px !important; height: 30px !important;
  border-radius: 50% !important;
  display: flex !important; align-items: center !important; justify-content: center !important;
  flex-shrink: 0 !important;
}

/* ── Chat window ────────────────────────────────────────────────────── */
#cf-chat-window {
  position: absolute !important;
  bottom: 0 !important;
  right: 0 !important;
  width: 380px !important;
  max-height: 620px !important;
  background: #111111 !important;
  border-radius: 20px !important;
  border: 1px solid rgba(255,255,255,0.07) !important;
  box-shadow: 0 24px 64px rgba(0,0,0,0.6), 0 4px 20px rgba(0,0,0,0.4) !important;
  display: flex !important;
  flex-direction: column !important;
  overflow: hidden !important;
  animation: cf-win-in 0.28s cubic-bezier(0.34, 1.56, 0.64, 1);
  visibility: visible !important;
  opacity: 1 !important;
}
@keyframes cf-win-in {
  from { opacity: 0; transform: translateY(16px) scale(0.97); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

/* ── Header ─────────────────────────────────────────────────────────── */
#cf-chat-header {
  background: #161616;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  padding: 14px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}
.header-info { display: flex; align-items: center; gap: 10px; }
.header-avatar {
  width: 38px; height: 38px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.header-logo-img { width: 38px; height: 38px; border-radius: 50%; object-fit: cover; }
.header-text { display: flex; flex-direction: column; gap: 2px; }
.header-name { font-size: 14px; font-weight: 600; color: #f1f5f9; letter-spacing: -0.2px; }
.header-status { font-size: 11px; color: #64748b; display: flex; align-items: center; gap: 4px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: #4ade80; }
#cf-close-btn {
  background: rgba(255,255,255,0.06); border: none; color: #94a3b8; cursor: pointer;
  width: 28px; height: 28px;
  min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px;
  border-radius: 50%; flex: 0 0 28px; align-self: center;
  display: flex; align-items: center; justify-content: center; transition: background 0.15s;
  padding: 0;
}
#cf-close-btn:hover { background: rgba(255,255,255,0.12); color: #f1f5f9; }

/* ── Messages ───────────────────────────────────────────────────────── */
#cf-chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #111111;
  min-height: 200px;
  max-height: 360px;
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.1) transparent;
}
#cf-chat-messages::-webkit-scrollbar { width: 4px; }
#cf-chat-messages::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }

.cf-msg {
  padding: 11px 15px;
  border-radius: 18px;
  max-width: 84%;
  word-wrap: break-word;
  font-size: 14px;
  line-height: 1.55;
  animation: cf-msg-in 0.22s ease;
}
@keyframes cf-msg-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.cf-msg-user {
  color: white;
  align-self: flex-end;
  border-bottom-right-radius: 4px;
}
.cf-msg-ai {
  background: #1e2433;
  color: #e2e8f0;
  align-self: flex-start;
  border-bottom-left-radius: 4px;
  border: 1px solid rgba(255,255,255,0.06);
}

/* ── Emoji reactions ────────────────────────────────────────────────── */
.msg-reactions {
  display: flex;
  gap: 4px;
  margin-top: 6px;
}
.reaction-btn {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 20px;
  padding: 2px 8px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  color: rgba(255,255,255,0.5);
}
.reaction-btn:hover { background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.8); }
.reaction-btn.active { background: rgba(99,102,241,0.2); border-color: rgba(99,102,241,0.4); color: #a5b4fc; }

/* ── Chat image ─────────────────────────────────────────────────────── */
.chat-image {
  max-width: 200px;
  max-height: 180px;
  border-radius: 12px;
  object-fit: cover;
  display: block;
}

/* ── Typing indicator ───────────────────────────────────────────────── */
.typing-indicator { display: flex; gap: 5px; align-items: center; height: 20px; }
.typing-indicator span { width: 7px; height: 7px; background: #475569; border-radius: 50%; animation: cf-bounce 1.2s infinite ease-in-out; }
.typing-indicator span:nth-child(2) { animation-delay: 0.18s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.36s; }
@keyframes cf-bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }

/* ── Image preview bar ──────────────────────────────────────────────── */
.image-preview-bar {
  padding: 8px 14px 0;
  background: #111111;
}
.image-preview-wrap { position: relative; display: inline-block; }
.preview-thumb { width: 56px; height: 56px; border-radius: 8px; object-fit: cover; display: block; border: 1px solid rgba(255,255,255,0.1); }
.preview-remove {
  position: absolute; top: -6px; right: -6px;
  width: 18px; height: 18px; border-radius: 50%;
  background: #ef4444; border: none; color: white; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}

/* ── Input area ─────────────────────────────────────────────────────── */
#cf-chat-input-area {
  display: flex;
  border-top: 1px solid rgba(255,255,255,0.06);
  padding: 10px 12px;
  background: #161616;
  align-items: center;
  gap: 7px;
  flex-shrink: 0;
}
.media-btn {
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
  color: #64748b;
  width: 34px; height: 34px;
  min-width: 34px; max-width: 34px; min-height: 34px; max-height: 34px;
  border-radius: 50%; flex: 0 0 34px; align-self: center;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all 0.15s; padding: 0;
}
.media-btn:hover { background: rgba(255,255,255,0.1); color: #94a3b8; }
.media-btn.recording { background: rgba(239,68,68,0.15); border-color: rgba(239,68,68,0.4); color: #f87171; animation: cf-pulse-rec 1s ease-in-out infinite; }
.media-btn.tts-active { background: rgba(99,102,241,0.15); border-color: rgba(99,102,241,0.4); color: #818cf8; }
@keyframes cf-pulse-rec { 0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.3); } 50% { box-shadow: 0 0 0 6px transparent; } }

#cf-chat-input {
  flex: 1;
  padding: 9px 14px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 20px;
  outline: none;
  font-size: 13px;
  background: rgba(255,255,255,0.05);
  color: #e2e8f0;
  font-family: inherit;
  transition: border-color 0.2s, background 0.2s;
}
#cf-chat-input:focus { border-color: rgba(99,102,241,0.4); background: rgba(255,255,255,0.07); }
#cf-chat-input::placeholder { color: rgba(255,255,255,0.25); }
#cf-chat-input:disabled { opacity: 0.5; cursor: not-allowed; }

#cf-send-btn {
  color: white; border: none; border-radius: 50%;
  cursor: pointer; transition: opacity 0.2s, transform 0.15s;
  display: flex; align-items: center; justify-content: center;
  width: 36px; height: 36px;
  min-width: 36px; max-width: 36px; min-height: 36px; max-height: 36px;
  flex: 0 0 36px; align-self: center; padding: 0;
}
#cf-send-btn:hover:not(:disabled) { opacity: 0.85; transform: scale(1.06); }
#cf-send-btn:disabled { opacity: 0.3; cursor: not-allowed; }

/* ── Powered-by footer ──────────────────────────────────────────────── */
.powered-by {
  text-align: center; font-size: 10px; color: rgba(255,255,255,0.2);
  padding: 5px 0 8px; background: #161616;
}
.powered-by a { color: rgba(255,255,255,0.3); text-decoration: none; }
.powered-by a:hover { color: rgba(255,255,255,0.5); }

/* ── Markdown ───────────────────────────────────────────────────────── */
.markdown-body { color: #e2e8f0; line-height: 1.6; }
.markdown-body :deep(p) { margin: 0 0 10px 0; color: #e2e8f0; line-height: 1.6; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(ol) {
  margin: 8px 0 10px 0; padding-left: 20px; color: #e2e8f0;
  list-style-type: decimal !important; display: block;
}
.markdown-body :deep(ul) {
  margin: 8px 0 10px 0; padding-left: 20px; color: #e2e8f0;
  list-style-type: disc !important; display: block;
}
.markdown-body :deep(li) {
  margin-bottom: 6px; color: #e2e8f0; line-height: 1.55;
  display: list-item !important;
}
.markdown-body :deep(li:last-child) { margin-bottom: 0; }
.markdown-body :deep(a) { color: #a5b4fc; text-decoration: underline; font-weight: 500; word-break: break-all; }
.markdown-body :deep(a:hover) { color: #c4b5fd; }
.markdown-body :deep(strong) { font-weight: 700; color: #f1f5f9; }
.markdown-body :deep(em) { font-style: italic; color: #cbd5e1; }
.markdown-body :deep(code) { background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; font-size: 12px; color: #c4b5fd; font-family: monospace; }
.markdown-body :deep(pre) { background: rgba(0,0,0,0.3); border-radius: 8px; padding: 10px 12px; margin: 8px 0; overflow-x: auto; }
.markdown-body :deep(pre code) { background: none; padding: 0; font-size: 12px; color: #a5b4fc; }
.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3) { color: #f1f5f9; font-weight: 700; margin: 10px 0 6px; line-height: 1.3; }
.markdown-body :deep(h1) { font-size: 16px; }
.markdown-body :deep(h2) { font-size: 15px; }
.markdown-body :deep(h3) { font-size: 14px; }
.markdown-body :deep(blockquote) { border-left: 3px solid rgba(99,102,241,0.5); margin: 8px 0; padding: 4px 12px; color: #94a3b8; font-style: italic; }
.markdown-body :deep(hr) { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 10px 0; }

/* ── Lead capture modal ─────────────────────────────────────────────── */
.cf-lead-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 1000000;
  display: flex; align-items: center; justify-content: center;
  animation: cf-msg-in 0.2s ease;
}
.cf-lead-modal {
  background: #1a1f2e; border: 1px solid rgba(255,255,255,0.1);
  border-radius: 20px; padding: 32px 28px; width: 320px; max-width: 90vw;
  position: relative; box-shadow: 0 20px 60px rgba(0,0,0,0.5);
}
.cf-lead-close {
  position: absolute; top: 12px; right: 14px;
  background: none; border: none; font-size: 22px; cursor: pointer; color: #64748b;
}
.cf-lead-icon { font-size: 36px; text-align: center; margin-bottom: 12px; }
.cf-lead-title { margin: 0 0 6px; font-size: 18px; font-weight: 700; color: #f1f5f9; text-align: center; }
.cf-lead-sub { margin: 0 0 20px; font-size: 13px; color: #64748b; text-align: center; line-height: 1.5; }
.cf-lead-input {
  width: 100%; padding: 11px 14px; border: 1px solid rgba(255,255,255,0.1); border-radius: 10px;
  font-size: 14px; margin-bottom: 10px; box-sizing: border-box; outline: none; font-family: inherit;
  background: rgba(255,255,255,0.05); color: #e2e8f0; transition: border 0.2s;
}
.cf-lead-input:focus { border-color: rgba(99,102,241,0.5); }
.cf-lead-input::placeholder { color: rgba(255,255,255,0.25); }
.cf-lead-submit {
  width: 100%; padding: 12px; border: none; border-radius: 10px;
  color: white; font-size: 15px; font-weight: 600; cursor: pointer;
  transition: opacity 0.2s; margin-top: 4px;
}
.cf-lead-submit:hover:not(:disabled) { opacity: 0.88; }
.cf-lead-submit:disabled { opacity: 0.45; cursor: not-allowed; }
</style>
