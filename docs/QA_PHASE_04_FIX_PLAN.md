# QA Phase 04 — Fix & Test Plan

Tracking doc for the QA Phase 04 issues (`Current_Development_Issues_Report(QA Phase 04).csv`)
plus the Reports Dashboard Metrics Brief. Grounded in the current codebase.

**Decisions (locked):**
- Large lists: **infinite scroll** (`{count, next, results}` on `/sessions/`).
- Kanban: **add missing columns** — New → Engaged → Qualified → Hot Lead → Ready to Buy → Converted → Lost; empty/None → New.
- Takeover media: **images + files + voice + deliver to WhatsApp/Messenger** (Meta media APIs).
- Lead capture: **detect silently + gentle ask** (popup removed).

---

## Key code facts

- 200 cap is server-side: `client_sessions` `qs[:200]` (`users/admin_views.py:667`). Conversations **and** Leads tables both read `/sessions/`.
- `ChatSession.channel` exists (`website|whatsapp|messenger|telegram`, `chat/models.py:167`) but no filter param; **Instagram missing** as a value.
- Kanban bug: columns lack `QUALIFIED` / `READY_TO_BUY` → leads in those states vanish (`PortalKanban.vue:164`, set in `ai_service.py:_maybe_promote_kanban`).
- Page Views = 0: analytics sums `behavioral_context['pages_viewed']` (only written on signal); real `AnalyticEvent` `page_view` rows never counted (`admin_views.py:1735`, `analytics/models.py`).
- Visitor mismatch: `client_visitors` returns capped list, no total count (`admin_views.py:950`).
- Media: messages are JSON `chat_history` array, no attachment field; admin send is text-only.
- Lead popup: `ChatWidget.vue` `showLeadForm` after 2 msgs; backend has LK-only inline phone, no email.
- Date filters: only presets today/7d/30d/90d; no all-time, no custom range.

---

## Workstreams

### WS-A — Backend foundation (pagination + filtering) [High]
- [ ] Pagination on `/sessions/` → `{count, next, results}`, `limit`+`offset`/cursor.
- [ ] `channel` filter param on `/sessions/` and `/kanban/`.
- [ ] Add `instagram` to `CHANNEL_CHOICES` + migration.
- [ ] Unified date params (`all` + presets + custom `date_from`/`date_to`) across sessions/leads/kanban/visitors/analytics/kpis.
- [ ] Move heat filter into SQL (currently runs after the slice).

### WS-B — Conversations tab [High] (#1,#2,#3,#4,#5)
- [ ] Channel chips (All/Web Chat/WhatsApp/Instagram/Messenger) per screenshot.
- [ ] `timeAgo()` fix: <60m→m, <24h→h, ≥24h→d, ≥7d→date (shared helper).
- [ ] All Chats infinite scroll + true total (remove 200).
- [ ] Live View redesign to screenshot (heat%, state, intent/budget/urgency bars, msgs, filters); paginate.
- [ ] Takeover media (#3):
  - [ ] Backend: `attachments[]` on messages, upload endpoint, REST + WS send paths.
  - [ ] Widget + portal render image/voice/file bubbles; voice recorder/player.
  - [ ] Outbound delivery to WhatsApp/Messenger media APIs.

### WS-C — Leads & Kanban [High/Med] (#6,#8)
- [ ] All Leads infinite scroll (drop limit:200).
- [ ] Kanban: add Qualified + Ready to Buy columns; normalize unknown/empty/None → New.

### WS-D — Audience & Behavior [High] (#7,#11)
- [ ] `client_visitors`: add `total_count`, paginate, header reads total.
- [ ] Page views from `AnalyticEvent` (page_view/pricing_visit/exit_intent); verify widget emits beacons.

### WS-E — Dashboard/Reports metrics rework [High] (#9,#10)
- [ ] Overview tab → brief formulas + proper Lead Funnel staging.
- [ ] Chats tab → + Avg First Response, Peak Hours, AI/Human/Missed daily split, Handling breakdown, Avg msgs/chat.
- [ ] Leads tab (new/expanded) → all brief metrics + funnel trend.
- [ ] Engagement tab → page views fixed + all brief metrics.
- [ ] Backend: per-message timestamps (first response, peak hours), hour/day grouping in analytics.
- [ ] Global filter component (All-Time + presets + custom range) on every tab.

### WS-F — Integrations UI [Med] (#12)
- [ ] Rebuild card grid to screenshot (sizing/spacing/alignment/status pill/action). CSS only.

### WS-G — Frictionless lead capture [High] (#13)
- [ ] Remove popup (`showLeadForm` + trigger).
- [ ] Inline email + general phone detection/validation/save + Kanban promote.
- [ ] AI prompt: gentle single ask at high intent.

---

## Execution order
1. WS-A (foundation).
2. Quick wins: #2 time, #11/#7 page views/visitors, #8 kanban.
3. #1/#4/#5 channel+pagination+live view, #6 leads.
4. WS-E metrics + global filters.
5. WS-F integrations CSS.
6. WS-G lead capture.
7. WS-B #3 media takeover (largest; sub-staged, web before Meta delivery).

---

## Testing (A–Z)
Extend the existing **207-test suite** (see memory: project_test_setup).

**Backend:** pagination (count/cursor/no dupes >200/>500); channel filter each value + `all`; date boundaries (tz, inclusive, all-time, custom); kanban every state → exactly one column; page views from seeded events; visitor total_count == DB count; each brief formula unit-tested (resolution/capture/conversion rate, first response, peak hours, breakdown=100%); inline capture valid/invalid/multi email+phone (LK+intl), idempotent; media upload/attach/retrieve + reject oversized/bad MIME.

**Frontend/E2E:** channel chips + date re-query; infinite scroll >200 no dupes; timeAgo buckets; Live View visual diff vs mockup; kanban shows previously-missing cards; audience count==cards; behavior page views non-zero; every Reports metric renders (no N/A) and reacts to global filter; integrations grid desktop+mobile; no popup + inline capture visible in Leads; media takeover round-trip.

**Regression:** full 207 green before/after; plan-gating intact; impersonation/plan persistence intact; multi-tenant isolation on new params; mobile responsive; VPS smoke test on growmiq.io.
