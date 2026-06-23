# Shopify Order-Tracking — Implementation Plan

Lets visitors ask the chatbot "where's my order / is it delivered?" and get a real
answer from the merchant's Shopify store.

**Decisions (locked):**
- **Connection:** Shopify **Dev Dashboard custom app** → merchant pastes **Client ID + Client Secret + shop domain** into the portal. (2026 change — see below.) OAuth one-click deferred.
- **Verification:** require **order number + matching email** before revealing any status.
- **Freshness:** **live lookup** per query via the Admin API (webhook caching deferred).

## 2026 Shopify credential change (IMPORTANT)
As of **Jan 1 2026**, Shopify removed in-admin custom-app creation and **no longer issues permanent `shpat_` tokens**. New custom apps are created in the **Dev Dashboard** and expose only a **Client ID + Client Secret**. The backend must exchange these for a **short-lived (24h) access token** via the **client-credentials grant** (works because each merchant's app lives in their own store org), cached + auto-refreshed before expiry. Existing pre-2026 `shpat_` tokens still work, so accept a pasted token too as a fallback.

## Why a new connection is needed
Current Shopify integration only reads the **public** `/products.json` (no auth). Orders are private → require the **authenticated Admin API** with `read_orders` scope. `Client` stores domain + webhook_secret but **no Admin credentials** (`users/models.py`). That's the missing piece.

## Flow
1. Visitor asks an order question → `_ORDER_STATUS_PATTERNS` regex detects intent (mirror `_CATALOG_PATTERNS`, `ai_service.py:636`).
2. Bot asks for **order number + email** (prompt skill block) if not already known.
3. Backend extracts order# + email (`extract_email` exists) and calls Admin API:
   `GET /admin/api/2024-10/orders.json?name=<num>&status=any`.
4. **Security:** confirm the order's `customer.email` == the email given. Mismatch/none → "couldn't find an order matching that number + email" (never confirm existence).
5. Inject a normalized **ORDER CONTEXT** block into the LLM prompt (same mechanism as catalog injection — no function-calling). LLM writes the friendly reply.

Normalized order shape: `{number, financial_status, fulfillment_status, fulfillments:[{carrier, tracking_number, tracking_url, shipment_status}], items:[{title, qty}], placed_at, eta}`.

## Phase 1 tasks (MVP, ~2–3 days)
- [ ] `Client`: add `shopify_client_id`, `shopify_client_secret` (**encrypted**, Fernet), `shopify_api_version` (default `2024-10`), and a cached `shopify_token`/`shopify_token_expires_at` (also accept a legacy pasted `shpat_` token); migration.
- [ ] `chat/shopify_orders.py`:
  - `_get_access_token(client)` → client-credentials grant exchange (POST `https://{shop}/admin/oauth/access_token`), cache until expiry, auto-refresh; fall back to a stored `shpat_` token if present.
  - `lookup_order(client, order_number, email)` → Admin API call, **email-match verification**, normalized return, rate-limit + audit log, graceful errors.
- [ ] `ai_service.py`: `_ORDER_STATUS_PATTERNS` + `_is_order_query()`; flow to ask for order#+email, then lookup + inject ORDER CONTEXT before the LLM call.
- [ ] `prompts.py`: a short "Order Status" skill — ask for order#+email once, answer ONLY from injected context, never invent a status; if not found, apologize + offer human handoff.
- [ ] `PortalSettings.vue` (Shopify section): **Client ID + Client Secret (masked) + shop domain** fields + "Test connection" button hitting a backend `test_shopify_orders` endpoint (does a live token exchange + sample order query).
- [ ] Tests: lookup success, email-mismatch denial, not-found, no-token, intent detection, no PII leak across sessions.

## Security / privacy
- Reveal status only on order# **and** email match (Shopify's own standard).
- Encrypt the Admin token at rest (it can read all orders) — stronger than current plaintext channel tokens.
- Minimal scopes: `read_orders` (+ `read_fulfillments`).
- Rate-limit + log lookups per session; don't persist full order PII in chat history.

## Later phases
- **Phase 2:** `orders/create` / `orders/updated` / `fulfillments/update` webhooks (reuse HMAC pattern) → cached `Order` table + proactive "your order shipped" messages.
- **Phase 3:** one-click OAuth "Connect Shopify"; WooCommerce parity; order-query analytics.

## Merchant setup (2026 Dev Dashboard)
Shopify admin → Settings → Apps and sales channels → Develop apps → Allow custom app development → **Build apps using Dev Dashboard** → Create app → add Admin API scopes `read_orders` (+`read_fulfillments`, opt. `read_customers`) → Release version → Install on store → copy **Client ID + Client Secret** → paste in our portal with the shop domain. (No `shpat_` token is shown anymore; the backend exchanges the Client ID/Secret for a 24h token automatically.)
