# GrowMiq AI Chatbot — Security, Performance & Scalability Review

**Date:** 2026-06-24
**Scope:** Full-system review per the requested brief (security, performance, scalability).
**Method:** Multi-area deep sweep across authentication/authorization & tenant isolation, API surface & configuration, webhook security, file uploads, customer/lead/chat-history data exposure, database permissions, and performance/scalability under load.
**Outcome:** Production posture verified; **6 Critical/High issues fixed and deployed**; remaining items documented with a prioritized plan. Test suite **489 passing**.

> Companion technical doc with code-level detail: `docs/SECURITY_AUDIT.md`.

---

## 1. Overall result (TL;DR)

- The most dangerous hypothetical — production running insecure dev settings — was **disproven**: prod runs the hardened config (`DEBUG=False`, real secret key, locked hosts), `.env` is gitignored and never committed, and no secrets exist in the repository.
- **Fixed & deployed now:** cross-tenant data-access bugs (the highest-severity class), a broken/bypassable webhook signature, a CORS misconfiguration, file-upload hardening, plus the key database/performance indexes and connection pooling.
- **Remaining:** a set of medium/high items that need a small schema change or frontend coordination (so they aren't rushed) — each is listed with severity and a fix plan.

---

## 2. Findings & fixes mapped to your requested points

### A. Admin access & user roles
**Checked:** the role model (superadmin / staff admin / tenant_admin), permission decorators on every admin endpoint, JWT auth, and the impersonation flow.
**Found:**
- Role enforcement is correct in principle (`get_accessible_clients`, `IsSuperAdmin`), and most endpoints scope correctly.
- **Critical — cross-tenant access (IDOR):** several session-level actions (take over chat, release, send message, upload file) fetched a chat session **only by its ID** with no check that it belonged to the requesting tenant. A tenant could act on another tenant's live conversation — including sending messages to the other tenant's visitors through that tenant's WhatsApp/Messenger connection.
- **Critical — live-chat WebSocket:** the God-View takeover socket let any tenant admin open **any** session ID and read/inject messages cross-tenant.
**Fixed ✅:** added a strict ownership check (`_scoped_session()`) to all four session endpoints, and an ownership check on the God-View WebSocket. Sessions not owned by the requester now return "Not found." Regression tests added; verified live (unauthorized request → 401/404).
**Outstanding ⏳:** JWT refresh-token rotation/blacklist on password change, and impersonation token revocability — Medium; planned.

### B. API security & exposed APIs
**Checked:** every public (unauthenticated) endpoint, rate limiting, CORS/CSRF, secrets handling, error disclosure.
**Found:**
- **High — CORS:** allow-all-origins was combined with allow-credentials (a credential/CSRF foot-gun).
- **Medium — abuse surface:** several widget endpoints (lead capture, analytics beacon, trigger events, link-click, transcript restore) are public and **unthrottled**, allowing spam/score-poisoning; and the AI chat endpoint can be driven by anonymous traffic (LLM cost abuse).
- **Good:** secrets are not in the repo or logs; Stripe/Shopify/invoice signatures are verified; session/client IDs are unguessable UUIDs.
**Fixed ✅:** disabled credentialed CORS (auth is Bearer-token, so it isn't needed) — verified the header is now absent in production.
**Outstanding ⏳:** add rate-limiting/throttling to public widget endpoints and the chat path (nginx `limit_req` + per-connection throttle), and require a valid client before invoking the paid LLM — High (cost); planned. *(Not rushed because hard-blocking risks breaking the live widget; needs careful rollout.)*

### C. Webhook security
**Checked:** all inbound webhooks (WhatsApp, Messenger, Telegram, Shopify, WooCommerce, WordPress, Stripe, Shopify-OAuth/GDPR) for signature verification.
**Found:**
- **High — Shopify (content sync) webhook:** the signature check was computed in the wrong encoding (hex vs Shopify's base64) so it never matched, **and** it was skipped entirely when no secret was configured — meaning a third party who knew the client ID could forge product updates/deletes and **poison or wipe the tenant's knowledge base**.
- **High — Meta/Telegram message webhooks:** verify the setup handshake but **not** the message payload signature.
- **Good:** Stripe, Shopify-OAuth, and the Shopify GDPR webhooks verify signatures correctly.
**Fixed ✅:** corrected the Shopify webhook to base64 constant-time verification and made a configured secret **mandatory** (reject otherwise). Tests updated + added.
**Outstanding ⏳:** Meta/Telegram payload-signature verification — requires storing a per-client app secret (a small schema + settings change); planned. Also webhook replay-protection (dedup on event ID).

### D. File uploads
**Checked:** the live-chat media upload, customer logo upload, and the widget image path.
**Found:**
- **High — attachment upload:** accepted any file type (including HTML/SVG/JS) served from the same origin → stored-XSS risk; and (per A) wasn't tenant-scoped.
- **Good:** the logo upload was already hardened (magic-byte sniffing, size cap, no SVG, random filenames).
**Fixed ✅:** added a strict MIME allowlist (images/audio/PDF/Office/zip/text only — HTML/SVG/JS rejected), kept the 25 MB cap, and applied tenant scoping. Test added (HTML upload now rejected).
**Outstanding ⏳:** add a byte-size cap to the inline widget image path; consider serving attachments from a cookieless media subdomain — Medium.

### E. Customer data, lead data & chat history (data leakage)
**Checked:** what public endpoints return, cross-visitor/cross-tenant exposure, secret storage, logging, and CSV exports.
**Found:**
- **Good:** transcript-restore endpoints are keyed by unguessable UUIDs and return only message text (no internal scoring/contact fields); the new Shopify order-lookup verifies order# **and** email and never reveals a mismatch; CSV exports are tenant-scoped; no PII/secrets are written to logs.
- **High — token exposure:** the client API returns integration tokens (WhatsApp/Messenger/HubSpot/etc.) to the browser in cleartext (own-tenant only, but exposed to any XSS/devtools), and these secrets are stored unencrypted in the database.
- **Medium — order PII persistence & retention:** order tracking details get written into chat history (readable via the transcript endpoint by anyone with the session ID); and the per-plan `data_retention_days` setting is not yet enforced by a purge job.
**Fixed ✅ (this class):** the cross-tenant exposure paths under A/D are closed.
**Outstanding ⏳:** make tokens write-only in the API + encrypt at rest (needs a coordinated frontend change so saving the settings form doesn't wipe stored tokens), redact tracking details from stored history, and add a retention/erasure job — High/Medium; planned. *(Deliberately not rushed to avoid wiping live integration tokens.)*

### F. Database permissions & integrity
**Checked:** ORM query safety (injection), raw SQL, secret defaults, and access scoping at the data layer.
**Found:** no SQL-injection vectors (ORM/parameterized throughout); the real database-layer risk was the **tenant-scoping gaps** (the IDORs in A), now fixed. Database credentials come from environment, not code.
**Fixed ✅:** tenant scoping enforced at the query layer for the affected endpoints.

### G. Stability under more users & live chats (performance/scalability)
**Checked:** hot-path queries, indexes, caching, the AI/RAG path, WebSocket/async handling, Celery offloading, connection pooling, and server topology.
**Found:**
- **Critical (scale) — RAG vector search had no index:** every chat turn did a full sequential scan computing similarity over all of a tenant's content — fine now, slow/expensive at thousands of chunks.
- **High — missing composite indexes** on the chat-session table for the inbox/leads/kanban/analytics filters+sorts.
- **High — no DB connection pooling** (a new Postgres connection per request).
- **Medium — no caching** on the analytics dashboard (recomputed every 45s per open tab) and widget-config (polled per widget per minute); an N+1 in the visitors list; and large chat-history JSON shipped on list endpoints.
- **Medium — single app process** serves REST + all WebSockets + the blocking LLM call (a concurrency ceiling).
**Fixed ✅:**
- Added a **pgvector HNSW index** (the biggest chat-latency win at scale).
- Added **composite indexes** on chat sessions (client + recency/stage).
- Enabled **DB connection pooling** (`CONN_MAX_AGE`).
**Outstanding ⏳ (performance roadmap):** caching for analytics + widget-config (Redis); fix the visitors N+1 and trim list payloads; offload the LLM call to the background queue and/or run multiple app processes (the Redis channel layer already supports horizontal scaling); raise Celery concurrency + split queues. These are the "load balancing / caching / queue handling / DB optimization / scaling" items from the brief — sequenced in the plan below.

---

## 3. Severity summary

| # | Area | Severity | Status |
|---|------|----------|--------|
| 1 | Cross-tenant session actions (takeover/send/upload/release) | Critical | ✅ Fixed |
| 2 | Cross-tenant live-chat WebSocket | Critical | ✅ Fixed |
| 3 | Shopify content webhook signature (broken + bypassable) | High | ✅ Fixed |
| 4 | CORS allow-all + credentials | High | ✅ Fixed |
| 5 | Upload stored-XSS (no MIME allowlist) | High | ✅ Fixed |
| 6 | RAG vector index + DB indexes + connection pooling | High (scale) | ✅ Fixed |
| 7 | Meta/Telegram webhook payload signatures | High | ⏳ Planned (needs app-secret field) |
| 8 | Anonymous LLM cost abuse / widget throttling | High (cost) | ⏳ Planned |
| 9 | Tokens write-only + encryption at rest | High | ⏳ Planned (frontend coord) |
| 10 | SSRF guard on scraper fetches | High | ⏳ Planned |
| 11 | Analytics/widget caching, N+1, list payload trimming | Medium (scale) | ⏳ Planned |
| 12 | LLM offload to queue / multi-process app | Medium (scale) | ⏳ Planned |
| 13 | Webhook replay-protection; data-retention purge | Medium | ⏳ Planned |
| 14 | JWT rotation/blacklist; minor hardening | Medium/Low | ⏳ Planned |

---

## 4. What was deployed in this pass
- Tenant-scoping fix on session takeover / release / send / upload + God-View WebSocket.
- Shopify webhook signature corrected (base64) and secret made mandatory.
- CORS credentials disabled.
- Upload MIME allowlist.
- pgvector HNSW index, chat-session composite indexes, DB connection pooling.
- Regression tests for IDOR, MIME blocking, and webhook signatures (suite: **489 passing**).
- Live-verified: app healthy, unauthorized session action → 401, CORS credential header removed, migrations applied.

## 5. Recommended next sprint (priority order)
1. Anonymous-LLM cost controls (nginx rate-limit + WebSocket throttle + require client).
2. Token serialization → write-only + encryption at rest (with the frontend "send only if changed" change).
3. Meta/Telegram webhook signature verification (add per-client app secret).
4. Analytics + widget-config caching; fix visitors N+1; trim list payloads.
5. SSRF guard; throttles on public widget endpoints; lead-overwrite guard.
6. Offload the LLM call to the queue / run multiple app processes; data-retention purge.

---

*Prepared as part of the requested security, performance, and scalability review. No outstanding item is a known active breach; the fixed items closed the cross-tenant and webhook-forgery exposure, which were the highest-impact risks.*
