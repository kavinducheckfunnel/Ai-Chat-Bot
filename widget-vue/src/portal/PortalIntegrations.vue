<template>
  <div class="integrations-page">
    <div class="page-header">
      <h1 class="page-title">Integrations</h1>
      <p class="page-sub">
        Connect your existing tools so the AI can sell on every channel your customers use.
        Each setup takes 2 minutes or less.
      </p>
    </div>

    <!-- Shopify order tracking (OAuth) -->
    <div class="shopify-ot-card">
      <div class="ot-head">
        <span class="ot-icon">🛍️</span>
        <div class="ot-titles">
          <span class="ot-name">Shopify Order Tracking</span>
          <span class="ot-tagline">Let the AI answer "where's my order?" with live status &amp; tracking.</span>
        </div>
        <span v-if="shopify.connected" class="ot-pill on">● Connected</span>
        <span v-else class="ot-pill off">Not connected</span>
      </div>

      <div v-if="shopify.connected" class="ot-body">
        <p class="ot-connected-line">Connected to <strong>{{ shopify.shop_domain }}</strong>. The chatbot can now look up orders by order number + email.</p>
        <button class="ot-btn ghost" @click="disconnectShopify" :disabled="shopify.busy">Disconnect</button>
      </div>
      <div v-else class="ot-body">
        <p class="ot-help">Enter your Shopify store domain, then authorize read-only order access. (One-time, ~10 seconds.)</p>
        <div class="ot-row">
          <input v-model="shopify.shop" class="ot-input" placeholder="your-store.myshopify.com" @keydown.enter="connectShopify" />
          <button class="ot-btn primary" @click="connectShopify" :disabled="shopify.busy || !shopify.shop.trim()">
            {{ shopify.busy ? 'Connecting…' : 'Connect Shopify' }}
          </button>
        </div>
        <p v-if="shopify.error" class="ot-error">{{ shopify.error }}</p>
      </div>
    </div>

    <!-- Filter tabs -->
    <div class="filter-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="filter-tab"
        :class="{ active: activeFilter === tab.key }"
        @click="activeFilter = tab.key"
      >{{ tab.label }} <span class="tab-count">{{ countFor(tab.key) }}</span></button>
    </div>

    <!-- Cards grid -->
    <div class="cards-grid">
      <div
        v-for="card in visibleCards"
        :key="card.key"
        class="card"
        :class="{ 'card-locked': card.locked }"
      >
        <div class="card-head">
          <div class="card-icon" :style="{ background: card.iconBg }">
            <span class="card-icon-emoji">{{ card.icon }}</span>
          </div>
          <div class="card-titles">
            <span class="card-name">{{ card.name }}</span>
            <span class="card-tagline">{{ card.tagline }}</span>
          </div>
          <span v-if="card.requiredPlan && card.locked" class="plan-pill">{{ card.requiredPlan }}</span>
          <span v-else-if="card.enabled" class="status-pill on">Active</span>
          <span v-else class="status-pill off">Not connected</span>
        </div>

        <p class="card-desc">{{ card.description }}</p>

        <div class="card-best-for">
          <strong>Best for:</strong> {{ card.bestFor }}
        </div>

        <div class="card-steps">
          <strong>Setup ({{ card.steps.length }} steps):</strong>
          <ol>
            <li v-for="(step, i) in card.steps" :key="i">{{ step }}</li>
          </ol>
        </div>

        <div class="card-actions">
          <router-link v-if="!card.locked && card.settingsAnchor" :to="`/portal/settings#${card.settingsAnchor}`" class="btn-primary">
            {{ card.enabled ? 'Manage' : 'Set up' }} →
          </router-link>
          <router-link v-else-if="card.locked" to="/portal/billing" class="btn-upgrade">
            Upgrade to {{ card.requiredPlan }} →
          </router-link>
          <span v-else class="btn-disabled">Coming soon</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, inject } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()
const portalClient = inject('portalClient', ref(null))

const activeFilter = ref('all')
const features = ref({})  // plan feature flags
const subscription = ref(null)

// ── Shopify order tracking (OAuth) ──────────────────────────────────────────
const shopify = ref({ connected: false, shop_domain: '', shop: '', busy: false, error: '' })

async function loadShopifyStatus() {
  const c = portalClient.value
  if (!c?.id) return
  try {
    const s = await api.getShopifyStatus(c.id)
    shopify.value.connected = !!s.connected
    shopify.value.shop_domain = s.shop_domain || ''
  } catch {}
}

async function connectShopify() {
  const c = portalClient.value
  if (!c?.id || !shopify.value.shop.trim()) return
  shopify.value.busy = true; shopify.value.error = ''
  try {
    const res = await api.getShopifyAuthorizeUrl(c.id, shopify.value.shop.trim())
    if (res?.url) { window.location.href = res.url; return }  // redirect to Shopify
    shopify.value.error = 'Could not start the connection.'
  } catch (e) {
    shopify.value.error = e?.message || 'Enter a valid myshopify.com domain.'
  } finally {
    shopify.value.busy = false
  }
}

async function disconnectShopify() {
  const c = portalClient.value
  if (!c?.id) return
  shopify.value.busy = true
  try {
    await api.disconnectShopify(c.id)
    shopify.value.connected = false; shopify.value.shop_domain = ''
  } catch {} finally { shopify.value.busy = false }
}

const tabs = [
  { key: 'all',       label: 'All' },
  { key: 'channels',  label: 'Channels' },
  { key: 'ecommerce', label: 'E-commerce' },
  { key: 'crm',       label: 'CRM & Notifications' },
  { key: 'custom',    label: 'Custom' },
]

// Master list of integrations. Keep in sync with docs/integration_guidance.md
// — this is the in-app version of the same content. Update both together.
const allCards = computed(() => {
  const c = portalClient.value || {}
  const planName = subscription.value?.plan?.name || ''
  const planAllows = (flag) => !!features.value[flag]

  return [
    {
      key: 'website', category: 'channels', icon: '🌐', iconBg: 'rgba(99,102,241,0.12)',
      name: 'Website Widget', tagline: 'One snippet of code, AI on every page',
      description: 'The default channel — embeds as a floating widget on any page of your site. Auto-opens with behavior-aware questions, captures leads, escalates to your team when needed.',
      bestFor: 'E-commerce stores, service businesses, SaaS landing pages',
      steps: [
        'Open /portal/settings → Channels & Embed',
        'Choose your embed format (HTML / WordPress / React)',
        'Copy the snippet and paste it before </body> on your site',
        'Refresh — the widget appears in the bottom-right',
      ],
      enabled: true,  // always on
      requiredPlan: null,
      locked: false,
      settingsAnchor: 'channels',
    },
    {
      key: 'whatsapp', category: 'channels', icon: '💬', iconBg: 'rgba(37,211,102,0.12)',
      name: 'WhatsApp Business', tagline: 'Sell on the world\'s most popular messaging app',
      description: 'Connect your WhatsApp Business number so the AI handles inquiries 24/7. Conversations sync to the same inbox as website chats. Hot leads escalate to your team in real time.',
      bestFor: 'Direct-to-consumer brands in LATAM, Africa, India, MENA. Service businesses that handle appointments via WhatsApp.',
      steps: [
        'Have a Meta Business account + verified WhatsApp number',
        'In /portal/settings → WhatsApp, paste your phone number ID',
        'Paste your access token + verify token from Meta Developer dashboard',
        'Copy our webhook URL into Meta\'s webhook config',
        'Toggle "Enable WhatsApp" and save',
      ],
      enabled: !!c.whatsapp_enabled,
      requiredPlan: 'Growth',
      locked: !planAllows('allow_whatsapp'),
      settingsAnchor: 'whatsapp',
    },
    {
      key: 'telegram', category: 'channels', icon: '📡', iconBg: 'rgba(0,136,204,0.12)',
      name: 'Telegram Bot', tagline: 'Webhook auto-registered, live in 2 minutes',
      description: 'Create a bot via @BotFather, paste the token, hit save. We handle webhook registration with Telegram\'s API automatically (no copy/paste URLs). Status reported live in the dashboard.',
      bestFor: 'Communities and audiences that already prefer Telegram (crypto, Eastern European markets, niche tech).',
      steps: [
        'Message @BotFather on Telegram, run /newbot',
        'Copy the token BotFather gives you',
        'In /portal/settings → Telegram, paste the token',
        'Toggle "Enable Telegram" and save',
        'Wait for "Webhook active" — send a test message to your bot',
      ],
      enabled: !!c.telegram_enabled,
      requiredPlan: 'Growth',
      locked: !planAllows('allow_telegram'),
      settingsAnchor: 'telegram',
    },
    {
      key: 'messenger', category: 'channels', icon: '📨', iconBg: 'rgba(0,132,255,0.12)',
      name: 'Facebook Messenger', tagline: 'Convert your page DMs without a 24/7 team',
      description: 'Connect your Facebook Page so Messenger DMs route to the AI. Same sales-trained behavior as the website widget — qualifies leads, captures contact info, escalates when needed.',
      bestFor: 'Brands with established Facebook page audiences. Lead-gen businesses (real estate, education, services) where Facebook ads drive DM volume.',
      steps: [
        'In Meta Developer Portal, create or open your Messenger app',
        'In /portal/settings → Messenger, paste your Page ID + access token',
        'Set your verify token + copy our webhook URL into Meta',
        'Toggle "Enable Messenger" and save',
      ],
      enabled: !!c.messenger_enabled,
      requiredPlan: 'Growth',
      locked: !planAllows('allow_messenger'),
      settingsAnchor: 'messenger',
    },
    {
      key: 'shopify', category: 'ecommerce', icon: '🛍️', iconBg: 'rgba(122,194,82,0.12)',
      name: 'Shopify Webhooks', tagline: 'Real-time product + order sync',
      description: 'Webhook integration pulls in product updates so the AI\'s knowledge base stays fresh without re-scraping. Order data flows in for post-purchase support flows.',
      bestFor: 'Any Shopify store. Especially valuable for stores with frequent catalog changes or large inventories.',
      steps: [
        'In Shopify admin: Settings → Notifications → Webhooks',
        'In /portal/settings → Shopify, copy our webhook URL + secret',
        'Add 2 Shopify webhooks: products/update + orders/create',
        'Paste the shared secret in Shopify for HMAC verification',
        'Products sync within 60 seconds of any update',
      ],
      enabled: c.platform === 'SHOPIFY',
      requiredPlan: null,
      locked: false,
      settingsAnchor: 'shopify',
    },
    {
      key: 'wordpress', category: 'ecommerce', icon: '📝', iconBg: 'rgba(33,117,155,0.12)',
      name: 'WordPress / WooCommerce', tagline: 'One-click install via official plugin',
      description: 'Native WordPress/WooCommerce plugin. Installs the chat widget, sets up product update webhooks, and embeds in your existing theme. Zero manual code editing.',
      bestFor: 'WordPress-powered e-commerce stores. Content sites that want chat plus auto-content sync.',
      steps: [
        'Download the Checkfunnel WordPress plugin',
        'WordPress admin → Plugins → Add New → Upload → Activate',
        'Click "Connect to Checkfunnel" button',
        'Authorize the link (one click)',
        'Widget + product sync are live',
      ],
      enabled: c.platform === 'WORDPRESS',
      requiredPlan: null,
      locked: false,
      settingsAnchor: 'wordpress',
    },
    {
      key: 'hubspot', category: 'crm', icon: '🧲', iconBg: 'rgba(255,123,79,0.12)',
      name: 'HubSpot CRM', tagline: 'Captured leads land in HubSpot with full chat context',
      description: 'When the AI captures a lead, it\'s pushed to HubSpot as a new contact with the conversation transcript attached as a note. Sales picks up the conversation where they already work.',
      bestFor: 'Sales-led B2B/B2C teams already using HubSpot. Service businesses with longer sales cycles.',
      steps: [
        'In HubSpot, generate a Private App access token (Contacts + Notes write scope)',
        'In /portal/settings → HubSpot CRM, paste the token',
        'Save — first captured lead syncs within 5 seconds',
      ],
      enabled: !!c.hubspot_api_key,
      requiredPlan: 'Growth',
      locked: !planAllows('allow_hubspot'),
      settingsAnchor: 'hubspot',
    },
    {
      key: 'slack', category: 'crm', icon: '💼', iconBg: 'rgba(74,21,75,0.12)',
      name: 'Slack Notifications', tagline: 'Get pinged the moment a hot lead is captured',
      description: 'Sends a Slack message to your team channel whenever a HOT_LEAD or CONVERTED session is detected. Includes the visitor\'s contact info, heat score, and a link to the full conversation.',
      bestFor: 'Small sales teams where one person responds fast to high-intent leads. Agencies managing multiple clients.',
      steps: [
        'In Slack, create an Incoming Webhook for your channel',
        'Copy the webhook URL (hooks.slack.com/services/...)',
        'In /portal/settings → Slack, paste the URL',
        'Save — first hot lead triggers a Slack post',
      ],
      enabled: !!c.slack_webhook_url,
      requiredPlan: 'Starter',
      locked: !planAllows('allow_slack'),
      settingsAnchor: 'slack',
    },
    {
      key: 'webhooks', category: 'custom', icon: '⚡', iconBg: 'rgba(245,158,11,0.12)',
      name: 'Outbound Webhooks', tagline: 'Pipe events to Zapier, n8n, or your own systems',
      description: 'Configure a single webhook URL we POST to whenever events fire: hot_lead, lead_captured, new_session, etc. JSON payload with the visitor, session, and event details. HMAC-SHA256 signed.',
      bestFor: 'Power users who want to integrate with Zapier, n8n, Make, custom CRMs, or marketing automation tools.',
      steps: [
        'In /portal/settings → Outbound Webhooks, paste your destination URL',
        'Choose which events fire (default: hot_lead, lead_captured, new_session)',
        'Save — events POST with Content-Type: application/json',
        'Verify with the included HMAC-SHA256 webhook secret',
      ],
      enabled: !!c.outbound_webhook_url,
      requiredPlan: null,
      locked: !planAllows('allow_webhooks'),
      settingsAnchor: 'webhooks',
    },
  ]
})

const visibleCards = computed(() => {
  if (activeFilter.value === 'all') return allCards.value
  return allCards.value.filter(c => c.category === activeFilter.value)
})

function countFor(key) {
  if (key === 'all') return allCards.value.length
  return allCards.value.filter(c => c.category === key).length
}

async function loadFeatures() {
  try {
    const sub = await api.getSubscription()
    subscription.value = sub
    // Derive feature flags from plan
    const plan = sub?.plan || {}
    features.value = {
      allow_whatsapp:  !!plan.allow_whatsapp || !!plan.max_social_channels,
      allow_telegram:  !!plan.allow_telegram || !!plan.max_social_channels,
      allow_messenger: !!plan.allow_messenger || !!plan.max_social_channels,
      allow_hubspot:   !!plan.allow_hubspot,
      allow_slack:     true,   // available on all paid plans
      allow_webhooks:  !!plan.allow_webhooks,
    }
  } catch {
    // No sub — treat as Free plan
    features.value = {}
  }
}

onMounted(() => {
  loadFeatures()
  loadShopifyStatus()
  // Surface the OAuth round-trip result (?shopify=connected|error).
  try {
    const p = new URLSearchParams(window.location.search).get('shopify')
    if (p === 'connected') { shopify.value.connected = true; loadShopifyStatus() }
    else if (p === 'error') { shopify.value.error = 'Shopify connection failed — please try again.' }
    if (p) window.history.replaceState({}, '', window.location.pathname)
  } catch {}
})
watch(() => portalClient.value?.id, () => loadShopifyStatus())
</script>

<style scoped>
.integrations-page { padding: 28px 32px; max-width: 1200px; font-family: 'Inter', -apple-system, sans-serif; }

/* Shopify order tracking card */
.shopify-ot-card { background: var(--cf-bg-surface-raised); border: 1px solid var(--cf-border-default); border-radius: 14px; padding: 18px 20px; margin-bottom: 20px; }
.ot-head { display: flex; align-items: center; gap: 12px; }
.ot-icon { font-size: 24px; }
.ot-titles { display: flex; flex-direction: column; flex: 1; min-width: 0; }
.ot-name { font-size: 15px; font-weight: 700; color: var(--cf-text-primary); }
.ot-tagline { font-size: 12.5px; color: var(--cf-text-muted); margin-top: 2px; }
.ot-pill { font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 20px; white-space: nowrap; }
.ot-pill.on { background: rgba(34,197,94,.14); color: #22c55e; }
.ot-pill.off { background: var(--cf-bg-ghost); color: var(--cf-text-muted); }
.ot-body { margin-top: 14px; }
.ot-help, .ot-connected-line { font-size: 13px; color: var(--cf-text-secondary); margin: 0 0 12px; line-height: 1.5; }
.ot-row { display: flex; gap: 10px; flex-wrap: wrap; }
.ot-input { flex: 1; min-width: 220px; padding: 10px 12px; background: var(--cf-bg-input); border: 1px solid var(--cf-border-default); border-radius: 9px; color: var(--cf-text-primary); font-size: 13px; font-family: inherit; outline: none; }
.ot-input:focus { border-color: #6366f1; }
.ot-btn { padding: 10px 18px; border-radius: 9px; font-size: 13px; font-weight: 600; cursor: pointer; border: 1px solid transparent; font-family: inherit; }
.ot-btn.primary { background: #95bf47; color: #fff; }
.ot-btn.primary:hover:not(:disabled) { background: #7fa83c; }
.ot-btn.ghost { background: var(--cf-bg-surface); border-color: var(--cf-border-default); color: var(--cf-text-secondary); }
.ot-btn:disabled { opacity: .5; cursor: not-allowed; }
.ot-error { color: #ef4444; font-size: 12px; margin: 8px 0 0; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--cf-text-primary); margin: 0 0 6px; letter-spacing: -0.4px; }
.page-sub { font-size: 14px; color: var(--cf-text-muted); margin: 0; max-width: 700px; line-height: 1.55; }

.filter-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--cf-border-subtle);
}
.filter-tab {
  background: none;
  border: none;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--cf-text-muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: -1px;
}
.filter-tab:hover { color: var(--cf-text-primary); }
.filter-tab.active { color: #a5b4fc; border-bottom-color: #6366f1; }
.tab-count {
  font-size: 11px;
  background: var(--cf-bg-ghost);
  color: var(--cf-text-muted);
  padding: 1px 6px;
  border-radius: 10px;
}
.filter-tab.active .tab-count { background: rgba(99,102,241,0.2); color: #a5b4fc; }

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
  gap: 16px;
  align-items: stretch;
}

.card {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 14px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: 100%;
  transition: border-color .15s, transform .15s, box-shadow .15s;
}
.card:hover { border-color: var(--cf-border-default); transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,.25); }
.card.card-locked { opacity: 0.7; }

/* Header: icon + titles take the row, status/plan pill pinned top-right. */
.card-head { display: flex; align-items: flex-start; gap: 12px; }
.card-icon {
  width: 40px; height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.card-icon-emoji { font-size: 20px; }
.card-titles { display: flex; flex-direction: column; flex: 1; min-width: 0; padding-top: 2px; }
.card-name { font-size: 15px; font-weight: 600; color: var(--cf-text-primary); }
.card-tagline { font-size: 12px; color: var(--cf-text-muted); margin-top: 3px; line-height: 1.4; }

.status-pill, .plan-pill {
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
  flex-shrink: 0;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.status-pill.on { background: rgba(34,197,94,0.12); color: #22c55e; border: 1px solid rgba(34,197,94,0.25); }
.status-pill.off { background: var(--cf-bg-ghost); color: var(--cf-text-muted); border: 1px solid var(--cf-border-subtle); }
.plan-pill { background: rgba(245,158,11,0.12); color: #f59e0b; border: 1px solid rgba(245,158,11,0.25); }

.card-desc {
  font-size: 13px;
  color: var(--cf-text-secondary);
  line-height: 1.55;
  margin: 0;
}
.card-best-for {
  font-size: 12px;
  color: var(--cf-text-secondary);
  line-height: 1.5;
  background: var(--cf-bg-input);
  padding: 8px 10px;
  border-radius: 8px;
}
.card-best-for strong { color: var(--cf-text-primary); font-weight: 600; }
.card-steps { font-size: 12px; color: var(--cf-text-secondary); background: var(--cf-bg-input); border-radius: 8px; padding: 10px 12px; }
.card-steps strong { color: var(--cf-text-primary); font-weight: 600; font-size: 12px; display: block; margin-bottom: 6px; }
.card-steps ol { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 3px; }
.card-steps li { line-height: 1.5; }

.card-actions { margin-top: auto; padding-top: 8px; }
.btn-primary, .btn-upgrade, .btn-disabled {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  font-size: 13px;
  font-weight: 600;
  padding: 9px 14px;
  border-radius: 8px;
  text-decoration: none;
  border: 1px solid transparent;
  cursor: pointer;
}
.btn-primary {
  background: rgba(99,102,241,0.12);
  border-color: rgba(99,102,241,0.3);
  color: #a5b4fc;
}
.btn-primary:hover { background: rgba(99,102,241,0.22); }
.btn-upgrade {
  background: rgba(245,158,11,0.1);
  border-color: rgba(245,158,11,0.3);
  color: #fbbf24;
}
.btn-disabled {
  background: var(--cf-bg-ghost);
  color: var(--cf-text-muted);
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .integrations-page { padding: 20px 16px; }
  .cards-grid { grid-template-columns: 1fr; }
}
</style>
