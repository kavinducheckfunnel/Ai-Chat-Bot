from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from . import widget_views, health_views

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('api/chat/', include('chat.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/scraper/', include('scraper.urls')),
    path('api/admin/', include('users.urls')),
    # Widget JS bundle — embeddable on any site
    path('widget/widget.js', widget_views.serve_widget_js, name='widget-js'),
    # Auto-updating loader — recommended one-line embed
    path('widget/embed.js', widget_views.serve_embed_js, name='widget-embed-js'),
    # CI/CD + uptime monitor pings this. Returns 200 only when DB + cache OK.
    # Exposed under /api/ so nginx's existing `location /api/` proxy_pass
    # forwards it to daphne without needing a separate location block.
    path('api/health/', health_views.health, name='health'),
    path('health/',     health_views.health, name='health-legacy'),
]

# In DEBUG, Django serves uploaded media files itself. In production
# nginx serves /media/ directly from disk — see the deploy notes.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
