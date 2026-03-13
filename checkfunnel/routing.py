from django.urls import re_path
from chat import consumers
from chat import admin_consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<client_id>[\w-]+)/(?P<session_id>[\w-]+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/admin/dashboard/$', admin_consumers.AdminDashboardConsumer.as_asgi()),
    re_path(r'ws/admin/sessions/(?P<session_id>[\w-]+)/$', admin_consumers.GodViewConsumer.as_asgi()),
]
