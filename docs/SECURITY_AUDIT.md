# GrowMiq — Security, Performance & Scalability Audit (2026-06-24)

Deep multi-area sweep (authz/tenant-isolation, API surface, webhooks/uploads, PII/data-leakage, performance/scalability). Severity: **Critical / High / Medium / Low**. Status: ✅ Fixed this pass · ⏳ Outstanding (planned).

---

## Executive summary
- **Verified the worst-case is NOT happening:** production runs the hardened `settings_prod` (systemd sets `DJANGO_SETTINGS_MODULE`), `DEBUG=False`, real env `SECRET_KEY`, restricted `ALLOWED_HOSTS`. `.env` is gitignored and never committed; no real secrets in the repo; Stripe/Shopify/invoice signatures all verified.
- **Fixed now:** 5 cross-tenant IDORs (incl. a live-chat WebSocket one), CORS credential foot-gun, a broken+bypassable Shopify webhook HMAC, upload MIME hardening, DB indexes (incl. pgvector ANN) and connection pooling.
- **Outstanding (needs a follow-up pass / decisions):** Meta/Telegram webhook signatures, anonymous LLM cost-abuse throttling, write-only token serialization, analytics/widget caching, data-retention job. Details + plan below.

---

## ✅ FIXED THIS PASS

### CRITICAL — Cross-tenant IDOR on session actions
Any authenticated `tenant_admin` could act on **another tenant's** chat session by guessing/knowing a `session_id`:
- `session_takeover`, `session_release`, `session_send_message`, `upload_attachment` fetched by `session_id` with **no tenant scoping**. `session_send_message` could even send messages to the victim tenant's visitors over **their** WhatsApp/Messenger tokens.
- **Fix:** new `_scoped_session()` helper (`users/admin_views.py`) — resolves the session only if its client ∈ `get_accessible_clients(user)`; NULL-client sessions treated as inaccessible. Applied to all four endpoints. Regression test added.

### CRITICAL — GodView WebSocket had no tenant scoping
`GodViewConsumer` (`chat/admin_consumers.py`) accepted any `tenant_admin` for **any** `session_id` → read full live transcripts + inject messages cross-tenant.
- **Fix:** added `_can_access_session()` ownership check on `connect`; closes `4003` if the session's client isn't accessible.

### HIGH — Shopify (scraper) webhook HMAC broken **and** bypassable
`scraper/views.py shopify_webhook` compared a **hex** digest while Shopify sends **base64** (so every signed webhook failed), and verification was skipped entirely when no secret was set → an attacker knowing the `client_id` could forge product `update`/`delete` and **poison/purge the tenant's knowledge base**.
- **Fix:** base64 HMAC + `compare_digest`; **require** a configured secret (401 otherwise). Tests updated + a "reject when no secret" test added.

### HIGH — CORS allow-all combined with allow-credentials
Base + prod settings had `CORS_ALLOW_ALL_ORIGINS=True` **and** `CORS_ALLOW_CREDENTIALS=True` (a known CSRF/credential foot-gun).
- **Fix:** `CORS_ALLOW_CREDENTIALS=False` in both (auth is JWT Bearer, not cookies — credentials aren't needed).

### HIGH — Upload endpoint stored-XSS / type abuse
`upload_attachment` accepted any MIME (incl. `text/html`, `image/svg+xml`) up to 25 MB, served same-origin → stored XSS.
- **Fix:** MIME allowlist (images/audio/pdf/office/zip/text only); HTML/SVG/JS rejected. (Tenant scoping also added above.) Test added.

### MEDIUM/PERF — Missing DB indexes & no connection pooling
- **Fix:** composite indexes on `ChatSession (client,-last_message_at)`, `(client,-created_at)`, `(client,kanban_state)`, `(client,conversation_state)` — covers the inbox/leads/kanban/analytics hot paths.
- **Fix:** **pgvector HNSW index** on `DocumentChunk.embedding` (`vector_cosine_ops`) + `client` index — turns every RAG lookup from a full sequential scan into sub-linear ANN (the single biggest scalability win for chat latency at scale).
- **Fix:** `CONN_MAX_AGE=60` + `CONN_HEALTH_CHECKS` in prod (was 0 → a fresh Postgres connection per request/sync-call).

---

## ⏳ OUTSTANDING (prioritized, with plan)

### HIGH — Meta/Telegram inbound webhooks don't verify payload signatures
`whatsapp_webhook`/`messenger_webhook`/`telegram_webhook` only check the GET verify-token, not the POST `X-Hub-Signature-256` / Telegram secret-token. Anyone with a `client_id` can forge inbound messages (burns tenant quota, sends outbound replies). *Not fixed now because it needs a per-client Meta **app secret** field (the app secret isn't stored) + tenant input.*
**Plan:** add `whatsapp_app_secret`/`messenger_app_secret` fields; verify `X-Hub-Signature-256` (HMAC raw body); set + check a per-client Telegram `secret_token` at `setWebhook`. (Shopify OAuth + GDPR webhooks already verify correctly.)

### HIGH/CRITICAL (cost) — Anonymous LLM spend
`chat_message` (REST) and `ChatConsumer` (WS) run the paid LLM for sessions with **no client** (quota bypassed). WS has only a 1s gap, no per-message throttle. *Not fixed now — hard-blocking risks breaking the live widget init path; needs care.*
**Plan:** require a valid `client_id` to create a session + invoke the LLM; add a per-connection WS throttle + shared atomic quota across REST/WS; add nginx `limit_req` on `/api/chat/` and the WS upgrade.

### HIGH — Tokens returned to the frontend + plaintext at rest
`ClientSerializer` returns `*_access_token`/`*_api_key`/`webhook_url` in cleartext (tenant-scoped, so own-data only — risk is XSS/devtools harvest), and all integration secrets are plaintext columns. *Not fixed now: making them write-only without a coordinated frontend "only send if changed" change would **wipe stored tokens on the next settings save**.*
**Plan:** write-only fields + `*_configured` booleans + masked suffix; update PortalSettings to send a token only when edited; encrypt secrets at rest (Fernet/KMS) and rotate.

### HIGH — SSRF on tenant-controlled outbound fetches
The scraper fetches `client.domain_url` (tenant-editable) with no internal-IP guard → a tenant could target `169.254.169.254`/localhost/internal IPs. (Shopify paths are constrained by the `*.myshopify.com` allowlist — safe.)
**Plan:** a shared URL validator (scheme allowlist + resolve host, reject private/loopback/link-local, re-check on redirects) applied before every scraper `requests.*`.

### MEDIUM — Widget endpoint abuse (no throttle): `capture_lead`, `trigger_event`, analytics `beacon`, `track_link_click`, `session_messages`, `visitor_latest_session`
Public + unthrottled → lead spam / CRM+Slack+webhook fan-out abuse, EMA/score poisoning, attribution poisoning, transcript reads. `session_id` is a proper UUIDv4 (not enumerable) — good — but a leaked id grants unthrottled transcript reads, and `capture_lead` overwrites an existing lead's email.
**Plan:** apply DRF throttles to all public widget endpoints; don't overwrite an already-set `lead_email`; bind beacon/lead/restore to a server-issued/first-party session token; add `rel="noreferrer"` on AI-sent links.

### MEDIUM — Performance/scalability (no breakage, but needed for growth)
- **Analytics + widget_config recomputed with zero caching** — `client_analytics` (~40 queries + Python loops) re-runs every 45s per open dashboard; `widget_config` hits the DB per widget per minute. **Plan:** Redis cache keyed by `(client_id, period[, dates])`, 60s TTL; cache widget_config 60–300s, invalidate on PATCH.
- **`client_visitors` N+1** (2 queries/visitor + JSON loop) and **`client_sessions`/`kanban_view` ship the big `chat_history` JSON** on list endpoints. **Plan:** annotate aggregates in one pass; `.only(...)`; drop `chat_history` from list payloads (load lazily on open).
- **One Daphne process serves REST + all WS + the blocking LLM call** → concurrency ceiling. **Plan:** offload `generate_ai_response` to Celery and push the reply via the channel layer, and/or run multiple Daphne procs (Redis channel layer already supports it); raise Celery concurrency + split fast/heavy queues.

### MEDIUM — Webhook replay protection + GDPR retention
No replay/dedup on webhooks; `data_retention_days` exists but nothing purges chat history/PII; Shopify GDPR webhooks are 200-stubs.
**Plan:** dedup on platform event-id (the `WebhookEvent` table can store it); scheduled purge honoring `data_retention_days` (`-1` = forever); per-visitor erasure endpoint.

### LOW
- `visitor_uid` generated with `Math.random()` in one widget path (use `crypto.randomUUID()`).
- `grant_addon_credits` uses inline `is_superuser` vs `IsSuperAdmin` (consistency).
- Account-owner emails logged at INFO (minor PII hygiene).
- nginx could serve the Vue dist directly (off-load WhiteNoise/Daphne).

---

## Notable GOOD findings (already solid)
Tenant scoping via `get_accessible_clients` on the vast majority of admin endpoints; Stripe + Shopify-OAuth + invoice-token signatures verified; logo upload hardened (magic-byte sniff, no SVG, random name); no secrets in logs or repo; `session_id`/`client_id` are UUIDv4; order-lookup email verification is correct and non-enumerable; exports are tenant-scoped; slow work largely offloaded to Celery; Redis channel layer enables horizontal scaling.

---

## Recommended next sprint (in order)
1. Anonymous-LLM cost controls (nginx `limit_req` + WS throttle + require client). 
2. Token serialization → write-only + encrypt at rest (with frontend coordination).
3. Meta/Telegram webhook signatures.
4. Analytics + widget_config caching; `client_visitors`/list payload trimming.
5. SSRF guard; webhook throttles + lead-overwrite guard.
6. Offload LLM to Celery / multi-Daphne; data-retention purge.
