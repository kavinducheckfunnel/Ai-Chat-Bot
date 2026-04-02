/**
 * Generates a fully self-contained chat widget embed snippet.
 * Lives in a plain .js file so the Vue SFC tokeniser never sees
 * <style>, </style>, <script>, </script> etc. as real HTML tags.
 *
 * Features:
 *  - Dark pill-bar idle state (replaces round bubble)
 *  - Full dark chat window
 *  - Session ID persisted in sessionStorage (no "new visitor" on refresh)
 *  - Loads voice_input_enabled / image_input_enabled from widget-config API
 *  - Voice input via Web Speech API (if enabled)
 *  - Image attach + thumbnail preview (if enabled)
 *  - 👍 👎 emoji reactions on AI messages
 *  - Gentle 3-note chime when AI replies (only when chat is open)
 */

export function generateEmbedCode(id, url, color, botName, format) {
  const name = (botName || 'AI Assistant').replace(/'/g, "\\'")

  const css = `<style>
#cf-w*{box-sizing:border-box;margin:0;padding:0}
#cf-w{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,sans-serif;position:fixed;bottom:24px;right:24px;z-index:2147483647;display:flex;flex-direction:column;align-items:flex-end;gap:0}

/* ── Pill bar (idle) ── */
#cf-pill{display:flex;align-items:center;gap:10px;padding:9px 11px 9px 9px;background:rgba(17,17,17,0.97);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,0.08);border-radius:100px;cursor:pointer;box-shadow:0 8px 32px rgba(0,0,0,0.5);transition:transform .2s,box-shadow .2s;min-width:220px;user-select:none;animation:cf-pi .3s cubic-bezier(.34,1.56,.64,1) forwards}
@keyframes cf-pi{from{opacity:0;transform:translateY(12px) scale(.95)}to{opacity:1;transform:translateY(0) scale(1)}}
#cf-pill:hover{transform:translateY(-2px);box-shadow:0 12px 40px rgba(0,0,0,0.55)}
.cf-pi-icon{width:32px;height:32px;border-radius:50%;background:${color};display:flex;align-items:center;justify-content:center;flex-shrink:0}
.cf-pi-txt{flex:1;font-size:13px;color:rgba(255,255,255,0.4);font-weight:400;white-space:nowrap}
.cf-pi-send{width:30px;height:30px;border-radius:50%;background:${color};display:flex;align-items:center;justify-content:center;flex-shrink:0}

/* ── Chat window ── */
#cf-win{position:absolute;bottom:0;right:0;width:370px;background:#111111;border-radius:20px;border:1px solid rgba(255,255,255,0.07);box-shadow:0 24px 64px rgba(0,0,0,0.65);display:none;flex-direction:column;overflow:hidden;max-height:600px}
#cf-win.open{display:flex;animation:cf-wi .28s cubic-bezier(.34,1.56,.64,1) forwards}
@keyframes cf-wi{from{opacity:0;transform:translateY(14px) scale(.97)}to{opacity:1;transform:translateY(0) scale(1)}}

/* ── Header ── */
#cf-head{background:#161616;border-bottom:1px solid rgba(255,255,255,0.06);padding:13px 15px;display:flex;align-items:center;gap:10px;flex-shrink:0}
.cf-av{width:36px;height:36px;border-radius:50%;background:${color};display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0}
.cf-hi{flex:1;min-width:0}
.cf-hn{font-size:14px;font-weight:600;color:#f1f5f9;letter-spacing:-.2px}
.cf-hs{font-size:11px;color:#64748b;display:flex;align-items:center;gap:4px;margin-top:2px}
.cf-dot{width:6px;height:6px;border-radius:50%;background:#4ade80;flex-shrink:0}
#cf-xb{background:rgba(255,255,255,0.06);border:none;color:#94a3b8;width:28px;height:28px;border-radius:50%;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;transition:background .15s;flex-shrink:0}
#cf-xb:hover{background:rgba(255,255,255,0.12);color:#f1f5f9}

/* ── Messages ── */
#cf-msgs{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:9px;background:#111111;min-height:180px;max-height:340px;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,0.1) transparent}
#cf-msgs::-webkit-scrollbar{width:4px}
#cf-msgs::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:4px}
.cf-ai,.cf-me{padding:10px 14px;border-radius:18px;font-size:14px;line-height:1.55;max-width:84%;animation:cf-mi .2s ease;word-break:break-word}
@keyframes cf-mi{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:translateY(0)}}
.cf-ai{background:#1e2433;color:#e2e8f0;align-self:flex-start;border-bottom-left-radius:4px;border:1px solid rgba(255,255,255,0.06)}
.cf-me{background:${color};color:#fff;align-self:flex-end;border-bottom-right-radius:4px}
.cf-img-msg{align-self:flex-end;max-width:180px;border-radius:12px;object-fit:cover;display:block;border:1px solid rgba(255,255,255,0.08)}

/* ── Reactions ── */
.cf-rxn{display:flex;gap:4px;margin-top:5px}
.cf-rb{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.08);border-radius:20px;padding:2px 8px;font-size:11px;cursor:pointer;transition:all .15s;color:rgba(255,255,255,0.45)}
.cf-rb:hover{background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.75)}
.cf-rb.on{background:rgba(99,102,241,0.2);border-color:rgba(99,102,241,0.4);color:#a5b4fc}

/* ── Typing ── */
.cf-typ{align-self:flex-start;background:#1e2433;border:1px solid rgba(255,255,255,0.06);border-radius:18px;border-bottom-left-radius:4px;padding:11px 15px;display:flex;gap:5px;align-items:center}
.cf-typ span{width:7px;height:7px;background:#475569;border-radius:50%;display:inline-block;animation:cf-bop 1.3s infinite ease-in-out}
.cf-typ span:nth-child(2){animation-delay:.18s}
.cf-typ span:nth-child(3){animation-delay:.36s}
@keyframes cf-bop{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-6px)}}

/* ── Image preview ── */
#cf-imgprev{padding:8px 13px 0;background:#111111;display:none}
#cf-imgprev.has-img{display:block}
.cf-prev-wrap{position:relative;display:inline-block}
.cf-prev-thumb{width:52px;height:52px;border-radius:8px;object-fit:cover;display:block;border:1px solid rgba(255,255,255,0.1)}
.cf-prev-rm{position:absolute;top:-5px;right:-5px;width:17px;height:17px;border-radius:50%;background:#ef4444;border:none;color:white;font-size:10px;cursor:pointer;display:flex;align-items:center;justify-content:center;line-height:1}

/* ── Input area ── */
#cf-foot{display:flex;gap:7px;padding:10px 12px;background:#161616;border-top:1px solid rgba(255,255,255,0.06);flex-shrink:0;align-items:center}
.cf-mb{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.08);color:#64748b;width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0;transition:all .15s}
.cf-mb:hover{background:rgba(255,255,255,0.1);color:#94a3b8}
.cf-mb.rec{background:rgba(239,68,68,0.15);border-color:rgba(239,68,68,0.4);color:#f87171;animation:cf-prec 1s ease-in-out infinite}
@keyframes cf-prec{0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,0.3)}50%{box-shadow:0 0 0 5px transparent}}
#cf-inp{flex:1;padding:9px 14px;border:1px solid rgba(255,255,255,0.08);border-radius:20px;outline:none;font-size:13px;font-family:inherit;background:rgba(255,255,255,0.05);color:#e2e8f0;transition:border-color .2s,background .2s}
#cf-inp:focus{border-color:rgba(99,102,241,0.4);background:rgba(255,255,255,0.07)}
#cf-inp::placeholder{color:rgba(255,255,255,0.25)}
#cf-inp:disabled{opacity:.5;cursor:not-allowed}
#cf-sb{width:36px;height:36px;border-radius:50%;background:${color};border:none;color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:opacity .15s,transform .15s}
#cf-sb:hover:not(:disabled){opacity:.85;transform:scale(1.07)}
#cf-sb:disabled{opacity:.3;cursor:not-allowed}
#cf-pby{text-align:center;font-size:10px;color:rgba(255,255,255,0.2);padding:5px 0 7px;background:#161616}
#cf-pby a{color:rgba(255,255,255,0.3);text-decoration:none}
</style>`

  const html = `<div id="cf-w">
<div id="cf-win" role="dialog" aria-label="Chat with ${name}">
<div id="cf-head">
<div class="cf-av">&#9889;</div>
<div class="cf-hi"><div class="cf-hn">${name}</div><div class="cf-hs"><span class="cf-dot"></span>Online</div></div>
<button id="cf-xb" aria-label="Close">&#10005;</button>
</div>
<div id="cf-msgs"><div class="cf-ai">&#128075; Hi! How can I help you today?</div></div>
<div id="cf-imgprev"><div class="cf-prev-wrap"><img class="cf-prev-thumb" id="cf-pt" src="" alt=""/><button class="cf-prev-rm" id="cf-prm">&#10005;</button></div></div>
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

  const js = `<script>
(function(){
var C='${id}',B='${url}';

// ── Session persistence (no "new visitor" on refresh) ──────────────────
var SK='__cf_sid__';
var sid=sessionStorage.getItem(SK);
if(!sid){sid='xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,function(c){var r=Math.random()*16|0;return(c=='x'?r:(r&3|8)).toString(16)});sessionStorage.setItem(SK,sid)}

var ws=null,busy=false,recording=false,pendingImg=null,recognition=null;
var voiceEnabled=false,imageEnabled=false;
var $=function(id){return document.getElementById(id)};

// ── Chime on AI reply ──────────────────────────────────────────────────
function chime(){if(!open)return;try{var a=new(window.AudioContext||window.webkitAudioContext)();[[880,0],[1100,.14],[1320,.26]].forEach(function(t){var o=a.createOscillator(),g=a.createGain();o.connect(g);g.connect(a.destination);o.type='sine';o.frequency.value=t[0];var st=a.currentTime+t[1];g.gain.setValueAtTime(0,st);g.gain.linearRampToValueAtTime(.09,st+.04);g.gain.exponentialRampToValueAtTime(.001,st+.38);o.start(st);o.stop(st+.38)});setTimeout(function(){a.close()},1400)}catch(e){}}

// ── DOM helpers ────────────────────────────────────────────────────────
function bubble(html,who,extra){
  var d=document.createElement('div');
  if(who==='img'){d.innerHTML='<img class="cf-img-msg" src="'+html+'" alt="image"/>';$('cf-msgs').appendChild(d.firstChild)}
  else{d.className=who==='ai'?'cf-ai':'cf-me';d.innerHTML=html;
  if(who==='ai'){var rx=document.createElement('div');rx.className='cf-rxn';['\\uD83D\\uDC4D','\\uD83D\\uDC4E'].forEach(function(e){var b=document.createElement('button');b.className='cf-rb';b.textContent=e;b.onclick=function(){var on=b.classList.toggle('on');Array.from(rx.children).forEach(function(x){if(x!==b)x.classList.remove('on')})};rx.appendChild(b)});d.appendChild(rx)}
  $('cf-msgs').appendChild(d)}
  $('cf-msgs').scrollTop=9999}
function dots(){var d=document.createElement('div');d.className='cf-typ';d.id='cf-tdots';d.innerHTML='<span></span><span></span><span></span>';$('cf-msgs').appendChild(d);$('cf-msgs').scrollTop=9999}
function rmDots(){var t=$('cf-tdots');if(t)t.remove()}
function setPlaceholder(txt){$('cf-inp').placeholder=txt}

// ── WebSocket ──────────────────────────────────────────────────────────
var open=false;
function connect(){
  ws=new WebSocket(B.replace(/^https/,'wss').replace(/^http/,'ws')+'/ws/chat/'+C+'/'+sid+'/');
  ws.onmessage=function(e){rmDots();busy=false;$('cf-sb').disabled=!$('cf-inp').value.trim()&&!pendingImg;
    try{var d=JSON.parse(e.data);if(d.type==='ai_message'&&d.message){bubble(escHtml(d.message),'ai');chime()}}catch(x){}};
  ws.onerror=function(){rmDots();busy=false};
  ws.onclose=function(){ws=null}}

// ── Send ───────────────────────────────────────────────────────────────
function send(){
  var text=$('cf-inp').value.trim();
  if((!text&&!pendingImg)||busy)return;
  if(pendingImg){bubble(pendingImg,'img');clearImg()}
  var msg=text||'[User sent an image]';
  bubble(escHtml(msg),'me');
  $('cf-inp').value='';$('cf-sb').disabled=true;busy=true;dots();
  var pl=JSON.stringify({message:msg});
  if(ws&&ws.readyState===1){ws.send(pl)}
  else{connect();ws.addEventListener('open',function(){ws.send(pl)},{once:true})}}

// ── Image handling ─────────────────────────────────────────────────────
function clearImg(){pendingImg=null;$('cf-imgprev').className='';$('cf-pt').src=''}
function handleFile(f){if(!f)return;var r=new FileReader();r.onload=function(ev){pendingImg=ev.target.result;$('cf-pt').src=pendingImg;$('cf-imgprev').className='has-img';$('cf-sb').disabled=false};r.readAsDataURL(f)}

// ── Voice ──────────────────────────────────────────────────────────────
function toggleVoice(){
  if(recording){if(recognition)recognition.stop();recording=false;$('cf-vb').classList.remove('rec');setPlaceholder('Type a message\u2026');return}
  var SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR)return;
  recognition=new SR();recognition.continuous=false;recognition.interimResults=false;recognition.lang='en-US';
  recognition.onresult=function(e){$('cf-inp').value=e.results[0][0].transcript;$('cf-sb').disabled=!$('cf-inp').value.trim();recording=false;$('cf-vb').classList.remove('rec');setPlaceholder('Type a message\u2026')};
  recognition.onerror=recognition.onend=function(){recording=false;$('cf-vb').classList.remove('rec');setPlaceholder('Type a message\u2026')};
  recognition.start();recording=true;$('cf-vb').classList.add('rec');setPlaceholder('\\uD83C\\uDFA4 Listening...')}

function escHtml(t){var d=document.createElement('div');d.textContent=t;return d.innerHTML}

// ── Load config (voice/image flags) ───────────────────────────────────
var configUrl=B+'/api/chat/widget-config/'+C+'/';
fetch(configUrl).then(function(r){return r.json()}).then(function(cfg){
  if(cfg.voice_input_enabled){voiceEnabled=true;$('cf-vb').style.display='flex'}
  if(cfg.image_input_enabled){imageEnabled=true;$('cf-ib').style.display='flex'}
}).catch(function(){});

// ── Toggle open/close ──────────────────────────────────────────────────
function toggleOpen(){
  open=!open;
  if(open){$('cf-win').classList.add('open');$('cf-pill').style.display='none';if(!ws)connect()}
  else{$('cf-win').classList.remove('open');$('cf-pill').style.display='flex'}}

// ── Event listeners ────────────────────────────────────────────────────
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
})();
` + '</' + 'script>'

  if (format === 'html') {
    return `<!-- Start of Checkfunnel code -->\n${css}\n${html}\n${js}\n<!-- End of Checkfunnel code -->`
  }

  if (format === 'wordpress') {
    const phpOpen = '<' + '?php'
    return `${phpOpen}
function checkfunnel_widget() { ?>
${css}
${html}
${js}
${phpOpen} }
add_action('wp_footer', 'checkfunnel_widget');`
  }

  if (format === 'react') {
    return `// Use the HTML tab to copy the full self-contained snippet.\n// Paste it via dangerouslySetInnerHTML or a useEffect that appends it to document.body.`
  }

  return ''
}
