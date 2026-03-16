from django.urls import path
from . import views

urlpatterns = [
    path('message/', views.chat_message, name='chat_message'),
    path('widget-config/<uuid:client_id>/', views.widget_config, name='widget_config'),
]
