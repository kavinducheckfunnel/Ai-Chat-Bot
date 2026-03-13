from django.urls import path
from . import admin_views

urlpatterns = [
    # Admin API
    path('clients/', admin_views.ClientListCreateView.as_view(), name='admin_client_list'),
    path('clients/<uuid:pk>/', admin_views.ClientDetailView.as_view(), name='admin_client_detail'),
    path('clients/<uuid:client_id>/sessions/', admin_views.client_sessions, name='admin_client_sessions'),
    path('clients/<uuid:client_id>/analytics/', admin_views.client_analytics, name='admin_client_analytics'),
    path('clients/<uuid:client_id>/config/', admin_views.get_public_config, name='admin_client_config_public'),
    path('clients/<uuid:client_id>/scrape/', admin_views.trigger_scrape, name='admin_client_scrape'),
    path('sessions/<uuid:session_id>/', admin_views.session_detail, name='admin_session_detail'),
    path('stats/', admin_views.global_stats, name='admin_global_stats'),
]
