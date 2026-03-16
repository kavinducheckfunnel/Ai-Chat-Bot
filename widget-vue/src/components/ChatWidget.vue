<template>
  <div id="cf-chat-container">
    <!-- Chat Window -->
    <div id="cf-chat-window" v-show="isOpen">
      <div id="cf-chat-header">
        <div class="header-title">
          <img v-if="branding.chatbot_logo_url" :src="branding.chatbot_logo_url" class="header-logo" alt="logo" />
          <div v-else class="status-dot"></div>
          {{ branding.chatbot_name }}
        </div>
        <button id="cf-close-btn" @click="toggleWindow" aria-label="Close chat">&times;</button>
      </div>

      <div id="cf-chat-messages" ref="messagesContainer">
        <!-- Chat messages -->
        <div
          v-for="(msg, index) in chatMessages"
          :key="index"
          :class="['cf-msg', msg.sender === 'user' ? 'cf-msg-user' : 'cf-msg-ai']"
          :style="msg.sender === 'user' ? { background: branding.color } : {}"
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
            <ProductCard :productId="msg.productId" />
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
          :style="{ background: branding.color }"
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

    <!-- Floating Bubble -->
    <button id="cf-chat-button" @click="toggleWindow" :style="{ background: branding.color }" aria-label="Open chat">
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

// ─── Tracker composable ───────────────────────────────────────────────────────
const { sessionId, behaviorMatrix, setNudgeCallback } = useTracker();

// ── Branding ────────────────────────────────────────────────────────────────
const branding = ref({
  chatbot_name: 'AI Assistant',
  chatbot_color: '#3B82F6',
  chatbot_logo_url: null,
});

async function loadBranding() {
  const clientId = window.__CF_CLIENT_ID__;
  if (!clientId) return;
  try {
    const API = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      ? 'http://localhost:8000'
      : '';
    const res = await fetch(`${API}/api/chat/widget-config/${clientId}/`);
    if (!res.ok) return;
    const cfg = await res.json();
    branding.value = cfg;
    // Inject CSS custom properties onto the widget root
    const root = document.getElementById('cf-app-root');
    if (root) {
      root.style.setProperty('--cf-primary', cfg.chatbot_color);
      // Derive a darker shade for hover states
      root.style.setProperty('--cf-primary-dark', cfg.chatbot_color + 'cc');
    }
    // Store FOMO config globally so the tracker can access it
    window.__CF_BRANDING__ = cfg;
  } catch { /* silently fail — widget still works with defaults */ }
}

const isOpen = ref(false);
const inputValue = ref('');
const chatMessages = ref([
  { type: 'text', text: "Hi! I'm your Checkfunnel AI Expert. How can I help you today?", sender: 'ai' }
]);
const messagesContainer = ref(null);
let socket = null;

// ─── State ────────────────────────────────────────────────────────────────────
const isOpen     = ref(false);
const isTyping   = ref(false);
const inputValue = ref('');
const branding   = ref({ name: '', color: '#3B82F6', logo_url: '' });

const chatMessages = ref([
  {
    type: 'text',
    text: "Hi! 👋 I'm your AI Assistant. How can I help you today?",
    sender: 'ai',
  },
]);

const messagesContainer = ref(null);

// ─── WebSocket ────────────────────────────────────────────────────────────────
let socket = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
const MAX_RECONNECT = 5;

function connectWebSocket() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return; // Already connected or connecting
  }

  const wsUrl = `${CF_WS_URL}/ws/chat/${CF_CLIENT_ID}/${sessionId.value}/`;
  console.log('[CF] Connecting WebSocket:', wsUrl);

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log('[CF] WebSocket connected.');
    reconnectAttempts = 0;
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      // Remove typing indicator
      removeTypingIndicator();
      isTyping.value = false;

      if (data.type === 'ai_message') {
        chatMessages.value.push({
          type: 'text',
          text: data.message || '',
          sender: 'ai',
        });

        if (data.suggested_product_id) {
          chatMessages.value.push({
            type: 'product',
            productId: data.suggested_product_id,
            sender: 'ai',
          });
        }
      }
    } catch (err) {
      console.error('[CF] Failed to parse WebSocket message:', err);
      removeTypingIndicator();
      isTyping.value = false;
    }
  };

  socket.onerror = (err) => {
    console.error('[CF] WebSocket error:', err);
  };

  socket.onclose = (event) => {
    console.warn('[CF] WebSocket closed. Code:', event.code);
    removeTypingIndicator();
    isTyping.value = false;
    socket = null;

    // Auto-reconnect with exponential back-off (skip if intentional close)
    if (event.code !== 1000 && reconnectAttempts < MAX_RECONNECT) {
      const delay = Math.min(1000 * 2 ** reconnectAttempts, 15000);
      reconnectAttempts++;
      console.log(`[CF] Reconnecting in ${delay}ms (attempt ${reconnectAttempts})…`);
      reconnectTimer = setTimeout(connectWebSocket, delay);
    }
  };
}

function disconnectWebSocket() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (socket) {
    socket.close(1000, 'Component unmounted');
    socket = null;
  }
}

// ─── Typing indicator helpers ─────────────────────────────────────────────────
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

  // Show message immediately — don't wait for socket
  chatMessages.value.push({ type: 'text', text, sender: 'user' });
  inputValue.value = '';
  isTyping.value = true;
  showTypingIndicator();

  // Ensure socket is open, then send
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    connectWebSocket();
  }
  _trySend(text, 0);
}

function _trySend(text, attempt) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ message: text, behavior_matrix: behaviorMatrix.value || {} }));
    return;
  }
  if (attempt < 10) {
    setTimeout(() => _trySend(text, attempt + 1), 400);
  } else {
    removeTypingIndicator();
    isTyping.value = false;
    chatMessages.value.push({
      type: 'text',
      text: '⚠️ Could not connect to server. Please try again.',
      sender: 'ai',
    });
  }
}

// ─── Auto-scroll on new messages ─────────────────────────────────────────────
watch(chatMessages, async () => {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
}, { deep: true });

// ─── Toggle chat window ───────────────────────────────────────────────────────
function toggleWindow() {
  isOpen.value = !isOpen.value;
  if (isOpen.value) {
    connectWebSocket();
    nextTick(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
      }
    });
  }
}

// Queue for messages sent while the socket is still connecting
const pendingMessages = [];
let reconnectTimer = null;

const connectWebSocket = () => {
  // Don't open a second connection if one is already open or connecting
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  const host = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost'
    ? '127.0.0.1:8000'
    : window.location.host;
  // Use actual client ID or a nil UUID so the backend skips client lookup cleanly
  const globalClientId = window.__CF_CLIENT_ID__ || '00000000-0000-0000-0000-000000000000';
  socket = new WebSocket(`ws://${host}/ws/chat/${globalClientId}/${sessionId}/`);

  socket.onopen = () => {
    // Flush any messages that were queued while connecting
    while (pendingMessages.length > 0) {
      const payload = pendingMessages.shift();
      socket.send(JSON.stringify(payload));
    }
  };

  socket.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.type === 'ai_message') {
        if (data.message) {
          chatMessages.value.push({ type: 'text', text: data.message, sender: 'ai' });
        }
        if (data.suggested_product_id) {
          chatMessages.value.push({ type: 'product', productId: data.suggested_product_id, sender: 'ai' });
        }
      }
    } catch { /* ignore malformed frames */ }
  };

  socket.onclose = () => {
    // Auto-reconnect after 3 seconds on unexpected close
    if (reconnectTimer) clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(() => {
      connectWebSocket();
    }, 3000);
  };

  socket.onerror = () => {
    // Let onclose handle the reconnect
  };
};

const sendMessage = () => {
  const msgText = inputValue.value.trim();
  if (!msgText) return;

  chatMessages.value.push({ type: 'text', text: msgText, sender: 'user' });
  inputValue.value = '';

  const payload = { message: msgText, behavior_matrix: behaviorMatrix };

  if (socket && socket.readyState === WebSocket.OPEN) {
    // Socket ready — send immediately
    socket.send(JSON.stringify(payload));
  } else {
    // Socket is connecting or closed — queue the message
    pendingMessages.push(payload);
    if (!socket || socket.readyState === WebSocket.CLOSED) {
      connectWebSocket();
    }
  }
}

// ─── Proactive nudge callback from tracker ────────────────────────────────────
function handleNudge(nudgeText) {
  if (!nudgeText) return;
  chatMessages.value.push({ type: 'text', text: nudgeText, sender: 'ai' });
  if (!isOpen.value) isOpen.value = true;
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(() => {
  loadBranding();
  // Connect immediately — no delay needed
  connectWebSocket();
});
</script>

<style scoped>
/* ── Container ─────────────────────────────────────────────────────── */
#cf-chat-container {
  position: fixed;
  bottom: 28px;
  right: 28px;
  z-index: 999999;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
#cf-chat-button {
  width: 65px;
  height: 65px;
  border-radius: 50%;
  background: var(--cf-primary, #3B82F6);
  color: white;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 15px rgba(0,0,0,0.25);
  font-size: 28px;
  transition: transform 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}
#cf-chat-button:hover {
  transform: scale(1.08);
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.3);
}

#cf-chat-header {
  background: var(--cf-primary, #3B82F6);
  color: white;
  padding: 20px;
  font-weight: 600;
  font-size: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-logo {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid rgba(255,255,255,0.4);
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Header ────────────────────────────────────────────────────────── */
#cf-chat-header {
  color: white;
  padding: 16px 18px;
  font-weight: 600;
  font-size: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-logo {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid rgba(255,255,255,0.5);
}

.status-dot {
  width: 36px;
  height: 36px;
  background: rgba(255,255,255,0.25);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}
.status-dot::after { content: '🤖'; }

.header-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.header-name {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.2;
}

.header-status {
  font-size: 11px;
  opacity: 0.85;
  letter-spacing: 0.3px;
}

#cf-close-btn {
  background: rgba(255,255,255,0.2);
  border: none;
  color: white;
  cursor: pointer;
  font-size: 20px;
  border-radius: 50%;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
  flex-shrink: 0;
}
#cf-chat-input:focus {
  border-color: var(--cf-primary, #3B82F6);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.15);
}

#cf-send-btn {
  background: var(--cf-primary, #3B82F6);
  color: white;
  border: none;
  padding: 14px 22px;
  border-radius: 25px;
  cursor: pointer;
  font-weight: 500;
  font-size: 15px;
  transition: opacity 0.2s;
}
#cf-send-btn:hover { opacity: 0.85; }

.cf-msg { 
  padding: 14px 20px; 
  border-radius: 18px; 
  max-width: 85%; 
  word-wrap: break-word; 
  font-size: 15px; 
  line-height: 1.5; 
  box-shadow: 0 2px 5px rgba(0,0,0,0.05); 
  animation: fadeIn 0.3s ease; 
}
@keyframes fadeIn { 
  from { opacity: 0; transform: translateY(10px); } 
  to { opacity: 1; transform: translateY(0); } 
}

.cf-msg-user {
  background: var(--cf-primary, #3B82F6);
  color: white;
  align-self: flex-end;
  border-bottom-right-radius: 4px;
}
.cf-msg-ai { 
  background: #ffffff; 
  color: #333; 
  align-self: flex-start; 
  border-bottom-left-radius: 4px; 
  border: 1px solid #efefef; 
}

.cf-msg-user {
  color: white;
  align-self: flex-end;
  border-bottom-right-radius: 4px;
}

.cf-msg-ai {
  background: #ffffff;
  color: #1a1a2e;
  align-self: flex-start;
  border-bottom-left-radius: 4px;
  border: 1px solid #ececec;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

/* ── Typing indicator ──────────────────────────────────────────────── */
.typing-indicator {
  display: flex;
  gap: 5px;
  align-items: center;
  height: 20px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #adb5bd;
  border-radius: 50%;
  animation: bounce 1.2s infinite ease-in-out;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30%           { transform: translateY(-6px); }
}

/* ── Input area ────────────────────────────────────────────────────── */
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
#cf-chat-input:focus {
  border-color: #3B82F6;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.12);
}
#cf-chat-input:disabled { opacity: 0.6; cursor: not-allowed; }

#cf-send-btn {
  color: white;
  border: none;
  padding: 11px 14px;
  border-radius: 50%;
  cursor: pointer;
  font-weight: 500;
  font-size: 15px;
  transition: opacity 0.2s, transform 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  flex-shrink: 0;
}
#cf-send-btn:hover:not(:disabled) { opacity: 0.88; transform: scale(1.05); }
#cf-send-btn:disabled { opacity: 0.45; cursor: not-allowed; }

/* ── Markdown styles inside AI bubbles ─────────────────────────────── */
.markdown-body :deep(p)           { margin: 0 0 8px 0; }
.markdown-body :deep(p:last-child){ margin-bottom: 0; }
.markdown-body :deep(ol),
.markdown-body :deep(ul)          { margin: 6px 0; padding-left: 18px; }
.markdown-body :deep(li)          { margin-bottom: 5px; }
.markdown-body :deep(a) {
  color: #3B82F6;
  text-decoration: none;
  font-weight: 600;
}
.markdown-body :deep(a:hover)     { text-decoration: underline; }
.markdown-body :deep(strong)      { font-weight: 700; }
.markdown-body :deep(code) {
  background: #f1f3f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}
</style>
