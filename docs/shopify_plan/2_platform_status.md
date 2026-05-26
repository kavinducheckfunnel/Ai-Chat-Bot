Here's the PM report. Clean markdown — you can copy/paste directly into Notion, Confluence, email, or share as a doc.

---

# Checkfunnel Platform — Status Report & Sprint Plan

**Prepared:** 2026-05-21
**Deadline:** 2026-05-27 (Wednesday)
**Working days remaining:** 5
**Live URL:** `https://ai.checkfunnels.com`
**Status:** On track. New Shopify scope identified; production essentials reprioritised into this sprint.

---

## Executive Summary

Over the last two sprints we have shipped **30+ production-grade features** spanning UX, super-admin tooling, real-time sync, infrastructure, MLOps foundation, and critical bug fixes. The platform is live with daily backups, health monitoring, and auto-deploy via GitHub Actions.

Going into this final sprint (5 working days), priority work splits into two streams:

1. **Sprint-scope (deadline 27 May):** Complete Shopify merchant integration (Phases A–D), ship production observability (Sentry), off-site backups (Backblaze B2), and pytest in CI. Total estimated effort: ~5 engineering days. **Realistic to complete.**
2. **Post-sprint roadmap (6 months):** GDPR compliance, security hardening, performance work, quality tooling, reliability infrastructure, and Shopify App Store distribution. Itemised in Section 5.

**Decisions required from PM** before sprint kickoff are listed in Section 6 — most importantly: confirm sprint scope, approve Backblaze B2 (~$5/month), approve Sentry free tier.

---

## 1. Shipped (Past 2 Sprints) — 33 Items Across 6 Categories

### 1.1 Frontend UX (10)

| # | Item | Status |
|---|---|---|
| 1 | Portal mobile responsiveness — all 8 pages | ✅ Live |
| 2 | Portal hamburger drawer + mobile single-panel Inbox nav | ✅ Live |
| 3 | Chat widget UI polish (padding, bubbles, reactions) | ✅ Live |
| 4 | Chat history persistence across page navigations | ✅ Live |
| 5 | ClientDetail super admin Settings parity (30+ fields, embedded PortalSettings) | ✅ Live |
| 6 | TenantManagement mobile table overflow fix | ✅ Live |
| 7 | Permissions Manager light-theme bug | ✅ Live |
| 8 | ClientDetail dark-mode theming (16 invisible-text bugs fixed) | ✅ Live |
| 9 | Webhook setup wizard in Knowledge tab (WP/WC/Shopify/Custom) | ✅ Live |
| 10 | CTA mode picker — 3-card radio (AI/Manual/Off) | ✅ Live |

### 1.2 Super Admin Tooling (5 new pages)

| # | Page | Path | Status |
|---|---|---|---|
| 11 | Platform Insights (cross-tenant aggregates) | `/admin/insights` | ✅ Live |
| 12 | Per-client Insights deep dive | `/admin/clients/<id>/insights` | ✅ Live |
| 13 | Activity Heatmap | `/admin/clients/<id>/heatmap` | ✅ Live |
| 14 | Cross-tenant Visitor Explorer | `/admin/visitors` | ✅ Live |
| 15 | Backup management (view/download/trigger/delete) | `/admin/backups` | ✅ Live |

### 1.3 Real-time Sync & Webhooks (6)

| # | Item | Status |
|---|---|---|
| 16 | Shopify + WooCommerce + WordPress webhook handlers (HMAC-verified) | ✅ Live |
| 17 | DELETE event support across all three platforms | ✅ Live |
| 18 | WordPress page-type support (was posts only) | ✅ Live |
| 19 | Sitemap watcher (15-min poll, covers Webflow/Squarespace/custom HTML) | ✅ Live |
| 20 | WebhookEvent audit log + 24h activity counters | ✅ Live |
| 21 | Webhook secret rotation UI | ✅ Live |

### 1.4 Infrastructure (5)

| # | Item | Status |
|---|---|---|
| 22 | Daily backup system (7 daily / 4 weekly / 6 monthly retention) | ✅ Live |
| 23 | Restore script with safety prompts | ✅ Live |
| 24 | CI/CD pipeline (GitHub Actions → backup → migrate → restart → health check → rollback) | ✅ Live |
| 25 | `/api/health/` endpoint (DB + Redis liveness) | ✅ Live |
| 26 | Periodic full re-scrape cadence: 3h → 24h (safety-net only) | ✅ Live |

### 1.5 MLOps Foundation (1)

| # | Item | Status |
|---|---|---|
| 27 | `LLMCallLog` model — every LLM call captures cost, latency, tokens, fallback chain, prompt_hash. Foundation for cost dashboard, A/B testing, drift detection. | ✅ Live |

### 1.6 Critical Bug Fixes (6)

| # | Bug | Fix |
|---|---|---|
| 28 | Kanban drag-drop didn't broadcast to dashboards | Added `channel_layer.group_send` on PATCH endpoint |
| 29 | Two CTAs firing simultaneously (AI-personalised + manual) | New `cta_mode` field (`ai` / `manual` / `off`) — single follow-up strategy |
| 30 | "Expires in 0 minutes" garbage on FOMO messages | Countdown text only when real offer exists AND seconds ≥ 60 |
| 31 | Permissions Manager unreadable in light theme | Replaced hardcoded `#111` with themed token |
| 32 | ClientDetail embed code was the OLD external `<script>` | Now uses `generateEmbedCode()` — byte-identical to tenant snippet |
| 33 | Widget chat reset on page navigation | sessionStorage persistence keyed by sessionId |

---

## 2. Production Status Dashboard

| Area | Maturity | Notes |
|---|---|---|
| Multi-tenant chat platform | 95% | Core flows fully working |
| Super admin tooling | 92% | All major pages shipped |
| Real-time sync (WP/WC/Shopify webhooks + sitemap) | 80% | Shopify install UX gap remains |
| Infrastructure (backups, CI/CD, health) | 90% | Off-site backup pending |
| Observability | 30% | LLMCallLog foundation exists; no Sentry / Grafana yet |
| Compliance (GDPR) | 5% | Roadmapped Sprint+1 |
| Quality tooling (tests in CI, linters, type checks) | 40% | Backend tests exist; not in CI; no frontend tests |
| Shopify merchant install UX | 20% | Scraping works server-side; portal UX gap |

---

## 3. Current Sprint Plan (Thu 22 May → Wed 27 May)

Five working days. Scope below is achievable; items ordered by dependency.

### Day 1 (Thu 22 May) — Shopify A + B + D · ~9 hours

**Phase A — Installation UX** (~2h)
- Add "Shopify" install tab next to "WordPress" on `/portal/settings → Channels & embed`
- 3-step install card: Online Store → Themes → Edit code → `theme.liquid` → paste before `</body>`
- Secondary option: install a free Custom Code Editor Shopify app

**Phase B — Full catalog coverage** (~6h)
- Extend `fetch_shopify_data` to also fetch:
  - `/pages.json` (About, Shipping, FAQ, Returns, etc.)
  - `/blogs.json` + `/blogs/<handle>/articles.json` (blog content)
  - `/collections.json` (product collections)
- Each chunk tagged with `metadata.type = 'page' | 'article' | 'collection' | 'product'`

**Phase D — Platform auto-detect** (~1h)
- During tenant onboarding, sniff for Shopify (domain pattern + `/products.json` response shape)
- Pre-select `platform=SHOPIFY` instead of requiring manual choice

### Day 2 (Fri 23 May) — Shopify C: Real-time Inventory · ~6 hours

- Extend Shopify webhook handler to subscribe to `inventory_levels/update` topic
- Store `inventory_item_id` on each chunk's metadata during initial scrape
- New Celery task: when stock changes, update affected chunk's metadata and re-embed an inventory-aware sentence
- Optionally suppress sold-out products from AI recommendations

### Day 3 (Mon 26 May) — Sentry + Off-site Backups · ~7 hours

**Sentry** (~4h)
- `sentry_sdk` backend integration; DSN via env; capture 5xx with breadcrumbs
- Vue Sentry SDK in widget-vue (admin SPA + chat widget); JS error + Web Vitals capture

**Off-site backups** (~3h)
- Backblaze B2 account + application key
- Add `rclone sync` step to `ops/backup.sh` so daily snapshots push to B2
- Backup integrity check via `pg_restore --list db.dump`

### Day 4 (Tue 27 May before deadline) — pytest in CI + QA buffer · ~5 hours

**pytest CI workflow** (~3h)
- New `.github/workflows/test.yml` — runs pytest on every PR + push to main
- `pytest-cov` for coverage tracking; failing build blocks merge
- Coverage threshold: not gated yet, just reported

**QA + buffer** (~2h)
- End-to-end test of Shopify install on a real Shopify Partner sandbox store
- Smoke test of full deploy pipeline
- Documentation updates in `/docs/runbook.md` (new section)

### Sprint Deliverables

By end of Wednesday 27 May:

- A Shopify merchant can **self-serve installation** end-to-end (paste snippet to theme.liquid, set up webhooks via in-portal wizard, all four phases documented)
- Their **full catalog** (products + pages + blogs + collections) is indexed automatically
- **Real-time inventory sync** working — stock changes propagate within seconds
- **Production-grade error visibility** via Sentry for backend + frontend
- **Off-site backups** active at Backblaze B2 (current backups are on-VPS only — single point of failure)
- **Every PR runs tests** in CI; merging blocked on failure

---

## 4. Sprint Risks & Mitigation

| Risk | Probability | Mitigation |
|---|---|---|
| Backblaze B2 account approval delay | Low | AWS S3 as fallback (5-min switch in rclone config) |
| Shopify test store unavailable | Low | Free Shopify Partner sandbox account available |
| Sentry free-tier sampling drops important errors | Low | Set 100% sample for `level >= error`, 25% for `info` |
| Shopify rate-limits `/products.json` scrape | Very Low | Public endpoint; 250 items/page; documented as unauthenticated |
| Unknown defects surface during Shopify QA | Medium | Day 4 includes 2h QA buffer; can extend into Wed morning if needed |
| GitHub Actions secrets not yet pasted | Medium | One outstanding action item — PM to confirm by Friday |

---

## 5. Post-Sprint Roadmap (Months 2–6)

The full gap analysis identified 5 phases of work beyond this sprint. Summary:

### Sprint+1 (Month 2): GDPR & Security Hardening · ~12 days
- Cookie consent banner in widget
- Data subject export endpoint
- Account deletion with 30-day grace period
- Data retention purge task
- Visitor IP anonymization (`/24` truncation)
- Encrypt API keys + Stripe tokens at column level
- GPG-encrypt backups
- CSP middleware
- 2FA (TOTP) for superadmin
- `django-axes` brute-force protection
- Dependabot dependency scanning

### Sprint+2 (Month 3): Observability & Cost Dashboard · ~10 days
- Cost dashboard from `LLMCallLog` (per-tenant LLM spend, alerts)
- Prometheus + Grafana for metrics
- Correlation IDs across request → Celery → LLM call
- DB connection pooling (`CONN_MAX_AGE`)
- Missing indexes (`ChatSession`, `Visitor`, `DocumentChunk` composites)
- N+1 query audit
- HTTP cache headers in nginx
- Status page (`status.checkfunnel.com`)

### Sprint+3 (Month 4): Quality & DX · ~10 days
- `ruff` + `black` + `pre-commit` (backend)
- `eslint` + `prettier` (frontend)
- Vitest + Playwright for 3 golden paths
- API docs via `drf-spectacular` → Swagger UI at `/api/docs/`
- `README.md` + `CONTRIBUTING.md` + `/docs/runbook.md`
- Bundle size CI check
- GitHub PR template + branch protection

### Sprint+4 (Month 5): Reliability & Polish · ~10 days
- WAL archiving / Point-in-Time-Recovery for Postgres
- Read replica for analytics queries
- Redis Sentinel or managed Redis
- Multi-daphne with nginx upstream
- Stripe billing reconciliation
- Accessibility audit (WCAG AA)
- i18n scaffolding

### Sprint+5 (Month 6): MLOps Depth & Shopify App · ~10 days
- Quality signals (👍/👎 → `prompt_hash` A/B grouping)
- Embedding health monitor + auto re-embed
- Prompt + Model A/B testing infrastructure
- Drift detection on chunk distribution
- **Shopify App with OAuth** (App Store listed): auto-webhook registration, ScriptTag widget injection, inventory levels via Admin API
- Customer help center
- In-app onboarding tour

**Total post-sprint effort: ~52 engineer-days across 5 months.** Solo-developer-feasible at ~50% of capacity (remaining 50% covers ongoing feature work, customer support, ops).

---

## 6. Decisions Required from PM

| # | Decision | Recommended | Rationale |
|---|---|---|---|
| 1 | Confirm sprint scope (Section 3) | Approve A+B+C+D + Sentry + off-site backups + CI tests | Achievable in 5 days; covers all the highest-impact gaps |
| 2 | Off-site backup provider | Backblaze B2 (~$5/mo for 100GB) | Cheapest S3-compatible option; offsite DR satisfied |
| 3 | Sentry tier | Cloud free (5k errors/month) | Sufficient for current traffic; upgrade later |
| 4 | Shopify integration depth | Phase A+B+C+D (full real-time, no Admin API) | Fits in sprint; covers 95% of merchants without app-store submission |
| 5 | When to build proper Shopify App | Defer to Sprint+5 | Validate demand first with 5+ paying Shopify merchants |
| 6 | Deadline strictness | Confirm: hard Wed EOD or Thu QA day acceptable? | Affects QA buffer planning |
| 7 | GitHub Actions secrets (VPS_HOST, VPS_USER, VPS_SSH_KEY) | Paste this week | 5-min task; unlocks auto-deploy |
| 8 | GDPR urgency | Confirm Sprint+1 is mandatory | EU customers expected; non-negotiable per audit |

---

## 7. Open Items / Blockers

- [ ] **GitHub Actions secrets** not yet pasted into repo (3 secrets, ~5 minutes manual work)
- [ ] **Backblaze B2 / Sentry accounts** need PM approval before Day 3
- [ ] **No paying Shopify merchant yet** — Shopify integration is speculative; phase scope assumes pre-launch readiness
- [ ] **No EU customers confirmed** — GDPR work in Sprint+1 is precautionary based on stated expectation

---

## 8. Production Snapshot (Live as of 2026-05-21)

| Metric | Value |
|---|---|
| Deployed commit | `bf3cc65` (CTA fix) |
| Last deploy | 2026-05-21 02:59 UTC (via `checkfunnel-deploy.sh`) |
| Services healthy | daphne ✓ · celery ✓ · celery-beat ✓ |
| Health endpoint | `200 OK` (DB + Redis green) |
| Latest backup | 2026-05-20 (3.8 MB; **on-VPS only — off-site coming this sprint**) |
| CI workflow status | `.github/workflows/deploy.yml` configured, secrets pending |
| Cron schedules | Daily backup 03:00 UTC · Sitemap watcher every 15 min · Full re-scrape daily 02:00 UTC |
| Webhook activity (last 24h) | (insert: counts from `/admin/clients/<id>/webhook-events/` if needed for PM) |

---

**End of report.**

---

## How to share this

This is plain markdown — paste it directly into:
- Notion / Confluence / Coda → renders natively
- Email → most modern clients render markdown; otherwise paste as code block
- Google Docs → File → Import → choose this as `.md` for native conversion

If you want, I can also:
1. **Save this as a file** in the repo at `/docs/sprint-2026-05-27.md` so it's version-controlled
2. **Spin it into a one-page TL;DR** (just Sections 2, 3, and 6) if your PM prefers brevity
3. **Generate a Gantt-style chart** of the 5-day sprint plan for visual stakeholders

Say the word and I'll do any of those.