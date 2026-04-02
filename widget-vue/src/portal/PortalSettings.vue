<template>
  <div class="settings-page">
    <div class="page-header">
      <h1 class="page-title">Settings</h1>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'channels' }" @click="activeTab = 'channels'">Channels & embed</button>
      <button class="tab" :class="{ active: activeTab === 'chatbot' }" @click="activeTab = 'chatbot'">Chatbot</button>
      <button class="tab" :class="{ active: activeTab === 'knowledge' }" @click="activeTab = 'knowledge'">Knowledge base</button>
    </div>

    <!-- ── Channels & embed ────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'channels'" class="tab-content">
      <div class="section-card">
        <div class="section-header">
          <div class="section-title-row">
            <div class="channel-icon web-icon">
              <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path d="M2 12h20M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            </div>
            <div>
              <h2 class="section-title">Website</h2>
              <p class="section-sub">Add the chatbot to any website with a single code snippet.</p>
            </div>
            <div class="status-badge active">Active</div>
          </div>
        </div>

        <div class="embed-box">
          <h3 class="embed-title">Choose how to add the widget code</h3>

          <!-- Format tabs -->
          <div class="format-tabs">
            <button v-for="f in formats" :key="f.id" class="format-tab" :class="{ active: embedFormat === f.id }" @click="embedFormat = f.id">
              <span class="format-icon" v-html="f.icon"></span>
              {{ f.label }}
            </button>
          </div>

          <p class="embed-instruction" v-if="embedFormat === 'wordpress'">Paste into your theme's <code>functions.php</code>, or use the "Insert Headers and Footers" plugin → Footer section.</p>
          <p class="embed-instruction" v-else-if="embedFormat === 'react'">Drop this component anywhere in your React app tree.</p>
          <p class="embed-instruction" v-else>Paste before the <code>&lt;/body&gt;</code> tag on every page.</p>

          <!-- Code block -->
          <div class="code-block" v-if="props.client">
            <pre class="code-pre"><code>{{ embedCode }}</code></pre>
            <button class="copy-btn" @click="copyCode" :class="{ copied }">
              <svg v-if="!copied" width="14" height="14" fill="none" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" stroke-width="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
              <svg v-else width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke="#22c55e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              {{ copied ? 'Copied!' : 'Copy code' }}
            </button>
          </div>
          <div class="code-block skeleton" v-else>
            <div class="skeleton-line"></div>
            <div class="skeleton-line short"></div>
            <div class="skeleton-line"></div>
          </div>
        </div>
      </div>

      <!-- Other channels (off) -->
      <div class="channels-list">
        <div class="channel-item">
          <div class="channel-icon messenger-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 2C6.477 2 2 6.145 2 11.243c0 2.842 1.358 5.38 3.504 7.106V22l3.36-1.847A10.94 10.94 0 0012 20.486c5.523 0 10-4.145 10-9.243S17.523 2 12 2z" fill="#0084FF"/></svg>
          </div>
          <div class="channel-meta">
            <span class="channel-name">Messenger</span>
            <span class="channel-status off">OFF</span>
          </div>
          <button class="btn-configure" disabled>Configure</button>
        </div>
        <div class="channel-item">
          <div class="channel-icon twilio-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#F22F46"/><circle cx="8.5" cy="8.5" r="1.5" fill="white"/><circle cx="15.5" cy="8.5" r="1.5" fill="white"/><circle cx="8.5" cy="15.5" r="1.5" fill="white"/><circle cx="15.5" cy="15.5" r="1.5" fill="white"/></svg>
          </div>
          <div class="channel-meta">
            <span class="channel-name">Twilio SMS</span>
            <span class="channel-status off">OFF</span>
          </div>
          <button class="btn-configure" disabled>Configure</button>
        </div>
      </div>
    </div>

    <!-- ── Chatbot config ──────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'chatbot'" class="tab-content">
      <div class="section-card">
        <h2 class="section-title">Chatbot appearance</h2>
        <div class="form-grid">
          <div class="field">
            <label>Chatbot name</label>
            <input v-model="form.chatbot_name" type="text" class="input" placeholder="AI Assistant" maxlength="60" />
          </div>
          <div class="field">
            <label>Notification email</label>
            <input v-model="form.notification_email" type="email" class="input" placeholder="you@company.com" />
          </div>
        </div>

        <div class="field">
          <label>Theme</label>
          <div class="theme-row">
            <button class="theme-btn" :class="{ selected: form.chatbot_theme === 'dark' }" @click="form.chatbot_theme = 'dark'">
              <span class="theme-dot dark-dot"></span> Dark
            </button>
            <button class="theme-btn" :class="{ selected: form.chatbot_theme === 'light' }" @click="form.chatbot_theme = 'light'">
              <span class="theme-dot light-dot"></span> Light
            </button>
          </div>
        </div>

        <div class="field">
          <label>Accent color</label>
          <div class="color-row">
            <button v-for="c in presetColors" :key="c" class="color-swatch" :class="{ selected: form.chatbot_color === c }" :style="{ background: c }" @click="form.chatbot_color = c"></button>
            <div class="color-custom">
              <input type="color" v-model="form.chatbot_color" class="color-picker" />
              <span class="color-hex">{{ form.chatbot_color }}</span>
            </div>
          </div>
        </div>

        <div class="field">
          <label>CTA message</label>
          <input v-model="form.cta_message" type="text" class="input" placeholder="You're clearly ready — grab your exclusive discount:" />
        </div>

        <button class="btn-save" :disabled="saving" @click="saveConfig">
          <span v-if="saving" class="mini-spinner"></span>
          <span v-else>Save changes</span>
        </button>
        <p v-if="saved" class="save-success">Changes saved.</p>
      </div>
    </div>

    <!-- ── Knowledge base ──────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'knowledge'" class="tab-content">
      <div class="section-card">
        <h2 class="section-title">Knowledge base</h2>
        <p class="section-sub">Your chatbot learns from your website content. Add your URL below to train it.</p>

        <div class="field">
          <label>Website URL</label>
          <div class="url-row">
            <input v-model="form.domain_url" type="url" class="input" placeholder="https://yoursite.com/" />
            <button class="btn-train" @click="triggerScrape" :disabled="scraping">
              <span v-if="scraping" class="mini-spinner"></span>
              <span v-else>Re-train</span>
            </button>
          </div>
        </div>

        <!-- Status -->
        <div v-if="props.client" class="scrape-status-row">
          <div class="status-indicator" :class="scrapeStatusClass">
            <span class="indicator-dot"></span>
            {{ scrapeStatusLabel }}
          </div>
          <span class="pages-count" v-if="props.client.total_pages_ingested > 0">
            {{ props.client.total_pages_ingested }} pages indexed
          </span>
        </div>

        <!-- Progress bar -->
        <div v-if="scraping" class="progress-wrap">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progressPct + '%' }"></div>
          </div>
          <span class="progress-text">Scanning pages…</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAdminApi, WIDGET_URL } from '../composables/useAdminApi'
import { generateEmbedCode } from './embedCodeGenerator'

const props = defineProps({ client: Object })
const emit = defineEmits(['client-updated'])
const api = useAdminApi()

const activeTab = ref('channels')
const embedFormat = ref('html')
const copied = ref(false)
const saving = ref(false)
const saved = ref(false)
const scraping = ref(false)
const scrapePages = ref(0)
let scrapeTimer = null

const backendUrl = WIDGET_URL.replace('/widget/widget.js', '')

const form = ref({
  chatbot_name: '',
  chatbot_color: '#6366F1',
  chatbot_theme: 'dark',
  notification_email: '',
  cta_message: '',
  domain_url: '',
})

const presetColors = ['#ffffff', '#3B82F6', '#22c55e', '#ef4444', '#6366f1', '#f59e0b']

const formats = [
  { id: 'html',      label: 'HTML',      icon: '<span style="color:#e34c26;font-weight:700;font-size:12px">HTML</span>' },
  { id: 'wordpress', label: 'WordPress', icon: '<span style="color:#21759b;font-weight:700;font-size:12px">WP</span>' },
  { id: 'react',     label: 'React',     icon: '<span style="color:#61dafb;font-weight:700;font-size:12px">⚛</span>' },
]

const embedCode = computed(() => {
  if (!props.client) return ''
  return generateEmbedCode(
    props.client.id,
    backendUrl,
    form.value.chatbot_color || '#6366f1',
    form.value.chatbot_name || 'AI Assistant',
    embedFormat.value,
  )
})


// Sync form with client prop
watch(() => props.client, (c) => {
  if (!c) return
  form.value.chatbot_name = c.chatbot_name || ''
  form.value.chatbot_color = c.chatbot_color || '#6366F1'
  form.value.chatbot_theme = c.chatbot_theme || 'dark'
  form.value.notification_email = c.notification_email || ''
  form.value.cta_message = c.cta_message || ''
  form.value.domain_url = c.domain_url || ''
  scrapePages.value = c.total_pages_ingested || 0
}, { immediate: true })

async function copyCode() {
  try {
    await navigator.clipboard.writeText(embedCode.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {}
}

async function saveConfig() {
  if (!props.client) return
  saving.value = true
  try {
    const updated = await api.updatePortalClient(props.client.id, form.value)
    emit('client-updated', updated)
    saved.value = true
    setTimeout(() => { saved.value = false }, 3000)
  } catch {} finally {
    saving.value = false
  }
}

async function triggerScrape() {
  if (!props.client) return
  scraping.value = true
  try {
    await api.updatePortalClient(props.client.id, { domain_url: form.value.domain_url })
    await api.triggerScrape(props.client.id)
    scrapeTimer = setInterval(async () => {
      try {
        const p = await api.getScrapeProgress(props.client.id)
        scrapePages.value = p.pages_scraped || 0
        if (p.status === 'DONE' || p.status === 'FAILED') {
          scraping.value = false
          emit('client-updated', { ingestion_status: p.status, total_pages_ingested: scrapePages.value })
          clearInterval(scrapeTimer)
        }
      } catch {}
    }, 1500)
  } catch {
    scraping.value = false
  }
}

const progressPct = computed(() => Math.min(90, scrapePages.value * 5 + 15))

const scrapeStatusClass = computed(() => {
  const s = props.client?.ingestion_status
  if (s === 'DONE') return 'status-done'
  if (s === 'RUNNING') return 'status-running'
  if (s === 'FAILED') return 'status-failed'
  return 'status-pending'
})

const scrapeStatusLabel = computed(() => {
  const s = props.client?.ingestion_status
  if (s === 'DONE') return 'Training complete'
  if (s === 'RUNNING') return 'Training in progress…'
  if (s === 'FAILED') return 'Training failed'
  return 'Not trained yet'
})
</script>

<style scoped>
* { box-sizing: border-box; }

.settings-page {
  padding: 32px 36px;
  max-width: 860px;
  font-family: 'Inter', -apple-system, sans-serif;
}

.page-header { margin-bottom: 24px; }
.page-title { font-size: 22px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.4px; }

/* Tabs */
.tabs {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid rgba(255,255,255,0.07);
  margin-bottom: 28px;
}

.tab {
  padding: 10px 18px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: 13px;
  font-weight: 500;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s;
  margin-bottom: -1px;
}
.tab:hover { color: #94a3b8; }
.tab.active { color: #a5b4fc; border-bottom-color: #6366f1; }

.tab-content { display: flex; flex-direction: column; gap: 16px; }

/* Section cards */
.section-card {
  background: #161616;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-header { }

.section-title-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.channel-icon {
  width: 36px; height: 36px;
  border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.web-icon { background: rgba(99,102,241,0.12); color: #a5b4fc; }
.messenger-icon { background: rgba(0,132,255,0.1); }
.twilio-icon { background: rgba(242,47,70,0.1); }

.section-title { font-size: 15px; font-weight: 600; color: #f1f5f9; }
.section-sub { font-size: 12px; color: #475569; margin-top: 3px; }

.status-badge {
  margin-left: auto;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
}
.status-badge.active { background: rgba(34,197,94,0.1); color: #22c55e; border: 1px solid rgba(34,197,94,0.2); }

/* Embed box */
.embed-box {
  background: #0d0d0d;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.embed-title { font-size: 14px; font-weight: 600; color: #e2e8f0; }

.format-tabs { display: flex; gap: 6px; }
.format-tab {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 14px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  transition: all 0.12s;
}
.format-tab:hover { background: rgba(255,255,255,0.07); color: #94a3b8; }
.format-tab.active { background: rgba(99,102,241,0.12); border-color: rgba(99,102,241,0.3); color: #a5b4fc; }
.format-icon { display: flex; align-items: center; }

.embed-instruction { font-size: 12px; color: #475569; }
.embed-instruction code { background: rgba(255,255,255,0.07); padding: 1px 5px; border-radius: 4px; font-family: monospace; color: #94a3b8; }

.code-block {
  background: #0a0a0a;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 16px;
  position: relative;
}

.code-pre {
  margin: 0;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.7;
  color: #94a3b8;
  white-space: pre;
  overflow-x: auto;
}

.code-block code { color: #a5b4fc; }

.copy-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 14px;
  padding: 8px 16px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.15s;
}
.copy-btn:hover { background: rgba(255,255,255,0.1); color: #f1f5f9; }
.copy-btn.copied { color: #22c55e; border-color: rgba(34,197,94,0.3); background: rgba(34,197,94,0.08); }

.skeleton { min-height: 120px; }
.skeleton-line { height: 12px; background: rgba(255,255,255,0.05); border-radius: 4px; margin-bottom: 10px; }
.skeleton-line.short { width: 60%; }

/* Channels list */
.channels-list { display: flex; flex-direction: column; gap: 10px; }

.channel-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  background: #161616;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
}

.channel-meta { flex: 1; display: flex; align-items: center; gap: 10px; }
.channel-name { font-size: 14px; font-weight: 500; color: #94a3b8; }
.channel-status { font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 4px; }
.channel-status.off { background: rgba(255,255,255,0.05); color: #475569; }

.btn-configure {
  padding: 6px 14px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 7px;
  font-size: 12px;
  font-weight: 500;
  color: #475569;
  cursor: not-allowed;
}

/* Form fields */
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

.field { display: flex; flex-direction: column; gap: 7px; }
.field label { font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; }

.input {
  padding: 10px 13px;
  background: #0d0d0d;
  border: 1px solid rgba(255,255,255,0.09);
  border-radius: 9px;
  font-size: 14px;
  color: #f1f5f9;
  outline: none;
  transition: border-color 0.15s;
  width: 100%;
}
.input:focus { border-color: #6366f1; }
.input::placeholder { color: #334155; }

/* Theme */
.theme-row { display: flex; gap: 10px; }
.theme-btn {
  display: flex; align-items: center; gap: 8px;
  padding: 9px 18px;
  background: #0d0d0d;
  border: 1.5px solid rgba(255,255,255,0.09);
  border-radius: 9px;
  font-size: 13px; font-weight: 500; color: #64748b;
  cursor: pointer; transition: all 0.12s;
}
.theme-btn:hover { border-color: #334155; color: #94a3b8; }
.theme-btn.selected { border-color: #6366f1; color: #a5b4fc; background: rgba(99,102,241,0.08); }
.theme-dot { width: 12px; height: 12px; border-radius: 50%; }
.dark-dot { background: #0f172a; border: 1px solid #334155; }
.light-dot { background: #f8fafc; border: 1px solid #cbd5e1; }

/* Colors */
.color-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.color-swatch { width: 26px; height: 26px; border-radius: 50%; border: 2px solid transparent; cursor: pointer; transition: all 0.12s; outline: 2px solid transparent; }
.color-swatch.selected { outline: 2px solid #6366f1; outline-offset: 2px; }
.color-custom { display: flex; align-items: center; gap: 7px; }
.color-picker { width: 26px; height: 26px; border: none; border-radius: 50%; cursor: pointer; padding: 0; background: none; }
.color-hex { font-size: 11px; color: #475569; font-family: monospace; }

/* Save */
.btn-save {
  align-self: flex-start;
  padding: 10px 24px;
  background: #6366f1;
  border: none;
  border-radius: 9px;
  font-size: 14px; font-weight: 600; color: white;
  cursor: pointer; transition: opacity 0.15s;
  display: flex; align-items: center; gap: 8px;
}
.btn-save:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-save:hover:not(:disabled) { opacity: 0.9; }

.save-success { font-size: 13px; color: #22c55e; margin-top: -8px; }

/* Knowledge base */
.url-row { display: flex; gap: 10px; }
.btn-train {
  padding: 10px 20px;
  background: #6366f1;
  border: none; border-radius: 9px;
  font-size: 13px; font-weight: 600; color: white;
  cursor: pointer; transition: opacity 0.15s;
  white-space: nowrap; display: flex; align-items: center; gap: 6px;
}
.btn-train:disabled { opacity: 0.5; cursor: not-allowed; }

.scrape-status-row { display: flex; align-items: center; gap: 16px; }
.status-indicator { display: flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 500; }
.indicator-dot { width: 8px; height: 8px; border-radius: 50%; }
.status-done .indicator-dot { background: #22c55e; }
.status-running .indicator-dot { background: #6366f1; animation: pulse 1s infinite; }
.status-failed .indicator-dot { background: #ef4444; }
.status-pending .indicator-dot { background: #475569; }
.status-done { color: #22c55e; }
.status-running { color: #a5b4fc; }
.status-failed { color: #ef4444; }
.status-pending { color: #475569; }

.pages-count { font-size: 12px; color: #475569; }

.progress-wrap { display: flex; flex-direction: column; gap: 6px; }
.progress-bar { height: 4px; background: #1e293b; border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: #6366f1; border-radius: 2px; transition: width 0.5s; }
.progress-text { font-size: 12px; color: #475569; }

.mini-spinner {
  width: 13px; height: 13px;
  border: 2px solid rgba(255,255,255,0.25);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
