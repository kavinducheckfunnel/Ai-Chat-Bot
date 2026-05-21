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
          <div class="live-update-banner">
            ⚡ <strong>Paste once.</strong> Change color, name, theme, or CTA from this panel anytime — the widget on your site picks up changes on the next page load and re-checks every 60 seconds. <strong>No re-paste ever needed</strong> for branding changes.
          </div>

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
          <label>Follow-up CTA</label>
          <p class="field-hint">
            Sent as a follow-up if a visitor goes idle for 2 minutes (and on key behavior signals when AI mode is on). Pick one strategy — they won't fire together.
          </p>
          <div class="cta-mode-row">
            <label class="cta-mode-opt" :class="{ active: form.cta_mode === 'ai' }">
              <input type="radio" v-model="form.cta_mode" value="ai" />
              <div class="cta-mode-body">
                <span class="cta-mode-title">✨ AI-generated</span>
                <span class="cta-mode-desc">Personalised from each visitor's browsing + intent signals.</span>
              </div>
            </label>
            <label class="cta-mode-opt" :class="{ active: form.cta_mode === 'manual' }">
              <input type="radio" v-model="form.cta_mode" value="manual" />
              <div class="cta-mode-body">
                <span class="cta-mode-title">📝 Manual message</span>
                <span class="cta-mode-desc">Send the exact text you write below to every visitor.</span>
              </div>
            </label>
            <label class="cta-mode-opt" :class="{ active: form.cta_mode === 'off' }">
              <input type="radio" v-model="form.cta_mode" value="off" />
              <div class="cta-mode-body">
                <span class="cta-mode-title">⛔ Off</span>
                <span class="cta-mode-desc">No automated follow-ups. AI still replies to direct messages.</span>
              </div>
            </label>
          </div>
        </div>

        <!-- Manual CTA text input — only relevant when manual is selected -->
        <div v-if="form.cta_mode === 'manual'" class="field">
          <label>
            CTA message
            <button class="suggest-cta-btn" @click="suggestCtaFromBehavior" :disabled="ctaSuggesting" type="button">
              <span v-if="ctaSuggesting" class="mini-spinner"></span>
              <span v-else>✨ Suggest from behavior</span>
            </button>
          </label>
          <input v-model="form.cta_message" type="text" class="input" placeholder="You're clearly ready — grab your exclusive discount:" />
          <div v-if="ctaSuggestions.length" class="cta-suggestions">
            <p class="cta-suggestions-hint">Click to apply, or keep your custom message:</p>
            <button
              v-for="(s, i) in ctaSuggestions"
              :key="i"
              type="button"
              class="cta-suggestion-pill"
              @click="form.cta_message = s"
            >{{ s }}</button>
          </div>
          <p v-if="ctaSuggestError" class="cta-error">{{ ctaSuggestError }}</p>
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

      <!-- Canned responses -->
      <div class="gate-wrap">
        <div v-if="features.allow_canned_responses === false" class="gate-overlay">
          <div class="gate-lock">🔒</div>
          <div class="gate-msg">Canned Responses require the <strong>Starter</strong> plan or higher.</div>
          <a href="/portal/billing" class="gate-upgrade-btn">Upgrade to Starter →</a>
        </div>
      <div class="section-card">
        <h2 class="section-title">Canned responses</h2>
        <p class="section-sub">Quick-reply shortcuts available during live takeover. Click to insert into the message box.</p>
        <div class="canned-list">
          <div v-for="(cr, idx) in cannedResponses" :key="cr.id" class="canned-row">
            <div class="canned-fields">
              <input class="input" type="text" v-model="cr.title" placeholder="Title (e.g. Greeting)" maxlength="60" />
              <textarea class="input canned-body" v-model="cr.body" placeholder="Response text…" rows="2" maxlength="500" />
            </div>
            <button class="canned-del" @click="removeCanned(idx)" title="Remove">✕</button>
          </div>
          <button class="btn-add-canned" @click="addCanned">+ Add response</button>
        </div>
        <div class="save-row">
          <button class="btn-save" @click="saveCanned" :disabled="cannedSaving">{{ cannedSaving ? 'Saving…' : cannedSaved ? '✓ Saved' : 'Save canned responses' }}</button>
        </div>
      </div>
      </div><!-- end gate-wrap -->
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

      <!-- ─── Real-time sync (webhooks) ─────────────────────────────────── -->
      <div class="section-card">
        <h2 class="section-title">⚡ Real-time sync</h2>
        <p class="section-sub">
          Get content changes pushed to your chatbot the moment they happen on your site — no waiting for the daily safety-net crawl. Configure your CMS to call the webhook URL for your platform below.
        </p>

        <!-- 24h activity strip — shows webhooks are actually firing -->
        <div class="wh-counters">
          <div class="wh-counter wh-counter-done">
            <span class="wh-counter-num">{{ webhook.counts_24h.done }}</span>
            <span class="wh-counter-label">Successful (24h)</span>
          </div>
          <div class="wh-counter wh-counter-queued">
            <span class="wh-counter-num">{{ webhook.counts_24h.queued }}</span>
            <span class="wh-counter-label">In flight</span>
          </div>
          <div class="wh-counter wh-counter-failed">
            <span class="wh-counter-num">{{ webhook.counts_24h.failed }}</span>
            <span class="wh-counter-label">Failed</span>
          </div>
          <button class="wh-refresh" @click="loadWebhookData" :disabled="webhookLoading">
            <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            Refresh
          </button>
        </div>

        <!-- Platform picker (decides which setup card to show) -->
        <div class="wh-platform-tabs">
          <button
            v-for="p in webhookPlatforms" :key="p.id"
            class="wh-platform-tab"
            :class="{ active: webhookPlatform === p.id }"
            @click="webhookPlatform = p.id"
          >
            <span class="wh-platform-icon" v-html="p.icon"></span>
            {{ p.label }}
          </button>
        </div>

        <!-- Per-platform setup card -->
        <div v-if="webhookPlatform === 'wordpress'" class="wh-setup-card">
          <p class="wh-setup-title">Install a webhook on WordPress (3 steps)</p>
          <ol class="wh-steps">
            <li>Install the free <strong>WP Webhooks</strong> plugin from the WordPress plugin directory.</li>
            <li>Go to <strong>WP Webhooks → Send Data → Add new webhook URL</strong>. Choose triggers: <em>post created</em>, <em>post updated</em>, <em>post deleted</em>.</li>
            <li>Paste the URL below into the webhook destination and the secret into the <em>Secret key</em> field.</li>
          </ol>
          <div class="wh-paste-row">
            <span class="wh-paste-label">Webhook URL</span>
            <code class="wh-paste-code">{{ webhook.webhook_urls.wordpress }}</code>
            <button class="wh-copy" @click="copyText(webhook.webhook_urls.wordpress, 'wp-url')">
              {{ copiedKey === 'wp-url' ? '✓' : 'Copy' }}
            </button>
          </div>
        </div>

        <div v-if="webhookPlatform === 'woocommerce'" class="wh-setup-card">
          <p class="wh-setup-title">Add a WooCommerce webhook</p>
          <ol class="wh-steps">
            <li>In WooCommerce → <strong>Settings → Advanced → Webhooks → Add webhook</strong>.</li>
            <li>Set <strong>Topic</strong> to <em>Product updated</em> (repeat with <em>Product created</em> and <em>Product deleted</em> for full coverage).</li>
            <li>Paste the URL below into <strong>Delivery URL</strong> and the secret into <strong>Secret</strong>.</li>
          </ol>
          <div class="wh-paste-row">
            <span class="wh-paste-label">Delivery URL</span>
            <code class="wh-paste-code">{{ webhook.webhook_urls.woocommerce }}</code>
            <button class="wh-copy" @click="copyText(webhook.webhook_urls.woocommerce, 'wc-url')">
              {{ copiedKey === 'wc-url' ? '✓' : 'Copy' }}
            </button>
          </div>
        </div>

        <div v-if="webhookPlatform === 'shopify'" class="wh-setup-card">
          <p class="wh-setup-title">Register a Shopify webhook</p>
          <ol class="wh-steps">
            <li>In Shopify Admin → <strong>Settings → Notifications → Webhooks → Create webhook</strong>.</li>
            <li>Select event <em>Product update</em> (repeat with <em>Product creation</em> and <em>Product deletion</em>).</li>
            <li>Paste the URL below into <strong>URL</strong>, format <strong>JSON</strong>, and use the secret as the <strong>shared secret</strong> in Notifications settings.</li>
          </ol>
          <div class="wh-paste-row">
            <span class="wh-paste-label">URL</span>
            <code class="wh-paste-code">{{ webhook.webhook_urls.shopify }}</code>
            <button class="wh-copy" @click="copyText(webhook.webhook_urls.shopify, 'sh-url')">
              {{ copiedKey === 'sh-url' ? '✓' : 'Copy' }}
            </button>
          </div>
        </div>

        <div v-if="webhookPlatform === 'custom'" class="wh-setup-card">
          <p class="wh-setup-title">Custom HTML or SaaS site</p>
          <p class="wh-custom-note">
            Webhooks aren't possible for static-HTML / Webflow / Squarespace sites without a backend. Your knowledge base will be refreshed by the daily safety-net crawl (runs at 02:00 UTC). Use <strong>Re-train</strong> above to force an immediate refresh anytime.
          </p>
        </div>

        <!-- Webhook secret (shared across all platforms) -->
        <div class="wh-secret-row">
          <span class="wh-paste-label">Secret</span>
          <code class="wh-paste-code wh-secret-code">
            <template v-if="secretRevealed">{{ webhook.webhook_secret || '(none set yet — click Generate)' }}</template>
            <template v-else>{{ webhook.webhook_secret ? maskedSecret : '(none set yet — click Generate)' }}</template>
          </code>
          <button class="wh-copy" @click="secretRevealed = !secretRevealed" :title="secretRevealed ? 'Hide' : 'Reveal'">
            {{ secretRevealed ? 'Hide' : 'Reveal' }}
          </button>
          <button class="wh-copy" @click="copyText(webhook.webhook_secret, 'secret')" :disabled="!webhook.webhook_secret">
            {{ copiedKey === 'secret' ? '✓' : 'Copy' }}
          </button>
          <button class="wh-rotate" @click="rotateSecret" :disabled="rotating">
            {{ rotating ? '…' : (webhook.webhook_secret ? 'Rotate' : 'Generate') }}
          </button>
        </div>
        <p class="wh-secret-help">
          The secret signs every payload your CMS sends so we can verify it's really from you. Rotating invalidates the old one — paste the new value into your CMS immediately.
        </p>

        <!-- Recent activity -->
        <div class="wh-activity">
          <p class="wh-activity-title">Recent activity</p>
          <div v-if="!webhook.events.length" class="wh-empty">
            No webhook events yet. Once your CMS is configured above, updates will start landing here within seconds.
          </div>
          <div v-else class="wh-events-list">
            <div
              v-for="e in webhook.events.slice(0, 10)" :key="e.id"
              class="wh-event"
              :class="'wh-event-' + e.status"
            >
              <span class="wh-event-dot"></span>
              <span class="wh-event-source">{{ e.source }}</span>
              <span class="wh-event-title">{{ e.resource_title || e.resource_id || e.event_type }}</span>
              <span class="wh-event-time">{{ formatRelativeTime(e.created_at) }}</span>
              <span v-if="e.duration_ms != null" class="wh-event-dur">{{ e.duration_ms }}ms</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Integrations tab ─────────────────────────────────────────────────── -->
  <div v-if="activeTab === 'integrations'" class="tab-content">

    <!-- BYOK -->
    <div class="gate-wrap">
      <div v-if="features.allow_byok === false" class="gate-overlay">
        <div class="gate-lock">🔒</div>
        <div class="gate-msg">Custom AI (BYOK) requires the <strong>Growth</strong> plan or higher.</div>
        <a href="/portal/billing" class="gate-upgrade-btn">Upgrade to Growth →</a>
      </div>
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
          <div class="model-input-row">
            <input class="input" type="text" v-model="intForm.ai_model" placeholder="e.g. gpt-4o / google/gemini-2.0-flash-001" />
            <button
              v-if="intForm.ai_provider === 'openrouter'"
              class="btn-browse-models"
              @click="openModelPicker"
              type="button"
            >Browse</button>
          </div>
          <span class="field-hint">Leave blank to use the platform default. OpenRouter users can click Browse to choose from live models.</span>
        </div>
      </div>
      <div class="save-row">
        <button class="btn-save" @click="saveIntegrations" :disabled="intSaving">{{ intSaving ? 'Saving…' : intSaved ? '✓ Saved' : 'Save AI settings' }}</button>
      </div>

      <!-- Model picker modal -->
      <teleport to="body">
        <div v-if="modelPickerOpen" class="model-picker-overlay" @click.self="modelPickerOpen = false">
          <div class="model-picker-box">
            <div class="model-picker-header">
              <span>OpenRouter Models</span>
              <button class="model-picker-close" @click="modelPickerOpen = false">✕</button>
            </div>
            <input
              class="model-picker-search"
              v-model="modelPickerSearch"
              placeholder="Search models…"
              autofocus
            />
            <div class="model-picker-list" v-if="!modelPickerLoading">
              <div
                v-for="m in modelPickerFiltered"
                :key="m.id"
                class="model-picker-row"
                :class="{ 'model-picker-active': intForm.ai_model === m.id }"
                @click="selectPickerModel(m)"
              >
                <div class="mp-id">{{ m.id }}</div>
                <div class="mp-meta">
                  <span v-if="m.pricing?.prompt === '0'" class="mp-free">FREE</span>
                  <span v-else class="mp-paid">PAID</span>
                  <span v-if="m.context_length" class="mp-ctx">{{ (m.context_length / 1000).toFixed(0) }}k ctx</span>
                </div>
              </div>
              <div v-if="!modelPickerFiltered.length" class="mp-empty">No models match your search.</div>
            </div>
            <div v-else class="mp-loading">Loading models…</div>
          </div>
        </div>
      </teleport>
    </div>
    </div><!-- end gate-wrap -->

    <!-- WhatsApp -->
    <div class="gate-wrap">
      <div v-if="features.allow_whatsapp === false" class="gate-overlay">
        <div class="gate-lock">🔒</div>
        <div class="gate-msg">WhatsApp Business requires the <strong>Starter</strong> plan or higher.</div>
        <a href="/portal/billing" class="gate-upgrade-btn">Upgrade to Starter →</a>
      </div>
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
    </div><!-- end gate-wrap -->

    <!-- Messenger -->
    <div class="gate-wrap">
      <div v-if="features.allow_messenger === false" class="gate-overlay">
        <div class="gate-lock">🔒</div>
        <div class="gate-msg">Facebook Messenger requires the <strong>Growth</strong> plan or higher.</div>
        <a href="/portal/billing" class="gate-upgrade-btn">Upgrade to Growth →</a>
      </div>
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
    </div><!-- end gate-wrap -->

    <!-- HubSpot CRM -->
    <div class="gate-wrap">
      <div v-if="features.allow_hubspot === false" class="gate-overlay">
        <div class="gate-lock">🔒</div>
        <div class="gate-msg">HubSpot CRM integration requires the <strong>Growth</strong> plan or higher.</div>
        <a href="/portal/billing" class="gate-upgrade-btn">Upgrade to Growth →</a>
      </div>
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
    </div><!-- end gate-wrap -->

    <!-- Telegram Bot -->
    <div class="gate-wrap">
      <div v-if="features.allow_telegram === false" class="gate-overlay">
        <div class="gate-lock">🔒</div>
        <div class="gate-msg">Telegram Bot requires the <strong>Growth</strong> plan or higher.</div>
        <a href="/portal/billing" class="gate-upgrade-btn">Upgrade to Growth →</a>
      </div>
    <div class="section-card">
      <div class="section-header">
        <div class="section-icon" style="background:#0088cc20">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0088cc" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2L15 22 11 13 2 9l20-7z"/></svg>
        </div>
        <div>
          <h2 class="section-title">Telegram Bot</h2>
          <p class="section-sub">Connect a Telegram bot so visitors can chat via Telegram.</p>
        </div>
        <div class="status-badge" :class="intForm.telegram_enabled ? 'active' : 'inactive'">{{ intForm.telegram_enabled ? 'Enabled' : 'Disabled' }}</div>
      </div>
      <div class="form-grid">
        <div class="field" style="grid-column:1/-1">
          <label>Bot Token</label>
          <input class="input" type="password" v-model="intForm.telegram_bot_token" placeholder="123456:ABCdef..." autocomplete="off" />
          <span class="field-hint">Obtain from @BotFather on Telegram. Set the webhook URL to: <code>{{ telegramWebhookUrl }}</code></span>
        </div>
        <div class="field toggle-field" style="grid-column:1/-1">
          <label class="toggle-label">
            <input type="checkbox" v-model="intForm.telegram_enabled" class="toggle-input" />
            <span class="toggle-slider"></span>
            Enable Telegram channel
          </label>
        </div>
      </div>
      <div class="save-row">
        <button class="btn-save" @click="saveIntegrations" :disabled="intSaving">{{ intSaving ? 'Saving…' : intSaved ? '✓ Saved' : 'Save Telegram settings' }}</button>
      </div>
    </div>
    </div><!-- end gate-wrap -->

    <!-- Slack notifications -->
    <div class="gate-wrap">
      <div v-if="features.allow_slack === false" class="gate-overlay">
        <div class="gate-lock">🔒</div>
        <div class="gate-msg">Slack Notifications require the <strong>Starter</strong> plan or higher.</div>
        <a href="/portal/billing" class="gate-upgrade-btn">Upgrade to Starter →</a>
      </div>
    <div class="section-card">
      <div class="section-header">
        <div class="section-icon" style="background:#4a154b20">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4a154b" stroke-width="2"><rect x="2" y="2" width="8" height="8" rx="2"/><rect x="14" y="2" width="8" height="8" rx="2"/><rect x="2" y="14" width="8" height="8" rx="2"/><rect x="14" y="14" width="8" height="8" rx="2"/></svg>
        </div>
        <div>
          <h2 class="section-title">Slack Notifications</h2>
          <p class="section-sub">Get notified in Slack when a hot lead or new lead is captured.</p>
        </div>
        <div class="status-badge" :class="intForm.slack_webhook_url ? 'active' : 'inactive'">{{ intForm.slack_webhook_url ? 'Connected' : 'Not connected' }}</div>
      </div>
      <div class="form-grid">
        <div class="field" style="grid-column:1/-1">
          <label>Incoming Webhook URL</label>
          <input class="input" type="password" v-model="intForm.slack_webhook_url" placeholder="https://hooks.slack.com/services/..." autocomplete="off" />
          <span class="field-hint">Create an Incoming Webhook in your Slack workspace → Apps → Incoming Webhooks.</span>
        </div>
      </div>
      <div class="save-row">
        <button class="btn-save" @click="saveIntegrations" :disabled="intSaving">{{ intSaving ? 'Saving…' : intSaved ? '✓ Saved' : 'Save Slack settings' }}</button>
      </div>
    </div>
    </div><!-- end gate-wrap -->

    <!-- Outbound Webhooks (Zapier / n8n) -->
    <div class="gate-wrap">
      <div v-if="features.allow_webhooks === false" class="gate-overlay">
        <div class="gate-lock">🔒</div>
        <div class="gate-msg">Outbound Webhooks require the <strong>Growth</strong> plan or higher.</div>
        <a href="/portal/billing" class="gate-upgrade-btn">Upgrade to Growth →</a>
      </div>
    <div class="section-card">
      <div class="section-header">
        <div class="section-icon" style="background:#ff620020">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ff6200" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
        </div>
        <div>
          <h2 class="section-title">Outbound Webhook (Zapier / n8n)</h2>
          <p class="section-sub">POST event data to an external URL when key events occur.</p>
        </div>
        <div class="status-badge" :class="intForm.outbound_webhook_url ? 'active' : 'inactive'">{{ intForm.outbound_webhook_url ? 'Active' : 'Not set' }}</div>
      </div>
      <div class="form-grid">
        <div class="field" style="grid-column:1/-1">
          <label>Webhook URL</label>
          <input class="input" type="text" v-model="intForm.outbound_webhook_url" placeholder="https://hooks.zapier.com/hooks/catch/..." />
        </div>
        <div class="field" style="grid-column:1/-1">
          <label>Events to send (comma-separated)</label>
          <input class="input" type="text" v-model="intForm.outbound_webhook_events" placeholder="hot_lead,lead_captured,new_session" />
          <span class="field-hint">Available events: <code>hot_lead</code>, <code>lead_captured</code>, <code>new_session</code></span>
        </div>
      </div>
      <div class="save-row">
        <button class="btn-save" @click="saveIntegrations" :disabled="intSaving">{{ intSaving ? 'Saving…' : intSaved ? '✓ Saved' : 'Save webhook settings' }}</button>
      </div>
    </div>
    </div><!-- end gate-wrap -->

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
import { ref, computed, watch, onMounted } from 'vue'
import { useAdminApi, WIDGET_URL } from '../composables/useAdminApi'
import { generateEmbedCode } from './embedCodeGenerator'
import { useToast } from '../composables/useToast'

const props = defineProps({ client: Object })
const emit = defineEmits(['client-updated'])
const api = useAdminApi()
const toast = useToast()

const activeTab = ref('channels')
const embedFormat = ref('html')
const copied = ref(false)
const saving = ref(false)
const saved = ref(false)
const scraping = ref(false)
const scrapePages = ref(0)
let scrapeTimer = null

// Feature flags (gating)
const features = ref({})
onMounted(async () => {
  try {
    const data = await api.getFeatureFlags()
    features.value = data || {}
  } catch {}
})

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
  telegram_bot_token: '',
  telegram_enabled: false,
  slack_webhook_url: '',
  outbound_webhook_url: '',
  outbound_webhook_events: 'hot_lead,lead_captured,new_session',
})

const aiProviders = [
  { val: 'openrouter', label: 'OpenRouter' },
  { val: 'openai', label: 'OpenAI' },
  { val: 'anthropic', label: 'Anthropic' },
]

// ── OpenRouter model picker ───────────────────────────────────────────────────
const modelPickerOpen = ref(false)
const modelPickerModels = ref([])
const modelPickerLoading = ref(false)
const modelPickerSearch = ref('')

const modelPickerFiltered = computed(() => {
  const q = modelPickerSearch.value.toLowerCase()
  return q
    ? modelPickerModels.value.filter(m => m.id.toLowerCase().includes(q) || (m.name || '').toLowerCase().includes(q))
    : modelPickerModels.value
})

async function openModelPicker() {
  modelPickerOpen.value = true
  if (modelPickerModels.value.length) return
  modelPickerLoading.value = true
  try {
    const data = await api.getOpenRouterModels()
    modelPickerModels.value = data?.models || []
  } catch (e) {
    toast.error('Failed to load models: ' + e.message)
  } finally {
    modelPickerLoading.value = false
  }
}

function selectPickerModel(model) {
  intForm.value.ai_model = model.id
  modelPickerOpen.value = false
}

const whatsappWebhookUrl = computed(() =>
  props.client ? `${backendUrl}/api/chat/webhooks/whatsapp/${props.client.id}/` : ''
)
const messengerWebhookUrl = computed(() =>
  props.client ? `${backendUrl}/api/chat/webhooks/messenger/${props.client.id}/` : ''
)
const telegramWebhookUrl = computed(() =>
  props.client ? `${backendUrl}/api/chat/webhooks/telegram/${props.client.id}/` : ''
)

const form = ref({
  chatbot_name: '',
  chatbot_color: '#6366F1',
  chatbot_theme: 'dark',
  notification_email: '',
  cta_mode: 'ai',
  cta_message: '',
  domain_url: '',
  voice_input_enabled: false,
  image_input_enabled: false,
})

const presetColors = ['#ffffff', '#3B82F6', '#22c55e', '#ef4444', '#6366f1', '#f59e0b']

const formats = [
  { id: 'html',      label: 'HTML',      icon: '<span style="font-weight:700;font-size:11px;letter-spacing:-0.5px;font-family:monospace">&lt;/&gt;</span>' },
  { id: 'wordpress', label: 'WordPress', icon: '<span style="color:#21759b;font-weight:700;font-size:11px">WP</span>' },
  { id: 'react',     label: 'React',     icon: '<span style="font-size:14px;line-height:1">⚛</span>' },
]

const embedCode = computed(() => {
  if (!props.client) return ''
  return generateEmbedCode(
    props.client.id,
    WIDGET_URL,  // full URL incl. /widget/widget.js — NOT backendUrl (host only)
    form.value.chatbot_color || '#6366f1',
    form.value.chatbot_name || 'AI Assistant',
    embedFormat.value,
  )
})


// ── CTA AI suggestions ────────────────────────────────────────────────────────
const ctaSuggesting = ref(false)
const ctaSuggestions = ref([])
const ctaSuggestError = ref('')

async function suggestCtaFromBehavior() {
  if (!props.client || ctaSuggesting.value) return
  ctaSuggesting.value = true
  ctaSuggestError.value = ''
  ctaSuggestions.value = []
  try {
    const data = await api.suggestCta(props.client.id)
    ctaSuggestions.value = data?.suggestions || []
    if (!ctaSuggestions.value.length) {
      ctaSuggestError.value = 'No suggestions returned. Try again later.'
    }
  } catch (e) {
    ctaSuggestError.value = 'Failed to generate suggestions: ' + (e.message || 'unknown error')
  } finally {
    ctaSuggesting.value = false
  }
}

// Sync form with client prop
watch(() => props.client, (c) => {
  if (!c) return
  form.value.chatbot_name = c.chatbot_name || ''
  form.value.chatbot_color = c.chatbot_color || '#6366F1'
  form.value.chatbot_theme = c.chatbot_theme || 'dark'
  form.value.notification_email = c.notification_email || ''
  form.value.cta_mode = c.cta_mode || 'ai'
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
  intForm.value.telegram_bot_token = c.telegram_bot_token || ''
  intForm.value.telegram_enabled = c.telegram_enabled || false
  intForm.value.slack_webhook_url = c.slack_webhook_url || ''
  intForm.value.outbound_webhook_url = c.outbound_webhook_url || ''
  intForm.value.outbound_webhook_events = c.outbound_webhook_events || 'hot_lead,lead_captured,new_session'
  cannedResponses.value = (c.canned_responses || []).map(cr => ({ ...cr }))
}, { immediate: true })

// ── Canned responses ─────────────────────────────────────────────────────────
const cannedResponses = ref([])
const cannedSaving = ref(false)
const cannedSaved = ref(false)

function addCanned() {
  cannedResponses.value.push({ id: crypto.randomUUID(), title: '', body: '' })
}
function removeCanned(idx) {
  cannedResponses.value.splice(idx, 1)
}
async function saveCanned() {
  if (!props.client) return
  cannedSaving.value = true
  try {
    const updated = await api.updatePortalClient(props.client.id, { canned_responses: cannedResponses.value })
    emit('client-updated', updated)
    cannedSaved.value = true
    setTimeout(() => { cannedSaved.value = false }, 3000)
  } catch {} finally {
    cannedSaving.value = false
  }
}

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

// ── Real-time sync (webhooks) ─────────────────────────────────────────────
// Powers the "Real-time sync" panel under Knowledge: setup wizards per
// CMS, secret reveal/rotate, and the 50-event audit log so tenants can
// SEE webhooks landing instead of guessing whether they wired it up right.
const webhookPlatform = ref('wordpress')
const webhookLoading = ref(false)
const rotating = ref(false)
const secretRevealed = ref(false)
const copiedKey = ref('')
const webhook = ref({
  webhook_secret: '',
  webhook_urls: { shopify: '', woocommerce: '', wordpress: '' },
  events: [],
  counts_24h: { queued: 0, done: 0, failed: 0 },
})

const webhookPlatforms = [
  { id: 'wordpress',   label: 'WordPress',   icon: '<span style="color:#21759B;font-weight:700;font-size:11px">WP</span>' },
  { id: 'woocommerce', label: 'WooCommerce', icon: '<span style="color:#7F54B3;font-weight:700;font-size:11px">WC</span>' },
  { id: 'shopify',     label: 'Shopify',     icon: '<span style="color:#95BF47;font-weight:700;font-size:11px">SH</span>' },
  { id: 'custom',      label: 'Custom site', icon: '<span style="font-weight:700;font-size:11px">⚙️</span>' },
]

const maskedSecret = computed(() => {
  const s = webhook.value.webhook_secret || ''
  if (s.length < 12) return s
  return s.slice(0, 4) + '••••••••••••' + s.slice(-4)
})

async function loadWebhookData() {
  if (!props.client) return
  webhookLoading.value = true
  try {
    const data = await api.getWebhookEvents(props.client.id)
    if (data) webhook.value = data
  } catch {} finally { webhookLoading.value = false }
}

async function rotateSecret() {
  if (!props.client) return
  // Generating-for-the-first-time doesn't need a confirm, but rotating an
  // existing secret breaks any CMS that's already pointed at the old one.
  if (webhook.value.webhook_secret && !confirm(
    'Rotating the secret invalidates the current one immediately. Make sure you can update your CMS right after. Continue?'
  )) return
  rotating.value = true
  try {
    const data = await api.rotateWebhookSecret(props.client.id)
    if (data?.webhook_secret) {
      webhook.value.webhook_secret = data.webhook_secret
      secretRevealed.value = true  // surface the new value so tenant can copy it
      try { toast.success('New secret generated — paste it into your CMS.') } catch {}
    }
  } catch {
    try { toast.error('Could not rotate secret. Try again.') } catch {}
  } finally { rotating.value = false }
}

async function copyText(text, key) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    copiedKey.value = key
    setTimeout(() => { if (copiedKey.value === key) copiedKey.value = '' }, 1500)
  } catch {}
}

function formatRelativeTime(iso) {
  if (!iso) return ''
  try {
    const diff = Date.now() - new Date(iso).getTime()
    const s = Math.floor(diff / 1000)
    if (s < 60)    return `${s}s ago`
    const m = Math.floor(s / 60)
    if (m < 60)    return `${m}m ago`
    const h = Math.floor(m / 60)
    if (h < 24)    return `${h}h ago`
    const d = Math.floor(h / 24)
    return `${d}d ago`
  } catch { return '' }
}

// Refresh activity when the tenant flips to the Knowledge tab and on first mount
watch(activeTab, (tab) => { if (tab === 'knowledge') loadWebhookData() })
watch(() => props.client, (c) => { if (c) loadWebhookData() }, { immediate: true })
</script>

<style scoped>
* { box-sizing: border-box; }

.settings-page {
  padding: 32px 36px;
  max-width: 860px;
  font-family: 'Inter', -apple-system, sans-serif;
}

.page-header { margin-bottom: 24px; }
.page-title { font-size: 22px; font-weight: 700; color: var(--cf-text-primary); letter-spacing: -0.4px; }

/* Tabs */
.tabs {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid var(--cf-border-subtle);
  margin-bottom: 28px;
}

.tab {
  padding: 10px 18px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: 13px;
  font-weight: 500;
  color: var(--cf-text-muted);
  cursor: pointer;
  transition: all 0.15s;
  margin-bottom: -1px;
}
.tab:hover { color: var(--cf-text-secondary); }
.tab.active { color: #6366f1; border-bottom-color: #6366f1; }

.tab-content { display: flex; flex-direction: column; gap: 16px; }

/* Section cards */
.section-card {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
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

.section-title { font-size: 15px; font-weight: 600; color: var(--cf-text-primary); }
.section-sub { font-size: 12px; color: var(--cf-text-muted); margin-top: 3px; }

.status-badge {
  margin-left: auto;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
}
.status-badge.active { background: rgba(34,197,94,0.1); color: #22c55e; border: 1px solid rgba(34,197,94,0.2); }

/* Embed box — always dark (code/terminal aesthetic) */
.embed-box {
  background: #0f1117;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Force light text inside embed-box since its bg is always dark */
.embed-title { font-size: 14px; font-weight: 600; color: #e2e8f0; }

.format-tabs { display: flex; gap: 6px; }
.format-tab {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 14px;
  background: var(--cf-bg-surface);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--cf-text-muted);
  cursor: pointer;
  transition: all 0.12s;
}
.format-tab:hover { background: var(--cf-bg-surface-hover); color: var(--cf-text-secondary); }
.format-tab.active { background: rgba(99,102,241,0.12); border-color: rgba(99,102,241,0.3); color: #a5b4fc; }
.format-icon { display: flex; align-items: center; }

.embed-instruction { font-size: 12px; color: #94a3b8; }
.embed-instruction code { background: rgba(255,255,255,0.08); padding: 1px 5px; border-radius: 4px; font-family: monospace; color: #a5b4fc; }

/* Format tabs inside embed-box always on dark bg — force dark-mode palette */
.embed-box .format-tab {
  background: rgba(255,255,255,0.05);
  border-color: rgba(255,255,255,0.1);
  color: #64748b;
}
.embed-box .format-tab:hover { background: rgba(255,255,255,0.09); color: #94a3b8; }
.embed-box .format-tab.active { background: rgba(99,102,241,0.15); border-color: rgba(99,102,241,0.3); color: #a5b4fc; }

.code-block {
  background: rgba(0,0,0,0.35);
  border: 1px solid rgba(255,255,255,0.07);
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
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.15s;
}
.copy-btn:hover { background: rgba(255,255,255,0.12); color: #e2e8f0; }
.copy-btn.copied { color: #22c55e; border-color: rgba(34,197,94,0.3); background: rgba(34,197,94,0.08); }

.skeleton { min-height: 120px; }
.skeleton-line { height: 12px; background: var(--cf-bg-input); border-radius: 4px; margin-bottom: 10px; }
.skeleton-line.short { width: 60%; }

/* Channels list */
.channels-list { display: flex; flex-direction: column; gap: 10px; }

.channel-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 12px;
}

.channel-meta { flex: 1; display: flex; align-items: center; gap: 10px; }
.channel-name { font-size: 14px; font-weight: 500; color: var(--cf-text-secondary); }
.channel-status { font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 4px; }
.channel-status.off { background: var(--cf-bg-input); color: var(--cf-text-muted); }

.btn-configure {
  padding: 6px 14px;
  background: var(--cf-bg-surface);
  border: 1px solid var(--cf-border-default);
  border-radius: 7px;
  font-size: 12px;
  font-weight: 500;
  color: var(--cf-text-muted);
  cursor: not-allowed;
}

/* Form fields */
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

.field { display: flex; flex-direction: column; gap: 7px; }
.field label { font-size: 12px; font-weight: 600; color: var(--cf-text-muted); text-transform: uppercase; letter-spacing: 0.06em; }

.input {
  padding: 10px 13px;
  background: var(--cf-bg-input);
  border: 1px solid var(--cf-border-default);
  border-radius: 9px;
  font-size: 14px;
  color: var(--cf-text-primary);
  outline: none;
  transition: border-color 0.15s, background 0.15s;
  width: 100%;
}
.input:focus { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.12); }
.input::placeholder { color: var(--cf-text-muted); }

/* Theme */
.theme-row { display: flex; gap: 10px; }
.theme-btn {
  display: flex; align-items: center; gap: 8px;
  padding: 9px 18px;
  background: var(--cf-bg-input);
  border: 1.5px solid var(--cf-border-default);
  border-radius: 9px;
  font-size: 13px; font-weight: 500; color: var(--cf-text-muted);
  cursor: pointer; transition: all 0.12s;
}
.theme-btn:hover { border-color: var(--cf-border-strong); color: var(--cf-text-secondary); }
.theme-btn.selected { border-color: #6366f1; color: #6366f1; background: rgba(99,102,241,0.08); }
.theme-dot { width: 12px; height: 12px; border-radius: 50%; }
.dark-dot { background: var(--cf-bg-page); border: 1px solid #334155; }
.light-dot { background: var(--cf-bg-surface); border: 1px solid #cbd5e1; }

/* Colors */
.color-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.color-swatch { width: 26px; height: 26px; border-radius: 50%; border: 2px solid transparent; cursor: pointer; transition: all 0.12s; outline: 2px solid transparent; }
.color-swatch.selected { outline: 2px solid #6366f1; outline-offset: 2px; }
.color-custom { display: flex; align-items: center; gap: 7px; }
.color-picker { width: 26px; height: 26px; border: none; border-radius: 50%; cursor: pointer; padding: 0; background: none; }
.color-hex { font-size: 11px; color: var(--cf-text-muted); font-family: monospace; }

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
.status-pending { color: var(--cf-text-muted); }

.pages-count { font-size: 12px; color: var(--cf-text-muted); }

.progress-wrap { display: flex; flex-direction: column; gap: 6px; }
.progress-bar { height: 4px; background: var(--cf-border-subtle); border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: #6366f1; border-radius: 2px; transition: width 0.5s; }
.progress-text { font-size: 12px; color: var(--cf-text-muted); }

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
  border-bottom: 1px solid var(--cf-border-subtle);
}
.feature-row:last-child { border-bottom: none; padding-bottom: 0; }
.feature-info { display: flex; flex-direction: column; gap: 3px; }
.feature-name { font-size: 14px; font-weight: 500; color: var(--cf-text-primary); }
.feature-desc { font-size: 12px; color: var(--cf-text-muted); }

.toggle { position: relative; display: inline-block; width: 44px; height: 24px; flex-shrink: 0; cursor: pointer; }
.toggle input { opacity: 0; width: 0; height: 0; }
.toggle-slider {
  position: absolute; inset: 0;
  background: var(--cf-bg-ghost-hover);
  border: 1px solid var(--cf-border-default);
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
.status-badge.inactive { background: rgba(71,85,105,0.2); color: var(--cf-text-muted); border: 1px solid rgba(71,85,105,0.3); }
.field-hint { font-size: 11px; color: var(--cf-text-muted); line-height: 1.5; }
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
  background: var(--cf-bg-ghost-hover);
  border: 1px solid var(--cf-border-default);
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
.toggle-lbl { font-size: 13px; color: var(--cf-text-muted); }
/* Canned responses */
.canned-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 12px; }
.canned-row { display: flex; gap: 10px; align-items: flex-start; }
.canned-fields { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.canned-body { resize: vertical; min-height: 56px; font-family: inherit; }
.canned-del { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.25); color: #fca5a5; border-radius: 7px; width: 32px; height: 32px; cursor: pointer; flex-shrink: 0; font-size: 13px; margin-top: 4px; }
.canned-del:hover { background: rgba(239,68,68,0.2); }
.btn-add-canned { background: rgba(99,102,241,0.08); border: 1px dashed rgba(99,102,241,0.3); color: #818cf8; border-radius: 9px; padding: 8px 16px; font-size: 13px; cursor: pointer; }
.btn-add-canned:hover { background: rgba(99,102,241,0.15); }
/* Toggle label in form */
.toggle-field { display: flex; align-items: center; }
.toggle-label { display: flex; align-items: center; gap: 10px; cursor: pointer; font-size: 13px; color: var(--cf-text-secondary); }
.toggle-input { position: absolute; opacity: 0; width: 0; height: 0; }

/* Feature gate overlay */
.gate-wrap { position: relative; }
.gate-overlay {
  position: absolute; inset: 0; z-index: 10;
  background: rgba(10,10,10,0.82);
  backdrop-filter: blur(3px);
  border-radius: 14px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 10px; padding: 24px; text-align: center;
}
.gate-lock { font-size: 28px; line-height: 1; }
.gate-msg { font-size: 13px; color: var(--cf-text-primary); line-height: 1.6; max-width: 280px; }
.gate-msg strong { color: #a5b4fc; }
.gate-upgrade-btn {
  display: inline-block; background: #6366f1; color: white;
  padding: 8px 18px; border-radius: 8px; font-size: 13px; font-weight: 600;
  text-decoration: none; transition: background 0.15s; margin-top: 4px;
}
.gate-upgrade-btn:hover { background: #4f46e5; }

@media (max-width: 768px) {
  .page-header { flex-direction: column; gap: 12px; align-items: flex-start; }
  .form-grid { grid-template-columns: 1fr !important; }
}

/* ── Model picker ─────────────────────────────────────────────────────── */
.model-input-row { display: flex; gap: 8px; align-items: center; }
.model-input-row .input { flex: 1; }
.btn-browse-models {
  flex-shrink: 0; padding: 0 14px; height: 40px; border-radius: 8px;
  background: rgba(99,102,241,0.15); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.3);
  font-size: 13px; font-weight: 500; cursor: pointer; white-space: nowrap;
  transition: background 0.15s;
}
.btn-browse-models:hover { background: rgba(99,102,241,0.25); }

.model-picker-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.65);
  z-index: 99997; display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(4px);
}
.model-picker-box {
  background: var(--cf-bg-surface-raised); border: 1px solid var(--cf-border-default);
  border-radius: 14px; width: 520px; max-width: calc(100vw - 32px);
  max-height: 80vh; display: flex; flex-direction: column;
  box-shadow: 0 24px 64px rgba(0,0,0,0.5);
}
.model-picker-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px; border-bottom: 1px solid var(--cf-border-subtle);
  font-size: 15px; font-weight: 600; color: var(--cf-text-primary);
}
.model-picker-close {
  background: none; border: none; color: var(--cf-text-muted); font-size: 16px;
  cursor: pointer; padding: 4px 8px; border-radius: 6px;
}
.model-picker-close:hover { color: var(--cf-text-primary); background: var(--cf-bg-ghost); }
.model-picker-search {
  margin: 12px 16px; padding: 10px 14px; border-radius: 8px;
  background: var(--cf-bg-surface); border: 1px solid var(--cf-border-default);
  color: var(--cf-text-primary); font-size: 14px; outline: none;
}
.model-picker-search:focus { border-color: #6366f1; }
.model-picker-list { flex: 1; overflow-y: auto; padding: 0 8px 12px; }
.model-picker-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 12px; border-radius: 8px; cursor: pointer;
  transition: background 0.12s;
}
.model-picker-row:hover { background: var(--cf-bg-input); }
.model-picker-active { background: rgba(99,102,241,0.12) !important; }
.mp-id { font-size: 13px; color: var(--cf-text-primary); font-family: monospace; word-break: break-all; }
.mp-meta { display: flex; gap: 6px; align-items: center; flex-shrink: 0; margin-left: 8px; }
.mp-free { font-size: 10px; font-weight: 700; background: rgba(34,197,94,0.15); color: #86efac; padding: 2px 6px; border-radius: 4px; }
.mp-paid { font-size: 10px; font-weight: 700; background: rgba(99,102,241,0.15); color: #a5b4fc; padding: 2px 6px; border-radius: 4px; }
.mp-ctx  { font-size: 11px; color: var(--cf-text-muted); }
.mp-empty, .mp-loading { padding: 24px; text-align: center; color: var(--cf-text-muted); font-size: 14px; }

.live-update-banner {
  background: linear-gradient(135deg, rgba(99,102,241,0.12), rgba(34,197,94,0.10));
  border: 1px solid rgba(99,102,241,0.30);
  color: #c7d2fe;
  font-size: 12px;
  padding: 9px 13px;
  border-radius: 8px;
  margin: 0 0 14px 0;
  line-height: 1.5;
}
.live-update-banner strong { color: #e0e7ff; font-weight: 700; }

/* ── CTA AI suggestions ──────────────────────────────────────────────────── */
.suggest-cta-btn {
  margin-left: 8px;
  background: linear-gradient(135deg, rgba(99,102,241,0.18), rgba(168,85,247,0.18));
  border: 1px solid rgba(99,102,241,0.35);
  color: #a5b4fc;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: background 0.15s, transform 0.1s;
  text-transform: none;
  letter-spacing: 0;
}
.suggest-cta-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(99,102,241,0.30), rgba(168,85,247,0.30));
  color: #c7d2fe;
}
.suggest-cta-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.cta-suggestions {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cta-suggestions-hint {
  font-size: 11px;
  color: var(--cf-text-muted);
  margin: 0 0 2px 0;
}
.cta-suggestion-pill {
  text-align: left;
  background: var(--cf-bg-input);
  border: 1px solid var(--cf-border-subtle);
  color: var(--cf-text-secondary);
  font-size: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  font-family: inherit;
  line-height: 1.5;
}
.cta-suggestion-pill:hover {
  background: var(--cf-bg-ghost-hover);
  border-color: rgba(99,102,241,0.4);
  color: var(--cf-text-primary);
}
.cta-error {
  margin-top: 6px;
  font-size: 12px;
  color: #f87171;
}

/* CTA mode picker — three radio cards stacked on mobile, 3-up on desktop.
   Visible radio button + title + description, with active state borrowing
   the brand accent like the theme picker above. */
.cta-mode-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 8px;
}
.cta-mode-opt {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  background: var(--cf-bg-input);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.cta-mode-opt:hover { background: var(--cf-bg-ghost-hover); border-color: var(--cf-border-default); }
.cta-mode-opt.active {
  background: rgba(99,102,241,0.10);
  border-color: rgba(99,102,241,0.55);
}
.cta-mode-opt input[type="radio"] { margin-top: 2px; accent-color: #6366f1; }
.cta-mode-body { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.cta-mode-title { font-size: 13px; font-weight: 600; color: var(--cf-text-primary); }
.cta-mode-desc  { font-size: 11.5px; color: var(--cf-text-muted); line-height: 1.4; }

@media (max-width: 720px) {
  .cta-mode-row { grid-template-columns: 1fr; }
}

/* ── Real-time sync panel ────────────────────────────────────────────── */
.wh-counters {
  display: flex; align-items: center; gap: 10px; margin: 16px 0 20px;
}
.wh-counter {
  flex: 1; display: flex; flex-direction: column; gap: 2px;
  padding: 10px 14px; border-radius: 10px;
  background: var(--cf-bg-input); border: 1px solid var(--cf-border-subtle);
}
.wh-counter-num   { font-size: 18px; font-weight: 700; letter-spacing: -0.3px; }
.wh-counter-label { font-size: 11px; color: var(--cf-text-muted); }
.wh-counter-done   .wh-counter-num { color: #4ade80; }
.wh-counter-queued .wh-counter-num { color: #a5b4fc; }
.wh-counter-failed .wh-counter-num { color: #f87171; }
.wh-refresh {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--cf-bg-input); border: 1px solid var(--cf-border-default);
  color: var(--cf-text-secondary); border-radius: 8px;
  padding: 8px 12px; font-size: 12px; font-weight: 500; cursor: pointer;
  font-family: inherit; transition: background 0.15s;
}
.wh-refresh:hover:not(:disabled) { background: var(--cf-bg-ghost-hover); color: var(--cf-text-primary); }
.wh-refresh:disabled { opacity: 0.5; cursor: not-allowed; }

.wh-platform-tabs {
  display: flex; gap: 6px; margin-bottom: 14px; flex-wrap: wrap;
}
.wh-platform-tab {
  display: inline-flex; align-items: center; gap: 7px;
  background: var(--cf-bg-input); border: 1px solid var(--cf-border-default);
  color: var(--cf-text-secondary); border-radius: 8px;
  padding: 8px 14px; font-size: 13px; font-weight: 500;
  cursor: pointer; font-family: inherit; transition: all 0.15s;
}
.wh-platform-tab:hover { color: var(--cf-text-primary); border-color: var(--cf-border-strong); }
.wh-platform-tab.active {
  background: rgba(99,102,241,0.12); border-color: rgba(99,102,241,0.4);
  color: #a5b4fc;
}
.wh-platform-icon { display: inline-flex; align-items: center; }

.wh-setup-card {
  background: var(--cf-bg-input); border: 1px solid var(--cf-border-subtle);
  border-radius: 12px; padding: 16px; margin-bottom: 14px;
}
.wh-setup-title { font-size: 14px; font-weight: 600; color: var(--cf-text-primary); margin-bottom: 10px; }
.wh-steps {
  margin: 0 0 14px 0; padding-left: 22px;
  display: flex; flex-direction: column; gap: 6px;
}
.wh-steps li { font-size: 13px; color: var(--cf-text-secondary); line-height: 1.55; }
.wh-steps li strong { color: var(--cf-text-primary); }
.wh-steps li em { color: #a5b4fc; font-style: normal; }

.wh-custom-note { font-size: 13px; color: var(--cf-text-secondary); line-height: 1.6; }

.wh-paste-row {
  display: flex; align-items: center; gap: 8px;
  background: var(--cf-bg-page); border: 1px solid var(--cf-border-subtle);
  border-radius: 8px; padding: 8px 10px; margin-bottom: 8px;
}
.wh-paste-label {
  font-size: 11px; font-weight: 700; color: var(--cf-text-muted);
  text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap;
}
.wh-paste-code {
  flex: 1; font-family: 'Fira Mono', 'JetBrains Mono', monospace;
  font-size: 12px; color: #a5b4fc; word-break: break-all;
}
.wh-secret-code { color: var(--cf-text-primary); }
.wh-copy, .wh-rotate {
  background: var(--cf-bg-ghost-hover); border: 1px solid var(--cf-border-default);
  color: var(--cf-text-primary); border-radius: 6px;
  padding: 4px 10px; font-size: 11.5px; font-weight: 500;
  cursor: pointer; font-family: inherit; transition: background 0.15s;
  white-space: nowrap;
}
.wh-copy:hover:not(:disabled) { background: var(--cf-border-default); }
.wh-copy:disabled { opacity: 0.4; cursor: not-allowed; }
.wh-rotate {
  background: rgba(239,68,68,0.10); border-color: rgba(239,68,68,0.30); color: #fca5a5;
}
.wh-rotate:hover:not(:disabled) { background: rgba(239,68,68,0.18); }

.wh-secret-row {
  display: flex; align-items: center; gap: 8px;
  background: var(--cf-bg-page); border: 1px solid var(--cf-border-subtle);
  border-radius: 8px; padding: 8px 10px; margin-top: 4px;
}
.wh-secret-help {
  font-size: 11.5px; color: var(--cf-text-muted); line-height: 1.5;
  margin-top: 8px; margin-bottom: 20px;
}

.wh-activity { border-top: 1px solid var(--cf-border-subtle); padding-top: 16px; }
.wh-activity-title {
  font-size: 11px; font-weight: 700; color: var(--cf-text-muted);
  text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 10px;
}
.wh-empty {
  background: var(--cf-bg-input); border: 1px dashed var(--cf-border-default);
  border-radius: 8px; padding: 16px; text-align: center;
  font-size: 12.5px; color: var(--cf-text-muted); line-height: 1.5;
}
.wh-events-list { display: flex; flex-direction: column; gap: 4px; }
.wh-event {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; background: var(--cf-bg-input);
  border: 1px solid var(--cf-border-subtle); border-radius: 7px;
  font-size: 12.5px;
}
.wh-event-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.wh-event-done   .wh-event-dot { background: #4ade80; }
.wh-event-queued .wh-event-dot { background: #a5b4fc; animation: wh-pulse 1.2s infinite ease-in-out; }
.wh-event-failed .wh-event-dot { background: #f87171; }
@keyframes wh-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
.wh-event-source {
  font-size: 10.5px; font-weight: 700; color: var(--cf-text-muted);
  text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap;
}
.wh-event-title {
  flex: 1; min-width: 0; color: var(--cf-text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.wh-event-time { color: var(--cf-text-muted); font-size: 11.5px; white-space: nowrap; }
.wh-event-dur  { color: var(--cf-text-muted); font-size: 11px; font-family: monospace; }

@media (max-width: 768px) {
  .wh-counters { flex-wrap: wrap; }
  .wh-counter  { min-width: calc(33.33% - 8px); }
  .wh-refresh  { width: 100%; justify-content: center; }
  .wh-paste-row, .wh-secret-row { flex-wrap: wrap; }
  .wh-paste-code { width: 100%; }
}
</style>
