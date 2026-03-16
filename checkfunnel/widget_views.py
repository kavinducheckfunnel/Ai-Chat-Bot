from pathlib import Path
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse


def serve_widget_js(request):
    """Serve the compiled widget JS bundle so any site can embed it via a single <script> tag."""
    widget_path = Path(settings.BASE_DIR) / 'widget-vue' / 'dist' / 'assets' / 'widget.js'
    if not widget_path.exists():
        return HttpResponse(
            '// Widget not built. Run: cd widget-vue && npm run build\n',
            content_type='application/javascript',
            status=503,
        )
    response = FileResponse(open(widget_path, 'rb'), content_type='application/javascript')
    # Allow any site to load the widget
    response['Access-Control-Allow-Origin'] = '*'
    # Cache for 5 minutes in browsers, revalidate on CDN
    response['Cache-Control'] = 'public, max-age=300, s-maxage=3600'
    return response
