from django.contrib import admin
from django.urls import path, include
from . import widget_views

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('api/chat/', include('chat.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/scraper/', include('scraper.urls')),
    path('api/admin/', include('users.urls')),
    # Widget JS bundle — embeddable on any site
    path('widget/widget.js', widget_views.serve_widget_js, name='widget-js'),
]
