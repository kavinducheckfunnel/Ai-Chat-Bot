/**
 * Generates a fully self-contained chat widget embed snippet.
 * Lives in a plain .js file so the Vue SFC tokeniser never sees
 * <style>, </style>, <script>, </script> etc. as real HTML tags.
 */

function darkenHex(hex, amt = 28) {
  const n = parseInt((hex || '#6366f1').replace('#', ''), 16)
  const r = Math.max(0, (n >> 16) - amt)
  const g = Math.max(0, ((n >> 8) & 0xff) - amt)
  const b = Math.max(0, (n & 0xff) - amt)
  return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')
}

export function generateEmbedCode(id, url, color, botName, format) {
  const dark = darkenHex(color)
  const name = (botName || 'AI Assistant').replace(/'/g, "\\'")

  const css = `<style>
#cf-w{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,sans-serif}
#cf-btn{position:fixed;bottom:24px;right:24px;width:58px;height:58px;border-radius:50%;background:${color};border:none;cursor:pointer;z-index:2147483647;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 18px ${color}55;transition:transform .2s;animation:cf-pulse 3s ease-in-out infinite}
#cf-btn:hover{transform:scale(1.09)}
@keyframes cf-pulse{0%,100%{box-shadow:0 4px 18px ${color}55,0 0 0 0 ${color}33}60%{box-shadow:0 4px 18px ${color}55,0 0 0 10px transparent}}
#cf-win{position:fixed;bottom:94px;right:24px;width:370px;background:#fff;border-radius:20px;box-shadow:0 24px 64px rgba(0,0,0,0.14),0 4px 18px rgba(0,0,0,0.07);z-index:2147483647;overflow:hidden;display:none;flex-direction:column}
#cf-win.open{display:flex;animation:cf-in .24s cubic-bezier(.34,1.56,.64,1) forwards}
@keyframes cf-in{from{opacity:0;transform:translateY(14px) scale(.97)}to{opacity:1;transform:translateY(0) scale(1)}}
#cf-head{background:linear-gradient(135deg,${color},${dark});padding:16px 18px;display:flex;align-items:center;gap:12px;flex-shrink:0}
.cf-av{width:40px;height:40px;border-radius:50%;background:rgba(255,255,255,.22);display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}
.cf-hi{flex:1;min-width:0}
.cf-hn{font-size:14px;font-weight:700;color:#fff;letter-spacing:-.2px}
.cf-hs{font-size:11px;color:rgba(255,255,255,.82);display:flex;align-items:center;gap:5px;margin-top:2px}
.cf-dot{width:7px;height:7px;border-radius:50%;background:#4ade80;flex-shrink:0}
#cf-xb{background:rgba(255,255,255,.18);border:none;color:#fff;width:30px;height:30px;border-radius:50%;cursor:pointer;font-size:18px;display:flex;align-items:center;justify-content:center;transition:background .15s;flex-shrink:0}
#cf-xb:hover{background:rgba(255,255,255,.32)}
#cf-msgs{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px;background:#f7f8fc;min-height:180px;max-height:320px}
#cf-msgs::-webkit-scrollbar{width:4px}
#cf-msgs::-webkit-scrollbar-thumb{background:#e2e8f0;border-radius:4px}
.cf-ai,.cf-me{padding:10px 14px;border-radius:18px;font-size:14px;line-height:1.55;max-width:84%;animation:cf-pop .2s ease;word-break:break-word}
@keyframes cf-pop{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:translateY(0)}}
.cf-ai{background:#fff;color:#1e293b;align-self:flex-start;border-bottom-left-radius:4px;border:1px solid #edf0f4;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.cf-me{background:${color};color:#fff;align-self:flex-end;border-bottom-right-radius:4px}
.cf-typing{align-self:flex-start;background:#fff;border:1px solid #edf0f4;border-radius:18px;border-bottom-left-radius:4px;padding:12px 16px;display:flex;gap:5px;align-items:center;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.cf-typing span{width:7px;height:7px;background:#c8d0db;border-radius:50%;display:inline-block;animation:cf-bop 1.3s infinite ease-in-out}
.cf-typing span:nth-child(2){animation-delay:.18s}
.cf-typing span:nth-child(3){animation-delay:.36s}
@keyframes cf-bop{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-6px)}}
#cf-foot{display:flex;gap:8px;padding:12px 14px;background:#fff;border-top:1px solid #f0f2f5;flex-shrink:0}
#cf-inp{flex:1;padding:10px 16px;border:1.5px solid #e8ecf0;border-radius:24px;outline:none;font-size:14px;font-family:inherit;background:#f7f8fc;color:#1e293b;transition:border-color .2s,background .2s}
#cf-inp:focus{border-color:${color};background:#fff}
#cf-inp::placeholder{color:#adb5c4}
#cf-sb{width:40px;height:40px;border-radius:50%;background:${color};border:none;color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:opacity .15s,transform .15s}
#cf-sb:hover:not(:disabled){opacity:.88;transform:scale(1.07)}
#cf-sb:disabled{opacity:.35;cursor:not-allowed}
#cf-pby{text-align:center;font-size:10px;color:#c4cdd8;padding:5px 0 8px;background:#fff}
#cf-pby a{color:#b0bac8;text-decoration:none}
</style>`

  const html = `<div id="cf-w">
<button id="cf-btn" aria-label="Open chat">
<svg width="26" height="26" viewBox="0 0 24 24" fill="white"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
</button>
<div id="cf-win" role="dialog">
<div id="cf-head">
<div class="cf-av">&#129302;</div>
<div class="cf-hi"><div class="cf-hn">${name}</div><div class="cf-hs"><span class="cf-dot"></span>Online</div></div>
<button id="cf-xb" aria-label="Close">&#10005;</button>
</div>
<div id="cf-msgs"><div class="cf-ai">&#128075; Hi! How can I help you today?</div></div>
<div id="cf-foot">
<input id="cf-inp" type="text" placeholder="Type a message&#8230;" autocomplete="off">
<button id="cf-sb" aria-label="Send" disabled>
<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
</button>
</div>
<div id="cf-pby">Powered by <a href="https://checkfunnels.com" target="_blank" rel="noopener">Checkfunnels</a></div>
</div>
</div>`

  const js = `<script>
(function(){
var C='${id}',B='${url}';
var sid='xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,function(c){var r=Math.random()*16|0;return(c=='x'?r:(r&3|8)).toString(16)});
var ws=null,played=false,busy=false;
var $=function(id){return document.getElementById(id)};

function chime(){try{var a=new(window.AudioContext||window.webkitAudioContext)();[[880,0],[1100,.2]].forEach(function(t){var o=a.createOscillator(),g=a.createGain();o.connect(g);g.connect(a.destination);o.type='sine';o.frequency.value=t[0];g.gain.setValueAtTime(0,a.currentTime+t[1]);g.gain.linearRampToValueAtTime(.14,a.currentTime+t[1]+.03);g.gain.exponentialRampToValueAtTime(.001,a.currentTime+t[1]+.3);o.start(a.currentTime+t[1]);o.stop(a.currentTime+t[1]+.3)});setTimeout(function(){a.close()},1200)}catch(e){}}

function bubble(text,who){var d=document.createElement('div');d.className=who==='ai'?'cf-ai':'cf-me';d.textContent=text;$('cf-msgs').appendChild(d);$('cf-msgs').scrollTop=9999}
function showDots(){var d=document.createElement('div');d.className='cf-typing';d.id='cf-typ';d.innerHTML='<span></span><span></span><span></span>';$('cf-msgs').appendChild(d);$('cf-msgs').scrollTop=9999}
function rmDots(){var t=$('cf-typ');if(t)t.remove()}

function connect(){
  ws=new WebSocket(B.replace(/^https/,'wss').replace(/^http/,'ws')+'/ws/chat/'+C+'/'+sid+'/');
  ws.onmessage=function(e){rmDots();busy=false;$('cf-sb').disabled=!$('cf-inp').value.trim();try{var d=JSON.parse(e.data);if(d.type==='ai_message'&&d.message)bubble(d.message,'ai')}catch(x){}};
  ws.onerror=function(){rmDots();busy=false};
  ws.onclose=function(){ws=null};
}

function send(){
  var text=$('cf-inp').value.trim();if(!text||busy)return;
  bubble(text,'user');$('cf-inp').value='';$('cf-sb').disabled=true;busy=true;showDots();
  var pl=JSON.stringify({message:text});
  if(ws&&ws.readyState===1){ws.send(pl)}
  else{connect();ws.addEventListener('open',function(){ws.send(pl)},{once:true})}
}

$('cf-btn').onclick=function(){
  var w=$('cf-win'),open=w.classList.toggle('open');
  if(open){if(!ws)connect();if(!played){played=true;setTimeout(chime,400)}}
};
$('cf-xb').onclick=function(){$('cf-win').classList.remove('open')};
$('cf-sb').onclick=send;
$('cf-inp').addEventListener('keydown',function(e){if(e.key==='Enter')send()});
$('cf-inp').addEventListener('input',function(){$('cf-sb').disabled=!this.value.trim()||busy});
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
