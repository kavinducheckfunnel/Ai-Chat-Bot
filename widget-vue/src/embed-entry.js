/**
 * Auto-updating widget loader entry.
 *
 * Built to dist/assets/embed.js and served by Django at
 *   /widget/embed.js?client_id=<UUID>
 * The merchant pastes ONE stable line:
 *   <script async src="https://ai.checkfunnels.com/widget/embed.js?client_id=X"></script>
 * and every future widget fix ships from our server WITHOUT a re-paste —
 * the root-cause fix for "the update didn't apply on the host site."
 *
 * This reuses the EXACT same inline snippet produced by generateEmbedCode
 * (single source of truth — no duplicated widget logic), then self-injects
 * it into the host page: styles + markup go in via DOM, and the snippet's
 * <script> is re-created as an executable element (innerHTML scripts never
 * run on their own).
 */
import { generateEmbedCode } from './portal/embedCodeGenerator.js'

;(function () {
  try {
    // Dedupe — never inject twice (e.g. SPA re-mount or double include).
    if (document.getElementById('cf-w')) return

    var clientId = window.__CF_CLIENT_ID__
    if (!clientId) return
    var backend = (window.__CF_BACKEND_URL__ || window.location.origin).replace(/\/$/, '')
    var widgetUrl = backend + '/widget/widget.js'
    var color = window.__CF_COLOR__ || '#6366f1'
    var name = window.__CF_NAME__ || 'AI Assistant'

    var snippet = generateEmbedCode(clientId, widgetUrl, color, name, 'html')
    if (!snippet) return

    function mount() {
      if (document.getElementById('cf-w')) return
      var wrap = document.createElement('div')
      wrap.innerHTML = snippet
      var nodes = Array.prototype.slice.call(wrap.childNodes)
      nodes.forEach(function (n) {
        if (n.tagName === 'SCRIPT') {
          // Re-create so the browser executes it.
          var s = document.createElement('script')
          if (n.src) s.src = n.src
          else s.textContent = n.textContent
          document.body.appendChild(s)
        } else {
          document.body.appendChild(n)
        }
      })
    }

    if (document.body) mount()
    else document.addEventListener('DOMContentLoaded', mount)
  } catch (e) {
    if (window.console && console.error) console.error('[CF embed]', e)
  }
})()
