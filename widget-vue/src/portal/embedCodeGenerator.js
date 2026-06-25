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
#cf-pill { position: relative; display: flex; align-items: center; gap: 10px;
  padding: 9px 11px 9px 9px; background: rgba(17,17,17,0.97);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.08); border-radius: 100px; cursor: pointer;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5); transition: transform .2s, box-shadow .2s;
  min-width: 220px; user-select: none;
  animation: cf-pi .3s cubic-bezier(.34,1.56,.64,1) forwards; }
/* ── Suggestion notification (page-aware greeting) ── */
#cf-note { display: none; max-width: 280px; margin-bottom: 10px; padding: 11px 13px;
  background: rgba(17,17,17,0.97); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.10); border-radius: 16px; border-bottom-right-radius: 6px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5); color: #e7e9ee; font-size: 13px; line-height: 1.45;
  position: relative; cursor: pointer; user-select: none;
  animation: cf-pi .3s cubic-bezier(.34,1.56,.64,1) forwards; }
#cf-note.show { display: block; }
#cf-note-tx { display: block; padding-right: 16px; }
#cf-note-x { position: absolute; top: 5px; right: 7px; background: none; border: none; color: #94a3b8;
  font-size: 15px; line-height: 1; cursor: pointer; padding: 2px; }
#cf-note-x:hover { color: #fff; }
/* ── Unread badge on the launcher ── */
#cf-badge { position: absolute; top: -6px; right: -4px; min-width: 18px; height: 18px; padding: 0 5px;
  background: #ef4444; color: #fff; font-size: 11px; font-weight: 700; border-radius: 9px;
  display: none; align-items: center; justify-content: center; box-shadow: 0 2px 6px rgba(0,0,0,0.4); }
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

/* Agent takeover media attachments (image / voice / file) inside AI bubbles */
#cf-w .cf-att-wrap { display: flex; flex-direction: column; gap: 6px; margin-bottom: 4px; }
#cf-w .cf-att-img { max-width: 200px; max-height: 200px; border-radius: 12px; display: block; cursor: pointer; }
#cf-w .cf-att-aud { width: 210px; max-width: 100%; height: 36px; }
#cf-w .cf-att-file { display: inline-flex; align-items: center; gap: 5px; font-size: 13px;
  color: var(--cf-accent); text-decoration: underline; word-break: break-all; }

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
#cf-lead { padding: 14px 14px 15px;
  border-top: 1px solid var(--cf-border-soft);
  background: var(--cf-bg-elev);
  display: none; animation: cf-leadslide .28s cubic-bezier(.34,1.56,.64,1); }
#cf-lead.show { display: block; }
@keyframes cf-leadslide { from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); } }
.cf-lead-head { display: flex; align-items: flex-start; justify-content: space-between;
  gap: 10px; margin-bottom: 12px; }
.cf-lead-titles { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.cf-lead-ttl { font-size: 13.5px; font-weight: 600; color: var(--cf-text-strong);
  letter-spacing: -.1px; line-height: 1.25; }
.cf-lead-sub { font-size: 11.5px; color: var(--cf-text-muted); line-height: 1.4; }
#cf-lead-cls { background: transparent; border: none; color: var(--cf-text-muted);
  cursor: pointer; padding: 0; font-size: 13px; line-height: 1; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; border-radius: 7px; margin: -2px -2px 0 0;
  transition: background .15s, color .15s; }
#cf-lead-cls:hover { background: rgba(255,255,255,0.08); color: var(--cf-text-strong); }
.cf-lead-inp { width: 100%; height: 42px; padding: 0 14px;
  background: rgba(255,255,255,0.045);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 11px; font-size: 13.5px; color: var(--cf-text);
  outline: none; box-sizing: border-box; font-family: inherit; line-height: 1.3;
  transition: border-color .15s, background .15s;
  /* Prevent browser autofill from painting the input white on dark themes */
  -webkit-text-fill-color: var(--cf-text); }
.cf-lead-inp:focus { border-color: var(--cf-accent); background: rgba(255,255,255,0.07); }
.cf-lead-inp::placeholder { color: rgba(255,255,255,0.4); opacity: 1; }
#cf-lead-em { margin-bottom: 9px; }
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
.cf-lead-btn { width: 100%; height: 42px; background: var(--cf-accent); border: none;
  border-radius: 11px; font-size: 13.5px; font-weight: 600; color: #fff;
  cursor: pointer; font-family: inherit; transition: opacity .15s, transform .1s;
  white-space: nowrap; box-sizing: border-box;
  display: inline-flex; align-items: center; justify-content: center; }
.cf-lead-btn:hover:not(:disabled) { opacity: .92; transform: translateY(-1px); }
.cf-lead-btn:disabled { opacity: .5; cursor: not-allowed; }
/* Phone field — the +94 affix is joined seamlessly to the input so it reads
   as one control instead of two disconnected pills. */
.cf-lead-phone { display: flex; align-items: stretch; margin-bottom: 12px; }
.cf-lead-cc { display: inline-flex; align-items: center; justify-content: center;
  height: 42px; padding: 0 12px; flex-shrink: 0;
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.1); border-right: none;
  border-radius: 11px 0 0 11px; font-size: 13px; font-weight: 600;
  color: var(--cf-text-muted); box-sizing: border-box; }
.cf-lead-phone .cf-lead-ph { border-radius: 0 11px 11px 0; letter-spacing: .3px; }
.cf-lead-phone:focus-within .cf-lead-cc { border-color: var(--cf-accent); }
.cf-lead-err { font-size: 11px; color: #f87171; min-height: 0; margin: 7px 2px 0;
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
#cf-w[data-cf-theme="light"] #cf-note { background: rgba(255,255,255,0.98); color: #1e293b; border-color: rgba(0,0,0,0.08); }
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

/* ════════════════════════════════════════════════════════════════════
   WIDGET STYLE SWITCHING — Style 1 (classic) vs Style 2 (assistant card)
   Style-2-only elements carry .cf-lux / dedicated classes; in Classic the
   wrappers collapse (display:contents) so the widget looks exactly as before.
   ════════════════════════════════════════════════════════════════════ */
#cf-tools, #cf-inrow { display: contents; }
.cf-lux { display: none; }
#cf-av .cf-av-bot { display: none; }
#cf-av .cf-av-ic { display: inline; }
.cf-hs .cf-hs-l { display: none; }
#cf-pill .cf-pi-robot { display: none; }
.cf-av-bot svg, .cf-pi-robot svg { width: 100%; height: 100%; }

/* ── Style 2: Assistant Card ─────────────────────────────────────────── */
#cf-w[data-cf-style="assistant"] #cf-av .cf-av-ic { display: none; }
#cf-w[data-cf-style="assistant"] #cf-av .cf-av-bot { display: flex; align-items: center; justify-content: center; width: 26px; height: 26px; color: #fff; }
#cf-w[data-cf-style="assistant"] .cf-hs .cf-hs-c { display: none; }
#cf-w[data-cf-style="assistant"] .cf-hs .cf-hs-l { display: inline; }

/* Launcher → gradient robot circle */
#cf-w[data-cf-style="assistant"] #cf-pill {
  min-width: 0; width: 64px; height: 64px; padding: 0; border-radius: 50%;
  align-items: center; justify-content: center;
  background: var(--cf-accent);
  background: linear-gradient(140deg, color-mix(in srgb, var(--cf-accent) 76%, #ffffff), color-mix(in srgb, var(--cf-accent) 82%, #000000));
  border: 3px solid rgba(255,255,255,0.92);
  box-shadow: 0 12px 34px rgba(0,0,0,0.32);
}
#cf-w[data-cf-style="assistant"] #cf-pill .cf-pi-icon,
#cf-w[data-cf-style="assistant"] #cf-pill .cf-pi-txt,
#cf-w[data-cf-style="assistant"] #cf-pill .cf-pi-send { display: none; }
#cf-w[data-cf-style="assistant"] #cf-pill .cf-pi-robot { display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; color: #fff; }
#cf-w[data-cf-style="assistant"] #cf-badge { top: -3px; right: -3px; border: 2px solid #fff; }

/* Suggestion card with sparkle + tail */
#cf-w[data-cf-style="assistant"] #cf-note {
  max-width: 300px; padding: 16px 30px 16px 16px; border-radius: 20px; border-bottom-right-radius: 6px;
  background: var(--cf-bg-elev); color: var(--cf-text); border: 1px solid var(--cf-border-soft);
  box-shadow: 0 18px 48px rgba(0,0,0,0.22); font-size: 15px; line-height: 1.5; font-weight: 600;
}
#cf-w[data-cf-style="assistant"] #cf-note::after {
  content: ''; position: absolute; bottom: -8px; right: 24px; width: 16px; height: 16px;
  background: var(--cf-bg-elev); border-right: 1px solid var(--cf-border-soft); border-bottom: 1px solid var(--cf-border-soft);
  transform: rotate(45deg);
}
#cf-w[data-cf-style="assistant"] .cf-note-spark { display: inline-flex; vertical-align: -3px; width: 18px; height: 18px; margin-right: 6px; color: var(--cf-accent); }
#cf-w[data-cf-style="assistant"] .cf-note-spark svg { width: 18px; height: 18px; }
#cf-w[data-cf-style="assistant"] #cf-note-x { top: 8px; right: 9px; }

/* Window + header */
#cf-w[data-cf-style="assistant"] #cf-win { border-radius: 22px; }
#cf-w[data-cf-style="assistant"] #cf-head {
  background: color-mix(in srgb, var(--cf-accent) 8%, var(--cf-bg-elev)); padding: 15px 16px;
}
#cf-w[data-cf-style="assistant"] .cf-av {
  width: 42px; height: 42px;
  background: linear-gradient(140deg, color-mix(in srgb, var(--cf-accent) 76%, #ffffff), color-mix(in srgb, var(--cf-accent) 82%, #000000));
}
#cf-w[data-cf-style="assistant"] .cf-hn { font-size: 15px; font-weight: 700; }
#cf-w[data-cf-style="assistant"] #cf-xb { background: var(--cf-bg); border: 1px solid var(--cf-border-soft); }

/* Messages — labels above soft cards */
#cf-w[data-cf-style="assistant"] #cf-msgs { padding: 18px 16px; gap: 14px; }
#cf-w[data-cf-style="assistant"] .cf-ai, #cf-w[data-cf-style="assistant"] .cf-me { max-width: 90%; border-radius: 16px; }
#cf-w[data-cf-style="assistant"] .cf-ai {
  background: color-mix(in srgb, var(--cf-text) 6%, var(--cf-bg));
  border: 1px solid var(--cf-border-soft); box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}
/* Light theme needs a stronger edge or the soft card vanishes against the window. */
#cf-w[data-cf-style="assistant"][data-cf-theme="light"] .cf-ai { border-color: var(--cf-border); }
#cf-w[data-cf-style="assistant"] .cf-ai::before {
  content: 'ASSISTANT'; display: block; font-size: 10px; font-weight: 800; letter-spacing: 0.09em;
  color: var(--cf-text-muted); margin-bottom: 5px;
}
#cf-w[data-cf-style="assistant"] .cf-me::before {
  content: 'YOU'; display: block; font-size: 10px; font-weight: 800; letter-spacing: 0.09em;
  color: rgba(255,255,255,0.82); margin-bottom: 5px;
}

/* Footer — tool row + input row */
#cf-w[data-cf-style="assistant"] #cf-foot { flex-direction: column; align-items: stretch; gap: 12px; padding: 12px 14px; }
#cf-w[data-cf-style="assistant"] #cf-tools { display: flex; align-items: center; gap: 10px; }
#cf-w[data-cf-style="assistant"] #cf-inrow { display: flex; align-items: center; gap: 10px; }
#cf-w[data-cf-style="assistant"] .cf-emojiwrap { display: block; position: relative; }
#cf-w[data-cf-style="assistant"] .cf-mb {
  width: 40px; height: 40px; border-radius: 12px; flex: none;
  background: color-mix(in srgb, var(--cf-accent) 10%, var(--cf-bg)); color: var(--cf-accent);
  border: 1px solid color-mix(in srgb, var(--cf-accent) 20%, transparent);
}
#cf-w[data-cf-style="assistant"] #cf-vb {
  margin-left: auto; color: #fff; border: none;
  background: linear-gradient(140deg, color-mix(in srgb, var(--cf-accent) 76%, #ffffff), color-mix(in srgb, var(--cf-accent) 82%, #000000));
  border-radius: 50%;
}
#cf-w[data-cf-style="assistant"] #cf-inp {
  flex: 1; border-radius: 24px; padding: 12px 16px;
  border: 1.5px solid color-mix(in srgb, var(--cf-accent) 28%, var(--cf-border)); background: var(--cf-bg);
}
#cf-w[data-cf-style="assistant"] #cf-sb {
  width: 46px; height: 46px; border-radius: 50%; flex: none; opacity: 1;
  background: linear-gradient(140deg, color-mix(in srgb, var(--cf-accent) 76%, #ffffff), color-mix(in srgb, var(--cf-accent) 82%, #000000));
}
#cf-w[data-cf-style="assistant"] #cf-sb:disabled { opacity: 0.55; }
/* Emoji picker */
#cf-w[data-cf-style="assistant"] .cf-emojipick {
  position: absolute; bottom: 50px; left: 0; z-index: 6; width: 224px; padding: 8px;
  background: var(--cf-bg-elev); border: 1px solid var(--cf-border-soft); border-radius: 14px;
  box-shadow: 0 14px 36px rgba(0,0,0,0.3); display: grid; grid-template-columns: repeat(6, 1fr); gap: 2px;
}
#cf-w[data-cf-style="assistant"] .cf-emojipick[hidden] { display: none; }
#cf-w[data-cf-style="assistant"] .cf-emojipick button {
  background: none; border: none; font-size: 18px; cursor: pointer; padding: 5px; border-radius: 8px; line-height: 1;
}
#cf-w[data-cf-style="assistant"] .cf-emojipick button:hover { background: color-mix(in srgb, var(--cf-accent) 14%, transparent); }

/* Notched iOS — add safe-area cushioning even on larger viewports so
   the floating pill never collides with the home indicator. */
@supports (padding: env(safe-area-inset-bottom)) {
  #cf-w { padding-bottom: env(safe-area-inset-bottom, 0px); }
}
</style>`

  const html = `<div id="cf-w" data-cf-theme="dark">
<div id="cf-win" role="dialog" aria-label="Chat with ${name}">
<div id="cf-head">
<div class="cf-av" id="cf-av"><span class="cf-av-ic">&#9889;</span><span class="cf-av-bot"><svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"><path d="M32 13v7"/><rect x="16" y="20" width="32" height="27" rx="9"/><circle cx="26" cy="34" r="3.6"/><circle cx="38" cy="34" r="3.6"/><path d="M28 42h8"/></svg></span></div>
<div class="cf-hi"><div class="cf-hn" id="cf-hn">${name}</div><div class="cf-hs"><span class="cf-dot"></span><span class="cf-hs-c">Online</span><span class="cf-hs-l">Online now</span></div></div>
<button id="cf-xb" aria-label="Close">&#10005;</button>
</div>
<div id="cf-msgs"><div class="cf-ai">&#128075; Hi! How can I help you today?</div></div>
<div id="cf-imgprev"><div class="cf-prev-wrap"><img class="cf-prev-thumb" id="cf-pt" src="" alt="" width="52" height="52"/><button class="cf-prev-rm" id="cf-prm">&#10005;</button></div></div>
<div id="cf-lead">
  <div class="cf-lead-head">
    <div class="cf-lead-titles">
      <span class="cf-lead-ttl">Get a personalised follow-up</span>
      <span class="cf-lead-sub">Leave your details and our team will reach out.</span>
    </div>
    <button id="cf-lead-cls" aria-label="Dismiss">&#10005;</button>
  </div>
  <input class="cf-lead-inp" id="cf-lead-em" type="email" placeholder="you@email.com"/>
  <div class="cf-lead-phone">
    <span class="cf-lead-cc">+94</span>
    <input class="cf-lead-inp cf-lead-ph" id="cf-lead-ph" type="tel" inputmode="tel" maxlength="20" placeholder="Phone number (optional)"/>
  </div>
  <button class="cf-lead-btn" id="cf-lead-sb">Send my details</button>
  <div class="cf-lead-err" id="cf-lead-err"></div>
</div>
<div id="cf-foot">
<input id="cf-fi" type="file" accept="image/*" style="display:none">
<div id="cf-tools">
<button class="cf-mb" id="cf-ib" style="display:none" title="Attach image">
<svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
</button>
<button class="cf-mb cf-lux" id="cf-mediab" type="button" style="display:none" title="Attach image">
<svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="m8.5 12.5 5.8-5.8a3 3 0 014.2 4.2l-7.1 7.1a4.4 4.4 0 01-6.2-6.2l7.5-7.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
</button>
<div class="cf-emojiwrap cf-lux">
<button class="cf-mb" id="cf-emoji" type="button" title="Emoji">
<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M9 10h.01M15 10h.01"/><path d="M8.5 14a4.5 4.5 0 007 0"/></svg>
</button>
<div class="cf-emojipick" id="cf-emojipick" hidden>
<button type="button">&#128522;</button><button type="button">&#128525;</button><button type="button">&#128293;</button><button type="button">&#10024;</button><button type="button">&#128077;</button><button type="button">&#128156;</button><button type="button">&#128091;</button><button type="button">&#8986;</button><button type="button">&#128095;</button><button type="button">&#127873;</button><button type="button">&#128172;</button><button type="button">&#9989;</button>
</div>
</div>
<button class="cf-mb" id="cf-vb" style="display:none" title="Voice input">
<svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
</button>
</div>
<div id="cf-inrow">
<input id="cf-inp" type="text" placeholder="Type a message&#8230;" autocomplete="off">
<button id="cf-sb" aria-label="Send" disabled>
<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2" fill="white" stroke="none"/></svg>
</button>
</div>
</div>
<div id="cf-pby">Powered by <a href="https://checkfunnels.com" target="_blank" rel="noopener">Checkfunnels</a></div>
</div>
<div id="cf-note"><span class="cf-note-spark cf-lux"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l1.7 6.3L20 10l-6.3 1.7L12 18l-1.7-6.3L4 10l6.3-1.7z"/></svg></span><span id="cf-note-tx"></span><button id="cf-note-x" aria-label="Dismiss">&#10005;</button></div>
<div id="cf-pill" role="button" aria-label="Open chat" tabindex="0">
<div class="cf-pi-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="white"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg></div>
<span class="cf-pi-txt">Write a message...</span>
<div class="cf-pi-send"><svg width="13" height="13" viewBox="0 0 24 24" fill="white"><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg></div>
<span class="cf-pi-robot"><svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"><path d="M32 13v7"/><rect x="16" y="20" width="32" height="27" rx="9"/><circle cx="26" cy="34" r="3.6"/><circle cx="38" cy="34" r="3.6"/><path d="M28 42h8"/><path d="M12 31v8M52 31v8"/></svg></span>
<span id="cf-badge"></span>
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

// ── Page-aware proactive triggers (URL → greeting) ───────────────────
// State + helpers. Matching/classification mirrors chat/page_rules.py so the
// widget can show greetings INSTANTLY (no LLM, no blocking round-trip); the
// server re-derives authoritatively when we persist for the inbox.
var pageRules=[],assistantIntro='',proactiveEnabled=true,notifTimeout=20,autoCloseSeconds=0;
var cfgReady=false,widgetHidden=false;
var UNREAD_KEY='cf_unread_'+sid,GREET_KEY='cf_greeted_'+sid,INTRO_KEY='cf_intro_'+sid,DND_KEY='cf_dnd_'+C;

function cfClassify(path){
  var p=(path||'/').toLowerCase().split('?')[0].split('#')[0];
  if(p===''||p==='/'||p==='/home'||p==='/home/')return'home';
  if(p.indexOf('/checkout')>=0)return'checkout';
  if(p.indexOf('/cart')>=0)return'cart';
  if(p.indexOf('/products/')>=0||p.indexOf('/product/')>=0)return'product';
  if(p.indexOf('/collections/')>=0||p.indexOf('/category/')>=0||p.indexOf('/product-category/')>=0||p.indexOf('/shop')>=0)return'collection';
  if(p.indexOf('/order-tracking')>=0||p.indexOf('/track')>=0||p.indexOf('/orders/')>=0)return'track';
  if(p.indexOf('/offers')>=0||p.indexOf('/pricing')>=0||p.indexOf('/deals')>=0||p.indexOf('/sale')>=0)return'offers';
  if(p.indexOf('/contact')>=0)return'contact';
  if(p.indexOf('/about')>=0)return'about';
  if(p.indexOf('/faq')>=0||p.indexOf('/help')>=0)return'faq';
  return'fallback';
}
function cfMatches(rule,path){
  var pt=rule.page_type||'';
  if(pt==='fallback')return true;
  var mt=rule.match_type||'contains',pat=rule.pattern||'';
  if(pat){try{
    if(mt==='exact'){if(path===pat||path.replace(/\\/+$/,'')===pat.replace(/\\/+$/,''))return true}
    else if(mt==='prefix'){if(path.indexOf(pat)===0)return true}
    else if(mt==='regex'){if(new RegExp(pat).test(path))return true}
    else{if(path.toLowerCase().indexOf(pat.toLowerCase())>=0)return true}
  }catch(e){}}
  return !!pt&&cfClassify(path)===pt;
}
function cfMatchRule(rules,path){
  var ranked=(rules||[]).slice().sort(function(a,b){return(b.priority||0)-(a.priority||0)});
  for(var i=0;i<ranked.length;i++){if(cfMatches(ranked[i],path))return ranked[i]}
  return null;
}
function cfGreetText(rule,pname){
  var m=rule.greeting_message||'';
  if(m.indexOf('{product_name}')>=0){
    var n=(pname||'').trim();
    if(n)m=m.split('{product_name}').join(n);
    else m=m.split('the {product_name}').join('this product').split('{product_name}').join('this product');
  }
  return m;
}
function cfProductName(){
  try{
    var s=document.querySelectorAll('script[type="application/ld+json"]');
    for(var i=0;i<s.length;i++){try{
      var j=JSON.parse(s[i].textContent||'{}');var arr=Array.isArray(j)?j:[j];
      for(var k=0;k<arr.length;k++){var o=arr[k];if(!o)continue;
        var ty=o['@type'];var isP=(ty==='Product')||(Array.isArray(ty)&&ty.indexOf('Product')>=0);
        if(isP&&o.name)return String(o.name).slice(0,120);
        if(o['@graph']&&o['@graph'].length){for(var g=0;g<o['@graph'].length;g++){var go=o['@graph'][g];if(go&&go['@type']==='Product'&&go.name)return String(go.name).slice(0,120)}}
      }
    }catch(e){}}
    var og=document.querySelector('meta[property="og:title"]');
    if(og&&og.content)return og.content.slice(0,120);
    if(document.title)return document.title.split('|')[0].split('\\u2013')[0].split('-')[0].trim().slice(0,120);
  }catch(e){}
  return'';
}
// Badge (persists across page loads, keyed by sid)
function getUnread(){try{return parseInt(localStorage.getItem(UNREAD_KEY)||'0',10)||0}catch(e){return 0}}
function setUnread(n){try{localStorage.setItem(UNREAD_KEY,String(n))}catch(e){}renderBadge()}
function bumpUnread(){setUnread(getUnread()+1)}
function clearUnread(){setUnread(0)}
function renderBadge(){var b=$('cf-badge');if(!b)return;var n=getUnread();if(n>0&&!isOpen){b.textContent=n>9?'9+':String(n);b.style.display='flex'}else{b.style.display='none'}}
// Do-not-disturb (session) + per-type greeting dedupe
function isDnd(){try{return sessionStorage.getItem(DND_KEY)==='1'}catch(e){return false}}
function setDnd(){try{sessionStorage.setItem(DND_KEY,'1')}catch(e){}}
function greetedTypes(){try{return JSON.parse(localStorage.getItem(GREET_KEY)||'[]')||[]}catch(e){return[]}}
function markGreeted(t){var a=greetedTypes();if(a.indexOf(t)<0){a.push(t);try{localStorage.setItem(GREET_KEY,JSON.stringify(a))}catch(e){}}}
// Suggestion bubble
var noteTimer=null;
function showNote(text){
  if(isDnd()||isOpen||widgetHidden)return;
  var n=$('cf-note'),tx=$('cf-note-tx');if(!n||!tx)return;
  tx.textContent=text;n.classList.add('show');
  if(noteTimer)clearTimeout(noteTimer);
  noteTimer=setTimeout(hideNote,(notifTimeout||20)*1000);
}
function hideNote(){var n=$('cf-note');if(n)n.classList.remove('show');if(noteTimer){clearTimeout(noteTimer);noteTimer=null}}
// Core: decide + show + persist the page greeting (one per page_type / session)
function maybeGreet(){
  if(!cfgReady||widgetHidden||!proactiveEnabled||isOpen)return;
  var path=location.pathname||'/';
  var rule=cfMatchRule(pageRules,path);
  if(!rule||rule.greeting_enabled===false||!rule.greeting_message)return;
  var pt=rule.page_type||cfClassify(path);
  if(greetedTypes().indexOf(pt)>=0)return;
  markGreeted(pt);
  var pname=(pt==='product')?cfProductName():'';
  var text=cfGreetText(rule,pname);
  var introDone=false;try{introDone=localStorage.getItem(INTRO_KEY)==='1'}catch(e){}
  if(!introDone&&assistantIntro){text=assistantIntro+' '+text;try{localStorage.setItem(INTRO_KEY,'1')}catch(e){}}
  bumpUnread();
  showNote(text);
  try{fetch(B+'/api/chat/page-message/',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({session_id:sid,client_id:C,page_url:location.href,page_type:pt,product_name:pname})}).catch(function(){})}catch(e){}
}
// Re-fetch the server transcript so persisted greetings appear when opened.
function refreshTranscript(){
  fetch(B+'/api/chat/session/'+encodeURIComponent(sid)+'/messages/?limit=50')
    .then(function(r){return r.ok?r.json():null})
    .then(function(d){if(d&&Array.isArray(d.messages)&&d.messages.length)renderServerMsgs(d.messages)})
    .catch(function(){});
}
// Auto-close idle timer
var lastActivity=Date.now();
function resetIdle(){lastActivity=Date.now()}
setInterval(function(){
  if(autoCloseSeconds>0&&isOpen&&(Date.now()-lastActivity)/1000>=autoCloseSeconds)toggleOpen();
},2000);
// Re-evaluate visibility + greeting on SPA route changes
function cfOnNav(){
  if(!cfgReady)return;
  applyVisibility();
  maybeGreet();
}
(function(){
  try{
    var _ps=history.pushState;history.pushState=function(){var r=_ps.apply(this,arguments);try{cfOnNav()}catch(e){}return r};
    var _rs=history.replaceState;history.replaceState=function(){var r=_rs.apply(this,arguments);try{cfOnNav()}catch(e){}return r};
    window.addEventListener('popstate',function(){try{cfOnNav()}catch(e){}});
  }catch(e){}
})();
function applyVisibility(){
  var w=$('cf-w');if(!w)return;
  var vr=cfMatchRule(pageRules,location.pathname||'/');
  widgetHidden=!!(vr&&vr.enabled_widget===false);
  w.style.display=widgetHidden?'none':'';
  if(widgetHidden)hideNote();
}

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
  // Widget style (Style 1 'classic' pill · Style 2 'assistant' card)
  var styleA=(cfg.widget_style==='assistant');
  if(w)w.setAttribute('data-cf-style',styleA?'assistant':'classic');
  if(cfg.voice_input_enabled)$('cf-vb').style.display='flex';else $('cf-vb').style.display='none';
  // Image attach: classic uses #cf-ib, Style 2 uses #cf-mediab — never both.
  if(cfg.image_input_enabled&&!styleA)$('cf-ib').style.display='flex';else $('cf-ib').style.display='none';
  var _mb=$('cf-mediab');if(_mb)_mb.style.display=(styleA&&cfg.image_input_enabled)?'flex':'none';
  if(cfg.cta_message)liveCtaMsg=cfg.cta_message;
  // Page-aware proactive config
  if(Array.isArray(cfg.page_rules))pageRules=cfg.page_rules;
  if(typeof cfg.assistant_intro==='string')assistantIntro=cfg.assistant_intro;
  if(typeof cfg.proactive_enabled!=='undefined')proactiveEnabled=!!cfg.proactive_enabled;
  if(cfg.notification_timeout_seconds)notifTimeout=cfg.notification_timeout_seconds;
  if(typeof cfg.auto_close_seconds!=='undefined')autoCloseSeconds=cfg.auto_close_seconds||0;
  cfgReady=true;
  applyVisibility();
  renderBadge();
  maybeGreet();
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
    var a=attHtml(m.attachments);
    var body=m.message?((who==='ai')?renderMd(m.message):'<p>'+escHtml(m.message)+'</p>'):'';
    var html=a+body;
    if(!html)return; // skip truly empty entries
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
function escAttr(t){return String(t||'').replace(/"/g,'&quot;').replace(/'/g,'&#39;')}
// Build HTML for media attachments an agent sent during takeover (image/voice/file).
function attHtml(atts){
  if(!atts||!atts.length)return'';
  var out='';
  atts.forEach(function(a){
    var u=a&&a.url?escAttr(a.url):'';if(!u)return;
    if(a.kind==='image'){out+='<a href="'+u+'" target="_blank" rel="noopener"><img class="cf-att-img" src="'+u+'" alt="attachment"/></a>';}
    else if(a.kind==='audio'){out+='<audio class="cf-att-aud" src="'+u+'" controls></audio>';}
    else{out+='<a class="cf-att-file" href="'+u+'" target="_blank" rel="noopener">\\uD83D\\uDCCE '+escHtml(a.name||'Download')+'</a>';}
  });
  return out?'<div class="cf-att-wrap">'+out+'</div>':'';
}

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
// Page-aware greetings (maybeGreet) are now the landing/navigation layer —
// they show as a non-intrusive bubble + badge instead of the old proactive_open
// which force-opened the window. Disabled to avoid double messaging.
// setTimeout(_sendProactive,10000);

function connect(){
  ws=new WebSocket(B.replace(/^https/,'wss').replace(/^http/,'ws')+'/ws/chat/'+C+'/'+sid+'/');
  ws.onopen=function(){sendVisitorMeta()};
  ws.onmessage=function(e){
    try{
      var d=JSON.parse(e.data);
      // QA #13 — no interrupting lead popup. The AI asks for contact details
      // conversationally and the server detects email/phone inline from the
      // visitor's own messages. We just open the window so the visitor sees
      // the AI's ask; we never pop the modal.
      if(d.type==='lead_capture_required'){
        if(!isOpen)toggleOpen();
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
      var _hasAtt=d.attachments&&d.attachments.length;
      if(d.type==='ai_message'&&(d.message||_hasAtt)){
        // Dedupe by server msg_id so the reply renders exactly once per tab.
        if(d.msg_id&&isSeen(d.msg_id))return;
        if(d.msg_id)markSeen(d.msg_id);
        // Render media attachments (agent takeover: photo/voice/file) + text.
        bubble(attHtml(d.attachments)+(d.message?renderMd(d.message):''),'ai');chime();
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
        var AUTO_OPEN=['afk_nudge','fomo','exit_intent','pricing_hesitation','add_to_cart_help','abandoned_form','deep_engagement','rage_click_help','high_intent_action','lead_captured'];
        if(AUTO_OPEN.indexOf(d.source)>=0&&!isOpen)toggleOpen();
        // Any bot message that arrives while the chat is closed counts as unread.
        else if(!isOpen)bumpUnread();
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
  // Capture the attached image BEFORE clearImg() wipes it — it must travel in
  // the payload below. Without this the image rendered in the chat but was
  // never sent to the server, so the AI replied "I can't see the image".
  var img=pendingImg;
  if(pendingImg){bubble(pendingImg,'img');clearImg()}
  var msg=text||'[User sent an image]';
  bubble(escHtml(msg),'me');
  $('cf-inp').value='';$('cf-sb').disabled=true;busy=true;dots();
  // QA #13 — no auto lead popup. The AI asks for contact details in-conversation
  // and the server captures any email/phone the visitor types. (msgCount kept
  // for any other heuristics that read it.)
  msgCount++;
  // Tag with a client msg_id so when the server echoes this message to the
  // session group (for other tabs), THIS tab dedupes and doesn't re-render it.
  var mid=newMsgId();markSeen(mid);
  var payload={message:msg,msg_id:mid,behavior_matrix:behavior,page_visits:buildPageVisits()};
  if(img)payload.image_data=img;
  var pl=JSON.stringify(payload);
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
  if(isOpen){
    $('cf-win').classList.add('open');$('cf-pill').style.display='none';
    hideNote();
    var hadUnread=getUnread()>0;
    clearUnread();              // read & clear — those messages won't re-badge
    if(hadUnread)refreshTranscript();   // surface persisted page greetings
    resetIdle();
    if(!ws)connect();
  }else{
    $('cf-win').classList.remove('open');$('cf-pill').style.display='flex';
    renderBadge();
  }}

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
$('cf-inp').addEventListener('keydown',function(e){resetIdle();if(e.key==='Enter')send()});
$('cf-inp').addEventListener('input',function(){resetIdle();$('cf-sb').disabled=!this.value.trim()&&!pendingImg});
// Suggestion bubble: click body → open chat; click X → do-not-disturb (session)
$('cf-note').onclick=function(e){if(e&&e.target&&e.target.id==='cf-note-x')return;hideNote();if(!isOpen)toggleOpen()};
$('cf-note-x').onclick=function(e){if(e){e.stopPropagation()}hideNote();setDnd()};
renderBadge();
$('cf-ib').onclick=function(){$('cf-fi').click()};
$('cf-fi').onchange=function(){handleFile(this.files[0]);this.value=''};
$('cf-prm').onclick=clearImg;
$('cf-vb').onclick=toggleVoice;
// Style 2 — media button opens the image picker; emoji picker inserts into input.
var _cfMediab=$('cf-mediab');if(_cfMediab)_cfMediab.onclick=function(){$('cf-fi').click()};
var _cfEmoji=$('cf-emoji'),_cfEpick=$('cf-emojipick');
if(_cfEmoji&&_cfEpick){
  _cfEmoji.onclick=function(e){e.stopPropagation();_cfEpick.hidden=!_cfEpick.hidden};
  Array.prototype.forEach.call(_cfEpick.querySelectorAll('button'),function(b){
    b.onclick=function(){var inp=$('cf-inp');inp.value+=b.textContent;try{inp.dispatchEvent(new Event('input'))}catch(e){}inp.focus();_cfEpick.hidden=true};
  });
  document.addEventListener('click',function(ev){if(!ev.target.closest||!ev.target.closest('.cf-emojiwrap'))_cfEpick.hidden=true});
}
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
    // theme-check-disable wraps the vendored block so Shopify's linter
    // doesn't flag our self-contained widget (img width/height, remote
    // asset, inline script, etc.) — these are best-practice hints meant for
    // theme authors, not a third-party snippet that must stay self-hosted.
    return [
      '{% comment %}',
      '  Checkfunnel AI chat widget — paste this block right before',
      '  </body> in Layout/theme.liquid (Online Store → Themes → Edit code).',
      '  Branding, color, name, and CTA stay live-editable from the',
      '  Checkfunnel portal — no re-paste needed.',
      '  PASTE ONCE: if you already have a "Start of Checkfunnel code" block,',
      '  replace it — do not add a second copy.',
      '{% endcomment %}',
      '{% # theme-check-disable %}',
      fullSnippet,
      '{% # theme-check-enable %}',
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
