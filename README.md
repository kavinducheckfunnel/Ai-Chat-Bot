<div align="center">

# ⚡ GrowMiq (Checkfunnel)

### Multi-tenant, multi-channel AI chat-sales-agent SaaS

Turn website visitors into qualified leads with an embeddable AI agent that answers product
questions, captures contacts, scores buyer intent in real time, and lets your team take over live.

`Django` · `Django Channels` · `Celery` · `PostgreSQL + pgvector` · `Vue 3` · `Stripe`

</div>

---

## Table of Contents

1. [What is this?](#1-what-is-this)
2. [Key features](#2-key-features)
3. [Architecture overview](#3-architecture-overview)
4. [Tech stack](#4-tech-stack)
5. [Repository structure](#5-repository-structure)
6. [Backend apps in depth](#6-backend-apps-in-depth)
7. [Frontend in depth](#7-frontend-in-depth)
8. [How a conversation flows](#8-how-a-conversation-flows)
9. [Data model (core entities)](#9-data-model-core-entities)
10. [Local development setup](#10-local-development-setup)
11. [Environment variables](#11-environment-variables)
12. [Background jobs (Celery)](#12-background-jobs-celery)
13. [Testing & QA](#13-testing--qa)
14. [Deployment](#14-deployment)
15. [Useful management commands](#15-useful-management-commands)

---

## 1. What is this?

**GrowMiq** (internally **Checkfunnel**) is a SaaS platform that lets any business deploy an
AI-powered sales/support agent across multiple channels — **website widget, WhatsApp, Facebook
Messenger, and Telegram** — from a single multi-tenant backend.

Unlike a plain FAQ chatbot, the agent:

- **Grounds answers** in the business's own content/product catalog via Retrieval-Augmented
  Generation (RAG) over a `pgvector` store.
- **Scores every conversation** on purchase **intent**, **budget**, and **urgency** using
  exponential moving averages (a "3-EMA" heat score) and a sales conversation state machine.
- **Captures and qualifies leads**, auto-progressing them through a Kanban pipeline
  (New → Engaged → Hot lead → Converted).
- Supports **real-time human takeover** ("God View") — an agent can jump into any live AI
  conversation, with the reply routed back to whatever channel the visitor is on.
- Is **billed by AI message volume** (not seats) through Stripe, with **BYOK** (bring-your-own
  OpenAI/Anthropic key) on any plan.

---

## 2. Key features

| Area | Capability |
|------|-----------|
| **Channels** | Embeddable web widget, WhatsApp Business, Facebook Messenger, Telegram |
| **AI** | RAG grounding, multi-provider LLM routing + fallback, multimodal (image) support, BYOK |
| **Lead scoring** | Real-time intent/budget/urgency EMAs, composite heat score, conversation-state machine |
| **Pipeline** | Auto-progressing Kanban (New/Engaged/Hot/Converted/Lost), drag-and-drop board |
| **Live ops** | God-View human takeover, real-time inbox over WebSockets, live session grid |
| **Lead capture** | In-chat email/phone capture with validation, image upload, voice input |
| **Analytics** | KPIs, funnels, conversation states, heat distribution, behavior heatmaps, referrals |
| **Billing** | Stripe subscriptions, message-based metering, usage meters, invoices (PDF), add-on top-ups |
| **Multi-tenancy** | Per-tenant data isolation, plan-driven feature flags, super-admin impersonation |
| **Knowledge base** | Website crawling/ingestion + embeddings, real-time CMS webhooks (Shopify/WooCommerce) |

---

## 3. Architecture overview

```
                          ┌─────────────────────────────────────────────┐
                          │                  Nginx (TLS)                 │
                          │  / → landing   /admin,/portal → SPA  /api,/ws │
                          └───────────────┬──────────────────────────────┘
                                          │
              ┌───────────────────────────┼────────────────────────────┐
              │                           │                            │
     ┌────────▼─────────┐      ┌──────────▼───────────┐     ┌──────────▼──────────┐
     │  Vue 3 SPAs      │      │  Daphne (ASGI)       │     │  Static / widget    │
     │  admin + portal  │◄────►│  Django + Channels   │     │  embed.js / widget  │
     └──────────────────┘      └──────────┬───────────┘     └─────────────────────┘
                                          │
        ┌─────────────────┬───────────────┼───────────────┬─────────────────┐
        │                 │               │               │                 │
 ┌──────▼──────┐  ┌───────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐  ┌───────▼──────┐
 │ PostgreSQL  │  │  Redis       │ │  Celery     │ │  LLM APIs   │  │  Stripe      │
 │ + pgvector  │  │ (broker/WS)  │ │  + Beat     │ │ OpenAI/etc. │  │  billing     │
 └─────────────┘  └──────────────┘ └─────────────┘ └─────────────┘  └──────────────┘
```

- **ASGI / Daphne** runs Django + **Channels** so the same process serves REST **and** WebSockets.
- **Redis** is both the Channels layer (real-time fan-out) and the Celery broker.
- **PostgreSQL + pgvector** stores app data and the RAG embedding vectors.
- **Celery + Beat** handle async/scheduled work (FOMO nudges, outcome tagging, monthly invoices, etc.).

---

## 4. Tech stack

**Backend**
- Python 3.11+, **Django 4.2**, Django REST Framework, SimpleJWT (auth)
- **Django Channels** + `channels-redis` (WebSockets)
- **Celery** + `django-celery-beat` (Redis broker)
- **PostgreSQL** + **pgvector** (`psycopg2`)
- **LangChain** (+ OpenAI / community integrations) for RAG and LLM orchestration
- `sentence-transformers`, `beautifulsoup4`, `playwright`, `lxml` (scraping/embeddings)
- **Stripe** (billing), **WeasyPrint** (invoice PDFs), **WhiteNoise** (static)

**Frontend**
- **Vue 3** + **Vite** (two SPAs: admin + tenant portal) and a standalone embeddable widget
- Vanilla-JS widget loader/embed bundle (no framework on the customer's site)

**Infra**
- Nginx + Let's Encrypt, Daphne + Celery under systemd, Docker/Compose for local parity

---

## 5. Repository structure

```
.
├── checkfunnel/              # Django project config (settings, ASGI, routing, Celery)
│   ├── settings.py           #   base settings (env-driven)
│   ├── settings_prod.py      #   production overrides (HTTPS, CORS, CSRF, logging)
│   ├── asgi.py / routing.py  #   ASGI entrypoint + WebSocket URL routing
│   ├── celery.py             #   Celery app + beat schedule wiring
│   ├── urls.py               #   root URL conf (mounts each app's API)
│   ├── widget_views.py       #   serves /widget/widget.js and /widget/embed.js
│   └── health_views.py       #   /api/health/ endpoint
│
├── chat/                     # 💬 Core conversation engine (see §6)
├── users/                    # 👤 Tenants, auth, billing, admin APIs (see §6)
├── scraper/                  # 🕷️ Knowledge-base crawling + embeddings (see §6)
├── analytics/                # 📊 Event tracking + analytics APIs (see §6)
│
├── widget-vue/               # 🖥️ Frontend — Vue 3 SPAs + embeddable widget (see §7)
│   ├── src/admin/            #   super-admin SPA views
│   ├── src/portal/           #   tenant portal SPA views
│   ├── src/components/       #   shared components (incl. ChatWidget)
│   ├── src/composables/      #   useAdminApi, useTheme, useToast, useTracker, …
│   ├── admin.html / index.html
│   └── vite.*.config.js      #   3 builds: admin SPA, widget, embed loader
│
├── admin-panel/              # (legacy/auxiliary admin assets)
├── widget/                   # legacy widget assets
├── docs/                     # integration guides, security/QA reports
├── nginx/                    # nginx conf templates
├── ops/                      # backup / restore / deploy / cron scripts
├── deploy.sh                 # one-shot deploy script (migrate, seed, build, collectstatic, restart)
├── Dockerfile / docker-compose.yml
├── requirements.txt
├── conftest.py / pytest.ini  # test configuration
└── manage.py
```

---

## 6. Backend apps in depth

### `chat/` — the conversation engine
The heart of the product. Handles every inbound message across channels and produces the AI reply.

| File | Responsibility |
|------|----------------|
| `consumers.py` | WebSocket consumer for the live website widget (async) |
| `admin_consumers.py` | WebSocket consumer feeding the admin/portal live inbox |
| `views.py` | REST endpoints: inbound webhooks (WhatsApp/Messenger/Telegram), lead capture, session restore |
| `ai_service.py` | LLM orchestration — builds the prompt, RAG retrieval, multi-provider routing + fallback, vision |
| `ema_engine.py` | Exponential-moving-average scoring of intent / budget / urgency |
| `state_machine.py` | Conversation state transitions (Research → Evaluation → … → Ready-to-buy) |
| `qualification.py` | Lead qualification / Kanban promotion logic |
| `prompt_service.py`, `prompts.py` | System-prompt assembly and versioned prompt templates |
| `tasks.py` | Celery tasks — FOMO nudges, AFK checks, outcome tagging, digests, archiving |
| `phone_utils.py`, `utils.py`, `throttles.py` | Phone normalization, chat-history truncation, rate limits |
| `models.py` | `Visitor`, `ChatSession`, `ProductLinkClick`, `LLMCallLog`, `PromptTemplate`, … |
| `management/commands/` | `run_qa_evaluation`, `run_qa_regression` (AI quality regression suite) |

### `users/` — tenants, auth, billing & admin APIs
| File | Responsibility |
|------|----------------|
| `models.py` | `TenantProfile`, `Plan`, `Client`, `Invoice`, `AddOnPurchase`, feature overrides, … |
| `admin_views.py` | Super-admin + portal APIs: tenants, clients, sessions, analytics, takeover, impersonation |
| `billing_views.py` | Stripe checkout / portal / webhooks, invoices (list/HTML/PDF), add-on purchases |
| `feature_flags.py` | Plan-driven feature gating + usage quotas (`-1` = unlimited convention) |
| `invoice_service.py` | Invoice generation + email (WeasyPrint PDF) |
| `permissions.py` | DRF permission classes (e.g. `IsSuperAdmin`) |
| `serializers.py` | DRF serializers |
| `tasks.py` | Monthly usage reset, lead reports, chat-history digests, monthly invoices |
| `management/commands/` | `seed_plans` (idempotent plan seeder), `send_test_email` |
| `templates/` | Email/invoice HTML templates |

### `scraper/` — knowledge base
| File | Responsibility |
|------|----------------|
| `ingestion.py` | Crawl a tenant's site / Shopify feeds, normalize content (prices, variants, currency) |
| `embeddings.py` | Chunk + embed content into the `pgvector` store |
| `tasks.py` | Async crawl/re-train jobs |
| `management/commands/` | `rescrape_client` |

### `analytics/` — behavioral tracking
Lightweight event ingestion (page views, clicks, exit intent, heatmaps) consumed by the portal's
**Behavior** and **Audience** views and the analytics KPIs.

---

## 7. Frontend in depth

`widget-vue/` produces **three** Vite builds (see `vite.*.config.js`):

1. **Admin/Portal SPA** (`admin.html` → `src/admin-main.js`) — a single Vue Router app serving both:
   - **Super-admin** (`/admin/*`, `src/admin/`): tenant management, plan assignment, God View,
     prompts, backups, platform insights, impersonation.
   - **Tenant portal** (`/portal/*`, `src/portal/`), organized as:
     - **Workspace** — Conversations (Inbox + Live grid), Leads (Table + Board), Audience
     - **Insights** — Dashboard, Behavior, Referrals
     - **Settings** — Channels & Embed, Integrations, Billing
2. **Widget** (`vite.widget.config.js`) — the chat UI that renders on a customer's website.
3. **Embed loader** (`vite.embed.config.js`) — the tiny `embed.js` snippet customers paste in.

Shared logic lives in `src/composables/` (`useAdminApi` — API client + JWT refresh + impersonation,
`useTheme`, `useToast`, `useConfirm`, `useTracker`). The API base is derived from
`window.location.origin`, so the frontend is domain-agnostic.

---

## 8. How a conversation flows

1. Visitor opens the widget → a **WebSocket** connects to `chat/consumers.py`.
2. The message triggers **RAG retrieval**: relevant chunks of the tenant's content are pulled from
   `pgvector` (cosine distance), with conversation-state-aware retrieval.
3. `ai_service.py` builds a grounded prompt and calls the LLM (tenant's BYOK key or the managed pool,
   with provider fallback).
4. `ema_engine.py` updates intent/budget/urgency scores; `state_machine.py` advances the
   conversation state; the Kanban stage auto-progresses.
5. The reply streams back over the WebSocket and is broadcast to the admin live inbox.
6. A human can **take over** at any time — the AI pauses and admin replies route to the visitor's channel.
7. Celery tasks follow up: FOMO nudges for hot sessions, outcome tagging, monthly invoicing.

---

## 9. Data model (core entities)

- **`TenantProfile`** — a customer account; holds plan, Stripe IDs, usage counters, feature overrides.
- **`Plan`** — subscription tier (limits + feature flags; `-1` means unlimited).
- **`Client`** — a configured chatbot/website belonging to a tenant (branding, channels, KB status).
- **`Visitor`** — a real person, aggregated across sessions (lead email/phone, lifetime stats).
- **`ChatSession`** — one conversation: `chat_history`, `heat_score`, EMA fields, `conversation_state`,
  `kanban_state`, channel, takeover flags, lead contact.
- **`LLMCallLog`** — per-call latency/tokens/cost/provider (powers AI response-time metrics & BYOK billing).
- **`Invoice` / `AddOnPurchase`** — billing records.

---

## 10. Local development setup

> Prerequisites: Python 3.11+, Node 18+, PostgreSQL 14+ with the `pgvector` extension, Redis.

```bash
# 1. Clone & enter
git clone https://github.com/kavinducheckfunnel/Ai-Chat-Bot.git
cd Ai-Chat-Bot

# 2. Backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install            # for the scraper
cp .env.example .env          # then fill in values (see §11)

# 3. Database
#    (ensure Postgres has:  CREATE EXTENSION IF NOT EXISTS vector;)
python manage.py migrate
python manage.py seed_plans   # seed subscription plans
python manage.py createsuperuser

# 4. Run the backend (ASGI — serves REST + WebSockets)
python manage.py runserver        # dev
# or: daphne checkfunnel.asgi:application

# 5. Background workers (separate terminals)
celery -A checkfunnel worker -l info
celery -A checkfunnel beat   -l info

# 6. Frontend
cd widget-vue
npm install
npm run dev                       # Vite dev server (proxies API to :8000)
# production build:  npm run build
```

> 🐳 Alternatively, `docker-compose up` brings up the full stack (web, db, redis, worker) for parity.

---

## 11. Environment variables

Copy `.env.example` → `.env`. Key variables:

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Django secret (required in prod) |
| `DJANGO_SETTINGS_MODULE` | `checkfunnel.settings` (dev) / `checkfunnel.settings_prod` (prod) |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` | Host/security config |
| `BACKEND_PUBLIC_URL` | Absolute origin used for links embedded in emails |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_HOST` | Database |
| `REDIS_URL`, `REDIS_CACHE_URL` | Celery broker + Channels layer |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Managed-AI pool keys (tenants may BYOK) |
| `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` / `STRIPE_WEBHOOK_SECRET` | Billing |
| `STRIPE_PORTAL_RETURN_URL` | Where Stripe returns after checkout/portal |
| `EMAIL_HOST` / `EMAIL_HOST_USER` / `DEFAULT_FROM_EMAIL` | Transactional email (SMTP) |

> ⚠️ Never commit real secrets. `.env` is git-ignored; `.env.example` documents the shape.

---

## 12. Background jobs (Celery)

Scheduled via `CELERY_BEAT_SCHEDULE` in `checkfunnel/settings.py`:

| Task | Schedule | Purpose |
|------|----------|---------|
| `chat.tasks.trigger_fomo_for_hot_sessions` | every 10 min | Proactive nudges to hot sessions |
| `chat.tasks.check_afk_sessions` | every 2 min | Re-engage idle visitors |
| `chat.tasks.tag_session_outcomes` | every 15 min | Tag stale sessions with outcomes (KPIs) |
| `chat.tasks.send_daily_digest` | daily 08:00 | Daily summary email |
| `users.tasks.reset_monthly_sessions` | monthly | Reset usage counters |
| `users.tasks.send_monthly_invoices` | monthly | Generate + email invoices |
| `users.tasks.send_monthly_lead_reports` / `send_monthly_chat_history_report` | monthly | Reports |

---

## 13. Testing & QA

```bash
pytest                              # full backend test suite (see pytest.ini / conftest.py)
python manage.py run_qa_regression  # AI conversation-quality regression suite
python manage.py run_qa_evaluation  # scored evaluation against fixtures (chat/qa_fixtures/)
```

Tests use a dedicated `checkfunnel/test_settings.py`. QA fixtures live in `chat/qa_fixtures/`.

---

## 14. Deployment

Production runs on a VPS behind Nginx + Let's Encrypt, with Daphne and Celery managed by systemd.

```bash
# from the server, in the project dir:
git pull origin main
venv/bin/python manage.py migrate --noinput
venv/bin/python manage.py seed_plans
cd widget-vue && npm ci && npm run build && cd ..
venv/bin/python manage.py collectstatic --noinput
systemctl restart checkfunnel-daphne checkfunnel-celery checkfunnel-celerybeat
```

`deploy.sh` wraps this sequence. Nginx routes: `/` → marketing landing, `/admin` & `/portal` →
the SPA (`admin.html`), `/api` & `/ws` → Daphne, `/static` & `/assets` → built files.

---

## 15. Useful management commands

| Command | What it does |
|---------|--------------|
| `python manage.py seed_plans` | Idempotently create/update subscription plans (source of truth for tiers) |
| `python manage.py rescrape_client <id>` | Re-crawl & re-embed a client's knowledge base |
| `python manage.py send_test_email` | Verify SMTP configuration |
| `python manage.py run_qa_regression` | Run the AI quality regression suite |

---

<div align="center">

**GrowMiq / Checkfunnel** — built with Django, Vue, and a lot of real-time plumbing.

</div>
