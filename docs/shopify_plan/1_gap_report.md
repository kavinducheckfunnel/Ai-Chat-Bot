Here's a complete report on the current state, gaps, and what's needed to ship a production-grade Shopify integration.

---

# 📋 Shopify Integration — Gap Report

## 1. What we have today

The codebase already has **partial** Shopify support — it's not greenfield, but it's also not complete:

| Component | Status | File |
|---|---|---|
| `Client.platform = 'SHOPIFY'` choice | ✅ Exists | [`users/models.py:78`](users/models.py#L78) |
| Product scraping via public `/products.json` | ✅ Works | [`scraper/ingestion.py:498-543`](scraper/ingestion.py#L498) |
| Webhook handler for product create/update | ✅ Works | [`scraper/views.py:79-117`](scraper/views.py#L79) |
| Webhook handler for product delete | ✅ Works (added Phase 2) | Same |
| HMAC signature verification | ✅ `X-Shopify-Hmac-Sha256` checked | Same |
| Sitemap watcher (catches pages a merchant adds) | ✅ Phase 2 | [`scraper/tasks.py:watch_sitemaps_for_changes`](scraper/tasks.py) |
| Webhook activity log + audit | ✅ Phase 1 | `WebhookEvent` model |
| Auto-scrape dispatch by platform | ✅ Routes SHOPIFY → fetch_shopify_data | [`scraper/ingestion.py:588-589`](scraper/ingestion.py#L588) |

**What this means in practice today:** A merchant who manually sets `platform=SHOPIFY` on their client, pastes our snippet into `theme.liquid`, and configures three Shopify webhooks gets a *mostly* working integration — product create/update/delete syncs in seconds, the daily safety-net crawl catches new pages.

---

## 2. What's missing

### Gap A — Installation friction (no Shopify install wizard)

The portal's `/portal/settings → Channels & embed` page currently shows **WordPress** instructions (WPCode plugin + functions.php tabs). There's no Shopify-specific tab. The merchant has to figure out on their own that:
- Our raw HTML snippet works in `theme.liquid`
- Or that they should install a custom-code Shopify app
- Or how to set up the webhooks in Shopify admin

**No code change needed for the snippet itself — it already works on Shopify.** The gap is purely documentation/UI.

### Gap B — Catalog coverage is products-only

`fetch_shopify_data()` only hits `/products.json`. It misses:

| Content type | Shopify endpoint | What's lost without it |
|---|---|---|
| **Static pages** (About, Shipping, FAQ, Returns) | `/pages.json` | AI can't answer policy questions |
| **Blog articles** | `/blogs.json` + `/blogs/<id>/articles.json` | AI doesn't know about content marketing |
| **Collections** | `/collections.json` + `/products.json?collection_id=…` | AI can't say "we have a Summer collection" |
| **Product metafields** | Requires Admin API (auth) | Can't see size guides, custom specs |
| **Variants beyond first** | Already captured | OK |
| **Draft products** | Requires Admin API (auth) | Can't preview unpublished products |

The sitemap watcher (Phase 2) **does** partially close this gap because Shopify auto-generates sitemap entries for pages, articles, and collections — but the watcher only triggers on `lastmod` changes, not on initial ingestion. So a new tenant misses pages/blogs until their next sitemap-watcher tick.

### Gap C — Real-time inventory NOT synced

The current Shopify webhook only listens for `products/*` topics. Shopify emits separate events for stock:

| Topic | What it tells us | Currently handled? |
|---|---|---|
| `products/create` / `update` / `delete` | Title, body, variants, price | ✅ Yes |
| `inventory_levels/update` | Stock count changed at a location | ❌ No |
| `inventory_levels/connect` | Variant linked to a new location | ❌ No |
| `inventory_items/update` | SKU / cost / tracking changed | ❌ No |
| `orders/create` | New order (could trim stock proactively) | ❌ No |

**Impact:** If a product runs out, our embeddings still say "available" because the *product* didn't change — only its *inventory level* did. AI confidently recommends sold-out items.

### Gap D — No platform auto-detection

`client.platform` is set manually during onboarding. We could detect Shopify automatically by:
- Domain ends in `.myshopify.com`
- Response includes `X-Shopify-Stage` or `X-ShopId` header
- HTML contains `Shopify.theme` / `Shopify.shop` JS objects
- `/products.json` returns valid JSON

This is a one-shot check at onboarding time, ~30 lines of code, and removes a step from the wizard.

### Gap E — No Admin API integration (the big one)

Right now everything Shopify-side is **public, read-only, scrape-based**. To level up to industry standard (Tidio / Crisp / Gorgias level), we need OAuth + Admin API access. That unlocks:

| Feature | Why it needs Admin API |
|---|---|
| Auto-register webhooks (no manual setup) | `POST /admin/api/2024-04/webhooks.json` |
| Read inventory levels per location | `GET /admin/api/2024-04/inventory_levels.json` |
| Read draft products | `?published_status=any` requires auth |
| Read customer-specific pricing | B2B / VIP customer scopes |
| Read metafields (size guides, custom specs) | `GET /products/<id>/metafields.json` |
| Read orders for context ("track my order #1234") | `read_orders` scope |
| Read customers (returning visitor context) | `read_customers` scope |
| Update inventory / fulfillments (advanced bots) | Write scopes |

### Gap F — No Shopify App = no App Store distribution

This is the most important business gap, not a technical one. Right now to install us a merchant must:

1. Read three setup pages
2. Copy a snippet, edit theme.liquid, paste, save
3. Open Shopify admin, navigate to Notifications → Webhooks
4. Create 3+ webhooks individually, paste URL + secret each time
5. Hope they got the topic names right

A proper Shopify App (App Store listed) reduces all that to: **install button → toggle ON in theme → done.**

---

## 3. Do we need merchant backend access?

**No, not for the basic integration.** Two zero-access paths work today:

| Path | Merchant grants | What we can do |
|---|---|---|
| **Tier 0: Public-only (current)** | Just paste snippet + create webhooks manually | Products, pages (via sitemap), basic real-time sync |
| **Tier 1: + Custom-Code app** | Install free Custom Code Editor app from App Store, paste snippet | Same as Tier 0, but easier install |
| **Tier 2: OAuth via our Shopify App** | One-click "Install Checkfunnel" on Shopify App Store, approves OAuth scopes | Tier 1 + inventory levels + draft products + auto-webhooks + metafields + (optionally) orders/customers |
| **Tier 3: Admin API token from merchant** | Merchant manually creates a custom app in their admin, gives us the access token | Same as Tier 2 but more friction, useful for power users only |

**Most realistic recommendation:** stay at **Tier 0/1** for the next 1–2 months while you onboard the first few Shopify merchants and validate the use case. Then build the **Tier 2** Shopify App once you have proof of demand.

---

## 4. Real-time inventory + knowledge sync — how it would work

This is what the user is specifically asking about. Here's the proposed flow:

```
Merchant changes a product's stock in Shopify admin
            ↓
Shopify fires "inventory_levels/update" webhook
            ↓
POST /api/scraper/webhooks/shopify/<client_id>/
   X-Shopify-Topic: inventory_levels/update
   { inventory_item_id, location_id, available, ... }
            ↓
scraper/views.py:shopify_webhook detects topic
            ↓
NEW: scraper/tasks.py:update_inventory_for_variant(client, inventory_item_id, available)
            ↓
Find the DocumentChunk(s) for that variant (we already have product_id;
  add inventory_item_id to metadata at scrape time)
            ↓
Update the chunk's `metadata.inventory.available` field
   AND embed a short "Stock: X units" sentence appended to content
            ↓
Re-generate the embedding for that one chunk only
            ↓
AI retrieval now returns "currently 12 in stock" / "currently sold out"
            ↓
Optional: if available == 0, suppress this product from recommendations
   by adding a metadata flag `is_active=false`
```

**Effort to implement this slice:** ~6 hours of work. Two new things needed:

1. **Extend `fetch_shopify_data`** to also capture `variants[].inventory_item_id` and store it in `DocumentChunk.metadata.inventory_items = [...]`.
2. **Add a new branch in `shopify_webhook`** that detects topic `inventory_levels/update` and queues a new Celery task `update_inventory_for_chunk`.

This sits alongside the existing product webhook — both fire in real-time, both close audit-log rows.

---

## 5. Scraping all products + pages — what we need to do

Right now we only get products via `/products.json`. To capture the full catalog properly:

### Without Admin API (public-only — works for ANY Shopify store today)

Extend `fetch_shopify_data` to also call these public endpoints:

| Endpoint | What it returns |
|---|---|
| `/products.json` ✅ | Products (already done) |
| `/pages.json` | Pages (About, Shipping, FAQ, etc.) |
| `/blogs.json` + `/blogs/<handle>/articles.json` | Blog articles |
| `/collections.json` | Collection summaries |
| `/sitemap.xml` (already used by Phase 2 watcher) | Discovery of new URLs |

All of these are public, no auth needed, paginated similarly. Adding them is roughly 40 lines per endpoint.

### With Admin API (richer — requires the merchant to install our Shopify App)

Same as above PLUS:
- `/admin/api/2024-04/inventory_levels.json?location_ids=...` — true stock counts
- `/admin/api/2024-04/products.json?published_status=any` — includes drafts
- `/admin/api/2024-04/products/<id>/metafields.json` — custom fields
- `/admin/api/2024-04/script_tags.json` — auto-inject our widget (no theme edit needed!)

### Frequency

- **Initial ingestion**: one-shot when merchant connects, async via Celery
- **Real-time updates**: webhooks for create/update/delete/inventory (instant)
- **Sitemap watcher**: every 15 min (catches anything webhooks missed)
- **Daily safety-net**: full re-scrape at 02:00 UTC (catches drift on custom-coded stores)

---

## 6. Proposed phased roadmap

| Phase | What ships | Merchant friction | Effort |
|---|---|---|---|
| **A — Documentation only** | Portal gets a "Shopify" install tab with theme.liquid steps + screenshots + webhook setup wizard. Existing scraping code unchanged. | Manual but documented | ~2 hours |
| **B — Catalog coverage** | Extend `fetch_shopify_data` to also fetch pages.json, blogs.json, collections.json. Sitemap watcher already covers ongoing discovery. | Same as A | ~6 hours |
| **C — Inventory webhook** | Listen for `inventory_levels/update`, store `inventory_item_id` per variant, update chunks in real-time. | Merchant adds one extra webhook | ~6 hours |
| **D — Platform auto-detect** | At onboarding, sniff for Shopify and pre-select the platform. | Skips one wizard step | ~1 hour |
| **E — Shopify App (proper)** | OAuth flow, App Store listing, auto-webhook registration, ScriptTag widget injection (no theme.liquid edit), optional inventory + orders + customers scopes. | One-click install | **2–3 weeks** including review |
| **F — App Embed Block (Online Store 2.0)** | Shopify Theme App Extension so merchants enable us via Theme Editor checkbox instead of pasting code. | Theme-editor toggle, no code | +3 days on top of E |

**My recommendation:**
- Ship **A + B + D** this week (~9 hours) — completes the zero-access Shopify story.
- Ship **C** the week after (~6 hours) — adds the inventory sync the user is explicitly asking about.
- Defer **E + F** until you have ~5 paying Shopify merchants, because Shopify App Store submission takes effort + review time and you'll want real users to validate the OAuth flow.

---

## 7. Direct answers to the user's questions

> **"How do we add our chat widget to a Shopify website?"**

Today: paste the existing HTML snippet from `/portal/settings → Channels & embed` into `theme.liquid` right before `</body>`. Or install any free Shopify custom-code app and paste it there. No code change on our side required. We just need to document it in the portal (Phase A).

> **"How do we scrape all the products and pages?"**

Products are already scraped via `/products.json`. Pages, blogs, and collections need ~40 lines per endpoint added to `scraper/ingestion.py` — all public, no auth needed (Phase B).

> **"Do we need their backend access?"**

No for products + pages + real-time sync via webhooks. **Yes** for: draft products, true inventory levels, metafields, orders, customers, auto-webhook registration. The "yes" version comes via the Shopify App with OAuth (Phase E), not by asking them for their admin password.

> **"Any way to update real-time the inventory AND the knowledge same time?"**

Yes — add the `inventory_levels/update` webhook handler (Phase C). Shopify fires this every time stock changes; we re-embed the affected chunk within seconds. Same realtime guarantee we already have for product create/update/delete — just extended to stock counts.

---

## 8. What I'd ship first

Given your existing momentum and the gap-analysis roadmap, **the highest-value 1-day chunk is Phase A + B + D**:

- Portal gets a polished "Shopify" install card next to "WordPress"
- Catalog scraping captures everything public (products + pages + blogs + collections)
- Platform auto-detect removes a wizard step
- Total effort: ~9 hours
- Outcome: a Shopify merchant can self-serve the whole installation, and we capture their full content catalog, all without Admin API access

**Phase C (real-time inventory)** is the natural follow-up at ~6 more hours.

Say the word and I'll start Phase A. If you want me to defer Shopify entirely until you have a confirmed Shopify customer, that's also a reasonable call — currently no paying tenants are on Shopify so we'd be building speculatively.