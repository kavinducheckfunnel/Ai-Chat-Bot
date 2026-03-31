<template>
  <div class="wizard-shell">
    <!-- Left: Steps -->
    <div class="wizard-left">
      <div class="wizard-top">
        <div class="brand">
          <div class="brand-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="url(#wg)"/>
              <defs>
                <linearGradient id="wg" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#A5B4FC"/>
                  <stop offset="100%" stop-color="#C4B5FD"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <span class="brand-name">Checkfunnel</span>
        </div>

        <!-- Step dots -->
        <div class="step-dots">
          <span v-for="n in 4" :key="n" class="dot" :class="{ active: step >= n, current: step === n }"></span>
        </div>
      </div>

      <!-- Step content -->
      <div class="step-content">

        <!-- Step 1: Goal -->
        <div v-if="step === 1" class="step-panel">
          <h1 class="step-title">What should <span class="brand-accent">{{ clientName }}</span> do first?</h1>

          <div class="goal-cards">
            <button
              v-for="goal in goals"
              :key="goal.value"
              class="goal-card"
              :class="{ selected: form.primary_goal === goal.value }"
              @click="form.primary_goal = goal.value"
            >
              <span class="goal-icon">{{ goal.icon }}</span>
              {{ goal.label }}
            </button>
          </div>

          <div class="step-footer">
            <button class="btn-next" :disabled="!form.primary_goal" @click="goNext">Next</button>
          </div>
        </div>

        <!-- Step 2: Website URL -->
        <div v-if="step === 2" class="step-panel">
          <h1 class="step-title">Train your chatbot on your website</h1>
          <p class="step-sub">Paste your website URL and we'll automatically learn your content.</p>

          <div class="url-input-row">
            <input
              v-model="form.domain_url"
              type="url"
              class="url-input"
              placeholder="https://yoursite.com/"
              @keyup.enter="triggerScrape"
            />
            <button class="btn-scrape" @click="triggerScrape" :disabled="scraping || !form.domain_url">
              <span v-if="scraping" class="mini-spinner"></span>
              <span v-else>Train</span>
            </button>
          </div>

          <!-- Progress bar -->
          <div v-if="scraping || scrapeStatus === 'DONE' || scrapeStatus === 'FAILED'" class="scrape-progress">
            <div class="progress-header">
              <span class="progress-label">
                <span v-if="scraping">Scanning pages…</span>
                <span v-else-if="scrapeStatus === 'DONE'">Training complete</span>
                <span v-else-if="scrapeStatus === 'FAILED'">Training failed — try again</span>
              </span>
              <span class="progress-count" v-if="scrapePages > 0">{{ scrapePages }} pages</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :class="{ done: scrapeStatus === 'DONE', failed: scrapeStatus === 'FAILED' }" :style="{ width: progressPct + '%' }"></div>
            </div>
          </div>

          <div class="checklist">
            <div class="check-item" :class="{ done: !!form.domain_url }">
              <svg v-if="!!form.domain_url" width="14" height="14" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#22c55e"/><path d="M8 12l3 3 5-5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              <span v-else class="check-circle"></span>
              Set website URL
            </div>
            <div class="check-item" :class="{ done: scrapeStatus === 'DONE' }">
              <svg v-if="scrapeStatus === 'DONE'" width="14" height="14" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#22c55e"/><path d="M8 12l3 3 5-5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              <span v-else class="check-circle"></span>
              Train on content
            </div>
          </div>

          <div class="step-footer">
            <button class="btn-back" @click="step--">Back</button>
            <button class="btn-next" @click="goNext">
              {{ scrapeStatus === 'DONE' ? 'Next' : 'Continue without training' }}
            </button>
          </div>
        </div>

        <!-- Step 3: Chatbot name & color (static branding only, no tone/instructions) -->
        <div v-if="step === 3" class="step-panel">
          <h1 class="step-title">Set up your chatbot</h1>
          <p class="step-sub">Give your chatbot a name and pick its accent color.</p>

          <div class="field">
            <label>Chatbot name</label>
            <input v-model="form.chatbot_name" type="text" class="text-input" placeholder="AI Assistant" maxlength="60" />
          </div>

          <div class="field">
            <label>Notification email</label>
            <input v-model="form.notification_email" type="email" class="text-input" placeholder="you@company.com" />
          </div>

          <div class="step-footer">
            <button class="btn-back" @click="step--">Back</button>
            <button class="btn-next" @click="goNext">Next</button>
          </div>
        </div>

        <!-- Step 4: Brand theme & color -->
        <div v-if="step === 4" class="step-panel">
          <h1 class="step-title">Make it feel like your brand</h1>
          <p class="step-sub">We matched the style to your site. Adjust it if you'd like.</p>

          <div class="field">
            <label>Theme</label>
            <div class="theme-cards">
              <button
                class="theme-card"
                :class="{ selected: form.chatbot_theme === 'light' }"
                @click="form.chatbot_theme = 'light'"
              >
                <div class="theme-preview light-preview">
                  <div class="preview-bubble light-bubble"></div>
                </div>
                <span>Light</span>
              </button>
              <button
                class="theme-card"
                :class="{ selected: form.chatbot_theme === 'dark' }"
                @click="form.chatbot_theme = 'dark'"
              >
                <div class="theme-preview dark-preview">
                  <div class="preview-bubble dark-bubble"></div>
                </div>
                <span>Dark</span>
              </button>
            </div>
          </div>

          <div class="field">
            <label>Accent color</label>
            <div class="color-row">
              <button
                v-for="c in presetColors"
                :key="c"
                class="color-swatch"
                :class="{ selected: form.chatbot_color === c }"
                :style="{ background: c }"
                @click="form.chatbot_color = c"
              ></button>
              <div class="color-custom">
                <input type="color" v-model="form.chatbot_color" class="color-picker" />
                <span class="color-hex">{{ form.chatbot_color }}</span>
              </div>
            </div>
          </div>

          <div class="step-footer">
            <button class="btn-back" @click="step--">Back</button>
            <button class="btn-next btn-finish" :disabled="saving" @click="finish">
              <span v-if="saving" class="mini-spinner"></span>
              <span v-else>Finish setup</span>
            </button>
          </div>
        </div>

      </div>
    </div>

    <!-- Right: Widget preview -->
    <div class="wizard-right" :style="previewBg">
      <div class="preview-label">Widget preview</div>

      <!-- Floating chat bubble -->
      <div class="widget-bubble" :style="{ background: form.chatbot_color }">
        <svg width="22" height="22" fill="none" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" fill="white"/></svg>
      </div>

      <!-- Chat panel preview -->
      <div class="chat-panel" :class="form.chatbot_theme === 'dark' ? 'chat-dark' : 'chat-light'">
        <div class="chat-header" :style="{ background: form.chatbot_color }">
          <div class="agent-dot"></div>
          <span>{{ form.chatbot_name || 'AI Assistant' }}</span>
        </div>

        <div class="chat-body">
          <div class="chat-greeting">
            <p class="greeting-big">Hello! 👋</p>
            <p class="greeting-sub">{{ greetingText }}</p>
          </div>
        </div>

        <div class="chat-cta">
          <button class="cta-btn primary" :style="{ borderColor: form.chatbot_color, color: form.chatbot_color }">Let's chat</button>
          <button class="cta-btn secondary">Just browsing</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminApi, WIDGET_URL } from '../composables/useAdminApi'

const router = useRouter()
const api = useAdminApi()

const step = ref(1)
const saving = ref(false)
const scraping = ref(false)
const scrapeStatus = ref('')
const scrapePages = ref(0)
let scrapeTimer = null

const client = ref(null)
const clientName = computed(() => client.value?.name || 'your chatbot')

const form = ref({
  primary_goal: '',
  domain_url: '',
  chatbot_name: 'AI Assistant',
  notification_email: '',
  chatbot_theme: 'dark',
  chatbot_color: '#6366F1',
})

const goals = [
  { value: 'sales',   label: 'Grow sales',        icon: '📈' },
  { value: 'support', label: 'Automate support',   icon: '🤖' },
  { value: 'leads',   label: 'Generate leads',     icon: '🎯' },
]

const presetColors = ['#ffffff', '#3B82F6', '#22c55e', '#ef4444', '#6366f1', '#f59e0b']

const progressPct = computed(() => {
  if (scrapeStatus.value === 'DONE') return 100
  if (scrapeStatus.value === 'FAILED') return 100
  if (scraping.value) return Math.min(90, scrapePages.value * 5 + 10)
  return 0
})

const greetingText = computed(() => {
  if (form.value.primary_goal === 'sales') return 'Ready to find the perfect solution for you?'
  if (form.value.primary_goal === 'support') return 'Need a hand? We\'ll point you in the right direction.'
  return 'Need a hand? We\'ll point you in the right direction.'
})

const previewBg = computed(() => ({
  background: form.value.chatbot_theme === 'dark'
    ? 'linear-gradient(135deg, #0f0f0f 0%, #1a1a2e 50%, #16213e 100%)'
    : 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
}))

onMounted(async () => {
  try {
    const c = await api.getPortalClient()
    if (c) {
      client.value = c
      form.value.domain_url = c.domain_url || ''
      form.value.chatbot_name = c.chatbot_name || 'AI Assistant'
      form.value.notification_email = c.notification_email || ''
      form.value.chatbot_theme = c.chatbot_theme || 'dark'
      form.value.chatbot_color = c.chatbot_color || '#6366F1'
      form.value.primary_goal = c.primary_goal || ''
      scrapeStatus.value = c.ingestion_status === 'DONE' ? 'DONE' : ''
      scrapePages.value = c.total_pages_ingested || 0
    }
  } catch {}
})

async function saveStep() {
  if (!client.value) return
  try {
    await api.updatePortalClient(client.value.id, {
      primary_goal: form.value.primary_goal,
      domain_url: form.value.domain_url,
      chatbot_name: form.value.chatbot_name,
      notification_email: form.value.notification_email,
      chatbot_theme: form.value.chatbot_theme,
      chatbot_color: form.value.chatbot_color,
    })
  } catch {}
}

async function goNext() {
  await saveStep()
  step.value++
}

async function triggerScrape() {
  if (!client.value || !form.value.domain_url) return
  scraping.value = true
  scrapeStatus.value = 'RUNNING'
  scrapePages.value = 0
  try {
    await api.updatePortalClient(client.value.id, { domain_url: form.value.domain_url })
    await api.triggerScrape(client.value.id)
    pollScrape()
  } catch {
    scraping.value = false
    scrapeStatus.value = 'FAILED'
  }
}

function pollScrape() {
  scrapeTimer = setInterval(async () => {
    try {
      const progress = await api.getScrapeProgress(client.value.id)
      scrapePages.value = progress.pages_scraped || 0
      if (progress.status === 'DONE' || progress.status === 'FAILED') {
        scrapeStatus.value = progress.status
        scraping.value = false
        clearInterval(scrapeTimer)
      }
    } catch {}
  }, 1500)
}

async function finish() {
  saving.value = true
  try {
    await api.updatePortalClient(client.value.id, {
      ...form.value,
      onboarding_complete: true,
    })
    router.push('/portal/inbox')
  } catch {
    saving.value = false
  }
}
</script>

<style scoped>
* { box-sizing: border-box; }

.wizard-shell {
  display: flex;
  height: 100vh;
  font-family: 'Inter', -apple-system, sans-serif;
}

/* ── Left panel ───────────────────────────────────────────────────────────── */
.wizard-left {
  width: 52%;
  min-width: 480px;
  background: #0d0d0d;
  display: flex;
  flex-direction: column;
  padding: 32px 48px;
  overflow-y: auto;
}

.wizard-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 48px;
}

.brand { display: flex; align-items: center; gap: 9px; }

.brand-icon {
  width: 32px; height: 32px;
  background: rgba(99,102,241,0.12);
  border: 1px solid rgba(99,102,241,0.22);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
}

.brand-name { font-size: 15px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.3px; }

.step-dots { display: flex; gap: 6px; align-items: center; }
.dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #1e293b;
  transition: all 0.2s;
}
.dot.active { background: #6366f1; }
.dot.current { width: 24px; border-radius: 4px; }

.step-content { flex: 1; display: flex; flex-direction: column; justify-content: center; }

.step-panel { display: flex; flex-direction: column; gap: 28px; max-width: 440px; }

.step-title {
  font-size: 28px;
  font-weight: 700;
  color: #f1f5f9;
  line-height: 1.25;
  letter-spacing: -0.5px;
}

.brand-accent { color: #a5b4fc; }

.step-sub { font-size: 14px; color: #64748b; line-height: 1.6; margin-top: -16px; }

/* Goal cards */
.goal-cards { display: flex; flex-direction: column; gap: 10px; }

.goal-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  background: #161616;
  border: 1.5px solid #1e293b;
  border-radius: 14px;
  font-size: 15px;
  font-weight: 500;
  color: #94a3b8;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s;
}

.goal-card:hover { border-color: #334155; color: #cbd5e1; background: #1a1a1a; }
.goal-card.selected { border-color: #6366f1; color: #f1f5f9; background: rgba(99,102,241,0.08); }

.goal-icon { font-size: 20px; }

/* URL input */
.url-input-row { display: flex; gap: 10px; }

.url-input {
  flex: 1;
  padding: 12px 16px;
  background: #161616;
  border: 1.5px solid #1e293b;
  border-radius: 10px;
  font-size: 14px;
  color: #f1f5f9;
  outline: none;
  transition: border-color 0.15s;
}
.url-input:focus { border-color: #6366f1; }
.url-input::placeholder { color: #334155; }

.btn-scrape {
  padding: 12px 22px;
  background: #6366f1;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  color: white;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.15s;
}
.btn-scrape:disabled { opacity: 0.5; cursor: not-allowed; }

/* Progress bar */
.scrape-progress { display: flex; flex-direction: column; gap: 8px; }
.progress-header { display: flex; justify-content: space-between; align-items: center; }
.progress-label { font-size: 13px; color: #64748b; }
.progress-count { font-size: 12px; color: #a5b4fc; font-weight: 600; }
.progress-bar { height: 4px; background: #1e293b; border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: #6366f1; border-radius: 2px; transition: width 0.5s ease; }
.progress-fill.done { background: #22c55e; }
.progress-fill.failed { background: #ef4444; }

/* Checklist */
.checklist { display: flex; flex-direction: column; gap: 10px; }
.check-item { display: flex; align-items: center; gap: 9px; font-size: 13px; color: #64748b; }
.check-item.done { color: #22c55e; }
.check-circle { width: 14px; height: 14px; border: 1.5px solid #334155; border-radius: 50%; }

/* Fields */
.field { display: flex; flex-direction: column; gap: 8px; }
.field label { font-size: 13px; font-weight: 600; color: #94a3b8; }
.text-input {
  padding: 11px 14px;
  background: #161616;
  border: 1.5px solid #1e293b;
  border-radius: 10px;
  font-size: 14px;
  color: #f1f5f9;
  outline: none;
  transition: border-color 0.15s;
}
.text-input:focus { border-color: #6366f1; }
.text-input::placeholder { color: #334155; }

/* Theme cards */
.theme-cards { display: flex; gap: 14px; }
.theme-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 16px;
  background: #161616;
  border: 1.5px solid #1e293b;
  border-radius: 12px;
  cursor: pointer;
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s;
}
.theme-card:hover { border-color: #334155; color: #cbd5e1; }
.theme-card.selected { border-color: #6366f1; color: #a5b4fc; background: rgba(99,102,241,0.06); }

.theme-preview {
  width: 80px; height: 52px; border-radius: 8px;
  display: flex; align-items: flex-end; justify-content: flex-end;
  padding: 6px; position: relative;
}
.light-preview { background: #f8fafc; border: 1px solid #e2e8f0; }
.dark-preview { background: #0f0f1a; border: 1px solid #1e293b; }
.preview-bubble { width: 22px; height: 22px; border-radius: 50%; }
.light-bubble { background: #1e293b; }
.dark-bubble { background: #6366f1; }

/* Colors */
.color-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.color-swatch {
  width: 30px; height: 30px; border-radius: 50%;
  border: 2.5px solid transparent;
  cursor: pointer; transition: all 0.15s;
  outline: 2px solid transparent;
}
.color-swatch.selected { outline: 2px solid #6366f1; outline-offset: 2px; }
.color-custom { display: flex; align-items: center; gap: 8px; }
.color-picker { width: 30px; height: 30px; border: none; border-radius: 50%; cursor: pointer; padding: 0; background: none; }
.color-hex { font-size: 12px; color: #64748b; font-family: monospace; }

/* Footer buttons */
.step-footer { display: flex; gap: 10px; align-items: center; margin-top: 8px; }
.btn-next {
  padding: 12px 28px;
  background: #1e293b;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
  cursor: pointer;
  transition: all 0.15s;
  display: flex; align-items: center; gap: 8px;
}
.btn-next:hover { background: #334155; }
.btn-next:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-finish { background: #6366f1; }
.btn-finish:hover { background: #4f46e5; }

.btn-back {
  padding: 12px 18px;
  background: none;
  border: none;
  font-size: 14px;
  font-weight: 500;
  color: #475569;
  cursor: pointer;
  transition: color 0.15s;
}
.btn-back:hover { color: #94a3b8; }

.mini-spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Right panel: widget preview ──────────────────────────────────────────── */
.wizard-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: background 0.4s;
}

.preview-label {
  position: absolute;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  font-weight: 600;
  color: rgba(255,255,255,0.35);
  background: rgba(255,255,255,0.06);
  padding: 4px 14px;
  border-radius: 20px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  white-space: nowrap;
}

.widget-bubble {
  position: absolute;
  bottom: 40px;
  right: 40px;
  width: 52px; height: 52px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  transition: background 0.3s;
  cursor: pointer;
}

.chat-panel {
  width: 300px;
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 24px 64px rgba(0,0,0,0.5);
}

.chat-dark { background: #111827; }
.chat-light { background: #ffffff; }

.chat-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 18px;
  font-size: 14px;
  font-weight: 600;
  color: white;
}

.agent-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: rgba(255,255,255,0.8);
}

.chat-body {
  padding: 24px 18px 16px;
}

.chat-greeting { text-align: center; }
.greeting-big {
  font-size: 26px; font-weight: 700;
  margin-bottom: 8px;
}
.chat-dark .greeting-big { color: #f1f5f9; }
.chat-light .greeting-big { color: #0f172a; }

.greeting-sub {
  font-size: 13px; line-height: 1.5;
}
.chat-dark .greeting-sub { color: #64748b; }
.chat-light .greeting-sub { color: #475569; }

.chat-cta {
  padding: 0 18px 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cta-btn {
  padding: 11px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
  text-align: center;
  width: 100%;
}

.cta-btn.primary {
  background: transparent;
  border: 1.5px solid;
}

.cta-btn.secondary {
  border: 1.5px solid transparent;
  background: rgba(255,255,255,0.06);
}
.chat-dark .cta-btn.secondary { color: #94a3b8; border-color: #1e293b; }
.chat-light .cta-btn.secondary { color: #475569; border-color: #e2e8f0; background: #f8fafc; }
</style>
