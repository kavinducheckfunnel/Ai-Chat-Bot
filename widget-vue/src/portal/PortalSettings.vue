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
      <button class="tab" :class="{ active: activeTab === 'integrations' }" @click="activeTab = 'integrations'">Integrations</button>
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

      <!-- Widget feature toggles -->
      <div class="section-card">
        <h2 class="section-title">Widget features</h2>
        <p class="section-sub">Enable or disable interactive features in the chat widget.</p>

        <div class="feature-row">
          <div class="feature-info">
            <span class="feature-name">Voice input</span>
            <span class="feature-desc">Visitors can dictate messages using their microphone (Web Speech API)</span>
          </div>
          <label class="toggle">
            <input type="checkbox" v-model="form.voice_input_enabled" @change="saveConfig">
            <span class="toggle-slider"></span>
          </label>
        </div>

        <div class="feature-row">
          <div class="feature-info">
            <span class="feature-name">Image input</span>
            <span class="feature-desc">Visitors can attach and send images in the chat</span>
          </div>
          <label class="toggle">
            <input type="checkbox" v-model="form.image_input_enabled" @change="saveConfig">
            <span class="toggle-slider"></span>
          </label>
        </div>
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

  <!-- ── Integrations tab ─────────────────────────────────────────────────── -->
  <div v-if="activeTab === 'integrations'" class="tab-content">

    <!-- BYOK -->
    <div class="section-card">
      <div class="section-header">
        <div class="section-title-row">
          <div class="channel-icon" style="background:rgba(168,85,247,0.12);color:#c084fc">
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M21 2H3v16h5v4l4-4h9V2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <div>
            <h2 class="section-title">AI Model (BYOK)</h2>
            <p class="section-sub">Use your own OpenAI, Anthropic or OpenRouter API key instead of the platform default.</p>
          </div>
        </div>
      </div>
      <div class="form-grid">
        <div class="field" style="grid-column:1/-1">
          <label>Provider</label>
          <div class="theme-row">
            <button v-for="p in aiProviders" :key="p.val" class="theme-btn" :class="{ selected: intForm.ai_provider === p.val }" @click="intForm.ai_provider = p.val">{{ p.label }}</button>
          </div>
        </div>
        <div class="field" style="grid-column:1/-1">
          <label>API Key</label>
          <input class="input" type="password" v-model="intForm.ai_api_key" placeholder="sk-… or your OpenRouter key" autocomplete="off" />
        </div>
        <div class="field" style="grid-column:1/-1">
          <label>Model ID</label>
          <input class="input" type="text" v-model="intForm.ai_model" placeholder="e.g. gpt-4o  /  claude-opus-4-6  /  google/gemini-3.1-pro-preview" />
          <span class="field-hint">Leave blank to use the platform default (Gemini 3.1 Pro).</span>
        </div>
      </div>
      <div class="save-row">
        <button class="btn-save" @click="saveIntegrations" :disabled="intSaving">{{ intSaving ? 'Saving…' : intSaved ? '✓ Saved' : 'Save AI settings' }}</button>
      </div>
    </div>

    <!-- WhatsApp -->
    <div class="section-card">
      <div class="section-header">
        <div class="section-title-row">
          <div class="channel-icon" style="background:rgba(37,211,102,0.1);color:#25d366">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
          </div>
          <div>
            <h2 class="section-title">WhatsApp Business</h2>
            <p class="section-sub">Connect your Meta WhatsApp Business number to route chats through the AI.</p>
          </div>
          <div class="status-badge" :class="intForm.whatsapp_enabled ? 'active' : 'inactive'">{{ intForm.whatsapp_enabled ? 'Active' : 'Inactive' }}</div>
        </div>
      </div>
      <div class="form-grid">
        <div class="field" style="grid-column:1/-1">
          <label>Webhook URL (paste this in Meta → Webhooks)</label>
          <div class="code-block" style="padding:10px 14px">
            <code style="font-family:monospace;font-size:12px;color:#a5b4fc">{{ whatsappWebhookUrl }}</code>
          </div>
        </div>
        <div class="field">
          <label>Phone Number ID</label>
          <input class="input" type="text" v-model="intForm.whatsapp_phone_number_id" placeholder="123456789012345" />
        </div>
        <div class="field">
          <label>Verify Token (you choose)</label>
          <input class="input" type="text" v-model="intForm.whatsapp_verify_token" placeholder="my_secure_verify_token" />
        </div>
        <div class="field" style="grid-column:1/-1">
          <label>Access Token</label>
          <input class="input" type="password" v-model="intForm.whatsapp_access_token" placeholder="EAAxxxxxxxxxxxxxxxx" autocomplete="off" />
        </div>
        <div class="field" style="grid-column:1/-1">
          <label>Enable WhatsApp</label>
          <div class="toggle-row">
            <button class="toggle-btn" :class="{ on: intForm.whatsapp_enabled }" @click="intForm.whatsapp_enabled = !intForm.whatsapp_enabled">
              <span class="toggle-knob"></span>
            </button>
            <span class="toggle-lbl">{{ intForm.whatsapp_enabled ? 'Enabled — AI will reply to WhatsApp messages' : 'Disabled' }}</span>
          </div>
        </div>
      </div>
      <div class="save-row">
        <button class="btn-save" @click="saveIntegrations" :disabled="intSaving">{{ intSaving ? 'Saving…' : intSaved ? '✓ Saved' : 'Save WhatsApp settings' }}</button>
      </div>
    </div>

    <!-- Messenger -->
    <div class="section-card">
      <div class="section-header">
        <div class="section-title-row">
          <div class="channel-icon messenger-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 2C6.477 2 2 6.145 2 11.243c0 2.842 1.358 5.38 3.504 7.106V22l3.36-1.847A10.94 10.94 0 0012 20.486c5.523 0 10-4.145 10-9.243S17.523 2 12 2z" fill="#0084FF"/></svg>
          </div>
          <div>
            <h2 class="section-title">Facebook Messenger</h2>
            <p class="section-sub">Connect your Facebook Page to receive and reply to Messenger conversations via AI.</p>
          </div>
          <div class="status-badge" :class="intForm.messenger_enabled ? 'active' : 'inactive'">{{ intForm.messenger_enabled ? 'Active' : 'Inactive' }}</div>
        </div>
      </div>
      <div class="form-grid">
        <div class="field" style="grid-column:1/-1">
          <label>Webhook URL (paste this in Meta → Webhooks)</label>
          <div class="code-block" style="padding:10px 14px">
            <code style="font-family:monospace;font-size:12px;color:#a5b4fc">{{ messengerWebhookUrl }}</code>
          </div>
        </div>
        <div class="field">
          <label>Page ID</label>
          <input class="input" type="text" v-model="intForm.messenger_page_id" placeholder="123456789" />
        </div>
        <div class="field">
          <label>Verify Token (you choose)</label>
          <input class="input" type="text" v-model="intForm.messenger_verify_token" placeholder="my_secure_verify_token" />
        </div>
        <div class="field" style="grid-column:1/-1">
          <label>Page Access Token</label>
          <input class="input" type="password" v-model="intForm.messenger_page_access_token" placeholder="EAAxxxxxxxxxxxxxxxx" autocomplete="off" />
        </div>
        <div class="field" style="grid-column:1/-1">
          <label>Enable Messenger</label>
          <div class="toggle-row">
            <button class="toggle-btn" :class="{ on: intForm.messenger_enabled }" @click="intForm.messenger_enabled = !intForm.messenger_enabled">
              <span class="toggle-knob"></span>
            </button>
            <span class="toggle-lbl">{{ intForm.messenger_enabled ? 'Enabled — AI will reply to Messenger messages' : 'Disabled' }}</span>
          </div>
        </div>
      </div>
      <div class="save-row">
        <button class="btn-save" @click="saveIntegrations" :disabled="intSaving">{{ intSaving ? 'Saving…' : intSaved ? '✓ Saved' : 'Save Messenger settings' }}</button>
      </div>
    </div>

    <!-- HubSpot CRM -->
    <div class="section-card">
      <div class="section-header">
        <div class="section-title-row">
          <div class="channel-icon" style="background:rgba(255,122,0,0.1);color:#ff7a00">
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="4" cy="4" r="2" stroke="currentColor" stroke-width="2"/></svg>
          </div>
          <div>
            <h2 class="section-title">HubSpot CRM</h2>
            <p class="section-sub">Automatically sync captured leads (email + phone) to HubSpot as Contacts and Deals.</p>
          </div>
          <div class="status-badge" :class="intForm.hubspot_api_key ? 'active' : 'inactive'">{{ intForm.hubspot_api_key ? 'Connected' : 'Not connected' }}</div>
        </div>
      </div>
      <div class="form-grid">
        <div class="field" style="grid-column:1/-1">
          <label>HubSpot Private App Token</label>
          <input class="input" type="password" v-model="intForm.hubspot_api_key" placeholder="pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" autocomplete="off" />
          <span class="field-hint">Create a Private App in HubSpot → Settings → Integrations → Private Apps. Requires CRM (contacts + deals) scopes.</span>
        </div>
      </div>
      <div class="save-row">
        <button class="btn-save" @click="saveIntegrations" :disabled="intSaving">{{ intSaving ? 'Saving…' : intSaved ? '✓ Saved' : 'Save HubSpot settings' }}</button>
      </div>
    </div>

    <!-- ── Security: Change password ─────────────────────────────────────────── -->
    <div class="section-card" style="margin-top:16px">
      <h2 class="section-title">Change password</h2>
      <p class="section-sub">Update the password for your Checkfunnel account.</p>
      <div class="form-grid">
        <div class="field">
          <label>Current password</label>
          <input class="input" type="password" v-model="pwForm.current" placeholder="••••••••" autocomplete="current-password" />
        </div>
        <div class="field">
          <label>New password</label>
          <input class="input" type="password" v-model="pwForm.next" placeholder="Min. 8 characters" autocomplete="new-password" />
        </div>
        <div class="field">
          <label>Confirm new password</label>
          <input class="input" type="password" v-model="pwForm.confirm" placeholder="••••••••" autocomplete="new-password" />
        </div>
      </div>
      <div v-if="pwError" class="pw-error">{{ pwError }}</div>
      <div class="save-row">
        <button class="btn-save" @click="changePassword" :disabled="pwSaving">{{ pwSaving ? 'Saving…' : pwSaved ? '✓ Password updated' : 'Change password' }}</button>
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

// ── Integrations form ─────────────────────────────────────────────────────────
const intSaving = ref(false)
const intSaved = ref(false)
const intForm = ref({
  ai_api_key: '',
  ai_model: '',
  ai_provider: 'openrouter',
  whatsapp_phone_number_id: '',
  whatsapp_access_token: '',
  whatsapp_verify_token: '',
  whatsapp_enabled: false,
  messenger_page_id: '',
  messenger_page_access_token: '',
  messenger_verify_token: '',
  messenger_enabled: false,
  hubspot_api_key: '',
})

const aiProviders = [
  { val: 'openrouter', label: 'OpenRouter' },
  { val: 'openai', label: 'OpenAI' },
  { val: 'anthropic', label: 'Anthropic' },
]

const whatsappWebhookUrl = computed(() =>
  props.client ? `${backendUrl}/api/chat/webhooks/whatsapp/${props.client.id}/` : ''
)
const messengerWebhookUrl = computed(() =>
  props.client ? `${backendUrl}/api/chat/webhooks/messenger/${props.client.id}/` : ''
)

const form = ref({
  chatbot_name: '',
  chatbot_color: '#6366F1',
  chatbot_theme: 'dark',
  notification_email: '',
  cta_message: '',
  domain_url: '',
  voice_input_enabled: false,
  image_input_enabled: false,
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
  form.value.voice_input_enabled = c.voice_input_enabled || false
  form.value.image_input_enabled = c.image_input_enabled || false
  scrapePages.value = c.total_pages_ingested || 0

  // Integrations
  intForm.value.ai_api_key = c.ai_api_key || ''
  intForm.value.ai_model = c.ai_model || ''
  intForm.value.ai_provider = c.ai_provider || 'openrouter'
  intForm.value.whatsapp_phone_number_id = c.whatsapp_phone_number_id || ''
  intForm.value.whatsapp_access_token = c.whatsapp_access_token || ''
  intForm.value.whatsapp_verify_token = c.whatsapp_verify_token || ''
  intForm.value.whatsapp_enabled = c.whatsapp_enabled || false
  intForm.value.messenger_page_id = c.messenger_page_id || ''
  intForm.value.messenger_page_access_token = c.messenger_page_access_token || ''
  intForm.value.messenger_verify_token = c.messenger_verify_token || ''
  intForm.value.messenger_enabled = c.messenger_enabled || false
  intForm.value.hubspot_api_key = c.hubspot_api_key || ''
}, { immediate: true })

// ── Change password ───────────────────────────────────────────────────────────
const pwForm = ref({ current: '', next: '', confirm: '' })
const pwSaving = ref(false)
const pwSaved = ref(false)
const pwError = ref('')

async function changePassword() {
  pwError.value = ''
  if (!pwForm.value.current) { pwError.value = 'Enter your current password.'; return }
  if (pwForm.value.next.length < 8) { pwError.value = 'New password must be at least 8 characters.'; return }
  if (pwForm.value.next !== pwForm.value.confirm) { pwError.value = 'Passwords do not match.'; return }
  pwSaving.value = true
  try {
    await api.changePassword(pwForm.value.current, pwForm.value.next)
    pwSaved.value = true
    pwForm.value = { current: '', next: '', confirm: '' }
    setTimeout(() => { pwSaved.value = false }, 4000)
  } catch (e) {
    pwError.value = e.message || 'Failed to update password.'
  } finally {
    pwSaving.value = false
  }
}

async function saveIntegrations() {
  if (!props.client) return
  intSaving.value = true
  try {
    const updated = await api.updatePortalClient(props.client.id, intForm.value)
    emit('client-updated', updated)
    intSaved.value = true
    setTimeout(() => { intSaved.value = false }, 3000)
  } catch {} finally {
    intSaving.value = false
  }
}

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

/* Widget feature toggles */
.feature-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.feature-row:last-child { border-bottom: none; padding-bottom: 0; }
.feature-info { display: flex; flex-direction: column; gap: 3px; }
.feature-name { font-size: 14px; font-weight: 500; color: #e2e8f0; }
.feature-desc { font-size: 12px; color: #475569; }

.toggle { position: relative; display: inline-block; width: 44px; height: 24px; flex-shrink: 0; cursor: pointer; }
.toggle input { opacity: 0; width: 0; height: 0; }
.toggle-slider {
  position: absolute; inset: 0;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 24px;
  transition: all 0.2s;
}
.toggle-slider::before {
  content: '';
  position: absolute;
  left: 3px; top: 3px;
  width: 16px; height: 16px;
  border-radius: 50%;
  background: #475569;
  transition: all 0.2s;
}
.toggle input:checked + .toggle-slider { background: rgba(99,102,241,0.3); border-color: rgba(99,102,241,0.5); }
.toggle input:checked + .toggle-slider::before { transform: translateX(20px); background: #6366f1; }

/* Integrations */
.status-badge.inactive { background: rgba(71,85,105,0.2); color: #475569; border: 1px solid rgba(71,85,105,0.3); }
.field-hint { font-size: 11px; color: #334155; line-height: 1.5; }
.save-row { display: flex; justify-content: flex-end; }
.pw-error { font-size: 13px; color: #fca5a5; background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); border-radius: 8px; padding: 8px 12px; margin-top: 8px; }
.btn-save {
  padding: 9px 22px;
  background: rgba(99,102,241,0.15);
  border: 1px solid rgba(99,102,241,0.3);
  border-radius: 9px;
  font-size: 13px;
  font-weight: 600;
  color: #a5b4fc;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-save:hover:not(:disabled) { background: rgba(99,102,241,0.25); }
.btn-save:disabled { opacity: 0.5; cursor: not-allowed; }
.toggle-row { display: flex; align-items: center; gap: 12px; }
.toggle-btn {
  position: relative;
  width: 44px; height: 24px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 24px;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}
.toggle-btn.on { background: rgba(99,102,241,0.3); border-color: rgba(99,102,241,0.5); }
.toggle-knob {
  position: absolute;
  left: 3px; top: 3px;
  width: 16px; height: 16px;
  border-radius: 50%;
  background: #475569;
  transition: all 0.2s;
}
.toggle-btn.on .toggle-knob { transform: translateX(20px); background: #6366f1; }
.toggle-lbl { font-size: 13px; color: #64748b; }
</style>
