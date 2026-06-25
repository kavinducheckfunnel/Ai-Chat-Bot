from django.urls import path
from . import views

urlpatterns = [
    # Public — widget
    path('message/', views.chat_message, name='chat_message'),
    path('widget-config/<uuid:client_id>/', views.widget_config, name='widget_config'),
    path('trigger/', views.trigger_event, name='trigger_event'),
    path('page-message/', views.page_message, name='page_message'),
    path('lead/', views.capture_lead, name='capture_lead'),
    path('link-click/', views.track_link_click, name='track_link_click'),
    path('session/<str:session_id>/messages/', views.session_messages, name='session_messages'),
    path('visitor/<uuid:client_id>/<str:visitor_uid>/latest/', views.visitor_latest_session, name='visitor_latest_session'),
    path('product/<str:product_id>/', views.product_detail, name='product_detail'),

    # Omnichannel webhooks (called by Meta's servers / Telegram)
    path('webhooks/whatsapp/<uuid:client_id>/', views.whatsapp_webhook, name='whatsapp_webhook'),
    path('webhooks/messenger/<uuid:client_id>/', views.messenger_webhook, name='messenger_webhook'),
    path('webhooks/instagram/<uuid:client_id>/', views.instagram_webhook, name='instagram_webhook'),
    path('webhooks/telegram/<uuid:client_id>/', views.telegram_webhook, name='telegram_webhook'),
]
