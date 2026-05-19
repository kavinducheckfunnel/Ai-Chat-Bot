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

/* ── Messages ── */
#cf-msgs { flex: 1; overflow-y: auto; padding: 14px;
  display: flex; flex-direction: column; gap: 9px; background: var(--cf-bg);
  min-height: 180px; max-height: 340px;
  scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.1) transparent; }
#cf-msgs::-webkit-scrollbar { width: 4px; }
#cf-msgs::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
.cf-ai, .cf-me { padding: 13px 18px; border-radius: 18px; font-size: 14px;
  line-height: 1.6; max-width: 82%; animation: cf-mi .2s ease; word-break: break-word; }
.cf-me { padding: 12px 20px; }  /* user bubble: slightly tighter vertical, more horizontal */
@keyframes cf-mi { from { opacity: 0; transform: translateY(7px); }
  to { opacity: 1; transform: translateY(0); } }
.cf-ai { background: var(--cf-bubble-ai); color: var(--cf-text);
  align-self: flex-start; border-bottom-left-radius: 6px; border: 1px solid var(--cf-border-soft); }
.cf-me { background: var(--cf-accent); color: #fff;
  align-self: flex-end; border-bottom-right-radius: 6px; }
.cf-img-msg { align-self: flex-end; max-width: 180px; border-radius: 12px;
  object-fit: cover; display: block; border: 1px solid rgba(255,255,255,0.08); }
.cf-ai ol { margin: 6px 0 4px 0; padding-left: 22px; list-style-type: decimal; }
.cf-ai li { margin-bottom: 8px; color: var(--cf-text); line-height: 1.55; display: list-item; padding-left: 4px; }
.cf-ai li:last-child { margin-bottom: 2px; }
.cf-ai p { margin: 0 0 7px 0; color: var(--cf-text); }
.cf-ai p:last-child { margin-bottom: 0; }
.cf-ai a { color: #a5b4fc; text-decoration: underline; font-weight: 500; word-break: break-word; }
.cf-ai a:hover { color: #c4b5fd; }
.cf-ai strong { color: var(--cf-text-strong); font-weight: 700; }

/* ── Reactions ── */
.cf-rxn { display: flex; gap: 4px; margin-top: 5px; }
.cf-rb { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
  border-radius: 20px; padding: 2px 8px; font-size: 11px; cursor: pointer;
  transition: all .15s; color: rgba(255,255,255,0.45); }
.cf-rb:hover { background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.75); }
.cf-rb.on { background: rgba(99,102,241,0.2); border-color: rgba(99,102,241,0.4); color: #a5b4fc; }

/* ── Typing ── */
.cf-typ { align-self: flex-start; background: var(--cf-bubble-ai);
  border: 1px solid var(--cf-border-soft); border-radius: 18px;
  border-bottom-left-radius: 4px; padding: 11px 15px; display: flex; gap: 5px; align-items: center; }
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
#cf-w[data-cf-theme="light"] .cf-rb { background: #e2e8f0; border-color: #cbd5e1; color: #475569; }
#cf-w[data-cf-theme="light"] .cf-rb:hover { background: #cbd5e1; color: #1e293b; }
#cf-w[data-cf-theme="light"] .cf-rb.on { background: rgba(99,102,241,0.15); border-color: rgba(99,102,241,0.4); color: #4338ca; }
#cf-w[data-cf-theme="light"] .cf-typ { background: #f1f5f9; border-color: #e2e8f0; }
#cf-w[data-cf-theme="light"] .cf-typ span { background: #94a3b8; }
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
    <input class="cf-lead-inp" id="cf-lead-em" type="email" placeholder="your@email.com"/>
    <button class="cf-lead-btn" id="cf-lead-sb">Send</button>
  </div>
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
// session_id (sid) lives in sessionStorage  → one per tab visit
// visitor_uid (vid) lives in localStorage   → one per browser across days
// Both are client-scoped so the same browser visiting different tenants
// never gets merged into one visitor record.
function newUuid(){return'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,function(c){var r=Math.random()*16|0;return(c=='x'?r:(r&3|8)).toString(16)})}
var SK='__cf_sid_'+C;
var VK='__cf_vid_'+C;
var sid=sessionStorage.getItem(SK);
if(!sid){sid=newUuid();sessionStorage.setItem(SK,sid)}
var vid=localStorage.getItem(VK);
if(!vid){vid=newUuid();localStorage.setItem(VK,vid)}

var ws=null,busy=false,recording=false,pendingImg=null,recognition=null;
var msgCount=0,liveCtaMsg=null;
var LEAD_KEY='cf_lead_'+C;
var leadDone=!!localStorage.getItem(LEAD_KEY);
var $=function(id){return document.getElementById(id)};

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
    return'<a href="'+l.u+'" target="_blank" rel="noopener noreferrer">'+st+'</a>'
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
function submitLead(){
  var em=($('cf-lead-em').value||'').trim();if(!em)return;
  $('cf-lead-sb').disabled=true;$('cf-lead-sb').textContent='…';
  fetch(B+'/api/chat/lead/',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({session_id:sid,email:em,phone:null})
  }).catch(function(){}).finally(function(){
    dismissLead();bubble('<p>✅ Thanks! We\\'ll be in touch soon.</p>','ai')})}

// ── Chime ────────────────────────────────────────────────────────────
function chime(){if(!isOpen)return;try{var a=new(window.AudioContext||window.webkitAudioContext)();[[880,0],[1100,.14],[1320,.26]].forEach(function(t){var o=a.createOscillator(),g=a.createGain();o.connect(g);g.connect(a.destination);o.type='sine';o.frequency.value=t[0];var st=a.currentTime+t[1];g.gain.setValueAtTime(0,st);g.gain.linearRampToValueAtTime(.09,st+.04);g.gain.exponentialRampToValueAtTime(.001,st+.38);o.start(st);o.stop(st+.38)});setTimeout(function(){a.close()},1400)}catch(e){}}

// ── DOM helpers ──────────────────────────────────────────────────────
function bubble(html,who){
  var d=document.createElement('div');
  if(who==='img'){d.innerHTML='<img class="cf-img-msg" src="'+html+'" alt="image"/>';$('cf-msgs').appendChild(d.firstChild)}
  else{d.className=who==='ai'?'cf-ai':'cf-me';d.innerHTML=html;
  if(who==='ai'){var rx=document.createElement('div');rx.className='cf-rxn';['\\uD83D\\uDC4D','\\uD83D\\uDC4E'].forEach(function(e){var b=document.createElement('button');b.className='cf-rb';b.textContent=e;b.onclick=function(){b.classList.toggle('on');Array.from(rx.children).forEach(function(x){if(x!==b)x.classList.remove('on')})};rx.appendChild(b)});d.appendChild(rx)}
  $('cf-msgs').appendChild(d)}
  $('cf-msgs').scrollTop=9999}
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
function connect(){
  ws=new WebSocket(B.replace(/^https/,'wss').replace(/^http/,'ws')+'/ws/chat/'+C+'/'+sid+'/');
  ws.onopen=function(){sendVisitorMeta()};
  ws.onmessage=function(e){rmDots();busy=false;$('cf-sb').disabled=!$('cf-inp').value.trim()&&!pendingImg;
    try{var d=JSON.parse(e.data);if(d.type==='ai_message'&&d.message){
      bubble(renderMd(d.message),'ai');chime();
      var AUTO_OPEN=['afk_nudge','fomo','exit_intent','pricing_hesitation','add_to_cart_help','abandoned_form','deep_engagement','rage_click_help','high_intent_action'];
      if(AUTO_OPEN.indexOf(d.source)>=0&&!isOpen)toggleOpen();
    }}catch(x){}};
  ws.onerror=function(){rmDots();busy=false};
  ws.onclose=function(){ws=null;sentVisitorMeta=false}}

// Open WebSocket ON LOAD so visitor_meta + page_visits get saved
// even before the visitor opens the chat — backend can then use this
// browsing context when AI generates the first reply.
setTimeout(connect,500);

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
  var pl=JSON.stringify({message:msg,behavior_matrix:behavior,page_visits:buildPageVisits()});
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

// Exit intent
document.addEventListener('mouseleave',function(e){
  if(e.clientY>20||behavior.exitIntentFired||behavior.timeOnSite<5)return;
  behavior.exitIntentFired=true;flush(true);fireTrigger('exit_intent');
});

// Time on site + deep engagement trigger
setInterval(function(){
  behavior.timeOnSite=Math.round((Date.now()-startTime)/1000);
  if(behavior.timeOnSite>=90&&behavior.scrollDepth>=75&&!behavior._deepFired){
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
window.addEventListener('beforeunload',function(){flush(true)});

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
})();
</` + `script>`

  // ───────────── Format wrappers ─────────────────
  const fullSnippet = '<!-- Start of Checkfunnel code -->\n' + css + '\n' + html + '\n' + js + '\n<!-- End of Checkfunnel code -->'

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
