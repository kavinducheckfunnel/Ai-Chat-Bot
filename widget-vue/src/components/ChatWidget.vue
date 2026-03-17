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
        <button id="cf-close-btn" @click="toggleWindow">&times;</button>
      </div>

      <div id="cf-chat-messages" ref="messagesContainer">
        <div v-for="(msg, index) in chatMessages" :key="index" :class="['cf-msg', msg.sender === 'user' ? 'cf-msg-user' : 'cf-msg-ai']">
          <template v-if="msg.type === 'text'">
            <div v-if="msg.sender === 'ai'" v-html="renderMarkdown(msg.text)" class="markdown-body"></div>
            <div v-else>{{ msg.text }}</div>
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
          @keypress.enter="sendMessage" 
          placeholder="Type your message..." 
          autocomplete="off" 
        />
        <button id="cf-send-btn" @click="sendMessage">Send</button>
      </div>
    </div>

    <!-- Floating Bubble -->
    <button id="cf-chat-button" @click="toggleWindow">💬</button>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted } from 'vue';
import ProductCard from './ProductCard.vue';
import { useTracker } from '../composables/useTracker';
import { marked } from 'marked';

const renderer = new marked.Renderer();
renderer.link = function(token) {
  return `<a target="_blank" href="${token.href}" title="${token.title || ''}">${token.text}</a>`;
};
marked.setOptions({ renderer });

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
  { type: 'text', text: "Hi! 👋 I'm your AI Assistant. How can I help you today?", sender: 'ai' }
]);
const messagesContainer = ref(null);
let socket = null;

// Auto-scroll
watch(chatMessages, async () => {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
}, { deep: true });

const toggleWindow = () => {
  isOpen.value = !isOpen.value;
};

const renderMarkdown = (text) => {
  if (!text) return '';
  // Marked parses markdown into safe HTML
  return marked.parse(text);
};

// Implement Nudge logic connected to tracker
const triggerNudge = () => {
  if (!isOpen.value) {
    toggleWindow();
    chatMessages.value.push({
      type: 'text',
      text: "Hello! I noticed you are exploring our site. Would you like a quick overview or have any questions I can answer right away?",
      sender: 'ai'
    });
  }
};
setNudgeCallback(triggerNudge);

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
};

onMounted(() => {
  loadBranding();
  // Connect immediately — no delay needed
  connectWebSocket();
});
</script>

<style scoped>
#cf-chat-container { 
  position: fixed; 
  bottom: 30px; 
  right: 30px; 
  z-index: 999999; 
  font-family: 'Inter', sans-serif; 
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
#cf-chat-button:hover { transform: scale(1.1); }

/* Changed display from block/none to flex with v-show logic managing it naturally */
#cf-chat-window {
  display: flex;
  width: 460px;
  height: 760px;
  background: #ffffff;
  border-radius: 20px;
  box-shadow: 0 12px 50px rgba(0,0,0,0.18);
  flex-direction: column;
  overflow: hidden;
  margin-bottom: 20px;
  border: 1px solid #eaeaea;
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

.header-title {
  display: flex; 
  align-items: center; 
  gap: 10px;
}

.status-dot {
  width: 10px; 
  height: 10px; 
  background: #28a745; 
  border-radius: 50%; 
  box-shadow: 0 0 5px #28a745;
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
}
#cf-close-btn:hover { background: rgba(255,255,255,0.4); }

#cf-chat-messages { 
  flex: 1; 
  padding: 20px; 
  overflow-y: auto; 
  display: flex; 
  flex-direction: column; 
  gap: 15px; 
  background: #fcfcfc; 
  scroll-behavior: smooth; 
}

#cf-chat-input-area { 
  display: flex; 
  border-top: 1px solid #f0f0f0; 
  padding: 15px; 
  background: white; 
  align-items: center; 
  gap: 10px; 
}

#cf-chat-input { 
  flex: 1; 
  padding: 14px 22px; 
  border: 1px solid #e1e1e1; 
  border-radius: 25px; 
  outline: none; 
  font-size: 15px; 
  background: #f8f9fa; 
  transition: border 0.2s; 
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

/* Markdown Specific Styles inside AI Messages */
.markdown-body :deep(p) {
  margin: 0 0 10px 0;
}
.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown-body :deep(a) {
  color: #007bff;
  text-decoration: none;
  font-weight: 600;
  transition: color 0.2s;
}
.markdown-body :deep(a:hover) {
  color: #0056b3;
  text-decoration: underline;
}
.markdown-body :deep(ul), .markdown-body :deep(ol) {
  margin: 10px 0;
  padding-left: 20px;
}
.markdown-body :deep(li) {
  margin-bottom: 6px;
}
</style>
