# GrowMiq — Page-Aware Triggers, Notification UX & Per-Page Controls (Implementation Plan)

**Status:** PLAN ONLY — not implemented. Awaiting sign-off on the open decisions in §11.
**Author:** engineering
**Scope:** Tenant-controlled, page-specific chatbot behavior on the customer storefront (Shopify/WooCommerce/custom).

---

## 1. What we're building (scope)

Five connected capabilities, all configured from the **tenant/client panel**:

1. **Page-specific greeting messages** — when a visitor lands on / navigates to a page, the bot surfaces a greeting matched to that page type (Home / Product / Cart / Checkout / Contact / etc.), per the URL→message mapping in the brief.
2. **Non-intrusive notification UX** — greetings appear as a **suggestion bubble above the closed launcher** (never force-open), auto-dismiss after 20s, with an **unread badge**, **read-&-clear on open**, and a **dismiss (X) "do-not-disturb"** rule (stop pop-ups, keep silent delivery + badge).
3. **Per-page behavior prompt** — for each high-level page discovered during scraping, the tenant can write *how the AI should act on that page* (injected into the live conversation, not just the greeting).
4. **Per-page visibility toggle** — show or hide the chat widget entirely on specific pages.
5. **Auto-close timer** — tenant sets an idle timeout after which the open chat window auto-collapses to the launcher.

All five are driven by tenant config delivered through `widget-config` (public) + the chat backend.

---

## 2. How it maps to what already exists (reuse, don't rebuild)

| Capability | Existing foundation | What's new |
|---|---|---|
| Page detection | Widget already reads `location.pathname`, tracks `page_visits`, classifies pricing/checkout paths (`embedCodeGenerator.js` behavior tracker) | A full URL→page-type router + tenant-editable rules |
| Greeting delivery | `trigger_event` persists a bot msg to `chat_history` + pushes over WS; widget renders bot bubbles | New `page_greeting` source that does **not** auto-open; bubble+badge UI |
| Config delivery | `widget_config` returns branding/CTA fields | Add intro text, proactive settings, auto-close, page rules |
| Per-page AI behavior | `ai_service.build_prompt` already injects dynamic blocks (order status, browsing context) | Inject a "PAGE CONTEXT" block from the matched rule |
| Discovered pages | Scraper stores every `source_url` in `DocumentChunk` | A deduped, classified **SitePage** list for the tenant to attach rules to |
| Session persistence | Widget persists `sid`/`vid`/messages across page loads (cookie + localStorage) | First-touch flag, unread set, DND flag |

---

## 3. Architecture overview

```
Storefront page load
   │
   ├─ widget boots → GET /api/chat/widget-config/<client>/   (now returns page_rules, intro, proactive + auto-close settings)
   │      │
   │      ├─ match current URL against page_rules (client-side, instant)
   │      ├─ rule.enabled_widget == false → DO NOT render widget at all (visibility toggle)
   │      └─ rule matched → request the greeting:
   │                 POST /api/chat/page-message/  { sid, client, page_url, page_type, product_name }
   │                        │  server: resolve text (literal | AI-rephrased), prepend intro on first touch,
   │                        │          persist to chat_history (source='page_greeting'), return {message, msg_id}
   │                        ▼
   │      widget shows SUGGESTION BUBBLE above launcher (20s timer) + increments UNREAD BADGE
   │
   ├─ visitor opens chat → badge clears, msg_ids marked seen (read & clear)
   ├─ visitor clicks X on bubble → sessionStorage DND=1 (no more bubbles; badge + inbox delivery continue)
   │
   └─ visitor sends a message → POST/WS includes page_url
              server: match rule → inject rule.behavior_prompt into the system prompt ("PAGE CONTEXT")
```

---

## 4. Data model

### 4.1 New model: `SitePage` (scraper app)
Populated/updated by the ingestion pipeline so tenants see a real list of their pages.

```python
class SitePage(models.Model):
    client       = FK(Client, related_name='site_pages')
    path         = CharField(max_length=1000)          # normalized URL path, e.g. /collections/hoodies
    url          = URLField(max_length=1000)           # full URL (last seen)
    title        = CharField(max_length=300, blank=True)
    page_type    = CharField(max_length=32, default='other')  # home|collection|product|cart|checkout|contact|about|faq|offers|track|other
    last_seen    = DateTimeField(auto_now=True)
    class Meta:
        unique_together = [('client', 'path')]
        indexes = [models.Index(fields=['client', 'page_type'])]
```

- Upserted during scrape/sync from `DocumentChunk.source_url` (dedupe by `(client, path)`), title from page metadata.
- `page_type` set by `classify_path()` (URL heuristics, §6.2).

### 4.2 New JSON field on `Client`: `page_rules`
Ordered list; seeded with the brief's defaults on first use. Each rule:

```jsonc
{
  "id": "uuid",
  "label": "Single Product",
  "match_type": "contains",         // contains | prefix | exact | regex
  "pattern": "/products/",
  "page_type": "product",           // canonical type (enables {product_name}, sale logic, etc.)
  "priority": 30,                    // higher wins when multiple match
  "enabled_widget": true,           // FALSE = hide chat on this page
  "greeting_enabled": true,         // FALSE = no proactive greeting here
  "greeting_message": "Interested in the {product_name}? I can help with details, pricing, sizing/color options, or suggest similar items.",
  "behavior_prompt": ""             // optional: how the AI should act on this page (in-chat)
}
```

### 4.3 New scalar fields on `Client`
```python
assistant_intro              = CharField(default="Hi! I'm your AI Shopping Assistant.")
proactive_notifications_enabled = Bool(default=True)
notification_timeout_seconds = Int(default=20)
proactive_mode               = CharField(default='literal')  # literal | ai | hybrid  (see §11.1)
auto_close_seconds           = Int(default=0)                 # 0 = never auto-close
```

### 4.4 New field on `ChatSession`
```python
greeting_intro_sent = Bool(default=False)   # first-touch intro prepend control
```

> Migration count: 1 (scraper SitePage) + 1 (users Client fields + page_rules) + 1 (chat ChatSession flag). All additive/nullable — safe.

---

## 5. Backend changes

### 5.1 `widget_config` (extend — `chat/views.py:185`)
Add to the response (public-safe — greetings + visibility, **no** behavior_prompt or secrets):
```python
'assistant_intro': client.assistant_intro,
'proactive_enabled': client.proactive_notifications_enabled and client.cta_mode != 'off',
'notification_timeout_seconds': client.notification_timeout_seconds,
'auto_close_seconds': client.auto_close_seconds,
'page_rules': [public_view(r) for r in (client.page_rules or [])],  # strips behavior_prompt
```
`public_view(rule)` returns id/label/match_type/pattern/page_type/priority/enabled_widget/greeting_enabled/greeting_message only.

### 5.2 New endpoint: `POST /api/chat/page-message/`
Public (AllowAny), throttled. Body: `{ session_id, client_id, page_url, page_type, product_name? }`.
- Resolve the matching rule server-side (re-match, don't trust client blindly) for the given `page_url`.
- Guards: skip if `takeover_active`, `cta_mode == 'off'`, `proactive_notifications_enabled == false`, or `greeting_enabled == false` for the rule.
- **De-dupe:** don't re-send the same page_type greeting within the session within a short window (cache key `pg_{sid}_{page_type}`, e.g. 10 min) — prevents spam when a visitor re-visits a page type.
- Build text:
  - `literal` mode → `greeting_message` with `{product_name}` interpolated.
  - `ai` mode → `_generate_personalised_cta`-style call seeded by the rule message (rephrase, keep meaning).
  - `hybrid` → literal for structural pages (cart/checkout/contact), AI for discovery pages (home/product/collection).
- **First touch:** if `not session.greeting_intro_sent` → prepend `assistant_intro + " "`; set flag.
- Persist to `chat_history` with `source='page_greeting'`, return `{ message, msg_id }`.
- Push over WS too (so an already-open chat shows it inline).

### 5.3 In-chat behavior prompt injection (`ai_service.build_prompt`)
- Ensure every visitor message carries `page_url` (widget already sends `page_url` in `proactive_trigger`; extend the normal `message` frame at `embedCodeGenerator.js:885` to include it).
- In `build_prompt`: match `page_url` → rule; if `rule.behavior_prompt`, inject:
  `PAGE CONTEXT: The visitor is on the "{label}" page. {behavior_prompt}` — appended after persona/state, same pattern as the order-status block.

### 5.4 Serializer + admin save (`users/serializers.py`, `admin_views.py`)
- Add `page_rules`, `assistant_intro`, `proactive_notifications_enabled`, `notification_timeout_seconds`, `proactive_mode`, `auto_close_seconds` to `ClientSerializer.fields` (tenant-writable).
- New read endpoint `GET /api/admin/clients/<id>/site-pages/` → SitePage list (tenant-scoped via `get_accessible_clients`) for the admin UI.
- A "seed default rules" action (button) that writes the brief's table into `page_rules` if empty.

---

## 6. Scraper changes

### 6.1 Upsert SitePage during ingestion
In the scrape/sync task, after fetching a page, upsert `SitePage(client, path=normalize(url), url, title, page_type=classify_path(path))`. Dedup by `(client, path)`. Keeps the tenant's page list fresh on every crawl/webhook.

### 6.2 `classify_path(path)` helper (shared, also used by backend matching)
URL heuristics covering Shopify/Woo conventions + the brief:
```
"/", "/home"                         → home
"/collections/", "/category", "/shop", "/product-category" → collection
"/products/", "/product/"            → product
"/cart"                              → cart
"/checkout"                          → checkout
"/contact"                           → contact
"/about"                             → about
"/faq", "/help"                      → faq
"/offers", "/pricing", "/deals", "/sale" → offers
"/track", "/order-tracking", "/orders/" → track
else                                 → other  (fallback message)
```
Used in three places: scraper classification, the `page-message` server re-match, and as defaults when seeding `page_rules`.

---

## 7. Widget changes (`embedCodeGenerator.js`)

> This is the biggest piece. The inline snippet is the live widget (not `ChatWidget.vue`).

### 7.1 Visibility gate (before render)
On boot, after `widget-config` loads: match `location.pathname` against `page_rules`; if the winning rule has `enabled_widget === false`, **abort widget injection** (no launcher, no WS, no triggers). Re-evaluate on SPA navigation (§7.6).

### 7.2 Suggestion bubble (repurpose `#cf-pill`)
- Extend the existing teaser pill into a **suggestion notification** above the launcher: message text + a small **X** button.
- Show it when a `page_greeting` arrives **and** chat is closed **and** DND is not set.
- **20s auto-dismiss** timer (`notification_timeout_seconds` from config); clearing the bubble does NOT clear the badge.
- Clicking the bubble body → open chat (counts as read).

### 7.3 Unread badge on launcher
- Add a numeric badge element on the launcher icon.
- Maintain an **unread set** in `localStorage` keyed by `sid` (survives navigation): add `msg_id` whenever a bot message is delivered while chat is closed.
- Badge count = size of unread set. Render 1/2/3… (cap at e.g. "9+").

### 7.4 Read & clear
- On chat open (`toggleOpen`, `embedCodeGenerator.js:906`): mark all unread `msg_id`s as seen, empty the unread set, hide badge. Those messages never re-count.

### 7.5 Dismiss (DND)
- X on the bubble → `sessionStorage['cf_dnd']=1`. While set: never show the bubble again this session; **still** persist/deliver greetings (server already does) and **still** increment the badge.

### 7.6 First-touch & navigation
- The server owns first-touch (intro prepend) via `greeting_intro_sent`. Widget just calls `page-message` on each qualifying page load.
- For SPA themes (history pushState/popstate): hook navigation to re-run match → visibility + greeting. For classic multi-page (full reloads), normal boot handles it.

### 7.7 `{product_name}` resolution (client-side)
On product pages, read the name from (in order): JSON-LD `Product.name` → `og:title` → `document.title` (trimmed). Send it to `page-message` so the server can interpolate. Fallback: drop the placeholder phrase gracefully if unknown.

### 7.8 Auto-close timer
- If `auto_close_seconds > 0`: when chat is open, start an idle timer; reset on visitor activity (typing/sending/scroll in window). On expiry, collapse to launcher. Disabled when 0.

### 7.9 Exclude `page_greeting` from auto-open
- Add `page_greeting` to a **non-auto-open** path (the current `AUTO_OPEN` list at `embedCodeGenerator.js:849` must NOT include it) so greetings never force the window open. (Decision §11.3: whether exit_intent etc. also move to bubble-only.)

---

## 8. Admin / tenant UI (PortalSettings — new "Proactive & Pages" tab)

**Global section**
- Toggle: Proactive notifications on/off
- Intro text (first-touch) input
- Notification timeout (seconds, default 20)
- Auto-close timer (seconds; 0 = never)
- Proactive mode: Literal / AI-rephrased / Hybrid

**Page Rules table** (rows from `page_rules`, with discovered `SitePage`s offered as quick-add)
- Columns: Label · Match (type + pattern) · Page type · Greeting message · Behavior prompt · **Widget visible** toggle · **Greeting** toggle · remove
- "Seed default rules" button (writes the brief's table)
- "Add rule" (custom URL pattern)
- Saved via existing client PATCH; SitePages fetched from the new read endpoint.

---

## 9. Phased delivery (step-by-step)

**Phase 0 — Foundations (model + config), no UX change**
1. Migrations: SitePage; Client fields + `page_rules`; ChatSession `greeting_intro_sent`.
2. `classify_path()` shared helper + unit tests.
3. Extend `widget_config` + `ClientSerializer`; seed-defaults action.
4. SitePage upsert in scraper + `site-pages` read endpoint.
*Deliverable:* config & data plumbing live; no visible change. *Tests:* serializer round-trip, classify_path, widget_config shape, tenant-scoping on site-pages.

**Phase 1 — Greeting delivery (server)**
5. `POST /api/chat/page-message/` (match, guards, de-dupe, literal mode, first-touch intro, persist, WS push).
*Deliverable:* greetings persist to inbox + WS. *Tests:* first-touch prepend once; subsequent no intro; de-dupe; takeover/off guards; unknown rule → fallback.

**Phase 2 — Widget notification UX**
6. Suggestion bubble (20s), unread badge (localStorage set), read-&-clear, DND (X), exclude from auto-open, `{product_name}` resolver, call `page-message` per page.
*Deliverable:* the full brief's UX. *Tests:* manual matrix on a test store (timeout, badge increments, clear on open, DND keeps badge, intro once).

**Phase 3 — Per-page visibility + auto-close**
7. Visibility gate on boot + SPA re-eval; auto-close idle timer.
*Deliverable:* hide-on-page + auto-close. *Tests:* hidden page renders nothing; auto-close fires/reset on activity.

**Phase 4 — Per-page behavior prompt (in-chat)**
8. Send `page_url` on normal messages; inject `behavior_prompt` in `build_prompt`.
*Deliverable:* page-specific AI behavior. *Tests:* prompt injection unit test; behavior differs by page.

**Phase 5 — Admin UI**
9. "Proactive & Pages" tab: globals + page-rules table + seed defaults + SitePage quick-add.
*Deliverable:* full tenant control. *Tests:* save/round-trip; gating by plan if desired.

**Phase 6 — Reconcile existing triggers + polish**
10. Decide proactive_open vs page-greeting overlap (§11.3); align behavioral triggers to the bubble model if chosen; analytics tags so greetings don't inflate engagement.

---

## 10. Testing & rollout

- **Automated:** pytest for classify_path, page-message (first-touch/de-dupe/guards), serializer, site-pages scoping, build_prompt injection. Target: keep the suite green (currently 497).
- **Manual:** a Shopify/Woo test store walk-through of the §11 UX matrix; verify hidden-page, auto-close, badge math, DND.
- **Deploy:** migrations + `seed_plans` (if plan-gated) + `widget-vue` build + `collectstatic` + restart daphne (standard VPS sequence). Widget changes require the on-VPS `npm run build`.
- **Backwards-compat:** defaults make the feature inert until a tenant configures it (proactive on but rules empty → fallback greeting only; visibility defaults visible; auto-close 0).

---

## 11. Open decisions (need your call before building)

1. **Literal vs AI vs Hybrid greetings.** The brief gives fixed strings (identical for every visitor → the "robotic" feeling you flagged earlier). Recommend **Hybrid**: literal for cart/checkout/contact, AI-rephrased for home/product/collection. Default in plan = `literal` to honor the brief exactly; switchable per tenant.
2. **Cost/quota for AI mode.** AI-rephrased greeting = 1 LLM call per qualifying page view. We'd cache per (session, page_type) and cap. Confirm acceptable, or keep literal.
3. **Do other triggers also go bubble-only?** Today `exit_intent`/`pricing_hesitation`/etc. auto-open the chat. The brief's philosophy is non-intrusive. Recommend moving **all** proactive messages to bubble+badge for consistency. Confirm, or keep urgent triggers auto-opening.
4. **Storing every greeting in the transcript.** Brief says deliver silently to inbox even if ignored. This can flood the conversation and inflate message/engagement counts. Recommend tagging `page_greeting` so analytics excludes unseen greetings and the AI knows it hasn't truly "engaged." Confirm.
5. **Rate cap per session.** A visitor hitting 12 products shouldn't get 12 bubbles. Recommend: one greeting per **page_type** per session (badge still counts repeats? — propose: no repeat greeting for same type). Confirm the cap.
6. **Page-type source.** Auto-classify by URL (works for Shopify/Woo) + tenant-editable patterns for custom sites. Confirm that's enough, or do we also auto-detect Shopify template via the storefront?
7. **Plan gating.** Should page rules / behavior prompts / auto-close be a Growth+ feature, or available to all paid tenants?

---

## 12. Risk register

| Risk | Mitigation |
|---|---|
| Greeting spam across many pages | per-type de-dupe + session caps (§5.2, §11.5) |
| Transcript/analytics inflation | tag `page_greeting`, exclude from engagement metrics (§11.4) |
| `{product_name}` wrong/missing | multi-source resolver + graceful fallback (§7.7) |
| SPA navigation missed | history hooks; classic reloads covered by boot (§7.6) |
| Widget hidden by mistake on all pages | visibility defaults visible; "hidden" requires explicit rule |
| AI-mode cost blowup | caching + cap + literal default (§11.1/2) |
| Behavior prompts conflicting with persona | inject as additive "PAGE CONTEXT", keep short, defined priority |
| Public `page-message` abuse | DRF throttle + server-side re-match + session guards |
```
