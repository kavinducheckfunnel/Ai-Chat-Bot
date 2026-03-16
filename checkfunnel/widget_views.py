from pathlib import Path
from django.conf import settings
from django.http import HttpResponse


def serve_widget_js(request):
    """
    Serve the compiled widget JS bundle so any third-party site can embed
    it via a single <script> tag with no CORS / CORB issues.

    CORB (Cross-Origin Read Blocking) triggers when a <script> tag receives
    a response whose Content-Type is HTML/JSON/XML rather than JavaScript.
    This view:
      - Reads the file as text and returns it as application/javascript
      - Sets Access-Control-Allow-Origin: * (CORS)
      - Sets Cross-Origin-Resource-Policy: cross-origin (CORP — tells Chrome
        that this resource is intentionally shareable across origins)
      - Sets X-Content-Type-Options: nosniff so the browser trusts our MIME
        type declaration and never falls back to sniffing
    """
    widget_path = Path(settings.BASE_DIR) / 'widget-vue' / 'dist' / 'assets' / 'widget.js'

    if not widget_path.exists():
        # Return valid JS so the <script> tag never triggers CORB even on error
        return _js_response(
            '// Checkfunnel widget not built. Run: cd widget-vue && npm run build\n',
            status=503,
        )

    content = widget_path.read_text(encoding='utf-8')
    return _js_response(content)


def _js_response(content, status=200):
    response = HttpResponse(content, content_type='application/javascript; charset=utf-8', status=status)
    # ── CORS ───────────────────────────────────────────────────────────────────
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    # ── CORP — tells Chrome this resource is intentionally cross-origin ────────
    response['Cross-Origin-Resource-Policy'] = 'cross-origin'
    # ── Prevent content-type sniffing ─────────────────────────────────────────
    response['X-Content-Type-Options'] = 'nosniff'
    # ── Cache 5 min in browser, 1 hour on CDN ─────────────────────────────────
    response['Cache-Control'] = 'public, max-age=300, s-maxage=3600'
    return response
