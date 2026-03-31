<template>
  <div id="cf-chat-container">
    <!-- Chat Window -->
    <div id="cf-chat-window" v-show="isOpen">
      <div id="cf-chat-header">
        <div class="header-info">
          <img v-if="branding.chatbot_logo_url" :src="branding.chatbot_logo_url" class="header-logo" alt="logo" />
          <div v-else class="status-dot"></div>
          <div class="header-text">
            <span class="header-name">{{ branding.chatbot_name }}</span>
            <span class="header-status">● Online</span>
          </div>
        </div>
        <button id="cf-close-btn" @click="toggleWindow" aria-label="Close chat">&times;</button>
      </div>

      <div id="cf-chat-messages" ref="messagesContainer">
        <div
          v-for="(msg, index) in chatMessages"
          :key="index"
          :class="['cf-msg', msg.sender === 'user' ? 'cf-msg-user' : 'cf-msg-ai']"
          :style="msg.sender === 'user' ? { background: branding.chatbot_color } : {}"
        >
          <template v-if="msg.type === 'text'">
            <div v-if="msg.sender === 'ai'" v-html="renderMarkdown(msg.text)" class="markdown-body"></div>
            <div v-else>{{ msg.text }}</div>
          </template>
          <template v-else-if="msg.type === 'typing'">
            <div class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </template>
          <template v-else-if="msg.type === 'product'">
            <ProductCard :productId="msg.productId" :clientId="clientId" />
          </template>
        </div>
      </div>

      <div id="cf-chat-input-area">
        <input
          type="text"
          id="cf-chat-input"
          v-model="inputValue"
          @keydown.enter.prevent="sendMessage"
          placeholder="Type your message…"
          autocomplete="off"
          :disabled="isTyping"
        />
        <button
          id="cf-send-btn"
          @click="sendMessage"
          :style="{ background: branding.chatbot_color }"
          :disabled="isTyping || !inputValue.trim()"
          aria-label="Send message"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>
    </div>

    <!-- Lead Capture Modal -->
    <div v-if="showLeadForm" class="cf-lead-overlay" @click.self="dismissLeadForm">
      <div class="cf-lead-modal">
        <button class="cf-lead-close" @click="dismissLeadForm">&times;</button>
        <div class="cf-lead-icon">📬</div>
        <h3 class="cf-lead-title">Stay in touch</h3>
        <p class="cf-lead-sub">Leave your contact and we'll follow up with a personalised answer.</p>
        <input
          v-model="leadEmail"
          type="email"
          class="cf-lead-input"
          placeholder="Your email address"
          @keydown.enter="submitLead"
        />
        <input
          v-model="leadPhone"
          type="tel"
          class="cf-lead-input"
          placeholder="Phone number (optional)"
          @keydown.enter="submitLead"
        />
        <button
          class="cf-lead-submit"
          :style="{ background: branding.chatbot_color }"
          @click="submitLead"
          :disabled="!leadEmail.trim()"
        >
          {{ leadSubmitting ? 'Saving…' : 'Send my details' }}
        </button>
      </div>
    </div>

    <!-- Floating Bubble -->
    <button id="cf-chat-button" @click="toggleWindow" :style="{ background: branding.chatbot_color }" aria-label="Open chat">
      <svg v-if="!isOpen" width="28" height="28" viewBox="0 0 24 24" fill="white">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
      <svg v-else width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
    </button>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue';
import ProductCard from './ProductCard.vue';
import { useTracker } from '../composables/useTracker';
import { marked } from 'marked';

const renderer = new marked.Renderer();
renderer.link = (token) =>
  `<a target="_blank" rel="noopener noreferrer" href="${token.href}">${token.text}</a>`;
marked.setOptions({ renderer, breaks: true });

const renderMarkdown = (text) => marked.parse(text || '');

// ─── Tracker ─────────────────────────────────────────────────────────────────
const { sessionId, behaviorMatrix, setNudgeCallback } = useTracker();

// ─── State ────────────────────────────────────────────────────────────────────
const clientId = window.__CF_CLIENT_ID__ || null;
const isOpen     = ref(false);
const isTyping   = ref(false);
const inputValue = ref('');
const branding   = ref({
  chatbot_name: 'AI Assistant',
  chatbot_color: '#3B82F6',
  chatbot_logo_url: null,
});
const chatMessages = ref([
  { type: 'text', text: "Hi! 👋 I'm your AI Assistant. How can I help you today?", sender: 'ai' },
]);
const messagesContainer = ref(null);
const userMessageCount = ref(0);

// ─── Lead capture state ───────────────────────────────────────────────────────
const showLeadForm    = ref(false);
const leadEmail       = ref('');
const leadPhone       = ref('');
const leadSubmitting  = ref(false);
const leadCaptured    = ref(false);  // only show once per session

// ─── WebSocket ────────────────────────────────────────────────────────────────
let socket = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
const MAX_RECONNECT = 5;
const pendingMessages = [];

function getApiBase() {
  // Production embed: main.js sets this from the <script src> URL so the widget
  // always calls back to the correct Django server, not the host page.
  if (window.__CF_BACKEND_URL__) return window.__CF_BACKEND_URL__;
  // Dev (Vite proxy) or same-origin Django: use relative paths (proxy handles it).
  return '';
}

function getWsBase() {
  // Production embed: derive ws(s):// from the known backend HTTP URL.
  if (window.__CF_BACKEND_URL__) {
    return window.__CF_BACKEND_URL__.replace(/^http/, 'ws');
  }
  // Dev / same-origin: WebSocket to the current host (Vite proxies /ws → Django).
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}`;
}

function connectWebSocket() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;

  const globalClientId = clientId || '00000000-0000-0000-0000-000000000000';
  socket = new WebSocket(`${getWsBase()}/ws/chat/${globalClientId}/${sessionId}/`);

  socket.onopen = () => {
    reconnectAttempts = 0;
    while (pendingMessages.length > 0) {
      socket.send(JSON.stringify(pendingMessages.shift()));
    }
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      removeTypingIndicator();
      isTyping.value = false;

      if (data.type === 'ai_message') {
        if (data.message) {
          chatMessages.value.push({ type: 'text', text: data.message, sender: 'ai' });
        }
        if (data.suggested_product_id) {
          chatMessages.value.push({ type: 'product', productId: data.suggested_product_id, sender: 'ai' });
        }
        // Trigger lead capture after 3rd AI response if not already captured
        if (!leadCaptured.value && userMessageCount.value >= 3) {
          setTimeout(() => { showLeadForm.value = true; }, 1500);
        }
      }
    } catch {
      removeTypingIndicator();
      isTyping.value = false;
    }
  };

  socket.onerror = () => {};

  socket.onclose = (event) => {
    removeTypingIndicator();
    isTyping.value = false;
    socket = null;
    if (event.code !== 1000 && reconnectAttempts < MAX_RECONNECT) {
      const delay = Math.min(1000 * 2 ** reconnectAttempts, 15000);
      reconnectAttempts++;
      reconnectTimer = setTimeout(connectWebSocket, delay);
    }
  };
}

function disconnectWebSocket() {
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
  if (socket) { socket.close(1000, 'Component unmounted'); socket = null; }
}

// ─── Typing indicator ─────────────────────────────────────────────────────────
const TYPING_MSG_ID = '__typing__';
function showTypingIndicator() {
  chatMessages.value.push({ type: 'typing', sender: 'ai', id: TYPING_MSG_ID });
}
function removeTypingIndicator() {
  const idx = chatMessages.value.findIndex((m) => m.id === TYPING_MSG_ID);
  if (idx !== -1) chatMessages.value.splice(idx, 1);
}

// ─── Send message ─────────────────────────────────────────────────────────────
function sendMessage() {
  const text = inputValue.value.trim();
  if (!text || isTyping.value) return;

  chatMessages.value.push({ type: 'text', text, sender: 'user' });
  inputValue.value = '';
  isTyping.value = true;
  userMessageCount.value++;
  showTypingIndicator();

  const payload = { message: text, behavior_matrix: behaviorMatrix };
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload));
  } else {
    pendingMessages.push(payload);
    if (!socket || socket.readyState === WebSocket.CLOSED) connectWebSocket();
  }
}

// ─── Lead capture ─────────────────────────────────────────────────────────────
function dismissLeadForm() {
  showLeadForm.value = false;
  leadCaptured.value = true;  // don't show again this session
}

async function submitLead() {
  const email = leadEmail.value.trim();
  if (!email || leadSubmitting.value) return;

  leadSubmitting.value = true;
  try {
    await fetch(`${getApiBase()}/api/chat/lead/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        email,
        phone: leadPhone.value.trim() || null,
      }),
    });
  } catch { /* silent fail — lead saved on best-effort */ }

  leadSubmitting.value = false;
  leadCaptured.value = true;
  showLeadForm.value = false;
  chatMessages.value.push({
    type: 'text',
    text: '✅ Thanks! We\'ll be in touch soon.',
    sender: 'ai',
  });
}

// ─── Auto-scroll ──────────────────────────────────────────────────────────────
watch(chatMessages, async () => {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
}, { deep: true });

// ─── Toggle ───────────────────────────────────────────────────────────────────
function toggleWindow() {
  isOpen.value = !isOpen.value;
  if (isOpen.value) {
    connectWebSocket();
    nextTick(() => {
      if (messagesContainer.value) messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    });
  }
}

// ─── Nudge callback ───────────────────────────────────────────────────────────
setNudgeCallback((nudgeText) => {
  if (!nudgeText) return;
  chatMessages.value.push({ type: 'text', text: nudgeText, sender: 'ai' });
  if (!isOpen.value) isOpen.value = true;
});

// ─── Branding ─────────────────────────────────────────────────────────────────
async function loadBranding() {
  if (!clientId) return;
  try {
    const res = await fetch(`${getApiBase()}/api/chat/widget-config/${clientId}/`);
    if (!res.ok) return;
    const cfg = await res.json();
    branding.value = cfg;
    const root = document.getElementById('cf-app-root');
    if (root) {
      root.style.setProperty('--cf-primary', cfg.chatbot_color);
      root.style.setProperty('--cf-primary-dark', cfg.chatbot_color + 'cc');
    }
    window.__CF_BRANDING__ = cfg;
  } catch { /* use defaults */ }
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(() => {
  loadBranding();
  connectWebSocket();
});

onBeforeUnmount(() => {
  disconnectWebSocket();
});
</script>

<style scoped>
/* ── Container ──────────────────────────────────────────────────────── */
/* !important on all positioning/visibility rules to resist WordPress theme overrides */
#cf-chat-container {
  all: initial !important;
  position: fixed !important;
  bottom: 28px !important;
  right: 28px !important;
  z-index: 2147483647 !important;   /* max possible z-index */
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
  color: #0F172A !important;
}

#cf-chat-button {
  width: 65px !important;
  height: 65px !important;
  border-radius: 50% !important;
  background: var(--cf-primary, #3B82F6) !important;
  color: white !important;
  border: none !important;
  cursor: pointer !important;
  box-shadow: 0 4px 15px rgba(0,0,0,0.25) !important;
  transition: transform 0.3s ease !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  visibility: visible !important;
  opacity: 1 !important;
  position: relative !important;
  padding: 0 !important;
  margin: 0 !important;
  outline: none !important;
  min-width: 0 !important;
  min-height: 0 !important;
}
#cf-chat-button:hover { transform: scale(1.08); box-shadow: 0 8px 28px rgba(0,0,0,0.3) !important; }

/* ── Chat window ────────────────────────────────────────────────────── */
#cf-chat-window {
  position: absolute !important;
  bottom: 80px !important;
  right: 0 !important;
  width: 420px !important;
  max-height: 640px !important;
  background: #fff !important;
  border-radius: 20px !important;
  box-shadow: 0 20px 60px rgba(0,0,0,0.18) !important;
  display: flex !important;
  flex-direction: column !important;
  overflow: hidden !important;
  animation: slideUp 0.25s ease;
  visibility: visible !important;
  opacity: 1 !important;
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Header ─────────────────────────────────────────────────────────── */
#cf-chat-header {
  background: var(--cf-primary, #3B82F6);
  color: white;
  padding: 16px 18px;
  font-weight: 600;
  font-size: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}
.header-info { display: flex; align-items: center; gap: 10px; }
.header-logo { width: 36px; height: 36px; border-radius: 50%; object-fit: cover; border: 2px solid rgba(255,255,255,0.5); }
.status-dot { width: 36px; height: 36px; background: rgba(255,255,255,0.25); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px; }
.status-dot::after { content: '🤖'; }
.header-text { display: flex; flex-direction: column; gap: 1px; }
.header-name { font-size: 15px; font-weight: 600; line-height: 1.2; }
.header-status { font-size: 11px; opacity: 0.85; }
#cf-close-btn {
  background: rgba(255,255,255,0.2); border: none; color: white; cursor: pointer;
  font-size: 20px; border-radius: 50%; width: 30px; height: 30px;
  display: flex; align-items: center; justify-content: center; transition: background 0.2s; flex-shrink: 0;
}

/* ── Messages ───────────────────────────────────────────────────────── */
#cf-chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #f8f9fb;
}
.cf-msg {
  padding: 13px 18px;
  border-radius: 18px;
  max-width: 85%;
  word-wrap: break-word;
  font-size: 15px;
  line-height: 1.55;
  animation: fadeIn 0.25s ease;
}
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.cf-msg-user { color: white; align-self: flex-end; border-bottom-right-radius: 4px; }
.cf-msg-ai { background: #fff; color: #1a1a2e; align-self: flex-start; border-bottom-left-radius: 4px; border: 1px solid #ececec; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }

/* ── Typing indicator ───────────────────────────────────────────────── */
.typing-indicator { display: flex; gap: 5px; align-items: center; height: 20px; }
.typing-indicator span { width: 8px; height: 8px; background: #adb5bd; border-radius: 50%; animation: bounce 1.2s infinite ease-in-out; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }

/* ── Input area ─────────────────────────────────────────────────────── */
#cf-chat-input-area {
  display: flex;
  border-top: 1px solid #efefef;
  padding: 12px 14px;
  background: white;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
#cf-chat-input {
  flex: 1;
  padding: 11px 18px;
  border: 1.5px solid #e1e5ea;
  border-radius: 24px;
  outline: none;
  font-size: 14px;
  background: #f8f9fb;
  transition: border 0.2s, box-shadow 0.2s;
  font-family: inherit;
}
#cf-chat-input:focus { border-color: var(--cf-primary, #3B82F6); background: #fff; box-shadow: 0 0 0 3px rgba(59,130,246,0.12); }
#cf-chat-input:disabled { opacity: 0.6; cursor: not-allowed; }
#cf-send-btn {
  color: white; border: none; padding: 11px 14px; border-radius: 50%;
  cursor: pointer; transition: opacity 0.2s, transform 0.15s;
  display: flex; align-items: center; justify-content: center;
  width: 44px; height: 44px; flex-shrink: 0;
}
#cf-send-btn:hover:not(:disabled) { opacity: 0.88; transform: scale(1.05); }
#cf-send-btn:disabled { opacity: 0.45; cursor: not-allowed; }

/* ── Markdown ───────────────────────────────────────────────────────── */
.markdown-body :deep(p) { margin: 0 0 8px 0; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(ol), .markdown-body :deep(ul) { margin: 6px 0; padding-left: 18px; }
.markdown-body :deep(li) { margin-bottom: 5px; }
.markdown-body :deep(a) { color: #3B82F6; text-decoration: none; font-weight: 600; }
.markdown-body :deep(a:hover) { text-decoration: underline; }
.markdown-body :deep(strong) { font-weight: 700; }
.markdown-body :deep(code) { background: #f1f3f5; padding: 2px 6px; border-radius: 4px; font-size: 13px; }

/* ── Lead capture modal ─────────────────────────────────────────────── */
.cf-lead-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.45);
  z-index: 1000000;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.2s ease;
}
.cf-lead-modal {
  background: #fff;
  border-radius: 20px;
  padding: 32px 28px;
  width: 320px;
  max-width: 90vw;
  position: relative;
  box-shadow: 0 20px 60px rgba(0,0,0,0.25);
  animation: slideUp 0.2s ease;
}
.cf-lead-close {
  position: absolute; top: 12px; right: 14px;
  background: none; border: none; font-size: 22px; cursor: pointer; color: #999;
}
.cf-lead-icon { font-size: 36px; text-align: center; margin-bottom: 12px; }
.cf-lead-title { margin: 0 0 6px; font-size: 18px; font-weight: 700; color: #1a1a2e; text-align: center; }
.cf-lead-sub { margin: 0 0 20px; font-size: 13px; color: #64748b; text-align: center; line-height: 1.5; }
.cf-lead-input {
  width: 100%; padding: 11px 14px; border: 1.5px solid #e1e5ea; border-radius: 10px;
  font-size: 14px; margin-bottom: 10px; box-sizing: border-box; outline: none; font-family: inherit;
  transition: border 0.2s;
}
.cf-lead-input:focus { border-color: var(--cf-primary, #3B82F6); }
.cf-lead-submit {
  width: 100%; padding: 12px; border: none; border-radius: 10px;
  color: white; font-size: 15px; font-weight: 600; cursor: pointer;
  transition: opacity 0.2s; margin-top: 4px;
}
.cf-lead-submit:hover:not(:disabled) { opacity: 0.88; }
.cf-lead-submit:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
