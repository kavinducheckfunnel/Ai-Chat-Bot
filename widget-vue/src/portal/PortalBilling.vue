<template>
  <div class="billing-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Billing</h1>
        <p class="page-sub">Manage your subscription and usage.</p>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="skeleton-wrap">
      <div class="sk-card" v-for="n in 3" :key="n"><div class="sk-line w60"></div><div class="sk-line w40"></div></div>
    </div>

    <template v-else>

      <!-- ── Current plan banner ──────────────────────────────────────────── -->
      <div class="current-plan-card" :class="statusClass">
        <div class="cp-left">
          <div class="cp-badge" :class="statusClass">{{ statusLabel }}</div>
          <h2 class="cp-plan-name">{{ sub.plan?.name || 'No plan' }}</h2>
          <p class="cp-price" v-if="sub.plan">
            ${{ billingInterval === 'annual' ? annualMonthly(sub.plan) : sub.plan.price_monthly }}<span>/mo</span>
            <span v-if="billingInterval === 'annual'" class="annual-tag">billed annually · save 15%</span>
          </p>
          <p class="cp-price" v-else>Free</p>

          <!-- Trial banner -->
          <div v-if="sub.trial_ends_at" class="trial-notice">
            <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="#a78bfa" stroke-width="2"/><path d="M12 8v4l2.5 2.5" stroke="#a78bfa" stroke-width="2" stroke-linecap="round"/></svg>
            Trial ends {{ formatDate(sub.trial_ends_at) }}
          </div>
        </div>
        <div class="cp-right">
          <button v-if="sub.stripe_subscription_id" class="btn-portal" @click="openPortal" :disabled="portalLoading">
            <span v-if="portalLoading" class="spinner"></span>
            <span v-else>Manage billing</span>
          </button>
        </div>
      </div>

      <!-- ── Usage bars ──────────────────────────────────────────────────── -->
      <div class="usage-section" v-if="sub.usage && sub.plan">
        <h3 class="section-heading">Usage this month</h3>
        <div class="usage-grid">
          <div class="usage-card" v-for="res in usageResources" :key="res.key">
            <div class="usage-label">
              <span>{{ res.label }}</span>
              <span class="usage-nums">
                {{ res.used.toLocaleString() }}
                <span v-if="res.limit >= 0"> / {{ res.limit.toLocaleString() }}</span>
                <span v-else> / ∞</span>
              </span>
            </div>
            <div class="usage-bar">
              <div
                class="usage-fill"
                :style="{ width: res.pct + '%', background: res.pct > 90 ? '#ef4444' : res.pct > 75 ? '#f59e0b' : '#6366f1' }"
              ></div>
            </div>
            <span v-if="res.pct > 80" class="usage-warn">
              {{ res.pct >= 100 ? 'Limit reached' : `${res.pct}% used — approaching limit` }}
            </span>
          </div>
        </div>
      </div>

      <!-- ── Add-ons / custom requirements → contact team ───────────── -->
      <div class="addon-section" v-if="sub.plan">
        <div class="contact-card">
          <div class="contact-card-icon">💬</div>
          <div class="contact-card-body">
            <div class="contact-card-title">Need add-ons or custom features?</div>
            <div class="contact-card-sub">
              For extra message / image / voice credits, white-label branding, or any
              custom requirement, our team will set you up.
            </div>
          </div>
          <a href="mailto:sales@checkfunnel.com?subject=Add-on%20/%20custom%20request" class="contact-card-btn">
            Please contact our team
          </a>
        </div>
      </div>

      <!-- ── Invoices section ────────────────────────────────────────── -->
      <div class="invoices-section">
        <div class="invoices-header">
          <div>
            <h3 class="section-heading" style="margin:0">Invoices</h3>
            <p class="section-sub-mini">Monthly invoices are emailed automatically on the 1st. Download anytime as PDF (Cmd/Ctrl + P → Save as PDF).</p>
          </div>
          <button class="btn-test-invoice" @click="sendTestInvoice" :disabled="testInvoiceSending">
            <span v-if="testInvoiceSending" class="spinner"></span>
            <span v-else>📧 Send me a test invoice</span>
          </button>
        </div>
        <p v-if="testInvoiceStatus" :class="['test-invoice-msg', testInvoiceOk ? 'ok' : 'err']">{{ testInvoiceStatus }}</p>
        <div v-if="!invoices.length && !invoicesLoading" class="invoices-empty">
          No invoices yet. Your first one will be emailed and shown here on the 1st of the next month.
        </div>
        <div v-else-if="invoicesLoading" class="invoices-empty">Loading invoices…</div>
        <div v-else class="invoice-list">
          <div v-for="inv in invoices" :key="inv.id" class="invoice-row">
            <div class="invoice-left">
              <div class="invoice-number">{{ inv.invoice_number }}</div>
              <div class="invoice-period">{{ formatInvoicePeriod(inv.period_start) }}</div>
            </div>
            <div class="invoice-center">
              <span class="invoice-status" :class="`inv-${inv.status}`">{{ inv.status }}</span>
              <span class="invoice-total">${{ inv.total_usd }} USD</span>
            </div>
            <div class="invoice-actions">
              <a class="btn-invoice-pdf" :href="invoicePdfUrl(inv)" target="_blank" rel="noopener" title="Download as PDF">
                ⬇ PDF
              </a>
              <a class="btn-invoice-view" :href="invoiceUrl(inv)" target="_blank" rel="noopener" title="Open invoice in a new tab">
                View →
              </a>
            </div>
          </div>
        </div>
      </div>

      <!-- Past due / canceled warning -->
      <div v-if="sub.stripe_subscription_status === 'past_due'" class="alert-banner warn">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="#f59e0b" stroke-width="2"/><line x1="12" y1="8" x2="12" y2="12" stroke="#f59e0b" stroke-width="2" stroke-linecap="round"/><line x1="12" y1="16" x2="12.01" y2="16" stroke="#f59e0b" stroke-width="2" stroke-linecap="round"/></svg>
        Your last payment failed. Please update your payment method to avoid interruptions.
        <button class="btn-link" @click="openPortal">Update payment</button>
      </div>
      <div v-if="sub.stripe_subscription_status === 'canceled'" class="alert-banner danger">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="#ef4444" stroke-width="2"/><path d="M15 9l-6 6M9 9l6 6" stroke="#ef4444" stroke-width="2" stroke-linecap="round"/></svg>
        Your subscription has been canceled. Upgrade to restore full access.
      </div>

      <!-- ── Billing interval toggle ─────────────────────────────────────── -->
      <div class="interval-toggle-wrap">
        <h3 class="section-heading" style="margin:0">Choose a plan</h3>
        <div class="interval-toggle">
          <button :class="{ active: billingInterval === 'monthly' }" @click="billingInterval = 'monthly'">Monthly</button>
          <button :class="{ active: billingInterval === 'annual' }" @click="billingInterval = 'annual'">
            Annual <span class="save-badge">Save 15%</span>
          </button>
        </div>
      </div>

      <!-- ── Plan cards ──────────────────────────────────────────────────── -->
      <div class="plans-grid">
        <div
          v-for="plan in plans"
          :key="plan.id"
          class="plan-card"
          :class="{ current: isCurrentPlan(plan), popular: plan.name === 'Growth' }"
        >
          <div class="plan-popular-badge" v-if="plan.name === 'Growth'">Most popular</div>
          <div class="plan-header">
            <span class="plan-name">{{ plan.name }}</span>
            <div class="plan-price" v-if="plan.price_monthly != null && plan.price_monthly >= 0">
              <span class="plan-amount">${{ billingInterval === 'annual' ? annualMonthly(plan) : formatPrice(plan.price_monthly) }}</span>
              <span class="plan-period">/mo</span>
            </div>
            <div class="plan-price" v-else>
              <span class="plan-amount plan-amount-custom">Custom</span>
            </div>
            <span v-if="billingInterval === 'annual' && plan.price_monthly > 0" class="plan-annual-note">billed ${{ annualTotal(plan) }}/yr</span>
          </div>
          <ul class="plan-features">
            <li v-for="feat in planFeatures(plan)" :key="feat">
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              {{ feat }}
            </li>
          </ul>
          <button
            class="plan-btn"
            :class="{
              'plan-btn-current': isCurrentPlan(plan),
              'plan-btn-upgrade': !isCurrentPlan(plan) && activePriceId(plan),
              'plan-btn-contact': !isCurrentPlan(plan) && !activePriceId(plan),
            }"
            :disabled="isCurrentPlan(plan) || checkoutLoading === plan.id"
            @click="activePriceId(plan) ? checkout(plan) : contactUs()"
          >
            <span v-if="checkoutLoading === plan.id" class="spinner"></span>
            <span v-else-if="isCurrentPlan(plan)">Current plan</span>
            <span v-else-if="!activePriceId(plan)">Contact us</span>
            <span v-else-if="isDowngrade(plan)">Downgrade</span>
            <span v-else>Upgrade</span>
          </button>
        </div>
      </div>

      <!-- Error -->
      <div v-if="error" class="error-msg">{{ error }}</div>

      <!-- ── Full feature comparison (mirrors the pricing doc) ───────────── -->
      <div class="compare-section" v-if="plans.length">
        <h3 class="section-heading">Compare all features</h3>
        <div class="compare-wrap">
          <table class="compare-table">
            <thead>
              <tr>
                <th class="cmp-feature-h">Feature</th>
                <th
                  v-for="p in plans"
                  :key="p.id"
                  :class="{ 'cmp-col-current': isCurrentPlan(p), 'cmp-col-popular': p.name === 'Growth' }"
                >
                  {{ p.name }}
                  <span v-if="p.name === 'Growth'" class="cmp-pop-badge">Popular</span>
                  <span v-if="isCurrentPlan(p)" class="cmp-cur-badge">Your plan</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in compareRows" :key="row.label">
                <td class="cmp-feature">{{ row.label }}</td>
                <td
                  v-for="p in plans"
                  :key="p.id"
                  :class="{ 'cmp-col-current': isCurrentPlan(p) }"
                  v-html="row.cell(p)"
                ></td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="compare-note">
          A “message” is one AI-generated response — human replies during Live Chat Takeover don’t count.
          Annual billing saves 15% (2 months free). Omnichannel (WhatsApp + Facebook) needs a Meta
          Developer App. Need add-ons or a custom feature?
          <a href="mailto:sales@checkfunnel.com?subject=Add-on%20/%20custom%20request">Contact our team.</a>
        </p>
      </div>

      <!-- ── FAQ ─────────────────────────────────────────────────────────── -->
      <div class="faq-section">
        <h3 class="section-heading">FAQ</h3>
        <div class="faq-list">
          <div class="faq-item" v-for="q in faqs" :key="q.q" @click="q.open = !q.open">
            <div class="faq-q">
              {{ q.q }}
              <svg width="14" height="14" fill="none" viewBox="0 0 24 24" :style="{ transform: q.open ? 'rotate(180deg)' : '', transition: '.2s' }"><path d="M6 9l6 6 6-6" stroke="#64748b" stroke-width="2" stroke-linecap="round"/></svg>
            </div>
            <div class="faq-a" v-if="q.open">{{ q.a }}</div>
          </div>
        </div>
      </div>

    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()

const loading = ref(true)
const portalLoading = ref(false)
const checkoutLoading = ref(null)
const error = ref('')
const sub = ref({})
const plans = ref([])
const billingInterval = ref('monthly')

// ── Invoices section ────────────────────────────────────────────────────────
const invoices = ref([])
const invoicesLoading = ref(false)
const testInvoiceSending = ref(false)
const testInvoiceStatus = ref('')
const testInvoiceOk = ref(false)

async function loadInvoices() {
  invoicesLoading.value = true
  try {
    const list = await api.listInvoices()
    invoices.value = Array.isArray(list) ? list : []
  } catch {
    invoices.value = []
  } finally {
    invoicesLoading.value = false
  }
}

function invoiceUrl(inv) {
  // Backend returns a signed-token URL valid for 1 hour, so it opens in a
  // new tab without needing the JWT Authorization header that browser-tab
  // navigations can't carry.
  const base = (typeof window !== 'undefined' && window.location.origin) || ''
  return base + inv.download_url
}

function invoicePdfUrl(inv) {
  // Same signed-link pattern, server-side renders WeasyPrint → PDF.
  const base = (typeof window !== 'undefined' && window.location.origin) || ''
  return base + (inv.pdf_url || inv.download_url)
}

function formatInvoicePeriod(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
  } catch { return iso }
}

async function sendTestInvoice() {
  testInvoiceStatus.value = ''
  testInvoiceSending.value = true
  try {
    const res = await api.sendTestInvoice()
    testInvoiceOk.value = true
    testInvoiceStatus.value = `Test invoice sent to ${res.sent_to}. Check your inbox (and spam folder).`
    await loadInvoices()  // refresh list — the generated invoice now appears
  } catch (e) {
    testInvoiceOk.value = false
    testInvoiceStatus.value = e.message || 'Could not send test invoice.'
  } finally {
    testInvoiceSending.value = false
  }
}

// ── helpers ──────────────────────────────────────────────────────────────────

function annualMonthly(plan) {
  return (parseFloat(plan.price_monthly) * 0.85).toFixed(0)
}
function annualTotal(plan) {
  return (parseFloat(plan.price_monthly) * 0.85 * 12).toFixed(0)
}
function activePriceId(plan) {
  return billingInterval.value === 'annual'
    ? plan.stripe_price_id_annual
    : plan.stripe_price_id
}
function isCurrentPlan(plan) {
  return sub.value.plan?.id === plan.id
}
function isDowngrade(plan) {
  return sub.value.plan && parseFloat(plan.price_monthly) < parseFloat(sub.value.plan.price_monthly)
}
function formatLimit(n) {
  if (n < 0) return 'Unlimited'
  return n.toLocaleString()
}

// ── Plan card feature list — derived from plan data to mirror the published
//    pricing doc (Section 4 "Feature Breakdown by Plan"). Driven entirely by
//    the seeded Plan fields so every tenant sees the same, correct list. ──────
function channelLabel(plan) {
  const social = plan.max_social_channels
  if (social === 0 || social == null) return 'Web chat only'
  if (social === 1) return 'Web chat + 1 social channel (WhatsApp or Facebook)'
  if (social < 0 && plan.name === 'Enterprise') return 'All channels (Web + omnichannel)'
  return 'Omnichannel (Web, WhatsApp, Facebook, Telegram…)'
}
function crmLabel(plan) {
  if (!plan.allow_hubspot) return null
  if (plan.name === 'Enterprise') return 'Custom CRM + Direct HubSpot Sync'
  if (plan.allow_advanced_reports) return 'CRM via Webhook + Direct HubSpot Sync'
  return 'CRM via Webhook (HubSpot, Zapier & more)'
}
function reportsLabel(plan) {
  if (plan.name === 'Enterprise') return 'Custom reports & exports'
  if (plan.allow_advanced_reports) return 'Advanced reports & exports'
  if (plan.allow_csv_export || plan.allow_voice_input) return 'Standard reports & exports'
  return 'Basic reports'
}
function supportLabel(plan) {
  if (plan.name === 'Enterprise') return 'Dedicated CSM'
  if (plan.priority_support) return 'Priority support'
  if (plan.allow_voice_input) return 'Email + chat support'  // Growth tier
  return 'Email support'
}
function retentionLabel(plan) {
  const d = plan.data_retention_days
  if (d == null || d < 0) return 'Custom data retention'
  if (d >= 365) return `${Math.round(d / 365)}-year data retention`
  return `${d}-day data retention`
}
function planFeatures(plan) {
  const feats = []
  feats.push(`${formatLimit(plan.max_messages_per_month)} AI messages / mo`)
  feats.push(channelLabel(plan))
  feats.push('AI lead scoring & in-chat checkout')
  const crm = crmLabel(plan)
  if (crm) feats.push(crm)
  if (plan.allow_image_input) feats.push('Image upload for questions')
  if (plan.allow_voice_input) feats.push('Voice command widget')
  if (plan.allow_real_time_inventory) feats.push('Real-time inventory sync')
  if (plan.allow_custom_domain) feats.push('Custom website integration (any platform)')
  feats.push(plan.allow_byok
    ? (plan.allow_advanced_reports || plan.name === 'Enterprise' ? 'BYOK — bring your own AI key' : 'BYOK support (optional)')
    : 'Managed AI included')
  feats.push(reportsLabel(plan))
  feats.push(supportLabel(plan))
  feats.push(retentionLabel(plan))
  if (plan.remove_branding) feats.push('White-label branding')
  return feats
}

// ── Full feature comparison matrix (pricing doc Section 4) ──────────────────
// Data-driven from the plan objects so it always matches what's seeded.
function cmpTick(on) {
  return on
    ? '<span class="cmp-yes">✓</span>'
    : '<span class="cmp-no">—</span>'
}
function crmCell(plan) {
  if (!plan.allow_hubspot) return cmpTick(false)
  if (plan.name === 'Enterprise') return 'Custom'
  if (plan.allow_advanced_reports) return 'Webhook + Direct HubSpot Sync'
  return 'Webhook (HubSpot, Zapier…)'
}
function webChannelsCell(plan) {
  const s = plan.max_social_channels
  if (s === 0 || s == null) return 'Website only'
  if (s === 1) return 'Website + 1 social'
  if (s < 0 && plan.name === 'Enterprise') return 'All channels'
  return 'Website + omnichannel'
}
const compareRows = [
  { label: 'Monthly messages',           cell: p => formatLimit(p.max_messages_per_month) },
  { label: 'Chatbots included',          cell: p => formatLimit(p.max_clients) },
  { label: 'Web channels',               cell: p => webChannelsCell(p) },
  { label: 'CRM integrations',           cell: p => crmCell(p) },
  { label: 'BYOK support',               cell: p => p.allow_byok ? (p.allow_advanced_reports || p.name === 'Enterprise' ? cmpTick(true) : cmpTick(true) + ' <span class="cmp-opt">optional</span>') : cmpTick(false) },
  { label: 'Voice command widget',       cell: p => cmpTick(p.allow_voice_input) },
  { label: 'Image upload for questions', cell: p => cmpTick(p.allow_image_input) },
  { label: 'Live chat takeover',         cell: p => cmpTick(p.allow_god_view) },
  { label: 'Real-time inventory sync',   cell: p => cmpTick(p.allow_real_time_inventory) },
  { label: 'Custom website integration', cell: p => cmpTick(p.allow_custom_domain) },
  { label: 'Custom internal DB',         cell: p => cmpTick(p.name === 'Enterprise') },
  { label: 'White-label branding',       cell: p => cmpTick(p.remove_branding) },
  { label: 'Support',                    cell: p => supportLabel(p) },
  { label: 'Reports / exports',          cell: p => reportsLabel(p) },
  { label: 'Data retention',             cell: p => retentionLabel(p) },
]
function formatPrice(p) {
  const n = parseFloat(p)
  if (isNaN(n)) return '—'
  return n === 0 ? '0' : n.toFixed(n % 1 === 0 ? 0 : 2)
}
function contactUs() {
  window.open('mailto:support@checkfunnels.com?subject=Plan inquiry', '_blank')
}
function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

// ── computed ─────────────────────────────────────────────────────────────────

const statusLabel = computed(() => {
  if (sub.value.trial_ends_at && new Date(sub.value.trial_ends_at) > new Date()) return 'Trial'
  const s = sub.value.stripe_subscription_status
  if (!s || s === 'active') return 'Active'
  if (s === 'past_due') return 'Past due'
  if (s === 'canceled') return 'Canceled'
  if (s === 'trialing') return 'Trial'
  return s
})

const statusClass = computed(() => {
  const s = sub.value.stripe_subscription_status
  if (s === 'past_due') return 'warn'
  if (s === 'canceled') return 'danger'
  return 'ok'
})

const usageResources = computed(() => {
  const u = sub.value.usage || {}

  function pct(used, limit) {
    if (limit < 0) return 0
    if (!limit) return 0
    return Math.min(Math.round((used / limit) * 100), 100)
  }

  return [
    { key: 'messages', label: 'AI Messages', used: u.messages?.used || 0, limit: u.messages?.limit ?? -1, pct: pct(u.messages?.used || 0, u.messages?.limit ?? -1) },
    { key: 'sessions', label: 'Chat Sessions', used: u.sessions?.used || 0, limit: u.sessions?.limit ?? -1, pct: pct(u.sessions?.used || 0, u.sessions?.limit ?? -1) },
    { key: 'images',   label: 'Image Uploads', used: u.images?.used || 0,   limit: u.images?.limit ?? -1,   pct: pct(u.images?.used || 0,   u.images?.limit ?? -1) },
    { key: 'voice',    label: 'Voice Commands', used: u.voice?.used || 0,    limit: u.voice?.limit ?? -1,    pct: pct(u.voice?.used || 0,    u.voice?.limit ?? -1) },
  ].filter(r => r.limit !== 0) // hide resources not in plan
})

const faqs = ref([
  { q: 'Can I switch plans mid-month?', a: 'Yes. Upgrades are pro-rated and take effect immediately. Downgrades apply at the start of the next billing cycle.', open: false },
  { q: "What counts as a 'message'?", a: 'One AI-generated response sent to a visitor. Human agent replies during Live Chat Takeover do NOT count toward your monthly limit.', open: false },
  { q: 'Is there a free trial?', a: 'Yes. All new accounts get a 14-day free trial on the Starter plan — no credit card required.', open: false },
  { q: 'What happens if I exceed my message limit?', a: 'You get alerts at 80% and 100%. After 100% you can either pay-as-you-go via the top-up packs above, or pause the chatbot until next month — your call.', open: false },
  { q: 'What happens to my data if I cancel?', a: 'Your data is retained for 30 days after cancellation so you can export it. After 30 days everything is permanently deleted.', open: false },
  { q: 'What is the annual discount?', a: 'Annual plans are billed upfront at 15% off — effectively two free months. Switch between monthly and annual any time.', open: false },
  { q: 'Can I use Checkfunnel without Stripe?', a: 'No. Stripe is the required payment processor for all subscription billing. A Stripe account is mandatory before going live.', open: false },
  { q: 'Is my payment information secure?', a: 'All payments are handled by Stripe — we never store your card details on our servers.', open: false },
  { q: 'Can I cancel anytime?', a: 'Yes — cancel from the Manage billing portal. Your access continues until the end of the current billing period.', open: false },
])


// ── data loading ─────────────────────────────────────────────────────────────

async function load() {
  // Only show the full skeleton on the very first load; subsequent refreshes
  // (navigation back, focus regain) should update silently in the background.
  const isInitial = !sub.value || !sub.value.plan
  if (isInitial) loading.value = true
  error.value = ''
  try {
    const [subData, planData] = await Promise.all([
      api.getSubscription(),
      api.getPublicPlans(),
    ])
    // Defensive: only overwrite sub.value if the API returned a real object.
    // A network blip or 401-then-refresh-failure can return undefined; in
    // that case we keep showing the last-known-good plan instead of
    // collapsing to "No plan / Free".
    if (subData && typeof subData === 'object') {
      sub.value = subData
      if (subData.billing_interval) billingInterval.value = subData.billing_interval
    }
    if (Array.isArray(planData)) plans.value = planData
    // Fetch invoices in the background (don't block main load)
    loadInvoices()
  } catch (e) {
    error.value = e.message || 'Failed to load billing info.'
  } finally {
    loading.value = false
  }
}

const route = useRoute()

// Refetch when the user navigates back to the billing route. Even though
// the router is not configured with <keep-alive>, this guards against
// future routing changes and the lifecycle is idempotent.
onActivated(load)

// Refetch when the tab regains focus (covers the case where the user
// completes Stripe checkout in another tab and comes back).
function onVisibilityChange() {
  if (document.visibilityState === 'visible') load()
}

onMounted(() => {
  load()
  document.addEventListener('visibilitychange', onVisibilityChange)
})

watch(() => route.fullPath, (newPath) => {
  if (newPath.startsWith('/portal/billing')) load()
})

async function checkout(plan) {
  error.value = ''
  checkoutLoading.value = plan.id
  const priceId = activePriceId(plan)
  if (!priceId) { error.value = 'This plan is not available yet.'; checkoutLoading.value = null; return }
  try {
    const { url } = await api.createCheckoutSession(plan.id)
    window.location.href = url
  } catch (e) {
    error.value = e.message || 'Could not start checkout. Please try again.'
    checkoutLoading.value = null
  }
}

async function openPortal() {
  error.value = ''
  portalLoading.value = true
  try {
    const { url } = await api.createPortalSession()
    window.location.href = url
  } catch (e) {
    error.value = e.message || 'Could not open billing portal.'
  } finally {
    portalLoading.value = false
  }
}

</script>

<style scoped>
.billing-page {
  padding: 32px;
  max-width: 1100px;
}

.page-header { margin-bottom: 28px; }
.page-title { font-size: 22px; font-weight: 700; color: var(--cf-text-primary); margin: 0 0 4px; }
.page-sub { font-size: 13px; color: var(--cf-text-muted); margin: 0; }

/* Skeleton */
.skeleton-wrap { display: flex; flex-direction: column; gap: 12px; }
.sk-card { background: var(--cf-bg-surface-raised); border: 1px solid var(--cf-border-subtle); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 10px; }
.sk-line { height: 12px; border-radius: 6px; background: var(--cf-bg-input); animation: pulse 1.5s ease-in-out infinite; }
.sk-line.w60 { width: 60%; }
.sk-line.w40 { width: 40%; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

/* Current plan card */
.current-plan-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  background: var(--cf-bg-surface-raised);
  border: 1px solid rgba(99,102,241,0.2);
  border-radius: 16px;
  padding: 24px 28px;
  margin-bottom: 16px;
  gap: 20px;
}
.current-plan-card.warn { border-color: rgba(245,158,11,0.3); }
.current-plan-card.danger { border-color: rgba(239,68,68,0.3); }

.cp-badge {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 3px 8px;
  border-radius: 6px;
  margin-bottom: 8px;
  background: rgba(34,197,94,0.1);
  color: #22c55e;
  border: 1px solid rgba(34,197,94,0.2);
}
.cp-badge.warn { background: rgba(245,158,11,0.1); color: #f59e0b; border-color: rgba(245,158,11,0.2); }
.cp-badge.danger { background: rgba(239,68,68,0.1); color: #ef4444; border-color: rgba(239,68,68,0.2); }

.cp-plan-name { font-size: 20px; font-weight: 700; color: var(--cf-text-primary); margin: 0 0 4px; }
.cp-price { font-size: 28px; font-weight: 800; color: var(--cf-text-primary); margin: 0 0 6px; display: flex; align-items: baseline; gap: 6px; flex-wrap: wrap; }
.cp-price span:first-child { font-size: 14px; font-weight: 400; color: var(--cf-text-muted); }
.annual-tag { font-size: 11px; font-weight: 600; color: #a78bfa; background: rgba(167,139,250,0.1); border: 1px solid rgba(167,139,250,0.2); border-radius: 6px; padding: 2px 8px; }

.trial-notice {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: #a78bfa;
  background: rgba(167,139,250,0.08);
  border: 1px solid rgba(167,139,250,0.2);
  border-radius: 8px;
  padding: 5px 10px;
  margin-top: 8px;
  width: fit-content;
}

/* Usage section */
.usage-section { margin-bottom: 20px; }
.usage-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.usage-card {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.usage-label {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 600;
  color: var(--cf-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.usage-nums { color: var(--cf-text-primary); font-weight: 700; text-transform: none; letter-spacing: 0; }
.usage-bar { height: 6px; background: var(--cf-bg-ghost); border-radius: 6px; overflow: hidden; }
.usage-fill { height: 100%; border-radius: 6px; transition: width 0.4s; }
.usage-warn { font-size: 11px; color: #f59e0b; }

.btn-portal {
  background: rgba(99,102,241,0.1);
  border: 1px solid rgba(99,102,241,0.3);
  color: #a5b4fc;
  border-radius: 10px;
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}
.btn-portal:hover:not(:disabled) { background: rgba(99,102,241,0.2); }
.btn-portal:disabled { opacity: 0.5; cursor: not-allowed; }

/* Invoices section */
.invoices-section {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 14px;
  padding: 20px 22px;
  margin: 16px 0 20px;
}
.invoices-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.section-sub-mini {
  font-size: 12px;
  color: var(--cf-text-muted);
  margin: 4px 0 0;
  line-height: 1.5;
  max-width: 560px;
}
.btn-test-invoice {
  background: rgba(99,102,241,0.1);
  border: 1px solid rgba(99,102,241,0.3);
  color: #a5b4fc;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.btn-test-invoice:hover:not(:disabled) { background: rgba(99,102,241,0.18); }
.btn-test-invoice:disabled { opacity: 0.5; cursor: not-allowed; }
.test-invoice-msg {
  font-size: 12px;
  border-radius: 8px;
  padding: 8px 12px;
  margin: 0 0 12px;
}
.test-invoice-msg.ok { background: rgba(34,197,94,0.08); border: 1px solid rgba(34,197,94,0.25); color: #4ade80; }
.test-invoice-msg.err { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); color: #fca5a5; }
.invoices-empty {
  font-size: 13px;
  color: var(--cf-text-muted);
  text-align: center;
  padding: 20px 12px;
  border: 1px dashed var(--cf-border-subtle);
  border-radius: 10px;
}
.invoice-list { display: flex; flex-direction: column; gap: 8px; }
.invoice-row {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--cf-bg-input);
  border-radius: 10px;
  flex-wrap: wrap;
  padding: 12px 14px;
}
.invoice-left { flex: 1 1 160px; min-width: 0; }
/* Long hyphenated invoice numbers must NOT break per character on mobile —
   keep them on one line and let them scroll within their cell if needed. */
.invoice-number {
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: var(--cf-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.invoice-period { font-size: 14px; font-weight: 600; color: var(--cf-text-primary); margin-top: 2px; }
.invoice-center { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.invoice-status {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 6px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: var(--cf-bg-ghost);
  color: var(--cf-text-muted);
  border: 1px solid var(--cf-border-subtle);
}
.invoice-status.inv-sent { background: rgba(34,197,94,0.12); color: #22c55e; border-color: rgba(34,197,94,0.25); }
.invoice-status.inv-issued { background: rgba(99,102,241,0.12); color: #a5b4fc; border-color: rgba(99,102,241,0.3); }
.invoice-status.inv-paid { background: rgba(34,197,94,0.18); color: #4ade80; border-color: rgba(34,197,94,0.4); }
.invoice-status.inv-draft { background: rgba(245,158,11,0.12); color: #fbbf24; border-color: rgba(245,158,11,0.25); }
.invoice-status.inv-void { background: rgba(239,68,68,0.1); color: #fca5a5; border-color: rgba(239,68,68,0.25); }
.invoice-total { font-size: 14px; font-weight: 700; color: var(--cf-text-primary); font-variant-numeric: tabular-nums; }
.invoice-actions { display: flex; gap: 6px; flex-shrink: 0; }
.btn-invoice-view,
.btn-invoice-pdf {
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  padding: 6px 10px;
  border-radius: 6px;
  white-space: nowrap;
}
.btn-invoice-view {
  color: #a5b4fc;
  background: rgba(99,102,241,0.08);
  border: 1px solid rgba(99,102,241,0.25);
}
.btn-invoice-view:hover { background: rgba(99,102,241,0.18); }
.btn-invoice-pdf {
  color: #ffffff;
  background: #6366f1;
  border: 1px solid #6366f1;
}
.btn-invoice-pdf:hover { background: #4f46e5; border-color: #4f46e5; }

/* Alert banners */
.alert-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  border-radius: 10px;
  padding: 12px 16px;
  font-size: 13px;
  margin-bottom: 12px;
}
.alert-banner.warn { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.2); color: #fcd34d; }
.alert-banner.danger { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); color: #fca5a5; }
.btn-link { background: none; border: none; text-decoration: underline; cursor: pointer; color: inherit; font-size: 13px; margin-left: auto; }

/* F7 — Add-on top-ups */
.addon-section {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 14px;
  padding: 20px 22px;
  margin: 16px 0 20px;
}
/* Add-ons / custom → contact team card */
.contact-card { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.contact-card-icon { font-size: 28px; line-height: 1; flex-shrink: 0; }
.contact-card-body { flex: 1 1 240px; min-width: 0; }
.contact-card-title { font-size: 15px; font-weight: 600; color: var(--cf-text-primary); margin-bottom: 4px; }
.contact-card-sub { font-size: 13px; color: var(--cf-text-muted); line-height: 1.5; }
.contact-card-btn {
  flex-shrink: 0;
  display: inline-block;
  background: #6366f1; color: #fff; text-decoration: none;
  font-size: 13px; font-weight: 600;
  padding: 10px 18px; border-radius: 9px;
  transition: opacity 0.15s;
}
.contact-card-btn:hover { opacity: 0.9; }
@media (max-width: 480px) { .contact-card-btn { width: 100%; text-align: center; } }
.section-heading + .section-sub { margin-top: -8px; }
.addon-section .section-sub {
  font-size: 13px;
  color: var(--cf-text-muted);
  line-height: 1.5;
  margin: 6px 0 14px;
}
.addon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.addon-card {
  background: var(--cf-bg-input);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.addon-card-header { display: flex; align-items: center; gap: 8px; }
.addon-icon { font-size: 20px; }
.addon-label { font-size: 13px; font-weight: 600; color: var(--cf-text-primary); }
.addon-price-line { font-size: 18px; font-weight: 700; color: var(--cf-text-primary); }
.addon-price-line span { font-size: 11px; font-weight: 500; color: var(--cf-text-muted); margin-left: 3px; }
.addon-bundles { display: flex; flex-direction: column; gap: 6px; }
.addon-bundle-btn {
  background: rgba(99,102,241,0.08);
  border: 1px solid rgba(99,102,241,0.25);
  color: var(--cf-text-primary);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.addon-bundle-btn:hover:not(:disabled) { background: rgba(99,102,241,0.15); }
.addon-bundle-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.addon-error {
  margin-top: 10px;
  font-size: 12px;
  color: #fca5a5;
  background: rgba(239,68,68,0.08);
  border: 1px solid rgba(239,68,68,0.2);
  border-radius: 8px;
  padding: 8px 12px;
}

/* Billing interval toggle */
.interval-toggle-wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 24px 0 16px;
}
.interval-toggle {
  display: flex;
  background: var(--cf-bg-surface);
  border: 1px solid var(--cf-border-default);
  border-radius: 10px;
  padding: 3px;
  gap: 3px;
}
.interval-toggle button {
  background: none;
  border: none;
  border-radius: 8px;
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 600;
  color: var(--cf-text-muted);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.interval-toggle button.active { background: rgba(99,102,241,0.2); color: #a5b4fc; }
.save-badge {
  font-size: 10px;
  font-weight: 700;
  background: rgba(167,139,250,0.15);
  color: #a78bfa;
  border-radius: 5px;
  padding: 1px 6px;
}

/* Plan grid */
.section-heading { font-size: 14px; font-weight: 600; color: var(--cf-text-muted); text-transform: uppercase; letter-spacing: 0.06em; margin: 0 0 16px; }

.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 28px;
}

.plan-card {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
  transition: border-color 0.2s;
}
.plan-card.popular {
  border-color: rgba(99,102,241,0.4);
  background: linear-gradient(135deg, var(--cf-popular-card-bg-start), var(--cf-popular-card-bg-end));
}
.plan-card.current { border-color: rgba(34,197,94,0.3); }

.plan-popular-badge {
  position: absolute;
  top: -11px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  font-size: 10px;
  font-weight: 700;
  padding: 3px 12px;
  border-radius: 20px;
  white-space: nowrap;
}

.plan-header { display: flex; flex-direction: column; gap: 4px; }
.plan-name { font-size: 13px; font-weight: 600; color: var(--cf-text-secondary); text-transform: uppercase; letter-spacing: 0.06em; }
.plan-price { display: flex; align-items: baseline; gap: 2px; }
.plan-amount { font-size: 32px; font-weight: 800; color: var(--cf-text-primary); }
.plan-period { font-size: 13px; color: var(--cf-text-muted); }
.plan-annual-note { font-size: 11px; color: var(--cf-text-muted); margin-top: 2px; }

.plan-features { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
.plan-features li { display: flex; align-items: flex-start; gap: 8px; font-size: 13px; color: var(--cf-text-secondary); line-height: 1.4; }
.plan-features li svg { flex-shrink: 0; margin-top: 2px; }

.plan-btn {
  width: 100%;
  border-radius: 10px;
  padding: 11px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: opacity 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: auto;
}
.plan-btn-current { background: rgba(34,197,94,0.1); color: #22c55e; border: 1px solid rgba(34,197,94,0.2); cursor: default; }
.plan-btn-upgrade { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; }
.plan-btn-contact { background: rgba(99,102,241,0.08); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.2); }
.plan-btn-contact:hover { background: rgba(99,102,241,0.15); }
.plan-btn:disabled:not(.plan-btn-current) { opacity: 0.4; cursor: not-allowed; }
.plan-btn-upgrade:hover:not(:disabled) { opacity: 0.9; }
.plan-amount-custom { font-size: 22px; color: var(--cf-text-muted); }

/* Spinner */
.spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: white; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Error */
.error-msg { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); border-radius: 10px; padding: 12px 16px; color: #fca5a5; font-size: 13px; margin-bottom: 16px; }

/* ── Feature comparison matrix ─────────────────────────────────────────── */
.compare-section { margin: 28px 0 8px; }
.compare-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  border: 1px solid var(--cf-border-subtle);
  border-radius: 14px;
  background: var(--cf-bg-surface-raised);
}
.compare-table { width: 100%; min-width: 600px; border-collapse: collapse; }
.compare-table th,
.compare-table td {
  padding: 12px 14px;
  text-align: left;
  font-size: 13px;
  border-bottom: 1px solid var(--cf-border-subtle);
  vertical-align: middle;
  white-space: nowrap;
}
.compare-table tbody tr:last-child td { border-bottom: none; }
.compare-table thead th {
  position: sticky; top: 0; z-index: 1;
  background: var(--cf-bg-surface);
  font-size: 12px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.04em;
  color: var(--cf-text-secondary);
}
/* Sticky first column so the feature name stays visible while scrolling. */
.cmp-feature, .cmp-feature-h {
  position: sticky; left: 0; z-index: 1;
  background: var(--cf-bg-surface-raised);
  color: var(--cf-text-primary); font-weight: 500;
}
.compare-table thead .cmp-feature-h { background: var(--cf-bg-surface); z-index: 2; }
.cmp-col-current { background: rgba(99,102,241,0.07); }
.compare-table thead th.cmp-col-current { background: rgba(99,102,241,0.12); }
.cmp-col-popular { color: #a5b4fc; }
.cmp-pop-badge, .cmp-cur-badge {
  display: inline-block; margin-left: 6px;
  font-size: 9px; font-weight: 700; letter-spacing: 0.03em;
  padding: 2px 6px; border-radius: 5px; vertical-align: middle;
  text-transform: none;
}
.cmp-pop-badge { background: rgba(99,102,241,0.18); color: #a5b4fc; }
.cmp-cur-badge { background: rgba(34,197,94,0.15); color: #4ade80; }
:deep(.cmp-yes) { color: #22c55e; font-weight: 700; }
:deep(.cmp-no) { color: var(--cf-text-muted); }
:deep(.cmp-opt) { font-size: 11px; color: var(--cf-text-muted); font-weight: 400; }
.compare-note {
  font-size: 12px; color: var(--cf-text-muted);
  margin: 12px 2px 0; line-height: 1.6;
}
.compare-note a { color: #a5b4fc; }

/* FAQ */
.faq-section { margin-top: 8px; }
.faq-list { display: flex; flex-direction: column; gap: 1px; }
.faq-item {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 10px;
  padding: 14px 18px;
  cursor: pointer;
  margin-bottom: 6px;
}
.faq-q { display: flex; justify-content: space-between; align-items: center; font-size: 14px; color: var(--cf-text-primary); font-weight: 500; }
.faq-a { font-size: 13px; color: var(--cf-text-muted); margin-top: 10px; line-height: 1.6; }

/* ══════════════════════════════════════════════════════════════════════════
   Documentation sections — shared building blocks first, then per-section.
   ══════════════════════════════════════════════════════════════════════════ */

.doc-section { margin-top: 28px; }
.doc-section + .doc-section { margin-top: 28px; }
.doc-sub {
  font-size: 13px;
  color: var(--cf-text-muted);
  margin: -4px 0 12px;
  line-height: 1.55;
}
.doc-subheading {
  font-size: 14px;
  font-weight: 600;
  color: var(--cf-text-primary);
  margin: 22px 0 12px;
}

/* Generic card used by every doc section. */
.doc-card {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 14px;
  padding: 22px 24px;
  box-sizing: border-box;
}
.doc-card-table { padding: 0; overflow: hidden; }
.doc-table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  max-width: 100%;
}
.doc-table {
  width: 100%;
  min-width: 560px;
  border-collapse: collapse;
}
.doc-table thead th {
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--cf-text-muted);
  padding: 14px 16px;
  background: rgba(255,255,255,0.025);
  border-bottom: 1px solid var(--cf-border-subtle);
  white-space: nowrap;
}
.doc-table th.th-starter { color: #60a5fa; }
.doc-table th.th-growth  { color: #c4b5fd; }
.doc-table th.th-pro     { color: #fbbf24; }
.doc-table th.th-enterprise { color: var(--cf-text-secondary); }
.doc-table th.th-us      { color: #a5b4fc; }
.doc-table td {
  padding: 12px 16px;
  font-size: 13px;
  color: var(--cf-text-secondary);
  border-bottom: 1px solid var(--cf-border-subtle);
  vertical-align: top;
  line-height: 1.5;
}
.doc-table tr:last-child td { border-bottom: none; }
.doc-table td:first-child { color: var(--cf-text-primary); font-weight: 500; white-space: nowrap; }
.doc-table .req { color: #22c55e; font-weight: 600; }
.doc-table .cell-us {
  color: var(--cf-text-primary);
  font-weight: 600;
  background: rgba(99,102,241,0.07);
}
.doc-note {
  margin: 12px 18px 18px;
  padding-top: 10px;
  font-size: 12px;
  font-style: italic;
  color: var(--cf-text-muted);
  line-height: 1.6;
}
.doc-note a { color: #a5b4fc; }

/* Expandable section header (Show / Hide) */
.doc-section-head {
  display: flex; align-items: center; justify-content: space-between;
  cursor: pointer;
  user-select: none;
  margin-bottom: 12px;
}
.doc-toggle {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--cf-bg-ghost);
  border: 1px solid var(--cf-border-default);
  color: var(--cf-text-secondary);
  font-size: 12px; font-weight: 500;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-family: inherit;
}
.doc-toggle:hover { background: var(--cf-bg-ghost-hover); color: var(--cf-text-primary); }

/* 1) Pricing philosophy ───────────────────────────────────────────────── */
.philosophy-card { padding: 24px; }
.philosophy-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
}
.philosophy-item { min-width: 0; }
.philosophy-icon { font-size: 22px; line-height: 1; margin-bottom: 8px; }
.philosophy-title { font-size: 14px; font-weight: 600; color: var(--cf-text-primary); margin-bottom: 6px; }
.philosophy-body { font-size: 13px; color: var(--cf-text-muted); line-height: 1.55; }
.philosophy-divider {
  height: 1px; background: var(--cf-border-subtle);
  margin: 20px 0 16px;
}
.philosophy-foot {
  font-size: 13px;
  color: var(--cf-text-secondary);
  line-height: 1.6;
}
.philosophy-foot strong { color: var(--cf-text-primary); }
.philosophy-foot em { color: #22c55e; font-style: normal; font-weight: 600; }

/* 3) BYOK card ────────────────────────────────────────────────────────── */
.byok-card { padding: 22px 24px; }
.byok-head { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
.byok-chip {
  display: inline-block; align-self: flex-start;
  background: rgba(99,102,241,0.12);
  border: 1px solid rgba(99,102,241,0.3);
  color: #a5b4fc;
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.06em;
  padding: 3px 10px; border-radius: 20px;
}
.byok-lead { font-size: 14px; color: var(--cf-text-secondary); line-height: 1.6; margin: 0; }
.byok-benefits {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px 18px;
  margin-bottom: 16px;
}
.byok-benefit {
  display: flex; gap: 8px; align-items: flex-start;
  font-size: 13px; color: var(--cf-text-secondary);
  line-height: 1.5;
}
.byok-tick { color: #22c55e; font-weight: 700; flex-shrink: 0; }
.byok-default {
  background: var(--cf-bg-input);
  border-left: 3px solid #6366f1;
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 12.5px;
  color: var(--cf-text-muted);
  line-height: 1.55;
}
.byok-default strong { color: var(--cf-text-primary); }

/* 6) Industry use cases ──────────────────────────────────────────────── */
.industry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}
.industry-card {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 12px;
  padding: 16px 18px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  min-width: 0;
}
.industry-card:hover { border-color: rgba(99,102,241,0.4); }
.industry-card.open { background: var(--cf-bg-input); }
.industry-head {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
}
.industry-title-row { display: flex; align-items: center; gap: 12px; min-width: 0; flex: 1; }
.industry-emoji { font-size: 26px; line-height: 1; flex-shrink: 0; }
.industry-title { font-size: 14px; font-weight: 600; color: var(--cf-text-primary); line-height: 1.2; }
.industry-tagline { font-size: 12px; color: var(--cf-text-muted); margin-top: 3px; line-height: 1.4; }
.industry-chevron { color: var(--cf-text-muted); flex-shrink: 0; }
.industry-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--cf-border-subtle);
}
.industry-col-title {
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--cf-text-muted);
  margin-bottom: 8px;
}
.industry-col ul { margin: 0; padding-left: 18px; list-style: disc; }
.industry-col li { font-size: 12.5px; color: var(--cf-text-secondary); line-height: 1.55; margin-bottom: 4px; }
.industry-meta { margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; font-size: 12.5px; line-height: 1.5; }
.industry-meta dt { color: var(--cf-text-muted); font-weight: 500; }
.industry-meta dd { color: var(--cf-text-primary); margin: 0; }

/* Subtle per-industry accent stripes */
.ind-hotel.open       { border-color: rgba(59,130,246,0.4); }
.ind-retail.open      { border-color: rgba(34,197,94,0.4); }
.ind-healthcare.open  { border-color: rgba(236,72,153,0.4); }
.ind-realestate.open  { border-color: rgba(217,119,6,0.4); }
.ind-education.open   { border-color: rgba(139,92,246,0.4); }

/* 7) Build your own custom package ───────────────────────────────────── */
.custom-hero {
  background: linear-gradient(135deg, rgba(99,102,241,0.12) 0%, rgba(139,92,246,0.08) 100%);
  border-color: rgba(99,102,241,0.3);
  text-align: center;
  padding: 26px 24px;
}
.custom-hero-title { font-size: 18px; font-weight: 700; color: var(--cf-text-primary); margin-bottom: 8px; }
.custom-hero-sub { font-size: 13px; color: var(--cf-text-secondary); line-height: 1.6; max-width: 560px; margin: 0 auto; }

.custom-steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 14px;
}
.custom-step {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 12px;
  padding: 16px 18px;
}
.custom-step-num { font-size: 18px; color: #a5b4fc; font-weight: 700; line-height: 1; margin-bottom: 8px; }
.custom-step-title { font-size: 14px; font-weight: 600; color: var(--cf-text-primary); margin-bottom: 6px; }
.custom-step-body { font-size: 12.5px; color: var(--cf-text-muted); line-height: 1.55; }

.packages-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}
.package-card {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 12px;
  padding: 18px 18px 16px;
  display: flex; flex-direction: column;
  gap: 8px;
}
.package-card.pkg-wa    { border-top: 3px solid #22c55e; }
.package-card.pkg-crm   { border-top: 3px solid #60a5fa; }
.package-card.pkg-omni  { border-top: 3px solid #c4b5fd; }
.package-card.pkg-full  { border-top: 3px solid #fbbf24; }
.package-name { font-size: 14px; font-weight: 700; color: var(--cf-text-primary); }
.package-tagline { font-size: 12px; color: var(--cf-text-muted); margin-bottom: 4px; }
.package-features { margin: 0; padding-left: 18px; list-style: none; display: flex; flex-direction: column; gap: 4px; }
.package-features li {
  position: relative;
  font-size: 12.5px;
  color: var(--cf-text-secondary);
  line-height: 1.5;
}
.package-features li::before {
  content: '✓';
  position: absolute;
  left: -16px;
  color: #22c55e;
  font-weight: 700;
}
.package-price {
  margin-top: auto;
  font-size: 13px;
  font-weight: 600;
  color: #a5b4fc;
  border-top: 1px dashed var(--cf-border-subtle);
  padding-top: 10px;
}

.custom-cta {
  margin-top: 18px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  border-radius: 12px;
  padding: 22px 24px;
  text-align: center;
}
.custom-cta-title { font-size: 16px; font-weight: 700; color: #ffffff; margin-bottom: 6px; }
.custom-cta-sub   { font-size: 13px; color: rgba(255,255,255,0.85); margin-bottom: 14px; line-height: 1.5; }
.custom-cta-btn {
  display: inline-block;
  background: #ffffff;
  color: #4f46e5;
  font-size: 14px; font-weight: 700;
  text-decoration: none;
  padding: 10px 22px;
  border-radius: 9px;
  transition: transform 0.12s;
}
.custom-cta-btn:hover { transform: translateY(-1px); }

/* ── Mobile breakpoints for doc sections ─────────────────────────────── */
@media (max-width: 720px) {
  .philosophy-row { grid-template-columns: 1fr 1fr; }
  .industry-body  { grid-template-columns: 1fr; }
  .custom-steps   { grid-template-columns: 1fr; }
  .byok-benefits  { grid-template-columns: 1fr; }
}
@media (max-width: 480px) {
  .doc-card { padding: 18px 16px; }
  .philosophy-row { grid-template-columns: 1fr; }
  .industry-card { padding: 14px 14px; }
  .industry-emoji { font-size: 22px; }
  .custom-hero { padding: 22px 16px; }
  .custom-hero-title { font-size: 16px; }
  .custom-cta { padding: 20px 16px; }
  .custom-cta-title { font-size: 15px; }
  .doc-table { min-width: 480px; }
  .doc-section-head { flex-wrap: wrap; gap: 8px; }
}

@media (max-width: 768px) {
  .page-header { flex-direction: column; gap: 12px; align-items: flex-start; }
  .current-plan-card { flex-direction: column; }
  .billing-page { padding: 20px 16px; }
  .interval-toggle-wrap { flex-direction: column; align-items: stretch; gap: 12px; }
  .cp-price { font-size: 24px; }
}

/* Phone-width tightening for the invoice list — labels, totals, and
   View/Download buttons re-flow into three rows so nothing is clipped. */
@media (max-width: 480px) {
  .invoice-row {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
    padding: 12px 14px;
  }
  .invoice-left { flex: 1 1 auto; width: 100%; }
  .invoice-center { width: 100%; justify-content: space-between; }
  .invoice-actions { width: 100%; gap: 8px; }
  .invoice-actions > * { flex: 1 1 auto; text-align: center; }
}
</style>
