from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('message/', views.chat_message, name='chat_message'),
    path('widget-config/<uuid:client_id>/', views.widget_config, name='widget_config'),
    path('trigger/', views.trigger_event, name='trigger_event'),
    path('lead/', views.capture_lead, name='capture_lead'),
    path('product/<str:product_id>/', views.product_detail, name='product_detail'),
]
