/**
 * Generates a fully self-contained chat widget embed snippet.
 *
 * HYBRID APPROACH — best of both worlds:
 *   - All HTML/CSS/JS inline → no external script dependency, works behind
 *     CSP / caching plugins / security plugins / ad-blockers / Hostinger / etc.
 *   - CSS variables for color → can update at runtime without re-rendering
 *   - Config fetched from API on load + polled every 60s → branding (color,
 *     chatbot name, CTA, voice/image flags) updates LIVE without re-paste.
 *   - Lightweight behavioral tracker built in → feeds EMA scoring backend.
 *   - WebSocket chat, lead capture, reactions, voice/image, chime — all here.
 *
 * Lives in a plain .js file so the Vue SFC tokeniser never sees <style>,
 * </style>, <script>, </script> etc. as real HTML tags.
 */

export function generateEmbedCode(id, url, color, botName, format) {
  if (!id || !url) return ''

  // Backend origin = WIDGET_URL with the /widget/widget.js suffix stripped.
  const backend = url.replace(/\/widget\/widget\.js.*$/, '').replace(/\/$/, '')
  const name = (botName || 'AI Assistant').replace(/'/g, "\\'")
  const defaultColor = color || '#6366f1'

  const css = `<style>
#cf-w {
  --cf-accent: ${defaultColor};
  --cf-bg: #111111;
  --cf-bg-elev: #161616;
  --cf-bubble-ai: #1e2433;
  --cf-text: #e2e8f0;
  --cf-text-strong: #f1f5f9;
  --cf-text-muted: #64748b;
  --cf-border: rgba(255,255,255,0.07);
  --cf-border-soft: rgba(255,255,255,0.06);
}
#cf-w * { box-sizing: border-box; margin: 0; padding: 0; }
#cf-w {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, sans-serif;
  position: fixed; bottom: 24px; right: 24px;
  z-index: 2147483647; display: flex; flex-direction: column; align-items: flex-end;
}

/* ── Pill bar ── */
#cf-pill { display: flex; align-items: center; gap: 10px;
  padding: 9px 11px 9px 9px; background: rgba(17,17,17,0.97);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.08); border-radius: 100px; cursor: pointer;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5); transition: transform .2s, box-shadow .2s;
  min-width: 220px; user-select: none;
  animation: cf-pi .3s cubic-bezier(.34,1.56,.64,1) forwards; }
@keyframes cf-pi { from { opacity: 0; transform: translateY(12px) scale(.95); }
  to { opacity: 1; transform: translateY(0) scale(1); } }
#cf-pill:hover { transform: translateY(-2px); box-shadow: 0 12px 40px rgba(0,0,0,0.55); }
.cf-pi-icon { width: 32px; height: 32px; border-radius: 50%;
  background: var(--cf-accent); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.cf-pi-txt { flex: 1; font-size: 13px; color: rgba(255,255,255,0.4); font-weight: 400; white-space: nowrap; }
.cf-pi-send { width: 30px; height: 30px; border-radius: 50%;
  background: var(--cf-accent); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }

/* ── Chat window ── */
#cf-win { position: absolute; bottom: 0; right: 0; width: 370px;
  background: var(--cf-bg); border-radius: 20px;
  border: 1px solid var(--cf-border); box-shadow: 0 24px 64px rgba(0,0,0,0.65);
  display: none; flex-direction: column; overflow: hidden; max-height: 600px; }
#cf-win.open { display: flex; animation: cf-wi .28s cubic-bezier(.34,1.56,.64,1) forwards; }
@keyframes cf-wi { from { opacity: 0; transform: translateY(14px) scale(.97); }
  to { opacity: 1; transform: translateY(0) scale(1); } }

/* ── Header ── */
#cf-head { background: var(--cf-bg-elev); border-bottom: 1px solid var(--cf-border-soft);
  padding: 13px 15px; display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.cf-av { width: 36px; height: 36px; border-radius: 50%; background: var(--cf-accent);
  display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; color: #fff; }
.cf-hi { flex: 1; min-width: 0; }
.cf-hn { font-size: 14px; font-weight: 600; color: var(--cf-text-strong); letter-spacing: -.2px; }
.cf-hs { font-size: 11px; color: var(--cf-text-muted); display: flex; align-items: center; gap: 4px; margin-top: 2px; }
.cf-dot { width: 6px; height: 6px; border-radius: 50%; background: #4ade80; flex-shrink: 0; }
#cf-xb { background: rgba(255,255,255,0.06); border: none; color: #94a3b8;
  width: 28px; height: 28px; border-radius: 50%; cursor: pointer; font-size: 16px;
  display: flex; align-items: center; justify-content: center; transition: background .15s;
  padding: 0; line-height: 1; }
#cf-xb:hover { background: rgba(255,255,255,0.12); color: var(--cf-text-strong); }

/* ── Messages — clean conversation UI, reactions as crisp icon chips inside the bubble ── */
#cf-msgs { flex: 1; overflow-y: auto; padding: 16px 14px;
  display: flex; flex-direction: column; gap: 10px; background: var(--cf-bg);
  min-height: 180px; max-height: 340px;
  scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.1) transparent; }
#cf-msgs::-webkit-scrollbar { width: 4px; }
#cf-msgs::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }

/* All chat-message selectors are scoped to #cf-w so they beat the universal
   #cf-w * { padding: 0 } reset on specificity — without this prefix, the
   reset wins and bubble padding silently collapses to 0. */
#cf-w .cf-ai, #cf-w .cf-me { padding: 12px 17px; border-radius: 19px; font-size: 14px;
  line-height: 1.5; max-width: 82%; animation: cf-mi .22s ease; word-break: break-word;
  box-shadow: 0 1px 2px rgba(0,0,0,0.18); }
@keyframes cf-mi { from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); } }
#cf-w .cf-ai { background: var(--cf-bubble-ai); color: var(--cf-text);
  align-self: flex-start; border-bottom-left-radius: 6px; border: 1px solid var(--cf-border-soft); }
#cf-w .cf-me { background: var(--cf-accent); color: #fff;
  align-self: flex-end; border-bottom-right-radius: 6px; }
#cf-w .cf-img-msg { align-self: flex-end; max-width: 180px; border-radius: 14px;
  object-fit: cover; display: block; border: 1px solid rgba(255,255,255,0.08); }

#cf-w .cf-ai ol { margin: 6px 0 4px 0; padding-left: 20px; list-style-type: decimal; }
#cf-w .cf-ai li { margin-bottom: 6px; color: var(--cf-text); line-height: 1.5; display: list-item; }
#cf-w .cf-ai li:last-child { margin-bottom: 2px; }
#cf-w .cf-ai p { margin: 0 0 6px 0; color: var(--cf-text); }
#cf-w .cf-ai p:last-child { margin-bottom: 0; }
#cf-w .cf-ai a { color: #a5b4fc; text-decoration: underline; font-weight: 500; word-break: break-word; }
#cf-w .cf-ai a:hover { color: #c4b5fd; }
#cf-w .cf-ai strong { color: var(--cf-text-strong); font-weight: 700; }

/* ── Reactions — crisp 26px circular icon chips, clearly visible against bubble bg ── */
#cf-w .cf-rxn { display: flex; gap: 6px; margin-top: 10px; }
#cf-w .cf-rb {
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 50%;
  width: 26px; height: 26px;
  padding: 0;
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background .15s, border-color .15s, transform .12s;
  color: rgba(255,255,255,0.85);
  font-family: 'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', sans-serif;
}
#cf-w .cf-rb:hover { background: rgba(255,255,255,0.13); border-color: rgba(255,255,255,0.2); transform: translateY(-1px); }
#cf-w .cf-rb.on { background: rgba(99,102,241,0.25); border-color: rgba(99,102,241,0.55); }

/* ── Typing — also scoped to win over the universal padding reset ── */
#cf-w .cf-typ { align-self: flex-start; background: var(--cf-bubble-ai);
  border: 1px solid var(--cf-border-soft); border-radius: 20px;
  border-bottom-left-radius: 6px; padding: 13px 16px; display: flex; gap: 5px; align-items: center; }
#cf-w .cf-qrs { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 2px 8px 2px; align-self: flex-start; max-width: 92%; }
#cf-w .cf-qr { background: transparent; color: var(--cf-accent, #6366f1); border: 1px solid currentColor; border-radius: 16px; padding: 6px 12px; font-size: 12px; font-weight: 500; cursor: pointer; transition: all 0.15s; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
#cf-w .cf-qr:hover { background: var(--cf-accent, #6366f1); color: #fff; }
.cf-typ span { width: 7px; height: 7px; background: #475569; border-radius: 50%;
  display: inline-block; animation: cf-bop 1.3s infinite ease-in-out; }
.cf-typ span:nth-child(2) { animation-delay: .18s; }
.cf-typ span:nth-child(3) { animation-delay: .36s; }
@keyframes cf-bop { 0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); } }

/* ── Image preview ── */
#cf-imgprev { padding: 8px 13px 0; background: var(--cf-bg); display: none; }
#cf-imgprev.has-img { display: block; }
.cf-prev-wrap { position: relative; display: inline-block; }
.cf-prev-thumb { width: 52px; height: 52px; border-radius: 8px; object-fit: cover;
  display: block; border: 1px solid rgba(255,255,255,0.1); }
.cf-prev-rm { position: absolute; top: -5px; right: -5px; width: 17px; height: 17px;
  border-radius: 50%; background: var(--cf-accent); border: none; color: white;
  font-size: 10px; cursor: pointer; display: flex; align-items: center; justify-content: center; line-height: 1; }

/* ── Input ── */
#cf-foot { display: flex; gap: 7px; padding: 10px 12px; background: var(--cf-bg-elev);
  border-top: 1px solid var(--cf-border-soft); flex-shrink: 0; align-items: center; }
.cf-mb { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
  color: var(--cf-text-muted); width: 34px; height: 34px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  padding: 0; transition: all .15s; line-height: 1; }
.cf-mb:hover { background: rgba(255,255,255,0.1); color: #94a3b8; }
.cf-mb.rec { background: rgba(239,68,68,0.15); border-color: rgba(239,68,68,0.4);
  color: #f87171; animation: cf-prec 1s ease-in-out infinite; }
@keyframes cf-prec { 0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.3); }
  50% { box-shadow: 0 0 0 5px transparent; } }
#cf-inp { flex: 1; padding: 9px 14px; border: 1px solid rgba(255,255,255,0.08);
  border-radius: 20px; outline: none; font-size: 13px; font-family: inherit;
  background: rgba(255,255,255,0.05); color: var(--cf-text);
  transition: border-color .2s, background .2s; }
#cf-inp:focus { border-color: rgba(99,102,241,0.4); background: rgba(255,255,255,0.07); }
#cf-inp::placeholder { color: rgba(255,255,255,0.25); }
#cf-inp:disabled { opacity: .5; cursor: not-allowed; }
#cf-sb { width: 36px; height: 36px; border-radius: 50%; background: var(--cf-accent);
  border: none; color: #fff; cursor: pointer; display: flex;
  align-items: center; justify-content: center; padding: 0;
  transition: opacity .15s, transform .15s; line-height: 1; }
#cf-sb:hover:not(:disabled) { opacity: .85; transform: scale(1.07); }
#cf-sb:disabled { opacity: .3; cursor: not-allowed; }
#cf-pby { text-align: center; font-size: 10px; color: rgba(255,255,255,0.2);
  padding: 5px 0 7px; background: var(--cf-bg-elev); }
#cf-pby a { color: rgba(255,255,255,0.3); text-decoration: none; }

/* ── Inline lead capture — slides up INSIDE the chat panel ─────── */
#cf-lead { padding: 13px 14px 14px;
  border-top: 1px solid var(--cf-border-soft);
  background: var(--cf-bg-elev);
  display: none; animation: cf-leadslide .28s cubic-bezier(.34,1.56,.64,1); }
#cf-lead.show { display: block; }
@keyframes cf-leadslide { from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); } }
.cf-lead-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 9px; }
.cf-lead-ttl { font-size: 13px; font-weight: 600; color: var(--cf-text-strong); letter-spacing: -.1px; }
#cf-lead-cls { background: rgba(255,255,255,0.06); border: none; color: var(--cf-text-muted);
  cursor: pointer; padding: 0; font-size: 11px; line-height: 1;
  display: flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border-radius: 50%;
  transition: background .15s; }
#cf-lead-cls:hover { background: rgba(255,255,255,0.12); color: var(--cf-text-strong); }
.cf-lead-row { display: flex; gap: 7px; align-items: stretch; }
.cf-lead-inp { flex: 1; padding: 10px 14px; height: 38px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 19px; font-size: 13px; color: var(--cf-text);
  outline: none; box-sizing: border-box; font-family: inherit; line-height: 1.3;
  transition: border-color .15s, background .15s;
  /* Prevent browser autofill from painting the input white on dark themes */
  -webkit-text-fill-color: var(--cf-text); }
.cf-lead-inp:focus { border-color: var(--cf-accent); background: rgba(255,255,255,0.09); }
.cf-lead-inp::placeholder { color: rgba(255,255,255,0.55); opacity: 1; }
/* Kill the yellow/white autofill background so the dark theme stays dark.
   The inset box-shadow trick is how WebKit lets us override autofill bg. */
.cf-lead-inp:-webkit-autofill,
.cf-lead-inp:-webkit-autofill:hover,
.cf-lead-inp:-webkit-autofill:focus,
.cf-lead-inp:-webkit-autofill:active {
  -webkit-text-fill-color: var(--cf-text) !important;
  -webkit-box-shadow: 0 0 0 1000px var(--cf-bg-elev) inset !important;
  caret-color: var(--cf-text) !important;
  transition: background-color 5000s ease-in-out 0s;
}
.cf-lead-btn { background: var(--cf-accent); border: none; border-radius: 19px;
  padding: 0 20px; height: 38px; min-width: 78px;
  font-size: 13px; font-weight: 600; color: #fff;
  cursor: pointer; font-family: inherit; transition: opacity .15s, transform .1s;
  white-space: nowrap; box-sizing: border-box;
  display: inline-flex; align-items: center; justify-content: center; }
.cf-lead-btn:hover:not(:disabled) { opacity: .88; transform: translateY(-1px); }
.cf-lead-btn:disabled { opacity: .5; cursor: not-allowed; }
/* Full-width Send on its own row — keeps email + phone fields aligned to
   the same width instead of the phone field being shortened by the button. */
.cf-lead-btn-full { width: 100%; margin-top: 9px; }
/* +94 country-code affix on the phone row */
.cf-lead-cc { display: inline-flex; align-items: center; justify-content: center;
  height: 38px; padding: 0 11px; flex-shrink: 0;
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
  border-radius: 19px; font-size: 13px; font-weight: 600; color: var(--cf-text-muted);
  box-sizing: border-box; }
.cf-lead-ph { letter-spacing: .5px; }
.cf-lead-err { font-size: 11px; color: #f87171; min-height: 0; margin: 4px 2px 0;
  line-height: 1.4; }
#cf-w[data-cf-theme="light"] .cf-lead-cc { background: #f1f5f9; border-color: #e2e8f0; color: #64748b; }

/* Inline lead capture — LIGHT theme */
#cf-w[data-cf-theme="light"] .cf-lead-inp {
  background: #f8fafc; border-color: #e2e8f0; color: #1e293b;
  -webkit-text-fill-color: #1e293b;
}
#cf-w[data-cf-theme="light"] .cf-lead-inp::placeholder { color: #94a3b8; opacity: 1; }
#cf-w[data-cf-theme="light"] .cf-lead-inp:focus { background: #ffffff; }
#cf-w[data-cf-theme="light"] .cf-lead-inp:-webkit-autofill,
#cf-w[data-cf-theme="light"] .cf-lead-inp:-webkit-autofill:hover,
#cf-w[data-cf-theme="light"] .cf-lead-inp:-webkit-autofill:focus {
  -webkit-text-fill-color: #1e293b !important;
  -webkit-box-shadow: 0 0 0 1000px #f8fafc inset !important;
  caret-color: #1e293b !important;
}

/* ── LIGHT THEME OVERRIDES (applied when data-cf-theme="light" on #cf-w) ── */
#cf-w[data-cf-theme="light"] {
  --cf-bg: #ffffff;
  --cf-bg-elev: #f8fafc;
  --cf-bubble-ai: #f1f5f9;
  --cf-text: #1e293b;
  --cf-text-strong: #0f172a;
  --cf-text-muted: #64748b;
  --cf-border: #e2e8f0;
  --cf-border-soft: #f1f5f9;
}
#cf-w[data-cf-theme="light"] #cf-pill { background: rgba(255,255,255,0.97);
  border: 1px solid #e2e8f0; box-shadow: 0 8px 32px rgba(0,0,0,0.10); }
#cf-w[data-cf-theme="light"] .cf-pi-txt { color: #64748b; }
#cf-w[data-cf-theme="light"] #cf-win { box-shadow: 0 24px 64px rgba(0,0,0,0.15); }
#cf-w[data-cf-theme="light"] #cf-xb { background: #f1f5f9; color: #475569; }
#cf-w[data-cf-theme="light"] #cf-xb:hover { background: #e2e8f0; color: #1e293b; }
#cf-w[data-cf-theme="light"] #cf-inp { background: #f8fafc; border-color: #e2e8f0; color: #1e293b; }
#cf-w[data-cf-theme="light"] #cf-inp::placeholder { color: #94a3b8; }
#cf-w[data-cf-theme="light"] #cf-pby { color: #94a3b8; }
#cf-w[data-cf-theme="light"] #cf-pby a { color: #64748b; }
#cf-w[data-cf-theme="light"] .cf-mb { background: #f1f5f9; border-color: #e2e8f0; color: #64748b; }
#cf-w[data-cf-theme="light"] .cf-mb:hover { background: #e2e8f0; color: #1e293b; }
/* Light-mode AI bubble — needs visible border since bg = border var by default */
#cf-w[data-cf-theme="light"] .cf-ai { background: #f1f5f9; border-color: #e2e8f0; color: #1e293b; }
#cf-w[data-cf-theme="light"] .cf-ai p { color: #1e293b; }
#cf-w[data-cf-theme="light"] .cf-ai li { color: #1e293b; }
#cf-w[data-cf-theme="light"] .cf-ai strong { color: #0f172a; }
#cf-w[data-cf-theme="light"] .cf-ai a { color: #4338ca; }
#cf-w[data-cf-theme="light"] .cf-rb { background: #ffffff; border-color: #d8dee9; }
#cf-w[data-cf-theme="light"] .cf-rb:hover { background: #f1f5f9; border-color: #94a3b8; }
#cf-w[data-cf-theme="light"] .cf-rb.on { background: rgba(99,102,241,0.15); border-color: rgba(99,102,241,0.55); }
#cf-w[data-cf-theme="light"] .cf-typ { background: #f1f5f9; border-color: #e2e8f0; }
#cf-w[data-cf-theme="light"] .cf-typ span { background: #94a3b8; }

/* ── Mobile responsive ────────────────────────────────────────────────
   Before this block the widget was unusable on phones:
     • #cf-win was width:370px → overflowed 360-390px viewports
     • #cf-pill at bottom:24px landed under the iOS home-indicator
     • Nothing accounted for env(safe-area-inset-*) on notched devices
   Now everything respects the visible viewport plus the safe-area
   insets — pill stays reachable, full chat window fits on screen,
   and message scroll area sizes to the available height. */
@media (max-width: 480px) {
  #cf-w {
    bottom: max(12px, env(safe-area-inset-bottom, 12px));
    right: max(8px, env(safe-area-inset-right, 8px));
    left: max(8px, env(safe-area-inset-left, 8px));
    align-items: flex-end;
  }
  #cf-pill {
    min-width: 0;
    max-width: 100%;
    padding: 11px 13px 11px 10px;
  }
  /* The chat window now anchors to all four edges so it occupies the
     full mobile viewport when open — Stripe Checkout / Tidio / Drift
     all do the same on phones because side-anchored 370px popups
     blow off-screen on iPhone SE-class devices. */
  #cf-win {
    position: fixed;
    bottom: max(12px, env(safe-area-inset-bottom, 12px));
    left: max(8px, env(safe-area-inset-left, 8px));
    right: max(8px, env(safe-area-inset-right, 8px));
    width: auto;
    max-height: calc(100vh - 24px - env(safe-area-inset-top, 0px));
    max-height: calc(100dvh - 24px - env(safe-area-inset-top, 0px));
    border-radius: 16px;
  }
  /* Header / input padding tightens on phones — no horizontal scroll. */
  #cf-head { padding: 11px 13px; }
  /* Messages area uses the rest of the viewport, capped so the input
     bar always stays visible above the on-screen keyboard. */
  #cf-msgs {
    padding: 12px 11px;
    max-height: none;
    /* Keep room for header (≈58px) + input (≈64px) + powered-by (≈22px). */
    min-height: 120px;
  }
  /* Lead-capture overlay must also fit small screens. */
  .cf-lead-card {
    left: 8px !important;
    right: 8px !important;
    width: auto !important;
  }
}

/* Notched iOS — add safe-area cushioning even on larger viewports so
   the floating pill never collides with the home indicator. */
@supports (padding: env(safe-area-inset-bottom)) {
  #cf-w { padding-bottom: env(safe-area-inset-bottom, 0px); }
}
</style>`

  const html = `<div id="cf-w" data-cf-theme="dark">
<div id="cf-win" role="dialog" aria-label="Chat with ${name}">
<div id="cf-head">
<div class="cf-av" id="cf-av">&#9889;</div>
<div class="cf-hi"><div class="cf-hn" id="cf-hn">${name}</div><div class="cf-hs"><span class="cf-dot"></span>Online</div></div>
<button id="cf-xb" aria-label="Close">&#10005;</button>
</div>
<div id="cf-msgs"><div class="cf-ai">&#128075; Hi! How can I help you today?</div></div>
<div id="cf-imgprev"><div class="cf-prev-wrap"><img class="cf-prev-thumb" id="cf-pt" src="" alt=""/><button class="cf-prev-rm" id="cf-prm">&#10005;</button></div></div>
<div id="cf-lead">
  <div class="cf-lead-head">
    <span class="cf-lead-ttl">Want a personalised follow-up?</span>
    <button id="cf-lead-cls" aria-label="Dismiss">&#10005;</button>
  </div>
  <div class="cf-lead-row">
    <input class="cf-lead-inp" id="cf-lead-em" type="email" placeholder="Email address"/>
  </div>
  <div class="cf-lead-row" style="margin-top:7px">
    <span class="cf-lead-cc">+94</span>
    <input class="cf-lead-inp cf-lead-ph" id="cf-lead-ph" type="tel" inputmode="tel" maxlength="20" placeholder="77 123 4567 — or +1, +44…"/>
  </div>
  <button class="cf-lead-btn cf-lead-btn-full" id="cf-lead-sb">Send my details</button>
  <div class="cf-lead-err" id="cf-lead-err"></div>
</div>
<div id="cf-foot">
<input id="cf-fi" type="file" accept="image/*" style="display:none">
<button class="cf-mb" id="cf-ib" style="display:none" title="Attach image">
<svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
</button>
<button class="cf-mb" id="cf-vb" style="display:none" title="Voice input">
<svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
</button>
<input id="cf-inp" type="text" placeholder="Type a message&#8230;" autocomplete="off">
<button id="cf-sb" aria-label="Send" disabled>
<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2" fill="white" stroke="none"/></svg>
</button>
</div>
<div id="cf-pby">Powered by <a href="https://checkfunnels.com" target="_blank" rel="noopener">Checkfunnels</a></div>
</div>
<div id="cf-pill" role="button" aria-label="Open chat" tabindex="0">
<div class="cf-pi-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="white"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg></div>
<span class="cf-pi-txt">Write a message...</span>
<div class="cf-pi-send"><svg width="13" height="13" viewBox="0 0 24 24" fill="white"><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg></div>
</div>
</div>`

  // ───────────── JS (inline, no external dependency) ─────────────────
  // Note: backslashes in regex are double-escaped (\\) because this string
  // lives inside a JS template literal — \\[ produces \[ in the output.
  const js = `<script>
(function(){
var C='${id}',B='${backend}';

// ── Identity persistence ─────────────────────────────────────────────
// session_id (sid)  → a FIRST-PARTY COOKIE (primary) + localStorage (mirror)
//                     so the SAME conversation continues across new tabs,
//                     sub-pages, and reloads. The cookie is the most robust
//                     carrier — it's sent on every same-origin page and
//                     survives some storage-clear edge-cases that break
//                     localStorage-only. 24h rolling TTL: a genuinely new
//                     visit (24h idle) starts a fresh conversation.
// visitor_uid (vid) → localStorage, one per browser across days.
// Both are client-scoped so the same browser visiting different tenants
// never gets merged into one visitor record.
function newUuid(){return'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,function(c){var r=Math.random()*16|0;return(c=='x'?r:(r&3|8)).toString(16)})}
var SK='__cf_sid_'+C;
var STK='__cf_sid_ts_'+C;   // last-active timestamp for the TTL
var VK='__cf_vid_'+C;
var CK='cf_sid_'+C;         // cookie name
var SID_TTL=24*60*60*1000;  // 24h of inactivity → new session
function getCookie(n){
  var parts=(document.cookie||'').split('; ');
  for(var i=0;i<parts.length;i++){
    var eq=parts[i].indexOf('=');
    if(eq>-1&&parts[i].slice(0,eq)===n)return decodeURIComponent(parts[i].slice(eq+1));
  }
  return null;
}
function setSidCookie(v){
  // 24h expiry, Lax so it rides same-origin navigations; Secure on https.
  var exp=new Date(Date.now()+SID_TTL).toUTCString();
  var sec=(location.protocol==='https:')?'; Secure':'';
  try{document.cookie=CK+'='+encodeURIComponent(v)+'; Path=/; Expires='+exp+'; SameSite=Lax'+sec}catch(e){}
}
// Resolve order: cookie → localStorage → new. Fall back gracefully if
// storage is blocked (private mode / disabled cookies).
var sid=getCookie(CK)||(function(){try{return localStorage.getItem(SK)}catch(e){return null}})();
var sidTs=parseInt((function(){try{return localStorage.getItem(STK)}catch(e){return '0'}})()||'0',10);
var sidExpired=(!sidTs||(Date.now()-sidTs)>SID_TTL);
if(!sid||(sidExpired&&!getCookie(CK))){
  // Fresh session: no carrier, or the localStorage TTL lapsed AND the
  // cookie is gone too. Clear the previous transcript so the new
  // conversation doesn't inherit an old one.
  if(sid){try{localStorage.removeItem('cf_msgs_'+sid)}catch(e){}}
  sid=newUuid();
}
try{localStorage.setItem(SK,sid)}catch(e){}
setSidCookie(sid);
function touchSession(){try{localStorage.setItem(STK,String(Date.now()))}catch(e){}setSidCookie(sid)}
touchSession();
var vid=(function(){try{return localStorage.getItem(VK)}catch(e){return null}})();
if(!vid){vid=newUuid();try{localStorage.setItem(VK,vid)}catch(e){}}

var ws=null,busy=false,recording=false,pendingImg=null,recognition=null;
var msgCount=0,liveCtaMsg=null;
var LEAD_KEY='cf_lead_'+C;
var leadDone=!!localStorage.getItem(LEAD_KEY);
var $=function(id){return document.getElementById(id)};

// ── Chat history persistence ─────────────────────────────────────────
// Stored in localStorage keyed by the current sid so the transcript is
// shared across tabs + survives reloads — opening a product link in a new
// tab continues the SAME conversation instead of starting blank. Bounded
// to the most recent 100 messages so the key never grows unbounded.
var MSGS_KEY='cf_msgs_'+sid;
var savedMsgs=[];
try{var _r=localStorage.getItem(MSGS_KEY);if(_r){savedMsgs=JSON.parse(_r)||[]}}catch(e){savedMsgs=[]}
if(!Array.isArray(savedMsgs))savedMsgs=[];

// In-memory mirror so we don't need to scrape the DOM each save
var msgLog=savedMsgs.slice();
function persistMsgs(){
  try{
    var keep=msgLog.length>100?msgLog.slice(msgLog.length-100):msgLog;
    localStorage.setItem(MSGS_KEY,JSON.stringify(keep));
    touchSession();
  }catch(e){}
}

// ── Cross-tab message dedupe ──────────────────────────────────────────
// Every message carries an id (client id for the visitor's own message,
// server id for AI replies). The server fans every message out to ALL open
// tabs in this session; each tab renders an id once, so the sending tab
// doesn't double its optimistic bubble and other tabs sync live.
var seenMsgIds={};
function markSeen(id){if(id)seenMsgIds[id]=1}
function isSeen(id){return !!(id&&seenMsgIds[id])}
function newMsgId(){return 'u_'+Date.now()+'_'+Math.random().toString(36).slice(2,8)}

// ── Live config — applied on load + every 60 seconds ─────────────────
function applyConfig(cfg){
  if(!cfg)return;
  var w=$('cf-w');
  if(cfg.chatbot_color&&w)w.style.setProperty('--cf-accent',cfg.chatbot_color);
  if(cfg.chatbot_name){
    var hn=$('cf-hn');if(hn)hn.textContent=cfg.chatbot_name;
    var win=$('cf-win');if(win)win.setAttribute('aria-label','Chat with '+cfg.chatbot_name);
  }
  if(cfg.chatbot_theme&&w)w.setAttribute('data-cf-theme',cfg.chatbot_theme);
  if(cfg.voice_input_enabled)$('cf-vb').style.display='flex';else $('cf-vb').style.display='none';
  if(cfg.image_input_enabled)$('cf-ib').style.display='flex';else $('cf-ib').style.display='none';
  if(cfg.cta_message)liveCtaMsg=cfg.cta_message;
}
function fetchConfig(){
  fetch(B+'/api/chat/widget-config/'+C+'/').then(function(r){return r.json()}).then(applyConfig).catch(function(){});
}
fetchConfig();
setInterval(fetchConfig,60000);

// ── Markdown renderer (numbered lists, links, bold) ──────────────────
function renderMd(text){
  var links=[];
  var s=text.replace(/\\[([^\\]]+)\\]\\((https?:\\/\\/[^\\s)]+)\\)/g,function(m,t,u){
    var i=links.length;links.push({t:t,u:u});return'__CFL_'+i+'__'
  });
  s=s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  s=s.replace(/__CFL_(\\d+)__/g,function(m,i){
    var l=links[+i],st=l.t.replace(/</g,'&lt;').replace(/>/g,'&gt;');
    // data-cf-plink tags AI-sent links so the delegated click handler can
    // attribute referrals (marketing dashboards). data-cf-pltext carries the
    // visible label for the report.
    var safeTxt=l.t.replace(/"/g,'&quot;');
    return'<a href="'+l.u+'" target="_blank" rel="noopener noreferrer" data-cf-plink="'+l.u+'" data-cf-pltext="'+safeTxt+'">'+st+'</a>'
  });
  s=s.replace(/\\*\\*([^*]+)\\*\\*/g,'<strong>$1</strong>');
  var lines=s.split('\\n'),out=[],inList=false;
  for(var i=0;i<lines.length;i++){
    var line=lines[i].trim();
    var m=line.match(/^(\\d+)\\. +(.+)$/);
    if(m){if(!inList){out.push('<ol>');inList=true}out.push('<li>'+m[2]+'</li>')}
    else{if(inList){out.push('</ol>');inList=false}if(line)out.push('<p>'+line+'</p>')}
  }
  if(inList)out.push('</ol>');
  return out.join('')
}

// ── Lead capture (inline slide-up inside chat panel) ─────────────────
function showLead(){if(leadDone)return;$('cf-lead').classList.add('show')}
function dismissLead(){$('cf-lead').classList.remove('show');leadDone=true;localStorage.setItem(LEAD_KEY,'1')}
// Phone normalisation — keeps +94 (Sri Lanka) as the DEFAULT for bare local
// numbers, but no longer rejects international visitors. Mirrors
// chat.phone_utils.normalize_phone on the client for instant feedback.
function normalizePhone(raw){
  var typedPlus=(raw||'').trim().charAt(0)==='+';
  var d=(raw||'').replace(/\\D/g,'');
  if(!d)return null;
  // 1) Try the LK interpretation first (the default market).
  var lk=d;
  if(lk.indexOf('0094')===0)lk=lk.slice(4);
  if(lk.indexOf('94')===0)lk=lk.slice(2);
  if(lk.length===10&&lk.charAt(0)==='0')lk=lk.slice(1);
  if(lk.length===9&&lk.charAt(0)==='7')return '+94'+lk;
  // 2) International fallback — accept any plausible number so non-LK
  //    visitors can submit. Add + when they typed one or it carries a
  //    country code (length > 10).
  if(d.length>=7&&d.length<=15)return (typedPlus||d.length>10)?('+'+d):d;
  return null;
}
function setLeadErr(msg){var e=$('cf-lead-err');if(e)e.textContent=msg||''}
function submitLead(){
  var em=($('cf-lead-em').value||'').trim();
  if(!em){setLeadErr('Please enter your email.');return}
  if(!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(em)){setLeadErr('Please enter a valid email.');return}
  // Phone is optional. Accepts a local LK number (defaults to +94) or any
  // international number.
  var phRaw=($('cf-lead-ph')?$('cf-lead-ph').value:'')||'';
  var phone=null;
  if(phRaw.trim()){
    phone=normalizePhone(phRaw);
    if(!phone){setLeadErr('Please enter a valid phone number (e.g. 77 123 4567 or +1 555 123 4567).');return}
  }
  setLeadErr('');
  $('cf-lead-sb').disabled=true;$('cf-lead-sb').textContent='…';
  fetch(B+'/api/chat/lead/',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({session_id:sid,email:em,phone:phone})
  }).then(function(r){
    if(r&&!r.ok&&r.status===400){
      // Backend rejected the phone — surface it and let them fix.
      $('cf-lead-sb').disabled=false;$('cf-lead-sb').textContent='Send my details';
      setLeadErr('Please enter a valid phone number.');
      throw new Error('invalid');
    }
    // Just hide the form. We do NOT post a local "we'll be in touch" bubble
    // — the backend pushes an engaging confirmation over the WebSocket that
    // keeps the conversation open ("anything else I can help with?"), so a
    // second local goodbye bubble would both duplicate it and make the chat
    // feel closed.
    dismissLead();
  }).catch(function(){});
}

// ── Chime ────────────────────────────────────────────────────────────
function chime(){if(!isOpen)return;try{var a=new(window.AudioContext||window.webkitAudioContext)();[[880,0],[1100,.14],[1320,.26]].forEach(function(t){var o=a.createOscillator(),g=a.createGain();o.connect(g);g.connect(a.destination);o.type='sine';o.frequency.value=t[0];var st=a.currentTime+t[1];g.gain.setValueAtTime(0,st);g.gain.linearRampToValueAtTime(.09,st+.04);g.gain.exponentialRampToValueAtTime(.001,st+.38);o.start(st);o.stop(st+.38)});setTimeout(function(){a.close()},1400)}catch(e){}}

// ── DOM helpers — EXACT old-code structure: simple divs, reactions inside the AI bubble ──
function renderBubble(html,who){
  var d=document.createElement('div');
  if(who==='img'){
    d.innerHTML='<img class="cf-img-msg" src="'+html+'" alt="image"/>';
    $('cf-msgs').appendChild(d.firstChild);
  }else{
    d.className=who==='ai'?'cf-ai':'cf-me';
    d.innerHTML=html;
    if(who==='ai'){
      var rx=document.createElement('div');rx.className='cf-rxn';
      ['\\uD83D\\uDC4D','\\uD83D\\uDC4E'].forEach(function(e){
        var b=document.createElement('button');b.className='cf-rb';b.textContent=e;
        b.onclick=function(){
          b.classList.toggle('on');
          Array.from(rx.children).forEach(function(x){if(x!==b)x.classList.remove('on')});
        };
        rx.appendChild(b);
      });
      d.appendChild(rx);
    }
    $('cf-msgs').appendChild(d);
  }
  $('cf-msgs').scrollTop=9999;
}
function bubble(html,who){
  renderBubble(html,who);
  msgLog.push({who:who,html:html});
  persistMsgs();
}

// On load: if we have saved (local) messages, paint them immediately so the
// transcript appears instantly — then the server restore below reconciles.
if(savedMsgs.length>0){
  $('cf-msgs').innerHTML='';
  savedMsgs.forEach(function(m){renderBubble(m.html,m.who)});
}

// ── Server-authoritative restore ─────────────────────────────────────
// The server is the source of truth for the conversation. On load we fetch
// the transcript for this sid and, if it has content, RE-RENDER from it.
// This is what makes continuity robust: a product link opened in a NEW TAB
// resolves the same sid (cookie/localStorage) and restores the SAME chat
// from the server even if that tab's local cache is empty. Best-effort —
// on any failure we keep whatever the local cache painted.
var serverRestored=false;
// Connect is gated behind restore so that, if we recover a different session
// by visitor id (Shopify cross-domain hop), the WebSocket opens on the
// RECOVERED sid — not the empty new one.
var connected=false;
function ensureConnect(){if(connected)return;connected=true;connect();}
// Adopt a server-recovered session id: re-point sid + its derived keys and
// persist it so subsequent loads resolve the same conversation.
function adoptSession(newSid){
  if(!newSid||newSid===sid)return;
  try{localStorage.removeItem(MSGS_KEY)}catch(e){}
  sid=newSid;
  MSGS_KEY='cf_msgs_'+sid;
  try{localStorage.setItem(SK,sid)}catch(e){}
  setSidCookie(sid);
}
function renderServerMsgs(messages){
  serverRestored=true;
  $('cf-msgs').innerHTML='';
  msgLog.length=0;
  messages.forEach(function(m){
    var who=(m.role==='user')?'me':'ai';
    var html=(who==='ai')?renderMd(m.message):'<p>'+escHtml(m.message)+'</p>';
    renderBubble(html,who);
    msgLog.push({who:who,html:html});
  });
  persistMsgs();
  if(typeof msgCount!=='undefined'){
    // Count visitor turns so the inline lead-capture trigger stays accurate.
    msgCount=messages.filter(function(m){return m.role==='user'}).length;
  }
  $('cf-msgs').scrollTop=9999;
}
function restoreFromServer(){
  if(serverRestored){ensureConnect();return;}
  fetch(B+'/api/chat/session/'+encodeURIComponent(sid)+'/messages/?limit=50')
    .then(function(r){return r.ok?r.json():null})
    .then(function(d){
      if(d&&Array.isArray(d.messages)&&d.messages.length){
        renderServerMsgs(d.messages);ensureConnect();return null;
      }
      // This sid has no history. Try the stable visitor id — survives the
      // Shopify case where the sid cookie/localStorage was lost crossing
      // between the custom domain and *.myshopify.com / checkout.
      return fetch(B+'/api/chat/visitor/'+C+'/'+encodeURIComponent(vid)+'/latest/')
        .then(function(r){return r.ok?r.json():null})
        .then(function(v){
          if(v&&v.session_id&&Array.isArray(v.messages)&&v.messages.length){
            adoptSession(v.session_id);
            renderServerMsgs(v.messages);
          }
          ensureConnect();
        });
    })
    .catch(function(){ensureConnect();});
}
function dots(){var d=document.createElement('div');d.className='cf-typ';d.id='cf-tdots';d.innerHTML='<span></span><span></span><span></span>';$('cf-msgs').appendChild(d);$('cf-msgs').scrollTop=9999}
function rmDots(){var t=$('cf-tdots');if(t)t.remove()}
function escHtml(t){var d=document.createElement('div');d.textContent=t;return d.innerHTML}

// ── Visitor metadata (sent once on WebSocket open) ───────────────────
function parseDevice(ua){if(/tablet|ipad|playbook|silk/i.test(ua))return'tablet';if(/mobile|iphone|ipod|android|blackberry/i.test(ua))return'mobile';return'desktop'}
function parseOS(ua){if(/windows nt/i.test(ua))return'Windows';if(/mac os x/i.test(ua)&&!/iphone|ipad|ipod/i.test(ua))return'macOS';if(/iphone|ipad|ipod/i.test(ua))return'iOS';if(/android/i.test(ua))return'Android';if(/linux/i.test(ua))return'Linux';return'Unknown'}
function parseBrowser(ua){if(/edg\\//i.test(ua))return'Edge';if(/opr\\//i.test(ua)||/opera/i.test(ua))return'Opera';if(/firefox/i.test(ua))return'Firefox';if(/chrome/i.test(ua))return'Chrome';if(/safari/i.test(ua))return'Safari';return'Other'}
var RETURNING_KEY='__cf_returning__';
var isReturning=!!localStorage.getItem(RETURNING_KEY);
localStorage.setItem(RETURNING_KEY,'1');
var visitorMeta={device:parseDevice(navigator.userAgent),os:parseOS(navigator.userAgent),
  browser:parseBrowser(navigator.userAgent),referrer:document.referrer||null,
  timezone:Intl.DateTimeFormat().resolvedOptions().timeZone||null,
  country:null,city:null,country_code:null,ip:null,is_returning:isReturning};
// Geo lookup (best-effort, non-blocking)
fetch('https://ipapi.co/json/').then(function(r){return r.json()}).then(function(d){
  visitorMeta.country=d.country_name||null;visitorMeta.city=d.city||null;
  visitorMeta.country_code=d.country_code||null;visitorMeta.ip=d.ip||null;
}).catch(function(){});

// ── WebSocket ────────────────────────────────────────────────────────
var isOpen=false;
var sentVisitorMeta=false;
function sendVisitorMeta(){
  if(sentVisitorMeta||!ws||ws.readyState!==1)return;
  sentVisitorMeta=true;
  var payload={type:'visitor_meta',visitor_uid:vid,page_visits:buildPageVisits()};
  for(var k in visitorMeta)payload[k]=visitorMeta[k];
  ws.send(JSON.stringify(payload));
}
// C2 — proactive_trigger: 10s after page load send a behavior frame to the
// backend; if widget hasn't been opened and no other nudge has fired, the
// server generates a context-aware question and pushes it back with
// source='proactive_open' (in AUTO_OPEN above, so it pops the widget).
// Once per session — flag in sessionStorage so multi-page nav doesn't re-fire.
// We send the accumulated page_visits from prior pages PLUS a LIVE snapshot
// of the current page so the bot sees the visitor's full journey, not just
// the page they happened to be on when the timer fired.
// Mobile networks routinely take 3-8s to complete the WebSocket
// handshake, so the original "send at exactly 10s" was a silent miss
// whenever the WS wasn't open at that instant. We now schedule the
// proactive trigger to RETRY up to 3 times (at 10s / 15s / 22s) until
// the WS is open and the visitor still hasn't engaged.
var _proactiveAttempts=0;
function _sendProactive(){
  try{
    var k='cf_proactive_'+C+'_'+sid;
    if(sessionStorage.getItem(k))return;
    if(isOpen)return;
    _proactiveAttempts++;
    if(!ws||ws.readyState!==1){
      if(_proactiveAttempts<3)setTimeout(_sendProactive,5000+_proactiveAttempts*2000);
      return;
    }
    var livePage={
      url: location.pathname,
      title: document.title || location.pathname,
      duration_seconds: Math.round((Date.now()-startTime)/1000),
      visited_at: new Date(startTime).toISOString()
    };
    var combined=(Array.isArray(pageVisits)?pageVisits.slice():[]).concat([livePage]);
    ws.send(JSON.stringify({type:'proactive_trigger',behavior_matrix:behavior,page_visits:combined,dwell_seconds:behavior.timeOnSite,page_url:location.href}));
    sessionStorage.setItem(k,String(Date.now()));
  }catch(_){}
}
setTimeout(_sendProactive,10000);

function connect(){
  ws=new WebSocket(B.replace(/^https/,'wss').replace(/^http/,'ws')+'/ws/chat/'+C+'/'+sid+'/');
  ws.onopen=function(){sendVisitorMeta()};
  ws.onmessage=function(e){
    try{
      var d=JSON.parse(e.data);
      // Server-pushed hot-lead trigger: visitor reached READY_TO_BUY / hot
      // score and we still don't have their contact. Auto-opens the chat
      // window if closed and pops the lead modal after a short delay so the
      // visitor sees the AI confirmation first.
      if(d.type==='lead_capture_required'&&!leadDone){
        if(!isOpen)toggleOpen();
        setTimeout(showLead,1200);
        return;
      }
      // Cross-tab live sync: a visitor message typed in ANOTHER tab. Render
      // it here (the sending tab dedupes its own via msg_id, keeping its own
      // typing dots) and show dots so this tab looks like it's awaiting the
      // reply too. We deliberately do NOT clear dots/busy on this branch.
      if(d.type==='user_message'){
        if(isSeen(d.msg_id))return;
        markSeen(d.msg_id);
        bubble(escHtml(d.message||''),'me');
        dots();
        return;
      }
      // Everything below is a terminal/assistant event → safe to clear the
      // typing indicator + re-enable input.
      rmDots();busy=false;$('cf-sb').disabled=!$('cf-inp').value.trim()&&!pendingImg;
      if(d.type==='ai_message'&&d.message){
        // Dedupe by server msg_id so the reply renders exactly once per tab.
        if(d.msg_id&&isSeen(d.msg_id))return;
        if(d.msg_id)markSeen(d.msg_id);
        bubble(renderMd(d.message),'ai');chime();
        // Q3: render clickable chip suggestions if the bot included any
        if(Array.isArray(d.quick_replies)&&d.quick_replies.length){
          var qrEl=document.createElement('div');qrEl.className='cf-qrs';
          d.quick_replies.slice(0,4).forEach(function(text){
            var b=document.createElement('button');b.className='cf-qr';b.textContent=text;
            b.onclick=function(){
              qrEl.remove(); // prevent double-tap during round-trip
              var inp=$('cf-inp');inp.value=text;send();
            };
            qrEl.appendChild(b);
          });
          $('cf-msgs').appendChild(qrEl);$('cf-msgs').scrollTop=9999;
        }
        var AUTO_OPEN=['afk_nudge','fomo','exit_intent','pricing_hesitation','add_to_cart_help','abandoned_form','deep_engagement','rage_click_help','high_intent_action','lead_captured','proactive_open'];
        if(AUTO_OPEN.indexOf(d.source)>=0&&!isOpen)toggleOpen();
      }
    }catch(x){}};
  ws.onerror=function(){rmDots();busy=false};
  ws.onclose=function(){ws=null;sentVisitorMeta=false}}

// Open WebSocket ON LOAD so visitor_meta + page_visits get saved
// even before the visitor opens the chat — backend can then use this
// browsing context when AI generates the first reply.
// Restore the conversation from the server so a new tab / reload shows the
// SAME chat, THEN open the socket — restoreFromServer() calls ensureConnect()
// once it resolves so the WS opens on the recovered sid if we adopted one.
restoreFromServer();
// Safety net: never let a hung/slow restore fetch block the socket.
setTimeout(ensureConnect,1500);

// ── Send message ─────────────────────────────────────────────────────
function send(){
  var text=$('cf-inp').value.trim();
  if((!text&&!pendingImg)||busy)return;
  if(pendingImg){bubble(pendingImg,'img');clearImg()}
  var msg=text||'[User sent an image]';
  bubble(escHtml(msg),'me');
  $('cf-inp').value='';$('cf-sb').disabled=true;busy=true;dots();
  // Track user-message count for inline lead capture trigger (after 3 user msgs)
  msgCount++;if(msgCount>=3&&!leadDone)setTimeout(showLead,1500);
  // Tag with a client msg_id so when the server echoes this message to the
  // session group (for other tabs), THIS tab dedupes and doesn't re-render it.
  var mid=newMsgId();markSeen(mid);
  var pl=JSON.stringify({message:msg,msg_id:mid,behavior_matrix:behavior,page_visits:buildPageVisits()});
  if(ws&&ws.readyState===1){ws.send(pl)}
  else{connect();ws.addEventListener('open',function(){ws.send(pl)},{once:true})}}

// ── Image ────────────────────────────────────────────────────────────
function clearImg(){pendingImg=null;$('cf-imgprev').className='';$('cf-pt').src=''}
function handleFile(f){if(!f)return;var r=new FileReader();r.onload=function(ev){pendingImg=ev.target.result;$('cf-pt').src=pendingImg;$('cf-imgprev').className='has-img';$('cf-sb').disabled=false};r.readAsDataURL(f)}

// ── Voice ────────────────────────────────────────────────────────────
function toggleVoice(){
  if(recording){if(recognition)recognition.stop();recording=false;$('cf-vb').classList.remove('rec');$('cf-inp').placeholder='Type a message…';return}
  var SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR)return;
  recognition=new SR();recognition.continuous=false;recognition.interimResults=false;recognition.lang='en-US';
  recognition.onresult=function(e){$('cf-inp').value=e.results[0][0].transcript;$('cf-sb').disabled=!$('cf-inp').value.trim();recording=false;$('cf-vb').classList.remove('rec');$('cf-inp').placeholder='Type a message…'};
  recognition.onerror=recognition.onend=function(){recording=false;$('cf-vb').classList.remove('rec');$('cf-inp').placeholder='Type a message…'};
  recognition.start();recording=true;$('cf-vb').classList.add('rec');$('cf-inp').placeholder='\\uD83C\\uDFA4 Listening...'}

// ── Toggle ───────────────────────────────────────────────────────────
function toggleOpen(){
  isOpen=!isOpen;
  if(isOpen){$('cf-win').classList.add('open');$('cf-pill').style.display='none';if(!ws)connect()}
  else{$('cf-win').classList.remove('open');$('cf-pill').style.display='flex'}}

// ── Lightweight behavioral tracker — PERSISTS ACROSS PAGE LOADS ──────
// State is kept in sessionStorage so visitors browsing multiple pages
// accumulate behavior + page_visits. Without this, each WP page reload
// would wipe the tracker and the AI would never see prior pages.
var STATE_KEY='cf_state_'+C;
var saved={};
try{saved=JSON.parse(sessionStorage.getItem(STATE_KEY)||'{}')}catch(e){}

var startTime=saved.sessionStartTime||Date.now();
var pageVisits=Array.isArray(saved.pageVisits)?saved.pageVisits:[];

// Finalize previous page if visitor navigated to a new URL
var pathNow=window.location.pathname;
if(saved.currentPage&&saved.currentPage.url&&saved.currentPage.url!==pathNow){
  // Page changed — push finalized prior visit into the list
  pageVisits.push({
    url:saved.currentPage.url,
    title:saved.currentPage.title||saved.currentPage.url,
    duration_seconds:saved.currentPage.duration_seconds||0,
    visited_at:saved.currentPage.visited_at||new Date().toISOString()
  });
  if(pageVisits.length>30)pageVisits=pageVisits.slice(-30);
}

var currentPage={url:pathNow,title:document.title,enteredAt:Date.now(),
  visited_at:new Date().toISOString(),duration_seconds:0};

var behavior=saved.behavior||{pagesViewed:[],timeOnSite:0,scrollDepth:0,
  pricingPageVisits:0,checkoutVisits:0,exitIntentFired:false,clickCount:0,ctaClicks:0,
  rageClicks:0,addToCartClicks:0,formFocused:false,formAbandoned:false,
  copyEvents:0,priceViews:0,videoPlays:0,fileDownloads:0,
  scrollMilestones:[],idleSeconds:0,tabHiddenSeconds:0,hoverCount:0};

// Add this page to pagesViewed list (deduped)
if(behavior.pagesViewed.indexOf(pathNow)<0)behavior.pagesViewed.push(pathNow);

// Pricing/checkout path detection (incremented per page visit)
var PRICING=['/pricing','/plans','/checkout','/subscribe','/upgrade','/buy'];
var CHECKOUT=['/checkout','/cart','/order'];
var pathLow=pathNow.toLowerCase();
if(PRICING.some(function(p){return pathLow.indexOf(p)>=0}))behavior.pricingPageVisits++;
if(CHECKOUT.some(function(p){return pathLow.indexOf(p)>=0}))behavior.checkoutVisits++;

// Save state every 2s + on beforeunload — keeps sessionStorage fresh
function saveState(){
  currentPage.duration_seconds=Math.round((Date.now()-currentPage.enteredAt)/1000);
  behavior.timeOnSite=Math.round((Date.now()-startTime)/1000);
  try{sessionStorage.setItem(STATE_KEY,JSON.stringify({
    sessionStartTime:startTime,pageVisits:pageVisits,
    currentPage:{url:currentPage.url,title:currentPage.title,
      duration_seconds:currentPage.duration_seconds,visited_at:currentPage.visited_at},
    behavior:behavior,
    eventQueue:eventQueue
  }))}catch(e){}
}
setInterval(saveState,2000);
window.addEventListener('beforeunload',saveState);

// Build the complete page_visits payload (history + current page snapshot)
function buildPageVisits(){
  var dur=Math.round((Date.now()-currentPage.enteredAt)/1000);
  return pageVisits.concat([{url:currentPage.url,title:currentPage.title,
    duration_seconds:dur,visited_at:currentPage.visited_at}]);
}

// Scroll tracking
var MILESTONES=[25,50,75,90];
window.addEventListener('scroll',function(){
  var dh=Math.max(document.body.scrollHeight,document.documentElement.scrollHeight)-window.innerHeight;
  if(dh<=0)return;
  var depth=Math.round((window.scrollY/dh)*100);
  if(depth>behavior.scrollDepth)behavior.scrollDepth=depth;
  for(var i=0;i<MILESTONES.length;i++){
    var m=MILESTONES[i];
    if(depth>=m&&behavior.scrollMilestones.indexOf(m)<0)behavior.scrollMilestones.push(m);
  }
},{passive:true});

// ── Event queue for heatmap / activity timeline ──────────────────────
// Each entry: {type, data: {page_url, page_title, x, y, text, tag, href, ts}}
var eventQueue=saved.eventQueue||[];
function logEvent(type,data){
  eventQueue.push({type:type,data:data||{}});
  if(eventQueue.length>200)eventQueue=eventQueue.slice(-200);
}
// Record this page view as a discrete event for timelines
logEvent('page_view',{page_url:pathNow,page_title:document.title});

// Click tracking with rage detection + add-to-cart + CTA + heatmap coords
var CTA_PAT=/add.to.cart|buy.now|get.started|subscribe|checkout|order.now|sign.up|book.now|contact/i;
var recentClicks={};
document.addEventListener('click',function(e){
  var el=e.target.closest('button,a,[role="button"],input[type="submit"]')||e.target;
  var text=(el.innerText||el.value||el.alt||'').trim().slice(0,80);
  var tag=(el.tagName||'').toLowerCase();
  var href=tag==='a'?(el.getAttribute('href')||'').slice(0,300):null;
  behavior.clickCount++;

  // Coordinates normalised to viewport width % and full-document height %
  var docH=Math.max(document.body.scrollHeight,document.documentElement.scrollHeight,window.innerHeight);
  var xPct=Math.round(e.clientX/window.innerWidth*1000)/10;
  var yPct=Math.round((e.clientY+window.scrollY)/docH*1000)/10;
  var clickData={page_url:pathNow,page_title:document.title,
    x:Math.max(0,Math.min(100,xPct)),y:Math.max(0,Math.min(100,yPct)),
    text:text,tag:tag,href:href};

  var isATC=el.matches&&el.matches('.add_to_cart_button,.single_add_to_cart_button,[name="add-to-cart"]');
  var isCTA=CTA_PAT.test(text);

  if(isATC){
    behavior.addToCartClicks++;
    logEvent('add_to_cart',clickData);
    flush(true);fireTrigger('add_to_cart_help');
  }else if(isCTA){
    behavior.ctaClicks++;
    logEvent('cta_click',clickData);
  }else{
    logEvent('click',clickData);
  }

  if(tag==='a'&&href){
    if(/\\.(pdf|zip|docx?|xlsx?|mp4|mp3)(\\?|$)/i.test(href))behavior.fileDownloads++;
  }

  // Rage detection
  var k=Math.round(e.clientX/20)+'_'+Math.round(e.clientY/20);
  if(!recentClicks[k])recentClicks[k]=[];
  var now=Date.now();
  recentClicks[k]=recentClicks[k].filter(function(t){return now-t<1000});
  recentClicks[k].push(now);
  if(recentClicks[k].length>=3){
    recentClicks[k]=[];behavior.rageClicks++;
    logEvent('rage_click',clickData);
    flush(true);fireTrigger('rage_click_help');
  }
});

// Form tracking — IGNORE the widget's own inputs (they were causing
// abandoned_form to fire constantly when the visitor focused our own
// chat input or lead-capture email field but didn't type immediately).
// Also rate-limit: fire once per session, never repeat.
var formAt=0;
var abandonedFired=false;
function isWidgetInput(el){
  return !!(el&&el.closest&&(el.closest('#cf-w')||el.closest('#cf-lead-ov')));
}
document.addEventListener('focusin',function(e){
  if(!e.target.matches('input:not([type="hidden"]):not([type="submit"]):not([type="button"]),textarea,select'))return;
  if(isWidgetInput(e.target))return;
  formAt=Date.now();if(!behavior.formFocused)behavior.formFocused=true;
});
document.addEventListener('focusout',function(e){
  if(!e.target.matches('input:not([type="hidden"]):not([type="submit"]):not([type="button"]),textarea,select'))return;
  if(isWidgetInput(e.target))return;
  if(abandonedFired)return;
  if(Date.now()-formAt>=4000&&!(e.target.value||'').trim()){
    behavior.formAbandoned=true;abandonedFired=true;
    flush(true);fireTrigger('abandoned_form');
  }
});

// Tab visibility
var hiddenAt=null;
document.addEventListener('visibilitychange',function(){
  if(document.hidden)hiddenAt=Date.now();
  else if(hiddenAt){behavior.tabHiddenSeconds+=Math.round((Date.now()-hiddenAt)/1000);hiddenAt=null}
});

// Copy tracking
document.addEventListener('copy',function(){
  var sel=(window.getSelection()||{}).toString();
  if(sel&&sel.length>=3)behavior.copyEvents++;
});

// Price visibility (IntersectionObserver)
setTimeout(function(){
  if(!window.IntersectionObserver)return;
  var seen=new Set();
  var obs=new IntersectionObserver(function(entries){
    entries.forEach(function(en){if(en.isIntersecting&&!seen.has(en.target)){seen.add(en.target);behavior.priceViews++}})
  },{threshold:0.5});
  document.querySelectorAll('.price,.woocommerce-Price-amount,[itemprop="price"]').forEach(function(el){obs.observe(el)});
},1500);

// Video play
document.addEventListener('play',function(){behavior.videoPlays++},true);

// Exit intent — three pathways so it works on every device:
//   • Desktop: cursor crosses top of viewport (mouseleave + clientY<20)
//   • Mobile A: visitor backgrounds the tab / locks the screen
//                (visibilitychange to hidden)
//   • Mobile B: visitor actually navigates away (pagehide)
// Touch devices never fire mouseleave, which is why exit_intent was
// previously dead on phones. Shared gate: timeOnSite>=10, once per session.
function _fireExitIntent(source){
  if(behavior.exitIntentFired||behavior.timeOnSite<10)return;
  behavior.exitIntentFired=true;flush(true);fireTrigger('exit_intent');
}
document.addEventListener('mouseleave',function(e){
  if(e.clientY>20)return;
  _fireExitIntent('mouse');
});
// Tab-switch debounce: opening a product link in a new tab fires
// visibilitychange→hidden, but that's NOT a leave — the visitor is coming
// right back. Only treat it as exit-intent if the tab STAYS hidden for 6s.
// If they return before then, cancel. This stops a spurious "leaving so
// soon?" nudge popping every time someone taps a product link.
var _hideTimer=null;
document.addEventListener('visibilitychange',function(){
  if(document.hidden){
    _hideTimer=setTimeout(function(){_fireExitIntent('visibility')},6000);
  }else if(_hideTimer){
    clearTimeout(_hideTimer);_hideTimer=null;
  }
});
// pagehide = a genuine navigation away → fire immediately.
window.addEventListener('pagehide',function(){_fireExitIntent('pagehide')});

// Time on site + deep engagement trigger
// C7 — lowered from scrollDepth>=75 + timeOnSite>=90 to scrollDepth>=50 + timeOnSite>=30
// QA flagged the old bar was so high most visitors who would benefit had already bounced.
setInterval(function(){
  behavior.timeOnSite=Math.round((Date.now()-startTime)/1000);
  if(behavior.timeOnSite>=30&&behavior.scrollDepth>=50&&!behavior._deepFired){
    behavior._deepFired=true;fireTrigger('deep_engagement');
  }
  if(behavior.timeOnSite>=120&&(behavior.ctaClicks>=1||behavior.pricingPageVisits>=1)&&!behavior._hiFired){
    behavior._hiFired=true;fireTrigger('high_intent_action');
  }
},5000);

// Pricing hesitation trigger
if(behavior.pricingPageVisits>=1){
  setTimeout(function(){fireTrigger('pricing_hesitation')},30000);
}

// Fire trigger
function fireTrigger(type){
  fetch(B+'/api/chat/trigger/',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({session_id:sid,client_id:C,trigger_type:type})}).catch(function(){});
}

// Beacon flush (periodic + on unload + on high-signal events)
function flush(force){
  // Snapshot current page entry as a temporary page-visit for inclusion
  var dur=Math.round((Date.now()-currentPage.enteredAt)/1000);
  var visits=pageVisits.concat([{url:currentPage.url,title:currentPage.title,duration_seconds:dur,visited_at:new Date(currentPage.enteredAt).toISOString()}]);
  // Send any queued events for heatmap/timeline
  var eventsToSend=eventQueue.slice();
  eventQueue.length=0;  // clear queue — backend dedupes via bulk_create
  var payload=JSON.stringify({sessionId:sid,clientId:C,behaviorMatrix:behavior,events:eventsToSend,page_visits_snapshot:visits});
  if(navigator.sendBeacon)navigator.sendBeacon(B+'/api/analytics/beacon/',payload);
  else fetch(B+'/api/analytics/beacon/',{method:'POST',body:payload,keepalive:true}).catch(function(){});
}
setInterval(function(){flush(false)},15000);
// Final-flush listeners. beforeunload is unreliable on iOS Safari; pagehide
// and visibilitychange-to-hidden are the only events that fire consistently
// when the visitor backgrounds the tab. All three call the same flush() via
// navigator.sendBeacon — the one request type the browser guarantees to
// complete during page tear-down.
window.addEventListener('beforeunload',function(){flush(true)});
window.addEventListener('pagehide',function(){flush(true)});
document.addEventListener('visibilitychange',function(){
  if(document.hidden)flush(true);
});

// ── Event listeners ──────────────────────────────────────────────────
$('cf-pill').onclick=toggleOpen;
$('cf-pill').onkeydown=function(e){if(e.key==='Enter'||e.key===' ')toggleOpen()};
$('cf-xb').onclick=toggleOpen;
$('cf-sb').onclick=send;
$('cf-inp').addEventListener('keydown',function(e){if(e.key==='Enter')send()});
$('cf-inp').addEventListener('input',function(){$('cf-sb').disabled=!this.value.trim()&&!pendingImg});
$('cf-ib').onclick=function(){$('cf-fi').click()};
$('cf-fi').onchange=function(){handleFile(this.files[0]);this.value=''};
$('cf-prm').onclick=clearImg;
$('cf-vb').onclick=toggleVoice;
$('cf-lead-cls').onclick=dismissLead;
$('cf-lead-sb').onclick=submitLead;
$('cf-lead-em').addEventListener('keydown',function(e){if(e.key==='Enter')submitLead()});
if($('cf-lead-ph')){
  // Digits-only, max 9 (the LK subscriber number after +94).
  $('cf-lead-ph').addEventListener('input',function(){
    var v=this.value.replace(/\\D/g,'').slice(0,9);
    if(v!==this.value)this.value=v;
    setLeadErr('');
  });
  $('cf-lead-ph').addEventListener('keydown',function(e){if(e.key==='Enter')submitLead()});
}

// ── Product-link click attribution ───────────────────────────────────────
// Delegated handler on the messages container: when the visitor clicks a
// link the AI sent ([data-cf-plink]), beacon it to the backend BEFORE the
// new tab opens. sendBeacon is fire-and-forget and survives navigation.
(function(){
  var box=$('cf-msgs');
  if(!box)return;
  box.addEventListener('click',function(e){
    var a=e.target.closest&&e.target.closest('a[data-cf-plink]');
    if(!a)return;
    try{
      var payload=JSON.stringify({
        session_id:sid,client_id:C,
        url:a.getAttribute('data-cf-plink')||a.href||'',
        link_text:a.getAttribute('data-cf-pltext')||a.textContent||''
      });
      if(navigator.sendBeacon){
        navigator.sendBeacon(B+'/api/chat/link-click/',new Blob([payload],{type:'application/json'}));
      }else{
        fetch(B+'/api/chat/link-click/',{method:'POST',headers:{'Content-Type':'application/json'},body:payload,keepalive:true}).catch(function(){});
      }
    }catch(_){}
  },true);
})();
})();
</` + `script>`

  // ───────────── Format wrappers ─────────────────
  const fullSnippet = '<!-- Start of Checkfunnel code -->\n' + css + '\n' + html + '\n' + js + '\n<!-- End of Checkfunnel code -->'

  if (format === 'loader') {
    // Auto-updating one-liner. The widget is served from our origin, so
    // future fixes deploy WITHOUT the merchant re-pasting. This is the
    // recommended embed.
    return [
      '<!-- Checkfunnel — paste once; updates automatically -->',
      '<script async src="' + backend + '/widget/embed.js?client_id=' + id + '"></script>',
    ].join('\n')
  }

  if (format === 'shopify') {
    // Liquid is HTML-compatible — raw <script>/<style>/<div> pass through
    // untouched because Liquid only processes `{% %}` and `{{ }}`. Wrap
    // the snippet with merchant-facing headers so it's obvious in
    // theme.liquid what was pasted and why.
    return [
      '{% comment %}',
      '  Checkfunnel AI chat widget — paste this block right before',
      '  </body> in Layout/theme.liquid (Online Store → Themes → Edit code).',
      '  Branding, color, name, and CTA stay live-editable from the',
      '  Checkfunnel portal — no re-paste needed.',
      '{% endcomment %}',
      fullSnippet,
    ].join('\n')
  }

  if (format === 'wordpress') {
    return [
      '<?php',
      '/**',
      ' * Checkfunnel AI chat widget — self-contained.',
      ' * Branding, color, name, CTA all update live from the portal',
      ' * (config is fetched on every page load + every 60 seconds).',
      ' * Paste into your active theme\'s functions.php.',
      ' */',
      'function checkfunnel_widget() {',
      '    ?>',
      fullSnippet,
      '    <?php',
      '}',
      "add_action( 'wp_footer', 'checkfunnel_widget' );",
    ].join('\n')
  }

  if (format === 'react') {
    return [
      "import { useEffect } from 'react'",
      '',
      'const SNIPPET = ' + JSON.stringify(fullSnippet) + ';',
      '',
      'export function CheckfunnelWidget() {',
      '  useEffect(() => {',
      "    if (document.getElementById('cf-w')) return",
      "    const wrap = document.createElement('div')",
      '    wrap.innerHTML = SNIPPET',
      '    Array.from(wrap.childNodes).forEach(n => document.body.appendChild(n))',
      '  }, [])',
      '  return null',
      '}',
    ].join('\n')
  }

  return fullSnippet
}
