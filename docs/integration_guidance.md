# Integration Guidance — Landing Page Content

Ready-to-publish copy and structure for the **Integrations** section of the public
checkfunnels.com landing page. Each integration has:

- Logo / icon name
- One-line tagline
- 2-3 sentence description
- Best-for use case
- Step-by-step setup (3-5 steps)
- Screenshot placeholders
- Demo video URL placeholder

The same content powers the in-app `/portal/integrations` page so tenants
have a single source of truth for setup help.

---

## Website Chat Widget

**Icon:** `globe` or browser icon
**Tagline:** Drop one snippet of code on your site, get a sales-trained AI in 60 seconds.
**Description:** The default channel. Embeds as a floating widget on any page of
your website. Auto-opens with behavior-aware questions, captures leads,
escalates to your team when needed.

**Best for:** E-commerce stores, service businesses, SaaS landing pages —
basically any website that wants more conversions.

**Setup steps:**
1. Sign up at `app.checkfunnels.com` and complete onboarding
2. Go to `/portal/settings` → **Channels & Embed** tab
3. Choose your embed format (HTML / WordPress / React)
4. Copy the snippet and paste it before `</body>` on your site
5. Refresh — the widget appears in the bottom-right corner

**Screenshots:** `widget_floating.png`, `widget_open.png`, `widget_chat.png`
**Demo video:** `demo_website_widget.mp4` (30-45 seconds)

---

## WhatsApp Business

**Icon:** WhatsApp logo (green speech bubble)
**Tagline:** Sell on the world's most popular messaging app — same AI, native channel.
**Description:** Connect your WhatsApp Business number so the AI handles
inquiries 24/7. Conversations sync to the same inbox as website chats.
Hot leads escalate to your team in real time.

**Best for:** Direct-to-consumer brands in LATAM, Africa, India, MENA where
WhatsApp is the default shopping channel. Service businesses that handle
appointments via WhatsApp.

**Setup steps:**
1. Have a Meta Business account + verified WhatsApp Business phone number
2. In `/portal/settings` → **WhatsApp Business**, paste your phone number ID
3. Paste your access token and verify token from the Meta Developer dashboard
4. Copy the webhook URL we show you into your Meta webhook config
5. Toggle "Enable WhatsApp channel" and save — verified within ~30 seconds

**Screenshots:** `whatsapp_settings_panel.png`, `whatsapp_webhook_setup.png`,
`whatsapp_conversation.png`
**Demo video:** `demo_whatsapp.mp4` (60 seconds — covers Meta setup + first message)
**Plan requirement:** Growth or higher

---

## Telegram Bot

**Icon:** Telegram paper-plane logo
**Tagline:** Spin up a Telegram bot for your customers in under 2 minutes — webhook auto-registered.
**Description:** Create a bot via @BotFather, paste the token, hit save.
We handle webhook registration with Telegram's API automatically (no
copy/paste URLs). Bot status is reported live in the dashboard.

**Best for:** Communities and audiences that already prefer Telegram (crypto,
Eastern European markets, niche tech). Niche e-commerce that wants a
dedicated bot identity.

**Setup steps:**
1. On Telegram, message `@BotFather` and run `/newbot` to create your bot
2. Copy the token BotFather gives you
3. In `/portal/settings` → **Telegram Bot**, paste the token
4. Toggle "Enable Telegram channel" and save
5. Status card appears below: "Webhook active" — send a test message to your bot

**Screenshots:** `telegram_botfather.png`, `telegram_settings.png`,
`telegram_webhook_status.png`
**Demo video:** `demo_telegram.mp4` (45 seconds)
**Plan requirement:** Growth or higher

---

## Facebook Messenger

**Icon:** Messenger circle logo
**Tagline:** Convert your Facebook page DMs without hiring a 24/7 support team.
**Description:** Connect your Facebook Page so Messenger DMs route to the AI.
Same sales-trained behavior as the website widget — qualifies leads,
captures contact info, escalates when needed.

**Best for:** Brands with established Facebook page audiences who can't keep up
with DMs manually. Lead-gen businesses (real estate, education, services)
where Facebook ads drive DM volume.

**Setup steps:**
1. In Meta Developer Portal, create or open your Messenger app
2. In `/portal/settings` → **Facebook Messenger**, paste your Page ID + access token
3. Set your verify token (any string — copy the same one to Meta's webhook config)
4. Use the webhook URL we show you in Meta's Messenger webhook subscription
5. Toggle "Enable Messenger" and save

**Screenshots:** `messenger_meta_setup.png`, `messenger_settings.png`
**Demo video:** `demo_messenger.mp4` (60 seconds)
**Plan requirement:** Growth or higher

---

## Shopify (Inventory + Webhooks)

**Icon:** Shopify shopping bag
**Tagline:** Auto-sync your product catalog and order data — the AI knows what's in stock.
**Description:** Real-time webhook integration pulls in product updates so the
AI's knowledge base stays fresh without re-scraping. Order data flows in
for post-purchase support flows.

**Best for:** Any Shopify store. Especially valuable for stores with frequent
catalog changes (fashion drops, seasonal SKUs) or large inventories.

**Setup steps:**
1. In your Shopify admin, go to **Settings → Notifications → Webhooks**
2. In `/portal/settings` → **Shopify Webhooks**, copy the webhook URL + secret we generate
3. In Shopify, add 2 webhooks: `products/update` and `orders/create`, both pointing at our URL
4. Paste the shared secret in Shopify so we can verify HMAC signatures
5. Your products appear in our knowledge base within 60 seconds of any update

**Screenshots:** `shopify_webhook_admin.png`, `shopify_secret_setup.png`
**Demo video:** `demo_shopify.mp4` (90 seconds)

---

## WordPress / WooCommerce

**Icon:** WordPress W logo
**Tagline:** One-click install via our plugin — automatic product + post sync.
**Description:** Native WordPress/WooCommerce plugin. Installs the chat widget,
sets up product update webhooks, and embeds in your existing theme. Zero
manual code editing.

**Best for:** WordPress-powered e-commerce stores (the largest share of the
e-commerce market). Content sites that want chat plus auto-content-sync.

**Setup steps:**
1. Download the Checkfunnel WordPress plugin from `/portal/settings → WordPress`
2. In WordPress admin: Plugins → Add New → Upload Plugin → Install + Activate
3. The plugin shows a "Connect to Checkfunnel" button — click it
4. Authorize the link from your Checkfunnel portal (one click)
5. Widget appears on all pages; products auto-sync to the knowledge base

**Screenshots:** `wp_plugin_install.png`, `wp_connect.png`
**Demo video:** `demo_wordpress.mp4` (60 seconds)

---

## HubSpot CRM

**Icon:** HubSpot sprocket
**Tagline:** Every captured lead lands in HubSpot — with full chat context attached.
**Description:** When the AI captures a lead's contact info, it's pushed to
HubSpot as a new contact with the conversation transcript as a note.
Sales teams pick up the conversation in HubSpot where they already work.

**Best for:** Sales-led B2B/B2C teams already using HubSpot. Service businesses
with longer sales cycles where reps follow up by phone/email after the
chat captures interest.

**Setup steps:**
1. In HubSpot, generate a Private App access token with Contacts + Notes write scope
2. In `/portal/settings` → **HubSpot CRM**, paste the token
3. Save — first captured lead syncs to HubSpot within 5 seconds

**Screenshots:** `hubspot_token.png`, `hubspot_contact_synced.png`
**Demo video:** `demo_hubspot.mp4` (45 seconds)
**Plan requirement:** Growth or higher

---

## Slack Notifications

**Icon:** Slack hashtag
**Tagline:** Get pinged the moment a hot lead is captured — never miss a deal.
**Description:** Sends a Slack message to your team channel whenever a HOT_LEAD
or CONVERTED session is detected. Includes the visitor's contact info,
heat score, and a link to the full conversation.

**Best for:** Small sales teams where one person needs to respond fast to
high-intent leads. Agencies managing multiple clients' chat funnels who
want a unified alert stream.

**Setup steps:**
1. In your Slack workspace, create an Incoming Webhook for the channel
   you want notifications in
2. Copy the webhook URL (looks like `https://hooks.slack.com/services/T.../B.../...`)
3. In `/portal/settings` → **Slack Notifications**, paste the URL
4. Save — first hot lead triggers a Slack post

**Screenshots:** `slack_webhook_create.png`, `slack_notification_example.png`
**Demo video:** `demo_slack.mp4` (30 seconds)
**Plan requirement:** Starter or higher

---

## Outbound Webhooks (Custom)

**Icon:** lightning bolt or arrow-out
**Tagline:** Pipe events to your own systems — bring your own automation.
**Description:** Configure a single webhook URL we POST to whenever specific
events fire: `hot_lead`, `lead_captured`, `new_session`, etc. JSON
payload with the visitor, session, and event details.

**Best for:** Power users who want to integrate with Zapier, n8n, Make,
custom CRMs, marketing automation tools, or their own dashboard.

**Setup steps:**
1. In `/portal/settings` → **Outbound Webhooks**, paste the destination URL
2. Choose which events fire (defaults: `hot_lead, lead_captured, new_session`)
3. Save — events POST with `Content-Type: application/json`
4. Use the included webhook secret to verify signatures (HMAC-SHA256)

**Screenshots:** `outbound_webhook_settings.png`
**Demo video:** `demo_webhooks.mp4` (90 seconds — Zapier example)

---

# Suggested Landing Page Layout

```
┌─────────────────────────────────────────────────────┐
│  Hero: "Connect once. Sell everywhere."             │
│  Sub: "9 integrations. Each takes <2 minutes."      │
├─────────────────────────────────────────────────────┤
│                                                      │
│  [Tabs: Channels | E-commerce | CRM | Custom]       │
│                                                      │
├─────────────────────────────────────────────────────┤
│  Grid of integration cards (3 per row on desktop):  │
│                                                      │
│  ┌──────┐  ┌──────┐  ┌──────┐                       │
│  │ Logo │  │ Logo │  │ Logo │                       │
│  │ Name │  │ Name │  │ Name │                       │
│  │ Tag  │  │ Tag  │  │ Tag  │                       │
│  │ ─→   │  │ ─→   │  │ ─→   │                       │
│  └──────┘  └──────┘  └──────┘                       │
│                                                      │
│  Click card → modal/dedicated page with:            │
│   - 2-3 sentence description                         │
│   - Best-for use case                                │
│   - Step-by-step setup with screenshots              │
│   - Embedded demo video                              │
│   - Direct "Sign up to enable this" CTA              │
└─────────────────────────────────────────────────────┘
```

# Screenshot Asset List (for marketing team to capture)

All screenshots should be taken against the **dark theme** at 1440×900
viewport with the actual production portal. Crop to relevant area + 8px
padding. PNG, no compression artifacts.

| Filename | What to capture |
|---|---|
| widget_floating.png | Widget pill in bottom-right corner on a demo product page |
| widget_open.png | Widget open with greeting + quick-reply chips |
| widget_chat.png | Mid-conversation showing AI reply + visitor reply |
| whatsapp_settings_panel.png | `/portal/settings → WhatsApp` with sample fields |
| whatsapp_webhook_setup.png | Meta Developer dashboard webhook page |
| whatsapp_conversation.png | WhatsApp app screenshot showing AI reply |
| telegram_botfather.png | @BotFather Telegram chat showing /newbot flow |
| telegram_settings.png | `/portal/settings → Telegram` with token field |
| telegram_webhook_status.png | Green "Webhook active" status card |
| messenger_meta_setup.png | Meta Developer Messenger app setup |
| messenger_settings.png | `/portal/settings → Messenger` |
| shopify_webhook_admin.png | Shopify Notifications/Webhooks page |
| shopify_secret_setup.png | `/portal/settings → Shopify Webhooks` |
| wp_plugin_install.png | WordPress admin plugin upload screen |
| wp_connect.png | "Connect to Checkfunnel" button on the plugin page |
| hubspot_token.png | HubSpot private apps token generation |
| hubspot_contact_synced.png | HubSpot contact with chat transcript note |
| slack_webhook_create.png | Slack webhook creation page |
| slack_notification_example.png | Slack message preview with hot-lead alert |
| outbound_webhook_settings.png | `/portal/settings → Outbound Webhooks` |

# Demo Video Asset List (for marketing team to record)

Each video should be **30-90 seconds**, no narration (text overlays only),
sped up where possible. Format: MP4, 1080p, max 8MB.

| File | Coverage |
|---|---|
| `demo_website_widget.mp4` | Snippet copy → paste → widget appears → first chat |
| `demo_whatsapp.mp4` | Meta dashboard setup → portal setup → WhatsApp test |
| `demo_telegram.mp4` | @BotFather → portal save → status active → test message |
| `demo_messenger.mp4` | Meta app config → portal setup → Facebook DM test |
| `demo_shopify.mp4` | Shopify webhook → portal copy URL → product update sync |
| `demo_wordpress.mp4` | Plugin upload → connect → widget appears |
| `demo_hubspot.mp4` | HubSpot token → portal paste → captured lead in HubSpot |
| `demo_slack.mp4` | Slack webhook → portal paste → hot lead notification |
| `demo_webhooks.mp4` | Zapier setup → portal webhook URL → event firing |

# Notes for the marketing team

1. **Each integration card on the landing page should link to a dedicated
   page** (e.g. `/integrations/whatsapp`) with the full setup steps,
   screenshots, and embedded video. Search engines love deep, focused
   integration pages.
2. **All "Sign up to enable" CTAs** should land on `/portal/signup?ref=int_<name>`
   so we can attribute conversion source.
3. **"Plan requirement" labels** need to be kept in sync with the actual
   plan features in the Plan model. If a tenant upgrades and gets access
   to a previously-locked integration, that's a measurable funnel event.
4. **The integrations page should be the #2 most-visited marketing page**
   after the homepage. Track scroll depth on each integration card to
   identify which integrations attract the most interest — useful signal
   for what to feature in ads.
